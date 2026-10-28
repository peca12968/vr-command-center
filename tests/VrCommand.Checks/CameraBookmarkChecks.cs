using VrCommand.Api;
using VrCommand.Core;
using VrCommand.Simulation;

internal static class CameraBookmarkChecks
{
    internal static void Run(Action<bool, string> check, string directory)
    {
        void Reject<T>(Action action, string message) where T : Exception
        { try { action(); } catch (T) { check(true, message); return; } throw new Exception("Expected " + typeof(T).Name + ": " + message); }
        var manager = new SessionManager();
        var master = new OperatorIdentity("camera-master", OperatorRole.Master);
        var room = new OperatorIdentity("camera-room", OperatorRole.RoomController, 1);
        var foreign = room with { RoomId = 2 };
        var server = new OperatorIdentity("camera-server", OperatorRole.GameServer);
        var mission = new MissionStore(Path.Combine(directory, "camera-missions")).Create(new("Camera arena", "Positions", 600,
            new(ExperienceMode.VR, Weather.Clear, TimeOfDay.Day, false), new(0, EnemyBehavior.Hold, false), []));
        var session = manager.Create(SessionMode.Independent, [1], mission, master);
        var stream = Guid.NewGuid(); manager.OpenStream(session.Id, new(stream, CombatOrigin.Simulation), server);
        var database = Path.Combine(directory, "camera-database"); Directory.CreateDirectory(database);
        var bookmarkId = Guid.NewGuid();
        var draft = new CameraBookmarkDraft("東側 <位置>", new([-28, .8, 1], .7, .9, 15));
        CameraBookmark saved;
        using (var store = new WorldRecordings(database, manager))
        {
            store.Open(session.Id, WorldRecordingHeader.Create(session.Id, stream, "Simulation", [1], []), server);
            saved = store.SaveBookmark(session.Id, bookmarkId, draft, master);
            check(WorldJson.Write(store.SaveBookmark(session.Id, bookmarkId, draft, master)) == WorldJson.Write(saved) && store.Bookmarks(session.Id, master).Single().Name == draft.Name,
                "Camera save retry preserves immutable identity and creation time");
            Reject<InvalidOperationException>(() => store.SaveBookmark(session.Id, bookmarkId, draft with { Name = "Other" }, master), "Conflicting camera retry cannot replace the stored position");
            check(store.Bookmarks(session.Id, room).Length == 0, "Room observer does not inherit another operator's camera positions");
            Reject<KeyNotFoundException>(() => store.DeleteBookmark(session.Id, bookmarkId, room), "A readable recording does not permit removing another operator's camera");
            store.SaveBookmark(session.Id, bookmarkId, draft with { Name = "Room view" }, room);
            check(store.Bookmarks(session.Id, room).Single().Name == "Room view" && store.Bookmarks(session.Id, master).Single().Name == draft.Name,
                "Same camera ID is independently namespaced by authenticated operator");
            Reject<AccessDeniedException>(() => store.Bookmarks(session.Id, foreign), "Foreign room cannot list camera positions");
            Reject<AccessDeniedException>(() => store.SaveBookmark(session.Id, Guid.NewGuid(), draft, foreign), "Foreign room cannot save a camera on another room's recording");
            Reject<AccessDeniedException>(() => store.DeleteBookmark(session.Id, bookmarkId, foreign), "Foreign room cannot remove a camera position");
            Reject<AccessDeniedException>(() => store.Bookmarks(session.Id, server), "GameServer identity cannot read operator camera settings");
            Reject<AccessDeniedException>(() => store.SaveBookmark(session.Id, Guid.NewGuid(), draft, server), "GameServer identity cannot write operator camera settings");
            Reject<ArgumentException>(() => store.SaveBookmark(session.Id, Guid.Empty, draft, master), "Empty camera ID is rejected");
            Reject<ArgumentException>(() => store.SaveBookmark(session.Id, Guid.NewGuid(), draft with { Name = "bad\nname" }, master), "Control characters are rejected in camera names");
            Reject<ArgumentException>(() => store.SaveBookmark(session.Id, Guid.NewGuid(), draft with { View = draft.View with { Target = [double.NaN, 0, 0] } }, master), "Nonfinite camera targets are rejected before persistence");
            Reject<ArgumentException>(() => store.SaveBookmark(session.Id, Guid.NewGuid(), draft with { View = draft.View with { Radius = 1000 } }, master), "Unbounded camera distances are rejected");
            Reject<ArgumentException>(() => store.SaveBookmark(session.Id, Guid.NewGuid(), draft with { View = draft.View with { Phi = 0 } }, master), "Camera elevation avoids a degenerate overhead orientation");
            var wideId = Guid.NewGuid();
            check(store.SaveBookmark(session.Id, wideId, draft with { View = draft.View with { Radius = 184 } }, master).View.Radius == 184,
                "Camera persistence supports the greater distance needed for a narrow all-room viewport");
            store.DeleteBookmark(session.Id, wideId, master);
            for (var index = 1; index < 24; index++) store.SaveBookmark(session.Id, Guid.NewGuid(), draft with { Name = "View " + index }, master);
            Reject<InvalidOperationException>(() => store.SaveBookmark(session.Id, Guid.NewGuid(), draft, master), "Camera quota applies atomically per operator and recording");
            check(WorldJson.Write(store.SaveBookmark(session.Id, bookmarkId, draft, master)) == WorldJson.Write(saved), "Camera retry still succeeds at the position quota");
            store.DeleteBookmark(session.Id, bookmarkId, master); store.DeleteBookmark(session.Id, bookmarkId, master);
            check(store.SaveBookmark(session.Id, bookmarkId, draft, master).Deleted && store.Bookmarks(session.Id, master).Length == 23,
                "Late save and delete retries do not resurrect a removed camera");
            store.SaveBookmark(session.Id, Guid.NewGuid(), draft, master);
            check(store.Bookmarks(session.Id, master).Length == 24, "Removing a position frees an active camera slot");
        }
        using var restored = new WorldRecordings(database, manager);
        var retry = restored.SaveBookmark(session.Id, bookmarkId, draft, master);
        check(retry.Deleted && retry.CreatedAtUtc == saved.CreatedAtUtc && retry.View.Target.SequenceEqual(draft.View.Target)
            && restored.Bookmarks(session.Id, master).Length == 24 && restored.Bookmarks(session.Id, room).Length == 1,
            "SQLite restart restores positions, operator isolation and removal tombstones");
    }
}
