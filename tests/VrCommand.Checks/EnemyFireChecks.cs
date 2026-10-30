using System.Text.Json;
using VrCommand.Simulation;

internal static class EnemyFireChecks
{
    private static readonly JsonSerializerOptions Json=new(){IncludeFields=true};
    private static T Copy<T>(T value)=>JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(value,Json),Json)!;
    internal static string Vectors()=>JsonSerializer.Serialize(
        (from tick in Enumerable.Range(10,23) from health in new[]{0,80,100}
         let p=EnemyFirePresentation.Pose(tick,health,new(5,11,new(0,1.4f,3),new(0,0,-1)))
         select new{tick,health,fireSequence=5,fireTickPlusOne=11,fireOrigin=new{x=0,y=1.4f,z=3},fireDirection=new{x=0,y=0,z=-1},flash=p.Flash,recoil=p.Recoil}).ToArray());
    internal static void Run(Action<bool,string> check)
    {
        void Reject(Action action,string label){try{action();}catch(ArgumentException){check(true,label);return;}throw new Exception(label);}
        var world=new ArenaWorld([3],[]);var player=Guid.NewGuid();world.AddPlayer(player,3,new(0,1.65f,-3));world.AddEnemy(Guid.NewGuid(),3,new(0,0,3),new(3,0,3));
        var h=WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",[3],[],assetSet:WorldAssetSets.CombatEffects,enemyPresentationVersion:1,weaponPresentationVersion:1,enemyFireVersion:1);
        WorldRecordingPacket Capture(long seq,long after)=>WorldRecordingPacket.Capture(world,seq,(seq-1)*50,1,world.Events().Count(e=>e.Kind==WorldEventKind.PlayerDamaged),after,_=>new(){kind="Simulated",left=new(new Vec3(-.2f,1.35f,-2.8f)),right=new(new Vec3(0,1.65f,-3))},enemyPresentationVersion:1,weaponPresentationVersion:1,enemyFireVersion:1);
        WorldRecordingValidation.Header(h);var initial=Capture(1,0);WorldRecordingValidation.Packet(h,initial,null);
        check(initial.frame.enemies[0].hasFireState && initial.frame.enemies[0].fireSequence==0,"New fire producer explicitly records an unfired enemy instead of inventing a shot");
        world.SetPhase(WorldPhase.Running);world.SetPolicy(AiBehavior.Hold,true,Visibility.Clear,false);world.Tick();var fired=Capture(2,0);WorldRecordingValidation.Packet(h,fired,initial);
        var shot=fired.events.Single(e=>e.kind=="EnemyShot");var enemy=fired.frame.enemies[0];
        check(enemy.fireSequence==shot.sequence && enemy.fireTickPlusOne==shot.tick+1 && enemy.fireOrigin.ToVector().Equals(shot.origin.ToVector()) && enemy.fireDirection.ToVector().Equals(shot.direction.ToVector()) && world.PlayerSnapshot(player).Health==80,
            "Saved fire metadata copies the exact accepted NPC event and retains original twenty-point damage");
        void Bad(Action<RecordedEnemy> mutate,string label){var p=Copy(fired);mutate(p.frame.enemies[0]);Reject(()=>WorldRecordingValidation.Packet(h,p,initial),label);}
        Bad(e=>e.fireSequence++,"A fire sequence without its accepted shot is rejected");
        Bad(e=>e.fireTickPlusOne++,"A changed fire clock cannot restart a flash");
        Bad(e=>e.fireOrigin.x+=.01f,"A shifted fire origin cannot substitute the current NPC position");
        Bad(e=>e.fireDirection=new(new Vec3(1,0,0)),"A different unit direction cannot substitute the current aim");
        Bad(e=>e.hasFireState=false,"New fire recordings require an explicit state flag");
        Bad(e=>e.fireOrigin=null!,"Missing fire vectors fail closed");
        var replayState=new EnemyFireState(enemy.fireSequence,enemy.fireTickPlusOne,enemy.fireOrigin.ToVector(),enemy.fireDirection.ToVector());
        var pose=EnemyFirePresentation.Pose(world.TickNumber,100,replayState);world.SetPhase(WorldPhase.Paused);for(var i=0;i<60;i++)world.Tick();var paused=Capture(3,world.EventSequence);WorldRecordingValidation.Packet(h,paused,fired);
        check(world.TickNumber==1 && pose.Flash && pose.Recoil>0 && EnemyFirePresentation.Pose(world.TickNumber,100,world.Snapshot().Enemies[0].Fire).Recoil==pose.Recoil,
            "A real paused ArenaWorld freezes the accepted fire tick and nonzero recoil without a local timer");
        world.SetPhase(WorldPhase.Running);world.SetPolicy(AiBehavior.Patrol,false,Visibility.Clear,false);for(var i=0;i<8;i++)world.Tick();var moved=Capture(4,world.EventSequence);WorldRecordingValidation.Packet(h,moved,paused);
        check(world.Snapshot().Enemies[0].Feet.X>0 && world.Snapshot().Enemies[0].Fire.Origin.Equals(replayState.Origin) && !EnemyFirePresentation.Pose(world.TickNumber,100,replayState).Flash,
            "Moving and turning after a shot retain its historical flash origin and naturally finish the pulse");
        var unwitnessed=Copy(moved);unwitnessed.frame.enemies[0].fireOrigin.x+=.1f;Reject(()=>WorldRecordingValidation.Packet(h,unwitnessed,paused),"A later packet cannot rewrite an old accepted fire ray");
        world.SetPolicy(AiBehavior.Hold,true,Visibility.Clear,false);while(world.TickNumber<21)world.Tick();var second=Capture(5,world.EventSequence-2);WorldRecordingValidation.Packet(h,second,moved);
        check(second.frame.enemies[0].fireSequence>enemy.fireSequence && second.frame.enemies[0].fireTickPlusOne==22 && world.PlayerSnapshot(player).Health==60,"The next actual twenty-tick NPC shot advances the saved effect once and retains cooldown");
        var old=WorldRecordingPacket.Capture(world,1,0,1,0,0,_=>new RecordedRig());check(!old.frame.enemies[0].hasFireState && old.frame.enemies[0].fireSequence==0,"Default old capture remains fire version zero after real shots");
        var legacy=Copy(h);legacy.enemyFireVersion=0;Reject(()=>WorldRecordingValidation.Header(legacy),"Effects profile cannot omit its fire version");
        legacy.assetSet=WorldAssetSets.ArmedCombatants;WorldRecordingValidation.Header(legacy);Reject(()=>WorldRecordingValidation.Packet(legacy,fired,initial),"A legacy header cannot smuggle in unversioned flash metadata");
        var unknown=Copy(h);unknown.enemyFireVersion=2;Reject(()=>WorldRecordingValidation.Header(unknown),"Unknown fire versions fail closed");
        check(!EnemyFirePresentation.Pose(1,0,replayState).Flash && EnemyFirePresentation.Pose(1,0,replayState).Recoil==0,"Death suppresses presentation without erasing accepted history");
        Reject(()=>EnemyFirePresentation.Pose(1,100,new(1,3,new(0,1.4f,0),new(0,0,1))),"Future shot clocks are rejected before rendering");
        Reject(()=>EnemyFirePresentation.Pose(1,100,new(0,0,new(1e-30f,0,0),default)),"An unfired state cannot hide even subnormal nonzero origin components");
    }
}
