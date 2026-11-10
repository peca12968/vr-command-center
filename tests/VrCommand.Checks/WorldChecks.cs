using System.Text.Json;
using Microsoft.Data.Sqlite;
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
        var header = WorldRecordingHeader.Create(id, queue.StreamId, "Simulation", [1], bridge.Props, assetSet: WorldAssetSets.PlayerFire, enemyPresentationVersion: 1, weaponPresentationVersion: 1, enemyFireVersion: 1, playerFireVersion: 1, combatAudioVersion: 1);
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
        var silentRetry=Copy(header);silentRetry.combatAudioVersion=0;
        Reject<InvalidOperationException>(()=>store.Open(id,silentRetry,owner),"Accepted audio policy cannot be silently removed from an immutable recording");
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
        var initial = WorldRecordingPacket.Capture(bridge.World, 1, 0, manager.Get(id).Sequence, 0, 0, Rig, enemyPresentationVersion: 1, weaponPresentationVersion: 1, enemyFireVersion: 1, playerFireVersion: 1);
        check(store.Append(id, initial, owner).AcceptedSequence == 1 && store.Append(id, Copy(initial), owner).AcceptedSequence == 1, "Initial preparing frame is persisted once");
        check(store.Info(id, master).Header.assetSet == WorldAssetSets.PlayerFire && store.Info(id, master).Header.enemyPresentationVersion == 1
            && store.Frame(id, 1, master)!.Packet.frame.enemies[0].hasPresentation, "SQLite records the humanoid profile and explicit initial enemy presentation together");
        check(store.Frame(id,1,master)!.Packet.frame.players[0].hasWeaponPresentation && store.Info(id,master).Header.weaponPresentationVersion==1,"SQLite retains the new action profile and explicit player action clock");
        var initialBad = Copy(initial); initialBad.elapsedMilliseconds = 1;
        Reject<InvalidOperationException>(() => store.Append(id, initialBad, owner), "Accepted frame cannot be changed by a retry");
        manager.Execute(id, new(Guid.NewGuid(), ControlAction.Begin), master); Refresh();
        bridge.Connect(1, player, 1, 0, manager.Get(id).Players.Single().AdmissionId); var head = ArenaSession.Spawn(1, 0); var target = bridge.World.Snapshot().Enemies[0].Feet + new Vec3(0, .9f, 0);
        bridge.Pose(1, head, head, (target - head).Normalized(), 0); bridge.Weapon(1, 1, false, 0); bridge.Tick(.05);
        var observed = manager.Get(id).Sequence; queue.Capture(bridge.World, observed);
        var running = WorldRecordingPacket.Capture(bridge.World, 2, 50, observed, queue.LastSequence, 0, Rig, enemyPresentationVersion: 1, weaponPresentationVersion: 1, enemyFireVersion: 1, playerFireVersion: 1);
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
        var final = WorldRecordingPacket.Capture(bridge.World, 3, 100, manager.Get(id).Sequence, queue.LastSequence, bridge.World.EventSequence, Rig, enemyPresentationVersion: 1, weaponPresentationVersion: 1, enemyFireVersion: 1, playerFireVersion: 1);
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
        var savedPlayer=restarted.Frame(id,2,master)!.Packet.frame.players[0];var originalPlayer=running.frame.players[0];
        check(restarted.Info(id,master).Header.playerFireVersion==1 && savedPlayer.hasFireState && savedPlayer.fireSequence>0 && savedPlayer.fireSequence==originalPlayer.fireSequence
            && savedPlayer.fireOrigin.ToVector().Equals(originalPlayer.fireOrigin.ToVector()) && savedPlayer.fireDirection.ToVector().Equals(originalPlayer.fireDirection.ToVector()),"Reopened SQLite preserves the accepted player fire sequence and exact historical ray");
        check(restarted.Append(id, running, owner).Complete, "Reopened archive accepts an exact historical retry");

        var rooms = new[] { 1, 2, 3, 4, 5 };
        var linked = manager.Create(SessionMode.Linked, rooms, mission with { Definition = mission.Definition with { Enemies = new(2, EnemyBehavior.Hold, true) } }, master);
        var linkedPlayer = Guid.NewGuid();
        manager.Join(linked.Id, linkedPlayer, "Reinforcement player", 1, HeadsetKind.Quest3, master);
        var reinforcementStream = Guid.NewGuid();
        manager.OpenStream(linked.Id, new(reinforcementStream, CombatOrigin.Simulation), owner);
        var linkedBridge = new ArenaSession();
        ManagementSnapshot LinkedView() => JsonSerializer.Deserialize<ManagementSnapshot>(
            JsonSerializer.Serialize(manager.Get(linked.Id, owner), JsonFormat.Options),
            new JsonSerializerOptions(JsonFormat.Options) { IncludeFields = true })!;
        linkedBridge.Apply(LinkedView());
        var reinforcementHeader = WorldRecordingHeader.Create(linked.Id, reinforcementStream, "Simulation", rooms, linkedBridge.Props);
        reinforcementHeader.reinforcementVersion = 2;
        Reject<ArgumentException>(() => store.Open(linked.Id, reinforcementHeader, owner), "Unknown reinforcement recording version fails closed");
        reinforcementHeader.reinforcementVersion = WorldRecordingHeader.ReinforcementVersion;
        store.Open(linked.Id, reinforcementHeader, owner);
        var linkedInitial = WorldRecordingPacket.Capture(linkedBridge.World, 1, 0, manager.Get(linked.Id).Sequence, 0, 0, _ => new());
        var missingInitial = Copy(linkedInitial); missingInitial.frame.enemies = [missingInitial.frame.enemies[0]];
        Reject<InvalidOperationException>(() => store.Append(linked.Id, missingInitial, owner), "Reinforcement recordings still require the full initial enemy roster");
        store.Append(linked.Id, linkedInitial, owner);
        manager.Execute(linked.Id, new(Guid.NewGuid(), ControlAction.Begin), master);
        linkedBridge.Apply(LinkedView());
        var partial = WorldRecordingPacket.Capture(linkedBridge.World, 2, 100, manager.Get(linked.Id).Sequence, 0, 0, _ => new());
        var wrongRoom = Copy(partial);
        wrongRoom.frame.enemies[1].roomId = 1;
        wrongRoom.frame.enemies[1].feet = wrongRoom.frame.enemies[0].feet;
        Reject<InvalidOperationException>(() => store.Append(linked.Id, wrongRoom, owner), "Reinforcements cannot exceed the target allocation in a single room");
        partial.frame.enemies = [partial.frame.enemies[0]];
        check(store.Append(linked.Id, partial, owner).AcceptedSequence == 2
            && store.Frame(linked.Id, 2, master)!.Packet.frame.enemies.Length == 1,
            "A blocked reinforcement remains absent from the saved and replayed world");
        var linkedObserved = manager.Get(linked.Id).Sequence;
        long combatSequence = 0;
        var firstShot = Guid.NewGuid(); var secondShot = Guid.NewGuid();
        var enemy = Guid.Parse(partial.frame.enemies[0].id);
        RecordedEvent Report(CombatKind kind, Guid? shot = null, Guid? target = null, int damage = 0)
        {
            var report = new CombatReport(Guid.NewGuid(), kind, CombatOrigin.Simulation, linkedPlayer, shot,
                kind == CombatKind.PlayerDamaged ? null : target, damage);
            manager.ReportStream(linked.Id, new(reinforcementStream, ++combatSequence, linkedObserved, report), owner);
            return new() { sequence = combatSequence, tick = partial.frame.tick, kind = kind.ToString(), eventId = report.ReportId.ToString("D"),
                playerId = linkedPlayer.ToString("D"), shotId = shot?.ToString("D") ?? "", enemyId = target?.ToString("D") ?? "", damage = damage,
                hasRay = kind == CombatKind.ShotFired, direction = new(new Vec3(0, 0, 1)), hit = kind == CombatKind.ShotFired ? "Miss" : "" };
        }
        void SaveCombat(long frameNumber, int ammo, int health, params RecordedEvent[] events)
        {
            var packet = Copy(partial); packet.sequence = frameNumber; packet.elapsedMilliseconds = frameNumber * 50;
            packet.events = events; packet.throughCombatSequence = packet.frame.throughSequence = combatSequence;
            packet.frame.players[0].magazine -= ammo; packet.frame.players[0].health = health;
            store.Append(linked.Id, packet, owner);
        }
        SaveCombat(3, 1, 100, Report(CombatKind.ShotFired, firstShot));
        SaveCombat(4, 2, 80, Report(CombatKind.ShotHit, firstShot, enemy), Report(CombatKind.ShotFired, secondShot),
            Report(CombatKind.ShotHit, secondShot, enemy), Report(CombatKind.EnemyEliminated, secondShot, enemy),
            Report(CombatKind.PlayerDamaged, target: enemy, damage: 20));
        var interval = store.ClipStatistics(linked.Id, 4, 4, 1, linkedPlayer, master, default);
        check(interval.Players.Single() is { AmmoUsed: 1, ShotsHit: 2, MatchedShots: 1, AccuracyPercent: 100, Kills: 1, HitsReceived: 1, DamageTaken: 20 }
            && store.ClipStatistics(linked.Id, 3, 4, 1, linkedPlayer, master, default).Players.Single() is { AmmoUsed: 2, MatchedShots: 2 },
            "Inclusive clip statistics count durable combat but exclude pre-range shots from clip accuracy");
        check(store.ClipStatistics(linked.Id, 2, 2, null, null, master, default).Players.Length == 0
            && store.ClipStatistics(linked.Id, 3, 4, null, null, room2, default) is { RoomId: 2, Players.Length: 0 },
            "Clip statistics preserve empty frames and limit room operators to their own recorded events");
        Reject<AccessDeniedException>(() => store.ClipStatistics(linked.Id, 3, 4, 1, null, room2, default), "Clip statistics reject another room scope");
        var fired = store.Frame(linked.Id, 3, master)!.Packet.events.Single();
        var fireId = Guid.Parse(fired.eventId);
        var trace = store.ShotTrace(linked.Id, 3, 3, fireId, 1, master, default);
        check(trace.ShotId == firstShot && trace.ThroughFrame == 3
            && trace.Events.SequenceEqual([new(fireId, "ShotFired", 3, 150, 1)]),
            "Shot trace excludes already durable outcomes beyond the requested saved prefix");
        var hit = store.Frame(linked.Id, 4, master)!.Packet.events.First();
        var hitId = Guid.Parse(hit.eventId);
        check(store.ShotTrace(linked.Id, 4, 4, hitId, 1, master, default).Events.SequenceEqual(
            [new(fireId, "ShotFired", 3, 150, 1), new(hitId, "ShotHit", 4, 200, 1)]),
            "Tracing a saved hit finds the earlier original fire and never mixes a neighboring shot");
        var elimination = store.Frame(linked.Id, 4, master)!.Packet.events.Single(item => item.kind == "EnemyEliminated");
        check(store.ShotTrace(linked.Id, 4, 4, Guid.Parse(elimination.eventId), null, master, default) is { RoomId: null, Events.Length: 3 } killTrace
            && killTrace.ShotId == secondShot && killTrace.Events.All(row => row.FrameSequence == 4),
            "A saved elimination identifies its own three ordered records at the same frame");
        Reject<KeyNotFoundException>(() => store.ShotTrace(linked.Id, 3, 4, fireId, null, room2, default), "Shot trace conceals another room's anchor");
        Reject<AccessDeniedException>(() => store.ShotTrace(linked.Id, 3, 4, fireId, 1, room2, default), "Shot trace rejects another room scope");

        SaveCombat(5, 2, 0, Report(CombatKind.PlayerDamaged, target: enemy, damage: 30),
            Report(CombatKind.PlayerDamaged, target: enemy, damage: 90));
        var overkill = store.Frame(linked.Id, 5, master)!;
        var combatTotal = manager.Statistics(linked.Id, master).Players.Single();
        check(overkill.Statistics.Single() == combatTotal && combatTotal is { Health: 0, HitsReceived: 3, DamageTaken: 100 }
            && overkill.Packet.events.Select(item => item.damage).SequenceEqual([30, 90]),
            "Overkill keeps original hit values and applies only remaining health to world statistics");
        check(store.ClipStatistics(linked.Id, 5, 5, 1, linkedPlayer, master, default).Players.Single() is { HitsReceived: 2, DamageTaken: 80 }
            && store.ClipStatistics(linked.Id, 1, 5, null, null, master, default).Players.Single() is { HitsReceived: 3, DamageTaken: 100 },
            "Clip loss uses the health before the selected range, including multiple hits in one frame");

        using var legacyWorld = new SqliteConnection(new SqliteConnectionStringBuilder
            { DataSource = Path.Combine(worldDirectory, "worlds.db"), Pooling = false }.ToString());
        legacyWorld.Open();
        using var legacyFrame = legacyWorld.CreateCommand();
        legacyFrame.CommandText = "UPDATE world_frames SET statistics=$stats WHERE session=$session AND sequence=$frame";
        legacyFrame.Parameters.AddWithValue("$session", linked.Id.ToString("D"));
        legacyFrame.Parameters.AddWithValue("$frame", 5);
        var legacyStatistics = WorldJson.Write(new[] { combatTotal with { DamageTaken = 140 } });
        legacyFrame.Parameters.AddWithValue("$stats", legacyStatistics);
        check(legacyFrame.ExecuteNonQuery() == 1, "Compatibility fixture stores the original inflated projection separately from the combat packet");
        check(restarted.Frame(linked.Id, 5, master)!.Statistics.Single() == combatTotal
            && restarted.ClipStatistics(linked.Id, 5, 5, null, linkedPlayer, master, default).Players.Single().DamageTaken == 80,
            "An older saved frame and clip agree with accepted health without replacing its combat events");

        manager.End(linked.Id, master);
        var linkedFinal = Copy(overkill.Packet);
        linkedFinal.sequence = 6;
        linkedFinal.elapsedMilliseconds += 50;
        linkedFinal.observedSequence = manager.Get(linked.Id, owner).Sequence;
        linkedFinal.events = [];
        linkedFinal.frame.phase = "Ended";
        restarted.Append(linked.Id, linkedFinal, owner);
        manager.SealStream(linked.Id, new(reinforcementStream, combatSequence), owner);
        check(restarted.Frame(linked.Id, 6, master)!.Statistics.Single() == combatTotal,
            "Appending after a legacy frame carries forward the accepted loss");
        legacyFrame.Parameters["$frame"].Value = 6;
        check(legacyFrame.ExecuteNonQuery() == 1 && restarted.Seal(linked.Id, 6, owner).Complete,
            "A previously saved terminal projection can seal at the original combat boundary");
        legacyFrame.CommandText = "SELECT statistics FROM world_frames WHERE session=$session AND sequence=$frame";
        legacyFrame.Parameters.RemoveAt("$stats");
        check((string?)legacyFrame.ExecuteScalar() == legacyStatistics,
            "Reading and sealing an older projection does not rewrite its stored frame");
    }
}
