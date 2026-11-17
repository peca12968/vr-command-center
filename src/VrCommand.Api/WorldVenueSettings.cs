using System.Text.Json.Serialization;
using VrCommand.Core;
using VrCommand.Simulation;

namespace VrCommand.Api;

internal sealed record WorldVenueSetting(Guid SessionId, Guid RequestId, Guid StreamId, int[] RoomIds,
    long AppliedAtSequence, long? WorldSequence,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] WorldVenueEnemyPopulation[]? EnemyPopulations = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] long? ObservedSequence = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] long? SupersededAtSequence = null);
internal sealed record WorldVenueEnemyPopulation(int RoomId, int Present, int Alive);

public sealed partial class WorldRecordings
{
    internal WorldVenueSetting ReadWorldVenueEnvironment(Guid id, Guid requestId, OperatorIdentity actor, CancellationToken cancellation)
    {
        var (applied, command, superseded, through) = manager.ReadVenueSettingCommand(id, requestId, ControlAction.SetEnvironment, actor);
        var environment = command.Environment!;
        var info = Info(id, actor);
        var weather = environment.Weather.ToString();
        var night = environment.TimeOfDay == TimeOfDay.Night;
        var packet = FindOriginalVenueSettingFrame(id, info.AcceptedSequence, applied, superseded ?? through + 1, candidate => candidate.weather == weather
            && candidate.frame.night == night && candidate.lightning == environment.Lightning, cancellation);
        return new(id, requestId, Guid.Parse(info.Header.streamId), info.Header.roomIds, applied, packet?.sequence,
            ObservedSequence: packet?.observedSequence, SupersededAtSequence: superseded);
    }

    internal WorldVenueSetting ReadWorldVenueEnemies(Guid id, Guid requestId, OperatorIdentity actor, CancellationToken cancellation)
    {
        var (applied, command, _, _) = manager.ReadVenueSettingCommand(id, requestId, ControlAction.SetEnemies, actor);
        var enemies = command.Enemies!;
        var info = Info(id, actor);
        var behavior = enemies.Behavior.ToString();
        var packet = FindOriginalVenueSettingFrame(id, info.AcceptedSequence, applied, applied + 1, candidate => candidate.frame.behavior == behavior
            && candidate.frame.autoAttack == enemies.AutoAttack && candidate.frame.roomEnemyPolicies is null or { Length: 0 }, cancellation);
        var byRoom = packet?.frame.enemies.ToLookup(enemy => enemy.roomId);
        var populations = byRoom is null ? null : info.Header.roomIds.Select(room =>
            new WorldVenueEnemyPopulation(room, byRoom[room].Count(), byRoom[room].Count(enemy => enemy.health > 0))).ToArray();
        return new(id, requestId, Guid.Parse(info.Header.streamId), info.Header.roomIds, applied, packet?.sequence, populations);
    }

    private WorldRecordingPacket? FindOriginalVenueSettingFrame(Guid id, long acceptedSequence, long applied, long upper,
        Func<WorldRecordingPacket, bool> matchesSetting, CancellationToken cancellation)
    {
        var session = id.ToString("D");

        // World frames are contiguous and their observed management sequence never decreases.
        long first = 1, end = acceptedSequence + 1;
        while (first < end)
        {
            cancellation.ThrowIfCancellationRequested();
            var middle = first + (end - first) / 2;
            lock (gate)
            {
                if (ReadWorldObservation(session, middle) < applied) first = middle + 1;
                else end = middle;
            }
        }

        for (; first <= acceptedSequence; first += 256)
        {
            cancellation.ThrowIfCancellationRequested();
            lock (gate)
            {
                if (ReadWorldObservation(session, first) >= upper) break;
                using var query = Command("""
                    SELECT packet FROM world_frames
                    WHERE session=$session AND sequence BETWEEN $first AND $last
                      AND json_extract(packet,'$.observedSequence') >= $applied
                      AND json_extract(packet,'$.observedSequence') < $upper
                      AND json_extract(packet,'$.frame.phase') = 'Running'
                      AND json_extract(packet,'$.frame.tick') > 0
                      AND json_extract(packet,'$.suspended') = 0
                    ORDER BY sequence
                    """, ("$session", session), ("$first", first), ("$last", Math.Min(acceptedSequence, first + 255)),
                    ("$applied", applied), ("$upper", upper));
                using var rows = query.ExecuteReader();
                while (rows.Read())
                {
                    cancellation.ThrowIfCancellationRequested();
                    var packet = WorldJson.Read<WorldRecordingPacket>(rows.GetString(0));
                    if (matchesSetting(packet)) return packet;
                }
            }
        }
        return null;
    }

    private long ReadWorldObservation(string session, long sequence)
    {
        using var query = Command("SELECT json_extract(packet,'$.observedSequence') FROM world_frames WHERE session=$session AND sequence=$sequence",
            ("$session", session), ("$sequence", sequence));
        return query.ExecuteScalar() is long observed ? observed : throw new InvalidDataException("Missing original world observation.");
    }
}
