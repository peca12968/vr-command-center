using System.Text.Json;
using VrCommand.Core;
using VrCommand.Simulation;

internal static class MissionLayoutChecks
{
    internal static void Run(Action<bool, string> check, string directory)
    {
        static PropPlacement Prop(string kind, float x, float z, float yaw = 0, float y = 0) => new(kind, new(x, y, z), yaw);
        static MissionLayoutReport Inspect(PropPlacement[] props, int count = 0, SessionMode mode = SessionMode.Independent, ExperienceMode experience = ExperienceMode.VR)
            => MissionLayout.Inspect(new MissionLayoutRequest(experience, mode, count, props));
        void Reject<T>(Action action, string message) where T : Exception
        { try { action(); } catch (T) { check(true, message); return; } throw new Exception("Expected " + typeof(T).Name + ": " + message); }
        var empty = Inspect([]);
        check(empty.CanStart == true && empty.EnemyCapacityPerRoom == 117 && empty.Spawns.Length == 5 && empty.Spawns[0] == new LayoutSpawn(0, -3, -3), "Empty VR room uses all five real spawn positions and the actual 117-candidate enemy grid");
        var wall = Enumerable.Range(0, 6).Select(i => Prop("sandbag", -5 + i * 2, -1)).ToArray();
        var enclosed = Inspect(wall, 8);
        check(enclosed.CanStart == true && enclosed.RoutePreview is { Step: .5f, TargetZ: 0 } enclosedPreview
            && enclosedPreview.Seats.Select(route => route.Seat).SequenceEqual(Enumerable.Range(0, 5))
            && enclosedPreview.Seats.All(route => route.Path.Length == 0),
            "A full-width barricade clears the required checks but the route preview finds no sampled way to the middle");
        var gap = wall.Where(prop => prop.Position.X != 1).ToArray();
        var gapReport = Inspect(gap, 8, SessionMode.Linked);
        var origin = ArenaWorld.RoomOrigin(3);
        var walk = new ArenaWalkSurface(origin, gap.Select(prop =>
            new WorldProp(Guid.NewGuid(), 3, PropKind.Sandbag, origin + new Vec3(prop.Position.X, prop.Position.Y, prop.Position.Z), prop.YawDegrees)).ToArray());
        check(gapReport.RoutePreview is { } passable && passable.Seats.All(route =>
        {
            var spawn = gapReport.Spawns[route.Seat];
            var path = route.Path;
            return path.Length > 1 && path[0] == new LayoutRoutePoint(spawn.X, spawn.Z) && path[^1].Z == 0
                && path.Zip(path.Skip(1)).All(edge =>
                    Math.Abs(edge.First.X - edge.Second.X) + Math.Abs(edge.First.Z - edge.Second.Z) == .5f
                    && walk.ClearSegment(origin + new Vec3(edge.First.X, 1.65f, edge.First.Z), origin + new Vec3(edge.Second.X, 1.65f, edge.Second.Z)));
        }), "Removing one bag opens five sampled routes whose individual segments pass the actual walking surface");
        check(JsonSerializer.Serialize(gapReport.RoutePreview) == JsonSerializer.Serialize(Inspect(gap, 8).RoutePreview),
            "Identical room geometry gives deterministic routes independent of session topology");
        check(Inspect([Prop("sandbag", 5.2f, 1, 45)]).Issues.Any(i => i.Code == "OutsideRoom"), "Rotated cover corners cannot extend beyond the room even when its centre is inside");
        check(Inspect([Prop("barrel", 5.65f, 1)]).CanStart == true, "A cover face may touch the room boundary within the defined float tolerance");
        check(Inspect([Prop("sandbag", 0, 2), Prop("sandbag", 2, 2)]).CanStart == true, "Face-touching cover is allowed for barricades without positive-area overlap");
        check(Inspect([Prop("sandbag", 0, 2, 45), Prop("sandbag", .5656854f, 2.5656854f, 45)]).CanStart == true, "SAT allows separated rotated cover whose axis-aligned envelopes overlap");
        var collision = Inspect([Prop("sandbag", 0, 2, 45), Prop("barrel", 0, 2)]);
        check(collision.CanStart == false && collision.Issues.Any(i => i.Code == "Overlap" && i.PropIndex == 0 && i.OtherPropIndex == 1), "Positive-area overlap reports both original prop indexes");
        var spawn = Inspect([Prop("barrel", -3, -3)]);
        check(spawn.Issues.Any(i => i.Code == "SpawnBlocked" && i.Seat == 0 && i.PropIndex == 0), "A cover obstruction reports the exact fixed admission seat");
        check(Inspect([Prop("barrel", -3, -2.4f)]).Issues.Any(i => i.Code == "SpawnBlocked"), "Spawn clearance uses the same 0.3m expansion as actual movement");
        check(Inspect([Prop("unsupported", 0, 2)]).Issues.Single().Code == "UnsupportedAsset", "Unsupported VR assets are reported before native launch");
        check(Inspect([Prop("barrel", 0, 2, y: .1f)]).Issues.Any(i => i.Code == "NotFloorLevel"), "Non-floor props cannot masquerade as supported VR cover");
        check(Inspect([Prop("barrel", 0, 2, yaw: 720)]).Issues.Single().Code == "YawOutOfRange", "New layouts require a bounded equivalent angle rather than unstable huge rotations");
        check(Inspect([Prop("barrel", float.MaxValue, 2), Prop("barrel", -float.MaxValue, 2)]).Issues.All(i => i.Code == "OutsideRoom"), "Extreme finite coordinates fail bounds checks without bogus overflow overlaps");
        var rows = (from z in new[] { 2f, 4f } from x in new[] { -3f, -1f, 1f, 3f } select Prop("sandbag", x, z)).ToArray();
        var single = Inspect(rows, 100); var linked = Inspect(rows, 100, SessionMode.Linked);
        check(single.EnemyCapacityPerRoom == 84 && single.Issues.Any(i => i.Code == "EnemySpawnCapacity"), "Initial enemy count cannot exceed the actual room candidate capacity");
        check(linked.CanStart == true && linked.RequestedEnemiesPerRoom == 20, "Linked preflight distributes the total enemy count across all five identical rooms");
        var full = Inspect(Enumerable.Repeat(Prop("barrel", 0, 2), 500).ToArray());
        check(full.Truncated && full.Issues.Length == 128 && full.TotalIssueCount == 124750 && full.InvalidProps.Length == 500, "Large overlap reports are bounded while keeping all invalid prop indexes and the true count");
        var mr = Inspect([Prop("unsupported", 100, 100)], experience: ExperienceMode.MR);
        check(!mr.Applies && mr.CanStart is null, "MR is explicitly outside VR preflight rather than falsely passing calibration");
        check(mr.RoutePreview is null && collision.RoutePreview is null, "Unsupported mode and invalid geometry do not emit route previews");
        var store = new MissionStore(Path.Combine(directory, "layout-missions"));
        var invalid = store.Create(new("Fixable layout", "Draft can be saved before layout corrections", 900,
            new(ExperienceMode.VR, Weather.Clear, TimeOfDay.Day, false), new(1, EnemyBehavior.Hold, false), [Prop("barrel", -3, -3)]));
        var manager = new SessionManager(); var actor = new OperatorIdentity("layout-master", OperatorRole.Master);
        Reject<MissionLayoutRejectedException>(() => manager.Create(SessionMode.Independent, [3], invalid, actor), "New invalid VR reservations are rejected by core policy");
        check(manager.Rooms(actor).All(room => room.SessionId is null)
            && JsonSerializer.Serialize(store.Get(invalid.Id).Definition, JsonFormat.Options) == JsonSerializer.Serialize(invalid.Definition, JsonFormat.Options),
            "Rejection reserves no room and never rewrites the saved mission");
        var defensive = store.Create(invalid.Definition with { Name = "Intentional barricade", Props = wall });
        var defensiveSession = manager.Create(SessionMode.Independent, [3], defensive, actor);
        check(defensiveSession.Mission.Id == defensive.Id && defensiveSession.State == SessionState.Preparing,
            "A sampled route warning remains advisory and does not change the new-session gate");
        var memory = new MemorySessionEventStore(); var id = Guid.NewGuid(); var request = Guid.NewGuid();
        memory.Seed(id, [new(6, Guid.NewGuid(), id, 1, DateTimeOffset.UtcNow, SessionEventKind.Created,
            JsonSerializer.SerializeToElement(new SessionCreated(SessionMode.Independent, [3], invalid), JsonFormat.Options), actor, request)]);
        var restored = new SessionManager(memory);
        check(restored.Get(id, actor).Mission.Id == invalid.Id, "Historically accepted layouts still reconstruct without applying the new-start gate");
        restored.End(id, actor);
        check(restored.Create(SessionMode.Independent, [3], invalid, actor, request).State == SessionState.Ended && memory.Load()[0].Length == 2,
            "Historical create-key retries confirm their old acceptance after End without revalidating or reapplying layout");
        Reject<AccessDeniedException>(() => restored.Create(SessionMode.Linked, [1, 2, 3, 4, 5], invalid, new("room", OperatorRole.RoomController, 3)), "Room control cannot bypass scope through layout failure handling");
    }
}
