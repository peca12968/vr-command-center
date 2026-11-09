using System.Text.Json.Serialization;

namespace VrCommand.Core;

public record VenuePhaseFence(Guid SessionId, long PhaseSinceSequence, long? SessionSequence = null,
    long? EnvironmentSinceSequence = null, long? EnemiesSinceSequence = null);
public record VenuePhaseTarget(Guid SessionId, long PhaseSinceSequence, int[] RoomIds,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] long? SessionSequence = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] long? EnvironmentSinceSequence = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] long? EnemiesSinceSequence = null);
public record VenuePhasePlan(VenuePhaseTarget[] Pause, VenuePhaseTarget[] Resume, VenuePhaseTarget[] Begin, VenuePhaseTarget[] End,
    VenuePhaseTarget[] Environment, VenuePhaseTarget[] Enemies);
public record VenueClimate(Weather? Weather, TimeOfDay? TimeOfDay, bool? Lightning);
[JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
public record VenueEnemyPolicy(EnemyBehavior? Behavior, bool? AutoAttack);
public record VenuePhaseApplied(Guid SessionId, long AppliedAtSequence);
public record VenuePhaseReceipt(Guid RequestId, ControlAction Action, VenuePhaseApplied[] Sessions, bool Duplicate,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)] bool RequireFullTracking = false);
public record VenueEndBatch(Guid RequestId, DateTimeOffset RecordedAtUtc, VenuePhaseApplied[] Sessions);
public record VenueEndSummary(Guid RequestId, DateTimeOffset RecordedAtUtc, int[] RoomIds, string[] MissionNames, int SessionCount);
public record VenueEndHistory(VenueEndSummary[] Batches, Guid? NextBefore);
public record VenuePhaseWitness(long PhaseSinceSequence, long SessionSequence, bool Ready, int[]? FullyTrackedRooms = null);
public sealed class VenuePhaseChangedException() : InvalidOperationException("The venue phase targets changed; review the current rooms.");
public sealed class VenuePauseNotObservedException(int[] roomIds) : InvalidOperationException("A game source has not confirmed its current pause.")
{
    public int[] RoomIds { get; } = roomIds;
}
public sealed class VenueResumeNotReadyException(int[] roomIds) : InvalidOperationException("A paused MR session is not ready to resume.")
{
    public int[] RoomIds { get; } = roomIds;
}
public sealed class VenueBeginNotReadyException(int[] roomIds) : InvalidOperationException("A preparing session is not ready to begin.")
{
    public int[] RoomIds { get; } = roomIds;
}

public sealed partial class SessionManager
{
    private readonly Dictionary<Guid, List<SessionEvent>> venueTransitions = [];
    private readonly SortedSet<(DateTimeOffset RecordedAtUtc, Guid Id)> venueEnds = [];

    public VenuePhasePlan ReadVenuePhase(OperatorIdentity actor)
    {
        RequireVenueMaster(actor);
        lock (gate) return new(Targets(ControlAction.Pause).Select(history => ToTarget(history)).ToArray(),
            Targets(ControlAction.Resume).Select(history => ToTarget(history)).ToArray(),
            Targets(ControlAction.Begin).Select(history => ToTarget(history, history.View.Sequence)).ToArray(),
            Targets(ControlAction.End).Select(history => ToTarget(history)).ToArray(),
            Targets(ControlAction.SetEnvironment).Select(history => ToTarget(history, environmentSinceSequence: history.EnvironmentSinceSequence)).ToArray(),
            Targets(ControlAction.SetEnemies).Select(history => ToTarget(history, enemiesSinceSequence: history.EnemiesSinceSequence)).ToArray());
    }

    public VenueEndBatch? ReadLatestVenueEnd(OperatorIdentity actor)
    {
        RequireVenueMaster(actor);
        lock (gate) return venueEnds.Count == 0 ? null : ToEndBatch(venueEnds.Max.Id);
    }

    public VenueEndBatch ReadVenueEnd(Guid id, OperatorIdentity actor)
    {
        RequireVenueMaster(actor);
        lock (gate) return ToEndBatch(id);
    }

