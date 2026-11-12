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

public sealed partial class WorldRecordings
{
    private sealed record EnemyRosterState(string[] EnemyIds, int Alive);

    public WorldPolicyPage PolicyFrames(Guid id, long after, long through, bool includeEnemyRoster, int? roomId, string? change,
        OperatorIdentity actor, CancellationToken cancellation)
    {
        var info = Info(id, actor);
        if (after < 0 || through < 1 || after > through)
            throw new ArgumentException("Use a positive saved frame limit and a cursor within that limit.");
        if (through > info.AcceptedSequence)
            throw new KeyNotFoundException("No saved world frame with this sequence.");
        if (roomId.HasValue && (!includeEnemyRoster || !info.Header.roomIds.Contains(roomId.Value)))
            throw new ArgumentException("Select a room within this recording when including enemy rosters.");
        if (change is not (null or "initial" or "phase" or "environment" or "enemies" or "enemy-roster")
            || (change == "enemy-roster" && !includeEnemyRoster))
            throw new ArgumentException("Use a recorded policy change kind. Enemy roster changes require includeEnemyRoster.");

        var frames = new List<WorldPolicyFrame>();
        var scanned = after;
        var boundary = Math.Min(through, after + 1024);
        RecordedWorldPolicy? previous = null;
        EnemyRosterState? previousRoster = null;
        // An inclusive anchor compares the first candidate with its actual predecessor, even across pages.
        var first = Math.Max(1, after);
        while (scanned < boundary && frames.Count < 24)
        {
            var candidates = ReadPolicies(id, first, boundary, includeEnemyRoster, roomId, cancellation);
            if (candidates.Count == 0) throw new InvalidDataException("Saved world frame sequence has a gap.");
            foreach (var candidate in candidates)
            {
                cancellation.ThrowIfCancellationRequested();
                if (candidate.Sequence != first++) throw new InvalidDataException("Saved world frame sequence has a gap.");
                var policy = candidate.Policy;
                var roster = candidate.Roster is null ? null : WorldJson.Read<EnemyRosterState>(candidate.Roster);
                var rosterChanged = roster is not null && previousRoster is not null
                    && !roster.EnemyIds.SequenceEqual(previousRoster.EnemyIds);
                if (candidate.Sequence != after)
                {
                    scanned = candidate.Sequence;
                    if (policy != previous || rosterChanged)
                    {
                        var changes = new List<string>(4);
                        if (previous is null) changes.Add("initial");
                        else
                        {
                            if (policy.Phase != previous.Phase) changes.Add("phase");
                            if (policy.Weather != previous.Weather || policy.Night != previous.Night || policy.Lightning != previous.Lightning)
                                changes.Add("environment");
                            if (policy.Behavior != previous.Behavior || policy.AutoAttack != previous.AutoAttack) changes.Add("enemies");
                            if (rosterChanged) changes.Add("enemy-roster");
                        }
                        if (change is null || changes.Contains(change))
                        {
                            var observation = roster is null ? null : new WorldPolicyEnemyRoster(roster.EnemyIds, roster.Alive,
                                rosterChanged ? roster.EnemyIds.Except(previousRoster!.EnemyIds).Count() : 0,
                                rosterChanged ? previousRoster!.EnemyIds.Except(roster.EnemyIds).Count() : 0);
                            frames.Add(new(scanned, candidate.Elapsed, policy, changes.ToArray(), observation));
                        }
                    }
                }
                previous = policy;
                previousRoster = roster;
                if (frames.Count == 24) break;
            }
        }
        return new(info.Header.sessionId, info.Header.streamId, through, after, scanned, scanned < through ? scanned : null,
            frames, includeEnemyRoster ? true : null, roomId, change);
    }

    private List<(long Sequence, long Elapsed, RecordedWorldPolicy Policy, string? Roster)> ReadPolicies(Guid id,
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
        return candidates;
    }
}
