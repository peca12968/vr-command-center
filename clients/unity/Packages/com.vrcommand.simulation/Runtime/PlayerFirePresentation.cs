using System;

namespace VrCommand.Simulation
{
    public readonly struct PlayerFireState
    {
        public readonly long Sequence,TickPlusOne;
        public readonly Vec3 Origin,Direction;
        public PlayerFireState(long sequence,long tickPlusOne,Vec3 origin,Vec3 direction)
        {Sequence=sequence;TickPlusOne=tickPlusOne;Origin=origin;Direction=direction;}
    }
    public readonly struct PlayerFirePose
    {
        public readonly bool Flash;
        public readonly float Recoil;
        public PlayerFirePose(bool flash,float recoil){Flash=flash;Recoil=recoil;}
    }
    public static class PlayerFirePresentation
    {
        public const int Version=1;
        public const float PulseScale=1.2f;
        public static void Validate(long tick,PlayerFireState fire)
        {
            if(tick<0 || tick>EnvironmentPresentation.MaximumTick || fire.Sequence<0 || fire.TickPlusOne<0 || fire.TickPlusOne>tick+1
                || !fire.Origin.Finite || !fire.Direction.Finite)throw new ArgumentException("Invalid player fire clock.");
            if(fire.Sequence==0)
            {
                if(fire.TickPlusOne!=0 || fire.Origin.X!=0 || fire.Origin.Y!=0 || fire.Origin.Z!=0 || fire.Direction.X!=0 || fire.Direction.Y!=0 || fire.Direction.Z!=0)
                    throw new ArgumentException("Unwitnessed player fire pose.");
            }
            else if(fire.TickPlusOne==0 || Math.Abs(fire.Direction.Length-1)>.01f)throw new ArgumentException("Missing player fire ray.");
        }
        public static PlayerFirePose Pose(long tick,int health,bool connected,bool reloading,PlayerFireState fire)
        {
            Validate(tick,fire);if(health<0 || health>100)throw new ArgumentException("Invalid player health.");
            if(health==0 || !connected || fire.Sequence==0)return new PlayerFirePose(false,0);
            var age=tick-(fire.TickPlusOne-1);
            var recoil=reloading?0:age==0?.014f:age==1?.022f:age==2?.012f:age==3?.004f:0;
            return new PlayerFirePose(age<3,recoil);
        }
    }
}
