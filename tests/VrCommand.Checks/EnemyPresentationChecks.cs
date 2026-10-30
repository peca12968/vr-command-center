using System.Text.Json;
using VrCommand.Simulation;

internal static class EnemyPresentationChecks
{
    internal static string Vectors() => JsonSerializer.Serialize(
        (from direction in new[] { new Vec3(0,0,1), new Vec3(0,0,-1), new Vec3(1,0,0), new Vec3(-1,1,1).Normalized(), new Vec3(0,1,0) }
         from walking in new[] { false, true }
         from tick in new long[] { 0,1,3,6,9,11,12,1728000 }
         let p = EnemyPresentation.Pose(direction, walking, tick)
         select new { forward = new { x=direction.X,y=direction.Y,z=direction.Z }, walking, tick, yaw=p.Yaw,pitch=p.Pitch,stride=p.Stride }).ToArray());
    internal static void Run(Action<bool,string> check)
    {
        void Reject(Action action, string label) { try { action(); } catch (ArgumentException) { check(true,label); return; } throw new Exception(label); }
        var world = new ArenaWorld([3], []); var player = Guid.NewGuid(); var enemy = Guid.NewGuid();
        world.AddPlayer(player, 3, new(0,1.65f,-3)); world.AddEnemy(enemy,3,new(0,0,3),new(3,0,3));
        world.SetPolicy(AiBehavior.Patrol,false,Visibility.Clear,false);
        WorldRecordingPacket Capture(int version) => WorldRecordingPacket.Capture(world,1,0,1,0,0,_=>new(){kind="Simulated",left=new(new Vec3(-.2f,1.35f,-2.8f)),right=new(new Vec3(.2f,1.35f,-2.8f))},enemyPresentationVersion:version);
        var header = WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",[3],[],assetSet:WorldAssetSets.Combatants,enemyPresentationVersion:1);
        WorldRecordingValidation.Header(header); var initial = Capture(1); WorldRecordingValidation.Packet(header,initial,null);
        check(initial.frame.enemies[0].hasPresentation && !initial.frame.enemies[0].walking && initial.frame.enemies[0].forward.z == -1,
            "New opponent profile records an explicit initial facing without invented movement");
        header.enemyPresentationVersion=0; Reject(()=>WorldRecordingValidation.Header(header),"Humanoid profile cannot omit its recorded presentation policy"); header.enemyPresentationVersion=2;
        Reject(()=>WorldRecordingValidation.Header(header),"Unknown enemy presentation versions fail closed"); header.enemyPresentationVersion=1;
        initial.frame.enemies[0].hasPresentation=false; Reject(()=>WorldRecordingValidation.Packet(header,initial,null),"Versioned enemies cannot omit their saved pose"); initial.frame.enemies[0].hasPresentation=true;
        initial.frame.enemies[0].forward.x=2; Reject(()=>WorldRecordingValidation.Packet(header,initial,null),"Non-unit enemy facing is rejected"); initial.frame.enemies[0].forward.x=0;
        initial.frame.enemies[0].walking=true; Reject(()=>WorldRecordingValidation.Packet(header,initial,null),"Preparing enemies cannot claim a walking stride");
        var old=Capture(0); var legacy=WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",[3],[]);
        WorldRecordingValidation.Packet(legacy,old,null);
        check(!old.frame.enemies[0].hasPresentation && !old.frame.enemies[0].walking && old.frame.enemies[0].forward.ToVector().Length==0 && legacy.enemyPresentationVersion==0,
            "Default producers retain legacy enemies instead of retroactively assigning animation");
        old.frame.enemies[0].hasPresentation=true; Reject(()=>WorldRecordingValidation.Packet(legacy,old,null),"Unversioned packets cannot sneak in opponent presentation");
        world.SetPhase(WorldPhase.Running); for(var i=0;i<3;i++)world.Tick(); var moving=world.Snapshot(); var npc=moving.Enemies[0];
        check(npc.Walking && npc.Forward.X>.99f && Math.Abs(npc.Forward.Y)<.001 && npc.Feet.X>0 && world.Events().Length==0,
            "Patrol metadata follows the actual successful navigation step without generating combat events");
        var pose=EnemyPresentation.Pose(npc.Forward,npc.Walking,moving.Tick); world.SetPhase(WorldPhase.Paused); for(var i=0;i<40;i++)world.Tick(); var paused=world.Snapshot();
        var frozen=EnemyPresentation.Pose(paused.Enemies[0].Forward,paused.Enemies[0].Walking,paused.Tick);
        check(paused.Tick==moving.Tick && paused.Enemies[0].Feet.Equals(npc.Feet) && pose.Stride==18 && frozen.Stride==pose.Stride,
            "Pause preserves the exact recorded leg pose rather than continuing a local animation clock");
        world.SetPhase(WorldPhase.Running); world.SetPolicy(AiBehavior.Hold,true,Visibility.Clear,false); world.Tick(); npc=world.Snapshot().Enemies[0]; var shot=world.Events().Single(e=>e.Kind==WorldEventKind.EnemyShot);
        check(!npc.Walking && Vec3.Distance(npc.Forward,shot.Direction!.Value)<.00001 && Vec3.Distance(shot.Origin!.Value,npc.Feet+new Vec3(0,1.4f,0))<.00001
            && world.Snapshot().Players[0].Health==80,"Auto-attack facing matches the original authoritative shot and unchanged 20-point damage");
        check(EnemyPresentation.Pose(new(0,1,0),true,9).Pitch==-45 && EnemyPresentation.Pose(new(0,0,-1),true,9).Stride==-18
            && EnemyPresentation.Pose(new(0,0,1),false,9).Stride==0,"Humanoid view clamps head pitch and produces bounded opposite-leg gait or a standing pose");
        Reject(()=>EnemyPresentation.Pose(new(),true,0),"Zero enemy direction is rejected before rendering");
        Reject(()=>EnemyPresentation.Pose(new(0,0,1),true,1728001),"Enemy animation rejects a tick beyond the recording time budget");
        Reject(()=>EnemyPresentation.Pose(new(float.NaN,0,1),false,0),"Non-finite enemy direction fails closed");
    }
}
