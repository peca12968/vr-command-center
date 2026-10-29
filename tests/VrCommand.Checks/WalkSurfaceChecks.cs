using VrCommand.Simulation;

static class WalkSurfaceChecks
{
    public static void Run(Action<bool, string> check)
    {
        for (var room = 1; room <= 5; room++)
        {
            var origin = ArenaWorld.RoomOrigin(room);
            var prop = new WorldProp(Guid.NewGuid(), room, PropKind.Sandbag, origin + new Vec3(-3.9f, 0, -2), 0);
            var surface = new ArenaWalkSurface(origin, [prop]); var world = new ArenaWorld([room], [prop]);
            var player = Guid.NewGuid(); var position = origin + new Vec3(-3, 1.65f, -3); world.AddPlayer(player, room, position);
            for (var index = 0; index < 40; index++)
            {
                position = surface.Constrain(position, position + new Vec3(0, 0, .05f));
                world.SetPlayerPose(player, position, position, new(0, 0, 1));
            }
            check(position.Z > -2.651f && position.Z < -2.649f && world.Snapshot().Players[0].Connected,
                $"Room {room} desktop wall clipping remains acceptable to the authoritative world");
            var retreat = surface.Constrain(position, position + new Vec3(0, 0, -.25f));
            world.SetPlayerPose(player, retreat, retreat, new(0, 0, 1));
            check(retreat.Z < -2.89f && world.Snapshot().Players[0].Magazine == 30 && world.Snapshot().Players[0].Health == 100,
                $"Room {room} can retreat from blocked input without resetting combat state");
        }
        var barrel = new WorldProp(Guid.NewGuid(), 3, PropKind.Barrel, new(), 0);
        var corner = new ArenaWalkSurface(new(), [barrel]); var from = new Vec3(-.7f, 1.65f, -.7f); var wish = new Vec3(-.5f, 1.65f, -.5f);
        var result = corner.Constrain(from, wish);
        check(!corner.ClearSegment(from, wish) && corner.ClearSegment(from, result) && Vec3.Distance(from, result) <= Vec3.Distance(from, wish),
            "Sliding chooses an authority-admissible segment without increasing frame displacement");
        check(!corner.ClearSegment(from, new(float.PositiveInfinity, 0, 0)) && Vec3.Distance(corner.Constrain(from, new(float.NaN, 0, 0)), from) == 0,
            "Non-finite desktop wishes cannot enter collision state");
        var rotated = new ArenaWalkSurface(new(), [new WorldProp(Guid.NewGuid(), 3, PropKind.Barrel, new(-2.5f, 0, -1.3f), 45)]);
        var stop = rotated.Constrain(new(-2.5f, 1.65f, -2.85f), new(-2.5f, 1.65f, 0));
        check(stop.Z > -2.225f && stop.Z < -2.219f, "Rotated barrel uses the same expanded footprint as authority and navigation");
    }
}
