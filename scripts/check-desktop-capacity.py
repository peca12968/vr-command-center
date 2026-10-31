"""Actual 25-client Windows loopback capacity / lifecycle checks. Simulation only.

Runs Linked, then five independent full rooms on fresh owned API / SSD data.
No headsets, input injection, graphics, packet-loss proxy or timing probes.
"""
import argparse
from collections import Counter
import ctypes
from ctypes import wintypes
from datetime import datetime,timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('capacity_practice',ROOT/'scripts/start-desktop-demo.py')
practice=importlib.util.module_from_spec(spec);spec.loader.exec_module(practice)
venue_module=practice.venue_module


def memory_status():
    if os.name!='nt':raise OSError('Windows native capacity fixture required')
    class Status(ctypes.Structure):
        _fields_=[('length',wintypes.DWORD),('load',wintypes.DWORD)]+[(n,ctypes.c_ulonglong) for n in
            ('totalPhysical','availablePhysical','totalPage','availablePage','totalVirtual','availableVirtual','reserved')]
    api=ctypes.WinDLL('kernel32',use_last_error=True);api.GlobalMemoryStatusEx.argtypes=[ctypes.POINTER(Status)];api.GlobalMemoryStatusEx.restype=wintypes.BOOL
    value=Status();value.length=ctypes.sizeof(value)
    if not api.GlobalMemoryStatusEx(ctypes.byref(value)):raise ctypes.WinError(ctypes.get_last_error())
    return {'totalPhysicalBytes':value.totalPhysical,'availablePhysicalBytes':value.availablePhysical}


def require_memory(value):
    if any(type(value[k]) is not int for k in ('totalPhysicalBytes','availablePhysicalBytes')) \
        or not 0<=value['availablePhysicalBytes']<=value['totalPhysicalBytes']:raise ValueError('Invalid host memory observation')
    if value['availablePhysicalBytes']<2*1024**3:raise RuntimeError('Less than 2 GiB available; stop adding owned native processes')


def validate_roster(players,rooms,seats):
    if len(players)!=len(rooms)*seats or len({p['id'] for p in players})!=len(players) or len({p['admissionId'] for p in players})!=len(players):
        raise ValueError('Duplicate or incomplete admission roster')
    if Counter(p['roomId'] for p in players)!=Counter({r:seats for r in rooms}):raise ValueError('Wrong room allocation')
    for room in rooms:
        if {p['seat'] for p in players if p['roomId']==room}!=set(range(seats)):raise ValueError('Missing or aliased spawn seats')


def validate_frame(value,players,*,active=True):
    packet=value['packet'];frame=packet['frame'];actual=frame['players'];expected={p['id']:p for p in players}
    if len(actual)!=len(expected) or {p['id'] for p in actual}!=set(expected):raise ValueError('World has foreign, duplicate or missing players')
    if packet.get('suspended'):raise ValueError('Native world suspended for management loss')
    for p in actual:
        owner=expected[p['id']]
        if p['roomId']!=owner['roomId'] or p['rig']['kind']!='Simulated':raise ValueError('World room or rig source disagrees')
        if active:
            x=(owner['roomId']-3)*14+(owner['seat']-2)*1.5
            if not p['connected'] or p['health']!=100 or abs(p['head']['x']-x)>.02 or abs(p['head']['z']+3)>.02:
                raise ValueError('Expected a fresh healthy native rig at its own spawn seat')
    return frame


def sse_frames(response):
    kind=''
    for raw in response:
        line=raw.decode('utf-8').strip()
        if line.startswith('event: '):kind=line[7:]
        elif line.startswith('data: '):
            if kind=='frame':yield json.loads(line[6:])
            elif kind=='complete':return
    raise RuntimeError('Replay ended without complete event')


def native_log_findings(directory):
    findings=[]
    for path in sorted(directory.glob('*.log')):
        count=path.read_text(errors='replace').count('send queue full')
        if count:findings.append({'file':path.name,'sendQueueFull':count})
    return findings


