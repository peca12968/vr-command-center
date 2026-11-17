"""Offline device feedback replay from a real isolated API and ArenaSession outbox. No physical hardware I/O."""
import argparse,hashlib,json,os,secrets,shutil,socket,subprocess,sys,tempfile,threading,time,urllib.request,uuid
from pathlib import Path
from local_api import add_api_arguments, api_command as resolve_api_command, checked_api_command
from windows_firewall import require_silent_windows_launch
from windows_ipc_api import has_no_ip_endpoints, unix_http_opener
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    add_api_arguments(p)
    for name,project in [('simulator','VrCommand.HardwareSimulator'),('relay','VrCommand.TelemetryRelay')]:
        default=ROOT/'tools'/project/'bin/Release/net10.0'/(project+'.dll')
        p.add_argument('--'+name+'-dll',type=Path,default=default)
    runtime_options = p.add_mutually_exclusive_group()
    runtime_options.add_argument('--runtime-root', type=Path)
    runtime_options.add_argument('--ipc-work-root', type=Path, help='Short existing Windows folder for the AF_UNIX rehearsal')
    args=p.parse_args()
    use_ipc = args.ipc_work_root is not None
    try:
        if use_ipc:
            if os.name != 'nt' or not args.ipc_work_root.is_dir():
                raise ValueError('Use a short existing Windows IPC work root.')
            api_command, api_cwd, api_assembly = resolve_api_command(args)
        else:
            api_command, api_cwd, api_assembly = checked_api_command(args)
            require_silent_windows_launch(sys.executable)
    except (OSError, RuntimeError, ValueError) as error:
        p.exit(2, f'{error}\n')
    binaries=[api_assembly,args.simulator_dll.resolve(),args.relay_dll.resolve()]
    if not all(v.is_file() for v in binaries):p.error('Build the complete solution first')
    binary_files={name:{v.relative_to(binary.parent).as_posix():sha(v) for v in binary.parent.rglob('*') if v.is_file()} for name,binary in zip(['api','simulator','relay'],binaries)}
    out=ROOT/'artifacts/hardware-simulator'/('run-'+uuid.uuid4().hex);out.mkdir(parents=True)
    root = args.ipc_work_root or args.runtime_root
    runtime=(root.resolve()/out.name) if root else Path(tempfile.mkdtemp(prefix='vr-hardware-simulator-'))
    if root:runtime.mkdir(parents=True,exist_ok=False)
    print(json.dumps({'stage':'starting','directory':str(out)}),flush=True)
    keys={name:secrets.token_hex(32) for name in ['Master','GameServer']};pipe=secrets.token_hex(32)
    keyfile=runtime/'keys.private.json';keyfile.write_text(json.dumps({'OperatorKeys':keys}),encoding='utf-8')
    env={k:v for k,v in os.environ.items() if not k.lower().startswith('operatorkeys__') and k.lower() not in ('operatorkeyfile','playerticketsigningkey','controlpipetoken','datadirectory','sessiondatadirectory')}
    env.update(OperatorKeyFile=str(keyfile),DataDirectory=str(runtime/'missions'),SessionDataDirectory=str(runtime/'sessions'),ControlPipeToken=pipe,Logging__LogLevel__Default='Warning')
    endpoint = runtime / 'api.sock'
    if use_ipc:
        port = 18000
    else:
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    base='http://127.0.0.1:'+str(port);logs=[];checks=[];complete=False;process=None;cleanup_errors=[]
    def check(value,label):
        if not value:raise AssertionError(label)
        checks.append(label);print('PASS: '+label,flush=True)
    def save(file,value,folder=out):
        with (folder/file).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')
    opener=unix_http_opener(lambda _port: endpoint) if use_ipc else urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def get(path):
        req=urllib.request.Request(base+path,headers={'Authorization':'Bearer '+keys['Master']})
        with opener.open(req,timeout=5) as response:return json.load(response)
    def run(name,command,success=True):
        result=subprocess.run(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
        text=result.stdout.decode('utf-8',errors='replace')
        for secret in [*keys.values(),pipe]:
            if secret in text:raise AssertionError('Generated credential appeared in diagnostic')
        (out/(name+'.log')).write_text(text,encoding='utf-8');check(result.returncode==(0 if success else 1),name+' exit status')
        return result
    try:
        api_urls = ['--urls', 'http://unix:/' + str(endpoint), '--preferHostingUrls', 'true'] if use_ipc else ['--urls', base]
        process=subprocess.Popen([*api_command,*api_urls],cwd=api_cwd,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        def collect():
            for line in iter(process.stdout.readline,b''):
                logs.append(line.decode('utf-8',errors='replace'))
                if sum(len(v) for v in logs)>65536:logs.pop(0)
        reader=threading.Thread(target=collect,daemon=True);reader.start();deadline=time.monotonic()+8
        while True:
            try:
                if get('/health')['status']=='ok':break
            except (OSError,ValueError,KeyError):pass
            if process.poll() is not None or time.monotonic()>=deadline:raise RuntimeError('Owned API failed its bounded startup')
            time.sleep(.1)
        check(get('/')['version']=='0.31.0','original API contract remains unchanged')
        journal=runtime/'combat.ndjson';relay=['dotnet',str(binaries[2]),'--journal',str(journal),'--base-url',base,'--key-file',str(keyfile)]
        if use_ipc:
            relay += ['--local-socket', str(endpoint)]
        run('arena-capture',relay+['--demo-room','3']);run('outbox-publish',relay)
        sessions=get('/api/sessions?includeEnded=true');check(len(sessions)==1,'isolated ArenaSession created exactly one original session')
        session=sessions[0];sid=session['id'];events=[];after=0
        while True:
            page=get(f'/api/sessions/{sid}/events?after={after}&limit=500')
            if not page:break
            events.extend(page);after=page[-1]['sequence']
            if len(events)>4096:raise AssertionError('Fixture history unexpectedly exceeded simulator bound')
        stats=get(f'/api/sessions/{sid}/statistics');save('source-events.json',events);save('source-session.json',session);save('source-statistics.json',stats)
        check(session['state']=='Ended' and session['combatStream']['sealed'] and stats['pendingTelemetry'] is False and after==stats['throughSequence'],'actual API End and exact combat seal agree with complete source history')
        player=next(e['payload'] for e in events if e['kind']=='PlayerJoined');device=str(uuid.uuid4())
        binding={'deviceId':device,'sessionId':sid,'streamId':session['combatStream']['streamId'],'roomId':player['roomId'],'playerId':player['id'],'admissionId':player['admissionId']}
        feedback=[e for e in events if e['kind']=='StreamCombatRecorded' and e['payload']['report']['kind'] in ('ShotFired','PlayerDamaged')]
        check(sum(e['payload']['report']['kind']=='ShotFired' for e in feedback)==2,'source contains the two real ArenaSession simulated firing events')
        def step(action,at=0,**extra):return {'atMilliseconds':at,'action':action,'deviceId':device,**extra}
        steps=[step('Connect',bindingIndex=0)]
        for delivery,event in enumerate(feedback,1):steps.extend([step('Dispatch',eventId=event['eventId']),step('Receive'),step('Acknowledge',connection=1,delivery=delivery)])
        source={'version':1,'events':events,'bindings':[binding],'steps':steps};save('simulation-input.json',source)
        tool=['dotnet',str(binaries[1])]
        normal=out/'simulation-report.json';run('simulation',tool+['--input',str(out/'simulation-input.json'),'--output',str(normal)])
        report=read(normal);receipts=[v for row in report['results'] for v in row['receipts']]
        check(report['complete'] and report['simulatedHardwareOnly'] and report['physicalDeliveryConfirmed'] is False,'report completes only an offline simulated device scenario')
        acks=[r['delivery']['signal'] for r in receipts if r['status']=='SimulatedAcknowledged']
        check(len(acks)==len(feedback) and all(a['eventId']==e['eventId'] and a['reportId']==e['payload']['report']['reportId'] and a['streamSequence']==e['payload']['streamSequence'] and a['observedSequence']==e['payload']['observedSequence'] and a['admissionId']==binding['admissionId'] and a['roomId']==3 for a,e in zip(acks,feedback)),'every simulated ACK preserves the original accepted combat/admission witness')
        save('repeat-input.json',source);repeat=out/'repeat-report.json';run('deterministic-repeat',tool+['--input',str(out/'repeat-input.json'),'--output',str(repeat)])
        check(sha(normal)==sha(repeat),'repeat offline runs produce byte-identical simulated reports')
        old=sha(normal);run('no-overwrite',tool+['--input',str(out/'simulation-input.json'),'--output',str(normal)],False);check(sha(normal)==old,'existing reports remain byte-identical after refused overwrite')
        input_hash=sha(out/'simulation-input.json');run('no-input-alias',tool+['--input',str(out/'simulation-input.json'),'--output',str(out/'simulation-input.json')],False);check(sha(out/'simulation-input.json')==input_hash,'input source remains unchanged after a refused output alias')
        faults={**source,'steps':[step('Connect',bindingIndex=0),step('Dispatch',eventId=feedback[0]['eventId']),step('Receive'),step('Disconnect'),step('Connect',bindingIndex=0),step('Acknowledge',connection=1,delivery=1),step('Dispatch',eventId=feedback[0]['eventId']),step('Dispatch',eventId=feedback[1]['eventId']),step('Receive',at=2000)]}
        save('fault-input.json',faults);fault=out/'fault-report.json';run('faults',tool+['--input',str(out/'fault-input.json'),'--output',str(fault)])
        values=read(fault)['results'];check(values[3]['receipts'][0]['status']=='Disconnected' and values[5]['status']=='IgnoredAcknowledgement' and values[6]['status']=='AlreadySeen' and values[8]['status']=='Empty' and values[8]['receipts'][0]['status']=='Expired','disconnect, reconnect, stale ACK, duplicate and exact expiry remain explicit non-delivery outcomes')
        bad_authority=json.loads(json.dumps(source));bad_authority['events'][0]['actor']={**bad_authority['events'][0]['actor'],'role':'RoomController','roomId':1}
        missing_player=json.loads(json.dumps(source));joined=next(e for e in missing_player['events'] if e['kind']=='PlayerJoined');joined['kind']='PlayerLeft';joined['payload']={'playerId':str(uuid.uuid4())}
        for name,bad in [('wrong-admission',{**source,'bindings':[{**binding,'admissionId':str(uuid.uuid4())}]}),('missing-seal',{**source,'events':events[:-1]}),('unknown-action',{**source,'steps':[step('Unsupported')]}),('missing-action',{**source,'steps':[{'atMilliseconds':0,'deviceId':device,'bindingIndex':0}]}),('unknown-version',{**source,'version':2}),('backwards-clock',{**source,'steps':[step('Connect',at=1,bindingIndex=0),step('Receive',at=0)]}),('wrong-authority',bad_authority),('missing-player',missing_player),('unknown-field',{**source,'operatorKey':keys['Master']})]:
            file=runtime/(name+'.json');save(name+'.json',bad,runtime);dest=out/(name+'-must-not-exist.json');run(name,tool+['--input',str(file),'--output',str(dest)],False);check(not dest.exists(),name+' leaves no accepted output')
        check(get(f'/api/sessions/{sid}/events?limit=500')==events and get(f'/api/sessions/{sid}/statistics')==stats and get('/api/sessions')==[],'offline simulator does not mutate accepted session history, statistics or active rooms')
        check(all(secret not in file.read_text(encoding='utf-8') for file in out.iterdir() if file.is_file() for secret in [*keys.values(),pipe]),'public reports and logs contain none of the generated credentials')
        if use_ipc:
            check(has_no_ip_endpoints([os.getpid(), process.pid]), 'Owned IPC fixture and API have zero TCP listeners and UDP endpoints')
        check(all(sha(binary.parent/name)==value for group,binary in zip(['api','simulator','relay'],binaries) for name,value in binary_files[group].items()),'the tested API, simulator and relay output graphs remain byte-identical')
        complete=True
    finally:
        if process is not None:
            try:
                if process.poll() is None:process.stdin.write(('STOP '+pipe+'\n').encode());process.stdin.flush();process.stdin.close()
                code=process.wait(timeout=15);reader.join(timeout=5)
                if code!=0 or reader.is_alive():raise RuntimeError('Original API did not finish normally')
            except Exception as error:cleanup_errors.append(type(error).__name__)
            text=''.join(logs)
            for secret in [*keys.values(),pipe]:text=text.replace(secret,'[redacted]')
            (out/'api.log').write_text(text,encoding='utf-8')
        save('cleanup.json',{'errors':cleanup_errors,'apiRemaining':process is not None and process.poll() is None})
        if cleanup_errors:raise RuntimeError('Owned API cleanup not confirmed; preserve original runtime')
        # Every child is terminal before the single raw snapshot. Never open preserved SQLite.
        shutil.copytree(runtime,out/'runtime-snapshot')
    save('checks.json',{'complete':complete,'checks':len(checks),'findings':checks,'runtimeDirectory':str(runtime),'binaries':{name:str(binary) for name,binary in zip(['api','simulator','relay'],binaries)},'binaryFiles':binary_files,'helperSha256':sha(Path(__file__)),'transport':'Windows AF_UNIX' if use_ipc else 'Loopback TCP',
         'ipcSupportSha256':sha(Path(__file__).with_name('windows_ipc_api.py')) if use_ipc else None,
         'scope':'Actual API and ArenaSession outbox plus compiled offline device simulator only; no physical hardware, vendor protocol, Unity/headset or gameplay load evidence'})
    (ROOT/'artifacts/hardware-simulator-latest-path.txt').write_text(str(out),encoding='utf-8')
    print(json.dumps({'complete':complete,'checks':len(checks),'directory':str(out)}))
if __name__=='__main__':main()
