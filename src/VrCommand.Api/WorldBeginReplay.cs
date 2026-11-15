using VrCommand.Core;

namespace VrCommand.Api;

internal sealed record WorldBeginReplay(Guid SessionId, Guid StreamId, Guid BeginRequestId, long AppliedAtSequence,
    long BeginFrame, long ThroughFrame, WorldFrameView? Frame);
public sealed record TrackedVrStartPlayer(Guid PlayerId, int RoomId);
public sealed record WorldTrackedVrStart(Guid SessionId, Guid StreamId, long AppliedAtSequence,
    long WorldSequence, long ElapsedMilliseconds, TrackedVrStartPlayer[] Players);

public sealed partial class WorldRecordings
{
    private WorldTrackedVrStart? ReadWorldTrackedVrStart(SessionView session, WorldRecordingInfo world, OperatorIdentity actor)
    {
        if (session.Environment.Mode != ExperienceMode.VR || world.Header.origin != "GameServer"
            || (actor.Role != OperatorRole.Master && session.Mode != SessionMode.Independent)
            || manager.ReadTrackedVrStart(session.Id, actor) is not { } start)
            return null;
        var anchor = start.Frame;
        if (anchor.StreamId.ToString("D") != world.Header.streamId || anchor.WorldSequence >= world.AcceptedSequence
            || Frame(session.Id, anchor.WorldSequence, actor) is not { Packet: var packet }
            || packet.elapsedMilliseconds != anchor.ElapsedMilliseconds || packet.observedSequence != start.AppliedAtSequence - 1
            || packet.suspended || packet.frame.phase != "Preparing" || packet.frame.tick != 0)
            return null;

        var roster = manager.Observed(session.Id, packet.observedSequence, actor).Players;
        var connected = packet.frame.players.Where(player => player.connected).ToDictionary(player => player.id);
        if (roster.Length == 0 || connected.Count != roster.Length || roster.Any(player =>
            !connected.TryGetValue(player.Id.ToString("D"), out var body) || body.roomId != player.RoomId
            || body.health <= 0 || body.rig.kind != "Tracked")) return null;

        return new(session.Id, anchor.StreamId, start.AppliedAtSequence, anchor.WorldSequence, anchor.ElapsedMilliseconds,
            roster.Select(player => new TrackedVrStartPlayer(player.Id, player.RoomId)).ToArray());
    }

    internal WorldBeginReplay ReadWorldBeginReplay(Guid id, long throughFrame, OperatorIdentity actor, CancellationToken cancellation)
    {
        var (tracking, participation) = manager.ReadVenueBeginEvidence(id, actor);
        var anchor = tracking?.Frame ?? participation?.Frame;
        if (anchor is null || tracking is not null && participation is not null)
            throw new KeyNotFoundException("No guarded venue Begin for this recording.");
        var appliedAt = tracking?.AppliedAtSequence ?? participation!.AppliedAtSequence;
        var requestId = tracking?.RequestId ?? participation!.RequestId;
        var info = Info(id, actor);
        if (throughFrame < anchor.WorldSequence || throughFrame > info.AcceptedSequence)
            throw new ArgumentException("Use a saved frame limit at or after the original Begin witness.");
        if (info.Header.streamId != anchor.StreamId.ToString("D"))
            throw new InvalidOperationException("The saved recording differs from the original Begin witness.");

        // Bound each database read so a long recording does not hold the publication gate for the entire search.
        for (var first = anchor.WorldSequence + 1; first <= throughFrame; first += 256)
        {
            cancellation.ThrowIfCancellationRequested();
            lock (gate)
            {
                cancellation.ThrowIfCancellationRequested();
                using var query = Command("""
                    SELECT sequence FROM world_frames
                    WHERE session=$id AND sequence BETWEEN $first AND $last
                      AND json_extract(packet,'$.observedSequence') >= $applied
                      AND json_extract(packet,'$.frame.phase') = 'Running'
                      AND json_extract(packet,'$.frame.tick') > 0
                      AND json_extract(packet,'$.suspended') = 0
                    ORDER BY sequence LIMIT 1
                    """, ("$id", id.ToString("D")), ("$first", first), ("$last", Math.Min(throughFrame, first + 255)), ("$applied", appliedAt));
                if (query.ExecuteScalar() is long sequence)
                {
                    var frame = Frame(id, sequence, actor) ?? throw new InvalidDataException("Missing original Running frame.");
                    return new(id, anchor.StreamId, requestId, appliedAt, anchor.WorldSequence, throughFrame, frame);
                }
            }
        }
        return new(id, anchor.StreamId, requestId, appliedAt, anchor.WorldSequence, throughFrame, null);
    }
}
