"""Exercise real portable control/server packages, five rooms, Linked and owned-job cleanup. No UI input."""
import argparse,ctypes,importlib.util,json,os,shutil,socket,subprocess,time,urllib.error,urllib.request,uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
package=module('server_package','package-windows-server.py');control=module('server_control_checks','check-control-package.py');venue=module('server_venue','start-desktop-venue.py');world=module('server_world','analyze-world-journal.py');debrief=module('server_debrief','check-desktop-debrief.py')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def free(kind=socket.SOCK_STREAM):
    with socket.socket(socket.AF_INET,kind) as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path);p.add_argument('--control-package',type=Path,required=True);p.add_argument('--runtime-root',type=Path,required=True);args=p.parse_args()
    if os.name!='nt':p.error('Actual Windows processes required')
    folder=args.package.resolve();manifest=package.verify(folder);assert manifest['launcherSourceSha256']==package.digest(ROOT/'tools/WindowsServerLauncher/ServerLauncher.cs')
    control.package.verify(args.control_package);out=ROOT/'artifacts/server-package-checks'/('run-'+uuid.uuid4().hex);out.mkdir(parents=True,exist_ok=False);runtime=args.runtime_root.resolve()/out.name;runtime.mkdir(parents=True,exist_ok=False)
    (ROOT/'artifacts/server-package-checks-latest-path.txt').write_text(str(out),encoding='utf-8');print(json.dumps({'stage':'starting','directory':str(out)}),flush=True)
    env=dict(os.environ);env.update(PATH=str(Path(os.environ['WINDIR'])/'System32'),DOTNET_ROOT=str(runtime/'absent-dotnet'),DOTNET_MULTILEVEL_LOOKUP='0');exe=folder/'Launch-Server.exe';control_exe=args.control_package.resolve()/'Start-Control.exe';data=runtime/'control';checks=[];runners=[];clients=[];cleanup=[];witnesses=[];api=None;api_witness=None;keys=None;sessions=[];rounds=[]
    def save(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    def stage(name,**extra):save('stage.json',{'stage':name,**extra});print(json.dumps({'stage':name,**extra}),flush=True)
    def check(ok,label):
        if not ok:raise AssertionError(label)
        checks.append(label);print('PASS: '+label,flush=True)
    def wait(fn,seconds,label):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            value=fn()
            if value:return value
            time.sleep(.1)
        raise RuntimeError('Timeout: '+label)
    def request(path,body=None,role='Master',method=None,expected=200,admission=None):
        h={'Authorization':'Bearer '+keys[role]};h.update({'Content-Type':'application/json'} if body is not None else {})
        if admission:h['If-Match-Admission']=admission
        req=urllib.request.Request(uri+path,data=None if body is None else json.dumps(body).encode(),headers=h,method=method)
        try:
            with urllib.request.urlopen(req,timeout=5) as r:code=r.status;raw=r.read()
        except urllib.error.HTTPError as e:code=e.code;raw=e.read()
        if code!=expected:raise RuntimeError(path+' HTTP '+str(code))
        if path.endswith('/report.csv'):return raw.decode('utf-8-sig')
        return json.loads(raw) if raw else None
    def command(session,action):return request('/api/sessions/'+session+'/commands',{'commandId':str(uuid.uuid4()),'action':action})
    def config(session,port=None,**extra):return dict({'role':'Server','managementApiUrl':uri,'gameServerKey':keys['GameServer'],'sessionId':session,'address':'127.0.0.1','listenAddress':'127.0.0.1','port':port or free(socket.SOCK_DGRAM)},**extra)
    def call(label,options,good=False,report=None):
        result=out/(label+'.json') if report is None else report
        child=subprocess.run([str(exe),*map(str,options),'--report',str(result)],env=env,cwd=out,timeout=45)
        check(child.returncode==(0 if good else 1),label+' original exit')
        if report is None:
            value=read(result);check(value['complete']==good,label+' complete flag')
        return result
    def rejected(label,value,**options):
        file=runtime/(label+'.json');file.write_text(json.dumps(value),encoding='utf-8');work=runtime/(label+'-work');ready=out/(label+'-ready.json')
        call(label,['--run',file,'--work',work,'--seconds',options.get('seconds',60),'--ready-report',ready]);check(not work.exists() and not ready.exists(),label+' creates no native world')
    def create(rooms,label):
        mission=request('/api/missions',{'name':'Portable '+label,'briefing':'Owned PC package fixture, Simulation only','durationSeconds':600,'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},'enemies':{'count':1,'behavior':'Hold','autoAttack':False},'props':[]},expected=201)
        state=request('/api/sessions',{'missionId':mission['id'],'mode':'Linked' if len(rooms)==5 else 'Independent','roomIds':rooms},expected=201);sessions.append(state['id']);return state
    def launch(state,label):
        value=config(state['id']);file=runtime/(label+'.json');file.write_text(json.dumps(value),encoding='utf-8');ready=out/(label+'-ready.json');report=out/(label+'-final.json');work=runtime/(label+'-work')
        child=subprocess.Popen([str(exe),'--run',str(file),'--work',str(work),'--seconds','600','--ready-report',str(ready),'--report',str(report)],cwd=out,env=env);entry={'process':child,'readyPath':ready,'reportPath':report,'work':work,'config':value,'label':label,'sessionId':state['id'],'witness':None};runners.append(entry)
        def is_ready():
            if child.poll() is not None:raise RuntimeError('Server launcher exited before ready '+label)
            return read(ready) if ready.exists() else None
        info=wait(is_ready,100,label+' ready');w=control.ChildWitness(info['childPid']);entry['witness']=w;witnesses.append(w);entry['ready']=info
        endpoint=request('/api/sessions/'+state['id']+'/connection-endpoint');check(info['streamId']==endpoint['streamId'] and info['port']==endpoint['port'] and endpoint['address']=='127.0.0.1',label+' original endpoint / child')
        return entry
    def player(entry,room):
        state=request('/api/sessions/'+entry['sessionId']+'/players',{'playerId':str(uuid.uuid4()),'roomId':room,'name':'Portable server room '+str(room),'headset':'Quest3'},role='Room'+str(room));person=next(x for x in state['players'] if x['roomId']==room)
        invitation=request('/api/sessions/'+state['id']+'/players/'+person['id']+'/join-ticket',{},role='Room'+str(room),admission=person['admissionId']);file=runtime/(entry['label']+'-client-'+str(room)+'.json');file.write_text(json.dumps({'role':'Client','address':'127.0.0.1','port':entry['ready']['port'],'joinTicket':invitation['ticket']}),encoding='utf-8');log=runtime/(file.stem+'.log')
        child=subprocess.Popen([str(folder/'Runtime/VrCommand.exe'),'-batchmode','-nographics','-job-worker-count','2','-logFile',str(log),'--vr-config',str(file)],cwd=runtime,env=env,creationflags=subprocess.CREATE_NO_WINDOW);client={'process':child,'log':log,'player':person,'sessionId':state['id']};clients.append(client);return client
    def observe(entry,expected,begin=None):
        metadata=request('/api/sessions/'+entry['sessionId']+'/world');path='/api/sessions/'+entry['sessionId']+'/world/watch?mode=live';req=urllib.request.Request(uri+path,headers={'Authorization':'Bearer '+keys['Master']})
        with urllib.request.urlopen(req,timeout=5) as response:
            kind=''
            for _ in range(80):
                line=response.readline().decode().strip()
                if line.startswith('event: '):kind=line[7:]
                if kind=='frame' and line.startswith('data: '):
                    frame=json.loads(line[6:]);rows=frame['packet']['frame']['players'];connected={p['id'] for p in rows if p['connected'] and p['rig']['kind']=='Simulated'}
                    packet=frame['packet'];source=datetime.fromisoformat(metadata['header']['captureStartedAtUtc'])+timedelta(milliseconds=packet['elapsedMilliseconds']);age=(datetime.now(timezone.utc)-source).total_seconds()
                    if connected==set(expected) and (begin is None or packet['frame']['phase']=='Running' and packet['frame']['tick']>0 and not packet['suspended'] and packet['observedSequence']>=begin and -1<=age<1.5):save(entry['label']+('-running.json' if begin is not None else '-live.json'),{'metadata':metadata,'frame':frame,'sourceAgeSeconds':age,'acceptedBeginSequence':begin});return frame
                    return None
    def finish(entry):
        entry['process'].wait(timeout=80);w=entry['witness'];w.wait();w.close();entry['witness']=None
        report=read(entry['reportPath']);check(entry['process'].returncode==0 and report['complete'] and report['cleanupCompleted'] and report['childExited'] and report['playerResultsAcknowledged'] is None,entry['label']+' dual seal / retained36 / original process terminal')
        closed=world.analyze(entry['work']/'telemetry'/(entry['sessionId']+'.worldlog'),expected_session=entry['sessionId']);save(entry['label']+'-journal.json',closed)
        check(closed['complete'] and closed['sealed'] and closed['unacknowledgedFrames']==0 and closed['lastFrame']['worldSequence']==report['finalWorld']['acceptedSequence'],entry['label']+' closed original journal complete / sealed / exact durable tail')
        stats=request('/api/sessions/'+entry['sessionId']+'/statistics');entry['sealed']={'world':report['finalWorld'],'statistics':stats};save(entry['label']+'-statistics.json',stats)
        frames=[];req=urllib.request.Request(uri+'/api/sessions/'+entry['sessionId']+'/world/watch?mode=replay&rate=4',headers={'Authorization':'Bearer '+keys['Master']})
        with urllib.request.urlopen(req,timeout=10) as response:
            kind=''
            for raw in response:
                line=raw.decode().strip()
                if line.startswith('event: '):kind=line[7:]
                elif line.startswith('data: '):
                    value=json.loads(line[6:])
                    if kind=='frame':frames.append(value)
                    if kind=='complete':break
        check(len(frames)==report['finalWorld']['acceptedSequence'] and [x['packet']['sequence'] for x in frames]==list(range(1,len(frames)+1)) and frames[-1]['packet']['frame']['phase']=='Ended',entry['label']+' full API replay through terminal frame')
        save(entry['label']+'-replay.json',frames);rounds.append({'name':entry['label'],'ready':entry['ready'],'report':report,'journal':closed,'replayFrames':len(frames)})
    try:
        subprocess.run([str(control_exe),'--init',str(data),'--port',str(free()),'--report',str(out/'control-init.json')],env=env,check=True,timeout=30);keys=read(data/'operator-keys.json')['OperatorKeys'];marker=read(data/'control-instance.json');uri='http://127.0.0.1:'+str(marker['port'])
        api_ready=out/'control-ready.json';api_stop=out/'control-stop.request';api=subprocess.Popen([str(control_exe),'--run',str(data),'--seconds','1800','--ready-report',str(api_ready),'--stop-file',str(api_stop),'--report',str(out/'control-final.json')],env=env,cwd=out)
        info=wait(lambda:read(api_ready) if api_ready.exists() else None,40,'control startup');api_witness=control.ChildWitness(info['childPid']);check(info['status']=='ready','packaged control API without SDK on PATH');call('verify',['--verify','package'],True)
        seed=create([1],'preflight');base=config(seed['id'])
        for name,change in [('master',{'gameServerKey':keys['Master']}),('room-key',{'gameServerKey':keys['Room1']}),('client-role',{'role':'Client'}),('host-role',{'role':'Host'}),('ambiguous-ip',{'address':'127.1'}),('wildcard-advertise',{'address':'0.0.0.0'}),('multicast',{'address':'224.0.0.1'}),('overflow-port',{'port':4294975073}),('extra-key',{'masterKey':'never-pass-to-unity'}),('url-userinfo',{'managementApiUrl':uri.replace('http://','http://user@')})]:rejected(name,dict(base,**change))
        rejected('short-timeout',base,seconds=59)
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as occupied:
            occupied.bind(('127.0.0.1',0));rejected('occupied-udp',dict(base,port=occupied.getsockname()[1]))
        command(seed['id'],'End');rejected('ended-session',base)
        # Five real independent sources / five actual receiving players, then one Linked source / five receiving players.
        for linked in [False,True]:
            entries=[];round_clients=[]
            for rooms in ([[1,2,3,4,5]] if linked else [[r] for r in range(1,6)]):
                state=create(rooms,'linked' if linked else 'independent');entry=launch(state,('linked' if linked else 'room-'+str(rooms[0])));entries.append(entry)
                if not linked and rooms==[1]:rejected('bound-preparing',config(state['id']))
                for room in rooms:round_clients.append(player(entry,room))
            for entry in entries:
                ids=[c['player']['id'] for c in round_clients if c['sessionId']==entry['sessionId']];wait(lambda:observe(entry,ids),60,entry['label']+' simulated bodies');begin=command(entry['sessionId'],'Begin');wait(lambda:observe(entry,ids,begin['session']['sequence']),20,entry['label']+' original Begin applied')
            stage('running-linked' if linked else 'running-five-independent')
            time.sleep(3)
            for entry in entries:command(entry['sessionId'],'End')
            for entry in entries:finish(entry)
            for client in round_clients:
                text=client['log'].read_text(encoding='utf-8',errors='replace');check(venue.player_result_phase(text)=='acknowledged','original player result / disconnect '+client['player']['id']);finals=[json.loads(line.split('VR_CLIENT_DEBRIEF_FINAL ',1)[1]) for line in text.splitlines() if 'VR_CLIENT_DEBRIEF_FINAL ' in line];check(len(finals)==1,'one original final result '+client['player']['id']);final=finals[0];entry=next(e for e in entries if e['sessionId']==client['sessionId']);debrief.validate_result(final,{'id':entry['sessionId']},client['player'],entry['sealed']);check(True,'original admission / exact final seals / stats '+client['player']['id']);save(client['player']['id']+'-result.json',final)
                csv=request('/api/sessions/'+client['sessionId']+'/report.csv');(out/(client['player']['id']+'.csv')).write_text(csv,encoding='utf-8')
                if client['process'].poll() is None:client['process'].terminate()
                client['process'].wait(timeout=15)
        # A killed launcher must close its already-assigned Job and stop the exact owned native handle.
        crash=launch(create([1],'parent-exit'),'parent-exit');crash['process'].kill();crash['process'].wait(timeout=10);w=crash['witness'];check(w.kernel.WaitForSingleObject(w.handle,15000)==0,'parent death stops original job child');w.close();crash['witness']=None;check(not crash['reportPath'].exists(),'killed parent cannot publish success');command(crash['sessionId'],'End')
        check(all(x['state']=='Ended' for x in request('/api/sessions?includeEnded=true')),'no active management sessions')
        save('evidence.json',{'rounds':rounds,'scope':'Five same-machine independent servers / five receiving clients, then one Linked server / five receiving clients; all Simulation, not 25 simultaneous operators or LAN.'})
    except BaseException as error:stage('failed',errorType=type(error).__name__);raise
    finally:
        for client in clients:
            try:
                if client['process'].poll() is None:client['process'].terminate()
                client['process'].wait(timeout=15)
            except Exception as e:cleanup.append({'kind':'client','errorType':type(e).__name__})
        for entry in runners:
            try:
                if entry['process'].poll() is None:entry['process'].kill()
                entry['process'].wait(timeout=15)
                w=entry['witness']
                if w:
                    if w.kernel.WaitForSingleObject(w.handle,15000)!=0:raise RuntimeError('Native child still live')
                    w.close();entry['witness']=None
            except Exception as e:cleanup.append({'kind':entry['label'],'errorType':type(e).__name__})
        try:
            if api and api.poll() is None:api_stop.write_text('stop own API',encoding='utf-8');api.wait(timeout=50)
            if api_witness:api_witness.wait();api_witness.close()
        except Exception as e:cleanup.append({'kind':'api','errorType':type(e).__name__})
        save('cleanup.json',{'errors':cleanup,'remainingRunners':[e['label'] for e in runners if e['process'].poll() is None],'remainingClients':[c['player']['id'] for c in clients if c['process'].poll() is None],'apiRemaining':api is not None and api.poll() is None})
        if cleanup:raise RuntimeError('Cleanup not confirmed; do not snapshot live runtime')
        venue.snapshot_runtime(runtime,out/'runtime-snapshot')
    for file in out.glob('*.json'):
        text=file.read_text(encoding='utf-8')
        if keys and any(k in text for k in keys.values()):raise RuntimeError('Public metadata contains a key')
    save('checks.json',{'complete':True,'checks':len(checks),'findings':checks,'runtimeDirectory':str(runtime),'packageDirectory':str(folder),'scope':'Actual Windows server and control packages; same-machine Simulation only; parent-death case intentionally unsealed and not a normal finished round.'});print(json.dumps({'complete':True,'checks':len(checks),'directory':str(out)}))
if __name__=='__main__':main()
