"""Bounded Windows Development batch-client generated movement/fire/reload over the original native RPC path.

Automated Simulation input, not physical operators, XR tracking, LAN or capacity acceptance.
"""
import argparse,concurrent.futures,importlib.util,json,math,os,re,sys,time,urllib.request,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
capacity=module('exercise_capacity','check-desktop-capacity.py');vm=capacity.venue_module;debrief=module('exercise_debrief','check-desktop-debrief.py')
active=module('exercise_active','check-desktop-active.py')

def validate_control_receipts(responses,session_id,command_ids,previous_sequence):
    if len(responses)!=2 or len(set(command_ids))!=2:raise ValueError('Expected two distinct operator intents')
    previous=previous_sequence
    for response,identity in zip(responses,command_ids):
        sequence=response.get('appliedAtSequence')
        if response.get('commandId')!=identity or response.get('duplicate') is not False or response.get('session',{}).get('id')!=session_id or type(sequence) is not int or sequence<=previous:
            raise ValueError('Operator receipt differs from its original intent/session/order')
        previous=sequence
    return previous

def match_control_reference(value,references,matched):
    sequence=value['packet']['sequence']
    if sequence in references:
        expected=references[sequence]
        if value['packet']!=expected['packet'] or value['statistics']!=expected['statistics']:raise ValueError('Operator source checkpoint differs from its original replay')
        matched.add(sequence)

def operator_phase(v,entry,environment,behavior):
    before=v.frame(entry,measure=True);commands=[str(uuid.uuid4()),str(uuid.uuid4())]
    witness={'transport':'ManagementApi','physicalOperators':0,'environment':environment,'behavior':behavior,'commandIds':commands,'before':before,'receipts':[],'applied':None}
    entry.setdefault('operatorControls',[]).append(witness)
    def save():v.save(entry['name']+'-operator-controls.json',entry['operatorControls'])
    save()
    for identity,action,payload in [(commands[0],'SetEnvironment',{'environment':environment}),(commands[1],'SetEnemies',{'enemies':{'count':len(entry['roomIds']),'behavior':behavior,'autoAttack':False}})]:
        expected=v.state(entry)['sequence']
        response=v.command(entry,action,commandId=identity,expectedSequence=expected,**payload)
        witness['receipts'].append(response);save()
    fence=validate_control_receipts(witness['receipts'],entry['id'],commands,before['packet']['observedSequence']);witness['acceptedSequence']=fence;save()
    def observed():
        value=v.frame(entry,measure=True)
        try:
            active.validate_operator_packet(value,environment,behavior,fence,before['packet']['frame']['tick']+20)
            frame=validate_frame(value,entry['players'],begin_sequence=entry['beginSequence'])
            distances=active.validate_enemy_motion(before['packet']['frame'],frame)
            if any(d<=.01 for d in distances.values()):return None
            if not all(p['walking'] for p in frame['players']):return None
        except ValueError:return None
        return value,distances
    value,distances=v.wait(observed,15,'generated clients plus operator '+behavior)
    witness['applied']=value;witness['enemyMovementMeters']=distances;save()
    references=entry.setdefault('operatorReferences',{})
    for point in [before,value]:references[point['packet']['sequence']]=point
    validate_roster(v.state(entry),entry['players'])
    return witness

def validate_roster(session,players):
    expected={p['id']:p for p in players};source={p['id']:p for p in session['players']}
    if set(source)!=set(expected) or any(source[k]['admissionId']!=p['admissionId'] or source[k]['roomId']!=p['roomId'] or source[k]['seat']!=p['seat'] for k,p in expected.items()):raise ValueError('Original API roster changed an admission, seat or room')

def validate_frame(value,players,pause=None,begin_sequence=1):
    packet=value['packet'];frame=packet['frame'];expected={p['id']:p for p in players};actual=frame['players'];observed=packet['observedSequence']
    if packet.get('suspended') or frame['phase'] not in ('Running','Paused') or len(actual)!=len(expected) or {p['id'] for p in actual}!=set(expected):raise ValueError('Missing, suspended or unexpected phase/body')
    if type(observed) is not int or observed<begin_sequence:raise ValueError('Source has not applied this original Begin')
    if frame['phase']=='Paused' and (pause is None or observed<pause['accepted'] or pause.get('resumed') is not None and observed>=pause['resumed']):raise ValueError('Unexpected pause cannot be ignored')
    for p in actual:
        owner=expected[p['id']];head=p['head'];x=(owner['roomId']-3)*14+(owner['seat']-2)*1.5
        if not p['connected'] or p['health']!=100 or p['roomId']!=owner['roomId'] or p['rig']['kind']!='Simulated':raise ValueError('Original native body became inactive or changed identity')
        if not all(type(head[a]) in (int,float) and math.isfinite(head[a]) for a in ('x','y','z')) or abs(head['x']-x)>.1 or not -3.4<=head['z']<=-1.6 or abs(head['y']-1.65)>.02:raise ValueError('Generated motion left its own bounded standing lane')
    return frame

