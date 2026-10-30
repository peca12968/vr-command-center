using System.Text.Json;
using VrCommand.Simulation;

internal static class PlayerFireChecks
{
    private static readonly JsonSerializerOptions Json=new(){IncludeFields=true};
    private static T Copy<T>(T value)=>JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(value,Json),Json)!;
    internal static string Vectors()=>JsonSerializer.Serialize(
        (from tick in Enumerable.Range(0,9) from health in new[]{0,80,100} from connected in new[]{false,true} from reloading in new[]{false,true}
         let p=PlayerFirePresentation.Pose(tick,health,connected,reloading,new(1,1,new(0,1.65f,-3),new(0,0,1)))
         select new{tick,health,connected,reloading,fireSequence=1,fireTickPlusOne=1,fireOrigin=new{x=0,y=1.65f,z=-3},fireDirection=new{x=0,y=0,z=1},flash=p.Flash,recoil=p.Recoil}).ToArray());
    internal static void Run(Action<bool,string> check)
    {
        void Reject<T>(Action action,string label)where T:Exception{try{action();}catch(T){check(true,label);return;}throw new Exception(label);}
        var world=new ArenaWorld([3],[]);var player=Guid.NewGuid();world.AddPlayer(player,3,new(0,1.65f,-3));
        var header=WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",[3],[],assetSet:WorldAssetSets.PlayerFire,enemyPresentationVersion:1,weaponPresentationVersion:1,enemyFireVersion:1,playerFireVersion:1);
        WorldRecordingPacket Capture(long seq,long after)=>WorldRecordingPacket.Capture(world,seq,(seq-1)*50,1,world.Events().Count(e=>e.Kind==WorldEventKind.ShotFired),after,
            _=>new(){kind="Simulated",left=new(new Vec3(world.PlayerSnapshot(player).Head.X-.2f,world.PlayerSnapshot(player).Head.Y-.3f,world.PlayerSnapshot(player).Head.Z+.2f)),right=new(world.PlayerSnapshot(player).Muzzle)},
            enemyPresentationVersion:1,weaponPresentationVersion:1,enemyFireVersion:1,playerFireVersion:1);
        WorldRecordingValidation.Header(header);var initial=Capture(1,0);WorldRecordingValidation.Packet(header,initial,null);
        check(initial.frame.players[0].hasFireState && initial.frame.players[0].fireSequence==0,"New player producer explicitly records an unfired state");
        world.SetPhase(WorldPhase.Running);var id=Guid.NewGuid();world.Fire(player,id);var fired=Capture(2,0);WorldRecordingValidation.Packet(header,fired,initial);var shot=fired.events.Single();var p=fired.frame.players[0];
        check(shot.tick==0 && p.fireSequence==shot.sequence && p.fireTickPlusOne==1 && p.fireOrigin.ToVector().Equals(shot.origin.ToVector()) && p.fireDirection.ToVector().Equals(shot.direction.ToVector()) && p.magazine==29,
            "An accepted tick-zero miss saves the exact player ray and original one-round cost");
        var prior=world.PlayerSnapshot(player).Fire;world.Fire(player,id);
        check(world.EventSequence==1 && world.PlayerSnapshot(player).Fire.Sequence==prior.Sequence && world.PlayerSnapshot(player).Magazine==29,"An accepted shot retry neither restarts presentation nor spends ammunition");
        Reject<InvalidOperationException>(()=>world.Fire(player,Guid.NewGuid()),"Unaccepted rapid fire cannot create a new presentation state");
        void Bad(Action<RecordedPlayer> mutate,string label){var value=Copy(fired);mutate(value.frame.players[0]);Reject<ArgumentException>(()=>WorldRecordingValidation.Packet(header,value,initial),label);}
        Bad(v=>v.hasFireState=false,"New player packets cannot omit their saved fire flag");
        Bad(v=>v.fireSequence++,"Player flash cannot refer to an unwitnessed sequence");
        Bad(v=>v.fireTickPlusOne++,"A rewritten player clock cannot restart recoil");
        Bad(v=>v.fireOrigin.x+=.01f,"A shifted muzzle cannot replace the accepted historical origin");
        Bad(v=>v.fireDirection=new(new Vec3(1,0,0)),"Current player aim cannot replace the accepted shot direction");
        Bad(v=>v.fireOrigin=null!,"Missing player fire vectors fail closed");
        world.SetPhase(WorldPhase.Paused);for(var i=0;i<60;i++)world.Tick();var paused=Capture(3,1);WorldRecordingValidation.Packet(header,paused,fired);
        var pose=PlayerFirePresentation.Pose(world.TickNumber,100,true,false,world.PlayerSnapshot(player).Fire);
        check(world.TickNumber==0 && pose.Flash && Math.Abs(pose.Recoil-.014f)<.000001f,"Real ArenaWorld Pause freezes a nonzero player flash and recoil at tick zero");
        world.SetPlayerPose(player,new(0,1.65f,-3),new(.2f,1.65f,-3),new(1,0,0));var moved=Capture(4,1);WorldRecordingValidation.Packet(header,moved,paused);
        check(moved.frame.players[0].fireOrigin.ToVector().Equals(p.fireOrigin.ToVector()) && !moved.frame.players[0].muzzle.ToVector().Equals(p.fireOrigin.ToVector()),"Moving the accepted pointer preserves the previous shot ray");
        world.SetPhase(WorldPhase.Running);for(var i=0;i<4;i++)world.Tick();world.Fire(player,Guid.NewGuid());var second=Capture(5,1);WorldRecordingValidation.Packet(header,second,moved);
        check(second.frame.players[0].fireSequence==2 && second.frame.players[0].fireTickPlusOne==5 && second.frame.players[0].magazine==28,"The next original four-tick shot advances the effect exactly once");
        world.Reload(player,Guid.NewGuid());var reloading=Capture(6,2);WorldRecordingValidation.Packet(header,reloading,second);
        check(PlayerFirePresentation.Pose(4,100,true,true,world.PlayerSnapshot(player).Fire).Recoil==0 && PlayerFirePresentation.Pose(4,100,true,true,world.PlayerSnapshot(player).Fire).Flash,
            "Accepted same-tick reload suppresses mesh recoil without erasing its shot flash");
        for(var i=0;i<30;i++)world.Tick();world.SetPlayerPose(player,new(5.5f,2.4f,0),new(6,2.6f,0),new(0,0,1));world.Fire(player,Guid.NewGuid());var boundary=Capture(7,3);WorldRecordingValidation.Packet(header,boundary,reloading);
        check(boundary.frame.players[0].fireOrigin.x==6 && boundary.frame.players[0].fireOrigin.y==2.6f && boundary.frame.players[0].reserve==88,"Original legal muzzle boundary and reload ammunition remain valid with fire metadata");
        var dead=PlayerFirePresentation.Pose(0,0,true,false,prior);var offline=PlayerFirePresentation.Pose(0,100,false,false,prior);
        check(!dead.Flash && dead.Recoil==0 && !offline.Flash && offline.Recoil==0,"Death and disconnection hide player effects while retaining accepted state");
        var old=WorldRecordingPacket.Capture(world,1,0,1,0,0,_=>new());check(!old.frame.players[0].hasFireState && old.frame.players[0].fireSequence==0,"Default old producers do not invent player effects after actual firing");
        var badHeader=Copy(header);badHeader.playerFireVersion=0;Reject<ArgumentException>(()=>WorldRecordingValidation.Header(badHeader),"Player fire profile cannot omit its explicit version");
        badHeader.assetSet=WorldAssetSets.CombatEffects;WorldRecordingValidation.Header(badHeader);Reject<ArgumentException>(()=>WorldRecordingValidation.Packet(badHeader,fired,initial),"Old profiles cannot carry unversioned player shot effects");
        badHeader=Copy(header);badHeader.playerFireVersion=2;Reject<ArgumentException>(()=>WorldRecordingValidation.Header(badHeader),"Unknown player fire versions fail closed");
        Reject<ArgumentException>(()=>PlayerFirePresentation.Pose(0,100,true,false,new(0,0,new(1e-30f,0,0),default)),"Unfired player metadata cannot hide subnormal origin components");
    }
}
