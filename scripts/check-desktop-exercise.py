"""Short Windows Development batch-client generated movement/fire/reload over the original native RPC path.

Automated Simulation input, not physical operators, XR tracking, LAN or capacity acceptance.
"""
import argparse,importlib.util,json,math,os,re,sys,time,urllib.request,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
capacity=module('exercise_capacity','check-desktop-capacity.py');vm=capacity.venue_module;debrief=module('exercise_debrief','check-desktop-debrief.py')

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

def validate_report(report,owner):
    if report.get('version')!=1 or report.get('mode')!='AutomatedSimulation' or report.get('role')!='Client' or report.get('physicalInput') is not False or type(report.get('headsets')) is not int or report['headsets']!=0:raise ValueError('Not an explicit synthetic client input report')
    if report.get('complete') is not True or report.get('truncated') is not False or report.get('reason')!='Requested' or report.get('fault') not in (None,''):raise ValueError('Exercise did not explicitly finish cleanly')
    if report['pid']!=owner['pid'] or report['playerId']!=owner['playerId'] or report['room']!=owner['roomId'] or report['connection']!=owner['nativeConnectionId']:raise ValueError('Exercise owner differs from original native process/connection')
    if report['fireSubmissions']!=2 or report['reloadSubmissions']!=1 or report['movementFrames']<1 or report['activeFrames']<report['movementFrames'] or not 0<=report['firstTick']<report['lastTick']:raise ValueError('Not all bounded production-path input attempts were made')

class ExerciseVenue(vm.Venue):
    def __init__(self,args):super().__init__(args,artifact_family='desktop-exercise');self.exercise={};self.receipts=[];self.pauses={}
    def launch(self,name,config,visible=False,*,extra_args=()):
        if config['role']=='Client':
            directory=self.runtime_directory/(name+'-exercise');self.exercise[name]=directory
            extra_args=(*extra_args,'--vr-desktop-exercise',str(directory))
        super().launch(name,config,visible,extra_args=extra_args)

def replay(v,entry,pause):
    request=urllib.request.Request(v.base+f'/api/sessions/{entry["id"]}/world/watch?mode=replay&fromMs=0&rate=4',headers={'Authorization':'Bearer '+v.tokens['Master']})
    rows=[];faults=[];previous=0;last=None;ranges={p['id']:{'min':None,'max':None,'reload':False} for p in entry['players']};last_running=None;running=0
    deadline=time.monotonic()+entry['sealed']['world']['durationMilliseconds']/4000+30
    with urllib.request.urlopen(request,timeout=10) as response:
        for value in capacity.sse_frames(response):
            if time.monotonic()>deadline:raise RuntimeError('Bounded full replay expired')
            number=value['packet']['sequence']
            if number!=previous+1:raise RuntimeError('Replay skipped or repeated an accepted frame')
            previous=number;last=value;rows.append(value)
            if value['packet']['frame']['phase'] not in ('Running','Paused'):continue
            try:frame=validate_frame(value,entry['players'],pause,entry.get('beginSequence',1))
            except ValueError as error:faults.append({'sequence':number,'reason':str(error)});continue
            if frame['phase']=='Running':
                elapsed=value['packet']['elapsedMilliseconds']
                if last_running is not None and elapsed-last_running>=1500:faults.append({'sequence':number,'reason':'Running source capture gap >=1500ms'})
                last_running=elapsed;running+=1
                for p in frame['players']:
                    span=ranges[p['id']];z=p['head']['z'];span['min']=z if span['min'] is None else min(span['min'],z);span['max']=z if span['max'] is None else max(span['max'],z);span['reload']|=p['reloading']
            else:last_running=None
    if last is None or previous!=entry['sealed']['world']['acceptedSequence'] or last['packet']['frame']['phase']!='Ended':raise RuntimeError('Replay did not reach exact final world seal')
    for identity,span in ranges.items():
        if not all(span[k] is not None and math.isfinite(span[k]) for k in ['min','max']) or span['max']-span['min']<.1 or not span['reload']:faults.append({'playerId':identity,'reason':'No accepted movement/reload witness'})
    result={'complete':not faults,'frames':previous,'runningFrames':running,'faults':faults,'ranges':ranges,'scope':'Full accepted native replay, generated input only; original continuity policies retained'}
    v.save(entry['name']+'-full-replay.json',rows);v.save(entry['name']+'-replay-checks.json',result);return result

