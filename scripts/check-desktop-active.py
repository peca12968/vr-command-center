"""Actual visible W / Space / R / Space with 24 native receiving peers.

Current successful game binary, no pose / weapon injection or test RPC.
Acknowledgements confirm observed UI actions; they do not send game input.
"""
import argparse
from datetime import datetime,timezone
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('active_capacity',ROOT/'scripts/check-desktop-capacity.py')
capacity=importlib.util.module_from_spec(spec);spec.loader.exec_module(capacity)
venue_module=capacity.venue_module
spec=importlib.util.spec_from_file_location('active_debrief',ROOT/'scripts/check-desktop-debrief.py')
debrief=importlib.util.module_from_spec(spec);spec.loader.exec_module(debrief)


def validate_final_results(entry,native,sealed,delivery,results,combat_sequence,server_log):
    players={p['id']:p for p in entry['players']}
    if len(native)!=25 or len(players)!=25 or {p['playerId'] for p in native}!=set(players) or len({p['name'] for p in native})!=25:
        raise ValueError('Final result roster is not the original 25 native players')
    if delivery['allAcknowledged'] is not True or delivery['timedOut']!=[] or set(delivery['phases'])!={p['name'] for p in native} \
        or any(p!='acknowledged' for p in delivery['phases'].values()):
        raise ValueError('All original players must acknowledge their final results')
    if len(results)!=25 or any(not isinstance(p,dict) for p in results) or len({p['playerId'] for p in results})!=25:
        raise ValueError('Missing or duplicated individual final results')
    acknowledgments=[int(value) for value in re.findall(r'VR_SERVER_DEBRIEF_ACK id=(\d+)',server_log)]
    if len(acknowledgments)!=25 or set(acknowledgments)!={p['nativeConnectionId'] for p in native} or 'VR_SERVER_DEBRIEF_TIMEOUT ' in server_log:
        raise ValueError('Server did not acknowledge exactly the original 25 connections')
    for owner,result in zip(native,results):
        player=players[owner['playerId']]
        if owner['admissionId']!=player['admissionId'] or owner['roomId']!=player['roomId']:
            raise ValueError('Native result owner changed admission or room')
        debrief.validate_result(result,entry,player,sealed)
        if result['finalStreamSequence']!=combat_sequence:raise ValueError('Final player combat boundary differs')
    return results


def actor(frame,identity):return next(p for p in frame['players'] if p['id']==identity)


def validate_input(frame,statistics,initial,identity,stage):
    players=frame['players'];original={p['id']:p for p in initial['players']}
    if len(players)!=25 or {p['id'] for p in players}!=set(original):raise ValueError('Incomplete / foreign active roster')
    metrics={p['playerId']:p for p in statistics['players']}
    if len(metrics)!=25 or set(metrics)!=set(original):raise ValueError('Incomplete active statistics')
    own=actor(frame,identity);start=original[identity]
    if not math.isfinite(own['head']['y']) or abs(own['head']['y']-start['head']['y'])>.02:raise ValueError('Unexpected active head height')
    distance=sum((own['head'][k]-start['head'][k])**2 for k in ('x','z'))**.5
    if not math.isfinite(distance) or not .02<distance<.4:raise ValueError('Expected one real short movement')
    shots={'move':0,'shot':1,'reload':1,'kill':2}[stage]
    if (own['fireSequence']>0)!=(shots>0):raise ValueError('Active fire witness differs')
    expected=(30,90) if stage=='move' else (29,90) if stage=='shot' else (30,89) if stage=='reload' else (29,89)
    for p in players:
        if not p['connected'] or p['health']!=100 or p['rig']['kind']!='Simulated':raise ValueError('Active participant is stale / injured / not Simulation')
        if p['reloading']:raise ValueError('Reload has not completed')
        if p['id']!=identity:
            if p['head']!=original[p['id']]['head'] or p['magazine']!=30 or p['reserve']!=90 or p['fireSequence']!=0 \
                or any(metrics[p['id']][k]!=0 for k in ('ammoUsed','shotsHit','kills','damageTaken','hitsReceived')):
                raise ValueError('Input leaked into a passive participant')
    metric=metrics[identity]
    if (own['magazine'],own['reserve'])!=expected or metric['ammoUsed']!=shots or metric['shotsHit']!=shots \
        or metric['kills']!=(1 if stage=='kill' else 0) or metric['accuracyPercent']!=(100 if shots else 0):
        raise ValueError('Accepted shot / reload / kill ledger differs')
    target=next(p for p in frame['enemies'] if p['roomId']==3)
    if target['health']!=100-50*shots:raise ValueError('Authoritative target damage differs')
    return {'distanceMeters':distance,'shots':shots,'statistics':metric,'enemyId':target['id'],'enemyHealth':target['health']}


