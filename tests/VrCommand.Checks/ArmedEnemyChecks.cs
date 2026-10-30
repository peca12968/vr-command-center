using System.Text.Json;
using VrCommand.Simulation;

internal static class ArmedEnemyChecks
{
    private static object Point(Vec3 v)=>new {x=v.X,y=v.Y,z=v.Z};
    internal static string Vectors()=>JsonSerializer.Serialize(
        (from yaw in new[]{-180,-90,0,45,180}
         from pitch in new[]{-90,-80,-45,0,45,80,90}
         from tick in new long[]{0,3,9,1728000}
         let a=yaw*Math.PI/180 let b=pitch*Math.PI/180
         let forward=new Vec3((float)(Math.Sin(a)*Math.Cos(b)),(float)-Math.Sin(b),(float)(Math.Cos(a)*Math.Cos(b)))
         let p=ArmedEnemyPresentation.Pose(forward,true,tick)
         select new {forward=Point(forward),tick,gunPitch=p.GunPitch,
             left=new {shoulder=Point(p.Left.Shoulder),elbow=Point(p.Left.Elbow),wrist=Point(p.Left.Wrist)},
             right=new {shoulder=Point(p.Right.Shoulder),elbow=Point(p.Right.Elbow),wrist=Point(p.Right.Wrist)}}).ToArray());
    internal static void Run(Action<bool,string> check)
    {
        for(var pitch=-90;pitch<=90;pitch++)
        {
            var a=pitch*Math.PI/180;var forward=new Vec3(0,(float)-Math.Sin(a),(float)Math.Cos(a));
            var pose=ArmedEnemyPresentation.Pose(forward,false,0);
            foreach(var arm in new[]{pose.Left,pose.Right})
                if(Math.Abs(Vec3.Distance(arm.Shoulder,arm.Elbow)-.22f)>.00001f || Math.Abs(Vec3.Distance(arm.Elbow,arm.Wrist)-.25f)>.00001f)
                    throw new Exception("Cosmetic arm length changed.");
            if(Vec3.Distance(ArmedEnemyPresentation.Pitch(new(0,0,1),pose.GunPitch),forward)>.00001f)throw new Exception("Pistol direction diverges.");
        }
        check(true,"Armed NPCs keep both bone lengths and the full authoritative pitch across 181 directions");
        var fallback=ArmedEnemyPresentation.Solve(new(),new(0,.3f,0),new(0,.1f,0),.22f,.25f);
        check(fallback.Elbow.Finite && Math.Abs(Vec3.Distance(fallback.Elbow,fallback.Wrist)-.25f)<.00001f,"Collinear cosmetic elbow hints use a finite deterministic fallback");
        try{ArmedEnemyPresentation.Solve(new(),new(0,2,0),new(),.22f,.25f);throw new Exception("Unreachable arm accepted");}
        catch(ArgumentException){check(true,"Cosmetic solve rejects unreachable grips instead of moving authority feet or muzzle");}
        var h=WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",[3],[],assetSet:WorldAssetSets.ArmedCombatants,enemyPresentationVersion:1,weaponPresentationVersion:1);
        WorldRecordingValidation.Header(h);check(WorldAssetSets.Supported(h.assetSet),"Armed profile explicitly composes the existing enemy and weapon contracts");
        foreach(var field in new[]{"enemy","weapon"})
        {
            h.enemyPresentationVersion=field=="enemy"?0:1;h.weaponPresentationVersion=field=="weapon"?0:1;
            try{WorldRecordingValidation.Header(h);throw new Exception("Missing armed contract accepted");}
            catch(ArgumentException){check(true,"Armed profile rejects a missing "+field+" presentation version");}
        }
        var world=new ArenaWorld([3],[]);var id=Guid.NewGuid();world.AddEnemy(Guid.NewGuid(),3,new(0,0,3),new(0,0,3));world.AddPlayer(id,3,new(0,1.65f,-3));
        world.SetPhase(WorldPhase.Running);world.SetPolicy(AiBehavior.Hold,true,Visibility.Clear,false);world.Tick();
        var enemy=world.Snapshot().Enemies[0];var shot=world.Events().Single(e=>e.Kind==WorldEventKind.EnemyShot);
        check(Vec3.Distance(shot.Origin!.Value,enemy.Feet+ArmedEnemyPresentation.Muzzle)<.00001f && world.PlayerSnapshot(id).Health==80,
            "Armed presentation still uses the original feet+(0,1.4,0) ray and unchanged damage rules");
    }
}
