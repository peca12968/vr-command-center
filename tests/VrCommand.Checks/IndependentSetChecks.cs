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
        var mixedKey = Guid.NewGuid();
        var mixedMissions = Enumerable.Range(1, SessionManager.RoomCount).Select(number => mission with
        {
            Id = Guid.NewGuid(),
            Definition = mission.Definition with { Name = $"Room {number}", DurationSeconds = 300 + number }
        }).ToArray();
        Guid[] mixedIds;
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
            var invalid = mixedMissions.ToArray();
            invalid[3] = dense;
            try
            {
                manager.CreateIndependentSet(invalid, master, mixedKey);
                throw new Exception("Expected room-specific layout rejection.");
            }
            catch (MissionLayoutRejectedException error)
            {
                check(error.RoomId == 4 && manager.List().Length == 0 && store.Load().Length == 1,
                    "A fourth room with an invalid layout rejects the complete distinct plan before any writes");
            }

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
                Reject<SqliteException>(() => manager.CreateIndependentSet(mixedMissions, master, mixedKey), "A failing third insert also rolls back a distinct mission plan");
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
            foreach (var session in manager.List()) manager.End(session.Id, master);
            var mixed = manager.CreateIndependentSet(mixedMissions, master, mixedKey);
            mixedIds = mixed.Sessions.Select(session => session.Id).ToArray();
            check(!mixed.Duplicate && mixed.Sessions.Select(session => session.Mission.Id).SequenceEqual(mixedMissions.Select(value => value.Id))
                && mixed.Sessions.Select(session => session.Mission.Definition.DurationSeconds).SequenceEqual(mixedMissions.Select(value => value.Definition.DurationSeconds)),
                "Five separate rooms pin their own immutable mission snapshots");
            var swapped = mixedMissions.ToArray();
            (swapped[1], swapped[2]) = (swapped[2], swapped[1]);
            Reject<InvalidOperationException>(() => manager.CreateIndependentSet(swapped, master, mixedKey), "A retry cannot swap two rooms even when all version IDs are the same set");
        }
        using (var store = new SqliteSessionEventStore(data))
        {
            var manager = new SessionManager(store);
            var retried = manager.CreateIndependentSet(mixedMissions, master, mixedKey);
            check(retried.Duplicate && retried.Sessions.Select(session => session.Id).SequenceEqual(mixedIds)
                && retried.Sessions.Select(session => session.Mission.Id).SequenceEqual(mixedMissions.Select(value => value.Id)),
                "SQLite restart restores the original room-to-version assignment and request key");
            var damaged = new MemorySessionEventStore();
            foreach (var stream in store.Load())
            {
                if (stream[0].SessionId == mixedIds[3])
                {
                    var creation = stream[0].Read<SessionCreated>() with { Mission = mixedMissions[2] };
                    stream[0] = stream[0] with { Payload = System.Text.Json.JsonSerializer.SerializeToElement(creation, JsonFormat.Options) };
                }
                damaged.Seed(stream[0].SessionId, stream);
            }
            Reject<InvalidDataException>(() => new SessionManager(damaged), "Recovery rejects a valid mission assigned to the wrong room in a persisted plan");
        }
    }
}