def validate_report(report,owner,expected_fires=2,expected_reloads=1,minimum_ticks=0,endurance=False):
    if report.get('version')!=1 or report.get('mode')!='AutomatedSimulation' or report.get('role')!='Client' or report.get('physicalInput') is not False or type(report.get('headsets')) is not int or report['headsets']!=0:raise ValueError('Not an explicit synthetic client input report')
    if report.get('complete') is not True or report.get('truncated') is not False or report.get('reason')!='Requested' or report.get('fault') not in (None,''):raise ValueError('Exercise did not explicitly finish cleanly')
    if report['pid']!=owner['pid'] or report['playerId']!=owner['playerId'] or report['room']!=owner['roomId'] or report['connection']!=owner['nativeConnectionId']:raise ValueError('Exercise owner differs from original native process/connection')
    if report['fireSubmissions']!=expected_fires or report['reloadSubmissions']!=expected_reloads or report['movementFrames']<1 or report['activeFrames']<report['movementFrames'] or not 0<=report['firstTick']<report['lastTick'] or report['lastTick']-report['firstTick']<minimum_ticks:raise ValueError('Not all bounded production-path input attempts were made')
    if endurance and (report.get('profile')!='Endurance' or report.get('motion')!='LocalPositionFeedback' or report.get('maximumActiveTicks')!=19000 or report.get('maximumCollectionSeconds')!=1200):raise ValueError('Not the explicit bounded endurance feedback profile')

def validate_endurance_cycles(cycles,expected):
    if set(cycles)!=set(range(expected)):raise ValueError('Endurance replay is missing a complete scheduled cycle')
    for index,sample in cycles.items():
        if not all(type(sample[k]) in (int,float) and math.isfinite(sample[k]) for k in ('min','max')) or sample['max']-sample['min']<.1 or sample['reload'] is not True or sample['ammoMax']!=2*(index+1) or sample['frames']<1 or sample['walkingFrames']<1:
            raise ValueError('Endurance cycle lacks accepted movement, reload or exact cumulative shots')

class ExerciseVenue(vm.Venue):
    def __init__(self,args):super().__init__(args,artifact_family='desktop-exercise');self.exercise={};self.receipts=[];self.pauses={}
    def launch(self,name,config,visible=False,*,extra_args=()):
        if config['role']=='Client':
            directory=self.runtime_directory/(name+'-exercise');self.exercise[name]=directory
            extra_args=(*extra_args,'--vr-desktop-endurance' if self.args.endurance else '--vr-desktop-exercise',str(directory))
        super().launch(name,config,visible,extra_args=extra_args)

def check_frame_review(v, entry, frames):
    route = f'/api/sessions/{entry["id"]}/world'
    first = next((index for index, frame in enumerate(frames[:-1])
                  if any(event['kind'] == 'ShotFired' for event in frame['packet']['events'])), None)
    if first is None:
        raise RuntimeError('No accepted native shot frame to inspect')
    sequence = first + 1
    exact = v.request(f'{route}/frames/{sequence}')
    request = urllib.request.Request(v.base + f'{route}/watch?mode=replay&fromFrame={sequence}&rate=4',
                                     headers={'Authorization': 'Bearer ' + v.tokens['Master']})
    with urllib.request.urlopen(request, timeout=10) as response:
        stream = capacity.sse_frames(response)
        resumed = [next(stream), next(stream)]
    if exact != frames[first] or resumed != frames[first:first + 2]:
        raise RuntimeError('Native shot frame or exact resume differed from the accepted full replay')
    v.save(entry['name'] + '-frame-review.json', {'complete': True, 'sequence': sequence,
           'resumedSequences': [frame['packet']['sequence'] for frame in resumed], 'frame': exact})


