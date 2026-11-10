using VrCommand.Core;

namespace VrCommand.Api;

public record WorldShotTrace(string SessionId, string StreamId, long FromFrame, long ThroughFrame, Guid EventId,
    Guid ShotId, Guid PlayerId, int? RoomId, WorldShotTraceEvent[] Events);
public record WorldShotTraceEvent(Guid EventId, string Kind, long FrameSequence, long ElapsedMilliseconds, int RoomId);

public sealed partial class WorldRecordings
{
    public WorldShotTrace ShotTrace(Guid id, long from, long through, Guid eventId, int? room, OperatorIdentity actor,
        CancellationToken cancellation)
    {
        if (actor.Role is not (OperatorRole.Master or OperatorRole.RoomController))
            throw new AccessDeniedException("Shot review requires a control desk.");
        if (actor.Role == OperatorRole.RoomController)
        {
            if (room.HasValue && room != actor.RoomId) throw new AccessDeniedException("Select your own room for shot review.");
            room = actor.RoomId;
        }
        if (from < 1 || through < from || eventId == Guid.Empty)
            throw new ArgumentException("Select a saved event and a valid recording boundary.");
        var info = Info(id, actor);
        ValidateEventScope(info, through, room, null, null);
        var anchorFrame = Frame(id, from, actor) ?? throw new KeyNotFoundException("No saved world frame with this sequence.");
        var anchor = anchorFrame.Packet.events.SingleOrDefault(entry => entry.eventId == eventId.ToString("D")
            && entry.kind is "ShotFired" or "ShotHit" or "EnemyEliminated");
        if (anchor is null || !Guid.TryParseExact(anchor.shotId, "D", out var shotId) || !Guid.TryParseExact(anchor.playerId, "D", out var playerId))
            throw new KeyNotFoundException("No saved shot event at this frame.");
        if (room.HasValue && !anchorFrame.Statistics.Any(player => player.PlayerId == playerId && player.RoomId == room))
            throw new KeyNotFoundException("No saved shot event in this room.");

        var boundary = CombatBoundary(id, through);
        var witnesses = manager.CombatShotWitnesses(id, shotId, actor);
        if (!witnesses.Any(row => row.Report.ReportId == eventId)) throw new InvalidDataException("The saved shot has no durable report.");
        var result = new List<WorldShotTraceEvent>();
        foreach (var row in witnesses.Where(row => row.StreamSequence <= boundary))
        {
            cancellation.ThrowIfCancellationRequested();
            if (row.StreamId.ToString("D") != info.Header.streamId || row.Report.PlayerId != playerId)
                throw new InvalidDataException("Shot report belongs to another source or player.");
            long left = 1, right = through;
            while (left < right)
            {
                cancellation.ThrowIfCancellationRequested();
                var mid = left + (right - left) / 2;
                if (CombatBoundary(id, mid) < row.StreamSequence) left = mid + 1;
                else right = mid;
            }
            var frame = left == from ? anchorFrame : Frame(id, left, actor);
            if (frame is null || !frame.Packet.events.Any(entry => entry.eventId == row.Report.ReportId.ToString("D")
                && entry.kind == row.Report.Kind.ToString() && entry.shotId == anchor.shotId && entry.playerId == anchor.playerId))
                throw new InvalidDataException("Durable shot report does not match the saved frame.");
            var player = frame.Statistics.Single(item => item.PlayerId == playerId);
            if (!room.HasValue || player.RoomId == room.Value)
                result.Add(new(row.Report.ReportId, row.Report.Kind.ToString(), left, frame.Packet.elapsedMilliseconds, player.RoomId));
        }
        return new(info.Header.sessionId, info.Header.streamId, from, through, eventId, shotId, playerId, room, [.. result]);
    }

    // The accepted combat boundary is monotonic, so frame lookup needs only indexed frame reads.
    private long CombatBoundary(Guid id, long sequence)
    {
        lock (gate)
        {
            using var command = Command("SELECT json_extract(packet,'$.throughCombatSequence') FROM world_frames WHERE session=$id AND sequence=$seq",
                ("$id", id.ToString("D")), ("$seq", sequence));
            return command.ExecuteScalar() is long boundary ? boundary : throw new InvalidDataException("Saved world frame has no combat boundary.");
        }
    }
}