def run(v):
    v.start();modes=[]
    def check(value,label):
        if not value:raise ValueError(label)
        v.evidence.append(label);v.stage('checking',check=label)
    for mode in (['linked','independent'] if v.args.mode=='both' else [v.args.mode]):
        entries=[];native=[];pause=None
        for rooms in ([list(range(1,6))] if mode=='linked' else [[r] for r in range(1,6)]):
            definition={'name':'Generated native input '+mode,'briefing':'Automated Simulation exercise; no physical operators or headsets','durationSeconds':600,'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},'enemies':{'count':0,'behavior':'Hold','autoAttack':False},'props':[]}
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
        deadline=time.monotonic()+v.args.seconds;pause_at=time.monotonic()+2;resume_at=None;live=[]
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
            time.sleep(.05)
        v.save(mode+'-live.json',live)
        for row in native:(v.exercise[row['name']]/'finish.request').write_text('',encoding='utf-8')
        v.wait(lambda:all((v.exercise[r['name']]/'report.json').exists() for r in native),15,'explicit exercise finish')
        reports=[]
        for row in native:
            report=vm.read_json(v.exercise[row['name']]/'report.json');validate_report(report,row);reports.append(report)
        v.save(mode+'-exercise-reports.json',reports);check(True,mode+': every original client submitted generated movement/two fire/one reload and explicitly finished')
        for e in entries:
            validate_roster(v.state(e),e['players']);sealed=v.seal(e);players=sealed['statistics']['players']
            check(all(p['ammoUsed']==2 and p['shotsHit']==0 and p['kills']==0 and p['health']==100 and p['damageTaken']==0 and p['hitsReceived']==0 for p in players),e['name']+': accepted statistics reflect exactly two generated shots for every player')
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
            v.stop_round(e);playback=replay(v,e,pause if e is entries[0] else None);check(playback['complete'],e['name']+': all replay frames retain original bodies, movement/reload, seals and results')
        findings=capacity.native_log_findings(v.directory);check(not findings,mode+': no native send queue errors')
        modes.append({'mode':mode,'clients':len(native),'automatedInputs':True,'physicalOperators':0,'networkCapacityAccepted':False})
    v.summary();v.save('exercise-result.json',{'complete':False,'modes':modes,'headsets':0,'hosts':1,'renderedClients':0,'posesWrittenDirectly':False,'newTestRpc':False,'automatedInput':True,'physicalOperators':0,'networkCapacityAccepted':False,'scope':'Actual Windows native clients using generated desktop movement/weapon intents through original RPCs; not humans, XR, LAN or capacity acceptance'})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime-root',type=Path,required=True);p.add_argument('--mode',choices=('linked','independent','both'),default='both');p.add_argument('--players-per-room',type=int,choices=(1,5),default=5);p.add_argument('--seconds',type=int,choices=range(12,41),default=16)
    p.add_argument('--api-dll',type=Path,default=Path(os.environ.get('VR_COMMAND_API_DLL',ROOT/'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')));p.add_argument('--player-exe',type=Path,default=ROOT/'artifacts/desktop/VrCommand.exe');args=p.parse_args();args.duration=600;args.visible_room=0;args.job_workers=2;args.check=False
    vm.verify_player(args);v=ExerciseVenue(args)
    try:run(v)
    except BaseException as error:
        v.stage('failed',errorType=type(error).__name__);forensics=[]
        for directory in v.exercise.values():
            if directory.is_dir() and not (directory/'report.json').exists():(directory/'finish.request').write_text('',encoding='utf-8')
        for entry in v.rounds:
            if (v.directory/(entry['name']+'-full-replay.json')).exists():continue
            try:
                if v.request(f'/api/sessions/{entry["id"]}/world',optional=True):
                    v.seal(entry);result=replay(v,entry,v.pauses.get(entry['id']));forensics.append({'sessionId':entry['id'],'replayRead':True,'acceptancePassed':result['complete']})
            except Exception as issue:forensics.append({'sessionId':entry['id'],'replayRead':False,'errorType':type(issue).__name__})
        v.save('failure-forensics.json',{'originalErrorType':type(error).__name__,'rounds':forensics,'acceptancePassed':False});raise
    finally:
        failed=sys.exc_info()[0] is not None;clean=v.cleanup()
        if not clean and not failed:raise RuntimeError('Exercise cleanup incomplete')
        if clean and not failed:
            result=vm.read_json(v.directory/'exercise-result.json');result['complete']=True;v.save('exercise-result.json',result);v.stage('passed',checks=len(v.evidence))
if __name__=='__main__':main()