def replay(v,entry,pause):
    request=urllib.request.Request(v.base+f'/api/sessions/{entry["id"]}/world/watch?mode=replay&fromMs=0&rate=4',headers={'Authorization':'Bearer '+v.tokens['Master']})
    rows=[];faults=[];previous=0;last=None;ranges={p['id']:{'min':None,'max':None,'reload':False,'cycles':{}} for p in entry['players']};last_running=None;running=0
    references=entry.get('operatorReferences',{});matched=set()
    deadline=time.monotonic()+entry['sealed']['world']['durationMilliseconds']/4000+30
    with urllib.request.urlopen(request,timeout=10) as response:
        for value in capacity.sse_frames(response):
            if time.monotonic()>deadline:raise RuntimeError('Bounded full replay expired')
            number=value['packet']['sequence']
            if number!=previous+1:raise RuntimeError('Replay skipped or repeated an accepted frame')
            previous=number;last=value;rows.append(value);match_control_reference(value,references,matched)
            if value['packet']['frame']['phase'] not in ('Running','Paused'):continue
            try:frame=validate_frame(value,entry['players'],pause,entry.get('beginSequence',1))
            except ValueError as error:faults.append({'sequence':number,'reason':str(error)});continue
            if frame['phase']=='Running':
                elapsed=value['packet']['elapsedMilliseconds']
                if last_running is not None and elapsed-last_running>=1500:faults.append({'sequence':number,'reason':'Running source capture gap >=1500ms'})
                last_running=elapsed;running+=1
                for p in frame['players']:
                    span=ranges[p['id']];z=p['head']['z'];span['min']=z if span['min'] is None else min(span['min'],z);span['max']=z if span['max'] is None else max(span['max'],z);span['reload']|=p['reloading']
                    if entry.get('endurance'):
                        report=entry['inputReports'][p['id']];relative=frame['tick']-report['firstTick'];cycle=relative//400
                        if 0<=relative and cycle<entry['expectedCycles'] and frame['tick']<=report['lastTick']:
                            sample=span['cycles'].setdefault(cycle,{'min':z,'max':z,'reload':False,'ammoMax':0,'frames':0,'walkingFrames':0})
                            sample['min']=min(sample['min'],z);sample['max']=max(sample['max'],z);sample['reload']|=p['reloading'];sample['frames']+=1;sample['walkingFrames']+=int(p['walking'])
                            sample['ammoMax']=max(sample['ammoMax'],next(s['ammoUsed'] for s in value['statistics'] if s['playerId']==p['id']))
            else:last_running=None
    if last is None or previous!=entry['sealed']['world']['acceptedSequence'] or last['packet']['frame']['phase']!='Ended':raise RuntimeError('Replay did not reach exact final world seal')
    if matched!=set(references):raise RuntimeError('Replay did not retain every original operator checkpoint')
    for identity,span in ranges.items():
        if not all(span[k] is not None and math.isfinite(span[k]) for k in ['min','max']) or span['max']-span['min']<.1 or not span['reload']:faults.append({'playerId':identity,'reason':'No accepted movement/reload witness'})
        if entry.get('endurance'):
            try:validate_endurance_cycles(span['cycles'],entry['expectedCycles'])
            except ValueError as error:faults.append({'playerId':identity,'reason':str(error)})
    result={'complete':not faults,'frames':previous,'runningFrames':running,'faults':faults,'ranges':ranges,'operatorReferences':len(matched),'scope':'Full accepted native replay, generated input only; original continuity policies retained'}
    v.save(entry['name']+'-full-replay.json',rows);v.save(entry['name']+'-replay-checks.json',result)
    if v.args.check_frame_review and result['complete']:
        check_frame_review(v, entry, rows)
    return result

