using System;

namespace VrCommand.Simulation
{
    public readonly struct EnemyArmPose
    {
        public readonly Vec3 Shoulder, Elbow, Wrist;
        public EnemyArmPose(Vec3 shoulder, Vec3 elbow, Vec3 wrist) { Shoulder = shoulder; Elbow = elbow; Wrist = wrist; }
    }
    public readonly struct ArmedEnemyPose
    {
        public readonly EnemyViewPose Body;
        public readonly float GunPitch;
        public readonly EnemyArmPose Left, Right;
        public ArmedEnemyPose(EnemyViewPose body, float pitch, EnemyArmPose left, EnemyArmPose right)
        { Body = body; GunPitch = pitch; Left = left; Right = right; }
    }
    // Cosmetic two-bone solve in yaw-local body space. Never adjusts authority,
    // recorded feet/direction or tracked player joints to fit the model.
    public static class ArmedEnemyPresentation
    {
        public static readonly Vec3 Muzzle = new Vec3(0, 1.4f, 0);
        public static readonly Vec3 LeftGrip = new Vec3(0, -.085f, -.035f), RightGrip = new Vec3(0, -.11f, -.075f);
        public const float UpperLength = .22f, LowerLength = .25f;
        public static ArmedEnemyPose Pose(Vec3 forward, bool walking, long tick)
        {
            var body = EnemyPresentation.Pose(forward, walking, tick);
            var unit = forward.Normalized();
            var pitch = (float)(-Math.Asin(Math.Max(-1, Math.Min(1, unit.Y))) * 180 / Math.PI);
            return new ArmedEnemyPose(body, pitch, Arm(true, pitch), Arm(false, pitch));
        }
        public static Vec3 Pitch(Vec3 p, float degrees)
        {
            var angle = degrees * Math.PI / 180; var sin = (float)Math.Sin(angle); var cos = (float)Math.Cos(angle);
            return new Vec3(p.X, cos * p.Y - sin * p.Z, sin * p.Y + cos * p.Z);
        }
        private static EnemyArmPose Arm(bool left, float pitch)
        {
            var side = left ? -1f : 1f;
            var shoulder = new Vec3(side * .215f, 1.37f, -.235f);
            var grip = left ? LeftGrip : RightGrip;
            var wrist = Muzzle + Pitch(grip + new Vec3(side * .07f, 0, 0), pitch);
            return Solve(shoulder, wrist, new Vec3(side * .36f, 1.10f, .04f), UpperLength, LowerLength);
        }
        public static EnemyArmPose Solve(Vec3 shoulder, Vec3 wrist, Vec3 hint, float upper, float lower)
        {
            var delta = wrist - shoulder; var distance = delta.Length;
            if (!shoulder.Finite || !wrist.Finite || !hint.Finite || !Vec3.Valid(upper) || !Vec3.Valid(lower) || upper <= 0 || lower <= 0
                || distance < .00001f || distance > upper + lower || distance < Math.Abs(upper - lower))
                throw new ArgumentException("Unreachable cosmetic arm.");
            var axis = delta * (1 / distance); var bend = hint - shoulder;
            bend = bend - axis * Vec3.Dot(bend, axis);
            if (bend.Length < .00001f)
            {
                var fallback = Math.Abs(axis.Y) < .9f ? new Vec3(0, 1, 0) : new Vec3(1, 0, 0);
                bend = fallback - axis * Vec3.Dot(fallback, axis);
            }
            var along = (upper * upper - lower * lower + distance * distance) / (2 * distance);
            var height = (float)Math.Sqrt(Math.Max(0, upper * upper - along * along));
            return new EnemyArmPose(shoulder, shoulder + axis * along + bend.Normalized() * height, wrist);
        }
    }
}
