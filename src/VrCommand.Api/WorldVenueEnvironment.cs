using VrCommand.Core;

namespace VrCommand.Api;

internal sealed record WorldVenueEnvironment(Guid SessionId, Guid RequestId, Guid StreamId, int[] RoomIds,
    long AppliedAtSequence, long? WorldSequence);

public sealed partial class WorldRecordings
{
    internal WorldVenueEnvironment ReadWorldVenueEnvironment(Guid id, Guid requestId, OperatorIdentity actor, CancellationToken cancellation)
    {
        var (applied, environment) = manager.ReadVenueEnvironmentCommand(id, requestId, actor);
        var info = Info(id, actor);
        var session = id.ToString("D");
        var result = new WorldVenueEnvironment(id, requestId, Guid.Parse(info.Header.streamId), info.Header.roomIds,
            applied, null);

        // World frames are contiguous and their observed management sequence never decreases.
        long first = 1, end = info.AcceptedSequence + 1;
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

        for (; first <= info.AcceptedSequence; first += 256)
        {
            cancellation.ThrowIfCancellationRequested();
            lock (gate)
            {
                if (ReadWorldObservation(session, first) != applied) break;
                using var query = Command("""
                    SELECT sequence FROM world_frames
                    WHERE session=$session AND sequence BETWEEN $first AND $last
                      AND json_extract(packet,'$.observedSequence') = $applied
                      AND json_extract(packet,'$.frame.phase') = 'Running'
                      AND json_extract(packet,'$.frame.tick') > 0
                      AND json_extract(packet,'$.suspended') = 0
                      AND json_extract(packet,'$.weather') = $weather
                      AND json_extract(packet,'$.frame.night') = $night
                      AND json_extract(packet,'$.lightning') = $lightning
                    ORDER BY sequence LIMIT 1
                    """, ("$session", session), ("$first", first), ("$last", Math.Min(info.AcceptedSequence, first + 255)),
                    ("$applied", applied), ("$weather", environment.Weather.ToString()),
                    ("$night", environment.TimeOfDay == TimeOfDay.Night ? 1 : 0), ("$lightning", environment.Lightning ? 1 : 0));
                if (query.ExecuteScalar() is long sequence) return result with { WorldSequence = sequence };
            }
        }
        return result;
    }

    private long ReadWorldObservation(string session, long sequence)
    {
        using var query = Command("SELECT json_extract(packet,'$.observedSequence') FROM world_frames WHERE session=$session AND sequence=$sequence",
            ("$session", session), ("$sequence", sequence));
        return query.ExecuteScalar() is long observed ? observed : throw new InvalidDataException("Missing original world observation.");
    }
}
