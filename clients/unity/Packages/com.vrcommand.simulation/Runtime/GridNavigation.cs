using System;
using System.Collections.Generic;

namespace VrCommand.Simulation
{
    // Uniform-cost 0.5m grid. Four-neighbour paths do not cut diagonally through corners.
    internal sealed class GridNavigation
    {
        private const int Size = 25;
        private const float Radius = .3f;
        private readonly Vec3 origin;
        private readonly WorldProp[] props;
        private readonly bool[] open = new bool[Size * Size];
        internal GridNavigation(Vec3 origin, WorldProp[] props)
        {
            this.origin = origin; this.props = props;
            for (var i = 0; i < open.Length; i++) open[i] = Walkable(Point(i));
        }
        private Vec3 Point(int index) => origin + new Vec3(index % Size * .5f - 6, 0, index / Size * .5f - 6);
        private int Index(Vec3 point)
        {
            var x = (int)Math.Round((point.X - origin.X + 6) * 2);
            var z = (int)Math.Round((point.Z - origin.Z + 6) * 2);
            return x < 0 || z < 0 || x >= Size || z >= Size ? -1 : z * Size + x;
        }
        internal bool Walkable(Vec3 point)
        {
            if (!point.Finite || Math.Abs(point.X - origin.X) > 6 - Radius || Math.Abs(point.Z - origin.Z) > 6 - Radius) return false;
            foreach (var prop in props)
            {
                if (prop.Feet.Y > 1.8f || prop.Center.Y + prop.HalfSize.Y < .1f) continue;
                var local = Vec3.Rotate(point - prop.Center, -prop.Yaw);
                if (Math.Abs(local.X) <= prop.HalfSize.X + Radius && Math.Abs(local.Z) <= prop.HalfSize.Z + Radius) return false;
            }
            return true;
        }
        internal bool ClearSegment(Vec3 a, Vec3 b)
        {
            // Small movement steps and centre samples conservatively check the swept actor radius.
            var distance = Vec3.Distance(a, b); var count = Math.Max(1, (int)Math.Ceiling(distance / .05f));
            for (var i = 0; i <= count; i++) if (!Walkable(a + (b - a) * ((float)i / count))) return false;
            return true;
        }
        internal List<Vec3> Find(Vec3 from, Vec3 to)
        {
            var start = Index(from); var end = Index(to);
            if (start < 0 || end < 0 || !open[start] || !open[end]) return new List<Vec3>();
            var previous = new int[open.Length]; for (var i = 0; i < previous.Length; i++) previous[i] = -1;
            var queue = new Queue<int>(); queue.Enqueue(start); previous[start] = start;
            while (queue.Count > 0 && previous[end] == -1)
            {
                var cell = queue.Dequeue(); var x = cell % Size; var z = cell / Size;
                Visit(x + 1, z, cell); Visit(x - 1, z, cell); Visit(x, z + 1, cell); Visit(x, z - 1, cell);
            }
            if (previous[end] == -1) return new List<Vec3>();
            var path = new List<Vec3>(); var cursor = end;
            while (cursor != start) { path.Add(Point(cursor)); cursor = previous[cursor]; }
            path.Add(Point(start)); path.Reverse(); return path;
            void Visit(int x, int z, int parent)
            {
                if (x < 0 || z < 0 || x >= Size || z >= Size) return;
                var next = z * Size + x;
                if (!open[next] || previous[next] != -1) return;
                previous[next] = parent; queue.Enqueue(next);
            }
        }
    }
}
