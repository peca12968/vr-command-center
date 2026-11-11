using System.Text.Json;
using System.Text.Json.Serialization;
using VrCommand.Core;
using VrCommand.Simulation;

namespace VrCommand.Api;

public record WorldEventFrame(long FrameSequence, long ElapsedMilliseconds, int MatchCount);
public record WorldEventFramePage(string SessionId, string StreamId, long ThroughFrame, long AfterFrame,
    long ScannedThroughFrame, long? NextAfterFrame, Guid? PlayerId, IReadOnlyList<WorldEventFrame> Frames)
{
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? ObserverRoomId { get; init; }
}
public record WorldEventNeighbor(string SessionId, string StreamId, long ThroughFrame, long FromFrame,
    string Direction, int? RoomId, string? Kind, Guid? PlayerId, long ScannedToFrame, long? NextFromFrame, WorldEventFrame? Frame)
{
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? ObserverRoomId { get; init; }
}

public sealed partial class WorldRecordings
{
    private static readonly HashSet<string> EventKinds = new(Enum.GetNames<WorldEventKind>(), StringComparer.Ordinal);
    private sealed record EventObservation(int RoomId, IReadOnlyDictionary<string, int> PropRooms);

    public WorldEventFramePage EventFrames(Guid id, long after, long through, int? room, string? kind, Guid? playerId,
        OperatorIdentity actor, CancellationToken cancellation, int? observerRoomId = null)
    {
        var info = Info(id, actor);
        if (after < 0 || through < 1 || after > through)
            throw new ArgumentException("Use a positive saved frame limit and a cursor within that limit.");
        ValidateEventScope(info, through, room, kind, playerId);
        var observation = EventScope(info, room, observerRoomId, actor);
        var frames = new List<WorldEventFrame>();
        var scanned = after;
        foreach (var candidate in ReadEventCandidates(id, after, through, false, room.HasValue && observation is null, cancellation))
        {
            cancellation.ThrowIfCancellationRequested();
            if (candidate.Sequence != scanned + 1) throw new InvalidDataException("Saved world frame sequence has a gap.");
            scanned = candidate.Sequence;
            var count = observation is null ? CountEvents(candidate.Events, candidate.Statistics, room, kind, playerId)
                : CountObservedEvents(id, scanned, candidate.Events, observation, kind, playerId, actor);
            if (count == 0) continue;
            frames.Add(new(scanned, candidate.Elapsed, count));
            if (frames.Count == 24) break;
        }
        if (scanned == after && after < through) throw new InvalidDataException("Saved world frame sequence has a gap.");
        return new(info.Header.sessionId, info.Header.streamId, through, after, scanned, scanned < through ? scanned : null, playerId, frames)
            { ObserverRoomId = observerRoomId };
    }

    public WorldEventNeighbor EventNeighbor(Guid id, long from, long through, string direction, int? room, string? kind,
        Guid? playerId, OperatorIdentity actor, CancellationToken cancellation, int? observerRoomId = null)
    {
        var info = Info(id, actor);
        if (from < 1 || from > through || direction is not ("previous" or "next"))
            throw new ArgumentException("Use a saved frame within the limit and select previous or next.");
        ValidateEventScope(info, through, room, kind, playerId);
        var observation = EventScope(info, room, observerRoomId, actor);
        var reverse = direction == "previous";
        var end = reverse ? 1 : through;
        var boundary = reverse ? Math.Max(end, from - 2048) : from + Math.Min(2048, end - from);
        var cursor = from;
        WorldEventNeighbor Result(WorldEventFrame? frame, long? continuation) => new(info.Header.sessionId,
            info.Header.streamId, through, from, direction, observerRoomId ?? room, kind, playerId, cursor, continuation, frame)
            { ObserverRoomId = observerRoomId };
        while (cursor != boundary)
        {
            var candidates = ReadEventCandidates(id, cursor, boundary, reverse, room.HasValue && observation is null, cancellation);
            if (candidates.Count == 0) throw new InvalidDataException("Saved world frame sequence has a gap.");
            foreach (var candidate in candidates)
            {
                cancellation.ThrowIfCancellationRequested();
                if (candidate.Sequence != cursor + (reverse ? -1 : 1)) throw new InvalidDataException("Saved world frame sequence has a gap.");
                cursor = candidate.Sequence;
                var count = observation is null ? CountEvents(candidate.Events, candidate.Statistics, room, kind, playerId)
                    : CountObservedEvents(id, cursor, candidate.Events, observation, kind, playerId, actor);
                if (count > 0) return Result(new(cursor, candidate.Elapsed, count), null);
            }
        }
        return Result(null, cursor == end ? null : cursor);
    }

