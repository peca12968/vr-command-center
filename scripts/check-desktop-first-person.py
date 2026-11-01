"""Actual desktop look / Space / R, own framebuffer sleeves and exact seals.

Only the human or computer-use supplies game input. Source poses remain Simulation.
"""
import argparse
import hashlib
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
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
venue_module=module('first_person_venue','start-desktop-venue.py')
capacity=module('first_person_stream','check-desktop-capacity.py')
debrief=module('first_person_debrief','check-desktop-debrief.py')
practice=module('first_person_report','start-desktop-demo.py')


def observer_sources():
    files=['check-desktop-first-person.py','start-desktop-venue.py','check-desktop-capacity.py','check-desktop-debrief.py','start-desktop-demo.py']
    return {file:hashlib.sha256((ROOT/'scripts'/file).read_bytes()).hexdigest() for file in files}


def vector(value):
    if not isinstance(value,dict) or set(value)!={'x','y','z'} or any(type(v) not in (int,float) or not math.isfinite(v) for v in value.values()):
        raise ValueError('Non-finite / malformed observed vector')
    return value


def grip_world(muzzle,forward,local):
    vector(muzzle);vector(forward)
    length=math.sqrt(sum(forward[k]**2 for k in ('x','y','z')))
    if not math.isfinite(length) or abs(length-1)>.01:raise ValueError('Invalid reference weapon direction')
    yaw=math.atan2(forward['x'],forward['z']);pitch=-math.asin(max(-1,min(1,forward['y']/length)))
    x,y,z=local;yp=math.cos(pitch)*y-math.sin(pitch)*z;zp=math.sin(pitch)*y+math.cos(pitch)*z
    return dict(zip(('x','y','z'),(muzzle['x']+math.cos(yaw)*x+math.sin(yaw)*zp,muzzle['y']+yp,muzzle['z']-math.sin(yaw)*x+math.cos(yaw)*zp)))


def validate_capture(capture,player,frame=None):
    row=capture.get('firstPerson')
    if not isinstance(row,dict) or row.get('id')!=player or any(row.get(k) is not True for k in ('firstPerson','visible','arms','simulated')):
        raise ValueError('Missing / foreign / hidden / tracked first-person view')
    if type(row.get('tick')) is not int or row['tick']<0 or capture.get('phase') not in ('Running','Paused'):raise ValueError('Invalid first-person clock / phase')
    for key in ('head','feet','leftElbow','leftWrist','rightElbow','rightWrist'):vector(row.get(key))
    if capture.get('players')!=[]:raise ValueError('Solo first-person capture must not relabel its owner as a remote body')
    if frame is not None:
        body=next(p for p in frame['players'] if p['id']==player)
        if capture['phase']!=frame['phase'] or row['tick']!=frame['tick'] or not body['connected'] or body['rig']['kind']!='Simulated':
            raise ValueError('Settled capture differs from the original accepted phase / tick / rig')
        right=grip_world(body['muzzle'],body['forward'],(.06,-.15,-.595))
        error=max(abs(row['head'][k]-body['head'][k]) for k in ('x','y','z'))
        error=max(error,max(abs(row['rightWrist'][k]-right[k]) for k in ('x','y','z')))
        if error>1e-6:raise ValueError('Native settled head / glove wrist differs from accepted source')
        return error
    return None


class FirstPersonVenue(venue_module.Venue):
    def __init__(self,args):
        super().__init__(args,artifact_family='desktop-first-person');self.probe=self.runtime_directory/'first-person-probe';self.probe_report=None
    def report(self):
        path=self.probe/('report.json' if (self.probe/'report.json').exists() else 'status.json')
        try:value=json.loads(path.read_text(encoding='utf-8-sig'))
        except (FileNotFoundError,json.JSONDecodeError):return None
        if value.get('error'):raise RuntimeError(value['error'])
        return value
    def finish_probe(self):
        if self.probe_report is not None:return self.probe_report
        if not self.probe.exists():return None
        (self.probe/'finish.request').write_text('Explicit first-person diagnostic stop',encoding='utf-8')
        value=self.wait(lambda:(r if (r:=self.report()) and r.get('complete') else None),15,'first-person diagnostic finish')
        if value['audioSamples']!=0 or value['callbackCount']!=0 or value['stopReason']!='Explicit diagnostic stop':raise RuntimeError('Unexpected first-person diagnostic scope / stop')
        self.probe_report=value;return value
    def cleanup(self):
        errors=[]
        try:
            try:self.finish_probe()
            except Exception as error:errors.append(type(error).__name__)
        finally:cleaned=super().cleanup()
        self.save('first-person-probe-cleanup.json',{'errors':errors,'finished':self.probe_report is not None})
        return cleaned and not errors


