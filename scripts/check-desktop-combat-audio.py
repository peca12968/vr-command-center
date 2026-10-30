"""Actual Space and operator AI sound cues with this game's AudioListener PCM."""
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('sound_venue',ROOT/'scripts/start-desktop-venue.py');module=importlib.util.module_from_spec(s);s.loader.exec_module(module)

def run(v):
    v.start();mission=v.request('/api/missions',{'name':'Combat audio - Simulation','briefing':'Actual keyboard / AI / own listener PCM',
        'durationSeconds':600,'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},'enemies':{'count':1,'behavior':'Hold','autoAttack':False},'props':[]},expected=201)
    entry=v.create(mission,[3],'combat-audio',role='Room3');own=entry['players'][0]
    v.wait(lambda:v.request('/api/sessions/'+entry['id']+'/world',optional=True),90,'audio recording')
    probe=v.runtime_directory/'combat-audio-probe';v.launch('combat-audio-player',v.client_config(entry,v.ticket(entry,own)),True,extra_args=['--vr-combat-audio-probe',str(probe.resolve())])
    v.wait(lambda:v.connected(entry),45,'visible native client');v.command(entry,'Begin');samples=[]
    def report(final=False):
        path=probe/('report.json'if final or (probe/'report.json').exists()else'status.json')
        try:r=json.loads(path.read_text(encoding='utf-8-sig'))
        except(FileNotFoundError,json.JSONDecodeError):return None
        if r['error']or r['truncated']or r['formatChanged']:raise RuntimeError('Native PCM collection failed or truncated')
        return r
    def observe(label):
        q=v.frame(entry,measure=True);f=q['packet']['frame'];p=next(p for p in f['players']if p['id']==own['id']);r=report()
        row={'label':label,'sequence':q['packet']['sequence'],'frame':f,'probeSeconds':r['audio'][-1]['seconds']if r and r['audio']else None};samples.append(row);v.save('combat-audio-samples.json',samples);return row
    v.wait(lambda:(r if (r:=report()) and r['callbackCount']>2 else None),15,'actual native AudioListener callbacks')
    time.sleep(.6);baseline=report();assert not baseline['cues'] and max(a['peak']for a in baseline['audio'][-10:])<.000001
    v.stage('fire',key='space',presses=1,note='Actual Space once, then fire.done; diagnostic records only this game listener')
    def fired_frame():
        row=observe('fire-wait')
        return row if next(p for p in row['frame']['players']if p['id']==own['id'])['magazine']==29 and (v.directory/'fire.done').exists()else None
    fired=v.wait(fired_frame,90,'one actual Space')
    def own_cue():
        r=report();return r if r and any(not c['shot']['enemy']and c['shot']['id']==own['id']for c in r['cues'])else None
    player_sound=v.wait(own_cue,10,'accepted player cue')
    v.wait(lambda:(r if (r:=report()) and max(a['peak']for a in r['audio'])>.001 else None),10,'nonzero actual native PCM after player shot')
    v.command(entry,'SetEnemies',enemies={'count':1,'behavior':'Hold','autoAttack':True})
    def hurt_frame():
        row=observe('ai-wait')
        return row if next(p for p in row['frame']['players']if p['id']==own['id'])['health']<=60 else None
    hurt=v.wait(hurt_frame,15,'two original AI hits')
    v.command(entry,'SetEnemies',enemies={'count':1,'behavior':'Hold','autoAttack':False});v.command(entry,'Pause')
    v.wait(lambda:observe('pause-wait')['frame']['phase']=='Paused',10,'paused world')
    time.sleep(.5);paused=report();cut=paused['audio'][-1]['seconds'];cues=len(paused['cues']);time.sleep(.6);quiet=report()
    assert len(quiet['cues'])==cues and [a for a in quiet['audio']if a['seconds']>cut] and max(a['peak']for a in quiet['audio']if a['seconds']>cut)<.000001
    v.command(entry,'Resume');v.wait(lambda:observe('resume-wait')['frame']['phase']=='Running',10,'Resume without attack')
    time.sleep(.6);resumed=report();assert len(resumed['cues'])==cues and max(a['peak']for a in resumed['audio'][-10:])<.000001
    assert any(c['shot']['enemy']for c in resumed['cues'])
    for c in resumed['cues']:assert 0<=c['shot']['tick']-(c['shot']['tickPlusOne']-1)<=3
    (probe/'finish.request').write_text('Finish diagnostic only; no gameplay mutation',encoding='utf-8')
    final=v.wait(lambda:(r if (r:=report(True)) and r['complete']else None),15,'complete own listener PCM')
    sealed=v.seal(entry);stats=next(p for p in sealed['statistics']['players']if p['playerId']==own['id']);assert stats['ammoUsed']==1 and stats['kills']==0 and 2<=stats['hitsReceived']<=3 and stats['damageTaken']==stats['hitsReceived']*20 and stats['health']==100-stats['damageTaken']
    assert sealed['world']['header']['combatAudioVersion']==1
    v.save('combat-audio-result.json',{'source':'Actual Windows keyboard / AI / own AudioListener PCM','headsets':0,'baseline':baseline,'playerSound':player_sound,
        'pausedCutSeconds':cut,'pausedQuiet':quiet,'resumedQuiet':resumed,'probe':final,'statistics':stats,'replayStatisticsMatch':sealed['replayStatisticsMatch'],'poseOrCombatInjected':False})
    v.evidence.extend(['Actual Space creates one accepted player sound and nonzero native listener PCM','Operator AI produces accepted enemy sounds and original twenty-point damage',
        'Pause and Resume without new shots remain silent without duplicate cues','Explicitly finished bounded PCM and exact game replay / combat seal'])
    v.summary()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime-root',type=Path)
    p.add_argument('--player-exe',type=Path,default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER',ROOT/'artifacts/desktop/VrCommand.exe')))
    p.add_argument('--api-dll',type=Path,default=Path(os.environ.get('VR_COMMAND_API_DLL',ROOT/'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    args=p.parse_args();args.duration=600;args.visible_room=3;args.job_workers=2;args.check=False
    try:module.verify_player(args)
    except(OSError,RuntimeError,ValueError)as e:p.error(str(e))
    v=module.Venue(args)
    try:run(v)
    except BaseException as e:v.stage('failed',errorType=type(e).__name__);raise
    finally:
        if not v.cleanup()and sys.exc_info()[0]is None:raise RuntimeError('Combat audio cleanup failed')

if __name__=='__main__':main()
