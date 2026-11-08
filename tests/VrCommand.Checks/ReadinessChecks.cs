using System.Text.Json;
using VrCommand.Api;
using VrCommand.Core;
using VrCommand.Simulation;

internal static class ReadinessChecks
{
    private sealed class Clock : TimeProvider { public DateTimeOffset Now; public override DateTimeOffset GetUtcNow() => Now; }
    internal static void Run(Action<bool, string> check, string directory)
    {
        var clock = new Clock { Now = DateTimeOffset.Parse("2026-10-31T08:00:00Z") };
        var manager = new SessionManager(); var master = new OperatorIdentity("readiness-master", OperatorRole.Master);
        var room = new OperatorIdentity("readiness-room", OperatorRole.RoomController, 1);
        var other = room with { RoomId = 2 }; var server = new OperatorIdentity("readiness-server", OperatorRole.GameServer);
        var mission = new MissionStore(Path.Combine(directory, "readiness-missions")).Create(new("Readiness", "Accepted snapshots", 60,
            new(ExperienceMode.VR, Weather.Clear, TimeOfDay.Day, false), new(0, EnemyBehavior.Hold, false), []));
        var id = manager.Create(SessionMode.Independent, [1], mission, master).Id; var player = Guid.NewGuid();
        manager.Join(id, player, "Player", 1, HeadsetKind.Quest3, master);
        var path = Path.Combine(directory, "readiness-worlds"); Directory.CreateDirectory(path);
        using var store = new WorldRecordings(path, manager, clock);
        void Denied(OperatorIdentity actor, string message)
        { try { store.Readiness(id, actor); } catch (AccessDeniedException) { check(true, message); return; } throw new Exception(message); }
        check(store.Readiness(id, room) is { SourceState: "NoRecording", WorldSequence: 0 } none && !none.Players.Single().CanParticipate,
            "Roster alone never claims an online or participating device");
        Denied(other, "Readiness rejects a foreign room before looking for its recording");
        Denied(server, "GameServer credentials cannot use the operator readiness endpoint");
        Denied(OperatorIdentity.Internal, "Readiness requires an explicit control-desk identity");
        var venue = store.ReadinessByRoom(master);
        check(venue.Length == 5 && venue[0] is { RoomId: 1, SessionId: var active, Registered: 1, SourceState: "NoRecording" } && active == id
            && venue.Skip(1).All(value => value is { SessionId: null, Registered: 0, SourceState: "Idle" }),
            "Master room readiness retains roster occupancy and distinguishes unused rooms from waiting for a world");
        check(store.ReadinessByRoom(other).Single() is { RoomId: 2, SessionId: null, SourceState: "Idle" },
            "A room controller receives only its own room even when another room has a player");
        var stream = Guid.NewGuid(); manager.OpenStream(id, new(stream, CombatOrigin.Simulation), server);
        var bridge = new ArenaSession();
        void Refresh() => bridge.Apply(JsonSerializer.Deserialize<ManagementSnapshot>(JsonSerializer.Serialize(manager.Get(id), JsonFormat.Options),
            new JsonSerializerOptions(JsonFormat.Options) { IncludeFields = true })!);
        Refresh(); var start = clock.Now;
        store.Open(id, WorldRecordingHeader.Create(id, stream, "Simulation", [1], bridge.Props, start.ToString("O")), server);
        check(store.Readiness(id, master).SourceState == "WaitingFrame", "Header registration is not a received world frame");
        long sequence = 0, after = 0;
        void Save(bool suspended = false)
        {
            RecordedRig Rig(Guid value)
            {
                var body = bridge.World.PlayerSnapshot(value);
                return body.Connected ? new() { kind = "Simulated", left = new(body.Head + new Vec3(-.2f, -.3f, .2f)), right = new(body.Muzzle) } : new();
            }
            var packet = WorldRecordingPacket.Capture(bridge.World, ++sequence, (sequence - 1) * 50, manager.Get(id).Sequence, 0, after, Rig);
            packet.suspended = suspended; after = bridge.World.EventSequence; store.Append(id, packet, server);
            clock.Now = start.AddMilliseconds(packet.elapsedMilliseconds);
        }
        Save();
        check(store.Readiness(id, room).Players.Single().State == "PoseUnavailable", "A saved disconnected body is not participation");
        var admission = manager.Get(id).Players.Single().AdmissionId;
        bridge.Connect(1, player, 1, 0, admission); var head = ArenaSession.Spawn(1, 0); bridge.Pose(1, head, head, new(0, 0, 1), 0); Save();
        var ready = store.Readiness(id, room);
        check(ready.SourceState == "Fresh" && ready.Origin == "Simulation" && ready.Players.Single() is { CanParticipate: true, RigKind: "Simulated", AdmissionId: var epoch } && epoch == admission,
            "Fresh accepted pose names the exact current admission and synthetic provenance");
        check(store.ReadinessByRoom(room).Single() is { RoomId: 1, SimulatedReady: 1, TrackedReady: 0, Registered: 1, SourceState: "Fresh" },
            "Room readiness separates accepted simulated poses from tracked poses");
        var captured = clock.Now;
        clock.Now = captured.AddMilliseconds(1500); check(store.Readiness(id, room).Players.Single().CanParticipate, "Readiness includes the 1.5-second source-age boundary");
        clock.Now = captured.AddMilliseconds(1500.01); check(store.Readiness(id, room).Players.Single() is { State: "Stale", CanParticipate: false }, "Source age expires without needing another world write");
        check(store.ReadinessByRoom(room).Single() is { SimulatedReady: 0, TrackedReady: 0, Registered: 1, SourceState: "Stale" },
            "A stale room summary never counts a formerly valid pose");
        clock.Now = captured.AddMilliseconds(-1000); check(store.Readiness(id, room).SourceState == "Fresh", "Source clock tolerance matches the existing observer boundary");
        clock.Now = captured.AddMilliseconds(-1000.01); check(store.Readiness(id, room).SourceState == "ClockSkew", "Future source time is not marked fresh beyond clock tolerance");
        clock.Now = captured;
        manager.Leave(id, player, master, expectedAdmissionId: admission); manager.Join(id, player, "Readmitted", 1, HeadsetKind.Quest3, master);
        var replacement = manager.Get(id).Players.Single().AdmissionId;
        check(replacement != admission && store.Readiness(id, room).Players.Single() is { State: "AwaitingAdmission", RigKind: "None", CanParticipate: false },
            "A fresh old body cannot make a replacement admission look connected");
        check(store.ReadinessByRoom(room).Single() is { Registered: 1, SimulatedReady: 0, TrackedReady: 0 },
            "Room summary cannot count the old body for a replacement admission with the same roster size");
        manager.Execute(id, new(Guid.NewGuid(), ControlAction.Begin), master);
        check(store.Readiness(id, room).SourceState == "PhasePending", "Current Begin does not relabel an older Preparing snapshot");
        Refresh(); bridge.Connect(2, player, 1, 0, replacement); bridge.Pose(2, head, head, new(0, 0, 1), .1); Save();
        check(store.Readiness(id, room).Players.Single().CanParticipate, "The replacement becomes participating only in its own accepted management epoch");
        bridge.Suspend(); Save(true);
        check(store.Readiness(id, room).Players.Single() is { State: "Suspended", CanParticipate: false }, "Management-loss suspension cannot report ready players");
        manager.End(id, master);
        check(store.Readiness(id, room).SourceState == "Ended" && store.Readiness(id, room).Players.All(value => !value.CanParticipate), "End overrides a formerly fresh body before final recording arrives");
        check(store.ReadinessByRoom(room).Single() is { SessionId: null, SourceState: "Idle", Registered: 0 },
            "Ended worlds disappear from the active room summary");
        check(store.Info(id, master).AcceptedSequence == sequence, "Reading participation status never appends, seals or alters archived frames");

        var oldId = manager.Create(SessionMode.Independent, [1], mission, master).Id;
        manager.Join(oldId, Guid.NewGuid(), "Legacy", 1, HeadsetKind.Quest3, master); var oldStream = Guid.NewGuid(); manager.OpenStream(oldId, new(oldStream, CombatOrigin.Simulation), server);
        var old = new ArenaSession(); old.Apply(JsonSerializer.Deserialize<ManagementSnapshot>(JsonSerializer.Serialize(manager.Get(oldId), JsonFormat.Options), new JsonSerializerOptions(JsonFormat.Options) { IncludeFields = true })!);
        store.Open(oldId, WorldRecordingHeader.Create(oldId, oldStream, "Simulation", [1], old.Props), server);
        store.Append(oldId, WorldRecordingPacket.Capture(old.World, 1, 0, manager.Get(oldId).Sequence, 0, 0, _ => new()), server);
        check(store.Readiness(oldId, room).SourceState == "UnknownCaptureTime", "Legacy capture time remains unknown rather than using API receive time");
        CheckMixedReality(check, directory, mission, master, server);
    }

