using System;

namespace VrCommand.Simulation
{
    public readonly struct WeaponViewPose
    {
        public readonly Vec3 MagazineOffset, LeftHand;
        public readonly float MagazineRoll, LeftRoll;
        public readonly bool MagazineVisible, HandsVisible;
        public WeaponViewPose(Vec3 offset, Vec3 left, float roll, float leftRoll, bool visible, bool hands)
        { MagazineOffset=offset;LeftHand=left;MagazineRoll=roll;LeftRoll=leftRoll;MagazineVisible=visible;HandsVisible=hands; }
    }
    // Cosmetic state driven exclusively by accepted simulation ticks. No local
    // reload timer, transformed tracking data, muzzle movement or ammo changes.
    public static class WeaponPresentation
    {
        public const int Version=1;
        public static readonly Vec3 RightGrip=new Vec3(0,-.15f,-.535f), LeftGrip=new Vec3(0,0,-.22f);
        private static readonly Vec3 MagazineGrip=new Vec3(0,-.17f,-.4025f), Lowered=new Vec3(-.16f,-.32f,0);
        public static void Validate(long tick,int health,bool reloading,long until)
        {
            if(tick<0 || tick>EnvironmentPresentation.MaximumTick || health<0 || health>100 || until<0 || until>EnvironmentPresentation.MaximumTick+30
                || (reloading ? until<30 || until-30>tick || (health>0 && until<=tick) : until!=0)) throw new ArgumentException("Invalid saved weapon presentation.");
        }
        public static WeaponViewPose Pose(long tick,int health,bool connected,bool simulated,bool reloading,long until)
        {
            Validate(tick,health,reloading,until);var hands=simulated && connected && health>0;
            if(!reloading || !connected || health==0) return new WeaponViewPose(default,LeftGrip,0,0,true,hands);
            var elapsed=tick-(until-30);Vec3 offset,left;float roll,leftRoll;
            if(elapsed<5) { offset=default;roll=0;left=Mix(LeftGrip,MagazineGrip,elapsed/5f);leftRoll=0; }
            else if(elapsed<11) { var t=(elapsed-5)/6f;offset=Lowered*t;roll=-20*t;left=MagazineGrip+offset;leftRoll=roll; }
            else if(elapsed<18) { offset=Lowered;roll=-20;left=MagazineGrip+offset;leftRoll=roll; }
            else if(elapsed<25) { var t=(25-elapsed)/7f;offset=Lowered*t;roll=-20*t;left=MagazineGrip+offset;leftRoll=roll; }
            else { offset=default;roll=0;left=Mix(MagazineGrip,LeftGrip,(elapsed-25)/5f);leftRoll=0; }
            return new WeaponViewPose(offset,left,roll,leftRoll,elapsed<12 || elapsed>=18,hands);
        }
        private static Vec3 Mix(Vec3 a,Vec3 b,float t)=>a+(b-a)*t;
    }
}
