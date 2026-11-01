"""Native server patrol around a rotated barrel; no pose, input or GPU injection."""
import argparse,hashlib,importlib.util,json,math,re,sys,time,urllib.request
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
venue=module('navigation_venue','start-desktop-venue.py');capacity=module('navigation_capacity','check-desktop-capacity.py');debrief=module('navigation_debrief','check-desktop-debrief.py');practice=module('navigation_report','start-desktop-demo.py')
def observer_sources():return {name:hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest() for name in ('check-desktop-navigation.py','start-desktop-venue.py','check-desktop-capacity.py','check-desktop-debrief.py','start-desktop-demo.py')}
def distance(a,b):return math.dist(tuple(a[k] for k in ('x','y','z')),tuple(b[k] for k in ('x','y','z')))
def wait_endpoint(v,entry,header,begin,enemy):
    deadline=time.monotonic()+20;started=datetime.fromisoformat(header['captureStartedAtUtc'])
    if started.utcoffset() is None:raise ValueError('Source capture UTC offset missing')
    request=urllib.request.Request(v.base+f'/api/sessions/{entry["id"]}/world/watch?mode=live',headers={'Authorization':'Bearer '+v.tokens['Master']})
    report={'complete':False,'frames':0,'firstSequence':None,'lastSequence':None,'maximumSourceAgeSeconds':None,'scope':'One continuous live source stream, 20 seconds / 256 frames; original endpoint distance <0.2m'}
    try:
        with urllib.request.urlopen(request,timeout=5) as response:
            for q in capacity.sse_frames(response):
                if time.monotonic()>deadline:raise RuntimeError('Native patrol endpoint observation timed out')
                p=q['packet'];report['frames']+=1
                if report['frames']>256:raise RuntimeError('Native patrol observation frame limit')
                if report['lastSequence'] is not None and p['sequence']!=report['lastSequence']+1:raise RuntimeError('Native patrol live source skipped a sequence')
                if report['firstSequence'] is None:report['firstSequence']=p['sequence']
                report['lastSequence']=p['sequence'];age=time.time()-started.timestamp()-p['elapsedMilliseconds']/1000
                report['maximumSourceAgeSeconds']=max(age,report['maximumSourceAgeSeconds'] if report['maximumSourceAgeSeconds'] is not None else age)
                if not -1<=age<1.5 or p['suspended']:raise RuntimeError('Native patrol source stale / suspended')
                row=next((e for e in p['frame']['enemies'] if e['id']==enemy),None)
                if p['observedSequence']>=begin and p['frame']['phase']=='Running' and p['frame']['tick']>0 and row and distance(row['feet'],{'x':4.5,'y':0,'z':5})<.2:
                    report['complete']=True;report['endpointTick']=p['frame']['tick'];return q
        raise RuntimeError('Native patrol live stream ended before endpoint')
    finally:v.save('navigation-patrol-observation.json',report)
def inspect_frame(value,player,enemy,previous=None):
    p=value['packet'];f=p['frame'];errors=[]
    if type(f.get('tick')) is not int or f['tick']<0:return ['invalid simulation clock']
    if p['suspended']:errors.append('source suspended')
    if len(f['players'])!=1 or f['players'][0]['id']!=player or not f['players'][0]['connected'] or f['players'][0]['health']!=100 or f['players'][0]['rig']['kind']!='Simulated':errors.append('original participant invalid')
    if len(f['enemies'])!=1 or f['enemies'][0]['id']!=enemy:return errors+['original enemy missing']
    row=f['enemies'][0];feet=row['feet']
    if row['health']!=100 or row['roomId']!=3 or f['autoAttack'] or row['fireSequence']!=0:errors.append('unexpected combat / room')
    if set(feet)!={'x','y','z'} or any(type(v) not in (int,float) or not math.isfinite(v) for v in feet.values()):return errors+['invalid position']
    # Independent saved-position check against this fixture's expanded rotated
    # barrel footprint. Missing intermediate ticks are NOT interpolated as paths.
    x,z=feet['x']-.25,feet['z']+1.75;c=math.sqrt(.5)
    if abs(feet['x'])>5.70001 or abs(feet['z'])>5.70001 or abs(feet['y'])>1e-5 or (abs(c*x-c*z)<=.65 and abs(c*x+c*z)<=.65):errors.append('saved position intersects clearance')
    if previous:
        prior=previous['packet']['frame'];dt=f['tick']-prior['tick']
        old=next((e for e in prior['enemies'] if e['id']==enemy),None)
        if dt<0 or (old and distance(old['feet'],feet)>.1*dt+.0001):errors.append('movement exceeds elapsed tick bound')
    return errors