    private static EventObservation? EventScope(WorldRecordingInfo info, int? room, int? observerRoomId, OperatorIdentity actor)
    {
        if (observerRoomId is not int observer) return null;
        RequireObserverRoom(info, observer, actor);
        if (room is int filter && filter != observer)
            throw new ArgumentException("The event room must match the observation room.");
        return new(observer, info.Header.props.ToDictionary(prop => prop.id, prop => prop.roomId));
    }

    private int CountObservedEvents(Guid id, long sequence, string events, EventObservation observation, string? kind,
        Guid? playerId, OperatorIdentity actor)
    {
        if (events == "[]") return 0;
        var frame = Frame(id, sequence, actor) ?? throw new InvalidDataException("Saved world frame sequence has a gap.");
        var projected = ObservationFrame(id, frame, observation.RoomId, observation.PropRooms, actor);
        var player = playerId?.ToString("D");
        return projected.Packet.events.Count(entry => (kind is null || entry.kind == kind) && (player is null || entry.playerId == player));
    }

    private static void ValidateEventScope(WorldRecordingInfo info, long through, int? room, string? kind, Guid? playerId)
    {
        if (through > info.AcceptedSequence) throw new KeyNotFoundException("No saved world frame with this sequence.");
        if (room is int roomId && !info.Header.roomIds.Contains(roomId))
            throw new ArgumentException("Select a room within this recording.");
        if (kind is not null && !EventKinds.Contains(kind))
            throw new ArgumentException("Select a recorded combat event kind.");
        if (playerId == Guid.Empty) throw new ArgumentException("Select a nonempty player ID.");
    }

    private List<(long Sequence, long Elapsed, string Events, string? Statistics)> ReadEventCandidates(Guid id, long cursor,
        long boundary, bool reverse, bool scoped, CancellationToken cancellation)
    {
        // Read an immutable prefix while holding the SQLite gate. Parse it after releasing the publisher.
        var candidates = new List<(long Sequence, long Elapsed, string Events, string? Statistics)>();
        var window = reverse ? "sequence<$cursor AND sequence>=$boundary ORDER BY sequence DESC"
            : "sequence>$cursor AND sequence<=$boundary ORDER BY sequence";
        lock (gate)
        {
            cancellation.ThrowIfCancellationRequested();
            using var command = Command($"""
                SELECT sequence, elapsed, json_extract(packet,'$.events'),
                  CASE WHEN $scoped AND json_array_length(packet,'$.events') > 0 THEN statistics ELSE NULL END
                FROM world_frames WHERE session=$id AND {window} LIMIT 128
                """, ("$id", id.ToString("D")), ("$cursor", cursor), ("$boundary", boundary), ("$scoped", scoped));
            using var row = command.ExecuteReader();
            long bytes = 0;
            while (row.Read())
            {
                cancellation.ThrowIfCancellationRequested();
                var events = row.GetString(2);
                var statistics = row.IsDBNull(3) ? null : row.GetString(3);
                bytes += 2L * (events.Length + (statistics?.Length ?? 0));
                if (candidates.Count > 0 && bytes > 4 * 1024 * 1024) break;
                candidates.Add((row.GetInt64(0), row.GetInt64(1), events, statistics));
            }
        }
        return candidates;
    }

    private static int CountEvents(string events, string? statistics, int? room, string? kind, Guid? playerId)
    {
        if (events == "[]") return 0;
        using var json = JsonDocument.Parse(events);
        var players = statistics is null ? null : WorldJson.Read<PlayerStatistics[]>(statistics)
            .Where(player => player.RoomId == room).Select(player => player.PlayerId).ToHashSet();
        var count = 0;
        foreach (var entry in json.RootElement.EnumerateArray())
        {
            if (kind is not null && !entry.GetProperty("kind").ValueEquals(kind)) continue;
            if ((players is not null || playerId.HasValue)
                && (!entry.GetProperty("playerId").TryGetGuid(out var player)
                    || (playerId.HasValue && player != playerId.Value)
                    || (players is not null && !players.Contains(player)))) continue;
            count++;
        }
        return count;
    }
}
