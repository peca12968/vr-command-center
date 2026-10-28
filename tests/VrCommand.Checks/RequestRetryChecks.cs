using VrCommand.Core;
using VrCommand.Persistence;

internal static class RequestRetryChecks
{
    internal static void Run(Action<bool, string> check, string directory, Mission mission)
    {
        void Reject<T>(Action action, string message) where T : Exception
        {
            try { action(); }
            catch (T) { check(true, message); return; }
            throw new Exception($"Expected {typeof(T).Name}: {message}");
        }
        var master = new OperatorIdentity("master", OperatorRole.Master);
        var room1 = new OperatorIdentity("room-1", OperatorRole.RoomController, 1);
        var room2 = new OperatorIdentity("room-2", OperatorRole.RoomController, 2);
        var game = new OperatorIdentity("game", OperatorRole.GameServer);
        var data = Path.Combine(directory, "request-retries");
        var createId = Guid.NewGuid(); var joinId = Guid.NewGuid(); var leaveId = Guid.NewGuid(); var player = Guid.NewGuid();
        Guid id;
        SessionEvent[] archive;
        using (var store = new SqliteSessionEventStore(data))
        {
            var manager = new SessionManager(store);
            var ids = new System.Collections.Concurrent.ConcurrentBag<Guid>();
            Parallel.For(0, 20, _ => ids.Add(manager.Create(SessionMode.Independent, [1], mission, master, createId).Id));
            id = ids.First();
            check(ids.All(value => value == id) && manager.List().Length == 1 && manager.Events(id).Length == 1,
                "Concurrent creation retries reserve one room and persist one Created event");
            Reject<ArgumentException>(() => manager.Create(SessionMode.Independent, [2], mission, master, Guid.Empty), "Empty lifecycle request UUID is rejected");
            Reject<InvalidOperationException>(() => manager.Create(SessionMode.Independent, [2], mission, master, createId), "Creation key cannot be reused for different rooms");
            Reject<InvalidOperationException>(() => manager.Create(SessionMode.Independent, [1], mission with { Definition = mission.Definition with { Name = "Changed" } }, master, createId),
                "Creation key binds the full immutable mission content");
            Reject<InvalidOperationException>(() => manager.Create(SessionMode.Independent, [1], mission, room1, createId), "Creation retry must use the original operator identity");
            Reject<AccessDeniedException>(() => manager.Create(SessionMode.Independent, [1], mission, room2, createId), "Creation retry rechecks room authorization");
            Reject<AccessDeniedException>(() => manager.Create(SessionMode.Independent, [1], mission, game, createId), "Game server cannot replay an operator creation");
            Reject<InvalidOperationException>(() => manager.Join(id, player, "Alpha", 1, HeadsetKind.Quest3, room1, createId), "Lifecycle request key cannot cross operation kinds");
            Parallel.For(0, 20, _ => manager.Join(id, player, "Alpha", 1, HeadsetKind.Quest3, room1, joinId));
            check(manager.Get(id).Players.Single().Seat == 0 && manager.Get(id).Sequence == 2,
                "Concurrent join retries retain one player and the original seat");
            Reject<InvalidOperationException>(() => manager.Join(id, player, "Changed", 1, HeadsetKind.Quest3, room1, joinId), "Join retry cannot change player details");
            Reject<InvalidOperationException>(() => manager.Join(id, player, "Alpha", 1, HeadsetKind.Quest3, master, joinId), "Master cannot take over another identity's join key");
            for (var i = 0; i < 4; i++) manager.Join(id, Guid.NewGuid(), "Other", 1, HeadsetKind.Quest3);
            check(manager.Join(id, player, "Alpha", 1, HeadsetKind.Quest3, room1, joinId).Players.Length == 5,
                "Original join retry succeeds even when its room is now full");
            Parallel.For(0, 20, _ => manager.Leave(id, player, room1, leaveId));
            var sequence = manager.Get(id).Sequence;
            check(manager.Get(id).Players.Length == 4 && manager.Events(id).Count(e => e.Kind == SessionEventKind.PlayerLeft) == 1,
                "Concurrent leave retries remove once and preserve the historical room");
            Reject<InvalidOperationException>(() => manager.Leave(id, Guid.NewGuid(), room1, leaveId), "Leave key cannot target a different player");
            Reject<AccessDeniedException>(() => manager.Leave(id, player, room2, leaveId), "Leave retry cannot bypass room access after removal");
            check(manager.Join(id, player, "Alpha", 1, HeadsetKind.Quest3, room1, joinId).Players.Length == 4 && manager.Get(id).Sequence == sequence,
                "Stale join retry acknowledges history without resurrecting a departed player");
            manager.Join(id, player, "Alpha", 1, HeadsetKind.Quest3, room1, Guid.NewGuid());
            sequence = manager.Get(id).Sequence;
            manager.Leave(id, player, room1, leaveId);
            check(manager.Get(id).Players.Length == 5 && manager.Get(id).Sequence == sequence,
                "Stale leave retry cannot remove a later re-admission of the same player");
            manager.End(id, master);
            var replacement = manager.Create(SessionMode.Independent, [1], mission, master, Guid.NewGuid());
            check(manager.Create(SessionMode.Independent, [1], mission, master, createId).Id == id && manager.Rooms()[0].SessionId == replacement.Id,
                "Archived creation retry returns the original session without replacing a new reservation");
            check(manager.Join(id, player, "Alpha", 1, HeadsetKind.Quest3, room1, joinId).State == SessionState.Ended,
                "Archived join retry acknowledges the original operation without reopening the session");
            manager.Leave(id, player, room1, leaveId);
            archive = manager.Events(id);
            check(archive.Where(e => e.RequestId.HasValue).Select(e => e.RequestId).Distinct().Count() == 4,
                "Request IDs are persisted only once alongside their accepted lifecycle events");
        }
        using (var store = new SqliteSessionEventStore(data))
        {
            var manager = new SessionManager(store);
            var count = manager.Events(id).Length;
            check(manager.Create(SessionMode.Independent, [1], mission, master, createId).Id == id
                && manager.Join(id, player, "Alpha", 1, HeadsetKind.Quest3, room1, joinId).State == SessionState.Ended,
                "SQLite restart restores creation and join keys including archived acknowledgments");
            manager.Leave(id, player, room1, leaveId);
            check(manager.Events(id).Length == count, "SQLite restart restores leave keys without a second append");
        }
        var poisoned = archive.ToArray();
        poisoned[1] = poisoned[1] with { RequestId = createId };
        var seed = new MemorySessionEventStore(); seed.Seed(id, poisoned);
        Reject<InvalidDataException>(() => new SessionManager(seed), "Recovery rejects duplicate lifecycle keys across events");
        poisoned = archive.ToArray(); poisoned[0] = poisoned[0] with { SchemaVersion = 3 };
        seed = new MemorySessionEventStore(); seed.Seed(id, poisoned);
        Reject<InvalidDataException>(() => new SessionManager(seed), "Old event versions cannot assert new request metadata");
        var crossStream = new MemorySessionEventStore();
        var otherId = Guid.NewGuid();
        crossStream.Seed(id, archive);
        crossStream.Seed(otherId, [archive[0] with { EventId = Guid.NewGuid(), SessionId = otherId }]);
        Reject<InvalidDataException>(() => new SessionManager(crossStream), "Recovery rejects a request key repeated in another session stream");
        var oldStore = new MemorySessionEventStore();
        oldStore.Seed(id, archive.Select(entry => entry with { SchemaVersion = 3, RequestId = null }).ToArray());
        check(new SessionManager(oldStore).Get(id).State == SessionState.Ended,
            "Existing schema 3 histories without request metadata remain readable");
        var failed = new FailingStore(); var durable = new SessionManager(failed);
        var retryKey = Guid.NewGuid();
        failed.Fail = true;
        Reject<IOException>(() => durable.Create(SessionMode.Independent, [3], mission, master, retryKey), "Failed creation append does not accept its request key");
        failed.Fail = false;
        var created = durable.Create(SessionMode.Independent, [3], mission, master, retryKey);
        check(created.Sequence == 1 && durable.Create(SessionMode.Independent, [3], mission, master, retryKey).Id == created.Id,
            "Creation can be retried after storage recovery without a phantom reservation");
        var retryJoin = Guid.NewGuid(); var retryLeave = Guid.NewGuid();
        failed.Fail = true;
        Reject<IOException>(() => durable.Join(created.Id, player, "Alpha", 3, HeadsetKind.Quest3, master, retryJoin), "Failed join append does not consume a seat or key");
        failed.Fail = false;
        durable.Join(created.Id, player, "Alpha", 3, HeadsetKind.Quest3, master, retryJoin);
        failed.Fail = true;
        Reject<IOException>(() => durable.Leave(created.Id, player, master, retryLeave), "Failed leave append retains the player and retry key remains available");
        failed.Fail = false;
        durable.Leave(created.Id, player, master, retryLeave);
        check(durable.Get(created.Id).Players.Length == 0 && durable.Get(created.Id).Sequence == 3,
            "Recovered join and leave persist exactly one event each");
        var linked = new SessionManager(); var linkedKey = Guid.NewGuid();
        var all = linked.Create(SessionMode.Linked, [5, 3, 1, 4, 2], mission, master, linkedKey);
        check(linked.Create(SessionMode.Linked, [1, 2, 3, 4, 5], mission, master, linkedKey).Id == all.Id,
            "Linked creation treats room order as the same canonical set");
    }

    private sealed class FailingStore : ISessionEventStore
    {
        public bool Fail { get; set; }
        private readonly MemorySessionEventStore inner = new();
        public SessionEvent[][] Load() => inner.Load();
        public void Append(SessionEvent entry)
        {
            if (Fail) throw new IOException("Simulated storage failure");
            inner.Append(entry);
        }
    }
}
