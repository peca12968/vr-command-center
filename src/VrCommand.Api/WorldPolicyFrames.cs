using System.Text.Json.Serialization;
using VrCommand.Core;

namespace VrCommand.Api;

public record RecordedWorldPolicy(string Phase, string Weather, bool Night, bool Lightning, string Behavior, bool AutoAttack);
public record WorldPolicyEnemyRoster(string[] EnemyIds, int Alive, int Added, int Removed);
public record WorldPolicyFrame(long FrameSequence, long ElapsedMilliseconds, RecordedWorldPolicy Policy, string[] Changes,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] WorldPolicyEnemyRoster? EnemyRoster = null);
public record WorldPolicyPage(string SessionId, string StreamId, long ThroughFrame, long AfterFrame,
    long ScannedThroughFrame, long? NextAfterFrame, IReadOnlyList<WorldPolicyFrame> Frames,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] bool? IncludeEnemyRoster = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] int? RoomId = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Change = null);
public record WorldPolicyNeighbor(string SessionId, string StreamId, long ThroughFrame, long FromFrame, string Direction,
    bool IncludeEnemyRoster, int? RoomId, string? Change, long ScannedToFrame, long? NextFromFrame, WorldPolicyFrame? Frame,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)] bool IncludeFrom = false);

public sealed partial class WorldRecordings
{
    private sealed record EnemyRosterState(string[] EnemyIds, int Alive);
    private sealed record PolicySample(long Sequence, long Elapsed, RecordedWorldPolicy Policy, EnemyRosterState? Roster);

    public WorldPolicyPage PolicyFrames(Guid id, long after, long through, bool includeEnemyRoster, int? roomId, string? change,
        OperatorIdentity actor, CancellationToken cancellation)
    {
        var info = Info(id, actor);
        if (after < 0 || through < 1 || after > through)
            throw new ArgumentException("Use a positive saved frame limit and a cursor within that limit.");
        ValidatePolicyScope(info, through, includeEnemyRoster, roomId, change);
        var frames = new List<WorldPolicyFrame>();
        var scanned = after;
        foreach (var candidate in ReadPolicyChanges(id, after, Math.Min(through, after + 1024), false, includeEnemyRoster, roomId, change, cancellation))
        {
            scanned = candidate.Sequence;
            if (candidate.Match is not { } match) continue;
            frames.Add(match);
            if (frames.Count == 24) break;
        }
        return new(info.Header.sessionId, info.Header.streamId, through, after, scanned, scanned < through ? scanned : null,
            frames, includeEnemyRoster ? true : null, roomId, change);
    }

    public WorldPolicyNeighbor PolicyNeighbor(Guid id, long from, long through, string direction, bool includeFrom, bool includeEnemyRoster,
        int? roomId, string? change, OperatorIdentity actor, CancellationToken cancellation)
    {
        var info = Info(id, actor);
        if (from < 1 || from > through || direction is not ("previous" or "next") || (includeFrom && direction != "previous"))
            throw new ArgumentException("Use a saved frame within the limit and select previous or next.");
        ValidatePolicyScope(info, through, includeEnemyRoster, roomId, change);
        var reverse = direction == "previous";
        var end = reverse ? 1 : through;
        var cursor = includeFrom ? from + 1 : from;
        var boundary = reverse ? Math.Max(end, cursor - 1024) : Math.Min(end, cursor + 1024);
        foreach (var candidate in ReadPolicyChanges(id, cursor, boundary, reverse, includeEnemyRoster, roomId, change, cancellation))
            if (candidate.Match is { } match)
                return new(info.Header.sessionId, info.Header.streamId, through, from, direction, includeEnemyRoster,
                    roomId, change, candidate.Sequence, null, match, includeFrom);
        return new(info.Header.sessionId, info.Header.streamId, through, from, direction, includeEnemyRoster,
            roomId, change, boundary, boundary == end ? null : boundary, null, includeFrom);
    }

    private static void ValidatePolicyScope(WorldRecordingInfo info, long through, bool includeEnemyRoster, int? roomId, string? change)
    {
        if (through > info.AcceptedSequence)
            throw new KeyNotFoundException("No saved world frame with this sequence.");
        if (roomId.HasValue && (!includeEnemyRoster || !info.Header.roomIds.Contains(roomId.Value)))
            throw new ArgumentException("Select a room within this recording when including enemy rosters.");
        if (change is not (null or "initial" or "phase" or "environment" or "enemies" or "enemy-roster")
            || (change == "enemy-roster" && !includeEnemyRoster))
            throw new ArgumentException("Use a recorded policy change kind. Enemy roster changes require includeEnemyRoster.");
    }

