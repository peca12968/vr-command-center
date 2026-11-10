"""Verify the actual compiled portable control launcher / self-contained API against fresh owned data."""
import argparse,ctypes,hashlib,importlib.util,json,os,secrets,shutil,socket,subprocess,time,urllib.error,urllib.request,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
package=module('control_package','package-control-server.py');venue=module('control_venue','start-desktop-venue.py')
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
class ChildWitness:
    """Hold the real started API's OS process handle; no PID-only liveness inference."""
    def __init__(self,pid,*,allow_terminate=False):
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32];self.kernel.OpenProcess.restype=ctypes.c_void_p
        self.kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32];self.kernel.WaitForSingleObject.restype=ctypes.c_uint32
        self.kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)];self.kernel.GetExitCodeProcess.restype=ctypes.c_int
        self.kernel.CloseHandle.argtypes=[ctypes.c_void_p];self.kernel.CloseHandle.restype=ctypes.c_int
        access=0x00100000|0x1000
        if allow_terminate:access|=0x0001
        self.handle=self.kernel.OpenProcess(access,False,pid)
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())
        if self.kernel.WaitForSingleObject(self.handle,0)!=258:raise RuntimeError('Expected the newly started child to be live')
    def wait(self):
        if self.kernel.WaitForSingleObject(self.handle,15000)!=0:raise RuntimeError('Original API child has not stopped')
        code=ctypes.c_uint32();assert self.kernel.GetExitCodeProcess(self.handle,ctypes.byref(code));assert code.value==0,('API exit',code.value)
    def terminate(self):
        self.kernel.TerminateProcess.argtypes=[ctypes.c_void_p,ctypes.c_uint32];self.kernel.TerminateProcess.restype=ctypes.c_int
        if self.kernel.WaitForSingleObject(self.handle,0)==258 and not self.kernel.TerminateProcess(self.handle,0):
            if self.kernel.WaitForSingleObject(self.handle,0)!=0:raise ctypes.WinError(ctypes.get_last_error())
    def close(self):
        if self.handle:self.kernel.CloseHandle(self.handle);self.handle=None
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('package',type=Path);parser.add_argument('--runtime-root',type=Path,required=True);args=parser.parse_args()
    if os.name!='nt':parser.error('Run the actual Windows launcher on Windows')
    folder=args.package.resolve();manifest=package.verify(folder);exe=folder/'Start-Control.exe';assert manifest['launcherSourceSha256']==sha(ROOT/'tools/WindowsControlLauncher/ControlLauncher.cs')
    out=ROOT/'artifacts/control-package-checks'/('run-'+uuid.uuid4().hex);out.mkdir(parents=True,exist_ok=False);runtime=args.runtime_root.resolve()/out.name;runtime.mkdir(parents=True,exist_ok=False)
    print(json.dumps({'stage':'starting','directory':str(out)}),flush=True)
    checks=[];runs=[];all_secrets=[];records=[];cleanup_errors=[]
    env=dict(os.environ);env.update(DOTNET_ROOT=str(runtime/'absent-dotnet'),DOTNET_MULTILEVEL_LOOKUP='0',PATH=os.path.join(os.environ.get('WINDIR','C:/Windows'),'System32'),ControlPipeToken=secrets.token_hex(32),OperatorKeys__Master=secrets.token_hex(32),DataDirectory=str(runtime/'forbidden-missions'),SessionDataDirectory=str(runtime/'forbidden-sessions'))
    def check(value,label):
        if not value:raise AssertionError(label)
        checks.append(label);print('PASS: '+label,flush=True)
    def call(label,options,success=True,runner=exe,report=None):
        report=report or out/(label+'.json');result=subprocess.run([str(runner),*map(str,options),'--report',str(report)],env=env,cwd=out,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=50)
        value=read(report) if report.exists() else None
        check(result.returncode==(0 if success else 1),label+' exit')
        if value:check(value['status'] in (('verified','initialized') if success else ('rejected',)),label+' report')
        return value
    def port():
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));return probe.getsockname()[1]
    def initialize(name,p=None):
        data=runtime/name;call('init-'+name,['--init',data,'--port',p or port()]);keys=read(data/'operator-keys.json')['OperatorKeys'];all_secrets.extend(keys.values());check(set(keys)==set(package_roles) and len(set(keys.values()))==7,'seven distinct roles: '+name);return data,keys
    def start(data,name):
        ready=out/(name+'-ready.json');final=out/(name+'-final.json');stop=out/(name+'-stop.request')
        child=subprocess.Popen([str(exe),'--run',str(data),'--seconds','180','--ready-report',str(ready),'--stop-file',str(stop),'--report',str(final)],env=env,cwd=out,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        entry={'process':child,'name':name,'ready':ready,'final':final,'stop':stop,'witness':None};runs.append(entry);deadline=time.monotonic()+35
        while not ready.exists():
            if child.poll() is not None:raise RuntimeError('Owned launcher exited before ready: '+name)
            if time.monotonic()>deadline:raise RuntimeError('Owned launcher readiness timeout: '+name)
            time.sleep(.05)
        info=read(ready);check(info['status']=='ready' and Path(info['runtimeCoreClr']).resolve()==(folder/'Runtime/coreclr.dll').resolve(),'actual packaged coreclr loaded: '+name)
        entry['witness']=ChildWitness(info['childPid']);entry['info']=info;return entry
    def stop(entry):
        entry['stop'].write_text('stop requested',encoding='utf-8');entry['process'].wait(timeout=50);entry['witness'].wait();entry['witness'].close();entry['witness']=None
        value=read(entry['final']);check(entry['process'].returncode==0 and value['complete'] and value['graceful'] and value['childExited'] and value['exitCode']==0,'graceful original API / launcher exit: '+entry['name']);records.append({'name':entry['name'],'ready':entry['info'],'final':value})
    def request(entry,keys,path,body=None,role='Master',expected=200):
        headers={} if role is None else {'Authorization':'Bearer '+keys[role]}
        if body is not None:headers['Content-Type']='application/json'
        req=urllib.request.Request(entry['info']['uri']+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=5) as response:status=response.status;raw=response.read();response_headers=dict(response.headers)
        except urllib.error.HTTPError as error:status=error.code;raw=error.read();response_headers=dict(error.headers)
        if status!=expected:raise RuntimeError(path+' unexpected status '+str(status))
        if path=='/console/':return raw.decode('utf-8'),response_headers
        return json.loads(raw) if raw else None
    package_roles=['Master','Room1','Room2','Room3','Room4','Room5','GameServer']
    try:
        call('verify',['--verify'])
        for name,bad in [('wildcard','0.0.0.0'),('url','http://127.0.0.1'),('alias','127.1'),('leading-zero','127.0.0.01'),('multicast','224.0.0.1'),('foreign','192.0.2.250')]:call(name,['--init',runtime/('invalid-'+name),'--bind',bad],False)
        for name,bad in [('port-low','1023'),('port-high','65536'),('port-bool','true')]:call(name,['--init',runtime/('invalid-'+name),'--port',bad],False)
        forbidden=folder/'unexpected-report.json';call('report-in-package',['--verify'],False,report=forbidden);check(not forbidden.exists(),'invalid output path cannot create a file inside the package')
        call('unknown-option',['--verify','--unknown','value'],False)
        data,keys=initialize('instance');marker_hash=sha(data/'control-instance.json');key_hash=sha(data/'operator-keys.json')
        call('existing-data',['--init',data],False);check(sha(data/'control-instance.json')==marker_hash and sha(data/'operator-keys.json')==key_hash,'existing instance / keys preserved on rejected init')
        for name,value in [('duration-low','0'),('duration-high','3601'),('duration-bool','true')]:call(name,['--run',data,'--seconds',value,'--ready-report',out/(name+'-ready.json')],False)
        alias=out/'alias-report.json';call('report-alias',['--run',data,'--seconds','1','--ready-report',str(alias).upper()],False,report=alias)
        entry=start(data,'first');check(request(entry,keys,'/')['version']=='0.31.0','actual portable API version');request(entry,keys,'/api/rooms',role=None,expected=401);check(True,'anonymous management requests rejected')
        html,headers=request(entry,keys,'/console/',role=None);check(manifest.get('consoleVersion')=='0.31.77' and 'v0.31.77' in html and "script-src 'self'" in headers['Content-Security-Policy'],'published current console served with original CSP and explicit UI version')
        for role in package_roles:check(request(entry,keys,'/api/me',role=role)['role']==('RoomController' if role.startswith('Room') else role),'actual isolated role identity: '+role)
        markers = [{'room': {'x': x, 'z': z}, 'tracking': {'x': -z - 3, 'z': x - 1}} for x, z in [(-2, -2), (2, -2), (-2, 2)]]
        alignment_input = {'roomId': 5, 'markers': markers}
        alignment = request(entry, keys, '/api/room-alignment', alignment_input)
        request(entry, keys, '/api/room-alignment', alignment_input, role='Room5', expected=403)
        check(alignment['withinTolerance'] and alignment['yawDegrees'] == 90 and alignment['roomOrigin'] == {'x': 28, 'z': 0},
              'packaged API solves the original room coordinates and keeps Master alignment permission')
        call('concurrent',['--run',data,'--seconds','1','--ready-report',out/'concurrent-ready.json'],False);check(not (out/'concurrent-ready.json').exists() and entry['process'].poll() is None,'second instance runner rejected without displacing the original API')
        mission=request(entry,keys,'/api/missions',{'name':'Portable control persistence','briefing':'Fresh management-only fixture','durationSeconds':600,'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},'enemies':{'count':0,'behavior':'Hold','autoAttack':False},'props':[]},expected=201)
        request(entry,keys,'/api/missions',mission['definition'],role='Room1',expected=403);check(True,'room controller cannot author missions')
        sessions=[]
        for room in range(1,6):
            session=request(entry,keys,'/api/sessions',{'missionId':mission['id'],'mode':'Independent','roomIds':[room]},role='Room'+str(room),expected=201)
            for seat in range(5):session=request(entry,keys,f'/api/sessions/{session["id"]}/players',{'playerId':str(uuid.uuid4()),'roomId':room,'name':'Portable seat '+str(seat),'headset':'Quest3'},role='Room'+str(room))
            sessions.append(session)
        check(sum(len(s['players']) for s in sessions)==25,'five independent API rosters accept 25 distinct admissions (not game connections)')
        overview=request(entry,keys,'/api/sessions/'+sessions[0]['id']+'/overview',role='Room1')
        check(overview['session']==sessions[0]
              and overview['statistics']['throughSequence']==overview['recentEvents'][-1]['sequence']==sessions[0]['sequence']
              and {row['playerId'] for row in overview['statistics']['players']}=={row['id'] for row in sessions[0]['players']},
              'packaged room overview matches its original roster and one event revision')
        for room in range(1,6):check([s['id'] for s in request(entry,keys,'/api/sessions',role='Room'+str(room))]==[sessions[room-1]['id']],'room list isolation: '+str(room))
        request(entry,keys,'/api/sessions/'+sessions[1]['id'],role='Room1',expected=403);request(entry,keys,'/api/sessions',{'missionId':mission['id'],'mode':'Linked','roomIds':[1,2,3,4,5]},expected=409);check(True,'foreign room access and overlapping Linked creation rejected')
        signing_hash=sha(data/'player-ticket-signing.key');stop(entry);entry=start(data,'reopened')
        after=[request(entry,keys,'/api/sessions/'+s['id']) for s in sessions];check(after==sessions,'normal API reopen recovers the same Preparing sessions / sequence / all original admissions')
        check(request(entry,keys,'/api/missions/'+mission['id'])==mission and sha(data/'operator-keys.json')==key_hash and sha(data/'player-ticket-signing.key')==signing_hash,'mission and both credential / ticket keys retained across owned-instance reopen')
        for session in after:request(entry,keys,'/api/sessions/'+session['id']+'/commands',{'commandId':str(uuid.uuid4()),'action':'End'})
        linked=request(entry,keys,'/api/sessions',{'missionId':mission['id'],'mode':'Linked','roomIds':[1,2,3,4,5]},expected=201)
        request(entry,keys,'/api/sessions/'+linked['id']+'/commands',{'commandId':str(uuid.uuid4()),'action':'End'});check(request(entry,keys,'/api/sessions')==[],'normal End frees rooms for a later Linked management session; final active zero')
        stop(entry);check(not (runtime/'forbidden-missions').exists() and not (runtime/'forbidden-sessions').exists(),'inherited data paths and role keys cannot redirect the owned API')
        crash_data,crash_keys=initialize('parent-exit');crash=start(crash_data,'parent-exit');crash['process'].kill();crash['process'].wait(timeout=5);crash['witness'].wait();crash['witness'].close();crash['witness']=None
        check(not crash['final'].exists(),'terminated launcher cannot claim a normal final report; owned API exits on pipe EOF')
        with socket.socket() as blocker:
            blocker.bind(('127.0.0.1',0));blocker.listen();blocked,_=initialize('occupied-port',blocker.getsockname()[1]);call('occupied-port',['--run',blocked,'--seconds','1','--ready-report',out/'occupied-ready.json'],False);check(not (out/'occupied-ready.json').exists(),'foreign listening socket never counts as owned API readiness')
        broken=out/'broken'/package.TOP;broken.mkdir(parents=True);shutil.copyfile(exe,broken/'Start-Control.exe');bad=json.loads(json.dumps(manifest));bad['files'][0]['path']='../outside';(broken/'control-package.json').write_text(json.dumps(bad),encoding='utf-8');call('bad-manifest',['--verify'],False,runner=broken/'Start-Control.exe')
        for path in out.glob('*.json'):
            text=path.read_text(encoding='utf-8');check(not any(secret in text for secret in all_secrets),'diagnostic contains no generated role key: '+path.name)
        package.verify(folder)
    finally:
        for run in runs:
            try:
                if run['process'].poll() is None:run['stop'].write_text('cleanup requested',encoding='utf-8');run['process'].wait(timeout=50)
                if run['witness']:run['witness'].wait();run['witness'].close();run['witness']=None
            except Exception as error:cleanup_errors.append({'name':run['name'],'errorType':type(error).__name__})
        (out/'cleanup.json').write_text(json.dumps({'errors':cleanup_errors,'remainingRunnerChildren':[r['name'] for r in runs if r['process'].poll() is None]},indent=2),encoding='utf-8')
        if cleanup_errors:raise RuntimeError('Preserve runtime: original child cleanup not confirmed')
        venue.snapshot_runtime(runtime,out/'runtime-snapshot')
    result={'complete':True,'checks':len(checks),'findings':checks,'runs':records,'runtimeDirectory':str(runtime),'packageDirectory':str(folder),'scope':'Actual packaged Windows API / private launcher / management roster persistence only. No Unity server/client, gameplay capacity, clean-machine install, LAN, headset or GPU acceptance.'}
    (out/'checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');(ROOT/'artifacts/control-package-checks-latest-path.txt').write_text(str(out),encoding='utf-8');print(json.dumps({'complete':True,'checks':len(checks),'directory':str(out)}))
if __name__=='__main__':main()
