using System.Text.Json;
using VrCommand.Core;
using VrCommand.Persistence;
using VrCommand.Simulation;
using VrCommand.Api;

internal static class AdmissionChecks
{
    internal static void Run(Action<bool, string> check, string directory, Mission mission)
    {
        void Reject<T>(Action action, string message) where T : Exception
        { try { action(); } catch (T) { check(true, message); return; } throw new Exception("Expected " + typeof(T).Name + ": " + message); }
        var storePath = Path.Combine(directory, "admission-events"); var server = new OperatorIdentity("admission-server", OperatorRole.GameServer);
        var master = new OperatorIdentity("admission-master", OperatorRole.Master);
        var signer = new PlayerJoinTicketSigner(Enumerable.Repeat((byte)81, 32).ToArray());
        Guid sessionId, playerId = Guid.NewGuid(), firstAdmission, secondAdmission, removeKey = Guid.NewGuid();
        PlayerJoinTicket oldTicket, newTicket; SessionView final;
        using (var disk = new SqliteSessionEventStore(storePath))
        {
            var manager = new SessionManager(disk); sessionId = manager.Create(SessionMode.Independent, [1], mission, master).Id;
            manager.Join(sessionId, playerId, "Admission player", 1, HeadsetKind.Quest3, master);
            var first = manager.Get(sessionId).Players.Single(); firstAdmission = first.AdmissionId;
            var joining = manager.Events(sessionId).Single(entry => entry.Kind == SessionEventKind.PlayerJoined);
            check(firstAdmission != Guid.Empty && firstAdmission == joining.EventId && joining.Read<Player>().AdmissionId == firstAdmission,
                "Admission is the durable joining event identity in snapshot and payload");
            oldTicket = signer.Issue(sessionId, first); var oldClaims = signer.Validate(oldTicket.Ticket, sessionId);
            check(oldTicket.Ticket.StartsWith("v2.") && oldClaims.AdmissionId == firstAdmission && oldClaims.Seat == 0,
                "V2 ticket signs its exact admission and spawn seat");
            var approval = manager.ResolveAdmission(oldClaims, server);
            Reject<AccessDeniedException>(() => manager.ResolveAdmission(oldClaims with { Seat = 4 }, server), "Validated claims cannot substitute another spawn seat");
            Reject<AccessDeniedException>(() => manager.ResolveAdmission(oldClaims with { AdmissionId = Guid.NewGuid() }, server), "Validated claims cannot substitute another admission");
            check(approval.AdmissionId == firstAdmission && approval.ThroughSequence == manager.Get(sessionId).Sequence && approval.ExpiresAtUtc == oldClaims.ExpiresAtUtc,
                "Validated admission includes its roster observation and expiry");
            Reject<AccessDeniedException>(() => manager.ResolveAdmission(oldClaims, master), "Operators cannot act as game-server ticket validators");
            Reject<ArgumentException>(() => manager.Leave(sessionId, playerId, master, requireAdmissionMatch: true), "Fresh network removal requires an admission fence");
            var beforeRejected = manager.Get(sessionId).Sequence;
            Reject<InvalidOperationException>(() => manager.Leave(sessionId, playerId, master, expectedAdmissionId: Guid.NewGuid(), requireAdmissionMatch: true),
                "Wrong admission cannot remove the current player");
            check(manager.Get(sessionId).Sequence == beforeRejected, "Rejected admission fence adds no durable event");
            manager.Leave(sessionId, playerId, master, removeKey, firstAdmission, true);
            Reject<AccessDeniedException>(() => manager.ResolveAdmission(oldClaims, server), "Leaving immediately revokes the current ticket admission");
            manager.Join(sessionId, playerId, "Admission player", 1, HeadsetKind.Quest3, master);
            var second = manager.Get(sessionId).Players.Single(); secondAdmission = second.AdmissionId;
            check(second.Seat == first.Seat && second.AdmissionId != firstAdmission, "Same player and seat receive a new admission on reentry");
            Reject<AccessDeniedException>(() => manager.ResolveAdmission(oldClaims, server), "Old ticket stays revoked after same-ID same-seat reentry");
            newTicket = signer.Issue(sessionId, second);
            check(manager.ResolveAdmission(signer.Validate(newTicket.Ticket, sessionId), server).AdmissionId == secondAdmission,
                "Newly issued ticket resolves only the new admission");
            manager.Leave(sessionId, playerId, master, removeKey, firstAdmission, true);
            check(manager.Get(sessionId).Players.Single().AdmissionId == secondAdmission, "Accepted old leave retry confirms history without removing a new admission");
            Reject<InvalidOperationException>(() => manager.Leave(sessionId, playerId, master, removeKey, secondAdmission, true),
                "A retry key cannot be rebound to the replacement admission fence");
            Reject<InvalidOperationException>(() => manager.Leave(sessionId, playerId, master, Guid.NewGuid(), firstAdmission, true),
                "Unaccepted stale removal cannot affect the replacement admission");
            var bridge = new ArenaSession();
            ManagementSnapshot Snapshot() => JsonSerializer.Deserialize<ManagementSnapshot>(JsonSerializer.Serialize(manager.Get(sessionId), JsonFormat.Options), new JsonSerializerOptions(JsonFormat.Options) { IncludeFields = true })!;
            bridge.Apply(Snapshot());
            check(!bridge.Connect(1, playerId, 1, 0, firstAdmission) && bridge.Connect(2, playerId, 1, 0, secondAdmission),
                "Game transport cannot bind an obsolete validated admission even at the same seat");
            var head = ArenaSession.Spawn(1, 0);
            check(bridge.Pose(2, head, head, new(0, 0, 1), 0), "Current admission can submit an accepted pose");
            manager.Leave(sessionId, playerId, master, expectedAdmissionId: secondAdmission);
            manager.Join(sessionId, playerId, "Admission player", 1, HeadsetKind.Quest3, master);
            var third = manager.Get(sessionId).Players.Single(); var skipped = Snapshot(); bridge.Apply(skipped);
            check(!bridge.Pose(2, head, head, new(0, 0, 1), .05) && !bridge.Weapon(2, 1, false, .05)
                && !bridge.World.PlayerSnapshot(playerId).Connected, "Polling across a skipped leave/rejoin revokes the old bound body and inputs");
            check(!bridge.Connect(3, playerId, 1, 0, secondAdmission) && bridge.Connect(4, playerId, 1, 0, third.AdmissionId),
                "Replacement transport accepts only the new exact admission");
            var badSnapshot = Snapshot(); badSnapshot.players[0].admissionId = "";
            Reject<ArgumentException>(() => new ArenaSession().Apply(badSnapshot), "Missing management admission cannot silently become a legacy binding");
            var duplicate = Snapshot(); duplicate.players = [duplicate.players[0], new() { id = Guid.NewGuid().ToString("D"), admissionId = duplicate.players[0].admissionId, roomId = 1, seat = 1 }];
            Reject<ArgumentException>(() => new ArenaSession().Apply(duplicate), "Distinct bodies cannot share an admission identity");
            manager.Execute(sessionId, new(Guid.NewGuid(), ControlAction.Begin), master); bridge.Apply(Snapshot());
            var changedRunning = Snapshot(); changedRunning.sequence++; changedRunning.players[0].admissionId = Guid.NewGuid().ToString("D");
            Reject<InvalidOperationException>(() => bridge.Apply(changedRunning), "A running world cannot fabricate a new admission or respawn");
            check(bridge.Pose(4, head, head, new(0, 0, 1), .1), "Rejected running admission mutation retains the accepted binding");
            final = manager.Get(sessionId);
        }
        using (var disk = new SqliteSessionEventStore(storePath))
        {
            var restarted = new SessionManager(disk);
            check(restarted.Get(sessionId).Players.Single().AdmissionId == final.Players.Single().AdmissionId, "Admission survives SQLite restart exactly");
            Reject<AccessDeniedException>(() => restarted.ResolveAdmission(signer.Validate(oldTicket.Ticket, sessionId), server), "Restart does not revive the first revoked ticket");
            Reject<AccessDeniedException>(() => restarted.ResolveAdmission(signer.Validate(newTicket.Ticket, sessionId), server), "Restart does not revive a later revoked ticket");
            restarted.Leave(sessionId, playerId, master, removeKey, firstAdmission, true);
            check(restarted.Get(sessionId).Players.Single().AdmissionId == final.Players.Single().AdmissionId, "Fenced leave retry remains harmless after restart");
        }
        var legacy = new SessionManager(); var oldSession = legacy.Create(SessionMode.Independent, [2], mission).Id;
        legacy.Join(oldSession, Guid.NewGuid(), "Legacy", 2, HeadsetKind.Quest3);
        var source = legacy.Events(oldSession).Select(entry => entry.Kind == SessionEventKind.PlayerJoined ? entry with
        {
            SchemaVersion = 5, Payload = JsonSerializer.SerializeToElement(new { entry.Read<Player>().Id, entry.Read<Player>().Name, entry.Read<Player>().RoomId, entry.Read<Player>().Headset, entry.Read<Player>().Seat }, JsonFormat.Options)
        } : entry with { SchemaVersion = 5 }).ToArray();
        var memory = new MemorySessionEventStore(); memory.Seed(oldSession, source);
        var upgraded = new SessionManager(memory);
        check(upgraded.Get(oldSession).Players.Single().AdmissionId == source[1].EventId, "Schema 1–5 histories derive a stable admission from their original joining event");
        check(new SessionManager(memory).Get(oldSession).Players.Single().AdmissionId == upgraded.Get(oldSession).Players.Single().AdmissionId,
            "Legacy admission reconstruction is deterministic across independent recoveries");
        var legacyPlayer = upgraded.Get(oldSession).Players.Single().Id; var legacyLeaveKey = Guid.NewGuid();
        legacy.Leave(oldSession, legacyPlayer, requestId: legacyLeaveKey); legacy.Join(oldSession, legacyPlayer, "Legacy", 2, HeadsetKind.Quest3);
        var oldRetryStore = new MemorySessionEventStore();
        oldRetryStore.Seed(oldSession, legacy.Events(oldSession).Select(entry => entry.Kind == SessionEventKind.PlayerLeft ? entry with
        {
            SchemaVersion = 5, Payload = JsonSerializer.SerializeToElement(new { entry.Read<PlayerLeft>().PlayerId, entry.Read<PlayerLeft>().RoomId }, JsonFormat.Options)
        } : entry with { SchemaVersion = 5 }).ToArray());
        var oldRetry = new SessionManager(oldRetryStore); var priorAdmission = oldRetry.Get(oldSession).Players.Single().AdmissionId;
        oldRetry.Leave(oldSession, legacyPlayer, requestId: legacyLeaveKey, requireAdmissionMatch: true);
        check(oldRetry.Get(oldSession).Players.Single().AdmissionId == priorAdmission, "Already accepted pre-v14 unfenced leave key can confirm history without removing its replacement");
        var malformed = source.ToArray(); malformed[1] = malformed[1] with { SchemaVersion = 6 };
        var broken = new MemorySessionEventStore(); broken.Seed(oldSession, malformed);
        Reject<InvalidDataException>(() => new SessionManager(broken), "New event schema cannot omit its persisted admission identity");
        Reject<ArgumentException>(() => signer.Issue(oldSession, upgraded.Get(oldSession).Players.Single() with { AdmissionId = Guid.Empty }),
            "Signer refuses tickets without a durable admission");
        var oldPlayer = upgraded.Get(oldSession).Players.Single(); var payload = new byte[58]; payload[0] = 1;
        oldSession.TryWriteBytes(payload.AsSpan(1, 16)); oldPlayer.Id.TryWriteBytes(payload.AsSpan(17, 16)); payload[33] = 2;
        System.Buffers.Binary.BinaryPrimitives.WriteInt64BigEndian(payload.AsSpan(34, 8), DateTimeOffset.UtcNow.AddMinutes(5).ToUnixTimeSeconds());
        System.Security.Cryptography.RandomNumberGenerator.Fill(payload.AsSpan(42, 16));
        static string Encode(byte[] value) => Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');
        var legacyTicket = "v1." + Encode(payload) + "." + Encode(System.Security.Cryptography.HMACSHA256.HashData(Enumerable.Repeat((byte)81, 32).ToArray(), payload));
        Reject<AccessDeniedException>(() => signer.Validate(legacyTicket, oldSession), "Previously valid signed v1 invitations are rejected after the admission protocol upgrade");
        // A reentry can be completely skipped by a recording poll, including a changed display name.
        var recordingManager = new SessionManager(); var recordedSession = recordingManager.Create(SessionMode.Independent, [3], mission).Id;
        var recordedPlayer = Guid.NewGuid(); recordingManager.Join(recordedSession, recordedPlayer, "Before reentry", 3, HeadsetKind.Quest3);
        var stream = Guid.NewGuid(); recordingManager.OpenStream(recordedSession, new(stream, CombatOrigin.Simulation), server);
        var world = new ArenaSession();
        void Observe() => world.Apply(JsonSerializer.Deserialize<ManagementSnapshot>(JsonSerializer.Serialize(recordingManager.Get(recordedSession), JsonFormat.Options), new JsonSerializerOptions(JsonFormat.Options) { IncludeFields = true })!);
        Observe(); var recordingsPath = Path.Combine(directory, "admission-world"); Directory.CreateDirectory(recordingsPath);
        using var recordings = new WorldRecordings(recordingsPath, recordingManager);
        recordings.Open(recordedSession, WorldRecordingHeader.Create(recordedSession, stream, "Simulation", [3], world.Props), server);
        recordings.Append(recordedSession, WorldRecordingPacket.Capture(world.World, 1, 0, recordingManager.Get(recordedSession).Sequence, 0, 0, _ => new(), mission.Definition.Environment.Weather.ToString(), mission.Definition.Environment.Lightning), server);
        recordingManager.Leave(recordedSession, recordedPlayer); recordingManager.Join(recordedSession, recordedPlayer, "After reentry", 3, HeadsetKind.Quest3);
        Observe(); recordings.Append(recordedSession, WorldRecordingPacket.Capture(world.World, 2, 10, recordingManager.Get(recordedSession).Sequence, 0, 0, _ => new(), mission.Definition.Environment.Weather.ToString(), mission.Definition.Environment.Lightning), server);
        check(recordings.Frame(recordedSession, 2, server)!.Statistics.Single().Name == "After reentry", "World recording follows the new admitted display name even when the leave/rejoin was skipped");
        recordingManager.Execute(recordedSession, new(Guid.NewGuid(), ControlAction.Begin)); Observe();
        recordingManager.Execute(recordedSession, new(Guid.NewGuid(), ControlAction.End)); Observe();
        recordings.Append(recordedSession, WorldRecordingPacket.Capture(world.World, 3, 20, recordingManager.Get(recordedSession).Sequence, 0, 0, _ => new(), mission.Definition.Environment.Weather.ToString(), mission.Definition.Environment.Lightning), server);
        recordingManager.SealStream(recordedSession, new(stream, 0), server);
        check(recordings.Seal(recordedSession, 3, server).Complete, "Reentry recording still seals against the exact final player statistics");
    }
}
