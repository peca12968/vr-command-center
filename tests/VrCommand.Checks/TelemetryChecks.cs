using System.Text.Json;
using VrCommand.Core;
using VrCommand.Persistence;
using VrCommand.Simulation;

internal static class TelemetryChecks
{
    internal static void Run(Action<bool, string> check, string directory, Mission mission)
    {
        void Reject<T>(Action action, string message) where T : Exception
        { try { action(); } catch (T) { check(true, message); return; } throw new Exception("Expected " + typeof(T).Name + ": " + message); }
        static StreamCombatRecord[] Batch(TelemetryOutbox queue) => JsonSerializer.Deserialize<StreamCombatRecord[]>(TelemetryOutbox.BatchJson(queue.PendingBatch()), JsonFormat.Options)!;
        var game = new OperatorIdentity("game", OperatorRole.GameServer); var other = new OperatorIdentity("other", OperatorRole.GameServer);
        var master = new OperatorIdentity("master", OperatorRole.Master);
        var data = Path.Combine(directory, "telemetry-db"); var file = Path.Combine(directory, "telemetry.journal");
        var player = Guid.NewGuid(); var enemy = Guid.NewGuid(); Guid id, stream, guardedId; long observed; StreamCombatRecord[] tail;
        var guardedStream = Guid.NewGuid();
        long guardedSequence;
        VenueStreamBatch venueBatch;
        var world = new ArenaWorld([3], []); world.AddPlayer(player, 3, new(0, 1.4f, -3)); world.AddEnemy(enemy, 3, new(0, 0, 3), new(0, 0, 3));
        using (var store = new SqliteSessionEventStore(data))
        {
            var manager = new SessionManager(store); id = manager.Create(SessionMode.Independent, [3], mission).Id;
            manager.Join(id, player, "Alpha", 3, HeadsetKind.Quest3);
            using var queue = TelemetryOutbox.OpenFile(file, id, "Simulation"); stream = queue.StreamId;
            Reject<AccessDeniedException>(() => manager.OpenStream(id, new(stream, CombatOrigin.Simulation), master), "Operator cannot take ownership of a game-server combat stream");
            var opened = manager.OpenStream(id, new(stream, CombatOrigin.Simulation), game);
            check(manager.OpenStream(id, new(stream, CombatOrigin.Simulation), game) == opened && manager.Events(id).Length == 3,
                "Lost stream-open response can be retried without attaching a second stream");
            Reject<InvalidOperationException>(() => manager.OpenStream(id, new(Guid.NewGuid(), CombatOrigin.Simulation), game), "A session cannot attach a competing writer stream");
            Reject<IOException>(() => { using var conflict = TelemetryOutbox.OpenExisting(file); }, "Telemetry file allows only one concurrent writer");
            manager.Execute(id, new(Guid.NewGuid(), ControlAction.Begin)); observed = manager.Get(id).Sequence; world.SetPhase(WorldPhase.Running);
            world.Fire(player, Guid.NewGuid()); world.Tick(); queue.Capture(world, observed);
            check(queue.LastSequence == 3 && queue.Pending!.StreamSequence == 1, "Durable capture selects player combat and AI damage while excluding enemy-shot visuals");
            var first = Batch(queue);
            check(first.All(record => record.Report.Origin == CombatOrigin.Simulation) && first[^1].Report.Kind == CombatKind.PlayerDamaged && first[^1].Report.EnemyId is null,
                "Wire conversion keeps explicit Simulation origin and omits forbidden absent GUID fields");
            manager.Execute(id, new(Guid.NewGuid(), ControlAction.Pause));
            Reject<InvalidOperationException>(() => manager.ReportCombat(id, first[0].Report, game), "Legacy report endpoint cannot bypass a bound ordered stream");
            Reject<AccessDeniedException>(() => manager.ReportStream(id, first[0], other), "Another server identity cannot submit to the bound stream");
            check(manager.ReportStreamBatch(id, first, game).AcceptedSequence == 3 && manager.Statistics(id).Players[0].Health == 80,
                "Reports observed during Running drain successfully after operator Pause");
            check(manager.ReportStreamBatch(id, first, game).Duplicate && manager.Statistics(id).Players[0].AmmoUsed == 1,
                "Lost batch response retry neither doubles ammunition nor AI damage");
            Reject<InvalidOperationException>(() => manager.ReportStream(id, first[0] with { Report = first[0].Report with { ShotId = Guid.NewGuid() } }, game), "Accepted report ID cannot change content on retry");
            Reject<InvalidOperationException>(() => manager.ReportStream(id, first[0] with { StreamSequence = 5, Report = first[0].Report with { ReportId = Guid.NewGuid(), ShotId = Guid.NewGuid() } }, game), "Ordered stream rejects gaps");
            Reject<InvalidOperationException>(() => manager.ReportStream(id, first[0] with { StreamSequence = 4, ObservedSequence = manager.Get(id).Sequence - 3, Report = first[0].Report with { ReportId = Guid.NewGuid(), ShotId = Guid.NewGuid() } }, game),
                "Observed Paused state cannot be presented as running combat");
            Reject<InvalidOperationException>(() => manager.ReportStream(id, first[0] with { StreamSequence = 4, Report = first[0].Report with { Origin = CombatOrigin.GameServer, ReportId = Guid.NewGuid(), ShotId = Guid.NewGuid() } }, game), "Stream cannot switch provenance");
            queue.AcknowledgeThrough(3, first[^1].Report.ReportId);
            for (var tick = 0; tick < 3; tick++) world.Tick(); world.Fire(player, Guid.NewGuid()); queue.Capture(world, observed);
            manager.Leave(id, player); manager.End(id);
            check(manager.Statistics(id).PendingTelemetry && manager.Rooms()[2].SessionId is null,
                "End releases rooms but clearly marks bound combat statistics unsealed");
            Reject<InvalidOperationException>(() => manager.SealStream(id, new(stream, 6), game), "Cannot seal across reports still missing at the server");
            world.SetPhase(WorldPhase.Ended); queue.Finish(world); tail = Batch(queue);
            check(queue.Complete && queue.LastSequence == 6 && queue.AcknowledgedSequence == 3,
                "World completion persists a final boundary independently of network delivery");

            var preview = manager.Create(SessionMode.Independent, [2], mission);
            guardedId = preview.Id;
            var edit = manager.Execute(guardedId, new(Guid.NewGuid(), ControlAction.SetEnvironment, Environment: preview.Environment));
            guardedSequence = edit.Session.Sequence;
            var open = new OpenCombatStream(guardedStream, CombatOrigin.Simulation, ExpectedSequence: preview.Sequence);
            Reject<InvalidOperationException>(() => manager.OpenGuardedStream(guardedId, open, game),
                "An original Preparing session cannot attach from an older reviewed sequence");
            check(manager.Get(guardedId).Sequence == guardedSequence && manager.Get(guardedId).CombatStream is null,
                "Stale attachment neither advances history nor reserves a source");
            var guarded = manager.OpenGuardedStream(guardedId, open with { ExpectedSequence = guardedSequence }, game);
            check(guarded.ExpectedSequence == guardedSequence && manager.Get(guardedId).Sequence == guardedSequence + 1,
                "A guarded open preserves the exact preceding sequence in the accepted source");
            Reject<InvalidOperationException>(() => manager.OpenStream(guardedId, open with { ExpectedSequence = null }, game),
                "Legacy retry cannot change the original guarded request");
            manager.End(guardedId);

            var venueSessions = Enumerable.Range(1, SessionManager.RoomCount)
                .Select(room => manager.Create(SessionMode.Independent, [room], mission)).ToArray();
            venueBatch = new(1, Guid.NewGuid(), SessionMode.Independent, venueSessions.Select(session =>
                new VenueStreamCandidate(session.Id, Guid.NewGuid(), CombatOrigin.Simulation, session.Sequence)).ToArray());
            Reject<AccessDeniedException>(() => manager.OpenVenueStreams(venueBatch, master), "Master cannot attach venue game sources");
            var last = venueSessions[^1];
            var changed = manager.Execute(last.Id, new(Guid.NewGuid(), ControlAction.SetEnvironment, Environment: last.Environment)).Session;
            Reject<InvalidOperationException>(() => manager.OpenVenueStreams(venueBatch, game),
                "A stale fifth room rejects atomic source attachment");
            check(venueSessions.All(session => manager.Get(session.Id) is { CombatStream: null } current
                && current.Sequence == (session.Id == last.Id ? changed.Sequence : session.Sequence)),
                "Stale fifth-room registration leaves all five histories unbound");
            venueBatch.Servers[^1] = venueBatch.Servers[^1] with { ExpectedSequence = changed.Sequence };
            var attached = manager.OpenVenueStreams(venueBatch, game);
            check(attached.Servers.Select(row => row.SessionId).SequenceEqual(venueSessions.Select(session => session.Id))
                && attached.Servers.All(row => row.Stream.VenueLaunchId == venueBatch.LaunchId
                    && manager.Get(row.SessionId).Sequence == row.Stream.ExpectedSequence + 1),
                "One venue transaction attaches all five original sources in room order");
            var firstCandidate = venueBatch.Servers[0];
            Reject<ArgumentException>(() => manager.OpenStream(firstCandidate.SessionId,
                new(firstCandidate.StreamId, firstCandidate.Origin, 1, 1, firstCandidate.ExpectedSequence, venueBatch.LaunchId), game),
                "A single-source request cannot impersonate a venue attachment");
        }
        using (var store = new SqliteSessionEventStore(data)) using (var queue = TelemetryOutbox.OpenExisting(file))
        {
            var manager = new SessionManager(store);
            var guardedBeforeRetry = manager.Get(guardedId);
            check(guardedBeforeRetry.State == SessionState.Ended
                && manager.OpenGuardedStream(guardedId, new(guardedStream, CombatOrigin.Simulation, ExpectedSequence: guardedSequence), game)
                    == guardedBeforeRetry.CombatStream && manager.Get(guardedId).Sequence == guardedBeforeRetry.Sequence,
                "SQLite replay preserves the guarded source and the exact retry after End");
            var recoveredVenue = manager.OpenVenueStreams(venueBatch with { Servers = venueBatch.Servers.Reverse().ToArray() }, game);
            check(recoveredVenue.Servers.Select(row => row.Stream.StreamId).SequenceEqual(venueBatch.Servers.Select(row => row.StreamId))
                && recoveredVenue.Servers.All(row => manager.Get(row.SessionId).Sequence == row.Stream.ExpectedSequence + 1),
                "A reordered venue retry after SQLite restart reuses the original five events");
            var altered = venueBatch.Servers.ToArray();
            altered[0] = altered[0] with { StreamId = Guid.NewGuid() };
            Reject<InvalidOperationException>(() => manager.OpenVenueStreams(venueBatch with { Servers = altered }, game),
                "A retry cannot replace a source in the original venue launch");
            check(queue.Complete && queue.Pending!.StreamSequence == 4 && manager.Get(id).CombatStream!.AcceptedSequence == 3,
                "Independent journal and SQLite restart resume from their durable acknowledged prefix");
            check(manager.ReportStreamBatch(id, tail, game).AcceptedSequence == 6 && manager.Statistics(id).Players[0].Kills == 1,
                "Late ordered reports remain causal after roster departure, End and API restart");
            queue.AcknowledgeThrough(6, tail[^1].Report.ReportId);
            Reject<InvalidOperationException>(() => manager.SealStream(id, new(stream, 5), game), "Final boundary cannot omit an accepted report");
            var sealedView = manager.SealStream(id, new(stream, 6), game);
            var sequence = manager.Get(id).Sequence;
            check(sealedView.Sealed && !manager.Statistics(id).PendingTelemetry && manager.Statistics(id).Players[0].AccuracyPercent == 100,
                "Seal makes complete statistics visible only after every contiguous report arrived");
            check(manager.SealStream(id, new(stream, 6), game).Sealed && manager.Get(id).Sequence == sequence,
                "Lost seal response retries without a second seal event");
            check(manager.ReportStreamBatch(id, tail, game).Duplicate, "Already accepted reports can still be acknowledged after sealing");
            Reject<InvalidOperationException>(() => manager.ReportStream(id, tail[0] with { StreamSequence = 7, Report = tail[0].Report with { ReportId = Guid.NewGuid(), ShotId = Guid.NewGuid() } }, game), "Sealed stream rejects new reports even with an old Running observation");
            queue.MarkSealed();
        }
        using (var queue = TelemetryOutbox.OpenExisting(file)) check(queue.Sealed && queue.Pending is null, "Final local receipt survives process restart");
        var corrupted = Path.Combine(directory, "telemetry-torn.journal"); File.Copy(file, corrupted);
        using (var cut = new FileStream(corrupted, FileMode.Open, FileAccess.Write)) cut.SetLength(cut.Length - 1);
        var length = new FileInfo(corrupted).Length;
        Reject<InvalidDataException>(() => { using var queue = TelemetryOutbox.OpenExisting(corrupted); }, "Torn telemetry tail is rejected instead of silently discarding accepted combat");
        check(new FileInfo(corrupted).Length == length, "Corruption detection leaves the recovery evidence unchanged");
        Reject<InvalidDataException>(() => { using var queue = TelemetryOutbox.OpenFile(file, Guid.NewGuid(), "Simulation"); }, "Journal cannot be rebound to another session");
        var fault = new FaultJournal(); using var fragile = new TelemetryOutbox(fault, Guid.NewGuid(), Guid.NewGuid(), "Simulation");
        var probe = new ArenaWorld([3], []); var who = Guid.NewGuid(); probe.AddPlayer(who, 3, new(0, 1.4f, -3)); probe.SetPhase(WorldPhase.Running); probe.Fire(who, Guid.NewGuid());
        fault.Fail = true;
        Reject<IOException>(() => fragile.Capture(probe, 3), "Disk append failure is surfaced before gameplay telemetry is published");
        check(fragile.LastSequence == 0, "Failed journal write does not advance in-memory report sequence");
        fault.Fail = false; fragile.Capture(probe, 3);
        Reject<InvalidOperationException>(() => fragile.AcknowledgeThrough(1, Guid.NewGuid()), "Receipt must name the exact saved report");
        fault.Fail = true;
        Reject<IOException>(() => fragile.Acknowledge(1, fragile.Pending!.ReportId), "Failed acknowledgment flush retains the pending report");
        check(fragile.AcknowledgedSequence == 0, "Network success alone cannot advance an undurable acknowledgment");
        fault.Fail = false; fragile.Acknowledge(1, fragile.Pending!.ReportId);
        Reject<InvalidOperationException>(() => fragile.Finish(probe), "Running world cannot claim a final journal boundary");
        probe.SetPhase(WorldPhase.Ended); fragile.Finish(probe); fragile.MarkSealed();
        check(fragile.Sealed, "Recovered storage can complete the exact same report without manufacturing another one");
        var interrupted = new InterruptedStore(); var partial = new SessionManager(interrupted);
        var partialSession = partial.Create(SessionMode.Independent, [4], mission); var partialPlayer = Guid.NewGuid();
        partial.Join(partialSession.Id, partialPlayer, "Partial", 4, HeadsetKind.Quest3);
        var partialStream = Guid.NewGuid(); partial.OpenStream(partialSession.Id, new(partialStream, CombatOrigin.Simulation), game);
        partial.Execute(partialSession.Id, new(Guid.NewGuid(), ControlAction.Begin)); var partialObserved = partial.Get(partialSession.Id).Sequence;
        var partialShot = Guid.NewGuid(); var partialEnemy = Guid.NewGuid();
        StreamCombatRecord[] records = [new(partialStream, 1, partialObserved, new(Guid.NewGuid(), CombatKind.ShotFired, CombatOrigin.Simulation, partialPlayer, partialShot)),
            new(partialStream, 2, partialObserved, new(Guid.NewGuid(), CombatKind.ShotHit, CombatOrigin.Simulation, partialPlayer, partialShot, partialEnemy))];
        interrupted.FailAt = interrupted.Calls + 2;
        Reject<IOException>(() => partial.ReportStreamBatch(partialSession.Id, records, game), "Interrupted batch reports its storage failure without claiming atomic completion");
        check(partial.Get(partialSession.Id).CombatStream!.AcceptedSequence == 1 && partial.Statistics(partialSession.Id).Players[0].ShotsHit == 0,
            "Partially committed batch retains exactly its durable prefix");
        interrupted.FailAt = 0;
        check(partial.ReportStreamBatch(partialSession.Id, records, game).AcceptedSequence == 2 && partial.Statistics(partialSession.Id).Players[0].AmmoUsed == 1,
            "Full-batch retry deduplicates its prefix and appends the remaining causal report");
        Reject<InvalidOperationException>(() => partial.SealStream(partialSession.Id, new(partialStream, 2), game), "Running stream cannot be sealed prematurely");
        partial.Leave(partialSession.Id, partialPlayer); var departed = partial.Get(partialSession.Id).Sequence;
        Reject<InvalidOperationException>(() => partial.ReportStream(partialSession.Id, new(partialStream, 3, departed,
            new(Guid.NewGuid(), CombatKind.ShotFired, CombatOrigin.Simulation, partialPlayer, Guid.NewGuid())), game), "Observed roster departure cannot authorize a new player's shot");
        var poisoned = partial.Events(partialSession.Id); poisoned[2] = poisoned[2] with { SchemaVersion = 4 };
        var seeded = new MemorySessionEventStore(); seeded.Seed(partialSession.Id, poisoned);
        Reject<InvalidDataException>(() => new SessionManager(seeded), "Old envelope versions cannot assert new stream ownership metadata");
    }
    private sealed class FaultJournal : ITelemetryJournal
    {
        private readonly List<byte[]> frames = [];
        internal bool Fail;
        public byte[][] Load() => frames.ToArray();
        public void Append(byte[] frame) { if (Fail) throw new IOException("Disk unavailable"); frames.Add(frame.ToArray()); }
        public void Dispose() { }
    }
    private sealed class InterruptedStore : ISessionEventStore
    {
        private readonly MemorySessionEventStore inner = new();
        internal int Calls, FailAt;
        public SessionEvent[][] Load() => inner.Load();
        public void Append(SessionEvent entry) { Calls++; if (Calls == FailAt) throw new IOException("Interrupted batch write"); inner.Append(entry); }
    }
}
