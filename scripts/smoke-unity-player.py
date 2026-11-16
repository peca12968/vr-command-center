"""Exercise a real Windows Unity server and two clients against an isolated API.

No headset, GPU rendering or automatic weapon input is simulated by this driver.
The clients use the player's existing desktop synthetic head/hand controls.
Private keys/configuration and evidence remain under ignored artifacts/.
"""
import argparse,json,os,secrets,socket,subprocess,time,urllib.error,urllib.request,uuid
import importlib.util
from pathlib import Path
import sys
from live_world_frame import read_live_frame
from windows_firewall import WindowsFirewallLaunchError, require_silent_windows_launch

root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--player-exe',type=Path,default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER',root/'artifacts/desktop/VrCommand.exe')))
parser.add_argument('--api-dll',type=Path,default=Path(os.environ.get('VR_COMMAND_API_DLL',root/'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
parser.add_argument('--seconds',type=int,default=8,choices=range(8,61))
parser.add_argument('--linked',action='store_true',help='Link all five rooms, with one real desktop client in room 1 and another in room 5')
parser.add_argument('--maximum-source-age-ms',type=int,default=1500)
storage=parser.add_mutually_exclusive_group()
storage.add_argument('--runtime-root',type=Path,help='Directory for new runtime files; default is local application data')
storage.add_argument('--runtime-on-artifact-drive',action='store_true',help='Use the artifact drive for active journals to test that storage')
args=parser.parse_args()
if os.name!='nt': raise RuntimeError('This fixture requires a Windows Unity player')
if not args.player_exe.is_file() or not args.api_dll.is_file(): raise RuntimeError('Build the current Unity Desktop player and API before running this fixture')
if not 500<=args.maximum_source_age_ms<=10000: raise ValueError('Source age threshold must be 500–10000 ms')
try:
    require_silent_windows_launch(args.player_exe)
except WindowsFirewallLaunchError as error:
    parser.exit(1, f'{error}\n')
directory=root/'artifacts/unity-player-smoke'/(time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
directory.mkdir(parents=True,exist_ok=False)
runtime_directory=directory
if not args.runtime_on_artifact_drive:
    runtime_root=args.runtime_root or Path(os.environ['LOCALAPPDATA'])/'VrCommand'/'UnitySmokeRuns'
    runtime_directory=runtime_root.resolve()/directory.name
    if runtime_directory!=directory: runtime_directory.mkdir(parents=True,exist_ok=False)
tokens={name:secrets.token_hex(32) for name in ['Master','GameServer']}
(directory/'keys.json').write_text(json.dumps({'OperatorKeys':tokens}),encoding='utf-8')
with socket.socket() as probe:
    probe.bind(('127.0.0.1',0)); http_port=probe.getsockname()[1]
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as probe:
    probe.bind(('127.0.0.1',0)); game_port=probe.getsockname()[1]
base=f'http://127.0.0.1:{http_port}'
environment={k:v for k,v in os.environ.items() if not k.lower().startswith('operatorkeys__') and k.lower() not in ['operatorkeyfile','playerticketsigningkey']}
environment.update(DataDirectory=str(runtime_directory/'missions'),SessionDataDirectory=str(runtime_directory/'sessions'),OperatorKeyFile=str(directory/'keys.json'),Logging__LogLevel__Default='Warning')
api_log=(directory/'api.log').open('wb')
processes=[]
session=None
observations=[]
def request(route,body=None,admission=None):
    headers={'Authorization':'Bearer '+tokens['Master'],'Content-Type':'application/json'}
    if admission: headers['If-Match-Admission']=admission
    with urllib.request.urlopen(urllib.request.Request(base+route,data=None if body is None else json.dumps(body).encode(),headers=headers),timeout=5) as response:
        return json.load(response)
def control(action):
    return request('/api/sessions/'+session+'/commands',{'commandId':str(uuid.uuid4()),'action':action})
def live_frame():
    with urllib.request.urlopen(urllib.request.Request(base+'/api/sessions/'+session+'/world/watch?mode=live',headers={'Authorization':'Bearer '+tokens['Master']}),timeout=5) as response:
        sample=read_live_frame(response,session)
    if sample is None: return None
    frame, observation=sample
    if observation['sourceAgeSeconds'] is None: raise RuntimeError('Native source capture UTC is missing')
    observation.update(tick=frame['packet']['frame']['tick'],phase=frame['packet']['frame']['phase'])
    observations.append(observation)
    (directory/'progress.json').write_text(json.dumps(observation),encoding='utf-8')
    return frame
def launch(name,config):
    path=directory/(name+'.json'); path.write_text(json.dumps(config),encoding='utf-8')
    process=subprocess.Popen([str(args.player_exe.resolve()),'-batchmode','-nographics','-logFile',str(directory/(name+'.log')),'--vr-config',str(path)],cwd=args.player_exe.resolve().parent,creationflags=subprocess.CREATE_NO_WINDOW)
    processes.append(process)
    return process
def wait_for(predicate,timeout,label):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if any(p.poll() is not None for p in processes): raise RuntimeError('A native child exited during '+label)
        try:
            value=predicate()
            if value:return value
        except (OSError,urllib.error.URLError,ValueError):pass
        time.sleep(.25)
    raise RuntimeError('Timed out: '+label)
try:
    api=subprocess.Popen(['dotnet',str(args.api_dll.resolve()),'--urls',base],cwd=root,env=environment,stdout=api_log,stderr=api_log,creationflags=subprocess.CREATE_NO_WINDOW)
    processes.append(api)
    wait_for(lambda:request('/health'),20,'isolated API')
    mission=request('/api/missions',{'name':'Unity desktop native integration - Simulation','briefing':'Two actual desktop clients; synthetic head/hand poses, no headset','durationSeconds':120,'environment':{'mode':'VR','weather':'Storm','timeOfDay':'Night','lightning':True},'enemies':{'count':2,'behavior':'Advance','autoAttack':True},'props':[]})
    room_ids=[1,2,3,4,5] if args.linked else [5]
    client_rooms=[1,5] if args.linked else [5,5]
    state=request('/api/sessions',{'missionId':mission['id'],'mode':'Linked' if args.linked else 'Independent','roomIds':room_ids}); session=state['id']
    players=[str(uuid.uuid4()),str(uuid.uuid4())]
    for index,identity in enumerate(players):
        state=request('/api/sessions/'+session+'/players',{'playerId':identity,'name':'Desktop Simulation '+str(index+1),'roomId':client_rooms[index],'headset':'Quest3'})
    launch('server',{'role':'Server','address':'127.0.0.1','listenAddress':'127.0.0.1','port':game_port,'sessionId':session,'managementApiUrl':base,'gameServerKey':tokens['GameServer'],'telemetryOrigin':'Simulation','telemetryDirectory':str(runtime_directory/'telemetry')})
    wait_for(lambda:request('/api/sessions/'+session+'/world'),60,'Unity server world publication')
    for index,identity in enumerate(players):
        player=next(p for p in state['players'] if p['id']==identity)
        ticket=request('/api/sessions/'+session+'/players/'+identity+'/join-ticket',{},player['admissionId'])
        launch('client'+str(index+1),{'role':'Client','address':'127.0.0.1','port':game_port,'joinTicket':ticket['ticket']})
    def both_connected():
        frame=live_frame()
        return frame if frame and sum(p['connected'] and p['rig']['kind']=='Simulated' for p in frame['packet']['frame']['players'])==2 else None
    connected=wait_for(both_connected,90,'two authenticated native clients with synthetic rigs')
    observations.clear()
    control('Begin')
    target_tick=args.seconds*20
    running=wait_for(lambda: (frame if (frame:=live_frame()) and frame['packet']['frame']['tick']>=target_tick else None),args.seconds*3+40,'native running world boundary')
    peak_running_age=max(observations,key=lambda row:row['sourceAgeSeconds'])
    if peak_running_age['sourceAgeSeconds']>=args.maximum_source_age_ms/1000:
        (directory/'freshness-failure.json').write_text(json.dumps(peak_running_age),encoding='utf-8')
        raise RuntimeError('Native live source exceeded its freshness threshold: '+str(peak_running_age['sourceAgeSeconds']))
    control('Pause')
    paused=wait_for(lambda: (frame if (frame:=live_frame()) and frame['packet']['frame']['phase']=='Paused' else None),15,'native pause')
    tick=paused['packet']['frame']['tick']; time.sleep(.5)
    assert live_frame()['packet']['frame']['tick']==tick
    control('End')
    world=wait_for(lambda: (info if (info:=request('/api/sessions/'+session+'/world'))['complete'] else None),30,'native final combat/world seal')
    stats=request('/api/sessions/'+session+'/statistics')
    assert stats['origin']=='Simulation' and not stats['pendingTelemetry']
    assert sum(player['hitsReceived'] for player in stats['players'])>0, 'Native enemy AI did not produce confirmed damage'
    assert world['header']['environmentVersion']==1 and world['header']['captureStartedAtUtc']
    assert world['header']['roomIds']==room_ids
    assert sorted(player['roomId'] for player in stats['players'])==sorted(client_rooms)
    final=live_frame()
    assert final['packet']['frame']['phase']=='Ended' and final['packet']['sequence']==world['acceptedSequence']
    assert sorted(final['statistics'],key=lambda p:p['playerId'])==sorted(stats['players'],key=lambda p:p['playerId']), 'Native replay statistics disagree with the sealed ledger'
    assert request('/api/sessions')==[]
    summary={'sessionId':session,'source':'Actual Unity Windows server + 2 desktop clients; Simulation rigs','headsets':0,'world':world,'statistics':stats,'connectedFrame':connected['packet']['sequence'],'runningTick':running['packet']['frame']['tick'],'pausedTick':tick,'maximumObservedSourceAgeSeconds':peak_running_age['sourceAgeSeconds'],'oldestRunningObservation':peak_running_age,'activeSessions':0,'mode':'Linked' if args.linked else 'Independent','clientRooms':client_rooms,'runtimeDirectory':str(runtime_directory)}
finally:
    failed=sys.exc_info()[0] is not None
    if session:
        try:control('End')
        except Exception:pass
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
    api_log.close()
    (root/'artifacts/latest-unity-player-smoke-path.txt').write_text(str(directory),encoding='utf-8')
    if runtime_directory!=directory:
        try:
            spec=importlib.util.spec_from_file_location('smoke_venue',root/'scripts/start-desktop-venue.py')
            venue=importlib.util.module_from_spec(spec); spec.loader.exec_module(venue)
            venue.snapshot_runtime(runtime_directory,directory/'runtime-snapshot')
        except Exception:
            print('Runtime snapshot failed; original remains at '+str(runtime_directory),file=sys.stderr,flush=True)
            if not failed: raise

(directory/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps({'success':True,'directory':str(directory),'frames':world['acceptedSequence'],'players':len(stats['players']),'tick':tick,'maximumSourceAgeSeconds':summary['maximumObservedSourceAgeSeconds'],'headsets':0}),flush=True)
