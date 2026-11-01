"""Prepare an isolated API, then observe real server GUI selection/start/seal/close. No UI input."""
import argparse,importlib.util,json,os,shutil,socket,subprocess,time,urllib.error,urllib.request,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
checks=module('gui_server_checks','check-control-package.py');venue=module('gui_server_venue','start-desktop-venue.py');world=module('gui_server_world','analyze-world-journal.py');package=module('gui_server_package','package-windows-server.py')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def free(kind=socket.SOCK_STREAM):
    with socket.socket(socket.AF_INET,kind) as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path);p.add_argument('--control-package',type=Path,required=True);p.add_argument('--runtime-root',type=Path,required=True);args=p.parse_args()
    folder=args.package.resolve();manifest=package.verify(folder);assert manifest['launcherSourceSha256']==package.digest(ROOT/'tools/WindowsServerLauncher/ServerLauncher.cs')
    out=ROOT/'artifacts/server-gui'/('run-'+uuid.uuid4().hex);out.mkdir(parents=True,exist_ok=False);runtime=args.runtime_root.resolve()/out.name;runtime.mkdir(parents=True,exist_ok=False);data=runtime/'control';port=free(socket.SOCK_DGRAM);api=None;api_witness=None;gui=None;witness=None;errors=[];observed=None;stopped=False;gui_report=None;gui_work=None;session=None;result=None;other_session=None
    reports=Path(os.environ['LOCALAPPDATA'])/'VrCommand/GameServerReports';old=set(reports.glob('*.json')) if reports.exists() else set()
    def save(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    def stage(value,**extra):save('stage.json',{'stage':value,**extra});print(json.dumps({'stage':value,'directory':str(out),**extra}),flush=True)
    (ROOT/'artifacts/server-gui-latest-path.txt').write_text(str(out),encoding='utf-8');exe=args.control_package.resolve()/'Start-Control.exe';stop=out/'api-stop.request';ready=out/'api-ready.json'
    def request(path,body=None,optional=False):
        req=urllib.request.Request(uri+path,data=None if body is None else json.dumps(body).encode(),headers={'Authorization':'Bearer '+keys['Master'],'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=5) as response:return json.load(response)
        except urllib.error.HTTPError as e:
            if optional and e.code==404:return None
            raise
    try:
        subprocess.run([str(exe),'--init',str(data),'--port',str(free()),'--report',str(out/'init.json')],check=True,timeout=30);marker=read(data/'control-instance.json');keys=read(data/'operator-keys.json')['OperatorKeys'];uri='http://127.0.0.1:'+str(marker['port'])
        api=subprocess.Popen([str(exe),'--run',str(data),'--seconds','600','--ready-report',str(ready),'--stop-file',str(stop),'--report',str(out/'api-final.json')]);deadline=time.monotonic()+40
        while not ready.exists():
            if api.poll() is not None or time.monotonic()>deadline:raise RuntimeError('API did not become ready')
            time.sleep(.05)
        api_witness=checks.ChildWitness(read(ready)['childPid']);original={name:checks.sha(data/name) for name in ['control-instance.json','operator-keys.json','player-ticket-signing.key']}
        mission=request('/api/missions',{'name':'GUI server fixture','briefing':'No GUI credential creation or player input','durationSeconds':600,'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},'enemies':{'count':1,'behavior':'Hold','autoAttack':False},'props':[]});session=request('/api/sessions',{'missionId':mission['id'],'mode':'Independent','roomIds':[1]})['id']
        other_session=request('/api/sessions',{'missionId':mission['id'],'mode':'Independent','roomIds':[2]})['id']
        gui=subprocess.Popen([str(folder/'Launch-Server.exe')],cwd=runtime);stage('select-instance',guiPid=gui.pid,instance=str(data/'control-instance.json'),sessionId=session,udpPort=port)
        powershell=Path(os.environ['WINDIR'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
        def children():
            script='$rows = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = '+str(gui.pid)+'" | Where-Object { $_.Name -eq "VrCommand.exe" } | ForEach-Object { [pscustomobject]@{ pid = $_.ProcessId; image = $_.ExecutablePath } }); ConvertTo-Json -InputObject $rows -Compress'
            done=subprocess.run([str(powershell),'-NoProfile','-NonInteractive','-Command',script],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10,check=True);return json.loads(done.stdout.decode('utf-8-sig'))
        deadline=time.monotonic()+360;commanded=False;begin=None
        while gui.poll() is None:
            if time.monotonic()>deadline:raise RuntimeError('GUI run exceeded360seconds')
            if observed is None:
                endpoint=request('/api/sessions/'+session+'/connection-endpoint',optional=True)
                if endpoint:
                    rows=children()
                    if len(rows)!=1 or Path(rows[0]['image']).resolve()!=(folder/'Runtime/VrCommand.exe').resolve():raise RuntimeError('Unexpected GUI-owned native child')
                    if endpoint['port']!=port or endpoint['address']!='127.0.0.1':raise RuntimeError('GUI did not publish the selected endpoint')
                    witness=checks.ChildWitness(rows[0]['pid']);observed={'child':rows[0],'endpoint':endpoint};save('native-observed.json',observed);stage('server-ready',guiPid=gui.pid,childPid=rows[0]['pid'])
            elif not commanded and (out/'gui-started.review.json').exists():
                review=read(out/'gui-started.review.json')
                if review!={'selected':True,'started':True}:raise RuntimeError('GUI start was not visually verified')
                begin=request('/api/sessions/'+session+'/commands',{'commandId':str(uuid.uuid4()),'action':'Begin'});save('begin.json',begin)
                sequence=begin['session']['sequence'];deadline_running=time.monotonic()+20;running=None
                while time.monotonic()<deadline_running and running is None:
                    req=urllib.request.Request(uri+'/api/sessions/'+session+'/world/watch?mode=live',headers={'Authorization':'Bearer '+keys['Master']})
                    with urllib.request.urlopen(req,timeout=5) as response:
                        kind=''
                        for _ in range(40):
                            line=response.readline().decode().strip()
                            if line.startswith('event: '):kind=line[7:]
                            if kind=='frame' and line.startswith('data: '):
                                value=json.loads(line[6:]);packet=value['packet']
                                if packet['frame']['phase']=='Running' and packet['frame']['tick']>0 and not packet['suspended'] and packet['observedSequence']>=sequence:running=value
                                break
                if running is None:raise RuntimeError('Original GUI native source did not apply Begin')
                save('running.json',running);time.sleep(3);end=request('/api/sessions/'+session+'/commands',{'commandId':str(uuid.uuid4()),'action':'End'});save('end.json',end);commanded=True;stage('waiting-seal-retention',guiPid=gui.pid)
            if observed and not stopped and witness.kernel.WaitForSingleObject(witness.handle,0)==0:
                witness.wait();witness.close();witness=None;stopped=True;stage('native-stopped-close-gui',guiPid=gui.pid)
            time.sleep(.2)
        gui.wait(timeout=5)
        if gui.returncode!=0 or not observed or not stopped:raise RuntimeError('GUI start / native seal-stop / close not completed')
        candidates=[]
        for file in set(reports.glob('*.json'))-old:
            value=read(file)
            if value.get('sessionId')==session and value.get('childPid')==observed['child']['pid']:candidates.append((file,value))
        if len(candidates)!=1:raise RuntimeError('Expected exactly one GUI report for original child / session')
        report_path,gui_report=candidates[0];save('gui-final.json',gui_report)
        if not gui_report['complete'] or not gui_report['childExited'] or not gui_report['cleanupCompleted'] or gui_report['status']!='sealed-stopped':raise RuntimeError('GUI lifecycle did not finish normally')
        gui_work=Path(gui_report['workDirectory']);closed=world.analyze(gui_work/'telemetry'/(session+'.worldlog'),expected_session=session);save('closed-journal.json',closed)
        if not closed['sealed'] or not closed['complete'] or closed['unacknowledgedFrames']!=0 or closed['lastFrame']['worldSequence']!=gui_report['finalWorld']['acceptedSequence']:raise RuntimeError('Original GUI journal tail differs')
        if any(checks.sha(data/name)!=sha for name,sha in original.items()):raise RuntimeError('GUI changed existing instance keys or marker')
        review_path=out/'gui-closed.review.json';review_deadline=time.monotonic()+30
        while not review_path.exists():
            if time.monotonic()>review_deadline:raise RuntimeError('GUI close review was not supplied after actual GUI exit')
            time.sleep(.05)
        if read(review_path)!={'stopped':True,'closed':True}:raise RuntimeError('GUI close was not visually verified')
        result={'complete':True,'guiPid':gui.pid,'guiExitCode':gui.returncode,'native':observed,'guiReport':str(report_path),'originalFileHashes':original,'journal':closed,'scope':'Actual GUI select existing instance / set UDP port / start / API fixture Begin-End / sealed retained36 stop / close. No GUI key creation, player actions, delivery, LAN or headset proof.'}
    except BaseException as e:stage('failed',errorType=type(e).__name__);raise
    finally:
        try:
            if api and api.poll() is None:
                for own_session in [session,other_session]:
                    if own_session and request('/api/sessions/'+own_session)['state']!='Ended':request('/api/sessions/'+own_session+'/commands',{'commandId':str(uuid.uuid4()),'action':'End'})
        except Exception as e:errors.append({'kind':'end','errorType':type(e).__name__})
        try:
            if gui and gui.poll() is None:gui.terminate();gui.wait(timeout=10)
            if witness:
                if witness.kernel.WaitForSingleObject(witness.handle,15000)!=0:raise RuntimeError('Original GUI child is still live')
                witness.close();witness=None
            if gui and children():raise RuntimeError('Unobserved GUI child remains')
        except Exception as e:errors.append({'kind':'gui','errorType':type(e).__name__})
        try:
            if api and api.poll() is None:stop.write_text('stop own API',encoding='utf-8');api.wait(timeout=50)
            if api_witness:api_witness.wait();api_witness.close()
        except Exception as e:errors.append({'kind':'api','errorType':type(e).__name__})
        save('cleanup.json',{'errors':errors,'remainingGui':bool(gui and gui.poll() is None),'remainingApiRunner':bool(api and api.poll() is None)})
        if errors:raise RuntimeError('Cleanup not confirmed; no snapshot')
        if gui_work:shutil.copytree(gui_work,runtime/'gui-server');shutil.copyfile(report_path,runtime/'gui-report.json')
        venue.snapshot_runtime(runtime,out/'runtime-snapshot')
    save('checks.json',result);stage('passed')
if __name__=='__main__':main()