    public VenueEndHistory ReadVenueEndHistory(Guid? before, int limit, OperatorIdentity actor)
    {
        RequireVenueMaster(actor);
        if (limit is < 1 or > 50) throw new ArgumentException("Venue history page size must be between 1 and 50.");
        lock (gate)
        {
            var ordered = before is { } id
                ? venueEnds.GetViewBetween((DateTimeOffset.MinValue, Guid.Empty), (EndEntries(id)[0].RecordedAtUtc, id)).Reverse().Skip(1)
                : venueEnds.Reverse();
            var page = ordered.Take(limit + 1).ToArray();
            var batches = page.Take(limit).Select(batch =>
            {
                var sessions = venueTransitions[batch.Id].Select(entry => Find(entry.SessionId).View).ToArray();
                return new VenueEndSummary(batch.Id, batch.RecordedAtUtc, sessions.SelectMany(session => session.RoomIds).Order().ToArray(),
                    sessions.OrderBy(session => session.RoomIds[0]).Select(session => session.Mission.Definition.Name).Distinct().ToArray(), sessions.Length);
            }).ToArray();
            return new(batches, page.Length > limit ? batches[^1].RequestId : null);
        }
    }

    private VenueEndBatch ToEndBatch(Guid id)
    {
        var entries = EndEntries(id);
        return new(id, entries[0].RecordedAtUtc, Applied(entries));
    }

    private List<SessionEvent> EndEntries(Guid id)
    {
        if (!venueTransitions.TryGetValue(id, out var entries) || !venueEnds.Contains((entries[0].RecordedAtUtc, id)))
            throw new KeyNotFoundException("No venue End batch with that ID.");
        return entries;
    }

    public VenuePhaseReceipt ExecuteVenuePhase(ControlAction action, VenuePhaseFence?[]? fences, Guid requestId,
        OperatorIdentity actor, IReadOnlyDictionary<Guid, VenuePhaseWitness>? witnesses = null, VenueClimate? climate = null,
        VenueEnemyPolicy? enemyPolicy = null, bool requireFullTracking = false)
    {
        RequireVenueMaster(actor);
        ValidateRequestId(requestId);
        var begin = action == ControlAction.Begin;
        if (requireFullTracking && !begin) throw new ArgumentException("Full venue tracking is only allowed for Begin.");
        var environment = action == ControlAction.SetEnvironment;
        var enemies = action == ControlAction.SetEnemies;
        if (environment ? climate is not { Weather: { } weather, TimeOfDay: { } time, Lightning: not null }
            || !Enum.IsDefined(weather) || !Enum.IsDefined(time) : climate is not null)
            throw new ArgumentException("Provide weather, time of day and lightning for a venue environment change.");
        if (enemies ? enemyPolicy is not { Behavior: { } behavior, AutoAttack: not null } || !Enum.IsDefined(behavior) : enemyPolicy is not null)
            throw new ArgumentException("Provide behavior and automatic attack for a venue enemy policy change.");
        if (action is not (ControlAction.Begin or ControlAction.Pause or ControlAction.Resume or ControlAction.End or ControlAction.SetEnvironment or ControlAction.SetEnemies)
            || fences is not { Length: >= 1 and <= RoomCount }
            || fences.Any(fence => fence is not { PhaseSinceSequence: > 0 } || fence.SessionId == Guid.Empty
                || (begin ? fence.SessionSequence is null || fence.SessionSequence < fence.PhaseSinceSequence : fence.SessionSequence is not null)
                || (environment ? fence.EnvironmentSinceSequence is not > 0 : fence.EnvironmentSinceSequence is not null)
                || (enemies ? fence.EnemiesSinceSequence is not > 0 : fence.EnemiesSinceSequence is not null))
            || fences.Select(fence => fence!.SessionId).Distinct().Count() != fences.Length)
            throw new ArgumentException("Provide distinct phase fences and the revision required by the action.");
        var expected = fences.OrderBy(fence => fence!.SessionId).ToArray();
        lock (gate)
        {
            if (venueTransitions.TryGetValue(requestId, out var existing))
            {
                var original = existing[0].Read<ControlCommand>();
                if (existing[0].Actor != actor || original.Action != action || existing[0].Venue!.RequireFullTracking != requireFullTracking
                    || ClimateOf(original) != climate || EnemyPolicyOf(original) != enemyPolicy
                    || !existing.Select(entry => new VenuePhaseFence(entry.SessionId, entry.Venue!.PhaseSinceSequence,
                        begin ? entry.Sequence - 1 : null, entry.Venue.EnvironmentSinceSequence, entry.Venue.EnemiesSinceSequence)).SequenceEqual(expected))
                    throw new InvalidOperationException("Venue request ID already used with different content.");
                return Receipt(requestId, action, existing, true);
            }
            var targets = Targets(action);
            if (!targets.Select(history => new VenuePhaseFence(history.View.Id, history.PhaseSinceSequence,
                begin ? history.View.Sequence : null, environment ? history.EnvironmentSinceSequence : null,
                enemies ? history.EnemiesSinceSequence : null)).SequenceEqual(expected))
                throw new VenuePhaseChangedException();
            if (begin) VerifyVenueBegin(targets, witnesses, requireFullTracking);
            if (action == ControlAction.Resume) VerifyVenueResume(targets, witnesses);
            if (targets.Any(history => history.Commands.ContainsKey(requestId)))
                throw new InvalidOperationException("A target already used this command ID.");
            if (eventStore is not IAtomicSessionEventStore store)
                throw new InvalidOperationException("Venue transitions require a transactional session store.");

            var entries = targets.Select(history =>
            {
                var settings = climate is null ? null : new EnvironmentSettings(history.View.Environment.Mode,
                    climate.Weather!.Value, climate.TimeOfDay!.Value, climate.Lightning!.Value);
                var enemySettings = enemyPolicy is null ? null : new EnemySettings(history.View.Enemies.Count,
                    enemyPolicy.Behavior!.Value, enemyPolicy.AutoAttack!.Value);
                var command = new ControlCommand(requestId, action, settings, enemySettings, ExpectedSequence: begin ? history.View.Sequence : null);
                return SessionEvent.Create(history.View.Id, history.View.Sequence + 1, SessionEventKind.ControlApplied, command, actor,
                    venue: new(history.PhaseSinceSequence, targets.Length, environment ? history.EnvironmentSinceSequence : null,
                        enemies ? history.EnemiesSinceSequence : null, requireFullTracking));
            }).ToArray();
            var views = entries.Select((entry, index) => SessionProjection.Apply(targets[index].View, entry)).ToArray();
            store.AppendBatch(entries);
            for (var index = 0; index < targets.Length; index++)
            {
                var history = targets[index];
                RememberCommitted(history, entries[index], views[index], history.Combat, history.Authority);
            }
            venueTransitions.Add(requestId, [.. entries]);
            if (action == ControlAction.End) venueEnds.Add((entries[0].RecordedAtUtc, requestId));
            return Receipt(requestId, action, entries, false);
        }
    }

