using System;

namespace VrCommand.Simulation
{
    // Shared planar footprint / swept-sample policy for authority, AI and desktop
    // prediction. This does not move tracked XR devices or replace MR calibration.
    public sealed class ArenaWalkSurface
    {
        public const float Radius = .3f;
        private readonly Vec3 origin;
        private readonly WorldProp[] props;
        public ArenaWalkSurface(Vec3 origin, WorldProp[] props)
        {
            if (!origin.Finite || props == null) throw new ArgumentException("Invalid walking surface.");
            this.origin = origin; this.props = (WorldProp[])props.Clone();
        }
        public bool Walkable(Vec3 point)
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
        public bool ClearSegment(Vec3 a, Vec3 b)
        {
            if (!Walkable(a) || !Walkable(b)) return false;
            var distance = Vec3.Distance(a, b); var count = Math.Max(1, (int)Math.Ceiling(distance / .05f));
            for (var i = 0; i <= count; i++) if (!Walkable(a + (b - a) * ((float)i / count))) return false;
            return true;
        }
        public Vec3 Constrain(Vec3 from, Vec3 desired)
        {
            if (!Walkable(from) || !desired.Finite) return from;
            var best = Clip(from, desired);
            // Each candidate is checked from the ORIGINAL position, so a slide
            // cannot cut a corner that the server's straight segment would reject.
            var x = Clip(from, new Vec3(desired.X, desired.Y, from.Z));
            var z = Clip(from, new Vec3(from.X, desired.Y, desired.Z));
            if (Vec3.Distance(x, desired) < Vec3.Distance(best, desired)) best = x;
            if (Vec3.Distance(z, desired) < Vec3.Distance(best, desired)) best = z;
            return best;
        }
        private Vec3 Clip(Vec3 from, Vec3 desired)
        {
            if (ClearSegment(from, desired)) return desired;
            var low = 0f; var high = 1f;
            for (var i = 0; i < 12; i++)
            {
                var middle = (low + high) * .5f;
                if (ClearSegment(from, from + (desired - from) * middle)) low = middle; else high = middle;
            }
            return from + (desired - from) * low;
        }
    }
}
