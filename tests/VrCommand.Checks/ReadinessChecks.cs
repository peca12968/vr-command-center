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
        var captured = clock.Now;
        clock.Now = captured.AddMilliseconds(1500); check(store.Readiness(id, room).Players.Single().CanParticipate, "Readiness includes the 1.5-second source-age boundary");
        clock.Now = captured.AddMilliseconds(1500.01); check(store.Readiness(id, room).Players.Single() is { State: "Stale", CanParticipate: false }, "Source age expires without needing another world write");
        clock.Now = captured.AddMilliseconds(-1000); check(store.Readiness(id, room).SourceState == "Fresh", "Source clock tolerance matches the existing observer boundary");
        clock.Now = captured.AddMilliseconds(-1000.01); check(store.Readiness(id, room).SourceState == "ClockSkew", "Future source time is not marked fresh beyond clock tolerance");
        clock.Now = captured;
        manager.Leave(id, player, master, expectedAdmissionId: admission); manager.Join(id, player, "Readmitted", 1, HeadsetKind.Quest3, master);
        var replacement = manager.Get(id).Players.Single().AdmissionId;
        check(replacement != admission && store.Readiness(id, room).Players.Single() is { State: "AwaitingAdmission", RigKind: "None", CanParticipate: false },
            "A fresh old body cannot make a replacement admission look connected");
        manager.Execute(id, new(Guid.NewGuid(), ControlAction.Begin), master);
        check(store.Readiness(id, room).SourceState == "PhasePending", "Current Begin does not relabel an older Preparing snapshot");
        Refresh(); bridge.Connect(2, player, 1, 0, replacement); bridge.Pose(2, head, head, new(0, 0, 1), .1); Save();
        check(store.Readiness(id, room).Players.Single().CanParticipate, "The replacement becomes participating only in its own accepted management epoch");
        bridge.Suspend(); Save(true);
        check(store.Readiness(id, room).Players.Single() is { State: "Suspended", CanParticipate: false }, "Management-loss suspension cannot report ready players");
        manager.End(id, master);
        check(store.Readiness(id, room).SourceState == "Ended" && store.Readiness(id, room).Players.All(value => !value.CanParticipate), "End overrides a formerly fresh body before final recording arrives");
        check(store.Info(id, master).AcceptedSequence == sequence, "Reading participation status never appends, seals or alters archived frames");

        var oldId = manager.Create(SessionMode.Independent, [1], mission, master).Id;
        manager.Join(oldId, Guid.NewGuid(), "Legacy", 1, HeadsetKind.Quest3, master); var oldStream = Guid.NewGuid(); manager.OpenStream(oldId, new(oldStream, CombatOrigin.Simulation), server);
        var old = new ArenaSession(); old.Apply(JsonSerializer.Deserialize<ManagementSnapshot>(JsonSerializer.Serialize(manager.Get(oldId), JsonFormat.Options), new JsonSerializerOptions(JsonFormat.Options) { IncludeFields = true })!);
        store.Open(oldId, WorldRecordingHeader.Create(oldId, oldStream, "Simulation", [1], old.Props), server);
        store.Append(oldId, WorldRecordingPacket.Capture(old.World, 1, 0, manager.Get(oldId).Sequence, 0, 0, _ => new()), server);
        check(store.Readiness(oldId, room).SourceState == "UnknownCaptureTime", "Legacy capture time remains unknown rather than using API receive time");
    }
}
