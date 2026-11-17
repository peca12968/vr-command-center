using System.Text.Json;
using VrCommand.Api;
using VrCommand.Core;
using VrCommand.Persistence;
using VrCommand.Simulation;

internal static class VenueClimateScopeChecks
{
    private sealed class Clock : TimeProvider
    {
        public DateTimeOffset Now = DateTimeOffset.UtcNow;
        public override DateTimeOffset GetUtcNow() => Now;
    }

    internal static void Run(Action<bool, string> check, string directory)
    {
        void Reject<T>(Action action, string message) where T : Exception
        {
            try { action(); }
            catch (T) { check(true, message); return; }
            throw new Exception("Expected " + typeof(T).Name + ": " + message);
        }
        var master = new OperatorIdentity("climate-scope-master", OperatorRole.Master);
        var server = new OperatorIdentity("climate-scope-server", OperatorRole.GameServer);
        var mission = new MissionStore(Path.Combine(directory, "climate-scope-missions")).Create(new("Independent settings", "Scope checks", 60,
            new(ExperienceMode.VR, Weather.Clear, TimeOfDay.Day, false), new(0, EnemyBehavior.Hold, false), []));
        var path = Path.Combine(directory, "climate-scope-events");
        var worldPath = Path.Combine(directory, "climate-scope-worlds");
        Directory.CreateDirectory(worldPath);
        var requestId = Guid.NewGuid();
        var climate = new VenueClimate(Weather.Storm, TimeOfDay.Night, true);
        var enemyRequest = Guid.NewGuid();
        var enemyPolicy = new VenueEnemyPolicy(EnemyBehavior.Patrol, false);
        VenuePhaseFence[] selected;
        VenuePhaseFence[] enemySelected;
        VenuePhaseReceipt accepted;
        Guid observedId;
        VenuePhaseFence[] Fences(SessionManager manager) => manager.ReadVenuePhase(master).Environment.Select(target =>
            new VenuePhaseFence(target.SessionId, target.PhaseSinceSequence, EnvironmentSinceSequence: target.EnvironmentSinceSequence)).ToArray();
        VenuePhaseFence[] EnemyFences(SessionManager manager) => manager.ReadVenuePhase(master).Enemies.Select(target =>
            new VenuePhaseFence(target.SessionId, target.PhaseSinceSequence, EnemiesSinceSequence: target.EnemiesSinceSequence,
                RoomEnemiesSinceSequence: target.RoomEnemiesSinceSequence)).ToArray();

        using (var store = new SqliteSessionEventStore(path))
        {
            var manager = new SessionManager(store);
            var sessions = Enumerable.Range(1, 3).Select(room => manager.Create(SessionMode.Independent, [room], mission, master).Id).ToArray();
            observedId = sessions[0];
            var stream = Guid.NewGuid();
            manager.OpenStream(observedId, new(stream, CombatOrigin.Simulation), server);
            foreach (var (id, index) in sessions.Select((id, index) => (id, index)))
                manager.Join(id, Guid.NewGuid(), $"Room {index + 1}", index + 1, HeadsetKind.Quest3, master);
            var bridge = new ArenaSession();
            void Refresh(SessionView view) => bridge.Apply(JsonSerializer.Deserialize<ManagementSnapshot>(
                JsonSerializer.Serialize(view, JsonFormat.Options), new JsonSerializerOptions(JsonFormat.Options) { IncludeFields = true })!);
            Refresh(manager.Get(observedId));
            var clock = new Clock();
            using var worlds = new WorldRecordings(worldPath, manager, clock);
            worlds.Open(observedId, WorldRecordingHeader.Create(observedId, stream, "Simulation", [1], bridge.Props, clock.Now.ToString("O")), server);
            worlds.Append(observedId, WorldRecordingPacket.Capture(bridge.World, 1, 0, manager.Get(observedId).Sequence, 0, 0, _ => new()), server);
            foreach (var id in sessions) manager.Execute(id, new(Guid.NewGuid(), ControlAction.Begin), master);

            selected = Fences(manager).Where(target => target.SessionId != sessions[1]).ToArray();
            Reject<VenuePhaseChangedException>(() => worlds.ExecuteVenuePhase(ControlAction.SetEnvironment, selected, requestId, master, climate),
                "Legacy environment request still requires all running sessions");
            Reject<ArgumentException>(() => worlds.ExecuteVenuePhase(ControlAction.SetEnvironment, selected, requestId, master, climate, roomIds: [1, 1]),
                "Selected climate scope rejects duplicate rooms");
            Reject<ArgumentException>(() => worlds.ExecuteVenuePhase(ControlAction.Pause, selected, requestId, master, roomIds: [1, 3]),
                "Room scope is restricted to setting operations");
            Reject<VenuePhaseChangedException>(() => worlds.ExecuteVenuePhase(ControlAction.SetEnvironment, selected, requestId, master, climate, roomIds: [1, 3, 5]),
                "An idle room in the requested scope rejects the whole change");
            var unselectedClimate = manager.Get(sessions[1]).Environment with { Weather = Weather.Fog };
            manager.Execute(sessions[1], new(Guid.NewGuid(), ControlAction.SetEnvironment, unselectedClimate), master);
            var unselectedSequence = manager.Get(sessions[1]).Sequence;
            accepted = worlds.ExecuteVenuePhase(ControlAction.SetEnvironment, selected, requestId, master, climate, roomIds: [3, 1]);
            check(accepted.Sessions.Select(row => row.SessionId).ToHashSet().SetEquals([sessions[0], sessions[2]])
                && manager.Get(sessions[1]).Sequence == unselectedSequence && manager.Get(sessions[1]).Environment == unselectedClimate,
                "Selected climate only updates rooms 1 and 3 despite newer settings in the unselected room");
            Reject<InvalidOperationException>(() => worlds.ExecuteVenuePhase(ControlAction.SetEnvironment, selected, requestId, master, climate, roomIds: [1]),
                "An accepted request cannot be replayed with a partial room selection");
            var stale = Fences(manager).Where(target => target.SessionId != sessions[1]).ToArray();
            var unaffected = manager.Get(sessions[2]).Sequence;
            manager.Execute(sessions[0], new(Guid.NewGuid(), ControlAction.SetEnvironment, manager.Get(sessions[0]).Environment), master);
            Reject<VenuePhaseChangedException>(() => worlds.ExecuteVenuePhase(ControlAction.SetEnvironment, stale, Guid.NewGuid(), master, climate, roomIds: [1, 3]),
                "A selected room's newer setting invalidates the entire scoped batch");
            check(manager.Get(sessions[2]).Sequence == unaffected, "Rejected selected-room change leaves other selected rooms intact");

            var savedSequence = manager.Get(observedId).Sequence;
            var observed = worlds.ExecuteVenuePhase(ControlAction.SetEnvironment, Fences(manager).Where(row => row.SessionId == observedId).ToArray(),
                Guid.NewGuid(), master, climate, roomIds: [1]);
            var frameId = observed.Sessions.Single().AppliedAtSequence;
            check(frameId == savedSequence + 1 && worlds.ReadinessByRoom(master)[0].VenueEnvironment is { WorldSequence: null },
                "Scoped setting waits for its source before reporting it applied");
            var current = manager.Get(observedId);
            Refresh(current);
            bridge.Tick(.05);
            clock.Now = clock.Now.AddMilliseconds(50);
            worlds.Append(observedId, WorldRecordingPacket.Capture(bridge.World, 2, 50, frameId, 0, 0, _ => new(),
                current.Environment.Weather.ToString(), current.Environment.Lightning), server);
            var rooms = worlds.ReadinessByRoom(master);
            var witness = worlds.Frame(observedId, 2, master)!.Packet;
            check(rooms[0].VenueEnvironment is { WorldSequence: 2 } && rooms[1].VenueEnvironment is null
                && rooms[2].VenueEnvironment is { WorldSequence: null } && witness.observedSequence == frameId
                && witness.weather == "Storm" && witness.frame.night && witness.lightning,
                "A real recorded setting frame confirms only its original selected source");

            enemySelected = EnemyFences(manager).Where(fence => fence.SessionId != sessions[1]).ToArray();
            var unselectedEnemies = new EnemySettings(3, EnemyBehavior.Hold, false);
            manager.Execute(sessions[1], new(Guid.NewGuid(), ControlAction.SetEnemies, Enemies: unselectedEnemies), master);
            var unselectedEnemySequence = manager.Get(sessions[1]).Sequence;
            Reject<AccessDeniedException>(() => manager.ExecuteVenuePhase(ControlAction.SetEnemies, enemySelected, enemyRequest,
                new("scope-room", OperatorRole.RoomController, 1), enemyPolicy: enemyPolicy, roomIds: [1, 3]),
                "Scoped enemy policies require the master");
            var enemyApplied = manager.ExecuteVenuePhase(ControlAction.SetEnemies, enemySelected, enemyRequest, master,
                enemyPolicy: enemyPolicy, roomIds: [3, 1]);
            var latestEnemies = manager.ReadVenuePhase(master).LatestEnemies!;
            check(enemyApplied.RoomIds!.SequenceEqual([1, 3]) && latestEnemies.RoomIds!.SequenceEqual([1, 3])
                && latestEnemies.Sessions.SelectMany(row => row.RoomIds).SequenceEqual([1, 3])
                && manager.Get(sessions[1]).Sequence == unselectedEnemySequence && manager.Get(sessions[1]).Enemies == unselectedEnemies
                && manager.Get(sessions[0]).Enemies == new EnemySettings(0, EnemyBehavior.Patrol, false),
                "Scoped enemy settings save the selected rooms without changing another room or the original count");
            Reject<InvalidOperationException>(() => manager.ExecuteVenuePhase(ControlAction.SetEnemies, enemySelected, enemyRequest, master,
                enemyPolicy: enemyPolicy), "A scoped enemy retry cannot omit its original selector");
            var currentEnemies = EnemyFences(manager).Where(fence => fence.SessionId != sessions[1]).ToArray();
            var unaffectedEnemySequence = manager.Get(sessions[2]).Sequence;
            manager.Execute(sessions[0], new(Guid.NewGuid(), ControlAction.SetEnemies, Enemies: manager.Get(sessions[0]).Enemies), master);
            Reject<VenuePhaseChangedException>(() => manager.ExecuteVenuePhase(ControlAction.SetEnemies, currentEnemies, Guid.NewGuid(), master,
                enemyPolicy: enemyPolicy, roomIds: [1, 3]), "A selected enemy policy revision invalidates the whole scoped batch");
            check(manager.Get(sessions[2]).Sequence == unaffectedEnemySequence, "Rejected scoped enemy settings leave other selected rooms intact");
        }
        using (var store = new SqliteSessionEventStore(path))
        {
            var manager = new SessionManager(store);
            var retry = manager.ExecuteVenuePhase(ControlAction.SetEnvironment, selected, requestId, master, climate: climate, roomIds: [1, 3]);
            check(retry.Duplicate && retry.Sessions.SequenceEqual(accepted.Sessions)
                && manager.ReadVenuePhase(master).LatestEnvironment!.Sessions.Single().SessionId == observedId,
                "Scoped retry after restart reads the original batch without replacing the newer room change");
            var enemyRetry = manager.ExecuteVenuePhase(ControlAction.SetEnemies, enemySelected, enemyRequest, master,
                enemyPolicy: enemyPolicy, roomIds: [1, 3]);
            check(enemyRetry.Duplicate && enemyRetry.RoomIds!.SequenceEqual([1, 3])
                && manager.ReadVenuePhase(master).LatestEnemies!.RoomIds!.SequenceEqual([1, 3]),
                "Scoped enemy selection and idempotency survive restart");
        }

        var linkedManager = new SessionManager();
        var linked = linkedManager.Create(SessionMode.Linked, [1, 2, 3, 4, 5], mission, master);
        linkedManager.Join(linked.Id, Guid.NewGuid(), "Linked player", 2, HeadsetKind.Quest3, master);
        linkedManager.Execute(linked.Id, new(Guid.NewGuid(), ControlAction.Begin), master);
        var linkedFences = Fences(linkedManager);
        Reject<VenuePhaseChangedException>(() => linkedManager.ExecuteVenuePhase(ControlAction.SetEnvironment, linkedFences, Guid.NewGuid(), master,
            climate: climate, roomIds: [2]), "A linked scene refuses a partial room scope");
        var shared = linkedManager.ExecuteVenuePhase(ControlAction.SetEnvironment, linkedFences, Guid.NewGuid(), master,
            climate: climate, roomIds: [1, 2, 3, 4, 5]);
        check(shared.Sessions.Length == 1 && linkedManager.ReadVenuePhase(master).LatestEnvironment!.Sessions.Single().RoomIds.SequenceEqual([1, 2, 3, 4, 5]),
            "A whole linked scene has exactly one environment command and all five original rooms");
        var linkedEnemies = EnemyFences(linkedManager);
        Reject<VenuePhaseChangedException>(() => linkedManager.ExecuteVenuePhase(ControlAction.SetEnemies, linkedEnemies, Guid.NewGuid(), master,
            enemyPolicy: enemyPolicy, roomIds: [1, 2, 3, 4, 5]), "Linked enemies require the whole-venue setting rather than a scoped request");
        var sharedEnemies = linkedManager.ExecuteVenuePhase(ControlAction.SetEnemies, linkedEnemies, Guid.NewGuid(), master,
            enemyPolicy: enemyPolicy);
        check(sharedEnemies.RoomIds is null && sharedEnemies.Sessions.Length == 1,
            "Whole linked enemy settings continue to use the existing single-session receipt");
    }
}
