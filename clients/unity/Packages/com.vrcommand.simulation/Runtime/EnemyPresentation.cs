using System;

namespace VrCommand.Simulation
{
    public readonly struct EnemyViewPose
    {
        public readonly float Yaw, Pitch, Stride;
        public EnemyViewPose(float yaw, float pitch, float stride) { Yaw = yaw; Pitch = pitch; Stride = stride; }
    }
    // Recorded tick, not local wall time: pause and direct replay seeks produce
    // the same stylised pose. This is not foot IK or a measured tracking rig.
    public static class EnemyPresentation
    {
        public const int Version = 1;
        public static EnemyViewPose Pose(Vec3 forward, bool walking, long tick)
        {
            if (!forward.Finite || Math.Abs(forward.Length - 1) > .01f || tick < 0 || tick > EnvironmentPresentation.MaximumTick)
                throw new ArgumentException("Invalid enemy presentation state.");
            var yaw = Math.Atan2(forward.X, forward.Z) * 180 / Math.PI;
            var pitch = Math.Max(-45, Math.Min(45, -Math.Asin(Math.Max(-1, Math.Min(1, forward.Y))) * 180 / Math.PI));
            var stride = walking ? Math.Sin((tick % 12) * Math.PI / 6) * 18 : 0;
            return new EnemyViewPose((float)yaw, (float)pitch, (float)stride);
        }
    }
}
