using System.Text.Json;
using VrCommand.Api;
using VrCommand.Core;
using VrCommand.Simulation;

internal static class MissionClockChecks
{
    internal static void Run(Action<bool,string> check,string directory)
    {
        void Reject<T>(Action action,string message) where T:Exception
        { try{action();}catch(T){check(true,message);return;}throw new Exception("Expected "+typeof(T).Name+": "+message); }
        check(MissionClock.LimitTicks(60)==1200 && Math.Abs(ArenaWorld.TickSeconds*MissionClock.TicksPerSecond-1)<.00001,
            "Mission clock uses the existing authoritative 20 Hz tick");
        check(MissionClock.RemainingSeconds(0,60)==60 && MissionClock.RemainingSeconds(1,60)==60
            && MissionClock.RemainingSeconds(1199,60)==1 && MissionClock.RemainingSeconds(1200,60)==0,
            "Countdown rounds remaining partial seconds up and reaches zero exactly at the limit");
        check(!MissionClock.Due(1199,60) && MissionClock.Due(1200,60) && MissionClock.RemainingSeconds(long.MaxValue,60)==0,
            "Clock boundary and large ticks do not underflow");
        Reject<ArgumentOutOfRangeException>(()=>MissionClock.LimitTicks(59),"Clock rejects durations outside the saved mission contract");
        var mission=new MissionStore(Path.Combine(directory,"clock-missions")).Create(new("Timed mission","Clock checks",60,
            new(ExperienceMode.VR,Weather.Clear,TimeOfDay.Day,false),new(0,EnemyBehavior.Hold,false),[]));
        var events=new MemorySessionEventStore();var manager=new SessionManager(events);
        var master=new OperatorIdentity("clock-master",OperatorRole.Master);var room=new OperatorIdentity("clock-room",OperatorRole.RoomController,1);
        var other=new OperatorIdentity("clock-other",OperatorRole.RoomController,2);var server=new OperatorIdentity("clock-server",OperatorRole.GameServer);
        var view=manager.Create(SessionMode.Independent,[1],mission,master);var id=view.Id;var player=Guid.NewGuid();var stream=Guid.NewGuid();
        manager.Join(id,player,"Clock player",1,HeadsetKind.Quest3,room);
        Reject<InvalidOperationException>(()=>manager.Execute(id,new(Guid.NewGuid(),ControlAction.SetMissionClock,MissionClock:new(true)),master),
            "Automatic expiry cannot be enabled without a clock-capable attached server");
        manager.OpenStream(id,new(stream,CombatOrigin.Simulation,1),server);
        Reject<AccessDeniedException>(()=>manager.Execute(id,new(Guid.NewGuid(),ControlAction.SetMissionClock,MissionClock:new(true)),other),
            "Clock settings retain independent-room authorization");
        var configure=new ControlCommand(Guid.NewGuid(),ControlAction.SetMissionClock,MissionClock:new(true));
        var accepted=manager.Execute(id,configure,room);
        check(manager.Execute(id,configure,room).Duplicate && accepted.Session.MissionClock is {Version:1,AutoEnd:true},
            "Clock configuration is explicit and its accepted retry is idempotent");
        Reject<AccessDeniedException>(()=>manager.ClockCandidates(master),"HTTP-capable identities cannot call the internal clock service");
        var bridge=new ArenaSession();
        ManagementSnapshot Snapshot()=>JsonSerializer.Deserialize<ManagementSnapshot>(JsonSerializer.Serialize(manager.Get(id),JsonFormat.Options),
            new JsonSerializerOptions(JsonFormat.Options){IncludeFields=true})!;
        bridge.Apply(Snapshot());
        var worldDirectory=Path.Combine(directory,"clock-worlds");Directory.CreateDirectory(worldDirectory);
        using var worlds=new WorldRecordings(worldDirectory,manager);
        var header=WorldRecordingHeader.Create(id,stream,"Simulation",[1],bridge.Props,missionClockVersion:1,missionDurationSeconds:60);
        worlds.Open(id,header,server);
        RecordedRig Rig(Guid p)=>new();
        worlds.Append(id,WorldRecordingPacket.Capture(bridge.World,1,0,manager.Get(id).Sequence,0,0,Rig),server);
        check(worlds.ExpireMissionClocks()==0,"A preparing frame cannot expire a mission");
        manager.Execute(id,new(Guid.NewGuid(),ControlAction.Begin),room);bridge.Apply(Snapshot());
        var admission=manager.Get(id).Players.Single().AdmissionId;
        check(bridge.Connect(7,player,1,0,admission),"Clock participant uses the normal admission binding");
        for(var i=0;i<400;i++)bridge.Tick(i*.05);
        manager.Execute(id,new(Guid.NewGuid(),ControlAction.Pause),room);bridge.Apply(Snapshot());
        for(var i=400;i<460;i++)bridge.Tick(i*.05);
        check(bridge.World.TickNumber==400 && MissionClock.RemainingSeconds(bridge.World.TickNumber,60)==40,
            "Paused ticks do not consume mission time");
        Reject<InvalidOperationException>(()=>manager.Execute(id,new(Guid.NewGuid(),ControlAction.SetMissionClock,MissionClock:new(false)),room),
            "The controller cannot reset or disable the time policy after Begin");
        manager.Execute(id,new(Guid.NewGuid(),ControlAction.Resume),room);bridge.Apply(Snapshot());
        for(var i=460;i<1400;i++)bridge.Tick(i*.05);
        check(bridge.World.TickNumber==1200 && bridge.ClockDue && bridge.World.Phase==WorldPhase.Running,
            "Authority stops exactly at the limit while awaiting a durable management End");
        check(!bridge.Weapon(7,1,false,70) && !bridge.Connect(8,player,1,0,admission),
            "A due mission cannot fire, reload or admit another gameplay binding");
        check(worlds.ExpireMissionClocks()==0,"Unpublished local time cannot authorize an automatic End");
        var evidence=new MissionClockExpiration(stream,manager.Get(id).Sequence,1200);
        Reject<AccessDeniedException>(()=>manager.ExpireMission(id,evidence,server),"A GameServer HTTP identity cannot directly expire a session");
        Reject<AccessDeniedException>(()=>manager.Execute(id,new(Guid.NewGuid(),ControlAction.End,ClockExpiration:evidence),master),
            "A user command cannot forge an internal deadline End reason");
        Reject<InvalidOperationException>(()=>manager.ExpireMission(id,evidence with{Tick=1199},SessionManager.ClockIdentity),
            "The internal boundary check rejects premature expiry");
        Reject<InvalidOperationException>(()=>manager.ExpireMission(id,evidence with{StreamId=Guid.NewGuid()},SessionManager.ClockIdentity),
            "Clock evidence cannot be borrowed from another combat source");
        worlds.Append(id,WorldRecordingPacket.Capture(bridge.World,2,65000,manager.Get(id).Sequence,0,0,Rig),server);
        check(worlds.ExpireMissionClocks()==1 && manager.Get(id).State==SessionState.Ended && manager.List().Length==0,
            "An accepted due source frame commits End and releases rooms");
        check(worlds.ExpireMissionClocks()==0 && !manager.ExpireMission(id,evidence,SessionManager.ClockIdentity),
            "Repeated service scans cannot append another End");
        var end=manager.Events(id).Single(e=>e.Kind==SessionEventKind.ControlApplied && e.Read<ControlCommand>().ClockExpiration!=null);
        check(end.Actor==SessionManager.ClockIdentity && end.SchemaVersion==7 && end.Read<ControlCommand>().ClockExpiration!.Tick==1200,
            "Automatic End persists its internal actor and exact source evidence in schema 7");
        bridge.Apply(Snapshot());manager.SealStream(id,new(stream,0),server);
        worlds.Append(id,WorldRecordingPacket.Capture(bridge.World,3,65100,manager.Get(id).Sequence,0,0,Rig),server);
        worlds.Seal(id,3,server);
        check(worlds.Info(id,master).Complete && !manager.Statistics(id).PendingTelemetry && manager.FinalReport(id,master).PlannedDurationSeconds==60,
            "Automatic End follows the normal exact combat and world seal / report flow");
        var loaded=new SessionManager(events);
        check(loaded.Get(id).State==SessionState.Ended && loaded.Get(id).MissionClock!.AutoEnd,
            "Restart projection preserves the explicit timer and accepted expiry without running it again");
        var legacy=manager.Create(SessionMode.Independent,[1],mission,master);
        check(legacy.MissionClock==null && manager.ClockCandidates(SessionManager.ClockIdentity).Length==0,
            "New and legacy sessions remain manual until a controller explicitly opts in");
        var oldHeader=WorldRecordingHeader.Create(legacy.Id,Guid.NewGuid(),"Simulation",[1],[]);
        check(oldHeader.missionClockVersion==0 && oldHeader.missionDurationSeconds==0,
            "Unchanged recording producers do not invent historical clock metadata");
    }
}
