namespace VrCommand.Core;

// Offline test-bench types, not a vendor wire format or a physical-device API.
public enum HardwareSimulationAction { Unspecified, Connect, Disconnect, Dispatch, Receive, Acknowledge, StopAll }
public record HardwareSimulationBinding(Guid DeviceId, Guid SessionId, Guid StreamId, int RoomId, Guid PlayerId, Guid AdmissionId);
public record HardwareSimulationStep(long AtMilliseconds, HardwareSimulationAction Action, Guid? DeviceId = null,
    int? BindingIndex = null, Guid? EventId = null, int? Connection = null, int? Delivery = null);
public record HardwareSimulationInput(int Version, SessionEvent[] Events, HardwareSimulationBinding[] Bindings, HardwareSimulationStep[] Steps);
public record HardwareSimulationSignal(Guid SessionId, Guid StreamId, Guid EventId, long EventSequence, long StreamSequence,
    long ObservedSequence, Guid ReportId, CombatOrigin CombatOrigin, CombatKind Kind, int RoomId, Guid PlayerId, Guid AdmissionId, int Damage);
public record HardwareSimulationDelivery(Guid DeviceId, int Connection, int Delivery, long ExpiresAtMilliseconds, HardwareSimulationSignal Signal);
public record HardwareSimulationReceipt(string Status, HardwareSimulationDelivery Delivery);
public record HardwareSimulationResult(int Step, long AtMilliseconds, string Status, HardwareSimulationDelivery? Received,
    HardwareSimulationReceipt[] Receipts);
public record HardwareSimulationReport(int Version, bool Complete, bool SimulatedHardwareOnly, bool PhysicalDeliveryConfirmed,
    Guid SessionId, Guid StreamId, int InputSteps, HardwareSimulationResult[] Results);