    private static void RequireVenueMaster(OperatorIdentity actor)
    {
        AccessPolicy.Validate(actor);
        if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Venue phase operations require the master operator.");
    }

    private static void VerifyVenueBegin(History[] targets, IReadOnlyDictionary<Guid, VenuePhaseWitness>? witnesses, bool requireFullTracking)
    {
        var waiting = targets.Where(history => history.View.Players.Length == 0
            || witnesses?.GetValueOrDefault(history.View.Id) is not { Ready: true } witness
            || witness.PhaseSinceSequence != history.PhaseSinceSequence || witness.SessionSequence != history.View.Sequence
            || (RequiresMrReadiness(history.View, ControlAction.Begin) && !HasMrSource(history.View)))
            .SelectMany(history => history.View.RoomIds).ToHashSet();
        if (requireFullTracking)
        {
            var fullyTracked = targets.SelectMany(history => history.View.RoomIds.Where(room =>
                history.View.Players.Count(player => player.RoomId == room) == PlayersPerRoom
                && witnesses?.GetValueOrDefault(history.View.Id)?.FullyTrackedRooms?.Contains(room) == true));
            waiting.UnionWith(Enumerable.Range(1, RoomCount).Except(fullyTracked));
        }
        if (waiting.Count > 0) throw new VenueBeginNotReadyException(waiting.Order().ToArray());
    }

    private static void VerifyVenueResume(History[] targets, IReadOnlyDictionary<Guid, VenuePhaseWitness>? witnesses)
    {
        var waiting = targets.Where(history => witnesses?.GetValueOrDefault(history.View.Id)?.PhaseSinceSequence != history.PhaseSinceSequence)
            .SelectMany(history => history.View.RoomIds).Order().ToArray();
        if (waiting.Length > 0) throw new VenuePauseNotObservedException(waiting);
        var blocked = targets.Where(history => RequiresMrReadiness(history.View, ControlAction.Resume)
            && (witnesses?.GetValueOrDefault(history.View.Id) is not { Ready: true } witness || witness.SessionSequence != history.View.Sequence
                || !HasMrSource(history.View)))
            .SelectMany(history => history.View.RoomIds).Order().ToArray();
        if (blocked.Length > 0) throw new VenueResumeNotReadyException(blocked);
    }