def run(v):
    v.start();modes=[]
    def check(value,label):
        if not value:raise ValueError(label)
        v.evidence.append(label);v.stage('checking',check=label)
    for mode in (['linked','independent'] if v.args.mode=='both' else [v.args.mode]):
        entries=[];native=[];pause=None
        for rooms in ([list(range(1,6))] if mode=='linked' else [[r] for r in range(1,6)]):
            definition={'name':'Generated native input '+mode,'briefing':'Automated Simulation exercise; no physical operators or headsets','durationSeconds':1800 if v.args.endurance else 600,'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},'enemies':{'count':len(rooms) if v.args.operator_controls else 0,'behavior':'Hold','autoAttack':False},'props':[]}
            mission=v.request('/api/missions',definition,expected=201);entry=v.create(mission,rooms,mode+'-'+str(rooms[0]))
            for room in rooms:
                for seat in range(1,v.args.players_per_room):
                    identity=str(uuid.uuid4());state=v.request(f'/api/sessions/{entry["id"]}/players',{'playerId':identity,'name':'Generated '+str(room)+'-'+str(seat),'roomId':room,'headset':'Quest3'},role='Room'+str(room));entry['players'].append(next(p for p in state['players'] if p['id']==identity))
            entries.append(entry)
        for e in entries:v.wait(lambda e=e:v.request(f'/api/sessions/{e["id"]}/world',optional=True),90,'new exercise world')
        for e,p in [(e,p) for e in entries for p in sorted(e['players'],key=lambda p:(p['seat'],p['roomId']))]:
            capacity.require_memory(capacity.memory_status());name=e['name']+'-client-'+p['admissionId'];v.launch(name,v.client_config(e,v.ticket(e,p)))
            native.append({'name':name,'sessionId':e['id'],'playerId':p['id'],'admissionId':p['admissionId'],'roomId':p['roomId'],'seat':p['seat'],'pid':v.processes[name].pid})
        for e in entries:capacity.validate_frame(v.wait(lambda e=e:v.connected(e),100,'all exercise admissions'),e['players'])
        for row in native:
            ids=set(re.findall(r'VR_CLIENT_CONNECTED id=(\d+)',debrief.log_text(v,row['name'])))
            if len(ids)!=1:raise RuntimeError('Client connection not uniquely witnessed')
            row['nativeConnectionId']=int(ids.pop())
        for e in entries:
            owners=[r for r in native if r['sessionId']==e['id']]
            if len({r['nativeConnectionId'] for r in owners})!=len(owners):raise RuntimeError('Native connection IDs are not unique within this server')
        if len({r['pid'] for r in native})!=len(native):raise RuntimeError('Native players did not retain distinct original processes')
        v.save(mode+'-native-clients.json',native);check(len(native)==5*v.args.players_per_room,mode+': original native clients admitted before generated input')
        for e in entries:
            validate_roster(v.state(e),e['players']);receipt=v.command(e,'Begin')
            if receipt['duplicate'] is not False or receipt['session']['id']!=e['id']:raise RuntimeError('Begin receipt belongs to another intent/session')
            e['beginSequence']=receipt['appliedAtSequence'];v.receipts.append(receipt)
        v.save(mode+'-begin-receipts.json',v.receipts);v.stage('running',mode=mode,automatedClients=len(native),seconds=v.args.seconds)
        started=time.monotonic();deadline=started+v.args.seconds;pause_at=started+2;resume_at=None;live=[];next_progress=started+30
        while time.monotonic()<deadline:
            if mode=='independent' and pause is None and time.monotonic()>=pause_at:
                others={e['id']:v.frame(e)['packet']['frame']['tick'] for e in entries[1:]}
                receipt=v.command(entries[0],'Pause');pause={'accepted':receipt['appliedAtSequence'],'resumed':None,'receipt':receipt,'otherStartTicks':others};v.pauses[entries[0]['id']]=pause;v.save(mode+'-pause.json',pause)
                def paused_source():
                    value=v.frame(entries[0],measure=True)
                    return value if value['packet']['frame']['phase']=='Paused' and value['packet']['observedSequence']>=pause['accepted'] else None
                witness=v.wait(paused_source,15,'original room Pause applied');validate_frame(witness,entries[0]['players'],pause)
                pause['pausedTick']=witness['packet']['frame']['tick'];pause['pausedSourceSequence']=witness['packet']['sequence'];resume_at=time.monotonic()+2;v.save(mode+'-pause.json',pause)
            if resume_at is not None and time.monotonic()>=resume_at:
                still=v.frame(entries[0],measure=True);validate_frame(still,entries[0]['players'],pause)
                if still['packet']['frame']['phase']!='Paused' or still['packet']['frame']['tick']!=pause['pausedTick']:raise RuntimeError('Paused room tick advanced unexpectedly')
                pause['otherEndTicks']={e['id']:v.frame(e)['packet']['frame']['tick'] for e in entries[1:]}
                if any(pause['otherEndTicks'][sid]<=tick for sid,tick in pause['otherStartTicks'].items()):raise RuntimeError('Other rooms did not continue while one room paused')
                receipt=v.command(entries[0],'Resume');pause['resumed']=receipt['appliedAtSequence'];pause['resumeReceipt']=receipt;resume_at=None;v.save(mode+'-pause.json',pause)
            for e in entries:
                value=v.frame(e,measure=True)
                if value['packet']['frame']['phase']=='Preparing':continue
                try:validate_frame(value,e['players'],pause if e is entries[0] else None,e['beginSequence'])
                except ValueError:
                    v.save('exercise-live-failure.json',{'round':e['id'],'value':value});raise
                live.append({'sessionId':e['id'],'sequence':value['packet']['sequence'],'tick':value['packet']['frame']['tick'],'phase':value['packet']['frame']['phase']})
            if time.monotonic()>=next_progress:
                v.stage('running',mode=mode,elapsedSeconds=round(time.monotonic()-started,2),requestedSeconds=v.args.seconds,lastSources=live[-len(entries):]);next_progress=time.monotonic()+30
            time.sleep(.05)
        v.save(mode+'-live.json',live)
        if v.args.operator_controls:
            for e in entries:
                v.wait(lambda e=e:all(p['ammoUsed']==2 for p in v.request(f'/api/sessions/{e["id"]}/statistics')['players']),10,'all original generated shots accepted before operator controls')
                for weather,night,behavior in [('Storm',True,'Patrol'),('Fog',False,'Advance')]:
                    operator_phase(v,e,{'mode':'VR','weather':weather,'timeOfDay':'Night' if night else 'Day','lightning':weather=='Storm'},behavior)
                    check(True,e['name']+': '+behavior+' and '+weather+' applied while every original client walked; original enemies retained and moved')
        for row in native:(v.exercise[row['name']]/'finish.request').write_text('',encoding='utf-8')
        v.wait(lambda:all((v.exercise[r['name']]/'report.json').exists() for r in native),15,'explicit exercise finish')
        reports=[]
        cycles=v.args.seconds//20 if v.args.endurance else 1;fires=cycles*2
        for row in native:
            report=vm.read_json(v.exercise[row['name']]/'report.json');validate_report(report,row,fires,cycles,max(0,v.args.seconds*20-100) if v.args.endurance else 0,v.args.endurance);reports.append(report)
        for e in entries:
            e['endurance']=v.args.endurance;e['expectedCycles']=cycles;e['inputReports']={r['playerId']:r for r in reports if r['room'] in e['roomIds']}
        v.save(mode+'-exercise-reports.json',reports);check(True,mode+': every original client submitted its exact generated fire/reload schedule and explicitly finished')
        for e in entries:
            validate_roster(v.state(e),e['players']);sealed=v.seal(e);players=sealed['statistics']['players']
            check(all(p['ammoUsed']==fires and p['shotsHit']==0 and p['kills']==0 and p['health']==100 and p['damageTaken']==0 and p['hitsReceived']==0 for p in players),e['name']+': accepted statistics reflect the exact generated shot count for every player')
            csv=capacity.practice.save_report(v,e,sealed['statistics'],filename=e['name']+'-report.csv');delivery=v.wait_for_player_results(e);owners=[r for r in native if r['sessionId']==e['id']];results=[]
            if delivery['allAcknowledged'] is not True or delivery['timedOut'] or set(delivery['phases'])!={r['name'] for r in owners}:raise RuntimeError('Original player results not all acknowledged')
            for row in owners:
                result=debrief.final_result(v,row['name']);player=next(p for p in e['players'] if p['id']==row['playerId']);debrief.validate_result(result,e,player,sealed)
                if result['finalStreamSequence']!=v.state(e)['combatStream']['acceptedSequence']:raise RuntimeError('Wrong final combat boundary')
                results.append(result)
            acknowledgments=[int(x) for x in re.findall(r'VR_SERVER_DEBRIEF_ACK id=(\d+)',debrief.log_text(v,e['name']+'-server'))]
            if len(acknowledgments)!=len(owners) or set(acknowledgments)!={r['nativeConnectionId'] for r in owners} or 'VR_SERVER_DEBRIEF_TIMEOUT ' in debrief.log_text(v,e['name']+'-server'):raise RuntimeError('Server ACK differs from original native connections')
            if any(debrief.log_text(v,r['name']).count('VR_CLIENT_CONNECTED id=')!=1 for r in owners):raise RuntimeError('A client changed connection before its final result')
            v.save(e['name']+'-results.json',{'delivery':delivery,'results':results,'serverAcknowledgments':acknowledgments,'csv':csv})
            v.stop_round(e)
            if not v.args.endurance:
                playback=replay(v,e,pause if e is entries[0] else None);check(playback['complete'],e['name']+': all replay frames retain original bodies, movement/reload, seals and results')
                if v.args.check_frame_review:
                    check(True, e['name'] + ': exact shot frame and first two resumed frames match the native archive')
        if v.args.endurance:
            # All native sources are stopped first. Each independent reader still
            # consumes every frame at the original rate4 and its original deadline.
            with concurrent.futures.ThreadPoolExecutor(max_workers=v.args.replay_workers) as pool:
                pending={pool.submit(replay,v,e,pause if e is entries[0] else None):e for e in entries}
                for future in concurrent.futures.as_completed(pending):
                    e=pending[future];playback=future.result();check(playback['complete'],e['name']+': complete endurance replay retains every original body and every movement/reload/two-shot cycle')
        findings=capacity.native_log_findings(v.directory);check(not findings,mode+': no native send queue errors')
        modes.append({'mode':mode,'clients':len(native),'automatedInputs':True,'operatorControls':v.args.operator_controls,'endurance':v.args.endurance,'requestedSeconds':v.args.seconds,'maximumReplayWorkers':v.args.replay_workers,'replayRate':4,'physicalOperators':0,'networkCapacityAccepted':False})
    v.summary();v.save('exercise-result.json',{'complete':False,'modes':modes,'headsets':0,'hosts':1,'renderedClients':0,'posesWrittenDirectly':False,'newTestRpc':False,'automatedInput':True,'physicalOperators':0,'networkCapacityAccepted':False,'scope':'Actual Windows native clients using generated desktop movement/weapon intents through original RPCs; not humans, XR, LAN or capacity acceptance'})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime-root',type=Path,required=True);p.add_argument('--mode',choices=('linked','independent','both'),default='both');p.add_argument('--players-per-room',type=int,choices=(1,5),default=5);p.add_argument('--seconds',type=int,default=16)
    p.add_argument('--endurance',action='store_true',help='Explicit separate bounded native profile: --seconds 60 (smoke) or 900 (long); never combined with operator-controls')
    p.add_argument('--replay-workers',type=int,choices=(1,5),default=1,help='Endurance only: independent closed-source replay readers; every stream retains rate4 and all original gates')
    p.add_argument('--operator-controls',action='store_true',help='After the base motion window, apply Storm Night Patrol then Fog Day Advance through normal management commands; no console UI or physical operator input')
    p.add_argument('--check-frame-review', action='store_true', help='Verify an exact native shot frame and resume during the short exercise')
    p.add_argument('--api-dll',type=Path,default=Path(os.environ.get('VR_COMMAND_API_DLL',ROOT/'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')));p.add_argument('--player-exe',type=Path,default=ROOT/'artifacts/desktop/VrCommand.exe');args=p.parse_args();args.duration=600;args.visible_room=0;args.job_workers=2;args.check=False
    if args.endurance and (args.seconds not in (60,900) or args.operator_controls) or not args.endurance and args.seconds not in range(12,41):p.error('Short seconds must be 12..40; endurance requires 60 or 900 and no operator-controls')
    if args.replay_workers!=1 and not args.endurance:p.error('Parallel replay readers require the explicit endurance profile')
    if args.check_frame_review and args.endurance:p.error('Frame review uses the short exercise')
    vm.verify_player(args);v=ExerciseVenue(args)
    try:run(v)
    except BaseException as error:
        v.stage('failed',errorType=type(error).__name__);forensics=[]
        v.save('partial-checks.json',{'complete':False,'checks':v.evidence,'scope':'Only completed assertions before the original failure; never whole-run acceptance'})
        for directory in v.exercise.values():
            if directory.is_dir() and not (directory/'report.json').exists():(directory/'finish.request').write_text('',encoding='utf-8')
        for entry in v.rounds:
            if (v.directory/(entry['name']+'-full-replay.json')).exists():continue
            try:
                if v.request(f'/api/sessions/{entry["id"]}/world',optional=True):
                    v.seal(entry);result=replay(v,entry,v.pauses.get(entry['id']));forensics.append({'sessionId':entry['id'],'replayRead':True,'replayContinuityPassed':result['complete'],'acceptancePassed':False})
            except Exception as issue:forensics.append({'sessionId':entry['id'],'replayRead':False,'errorType':type(issue).__name__})
        v.save('failure-forensics.json',{'originalErrorType':type(error).__name__,'rounds':forensics,'acceptancePassed':False});raise
    finally:
        failed=sys.exc_info()[0] is not None;clean=v.cleanup()
        if not clean and not failed:raise RuntimeError('Exercise cleanup incomplete')
        if clean and not failed:
            result=vm.read_json(v.directory/'exercise-result.json');result['complete']=True;v.save('exercise-result.json',result);v.stage('passed',checks=len(v.evidence))
if __name__=='__main__':main()
