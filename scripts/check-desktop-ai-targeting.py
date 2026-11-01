"""Three genuine PC admissions and two generated NPCs; no pose / input injection."""
import argparse,hashlib,importlib.util,json,math,re,sys,time,urllib.request,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
venue=module('targeting_venue','start-desktop-venue.py');capacity=module('targeting_capacity','check-desktop-capacity.py');debrief=module('targeting_debrief','check-desktop-debrief.py');practice=module('targeting_practice','start-desktop-demo.py')
def observer_sources():return {name:hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest() for name in ('check-desktop-ai-targeting.py','start-desktop-venue.py','check-desktop-capacity.py','check-desktop-debrief.py','start-desktop-demo.py')}
def props():
    return [{'assetId':'sandbag','position':{'x':-4.6,'y':0,'z':-.6},'yawDegrees':90},{'assetId':'barrel','position':{'x':-3.8,'y':0,'z':-.6},'yawDegrees':0}]+[
        {'assetId':'sandbag','position':{'x':x,'y':0,'z':-.625},'yawDegrees':0} for x in (-1.5,.8,3.1)]+[{'assetId':'barrel','position':{'x':4.9,'y':0,'z':-.625},'yawDegrees':0}]
def near(a,b):return all(type(a.get(k)) in (int,float) and math.isfinite(a[k]) and abs(a[k]-b[k])<1e-5 for k in ('x','y','z'))
def targeting_errors(events,shooter,far,blocker,close):
    first=next((e for e in events if e['kind']=='EnemyShot' and e['enemyId']==shooter),None)
    if first is None:return ['rear NPC never fired']
    errors=[]
    if first['tick']!=1 or first['playerId']!=far or first['targetId']!=far or first['hit']!='Friendly':errors.append('rear NPC did not select the visible farther player on tick1')
    if sum(e.get('damage',0) for e in events if e['sequence']<first['sequence'] and e['kind']=='PlayerDamaged' and e['playerId']==close)!=20:errors.append('closest player was not alive with the original front-NPC damage when the rear NPC fired')
    damage=next((e for e in events if e['sequence']==first['sequence']+1),None)
    if damage is None or damage['kind']!='PlayerDamaged' or damage['playerId']!=far or damage['enemyId']!=shooter or damage['tick']!=first['tick'] or damage.get('damage')!=20:errors.append('visible-target damage does not match the accepted twenty-point shot')
    direction={'x':3,'y':.25,'z':-2.75};length=math.sqrt(sum(v*v for v in direction.values()));direction={k:v/length for k,v in direction.items()}
    if not near(first.get('origin',{}),{'x':-3,'y':1.4,'z':-.25}) or not near(first.get('direction',{}),direction):errors.append('shot differs from the actual rear muzzle / visible target ray')
    front=next((e for e in events if e['kind']=='EnemyShot' and e['enemyId']==blocker),None)
    if front is None or front['tick']!=1 or front['playerId']!=close:errors.append('front NPC / closest live player control differs')
    return errors
