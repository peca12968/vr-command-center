using System.Text.Json;
using VrCommand.Api;
using VrCommand.Core;
using VrCommand.Simulation;

internal static class WorldChecks
{
    internal static void Run(Action<bool, string> check, string directory)
    {
        void Reject<T>(Action action, string message) where T : Exception
        { try { action(); } catch (T) { check(true, message); return; } throw new Exception("Expected " + typeof(T).Name + ": " + message); }
        static T Copy<T>(T source) => WorldJson.Read<T>(WorldJson.Write(source));
        var manager = new SessionManager(); var owner = new OperatorIdentity("world-server", OperatorRole.GameServer);
        var master = new OperatorIdentity("world-master", OperatorRole.Master); var room2 = new OperatorIdentity("room2", OperatorRole.RoomController, 2);
        var mission = new MissionStore(Path.Combine(directory, "world-missions")).Create(new("Recorded arena", "World checks", 900,
            new(ExperienceMode.VR, Weather.Clear, TimeOfDay.Day, false), new(1, EnemyBehavior.Hold, true), [new("sandbag", new(2, 0, 1), 10)]));
        var session = manager.Create(SessionMode.Independent, [1], mission, master); var id = session.Id; var player = Guid.NewGuid();
        manager.Join(id, player, "Recorded player", 1, HeadsetKind.Quest3, master);
        using var queue = TelemetryOutbox.OpenFile(Path.Combine(directory, "world-combat.journal"), id, "Simulation");
        manager.OpenStream(id, new(queue.StreamId, CombatOrigin.Simulation), owner);
        var bridge = new ArenaSession();
        void Refresh()
        {
            var json = JsonSerializer.Serialize(manager.Get(id, owner), JsonFormat.Options);
            bridge.Apply(JsonSerializer.Deserialize<ManagementSnapshot>(json, new JsonSerializerOptions(JsonFormat.Options) { IncludeFields = true })!);
        }
        Refresh();
        var header = WorldRecordingHeader.Create(id, queue.StreamId, "Simulation", [1], bridge.Props, assetSet: WorldAssetSets.CombatEffects, enemyPresentationVersion: 1, weaponPresentationVersion: 1, enemyFireVersion: 1);
        var field = Copy(header); field.assetSet = WorldAssetSets.FieldProps; WorldRecordingValidation.Header(field);
        check(WorldAssetSets.Supported(WorldAssetSets.ServiceRifle) && field.assetSet == WorldAssetSets.FieldProps, "New rifle and retained field-prop profiles are explicitly supported without changing the default");
        check(WorldRecordingHeader.Create(id, queue.StreamId, "Simulation", [1], bridge.Props).assetSet == WorldAssetSets.Legacy, "Existing recording producers retain their original primitive asset profile");
        WorldRecordingValidation.Header(header);
        var legacy = Copy(header); legacy.assetSet = WorldAssetSets.Legacy; WorldRecordingValidation.Header(legacy);
        check(true, "Legacy and versioned field-prop recording headers both remain readable");
        var worldDirectory = Path.Combine(directory, "world-database"); Directory.CreateDirectory(worldDirectory);
        using var store = new WorldRecordings(worldDirectory, manager);
        Reject<AccessDeniedException>(() => store.Open(id, header, master), "Operators cannot publish a world");
        Reject<AccessDeniedException>(() => store.Open(id, header, owner with { Id = "other-server" }), "Combat owner alone may publish its world");
        var wrong = Copy(header); wrong.origin = "GameServer";
        Reject<InvalidOperationException>(() => store.Open(id, wrong, owner), "World cannot relabel Simulation combat as GameServer");
        wrong = Copy(header); wrong.props[0].feet.x += 1;
        Reject<InvalidOperationException>(() => store.Open(id, wrong, owner), "Recorded cover must match canonical mission geometry");
        wrong = Copy(header); wrong.rulesVersion = "99";
        Reject<ArgumentException>(() => store.Open(id, wrong, owner), "Unknown recording rules fail closed");
        wrong = Copy(header); wrong.assetSet = "field-props-v99";
        Reject<ArgumentException>(() => store.Open(id, wrong, owner), "Unknown prop asset profiles fail closed");
        check(store.Open(id, header, owner).AcceptedSequence == 0 && store.Open(id, header, owner).AcceptedSequence == 0, "Immutable recording header is retryable");
        Reject<InvalidOperationException>(() => store.Open(id, legacy, owner), "An accepted recording cannot switch appearance profiles on retry");
        Reject<InvalidOperationException>(() => store.Open(id, field, owner), "A rifle recording cannot be silently downgraded to the old weapon appearance");
        var noPoseHeader = Copy(header); noPoseHeader.assetSet = WorldAssetSets.ServiceRifle; noPoseHeader.enemyPresentationVersion = 0;
        Reject<InvalidOperationException>(() => store.Open(id, noPoseHeader, owner), "Accepted humanoid recording cannot drop its saved pose policy on retry");
        Reject<AccessDeniedException>(() => store.Info(id, room2), "Archive metadata preserves room authorization");
        check(store.List(room2).Length == 0, "Scoped world list reveals no foreign archive");
        RecordedRig Rig(Guid value)
        {
            var body = bridge.World.PlayerSnapshot(value);
            return body.Connected ? new() { kind = "Simulated", left = new(body.Head + new Vec3(-.2f, -.3f, .2f)), right = new(body.Muzzle) } : new();
        }
        var initial = WorldRecordingPacket.Capture(bridge.World, 1, 0, manager.Get(id).Sequence, 0, 0, Rig, enemyPresentationVersion: 1, weaponPresentationVersion: 1, enemyFireVersion: 1);
        check(store.Append(id, initial, owner).AcceptedSequence == 1 && store.Append(id, Copy(initial), owner).AcceptedSequence == 1, "Initial preparing frame is persisted once");
        check(store.Info(id, master).Header.assetSet == WorldAssetSets.CombatEffects && store.Info(id, master).Header.enemyPresentationVersion == 1
            && store.Frame(id, 1, master)!.Packet.frame.enemies[0].hasPresentation, "SQLite records the humanoid profile and explicit initial enemy presentation together");
        check(store.Frame(id,1,master)!.Packet.frame.players[0].hasWeaponPresentation && store.Info(id,master).Header.weaponPresentationVersion==1,"SQLite retains the new action profile and explicit player action clock");
        var initialBad = Copy(initial); initialBad.elapsedMilliseconds = 1;
        Reject<InvalidOperationException>(() => store.Append(id, initialBad, owner), "Accepted frame cannot be changed by a retry");
        manager.Execute(id, new(Guid.NewGuid(), ControlAction.Begin), master); Refresh();
        bridge.Connect(1, player, 1, 0, manager.Get(id).Players.Single().AdmissionId); var head = ArenaSession.Spawn(1, 0); var target = bridge.World.Snapshot().Enemies[0].Feet + new Vec3(0, .9f, 0);
        bridge.Pose(1, head, head, (target - head).Normalized(), 0); bridge.Weapon(1, 1, false, 0); bridge.Tick(.05);
        var observed = manager.Get(id).Sequence; queue.Capture(bridge.World, observed);
        var running = WorldRecordingPacket.Capture(bridge.World, 2, 50, observed, queue.LastSequence, 0, Rig, enemyPresentationVersion: 1, weaponPresentationVersion: 1, enemyFireVersion: 1);
        Reject<InvalidOperationException>(() => store.Append(id, running, owner), "World frame waits for its matching durable combat reports");
        manager.ReportStreamBatch(id, JsonSerializer.Deserialize<StreamCombatRecord[]>(TelemetryOutbox.BatchJson(queue.PendingBatch()), JsonFormat.Options)!, owner);
        void Bad<T>(Action<WorldRecordingPacket> mutate, string message) where T : Exception
        { var value = Copy(running); mutate(value); Reject<T>(() => store.Append(id, value, owner), message); }
        Bad<ArgumentException>(value => value.sequence = 4, "World frame gaps are rejected");
        Bad<ArgumentException>(value => value.elapsedMilliseconds = -1, "World time cannot rewind");
        Bad<ArgumentException>(value => value.observedSequence = 999999, "World cannot refer to future management history");
        Bad<InvalidOperationException>(value => value.weather = "Storm", "World policy must match its observed management view");
        Bad<InvalidOperationException>(value => value.frame.players = [], "Recording cannot omit admitted bodies");
        Bad<InvalidOperationException>(value => value.frame.enemies = [], "Recording enemy count follows management");
        Bad<ArgumentException>(value => value.frame.players[0].head.x += 100, "Out-of-room recorded pose is rejected");
        Bad<ArgumentException>(value => value.frame.players[0].rig.leftRotation.w = 0, "Invalid tracked rotation is rejected");
        Bad<ArgumentException>(value => value.frame.players[0].rig.kind = "None", "Connected bodies require explicit rig provenance");
        Bad<InvalidOperationException>(value => value.frame.players[0].health = 99, "Frame health must match the accepted combat prefix");
        Bad<InvalidOperationException>(value => value.frame.players[0].magazine = 30, "Frame ammunition must match the accepted combat prefix");
        Bad<ArgumentException>(value => value.events[0].hit = "999", "Numeric or unknown hit kinds cannot bypass ray validation");
        Bad<ArgumentException>(value => value.events[0].direction.x = 100, "Recorded shot direction must be a finite unit ray");
        Bad<ArgumentException>(value => value.frame.enemies[0].forward.z = float.NaN, "Non-finite saved enemy facing never commits a world frame");
        Bad<ArgumentException>(value => value.frame.enemies[0].hasPresentation = false, "Versioned stream cannot omit an individual enemy pose");
        Bad<InvalidOperationException>(value => value.events[0].shotId = Guid.NewGuid().ToString("D"), "World cannot substitute a combat shot identity");
        Bad<ArgumentException>(value => value.throughCombatSequence++, "World event count and combat boundary must agree");
        check(store.Append(id, running, owner).AcceptedSequence == 2, "Validated world frame commits after its report prefix");
        check(store.Frame(id, 2, owner)!.Statistics.Single().AmmoUsed == 1, "Per-frame statistics are derived from witnessed events");
        Reject<InvalidOperationException>(() => store.Seal(id, 2, owner), "Running world cannot claim complete recording");
        Reject<AccessDeniedException>(() => manager.Observed(id, observed, room2), "Historical observation accessor is scoped");
        Reject<AccessDeniedException>(() => manager.CombatWitness(id, Guid.Parse(running.events[0].eventId), room2), "Combat witness accessor is scoped");
        manager.Execute(id, new(Guid.NewGuid(), ControlAction.End), master); Refresh();
        var final = WorldRecordingPacket.Capture(bridge.World, 3, 100, manager.Get(id).Sequence, queue.LastSequence, bridge.World.EventSequence, Rig, enemyPresentationVersion: 1, weaponPresentationVersion: 1, enemyFireVersion: 1);
        var duplicateEvent = Copy(final); duplicateEvent.frame.throughSequence++;
        duplicateEvent.events = [new() { sequence = duplicateEvent.frame.throughSequence, tick = final.frame.tick, eventId = running.events[0].eventId, kind = "ReloadStarted", playerId = player.ToString("D") }];
        duplicateEvent.frame.players[0].reloading=true; duplicateEvent.frame.players[0].reloadUntilTick=final.frame.tick+30; // Keep the new action witness valid before exercising the duplicate event transaction.
        Reject<InvalidOperationException>(() => store.Append(id, duplicateEvent, owner), "World event IDs are unique across frame transactions");
        check(store.Info(id, owner).AcceptedSequence == 2 && store.Frame(id, 3, owner) is null, "Rejected frame transaction leaves no row or cursor advancement");
        store.Append(id, final, owner);
        Reject<InvalidOperationException>(() => store.Seal(id, 3, owner), "Ended world still waits for the combat stream seal");
        manager.SealStream(id, new(queue.StreamId, queue.LastSequence), owner);
        check(store.Seal(id, 3, owner).Complete && store.Seal(id, 3, owner).Complete, "Final world and combat statistics seal idempotently together");
        check(store.Seek(id, 60, owner) == 2 && store.Seek(id, 9999, owner) == 3, "Indexed time seek chooses the last preceding frame");
        using var restarted = new WorldRecordings(worldDirectory, manager);
        check(restarted.Info(id, owner).Complete && restarted.Frame(id, 2, owner)!.Packet.events.Length == running.events.Length, "World database reopens without loading or losing the archive");
        var savedEnemy = restarted.Frame(id, 2, master)!.Packet.frame.enemies[0];
        check(savedEnemy.hasPresentation && savedEnemy.forward.ToVector().Equals(running.frame.enemies[0].forward.ToVector()) && savedEnemy.walking == running.frame.enemies[0].walking,
            "Reopened SQLite archive preserves exact enemy facing and stride mode for direct seeks");
        check(savedEnemy.hasFireState && savedEnemy.fireSequence>0 && savedEnemy.fireSequence==running.frame.enemies[0].fireSequence
            && savedEnemy.fireTickPlusOne==running.frame.enemies[0].fireTickPlusOne && savedEnemy.fireOrigin.ToVector().Equals(running.frame.enemies[0].fireOrigin.ToVector())
            && savedEnemy.fireDirection.ToVector().Equals(running.frame.enemies[0].fireDirection.ToVector()),"Reopened SQLite preserves a nonzero accepted enemy fire clock and exact historical ray");
        check(restarted.Append(id, running, owner).Complete, "Reopened archive accepts an exact historical retry");
    }
}
