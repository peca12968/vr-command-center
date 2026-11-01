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
    }
}
