using System;

namespace VrCommand.Simulation
{
    public readonly struct Vec3
    {
        public float X { get; }
        public float Y { get; }
        public float Z { get; }
        public Vec3(float x, float y, float z) { X = x; Y = y; Z = z; }
        public bool Finite => Valid(X) && Valid(Y) && Valid(Z);
        public float Length => (float)Math.Sqrt(Dot(this, this));
        public Vec3 Normalized()
        {
            var length = Length;
            if (!Finite || !Valid(length) || length < 0.00001f) throw new ArgumentException("Direction must be finite and nonzero.");
            return this * (1 / length);
        }
        public static bool Valid(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
        public static Vec3 operator +(Vec3 a, Vec3 b) => new Vec3(a.X + b.X, a.Y + b.Y, a.Z + b.Z);
        public static Vec3 operator -(Vec3 a, Vec3 b) => new Vec3(a.X - b.X, a.Y - b.Y, a.Z - b.Z);
        public static Vec3 operator *(Vec3 a, float scale) => new Vec3(a.X * scale, a.Y * scale, a.Z * scale);
        public static float Dot(Vec3 a, Vec3 b) => a.X * b.X + a.Y * b.Y + a.Z * b.Z;
        public static float Distance(Vec3 a, Vec3 b) => (a - b).Length;
        public static Vec3 Flat(Vec3 value) => new Vec3(value.X, 0, value.Z);
        internal static Vec3 Rotate(Vec3 value, float degrees)
        {
            var angle = degrees * Math.PI / 180;
            var sin = (float)Math.Sin(angle); var cos = (float)Math.Cos(angle);
            return new Vec3(cos * value.X + sin * value.Z, value.Y, -sin * value.X + cos * value.Z);
        }
    }

    public static class ArenaGeometry
    {
        // Returns the first positive intersection, including zero when the ray starts inside a solid.
        public static float? RayBox(Vec3 origin, Vec3 direction, Vec3 center, Vec3 halfSize, float yaw, float range)
        {
            if (!origin.Finite || !direction.Finite || !center.Finite || !halfSize.Finite || !Vec3.Valid(yaw)
                || !Vec3.Valid(range) || range <= 0 || halfSize.X <= 0 || halfSize.Y <= 0 || halfSize.Z <= 0)
                throw new ArgumentException("Invalid ray or box.");
            direction = direction.Normalized();
            var local = Vec3.Rotate(origin - center, -yaw);
            var ray = Vec3.Rotate(direction, -yaw);
            var near = 0f; var far = range;
            if (!Slab(local.X, ray.X, halfSize.X, ref near, ref far)
                || !Slab(local.Y, ray.Y, halfSize.Y, ref near, ref far)
                || !Slab(local.Z, ray.Z, halfSize.Z, ref near, ref far)) return null;
            return near;
        }
        private static bool Slab(float origin, float direction, float half, ref float near, ref float far)
        {
            if (Math.Abs(direction) < 0.000001f) return Math.Abs(origin) <= half;
            var a = (-half - origin) / direction; var b = (half - origin) / direction;
            near = Math.Max(near, Math.Min(a, b)); far = Math.Min(far, Math.Max(a, b));
            return near <= far;
        }
    }
}