def run(v):
    v.start();mission=v.request('/api/missions',{'name':'AI visible target - Simulation','briefing':'Three normal admissions, two generated NPCs; no client input.', 'durationSeconds':180,
        'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},'enemies':{'count':2,'behavior':'Hold','autoAttack':True},'props':props()},expected=201)
    e=v.create(mission,[3],'ai-targeting',role='Room3')
    for label in ('middle occluded','far visible'):
        state=v.request(f'/api/sessions/{e["id"]}/players',{'playerId':str(uuid.uuid4()),'roomId':3,'name':'PC '+label,'headset':'Quest3'},role='Room3');e['players']=state['players']
    v.wait(lambda:v.request(f'/api/sessions/{e["id"]}/world',optional=True),90,'own world header')
    names={}
    for player in e['players']:
        name=e['name']+'-client-'+player['admissionId'];names[player['id']]=name;v.launch(name,v.client_config(e,v.ticket(e,player)))
    initial=v.wait(lambda:v.connected(e),30,'both original valid synthetic rigs');frame=initial['packet']['frame']
    players=sorted(e['players'],key=lambda p:p['seat']);close,middle,far=(p['id'] for p in players)
    enemies=sorted(frame['enemies'],key=lambda p:p['feet']['z']);blocker,shooter=(p['id'] for p in enemies)
    if len(enemies)!=2 or not near(enemies[0]['feet'],{'x':-3,'y':0,'z':-1}) or not near(enemies[1]['feet'],{'x':-3,'y':0,'z':-.25}):raise RuntimeError('Generated NPC geometry differs')
    for p,x in zip(players,(-3,-1.5,0)):
        row=next(row for row in frame['players'] if row['id']==p['id'])
        if not near(row['head'],{'x':x,'y':1.65,'z':-3}) or row['health']!=100:raise RuntimeError('Original player spawn differs')
    v.save('targeting-initial.json',initial);begin=v.command(e,'Begin');v.save('targeting-begin.json',begin)
    running=v.wait(lambda:(q if (q:=v.frame(e,True))['packet']['observedSequence']>=begin['appliedAtSequence'] and q['packet']['frame']['phase']=='Running' and q['packet']['frame']['tick']>0 and not q['packet']['suspended'] else None),15,'accepted Begin applied')
    v.save('targeting-first-live.json',running);pause=v.command(e,'Pause');v.save('targeting-pause.json',pause)
    v.wait(lambda:(q if (q:=v.frame(e,True))['packet']['observedSequence']>=pause['appliedAtSequence'] and q['packet']['frame']['phase']=='Paused' and q['packet']['frame']['tick']>0 and not q['packet']['suspended'] else None),15,'Pause applied')
    sealed=v.seal(e);delivery=v.wait_for_player_results(e);results={}
    connected=[]
    for p in players:
        name=names[p['id']];result=debrief.final_result(v,name);debrief.validate_result(result,e,p,sealed);results[p['id']]=result
        ids=re.findall(r'VR_CLIENT_CONNECTED id=(\d+)',debrief.log_text(v,name))
        if len(ids)!=1:raise RuntimeError('Ambiguous original native connection')
        connected.extend(ids)
    acks=re.findall(r'VR_SERVER_DEBRIEF_ACK id=(\d+)',debrief.log_text(v,e['name']+'-server'))
    if delivery['allAcknowledged'] is not True or delivery['timedOut'] or sorted(acks)!=sorted(connected):raise RuntimeError('Original result ACK differs')
    csv=practice.save_report(v,e,sealed['statistics']);v.stop_round(e)
    request=urllib.request.Request(v.base+f'/api/sessions/{e["id"]}/world/watch?mode=replay&fromMs=0&rate=4',headers={'Authorization':'Bearer '+v.tokens['Master']})
    count=0;events=[];event_sequence=0;validated=0;deadline=time.monotonic()+sealed['world']['durationMilliseconds']/4000+30
    with urllib.request.urlopen(request,timeout=10) as response:
        for q in capacity.sse_frames(response):
            count+=1;p=q['packet'];f=p['frame']
            for event in p['events']:
                event_sequence+=1
                if event['sequence']!=event_sequence:raise RuntimeError('Replay event sequence skipped / duplicated')
                events.append(event)
            if time.monotonic()>deadline or p['sequence']!=count:raise RuntimeError('Replay exceeded bound / skipped sequence')
            if p['observedSequence']>=begin['appliedAtSequence'] and f['phase'] in ('Running','Paused'):
                validated+=1
                heads={close:-3,middle:-1.5,far:0}
                if p['suspended'] or {r['id'] for r in f['players']}!={close,middle,far} or any(not r['connected'] or r['roomId']!=3 or r['rig']['kind']!='Simulated' or not near(r['head'],{'x':heads[r['id']],'y':1.65,'z':-3}) for r in f['players']):raise RuntimeError('Original stationary participants lost during combat')
                if {r['id'] for r in f['enemies']}!={shooter,blocker} or any(r['health']!=100 or r['roomId']!=3 or not near(r['feet'],{'x':-3,'y':0,'z':-.25 if r['id']==shooter else -1}) for r in f['enemies']):raise RuntimeError('Hold NPC identity / position differs')
    if count!=sealed['world']['acceptedSequence'] or not validated:raise RuntimeError('Replay / seal differs')
    errors=targeting_errors(events,shooter,far,blocker,close)
    v.save('targeting-result.json',{'complete':False,'acceptancePassed':not errors,'errors':errors,'frames':count,'validatedFrames':validated,'events':events,'results':results,'csv':csv,
        'scope':'Actual same-machine Windows authority and three headless clients / original admissions; Simulation. No player input, pose injection, GPU or headset.'})
    if errors:raise RuntimeError('First-tick targeting failed: '+', '.join(errors))
    v.evidence.extend(['valid VR layout yields original two stationary NPCs and three real admissions','rear NPC selects visible farther player while front NPC blocks the closer players on tick1','complete replay preserves original participants / Hold positions','exact seals / original result ACKs / CSV']);v.summary()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime-root',type=Path,required=True);p.add_argument('--api-dll',type=Path,required=True);p.add_argument('--player-exe',type=Path,default=ROOT/'artifacts/desktop/VrCommand.exe');args=p.parse_args();args.duration=180;args.visible_room=0;args.job_workers=2;args.check=False
    venue.verify_player(args);v=venue.Venue(args,artifact_family='desktop-ai-targeting');sources=observer_sources();v.save('observer-sources.json',{'files':sources,'scope':'Five helper files only, not a complete runtime / OS dependency graph'})
    try:v.stage('starting',headsets=0);run(v)
    except BaseException as error:v.stage('failed',errorType=type(error).__name__);raise
    finally:
        failed=sys.exc_info()[0] is not None
        if not v.cleanup() and not failed:v.stage('failed',errorType='CleanupError');raise RuntimeError('Targeting cleanup failed')
    if observer_sources()!=sources:v.stage('failed',errorType='ObserverSourceChanged');raise RuntimeError('Targeting helpers changed during this run')
    result=venue.read_json(v.directory/'targeting-result.json');result['complete']=True;v.save('targeting-result.json',result);v.stage('passed',checks=len(v.evidence))
if __name__=='__main__':main()
