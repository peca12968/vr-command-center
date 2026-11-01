"""Observe actual C / W input in one owned visible Windows client. No input injection."""
import argparse,hashlib,importlib.util,json,math,re,sys,time,urllib.request,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
venue=module('crouch_venue','start-desktop-venue.py');capacity=module('crouch_capacity','check-desktop-capacity.py');debrief=module('crouch_debrief','check-desktop-debrief.py');practice=module('crouch_practice','start-desktop-demo.py')
def sources():return {n:hashlib.sha256((ROOT/'scripts'/n).read_bytes()).hexdigest() for n in ('check-desktop-crouch.py','start-desktop-venue.py','check-desktop-capacity.py','check-desktop-debrief.py','start-desktop-demo.py')}
def height(body,value):return type(body['head']['y']) in (int,float) and math.isfinite(body['head']['y']) and abs(body['head']['y']-value)<1e-5
def validate_body(body,health,eligible=True):
    if body['health']!=health or body['magazine']!=30 or body['reserve']!=90:raise RuntimeError('Unexpected crouch health / ammunition')
    if eligible and (not body['connected'] or body['rig']['kind']!='Simulated'):raise RuntimeError('Original crouch participant invalid')
def intentional_focus_pause(packet,receipts):
    observed=packet.get('observedSequence')
    return packet['frame']['phase']=='Paused' and type(observed) is int and receipts['focus-pause']['appliedAtSequence']<=observed<receipts['focus-resume']['appliedAtSequence']
