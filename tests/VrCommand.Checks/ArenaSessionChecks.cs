using System.Text.Json;
using VrCommand.Core;
using VrCommand.Simulation;

internal static class ArenaSessionChecks
{
    internal static void Run(Action<bool, string> check, string directory)
    {
        void Reject<T>(Action action, string message) where T : Exception
        {
            try { action(); } catch (T) { check(true, message); return; }
            throw new Exception("Expected " + typeof(T).Name + ": " + message);
        }
        var store = new MissionStore(Path.Combine(directory, "arena-adapter"));
        var mission = store.Create(new("Combat adapter", "No headset attached", 900,
            new(ExperienceMode.VR, Weather.Clear, TimeOfDay.Day, false), new(1, EnemyBehavior.Hold, false),
            [new("barrel", new(0, 0, 0), 0), new("sandbag", new(2, 0, 2), 45)]));
        var manager = new SessionManager();
        var managed = manager.Create(SessionMode.Independent, [3], mission);
        var player = Guid.NewGuid(); manager.Join(managed.Id, player, "Alpha", 3, HeadsetKind.Quest3);
        ManagementSnapshot Snapshot() => JsonSerializer.Deserialize<ManagementSnapshot>(JsonSerializer.Serialize(manager.Get(managed.Id), JsonFormat.Options),
            new JsonSerializerOptions(JsonFormat.Options) { IncludeFields = true })!;
        var admission = manager.Get(managed.Id).Players.Single().AdmissionId;
        var adapter = new ArenaSession(); adapter.Apply(Snapshot());
        check(adapter.World.Snapshot().Players.Single().Id == player && !adapter.World.Snapshot().Players.Single().Connected,
            "Real management JSON creates the admitted roster as inactive bodies until an authenticated connection sends pose");
        check(adapter.Props.Length == 2 && adapter.Props[0].Kind == PropKind.Barrel && adapter.Props[1].Yaw == 45
            && adapter.Props[1].HalfSize.Equals(new Vec3(1, .45f, .35f)),
            "Mission placements use the exact shared collision geometry and rotation");
        Reject<ArgumentException>(() => adapter.Apply(new()), "Incomplete management snapshot cannot create a playable world");
        var invalid = Snapshot(); invalid.environment.mode = "MR";
        Reject<ArgumentException>(() => adapter.Apply(invalid), "Unsupported MR mode is rejected instead of pretending to calibrate a venue");
        invalid = Snapshot(); invalid.mission.definition.props[0].assetId = "unknown";
        Reject<ArgumentException>(() => adapter.Apply(invalid), "Unknown assets cannot silently acquire arbitrary collision shapes");
        check(adapter.Connect(17, player, 3, 0, admission), "Validated ticket identity binds its exact room and seat to a transport connection");
        check(!adapter.Connect(18, player, 3, 0, admission) && !adapter.Connect(18, Guid.NewGuid(), 3, 0, admission) && !adapter.Connect(18, player, 2, 0, admission),
            "Duplicate, unknown and cross-room admission bindings are rejected");
        var head = ArenaSession.Spawn(3, 0);
        var target = adapter.World.Snapshot().Enemies[0].Feet + new Vec3(0, .9f, 0);
        var forward = (target - head).Normalized();
        check(!adapter.Pose(99, head, head, forward, 0) && adapter.Pose(17, head, head, forward, 0),
            "Pose cannot select a player ID and requires a bound transport identity");
        check(!adapter.Weapon(17, 1, false, 0), "Preparing cannot fire even with a valid tracked pose");
        manager.Execute(managed.Id, new(Guid.NewGuid(), ControlAction.Begin)); adapter.Apply(Snapshot());
        check(adapter.Weapon(17, 1, false, 0) && adapter.World.Snapshot().Enemies[0].Health == 50,
            "Bound weapon input reaches the real geometric hit test and authoritative enemy health");
        check(!adapter.Weapon(17, 1, false, 0) && adapter.World.Snapshot().Players.Single().Magazine == 29,
            "Repeated owner input cannot consume another round");
        check(!adapter.Weapon(17, 2, false, 0), "Shared weapon cooldown rejects excessive input frequency");
        var now = 0d;
        for (var i = 0; i < 4; i++) { now += .05; adapter.Tick(now); }
        check(adapter.Weapon(17, 3, false, now) && adapter.World.Snapshot().Enemies[0].Health == 0,
            "Subsequent accepted shot eliminates through the same server collision core");
        check(adapter.World.Events().Count(entry => entry.Kind == WorldEventKind.EnemyEliminated) == 1,
            "Combat adapter emits one causal elimination for later telemetry integration");
        check(!adapter.Pose(17, head + new Vec3(4, 0, 0), head, forward, now) && !adapter.Pose(17, head, head, forward, double.NaN),
            "Impossible displacement and non-finite receipt time cannot enter combat state");
        adapter.Suspend(); var tick = adapter.World.TickNumber; adapter.Tick(now + .1);
        check(adapter.World.TickNumber == tick && !adapter.Weapon(17, 4, false, now), "Management loss suspension freezes combat ticks and input");
        adapter.Apply(Snapshot());
        check(adapter.World.Phase == WorldPhase.Running, "A fresh unchanged management snapshot can resume a suspended world");
        adapter.Disconnect(17); var ammunition = adapter.World.Snapshot().Players.Single().Magazine;
        check(!adapter.World.Snapshot().Players.Single().Connected && !adapter.Weapon(17, 4, false, now),
            "Disconnected owner loses firing and collision participation without deleting its weapon state");
        check(adapter.Connect(19, player, 3, 0, admission) && adapter.Pose(19, head, head, forward, now), "Reconnect rebinds the retained roster body without a respawn");
        for (var i = 0; i < 4; i++) { now += .05; adapter.Tick(now); }
        check(adapter.Weapon(19, 1, false, now) && adapter.World.Snapshot().Players.Single().Magazine == ammunition - 1,
            "New connection input sequence cannot collide with the previous connection's shot IDs");
        adapter.Disconnect(17); adapter.Tick(now);
        check(adapter.World.Snapshot().Players.Single().Connected, "Late old disconnect callback cannot deactivate the replacement connection");
        adapter.Tick(now + 1);
        check(!adapter.World.Snapshot().Players.Single().Connected && !adapter.Weapon(19, 2, false, now + 1),
            "Stale tracking removes combat participation until a new valid pose arrives");
        now += 1;
        check(adapter.Pose(19, head, head, forward, now), "Tracking can recover without resetting ammunition or health");
        manager.Leave(managed.Id, player); adapter.Apply(Snapshot());
        check(!adapter.Weapon(19, 3, false, now) && !adapter.Connect(20, player, 3, 0, admission),
            "Roster revocation removes the bound owner and prevents readmission to combat");
        manager.End(managed.Id); adapter.Apply(Snapshot());
        check(adapter.World.Phase == WorldPhase.Ended && !adapter.Connect(20, player, 3, 0, admission), "Ended management state ends the combat world permanently");
        var late = new ArenaSession();
        Reject<InvalidOperationException>(() => late.Apply(Snapshot()), "Server cannot invent a fresh combat world for an already ended mission");

        var allManager = new SessionManager();
        var all = allManager.Create(SessionMode.Linked, [1, 2, 3, 4, 5], mission);
        for (var room = 1; room <= 5; room++) for (var seat = 0; seat < 5; seat++) allManager.Join(all.Id, Guid.NewGuid(), "Player", room, HeadsetKind.Quest3);
        ManagementSnapshot AllSnapshot() => JsonSerializer.Deserialize<ManagementSnapshot>(JsonSerializer.Serialize(allManager.Get(all.Id), JsonFormat.Options),
            new JsonSerializerOptions(JsonFormat.Options) { IncludeFields = true })!;
        var five = new ArenaSession(); var allSnapshot = AllSnapshot(); allSnapshot.enemies.count = 10; five.Apply(allSnapshot);
        check(five.World.Snapshot().Players.Length == 25 && five.Props.Length == 10 && five.World.Snapshot().Enemies.Length == 10
            && five.World.Snapshot().Enemies.GroupBy(enemy => enemy.RoomId).All(group => group.Count() == 2),
            "Five-room mission maps 25 seats, per-room props and a shared total enemy count");
        var originalProps = five.Props.Select(prop => prop.Id).ToArray(); five.Apply(allSnapshot);
        check(five.Props.Select(prop => prop.Id).SequenceEqual(originalProps), "Repeated management refresh keeps stable world prop identity");
        allSnapshot.enemies.count = 2; allSnapshot.sequence++; five.Apply(allSnapshot);
        var previousEnemyIds = five.World.Snapshot().Enemies.Select(enemy => enemy.Id).ToArray();
        allSnapshot.enemies.count = 5; allSnapshot.sequence++; five.Apply(allSnapshot);
        check(five.World.Snapshot().Enemies.Length == 5 && five.World.Snapshot().Enemies.Select(enemy => enemy.Id).Distinct().Count() == 5
            && five.World.Snapshot().Enemies.Take(2).Select(enemy => enemy.Id).SequenceEqual(previousEnemyIds),
            "Operator enemy count changes retain surviving lives and use new IDs for added enemies");
        invalid = AllSnapshot(); invalid.sequence = allSnapshot.sequence - 1;
        Reject<InvalidOperationException>(() => five.Apply(invalid), "Stale management refresh cannot rewind a live authority");
        var emptyMission = store.Create(mission.Definition with { Props = [], Enemies = new(100, EnemyBehavior.Patrol, false) });
        var capacity = new SessionManager(); var crowded = capacity.Create(SessionMode.Independent, [1], emptyMission);
        var maximum = JsonSerializer.Deserialize<ManagementSnapshot>(JsonSerializer.Serialize(capacity.Get(crowded.Id), JsonFormat.Options),
            new JsonSerializerOptions(JsonFormat.Options) { IncludeFields = true })!;
        var full = new ArenaSession(); full.Apply(maximum);
        check(full.World.Snapshot().Enemies.Length == 100, "Open arena supports the configured 100-enemy input ceiling without overlapping spawn centers");
        maximum.mission.definition.props = [new() { assetId = "barrel", position = new() { x = 0, z = 0 } }];
        var geometry = new ArenaSession(); geometry.Apply(maximum);
        var moving = maximum.players = [new() { id = Guid.NewGuid().ToString(), admissionId = Guid.NewGuid().ToString(), roomId = 1, seat = 2 }]; maximum.sequence++;
        geometry.Apply(maximum); var mover = Guid.Parse(moving[0].id); geometry.Connect(1, mover, 1, 2, Guid.Parse(moving[0].admissionId));
        var start = ArenaSession.Spawn(1, 2);
        check(!geometry.Pose(1, start + new Vec3(0, 0, 3), start, new(0, 0, 1), 0),
            "Transport pose cannot cross mission cover or teleport to it");
        var fresh = new ArenaSession(); var preparing = AllSnapshot(); preparing.state = "Running";
        Reject<InvalidOperationException>(() => fresh.Apply(preparing), "Server restart cannot silently reset a running mission's health and enemies");
        var presence = new ArenaWorld([3], []); var front = Guid.NewGuid(); var rear = Guid.NewGuid(); var npc = Guid.NewGuid();
        presence.AddPlayer(rear, 3, new(0, 1.4f, -3)); presence.AddPlayer(front, 3, new(0, 1.4f, 0));
        presence.AddEnemy(npc, 3, new(0, 0, 3), new(0, 0, 3)); presence.SetPhase(WorldPhase.Running);
        presence.SetPlayerConnected(front, false);
        check(presence.Fire(rear, Guid.NewGuid()).Hit == HitKind.Enemy, "Disconnected body no longer blocks another player's authoritative shot");
        Reject<InvalidOperationException>(() => presence.Fire(front, Guid.NewGuid()), "Inactive body cannot fire through a direct core call");
        presence.Tick();
        check(presence.PlayerSnapshot(rear).Health == 80 && presence.PlayerSnapshot(front).Health == 100,
            "AI ignores disconnected bodies and its ray reaches an active player behind them");
        presence.SetPlayerConnected(rear, false); for (var step = 0; step < 30; step++) presence.Tick();
        check(presence.PlayerSnapshot(rear).Health == 80, "Tracking loss prevents additional AI damage while keeping the previous health");
        presence.SetPlayerConnected(rear, true);
        check(presence.PlayerSnapshot(rear).Health == 80 && presence.PlayerSnapshot(rear).Magazine == 29,
            "Restoring participation retains damage and ammunition rather than respawning the player");
        var pending = new ArenaSession(); var pendingSnapshot = AllSnapshot(); pending.Apply(pendingSnapshot);
        var pendingId = Guid.Parse(pendingSnapshot.players[0].id);
        pending.Connect(55, pendingId, pendingSnapshot.players[0].roomId, pendingSnapshot.players[0].seat, Guid.Parse(pendingSnapshot.players[0].admissionId));
        pendingSnapshot.players = pendingSnapshot.players.Skip(1).ToArray(); pendingSnapshot.sequence++;
        pending.Apply(pendingSnapshot);
        check(pending.World.Snapshot().Players.Length == 24 && !pending.Weapon(55, 1, false, 0),
            "Preparing roster removal safely drops an existing binding while replacing the unstarted world");
        var skipped = new ArenaSession(); var skippedSnapshot = AllSnapshot(); skippedSnapshot.players = []; skipped.Apply(skippedSnapshot);
        skippedSnapshot.state = "Running"; skippedSnapshot.sequence += 3; skipped.Apply(skippedSnapshot); skipped.Tick(0);
        check(skipped.World.Phase == WorldPhase.Running && skipped.World.Snapshot().Players.Length == 0,
            "Management Begin followed by all departures between polls does not invent bodies or fail the world transition");
        var unstarted = new ArenaWorld([3], []);
        Reject<InvalidOperationException>(() => unstarted.SetPhase(WorldPhase.Running),
            "Direct simulation still requires a player before its first Begin");
    }
}
