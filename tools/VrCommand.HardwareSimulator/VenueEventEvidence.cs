using System.Text.Json;
using VrCommand.Core;

internal static partial class LiveHardwareGateway
{
    private sealed class VenueEventEvidence
    {
        private const int MaxSessionEventsBytes = 32 * 1024 * 1024;
        private readonly record struct History(SessionEvent[] Events, long[] RunningSince);
        private readonly Dictionary<Guid, History> histories = new();
        private readonly SessionManager manager;
        internal int SignalsVerified { get; private set; }

        internal VenueEventEvidence(string directory, VenueBindingManifest manifest)
        {
            var store = new MemorySessionEventStore();
            var groups = manifest.Rooms.GroupBy(room => room.SessionId).ToArray();
            foreach (var group in groups)
            {
                var path = Path.Combine(directory, group.Key.ToString("D") + ".json");
                var events = JsonSerializer.Deserialize<SessionEvent[]>(ReadReportBytes(path, MaxSessionEventsBytes), HeartbeatWire);
                if (events is not { Length: > 0 } || events.Any(entry => entry is null || entry.SchemaVersion < 6 || entry.SessionId != group.Key))
                    throw new InvalidDataException("Provide the complete admission-aware events for every original session.");
                store.Seed(group.Key, events);
                long running = 0;
                var runningSince = new long[events.Length];
                for (var index = 0; index < events.Length; index++)
                {
                    var entry = events[index];
                    if (entry.Kind == SessionEventKind.ControlApplied)
                        running = entry.Read<ControlCommand>().Action switch
                        {
                            ControlAction.Begin or ControlAction.Resume => entry.Sequence,
                            ControlAction.Pause or ControlAction.End => 0,
                            _ => running
                        };
                    runningSince[index] = running;
                }
                histories.Add(group.Key, new(events, runningSince));
            }

            // Rebuild the whole batch so venue commands and independent-set creation retain their original atomic boundaries.
            manager = new SessionManager(store);
            foreach (var group in groups)
            {
                var original = manager.Get(group.Key);
                if (original.Mode != manifest.Mode || !original.RoomIds.Order().SequenceEqual(group.Select(room => room.RoomId))
                    || original.State != SessionState.Ended || original.CombatStream is not { Sealed: true }
                    || manager.Statistics(group.Key).PendingTelemetry)
                    throw new InvalidDataException("Source events do not reconstruct the original sealed venue.");
            }
        }

        internal void VerifyBindings(VenueBindingRoom room, Configuration config)
        {
            var original = manager.Observed(room.SessionId, room.SessionSequence, OperatorIdentity.Internal);
            if (original.State == SessionState.Ended || config.Bindings.Any(binding => !original.Players.Any(player =>
                player.Id == binding.PlayerId && player.AdmissionId == binding.AdmissionId && player.RoomId == room.RoomId && player.Seat == binding.Seat)))
                throw new InvalidDataException("The equipped seats differ from the original binding revision.");
        }

        internal void VerifySignal(Guid sessionId, int roomId, Guid streamId, long runningSince, RoomHardwareSignal signal)
        {
            var history = histories[sessionId];
            if (signal.EventSequence < 1 || signal.EventSequence > history.Events.Length)
                throw new InvalidDataException("A hardware signal is outside the original event history.");
            var index = (int)signal.EventSequence - 1;
            var entry = history.Events[index];
            if (entry.Kind != SessionEventKind.StreamCombatRecorded || entry.EventId != signal.EventId
                || entry.RecordedAtUtc != signal.AcceptedAtUtc || history.RunningSince[index] != runningSince)
                throw new InvalidDataException("A hardware signal differs from the original accepted event or running phase.");
            var record = entry.Read<StreamCombatRecord>();
            if (record.StreamId != streamId || record.StreamSequence != signal.StreamSequence || record.ObservedSequence != signal.ObservedSequence
                || record.Report.ReportId != signal.ReportId || record.Report.Kind != signal.Kind || record.Report.Damage != signal.Damage
                || record.Report.PlayerId != signal.PlayerId)
                throw new InvalidDataException("A hardware signal differs from the original combat report.");
            var observed = manager.Observed(sessionId, signal.ObservedSequence, OperatorIdentity.Internal);
            if (observed.State != SessionState.Running || !observed.Players.Any(player => player.Id == signal.PlayerId
                    && player.AdmissionId == signal.AdmissionId && player.RoomId == roomId && player.Seat == signal.Seat))
                throw new InvalidDataException("The hardware signal does not belong to its original admission and room.");
            SignalsVerified++;
        }
    }
}