    private static bool HasMrSource(SessionView session) => session.CombatStream?.Origin == CombatOrigin.GameServer
        && session.Players.All(player => player.Headset == HeadsetKind.Quest3);

    private static bool IsVenuePhase(History history) => history.Events[(int)history.PhaseSinceSequence - 1].Venue is not null;

    private History[] Targets(ControlAction action) => sessions.Values.Where(history => action switch
        {
            ControlAction.Begin => history.View.State == SessionState.Preparing,
            ControlAction.Pause or ControlAction.SetEnvironment or ControlAction.SetEnemies => history.View.State == SessionState.Running,
            ControlAction.Resume => history.View.State == SessionState.Paused && IsVenuePhase(history),
            ControlAction.End => history.View.State != SessionState.Ended,
            _ => false
        })
        .OrderBy(history => history.View.Id).ToArray();

    private static VenuePhaseTarget ToTarget(History history, long? sessionSequence = null, long? environmentSinceSequence = null,
        long? enemiesSinceSequence = null) =>
        new(history.View.Id, history.PhaseSinceSequence, [.. history.View.RoomIds], sessionSequence, environmentSinceSequence, enemiesSinceSequence);

    private static VenueClimate? ClimateOf(ControlCommand command) => command.Environment is { } settings
        ? new(settings.Weather, settings.TimeOfDay, settings.Lightning) : null;

    private static VenueEnemyPolicy? EnemyPolicyOf(ControlCommand command) => command.Enemies is { } settings
        ? new(settings.Behavior, settings.AutoAttack) : null;

    private static VenuePhaseReceipt Receipt(Guid requestId, ControlAction action, IReadOnlyList<SessionEvent> entries, bool duplicate) =>
        new(requestId, action, Applied(entries), duplicate, entries[0].Venue!.RequireFullTracking);

    private static VenuePhaseApplied[] Applied(IEnumerable<SessionEvent> entries) =>
        entries.Select(entry => new VenuePhaseApplied(entry.SessionId, entry.Sequence)).ToArray();

    private void RestoreVenueEvent(SessionEvent[] events, SessionEvent entry, long phaseSince, long environmentSince, long enemiesSince, ControlCommand command)
    {
        if (entry.Venue!.PhaseSinceSequence != phaseSince
            || (command.Action == ControlAction.SetEnvironment && entry.Venue.EnvironmentSinceSequence != environmentSince)
            || (command.Action == ControlAction.SetEnemies && entry.Venue.EnemiesSinceSequence != enemiesSince)
            || (command.Action == ControlAction.Resume && events[(int)phaseSince - 1].Venue is null))
            throw new InvalidDataException("Venue transition does not follow its original phase.");
        if (!venueTransitions.TryGetValue(command.CommandId, out var group)) venueTransitions.Add(command.CommandId, group = []);
        group.Add(entry);
    }

    private void ValidateRestoredVenueTransitions()
    {
        foreach (var (id, entries) in venueTransitions)
        {
            var first = entries[0];
            var command = first.Read<ControlCommand>();
            var action = command.Action;
            var climate = ClimateOf(command);
            var enemyPolicy = EnemyPolicyOf(command);
            if (entries.Count != first.Venue!.TargetCount || entries.Select(entry => entry.SessionId).Distinct().Count() != entries.Count
                || (first.Venue.RequireFullTracking && !entries.SelectMany(entry => Find(entry.SessionId).View.RoomIds).Order()
                    .SequenceEqual(Enumerable.Range(1, RoomCount)))
                || entries.Any(entry =>
                {
                    var other = entry.Read<ControlCommand>();
                    return entry.Actor != first.Actor || entry.Venue!.TargetCount != entries.Count || other.Action != action
                        || entry.Venue.RequireFullTracking != first.Venue.RequireFullTracking
                        || ClimateOf(other) != climate || EnemyPolicyOf(other) != enemyPolicy;
                }))
                throw new InvalidDataException("Incomplete or inconsistent venue transition batch.");
            entries.Sort((a, b) => a.SessionId.CompareTo(b.SessionId));
            if (action == ControlAction.End) venueEnds.Add((entries[0].RecordedAtUtc, id));
        }
    }
}
