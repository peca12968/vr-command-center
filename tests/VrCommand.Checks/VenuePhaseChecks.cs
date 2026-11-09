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
        static VenuePhaseFence[] Fences(VenuePhaseTarget[] targets) => targets.Select(target => new VenuePhaseFence(target.SessionId, target.PhaseSinceSequence)).ToArray();
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
            var resume = manager.ExecuteVenuePhase(ControlAction.Resume, Fences(manager.ReadVenuePhase(master).Resume), Guid.NewGuid(), master);
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
        Reject<VenueResumeNotReadyException>(() => mixedManager.ExecuteVenuePhase(ControlAction.Resume, mixedResume, Guid.NewGuid(), master),
            "A missing MR readiness witness prevents the entire mixed venue Resume");
        check(mixedManager.List().All(session => session.State == SessionState.Paused), "A blocked MR room leaves the eligible VR room paused too");
    }
}
