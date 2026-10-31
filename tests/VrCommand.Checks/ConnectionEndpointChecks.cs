using System.Text.Json;
using VrCommand.Api;
using VrCommand.Core;
using VrCommand.Simulation;

internal static class ConnectionEndpointChecks
{
    internal static void Run(Action<bool, string> check, string directory)
    {
        void Reject<T>(Action action, string message) where T : Exception
        { try { action(); } catch (T) { check(true, message); return; } throw new Exception("Expected " + typeof(T).Name + ": " + message); }
        var manager = new SessionManager(); var master = new OperatorIdentity("endpoint-master", OperatorRole.Master);
        var room = new OperatorIdentity("endpoint-room", OperatorRole.RoomController, 1); var other = room with { RoomId = 2 };
        var server = new OperatorIdentity("endpoint-server", OperatorRole.GameServer);
        var mission = new MissionStore(Path.Combine(directory, "endpoint-missions")).Create(new("Endpoint", "IPv4 setup", 60,
            new(ExperienceMode.VR, Weather.Clear, TimeOfDay.Day, false), new(0, EnemyBehavior.Hold, false), []));
        var id = manager.Create(SessionMode.Independent, [1], mission, master).Id; var stream = Guid.NewGuid();
        manager.OpenStream(id, new(stream, CombatOrigin.Simulation), server);
        var path = Path.Combine(directory, "endpoint-worlds"); Directory.CreateDirectory(path);
        ConnectionEndpoint saved; var draft = new ConnectionEndpointDraft(1, stream, "127.0.0.1", 17777);
        using (var store = new WorldRecordings(path, manager))
        {
            Reject<KeyNotFoundException>(() => store.ConnectionEndpoint(id, room), "Unannounced endpoint remains explicitly missing");
            Reject<AccessDeniedException>(() => store.ConnectionEndpoint(id, other), "Endpoint read checks room scope before revealing existence");
            Reject<AccessDeniedException>(() => store.PublishEndpoint(id, draft, master), "Master cannot impersonate the game source's endpoint announcement");
            Reject<AccessDeniedException>(() => store.PublishEndpoint(id, draft, OperatorIdentity.Internal), "Internal is not an HTTP endpoint publisher shortcut");
            Reject<AccessDeniedException>(() => store.PublishEndpoint(id, draft, server with { Id = "other-source" }), "A foreign game source cannot publish an endpoint");
            Reject<KeyNotFoundException>(() => store.PublishEndpoint(id, draft, server), "An attached stream without a world header cannot announce a running server");
            var bridge = new ArenaSession(); bridge.Apply(JsonSerializer.Deserialize<ManagementSnapshot>(JsonSerializer.Serialize(manager.Get(id), JsonFormat.Options),
                new JsonSerializerOptions(JsonFormat.Options) { IncludeFields = true })!);
            var header = WorldRecordingHeader.Create(id, stream, "Simulation", [1], bridge.Props); store.Open(id, header, server);
            Reject<InvalidOperationException>(() => store.PublishEndpoint(id, draft with { StreamId = Guid.NewGuid() }, server), "Announcement is fenced by the attached stream ID");
            foreach (var address in new[] { "0.0.0.0", "224.0.0.1", "255.255.255.255", "127.1", "127.0.0.01", "localhost", "https://127.0.0.1", "::1", " 127.0.0.1" })
                try { store.PublishEndpoint(id, draft with { Address = address }, server); throw new Exception("Accepted invalid endpoint " + address); } catch (ArgumentException) { }
            check(true, "Endpoint v1 rejects wildcard, multicast, URLs, DNS, ambiguous forms and unsupported address families");
            foreach (var invalid in new[] { draft with { Version = 2 }, draft with { Port = 1023 }, draft with { Port = 65536 }, draft with { StreamId = Guid.Empty } })
                try { store.PublishEndpoint(id, invalid, server); throw new Exception("Accepted invalid endpoint contract"); } catch (ArgumentException) { }
            check(true, "Endpoint contract version, stream and port boundaries are validated");
            var before = manager.Get(id).Sequence; saved = store.PublishEndpoint(id, draft, server);
            check(saved.Address == draft.Address && saved.Port == draft.Port && !saved.SessionEnded && saved.SessionId == id,
                "Owning source publishes its declared player-facing endpoint");
            check(store.PublishEndpoint(id, draft, server) == saved, "Exact endpoint retry confirms the original timestamp and content");
            Reject<InvalidOperationException>(() => store.PublishEndpoint(id, draft with { Port = 17778 }, server), "A second port cannot replace the accepted endpoint");
            Reject<InvalidOperationException>(() => store.PublishEndpoint(id, draft with { Address = "192.168.1.100" }, server), "A second address cannot silently redirect player downloads");
            check(store.ConnectionEndpoint(id, master) == saved && store.ConnectionEndpoint(id, room) == saved, "Master and own-room controller read the same endpoint without any source credential");
            Reject<AccessDeniedException>(() => store.ConnectionEndpoint(id, server), "GameServer is not a control-desk endpoint reader");
            check(manager.Get(id).Sequence == before && WorldJson.Write(store.Info(id, master).Header) == WorldJson.Write(header), "Endpoint metadata changes neither management events nor the original recording header");
        }
        manager.End(id, master);
        using var reopened = new WorldRecordings(path, manager);
        var ended = reopened.ConnectionEndpoint(id, room);
        check(ended.SessionEnded && ended.Address == saved.Address && ended.CreatedAtUtc == saved.CreatedAtUtc, "Reopened endpoint preserves metadata and reports current Ended state");
        check(reopened.PublishEndpoint(id, draft, server) == ended, "Accepted source retry after End confirms metadata without reopening the world");
        var next = manager.Create(SessionMode.Independent, [1], mission, master);
        Reject<KeyNotFoundException>(() => reopened.ConnectionEndpoint(next.Id, room), "Room reuse does not inherit the previous session endpoint");
    }
}
