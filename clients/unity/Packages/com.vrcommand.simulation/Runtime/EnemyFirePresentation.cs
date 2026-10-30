using System;

namespace VrCommand.Simulation
{
    public readonly struct EnemyFireState
    {
        public readonly long Sequence, TickPlusOne;
        public readonly Vec3 Origin, Direction;
        public EnemyFireState(long sequence, long tickPlusOne, Vec3 origin, Vec3 direction)
        { Sequence=sequence; TickPlusOne=tickPlusOne; Origin=origin; Direction=direction; }
    }
    public readonly struct EnemyFirePose
    {
        public readonly bool Flash;
        public readonly float Recoil;
        public EnemyFirePose(bool flash,float recoil) { Flash=flash; Recoil=recoil; }
    }
    public static class EnemyFirePresentation
    {
        public const int Version=1;
        public static void Validate(long tick,EnemyFireState fire)
        {
            if(tick<0 || tick>EnvironmentPresentation.MaximumTick || fire.Sequence<0 || fire.TickPlusOne<0 || fire.TickPlusOne>tick+1
                || !fire.Origin.Finite || !fire.Direction.Finite)throw new ArgumentException("Invalid enemy fire clock.");
            if(fire.Sequence==0)
            {
                if(fire.TickPlusOne!=0 || fire.Origin.X!=0 || fire.Origin.Y!=0 || fire.Origin.Z!=0 || fire.Direction.X!=0 || fire.Direction.Y!=0 || fire.Direction.Z!=0)throw new ArgumentException("Unwitnessed enemy fire pose.");
            }
            else if(fire.TickPlusOne==0 || Math.Abs(fire.Direction.Length-1)>.01f)throw new ArgumentException("Missing enemy fire ray.");
        }
        // Saved simulation tick only: pause, replay and direct seek agree.
        public static EnemyFirePose Pose(long tick,int health,EnemyFireState fire)
        {
            Validate(tick,fire);if(health<0 || health>100)throw new ArgumentException("Invalid enemy health.");
            if(health==0 || fire.Sequence==0)return new EnemyFirePose(false,0);
            var age=tick-(fire.TickPlusOne-1);
            var recoil=age==0?.012f:age==1?.018f:age==2?.010f:age==3?.004f:age==4?.001f:0;
            return new EnemyFirePose(age<3,recoil);
        }
    }
}