def validate_active_replica(snapshot,frame,native,*,server):
    capacity.validate_replica(snapshot,frame,native,server=server)
    for p in snapshot['actors']:
        if not p['enemy'] and p['fireSequence']!=actor(frame,p['id'])['fireSequence']:
            raise ValueError('Local player fire witness differs from authority')


def analyze_continuity(report,start):
    rows=[r for r in report['rows'] if r['seconds']>=start]
    running=[r for r in rows if r['phase']==1]
    invalid_clock=any(not math.isfinite(r['seconds']) for r in rows) or any(b['seconds']<=a['seconds'] for a,b in zip(rows,rows[1:]))
    bad=[r for r in running if not r['ready'] or not r['coherent'] or r['players']!=25 or r['connected']!=25 or r['health']!=2500]
    gaps=[b['seconds']-a['seconds'] for a,b in zip(rows,rows[1:]) if a['phase']==b['phase']==1]
    maximum=max(gaps,default=None)
    return {'passed':bool(running) and not invalid_clock and not bad and maximum is not None and maximum<1.5,
        'runningRows':len(running),'badRunningRows':bad,'maximumAdjacentRunningTickGapSeconds':maximum,'invalidClock':invalid_clock}


def world_continuity_fault(frame,expected):
    if frame['phase']!='Running':return None
    players=frame['players'];invalid=[p['id'] for p in players if not p['connected'] or p['health']!=100 or p['rig']['kind']!='Simulated']
    if len(players)!=25 or {p['id'] for p in players}!=expected or invalid:
        return {'tick':frame['tick'],'invalidPlayerIds':invalid,'rosterCount':len(players)}
    return None


def capture(v,entry,native,label,references):
    pending={r['name'] for r in native}|{entry['name']+'-server'};deadline=time.monotonic()+8
    while pending:
        if time.monotonic()>deadline:raise RuntimeError('Active replica convergence timed out: '+label)
        reference=v.frame(entry,measure=True)
        if reference['packet'].get('suspended'):raise RuntimeError('Active world suspended for management loss')
        v.capture_number+=1;number=v.capture_number
        if number>64:raise RuntimeError('Active capture bound exceeded')
        references[reference['packet']['sequence']]=reference
        v.save(f'active-reference-{number}.json',reference)
        if not v.args.replication_probe:return
        ordered=sorted(pending)
        for offset in range(0,len(ordered),v.args.capture_batch):
            group=ordered[offset:offset+v.args.capture_batch]
            for name in group:venue_module.atomic_json(v.probes[name]/'capture.request',number)
            v.wait(lambda:all((v.probes[n]/f'capture-{number}.json').exists() for n in group),5,'active capture '+label)
            for name in group:
                snapshot=venue_module.read_json(v.probes[name]/f'capture-{number}.json');error=None
                try:validate_active_replica(snapshot,reference['packet']['frame'],native,server=name.endswith('-server'))
                except ValueError as issue:error=str(issue)
                v.replica_checks.append({'name':name,'stage':label,'capture':number,'referenceSequence':reference['packet']['sequence'],
                    'authorityTick':reference['packet']['frame']['tick'],'observedTick':snapshot['presentation']['tick'],
                    'passed':error is None,'error':error})
                if error is None:pending.remove(name)
        v.save('replication-checks.json',v.replica_checks)
        if pending:time.sleep(.2)


