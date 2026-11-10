using VrCommand.Core;

namespace VrCommand.Api;

public record RecordedWorldPolicy(string Phase, string Weather, bool Night, bool Lightning, string Behavior, bool AutoAttack);
public record WorldPolicyFrame(long FrameSequence, long ElapsedMilliseconds, RecordedWorldPolicy Policy, string[] Changes);
public record WorldPolicyPage(string SessionId, string StreamId, long ThroughFrame, long AfterFrame,
    long ScannedThroughFrame, long? NextAfterFrame, IReadOnlyList<WorldPolicyFrame> Frames);

public sealed partial class WorldRecordings
{
    public WorldPolicyPage PolicyFrames(Guid id, long after, long through, OperatorIdentity actor, CancellationToken cancellation)
    {
        var info = Info(id, actor);
        if (after < 0 || through < 1 || after > through)
            throw new ArgumentException("Use a positive saved frame limit and a cursor within that limit.");
        if (through > info.AcceptedSequence)
            throw new KeyNotFoundException("No saved world frame with this sequence.");

        var frames = new List<WorldPolicyFrame>();
        var scanned = after;
        var boundary = Math.Min(through, after + 1024);
        RecordedWorldPolicy? previous = null;
        // An inclusive anchor compares the first candidate with its actual predecessor, even across pages.
        var first = Math.Max(1, after);
        while (scanned < boundary && frames.Count < 24)
        {
            var candidates = ReadPolicies(id, first, boundary, cancellation);
            if (candidates.Count == 0) throw new InvalidDataException("Saved world frame sequence has a gap.");
            foreach (var candidate in candidates)
            {
                cancellation.ThrowIfCancellationRequested();
                if (candidate.Sequence != first++) throw new InvalidDataException("Saved world frame sequence has a gap.");
                var policy = candidate.Policy;
                if (candidate.Sequence != after)
                {
                    scanned = candidate.Sequence;
                    if (policy != previous)
                    {
                        var changes = new List<string>(3);
                        if (previous is null) changes.Add("initial");
                        else
                        {
                            if (policy.Phase != previous.Phase) changes.Add("phase");
                            if (policy.Weather != previous.Weather || policy.Night != previous.Night || policy.Lightning != previous.Lightning)
                                changes.Add("environment");
                            if (policy.Behavior != previous.Behavior || policy.AutoAttack != previous.AutoAttack) changes.Add("enemies");
                        }
                        frames.Add(new(scanned, candidate.Elapsed, policy, changes.ToArray()));
                    }
                }
                previous = policy;
                if (frames.Count == 24) break;
            }
        }
        return new(info.Header.sessionId, info.Header.streamId, through, after, scanned, scanned < through ? scanned : null, frames);
    }

    private List<(long Sequence, long Elapsed, RecordedWorldPolicy Policy)> ReadPolicies(Guid id, long first, long boundary,
        CancellationToken cancellation)
    {
        var candidates = new List<(long, long, RecordedWorldPolicy)>();
        // Keep only scalar fields and release the archive gate between batches so publishers can progress.
        lock (gate)
        {
            cancellation.ThrowIfCancellationRequested();
            using var command = Command("""
                SELECT sequence, elapsed, coalesce(json_extract(packet,'$.frame.phase'),'Preparing'),
                  coalesce(json_extract(packet,'$.weather'),'Clear'), coalesce(json_extract(packet,'$.frame.night'),0),
                  coalesce(json_extract(packet,'$.lightning'),0), coalesce(json_extract(packet,'$.frame.behavior'),'Hold'),
                  coalesce(json_extract(packet,'$.frame.autoAttack'),0)
                FROM world_frames WHERE session=$id AND sequence BETWEEN $first AND $boundary ORDER BY sequence LIMIT 128
                """, ("$id", id.ToString("D")), ("$first", first), ("$boundary", boundary));
            using var row = command.ExecuteReader();
            while (row.Read())
            {
                cancellation.ThrowIfCancellationRequested();
                candidates.Add((row.GetInt64(0), row.GetInt64(1), new(row.GetString(2), row.GetString(3), row.GetBoolean(4),
                    row.GetBoolean(5), row.GetString(6), row.GetBoolean(7))));
            }
        }
        return candidates;
    }
}