public static class HardwareFeedbackSimulation
{
    public const int MaxEvents = 4096, MaxBindings = 128, MaxSteps = 4096, QueueCapacity = 32;
    public const long DeliveryLifetimeMilliseconds = 2000, MaxTimeMilliseconds = 600000;
    private sealed class Device
    {
        internal HardwareSimulationBinding? Binding;
        internal int Connection;
        internal long LastQueuedSequence;
        internal readonly Queue<HardwareSimulationDelivery> Queue = [];
        internal HardwareSimulationDelivery? InFlight;
    }
    public static HardwareSimulationReport Run(HardwareSimulationInput input)
    {
        ArgumentNullException.ThrowIfNull(input);
        if (input.Version != 1 || input.Events is null || input.Events.Length is < 1 or > MaxEvents
            || input.Bindings is null || input.Bindings.Length is < 1 or > MaxBindings
            || input.Steps is null || input.Steps.Length is < 1 or > MaxSteps)
            throw new ArgumentException("Unsupported or oversized offline hardware simulation input.");
        // Reconstruct with the production admission, stream, combat and seal rules.
        // JsonElement.Clone detaches payload ownership from caller-owned documents.
        var events = input.Events.Select(e => e is null ? throw new ArgumentException("Null event.") : e with { Payload = e.Payload.Clone() }).ToArray();
        var sessionId = events[0].SessionId;
        if (sessionId == Guid.Empty || events.Any(e => e.SessionId != sessionId || e.SchemaVersion is < 6 or > 7))
            throw new ArgumentException("Use one complete admission-aware event history (schema 6 or 7).");
        var store = new MemorySessionEventStore(); store.Seed(sessionId, events);
        var manager = new SessionManager(store); var session = manager.Get(sessionId);
        if (session.State != SessionState.Ended || session.CombatStream is not { Sealed: true } stream || manager.Statistics(sessionId).PendingTelemetry)
            throw new ArgumentException("Offline feedback replay requires an Ended, exactly sealed combat history.");
        var admissions = events.Where(e => e.Kind == SessionEventKind.PlayerJoined)
            .Select(e => manager.Observed(sessionId, e.Sequence, OperatorIdentity.Internal).Players.Single(p => p.Id == e.Read<Player>().Id)).ToArray();
        var bindings = input.Bindings.ToArray(); var steps = input.Steps.ToArray();
        foreach (var binding in bindings)
            if (binding is null || binding.DeviceId == Guid.Empty || binding.SessionId != sessionId || binding.StreamId != stream.StreamId
                || !admissions.Any(p => p.Id == binding.PlayerId && p.AdmissionId == binding.AdmissionId && p.RoomId == binding.RoomId))
                throw new ArgumentException("Device binding must identify an original admission in this exact session, stream and room.");
        var devices = bindings.Select(b => b.DeviceId).Distinct().ToDictionary(id => id, _ => new Device());
        var eventIds = events.Select(e => e.EventId).ToHashSet();
        long clock = 0;
        foreach (var step in steps)
        {
            if (step is null || !Enum.IsDefined(step.Action) || step.Action == HardwareSimulationAction.Unspecified || step.AtMilliseconds < clock || step.AtMilliseconds > MaxTimeMilliseconds
                || (step.Action == HardwareSimulationAction.StopAll ? step.DeviceId is not null : step.DeviceId is null || !devices.ContainsKey(step.DeviceId.Value))
                || (step.Action == HardwareSimulationAction.Connect ? step.BindingIndex is null || step.BindingIndex < 0 || step.BindingIndex >= bindings.Length || bindings[step.BindingIndex.Value].DeviceId != step.DeviceId : step.BindingIndex is not null)
                || (step.Action == HardwareSimulationAction.Dispatch ? step.EventId is null || !eventIds.Contains(step.EventId.Value) : step.EventId is not null)
                || (step.Action == HardwareSimulationAction.Acknowledge ? step.Connection is null or < 1 || step.Delivery is null or < 1 : step.Connection is not null || step.Delivery is not null))
                throw new ArgumentException("Invalid, ambiguous, unbounded or non-monotonic simulation step.");
            clock = step.AtMilliseconds;
        }
        var signals = new Dictionary<Guid, HardwareSimulationSignal>();
        foreach (var entry in events.Where(e => e.Kind == SessionEventKind.StreamCombatRecorded))
        {
            var record = entry.Read<StreamCombatRecord>();
            if (record.Report.Kind is not (CombatKind.ShotFired or CombatKind.PlayerDamaged)) continue;
            // Late accepted telemetry uses its original administrative observation,
            // never the current roster or the time the report reached the API.
            var player = manager.Observed(sessionId, record.ObservedSequence, OperatorIdentity.Internal).Players.Single(p => p.Id == record.Report.PlayerId);
            signals.Add(entry.EventId, new(sessionId, record.StreamId, entry.EventId, entry.Sequence, record.StreamSequence,
                record.ObservedSequence, record.Report.ReportId, record.Report.Origin, record.Report.Kind, player.RoomId, player.Id, player.AdmissionId, record.Report.Damage));
        }
        var results = new List<HardwareSimulationResult>(); var nextDelivery = 0;
        void Cancel(Device device, string reason, List<HardwareSimulationReceipt> receipts)
        {
            if (device.InFlight is { } flight) { receipts.Add(new(reason, flight)); device.InFlight = null; }
            while (device.Queue.TryDequeue(out var pending)) receipts.Add(new(reason, pending));
        }
        void Expire(long now, List<HardwareSimulationReceipt> receipts)
        {
            foreach (var device in devices.Values)
            {
                if (device.InFlight is { } flight && flight.ExpiresAtMilliseconds <= now)
                { receipts.Add(new("TimedOut", flight)); device.InFlight = null; }
                while (device.Queue.TryPeek(out var pending) && pending.ExpiresAtMilliseconds <= now)
                { device.Queue.Dequeue(); receipts.Add(new("Expired", pending)); }
            }
        }
        for (var index = 0; index < steps.Length; index++)
        {
            var step = steps[index]; var receipts = new List<HardwareSimulationReceipt>(); Expire(step.AtMilliseconds, receipts);
            HardwareSimulationDelivery? received = null; string status;
            if (step.Action == HardwareSimulationAction.StopAll)
            {
                foreach (var item in devices.Values) { Cancel(item, "Stopped", receipts); item.Binding = null; }
                status = "Stopped";
            }
            else
            {
                var device = devices[step.DeviceId!.Value];
                switch (step.Action)
                {
                    case HardwareSimulationAction.Connect:
                        Cancel(device, "Rebound", receipts); device.Binding = bindings[step.BindingIndex!.Value]; device.Connection++; status = "Connected"; break;
                    case HardwareSimulationAction.Disconnect:
                        Cancel(device, "Disconnected", receipts); device.Binding = null; status = "Disconnected"; break;
                    case HardwareSimulationAction.Dispatch:
                        if (!signals.TryGetValue(step.EventId!.Value, out var signal)) status = "NotFeedback";
                        else if (device.Binding is not { } binding) status = "Disconnected";
                        else if (binding.PlayerId != signal.PlayerId || binding.AdmissionId != signal.AdmissionId || binding.RoomId != signal.RoomId) status = "BindingMismatch";
                        else if (signal.EventSequence <= device.LastQueuedSequence) status = "AlreadySeen";
                        else if (device.Queue.Count + (device.InFlight is null ? 0 : 1) >= QueueCapacity) status = "QueueFull";
                        else
                        {
                            var delivery = new HardwareSimulationDelivery(binding.DeviceId, device.Connection, ++nextDelivery,
                                step.AtMilliseconds + DeliveryLifetimeMilliseconds, signal);
                            device.Queue.Enqueue(delivery); device.LastQueuedSequence = signal.EventSequence; status = "Queued";
                        }
                        break;
                    case HardwareSimulationAction.Receive:
                        if (device.Binding is null) status = "Disconnected";
                        else if (device.InFlight is not null) status = "AwaitingAcknowledgement";
                        else if (!device.Queue.TryDequeue(out received)) status = "Empty";
                        else { device.InFlight = received; receipts.Add(new("SimulatedReceived", received)); status = "SimulatedReceived"; }
                        break;
                    case HardwareSimulationAction.Acknowledge:
                        if (device.Binding is null || device.InFlight is not { } inflight || inflight.Connection != step.Connection || inflight.Delivery != step.Delivery) status = "IgnoredAcknowledgement";
                        else { receipts.Add(new("SimulatedAcknowledged", inflight)); device.InFlight = null; status = "SimulatedAcknowledged"; }
                        break;
                    default: throw new InvalidOperationException("Unexpected simulation action.");
                }
            }
            results.Add(new(index, step.AtMilliseconds, status, received, receipts.ToArray()));
        }
        // Always close every simulated queue. Cancellation never becomes an ACK.
        var final = new List<HardwareSimulationReceipt>();
        foreach (var item in devices.Values) { Cancel(item, "Finalized", final); item.Binding = null; }
        results.Add(new(steps.Length, clock, "Finalized", null, final.ToArray()));
        return new(1, true, true, false, sessionId, stream.StreamId, steps.Length, results.ToArray());
    }
}
