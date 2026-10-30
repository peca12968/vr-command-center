using System.Text.Json;
using VrCommand.Simulation;

internal static class CombatAudioChecks
{
    internal static string Vectors()
    {
        var steps=new[]{(0,"Preparing",0L,0L,true),(0,"Running",1L,1L,true),(0,"Running",1L,1L,true),(1,"Paused",1L,1L,true),
            (1,"Running",1L,1L,true),(2,"Running",2L,3L,true),(20,"Running",3L,21L,true),(21,"Running",4L,22L,true),
            (20,"Running",3L,21L,true),(21,"Running",4L,22L,true),(22,"Running",5L,23L,false),(23,"Running",6L,24L,true),
            (24,"Running",7L,25L,true),(25,"Ended",7L,25L,true)};
        var cursor=new CombatAudioCursor();return JsonSerializer.Serialize(steps.Select(s=>new{tick=s.Item1,phase=s.Item2,sequence=s.Item3,tickPlusOne=s.Item4,continuous=s.Item5,sound=cursor.Advance(s.Item1,s.Item2,s.Item3,s.Item4,s.Item5)}));
    }
    internal static void Run(Action<bool,string> check)
    {
        var c=new CombatAudioCursor();
        check(!c.Advance(0,"Preparing",0,0,true)&&c.Advance(0,"Running",1,1,true),"Accepted tick-zero shot may sound after an observed preparing baseline");
        check(!c.Advance(0,"Running",1,1,true)&&!c.Advance(1,"Running",1,1,true),"Repeated snapshots and clocks cannot replay one accepted shot");
        check(!c.Advance(1,"Paused",1,1,true)&&!c.Advance(1,"Running",1,1,true)&&c.Advance(2,"Running",2,3,true),"Pause consumes no old cue; subsequent newly accepted shot sounds once");
        check(!c.Advance(20,"Running",3,21,true)&&c.Advance(21,"Running",4,22,true),"Long source gaps suppress catch-up and establish a fresh baseline");
        check(!c.Advance(19,"Running",3,20,true)&&c.Advance(20,"Running",4,21,true),"Reverse seek rebases rather than replaying a historical cue immediately");
        check(!c.Advance(21,"Running",5,22,false)&&!c.Advance(22,"Running",6,23,true)&&c.Advance(23,"Running",7,24,true),"Muted or discontinuous observation cannot replay sounds upon re-enable");
        check(!c.Advance(24,"Running",8,1,true),"An old accepted ray never creates a late catch-up sound");
        var joined=new CombatAudioCursor();check(!joined.Advance(30,"Running",10,31,true)&&joined.Advance(31,"Running",11,32,true),"Late join suppresses current shot and accepts only subsequent cues");
        joined.Reset();check(!joined.Advance(31,"Running",11,32,true),"New recording reset cannot carry a prior cue cursor");
        var header=WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",[3],[],assetSet:WorldAssetSets.PlayerFire,
            enemyPresentationVersion:1,weaponPresentationVersion:1,enemyFireVersion:1,playerFireVersion:1,combatAudioVersion:1);WorldRecordingValidation.Header(header);
        check(header.combatAudioVersion==1,"New source explicitly versions combat audio separately from frozen geometry");
        header.playerFireVersion=0;try{WorldRecordingValidation.Header(header);throw new Exception("Missing player fire metadata accepted");}catch(ArgumentException){check(true,"Audio cannot claim a version without accepted player and enemy fire witnesses");}
        header.playerFireVersion=1;header.combatAudioVersion=2;try{WorldRecordingValidation.Header(header);throw new Exception("Unknown audio accepted");}catch(ArgumentException){check(true,"Unknown sound rules fail closed");}
        check(WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",[3],[]).combatAudioVersion==0,"Legacy sources default to no combat sounds");
        try{c.Advance(0,"Running",1,2,true);throw new Exception("Future shot accepted");}catch(ArgumentException){check(true,"Future accepted-shot clocks cannot create audio");}
    }
}
