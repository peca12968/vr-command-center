"""Prepare an owned instance, then observe actual GUI select / start / stop / close actions. Never sends UI input."""
import argparse,importlib.util,json,os,secrets,socket,subprocess,sys,time,urllib.request,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
checks=module('control_gui_checks','check-control-package.py');venue=module('control_gui_venue','start-desktop-venue.py')
def main():
    from windows_firewall import WindowsFirewallLaunchError, require_silent_windows_launch, start_checked_windows_process

    p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path);p.add_argument('--runtime-root',type=Path,required=True);args=p.parse_args()
    if os.name!='nt':p.error('Windows GUI evidence only')
    folder=args.package.resolve();checks.package.verify(folder);exe=folder/'Start-Control.exe'
    api_exe = folder / 'Runtime/VrCommand.Api.exe'
    try:
        require_silent_windows_launch(sys.executable)
        require_silent_windows_launch(api_exe)
        require_silent_windows_launch(exe)
    except WindowsFirewallLaunchError as error:
        p.exit(2, f'{error}\n')
    out=ROOT/'artifacts/control-gui'/('run-'+uuid.uuid4().hex);out.mkdir(parents=True,exist_ok=False);runtime=args.runtime_root.resolve()/out.name;runtime.mkdir(parents=True,exist_ok=False);data=runtime/'instance'
    def save(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    def stage(value,**extra):save('stage.json',{'stage':value,**extra});print(json.dumps({'stage':value,'directory':str(out),**extra}),flush=True)
    (ROOT/'artifacts/control-gui-latest-path.txt').write_text(str(out),encoding='utf-8')
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    subprocess.run([str(exe),'--init',str(data),'--port',str(port),'--report',str(out/'init.json')],check=True,timeout=30)
    ready=out/'warm-ready.json';final=out/'warm-final.json';stop=out/'warm-stop.request';warm=None;gui=None;witness=None;errors=[];observed=None;stopped=False
    try:
        require_silent_windows_launch(api_exe)
        warm=start_checked_windows_process([exe,'--run',str(data),'--seconds','30','--ready-report',str(ready),'--stop-file',str(stop),'--report',str(final)])
        deadline=time.monotonic()+35
        while not ready.exists():
            if warm.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Warm instance did not become ready')
            time.sleep(.05)
        info=checks.read(ready);witness=checks.ChildWitness(info['childPid']);stop.write_text('warm stop',encoding='utf-8');warm.wait(timeout=50);witness.wait();witness.close();witness=None
        if warm.returncode!=0 or not checks.read(final)['graceful']:raise RuntimeError('Warm instance did not close normally')
        original={name:checks.sha(data/name) for name in ['control-instance.json','operator-keys.json','player-ticket-signing.key']}
        keys=checks.read(data/'operator-keys.json')['OperatorKeys'];uri=f'http://127.0.0.1:{port}'
        require_silent_windows_launch(api_exe)
        gui=start_checked_windows_process([exe],cwd=out,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);stage('select-existing-instance',guiPid=gui.pid,instance=str(data))
        powershell=Path(os.environ.get('WINDIR','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
        def children():
            # Own child process metadata only; no UI Automation, command lines,
            # environment, stacks, memory reads, priorities or system settings.
            script='$rows = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = '+str(gui.pid)+'" | Where-Object { $_.Name -eq "VrCommand.Api.exe" } | ForEach-Object { $core = (Get-Process -Id $_.ProcessId).Modules | Where-Object { $_.ModuleName -eq "coreclr.dll" } | Select-Object -First 1; [pscustomobject]@{ pid = $_.ProcessId; image = $_.ExecutablePath; core = $core.FileName } }); ConvertTo-Json -InputObject $rows -Compress'
            result=subprocess.run([str(powershell),'-NoProfile','-NonInteractive','-Command',script],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10,check=True)
            return json.loads(result.stdout.decode('utf-8-sig'))
        deadline=time.monotonic()+300
        while gui.poll() is None:
            if time.monotonic()>deadline:raise RuntimeError('GUI observation exceeded 300 seconds')
            if observed is None:
                rows=children()
                if rows:
                    if len(rows)!=1:raise RuntimeError('Ambiguous GUI-owned API children')
                    row=rows[0]
                    if not row.get('core'):time.sleep(.1);continue
                    if Path(row['image']).resolve()!=(folder/'Runtime/VrCommand.Api.exe').resolve() or Path(row['core']).resolve()!=(folder/'Runtime/coreclr.dll').resolve():raise RuntimeError('GUI child module is outside the actual package')
                    witness=checks.ChildWitness(row['pid'])
                    request=urllib.request.Request(uri+'/api/me',headers={'Authorization':'Bearer '+keys['Master']})
                    try:
                        with urllib.request.urlopen(request,timeout=5) as response:identity=json.load(response)
                    except urllib.error.URLError:witness.close();witness=None;time.sleep(.1);continue
                    if identity['role']!='Master':raise RuntimeError('GUI-owned API did not retain the private instance identity')
                    observed=row;save('gui-api-observed.json',row);stage('gui-running',guiPid=gui.pid,apiPid=row['pid'])
            elif not stopped and witness.kernel.WaitForSingleObject(witness.handle,0)==0:
                witness.wait();witness.close();witness=None;stopped=True;stage('gui-api-stopped',guiPid=gui.pid)
            time.sleep(.25)
        gui.wait(timeout=5)
        if gui.returncode!=0 or not observed or not stopped:raise RuntimeError('GUI did not complete an observed original API start / stop / close cycle')
        review=checks.read(out/'gui.review.json')
        if review.get('version')!=1 or any(review.get(name) is not True for name in ['selected','started','stopped']):raise RuntimeError('GUI visual observations were not confirmed')
        if any(checks.sha(data/name)!=value for name,value in original.items()):raise RuntimeError('GUI unexpectedly replaced an existing instance / key')
        result={'complete':True,'guiExitCode':gui.returncode,'api':observed,'instance':str(data),'originalPrivateFileHashes':original,'review':review,'scope':'Actual native GUI select-existing / start / stop / close, child OS handle / own coreclr / identity. No GUI key creation, clipboard, browser login, remote LAN, Unity or headset proof.'}
    except BaseException as error:
        stage('failed',errorType=type(error).__name__);raise
    finally:
        if warm and warm.poll() is None:stop.write_text('cleanup',encoding='utf-8');warm.wait(timeout=50)
        if gui and gui.poll() is None:gui.terminate();gui.wait(timeout=5)
        if witness:
            try:witness.wait();witness.close();witness=None
            except Exception as error:errors.append(type(error).__name__)
        if gui and not observed:
            try:
                deadline=time.monotonic()+15
                while children():
                    if time.monotonic()>deadline:raise RuntimeError('Unobserved GUI API child remains')
                    time.sleep(.1)
            except Exception as error:errors.append(type(error).__name__)
        save('cleanup.json',{'errors':errors,'remainingGui':bool(gui and gui.poll() is None),'remainingWarmRunner':bool(warm and warm.poll() is None)})
        if errors:raise RuntimeError('Preserve runtime: GUI-owned API stop is not confirmed')
        venue.snapshot_runtime(runtime,out/'runtime-snapshot')
    save('checks.json',result);stage('passed')
if __name__=='__main__':main()
