using System;

namespace VrCommand.Simulation
{
    public readonly struct FloorXZ
    {
        public readonly double X, Z;
        public FloorXZ(double x, double z) { X = x; Z = z; }
        public bool InRange(double limit) => Math.Abs(X) <= limit && Math.Abs(Z) <= limit;
        public double Length => Math.Sqrt(X * X + Z * Z);
        public static FloorXZ operator -(FloorXZ a, FloorXZ b) => new FloorXZ(a.X - b.X, a.Z - b.Z);
        public static FloorXZ operator +(FloorXZ a, FloorXZ b) => new FloorXZ(a.X + b.X, a.Z + b.Z);
    }

    public enum FloorFitResult { Valid, InvalidPoints, ShortBaseline, NarrowReference, OutsideTolerance }

    public readonly struct FloorTransform
    {
        private readonly double sine, cosine;
        public readonly double YawDegrees;
        public readonly FloorXZ Translation;
        internal FloorTransform(double yaw, FloorXZ trackingA, FloorXZ roomA)
        {
            sine = Math.Sin(yaw);
            cosine = Math.Cos(yaw);
            YawDegrees = Math.IEEERemainder(yaw * 180 / Math.PI, 360);
            Translation = roomA - new FloorXZ(cosine * trackingA.X + sine * trackingA.Z, -sine * trackingA.X + cosine * trackingA.Z);
        }
        public FloorXZ Map(FloorXZ point) => new FloorXZ(cosine * point.X + sine * point.Z, -sine * point.X + cosine * point.Z) + Translation;
    }

    public static class RoomFloorFit
    {
        public const string Profile = "room-floor-alignment-v1";
        public const double TrackingLimit = 100, Tolerance = .05;
        private const double MinimumSpacing = .5, ComparisonEpsilon = 1e-9;

        public static FloorFitResult Solve(FloorXZ[] room, FloorXZ[] tracking, out FloorTransform transform)
        {
            transform = default;
            if (room == null || tracking == null || room.Length != 3 || tracking.Length != 3) return FloorFitResult.InvalidPoints;
            for (var i = 0; i < 3; i++)
                if (!room[i].InRange(ArenaLayout.RoomHalfSize) || !tracking[i].InRange(TrackingLimit)) return FloorFitResult.InvalidPoints;

            var target = room[1] - room[0];
            var observed = tracking[1] - tracking[0];
            var targetLength = target.Length;
            if (targetLength < MinimumSpacing || observed.Length < MinimumSpacing) return FloorFitResult.ShortBaseline;
            var third = room[2] - room[0];
            if (Math.Abs(target.X * third.Z - target.Z * third.X) / targetLength < MinimumSpacing) return FloorFitResult.NarrowReference;

            // Unity yaw turns +Z towards +X. Fit A/B before looking at the independent C measurement.
            var yaw = Math.Atan2(observed.Z, observed.X) - Math.Atan2(target.Z, target.X);
            transform = new FloorTransform(yaw, tracking[0], room[0]);
            for (var i = 0; i < 3; i++)
                if ((transform.Map(tracking[i]) - room[i]).Length > Tolerance + ComparisonEpsilon) return FloorFitResult.OutsideTolerance;
            return FloorFitResult.Valid;
        }
    }
}