def verify_replay(v,entry,bounds):
    route=v.base+f'/api/sessions/{entry["id"]}/world/watch?mode=replay&fromMs={bounds["fromMs"]}&rate=4'
    request=urllib.request.Request(route,headers={'Authorization':'Bearer '+v.tokens['Master']})
    previous=None;stable=0;first=None;last=None
    deadline=time.monotonic()+(entry['sealed']['world']['durationMilliseconds']-bounds['fromMs'])/4000+30
    with urllib.request.urlopen(request,timeout=10) as response:
        for value in sse_frames(response):
            if time.monotonic()>deadline:raise RuntimeError('Replay exceeded bounded observation time')
            sequence=value['packet']['sequence']
            if previous is not None and sequence!=previous+1:raise RuntimeError('Sequential replay skipped or repeated a frame')
            if previous is None and sequence>bounds['firstSequence']:raise RuntimeError('Replay seek skipped stable start')
            previous=sequence;last=value
            if bounds['firstSequence']<=sequence<=bounds['lastSequence']:
                frame=validate_frame(value,entry['players'])
                if frame['phase']!='Running':raise RuntimeError('Stable replay interval is not Running')
                first=first or value;stable+=1
    if stable!=bounds['lastSequence']-bounds['firstSequence']+1 or stable<2 or previous!=entry['sealed']['world']['acceptedSequence']:
        raise RuntimeError('Replay did not cover every stable / final frame')
    if last['packet']['frame']['phase']!='Ended' or sorted(last['statistics'],key=lambda p:p['playerId'])!=sorted(entry['sealed']['statistics']['players'],key=lambda p:p['playerId']):
        raise RuntimeError('Replay final state / ledger mismatch')
    return {'stableFrames':stable,'firstStableSequence':first['packet']['sequence'],'lastStableSequence':bounds['lastSequence'],
        'finalSequence':previous,'complete':True}


