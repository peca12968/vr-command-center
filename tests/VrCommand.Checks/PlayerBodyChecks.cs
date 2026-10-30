using System.Text.Json;
using VrCommand.Simulation;
internal static class PlayerBodyChecks
{
    internal static string Vectors()=>JsonSerializer.Serialize((from tick in new long[]{0,1,3,6,11,80} from yaw in new[]{0f,90f,-120f} from height in new[]{.6f,1.65f,2.4f}
        let head=new Vec3(2,height,-3) let f=PlayerPresentation.Yaw(new Vec3(0,0,1),yaw)
        let p=PlayerPresentation.Pose(head,f,head+PlayerPresentation.Yaw(new Vec3(.18f,-.12f,.9f),yaw),f,true,tick,100,true,true,false,0)
        select new{tick,inputYaw=yaw,height,p.Yaw,p.HeightScale,p.Stride,p.Arms,left=new[]{p.Left.Elbow.X,p.Left.Elbow.Y,p.Left.Elbow.Z},right=new[]{p.Right.Wrist.X,p.Right.Wrist.Y,p.Right.Wrist.Z}}));
    internal static void Run(Action<bool,string> check)
    {
        var w=new ArenaWorld([3],[]);var id=Guid.NewGuid();w.AddPlayer(id,3,new Vec3(0,1.65f,0));w.SetPlayerPose(id,new Vec3(.1f,1.65f,0),new Vec3(.1f,1.5f,.8f),new Vec3(0,0,1));
        check(!w.PlayerSnapshot(id).Walking,"Preparing movement cannot invent a walking phase");w.SetPhase(WorldPhase.Running);
        w.SetPlayerPose(id,new Vec3(.2f,1.65f,0),new Vec3(.2f,1.5f,.8f),new Vec3(0,0,1));check(w.PlayerSnapshot(id).Walking,"Only accepted planar movement starts player presentation stride");
        w.SetPhase(WorldPhase.Paused);var before=w.Snapshot();w.Tick();check(w.PlayerSnapshot(id).Walking&&w.Snapshot().Tick==before.Tick,"Paused saved clock preserves player walking pose");w.SetPhase(WorldPhase.Running);
        for(var i=0;i<5;i++)w.Tick();check(!w.PlayerSnapshot(id).Walking,"Idle player clears presentation movement after four ticks");
        w.SetPlayerPose(id,new Vec3(.2f,1.7f,0),new Vec3(.2f,1.5f,.8f),new Vec3(0,0,1));check(!w.PlayerSnapshot(id).Walking,"Height or aim-only changes do not start a planar stride");
        try{w.SetPlayerPose(id,new Vec3(20,1.65f,0),new Vec3(20,1.5f,.8f),new Vec3(0,0,1));throw new Exception("Invalid pose accepted");}catch(ArgumentException){check(!w.PlayerSnapshot(id).Walking,"Rejected movement cannot change saved presentation");}
        w.SetPlayerPose(id,new Vec3(.3f,1.65f,0),new Vec3(.3f,1.5f,.8f),new Vec3(0,0,1));w.SetPlayerConnected(id,false);check(!w.PlayerSnapshot(id).Walking,"Disconnected player never claims active walking");
        var head=new Vec3(0,1.65f,0);var f=new Vec3(0,0,1);var muzzle=head+new Vec3(.18f,-.12f,.9f);
        var p=PlayerPresentation.Pose(head,f,muzzle,f,true,3,100,true,true,false,0);check(p.Arms&&Math.Abs(p.Stride-18)<.001f&&p.Feet.Y==0&&p.HeightScale==1,"Military silhouette follows saved eye height, floor and tick phase");
        var expected=muzzle+WeaponPresentation.RightGrip+new Vec3(.06f,0,-.06f);check(Vec3.Distance(expected,p.Right.Wrist)<.00001f,"Simulated arm ends at existing cosmetic glove instead of aim pointer");
        var tracked=PlayerPresentation.Pose(head,f,muzzle,f,true,3,100,true,false,false,0);check(!tracked.Arms&&tracked.Stride==p.Stride,"Tracked presentation keeps real hand markers without invented grip arms");
        var reload=PlayerPresentation.Pose(head,f,muzzle,f,false,12,100,true,true,true,30);var wp=WeaponPresentation.Pose(12,100,true,true,true,30);check(Vec3.Distance(reload.Left.Wrist,muzzle+wp.LeftHand+new Vec3(-.06f,0,-.06f))<.00001f,"Simulated left arm follows saved reload glove without changing the muzzle");
        var h=WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",[3],[],assetSet:WorldAssetSets.PlayerBody,enemyPresentationVersion:1,weaponPresentationVersion:1,enemyFireVersion:1,playerFireVersion:1,combatAudioVersion:1,playerPresentationVersion:1);WorldRecordingValidation.Header(h);check(h.playerPresentationVersion==1,"Player body profile explicitly requires new saved player presentation");
        h.playerPresentationVersion=0;try{WorldRecordingValidation.Header(h);throw new Exception("Unversioned body accepted");}catch(ArgumentException){check(true,"New player body cannot silently use an old player reader");}
        h.playerPresentationVersion=1;var source=new ArenaWorld([3],[]);var sourceId=Guid.NewGuid();source.AddPlayer(sourceId,3,head);
        var first=WorldRecordingPacket.Capture(source,1,0,1,0,0,_=>new RecordedRig{kind="Simulated"},enemyPresentationVersion:1,weaponPresentationVersion:1,enemyFireVersion:1,playerFireVersion:1,playerPresentationVersion:1);WorldRecordingValidation.Packet(h,first,null);
        check(first.frame.players[0].hasPlayerPresentation&&!first.frame.players[0].walking,"New recording captures explicit unstarted player body state");
        source.SetPhase(WorldPhase.Running);source.SetPlayerPose(sourceId,head+new Vec3(.1f,0,0),muzzle,f);source.Tick();var moving=WorldRecordingPacket.Capture(source,2,100,1,0,0,_=>new RecordedRig{kind="Simulated"},enemyPresentationVersion:1,weaponPresentationVersion:1,enemyFireVersion:1,playerFireVersion:1,playerPresentationVersion:1);WorldRecordingValidation.Packet(h,moving,first);
        check(moving.frame.players[0].walking,"World recorder persists accepted movement for direct player replay seeks");
        moving.frame.players[0].hasPlayerPresentation=false;try{WorldRecordingValidation.Packet(h,moving,first);throw new Exception("Missing body accepted");}catch(ArgumentException){check(true,"New world rejects missing explicit player presentation");}
        check(WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",[3],[]).playerPresentationVersion==0,"Legacy recordings retain original player boxes without fabricated walking");
    }
}
