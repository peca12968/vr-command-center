using Microsoft.Data.Sqlite;
using VrCommand.Core;
using VrCommand.Persistence;

internal static class IndependentSetChecks
{
    internal static void Run(Action<bool, string> check, string directory, Mission mission)
    {
        void Reject<T>(Action action, string message) where T : Exception
        {
            try { action(); }
            catch (T) { check(true, message); return; }
            throw new Exception($"Expected {typeof(T).Name}: {message}");
        }

        var master = new OperatorIdentity("independent-set-master", OperatorRole.Master);
        var room = new OperatorIdentity("independent-set-room", OperatorRole.RoomController, 3);
        var key = Guid.NewGuid();
        var data = Path.Combine(directory, "independent-set");
        Guid[] original;
        Guid replacement;
        using (var store = new SqliteSessionEventStore(data))
        {
            var manager = new SessionManager(store);
            Reject<AccessDeniedException>(() => manager.CreateIndependentSet(mission, room, key), "A room operator cannot reserve all five independent rooms");
            Reject<ArgumentException>(() => manager.CreateIndependentSet(mission, master, Guid.Empty), "A five-room reservation requires a non-empty key");
            var occupied = manager.Create(SessionMode.Independent, [3], mission, room);
            Reject<IndependentRoomsOccupiedException>(() => manager.CreateIndependentSet(mission, master, key), "A busy room rejects the entire reservation");
            check(store.Load().Length == 1 && manager.List().Single().Id == occupied.Id, "A busy room leaves the other four rooms free on disk and in memory");
            manager.End(occupied.Id, room);

            var dense = mission with { Definition = mission.Definition with { Enemies = mission.Definition.Enemies with { Count = 100 },
                Props = [.. from z in new[] { 2, 4 } from x in new[] { -3, -1, 1, 3 } select new PropPlacement("sandbag", new(x, 0, z), 0)] } };
            Reject<MissionLayoutRejectedException>(() => manager.CreateIndependentSet(dense, master, key), "A five-room reservation checks independent layout capacity before creating any session");

            using (var connection = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = store.DatabasePath, Pooling = false }.ToString()))
            {
                connection.Open();
                using var command = connection.CreateCommand();
                command.CommandText = """
                    CREATE TRIGGER fail_third_room BEFORE INSERT ON session_events
                    WHEN NEW.sequence=1 AND json_extract(NEW.envelope,'$.payload.roomIds[0]')=3
                    BEGIN SELECT RAISE(ABORT,'test third-room insert failure'); END;
                    """;
                command.ExecuteNonQuery();
                Reject<SqliteException>(() => manager.CreateIndependentSet(mission, master, key), "A failing third insert rolls back the real SQLite transaction");
                check(manager.List().Length == 0 && store.Load().Single()[0].SessionId == occupied.Id,
                    "No partial reservations or committed batch key survive a failed transaction");
                command.CommandText = "DROP TRIGGER fail_third_room";
                command.ExecuteNonQuery();
            }

            var receipts = new IndependentSessionSet[12];
            Parallel.For(0, receipts.Length, index => receipts[index] = manager.CreateIndependentSet(mission, master, key));
            original = receipts[0].Sessions.Select(session => session.Id).ToArray();
            check(receipts.Count(receipt => !receipt.Duplicate) == 1 && receipts.All(receipt => receipt.Sessions.Select(session => session.Id).SequenceEqual(original))
                && manager.Rooms().Select(value => value.SessionId).SequenceEqual(original.Select(id => (Guid?)id)),
                "Concurrent same-key requests commit exactly one five-room set and return the same IDs in room order");
            check(receipts[0].Sessions.All(session => session.State == SessionState.Preparing && session.Mode == SessionMode.Independent && session.Mission.Id == mission.Id
                && manager.Events(session.Id).Single().Kind == SessionEventKind.Created), "Five separate preparing sessions pin the same saved mission with one event each");
            Reject<InvalidOperationException>(() => manager.CreateIndependentSet(mission with { Definition = mission.Definition with { Name = "Changed" } }, master, key),
                "A five-room retry cannot replace the immutable mission");
            Reject<InvalidOperationException>(() => manager.Create(SessionMode.Independent, [1], mission, master, key), "A batch key cannot confirm a single-room request");
            manager.End(original[2], room);
            replacement = manager.Create(SessionMode.Independent, [3], mission, room).Id;
        }
        using (var store = new SqliteSessionEventStore(data))
        {
            var manager = new SessionManager(store);
            var retried = manager.CreateIndependentSet(mission, master, key);
            check(retried.Duplicate && retried.Sessions.Select(session => session.Id).SequenceEqual(original)
                && retried.Sessions[2].State == SessionState.Ended && manager.Rooms()[2].SessionId == replacement,
                "A SQLite restart restores the full batch key without reopening an ended room or replacing its new session");
            var damaged = new MemorySessionEventStore();
            foreach (var stream in store.Load().Where(stream => stream[0].SessionId != original[2])) damaged.Seed(stream[0].SessionId, stream);
            Reject<InvalidDataException>(() => new SessionManager(damaged), "Recovery rejects an incomplete persisted batch");
        }
    }
}
