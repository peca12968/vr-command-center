using System.Security.Cryptography;
using System.Text;
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

    public IndependentSessionSet CreateIndependentSet(Mission mission, OperatorIdentity actor, Guid requestId) =>
        CreateIndependentSet(Enumerable.Repeat(mission, RoomCount).ToArray(), actor, requestId);

    // One immutable mission snapshot for each room, in room number order.
    public IndependentSessionSet CreateIndependentSet(Mission[] roomMissions, OperatorIdentity actor, Guid requestId)
    {
        AccessPolicy.Validate(actor);
        if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Only the master may reserve all five independent rooms.");
        ValidateRequestId(requestId);
        if (roomMissions is not { Length: RoomCount })
            throw new ArgumentException("Assign one saved mission to every room.");
        var missions = roomMissions.ToArray();
        for (var index = 0; index < missions.Length; index++)
            SessionProjection.ValidateCreation(new(SessionMode.Independent, [index + 1], missions[index]));
        var contents = missions.Select(MissionContent).ToArray();
        var distinct = missions.Select((mission, index) => (Mission: mission, Index: index)).GroupBy(row => row.Mission.Id).ToArray();
        if (distinct.Any(group => group.Select(row => contents[row.Index]).Distinct().Skip(1).Any()))
            throw new ArgumentException("A saved mission ID must identify the same content in every room.");
        var plan = distinct.Length > 1 ? PlanDigest(missions) : null;
        lock (gate)
        {
            if (Request(requestId, SessionEventKind.Created, actor) is not null)
            {
                if (!independentSets.TryGetValue(requestId, out var original)
                    || !original.Select(id => MissionContent(Find(id).View.Mission)).SequenceEqual(contents))
                    throw new InvalidOperationException("Request ID already used with different content.");
                return new(original.Select(id => Snapshot(Find(id).View)).ToArray(), true);
            }
            var occupied = Active().SelectMany(session => session.RoomIds).Order().ToArray();
            if (occupied.Length > 0) throw new IndependentRoomsOccupiedException(occupied);
            foreach (var group in distinct)
            {
                var first = group.First();
                MissionLayout.RequireNewStart(first.Mission, SessionMode.Independent, plan is null ? null : first.Index + 1);
            }
            if (eventStore is not IAtomicSessionEventStore store)
                throw new InvalidOperationException("Five independent sessions require a transactional session store.");

            var ids = Enumerable.Range(1, RoomCount).Select(_ => Guid.NewGuid()).ToArray();
            var entries = ids.Select((id, index) => SessionEvent.Create(id, 1, SessionEventKind.Created,
                new SessionCreated(SessionMode.Independent, [index + 1], missions[index], requestId, index == 0 ? plan : null), actor,
                index == 0 ? requestId : null)).ToArray();
            var views = entries.Select(entry => SessionProjection.Apply(null, entry)).ToArray();
            store.AppendBatch(entries);
            for (var index = 0; index < entries.Length; index++)
            {
                RememberCommitted(null, entries[index], views[index], new CombatLedger(), []);
            }
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
            var missions = ordered.Select(row => row.Creation.Mission).ToArray();
            var plan = first.Creation.IndependentSetPlanSha256;
            if (!ordered.Select(row => row.Creation.RoomIds[0]).SequenceEqual(Enumerable.Range(1, RoomCount))
                || ordered.Any(row => row.Entry.Actor != first.Entry.Actor)
                || (plan is null ? missions.Select(MissionContent).Distinct().Skip(1).Any()
                    : plan != PlanDigest(missions)
                      || missions.GroupBy(mission => mission.Id).Any(group => group.Select(MissionContent).Distinct().Skip(1).Any())))
                throw new InvalidDataException("Five-room creation receipt does not match its session histories.");
            independentSets.Add(group.Key, ordered.Select(row => row.Entry.SessionId).ToArray());
        }
    }

    private static string MissionContent(Mission mission) => JsonSerializer.Serialize(mission, JsonFormat.Options);
    private static string PlanDigest(IEnumerable<Mission> missions) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(string.Join('/', missions.Select(mission => mission.Id.ToString("D"))))));
}
