using VrCommand.Simulation;

namespace VrCommand.Core;

public record LayoutRoutePoint(float X, float Z);
public record LayoutSeatRoute(int Seat, LayoutRoutePoint[] Path);
public record LayoutRoutePreview(float Step, float TargetZ, LayoutSeatRoute[] Seats);

internal static class LayoutWalkways
{
    // Room-local planar samples. The standing footprint and swept segments
    // come from the same surface used by desktop movement.
    private const float Step = .5f, Limit = 5.5f, TargetZ = 0;
    private const int Side = (int)(2 * Limit / Step) + 1;

    internal static LayoutRoutePreview Preview(ManagedProp[] props, LayoutSpawn[] spawns)
    {
        var origin = ArenaWorld.RoomOrigin(3);
        var geometry = props.Select((prop, index) => new WorldProp(new Guid(index + 1, 0, 0, new byte[8]), 3,
            prop.assetId == "barrel" ? PropKind.Barrel : PropKind.Sandbag, origin + prop.position.Vector, prop.yawDegrees)).ToArray();
        var surface = new ArenaWalkSurface(origin, geometry);
        var next = new int[Side * Side];
        Array.Fill(next, -1);
        var queue = new Queue<int>();
        var targetRow = Grid(TargetZ);
        for (var x = 0; x < Side; x++)
        {
            var index = targetRow * Side + x;
            if (!surface.Walkable(Point(index))) continue;
            next[index] = index;
            queue.Enqueue(index);
        }
        while (queue.TryDequeue(out var index))
        {
            var x = index % Side;
            var z = index / Side;
            Visit(x + 1, z, index);
            Visit(x - 1, z, index);
            Visit(x, z + 1, index);
            Visit(x, z - 1, index);
        }
        return new(Step, TargetZ, spawns.Select(spawn => new LayoutSeatRoute(spawn.Seat, Path(spawn))).ToArray());

        Vec3 Point(int index) => origin + new Vec3(index % Side * Step - Limit, 0, index / Side * Step - Limit);
        void Visit(int x, int z, int parent)
        {
            if (x < 0 || z < 0 || x >= Side || z >= Side) return;
            var index = z * Side + x;
            if (next[index] >= 0 || !surface.ClearSegment(Point(index), Point(parent))) return;
            next[index] = parent;
            queue.Enqueue(index);
        }
        LayoutRoutePoint[] Path(LayoutSpawn spawn)
        {
            var x = Grid(spawn.X);
            var z = Grid(spawn.Z);
            if (x < 0 || z < 0 || x >= Side || z >= Side) return [];
            var index = z * Side + x;
            var start = Point(index) - origin;
            if (start.X != spawn.X || start.Z != spawn.Z || next[index] < 0) return [];
            var path = new List<LayoutRoutePoint>();
            while (true)
            {
                var point = Point(index) - origin;
                path.Add(new(point.X, point.Z));
                if (next[index] == index) return path.ToArray();
                index = next[index];
            }
        }
    }

    private static int Grid(float coordinate) => (int)Math.Round((coordinate + Limit) / Step);
}
