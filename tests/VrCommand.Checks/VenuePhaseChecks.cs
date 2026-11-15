using Microsoft.Data.Sqlite;
using VrCommand.Core;
using VrCommand.Persistence;

internal static class VenuePhaseChecks
{
    internal static void Run(Action<bool, string> check, string directory, Mission mission)
    {
        void Reject<T>(Action action, string message) where T : Exception
        {
            try { action(); }
            catch (T) { check(true, message); return; }
            throw new Exception($"Expected {typeof(T).Name}: {message}");
        }
        static VenuePhaseFence[] Fences(VenuePhaseTarget[] targets) => targets.Select(target => new VenuePhaseFence(target.SessionId, target.PhaseSinceSequence, target.SessionSequence)).ToArray();
        var master = new OperatorIdentity("venue-master", OperatorRole.Master);
        var room2 = new OperatorIdentity("venue-room-2", OperatorRole.RoomController, 2);
        var data = Path.Combine(directory, "venue-phase");
        var pauseKey = Guid.NewGuid();
        VenuePhaseFence[] original;
        VenuePhaseApplied[] applied;
        Guid[] ids;
        using (var store = new SqliteSessionEventStore(data))
        {
            var manager = new SessionManager(store);
            ids = manager.CreateIndependentSet(mission, master, Guid.NewGuid()).Sessions.Select(session => session.Id).ToArray();
            void Command(int room, ControlAction action, OperatorIdentity? actor = null) => manager.Execute(ids[room - 1], new(Guid.NewGuid(), action), actor ?? master);
            for (var room = 1; room <= 3; room++)
            {
                manager.Join(ids[room - 1], Guid.NewGuid(), $"Venue {room}", room, HeadsetKind.Quest3, master);
                Command(room, ControlAction.Begin);
            }
            Command(3, ControlAction.Pause);
            Command(5, ControlAction.End);
            Reject<AccessDeniedException>(() => manager.ReadVenuePhase(room2), "Room operators cannot preview whole-venue phase targets");
            Reject<AccessDeniedException>(() => manager.ExecuteVenuePhase(ControlAction.Pause, [], pauseKey, room2), "Room operators cannot submit venue phase changes");
            var preview = manager.ReadVenuePhase(master);
            check(preview.Pause.SelectMany(target => target.RoomIds).Order().SequenceEqual(new[] { 1, 2 }) && preview.Resume.Length == 0,
                "The venue plan excludes manually paused, preparing and ended rooms");
            Command(2, ControlAction.Pause, room2);
            Command(2, ControlAction.Resume, room2);
            Reject<VenuePhaseChangedException>(() => manager.ExecuteVenuePhase(ControlAction.Pause, Fences(preview.Pause), pauseKey, master),
                "A room leaving and re-entering Running rejects the old whole-venue preview");
            original = Fences(manager.ReadVenuePhase(master).Pause);
            Reject<ArgumentException>(() => manager.ExecuteVenuePhase(ControlAction.Pause, [original[0], original[0]], pauseKey, master), "Repeated venue targets are rejected");
            using (var connection = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = store.DatabasePath, Pooling = false }.ToString()))
            {
                connection.Open();
                using var trigger = connection.CreateCommand();
                trigger.CommandText = $"""
                    CREATE TRIGGER fail_venue_target BEFORE INSERT ON session_events
                    WHEN NEW.session_id='{original[1].SessionId:D}' AND json_extract(NEW.envelope,'$.venue.targetCount')=2
                    BEGIN SELECT RAISE(ABORT,'venue second insert failure'); END;
                    """;
                trigger.ExecuteNonQuery();
                Reject<SqliteException>(() => manager.ExecuteVenuePhase(ControlAction.Pause, original, pauseKey, master), "The second venue write failure rolls back the real SQLite transaction");
                check(manager.Get(ids[0]).State == SessionState.Running && manager.Get(ids[1]).State == SessionState.Running
                    && store.Load().SelectMany(events => events).All(entry => entry.Venue is null), "A failed venue batch leaves no durable or in-memory partial pause");
                trigger.CommandText = "DROP TRIGGER fail_venue_target";
                trigger.ExecuteNonQuery();
            }
            var receipts = new VenuePhaseReceipt[8];
            Parallel.For(0, receipts.Length, index => receipts[index] = manager.ExecuteVenuePhase(ControlAction.Pause, original.Reverse().ToArray(), pauseKey, master));
            applied = receipts[0].Sessions;
            check(receipts.Count(receipt => !receipt.Duplicate) == 1 && receipts.All(receipt => receipt.Sessions.SequenceEqual(applied))
                && applied.Select(row => row.SessionId).SequenceEqual(original.Select(fence => fence.SessionId)),
                "Concurrent venue retries apply exactly one ordered pause batch");
            var resumable = Fences(manager.ReadVenuePhase(master).Resume);
            Command(2, ControlAction.Resume, room2);
            Command(2, ControlAction.Pause, room2);
            Reject<VenuePhaseChangedException>(() => manager.ExecuteVenuePhase(ControlAction.Resume, resumable, Guid.NewGuid(), master),
                "A room paused individually after a venue pause cannot be resumed by the old batch preview");
            var current = Fences(manager.ReadVenuePhase(master).Resume);
            Reject<VenuePauseNotObservedException>(() => manager.ExecuteVenuePhase(ControlAction.Resume, current, Guid.NewGuid(), master),
                "A paused VR target also requires the current source confirmation");
            var witness = current.ToDictionary(row => row.SessionId, row => new VenuePhaseWitness(row.PhaseSinceSequence, manager.Get(row.SessionId).Sequence, false));
            var resume = manager.ExecuteVenuePhase(ControlAction.Resume, current, Guid.NewGuid(), master, witness);
            check(resume.Sessions.Single().SessionId == ids[0] && manager.Get(ids[0]).State == SessionState.Running
                && manager.Get(ids[1]).State == SessionState.Paused && manager.Get(ids[2]).State == SessionState.Paused,
                "Whole-venue Resume leaves both individually paused rooms untouched");
        }
        using (var store = new SqliteSessionEventStore(data))
        {
            var manager = new SessionManager(store);
            var receipt = manager.ExecuteVenuePhase(ControlAction.Pause, original, pauseKey, master);
            check(receipt.Duplicate && receipt.Sessions.SequenceEqual(applied) && manager.Get(ids[0]).State == SessionState.Running,
                "SQLite restart retains the original receipt without applying the old Pause again");
            Reject<InvalidOperationException>(() => manager.ExecuteVenuePhase(ControlAction.Resume, original, pauseKey, master), "A used venue key cannot change action");
            var damaged = new MemorySessionEventStore();
            foreach (var stream in store.Load()) damaged.Seed(stream[0].SessionId,
                stream[0].SessionId == ids[1] ? stream.TakeWhile(entry => entry.Venue is null).ToArray() : stream);
            Reject<InvalidDataException>(() => new SessionManager(damaged), "Restart rejects an incomplete venue transaction history");
            foreach (var session in manager.List()) manager.End(session.Id, master);
            var linked = manager.Create(SessionMode.Linked, [1, 2, 3, 4, 5], mission, master);
            manager.Join(linked.Id, Guid.NewGuid(), "Linked venue", 1, HeadsetKind.Quest3, master);
            manager.Execute(linked.Id, new(Guid.NewGuid(), ControlAction.Begin), master);
            var plan = manager.ReadVenuePhase(master);
            var receiptLinked = manager.ExecuteVenuePhase(ControlAction.Pause, Fences(plan.Pause), Guid.NewGuid(), master);
            check(plan.Pause.Single().RoomIds.Length == 5 && receiptLinked.Sessions.Single().SessionId == linked.Id,
                "Five linked rooms produce exactly one session transition");
        }

        var mixedManager = new SessionManager();
        var vr = mixedManager.Create(SessionMode.Independent, [1], mission, master);
        var mrMission = mission with { Definition = mission.Definition with { Environment = mission.Definition.Environment with { Mode = ExperienceMode.MR } } };
        var mr = mixedManager.Create(SessionMode.Independent, [2], mrMission, master);
        mixedManager.Join(vr.Id, Guid.NewGuid(), "VR seat", 1, HeadsetKind.Quest3, master);
        mixedManager.Join(mr.Id, Guid.NewGuid(), "MR seat", 2, HeadsetKind.Quest3, master);
        mixedManager.Execute(vr.Id, new(Guid.NewGuid(), ControlAction.Begin), master);
        mixedManager.OpenStream(mr.Id, new(Guid.NewGuid(), CombatOrigin.GameServer), new("venue-test-source", OperatorRole.GameServer));
        mixedManager.Execute(mr.Id, new(Guid.NewGuid(), ControlAction.Begin), master, mixedManager.Get(mr.Id).Sequence);
        mixedManager.ExecuteVenuePhase(ControlAction.Pause, Fences(mixedManager.ReadVenuePhase(master).Pause), Guid.NewGuid(), master);
        var mixedResume = Fences(mixedManager.ReadVenuePhase(master).Resume);
        var mixedWitness = mixedResume.ToDictionary(row => row.SessionId, row => new VenuePhaseWitness(row.PhaseSinceSequence, mixedManager.Get(row.SessionId).Sequence, false));
        Reject<VenueResumeNotReadyException>(() => mixedManager.ExecuteVenuePhase(ControlAction.Resume, mixedResume, Guid.NewGuid(), master, mixedWitness),
            "A missing MR readiness witness prevents the entire mixed venue Resume");
        check(mixedManager.List().All(session => session.State == SessionState.Paused), "A blocked MR room leaves the eligible VR room paused too");

        var beginData = Path.Combine(directory, "venue-begin");
        var trackingData = Path.Combine(directory, "venue-full-tracking");
        var trackingKey = Guid.NewGuid();
        var trackingFrame = new VenueTrackingFrame(Guid.NewGuid(), 20, 2000);
        VenuePhaseFence[] trackingTargets;
        VenuePhaseReceipt trackedBegin;
        using (var store = new SqliteSessionEventStore(trackingData))
        {
            var manager = new SessionManager(store);
            var roomIds = Enumerable.Range(1, SessionManager.RoomCount).ToArray();
            var session = manager.Create(SessionMode.Linked, roomIds, mission, master);
            manager.OpenStream(session.Id, new(trackingFrame.StreamId, CombatOrigin.Simulation),
                new OperatorIdentity("venue-tracking-source", OperatorRole.GameServer));
            foreach (var room in roomIds)
                for (var seat = 0; seat < SessionManager.PlayersPerRoom; seat++)
                    manager.Join(session.Id, Guid.NewGuid(), $"Seat {room}/{seat}", room, HeadsetKind.Quest3, master);
            trackingTargets = Fences(manager.ReadVenuePhase(master).Begin);
            var target = trackingTargets.Single();
            var evidence = new Dictionary<Guid, VenuePhaseWitness> { [session.Id] = new(target.PhaseSinceSequence, target.SessionSequence!.Value,
                true, [1, 2, 3, 4], trackingFrame) };
            Reject<VenueBeginNotReadyException>(() => manager.ExecuteVenuePhase(ControlAction.Begin, trackingTargets, trackingKey, master, evidence, requireFullTracking: true),
                "A linked venue with one room missing tracked evidence cannot start under the full tracking policy");
            check(manager.Get(session.Id).State == SessionState.Preparing, "A rejected full-tracking Begin appends no phase event");
            evidence[session.Id] = evidence[session.Id] with { FullRooms = roomIds };
            var wrongSource = new Dictionary<Guid, VenuePhaseWitness> { [session.Id] = evidence[session.Id] with
                { BeginFrame = trackingFrame with { StreamId = Guid.NewGuid() } } };
            Reject<VenueBeginNotReadyException>(() => manager.ExecuteVenuePhase(ControlAction.Begin, trackingTargets, trackingKey, master, wrongSource,
                requireFullTracking: true), "Guarded Begin rejects a frame from a different game source");
            trackedBegin = manager.ExecuteVenuePhase(ControlAction.Begin, trackingTargets, trackingKey, master, evidence, requireFullTracking: true);
            check(trackedBegin.RequireFullTracking && manager.Get(session.Id).State == SessionState.Running,
                "The original full-tracking request starts only after all five rooms are witnessed");
        }
        using (var store = new SqliteSessionEventStore(trackingData))
        {
            var manager = new SessionManager(store);
            var retry = manager.ExecuteVenuePhase(ControlAction.Begin, trackingTargets, trackingKey, master, requireFullTracking: true);
            check(retry.Duplicate && retry.RequireFullTracking && retry.Sessions.SequenceEqual(trackedBegin.Sessions),
                "Full-tracking Begin retry preserves the durable policy and receipt after reopening SQLite");
            var trackedApplied = retry.Sessions.Single();
            check(manager.ReadVenueTrackingBegin(trackedApplied.SessionId, master) == new VenueTrackingBegin(trackingKey, trackedApplied.AppliedAtSequence, trackingFrame),
                "The exact guarded Begin frame survives reopening the management store");
            Reject<AccessDeniedException>(() => manager.ReadVenueTrackingBegin(trackedApplied.SessionId, room2), "Only Master can read a venue tracking witness");
            Reject<InvalidOperationException>(() => manager.ExecuteVenuePhase(ControlAction.Begin, trackingTargets, trackingKey, master),
                "A retry cannot weaken the original tracking policy after reopening SQLite");
            using var connection = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = store.DatabasePath, Pooling = false }.ToString());
            connection.Open();
            using var removeWitness = connection.CreateCommand();
            removeWitness.CommandText = "UPDATE session_events SET envelope=json_remove(envelope, '$.venue.trackingFrame') WHERE json_type(envelope, '$.venue.trackingFrame')='object'";
            check(removeWitness.ExecuteNonQuery() == 1, "Compatibility fixture reproduces a previously stored policy without a frame pointer");
        }
        using (var store = new SqliteSessionEventStore(trackingData))
        {
            var manager = new SessionManager(store);
            var legacy = manager.ExecuteVenuePhase(ControlAction.Begin, trackingTargets, trackingKey, master, requireFullTracking: true);
            check(legacy.Duplicate && legacy.RequireFullTracking && manager.ReadVenueTrackingBegin(legacy.Sessions.Single().SessionId, master) is null,
                "Existing guarded Begin events retain their policy without inventing a witness frame");
        }
        var trackedVrData = Path.Combine(directory, "tracked-vr-start");
        var vrFrame = new VenueTrackingFrame(Guid.NewGuid(), 4, 300);
        Guid vrSession;
        ControlCommand vrBegin;
        long vrApplied;
        using (var store = new SqliteSessionEventStore(trackedVrData))
        {
            var manager = new SessionManager(store);
            vrSession = manager.Create(SessionMode.Independent, [2], mission, master).Id;
            manager.OpenStream(vrSession, new(vrFrame.StreamId, CombatOrigin.GameServer),
                new OperatorIdentity("tracked-vr-source", OperatorRole.GameServer));
            manager.Join(vrSession, Guid.NewGuid(), "Tracked Quest", 2, HeadsetKind.Quest3, room2);
            vrBegin = new(Guid.NewGuid(), ControlAction.Begin, ExpectedSequence: manager.Get(vrSession).Sequence, RequireTrackedStart: true);
            Reject<TrackedVrStartException>(() => manager.Execute(vrSession, vrBegin, room2),
                "No new tracked VR start is accepted without its frame");
            Reject<TrackedVrStartException>(() => manager.Execute(vrSession, vrBegin, room2,
                trackedVrStartFrame: vrFrame with { StreamId = Guid.NewGuid() }), "A different stream cannot witness tracked VR start");
            vrApplied = manager.Execute(vrSession, vrBegin, room2, trackedVrStartFrame: vrFrame).AppliedAtSequence;
        }
        using (var store = new SqliteSessionEventStore(trackedVrData))
        {
            var manager = new SessionManager(store);
            var retry = manager.Execute(vrSession, vrBegin, room2);
            check(retry.Duplicate && retry.AppliedAtSequence == vrApplied && manager.ReadTrackedVrStart(vrSession, room2) == new TrackedVrStartEvidence(vrApplied, vrFrame),
                "The exact single-session tracked Begin frame and its retry survive reopening SQLite");
            Reject<AccessDeniedException>(() => manager.ReadTrackedVrStart(vrSession, room2 with { RoomId = 1 }),
                "A different room cannot read the tracked opening witness");
            using var connection = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = store.DatabasePath, Pooling = false }.ToString());
            connection.Open();
            using var removeWitness = connection.CreateCommand();
            removeWitness.CommandText = "UPDATE session_events SET envelope=json_remove(envelope, '$.trackedVrStartFrame') WHERE json_type(envelope, '$.trackedVrStartFrame')='object'";
            check(removeWitness.ExecuteNonQuery() == 1, "The fixture can reproduce an original tracked VR start from before frame pointers were saved");
        }
        using (var store = new SqliteSessionEventStore(trackedVrData))
        {
            var manager = new SessionManager(store);
            check(manager.Execute(vrSession, vrBegin, room2).Duplicate && manager.ReadTrackedVrStart(vrSession, room2) is null,
                "Legacy tracked VR starts reopen and preserve command retry without inventing a frame");
        }
        var participationData = Path.Combine(directory, "venue-participation");
        var participationKey = Guid.NewGuid();
        VenuePhaseFence[] participationTargets;
        var participationFrame = new VenueTrackingFrame(Guid.NewGuid(), 7, 600);
        using (var store = new SqliteSessionEventStore(participationData))
        {
            var manager = new SessionManager(store);
            var roomIds = Enumerable.Range(1, SessionManager.RoomCount).ToArray();
            var session = manager.Create(SessionMode.Linked, roomIds, mission, master);
            manager.OpenStream(session.Id, new(participationFrame.StreamId, CombatOrigin.Simulation),
                new OperatorIdentity("venue-participation-source", OperatorRole.GameServer));
            foreach (var room in roomIds)
                for (var seat = 0; seat < SessionManager.PlayersPerRoom; seat++)
                    manager.Join(session.Id, Guid.NewGuid(), $"Seat {room}/{seat}", room, HeadsetKind.Quest3, master);
            participationTargets = Fences(manager.ReadVenuePhase(master).Begin);
            var target = participationTargets.Single();
            var witness = new VenuePhaseWitness(target.PhaseSinceSequence, target.SessionSequence!.Value, true, roomIds, participationFrame);
            var evidence = new Dictionary<Guid, VenuePhaseWitness> { [session.Id] = witness with { BeginFrame = null } };
            Reject<VenueBeginNotReadyException>(() => manager.ExecuteVenuePhase(ControlAction.Begin, participationTargets, participationKey, master,
                evidence, requireFullParticipation: true), "Full participation requires an exact saved Preparing frame");
            evidence[session.Id] = witness;
            var receipt = manager.ExecuteVenuePhase(ControlAction.Begin, participationTargets, participationKey, master, evidence, requireFullParticipation: true);
            check(receipt.RequireFullParticipation && !receipt.RequireFullTracking && manager.ReadVenueTrackingBegin(session.Id, master) is null,
                "Full participation starts the witnessed venue without recording a full-tracking claim");
        }
        using (var store = new SqliteSessionEventStore(participationData))
        {
            var manager = new SessionManager(store);
            var retry = manager.ExecuteVenuePhase(ControlAction.Begin, participationTargets, participationKey, master, requireFullParticipation: true);
            var appliedBegin = retry.Sessions.Single();
            var evidence = manager.ReadVenueBeginEvidence(appliedBegin.SessionId, master);
            check(retry.Duplicate && retry.RequireFullParticipation && manager.Get(appliedBegin.SessionId).State == SessionState.Running
                && evidence == (null, new VenueParticipationBegin(participationKey, appliedBegin.AppliedAtSequence, participationFrame)),
                "Full participation policy and frame survive a management restart");
            Reject<InvalidOperationException>(() => manager.ExecuteVenuePhase(ControlAction.Begin, participationTargets, participationKey, master),
                "A retry cannot weaken the original participation policy after reopening SQLite");
        }
        var beginId = Guid.NewGuid();
        var reportSource = new OperatorIdentity("venue-report-source", OperatorRole.GameServer);
        var reportStream = Guid.NewGuid();
        VenuePhaseFence[] start;
        VenuePhaseApplied[] started;
        using (var store = new SqliteSessionEventStore(beginData))
        {
            var manager = new SessionManager(store);
            var first = manager.Create(SessionMode.Independent, [1], mission, master);
            var second = manager.Create(SessionMode.Independent, [2], mission, master);
            manager.OpenStream(second.Id, new(reportStream, CombatOrigin.Simulation), reportSource);
            manager.Join(first.Id, Guid.NewGuid(), "First", 1, HeadsetKind.Quest3, master);
            var stale = Fences(manager.ReadVenuePhase(master).Begin);
            manager.Join(second.Id, Guid.NewGuid(), "Second", 2, HeadsetKind.Quest3, master);
            Reject<VenuePhaseChangedException>(() => manager.ExecuteVenuePhase(ControlAction.Begin, stale, beginId, master),
                "A new admission makes the original batch Begin revision stale");
            start = Fences(manager.ReadVenuePhase(master).Begin);
            var witnesses = start.ToDictionary(row => row.SessionId, row => new VenuePhaseWitness(row.PhaseSinceSequence, row.SessionSequence!.Value, true));
            var partial = witnesses.Where(row => row.Key == first.Id).ToDictionary();
            Reject<VenueBeginNotReadyException>(() => manager.ExecuteVenuePhase(ControlAction.Begin, start, beginId, master, partial),
                "Batch Begin requires a current witness for every preparing session");
            check(manager.List().All(session => session.State == SessionState.Preparing), "An unready room leaves both rooms preparing");
            started = manager.ExecuteVenuePhase(ControlAction.Begin, start, beginId, master, witnesses).Sessions;
            check(started.Length == 2 && started.Zip(start).All(pair => pair.First.AppliedAtSequence == pair.Second.SessionSequence + 1),
                "Batch Begin saves each witnessed revision and its exact resulting sequence");
            manager.End(first.Id, master);
        }
        var endId = Guid.NewGuid();
        var newerEndId = Guid.NewGuid();
        VenuePhaseFence[] endTargets;
        VenuePhaseApplied[] ended;
        Guid replacement;
        using (var store = new SqliteSessionEventStore(beginData))
        {
            var manager = new SessionManager(store);
            var retry = manager.ExecuteVenuePhase(ControlAction.Begin, start, beginId, master);
            check(retry.Duplicate && retry.Sessions.SequenceEqual(started)
                && manager.List(includeEnded: true).Count(session => session.State == SessionState.Ended) == 1,
                "Restart preserves the original batch Begin receipt after a room ends");
            check(manager.ReadLatestVenueEnd(master) is null, "Individual End does not create a venue closure batch");
            check(manager.FindVenueEndForSessions([manager.List(includeEnded: true).Single(session => session.State == SessionState.Ended).Id], master) is null,
                "An individual End does not identify a shared replay batch");
            Reject<AccessDeniedException>(() => manager.ReadLatestVenueEnd(room2), "Venue closure is scoped to Master");
            var preparing = manager.Create(SessionMode.Independent, [1], mission, master);
            var running = manager.List().Single(session => session.State == SessionState.Running);
            var staleEnd = Fences(manager.ReadVenuePhase(master).End);
            manager.Execute(running.Id, new(Guid.NewGuid(), ControlAction.Pause), room2);
            Reject<VenuePhaseChangedException>(() => manager.ExecuteVenuePhase(ControlAction.End, staleEnd, endId, master),
                "An intervening phase change rejects the whole End preview");
            endTargets = Fences(manager.ReadVenuePhase(master).End);
            using (var connection = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = store.DatabasePath, Pooling = false }.ToString()))
            {
                connection.Open();
                using var trigger = connection.CreateCommand();
                trigger.CommandText = $"""
                    CREATE TRIGGER fail_venue_end BEFORE INSERT ON session_events
                    WHEN NEW.session_id='{endTargets[1].SessionId:D}' AND json_extract(NEW.envelope,'$.venue.targetCount')=2
                    BEGIN SELECT RAISE(ABORT,'venue End second insert failure'); END;
                    """;
                trigger.ExecuteNonQuery();
                Reject<SqliteException>(() => manager.ExecuteVenuePhase(ControlAction.End, endTargets, endId, master),
                    "An End failure on the second write rolls back the SQLite batch");
                check(manager.Get(preparing.Id).State == SessionState.Preparing && manager.Get(running.Id).State == SessionState.Paused
                    && manager.ReadLatestVenueEnd(master) is null, "Failed End leaves the original phases and has no closure receipt");
                trigger.CommandText = "DROP TRIGGER fail_venue_end";
                trigger.ExecuteNonQuery();
            }
            ended = manager.ExecuteVenuePhase(ControlAction.End, endTargets, endId, master).Sessions;
            check(ended.Length == 2 && manager.List().Length == 0 && manager.Get(preparing.Id).StartedAtUtc is null,
                "The whole venue can end a preparing room without a source alongside a paused room");
            Reject<AccessDeniedException>(() => manager.FinalVenueReports(endId, room2), "Batch final reports require Master before looking up the ID");
            Reject<KeyNotFoundException>(() => manager.FinalVenueReports(beginId, master), "A venue Begin ID cannot export a final report bundle");
            Reject<VenueReportsNotReadyException>(() => manager.FinalVenueReports(endId, master),
                "One unsealed source prevents export of the entire venue report bundle");
            manager.SealStream(running.Id, new(reportStream, 0), reportSource);
            replacement = manager.Create(SessionMode.Independent, [1], mission, master).Id;
        }
        using (var store = new SqliteSessionEventStore(beginData))
        {
            var manager = new SessionManager(store);
            var batch = manager.ReadLatestVenueEnd(master);
            var retry = manager.ExecuteVenuePhase(ControlAction.End, endTargets, endId, master);
            check(batch?.RequestId == endId && batch.Sessions.SequenceEqual(ended) && retry.Duplicate
                && retry.Sessions.SequenceEqual(ended) && manager.List().Single().Id == replacement,
                "After restart and room reuse, closure and End retry identify the original batch without touching its replacement");
            var report = manager.FinalVenueReports(endId, master);
            check(report.Sessions.Select(item => item.Report.RoomIds.Single()).SequenceEqual(new[] { 1, 2 })
                && report.Sessions.All(item => item.AppliedAtSequence == ended.Single(row => row.SessionId == item.Report.SessionId).AppliedAtSequence)
                && report.Sessions[0].Report.Players.Length == 0 && report.Sessions[1].Report.FinalStreamSequence == 0
                && report.Sessions.All(item => item.Report.SessionId != replacement),
                "After restart the batch report identifies the original no-source room and sealed room in room order");
            manager.ExecuteVenuePhase(ControlAction.End, Fences(manager.ReadVenuePhase(master).End), newerEndId, master);
            var firstPage = manager.ReadVenueEndHistory(null, 1, master);
            check(firstPage.Batches.Single().RequestId == newerEndId && firstPage.NextBefore == newerEndId,
                "Venue history returns the newest End and an exclusive cursor");
            Reject<AccessDeniedException>(() => manager.ReadVenueEndHistory(null, 1, room2), "Venue history is scoped to Master");
            Reject<KeyNotFoundException>(() => manager.ReadVenueEndHistory(beginId, 1, master), "A non-End request ID is not a history cursor");
            Reject<ArgumentException>(() => manager.ReadVenueEndHistory(null, 51, master), "Venue history caps the page size");
        }
        using (var store = new SqliteSessionEventStore(beginData))
        {
            var manager = new SessionManager(store);
            var earlier = manager.ReadVenueEndHistory(newerEndId, 1, master);
            var old = earlier.Batches.Single();
            check(manager.ReadLatestVenueEnd(master)?.RequestId == newerEndId && earlier.NextBefore is null
                && old.RequestId == endId && old.RoomIds.SequenceEqual(new[] { 1, 2 }) && old.SessionCount == 2
                && manager.ReadVenueEnd(endId, master).Sessions.SequenceEqual(ended),
                "Restart restores the exclusive history cursor and the exact older batch behind it");
            var originalSessions = ended.Select(row => row.SessionId).Reverse().ToArray();
            check(manager.FindVenueEndForSessions(originalSessions, master) == endId
                && manager.FindVenueEndForSessions([originalSessions[0]], master) is null
                && manager.FindVenueEndForSessions([originalSessions[0], replacement], master) is null
                && manager.FindVenueEndForSessions([replacement, originalSessions[0]], master) is null,
                "Replay binding resolves the original durable End after restart and rejects partial or mixed batches");
            Reject<AccessDeniedException>(() => manager.FindVenueEndForSessions(originalSessions, room2),
                "Original replay batch lookup is scoped to Master");
        }

        var environmentData = Path.Combine(directory, "venue-environment");
        var climateKey = Guid.NewGuid();
        var storm = new VenueClimate(Weather.Storm, TimeOfDay.Night, true);
        VenuePhaseFence[] climateTargets;
        VenuePhaseApplied[] changed;
        Guid vrId;
        Guid mrId;
        using (var store = new SqliteSessionEventStore(environmentData))
        {
            var manager = new SessionManager(store);
            var small = mission with { Definition = mission.Definition with { Enemies = mission.Definition.Enemies with { Count = 1 } } };
            var larger = mrMission with { Definition = mrMission.Definition with { Enemies = mrMission.Definition.Enemies with { Count = 2 } } };
            vrId = manager.Create(SessionMode.Independent, [1], small, master).Id;
            mrId = manager.Create(SessionMode.Independent, [2], larger, master).Id;
            manager.Create(SessionMode.Independent, [3], mission, master);
            manager.Join(vrId, Guid.NewGuid(), "VR seat", 1, HeadsetKind.Quest3, master);
            manager.Join(mrId, Guid.NewGuid(), "MR seat", 2, HeadsetKind.Quest3, master);
            manager.OpenStream(mrId, new(Guid.NewGuid(), CombatOrigin.GameServer), new("venue-climate-source", OperatorRole.GameServer));
            manager.Execute(vrId, new(Guid.NewGuid(), ControlAction.Begin), master);
            manager.Execute(mrId, new(Guid.NewGuid(), ControlAction.Begin), master, manager.Get(mrId).Sequence);
            VenuePhaseFence[] ClimateFences() => manager.ReadVenuePhase(master).Environment.Select(target =>
                new VenuePhaseFence(target.SessionId, target.PhaseSinceSequence, EnvironmentSinceSequence: target.EnvironmentSinceSequence)).ToArray();
            var stale = ClimateFences();
            check(stale.Length == 2, "Venue environment targets only the running rooms");
            var current = manager.Get(mrId);
            manager.Execute(mrId, new(Guid.NewGuid(), ControlAction.SetEnvironment, current.Environment), room2);
            Reject<VenuePhaseChangedException>(() => manager.ExecuteVenuePhase(ControlAction.SetEnvironment, stale, climateKey, master, climate: storm),
                "An intervening room environment command rejects the whole climate preview");
            climateTargets = ClimateFences();
            Reject<ArgumentException>(() => manager.ExecuteVenuePhase(ControlAction.SetEnvironment, climateTargets, climateKey, master,
                climate: storm with { Lightning = null }), "Venue climate requires an explicit lightning setting");
            manager.Execute(vrId, new(Guid.NewGuid(), ControlAction.SetEnemies, Enemies: manager.Get(vrId).Enemies), master);
            changed = manager.ExecuteVenuePhase(ControlAction.SetEnvironment, climateTargets, climateKey, master, climate: storm).Sessions;
            var vrView = manager.Get(vrId);
            var mrView = manager.Get(mrId);
            check(changed.Length == 2 && vrView.Environment == new EnvironmentSettings(ExperienceMode.VR, Weather.Storm, TimeOfDay.Night, true)
                && mrView.Environment == (vrView.Environment with { Mode = ExperienceMode.MR })
                && vrView.Mission.Definition.Environment == mission.Definition.Environment,
                "One climate transaction retains each experience mode and the saved mission across unrelated commands");
            Reject<InvalidOperationException>(() => manager.ExecuteVenuePhase(ControlAction.SetEnvironment, climateTargets, climateKey, master,
                climate: storm with { Weather = Weather.Rain }), "A climate request ID cannot change the selected weather");
            manager.Execute(mrId, new(Guid.NewGuid(), ControlAction.SetEnvironment, mrView.Environment with { Lightning = false }), room2);
        }
        var enemyKey = Guid.NewGuid();
        var policy = new VenueEnemyPolicy(EnemyBehavior.Patrol, true);
        VenuePhaseFence[] enemyTargets;
        VenuePhaseApplied[] changedEnemies;
        using (var store = new SqliteSessionEventStore(environmentData))
        {
            var manager = new SessionManager(store);
            var retry = manager.ExecuteVenuePhase(ControlAction.SetEnvironment, climateTargets, climateKey, master, climate: storm);
            check(retry.Duplicate && retry.Sessions.SequenceEqual(changed) && manager.GetWithPhase(vrId).VenueEnvironmentSequence
                == changed.Single(row => row.SessionId == vrId).AppliedAtSequence && manager.GetWithPhase(mrId).VenueEnvironmentSequence is null
                && !manager.Get(mrId).Environment.Lightning, "Climate receipt survives restart and leaves a later room override intact");
            var climate = manager.ReadVenuePhase(master).LatestEnvironment!;
            check(climate.RequestId == climateKey && climate.RecordedAtUtc != default && climate.Weather == Weather.Storm
                && climate.TimeOfDay == TimeOfDay.Night && climate.Lightning && climate.Sessions.Length == 2
                && climate.Sessions[0].RoomIds.SequenceEqual([1]) && climate.Sessions[1].RoomIds.SequenceEqual([2])
                && climate.Sessions[0].State == VenueEnvironmentApplicationState.Current && climate.Sessions[1].State == VenueEnvironmentApplicationState.Superseded
                && climate.Sessions.All(row => row.AppliedAtSequence == changed.Single(entry => entry.SessionId == row.SessionId).AppliedAtSequence),
                "Restart restores the original climate batch, exact commands, settings, rooms and current override status");

            VenuePhaseFence[] EnemyFences() => manager.ReadVenuePhase(master).Enemies.Select(target =>
                new VenuePhaseFence(target.SessionId, target.PhaseSinceSequence, EnemiesSinceSequence: target.EnemiesSinceSequence)).ToArray();
            var stale = EnemyFences();
            var current = manager.Get(mrId);
            manager.Execute(mrId, new(Guid.NewGuid(), ControlAction.SetEnemies, Enemies: current.Enemies), room2);
            Reject<VenuePhaseChangedException>(() => manager.ExecuteVenuePhase(ControlAction.SetEnemies, stale, enemyKey, master, enemyPolicy: policy),
                "An intervening enemy command rejects the entire strategy preview");
            enemyTargets = EnemyFences();
            Reject<ArgumentException>(() => manager.ExecuteVenuePhase(ControlAction.SetEnemies, enemyTargets, enemyKey, master,
                enemyPolicy: policy with { AutoAttack = null }), "Batch enemy policy requires an explicit attack setting");
            manager.Execute(mrId, new(Guid.NewGuid(), ControlAction.SetEnvironment, current.Environment), room2);
            changedEnemies = manager.ExecuteVenuePhase(ControlAction.SetEnemies, enemyTargets, enemyKey, master, enemyPolicy: policy).Sessions;
            check(changedEnemies.Length == 2 && manager.Get(vrId).Enemies == new EnemySettings(1, EnemyBehavior.Patrol, true)
                && manager.Get(mrId).Enemies == new EnemySettings(2, EnemyBehavior.Patrol, true)
                && manager.GetWithPhase(vrId).VenueEnvironmentSequence is not null,
                "Enemy policy preserves different counts and can commit across a separate climate update");
            var batch = manager.ReadVenuePhase(master).LatestEnemies!;
            check(batch.RequestId == enemyKey && batch.RecordedAtUtc != default && batch.Behavior == EnemyBehavior.Patrol && batch.AutoAttack
                && batch.Sessions.Length == 2 && batch.Sessions[0].RoomIds.SequenceEqual([1]) && batch.Sessions[1].RoomIds.SequenceEqual([2])
                && batch.Sessions.All(row => row.State == VenueEnemyApplicationState.Current
                    && row.AppliedAtSequence == changedEnemies.Single(entry => entry.SessionId == row.SessionId).AppliedAtSequence)
                && batch.Sessions.Select(row => row.TargetCount).SequenceEqual([1, 2]),
                "Latest enemy batch reads original room scopes, command sequences and different saved counts");
            Reject<InvalidOperationException>(() => manager.ExecuteVenuePhase(ControlAction.SetEnemies, enemyTargets, enemyKey, master,
                enemyPolicy: policy with { AutoAttack = false }), "The enemy policy key cannot be reused with a different attack setting");
            manager.Execute(mrId, new(Guid.NewGuid(), ControlAction.SetEnemies, Enemies: new(2, EnemyBehavior.Hold, false)), room2);
        }
        using (var store = new SqliteSessionEventStore(environmentData))
        {
            var manager = new SessionManager(store);
            var retry = manager.ExecuteVenuePhase(ControlAction.SetEnemies, enemyTargets, enemyKey, master, enemyPolicy: policy);
            check(retry.Duplicate && retry.Sessions.SequenceEqual(changedEnemies)
                && manager.GetWithPhase(vrId).VenueEnemiesSequence == changedEnemies.Single(row => row.SessionId == vrId).AppliedAtSequence
                && manager.GetWithPhase(mrId).VenueEnemiesSequence is null && manager.Get(mrId).Enemies == new EnemySettings(2, EnemyBehavior.Hold, false),
                "Restart preserves the enemy policy receipt and the later room override");
            var latest = manager.ReadVenuePhase(master).LatestEnemies!;
            check(latest.RequestId == enemyKey && latest.Sessions[0].State == VenueEnemyApplicationState.Current
                && latest.Sessions[1].State == VenueEnemyApplicationState.Superseded && latest.Sessions[1].TargetCount == 2,
                "Latest enemy batch is restored from the original ledger with the current override status");
            manager.Execute(mrId, new(Guid.NewGuid(), ControlAction.End), master);
            var endedClimate = manager.ReadVenuePhase(master).LatestEnvironment!;
            check(endedClimate.RequestId == climateKey && endedClimate.Sessions[1].SessionId == mrId
                && endedClimate.Sessions[1].State == VenueEnvironmentApplicationState.Ended
                && endedClimate.Sessions[1].AppliedAtSequence == changed.Single(row => row.SessionId == mrId).AppliedAtSequence,
                "Ending an overridden room preserves the original climate target and sequence with terminal status");
            var laterClimateKey = Guid.NewGuid();
            var laterClimateTargets = manager.ReadVenuePhase(master).Environment.Select(row =>
                new VenuePhaseFence(row.SessionId, row.PhaseSinceSequence, EnvironmentSinceSequence: row.EnvironmentSinceSequence)).ToArray();
            manager.ExecuteVenuePhase(ControlAction.SetEnvironment, laterClimateTargets, laterClimateKey, master, climate: storm);
            manager.ExecuteVenuePhase(ControlAction.SetEnvironment, climateTargets, climateKey, master, climate: storm);
            check(manager.ReadVenuePhase(master).LatestEnvironment is { } laterClimate && laterClimate.RequestId == laterClimateKey
                && laterClimate.Sessions.Single().SessionId == vrId && laterClimate.Sessions[0].AppliedAtSequence > endedClimate.Sessions[0].AppliedAtSequence,
                "A new climate batch with identical settings replaces the previous batch even after an older request is retried");
            var endedEnemyBatch = manager.ReadVenuePhase(master).LatestEnemies!;
            check(endedEnemyBatch.RequestId == enemyKey && endedEnemyBatch.Sessions[1].State == VenueEnemyApplicationState.Ended
                && endedEnemyBatch.Sessions[1].SessionId == mrId && endedEnemyBatch.Sessions[1].AppliedAtSequence == latest.Sessions[1].AppliedAtSequence,
                "Ending a room keeps its original enemy batch identity and command sequence");
            var nextKey = Guid.NewGuid();
            var nextTargets = manager.ReadVenuePhase(master).Enemies.Select(row =>
                new VenuePhaseFence(row.SessionId, row.PhaseSinceSequence, EnemiesSinceSequence: row.EnemiesSinceSequence)).ToArray();
            manager.ExecuteVenuePhase(ControlAction.SetEnemies, nextTargets, nextKey, master, enemyPolicy: policy with { Behavior = EnemyBehavior.Advance });
            manager.ExecuteVenuePhase(ControlAction.SetEnemies, enemyTargets, enemyKey, master, enemyPolicy: policy);
            var next = manager.ReadVenuePhase(master).LatestEnemies!;
            check(next.RequestId == nextKey && next.Behavior == EnemyBehavior.Advance && next.Sessions.Single().SessionId == vrId,
                "An old batch retry cannot replace the latest accepted enemy batch");
        }
    }
}