    private static void CheckMixedReality(Action<bool, string> check, string directory, Mission template, OperatorIdentity master, OperatorIdentity server)
    {
        var clock = new Clock { Now = DateTimeOffset.Parse("2026-10-31T08:00:00Z") };
        var start = clock.Now;
        var manager = new SessionManager();
        var environment = template.Definition.Environment with { Mode = ExperienceMode.MR };
        var mission = template with { Definition = template.Definition with { Environment = environment } };
        var id = manager.Create(SessionMode.Linked, [1, 2, 3, 4, 5], mission, master).Id;
        var directoryPath = Path.Combine(directory, "mr-start-world");
        Directory.CreateDirectory(directoryPath);
        using var store = new WorldRecordings(directoryPath, manager, clock);
        void Reject<T>(Action action, string message) where T : Exception
        {
            try { action(); } catch (T) { check(true, message); return; }
            throw new Exception(message);
        }
        var begin = new ControlCommand(Guid.NewGuid(), ControlAction.Begin);
        check(store.Readiness(id, master).MrStartState == "EmptyRoster", "MR start diagnostics identify an empty roster");
        Reject<MixedRealityNotReadyException>(() => store.ExecuteCommand(id, begin, master), "MR cannot begin before a server and live roster exist");
        Reject<InvalidOperationException>(() => manager.Join(id, Guid.NewGuid(), "VIVE", 1, HeadsetKind.ViveXr, master), "Current MR roster requires Quest 3 support");
        Reject<InvalidOperationException>(() => manager.OpenStream(id, new(Guid.NewGuid(), CombatOrigin.Simulation), server), "MR cannot be bound to a simulation source");
        Reject<InvalidOperationException>(() => manager.Execute(id, new(Guid.NewGuid(), ControlAction.SetEnvironment,
            environment with { Mode = ExperienceMode.VR }), master), "MR experience cannot be switched after reservation");

        var alpha = Guid.NewGuid(); var bravo = Guid.NewGuid();
        manager.Join(id, alpha, "Alpha", 1, HeadsetKind.Quest3, master);
        manager.Join(id, bravo, "Bravo", 5, HeadsetKind.Quest3, master);
        check(store.Readiness(id, master) is { MrStartState: "WaitingSource", SourceState: "NoRecording" },
            "A populated MR roster waits for its world source");
        var stream = Guid.NewGuid(); manager.OpenStream(id, new(stream, CombatOrigin.GameServer), server);
        var bridge = new ArenaSession();
        void Refresh() => bridge.Apply(JsonSerializer.Deserialize<ManagementSnapshot>(JsonSerializer.Serialize(manager.Get(id), JsonFormat.Options),
            new JsonSerializerOptions(JsonFormat.Options) { IncludeFields = true })!);
        Refresh();
        var header = WorldRecordingHeader.Create(id, stream, "GameServer", [1, 2, 3, 4, 5], bridge.Props, start.ToString("O"));
        Reject<InvalidOperationException>(() => store.Open(id, header, server), "An MR recording cannot publish a VR header");
        header.calibration = WorldRecordingHeader.QuestMixedRealityProfile;
        store.Open(id, header, server);
        WorldRecordingPacket Frame(long sequence, string rigKind = "Tracked") =>
            WorldRecordingPacket.Capture(bridge.World, sequence, (sequence - 1) * 50, manager.Get(id).Sequence, 0, 0, player =>
            {
                var body = bridge.World.PlayerSnapshot(player);
                return body.Connected ? new() { kind = rigKind, left = new(body.Head), right = new(body.Muzzle) } : new();
            }, manager.Get(id).Environment.Weather.ToString(), manager.Get(id).Environment.Lightning);
        store.Append(id, Frame(1), server);
        void Track(ulong connection, Guid player, int room, double time)
        {
            var admission = manager.Get(id).Players.Single(value => value.Id == player).AdmissionId;
            var head = ArenaSession.Spawn(room, 0);
            if (!bridge.Connect(connection, player, room, 0, admission)
                || !bridge.Pose(connection, head, head, new(0, 0, 1), time, tracked: true))
                throw new Exception("Fixture could not supply a tracked pose.");
        }
        Track(1, alpha, 1, .05);
        Reject<InvalidOperationException>(() => store.Append(id, Frame(2, "Simulated"), server), "MR recording rejects connected simulated bodies");
        store.Append(id, Frame(2), server);
        check(store.Readiness(id, master) is { MrStartState: "WaitingPlayers" } partial
            && partial.Players.Single(p => !p.CanParticipate).PlayerId == bravo,
            "MR start diagnostics identify the same missing player as the Begin gate");
        Reject<InvalidOperationException>(() => store.ExecuteCommand(id, begin, master), "One room's tracked pose cannot stand in for the other roster player");
        Track(2, bravo, 5, .1);
        store.Append(id, Frame(3), server);
        clock.Now = start.AddMilliseconds(1601);
        check(store.Readiness(id, master) is { MrStartState: "WaitingSource", SourceState: "Stale" }, "MR diagnostics expire at the Begin source-age gate");
        Reject<InvalidOperationException>(() => store.ExecuteCommand(id, begin, master), "Stale tracked snapshots cannot open MR");
        clock.Now = start.AddMilliseconds(100);
        manager.Execute(id, new(Guid.NewGuid(), ControlAction.SetEnvironment,
            environment with { Weather = Weather.Storm, Lightning = true }), master);
        check(store.Readiness(id, master).MrStartState == "WaitingRevision", "Fresh MR bodies still wait for the exact management revision");
        Reject<InvalidOperationException>(() => store.ExecuteCommand(id, begin, master), "A snapshot must observe the latest MR management revision");
        Refresh(); store.Append(id, Frame(4), server);
        check(store.Readiness(id, master).MrStartState == "Ready", "Only the exact ready MR roster satisfies the shared diagnostic and Begin gate");
        Reject<AccessDeniedException>(() => store.ExecuteCommand(id, begin, new("room1", OperatorRole.RoomController, 1)),
            "Linked MR start remains under master control");
        var accepted = store.ExecuteCommand(id, begin, master);
        check(store.Readiness(id, master).MrStartState is null, "The MR start diagnostic applies only while preparing");
        check(accepted.Session.State == SessionState.Running && accepted.Session.Environment is { Mode: ExperienceMode.MR, Weather: Weather.Storm, Lightning: true },
            "Fresh tracked poses for both admitted rooms open the MR mission with the current environment");
        clock.Now = start.AddSeconds(5);
        check(store.ExecuteCommand(id, begin, master).Duplicate, "An accepted MR Begin retains its original idempotent receipt");

        Refresh();
        store.Append(id, Frame(5), server);
        clock.Now = start.AddMilliseconds(200);
        var paused = store.ExecuteCommand(id, new(Guid.NewGuid(), ControlAction.Pause), master).Session;
        var resume = new ControlCommand(Guid.NewGuid(), ControlAction.Resume);
        check(store.Readiness(id, master) is { MrStartState: null, MrResumeState: "WaitingSource", SourceState: "PhasePending" },
            "Fresh Running poses cannot count as a paused MR snapshot");
        Reject<MixedRealityNotReadyException>(() => manager.Execute(id, resume, master),
            "Direct MR Resume cannot bypass the paused tracking gate");
        Reject<MixedRealityNotReadyException>(() => store.ExecuteCommand(id, resume, master),
            "MR Resume waits until the source applies Pause");
        Refresh();
        bridge.Tick(.8);
        var alphaHead = ArenaSession.Spawn(1, 0);
        check(bridge.Pose(1, alphaHead, alphaHead, new(0, 0, 1), .8, tracked: true)
            && !bridge.Weapon(1, 1, false, .8) && bridge.World.TickNumber == 0,
            "A paused MR arena can refresh tracked poses while weapons and mission ticks stay stopped");
        store.Append(id, Frame(6), server);
        clock.Now = start.AddMilliseconds(250);
        check(store.Readiness(id, master) is { MrResumeState: "WaitingPlayers" } pausedPartial
            && pausedPartial.Players.Single(p => !p.CanParticipate).PlayerId == bravo,
            "A tracked pose that expired while paused is identified as waiting");
        Reject<MixedRealityNotReadyException>(() => store.ExecuteCommand(id, resume, master),
            "MR Resume rejects a fresh paused snapshot with a missing live pose");
        check(manager.Get(id).Sequence == paused.Sequence, "Rejected MR Resume leaves the original paused sequence and intent untouched");

        manager.Execute(id, new(Guid.NewGuid(), ControlAction.SetEnvironment,
            environment with { Weather = Weather.Fog }), master);
        check(store.Readiness(id, master).MrResumeState == "WaitingRevision", "A paused MR snapshot cannot authorize a newer management revision");
        Reject<MixedRealityNotReadyException>(() => manager.Execute(id, resume, master, paused.Sequence),
            "The core rejects a resume witness for a superseded paused revision");
        Refresh();
        var bravoHead = ArenaSession.Spawn(5, 0);
        check(bridge.Pose(2, bravoHead, bravoHead, new(0, 0, 1), .9, tracked: true), "The original admission can recover tracking while paused");
        store.Append(id, Frame(7), server);
        clock.Now = start.AddMilliseconds(1800.01);
        check(store.Readiness(id, master) is { MrResumeState: "WaitingSource", SourceState: "Stale" },
            "The paused MR diagnostic expires beyond the original freshness boundary");
        Reject<MixedRealityNotReadyException>(() => store.ExecuteCommand(id, resume, master), "MR Resume rejects an expired paused snapshot");
        clock.Now = start.AddMilliseconds(300);
        check(store.Readiness(id, master).MrResumeState == "Ready", "All living MR seats on the exact paused revision satisfy Resume");
        var continued = store.ExecuteCommand(id, resume, master);
        check(continued.Session.State == SessionState.Running && !continued.Duplicate && continued.Session.StartedAtUtc == accepted.Session.StartedAtUtc,
            "The same previously rejected MR Resume succeeds on fresh tracking without resetting the mission start");
        store.ExecuteCommand(id, new(Guid.NewGuid(), ControlAction.Pause), master);
        check(store.ExecuteCommand(id, resume, master) is { Duplicate: true } retry && retry.AppliedAtSequence == continued.AppliedAtSequence
            && retry.Session.State == SessionState.Paused, "An accepted Resume retry returns the original receipt without overriding a later Pause");
    }
}
