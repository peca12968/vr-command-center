using System.Text.Json.Serialization;
using VrCommand.Simulation;

namespace VrCommand.Core;

public record LayoutRoutePoint(float X, float Z);
public record LayoutSeatRoute(int Seat, LayoutRoutePoint[] Path,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] float? SampleStep = null);
public record LayoutRoutePreview(float Step, float TargetZ, LayoutSeatRoute[] Seats);

internal static class LayoutWalkways
{
    // Room-local planar samples. The standing footprint and swept segments
    // come from the same surface used by desktop movement.
    private const float Step = .5f, FineStep = .125f, Limit = 5.5f, TargetZ = 0;

    internal static LayoutRoutePreview Preview(ManagedProp[] props, LayoutSpawn[] spawns)
    {
        var origin = ArenaWorld.RoomOrigin(3);
        var geometry = props.Select((prop, index) => new WorldProp(new Guid(index + 1, 0, 0, new byte[8]), 3,
            prop.assetId == "barrel" ? PropKind.Barrel : PropKind.Sandbag, origin + prop.position.Vector, prop.yawDegrees)).ToArray();
        var surface = new ArenaWalkSurface(origin, geometry);
        var routes = Sample(surface, origin, spawns, Step);
        if (routes.Any(route => route.Path.Length == 0))
        {
            var finer = Sample(surface, origin, spawns, FineStep);
            for (var i = 0; i < routes.Length; i++)
                if (routes[i].Path.Length == 0 && finer[i].Path.Length > 0)
                    routes[i] = finer[i] with { SampleStep = FineStep };
        }
        return new(Step, TargetZ, routes);
    }

    private static LayoutSeatRoute[] Sample(ArenaWalkSurface surface, Vec3 origin, LayoutSpawn[] spawns, float step)
    {
        var side = (int)(2 * Limit / step) + 1;
        var next = new int[side * side];
        var walkable = new bool?[next.Length];
        Array.Fill(next, -1);
        var queue = new Queue<int>();
        var targetRow = Grid(TargetZ);
        for (var x = 0; x < side; x++)
        {
            var index = targetRow * side + x;
            if (!Open(index)) continue;
            next[index] = index;
            queue.Enqueue(index);
        }
        while (queue.TryDequeue(out var index))
        {
            var x = index % side;
            var z = index / side;
            Visit(x + 1, z, index);
            Visit(x - 1, z, index);
            Visit(x, z + 1, index);
            Visit(x, z - 1, index);
        }
        return spawns.Select(spawn => new LayoutSeatRoute(spawn.Seat, Path(spawn))).ToArray();

        int Grid(float coordinate) => (int)Math.Round((coordinate + Limit) / step);
        Vec3 Point(int index) => origin + new Vec3(index % side * step - Limit, 0, index / side * step - Limit);
        bool Open(int index)
        {
            if (walkable[index] is bool cached) return cached;
            var open = surface.Walkable(Point(index));
            walkable[index] = open;
            return open;
        }
        void Visit(int x, int z, int parent)
        {
            if (x < 0 || z < 0 || x >= side || z >= side) return;
            var index = z * side + x;
            if (next[index] >= 0 || !Open(index) || !surface.ClearSegment(Point(index), Point(parent))) return;
            next[index] = parent;
            queue.Enqueue(index);
        }
        LayoutRoutePoint[] Path(LayoutSpawn spawn)
        {
            var x = Grid(spawn.X);
            var z = Grid(spawn.Z);
            if (x < 0 || z < 0 || x >= side || z >= side) return [];
            var index = z * side + x;
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
}
