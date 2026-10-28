using VrCommand.Simulation;

internal static class SimulationChecks
{
    internal static void Run(Action<bool, string> check)
    {
        void Reject<T>(Action action, string message) where T : Exception
        {
            try { action(); } catch (T) { check(true, message); return; }
            throw new Exception("Expected " + typeof(T).Name + ": " + message);
        }
        static void Step(ArenaWorld world, int ticks) { for (var i = 0; i < ticks; i++) world.Tick(); }
        static (ArenaWorld World, Guid Player, Guid Enemy) World(WorldProp[]? props = null, Vec3? enemyFeet = null, Vec3? playerHead = null)
        {
            var world = new ArenaWorld([3], props ?? []); var player = Guid.NewGuid(); var enemy = Guid.NewGuid();
            world.AddPlayer(player, 3, playerHead ?? new(0, 1.4f, -3));
            var feet = enemyFeet ?? new Vec3(0, 0, 3);
            world.AddEnemy(enemy, 3, feet, new(3, 0, feet.Z)); world.SetPolicy(AiBehavior.Hold, false, Visibility.Clear, false);
            world.SetPhase(WorldPhase.Running); return (world, player, enemy);
        }
        var forward = new Vec3(0, 0, 1);
        check(Math.Abs(new Vec3(2, 1, 3).Normalized().Length - 1) < .0001f, "Simulation normalizes finite ray directions");
        check(Math.Abs(ArenaGeometry.RayBox(new(0, 0, -3), forward, new(), new(1, 1, 1), 0, 10)!.Value - 2) < .0001f,
            "Ray/box intersection returns geometric first-contact distance");
        check(ArenaGeometry.RayBox(new(), forward, new(), new(1, 1, 1), 0, 10) == 0, "A muzzle inside cover cannot shoot through it");
        check(ArenaGeometry.RayBox(new(2, 0, -3), forward, new(), new(1, 1, 1), 0, 10) is null, "Parallel ray outside a slab misses");
        check(ArenaGeometry.RayBox(new(1, 0, -3), forward, new(), new(2, 1, .2f), 0, 10).HasValue
            && !ArenaGeometry.RayBox(new(1, 0, -3), forward, new(), new(2, 1, .2f), 90, 10).HasValue, "Yaw rotates cover geometry rather than only its display");
        check(ArenaGeometry.RayBox(new(0, 0, -3), forward, new(), new(1, 1, 1), 0, 1) is null, "Targets beyond weapon range do not intersect");
        Reject<ArgumentException>(() => ArenaGeometry.RayBox(new(), new(), new(), new(1, 1, 1), 0, 10), "Zero-length shot direction rejected");
        Reject<ArgumentException>(() => new ArenaWorld([1, 1, 2, 3, 4], []), "Simulation rejects repeated linked rooms");
        var cover = new WorldProp(Guid.NewGuid(), 3, PropKind.Barrel, new(), 0);
        var blocked = World([cover]);
        var muzzle = new Vec3(0, .6f, -3);
        blocked.World.SetPlayerPose(blocked.Player, new(0, 1.4f, -3), muzzle, (new Vec3(0, .9f, 3) - muzzle).Normalized());
        var first = blocked.World.Fire(blocked.Player, Guid.NewGuid());
        var ray = blocked.World.Events()[0];
        check(ray.Hit == HitKind.Cover && ray.TargetId == cover.Id && ray.Origin?.Y == .6f && ray.Distance > 2 && ray.Distance < 4 && Math.Abs(ray.Direction!.Value.Length - 1) < .0001f,
            "Recorded shot preserves its authoritative muzzle, direction, collision distance and cover identity");
        check(first.Hit == HitKind.Cover && blocked.World.Snapshot().Enemies[0].Health == 100 && blocked.World.Events().Length == 1,
            "Barrel blocks a low shot before the enemy and emits only ammunition consumption");
        Reject<ArgumentException>(() => blocked.World.SetPlayerPose(blocked.Player, new(0, 1.4f, 3), new(0, 1.4f, 3), forward), "Player pose cannot teleport across solid cover");
        Reject<ArgumentException>(() => blocked.World.SetPlayerPose(blocked.Player, new(float.NaN, 1, -3), muzzle, forward), "Non-finite player tracking input rejected");
        Reject<ArgumentException>(() => blocked.World.SetPlayerPose(blocked.Player, new(0, 1.4f, -3), new(5, 1, -3), forward), "Remote muzzle cannot be detached from the tracked head");
        var shooting = World();
        shooting.World.SetPlayerPose(shooting.Player, new(0, 1.4f, -3), new(0, 1.4f, -3), (new Vec3(0, .9f, 3) - new Vec3(0, 1.4f, -3)).Normalized());
        var shotId = Guid.NewGuid(); var hit = shooting.World.Fire(shooting.Player, shotId);
        check(hit.Hit == HitKind.Enemy && !hit.Eliminated && shooting.World.Snapshot().Enemies[0].Health == 50, "Server raycast determines a 50-point enemy hit");
        check(shooting.World.Fire(shooting.Player, shotId) == hit && shooting.World.Snapshot().Players[0].Magazine == 29,
            "Repeated shot ID returns its frozen result without consuming ammunition twice");
        Reject<InvalidOperationException>(() => shooting.World.Fire(Guid.NewGuid(), shotId), "Another player cannot reuse a shot identity");
        Reject<InvalidOperationException>(() => shooting.World.Fire(shooting.Player, Guid.NewGuid()), "Weapon rate limit rejects a second shot in the same tick");
        shooting.World.SetPhase(WorldPhase.Paused); var frozen = shooting.World.Snapshot(); Step(shooting.World, 100);
        check(shooting.World.TickNumber == frozen.Tick && shooting.World.Fire(shooting.Player, shotId) == hit, "Pause freezes simulation time while accepted shot retries remain available");
        Reject<InvalidOperationException>(() => shooting.World.Fire(shooting.Player, Guid.NewGuid()), "Paused world cannot accept a new shot");
        shooting.World.SetPhase(WorldPhase.Running); Step(shooting.World, 4);
        var kill = shooting.World.Fire(shooting.Player, Guid.NewGuid());
        check(kill.Eliminated && shooting.World.Events().Count(e => e.Kind == WorldEventKind.ShotHit) == 2
            && shooting.World.Events().Count(e => e.Kind == WorldEventKind.EnemyEliminated) == 1, "Two geometric hits produce exactly one enemy elimination");
        shooting.World.Snapshot().Enemies[0] = null!;
        check(shooting.World.Snapshot().Enemies[0].Health == 0, "Mutating a returned world array does not change the simulation");
        Step(shooting.World, 4); var miss = shooting.World.Fire(shooting.Player, Guid.NewGuid());
        check(miss.Hit == HitKind.Miss, "Dead enemies do not absorb or score subsequent bullets");
        var reloadId = Guid.NewGuid(); shooting.World.Reload(shooting.Player, reloadId); shooting.World.Reload(shooting.Player, reloadId);
        Reject<InvalidOperationException>(() => shooting.World.Fire(shooting.Player, Guid.NewGuid()), "Reloading blocks firing");
        Step(shooting.World, 29); check(shooting.World.Snapshot().Players[0].Reloading, "Reload does not complete before 30 running ticks");
        Step(shooting.World, 1); var reloaded = shooting.World.Snapshot().Players[0];
        check(reloaded.Magazine == 30 && reloaded.Reserve == 87 && !reloaded.Reloading, "Reload transfers only missing rounds from a finite reserve");
        shooting.World.Reload(shooting.Player, reloadId);
        check(shooting.World.Events().Count(e => e.Kind == WorldEventKind.ReloadStarted) == 1, "Delayed reload retry cannot start a second reload");
        shooting.World.SetPhase(WorldPhase.Ended);
        Reject<InvalidOperationException>(() => shooting.World.SetPhase(WorldPhase.Running), "Ended simulation cannot restart");
        check(shooting.World.Fire(shooting.Player, shotId) == hit, "Archived simulation still recognizes accepted shot retries");
        var ammo = World();
        for (var i = 0; i < 120; i++)
        {
            if (ammo.World.Snapshot().Players[0].Magazine == 0) { ammo.World.Reload(ammo.Player, Guid.NewGuid()); Step(ammo.World, 30); }
            ammo.World.Fire(ammo.Player, Guid.NewGuid()); Step(ammo.World, 4);
        }
        check(ammo.World.Snapshot().Players[0].Reserve == 0 && ammo.World.Snapshot().Players[0].Magazine == 0, "Repeated firing and reload cannot manufacture ammunition");
        Reject<InvalidOperationException>(() => ammo.World.Fire(ammo.Player, Guid.NewGuid()), "Empty magazine rejects firing");
        Reject<InvalidOperationException>(() => ammo.World.Reload(ammo.Player, Guid.NewGuid()), "Empty reserve rejects reloading");
        var friends = new ArenaWorld([3], []); var shooter = Guid.NewGuid(); var friendly = Guid.NewGuid(); var behind = Guid.NewGuid();
        friends.AddPlayer(shooter, 3, new(0, 1.4f, -3)); friends.AddPlayer(friendly, 3, new(0, 1.4f, 0));
        friends.AddEnemy(behind, 3, new(0, 0, 3), new(2, 0, 3)); friends.SetPolicy(AiBehavior.Hold, false, Visibility.Clear, false); friends.SetPhase(WorldPhase.Running);
        check(friends.Fire(shooter, Guid.NewGuid()).Hit == HitKind.Friendly && friends.Snapshot().Enemies[0].Health == 100 && friends.Snapshot().Players[1].Health == 100,
            "Nearest teammate stops a player bullet without friendly-fire damage or enemy credit");
        var ai = World(); ai.World.SetPolicy(AiBehavior.Hold, true, Visibility.Clear, false); ai.World.Tick();
        check(ai.World.Snapshot().Players[0].Health == 80 && ai.World.Events().Count(e => e.Kind == WorldEventKind.PlayerDamaged) == 1,
            "AI with clear line of sight generates actual player damage");
        Step(ai.World, 19); check(ai.World.Snapshot().Players[0].Health == 80, "AI cooldown prevents repeated damage each frame");
        ai.World.Tick(); check(ai.World.Snapshot().Players[0].Health == 60, "AI attack becomes available after its one-second tick cooldown");
        Step(ai.World, 200); check(ai.World.Snapshot().Players[0].Health == 0 && ai.World.Events().Count(e => e.Kind == WorldEventKind.PlayerDamaged) == 5,
            "AI stops damaging a dead player and does not inflate hit count");
        Reject<InvalidOperationException>(() => ai.World.Fire(ai.Player, Guid.NewGuid()), "Dead player cannot fire");
        var hidden = World([cover], playerHead: new(0, .6f, -3)); hidden.World.SetPolicy(AiBehavior.Hold, true, Visibility.Clear, false); Step(hidden.World, 50);
        check(hidden.World.Snapshot().Players[0].Health == 100, "Cover prevents AI firing at a crouched player");
        var fog = World(enemyFeet: new(0, 0, 5), playerHead: new(0, 1.4f, -5)); fog.World.SetPolicy(AiBehavior.Hold, true, Visibility.Fog, false); Step(fog.World, 25);
        check(fog.World.Snapshot().Visibility == Visibility.Fog && fog.World.Snapshot().AutoAttack && fog.World.Snapshot().Behavior == AiBehavior.Hold && !fog.World.Snapshot().Night,
            "World snapshots preserve the active visibility and AI policy for playback");
        check(fog.World.Snapshot().Players[0].Health == 100, "Fog reduces AI engagement range");
        fog.World.SetPolicy(AiBehavior.Hold, true, Visibility.Clear, true); fog.World.Tick();
        check(fog.World.Snapshot().Players[0].Health == 100, "Night reduces AI engagement range");
        fog.World.SetPolicy(AiBehavior.Hold, true, Visibility.Clear, false); fog.World.Tick();
        check(fog.World.Snapshot().Players[0].Health == 80, "Operator visibility changes affect the running AI policy");
        fog.World.SetPolicy(AiBehavior.Hold, false, Visibility.Clear, false); Step(fog.World, 100);
        check(fog.World.Snapshot().Players[0].Health == 80, "Operator can disable automatic attacks without removing enemies");
        var patrol = World([cover], new(-3, 0, 0), new(-4, 1.4f, -4));
        // The World helper sets a patrol endpoint at (3, 0, 0), across the cover.
        patrol.World.SetPolicy(AiBehavior.Patrol, false, Visibility.Clear, false);
        var movedAround = false; var reachedRight = false; var validMovement = true; var previous = patrol.World.Snapshot().Enemies[0].Feet;
        for (var i = 0; i < 160; i++)
        {
            patrol.World.Tick(); var feet = patrol.World.Snapshot().Enemies[0].Feet;
            movedAround |= Math.Abs(feet.Z) >= .9f; reachedRight |= feet.X >= 2.8f;
            validMovement &= Vec3.Distance(previous, feet) <= .1001f && !(Math.Abs(feet.X) <= .65f && Math.Abs(feet.Z) <= .65f); previous = feet;
        }
        check(movedAround && reachedRight && validMovement, "Grid patrol routes around cover with bounded movement instead of walking through it");
        patrol.World.SetPolicy(AiBehavior.Hold, false, Visibility.Clear, false); var held = patrol.World.Snapshot().Enemies[0].Feet; Step(patrol.World, 30);
        check(Vec3.Distance(held, patrol.World.Snapshot().Enemies[0].Feet) == 0, "Operator Hold override stops a moving patrol");
        var wall = Enumerable.Range(-5, 11).Select(x => new WorldProp(Guid.NewGuid(), 3, PropKind.Sandbag, new(x, 0, 0), 0)).ToArray();
        var unreachable = World(wall, new(0, 0, -3), new(-4, 1.4f, -4));
        unreachable.World.RemoveEnemy(unreachable.Enemy); var trapped = Guid.NewGuid(); unreachable.World.AddEnemy(trapped, 3, new(0, 0, -3), new(0, 0, 3));
        unreachable.World.SetPolicy(AiBehavior.Patrol, false, Visibility.Clear, false); Step(unreachable.World, 100);
        check(Vec3.Distance(unreachable.World.Snapshot().Enemies[0].Feet, new(0, 0, -3)) == 0, "Unreachable patrol destination does not teleport through a complete wall");
        Reject<ArgumentException>(() => unreachable.World.AddEnemy(unreachable.Enemy, 3, new(2, 0, 3), new(3, 0, 3)), "Removed enemy identity cannot be reused for another life");
        var advance = World(enemyFeet: new(0, 0, 4)); advance.World.SetPolicy(AiBehavior.Advance, false, Visibility.Clear, false); Step(advance.World, 20);
        check(advance.World.Snapshot().Enemies[0].Feet.Z < 3, "Advance behavior pursues the nearest live player in its room");
        var linked = new ArenaWorld([1, 2, 3, 4, 5], []);
        foreach (var room in Enumerable.Range(1, 5)) foreach (var seat in Enumerable.Range(0, 5)) linked.AddPlayer(Guid.NewGuid(), room, ArenaWorld.RoomOrigin(room) + new Vec3((seat - 2) * 1.5f, 1.4f, -3));
        check(linked.Snapshot().Players.Length == 25, "Shared simulation admits five rooms and 25 roster bodies");
        Reject<InvalidOperationException>(() => linked.AddPlayer(Guid.NewGuid(), 1, ArenaWorld.RoomOrigin(1) + new Vec3(0, 1.4f, -5)), "Simulation rejects a sixth player in one room");
        linked.SetPolicy(AiBehavior.Hold, true, Visibility.Clear, false);
        foreach (var room in Enumerable.Range(1, 5)) linked.AddEnemy(Guid.NewGuid(), room, ArenaWorld.RoomOrigin(room) + new Vec3(0, 0, 3), ArenaWorld.RoomOrigin(room) + new Vec3(2, 0, 3));
        linked.SetPhase(WorldPhase.Running); linked.Tick();
        check(linked.Events().Count(e => e.Kind == WorldEventKind.PlayerDamaged) == 5 && linked.Snapshot().Players.Count(p => p.Health == 80) == 5,
            "Five-room headless AI updates damage one visible player in each room");
        var page = linked.Events(1, 2);
        check(linked.Snapshot().ThroughSequence == linked.Events().Last().Sequence && linked.Snapshot().Players.All(p => p.Muzzle.Finite && p.Forward.Finite),
            "World snapshots identify their event boundary and authoritative weapon pose");
        check(page.Length == 2 && page[0].Sequence == 2 && linked.Events().Select(e => e.EventId).Distinct().Count() == linked.Events().Length,
            "Simulation events have unique stable IDs and exclusive sequence paging");
    }
}
