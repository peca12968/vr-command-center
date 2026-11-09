namespace VrCommand.Core;

public record VenuePhaseFence(Guid SessionId, long PhaseSinceSequence);
public record VenuePhaseTarget(Guid SessionId, long PhaseSinceSequence, int[] RoomIds);
public record VenuePhasePlan(VenuePhaseTarget[] Pause, VenuePhaseTarget[] Resume);
public record VenuePhaseApplied(Guid SessionId, long AppliedAtSequence);
public record VenuePhaseReceipt(Guid RequestId, ControlAction Action, VenuePhaseApplied[] Sessions, bool Duplicate);
public record VenueResumeWitness(long PhaseSinceSequence, long SessionSequence, bool MrReady);
public sealed class VenuePhaseChangedException() : InvalidOperationException("The venue phase targets changed; review the current rooms.");
public sealed class VenuePauseNotObservedException(int[] roomIds) : InvalidOperationException("A game source has not confirmed its current pause.")
{
    public int[] RoomIds { get; } = roomIds;
}
public sealed class VenueResumeNotReadyException(int[] roomIds) : InvalidOperationException("A paused MR session is not ready to resume.")
{
    public int[] RoomIds { get; } = roomIds;
}

public sealed partial class SessionManager
{
    private readonly Dictionary<Guid, List<SessionEvent>> venueTransitions = [];

    public VenuePhasePlan ReadVenuePhase(OperatorIdentity actor)
    {
        RequireVenueMaster(actor);
        lock (gate) return new(Targets(ControlAction.Pause).Select(ToTarget).ToArray(),
            Targets(ControlAction.Resume).Select(ToTarget).ToArray());
    }

    public VenuePhaseReceipt ExecuteVenuePhase(ControlAction action, VenuePhaseFence?[]? fences, Guid requestId,
        OperatorIdentity actor, IReadOnlyDictionary<Guid, VenueResumeWitness>? witnesses = null)
    {
        RequireVenueMaster(actor);
        ValidateRequestId(requestId);
        if (action is not (ControlAction.Pause or ControlAction.Resume) || fences is not { Length: >= 1 and <= RoomCount }
            || fences.Any(fence => fence is not { PhaseSinceSequence: > 0 } || fence.SessionId == Guid.Empty)
            || fences.Select(fence => fence!.SessionId).Distinct().Count() != fences.Length)
            throw new ArgumentException("Provide a Pause or Resume with distinct session phase fences.");
        var expected = fences.OrderBy(fence => fence!.SessionId).ToArray();
        lock (gate)
        {
            if (venueTransitions.TryGetValue(requestId, out var existing))
            {
                if (existing[0].Actor != actor || existing[0].Read<ControlCommand>().Action != action
                    || !existing.Select(entry => new VenuePhaseFence(entry.SessionId, entry.Venue!.PhaseSinceSequence)).SequenceEqual(expected))
                    throw new InvalidOperationException("Venue request ID already used with different content.");
                return Receipt(requestId, action, existing, true);
            }
            var targets = Targets(action);
            if (!targets.Select(history => new VenuePhaseFence(history.View.Id, history.PhaseSinceSequence)).SequenceEqual(expected))
                throw new VenuePhaseChangedException();
            if (action == ControlAction.Resume) VerifyVenueResume(targets, witnesses);
            if (targets.Any(history => history.Commands.ContainsKey(requestId)))
                throw new InvalidOperationException("A target already used this command ID.");
            if (eventStore is not IAtomicSessionEventStore store)
                throw new InvalidOperationException("Venue transitions require a transactional session store.");

            var entries = targets.Select(history => SessionEvent.Create(history.View.Id, history.View.Sequence + 1,
                SessionEventKind.ControlApplied, new ControlCommand(requestId, action), actor,
                venue: new(history.PhaseSinceSequence, targets.Length))).ToArray();
            var views = entries.Select((entry, index) => SessionProjection.Apply(targets[index].View, entry)).ToArray();
            store.AppendBatch(entries);
            for (var index = 0; index < targets.Length; index++)
            {
                var history = targets[index];
                RememberCommitted(history, entries[index], views[index], history.Combat, history.Authority);
            }
            venueTransitions.Add(requestId, [.. entries]);
            return Receipt(requestId, action, entries, false);
        }
    }

    private static void RequireVenueMaster(OperatorIdentity actor)
    {
        AccessPolicy.Validate(actor);
        if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Venue phase operations require the master operator.");
    }

    private static void VerifyVenueResume(History[] targets, IReadOnlyDictionary<Guid, VenueResumeWitness>? witnesses)
    {
        var waiting = targets.Where(history => witnesses?.GetValueOrDefault(history.View.Id)?.PhaseSinceSequence != history.PhaseSinceSequence)
            .SelectMany(history => history.View.RoomIds).Order().ToArray();
        if (waiting.Length > 0) throw new VenuePauseNotObservedException(waiting);
        var blocked = targets.Where(history => RequiresMrReadiness(history.View, ControlAction.Resume)
            && (witnesses?.GetValueOrDefault(history.View.Id) is not { MrReady: true } witness || witness.SessionSequence != history.View.Sequence
                || history.View.CombatStream?.Origin != CombatOrigin.GameServer
                || history.View.Players.Any(player => player.Headset != HeadsetKind.Quest3)))
            .SelectMany(history => history.View.RoomIds).Order().ToArray();
        if (blocked.Length > 0) throw new VenueResumeNotReadyException(blocked);
    }

    private static bool IsVenuePhase(History history) => history.Events[(int)history.PhaseSinceSequence - 1].Venue is not null;

    private History[] Targets(ControlAction action) => sessions.Values.Where(history => action == ControlAction.Pause
        ? history.View.State == SessionState.Running
        : history.View.State == SessionState.Paused && IsVenuePhase(history))
        .OrderBy(history => history.View.Id).ToArray();

    private static VenuePhaseTarget ToTarget(History history) => new(history.View.Id, history.PhaseSinceSequence, [.. history.View.RoomIds]);

    private static VenuePhaseReceipt Receipt(Guid requestId, ControlAction action, IEnumerable<SessionEvent> entries, bool duplicate) =>
        new(requestId, action, entries.Select(entry => new VenuePhaseApplied(entry.SessionId, entry.Sequence)).ToArray(), duplicate);

    private void RestoreVenueEvent(SessionEvent[] events, SessionEvent entry, long phaseSince)
    {
        var command = entry.Read<ControlCommand>();
        if (entry.Venue!.PhaseSinceSequence != phaseSince || (command.Action == ControlAction.Resume && events[(int)phaseSince - 1].Venue is null))
            throw new InvalidDataException("Venue transition does not follow its original phase.");
        if (!venueTransitions.TryGetValue(command.CommandId, out var group)) venueTransitions.Add(command.CommandId, group = []);
        group.Add(entry);
    }

    private void ValidateRestoredVenueTransitions()
    {
        foreach (var entries in venueTransitions.Values)
        {
            var first = entries[0];
            var action = first.Read<ControlCommand>().Action;
            if (entries.Count != first.Venue!.TargetCount || entries.Select(entry => entry.SessionId).Distinct().Count() != entries.Count
                || entries.Any(entry => entry.Actor != first.Actor || entry.Venue!.TargetCount != entries.Count || entry.Read<ControlCommand>().Action != action))
                throw new InvalidDataException("Incomplete or inconsistent venue transition batch.");
            entries.Sort((a, b) => a.SessionId.CompareTo(b.SessionId));
        }
    }
}