def run(v):
    deadline=time.monotonic()+600;v.start();mission=v.request('/api/missions',{'name':'Desktop crouch cover - Simulation','briefing':'C toggles crouch, Ctrl holds crouch; actual keyboard only.', 'durationSeconds':600,
        'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},'enemies':{'count':1,'behavior':'Hold','autoAttack':False},
        'props':[{'assetId':'barrel','position':{'x':-3.75,'y':0,'z':-2},'yawDegrees':0}]},expected=201)
    e=v.create(mission,[3],'crouch',role='Room3');player=e['players'][0]
    state=v.request(f'/api/sessions/{e["id"]}/players',{'playerId':str(uuid.uuid4()),'roomId':3,'name':'PC crouch peer','headset':'Quest3'},role='Room3');e['players']=state['players'];peer=next(p for p in e['players'] if p['id']!=player['id'])
    v.wait(lambda:v.request(f'/api/sessions/{e["id"]}/world',optional=True),90,'own crouch header')
    v.launch('crouch-peer',v.client_config(e,v.ticket(e,peer)));v.launch('crouch-player',v.client_config(e,v.ticket(e,player)),True);v.wait(lambda:v.connected(e),30,'both crouch participants')
    refs={};receipts={};reviews={}
    def sample(label):
        if time.monotonic()>deadline:raise RuntimeError('Crouch fixture exceeded 600 seconds')
        q=v.frame(e,True);body=next(r for r in q['packet']['frame']['players'] if r['id']==player['id']);other=next(r for r in q['packet']['frame']['players'] if r['id']==peer['id'])
        if not height(other,1.65) or abs(other['head']['x']+1.5)>1e-5 or abs(other['head']['z']+3)>1e-5 or other['magazine']!=30 or other['reserve']!=90:raise RuntimeError('Local stance input changed the original peer')
        refs[label]=q;v.save('crouch-references.json',refs);return q,body
    def fence(label,action,**extra):
        receipt=v.command(e,action,**extra);receipts[label]=receipt;v.save('crouch-commands.json',receipts)
        return v.wait(lambda:(q if (q:=sample(label)[0])['packet']['observedSequence']>=receipt['appliedAtSequence'] and not q['packet']['suspended'] and q['packet']['frame']['phase']==('Paused' if action=='Pause' else 'Running') and q['packet']['frame']['tick']>0 else None),15,label+' applied')
    def review(stage,predicate,*,protect=False,allow_unavailable=False):
        v.stage('input-'+stage,review=stage+'.review.json',instruction={'crouch':'Press C once and inspect CROUCHED','stand':'Press C once and inspect STANDING; server stops AI after one hit','move':'Press C to crouch, then W once; inspect CROUCHED','focus':'While Paused, minimize and restore this owned game window without C; inspect STANDING'}[stage])
        stopped=False
        def ready():
            nonlocal stopped
            q,body=sample('review-'+stage)
            if protect and body['health']<100 and not stopped:
                fence('attack-off','SetEnemies',enemies={'count':1,'behavior':'Hold','autoAttack':False});stopped=True;q,body=sample('protected-stand')
            validate_body(body,80 if stage in ('move','focus') or stopped else 100,eligible=not allow_unavailable)
            path=v.directory/(stage+'.review.json')
            if path.exists():
                value=venue.read_json(path)
                if value.get('version')!=1 or value.get('stage')!=stage or value.get('observed') is not True:raise RuntimeError('Input review did not confirm the observed stage')
                reviews[stage]=value;v.save('crouch-reviews.json',reviews)
                if predicate(q,body) and (not protect or stopped):return q
            return None
        return v.wait(ready,120,'actual observed input '+stage)
    initial=fence('begin','Begin');q,body=sample('standing-before');validate_body(body,100)
    if not height(body,1.65) or abs(body['head']['x']+3)>1e-5 or abs(body['head']['z']+3)>1e-5:raise RuntimeError('Original crouch spawn differs')
    if len(q['packet']['frame']['enemies'])!=1 or abs(q['packet']['frame']['enemies'][0]['feet']['x']+4.5)>1e-5 or abs(q['packet']['frame']['enemies'][0]['feet']['z']+1)>1e-5:raise RuntimeError('Original enemy spawn differs')
    enemy=q['packet']['frame']['enemies'][0]['id']
    header=v.request(f'/api/sessions/{e["id"]}/world')['header'];v.save('crouch-world-header.json',header)
    if header['origin']!='Simulation' or header['roomIds']!=[3] or len(header['props'])!=1:raise RuntimeError('Crouch source / geometry differs')
    prop=header['props'][0]
    if prop['kind']!='Barrel' or prop['roomId']!=3 or prop['yaw']!=0 or any(abs(prop['feet'][k]-value)>1e-5 for k,value in {'x':-3.75,'y':0,'z':-2}.items()):raise RuntimeError('Crouch cover differs from the actual recorded barrel')
    review('crouch',lambda q,b:height(b,1))
    active=fence('attack-on','SetEnemies',enemies={'count':1,'behavior':'Hold','autoAttack':True});start=active['packet']['frame']['tick']
    def protected():
        q,b=sample('crouch-protected');validate_body(b,100)
        if not height(b,1) or body_x(b)>1e-5 or abs(b['head']['z']+3)>1e-5 or not q['packet']['frame']['autoAttack']:raise RuntimeError('Crouched cover did not block AI at its original position')
        return q if q['packet']['frame']['tick']>=start+44 else None
    defended=v.wait(protected,8,'44 active crouch ticks behind cover');defense_end=defended['packet']['frame']['tick']
    review('stand',lambda q,b:height(b,1.65) and body_x(b)<1e-5 and abs(b['head']['z']+3)<1e-5 and b['health']==80,protect=True)
    review('move',lambda q,b:height(b,1) and body_x(b)<.01 and -2.99<b['head']['z']<-2.5)
    fence('focus-pause','Pause');review('focus',lambda q,b:b['connected'] and b['rig']['kind']=='Simulated' and height(b,1.65) and b['health']==80,allow_unavailable=True)
    fence('focus-resume','Resume');q,body=sample('restored-standing');validate_body(body,80)
    sealed=v.seal(e);delivery=v.wait_for_player_results(e);result=debrief.final_result(v,'crouch-player');debrief.validate_result(result,e,player,sealed)
    peer_result=debrief.final_result(v,'crouch-peer');debrief.validate_result(peer_result,e,peer,sealed)
    if not delivery['allAcknowledged'] or delivery['timedOut'] or result['damageTaken']!=20 or result['hitsReceived']!=1 or result['ammoUsed']!=0:raise RuntimeError('Final crouch statistics differ')
    ids=[]
    for name in ('crouch-player','crouch-peer'):
        connected=re.findall(r'VR_CLIENT_CONNECTED id=(\d+)',debrief.log_text(v,name))
        if len(connected)!=1:raise RuntimeError('Ambiguous crouch original connection')
        ids.extend(connected)
    acks=re.findall(r'VR_SERVER_DEBRIEF_ACK id=(\d+)',debrief.log_text(v,'crouch-server'))
    if len(set(ids))!=2 or sorted(ids)!=sorted(acks):raise RuntimeError('Original crouch ACK differs')
    csv=practice.save_report(v,e,sealed['statistics']);v.stop_round(e)
    request=urllib.request.Request(v.base+f'/api/sessions/{e["id"]}/world/watch?mode=replay&fromMs=0&rate=4',headers={'Authorization':'Bearer '+v.tokens['Master']})
    count=0;events=[];validated=0;unavailable_paused=0;matched=set();references={q['packet']['sequence']:q['packet'] for q in refs.values()};replay_deadline=time.monotonic()+sealed['world']['durationMilliseconds']/4000+30
    with urllib.request.urlopen(request,timeout=10) as response:
        for q in capacity.sse_frames(response):
            count+=1;p=q['packet'];f=p['frame']
            if p['sequence']!=count or time.monotonic()>replay_deadline:raise RuntimeError('Crouch replay skipped / exceeded bound')
            for event in p['events']:
                if event['sequence']!=len(events)+1:raise RuntimeError('Crouch event sequence skipped')
                events.append(event)
            if count in references:
                if p!=references[count]:raise RuntimeError('Saved crouch checkpoint differs')
                matched.add(count)
            if p['observedSequence']>=receipts['begin']['appliedAtSequence'] and f['phase'] in ('Running','Paused'):
                validated+=1;body=next((b for b in f['players'] if b['id']==player['id']),None)
                if body is None or p['suspended']:raise RuntimeError('Crouch source invalid')
                intentional=intentional_focus_pause(p,receipts)
                if f['phase']=='Paused' and not intentional:raise RuntimeError('Unexpected crouch Pause')
                if not body['connected'] or body['rig']['kind']!='Simulated':
                    if not intentional:raise RuntimeError('Running crouch participant lost')
                    unavailable_paused+=1
                if body['magazine']!=30 or body['reserve']!=90 or body['health'] not in (80,100):raise RuntimeError('Unexpected saved crouch combat')
                if len(f['players'])!=2 or {b['id'] for b in f['players']}!={player['id'],peer['id']} or body['roomId']!=3 or len(f['enemies'])!=1 or f['enemies'][0]['id']!=enemy or f['enemies'][0]['health']!=100 or f['behavior']!='Hold':raise RuntimeError('Original crouch roster / NPC / policy differs')
                other=next(b for b in f['players'] if b['id']==peer['id'])
                if not height(other,1.65) or abs(other['head']['x']+1.5)>1e-5 or abs(other['head']['z']+3)>1e-5 or other['magazine']!=30 or other['reserve']!=90:raise RuntimeError('Saved crouch input moved the peer')
                if other['health']>0 and (not other['connected'] or other['rig']['kind']!='Simulated'):raise RuntimeError('Alive peer lost participation')
                feet=f['enemies'][0]['feet']
                if abs(feet['x']+4.5)>1e-5 or abs(feet['y'])>1e-5 or abs(feet['z']+1)>1e-5:raise RuntimeError('Hold enemy moved during crouch')
                if body['connected'] and body['rig']['kind']=='Simulated' and not (height(body,1) or height(body,1.65)):raise RuntimeError('Accepted desktop eye height differs from either stance')
    shots=[e for e in events if e['kind']=='EnemyShot' and e['playerId']==player['id']];damages=[e for e in events if e['kind']=='PlayerDamaged' and e['playerId']==player['id']]
    peer_defense=[event for event in events if event['kind']=='EnemyShot' and event['playerId']==peer['id'] and start<=event['tick']<=defense_end]
    if count!=sealed['world']['acceptedSequence'] or matched!=set(references) or len(shots)!=1 or len(damages)!=1 or damages[0]['damage']!=20 or len(peer_defense)<2 or any(e['kind']=='ShotFired' for e in events):raise RuntimeError('Crouch replay / exact shot count differs')
    v.save('crouch-result.json',{'complete':False,'headsets':0,'source':'Actual Windows C / W and focus UI; Simulation, no pose / weapon injection','frames':count,'validatedFrames':validated,'matchedReferences':len(matched),'intentionalUnavailablePausedFrames':unavailable_paused,'defenseStartTick':start,'defenseEndTick':defense_end,'peerDefenseShots':len(peer_defense),'result':result,'peerResult':peer_result,'csv':csv,'reviews':reviews})
    v.evidence.extend(['actual C lowers the original accepted eye and gun pose','44 active ticks behind barrel protect the crouched player while AI actually fires at the peer','standing permits exactly one original twenty-point enemy hit','actual crouched W preserves height; peer stays at its original standing pose','explicit Pause / focus restore clears stance before valid Resume','complete replay / two original admission results / CSV / dual seals / unique ACKs']);v.summary()
def body_x(body):return abs(body['head']['x']+3)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime-root',type=Path,required=True);p.add_argument('--api-dll',type=Path,required=True);p.add_argument('--player-exe',type=Path,default=ROOT/'artifacts/desktop/VrCommand.exe');args=p.parse_args();args.duration=600;args.visible_room=3;args.job_workers=2;args.check=False
    venue.verify_player(args);v=venue.Venue(args,artifact_family='desktop-crouch');original=sources();v.save('observer-sources.json',{'files':original,'scope':'Five helper files, not a complete runtime / OS graph'})
    try:v.stage('starting',headsets=0);run(v)
    except BaseException as error:v.stage('failed',errorType=type(error).__name__);raise
    finally:
        failed=sys.exc_info()[0] is not None
        if not v.cleanup() and not failed:v.stage('failed',errorType='CleanupError');raise RuntimeError('Crouch cleanup failed')
    if sources()!=original:v.stage('failed',errorType='ObserverSourceChanged');raise RuntimeError('Crouch helpers changed during this run')
    result=venue.read_json(v.directory/'crouch-result.json');result['complete']=True;v.save('crouch-result.json',result);v.stage('passed',checks=len(v.evidence))
if __name__=='__main__':main()
