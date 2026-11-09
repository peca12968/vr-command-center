using System.Text.Json;

namespace VrCommand.Core;

public record IndependentSessionSet(SessionView[] Sessions, bool Duplicate);
public sealed class IndependentRoomsOccupiedException(int[] roomIds) : InvalidOperationException("Five independent sessions require all rooms to be free.")
{
    public int[] RoomIds { get; } = roomIds;
}

public sealed partial class SessionManager
{
    private readonly Dictionary<Guid, Guid[]> independentSets = [];

    public IndependentSessionSet CreateIndependentSet(Mission mission, OperatorIdentity actor, Guid requestId)
    {
        AccessPolicy.Validate(actor);
        if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Only the master may reserve all five independent rooms.");
        ValidateRequestId(requestId);
        SessionProjection.ValidateCreation(new(SessionMode.Independent, [1], mission));
        lock (gate)
        {
            if (Request(requestId, SessionEventKind.Created, actor) is { } previous)
            {
                var creation = previous.Read<SessionCreated>();
                if (!independentSets.TryGetValue(requestId, out var original) || MissionContent(creation.Mission) != MissionContent(mission))
                    throw new InvalidOperationException("Request ID already used with different content.");
                return new(original.Select(id => Snapshot(Find(id).View)).ToArray(), true);
            }
            var occupied = Active().SelectMany(session => session.RoomIds).Order().ToArray();
            if (occupied.Length > 0) throw new IndependentRoomsOccupiedException(occupied);
            MissionLayout.RequireNewStart(mission.Definition, SessionMode.Independent);
            if (eventStore is not IAtomicSessionEventStore store)
                throw new InvalidOperationException("Five independent sessions require a transactional session store.");

            var ids = Enumerable.Range(1, RoomCount).Select(_ => Guid.NewGuid()).ToArray();
            var entries = ids.Select((id, index) => SessionEvent.Create(id, 1, SessionEventKind.Created,
                new SessionCreated(SessionMode.Independent, [index + 1], mission, requestId), actor,
                index == 0 ? requestId : null)).ToArray();
            var views = entries.Select(entry => SessionProjection.Apply(null, entry)).ToArray();
            store.AppendBatch(entries);
            for (var index = 0; index < entries.Length; index++)
            {
                var view = views[index];
                sessions.Add(view.Id, new(view, [entries[index]], [], new CombatLedger(), [view], view.Sequence));
            }
            requests.Add(requestId, entries[0]);
            independentSets.Add(requestId, ids);
            return new(views.Select(Snapshot).ToArray(), false);
        }
    }

    private void RestoreIndependentSets()
    {
        var groups = sessions.Values.Select(history => history.Events[0])
            .Where(entry => entry.Payload.TryGetProperty("independentSetId", out var id) && id.ValueKind != JsonValueKind.Null)
            .Select(entry => (Entry: entry, Creation: entry.Read<SessionCreated>()))
            .GroupBy(row => row.Creation.IndependentSetId!.Value);
        foreach (var group in groups)
        {
            var ordered = group.OrderBy(row => row.Creation.RoomIds[0]).ToArray();
            var first = ordered[0];
            var mission = MissionContent(first.Creation.Mission);
            if (!ordered.Select(row => row.Creation.RoomIds[0]).SequenceEqual(Enumerable.Range(1, RoomCount))
                || ordered.Any(row => row.Entry.Actor != first.Entry.Actor || MissionContent(row.Creation.Mission) != mission))
                throw new InvalidDataException("Five-room creation receipt does not match its session histories.");
            independentSets.Add(group.Key, ordered.Select(row => row.Entry.SessionId).ToArray());
        }
    }

    private static string MissionContent(Mission mission) => JsonSerializer.Serialize(mission, JsonFormat.Options);
}
