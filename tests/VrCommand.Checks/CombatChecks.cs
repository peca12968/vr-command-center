using VrCommand.Core;

internal static class CombatChecks
{
    internal static void Run(Action<bool, string> check, Mission mission)
    {
        void Reject<T>(Action action, string message) where T : Exception
        {
            try { action(); }
            catch (T) { check(true, message); return; }
            throw new Exception($"Expected {typeof(T).Name}: {message}");
        }
        var store = new MemorySessionEventStore();
        var manager = new SessionManager(store);
        var server = new OperatorIdentity("game-server", OperatorRole.GameServer);
        var master = new OperatorIdentity("master", OperatorRole.Master);
        var room2 = new OperatorIdentity("room-2", OperatorRole.RoomController, 2);
        var id = manager.Create(SessionMode.Independent, [1], mission, master).Id;
        var alpha = Guid.NewGuid();
        var bravo = Guid.NewGuid();
        manager.Join(id, alpha, "Alpha", 1, HeadsetKind.Quest3, master);
        manager.Join(id, bravo, "Bravo", 1, HeadsetKind.ViveXr, master);
        CombatReport Make(CombatKind kind, Guid player, Guid? shot = null, Guid? enemy = null, int damage = 0) =>
            new(Guid.NewGuid(), kind, CombatOrigin.Simulation, player, shot, enemy, damage);
        CombatReceipt Report(CombatReport report) => manager.ReportCombat(id, report, server);
        var shot1 = Guid.NewGuid();
        var shot2 = Guid.NewGuid();
        var shot3 = Guid.NewGuid();
        var bravoShot = Guid.NewGuid();
        var enemy1 = Guid.NewGuid();
        var enemy2 = Guid.NewGuid();
        var fired = Make(CombatKind.ShotFired, alpha, shot1);
        Reject<InvalidOperationException>(() => Report(fired), "Combat cannot enter a preparing session");
        check(manager.Statistics(id).Players.All(p => p.AccuracyPercent == 0 && p.Health == 100)
            && manager.Statistics(id).Origin is null, "Joined players begin with zero statistics and full health");
        manager.Execute(id, new(Guid.NewGuid(), ControlAction.Begin), master);
        Reject<AccessDeniedException>(() => manager.ReportCombat(id, fired, master), "Master cannot fabricate combat-source reports");
        Reject<AccessDeniedException>(() => manager.ReportCombat(id, fired, room2), "Room controller cannot submit combat-source reports");
        Reject<AccessDeniedException>(() => manager.Statistics(id, room2), "Independent combat statistics obey room visibility");
        var first = Report(fired);
        Report(Make(CombatKind.ShotFired, alpha, shot2));
        Report(Make(CombatKind.ShotFired, alpha, shot3));
        Report(Make(CombatKind.ShotFired, bravo, bravoShot));
        Report(Make(CombatKind.ShotHit, alpha, shot1, enemy1));
        Report(Make(CombatKind.ShotHit, bravo, bravoShot, enemy1));
        Report(Make(CombatKind.EnemyEliminated, alpha, shot1, enemy1));
        Reject<InvalidOperationException>(() => Report(Make(CombatKind.EnemyEliminated, bravo, bravoShot, enemy1)),
            "One enemy cannot award a kill to two players");
        Report(Make(CombatKind.ShotHit, alpha, shot2, enemy2));
        Report(Make(CombatKind.PlayerDamaged, alpha, damage: 20));
        var statistic = manager.Statistics(id).Players.Single(p => p.PlayerId == alpha);
        check(statistic.AmmoUsed == 3 && statistic.ShotsHit == 2 && statistic.Kills == 1 && statistic.AccuracyPercent == 66.67m
            && statistic.HitsReceived == 1 && statistic.DamageTaken == 20 && statistic.Health == 80,
            "Ammo, confirmed-shot accuracy, kills, hits, health loss and remaining health agree");
        var sequence = manager.Get(id).Sequence;
        Parallel.For(0, 20, _ =>
        {
            var retry = Report(fired);
            if (!retry.Duplicate || retry.AppliedAtSequence != first.AppliedAtSequence) throw new Exception("Invalid retry receipt");
        });
        check(manager.Get(id).Sequence == sequence && manager.Statistics(id).Players.Single(p => p.PlayerId == alpha).AmmoUsed == 3,
            "Concurrent combat report retries do not inflate ammo or append duplicate events");
        Reject<InvalidOperationException>(() => Report(fired with { ShotId = Guid.NewGuid() }), "Report ID cannot be reused with another shot");
        Reject<InvalidOperationException>(() => Report(Make(CombatKind.ShotFired, alpha, shot1)), "Another report ID cannot count the same shot twice");
        Reject<InvalidOperationException>(() => Report(Make(CombatKind.ShotHit, alpha, Guid.NewGuid(), enemy2)), "Hit without a fired shot is rejected");
        Reject<InvalidOperationException>(() => Report(Make(CombatKind.ShotHit, bravo, shot3, enemy2)), "Player cannot claim another player's shot");
        Reject<InvalidOperationException>(() => Report(Make(CombatKind.ShotHit, alpha, shot1, enemy2)), "One shot cannot inflate accuracy with multiple scored hits");
        Reject<InvalidOperationException>(() => Report(Make(CombatKind.EnemyEliminated, alpha, shot3, enemy2)), "Kill without a confirmed matching hit is rejected");
        Reject<ArgumentException>(() => Report(Make(CombatKind.PlayerDamaged, Guid.NewGuid(), damage: 10)), "Unknown player is rejected");
        Reject<ArgumentException>(() => Report(Make(CombatKind.PlayerDamaged, alpha, damage: 0)), "Zero damage is rejected");
        Reject<ArgumentException>(() => Report(fired with { Origin = CombatOrigin.Unspecified }), "Combat origin must be explicit");
        Reject<InvalidOperationException>(() => Report(fired with { ReportId = Guid.NewGuid(), ShotId = Guid.NewGuid(), Origin = CombatOrigin.GameServer }),
            "Simulation and real-source reports cannot be mixed into one session");
        manager.Execute(id, new(Guid.NewGuid(), ControlAction.Pause), master);
        Reject<InvalidOperationException>(() => Report(Make(CombatKind.PlayerDamaged, alpha, damage: 10)), "Paused session rejects new combat");
        check(Report(fired).Duplicate, "Previously accepted combat may be retried while paused");
        manager.Execute(id, new(Guid.NewGuid(), ControlAction.Resume), master);
        manager.Leave(id, alpha, master);
        var enemy3 = Guid.NewGuid();
        Report(Make(CombatKind.ShotHit, alpha, shot3, enemy3));
        Report(Make(CombatKind.EnemyEliminated, alpha, shot3, enemy3));
        check(manager.Statistics(id).Players.Single(p => p.PlayerId == alpha).Kills == 2,
            "A previously fired projectile may resolve after its shooter leaves");
        Reject<InvalidOperationException>(() => Report(Make(CombatKind.ShotFired, alpha, Guid.NewGuid())), "Departed player cannot fire new shots");
        Report(Make(CombatKind.PlayerDamaged, bravo, damage: 30));
        Report(Make(CombatKind.PlayerDamaged, bravo, damage: 200));
        var bravoStats = manager.Statistics(id).Players.Single(p => p.PlayerId == bravo);
        check(bravoStats.Health == 0 && bravoStats.DamageTaken == 100 && bravoStats.HitsReceived == 2,
            "Overkill clamps health loss at zero while counting received hit events");
        Reject<InvalidOperationException>(() => Report(Make(CombatKind.ShotFired, bravo, Guid.NewGuid())), "Dead player cannot fire new shots");
        Reject<InvalidOperationException>(() => Report(Make(CombatKind.PlayerDamaged, bravo, damage: 1)), "Dead player cannot accumulate extra damage hits");
        manager.End(id, master);
        var archived = manager.Statistics(id);
        var restored = new SessionManager(store);
        check(restored.Statistics(id).Players.SequenceEqual(archived.Players) && restored.Statistics(id).Origin == CombatOrigin.Simulation,
            "Statistics including departed players rebuild from archived event history");
        check(restored.ReportCombat(id, fired, server).Duplicate, "Combat deduplication survives recovery and session end");
        Reject<InvalidOperationException>(() => restored.ReportCombat(id, Make(CombatKind.PlayerDamaged, alpha, damage: 10), server),
            "Ended session rejects new combat reports");
        archived.Players[0] = archived.Players[0] with { Kills = 999 };
        check(restored.Statistics(id).Players.All(p => p.Kills < 999), "Returned statistics cannot mutate internal counters");

        var failure = new FailingStore();
        var durable = new SessionManager(failure);
        var failedId = durable.Create(SessionMode.Independent, [1], mission).Id;
        durable.Join(failedId, alpha, "Alpha", 1, HeadsetKind.Quest3);
        durable.Execute(failedId, new(Guid.NewGuid(), ControlAction.Begin));
        var before = durable.Get(failedId).Sequence;
        failure.Fail = true;
        Reject<IOException>(() => durable.ReportCombat(failedId, fired, server), "Combat storage failure surfaces to the caller");
        check(durable.Get(failedId).Sequence == before && durable.Statistics(failedId).Players.Single().AmmoUsed == 0,
            "Uncommitted combat cannot change statistics");
        failure.Fail = false;
        check(!durable.ReportCombat(failedId, fired, server).Duplicate && durable.Statistics(failedId).Players.Single().AmmoUsed == 1,
            "Combat report can be retried after a failed transaction");
    }

    private sealed class FailingStore : ISessionEventStore
    {
        private readonly MemorySessionEventStore inner = new();
        public bool Fail { get; set; }
        public SessionEvent[][] Load() => inner.Load();
        public void Append(SessionEvent entry)
        {
            if (Fail) throw new IOException("Simulated commit failure.");
            inner.Append(entry);
        }
    }
}