def finish(v,names):
    if not v.args.replication_probe:return
    for name in names:(v.probes[name]/'finish.request').write_text('')
    v.wait(lambda:all((v.probes[n]/'report.json').exists() for n in names),15,'active explicit probe finish')
    for name in names:
        value=venue_module.read_json(v.probes[name]/'report.json')
        if not value['complete'] or value['truncated']:raise RuntimeError('Incomplete active probe: '+name)
        initial=next(c for c in v.replica_checks if c['name']==name and c['stage']=='initial' and c['passed'])
        start=venue_module.read_json(v.probes[name]/f'capture-{initial["capture"]}.json')['seconds']
        v.active_continuity[name]=analyze_continuity(value,start)
        v.save('active-continuity.json',v.active_continuity)


def replay(v,entry,references):
    request=urllib.request.Request(v.base+f'/api/sessions/{entry["id"]}/world/watch?mode=replay&fromMs=0&rate=4',headers={'Authorization':'Bearer '+v.tokens['Master']})
    previous=0;matched=set();last=None;faults=[];expected={p['id'] for p in entry['players']}
    deadline=time.monotonic()+entry['sealed']['world']['durationMilliseconds']/4000+30
    with urllib.request.urlopen(request,timeout=10) as response:
        for value in capacity.sse_frames(response):
            if time.monotonic()>deadline:raise RuntimeError('Active replay deadline exceeded')
            number=value['packet']['sequence']
            if number!=previous+1:raise RuntimeError('Active replay is not contiguous')
            previous=number;last=value
            if min(references)<=number<=max(references):
                fault=world_continuity_fault(value['packet']['frame'],expected)
                if fault:faults.append({'sequence':number,**fault})
            if number in references:
                if value['packet']!=references[number]['packet'] or value['statistics']!=references[number]['statistics']:
                    raise RuntimeError('Saved active checkpoint differs from replay')
                matched.add(number)
    if matched!=set(references) or previous!=entry['sealed']['world']['acceptedSequence'] or last['packet']['frame']['phase']!='Ended':
        raise RuntimeError('Active replay did not include every reference / final seal')
    return {'frames':previous,'matchedReferences':len(matched),'complete':True,'worldContinuityFaults':faults,'continuityPassed':not faults}


