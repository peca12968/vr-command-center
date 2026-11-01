"""Exercise the actual API's opt-in private stdin lifetime. No HTTP shutdown endpoint or historical data."""
import argparse,json,os,secrets,socket,subprocess,threading,time,urllib.error,urllib.request,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--api',type=Path,default=Path(os.environ.get('VR_COMMAND_API_DLL',ROOT/'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')));parser.add_argument('--runtime-root',type=Path);args=parser.parse_args()
    out=ROOT/'artifacts/control-pipe'/('run-'+uuid.uuid4().hex);out.mkdir(parents=True,exist_ok=False)
    runtime=(args.runtime_root.resolve()/out.name) if args.runtime_root else out/'runtime';runtime.mkdir(parents=True,exist_ok=False);rows=[]
    for mode in ('default','invalid','stop','eof','oversized','closed-pipes'):
        data=runtime/mode;data.mkdir();key=secrets.token_hex(32);nonce='X'*64 if mode=='invalid' else secrets.token_hex(32)
        keyfile=data/'keys.json';keyfile.write_text(json.dumps({'OperatorKeys':{'Master':key}}),encoding='utf-8')
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        env={k:v for k,v in os.environ.items() if not k.lower().startswith('operatorkeys__') and k.lower() not in ('operatorkeyfile','playerticketsigningkey','controlpipetoken')}
        env.update(OperatorKeyFile=str(keyfile),DataDirectory=str(data/'missions'),SessionDataDirectory=str(data/'sessions'),Logging__LogLevel__Default='Warning')
        if mode!='default':env['ControlPipeToken']=nonce
        command=([str(args.api.resolve())] if args.api.suffix.lower()=='.exe' else ['dotnet',str(args.api.resolve())])+['--urls',f'http://127.0.0.1:{port}']
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL if mode=='default' else subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        ready=threading.Event();logs=[];ready_count=[0]
        def output():
            for raw in process.stdout:
                line=raw.decode('utf-8',errors='replace').rstrip('\r\n')
                if line=='VR_CONTROL_READY '+nonce:ready_count[0]+=1;ready.set()
                logs.append(line.replace(key,'[key]').replace(nonce,'[control-token]')[:2048])
        thread=None
        if mode=='closed-pipes':process.stdout.close();process.stdin.close()
        else:thread=threading.Thread(target=output,daemon=True);thread.start()
        def get(path,expected=200,method='GET'):
            req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=b'{}' if method=='POST' else None,method=method,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
            try:
                with urllib.request.urlopen(req,timeout=2) as response:status=response.status;body=response.read()
            except urllib.error.HTTPError as error:status=error.code;body=error.read()
            assert status==expected,(mode,path,status)
            return json.loads(body) if body else None
        try:
            if mode=='closed-pipes':
                process.wait(timeout=15);assert process.returncode==0
            elif mode=='invalid':
                process.wait(timeout=15);assert process.returncode!=0 and not ready.is_set()
            else:
                until=time.monotonic()+15
                while True:
                    if process.poll() is not None:raise RuntimeError('API exited before readiness: '+mode)
                    try:
                        if (mode=='default' or ready.is_set()) and get('/health')['status']=='ok':break
                    except urllib.error.URLError:pass
                    if time.monotonic()>until:raise RuntimeError('API readiness timeout: '+mode)
                    time.sleep(.05)
                assert get('/')['version']=='0.31.0';get('/api/control/stop',404);get('/api/control/stop',404,method='POST')
                if mode=='default':
                    time.sleep(.15);assert process.poll() is None and ready_count[0]==0;process.terminate();process.wait(timeout=10)
                else:
                    assert ready_count[0]==1
                    if mode=='stop':
                        process.stdin.write(('STOP '+secrets.token_hex(32)+'\n'+'x'*128+'\n').encode());process.stdin.flush();time.sleep(.2);assert process.poll() is None
                        process.stdin.write(('STOP '+nonce+'\n').encode());process.stdin.flush()
                    elif mode=='oversized':process.stdin.write(b'x'*129);process.stdin.flush()
                    else:process.stdin.close()
                    process.wait(timeout=15);assert process.returncode==0
            rows.append({'case':mode,'exitCode':process.returncode,'readyEvents':None if mode=='closed-pipes' else ready_count[0],'readyObservation':'DisabledByFixture' if mode=='closed-pipes' else 'Observed','passed':True})
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=10)
            if process.stdin and not process.stdin.closed:process.stdin.close()
            if thread:thread.join(timeout=3);assert not thread.is_alive()
            if not process.stdout.closed:process.stdout.close()
            text='\n'.join(logs);assert key not in text and nonce not in text;(out/(mode+'.log')).write_text(text,encoding='utf-8')
            (out/(mode+'-status.json')).write_text(json.dumps({'case':mode,'acceptancePassed':any(row['case']==mode for row in rows),'processExited':process.poll() is not None,'exitCode':process.returncode,
                'readyEvents':None if mode=='closed-pipes' else ready_count[0],'readyObservation':'DisabledByFixture' if mode=='closed-pipes' else 'Observed'},indent=2)+'\n',encoding='utf-8')
    if runtime!=out/'runtime':
        import importlib.util
        spec=importlib.util.spec_from_file_location('pipe_venue',ROOT/'scripts/start-desktop-venue.py');venue=importlib.util.module_from_spec(spec);spec.loader.exec_module(venue);venue.snapshot_runtime(runtime,out/'runtime-snapshot')
    result={'complete':True,'checks':len(rows),'cases':rows,'runtime':str(runtime),'scope':'Actual private API process lifetime only; no public shutdown route, Unity, LAN, gameplay or headset acceptance'}
    (out/'checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');(ROOT/'artifacts/control-pipe-latest-path.txt').write_text(str(out),encoding='utf-8');print(json.dumps({'complete':True,'checks':len(rows),'directory':str(out)}))
if __name__=='__main__':main()
