using System;
namespace VrCommand.Simulation
{
    public readonly struct PlayerViewPose
    {
        public readonly Vec3 Feet;public readonly float Yaw,HeightScale,Stride;public readonly bool Arms;
        public readonly EnemyArmPose Left,Right;
        public PlayerViewPose(Vec3 feet,float yaw,float scale,float stride,bool arms,EnemyArmPose left,EnemyArmPose right)
        {Feet=feet;Yaw=yaw;HeightScale=scale;Stride=stride;Arms=arms;Left=left;Right=right;}
    }
    // Approximate silhouette only. Never modifies a tracked joint or authority.
    public static class PlayerPresentation
    {
        public const int Version=1,WalkHoldTicks=4;
        public static PlayerViewPose Pose(Vec3 head,Vec3 headForward,Vec3 muzzle,Vec3 gunForward,bool walking,long tick,int health,bool connected,bool simulated,bool reloading,long until)
        {
            WeaponPresentation.Validate(tick,health,reloading,until);
            if(!head.Finite||head.Y<.45f||head.Y>2.4f||!headForward.Finite||Math.Abs(headForward.Length-1)>.01f||!muzzle.Finite||!gunForward.Finite||Math.Abs(gunForward.Length-1)>.01f)throw new ArgumentException("Invalid player silhouette.");
            var yaw=(float)(Math.Atan2(headForward.X,headForward.Z)*180/Math.PI);var scale=head.Y/1.65f;
            var stride=walking?(float)(Math.Sin((tick%12)*Math.PI/6)*18):0;
            var feet=Vec3.Flat(head);var weapon=WeaponPresentation.Pose(tick,health,connected,simulated,reloading,until);
            var left=Arm(-1,feet,yaw,scale,muzzle,gunForward,weapon.LeftHand+new Vec3(-.06f,0,-.06f));
            var right=Arm(1,feet,yaw,scale,muzzle,gunForward,WeaponPresentation.RightGrip+new Vec3(.06f,0,-.06f));
            var arms=weapon.HandsVisible&&left.Item1&&right.Item1;
            return new PlayerViewPose(feet,yaw,scale,stride,arms,left.Item2,right.Item2);
        }
        public static Vec3 Yaw(Vec3 p,float degrees)
        {var a=degrees*Math.PI/180;var s=(float)Math.Sin(a);var c=(float)Math.Cos(a);return new Vec3(c*p.X+s*p.Z,p.Y,-s*p.X+c*p.Z);}
        // A roll-free weapon basis, identical to the existing rifle alignment.
        public static Vec3 Gun(Vec3 p,Vec3 forward)
        {
            var f=forward.Normalized();var yaw=(float)(Math.Atan2(f.X,f.Z)*180/Math.PI);var pitch=(float)(-Math.Asin(Math.Max(-1,Math.Min(1,f.Y)))*180/Math.PI);
            return Yaw(ArmedEnemyPresentation.Pitch(p,pitch),yaw);
        }
        private static Tuple<bool,EnemyArmPose> Arm(float side,Vec3 feet,float yaw,float scale,Vec3 muzzle,Vec3 forward,Vec3 grip)
        {
            var shoulder=feet+Yaw(new Vec3(side*.215f,1.37f*scale,-.035f),yaw);var wrist=muzzle+Gun(grip,forward);
            var d=Vec3.Distance(shoulder,wrist);if(d<.03f||d>1.24f)return Tuple.Create(false,default(EnemyArmPose));
            var stretch=Math.Max(1,d/.619f);var upper=.30f*stretch;var lower=.32f*stretch;
            return Tuple.Create(true,ArmedEnemyPresentation.Solve(shoulder,wrist,feet+Yaw(new Vec3(side*.42f,1.05f*scale,-.12f),yaw),upper,lower));
        }
    }
}
