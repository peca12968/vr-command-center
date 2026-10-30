"""Read-only native GPU probe of actual operator-enabled AI shots.

Own API / server / visible Simulation client. No input, pose or combat injection.
The review marker acknowledges inspection of the probe's own framebuffer images.
"""
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fire_venue',ROOT/'scripts/start-desktop-venue.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def run(v):
    v.start()
    mission=v.request('/api/missions',{'name':'Native NPC fire - Simulation','briefing':'Actual AI events / saved muzzle / own GPU capture; no injection',
        'durationSeconds':300,'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},
        'enemies':{'count':1,'behavior':'Hold','autoAttack':False},'props':[]},expected=201)
    entry=v.create(mission,[3],'enemy-fire',role='Room3');own=entry['players'][0]
    v.wait(lambda:v.request('/api/sessions/'+entry['id']+'/world',optional=True),90,'enemy fire recording')
    probe=v.runtime_directory/'enemy-fire-probe';v.launch('enemy-fire-player',v.client_config(entry,v.ticket(entry,own)),True,
        extra_args=['--vr-enemy-fire-probe',str(probe.resolve())])
    v.wait(lambda:v.connected(entry),30,'connected actual visible client')
    samples=[]
    def frame(label):
        row=v.frame(entry,measure=True);f=row['packet']['frame'];samples.append({'label':label,'sequence':row['packet']['sequence'],'frame':f});v.save('fire-samples.json',samples);return f
    def report(complete=False):
        path=probe/('report.json' if complete or (probe/'report.json').exists() else 'status.json')
        try:r=json.loads(path.read_text(encoding='utf-8-sig'))
        except(FileNotFoundError,json.JSONDecodeError):return None
        if r.get('error'):raise RuntimeError(r['error'])
        return r
    v.command(entry,'Begin');v.command(entry,'SetEnemies',enemies={'count':1,'behavior':'Hold','autoAttack':True})
    def shot_seen():
        f=frame('shot-wait');r=report()
        if next(p for p in f['players'] if p['id']==own['id'])['health']==0:raise RuntimeError('No GPU pulse captured before player elimination')
        return r if r and any(c['file'].startswith('shot-') for c in r['captures']) else None
    first=v.wait(shot_seen,4,'actual rendered enemy shot')
    v.command(entry,'SetEnemies',enemies={'count':1,'behavior':'Hold','autoAttack':False});v.command(entry,'Pause')
    paused=v.wait(lambda:(f if (f:=frame('pause-wait'))['phase']=='Paused' else None),10,'native Pause after shot')
    npc=paused['enemies'][0];assert npc['hasFireState'] and npc['fireSequence']>0
    v.wait(lambda:(r if (r:=report()) and any(c['phase']=='Paused' for c in r['captures']) else None),10,'paused GPU evidence')
    day_paused=paused
    v.command(entry,'SetEnvironment',environment={'mode':'VR','weather':'Clear','timeOfDay':'Night','lightning':False})
    v.command(entry,'SetEnemies',enemies={'count':1,'behavior':'Hold','autoAttack':True});v.command(entry,'Resume')
    def night_shot():
        f=frame('night-shot-wait');r=report()
        return r if f['night'] and r and any(e['visible'] and e['fireSequence']>npc['fireSequence'] for c in r['captures'] for e in c['enemies']) else None
    v.wait(night_shot,4,'actual night muzzle pulse')
    v.command(entry,'SetEnemies',enemies={'count':1,'behavior':'Hold','autoAttack':False});v.command(entry,'Pause')
    paused=v.wait(lambda:(f if (f:=frame('night-pause-wait'))['phase']=='Paused' and f['night'] else None),10,'native night Pause');npc=paused['enemies'][0]
    v.command(entry,'SetEnemies',enemies={'count':1,'behavior':'Patrol','autoAttack':False});v.command(entry,'Resume')
    moved=v.wait(lambda:(f if (f:=frame('move-wait'))['phase']=='Running' and f['tick']>=npc['fireTickPlusOne']+7
        and abs(f['enemies'][0]['feet']['x']-npc['feet']['x'])>.05 else None),10,'actual patrol after original shot')
    v.command(entry,'Pause');settled=v.wait(lambda:(f if (f:=frame('settled-wait'))['phase']=='Paused' else None),10,'settled native Pause')
    assert settled['enemies'][0]['fireSequence']==npc['fireSequence'] and settled['enemies'][0]['fireOrigin']==npc['fireOrigin']
    v.wait(lambda:(r if (r:=report()) and any(c['phase']=='Paused' and any(e['tick']==settled['tick'] for e in c['enemies']) for c in r['captures']) else None),10,'settled GPU capture')
    r=report();shots=[e for c in r['captures'] if c['file'].startswith('shot-') for e in c['enemies'] if e['visible']]
    distance=lambda a,b:math.sqrt(sum((a[k]-b[k])**2 for k in ['x','y','z']))
    assert shots and all(0<=e['tick']-(e['fireTickPlusOne']-1)<3 and e['fireSequence']>0 and e['recoil']>0
        and distance(e['acceptedOrigin'],e['flashOrigin'])<.0001 and distance(e['acceptedDirection'],e['flashDirection'])<.0001 for e in shots)
    v.save('fire-probe-evidence.json',{'source':'Actual native AI events / own GPU framebuffer','headsets':0,'probeDirectory':str(probe),'captures':r['captures'],'dayPaused':day_paused,'paused':paused,'settled':settled,'poseOrCombatInjected':False})
    v.stage('review',probeDirectory=str(probe),note='Inspect shot and paused PNGs, then review.done. No input is injected by this marker.')
    v.wait(lambda:(v.directory/'review.done').exists(),300,'actual GPU image review')
    # Stop only this explicitly enabled diagnostic while the client still owns
    # its avatar. End revokes admission and may despawn it before an End row.
    (probe/'finish.request').write_text('Finish diagnostic collection only; no game mutation',encoding='utf-8')
    final=v.wait(lambda:(r if (r:=report(True)) and r['complete'] else None),10,'explicit native diagnostic stop')
    assert final['stopReason']=='Explicit local diagnostic stop' and not final['observedEnd']
    sealed=v.seal(entry);stats=next(p for p in sealed['statistics']['players'] if p['playerId']==own['id'])
    assert 2<=stats['hitsReceived']<5 and stats['damageTaken']==stats['hitsReceived']*20 and stats['health']==100-stats['damageTaken'] and stats['ammoUsed']==0
    assert sealed['world']['header']['assetSet']=='combat-effects-v1' and sealed['world']['header']['enemyFireVersion']==1
    assert final['audioSamples']==final['callbackCount']==0 and final['source']=='NativeWindowsFramebuffer'
    v.save('fire-result.json',{'statistics':stats,'replayStatisticsMatch':sealed['replayStatisticsMatch'],'probe':final,'poseOrCombatInjected':False})
    v.evidence.extend(['Actual AI accepted shots render on their historical muzzle/direction with nonzero recoil','Native Pause, Patrol, settled effect retain the original accepted shot','GPU PNGs reviewed; diagnostic records no PCM or input','Final native replay and twenty-point damage statistics seal exactly'])
    v.summary()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime-root',type=Path)
    p.add_argument('--player-exe',type=Path,default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER',ROOT/'artifacts/desktop/VrCommand.exe')))
    p.add_argument('--api-dll',type=Path,default=Path(os.environ.get('VR_COMMAND_API_DLL',ROOT/'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    args=p.parse_args();args.duration=300;args.visible_room=3;args.job_workers=2;args.check=False
    try:module.verify_player(args)
    except(OSError,RuntimeError,ValueError) as error:p.error(str(error))
    venue=module.Venue(args)
    try:run(venue)
    except BaseException as error:venue.stage('failed',errorType=type(error).__name__);raise
    finally:
        if not venue.cleanup() and sys.exc_info()[0] is None:raise RuntimeError('Enemy fire cleanup failed')

if __name__=='__main__':main()
