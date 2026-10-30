using System.Text.Json;
using VrCommand.Simulation;

internal static class WeaponPresentationChecks
{
    internal static string Vectors() => JsonSerializer.Serialize(
        (from elapsed in Enumerable.Range(0,30) from tracked in new[]{false,true}
         let p=WeaponPresentation.Pose(100+elapsed,100,true,!tracked,true,130)
         select new{tick=100+elapsed,health=100,connected=true,simulated=!tracked,reloading=true,until=130,
             offset=new[]{p.MagazineOffset.X,p.MagazineOffset.Y,p.MagazineOffset.Z},left=new[]{p.LeftHand.X,p.LeftHand.Y,p.LeftHand.Z},roll=p.MagazineRoll,leftRoll=p.LeftRoll,visible=p.MagazineVisible,hands=p.HandsVisible}).ToArray());
    internal static void Run(Action<bool,string> check)
    {
        void Reject(Action action,string label){try{action();}catch(ArgumentException){check(true,label);return;}throw new Exception(label);}
        var world=new ArenaWorld([3],[]);var id=Guid.NewGuid();world.AddPlayer(id,3,new(0,1.65f,-3));
        var header=WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",[3],[],assetSet:WorldAssetSets.WeaponActions,enemyPresentationVersion:1,weaponPresentationVersion:1);
        WorldRecordingValidation.Header(header);
        RecordedRig Rig(Guid _) => new(){kind="Simulated",left=new(new Vec3(-.2f,1.35f,-2.8f)),right=new(new Vec3(.2f,1.35f,-2.8f))};
        WorldRecordingPacket Capture(long sequence,long after,long combat)=>WorldRecordingPacket.Capture(world,sequence,(sequence-1)*50,1,combat,after,Rig,enemyPresentationVersion:1,weaponPresentationVersion:1);
        var initial=Capture(1,0,0);WorldRecordingValidation.Packet(header,initial,null);
        check(initial.frame.players[0].hasWeaponPresentation&&initial.frame.players[0].reloadUntilTick==0,"New weapon profile begins without an invented reload");
        header.weaponPresentationVersion=0;Reject(()=>WorldRecordingValidation.Header(header),"Action rifle cannot omit its versioned clock");header.weaponPresentationVersion=1;
        world.SetPhase(WorldPhase.Running);world.Fire(id,Guid.NewGuid());var reloading=Guid.NewGuid();world.Reload(id,reloading);world.Reload(id,reloading);
        for(var i=0;i<8;i++)world.Tick();var frame=world.Snapshot();var muzzle=frame.Players[0].Muzzle;var packet=Capture(2,0,1);WorldRecordingValidation.Packet(header,packet,initial);
        check(packet.frame.players[0].reloadUntilTick==30&&world.Events().Count(e=>e.Kind==WorldEventKind.ReloadStarted)==1,"Accepted reload and exact retry expose one original completion tick");
        var pose=WeaponPresentation.Pose(frame.Tick,100,true,true,true,30);
        check(pose.MagazineOffset.Y<-.1f&&pose.HandsVisible&&pose.MagazineVisible,"A real accepted partial reload lowers its magazine and simulated grip");
        world.SetPhase(WorldPhase.Paused);for(var i=0;i<40;i++)world.Tick();var frozen=world.Snapshot();var paused=WeaponPresentation.Pose(frozen.Tick,100,true,true,true,30);
        check(frozen.Tick==frame.Tick&&paused.MagazineOffset.Equals(pose.MagazineOffset)&&frozen.Players[0].Muzzle.Equals(muzzle),"Pause freezes the exact magazine pose without moving the accepted muzzle");
        var saved=packet.frame.players[0].reloadUntilTick;packet.frame.players[0].reloadUntilTick++;
        Reject(()=>WorldRecordingValidation.Packet(header,packet,initial),"A plausible but unwitnessed reload clock is rejected");packet.frame.players[0].reloadUntilTick=saved;
        var ghost=Capture(2,0,1);ghost.events=ghost.events.Where(e=>e.kind!="ReloadStarted").ToArray();ghost.frame.throughSequence--;
        // Renumber the remaining single ShotFired event; the missing reload must still fail.
        Reject(()=>WorldRecordingValidation.Packet(header,ghost,initial),"A reload action cannot appear without its world event witness");
        check(!WeaponPresentation.Pose(14,100,true,false,true,30).HandsVisible&&!WeaponPresentation.Pose(14,100,true,true,true,30).MagazineVisible,
            "Tracked rigs retain their real hand data while the cosmetic magazine exchange has a bounded hidden interval");
        check(!WeaponPresentation.Pose(50,0,true,true,true,30).HandsVisible&&WeaponPresentation.Pose(50,0,true,true,true,30).MagazineOffset.Equals(default(Vec3)),
            "An eliminated player cannot continue a cosmetic reload even when the legacy rule retains an overdue reload flag");
        world.SetPhase(WorldPhase.Running);for(var i=0;i<22;i++)world.Tick();var complete=Capture(3,packet.frame.throughSequence,1);WorldRecordingValidation.Packet(header,complete,packet);
        check(!complete.frame.players[0].reloading&&complete.frame.players[0].reloadUntilTick==0&&world.PlayerSnapshot(id).Magazine==30&&world.PlayerSnapshot(id).Reserve==89,
            "Original 30-tick completion clears the cosmetic clock and transfers only the spent round");
        var legacy=WorldRecordingPacket.Capture(world,1,0,1,1,world.EventSequence,Rig);
        check(!legacy.frame.players[0].hasWeaponPresentation&&legacy.frame.players[0].reloadUntilTick==0,"Default legacy producers do not retroactively acquire animated weapon state");
        Reject(()=>WeaponPresentation.Pose(31,100,true,true,true,30),"A live expired reload clock fails closed");
        Reject(()=>WeaponPresentation.Pose(0,100,true,true,false,30),"A standing weapon cannot keep a phantom reload deadline");
    }
}
