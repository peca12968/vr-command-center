using System.Text.Json;
using Microsoft.Data.Sqlite;
using VrCommand.Core;
using VrCommand.Persistence;

internal static class PersistenceChecks
{
    internal static void Run(Action<bool, string> check, string directory, Mission mission)
    {
        void Reject<T>(Action action, string message) where T : Exception
        {
            try { action(); }
            catch (T) { check(true, message); return; }
            throw new Exception($"Expected {typeof(T).Name}: {message}");
        }
        var data = Path.Combine(directory, "sqlite-migration");
        Guid id;
        SessionEvent[] legacy;
        using (var old = new FileSessionEventStore(data))
        {
            var manager = new SessionManager(old);
            id = manager.Create(SessionMode.Independent, [1], mission).Id;
            manager.Join(id, Guid.NewGuid(), "Legacy", 1, HeadsetKind.Quest3);
            manager.Execute(id, new(Guid.NewGuid(), ControlAction.Begin));
            legacy = manager.Events(id).Select(entry => entry with { SchemaVersion = 2 }).ToArray();
            File.WriteAllText(Path.Combine(data, $"{id:D}.json"), JsonSerializer.Serialize(legacy, JsonFormat.Options));
        }
        var backupPath = Path.Combine(data, $"{id:D}.json");
        var backup = File.ReadAllText(backupPath);
        var isolated = new MemorySessionEventStore();
        Reject<InvalidOperationException>(() => isolated.Append(legacy[1] with { SessionId = Guid.NewGuid() }),
            "Memory store rejects a non-initial first event");
        check(isolated.Load().Length == 0, "Rejected memory append cannot leave an empty phantom session");
        using (var store = new SqliteSessionEventStore(data))
        {
            var restored = new SessionManager(store);
            check(restored.Get(id).State == SessionState.Running && restored.Events(id).Length == legacy.Length,
                "SQLite imports existing JSON histories before serving sessions");
            check(File.ReadAllText(backupPath) == backup, "Migration leaves JSON backup byte-for-byte unchanged");
            Reject<IOException>(() => { using var competing = new SqliteSessionEventStore(data); }, "SQLite store retains the exclusive process lease");
            Reject<InvalidOperationException>(() => store.Append(legacy[^1] with { Sequence = legacy.Length + 2, EventId = Guid.NewGuid() }),
                "Storage rejects non-contiguous append without adding a row");
            Reject<SqliteException>(() => store.Append(legacy[0] with { Sequence = legacy.Length + 1 }),
                "Unique event ID violation rolls back the transaction");
            check(store.Load().Single().Length == legacy.Length, "Rejected SQLite appends leave persisted history intact");
            restored.Execute(id, new(Guid.NewGuid(), ControlAction.Pause));
            check(store.Load().Single().Length == legacy.Length + 1, "Valid append succeeds after a rolled-back transaction");
        }
        // After migration the database is authoritative; old backups are not re-imported on every restart.
        File.WriteAllText(backupPath, "obsolete-backup-no-longer-read");
        using (var store = new SqliteSessionEventStore(data))
        {
            check(new SessionManager(store).Get(id).State == SessionState.Paused && store.Load().Single().Length == legacy.Length + 1,
                "Restart uses SQLite and does not re-import stale JSON backups");
        }
        var disposed = new SqliteSessionEventStore(data);
        var database = disposed.DatabasePath;
        disposed.Dispose();
        Reject<ObjectDisposedException>(() => disposed.Append(legacy[0]), "Disposed SQLite store cannot append");
        Execute(database, "UPDATE session_events SET envelope='{}' WHERE sequence=1");
        using (var store = new SqliteSessionEventStore(data))
            Reject<InvalidDataException>(() => new SessionManager(store), "Row/envelope identity corruption fails recovery");

        var retryDirectory = Path.Combine(directory, "sqlite-import-retry");
        Directory.CreateDirectory(retryDirectory);
        File.WriteAllText(Path.Combine(retryDirectory, $"{id:D}.json"), backup);
        var memory = new SessionManager();
        var second = memory.Create(SessionMode.Independent, [2], mission);
        var invalidPath = Path.Combine(retryDirectory, $"{second.Id:D}.json");
        File.WriteAllText(invalidPath, "[]");
        Reject<InvalidDataException>(() => { using var invalid = new SqliteSessionEventStore(retryDirectory); },
            "Invalid legacy stream aborts the complete migration");
        File.WriteAllText(invalidPath, JsonSerializer.Serialize(memory.Events(second.Id), JsonFormat.Options));
        using (var store = new SqliteSessionEventStore(retryDirectory))
            check(new SessionManager(store).List().Length == 2 && store.Load().Sum(e => e.Length) == legacy.Length + 1,
                "Fixing a failed import permits one clean retry without partial or duplicate rows");

        var fullVenue = Path.Combine(directory, "sqlite-25-player-combat");
        Guid fullId;
        using (var store = new SqliteSessionEventStore(fullVenue))
        {
            var manager = new SessionManager(store);
            var master = new OperatorIdentity("master", OperatorRole.Master);
            var server = new OperatorIdentity("game-server", OperatorRole.GameServer);
            fullId = manager.Create(SessionMode.Linked, [1,2,3,4,5], mission, master).Id;
            foreach (var room in Enumerable.Range(1, 5))
                foreach (var player in Enumerable.Range(1, 5))
                    manager.Join(fullId, Guid.NewGuid(), $"Quest3-{room}-{player}", room, HeadsetKind.Quest3, master);
            manager.Execute(fullId, new(Guid.NewGuid(), ControlAction.Begin), master);
            foreach (var player in manager.Get(fullId).Players)
            {
                var shots = Enumerable.Range(0, 3).Select(_ => Guid.NewGuid()).ToArray();
                var enemies = Enumerable.Range(0, 2).Select(_ => Guid.NewGuid()).ToArray();
                foreach (var shot in shots)
                    manager.ReportCombat(fullId, new(Guid.NewGuid(), CombatKind.ShotFired, CombatOrigin.Simulation, player.Id, shot), server);
                for (var index = 0; index < 2; index++)
                    manager.ReportCombat(fullId, new(Guid.NewGuid(), CombatKind.ShotHit, CombatOrigin.Simulation, player.Id, shots[index], enemies[index]), server);
                manager.ReportCombat(fullId, new(Guid.NewGuid(), CombatKind.EnemyEliminated, CombatOrigin.Simulation, player.Id, shots[0], enemies[0]), server);
                manager.ReportCombat(fullId, new(Guid.NewGuid(), CombatKind.PlayerDamaged, CombatOrigin.Simulation, player.Id, Damage: 20), server);
            }
            manager.End(fullId, master);
            var stats = manager.Statistics(fullId);
            check(stats.Players.Length == 25 && stats.Players.Sum(p => p.AmmoUsed) == 75 && stats.Players.Sum(p => p.ShotsHit) == 50
                && stats.Players.Sum(p => p.Kills) == 25 && stats.Players.Sum(p => p.DamageTaken) == 500,
                "Five-room 25-player simulated records aggregate without cross-player contamination");
            check(stats.ThroughSequence == 203 && stats.Players.All(p => p.Health == 80 && p.AccuracyPercent == 66.67m),
                "SQLite commits all 175 simulated combat reports alongside lifecycle and roster events");
        }
        using (var store = new SqliteSessionEventStore(fullVenue))
        {
            var recovered = new SessionManager(store);
            check(recovered.Statistics(fullId).Players.Length == 25 && recovered.Statistics(fullId).ThroughSequence == 203
                && recovered.Rooms().All(r => r.SessionId is null),
                "Full-venue simulated statistics and released rooms survive a store restart");
        }
    }

    private static void Execute(string database, string sql)
    {
        using var connection = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = database, Pooling = false }.ToString());
        connection.Open();
        using var command = connection.CreateCommand();
        command.CommandText = sql;
        command.ExecuteNonQuery();
    }
}
