using System.Text.Json;
using VrCommand.Core;
using VrCommand.Simulation;

namespace VrCommand.Api;

public record WorldEventFrame(long FrameSequence, long ElapsedMilliseconds, int MatchCount);
public record WorldEventFramePage(string SessionId, string StreamId, long ThroughFrame, long AfterFrame,
    long ScannedThroughFrame, long? NextAfterFrame, IReadOnlyList<WorldEventFrame> Frames);

public sealed partial class WorldRecordings
{
    private static readonly HashSet<string> EventKinds = new(Enum.GetNames<WorldEventKind>(), StringComparer.Ordinal);

    public WorldEventFramePage EventFrames(Guid id, long after, long through, int? room, string? kind,
        OperatorIdentity actor, CancellationToken cancellation)
    {
        var info = Info(id, actor);
        if (after < 0 || through < 1 || after > through)
            throw new ArgumentException("Use a positive saved frame limit and a cursor within that limit.");
        if (through > info.AcceptedSequence) throw new KeyNotFoundException("No saved world frame with this sequence.");
        if (room is int roomId && !info.Header.roomIds.Contains(roomId))
            throw new ArgumentException("Select a room within this recording.");
        if (kind is not null && !EventKinds.Contains(kind))
            throw new ArgumentException("Select a recorded combat event kind.");

        // Read an immutable prefix while holding the SQLite gate. Parse it after releasing the publisher.
        var candidates = new List<(long Sequence, long Elapsed, string Packet, string? Statistics)>();
        lock (gate)
        {
            cancellation.ThrowIfCancellationRequested();
            using var command = Command("""
                SELECT sequence, elapsed, packet, CASE WHEN $scoped THEN statistics ELSE NULL END
                FROM world_frames WHERE session=$id AND sequence>$after AND sequence<=$through
                ORDER BY sequence LIMIT 128
                """, ("$id", id.ToString("D")), ("$after", after), ("$through", through), ("$scoped", room.HasValue));
            using var row = command.ExecuteReader();
            long bytes = 0;
            while (row.Read())
            {
                cancellation.ThrowIfCancellationRequested();
                var packet = row.GetString(2);
                var statistics = row.IsDBNull(3) ? null : row.GetString(3);
                bytes += 2L * (packet.Length + (statistics?.Length ?? 0));
                if (candidates.Count > 0 && bytes > 4 * 1024 * 1024) break;
                candidates.Add((row.GetInt64(0), row.GetInt64(1), packet, statistics));
            }
        }

        var frames = new List<WorldEventFrame>();
        var scanned = after;
        foreach (var (sequence, elapsed, packet, statistics) in candidates)
        {
            cancellation.ThrowIfCancellationRequested();
            if (sequence != scanned + 1) throw new InvalidDataException("Saved world frame sequence has a gap.");
            scanned = sequence;
            using var json = JsonDocument.Parse(packet);
            var events = json.RootElement.GetProperty("events");
            if (events.GetArrayLength() == 0) continue;
            var players = statistics is null ? null : WorldJson.Read<PlayerStatistics[]>(statistics)
                .Where(player => player.RoomId == room).Select(player => player.PlayerId).ToHashSet();
            var count = 0;
            foreach (var entry in events.EnumerateArray())
            {
                if (kind is not null && !entry.GetProperty("kind").ValueEquals(kind)) continue;
                if (players is not null && (!entry.GetProperty("playerId").TryGetGuid(out var player) || !players.Contains(player))) continue;
                count++;
            }
            if (count == 0) continue;
            frames.Add(new(sequence, elapsed, count));
            if (frames.Count == 24) break;
        }
        if (scanned == after && after < through) throw new InvalidDataException("Saved world frame sequence has a gap.");
        return new(info.Header.sessionId, info.Header.streamId, through, after, scanned, scanned < through ? scanned : null, frames);
    }
}
