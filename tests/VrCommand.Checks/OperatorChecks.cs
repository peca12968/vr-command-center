using VrCommand.Core;

internal static class OperatorChecks
{
    internal static void Run(Action<bool, string> check, Mission mission)
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
        var server = new OperatorIdentity("game-server", OperatorRole.GameServer);
        var store = new MemorySessionEventStore();
        var manager = new SessionManager(store);
        var own = manager.Create(SessionMode.Independent, [1], mission, room1);
        var other = manager.Create(SessionMode.Independent, [2], mission, room2);
        check(manager.List(actor: room1).Length == 1 && manager.Rooms(room2).Single().Id == 2,
            "Room-scoped list and reservation views exclude other independent rooms");
        Reject<AccessDeniedException>(() => manager.Get(other.Id, room1), "Room controller cannot read another independent session");
        Reject<AccessDeniedException>(() => manager.Events(other.Id, actor: room1), "Room controller cannot read another room's event history");
        Reject<AccessDeniedException>(() => manager.End(other.Id, room1), "Room controller cannot end another independent session");
        Reject<AccessDeniedException>(() => manager.Create(SessionMode.Linked, [1,2,3,4,5], mission, room1), "Room controller cannot create a linked session");
        Reject<AccessDeniedException>(() => manager.Create(SessionMode.Independent, [3], mission, server), "Game server cannot create management sessions");
        Reject<AccessDeniedException>(() => AccessPolicy.AuthorMission(room1), "Room controller cannot overwrite the shared mission library");
        var player = Guid.NewGuid();
        manager.Join(own.Id, player, "Alpha", 1, HeadsetKind.Quest3, room1);
        var command = new ControlCommand(Guid.NewGuid(), ControlAction.Begin);
        manager.Execute(own.Id, command, room1);
        Reject<InvalidOperationException>(() => manager.Execute(own.Id, command, master), "A different actor cannot take ownership of an accepted command ID");
        check(manager.Events(own.Id).All(e => e.Actor == room1 && e.SchemaVersion == 6), "New event envelopes retain the verified identity");
        var restored = new SessionManager(store);
        check(restored.Execute(own.Id, command, room1).Duplicate, "Authenticated command retries survive recovery");
        manager.End(own.Id, room1);
        manager.End(other.Id, room2);
        var linked = manager.Create(SessionMode.Linked, [1,2,3,4,5], mission, master);
        check(manager.Get(linked.Id, room1).RoomIds.Length == 5, "Room controller can read a linked world containing its room");
        Reject<AccessDeniedException>(() => manager.Execute(linked.Id, new(Guid.NewGuid(), ControlAction.End), room1), "Only master can control the shared linked mission");
        manager.Join(linked.Id, player, "Alpha", 1, HeadsetKind.Quest3, room1);
        Reject<AccessDeniedException>(() => manager.Join(linked.Id, Guid.NewGuid(), "Other", 2, HeadsetKind.ViveXr, room1), "Linked player assignment cannot cross room scope");
        Reject<AccessDeniedException>(() => manager.Leave(linked.Id, player, room2), "Linked player removal cannot cross room scope");
        Reject<AccessDeniedException>(() => manager.Join(linked.Id, Guid.NewGuid(), "Server", 1, HeadsetKind.Quest3, server), "Combat source cannot manage player seats");
        manager.Leave(linked.Id, player, room1);
        check(manager.Get(linked.Id).Players.Length == 0, "Room controller may release its own linked player slot");
        var oldEvents = manager.Events(own.Id).Select(e => e with { SchemaVersion = 1, Actor = null }).ToArray();
        var legacyStore = new MemorySessionEventStore();
        legacyStore.Seed(own.Id, oldEvents);
        var legacy = new SessionManager(legacyStore);
        check(legacy.Get(own.Id).State == SessionState.Ended && legacy.Events(own.Id).All(e => e.Actor is null),
            "Version 1 histories remain readable without inventing an operator identity");
        var invalid = oldEvents.ToArray();
        invalid[0] = invalid[0] with { SchemaVersion = 2 };
        legacyStore.Seed(own.Id, invalid);
        Reject<InvalidDataException>(() => new SessionManager(legacyStore), "Version 2 history cannot omit its actor");
        Reject<ArgumentException>(() => manager.Rooms(new("invalid", OperatorRole.RoomController, 6)),
            "Invalid room-scoped identity rejected");
        var unauthorized = manager.Events(linked.Id).ToArray();
        unauthorized[0] = unauthorized[0] with { Actor = room1 };
        var unauthorizedStore = new MemorySessionEventStore();
        unauthorizedStore.Seed(linked.Id, unauthorized);
        Reject<AccessDeniedException>(() => new SessionManager(unauthorizedStore),
            "Recovery revalidates the recorded actor's authority over linked creation");
    }
}