def run(v):
    def check(value,message):
        if not value:raise RuntimeError(message)
        v.evidence.append(message);print('PASS: '+message,flush=True)
    resources=[]
    def resource():
        value=capacity.memory_status();capacity.require_memory(value);resources.append(value);v.save('active-resources.json',resources)
    v.active_continuity={};v.start();resource()
    mission=v.request('/api/missions',{'name':'Active 25 native peers - Simulation','briefing':'One real PC operator, 24 receiving peers; no headset.',
        'durationSeconds':600,'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},
        'enemies':{'count':5,'behavior':'Hold','autoAttack':False},
        'props':[{'assetId':'barrel','position':{'x':-4.125,'y':0,'z':-1},'yawDegrees':0}]},expected=201)
    entry=v.create(mission,[1,2,3,4,5],'active-linked')
    for room in range(1,6):
        for seat in range(4):
            identity=str(uuid.uuid4());state=v.request(f'/api/sessions/{entry["id"]}/players',{'playerId':identity,'roomId':room,'name':f'Active R{room}-{seat+1}','headset':'Quest3'},role='Room'+str(room))
            entry['players'].append(next(p for p in state['players'] if p['id']==identity))
    capacity.validate_roster(entry['players'],[1,2,3,4,5],5)
    own=next(p for p in entry['players'] if p['roomId']==3 and p['seat']==0);native=[]
    v.wait(lambda:v.request(f'/api/sessions/{entry["id"]}/world',optional=True),90,'active world')
    pairs=sorted(entry['players'],key=lambda p:(p['id']==own['id'],p['seat'],p['roomId']))
    for index,p in enumerate(pairs,1):
        resource();name=entry['name']+'-client-'+p['admissionId'];v.launch(name,v.client_config(entry,v.ticket(entry,p)),p['id']==own['id'])
        native.append({'name':name,'sessionId':entry['id'],'playerId':p['id'],'admissionId':p['admissionId'],
            'roomId':p['roomId'],'seat':p['seat'],'pid':v.processes[name].pid,'visible':p['id']==own['id']})
        if index%5==0:
            expected={p['playerId'] for p in native}
            v.wait(lambda:{p['id'] for p in v.frame(entry)['packet']['frame']['players'] if p['connected'] and p['rig']['kind']=='Simulated'}==expected,100,'active batch admission')
    for row in native:
        ids=set(re.findall(r'VR_CLIENT_CONNECTED id=(\d+)',(v.directory/(row['name']+'.log')).read_text(errors='replace')))
        if len(ids)!=1:raise RuntimeError('Active client does not have exactly one connection')
        row['nativeConnectionId']=int(ids.pop())
    check(len({r['pid'] for r in native})==25 and len({r['nativeConnectionId'] for r in native})==25,'25 distinct real native clients and connections, one visible')
    v.save('active-native-clients.json',native);v.command(entry,'Begin')
    initial=v.wait(lambda:(p if (p:=v.frame(entry,measure=True))['packet']['frame']['phase']=='Running' else None),30,'active Running')
    capacity.validate_frame(initial,entry['players'])
    target=next(p for p in initial['packet']['frame']['enemies'] if p['roomId']==3)
    check(abs(target['feet']['x']+3)<.001 and abs(target['feet']['z']+1)<.001,'ordinary barrel layout places the target on the real sight line')
    references={};capture(v,entry,native,'initial',references)
    v.save('active-ready.json',{'source':'Simulation','headsets':0,'visiblePlayerId':own['id'],'visiblePid':next(r['pid'] for r in native if r['visible']),
        'nativeClients':25,'renderedClients':1,'directory':str(v.directory),'runtimeDirectory':str(v.runtime_directory)})
    observations=[];accepted=[];next_resource=time.monotonic()+5
    for stage,key in [('move','w'),('shot','space'),('reload','r'),('kill','space')]:
        if stage!='move':v.command(entry,'Resume');v.wait(lambda:v.frame(entry)['packet']['frame']['phase']=='Running',15,'active Resume')
        v.stage('active-input',action=stage,key=key,acknowledgement=stage+'.done',seconds=v.args.input_timeout)
        def observed():
            nonlocal next_resource
            if time.monotonic()>=next_resource:resource();next_resource=time.monotonic()+5
            packet=v.frame(entry,measure=True);frame=packet['packet']['frame'];stats=v.request(f'/api/sessions/{entry["id"]}/statistics')
            observations.append({'stage':stage,'sequence':packet['packet']['sequence'],'utc':datetime.now(timezone.utc).isoformat()})
            try:result=validate_input(frame,stats,initial['packet']['frame'],own['id'],stage)
            except ValueError:return None
            return (packet,result) if (v.directory/(stage+'.done')).exists() else None
        packet,result=v.wait(observed,v.args.input_timeout,'actual UI '+stage);v.command(entry,'Pause')
        frozen=v.wait(lambda:(p if (p:=v.frame(entry,measure=True))['packet']['frame']['phase']=='Paused' else None),15,'active Pause')
        validate_input(frozen['packet']['frame'],v.request(f'/api/sessions/{entry["id"]}/statistics'),initial['packet']['frame'],own['id'],stage)
        capture(v,entry,native,stage,references)
        accepted.append({'stage':stage,**result,'referenceSequence':frozen['packet']['sequence']});references[frozen['packet']['sequence']]=frozen
        scope='all 25 receiving replicas' if v.args.replication_probe else 'authority only (receiver state not observed)'
        check(True,stage+': actual input / authoritative damage / '+scope+' agree; passive players unchanged')
        v.save('active-input-observations.json',observations);v.save('active-input-results.json',accepted)
    finish(v,[r['name'] for r in native]);sealed=v.seal(entry)
    report=capacity.practice.save_report(v,entry,sealed['statistics']);finish(v,[entry['name']+'-server'])
    v.stage('active-results',players=len(native))
    delivery=v.wait_for_player_results(entry)
    results=[debrief.final_result(v,p['name']) for p in native]
    server_log=debrief.log_text(v,entry['name']+'-server')
    validate_final_results(entry,native,sealed,delivery,results,v.state(entry)['combatStream']['acceptedSequence'],server_log)
    if any(debrief.log_text(v,p['name']).count('VR_CLIENT_CONNECTED id=')!=1 for p in native):raise ValueError('A native player changed connection before its final result')
    v.save('active-player-results.json',{'delivery':delivery,'results':results,'serverAcknowledgedConnections':[int(value) for value in re.findall(r'VR_SERVER_DEBRIEF_ACK id=(\d+)',server_log)]})
    check(True,'all 25 original players acknowledge exact individual world / combat / ledger results before shutdown')
    v.stop_round(entry)
    playback=replay(v,entry,references);check(playback['complete'],'every saved active checkpoint matches contiguous replay / final ledger and CSV')
    findings=capacity.native_log_findings(v.directory);check(not findings,'no native send queue full messages')
    v.save('active-result.json',{'complete':False,'source':'Actual Windows native input / UDP / NGO; Simulation','headsets':0,'hosts':1,
        'activePlayers':1,'receivingPeers':24,'renderedClients':1,'poseOrWeaponInjected':False,'all25SimultaneouslyActive':False,
        'statistics':accepted[-1]['statistics'],'inputStages':accepted,'replay':playback,'csv':report,'nativeLogFindings':findings,
        'individualResults':results,'acknowledgedResults':len(results),
        'minimumFreePhysicalBytes':min(p['availablePhysicalBytes'] for p in resources),'networkCapacityAccepted':False,
        'localReplicaContinuityChecked':v.args.replication_probe,
        'captureBatch':v.args.capture_batch if v.args.replication_probe else None,
        'continuityPassed':playback['continuityPassed'] and all(p['passed'] for p in v.active_continuity.values())})
    scope='saved Running world frames and observed local tick rows' if v.args.replication_probe else 'saved Running world frames only (local replicas not observed)'
    check(playback['continuityPassed'] and all(p['passed'] for p in v.active_continuity.values()),scope+' retain every participant between checkpoints')
    v.summary()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--runtime-root',type=Path,required=True)
    parser.add_argument('--without-replication-probe',action='store_true',help='World/replay control only; does not establish receiving peer state')
    parser.add_argument('--capture-batch',type=int,choices=range(1,27),default=1,help='Bound simultaneous local snapshot IO; 26 recreates fan-out observations')
    parser.add_argument('--input-timeout',type=int,choices=range(15,121),default=30)
    parser.add_argument('--api-dll',type=Path,default=Path(os.environ.get('VR_COMMAND_API_DLL',ROOT/'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    parser.add_argument('--player-exe',type=Path,default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER',ROOT/'artifacts/desktop/VrCommand.exe')))
    args=parser.parse_args();args.duration=600;args.visible_room=3;args.job_workers=2;args.check=False;args.replication_probe=not args.without_replication_probe
    if args.replication_probe and args.input_timeout>40:parser.error('Replication probe has a 240-second lifetime; use at most 40 seconds per UI stage')
    venue_module.verify_player(args);v=capacity.ReplicationVenue(args,artifact_family='desktop-active')
    try:v.stage('starting',source='Simulation',headsets=0,activePlayers=1,receivingPeers=24);run(v)
    except BaseException as error:v.stage('failed',errorType=type(error).__name__);raise
    finally:
        failed=sys.exc_info()[0] is not None;cleaned=v.cleanup()
        if not cleaned:
            v.stage('failed',errorType='CleanupError')
            if not failed:raise RuntimeError('Active fixture cleanup failed')
        elif not failed:
            result=venue_module.read_json(v.directory/'active-result.json');result['complete']=True;v.save('active-result.json',result)
            v.stage('passed',checks=len(v.evidence),rounds=1)


if __name__=='__main__':main()
