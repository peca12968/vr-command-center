"""Actual compiled Framework catalog/state checks against fresh owned management data; no UI input."""
import argparse,hashlib,importlib.util,json,os,shutil,socket,subprocess,sys,time,urllib.error,urllib.request,uuid
from contextlib import contextmanager
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from windows_firewall import WindowsFirewallLaunchError, require_silent_windows_launch
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
control=module('catalog_control','check-control-package.py');package=module('catalog_package','package-windows-server.py');venue=module('catalog_venue','start-desktop-venue.py')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

@contextmanager
def held_catalog(port, folder):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path not in ('/', '/api/me', '/api/sessions'):
                self.send_error(404)
                return
            if self.path == '/api/sessions':
                mode = (folder/'mode').read_text()
                (folder/'entered').touch()
                until = time.monotonic() + 4
                while not (folder/'release').exists():
                    if time.monotonic() >= until:
                        self.send_error(504)
                        return
                    time.sleep(.01)
                if mode == 'failure':
                    self.send_error(503)
                    return
            connection = HTTPConnection('127.0.0.1', port, timeout=3)
            try:
                connection.request('GET', self.path, headers={'Authorization': self.headers['Authorization']})
                upstream = connection.getresponse()
                body = upstream.read()
                self.send_response(upstream.status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass  # The owned window may close while the last reply is held.
            finally:
                connection.close()

    with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
        server.daemon_threads = False
        worker = Thread(target=server.serve_forever, kwargs={'poll_interval': .05})
        worker.start()
        try:
            yield server.server_port
        finally:
            (folder/'release').touch()
            server.shutdown()
            worker.join(3)
            assert not worker.is_alive()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path);p.add_argument('--control-package',type=Path,required=True);p.add_argument('--runtime-root',type=Path,required=True);args=p.parse_args()
    if os.name!='nt':p.error('Actual Framework compiler/process checks require Windows')
    folder=args.package.resolve();manifest=package.verify(folder);assert manifest['launcherSourceSha256']==sha(ROOT/'tools/WindowsServerLauncher/ServerLauncher.cs');control.package.verify(args.control_package)
    try:
        require_silent_windows_launch(args.control_package / 'Runtime/VrCommand.Api.exe')
        require_silent_windows_launch(sys.executable)
    except WindowsFirewallLaunchError as error:
        p.exit(2, f'{error}\n')
    out=ROOT/'artifacts/server-catalog'/('run-'+uuid.uuid4().hex);out.mkdir(parents=True,exist_ok=False);runtime=args.runtime_root.resolve()/out.name;runtime.mkdir(parents=True,exist_ok=False);data=runtime/'control';exe=folder/'Launch-Server.exe';api=None;witness=None;errors=[];checks=[];sessions=[]
    def save(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    def check(ok,name):
        if not ok:raise AssertionError(name)
        checks.append(name);print('PASS: '+name,flush=True)
    def request(path,body=None,role='Master'):
        req=urllib.request.Request(uri+path,data=None if body is None else json.dumps(body).encode(),headers={'Authorization':'Bearer '+keys[role],'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=5) as response:return json.load(response)
    def catalog(name,marker=None,success=True,report=None,extra=()):
        report=report or out/(name+'.json');existed=report.exists();run=subprocess.run([str(exe),'--catalog',str(marker or data/'control-instance.json'),*map(str,extra),'--report',str(report)],cwd=out,timeout=45)
        check(run.returncode==(0 if success else 1),name+' actual exit');return read(report) if report.exists() and not existed else None
    print(json.dumps({'stage':'starting','directory':str(out)}),flush=True);(ROOT/'artifacts/server-catalog-latest-path.txt').write_text(str(out),encoding='utf-8');ready=out/'api-ready.json';stop=out/'api-stop.request';controller=args.control_package.resolve()/'Start-Control.exe'
    try:
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        subprocess.run([str(controller),'--init',str(data),'--port',str(port),'--report',str(out/'init.json')],check=True,timeout=30);keys=read(data/'operator-keys.json')['OperatorKeys'];uri='http://127.0.0.1:'+str(port)
        api=subprocess.Popen([str(controller),'--run',str(data),'--seconds','300','--ready-report',str(ready),'--stop-file',str(stop),'--report',str(out/'api-final.json')]);deadline=time.monotonic()+40
        while not ready.exists():
            if api.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Owned API startup not confirmed')
            time.sleep(.05)
        witness=control.ChildWitness(read(ready)['childPid']);check(catalog('empty')['sessions']==[],'empty list is a completed read, not server readiness')
        for room in [1,2]:
            mission=request('/api/missions',{'name':'任務 '+str(room)+' & <辨識>','briefing':'Catalog metadata only','durationSeconds':600,'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},'enemies':{'count':1,'behavior':'Hold','autoAttack':False},'props':[]});state=request('/api/sessions',{'missionId':mission['id'],'mode':'Independent','roomIds':[room]});sessions.append(state['id'])
        before={sid:request('/api/sessions/'+sid) for sid in sessions};listing=catalog('two-rooms');check([x['id'] for x in listing['sessions']]==sessions,'catalog keeps exact room-ordered session IDs');check(all(x['missionId']==before[x['id']]['mission']['id'] and '房間 '+str(x['roomIds'][0]) in x['display'] and x['missionName'] in x['display'] for x in listing['sessions']),'catalog carries exact mission version and readable labels')
        check(all(request('/api/sessions/'+sid)==state for sid,state in before.items()),'catalog GETs do not reserve or mutate sessions')
        original={name:sha(data/name) for name in ['operator-keys.json','control-instance.json']};proof=runtime/'proof';proof.mkdir()
        for source in [ROOT/'tools/WindowsServerLauncher/ServerLauncher.cs',ROOT/'tools/WindowsServerLauncher/Tests/CatalogProof.cs']:shutil.copyfile(source,proof/source.name)
        descriptor=runtime/'proof-private.json';delayed=runtime/'delayed';delayed.mkdir()
        delayed_instance=delayed/'control-instance.json'
        shutil.copyfile(data/'operator-keys.json',delayed/'operator-keys.json')
        compiler=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
        with (proof/'compile.log').open('xb') as log:subprocess.run([str(compiler),'/nologo','/warnaserror','/codepage:65001','/target:exe','/platform:x64','/main:ServerCatalogProof','/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Web.Extensions.dll','/out:'+str(proof/'CatalogProof.exe'),str(proof/'ServerLauncher.cs'),str(proof/'CatalogProof.cs')],stdout=log,stderr=subprocess.STDOUT,check=True)
        with held_catalog(port, delayed) as relay_port:
            delayed_instance.write_text(json.dumps(dict(read(data/'control-instance.json'),port=relay_port)),encoding='utf-8')
            descriptor.write_text(json.dumps({'instance':str(data/'control-instance.json'),'masterKey':keys['Master'],
                                              'delayedInstance':str(delayed_instance)}),encoding='utf-8')
            result=subprocess.run([str(proof/'CatalogProof.exe'),str(descriptor),str(out/'framework-proof.json')],timeout=60)
        values=read(out/'framework-proof.json');check(result.returncode==0 and values['complete'],'actual Framework parser, selection state and responsive WinForms catalog');check(all(sha(data/name)==h for name,h in original.items()),'proof restores its own private test marker / credentials exactly')
        remaining=catalog('after-end');check([x['id'] for x in remaining['sessions']]==sessions[1:],'Ended original is absent without selecting a replacement')
        for room in [1,3,4,5]:
            state=request('/api/sessions',{'missionId':before[sessions[1]]['mission']['id'],'mode':'Independent','roomIds':[room]});sessions.append(state['id'])
        five=catalog('five-independent');check([x['roomIds'] for x in five['sessions']]==[[r] for r in range(1,6)] and {x['id'] for x in five['sessions']}==set(sessions[1:]),'five actual independent rooms keep all original identities')
        for sid in sessions[1:]:request('/api/sessions/'+sid+'/commands',{'commandId':str(uuid.uuid4()),'action':'End'})
        linked=request('/api/sessions',{'missionId':before[sessions[1]]['mission']['id'],'mode':'Linked','roomIds':[1,2,3,4,5]});sessions.append(linked['id']);whole=catalog('linked');check(len(whole['sessions'])==1 and whole['sessions'][0]['id']==linked['id'] and whole['sessions'][0]['mode']=='Linked' and whole['sessions'][0]['roomIds']==[1,2,3,4,5],'actual Linked source is one clearly labelled five-room choice')
        stream=str(uuid.uuid4());request('/api/sessions/'+linked['id']+'/combat-stream',{'streamId':stream,'origin':'Simulation'},role='GameServer');check(catalog('bound-source')['sessions']==[],'bound actual source is not offered again')
        request('/api/sessions/'+linked['id']+'/commands',{'commandId':str(uuid.uuid4()),'action':'End'});request('/api/sessions/'+linked['id']+'/combat-stream/seal',{'streamId':stream,'finalSequence':0},role='GameServer')
        mr_mission=request('/api/missions',{'name':'MR catalog test','briefing':'Owned catalog fixture','durationSeconds':600,'environment':{'mode':'MR','weather':'Clear','timeOfDay':'Day','lightning':False},'enemies':{'count':0,'behavior':'Hold','autoAttack':False},'props':[]})
        for mode,rooms in [('Independent',[1]),('Linked',[1,2,3,4,5])]:
            label='mr-'+mode.lower()
            mr=request('/api/sessions',{'missionId':mr_mission['id'],'mode':mode,'roomIds':rooms});sessions.append(mr['id'])
            route='/api/sessions/'+mr['id'];choices=catalog(label+'-unlocked')['sessions']
            check(len(choices)==1 and choices[0]['id']==mr['id'] and choices[0]['experienceMode']=='MR'
                  and choices[0]['canStart'] is False and choices[0]['missingAlignmentRoomIds']==rooms and '待鎖定校正' in choices[0]['display'],
                  mode+' retains the exact MR choice and lists all missing locks')
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as udp:udp.bind(('127.0.0.1',0));game_port=udp.getsockname()[1]
            work=runtime/(label+'-work');config=runtime/(label+'-private.json');ready_report=out/(label+'-ready.json');run_report=out/(label+'-run.json')
            config.write_text(json.dumps({'role':'Server','managementApiUrl':uri,'gameServerKey':keys['GameServer'],
                'sessionId':mr['id'],'address':'127.0.0.1','listenAddress':'127.0.0.1','port':game_port}),encoding='utf-8')
            rejected=subprocess.run([str(exe),'--run',str(config),'--work',str(work),'--seconds','60',
                '--ready-report',str(ready_report),'--report',str(run_report)],cwd=out,timeout=45)
            failure=read(run_report)
            check(rejected.returncode==1 and failure['complete'] is False and failure['childPid'] is None and failure['streamId'] is None
                  and '尚無有效的校正鎖定' in failure['error'] and not work.exists() and not ready_report.exists() and request(route)==mr,
                  mode+' direct CLI refuses before child, work, readiness or source changes')
            markers=[{'room':{'x':x,'z':z},'tracking':{'x':x,'z':z}} for x,z in [(-2,-2),(2,-2),(-2,2)]]
            pins={f'room{room}':hashlib.sha256(json.dumps(request('/api/room-alignment',{'roomId':room,'markers':markers})).encode()).hexdigest() for room in rooms}
            locked=request(route+'/commands',{'commandId':str(uuid.uuid4()),'action':'SetRoomAlignment','roomAlignment':pins})['session']
            after=catalog(label+'-locked')['sessions']
            check(len(after)==1 and after[0]['id']==mr['id'] and after[0]['missionId']==choices[0]['missionId']
                  and after[0]['canStart'] is True and after[0]['missingAlignmentRoomIds']==[] and '待鎖定校正' not in after[0]['display']
                  and all(value not in json.dumps(after) for value in pins.values()) and request(route)==locked,
                  mode+' refresh exposes the same locked session without returning hashes or altering state')
            request(route+'/commands',{'commandId':str(uuid.uuid4()),'action':'End'})
        bad=catalog('wrong-file',runtime/'not-an-instance.json',False);check(not bad['complete'],'invalid source cannot create a completed catalog')
        illegal=data/'forbidden-report.json';catalog('inside-data',success=False,report=illegal);check(not illegal.exists(),'catalog output cannot write into instance data')
        catalog('mixed-options',success=False,extra=['--unknown','value']);existing=out/'existing.json';existing.write_text('preserve',encoding='utf-8');catalog('existing-report',success=False,report=existing);check(existing.read_text(encoding='utf-8')=='preserve','existing report never overwritten')
        for file in out.glob('*.json'):
            check(not any(key in file.read_text(encoding='utf-8') for key in keys.values()),'public metadata excludes generated keys: '+file.name)
        save('evidence.json',{'frameworkChecks':values['checks'],'initial':listing,'afterEnd':remaining,'fiveIndependent':five,'linked':whole,'scope':'Real readonly catalog, pre-child CLI rejection, and compiled production state / parser. Test fixtures pin and end their own sessions.'})
    finally:
        for sid in sessions:
            try:
                if api and api.poll() is None and request('/api/sessions/'+sid)['state']!='Ended':request('/api/sessions/'+sid+'/commands',{'commandId':str(uuid.uuid4()),'action':'End'})
            except Exception as e:errors.append({'kind':'end','errorType':type(e).__name__})
        try:
            if api and api.poll() is None:stop.write_text('stop own API',encoding='utf-8');api.wait(timeout=50)
            if witness:witness.wait();witness.close()
        except Exception as e:errors.append({'kind':'api','errorType':type(e).__name__})
        save('cleanup.json',{'errors':errors,'apiRemaining':bool(api and api.poll() is None)})
        if errors:raise RuntimeError('Do not snapshot until actual owned API cleanup is confirmed')
        venue.snapshot_runtime(runtime,out/'runtime-snapshot')
    save('checks.json',{'complete':True,'checks':len(checks),'frameworkChecks':values['checks'],'findings':checks,'runtimeDirectory':str(runtime),'scope':'Fresh owned API, WinForms message loop and catalog CLI; no desktop input, Unity, LAN or headset claim.'});print(json.dumps({'complete':True,'checks':len(checks),'frameworkChecks':values['checks'],'directory':str(out)}))
if __name__=='__main__':main()
