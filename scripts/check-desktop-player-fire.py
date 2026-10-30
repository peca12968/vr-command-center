"""Verify accepted player fire using real keyboard input and native GPU frames.

Own isolated Simulation API / server / visible client. Marker files acknowledge
actual computer-use actions and image review; they never inject input or poses.
"""
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('player_fire_venue',ROOT/'scripts/start-desktop-venue.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def run(v):
    v.start()
    mission=v.request('/api/missions',{'name':'Native player fire - Simulation','briefing':'Actual Space twice / Right; accepted shot ray and own GPU capture',
        'durationSeconds':600,'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},
        'enemies':{'count':0,'behavior':'Hold','autoAttack':False},'props':[]},expected=201)
    entry=v.create(mission,[3],'player-fire',role='Room3');own=entry['players'][0]
    v.wait(lambda:v.request('/api/sessions/'+entry['id']+'/world',optional=True),90,'player fire recording')
    probe=v.runtime_directory/'player-fire-probe'
    v.launch('player-fire-player',v.client_config(entry,v.ticket(entry,own)),True,extra_args=['--vr-player-fire-probe',str(probe.resolve())])
    v.wait(lambda:v.connected(entry),30,'visible native client')
    samples=[]
    def observe(label):
        value=v.frame(entry,measure=True);f=value['packet']['frame'];p=next(p for p in f['players'] if p['id']==own['id'])
        assert p['health']==100 and p['hasFireState']
        # Pose freshness can temporarily mark an admitted client disconnected.
        # Keep these observations; only accept input stages on a live rig.
        row={'label':label,'sequence':value['packet']['sequence'],'tick':f['tick'],'phase':f['phase'],'body':p};samples.append(row)
        v.save('player-fire-samples.json',samples);return row
    def report(final=False):
        path=probe/('report.json' if final or (probe/'report.json').exists() else 'status.json')
        try:r=json.loads(path.read_text(encoding='utf-8-sig'))
        except(FileNotFoundError,json.JSONDecodeError):return None
        if r.get('error'):raise RuntimeError(r['error'])
        return r
    v.command(entry,'Begin');baseline=observe('baseline');assert baseline['body']['magazine']==30
    v.stage('day-fire',key='space',presses=1,note='Actual Space once, then day-fire.done')
    def live(row):return row['body']['connected'] and row['body']['rig']['kind']=='Simulated'
    day=v.wait(lambda:(r if live(r:=observe('day-wait')) and r['body']['magazine']==29 and (v.directory/'day-fire.done').exists() else None),180,'actual daytime Space')
    v.wait(lambda:(r if (r:=report()) and any(p['visible'] for c in r['captures'] for p in c['players']) else None),10,'day GPU flash')
    v.command(entry,'Pause');v.wait(lambda:observe('day-pause')['phase']=='Paused',10,'day Pause')
    v.command(entry,'SetEnvironment',environment={'mode':'VR','weather':'Clear','timeOfDay':'Night','lightning':False});v.command(entry,'Resume')
    v.stage('night-fire',key='space',presses=1,note='Actual Space once at night, then night-fire.done')
    night=v.wait(lambda:(r if live(r:=observe('night-wait')) and r['body']['magazine']==28 and (v.directory/'night-fire.done').exists() else None),180,'actual nighttime Space')
    v.wait(lambda:(r if (r:=report()) and any(p['visible'] and p['fireSequence']==night['body']['fireSequence'] for c in r['captures'] for p in c['players']) else None),10,'night GPU flash')
    v.stage('turn',key='Right',presses=1,note='Actual Right once to turn; then turn.done')
    moved=v.wait(lambda:(r if live(r:=observe('turn-wait')) and r['body']['forward']!=night['body']['forward'] and (v.directory/'turn.done').exists() else None),180,'actual changed pointer direction')
    assert moved['body']['fireOrigin']==night['body']['fireOrigin'] and moved['body']['fireDirection']==night['body']['fireDirection']
    v.command(entry,'Pause');settled=v.wait(lambda:(r if (r:=observe('settled'))['phase']=='Paused' else None),10,'settled Pause')
    v.wait(lambda:(r if (r:=report()) and any(c['phase']=='Paused' and any(p['tick']==settled['tick'] for p in c['players']) for c in r['captures']) else None),10,'settled GPU capture')
    r=report();shots=[p for c in r['captures'] if c['file'].startswith('shot-') for p in c['players'] if p['visible']]
    distance=lambda a,b:math.sqrt(sum((a[k]-b[k])**2 for k in ['x','y','z']))
    assert len(shots)==2 and all(0<=p['tick']-(p['fireTickPlusOne']-1)<3 and p['recoil']>0
        and distance(p['acceptedOrigin'],p['flashOrigin'])<.0001 and distance(p['acceptedDirection'],p['flashDirection'])<.0001
        and distance(p['gun'],{k:p['pointer'][k]+p['pointerDirection'][k]*.15 for k in ['x','y','z']})<.0001 for p in shots)
    v.save('player-fire-probe-evidence.json',{'source':'Actual Windows keyboard / own GPU framebuffer','headsets':0,'probeDirectory':str(probe),
        'captures':r['captures'],'baseline':baseline,'day':day,'night':night,'moved':moved,'settled':settled,'poseOrCombatInjected':False})
    v.stage('review',probeDirectory=str(probe),note='Inspect day/night shot and settled PNGs, then review.done')
    v.wait(lambda:(v.directory/'review.done').exists(),180,'native GPU image review')
    (probe/'finish.request').write_text('Finish diagnostic collection only; no game mutation',encoding='utf-8')
    final=v.wait(lambda:(r if (r:=report(True)) and r['complete'] else None),10,'explicit probe finish')
    assert final['stopReason']=='Explicit local diagnostic stop' and not final['observedEnd'] and final['audioSamples']==final['callbackCount']==0
    sealed=v.seal(entry);stats=next(p for p in sealed['statistics']['players'] if p['playerId']==own['id'])
    assert stats['ammoUsed']==2 and stats['shotsHit']==stats['kills']==stats['hitsReceived']==stats['damageTaken']==0 and stats['health']==100
    assert sealed['world']['header']['assetSet']=='player-fire-v1' and sealed['world']['header']['playerFireVersion']==1
    v.save('player-fire-result.json',{'statistics':stats,'replayStatisticsMatch':sealed['replayStatisticsMatch'],'probe':final,'poseOrCombatInjected':False})
    v.evidence.extend(['Actual daytime and nighttime Space / accepted player rays / own GPU flash and recoil',
        'Root muzzle remains pointer plus 0.15 m; actual Right changes aim without rewriting historical shot',
        'Settled Pause and reviewed GPU PNGs; no PCM, input or pose injection','Two rounds / no hits / exact ledger and replay seal'])
    v.summary()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime-root',type=Path)
    p.add_argument('--player-exe',type=Path,default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER',ROOT/'artifacts/desktop/VrCommand.exe')))
    p.add_argument('--api-dll',type=Path,default=Path(os.environ.get('VR_COMMAND_API_DLL',ROOT/'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    args=p.parse_args();args.duration=600;args.visible_room=3;args.job_workers=2;args.check=False
    try:module.verify_player(args)
    except(OSError,RuntimeError,ValueError) as error:p.error(str(error))
    venue=module.Venue(args)
    try:run(venue)
    except BaseException as error:venue.stage('failed',errorType=type(error).__name__);raise
    finally:
        if not venue.cleanup() and sys.exc_info()[0] is None:raise RuntimeError('Player fire cleanup failed')

if __name__=='__main__':main()