def replay(v,entry,references):
    request=urllib.request.Request(v.base+f'/api/sessions/{entry["id"]}/world/watch?mode=replay&fromMs=0&rate=4',headers={'Authorization':'Bearer '+v.tokens['Master']})
    number=0;matched=set();faults=[];first=min(references);last=None
    deadline=time.monotonic()+entry['sealed']['world']['durationMilliseconds']/4000+30
    with urllib.request.urlopen(request,timeout=10) as response:
        for value in capacity.sse_frames(response):
            if time.monotonic()>deadline:raise RuntimeError('First-person replay observation exceeded its bound')
            packet=value['packet'];frame=packet['frame']
            if packet['sequence']!=number+1:raise RuntimeError('First-person replay is not contiguous')
            number=packet['sequence'];last=value
            if number>=first and frame['phase']=='Running':
                expected=entry['players'][0]['id'];players=frame['players']
                fault=None if len(players)==1 and players[0]['id']==expected and players[0]['connected'] and players[0]['health']==100 and players[0]['rig']['kind']=='Simulated' else 'Original solo participant was missing / stale / invalid'
                if fault or packet['suspended']:faults.append({'sequence':number,'fault':fault,'suspended':packet['suspended']})
            if number in references:
                if value!=references[number]:raise RuntimeError('First-person accepted checkpoint differs from full replay')
                matched.add(number)
    if number!=entry['sealed']['world']['acceptedSequence'] or matched!=set(references) or last['packet']['frame']['phase']!='Ended':raise RuntimeError('Incomplete first-person replay / seal')
    return {'complete':not faults,'frames':number,'matchedReferences':len(matched),'worldContinuityFaults':faults}