def run(v):
    v.start();results=[];resources=[]
    def resource(phase):
        value=memory_status();value.update(phase=phase,utc=datetime.now(timezone.utc).isoformat(),
            ownNativeProcesses=sum(name!='api' for name in v.processes))
        resources.append(value);v.save('capacity-resources.json',resources);require_memory(value)
    def check(ok,message):
        if not ok:raise RuntimeError(message)
        v.evidence.append(message);print('PASS: '+message,flush=True)
    modes=['linked','independent'] if v.args.mode=='both' else [v.args.mode]
    for mode in modes:
        entries=[];rooms_list=[[1,2,3,4,5]] if mode=='linked' else [[r] for r in range(1,6)]
        for rooms in rooms_list:
            name='capacity-'+mode+'-'+str(rooms[0])
            mission=v.request('/api/missions',{'name':name+' - Simulation','briefing':'Actual native static desktop rigs, no headset.',
                'durationSeconds':600,'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},
                'enemies':{'count':len(rooms),'behavior':'Hold','autoAttack':False},'props':[]},expected=201)
            resource(name+'-server');entry=v.create(mission,rooms,name);entries.append(entry)
            for room in rooms:
                for _ in range(v.args.players_per_room-1):
                    identity=str(uuid.uuid4());state=v.request(f'/api/sessions/{entry["id"]}/players',
                        {'playerId':identity,'roomId':room,'name':f'Capacity R{room}','headset':'Quest3'},role='Room'+str(room))
                    entry['players'].append(next(p for p in state['players'] if p['id']==identity))
            validate_roster(entry['players'],rooms,v.args.players_per_room)
            if v.args.players_per_room==5:
                for room in rooms:v.request(f'/api/sessions/{entry["id"]}/players',
                    {'playerId':str(uuid.uuid4()),'roomId':room,'name':'Overflow','headset':'Quest3'},role='Room'+str(room),expected=409)
        check(sum(len(e['players']) for e in entries)==5*v.args.players_per_room,mode+': five full admission / spawn allocations and overflow fences')
        started={e['id']:set() for e in entries};native=[]
        for entry in entries:v.wait(lambda e=entry:v.request(f'/api/sessions/{e["id"]}/world',optional=True),90,'capacity world')
        pairs=[(e,p) for e in entries for p in sorted(e['players'],key=lambda p:(p['seat'],p['roomId']))]
        for index,(entry,p) in enumerate(pairs,1):
            resource(mode+'-client-'+str(index));name=entry['name']+'-client-'+p['admissionId']
            v.launch(name,v.client_config(entry,v.ticket(entry,p)));started[entry['id']].add(p['id'])
            native.append({'name':name,'sessionId':entry['id'],'playerId':p['id'],'admissionId':p['admissionId'],
                'roomId':p['roomId'],'seat':p['seat'],'pid':v.processes[name].pid})
            if index%5==0 or index==len(pairs):
                for e in entries:
                    expected=started[e['id']]
                    def accepted(e=e,expected=expected):
                        value=v.frame(e)
                        actual={p['id'] for p in value['packet']['frame']['players'] if p['connected'] and p['rig']['kind']=='Simulated'}
                        return value if actual==expected else None
                    if expected:v.wait(accepted,100,'capacity batch admission')
                v.stage('admitting',mode=mode,nativeClients=index,targetClients=len(pairs))
        for entry in entries:validate_frame(v.wait(lambda e=entry:v.connected(e),100,'all native capacity clients'),entry['players'])
        for entry in entries:
            rows=[r for r in native if r['sessionId']==entry['id']]
            for row in rows:
                ids=set(re.findall(r'VR_CLIENT_CONNECTED id=(\d+)',(v.directory/(row['name']+'.log')).read_text(errors='replace')))
                if len(ids)!=1:raise RuntimeError('A native client did not retain one unique connection')
                row['nativeConnectionId']=int(ids.pop())
            check(len({r['nativeConnectionId'] for r in rows})==len(rows),entry['name']+': distinct native UDP / NGO client connections')
        v.save(mode+'-native-clients.json',native)
        check(len({r['pid'] for r in native})==len(pairs),mode+': every player owns a distinct live native process')
        if mode=='linked':v.command(entries[0],'Begin',role='Room1',expected=403)
        else:v.command(entries[0],'Begin',role='Room2',expected=403)
        for entry in entries:v.command(entry,'Begin')
        bounds={};observations=[]
        for entry in entries:
            value=v.wait(lambda e=entry:(f if (f:=v.frame(e,measure=True))['packet']['frame']['phase']=='Running' else None),30,'capacity Running')
            validate_frame(value,entry['players']);bounds[entry['id']]={'firstSequence':value['packet']['sequence'],'fromMs':value['packet']['elapsedMilliseconds']}
        v.stage('running',mode=mode,nativeClients=len(pairs),seconds=v.args.seconds)
        deadline=time.monotonic()+v.args.seconds;next_status=time.monotonic()+15;next_memory=time.monotonic()+5
        while time.monotonic()<deadline:
            for entry in entries:
                value=v.frame(entry,measure=True);frame=validate_frame(value,entry['players'])
                if frame['phase']!='Running':raise RuntimeError('Capacity stable phase stopped Running')
                observations.append({'sessionId':entry['id'],'sequence':value['packet']['sequence'],'tick':frame['tick'],'utc':datetime.now(timezone.utc).isoformat()})
            if time.monotonic()>=next_memory:resource(mode+'-running');next_memory=time.monotonic()+5
            if time.monotonic()>=next_status:v.stage('running',mode=mode,nativeClients=len(pairs),remainingSeconds=max(0,round(deadline-time.monotonic())));next_status=time.monotonic()+15
            time.sleep(.2)
        for entry in entries:
            value=v.frame(entry,measure=True);validate_frame(value,entry['players']);bounds[entry['id']]['lastSequence']=value['packet']['sequence']
        v.save(mode+'-stable-observations.json',observations);check(bool(observations),mode+': all live stable samples have fresh healthy per-seat Simulation rigs')
        first=entries[0];v.command(first,'Pause')
        paused=v.wait(lambda:(f if (f:=v.frame(first,measure=True))['packet']['frame']['phase']=='Paused' else None),15,'capacity Pause')
        other_ticks={e['id']:v.frame(e)['packet']['frame']['tick'] for e in entries[1:]};time.sleep(.6)
        check(v.frame(first,measure=True)['packet']['frame']['tick']==paused['packet']['frame']['tick'],mode+': Pause freezes the targeted world tick')
        for entry in entries[1:]:
            value=v.frame(entry,measure=True);validate_frame(value,entry['players'])
            if value['packet']['frame']['phase']!='Running' or value['packet']['frame']['tick']<=other_ticks[entry['id']]:raise RuntimeError('Independent room stopped with another room Pause')
        v.command(first,'Resume');v.wait(lambda:(f if (f:=v.frame(first,measure=True))['packet']['frame']['phase']=='Running'
            and f['packet']['frame']['tick']>paused['packet']['frame']['tick'] else None),15,'capacity Resume')
        check(True,mode+': Resume advances; other independent worlds retain active rigs')
        for entry in entries:v.command(entry,'SetEnemies',enemies={'count':len(entry['roomIds']),'behavior':'Advance','autoAttack':True})
        for entry in entries:
            v.wait(lambda e=entry:{p['roomId'] for p in v.request(f'/api/sessions/{e["id"]}/statistics')['players'] if p['hitsReceived']>0}==set(e['roomIds']),30,'authoritative AI hit in every room')
        for entry in entries:v.command(entry,'SetEnemies',enemies={'count':len(entry['roomIds']),'behavior':'Hold','autoAttack':False})
        check(True,mode+': operator-enabled authoritative AI damage recorded in all five rooms')
        reports=[]
        for entry in entries:
            sealed=v.seal(entry);report=practice.save_report(v,entry,sealed['statistics'],filename=entry['name']+'-report.csv')
            v.stop_round(entry);reports.append({'sessionId':entry['id'],'csv':report})
        for entry,result in zip(entries,reports):
            for row in (r for r in native if r['sessionId']==entry['id']):
                ids=set(re.findall(r'VR_CLIENT_CONNECTED id=(\d+)',(v.directory/(row['name']+'.log')).read_text(errors='replace')))
                if ids!={str(row['nativeConnectionId'])}:raise RuntimeError('Native connection identity changed during capacity run')
            result['replay']=verify_replay(v,entry,bounds[entry['id']])
        check(True,mode+': every stable saved frame and final CSV / ledger agree after exact seals')
        results.append({'mode':mode,'clientCount':len(pairs),'serverCount':len(entries),'stableSecondsRequested':v.args.seconds,'reports':reports})
    findings=native_log_findings(v.directory)
    if findings:print('WARN: native send queue errors observed; lifecycle checks do not establish network capacity acceptance',flush=True)
    v.save('capacity-result.json',{'complete':False,'validationScope':'server admission / static poses / lifecycle / recording only',
        'networkCapacityAccepted':False,'nativeLogFindings':findings,
        'source':'Actual Windows native UDP / NGO; Simulation','headsets':0,'hosts':1,'renderedClients':0,
        'inputInjected':False,'modes':results,'minimumFreePhysicalBytes':min(r['availablePhysicalBytes'] for r in resources)})
    v.summary()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--runtime-root',type=Path,required=True)
    parser.add_argument('--mode',choices=('linked','independent','both'),default='both')
    parser.add_argument('--players-per-room',type=int,choices=range(1,6),default=5)
    parser.add_argument('--seconds',type=int,choices=range(30,301),default=60)
    parser.add_argument('--api-dll',type=Path,default=Path(os.environ.get('VR_COMMAND_API_DLL',ROOT/'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    parser.add_argument('--player-exe',type=Path,default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER',ROOT/'artifacts/desktop/VrCommand.exe')))
    args=parser.parse_args();args.duration=600;args.visible_room=0;args.job_workers=2;args.check=False
    venue_module.verify_player(args);v=venue_module.Venue(args,artifact_family='desktop-capacity')
    try:v.stage('starting',source='Simulation',headsets=0);run(v)
    except BaseException as error:v.stage('failed',errorType=type(error).__name__);raise
    finally:
        failed=sys.exc_info()[0] is not None
        cleaned=v.cleanup()
        if not cleaned:
            v.stage('failed',errorType='CleanupError')
            if not failed:raise RuntimeError('Capacity cleanup / snapshot failed')
        elif not failed:
            result=json.loads((v.directory/'capacity-result.json').read_text());result['complete']=True;v.save('capacity-result.json',result)
            v.stage('passed',rounds=len(v.rounds),checks=len(v.evidence))


if __name__=='__main__':main()
