using VrCommand.Simulation;

internal static class NavigationChecks
{
    private static (ArenaWorld World, ArenaWalkSurface Surface, Vec3 Start, Vec3 End) Rotated(int room = 3)
    {
        var origin=ArenaWorld.RoomOrigin(room);
        var props=new[]{new WorldProp(Guid.NewGuid(),room,PropKind.Barrel,origin+new Vec3(.25f,0,.25f),45)};
        var world=new ArenaWorld(room==3?[3]:[1,2,3,4,5],props);
        world.AddPlayer(Guid.NewGuid(),room,origin+new Vec3(-4,1.65f,-4));
        var start=origin+new Vec3(-2,0,1);var end=origin+new Vec3(2,0,1);
        world.AddEnemy(Guid.NewGuid(),room,start,end);world.SetPolicy(AiBehavior.Patrol,false,Visibility.Clear,false);world.SetPhase(WorldPhase.Running);
        return(world,new ArenaWalkSurface(origin,props),start,end);
    }
    private static (ArenaWorld World, Guid Enemy, ArenaWalkSurface Surface, Vec3 Start, Vec3 End) Generated(bool goal,int room=3,bool linked=false)
    {
        var source=new ArenaSession();source.Apply(new ManagementSnapshot{id=Guid.NewGuid().ToString(),state="Preparing",sequence=1,roomIds=linked?[1,2,3,4,5]:[room],
            mission=new ManagedMission{id=Guid.NewGuid().ToString(),definition=new ManagedDefinition{name="Non-grid navigation",briefing="Generator regression",durationSeconds=180,
                props=[new ManagedProp{assetId="barrel",position=new ManagedPosition{x=goal?5.1f:-4.6f,z=goal?5:-1}}]}},
            environment=new ManagedEnvironment{mode="VR",weather="Clear",timeOfDay="Day"},enemies=new ManagedEnemies{count=linked?5:1,behavior="Patrol",autoAttack=false},
            players=[new ManagedPlayer{id=Guid.NewGuid().ToString(),admissionId=Guid.NewGuid().ToString(),roomId=room,seat=0}]});
        var enemy=source.World.Snapshot().Enemies.Single(e=>e.RoomId==room);source.World.SetPhase(WorldPhase.Running);
        var origin=ArenaWorld.RoomOrigin(room);return(source.World,enemy.Id,new ArenaWalkSurface(origin,source.Props.Where(p=>p.RoomId==room).ToArray()),enemy.Feet,origin+new Vec3(goal?3.75f:4.5f,0,5));
    }
    private static (bool Reached,bool Returned,bool Safe) Exercise(ArenaWorld world,Guid enemy,ArenaWalkSurface surface,Vec3 start,Vec3 end)
    {
        var reached=false;var returned=false;var safe=true;var previous=start;
        for(var i=0;i<320;i++)
        {
            world.Tick();var feet=world.Snapshot().Enemies.Single(e=>e.Id==enemy).Feet;
            reached|=Vec3.Distance(feet,end)<.15f;returned|=reached&&Vec3.Distance(feet,start)<.15f;
            safe&=surface.ClearSegment(previous,feet)&&Vec3.Distance(previous,feet)<=.1001f;previous=feet;
        }
        return(reached,returned,safe);
    }
    internal static void Run(Action<bool,string> check)
    {
        var r=Rotated();var outbound=false;var returned=false;var valid=true;var previous=r.Start;
        for(var i=0;i<320;i++)
        {
            r.World.Tick();var p=r.World.Snapshot().Enemies[0].Feet;
            outbound|=Vec3.Distance(p,r.End)<.15f;returned|=outbound&&Vec3.Distance(p,r.Start)<.15f;
            valid&=r.Surface.ClearSegment(previous,p)&&Vec3.Distance(previous,p)<=.1001f;previous=p;
        }
        check(outbound,"Patrol bypasses a rotated corner whose grid endpoints are open but connecting edge is blocked");
        check(returned,"Patrol returns over the cached undirected grid without repeatedly choosing the rejected corner");
        check(valid,"Every rotated-cover patrol movement retains the original swept clearance and 0.1m tick limit");
        r.World.SetPhase(WorldPhase.Paused);var tick=r.World.TickNumber;var p0=r.World.Snapshot().Enemies[0].Feet;
        for(var i=0;i<20;i++)r.World.Tick();
        var paused=r.World.TickNumber==tick&&Vec3.Distance(p0,r.World.Snapshot().Enemies[0].Feet)==0;
        r.World.SetPhase(WorldPhase.Running);r.World.SetPolicy(AiBehavior.Hold,false,Visibility.Clear,false);
        for(var i=0;i<20;i++)r.World.Tick();
        check(paused&&Vec3.Distance(p0,r.World.Snapshot().Enemies[0].Feet)==0,"Navigation edge cache does not bypass Pause or operator Hold");
        var linked=true;
        foreach(var room in new[]{1,5})
        {
            var shifted=Rotated(room);var reached=false;
            for(var i=0;i<160;i++){shifted.World.Tick();reached|=Vec3.Distance(shifted.World.Snapshot().Enemies[0].Feet,shifted.End)<.15f;}
            linked&=reached;
        }
        check(linked,"Rotated-cover routing respects both outer room origins in a five-room world");
        var wall=Enumerable.Range(-2,5).Select(x=>new WorldProp(Guid.NewGuid(),3,PropKind.Sandbag,new Vec3(x*2.4f,0,0),0)).ToArray();
        var blocked=new ArenaWorld([3],wall);blocked.AddPlayer(Guid.NewGuid(),3,new Vec3(-4,1.65f,-4));
        blocked.AddEnemy(Guid.NewGuid(),3,new Vec3(0,0,-3),new Vec3(0,0,3));blocked.SetPolicy(AiBehavior.Patrol,false,Visibility.Clear,false);blocked.SetPhase(WorldPhase.Running);
        for(var i=0;i<160;i++)blocked.Tick();
        check(Vec3.Distance(blocked.Snapshot().Enemies[0].Feet,new Vec3(0,0,-3))==0,"A complete cover wall remains unreachable after edge validation; no fallback teleport");
        var startCase=Generated(false);var startRun=Exercise(startCase.World,startCase.Enemy,startCase.Surface,startCase.Start,startCase.End);
        check(startCase.Start.X==-3.75f&&startRun.Reached,"A real non-grid generated spawn connects through a clear cell corner when its rounded node is blocked");
        var goalCase=Generated(true);var goalRun=Exercise(goalCase.World,goalCase.Enemy,goalCase.Surface,goalCase.Start,goalCase.End);
        check(goalCase.Start.X==-4.5f&&goalRun.Reached,"Patrol reaches its original non-grid destination instead of stopping 0.25m away at the rounded node");
        check(startRun.Returned&&goalRun.Returned&&startRun.Safe&&goalRun.Safe,"Both generated endpoint cases return without teleporting or changing tick speed / swept clearance");
        var outer=true;
        foreach(var room in new[]{1,5})
        {
            var q=Generated(room==5,room,true);var result=Exercise(q.World,q.Enemy,q.Surface,q.Start,q.End);outer&=result.Reached&&result.Returned&&result.Safe;
        }
        check(outer,"Non-grid endpoint connections remain in the correct outer rooms of a Linked world");
        bool Local(Vec3 from,Vec3 to,WorldProp[] props)
        {
            var w=new ArenaWorld([3],props);w.AddPlayer(Guid.NewGuid(),3,new Vec3(-3,1.65f,-3));var id=Guid.NewGuid();w.AddEnemy(id,3,from,to);w.SetPolicy(AiBehavior.Patrol,false,Visibility.Clear,false);w.SetPhase(WorldPhase.Running);
            var result=Exercise(w,id,new ArenaWalkSurface(new Vec3(),props),from,to);return result.Reached&&result.Safe;
        }
        check(Local(new Vec3(.1f,0,.1f),new Vec3(.24f,0,.24f),[]),"A clear same-cell route retains its actual destination instead of getting stuck at a shared rounded node");
        check(Local(new Vec3(.05f,0,.9f),new Vec3(.45f,0,.9f),[new WorldProp(Guid.NewGuid(),3,PropKind.Barrel,new Vec3(.25f,0,.15f),45)]),"Same-cell endpoint linking routes around a blocked direct corner instead of clipping through it");
    }
}
