using System;
using System.Collections.Generic;

namespace VrCommand.Simulation
{
    // Uniform-cost 0.5m grid. Four-neighbour paths do not cut diagonally through corners.
    internal sealed class GridNavigation
    {
        private const int Size = 25;
        private readonly Vec3 origin;
        private readonly ArenaWalkSurface surface;
        private readonly bool[] open = new bool[Size * Size];
        // Geometry is immutable. Each undirected grid edge is sampled at most
        // once, using the same clearance policy as the eventual movement.
        private readonly sbyte[] edges = new sbyte[Size * Size * 4];
        internal GridNavigation(Vec3 origin, WorldProp[] props)
        {
            this.origin = origin; surface = new ArenaWalkSurface(origin, props);
            for (var i = 0; i < open.Length; i++) open[i] = Walkable(Point(i));
        }
        private Vec3 Point(int index) => origin + new Vec3(index % Size * .5f - 6, 0, index / Size * .5f - 6);
        private List<int> Anchors(Vec3 point, bool start)
        {
            var result = new List<int>(4);
            var x = (point.X - origin.X + 6) * 2; var z = (point.Z - origin.Z + 6) * 2;
            var x0 = (int)Math.Floor(x); var x1 = (int)Math.Ceiling(x);
            var z0 = (int)Math.Floor(z); var z1 = (int)Math.Ceiling(z);
            for (var iz = z0; iz <= z1; iz++) for (var ix = x0; ix <= x1; ix++)
            {
                if (ix < 0 || iz < 0 || ix >= Size || iz >= Size) continue;
                var index = iz * Size + ix;
                if (open[index] && (start ? ClearSegment(point, Point(index)) : ClearSegment(Point(index), point))) result.Add(index);
            }
            result.Sort((a, b) => { var order = Vec3.Distance(point, Point(a)).CompareTo(Vec3.Distance(point, Point(b))); return order != 0 ? order : a.CompareTo(b); });
            return result;
        }
        internal bool Walkable(Vec3 point)
        {
            return surface.Walkable(point);
        }
        internal bool ClearSegment(Vec3 a, Vec3 b)
        {
            return surface.ClearSegment(a, b);
        }
        internal List<Vec3> Find(Vec3 from, Vec3 to)
        {
            if (!Walkable(from) || !Walkable(to)) return new List<Vec3>();
            var starts = Anchors(from, true); var ends = Anchors(to, false);
            if (starts.Count == 0 || ends.Count == 0) return new List<Vec3>();
            // Endpoints in the same cell need no detour through a rounded node,
            // but the real segment must pass the unchanged movement policy.
            foreach (var cell in starts) if (ends.Contains(cell) && ClearSegment(from, to)) return new List<Vec3> { from, to };
            var previous = new int[open.Length]; for (var i = 0; i < previous.Length; i++) previous[i] = -1;
            var targets = new bool[open.Length]; foreach (var cell in ends) targets[cell] = true;
            var queue = new Queue<int>(); foreach (var cell in starts) { queue.Enqueue(cell); previous[cell] = cell; }
            var end = -1;
            while (queue.Count > 0)
            {
                var cell = queue.Dequeue(); if (targets[cell]) { end = cell; break; }
                var x = cell % Size; var z = cell / Size;
                Visit(x + 1, z, cell, 0); Visit(x - 1, z, cell, 1); Visit(x, z + 1, cell, 2); Visit(x, z - 1, cell, 3);
            }
            if (end < 0) return new List<Vec3>();
            var path = new List<Vec3>(); var cursor = end;
            while (previous[cursor] != cursor) { path.Add(Point(cursor)); cursor = previous[cursor]; }
            path.Add(Point(cursor)); path.Reverse();
            if (Vec3.Distance(path[0], from) > 0) path.Insert(0, from);
            if (Vec3.Distance(path[path.Count - 1], to) > 0) path.Add(to);
            return path;
            void Visit(int x, int z, int parent, int direction)
            {
                if (x < 0 || z < 0 || x >= Size || z >= Size) return;
                var next = z * Size + x;
                if (!open[next] || previous[next] != -1) return;
                var edge = parent * 4 + direction;
                if (edges[edge] == 0)
                {
                    var value = (sbyte)(ClearSegment(Point(parent), Point(next)) ? 1 : -1);
                    edges[edge] = value; edges[next * 4 + (direction ^ 1)] = value;
                }
                if (edges[edge] < 0) return;
                previous[next] = parent; queue.Enqueue(next);
            }
        }
    }
}
