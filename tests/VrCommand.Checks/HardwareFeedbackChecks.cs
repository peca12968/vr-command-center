using VrCommand.Core;

internal static class HardwareFeedbackChecks
{
    internal static void Run(Action<bool, string> check, Mission mission)
    {
        var store = new MemorySessionEventStore(); var manager = new SessionManager(store);
        var master = new OperatorIdentity("hardware-fixture-master", OperatorRole.Master);
        var server = new OperatorIdentity("hardware-fixture-server", OperatorRole.GameServer);
        var session = manager.Create(SessionMode.Linked, [1, 2, 3, 4, 5], mission, master);
        var alpha = Guid.NewGuid(); var bravo = Guid.NewGuid(); var device = Guid.NewGuid(); var otherDevice = Guid.NewGuid();
        manager.Join(session.Id, alpha, "Alpha old", 1, HeadsetKind.Quest3, master);
        var old = manager.Get(session.Id).Players.Single(); manager.Leave(session.Id, alpha, master, expectedAdmissionId: old.AdmissionId);
        manager.Join(session.Id, alpha, "Alpha current", 2, HeadsetKind.Quest3, master); manager.Join(session.Id, bravo, "Bravo", 3, HeadsetKind.Quest3, master);
        var current = manager.Get(session.Id).Players.Single(p => p.Id == alpha); var b = manager.Get(session.Id).Players.Single(p => p.Id == bravo);
        var stream = Guid.NewGuid(); manager.OpenStream(session.Id, new(stream, CombatOrigin.Simulation), server);
        manager.Execute(session.Id, new(Guid.NewGuid(), ControlAction.Begin), master); var observed = manager.Get(session.Id).Sequence; long sequence = 0;
        var firstShot = Guid.NewGuid();
        void Report(CombatReport report) => manager.ReportStream(session.Id, new(stream, ++sequence, observed, report), server);
        Report(new(Guid.NewGuid(), CombatKind.ShotFired, CombatOrigin.Simulation, alpha, firstShot));
        Report(new(Guid.NewGuid(), CombatKind.ShotHit, CombatOrigin.Simulation, alpha, firstShot, Guid.NewGuid()));
        Report(new(Guid.NewGuid(), CombatKind.PlayerDamaged, CombatOrigin.Simulation, alpha, Damage: 20));
        Report(new(Guid.NewGuid(), CombatKind.ShotFired, CombatOrigin.Simulation, bravo, Guid.NewGuid()));
        for (var i = 0; i < 35; i++) Report(new(Guid.NewGuid(), CombatKind.ShotFired, CombatOrigin.Simulation, alpha, Guid.NewGuid()));
        manager.Leave(session.Id, alpha, master, expectedAdmissionId: current.AdmissionId);
        manager.Execute(session.Id, new(Guid.NewGuid(), ControlAction.End), master);
        Report(new(Guid.NewGuid(), CombatKind.ShotFired, CombatOrigin.Simulation, alpha, Guid.NewGuid()));
        manager.SealStream(session.Id, new(stream, sequence), server);
        var events = store.Load().Single(); var reports = events.Where(e => e.Kind == SessionEventKind.StreamCombatRecorded).ToArray();
        HardwareSimulationBinding Binding(Guid id, Player player) => new(id, session.Id, stream, player.RoomId, player.Id, player.AdmissionId);
        var bindings = new[] { Binding(device, current), Binding(device, old), Binding(otherDevice, b) };
        HardwareSimulationStep Connect(int binding = 0, long at = 0) => new(at, HardwareSimulationAction.Connect, bindings[binding].DeviceId, binding);
        HardwareSimulationStep Send(int report = 0, long at = 0, Guid? target = null) => new(at, HardwareSimulationAction.Dispatch, target ?? device, EventId: reports[report].EventId);
        HardwareSimulationStep Receive(long at = 0, Guid? target = null) => new(at, HardwareSimulationAction.Receive, target ?? device);
        HardwareSimulationStep Ack(int connection = 1, int delivery = 1, long at = 0, Guid? target = null) => new(at, HardwareSimulationAction.Acknowledge, target ?? device, Connection: connection, Delivery: delivery);
        HardwareSimulationInput Input(params HardwareSimulationStep[] steps) => new(1, events, bindings, steps);
        HardwareSimulationReport Run(params HardwareSimulationStep[] steps) => HardwareFeedbackSimulation.Run(Input(steps));
        void Reject(Action action, string message)
        { try { action(); } catch (Exception ex) when (ex is ArgumentException or InvalidDataException or InvalidOperationException) { check(true, message); return; } throw new Exception("Expected rejection: " + message); }
        var normal = Run(Connect(), Send(), Receive(), Ack()); var signal = normal.Results[2].Received!.Signal;
        check(normal.Complete && normal.SimulatedHardwareOnly && !normal.PhysicalDeliveryConfirmed && normal.Results[3].Status == "SimulatedAcknowledged",
            "Hardware test bench completes only simulated receipt/ack and never confirms physical delivery");
        check(signal.SessionId == session.Id && signal.StreamId == stream && signal.EventId == reports[0].EventId && signal.StreamSequence == 1
            && signal.ReportId == reports[0].Read<StreamCombatRecord>().Report.ReportId && signal.AdmissionId == current.AdmissionId && signal.RoomId == 2,
            "Simulated feedback retains the exact accepted event, stream, room and original admission witness");
        check(Run(Connect(1), Send()).Results[1].Status == "BindingMismatch", "Reusing a player ID cannot route feedback to an obsolete admission in another room");
        var late = Run(Connect(), Send(reports.Length - 1), Receive());
        check(late.Results[2].Received!.Signal.AdmissionId == current.AdmissionId && late.Results[2].Received!.Signal.ObservedSequence == observed,
            "Late telemetry after leave and End uses the original Running observation, not the final empty roster");
        check(Run(Connect(), Send(3)).Results[1].Status == "BindingMismatch", "A device cannot consume another room's player report");
        check(Run(Connect(), Send(1)).Results[1].Status == "NotFeedback", "Hit accounting is not silently invented as an unsupported physical effect");
        check(Run(Connect(), Send(2), Receive()).Results[2].Received!.Signal is { Kind: CombatKind.PlayerDamaged, Damage: 20 }, "Damage feedback preserves accepted damage without deriving actuator strength");
        var duplicate = Run(Connect(), Send(), Send(), Receive(), Ack(), Send());
        check(duplicate.Results[2].Status == "AlreadySeen" && duplicate.Results[5].Status == "AlreadySeen", "Duplicate feedback is not re-enqueued before or after acknowledgement");
        check(Run(Connect(), Send(2), Send()).Results[2].Status == "AlreadySeen", "A consumed source cursor cannot move backwards to an older accepted event");
        check(Run(Send(), Receive()).Results[0].Status == "Disconnected", "Disconnected simulated devices cannot receive feedback");
        check(Run(Connect(), Send(), Receive(), Receive(), Ack(2), Ack()).Results[3].Status == "AwaitingAcknowledgement", "Only one simulated delivery may be in flight per device");
        check(Run(Connect(), Send(), Receive(), Ack(2), Ack(delivery: 2), Ack()).Results[3..6].Select(r => r.Status)
            .SequenceEqual(new[] { "IgnoredAcknowledgement", "IgnoredAcknowledgement", "SimulatedAcknowledged" }), "Wrong connection and delivery acknowledgements leave the original flight intact");
        var rebound = Run(Connect(), Send(), Receive(), Connect(1), Ack(), Send());
        check(rebound.Results[3].Receipts.Single().Status == "Rebound" && rebound.Results[4].Status == "IgnoredAcknowledgement" && rebound.Results[5].Status == "BindingMismatch",
            "Rebinding cancels the prior connection and rejects its late acknowledgement and obsolete routing");
        var reconnect = Run(Connect(), Send(), new(0, HardwareSimulationAction.Disconnect, device), Connect(), Send());
        check(reconnect.Results[2].Receipts.Single().Status == "Disconnected" && reconnect.Results[4].Status == "AlreadySeen", "Reconnect never automatically replays cancelled effects or clears the source cursor");
        var expired = Run(Connect(), Send(), Receive(2000));
        check(expired.Results[2].Status == "Empty" && expired.Results[2].Receipts.Single().Status == "Expired", "A queued feedback item expires at the exact virtual deadline");
        var timed = Run(Connect(), Send(), Receive(), Ack(at: 2000));
        check(timed.Results[3].Status == "IgnoredAcknowledgement" && timed.Results[3].Receipts.Single().Status == "TimedOut", "An acknowledgement at the deadline cannot revive an expired in-flight item");
        check(Run(Connect(), Send(), Receive(), Ack(at: 1999)).Results[3].Status == "SimulatedAcknowledged", "Virtual deadline acceptance remains strictly before expiry");
        var crossDevice = Run(Connect(), Connect(2), Send(), Send(3, target: otherDevice), Receive(), Receive(target: otherDevice), Ack(delivery: 2), Ack(delivery: 2, target: otherDevice));
        check(crossDevice.Results[6].Status == "IgnoredAcknowledgement" && crossDevice.Results[7].Status == "SimulatedAcknowledged", "A device cannot acknowledge another device's delivery even with the same connection number");
        var queueSteps = new List<HardwareSimulationStep> { Connect() }; queueSteps.AddRange(new[] { 0, 2 }.Concat(Enumerable.Range(4, 35)).Select(i => Send(i)));
        var full = Run(queueSteps.ToArray());
        check(full.Results.Count(r => r.Status == "Queued") == 32 && full.Results.Count(r => r.Status == "QueueFull") == 5
            && full.Results[^1].Receipts.Length == 32 && full.Results[^1].Receipts.All(r => r.Status == "Finalized"), "Queue capacity includes complete pending items and finalization cancels every unacknowledged item");
        var inflightSteps = new List<HardwareSimulationStep> { Connect(), Send(), Receive() }; inflightSteps.AddRange(new[] { 2 }.Concat(Enumerable.Range(4, 35)).Select(i => Send(i)));
        var inflightFull = Run(inflightSteps.ToArray());
        check(inflightFull.Results.Count(r => r.Status == "Queued") == 32 && inflightFull.Results.Count(r => r.Status == "QueueFull") == 5, "Queue capacity counts the in-flight item as well as unsent items");
        var stopped = Run(Connect(), Send(), new(0, HardwareSimulationAction.StopAll), Receive());
        check(stopped.Results[2].Receipts.Single().Status == "Stopped" && stopped.Results[3].Status == "Disconnected", "StopAll closes simulated queues without manufacturing an acknowledgement or a physical stop guarantee");
        Reject(() => HardwareFeedbackSimulation.Run(Input(Connect()) with { Bindings = [bindings[0] with { StreamId = Guid.NewGuid() }] }), "Unknown stream cannot be substituted into a hardware binding");
        Reject(() => HardwareFeedbackSimulation.Run(Input(Connect()) with { Bindings = [bindings[0] with { AdmissionId = Guid.NewGuid() }] }), "A never-admitted player instance cannot bind a device");
        Reject(() => HardwareFeedbackSimulation.Run(Input(Connect()) with { Events = events[..^1] }), "Unsealed histories cannot be called complete offline hardware recordings");
        Reject(() => HardwareFeedbackSimulation.Run(Input(Connect()) with { Events = [.. events, events[^1]] }), "Duplicate source events are rejected by production history reconstruction");
        Reject(() => Run(Connect(at: 2), Receive(at: 1)), "Simulation clocks may not move backwards");
        Reject(() => Run(Connect(), Receive(at: HardwareFeedbackSimulation.MaxTimeMilliseconds + 1)), "The offline virtual timeline is bounded");
        Reject(() => Run(Connect() with { EventId = reports[0].EventId }), "Ambiguous step fields are rejected before running the simulation");
        Reject(() => Run(Connect(), Send() with { EventId = Guid.NewGuid() }), "A fabricated event ID cannot enter the simulated device pipeline");
        Reject(() => HardwareFeedbackSimulation.Run(Input(Connect()) with { Steps = Enumerable.Repeat(Connect(), HardwareFeedbackSimulation.MaxSteps + 1).ToArray() }), "Offline simulation action count is bounded");
        Reject(() => HardwareFeedbackSimulation.Run(Input(Connect()) with { Events = Enumerable.Repeat(events[0], HardwareFeedbackSimulation.MaxEvents + 1).ToArray() }), "Oversized source history is rejected before projection");
        Reject(() => HardwareFeedbackSimulation.Run(Input(Connect()) with { Bindings = Enumerable.Repeat(bindings[0], HardwareFeedbackSimulation.MaxBindings + 1).ToArray() }), "Offline device binding count is bounded");
        Reject(() => Run(Connect() with { Action = HardwareSimulationAction.Unspecified }), "A missing or unspecified simulation action is never interpreted as a connect");
        var again = Run(Connect(), Send(), Receive(), Ack());
        check(System.Text.Json.JsonSerializer.Serialize(normal, JsonFormat.Options) == System.Text.Json.JsonSerializer.Serialize(again, JsonFormat.Options), "Identical accepted history and virtual actions produce deterministic simulated feedback");
    }
}
