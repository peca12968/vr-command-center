using System;
using System.Collections.Generic;
using System.Linq;

namespace VrCommand.Simulation
{
    public sealed class ArenaLayoutIssue
    {
        public string Code { get; }
        public int PropIndex { get; }
        public int OtherPropIndex { get; }
        public int Seat { get; }
        public ArenaLayoutIssue(string code, int propIndex = -1, int otherPropIndex = -1, int seat = -1)
        { Code = code; PropIndex = propIndex; OtherPropIndex = otherPropIndex; Seat = seat; }
    }
    public sealed class ArenaLayoutResult
    {
        public ArenaLayoutIssue[] Issues { get; }
        public int[] InvalidProps { get; }
        public int IssueCount { get; }
        public int? EnemyCapacityPerRoom { get; }
        public int RequestedEnemiesPerRoom { get; }
        public bool Truncated => IssueCount > Issues.Length;
        public bool Valid => IssueCount == 0;
        internal ArenaLayoutResult(ArenaLayoutIssue[] issues, int[] invalid, int count, int? capacity, int requested)
        { Issues = issues; InvalidProps = invalid; IssueCount = count; EnemyCapacityPerRoom = capacity; RequestedEnemiesPerRoom = requested; }
    }

    // New-start preflight for the existing rules 0.8.0 room. This does not change
    // collision, replay old acceptances, validate MR or prove tactical reachability.
    public static class ArenaLayout
    {
        public const int Version = 1, MaxIssues = 128;
        public const float RoomHalfSize = 6, Tolerance = .0001f;
        private sealed class Box
        {
            internal WorldProp Prop = null!;
            internal Vec3 Right, Forward;
            internal Box(WorldProp prop) { Prop = prop; Right = Vec3.Rotate(new Vec3(1, 0, 0), prop.Yaw); Forward = Vec3.Rotate(new Vec3(0, 0, 1), prop.Yaw); }
            internal float Radius(Vec3 axis) => Math.Abs(Vec3.Dot(Right, axis)) * Prop.HalfSize.X + Math.Abs(Vec3.Dot(Forward, axis)) * Prop.HalfSize.Z;
        }
        public static ArenaLayoutResult Inspect(ManagedProp[] definitions, int enemyCount, int roomCount)
        {
            if (definitions == null || definitions.Length > 500 || enemyCount < 0 || enemyCount > 100 || (roomCount != 1 && roomCount != 5))
                throw new ArgumentException("Invalid layout inspection context.");
            var issues = new List<ArenaLayoutIssue>(); var invalid = new HashSet<int>(); var boxes = new Box?[definitions.Length];
            var total = 0; var canPlan = true;
            void Add(string code, int index = -1, int other = -1, int seat = -1)
            {
                total++; if (index >= 0) invalid.Add(index); if (other >= 0) invalid.Add(other);
                if (issues.Count < MaxIssues) issues.Add(new ArenaLayoutIssue(code, index, other, seat));
            }
            for (var i = 0; i < definitions.Length; i++)
            {
                var item = definitions[i];
                if (item == null || item.position == null || !item.position.Vector.Finite || !Vec3.Valid(item.yawDegrees))
                { Add("InvalidProp", i); canPlan = false; continue; }
                if (item.assetId != "sandbag" && item.assetId != "barrel")
                { Add("UnsupportedAsset", i); canPlan = false; continue; }
                if (Math.Abs(item.yawDegrees) > 360)
                { Add("YawOutOfRange", i); canPlan = false; continue; }
                var prop = new WorldProp(new Guid(i + 1, 0, 0, new byte[8]), 3, item.assetId == "barrel" ? PropKind.Barrel : PropKind.Sandbag, item.position.Vector, item.yawDegrees);
                var box = new Box(prop); var usable = true;
                if (Math.Abs(prop.Feet.Y) > .001f) { Add("NotFloorLevel", i); canPlan = usable = false; }
                if (Math.Abs(prop.Feet.X) + box.Radius(new Vec3(1, 0, 0)) > RoomHalfSize + Tolerance
                    || Math.Abs(prop.Feet.Z) + box.Radius(new Vec3(0, 0, 1)) > RoomHalfSize + Tolerance)
                { Add("OutsideRoom", i); canPlan = usable = false; }
                if (!usable) continue;
                boxes[i] = box;
                var surface = new ArenaWalkSurface(new Vec3(), new[] { prop });
                for (var seat = 0; seat < 5; seat++) if (!surface.Walkable(ArenaSession.Spawn(3, seat))) Add("SpawnBlocked", i, seat: seat);
            }
            for (var i = 0; i < boxes.Length; i++) for (var j = i + 1; j < boxes.Length; j++)
            {
                var a = boxes[i]; var b = boxes[j]; if (a == null || b == null) continue;
                var delta = Vec3.Flat(b.Prop.Center - a.Prop.Center);
                bool Separates(Vec3 axis) => a.Radius(axis) + b.Radius(axis) - Math.Abs(Vec3.Dot(delta, axis)) <= Tolerance;
                if (!Separates(a.Right) && !Separates(a.Forward) && !Separates(b.Right) && !Separates(b.Forward)) Add("Overlap", i, j);
            }
            var requested = (enemyCount + roomCount - 1) / roomCount;
            int? capacity = canPlan ? EnemyCandidates(3, boxes.Where(box => box != null).Select(box => box!.Prop).ToArray()).Count : (int?)null;
            if (capacity.HasValue && requested > capacity.Value) Add("EnemySpawnCapacity");
            return new ArenaLayoutResult(issues.ToArray(), invalid.OrderBy(i => i).ToArray(), total, capacity, requested);
        }
        // The same ordered 0.75m candidate grid is used by actual enemy planning.
        // Grid spacing exceeds the planner's 0.7m separation for an empty world.
        internal static List<Vec3> EnemyCandidates(int room, WorldProp[] geometry, Func<Vec3, bool>? available = null)
        {
            var origin = ArenaWorld.RoomOrigin(room);
            var navigation = new GridNavigation(origin, geometry.Where(prop => prop.RoomId == room).ToArray());
            var result = new List<Vec3>();
            for (var z = -1f; z <= 5; z += .75f) for (var x = -4.5f; x <= 4.5f; x += .75f)
            {
                var point = origin + new Vec3(x, 0, z); if (navigation.Walkable(point) && (available == null || available(point))) result.Add(point);
            }
            return result;
        }
    }
}