def run(v):
    v.start();mission=v.request('/api/missions',{'name':'Rotated barrel navigation - Simulation','briefing':'Server patrol / Hold / Pause / Advance. No client input.', 'durationSeconds':180,
        'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},'enemies':{'count':1,'behavior':'Patrol','autoAttack':False},
        'props':[{'assetId':'barrel','position':{'x':.25,'y':0,'z':-1.75},'yawDegrees':45}]},expected=201)
    e=v.create(mission,[3],'navigation',role='Room3');own=e['players'][0]
    v.clients([e]);initial=v.wait(lambda:v.connected(e),30,'original navigation player')
    header=v.request(f'/api/sessions/{e["id"]}/world')['header'];props=header['props']
    if header['origin']!='Simulation' or header['roomIds']!=[3] or len(props)!=1 or props[0]['kind']!='Barrel' or props[0]['roomId']!=3 or props[0]['yaw']!=45 or props[0]['feet']!={'x':.25,'y':0,'z':-1.75}:raise RuntimeError('Accepted geometry differs from navigation fixture')
    v.save('navigation-world-header.json',header)
    enemy=initial['packet']['frame']['enemies'][0]['id'];feet=initial['packet']['frame']['enemies'][0]['feet']
    if distance(feet,{'x':-4.5,'y':0,'z':-1})>1e-5:raise RuntimeError('Generated patrol spawn differs')
    refs={};receipts={}
    def frame():return v.frame(e,measure=True)
    def fence(label,action,**extra):
        receipt=v.command(e,action,**extra);receipts[label]=receipt;v.save('navigation-command-receipts.json',receipts)
        value=v.wait(lambda:(q if (q:=frame())['packet']['observedSequence']>=receipt['appliedAtSequence'] and not q['packet']['suspended'] and q['packet']['frame']['phase']==('Paused' if action=='Pause' else 'Running') and q['packet']['frame']['tick']>0 else None),15,label+' applied by source')
        refs[label]=value;v.save('navigation-references.json',refs);return value
    running=fence('begin','Begin')
    reached=wait_endpoint(v,e,header,receipts['begin']['appliedAtSequence'],enemy)
    refs['patrol-endpoint']=reached
    held=fence('hold','SetEnemies',enemies={'count':1,'behavior':'Hold','autoAttack':False})
    later=v.wait(lambda:(q if (q:=frame())['packet']['frame']['tick']>=held['packet']['frame']['tick']+12 else None),5,'Hold observation')
    if distance(held['packet']['frame']['enemies'][0]['feet'],later['packet']['frame']['enemies'][0]['feet'])>1e-6:raise RuntimeError('Hold moved the enemy')
    refs['hold-later']=later;paused=fence('pause','Pause');time.sleep(.5);again=frame()
    if again['packet']['frame']['tick']!=paused['packet']['frame']['tick'] or distance(again['packet']['frame']['enemies'][0]['feet'],paused['packet']['frame']['enemies'][0]['feet'])>1e-6:raise RuntimeError('Paused navigation moved')
    refs['paused-later']=again;fence('resume','Resume');advance=fence('advance','SetEnemies',enemies={'count':1,'behavior':'Advance','autoAttack':False})
    moved=v.wait(lambda:(q if distance((q:=frame())['packet']['frame']['enemies'][0]['feet'],advance['packet']['frame']['enemies'][0]['feet'])>1 else None),8,'native Advance movement');refs['advance-moved']=moved
    v.save('navigation-references.json',refs);sealed=v.seal(e);delivery=v.wait_for_player_results(e)
    result=debrief.final_result(v,'navigation-client-3');debrief.validate_result(result,e,own,sealed)
    connected=re.findall(r'VR_CLIENT_CONNECTED id=(\d+)',debrief.log_text(v,'navigation-client-3'));acks=re.findall(r'VR_SERVER_DEBRIEF_ACK id=(\d+)',debrief.log_text(v,'navigation-server'))
    if delivery['allAcknowledged'] is not True or delivery['timedOut'] or len(connected)!=1 or acks!=connected:raise RuntimeError('Original result / native ACK differs')
    stats=sealed['statistics']['players'][0]
    if stats['health']!=100 or any(stats[k]!=0 for k in ('ammoUsed','kills','damageTaken','hitsReceived','shotsHit')):raise RuntimeError('Navigation controls changed isolated combat statistics')
    csv=practice.save_report(v,e,sealed['statistics']);v.stop_round(e)
    request=urllib.request.Request(v.base+f'/api/sessions/{e["id"]}/world/watch?mode=replay&fromMs=0&rate=4',headers={'Authorization':'Bearer '+v.tokens['Master']})
    count=0;faults=[];fault_count=0;previous=None;matched=set();expected={q['packet']['sequence']:q for q in refs.values()};validated=0;first_validated=None
    deadline=time.monotonic()+sealed['world']['durationMilliseconds']/4000+30
    with urllib.request.urlopen(request,timeout=10) as response:
        for q in capacity.sse_frames(response):
            if time.monotonic()>deadline:raise RuntimeError('Navigation replay exceeded its bound')
            p=q['packet'];count+=1
            if p['sequence']!=count:raise RuntimeError('Noncontiguous navigation replay')
            if p['observedSequence']>=receipts['begin']['appliedAtSequence'] and p['frame']['phase'] in ('Running','Paused'):
                validated+=1
                if first_validated is None:first_validated=count
                errors=inspect_frame(q,own['id'],enemy,previous)
                if errors:
                    fault_count+=1
                    if len(faults)<128:faults.append({'sequence':count,'errors':errors})
                previous=q
            if count in expected:
                if q!=expected[count]:raise RuntimeError('Navigation checkpoint differs from saved replay')
                matched.add(count)
            last=q
    replay={'complete':fault_count==0 and validated>0,'frames':count,'validatedFrames':validated,'firstValidatedSequence':first_validated,'firstLiveRunningSequence':running['packet']['sequence'],
        'acceptedBeginSequence':receipts['begin']['appliedAtSequence'],'faultCount':fault_count,'faults':faults,'matchedReferences':len(matched),'scope':'All accepted-Begin Running / Paused saved positions and elapsed-tick displacement; no intermediate-tick interpolation or render / replica evidence'}
    v.save('navigation-replay.json',replay)
    if not replay['complete'] or count!=sealed['world']['acceptedSequence'] or matched!=set(expected) or last['packet']['frame']['phase']!='Ended':raise RuntimeError('Navigation replay / exact seal failed')
    v.save('navigation-result.json',{'complete':False,'headsets':0,'hosts':1,'source':'Actual Windows authority / headless client; Simulation','poseOrInputInjected':False,'replay':replay,'csv':csv,'result':result})
    v.evidence.extend(['native generated patrol bypasses rotated cover and reaches its original endpoint','operator Hold and Pause preserve the original enemy clock / position; Advance resumes movement','full saved-world replay preserves original participant / enemy and clearance / tick bounds','exact dual seals / original player result / CSV / native server ACK'])
    v.summary()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime-root',type=Path,required=True);p.add_argument('--api-dll',type=Path,required=True);p.add_argument('--player-exe',type=Path,default=ROOT/'artifacts/desktop/VrCommand.exe');args=p.parse_args();args.duration=180;args.visible_room=0;args.job_workers=2;args.check=False
    venue.verify_player(args);v=venue.Venue(args,artifact_family='desktop-navigation');sources=observer_sources();v.save('observer-sources.json',{'files':sources,'scope':'Five helpers only; not the complete runtime / OS dependency graph'})
    try:v.stage('starting',headsets=0);run(v)
    except BaseException as error:v.stage('failed',errorType=type(error).__name__);raise
    finally:
        failed=sys.exc_info()[0] is not None
        if not v.cleanup() and not failed:v.stage('failed',errorType='CleanupError');raise RuntimeError('Navigation cleanup failed')
    if observer_sources()!=sources:v.stage('failed',errorType='ObserverSourceChanged');raise RuntimeError('Navigation helpers changed during this run')
    result=venue.read_json(v.directory/'navigation-result.json');result['complete']=True;v.save('navigation-result.json',result);v.stage('passed',checks=len(v.evidence))
if __name__=='__main__':main()
