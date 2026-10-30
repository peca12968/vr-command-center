"""Verify normal native keyboard reloads and a paused cosmetic action.

Only this run's API, server, players and Simulation data are used. Stage marker
files acknowledge actual user/computer-use input; they never inject poses.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('reload_venue',ROOT/'scripts/start-desktop-venue.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def run(v):
    v.start()
    mission=v.request('/api/missions',{'name':'Native reload - Simulation','briefing':'Real Space / R; saved reload clock, no pose injection','durationSeconds':600,
        'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},'enemies':{'count':0,'behavior':'Hold','autoAttack':False},'props':[]},expected=201)
    entry=v.create(mission,[3],'reload',role='Room3');peer_id=str(uuid.uuid4())
    state=v.request('/api/sessions/'+entry['id']+'/players',{'playerId':peer_id,'roomId':3,'name':'Reload peer','headset':'Quest3'},role='Room3')
    peer=next(p for p in state['players'] if p['id']==peer_id);entry['players'].append(peer)
    v.wait(lambda:v.request('/api/sessions/'+entry['id']+'/world',optional=True),90,'native reload recording')
    v.launch('reload-peer',v.client_config(entry,v.ticket(entry,peer)))
    probe=v.runtime_directory/'reload-probe'
    own=entry['players'][0];v.launch('reload-player',v.client_config(entry,v.ticket(entry,own)),True,extra_args=['--vr-hud-probe',str(probe.resolve())])
    v.wait(lambda:v.connected(entry),30,'two connected native clients');v.command(entry,'Begin');samples=[]
    def observe(label):
        value=v.frame(entry,measure=True);frame=value['packet']['frame'];body=next(p for p in frame['players'] if p['id']==own['id'])
        assert body['connected'] and body['rig']['kind']=='Simulated' and body['hasWeaponPresentation'] and body['health']==100
        row={'label':label,'sequence':value['packet']['sequence'],'tick':frame['tick'],'phase':frame['phase'],'body':body};samples.append(row);v.save('reload-samples.json',samples);return row
    baseline=observe('baseline');assert baseline['body']['magazine']==30 and baseline['body']['reloadUntilTick']==0
    v.stage('fire',key='space',presses=1,note='Actual Space once, then fire.done')
    v.wait(lambda:observe('fire-wait')['body']['magazine']==29 and (v.directory/'fire.done').exists(),240,'one actual shot')
    v.stage('reload',key='r',presses=1,note='Actual R once. Helper pauses as soon as the native saved frame reports reloading.')
    active=v.wait(lambda:(row if (row:=observe('reload-wait'))['body']['reloading'] else None),240,'actual reload acceptance')
    v.wait(lambda:(row if 6<=(row:=observe('withdraw-wait'))['tick']-(row['body']['reloadUntilTick']-30)<23 else None),3,'accepted nonzero magazine withdrawal')
    v.command(entry,'Pause');paused=v.wait(lambda:(row if (row:=observe('pause-wait'))['phase']=='Paused' else None),10,'native reload Pause')
    assert paused['body']['reloading'] and paused['body']['reloadUntilTick']==active['body']['reloadUntilTick']
    assert 5<paused['tick']-(paused['body']['reloadUntilTick']-30)<25 and paused['body']['magazine']==29
    v.stage('paused-review',tick=paused['tick'],reloadUntilTick=paused['body']['reloadUntilTick'],elapsed=paused['tick']-(paused['body']['reloadUntilTick']-30),
        note='Inspect actual native gloves / reload state. Press actual Space while paused, then pause.done; no ammo may be consumed.')
    v.wait(lambda:observe('paused-review') and (v.directory/'pause.done').exists(),600,'actual paused review')
    still=observe('still-paused');assert still['tick']==paused['tick'] and still['body']['reloadUntilTick']==paused['body']['reloadUntilTick'] and still['body']['magazine']==29
    v.command(entry,'Resume');complete=v.wait(lambda:(row if not (row:=observe('completion-wait'))['body']['reloading'] and row['body']['magazine']==30 else None),10,'original reload completion')
    assert complete['body']['reserve']==89 and complete['body']['reloadUntilTick']==0 and complete['body']['head']==baseline['body']['head']
    v.stage('complete-review',magazine=30,reserve=89,note='Inspect returned magazine / grip, then complete.done')
    v.wait(lambda:observe('complete-review') and (v.directory/'complete.done').exists(),600,'actual complete review')
    sealed=v.seal(entry);stats=next(p for p in sealed['statistics']['players'] if p['playerId']==own['id'])
    assert stats['ammoUsed']==1 and stats['shotsHit']==stats['kills']==stats['damageTaken']==0 and stats['health']==100
    assert sealed['world']['header']['assetSet']=='weapon-actions-v1' and sealed['world']['header']['weaponPresentationVersion']==1
    report=v.wait(lambda:json.loads((probe/'report.json').read_text(encoding='utf-8-sig')) if (probe/'report.json').exists() else None,10,'native HUD GPU report')
    assert report['mode']=='hud' and report['complete'] and report['audioSamples']==report['callbackCount']==0 and not report['error']
    v.save('reload-result.json',{'source':'Actual Windows keyboard / own native HUD GPU probe; Simulation','headsets':0,'baseline':baseline,'active':active,'paused':paused,'still':still,
        'complete':complete,'statistics':stats,'replayStatisticsMatch':sealed['replayStatisticsMatch'],'poseOrCombatInjected':False,'diagnosticProbeEnabled':True,'probeDirectory':str(probe),'probeReport':report})
    v.evidence.extend(['Actual Space / accepted reload deadline','Native Pause freezes saved reload tick; paused Space consumes no ammo','Resume completes original 30 ticks and spends only one reserve round','Exact replay / ledger seal agrees'])
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
        if not venue.cleanup() and sys.exc_info()[0] is None:raise RuntimeError('Reload fixture cleanup failed')

if __name__=='__main__':main()