    private IEnumerable<(long Sequence, WorldPolicyFrame? Match)> ReadPolicyChanges(Guid id, long cursor, long boundary,
        bool reverse, bool includeEnemyRoster, int? roomId, string? change, CancellationToken cancellation)
    {
        while (cursor != boundary)
        {
            var first = reverse ? Math.Max(boundary, cursor - 127) : cursor + 1;
            var last = reverse ? cursor - 1 : Math.Min(boundary, cursor + 127);
            // Keep one predecessor in each SQL batch, even when visiting candidates backwards.
            var anchor = Math.Max(1, first - 1);
            var samples = ReadPolicies(id, anchor, last, includeEnemyRoster, roomId, cancellation);
            if (samples.Count != last - anchor + 1 || samples.Where((sample, index) => sample.Sequence != anchor + index).Any())
                throw new InvalidDataException("Saved world frame sequence has a gap.");
            var count = last - first + 1;
            for (var offset = 0; offset < count; offset++)
            {
                cancellation.ThrowIfCancellationRequested();
                var sequence = reverse ? last - offset : first + offset;
                var index = (int)(sequence - anchor);
                yield return (sequence, DescribePolicy(samples[index], index > 0 ? samples[index - 1] : null, change));
            }
            cursor = reverse ? first : last;
        }
    }

    private static WorldPolicyFrame? DescribePolicy(PolicySample candidate, PolicySample? previous, string? change)
    {
        var policy = candidate.Policy;
        var roster = candidate.Roster;
        var priorRoster = previous?.Roster;
        var rosterChanged = roster is not null && priorRoster is not null && !roster.EnemyIds.SequenceEqual(priorRoster.EnemyIds);
        if (policy == previous?.Policy && !rosterChanged) return null;
        var changes = new List<string>(4);
        if (previous is null) changes.Add("initial");
        else
        {
            if (policy.Phase != previous.Policy.Phase) changes.Add("phase");
            if (policy.Weather != previous.Policy.Weather || policy.Night != previous.Policy.Night || policy.Lightning != previous.Policy.Lightning)
                changes.Add("environment");
            if (policy.Behavior != previous.Policy.Behavior || policy.AutoAttack != previous.Policy.AutoAttack) changes.Add("enemies");
            if (rosterChanged) changes.Add("enemy-roster");
        }
        if (change is not null && !changes.Contains(change)) return null;
        var observation = roster is null ? null : new WorldPolicyEnemyRoster(roster.EnemyIds, roster.Alive,
            rosterChanged ? roster.EnemyIds.Except(priorRoster!.EnemyIds).Count() : 0,
            rosterChanged ? priorRoster!.EnemyIds.Except(roster.EnemyIds).Count() : 0);
        return new(candidate.Sequence, candidate.Elapsed, policy, changes.ToArray(), observation);
    }

    private List<PolicySample> ReadPolicies(Guid id,
        long first, long boundary, bool includeEnemyRoster, int? roomId, CancellationToken cancellation)
    {
        var candidates = new List<(long, long, RecordedWorldPolicy, string?)>();
        // Project only the fields needed for the timeline. Compare them outside the archive gate.
        lock (gate)
        {
            cancellation.ThrowIfCancellationRequested();
            using var command = Command("""
                SELECT sequence, elapsed, coalesce(json_extract(packet,'$.frame.phase'),'Preparing'),
                  coalesce(json_extract(packet,'$.weather'),'Clear'), coalesce(json_extract(packet,'$.frame.night'),0),
                  coalesce(json_extract(packet,'$.lightning'),0),
                  coalesce(json_extract(roomPolicy.value,'$.behavior'),json_extract(packet,'$.frame.behavior'),'Hold'),
                  coalesce(json_extract(roomPolicy.value,'$.autoAttack'),json_extract(packet,'$.frame.autoAttack'),0),
                  CASE WHEN $roster THEN (
                    SELECT json_object('enemyIds',json_group_array(json_extract(enemy.value,'$.id') ORDER BY json_extract(enemy.value,'$.id')),
                        'alive',count(CASE WHEN json_extract(enemy.value,'$.health') > 0 THEN 1 END))
                    FROM json_each(world_frames.packet,'$.frame.enemies') AS enemy
                    WHERE $room IS NULL OR json_extract(enemy.value,'$.roomId')=$room
                  ) END
                FROM world_frames
                LEFT JOIN json_each(world_frames.packet,'$.frame.roomEnemyPolicies') AS roomPolicy
                  ON $room IS NOT NULL AND json_extract(roomPolicy.value,'$.roomId')=$room
                WHERE session=$id AND sequence BETWEEN $first AND $boundary ORDER BY sequence LIMIT 128
                """, ("$id", id.ToString("D")), ("$first", first), ("$boundary", boundary),
                ("$roster", includeEnemyRoster), ("$room", (object?)roomId ?? DBNull.Value));
            using var row = command.ExecuteReader();
            while (row.Read())
            {
                cancellation.ThrowIfCancellationRequested();
                candidates.Add((row.GetInt64(0), row.GetInt64(1), new(row.GetString(2), row.GetString(3), row.GetBoolean(4),
                    row.GetBoolean(5), row.GetString(6), row.GetBoolean(7)), row.IsDBNull(8) ? null : row.GetString(8)));
            }
        }
        return candidates.Select(row => new PolicySample(row.Item1, row.Item2, row.Item3,
            row.Item4 is null ? null : WorldJson.Read<EnemyRosterState>(row.Item4))).ToList();
    }
}
