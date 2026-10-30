using System.Text.Json;
using VrCommand.Api;
using VrCommand.Core;
using VrCommand.Simulation;

internal static class WorldSourceChecks
{
    internal static void Run(Action<bool, string> check, string directory)
    {
        void Reject<T>(Action action, string message) where T : Exception
        { try { action(); } catch (T) { check(true, message); return; } throw new Exception("Expected " + typeof(T).Name + ": " + message); }
        var manager = new SessionManager(); var actor = new OperatorIdentity("world-source", OperatorRole.GameServer);
        var mission = new MissionStore(Path.Combine(directory, "source-missions")).Create(new("Source recovery", "Synthetic", 60,
            new(ExperienceMode.VR, Weather.Clear, TimeOfDay.Day, false), new(1, EnemyBehavior.Hold, false), []));
        var session = manager.Create(SessionMode.Independent, [3], mission); var id = session.Id; var player = Guid.NewGuid();
        manager.Join(id, player, "Source player", 3, HeadsetKind.Quest3);
        using var combat = TelemetryOutbox.OpenFile(Path.Combine(directory, "source-combat.journal"), id, "Simulation");
        manager.OpenStream(id, new(combat.StreamId, CombatOrigin.Simulation), actor);
        var bridge = new ArenaSession(); var codec = new Codec();
        void Refresh() => bridge.Apply(JsonSerializer.Deserialize<ManagementSnapshot>(JsonSerializer.Serialize(manager.Get(id), JsonFormat.Options), Codec.Json)!);
        Refresh();
        var header = WorldRecordingHeader.Create(id, combat.StreamId, "Simulation", [3], bridge.Props);
        var legacy = WorldRecordingHeader.Create(Guid.NewGuid(), Guid.NewGuid(), "Simulation", [3], [], environmentVersion: 0);
        var legacyJson = codec.Header(legacy).Replace("\"environmentVersion\":0,", "").Replace("\"enemyPresentationVersion\":0,", "").Replace("\"weaponPresentationVersion\":0,", "").Replace("\"enemyFireVersion\":0,", "").Replace("\"playerFireVersion\":0,", "");
        var legacyPath = Path.Combine(directory, "legacy-environment.worldlog");
        using (var legacyJournal = new FileWorldJournal(legacyPath, true))
            legacyJournal.Append(new byte[] { 0 }.Concat(System.Text.Encoding.UTF8.GetBytes(legacyJson)).ToArray());
        using (var legacySource = new WorldOutbox(new FileWorldJournal(legacyPath, false), codec, legacy))
            check(legacySource.Header.environmentVersion == 0 && legacySource.Header.enemyPresentationVersion == 0 && legacySource.HeaderJson == legacyJson, "Legacy source without a presentation field recovers as zero while preserving its exact original header bytes");
        var legacyWorld = new ArenaWorld([3], []); legacyWorld.AddEnemy(Guid.NewGuid(), 3, new(0,0,3), new(2,0,3));
        var oldPacket = System.Text.Json.Nodes.JsonNode.Parse(codec.Packet(WorldRecordingPacket.Capture(legacyWorld,1,0,1,0,0,_=>new())))!;
        foreach (var enemyNode in oldPacket["frame"]!["enemies"]!.AsArray())
        { var enemy = enemyNode!.AsObject(); enemy.Remove("forward"); enemy.Remove("walking"); enemy.Remove("hasPresentation"); foreach(var field in new[]{"hasFireState","fireSequence","fireTickPlusOne","fireOrigin","fireDirection"})enemy.Remove(field); }
        var oldPayload = oldPacket.ToJsonString();
        using (var journal = new FileWorldJournal(legacyPath, false)) journal.Append(new byte[]{1}.Concat(System.Text.Encoding.UTF8.GetBytes(oldPayload)).ToArray());
        var beforeRecovery = File.ReadAllBytes(legacyPath);
        using (var legacySource = WorldOutbox.Recover(legacyPath, codec))
            check(legacySource.Header.enemyPresentationVersion == 0 && legacySource.Pending!.Json == oldPayload
                && !codec.ReadPacket(legacySource.Pending.Json).frame.enemies[0].hasPresentation,
                "Old binary enemy packets retain their exact payload while parsed metadata stays legacy");
        check(beforeRecovery.SequenceEqual(File.ReadAllBytes(legacyPath)), "Reading old opponent records preserves the original binary header, payload and checksums byte for byte");
        var sourcePath = Path.Combine(directory, "world-source.bin");
        var source = WorldOutbox.Create(sourcePath, header, codec);
        var storePath = Path.Combine(directory, "source-worlds"); Directory.CreateDirectory(storePath);
        using var store = new WorldRecordings(storePath, manager);
        var initial = WorldRecordingPacket.Capture(bridge.World, 1, 0, manager.Get(id).Sequence, 0, 0, _ => new());
        source.Append(initial); initial.frame.players[0].health = 1;
        check(codec.ReadPacket(source.Pending!.Json).frame.players[0].health == 100, "World source detaches caller-owned packet mutations before publishing");
        var exposed = source.Header; exposed.origin = "GameServer";
        check(source.Header.origin == "Simulation", "Published world header cannot be mutated through its public view");
        check(DateTimeOffset.TryParseExact(source.Header.captureStartedAtUtc, "O", System.Globalization.CultureInfo.InvariantCulture, System.Globalization.DateTimeStyles.None, out _), "New world source persists its actual UTC capture clock");
        var invalidClock = source.Header; invalidClock.captureStartedAtUtc = "2026-10-29T00:00:00.0000000+08:00";
        Reject<ArgumentException>(() => WorldRecordingValidation.Header(invalidClock), "Ambiguous or non-UTC source clock is rejected");
        Reject<IOException>(() => WorldOutbox.Recover(sourcePath, codec), "World source enforces an exclusive process lease");
        Reject<IOException>(() => WorldOutbox.Create(sourcePath, header, codec), "New world source cannot overwrite an existing recording");
        var connection = new Loopback(store, id, actor, codec) { DropFrame = true };
        using (var publisher = new WorldPublisher(source, codec, connection))
            Reject<WorldConnectionInterrupted>(() => publisher.Deliver(0, false, default).GetAwaiter().GetResult(), "Lost world acknowledgment surfaces a retryable connection failure");
        check(source.AcknowledgedSequence == 0 && store.Info(id, actor).AcceptedSequence == 1, "Network success without receipt does not acknowledge the source");
        var relabeled = source.Header; relabeled.captureStartedAtUtc = DateTimeOffset.UtcNow.AddMinutes(1).ToString("O", System.Globalization.CultureInfo.InvariantCulture);
        Reject<InvalidOperationException>(() => store.Open(id, relabeled, actor), "Accepted recording cannot reset its capture clock to disguise an old source");
        source.Dispose();
        var disk = new FaultJournal(new FileWorldJournal(sourcePath, false)); source = new WorldOutbox(disk, codec, null);
        connection = new Loopback(store, id, actor, codec);
        using (var publisher = new WorldPublisher(source, codec, connection))
            check(publisher.Deliver(0, false, default).GetAwaiter().GetResult() && source.AcknowledgedSequence == 1, "Recovered source retries the exact accepted frame without duplication");
        manager.Execute(id, new(Guid.NewGuid(), ControlAction.Begin)); Refresh(); bridge.Connect(1, player, 3, 0, manager.Get(id).Players.Single().AdmissionId);
        var head = ArenaSession.Spawn(3, 0); var target = bridge.World.Snapshot().Enemies[0].Feet + new Vec3(0, .9f, 0);
        bridge.Pose(1, head, head, (target - head).Normalized(), 0); bridge.Weapon(1, 1, false, 0);
        combat.Capture(bridge.World, manager.Get(id).Sequence);
        RecordedRig Rig(Guid value) => new() { kind = "Simulated", left = new(head + new Vec3(-.2f, -.3f, .2f)), right = new(head) };
        var running = WorldRecordingPacket.Capture(bridge.World, 2, 50, manager.Get(id).Sequence, combat.LastSequence, 0, Rig);
        source.Append(running);
        Reject<InvalidOperationException>(() => source.Finish(), "Running world cannot persist completion intent");
        using (var publisher = new WorldPublisher(source, codec, new Loopback(store, id, actor, codec)))
            check(!publisher.Deliver(0, false, default).GetAwaiter().GetResult() && store.Info(id, actor).AcceptedSequence == 1, "World publication waits for its combat acknowledgment dependency");
        manager.ReportStreamBatch(id, JsonSerializer.Deserialize<StreamCombatRecord[]>(TelemetryOutbox.BatchJson(combat.PendingBatch()), JsonFormat.Options)!, actor);
        connection = new Loopback(store, id, actor, codec) { AfterFrame = () => disk.Fail = true };
        using (var publisher = new WorldPublisher(source, codec, connection))
            Reject<IOException>(() => publisher.Deliver(combat.LastSequence, false, default).GetAwaiter().GetResult(), "World receipt disk failure is surfaced after server acceptance");
        check(source.AcknowledgedSequence == 1 && source.Pending!.Sequence == 2 && store.Info(id, actor).AcceptedSequence == 2, "Failed receipt flush retains the same pending source boundary");
        disk.Fail = false;
        manager.Execute(id, new(Guid.NewGuid(), ControlAction.End)); Refresh();
        source.Append(WorldRecordingPacket.Capture(bridge.World, 3, 100, manager.Get(id).Sequence, combat.LastSequence, bridge.World.EventSequence, Rig));
        disk.Fail = true; Reject<IOException>(() => source.Finish(), "World completion disk failure does not manufacture a final intent");
        check(!source.Complete, "Failed world completion leaves source visibly incomplete"); disk.Fail = false; source.Finish();
        Reject<InvalidOperationException>(() => source.MarkSealed(), "Undelivered world cannot accept a seal receipt");
        connection = new Loopback(store, id, actor, codec);
        using (var publisher = new WorldPublisher(source, codec, connection))
        {
            check(publisher.Deliver(combat.LastSequence, false, default).GetAwaiter().GetResult() && source.AcknowledgedSequence == 2, "Same pending frame safely confirms its accepted server prefix");
            check(publisher.Deliver(combat.LastSequence, false, default).GetAwaiter().GetResult() && source.AcknowledgedSequence == 3, "Ended world frame drains before world completion");
            check(!publisher.Deliver(combat.LastSequence, false, default).GetAwaiter().GetResult() && !source.Sealed, "World seal waits for explicit combat seal confirmation");
            manager.SealStream(id, new(combat.StreamId, combat.LastSequence), actor); connection.DropSeal = true;
            Reject<WorldConnectionInterrupted>(() => publisher.Deliver(combat.LastSequence, true, default).GetAwaiter().GetResult(), "Lost final seal response remains retryable");
            check(store.Info(id, actor).Complete && !source.Sealed, "Server seal alone cannot advance an unconfirmed local seal");
        }
        using (var publisher = new WorldPublisher(source, codec, new Loopback(store, id, actor, codec)))
            check(publisher.Deliver(combat.LastSequence, true, default).GetAwaiter().GetResult() && source.Sealed, "Exact seal retry confirms one durable final world");
        source.Dispose();
        using (var recovered = WorldOutbox.Recover(sourcePath, codec))
        {
            check(recovered.Complete && recovered.Sealed && recovered.AcknowledgedSequence == 3 && recovered.Pending is null, "Completion, acknowledgment and seal survive independent source recovery");
            var wrong = new Loopback(store, id, actor, codec) { WrongIdentity = true };
            using (var publisher = new WorldPublisher(recovered, codec, wrong))
                Reject<WorldPublicationRejected>(() => publisher.Deliver(2, true, default).GetAwaiter().GetResult(), "World publisher rejects a mismatched attachment receipt");
            var gate = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            using var concurrent = new WorldPublisher(recovered, codec, new Loopback(store, id, actor, codec) { Gate = gate.Task });
            var first = concurrent.Deliver(2, true, default);
            Reject<InvalidOperationException>(() => concurrent.Deliver(2, true, default).GetAwaiter().GetResult(), "Publisher rejects concurrent operations on its socket");
            gate.SetResult(true); first.GetAwaiter().GetResult();
        }
        var bytes = File.ReadAllBytes(sourcePath); var torn = Path.Combine(directory, "world-torn.bin"); File.WriteAllBytes(torn, bytes[..^1]);
        Reject<InvalidDataException>(() => WorldOutbox.Recover(torn, codec), "World journal torn tail fails recovery instead of discarding a receipt");
        check(File.ReadAllBytes(torn).SequenceEqual(bytes[..^1]), "Failed world recovery preserves the complete corrupt evidence");
        var corrupt = Path.Combine(directory, "world-corrupt.bin"); bytes[^1] ^= 1; File.WriteAllBytes(corrupt, bytes);
        Reject<InvalidDataException>(() => WorldOutbox.Recover(corrupt, codec), "World record checksum rejects silent payload corruption");
        Reject<ArgumentException>(() => new WorldWebSocket("https://example.test/?key=bad", id, "server"), "World connection refuses credential-bearing query URLs");
    }
    private sealed class Codec : IWorldCodec
    {
        internal static readonly JsonSerializerOptions Json = new(JsonFormat.Options) { IncludeFields = true, WriteIndented = false };
        public string Header(WorldRecordingHeader value) => JsonSerializer.Serialize(value, Json);
        public string Packet(WorldRecordingPacket value) => JsonSerializer.Serialize(value, Json);
        public WorldRecordingHeader ReadHeader(string value) => JsonSerializer.Deserialize<WorldRecordingHeader>(value, Json)!;
        public WorldRecordingPacket ReadPacket(string value) => JsonSerializer.Deserialize<WorldRecordingPacket>(value, Json)!;
        public WorldPublicationAck ReadAck(string value) => JsonSerializer.Deserialize<WorldPublicationAck>(value, Json)!;
    }
    private sealed class FaultJournal(IWorldJournal inner) : IWorldJournal
    {
        internal bool Fail;
        public long Length => inner.Length;
        public WorldJournalRecord? Read(long position) => inner.Read(position);
        public void Append(byte[] payload) { if (Fail) throw new IOException("Disk unavailable."); inner.Append(payload); }
        public void Dispose() => inner.Dispose();
    }
    private sealed class Loopback(WorldRecordings store, Guid id, OperatorIdentity actor, Codec codec) : IWorldConnection
    {
        internal bool DropFrame, DropSeal, WrongIdentity;
        internal Action? AfterFrame;
        internal Task? Gate;
        public Task Connect(CancellationToken cancellation) => Task.CompletedTask;
        public async Task<string> Exchange(string message, CancellationToken cancellation)
        {
            if (Gate is not null) await Gate;
            using var json = JsonDocument.Parse(message); var root = json.RootElement; var type = root.GetProperty("type").GetString();
            var info = type switch
            {
                "header" => store.Open(id, codec.ReadHeader(root.GetProperty("payload").GetRawText()), actor),
                "frame" => store.Append(id, codec.ReadPacket(root.GetProperty("payload").GetRawText()), actor),
                "seal" => store.Seal(id, root.GetProperty("finalSequence").GetInt64(), actor),
                _ => throw new InvalidOperationException("Unknown test message.")
            };
            if (type == "frame") { AfterFrame?.Invoke(); if (DropFrame) throw new WorldConnectionInterrupted("Lost frame receipt.", new IOException()); }
            if (type == "seal" && DropSeal) throw new WorldConnectionInterrupted("Lost seal receipt.", new IOException());
            if (WrongIdentity) info.Header.streamId = Guid.NewGuid().ToString("D");
            return JsonSerializer.Serialize(new { type = "ack", info }, Codec.Json);
        }
        public void Dispose() { }
    }
}