def run(v):
    v.start();mission=v.request('/api/missions',{'name':'First-person sleeves - Simulation','briefing':'Actual desktop look, one Space and R; no headset or input injection.',
        'durationSeconds':600,'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},'enemies':{'count':0,'behavior':'Hold','autoAttack':False},'props':[]},expected=201)
    entry=v.create(mission,[3],'first-person',role='Room3');own=entry['players'][0];references={}
    v.wait(lambda:v.request(f'/api/sessions/{entry["id"]}/world',optional=True),90,'first-person source recording')
    v.launch('first-person-client',v.client_config(entry,v.ticket(entry,own)),True,extra_args=['--vr-player-body-probe',str(v.probe.resolve())])
    def frame():return v.frame(entry,measure=True)
    def player(value):return next(p for p in value['packet']['frame']['players'] if p['id']==own['id'])
    def checkpoint():
        value=frame();references[value['packet']['sequence']]=value;v.save('first-person-references.json',list(references.values()));return value['packet']['frame']
    def capture(label):
        path=v.probe/('capture-'+uuid.uuid4().hex+'.tmp');path.write_text(label,encoding='utf-8');os.replace(path,v.probe/'capture.request')
        result=v.wait(lambda:(row if (r:=v.report()) and (row:=next((c for c in r['captures'] if c['file']==label+'.png'),None)) else None),15,'actual first-person framebuffer '+label)
        validate_capture(result,own['id']);return result
    v.wait(lambda:player(frame())['connected'],30,'first-person accepted simulated rig');v.command(entry,'Begin')
    v.wait(lambda:frame()['packet']['frame']['phase']=='Running',15,'first-person Running');checkpoint();time.sleep(.3);idle=capture('idle')
    v.stage('first-person-look',note='Actual Right and Down in this owned game window; source must accept a nonzero yaw and pitch. No game input from this helper.',visiblePid=v.processes['first-person-client'].pid)
    v.wait(lambda:(p if (p:=player(frame()))['forward']['x']>.02 and p['forward']['y']<-.02 else None),90,'actual desktop look')
    checkpoint();look=capture('look')
    v.stage('first-person-shot',note='Actual Space once; helper waits for accepted ammunition.')
    v.wait(lambda:player(frame())['magazine']==29,90,'one real accepted shot');checkpoint();shot=capture('after-shot')
    v.stage('first-person-reload',note='Actual R once; the helper pauses the accepted reload for fixed-clock captures.')
    def accepted_reload():
        value=frame();p=player(value)
        return p if p['reloading'] and 8<=p['reloadUntilTick']-value['packet']['frame']['tick']<=22 else None
    v.wait(accepted_reload,90,'actual reload')
    v.command(entry,'Pause');v.wait(lambda:frame()['packet']['frame']['phase']=='Paused',15,'first-person reload Pause');paused=checkpoint();time.sleep(.6)
    reload=capture('paused-reload');time.sleep(.25);again=capture('paused-reload-again')
    errors=[validate_capture(c,own['id'],paused) for c in (reload,again)]
    a,b=reload['firstPerson'],again['firstPerson'];vectors=['head','feet','leftElbow','leftWrist','rightElbow','rightWrist']
    delta=max(abs(a[k][axis]-b[k][axis]) for k in vectors for axis in ('x','y','z'))
    if delta>1e-6 or any(a[k]!=b[k] for k in a if k not in vectors):raise RuntimeError('First-person paused sleeve transforms / saved clock changed')
    if math.dist(tuple(look['firstPerson']['leftWrist'][k] for k in ('x','y','z')),tuple(a['leftWrist'][k] for k in ('x','y','z')))<.01:raise RuntimeError('Accepted reload did not move the actual first-person left wrist')
    v.command(entry,'Resume');v.wait(lambda:(p if not (p:=player(frame()))['reloading'] and p['magazine']==30 and p['reserve']==89 else None),15,'accepted reload completion')
    checkpoint();after=capture('after-reload')
    v.stage('first-person-review',note='Inspect all six own framebuffer PNGs before creating review.done. Diagnostic completion is separate from game End.',probeDirectory=str(v.probe),captures=[c['file'] for c in (idle,look,shot,reload,again,after)])
    v.wait(lambda:(v.directory/'review.done').exists(),120,'actual first-person image review');probe=v.finish_probe();sealed=v.seal(entry)
    delivery=v.wait_for_player_results(entry)
    if delivery['allAcknowledged'] is not True or delivery['timedOut']!=[]:raise RuntimeError('Original player result was not acknowledged')
    result=debrief.final_result(v,'first-person-client');debrief.validate_result(result,entry,own,sealed)
    stream=v.state(entry)['combatStream'];server=debrief.log_text(v,'first-person-server')
    connected=re.findall(r'VR_CLIENT_CONNECTED id=(\d+)',debrief.log_text(v,'first-person-client'));acked=re.findall(r'VR_SERVER_DEBRIEF_ACK id=(\d+)',server)
    if not stream['sealed'] or result['finalStreamSequence']!=stream['acceptedSequence'] or len(connected)!=1 or acked!=connected or 'VR_SERVER_DEBRIEF_TIMEOUT ' in server:raise RuntimeError('Final combat seal / original connection acknowledgement differs')
    statistics=sealed['statistics']['players'][0]
    if statistics['ammoUsed']!=1 or statistics['health']!=100 or any(statistics[k]!=0 for k in ('shotsHit','kills','damageTaken','hitsReceived','accuracyPercent')):raise RuntimeError('Sleeve presentation changed original combat statistics')
    csv=practice.save_report(v,entry,sealed['statistics']);v.stop_round(entry);playback=replay(v,entry,references)
    if not playback['complete']:raise RuntimeError('First-person world participation failed during replay')
    v.save('first-person-result.json',{'complete':False,'source':'Actual Windows input / own framebuffer / Simulation','headsets':0,'hosts':1,'poseOrWeaponInjected':False,
        'probe':probe,'pausedMaximumTransformDelta':delta,'pausedMaximumSourceEndpointError':max(errors),'pausedFrame':paused,'result':result,'csv':csv,'replay':playback})
    v.evidence.extend(['actual local sleeves / hidden local torso and helmet; six reviewed GPU captures','actual look and one Space / R, original accepted pose and ammunition','paused native wrists match accepted source and remain within one micrometre','full contiguous replay / CSV / exact dual seals / own final result and server ACK'])
    v.summary()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--runtime-root',type=Path,required=True);parser.add_argument('--player-exe',type=Path,default=ROOT/'artifacts/desktop/VrCommand.exe');parser.add_argument('--api-dll',type=Path,required=True)
    args=parser.parse_args();args.duration=600;args.visible_room=3;args.job_workers=2;args.check=False;venue_module.verify_player(args);v=FirstPersonVenue(args);sources=observer_sources()
    v.save('observer-sources.json',{'files':sources,'scope':'These five helper sources only; not a complete runtime / OS / computer-use dependency graph'})
    try:v.stage('starting',source='Simulation',headsets=0);run(v)
    except BaseException as error:v.stage('failed',errorType=type(error).__name__);raise
    finally:
        failed=sys.exc_info()[0] is not None;cleaned=v.cleanup()
        if not cleaned:
            v.stage('failed',errorType='CleanupError')
            if not failed:raise RuntimeError('First-person diagnostic / native cleanup failed')
        elif not failed:
            if observer_sources()!=sources:
                v.stage('failed',errorType='ObserverSourceChanged');raise RuntimeError('First-person helper source changed during this run')
            result=venue_module.read_json(v.directory/'first-person-result.json');result['complete']=True;v.save('first-person-result.json',result);v.stage('passed',checks=len(v.evidence))

if __name__=='__main__':main()
