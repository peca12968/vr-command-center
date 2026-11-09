"""Exercise portable Windows packages, five rooms, Linked and owned process cleanup."""
import argparse,base64,csv,hashlib,importlib.util,io,ipaddress,json,os,re,shutil,socket,subprocess,sys,tempfile,threading,time,urllib.error,urllib.request,uuid,zipfile
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
package=module('server_package','package-windows-server.py');control=module('server_control_checks','check-control-package.py');venue=module('server_venue','start-desktop-venue.py');world=module('server_world','analyze-world-journal.py');debrief=module('server_debrief','check-desktop-debrief.py')
field=module('server_field_results','verify-field-results.py')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def free(kind=socket.SOCK_STREAM,address='127.0.0.1'):
    with socket.socket(socket.AF_INET,kind) as s:s.bind((address,0));return s.getsockname()[1]

def reconcile_ai_damage(frames, owners, enabled_sequence, disabled_sequence):
    totals={player:{'roomId':room,'hitsReceived':0,'damageTaken':0} for player,room in owners.items()}
    events=set(); pending=None; last_sequence=0; damage_events=0
    for value in frames:
        packet=value['packet'];frame=packet['frame']
        enemies={enemy['id']:enemy['roomId'] for enemy in frame['enemies']}
        for event in packet['events']:
            victim=event['playerId']
            if event['sequence']!=last_sequence+1 or event['eventId'] in events or owners.get(victim) is None \
                or enemies.get(event['enemyId'])!=owners[victim] or frame['phase']!='Running' or packet['suspended'] \
                or not enabled_sequence<=packet['observedSequence']<disabled_sequence or not frame['autoAttack']:
                raise ValueError('Combat replay event violates its original room, order or enabled window')
            events.add(event['eventId']);last_sequence=event['sequence']
            attack=(event['tick'],event['enemyId'],victim)
            if event['kind']=='EnemyShot' and pending is None and event['hasRay'] and event['hit']=='Friendly' and event['targetId']==victim:
                pending=attack
            elif event['kind']=='PlayerDamaged' and pending==attack:
                row=totals[victim]
                if event['damage']!=min(20,100-row['damageTaken']) or event['damage']<=0:
                    raise ValueError('Combat replay damage does not match the remaining health')
                row['hitsReceived']+=1;row['damageTaken']+=event['damage'];damage_events+=1;pending=None
            else:
                raise ValueError('Combat replay damage must follow its original enemy shot')
        if packet['throughCombatSequence']!=damage_events:
            raise ValueError('Combat replay ledger boundary differs from its original damage events')
        seen=set()
        for row in value['statistics']:
            player=row['playerId'];total=totals.get(player)
            if player in seen or total is None or any(row[key]!=count for key,count in total.items()) \
                or row['health']!=100-total['damageTaken'] or any(row[key]!=0 for key in ('ammoUsed','shotsHit','kills','accuracyPercent')):
                raise ValueError('Combat replay statistics differ from the original event prefix')
            seen.add(player)
        if packet['observedSequence']>=enabled_sequence and seen!=owners.keys():
            raise ValueError('Combat replay statistics omit an original admission')
    if pending or not totals or any(not row['hitsReceived'] for row in totals.values()):
        raise ValueError('Combat replay must include a complete attack and damage for every original player')
    return {'damageEvents':damage_events,'players':totals}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path);p.add_argument('--control-package',type=Path,required=True);p.add_argument('--runtime-root',type=Path,required=True);p.add_argument('--observe-closure-ui',action='store_true')
    p.add_argument('--player-package',type=Path,help='Launch five players per room from the API room ZIP, using this extracted player package')
    p.add_argument('--game-address',type=ipaddress.IPv4Address,help='Local private IPv4 for the three-package check')
    p.add_argument('--check-lan-preflight',action='store_true',help='Release a same-PC UDP preflight before Unity binds each original game port')
    p.add_argument('--check-vr-venue-tickets',action='store_true',help='Launch all 25 players in each mode from the shipped console venue ZIP')
    p.add_argument('--check-quest-vr-deploy',action='store_true',help='Run Quest preflight and mapped mock deployment from each original VR venue ZIP')
    p.add_argument('--check-quest-vr-partial-map',action='store_true',help='Use a mixed headset roster and deploy five selected Quest seats from each original VR venue ZIP')
    p.add_argument('--check-windows-venue-staging',action='store_true',help='Stage VIVE XR seats from the original VR or mixed venue ZIP')
    p.add_argument('--check-venue-openxr',action='store_true',help='Use one graphical mock OpenXR seat alongside 24 desktop peers per topology')
    p.add_argument('--peer-diagnostics',action='store_true',help='Verify observed UDP peers in Linked and absence in default Independent runs')
    p.add_argument('--field-evidence',action='store_true',help='Verify the management ZIP with the original Linked player and server logs')
    p.add_argument('--venue-field-evidence',action='store_true',help='Verify full sealed admission evidence for both original venue End batches')
    p.add_argument('--venue-concurrent-roster-seconds', type=int, help='Require this many recorded seconds of concurrent 25-seat play in both sealed batches')
    p.add_argument('--check-venue-field-ui',action='store_true',help='Download the original current and earlier field bundles from the shipped console')
    p.add_argument('--check-room-readiness',action='store_true',help='Verify live aggregate pose counts from the management package in both modes')
    p.add_argument('--check-room-observer',action='store_true',help='Verify room-scoped observation and instant replay on the original Linked source')
    p.add_argument('--check-room-participation',action='store_true',help='Disconnect and restore one original VR admission in each five-room mode')
    p.add_argument('--check-room-endpoints',action='store_true',help='Verify real published UDP endpoints in the room cards and scoped API')
    p.add_argument('--check-room-clocks', action='store_true', help='Verify room clocks and the original pause/resume boundaries in both modes')
    p.add_argument('--check-venue-phase', action='store_true', help='Verify whole-venue pause and resume against both native topologies')
    p.add_argument('--check-venue-begin', action='store_true', help='Start both native topologies with one witnessed Begin per topology')
    p.add_argument('--check-venue-tracking-gate', action='store_true', help='Reject full tracking Begin while the same native roster is otherwise ready')
    p.add_argument('--check-venue-end', action='store_true', help='End each native topology in one batch and read its original archives')
    p.add_argument('--check-venue-reports', action='store_true', help='Verify the original reports ZIP for each native End batch')
    p.add_argument('--check-venue-replay-ui', action='store_true', help='Open the original native archives through the shipped console')
    p.add_argument('--check-venue-history-ui', action='store_true', help='Reopen and download the earlier batch after the newer native round')
    p.add_argument('--check-venue-environment', action='store_true', help='Confirm two batch environment changes in each native topology')
    p.add_argument('--check-venue-enemies', action='store_true', help='Use venue enemy policy to enable and stop native attacks')
    p.add_argument('--check-layout-preview',action='store_true',help='Load a saved barricade opening and compare its preview with native world geometry')
    p.add_argument('--check-room-reports',action='store_true',help='Verify scoped Linked CSVs and the ZIP against the full sealed native report')
    p.add_argument('--check-room-combat',action='store_true',help='Require actual enemy damage on every original admission and reconcile each replay frame and final report')
    p.add_argument('--check-hardware-feedback',action='store_true',help='Match live room feedback to the native combat reports')
    p.add_argument('--hardware-simulator-package',type=Path,help='Pass native live feedback through this extracted mock gateway package')
    p.add_argument('--prepare-independent-set',action='store_true',help='Prepare the five independent native sessions in one management request')
    p.add_argument('--check-independent-room-missions',action='store_true',help='Assign a different saved VR mission to every independent room and verify the accepted native world')
    p.add_argument('--mission-template',type=Path,help='Check and save an exported VR mission template, then run both native topologies with it')
    p.add_argument('--check-interrupted-replay', action='store_true', help='Play the saved native prefix after the owned launcher is killed')
    p.add_argument('--check-managed-mr', action='store_true', help='Verify the MR alignment startup gate, desktop rejection and Preparing seal')
    p.add_argument('--mr-venue-bundle-only', action='store_true', help='Verify both MR venue exports from native publishers, without starting desktop players')
    p.add_argument('--mixed-venue-bundle-only', action='store_true', help='Verify a mixed five-room console ZIP and mapped mock Quest deployment from native publishers')
    p.add_argument('--openxr-mock-only', action='store_true', help='Verify a packaged graphical OpenXR client with the installed Unity mock runtime')
    p.add_argument('--check-openxr-reconnect', action='store_true', help='Interrupt the tracked UDP client and reload its ticket with the mock right Vive menu button')
    p.add_argument('--check-openxr-revocation', action='store_true', help='Reject a revoked OpenXR ticket when the same seat receives a new admission')
    p.add_argument('--openxr-mock-pose-dll', type=Path, help='Compiled tests/fixtures/openxr-mock-pose.c for the OpenXR mock check')
    p.add_argument('--check-mapped-quest', action='store_true', help='Use full and five-seat mock ADB maps with each native MR venue export')
    p.add_argument('--check-live-reinforcement', action='store_true', help='Verify a native server accepts only supported live enemy targets and records the result')
    args=p.parse_args()
    if os.name!='nt':p.error('Actual Windows processes required')
    if args.check_mapped_quest and not args.mr_venue_bundle_only:p.error('--check-mapped-quest requires --mr-venue-bundle-only')
    if args.check_room_endpoints and not (args.check_vr_venue_tickets or args.mixed_venue_bundle_only):
        p.error('--check-room-endpoints requires --check-vr-venue-tickets or --mixed-venue-bundle-only')
    venue_only = args.mr_venue_bundle_only or args.mixed_venue_bundle_only
    if args.mr_venue_bundle_only and args.mixed_venue_bundle_only:p.error('Choose a single venue bundle check')
    if args.openxr_mock_only and (venue_only or not args.player_package):
        p.error('--openxr-mock-only requires a player package and its own native room')
    if args.check_openxr_reconnect and (not args.openxr_mock_only or args.game_address is not None):
        p.error('--check-openxr-reconnect requires --openxr-mock-only on loopback')
    if args.check_openxr_revocation and (not args.openxr_mock_only or args.check_openxr_reconnect):
        p.error('--check-openxr-revocation requires --openxr-mock-only without --check-openxr-reconnect')
    if args.check_venue_openxr and (venue_only or args.openxr_mock_only or not args.check_quest_vr_partial_map or args.check_room_participation):
        p.error('--check-venue-openxr requires --check-quest-vr-partial-map and its own venue participation check')
    if (args.openxr_mock_only or args.check_venue_openxr) != bool(args.openxr_mock_pose_dll):
        p.error('Supply --openxr-mock-pose-dll with --openxr-mock-only or --check-venue-openxr')
    if venue_only:
        if not args.game_address or args.player_package:p.error('The venue bundle check needs --game-address and no player package')
    elif not args.openxr_mock_only and bool(args.player_package)!=bool(args.game_address):p.error('Provide --player-package and --game-address together')
    if args.check_lan_preflight and not args.player_package:
        p.error('--check-lan-preflight requires the three-package check')
    if args.check_vr_venue_tickets and not args.player_package:
        p.error('--check-vr-venue-tickets requires the three-package check')
    if args.check_quest_vr_deploy and not args.check_vr_venue_tickets:
        p.error('--check-quest-vr-deploy requires --check-vr-venue-tickets')
    if args.check_quest_vr_partial_map and (not args.check_vr_venue_tickets or args.check_quest_vr_deploy):
        p.error('--check-quest-vr-partial-map requires --check-vr-venue-tickets without the full Quest fleet check')
    if args.check_windows_venue_staging and not (args.check_quest_vr_partial_map or args.mixed_venue_bundle_only):
        p.error('--check-windows-venue-staging requires --check-quest-vr-partial-map or --mixed-venue-bundle-only')
    if args.peer_diagnostics and not args.player_package:p.error('--peer-diagnostics requires the three-package check')
    if args.field_evidence and not args.peer_diagnostics:p.error('--field-evidence requires --peer-diagnostics')
    if args.venue_field_evidence and not (args.field_evidence and args.check_venue_end):
        p.error('--venue-field-evidence requires --field-evidence and --check-venue-end')
    if args.venue_concurrent_roster_seconds is not None and (not args.venue_field_evidence or not 1 <= args.venue_concurrent_roster_seconds <= 90):
        p.error('--venue-concurrent-roster-seconds requires --venue-field-evidence and 1..90 seconds')
    if args.check_venue_field_ui and not args.venue_field_evidence:
        p.error('--check-venue-field-ui requires --venue-field-evidence')
    if args.check_room_readiness and not args.player_package:p.error('--check-room-readiness requires five players per room')
    if args.check_room_observer and not args.player_package:p.error('--check-room-observer requires the three-package check')
    if args.check_room_participation and (not args.check_room_readiness or args.peer_diagnostics):
        p.error('--check-room-participation requires --check-room-readiness without the one-connection peer diagnostics check')
    if args.check_room_clocks and not args.player_package:p.error('--check-room-clocks requires five players per room')
    if args.check_venue_phase and not args.check_room_clocks:p.error('--check-venue-phase requires --check-room-clocks')
    if args.check_venue_begin and not args.player_package:p.error('--check-venue-begin requires the three-package check')
    if args.check_venue_tracking_gate and not args.check_venue_begin:p.error('--check-venue-tracking-gate requires --check-venue-begin')
    if args.check_venue_end and (not args.player_package or args.observe_closure_ui):
        p.error('--check-venue-end requires the three-package check and its own End path')
    if args.check_venue_reports and (not args.check_venue_end or not args.check_room_reports):
        p.error('--check-venue-reports requires --check-venue-end and --check-room-reports')
    if args.check_venue_replay_ui and not args.check_venue_end:
        p.error('--check-venue-replay-ui requires --check-venue-end')
    if args.check_venue_history_ui and not (args.check_venue_replay_ui and args.check_venue_reports):
        p.error('--check-venue-history-ui requires --check-venue-replay-ui and --check-venue-reports')
    if args.check_venue_environment and not args.player_package:
        p.error('--check-venue-environment requires the three-package check')
    if args.check_venue_enemies and not args.check_room_combat:
        p.error('--check-venue-enemies requires --check-room-combat')
    if args.check_room_reports and not args.player_package:p.error('--check-room-reports requires the three-package check')
    if args.check_room_combat and not args.check_room_reports:p.error('--check-room-combat requires --check-room-reports')
    if args.check_hardware_feedback and not args.check_room_combat:p.error('--check-hardware-feedback requires --check-room-combat')
    openxr_hardware=bool(args.openxr_mock_only and args.hardware_simulator_package)
    if args.hardware_simulator_package and not (args.check_hardware_feedback or openxr_hardware):
        p.error('--hardware-simulator-package requires --check-hardware-feedback or --openxr-mock-only')
    if args.prepare_independent_set and not args.player_package:p.error('--prepare-independent-set requires the player package')
    if args.check_independent_room_missions and (not args.prepare_independent_set or args.check_layout_preview or args.check_room_combat):
        p.error('--check-independent-room-missions requires --prepare-independent-set and its own mission fixtures')
    if args.mission_template and (not args.prepare_independent_set or venue_only or args.openxr_mock_only
            or args.check_independent_room_missions or args.check_layout_preview or args.check_room_combat):
        p.error('--mission-template requires --prepare-independent-set and the ordinary two-topology check')
    address='127.0.0.1'
    if args.game_address:
        if not any(args.game_address in ipaddress.IPv4Network(net) for net in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')):
            p.error('--game-address must be a local private IPv4 address')
        address=str(args.game_address)
        try:free(socket.SOCK_DGRAM,address)
        except OSError:p.error('--game-address must be assigned to this PC')
    folder=args.package.resolve();manifest=package.verify(folder);assert manifest['launcherSourceSha256']==package.digest(ROOT/'tools/WindowsServerLauncher/ServerLauncher.cs')
    player_folder=None
    openxr_mock=None
    if args.player_package:
        player_folder=args.player_package.resolve()
        player_package=module('portable_player_package','package-windows-player.py')
        player_manifest=player_package.verify(player_folder)
        if player_manifest['build']['sourceFingerprint']!=manifest['build']['sourceFingerprint']:
            p.error('Player and server packages must share the Unity build source')
    if args.openxr_mock_only or args.check_venue_openxr:
        unity=ROOT/'clients/unity'
        mock_package_version=read(unity/'Packages/manifest.json')['dependencies']['com.unity.xr.openxr']
        candidates=[path for path in (unity/'Library/PackageCache').glob('com.unity.xr.openxr@*')
                    if (path/'package.json').is_file() and read(path/'package.json')['version']==mock_package_version]
        if len(candidates)!=1:
            p.error('Restore the project-pinned Unity OpenXR package in the Editor first')
        openxr_mock=candidates[0]/'Runtime/MockRuntime/unity-mock-runtime.json'
        runtime_file=openxr_mock.parent/'windows/x64/mock_runtime.dll'
        expected={'api_version':'1.0','name':'Unity Mock Runtime','library_path':r'.\windows\x64\mock_runtime.dll'}
        if not openxr_mock.is_file() or read(openxr_mock).get('runtime')!=expected or not runtime_file.is_file():
            p.error('The pinned Unity OpenXR package does not contain the expected Windows mock runtime')
    control.package.verify(args.control_package);out=ROOT/'artifacts/server-package-checks'/('run-'+uuid.uuid4().hex);out.mkdir(parents=True,exist_ok=False);runtime=args.runtime_root.resolve()/out.name;runtime.mkdir(parents=True,exist_ok=False)
    (ROOT/'artifacts/server-package-checks-latest-path.txt').write_text(str(out),encoding='utf-8');print(json.dumps({'stage':'starting','directory':str(out)}),flush=True)
    env=dict(os.environ);env.update(PATH=str(Path(os.environ['WINDIR'])/'System32'),DOTNET_ROOT=str(runtime/'absent-dotnet'),DOTNET_MULTILEVEL_LOOKUP='0');exe=folder/'Launch-Server.exe';control_exe=args.control_package.resolve()/'Start-Control.exe';data=runtime/'control';checks=[];runners=[];clients=[];cleanup=[];witnesses=[];api=None;api_witness=None;keys=None;sessions=[];rounds=[];observer=None;observer_log=None;observer_out=out/'closure-ui';observer_stop=out/'closure-ui-stop.request';observer_entry=None
    hardware_processes=[]
    reconnect_gates=[]
    if args.hardware_simulator_package:
        hardware=args.hardware_simulator_package.resolve()
        hardware_manifest=module('native_hardware_package','package-hardware-simulator.py').verify(hardware)
        if hardware_manifest['mode']!='OfflineAndLiveSimulation':p.error('Use a live hardware simulator package')
        dotnet=shutil.which('dotnet')
        if not dotnet:p.error('The hardware simulator requires .NET 10')
        mock_env={key:value for key,value in os.environ.items() if not key.lower().startswith('operatorkeys__') and key.lower() not in
            ('operatorkeyfile','playerticketsigningkey','controlpipetoken','vr_command_room_key')}
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
    def request(path,body=None,role='Master',method=None,expected=200,admission=None,raw_response=False,request_id=None):
        h={'Authorization':'Bearer '+keys[role]};h.update({'Content-Type':'application/json'} if body is not None else {})
        if admission:h['If-Match-Admission']=admission
        if request_id:h['Idempotency-Key']=request_id
        if isinstance(body,bytes):h['Content-Type']='application/octet-stream'
        req=urllib.request.Request(uri+path,data=body if isinstance(body,bytes) or body is None else json.dumps(body).encode(),headers=h,method=method)
        try:
            with urllib.request.urlopen(req,timeout=5) as r:code=r.status;raw=r.read();headers=r.headers
        except urllib.error.HTTPError as e:code=e.code;raw=e.read();headers=e.headers
        if code!=expected:raise RuntimeError(path+' HTTP '+str(code))
        if raw_response:return raw,headers
        if path.endswith('/report.csv'):return raw.decode('utf-8-sig')
        return json.loads(raw) if raw else None
    def command(session,action):return request('/api/sessions/'+session+'/commands',{'commandId':str(uuid.uuid4()),'action':action})
    def config(session,port=None,**extra):return dict({'role':'Server','managementApiUrl':uri,'gameServerKey':keys['GameServer'],'sessionId':session,'address':address,'listenAddress':address,'port':port or free(socket.SOCK_DGRAM,address)},**extra)
    def call(label,options,good=False,report=None):
        result=out/(label+'.json') if report is None else report
        child=subprocess.run([str(exe),*map(str,options),'--report',str(result)],env=env,cwd=out,timeout=45)
        check(child.returncode==(0 if good else 1),label+' original exit')
        if report is None:
            value=read(result);check(value['complete']==good,label+' complete flag')
        return result
    def rejected(label,value,**options):
        file=runtime/(label+'.json');file.write_text(json.dumps(value),encoding='utf-8');work=runtime/(label+'-work');ready=out/(label+'-ready.json')
        call(label,['--run',file,'--work',work,'--seconds',options.get('seconds',60),'--ready-report',ready,*options.get('extra',())]);check(not work.exists() and not ready.exists(),label+' creates no native world')
    def save_mission(label, *, auto_attack=False, enemy_count=1, experience='VR', props=None):
        if props is None:
            props=[{'assetId':'sandbag','position':{'x':x,'y':0,'z':-1},'yawDegrees':0}
                   for x in (-5,-3,-1,3,5)] if args.check_layout_preview else []
        return request('/api/missions',{'name':'Portable '+label,'briefing':'Owned PC package fixture','durationSeconds':600,'environment':{'mode':experience,'weather':'Clear','timeOfDay':'Day','lightning':False},'enemies':{'count':enemy_count,'behavior':'Hold','autoAttack':auto_attack},'props':props},expected=201)
    def create(rooms,label, **options):
        mission=save_mission(label,**options)
        state=request('/api/sessions',{'missionId':mission['id'],'mode':'Linked' if len(rooms)==5 else 'Independent','roomIds':rooms},expected=201);sessions.append(state['id']);return state

    def verify_template_world(entry, mission, running):
        info=request(f"/api/sessions/{entry['sessionId']}/world")
        definition=mission['definition']; environment=definition['environment']; enemies=definition['enemies']
        header=info['header']; packet=running['packet']; frame=packet['frame']
        expected=[]
        for room in header['roomIds']:
            for prop in definition['props']:
                feet=prop['position']
                expected.append((room,prop['assetId'],feet['x']+(room-3)*14,feet['y'],feet['z'],prop['yawDegrees']))
        actual=[(prop['roomId'],prop['kind'].lower(),prop['feet']['x'],prop['feet']['y'],prop['feet']['z'],prop['yaw'])
                for prop in header['props']]
        def matches(left,right):
            return left[:2]==right[:2] and all(abs(a-b)<.0001 for a,b in zip(left[2:],right[2:]))
        check(header['missionDurationSeconds']==definition['durationSeconds'] and packet['weather']==environment['weather']
              and packet['lightning']==environment['lightning'] and frame['night']==(environment['timeOfDay']=='Night')
              and frame['behavior']==enemies['behavior'] and frame['autoAttack']==enemies['autoAttack']
              and len(frame['enemies'])==enemies['count'] and len(actual)==len(expected)
              and all(matches(left,right) for left,right in zip(actual,expected)),
              entry['label']+' native duration, environment, enemies and cover match the imported template')
        save(entry['label']+'-template-world.json',{'missionId':mission['id'],'header':header,'runningSequence':packet['sequence']})

    def verify_lan_preflight(value, label):
        powershell = Path(os.environ['WINDIR']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        script = [str(powershell), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'RemoteSigned',
                  '-File', str(ROOT/'scripts/check-lan-udp.ps1')]
        options = {'cwd': out, 'creationflags': subprocess.CREATE_NO_WINDOW}
        with tempfile.TemporaryDirectory(prefix='udp-key-', dir=runtime) as directory:
            key = str(Path(directory)/'probe.key')
            subprocess.run(script + ['-NewKey', '-KeyFile', key], capture_output=True, check=True, timeout=10, **options)
            common = ['-KeyFile', key, '-LocalAddress', value['address'], '-PeerAddress', value['address'],
                      '-Port', str(value['port']), '-Count', '3']
            log_path = out/(label+'-lan-listener.ndjson')
            with log_path.open('xb') as log:
                listener = subprocess.Popen(script + ['-Mode', 'Listen', '-Seconds', '15', *common],
                                            stdout=log, stderr=subprocess.STDOUT, **options)
                try:
                    def listening():
                        if listener.poll() is not None: raise RuntimeError('UDP preflight listener exited before its bind')
                        text = log_path.read_text(encoding='utf-8')
                        return json.loads(text.splitlines()[0]) if '\n' in text else None
                    ready = wait(listening, 10, label+' UDP preflight bind')
                    if ready != {'version': 1, 'stage': 'listening', 'localAddress': value['address'],
                                 'peerAddress': value['address'], 'port': value['port']}:
                        raise RuntimeError('UDP preflight reported another endpoint')
                    probe = subprocess.run(script + ['-Mode', 'Probe', *common], capture_output=True, check=True,
                                           encoding='utf-8', timeout=10, **options)
                    if listener.wait(timeout=17) != 0: raise RuntimeError('UDP preflight listener did not finish')
                finally:
                    if listener.poll() is None: listener.kill(); listener.wait(timeout=10)
            reply = json.loads(probe.stdout)
            final = json.loads(log_path.read_text(encoding='utf-8').splitlines()[-1])
            probe_path = out/(label+'-lan-probe.json')
            probe_path.write_text(probe.stdout, encoding='utf-8')
            pair = json.loads(subprocess.check_output(script + ['-ListenerReport', str(log_path), '-ProbeReport', str(probe_path)],
                                                      encoding='utf-8', timeout=10, **options))
        check(all(item['complete'] and item['port'] == value['port'] and item['matched'] == item['requested'] == 3
                  and item['scope'] == 'authenticated-udp-only' for item in (reply, final))
              and [sample['sample'] for sample in reply['samples']] == [1, 2, 3]
              and all(sample['roundTripMs'] >= 0 for sample in reply['samples']),
              label+' Windows PowerShell UDP preflight exchanged all three authenticated samples and exited')
        check(pair['complete'] is True and pair['stage'] == 'pair-verified' and pair['port'] == value['port'] and pair['matched'] == 3
              and pair['exchangeSha256'] == reply['exchangeSha256'] == final['exchangeSha256'],
              label+' original listener and probe reports match the same authenticated exchange')
        return {'listener': final, 'probe': reply, 'pair': pair}

    def launch(state,label, *, listen_address=None, verify_layout=True):
        value=config(state['id'], listenAddress=listen_address or address);file=runtime/(label+'.json');file.write_text(json.dumps(value),encoding='utf-8');ready=out/(label+'-ready.json');report=out/(label+'-final.json');work=runtime/(label+'-work')
        preflight = verify_lan_preflight(value, label) if args.check_lan_preflight and label in ('room-1', 'room-2', 'room-3', 'room-4', 'room-5', 'linked') else None
        diagnostics=args.peer_diagnostics and (label=='linked' or (args.venue_field_evidence and label in {f'room-{i}' for i in range(1,6)}))
        options=['--peer-diagnostics','on'] if diagnostics else []
        child=subprocess.Popen([str(exe),'--run',str(file),'--work',str(work),'--seconds','600','--ready-report',str(ready),'--report',str(report),*options],cwd=out,env=env);entry={'process':child,'readyPath':ready,'reportPath':report,'work':work,'config':value,'label':label,'sessionId':state['id'],'witness':None,'peerDiagnostics':diagnostics};runners.append(entry)
        def is_ready():
            if child.poll() is not None:raise RuntimeError('Server launcher exited before ready '+label)
            return read(ready) if ready.exists() else None
        info=wait(is_ready,100,label+' ready');w=control.ChildWitness(info['childPid']);entry['witness']=w;witnesses.append(w);entry['ready']=info
        check(info['peerDiagnosticsEnabled'] is diagnostics, label+' ready report records the explicit diagnostics choice')
        if args.check_layout_preview and verify_layout:entry['layoutSession']=state
        endpoint=request('/api/sessions/'+state['id']+'/connection-endpoint');check(info['streamId']==endpoint['streamId'] and info['port']==endpoint['port'] and endpoint['address']==address,label+' original endpoint / child')
        binding = info['udpBinding']
        observed = datetime.fromisoformat(binding['observedAtUtc'])
        check(binding['processId'] == info['childPid'] and binding['address'] == value['listenAddress'] and binding['port'] == value['port']
              and observed <= datetime.fromisoformat(endpoint['createdAtUtc']), label + ' owned binding observed before endpoint publication')
        netstat = Path(os.environ['WINDIR']) / 'System32/netstat.exe'
        rows = subprocess.check_output([str(netstat), '-ano', '-p', 'udp'], cwd=out, timeout=10, encoding='ascii', errors='ignore').splitlines()
        local = f"{binding['address']}:{binding['port']}"
        pid = str(binding['processId'])
        check(any(len(parts) >= 4 and parts[0] == 'UDP' and parts[1] == local and parts[-1] == pid
                  for parts in map(str.split, rows)), label + ' independent Windows UDP owner check')
        if preflight:
            check((binding['address'], binding['port']) == (preflight['listener']['localAddress'], preflight['listener']['port']),
                  label+' original Unity child owns the exact endpoint released by the UDP preflight')
            save(label+'-lan-preflight.json', dict(preflight, gameBinding=binding, scope='same-host'))
        return entry
    def player(entry,room):
        state=request('/api/sessions/'+entry['sessionId']+'/players',{'playerId':str(uuid.uuid4()),'roomId':room,'name':'Portable server room '+str(room),'headset':'Quest3'},role='Room'+str(room));person=next(x for x in state['players'] if x['roomId']==room)
        invitation=request('/api/sessions/'+state['id']+'/players/'+person['id']+'/join-ticket',{},role='Room'+str(room),admission=person['admissionId']);file=runtime/(entry['label']+'-client-'+str(room)+'.json');file.write_text(json.dumps({'role':'Client','address':address,'port':entry['ready']['port'],'joinTicket':invitation['ticket']}),encoding='utf-8');log=runtime/(file.stem+'.log')
        child=subprocess.Popen([str(folder/'Runtime/VrCommand.exe'),'-batchmode','-nographics','-job-worker-count','2','-logFile',str(log),'--vr-config',str(file)],cwd=runtime,env=env,creationflags=subprocess.CREATE_NO_WINDOW);client={'process':child,'log':log,'player':person,'sessionId':state['id']};clients.append(client);return client
    def prepare_room_roster(entry,room):
        path='/api/sessions/'+entry['sessionId']
        role='Room'+str(room)
        for seat in range(1,6):
            headset = 'ViveXr' if args.check_quest_vr_partial_map and seat in (2, 4) else 'Quest3'
            state=request(path+'/players',{'playerId':str(uuid.uuid4()),'roomId':room,
                'name':f'Portable room {room} seat {seat}','headset':headset},role=role)
        return sorted((p for p in state['players'] if p['roomId']==room),key=lambda p:p['seat'])
    def room_players(entry,room,people=None,raw=None,*,windows_files=None):
        path='/api/sessions/'+entry['sessionId']
        role='Room'+str(room)
        if people is None: people=prepare_room_roster(entry,room)
        names=[f'room-{room:02}-seat-{seat:02}.json' for seat in range(1,6)]
        destination={'address':address,'port':entry['ready']['port']}
        if raw is None:
            raw,headers=request(path+f'/rooms/{room}/join-ticket-bundle',
                dict(destination,players=[{'playerId':p['id'],'admissionId':p['admissionId']} for p in people]),
                role=role,raw_response=True)
            check(headers.get_content_type()=='application/zip' and headers['Cache-Control']=='no-store',
                entry['label']+f' room {room} no-store ticket download')
        directory=runtime/(entry['label']+f'-bundle-{room}')
        directory.mkdir()
        (directory/'download.zip').write_bytes(raw)
        prepared=[]
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            check(archive.namelist()==names and [p['seat'] for p in people]==list(range(5)),
                entry['label']+f' room {room} exact five seats')
            for name,person in zip(names,people,strict=True):
                content=archive.read(name)
                value=json.loads(content)
                if value!={'role':'Client',**destination,'joinTicket':value.get('joinTicket')} or not value['joinTicket']:
                    raise ValueError('Player connection file differs from the advertised endpoint')
                file = (windows_files or {}).get((room, person['seat'] + 1))
                if file is None:
                    file = directory/name
                    file.write_bytes(content)
                elif file.read_bytes() != content:
                    raise ValueError('Windows staging changed the original connection file')
                prepared.append((person,file))
        launched=[]
        for person,file in prepared:
            mock=None
            if args.check_venue_openxr and (room,person['seat'])==(5,1):
                tracking_loss=runtime/(entry['label']+'-openxr-loss.request')
                mock=openxr_environment(entry['label']+'-openxr-runtime.json',tracking_loss)
                entry['openxrLossMarker']=tracking_loss
                entry['openxrPlayerId']=person['id']
            launched.append(packaged_player(entry,person,file,mock=mock))
        return launched

    def room_endpoint_descriptor(preview):
        if not args.check_room_endpoints: return {}
        rows = request('/api/rooms/readiness')['rooms']
        endpoints = {row['roomId']: row['endpoint'] for row in preview['rooms']}
        check({row['roomId']: row['endpoint'] for row in rows} == endpoints
              and all([(row['roomId'], row['endpoint']) for row in request('/api/rooms/readiness', role=f'Room{room}')['rooms']]
                      == [(room, endpoint)] for room, endpoint in endpoints.items()),
              'master and room desks receive only their original published UDP endpoints')
        return {'expectedEndpoints': [{'roomId': room, 'address': endpoint['address'], 'port': endpoint['port']}
                                      for room, endpoint in endpoints.items()]}

    def venue_ticket_players(staged, linked):
        mode = 'Linked' if linked else 'Independent'
        label = mode.lower()
        preview = request('/api/vr-deployment/venue')
        check(preview['ready'] and preview['topology'] == mode
              and all(row['roomId'] == room and row['sessionId'] == entry['sessionId']
                      and (row['endpoint']['address'], row['endpoint']['port'], row['endpoint']['streamId'])
                      == (address, entry['ready']['port'], entry['ready']['streamId'])
                      and [seat['admissionId'] for seat in row['seats']] == [person['admissionId'] for person in people]
                      for row, (entry, room, people) in zip(preview['rooms'], staged, strict=True)),
              mode+' venue previews all current admissions on their original native UDP endpoints')
        node = shutil.which('node')
        if not node: raise RuntimeError('Node is required for the shipped venue ticket test')
        descriptor = runtime / (label+'-venue-tickets-private.json')
        archive_path = runtime / (label+'-vr-venue-connections.zip')
        output = out / (label+'-vr-venue-tickets-ui.json')
        descriptor.write_text(json.dumps({'base':uri,'masterKey':keys['Master'],'mode':mode,**room_endpoint_descriptor(preview)}),encoding='utf-8')
        with (out/(label+'-vr-venue-tickets-ui.log')).open('xb') as log:
            subprocess.run([node, str(ROOT/'tests/browser/check-vr-venue-tickets-native.cjs'), str(descriptor),
                            str(archive_path), str(output)], stdout=log, stderr=subprocess.STDOUT, check=True, timeout=65)
        if args.check_room_endpoints:
            check(read(output)['verifiedRoomEndpoints'] == 5, mode+' shipped room cards show five original UDP endpoints')
        files = []
        with zipfile.ZipFile(archive_path) as archive:
            manifest = json.loads(archive.read('venue.json'))
            expected = [{'roomId':room,'sessionId':entry['sessionId'],'address':address,'port':entry['ready']['port'],
                         'ticketsZip':f'room-{room:02}-connections.zip',
                         'seats':[{'seat':person['seat']+1,'name':person['name']} for person in people]}
                        for entry,room,people in staged]
            check(read(output)['complete'] and manifest == {'version':1,'mode':'VR','topology':mode,'rooms':expected}
                  and archive.namelist() == ['venue.json', *[row['ticketsZip'] for row in expected]]
                  and archive.testzip() is None, mode+' shipped browser ZIP includes the five original rooms and no other files')
            files = [archive.read(row['ticketsZip']) for row in expected]
        windows_files = {}
        if args.check_quest_vr_deploy or args.check_quest_vr_partial_map:
            before = request('/api/sessions')
            pwsh = shutil.which('pwsh')
            if not pwsh: raise RuntimeError('PowerShell is required for the Quest deployment check')
            deploy = [pwsh, '-NoProfile', '-File', str(ROOT/'scripts/deploy-quest.ps1'),
                      '-VenueBundle', str(archive_path), '-ManagementApi', uri]
            environment = {**os.environ, 'VR_COMMAND_MASTER_KEY': keys['Master']}
            with tempfile.TemporaryDirectory(prefix='quest-vr-', dir=runtime) as scratch:
                destination = Path(scratch).resolve()
                if destination.parent != runtime: raise RuntimeError('Invalid owned deployment scratch directory')
                sample = '1' if args.check_quest_vr_partial_map else '2'
                seat = json.loads(subprocess.check_output([*deploy, '-RoomId', '4', '-Seat', sample, '-CheckOnly'],
                    env=environment, timeout=25, encoding='utf-8', cwd=destination))
                check(seat['roomId']==4 and seat['seat']==int(sample) and seat['mode']=='VR' and seat['headset']=='Quest3'
                      and seat['managementVerified'] and seat['alignmentSha256'] is None and not list(destination.iterdir()),
                      mode+' Quest tool checks the original VR seat using the live game endpoint without ADB')
                save(f'vr-venue-{label}-quest-seat.json', seat)
                verify_mapped_quest(deploy, destination, environment, archive_path.read_bytes(), mode, partial=args.check_quest_vr_partial_map)
            if args.check_windows_venue_staging:
                mapped = [{'roomId': room, 'seat': person['seat'] + 1,
                           'station': f"R{room}-S{person['seat'] + 1}"}
                          for _, room, people in staged for person in people if person['headset'] == 'ViveXr']
                seat_map = runtime / f'{label}-windows-map.json'
                seat_map.write_text(json.dumps({'version': 1, 'seats': mapped[::-1]}), encoding='utf-8')
                staged_path = runtime / f'{label}-windows'
                command = [*deploy, '-WindowsSeatMap', str(seat_map), '-WindowsOutputDirectory', str(staged_path)]
                report = json.loads(subprocess.check_output(command, env=environment, timeout=25, encoding='utf-8'))
                expected_rows = [{**row, 'file': f"pc-{row['station']}-room-{row['roomId']:02}-seat-{row['seat']:02}.json",
                                  'endpoint': f"{address}:{staged[row['roomId'] - 1][0]['ready']['port']}"} for row in mapped]
                check(report['topology'] == mode and report['managementVerified'] and len(mapped) == 10
                      and [{k: v for k, v in row.items() if k != 'expiresAtUtc'} for row in report['seats']] == expected_rows
                      and {file.name for file in staged_path.iterdir()} == {row['file'] for row in expected_rows},
                      mode+' stages exactly the ten live-verified VIVE XR seats')
                windows_files = {(row['roomId'], row['seat']): staged_path / row['file'] for row in expected_rows}
                save(f'vr-venue-{label}-windows-staging.json', report)
            check(request('/api/sessions') == before, mode+' deployment checks do not change the original venue roster')
        launched = [client for (entry, room, people), raw in zip(staged, files, strict=True)
                    for client in room_players(entry, room, people, raw, windows_files=windows_files)]
        if windows_files:
            check({Path(client['configPath']) for client in launched if client['player']['headset'] == 'ViveXr'}
                  == set(windows_files.values()), mode+' Windows launchers consumed the original staged files')
        return launched

    def packaged_player(entry,person,file, *, mock=None):
        log=file.with_suffix('.log')
        report=file.with_suffix('.launcher.json')
        flags=['--headless'] if mock is None else ['--openxr']
        environment=env if mock is None else {**env,**mock}
        child=subprocess.Popen([str(player_folder/'Launch-Player.exe'),'--config',str(file),'--launch',
            *flags,'--wait','--log',str(log),'--report',str(report)],cwd=runtime,env=environment)
        client={'process':child,'log':log,'player':person,'sessionId':entry['sessionId'],
            'launcherReport':report,'witness':None,'configPath':file}
        clients.append(client)
        def started():
            if child.poll() is not None:raise RuntimeError('Player launcher exited before admission')
            return read(report) if report.exists() else None
        info=wait(started,30,'owned player launcher')
        if info['status']!='started':raise RuntimeError('Player launcher did not report a live child')
        client['witness']=control.ChildWitness(info['processId'],allow_terminate=True)
        client['nativePid']=info['processId']
        return client
    def stop_player(client):
        child=client['process']
        report=client.get('launcherReport')
        if report:
            witness=client['witness']
            if witness is None and child.poll() is None:
                info=wait(lambda:read(report) if report.exists() else None,10,'player cleanup ownership')
                if info['status']=='started':
                    witness=control.ChildWitness(info['processId'],allow_terminate=True)
                    client['witness']=witness
                    client['nativePid']=info['processId']
            if witness:
                witness.terminate()
                witness.wait()
                child.wait(timeout=15)
                status=read(report)
                if child.returncode!=0 or status!={'status':'exited','processId':client['nativePid'],'exitCode':0}:
                    raise RuntimeError('Launcher did not confirm original player exit')
                witness.close()
                client['witness']=None
            elif not report.exists() or read(report)['status'] not in ('exited','rejected'):
                raise RuntimeError('Native player cleanup unknown')
        elif child.poll() is None:
            child.terminate()
        child.wait(timeout=15)
    def verify_delivery(entry,owners):
        manifest_entry = None
        world_journal = None
        server=(entry['work']/'server.log').read_text(encoding='utf-8',errors='replace')
        acks=[int(value) for value in re.findall(r'VR_SERVER_DEBRIEF_ACK id=(\d+)',server)]
        check(len(acks)==len(owners) and set(acks)=={c['connection'] for c in owners}
            and 'VR_SERVER_DEBRIEF_TIMEOUT ' not in server,entry['label']+' exact original server ACKs')
        if args.peer_diagnostics:
            peers=re.findall(r'^VR_SERVER_PEER id=(\d+) endpoint=(\S+)$',server,re.M)
            check('VR_SERVER_PEER_LIMIT' not in server,entry['label']+' no peer log overflow')
            if entry['peerDiagnostics']:
                check(len(peers)==len(acks) and {int(connection) for connection,_ in peers}==set(acks),
                    entry['label']+' exactly one UDP endpoint for every original acknowledged connection')
                session_path='/api/sessions/'+entry['sessionId']
                session_raw,_=request(session_path,raw_response=True)
                endpoint_raw,_=request(session_path+'/connection-endpoint',raw_response=True)
                (out/(entry['label']+'-session.json')).write_bytes(session_raw)
                (out/(entry['label']+'-endpoint.json')).write_bytes(endpoint_raw)
                session,endpoint=field.read_json(session_raw),field.read_json(endpoint_raw)
                statistics=field.read_json(field.content(out/(entry['label']+'-statistics.json')))
                if args.field_evidence:
                    route=session_path+'/field-evidence.zip'
                    raw,headers=request(route,raw_response=True)
                    check(headers.get_content_type()=='application/zip' and headers['Cache-Control']=='no-store'
                          and f'vr-command-field-v1-{entry["sessionId"]}.zip' in headers['Content-Disposition'],
                          entry['label']+' management ZIP headers and original session filename')
                    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                        check(archive.namelist()==['session.json','statistics.json','endpoint.json'] and archive.testzip() is None,
                              entry['label']+' management ZIP contains exactly three JSON records')
                        exported=[field.read_json(archive.read(name)) for name in archive.namelist()]
                    check(exported==[session,statistics,endpoint],entry['label']+' management ZIP matches the original sealed API data')
                    request(route,role='Room1',expected=403)
                    check(True,entry['label']+' room controller denied the full evidence ZIP')
                    evidence_zip=out/(entry['label']+'-field-evidence.zip')
                    evidence_zip.write_bytes(raw)
                    session,statistics,endpoint=exported
                    world_journal = entry['work']/'telemetry'/(entry['sessionId']+'.worldlog')
                    manifest_entry={'evidenceZip':str(evidence_zip),'launcherReport':str(entry['reportPath']),
                        'serverLog':str(entry['work']/'server.log'),'worldJournal':str(world_journal),
                        'players':[{'address':address,'log':str(c['log'])} for c in owners]}
                preflight = (out/(entry['label']+'-lan-listener.ndjson'), out/(entry['label']+'-lan-probe.json')) if args.check_lan_preflight else None
                if manifest_entry is not None and preflight is not None:
                    manifest_entry['udpSourcePreflights'] = [dict(zip(('listener', 'probe'), map(str, preflight), strict=True))]
                ip=ipaddress.IPv4Address(address)
                result=field.verify('same-host',{ip},read(entry['reportPath']),session,statistics,endpoint,server,
                    [(ip,field.content(c['log'])) for c in owners], world_journal=world_journal,
                    udp_source_preflights=[preflight] if preflight is not None else None,
                    verify_player_sources=args.check_venue_openxr and world_journal is not None)
                save(entry['label']+'-field-results.json',result)
                check(result['serverAcknowledgements']==len(acks),entry['label']+' field report matches same-PC endpoints and sealed player results')
                if world_journal is not None:
                    check(result['worldJournal']['frames']==result['worldSequence'] and result['worldJournal']['runningFrames']>0,
                          entry['label']+' field report verifies the original closed world journal')
                if preflight is not None:
                    coverage = result['udpSourcePreflight']
                    check(coverage['observedSourceAddresses']==coverage['verifiedSourceAddresses']==1
                          and [pair['samples'] for pair in coverage['pairs']]==[3],
                          entry['label']+' field report binds the original UDP preflight to the server endpoint and accepted player sources')
            else:
                check('VR_SERVER_PEER' not in server,entry['label']+' default does not record UDP peers')
        raw,headers=request('/api/sessions/'+entry['sessionId']+'/report.csv',raw_response=True)
        rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'),newline='')))
        results={c['player']['id']:c['final'] for c in owners}
        check(headers.get_content_type()=='text/csv' and raw.startswith(b'\xef\xbb\xbf')
            and len(rows)==len(owners) and {r['playerId'] for r in rows}==set(results),
            entry['label']+' exact CSV roster')
        fields=('playerId','origin','sessionId','streamId')
        numbers=('throughSequence','finalStreamSequence','ammoUsed','shotsHit','kills',
            'damageTaken','hitsReceived','accuracyPercent','health')
        for row in rows:
            final=results[row['playerId']]
            if row['rowType']!='Player' or row['reportVersion']!='1' or int(row['playerRoomId'])!=final['roomId'] \
                or any(row[k]!=final[k] for k in fields) or any(Decimal(row[k])!=Decimal(str(final[k])) for k in numbers):
                raise ValueError('CSV row differs from the original sealed player result')
        (out/(entry['label']+'-report.csv')).write_bytes(raw)
        if args.check_room_reports and entry['label']=='linked':
            session_path='/api/sessions/'+entry['sessionId']
            prefix='vr-command-report-v1-'+entry['sessionId']
            expected_files={prefix+'.csv':raw}
            for room in range(1,6):
                scoped,scoped_headers=request(session_path+f'/rooms/{room}/report.csv',
                    role=f'Room{room}',raw_response=True)
                scoped_rows=list(csv.DictReader(io.StringIO(scoped.decode('utf-8-sig'),newline='')))
                expected=[dict(row,reportRoomId=str(room)) for row in rows if row['playerRoomId']==str(room)]
                check(len(expected)==5 and scoped_rows==expected and scoped_headers['Cache-Control']=='no-store'
                    and f'-room-{room:02}.csv' in scoped_headers['Content-Disposition'],
                    f'room {room} CSV matches its five original sealed Linked player rows')
                (out/f'linked-scoped-room-{room:02}.csv').write_bytes(scoped)
                expected_files[f'{prefix}-room-{room:02}.csv']=scoped
            request(session_path+'/rooms/2/report.csv',role='Room1',expected=403)
            reports,headers=request(session_path+'/reports.zip',raw_response=True)
            check(headers.get_content_type()=='application/zip' and headers['Cache-Control']=='no-store'
                  and f'vr-command-reports-v1-{entry["sessionId"]}.zip' in headers['Content-Disposition'],
                  'Linked battle ZIP headers and original session filename')
            with zipfile.ZipFile(io.BytesIO(reports)) as archive:
                check(archive.namelist()==list(expected_files) and archive.testzip() is None
                      and all(archive.read(name)==content for name,content in expected_files.items()),
                      'Linked battle ZIP matches the exact six CSVs from the original 25 player results')
            request(session_path+'/reports.zip',role='Room1',expected=403)
            (out/'linked-reports.zip').write_bytes(reports)
        save(entry['label']+'-delivery.json',{'serverAcknowledgedConnections':acks,
            'players':[{'playerId':c['player']['id'],'admissionId':c['player']['admissionId'],
                'roomId':c['player']['roomId'],'seat':c['player']['seat'],'connectionId':c['connection'],
                'nativePid':c['nativePid'],'launcherPid':c['process'].pid} for c in owners]})
        check(True,entry['label']+' CSV rows match sealed player results')
        return manifest_entry

    def verify_venue_field_evidence(mode, closed, entries):
        label = mode.lower()
        route = '/api/venue/closure/' + closed['requestId']
        raw, headers = request(route, raw_response=True)
        check(field.read_json(raw)['batch'] == closed and headers['Cache-Control'] == 'no-store',
              label + ' field evidence reads the exact sealed closure by original batch ID')
        closure_file = out / (label + '-field-closure.json')
        closure_file.write_bytes(raw)
        bundle_route = route + '/field-evidence.zip'
        bundle, headers = request(bundle_route, raw_response=True)
        request(bundle_route, role='Room1', expected=403)
        check(headers['Cache-Control'] == 'no-store' and headers.get_content_type() == 'application/zip'
              and f'vr-command-venue-field-v1-{closed["requestId"]}.zip' in headers['Content-Disposition'],
              label + ' field bundle uses the original batch filename and Master scope')
        names = ['linked.zip'] if mode == 'Linked' else [f'room-{room:02}.zip' for room in range(1, 6)]
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            check(archive.namelist() == ['closure.json', *names] and archive.testzip() is None
                  and field.read_json(archive.read('closure.json')) == field.read_json(raw)
                  and all(archive.read(name) == Path(entry['evidenceZip']).read_bytes() for name, entry in zip(names, entries)),
                  label + ' field bundle contains the original closure and exact individual ZIP bytes')
        bundle_file = out / (label + '-venue-field-evidence.zip')
        bundle_file.write_bytes(bundle)
        manifest_path = runtime / (label + '-field-manifest.json')
        common = {'version': 1, 'mode': mode, 'topology': 'same-host', 'serverIps': [address],
                  **({'verifyPlayerSources': True} if args.check_venue_openxr else {})}
        concurrent_seconds = args.venue_concurrent_roster_seconds
        if concurrent_seconds is not None:
            common['minimumConcurrentMilliseconds'] = concurrent_seconds * 1000
        evidence = dict(common, venueBundle=str(bundle_file),
                        sessions=[{key: value for key, value in entry.items() if key not in ('evidenceZip', 'players')}
                                  for entry in reversed(entries)],
                        windowsPlayers=[player for entry in reversed(entries) for player in reversed(entry['players'])])
        split = dict(common, closure=str(closure_file), sessions=entries)

        def run(manifest):
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            return subprocess.run([sys.executable, str(ROOT / 'scripts/verify-field-results.py'),
                                   '--venue-manifest', str(manifest_path)], capture_output=True, encoding='utf-8', timeout=45)

        result = run(evidence)
        if result.returncode:
            raise RuntimeError('Native venue field evidence rejected: ' + result.stderr.strip())
        summary = json.loads(result.stdout)
        original = run(split)
        check(original.returncode == 0 and json.loads(original.stdout) == summary,
              label + ' untouched venue ZIP and unordered Windows logs match the original split field summary')
        check(summary['consistent'] and summary['mode'] == mode and summary['players'] == summary['serverAcknowledgements'] == 25
              and summary['rooms'] == [{'roomId': room, 'players': 5, 'playersOutsideDeclaredServer': 0} for room in range(1, 6)]
              and not summary['physicalHostsVerified'] and not summary['networkCapacityAccepted'],
              label + ' field evidence matches all 25 original sealed admissions and UDP peers')
        check(summary['worldJournalsVerified'] == len(entries)
              and all(row['worldJournal']['frames'] == row['worldSequence'] and row['worldJournal']['runningFrames'] > 0
                      for row in summary['sessions']), label + ' field evidence verifies every original closed world journal')
        if concurrent_seconds is not None:
            coverage = summary['concurrentRoster']
            check(coverage['players'] == 25 and coverage['longestMilliseconds'] >= concurrent_seconds * 1000,
                  label + ' original closed world journals verify the continuous concurrent 25-seat window')
        if args.check_venue_openxr:
            sources={(row['roomId'],row['seat']):row['source'] for session in summary['sessions'] for row in session['playerSources']}
            check(sources=={(room,seat):'windows-openxr-mock-tracked' if (room,seat)==(5,2) else 'windows-desktop-simulated'
                           for room in range(1,6) for seat in range(1,6)},
                  label+' closed field evidence identifies the exact mock OpenXR seat and all 24 desktop peers')
        if args.check_lan_preflight:
            check(summary['udpSourcePreflightsVerified'] == len(entries)
                  and all(row['udpSourcePreflight']['verifiedSourceAddresses'] == 1 for row in summary['sessions']),
                  label + ' original paired UDP reports cover all acknowledged source addresses at every sealed game endpoint')
        save(label + '-venue-field-results.json', summary)
        rejected = run(dict(evidence, topology='direct-lan'))
        check(rejected.returncode == 1 and not rejected.stdout and 'outside the declared server addresses' in rejected.stderr,
              label + ' field evidence rejects relabeling the same-PC peers as direct LAN')
        manifest_path.write_text(json.dumps(evidence), encoding='utf-8')
        return {'batchId': closed['requestId'], 'zip': str(bundle_file), 'route': bundle_route}

    def verify_venue_field_ui(mode, current, earlier):
        node = shutil.which('node')
        if not node: raise RuntimeError('Node is required for the shipped field bundle check')
        cases = [dict(current, archived=False)]
        if earlier: cases.append(dict(earlier, archived=True))
        descriptor = runtime / (mode + '-field-browser-private.json')
        output = out / (mode + '-venue-field-ui.json')
        descriptor.write_text(json.dumps({'base': uri, 'masterKey': keys['Master'], 'mode': mode,
                                          'sessions': [], 'fieldEvidence': cases}), encoding='utf-8')
        with (out / (mode + '-venue-field-ui.log')).open('xb') as log:
            subprocess.run([node, str(ROOT/'tests/browser/check-venue-replay-native.cjs'), str(descriptor), str(output)],
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=75)
        result = read(output)
        check(result['complete'] and result['fieldEvidence'] == [case['batchId'] for case in cases],
              mode + ' shipped console downloads exact field bundles for the selected original batches')
    def verify_venue_reports(entries, receipt, linked):
        mode = 'linked' if linked else 'independent'
        key = receipt['requestId']
        route = f'/api/venue/closure/{key}/reports.zip'
        raw, headers = request(route, raw_response=True)
        check(headers.get_content_type() == 'application/zip' and headers['Cache-Control'] == 'no-store'
              and f'vr-command-venue-reports-v1-{key}.zip' in headers['Content-Disposition'],
              f'{mode} batch ZIP uses the original End request and no-store')
        request(route, role='Room1', expected=403)
        expected = {}
        manifest_sessions = []
        sequences = {item['sessionId']: item['appliedAtSequence'] for item in receipt['sessions']}
        for entry in entries:
            sid = entry['sessionId']
            session_path = '/api/sessions/' + sid
            rooms = request(session_path)['roomIds']
            prefix = f'vr-command-report-v1-{sid}'
            files = []
            if linked:
                name = prefix + '.csv'
                expected[name] = (out/(entry['label']+'-report.csv')).read_bytes()
                files.append({'roomId': None, 'name': name})
            for room in rooms:
                name = f'{prefix}-room-{room:02}.csv'
                expected[name], _ = request(session_path+f'/rooms/{room}/report.csv', raw_response=True)
                files.append({'roomId': room, 'name': name})
                scoped = list(csv.DictReader(io.StringIO(expected[name].decode('utf-8-sig'), newline='')))
                original = (out/(entry['label']+'-report.csv')).read_text(encoding='utf-8-sig')
                original_rows = list(csv.DictReader(io.StringIO(original)))
                check(scoped == [dict(row, reportRoomId=str(room)) for row in original_rows if row['playerRoomId'] == str(room)]
                      and len(scoped) == 5, f'{mode} batch room {room} preserves its five sealed native rows')
            manifest_sessions.append({'sessionId': sid, 'roomIds': rooms, 'appliedAtSequence': sequences[sid],
                'throughSequence': entry['sealed']['statistics']['throughSequence'], 'files': files})
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            manifest = json.loads(archive.read('manifest.json'))
            check(archive.namelist() == ['manifest.json', *expected] and archive.testzip() is None
                  and all(archive.read(name) == value for name, value in expected.items())
                  and manifest['schemaVersion'] == 1 and manifest['requestId'] == key and manifest['sessions'] == manifest_sessions,
                  f'{mode} batch ZIP matches the original session manifest and exact scoped CSV bytes')
        (out/f'{mode}-venue-reports.zip').write_bytes(raw)
        return route, raw

    def verify_venue_replay_ui(entries, closed, linked, earlier=None):
        mode = 'linked' if linked else 'independent'
        sources = {entry['sessionId']: entry['sealed']['world'] for entry in entries}
        rows = closed['sessions']
        check(all(row['replay'] == {'streamId': sources[row['sessionId']]['header']['streamId'],
                                   'throughSequence': sources[row['sessionId']]['acceptedSequence']} for row in rows),
              f'{mode} closure exposes the original native stream and replay boundary')
        node = shutil.which('node')
        if not node:
            raise RuntimeError('Node is required for the shipped replay console check')
        descriptor = runtime / f'{mode}-venue-replay-private.json'
        output = out / f'{mode}-venue-replay-ui.json'
        config = {'base': uri, 'masterKey': keys['Master'], 'mode': mode, 'sessions': rows}
        if earlier:
            config['history'] = {'batch': earlier, 'zip': str(out/'independent-venue-reports.zip')}
        descriptor.write_text(json.dumps(config), encoding='utf-8')
        with (out/f'{mode}-venue-replay-ui.log').open('xb') as log:
            subprocess.run([node, str(ROOT/'tests/browser/check-venue-replay-native.cjs'), str(descriptor), str(output)],
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=75)
        result = read(output)
        check(result['complete'] and [item['sessionId'] for item in result['results']] == [row['sessionId'] for row in rows]
              and all(item['throughSequence'] == sources[item['sessionId']]['acceptedSequence'] for item in result['results']),
              f'{mode} shipped console opens every original sealed native replay')
        first = result['results'][0]
        interval = first['interval']
        check(0 < interval['start'] < interval['end'] == interval['reached'] < first['throughSequence'],
              f'{mode} shipped console stops at the exact marked interval in the original sealed native replay')
        clips_path = f"/api/sessions/{first['sessionId']}/world/clips"
        shared = request(clips_path, role=f"Room{rows[0]['roomIds'][0]}")
        clip = shared['clips'][0]
        check(shared == request(clips_path) and len(shared['clips']) == 1
              and shared['sessionId'] == first['sessionId'] and shared['streamId'] == sources[first['sessionId']]['header']['streamId']
              and (clip['id'], clip['startFrame'], clip['endFrame'], clip['endMilliseconds'])
              == (interval['clipId'], interval['start'], interval['end'], interval['elapsedMilliseconds']),
              f'{mode} original native replay clip is shared with the authorized room')
        check(interval['playerReplay'] == {'start': interval['start'], 'end': interval['end'],
              'originalPackets': interval['end'] - interval['start'] + 1, 'apiRequests': 0},
              f'{mode} unauthenticated player plays the exact exported native frames locally')
        if earlier:
            older = earlier['sessions'][2]
            history = result['history']
            check(history['requestId'] == earlier['requestId'] and history['zipMatched']
                  and history['sessionId'] == older['sessionId'] and history['room'] == '3'
                  and history['throughSequence'] == older['replay']['throughSequence'],
                  'shipped history reopens the older original native replay and byte-identical ZIP after the Linked batch')

    def observe(entry,expected,begin=None, *, record=True):
        metadata=request('/api/sessions/'+entry['sessionId']+'/world');path='/api/sessions/'+entry['sessionId']+'/world/watch?mode=live';req=urllib.request.Request(uri+path,headers={'Authorization':'Bearer '+keys['Master']})
        with urllib.request.urlopen(req,timeout=5) as response:
            kind=''
            for _ in range(80):
                line=response.readline().decode().strip()
                if line.startswith('event: '):kind=line[7:]
                if kind=='frame' and line.startswith('data: '):
                    frame=json.loads(line[6:]);rows=frame['packet']['frame']['players'];connected={p['id'] for p in rows if p['connected'] and p['rig']['kind']=='Simulated'}
                    packet=frame['packet'];source=datetime.fromisoformat(metadata['header']['captureStartedAtUtc'])+timedelta(milliseconds=packet['elapsedMilliseconds']);age=(datetime.now(timezone.utc)-source).total_seconds()
                    expected_rigs=set(expected)
                    rigs_match=connected==expected_rigs
                    if 'openxrPlayerId' in entry:
                        tracked=entry['openxrPlayerId']
                        rigs_match=connected==expected_rigs-{tracked} and {p['id'] for p in rows
                            if p['connected'] and p['rig']['kind']=='Tracked'}=={tracked}
                    if rigs_match and (begin is None or packet['frame']['phase']=='Running' and packet['frame']['tick']>0 and not packet['suspended'] and packet['observedSequence']>=begin and -1<=age<1.5):
                        if record:save(entry['label']+('-running.json' if begin is not None else '-live.json'),{'metadata':metadata,'frame':frame,'sourceAgeSeconds':age,'acceptedBeginSequence':begin})
                        return frame
                    return None
    def start_hardware_mock(feed):
        frames=[]
        room=feed['room']; sid=feed['session']; label=f'{sid}-room-{room}'
        mock=subprocess.Popen([sys.executable,str(hardware/'mock-device.py')],env=mock_env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                              text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
        hardware_processes.append(mock)
        def collect():
            for line in mock.stdout:
                try:frames.append(json.loads(line))
                except ValueError:frames.append({'kind':'invalid'})
        reader=threading.Thread(target=collect,daemon=True);reader.start()
        listening=wait(lambda:next((f for f in frames if f['kind']=='listening'),None),8,'mock '+label+' listening')
        bindings=[{'deviceId':str(uuid.uuid4()),'playerId':player,'admissionId':admission,'seat':seat}
                  for player,(admission,seat) in feed['players'].items()]
        setup={'version':1,'managementUrl':uri,'sessionId':sid,'roomId':room,'mockPort':listening['port'],'seconds':120,'bindings':bindings}
        config=runtime/(label+'-hardware.json')
        gateway_env={**mock_env,'VR_COMMAND_ROOM_KEY':keys[f'Room{room}']}
        simulator=str(hardware/'VrCommand.HardwareSimulator.dll')
        if hardware_manifest['toolVersion'] in ('0.2.3','0.2.4'):
            seat_map=runtime/(label+'-seat-map.json')
            map_value={key:value for key,value in setup.items() if key!='bindings'}
            map_value['devices']=[{'deviceId':b['deviceId'],'seat':b['seat']} for b in bindings]
            seat_map.write_text(json.dumps(map_value),encoding='utf-8')
            result=subprocess.run([dotnet,simulator,'--bind-room',str(seat_map),'--output',str(config)],
                env=gateway_env,capture_output=True,timeout=8,creationflags=subprocess.CREATE_NO_WINDOW)
            bound=read(config) if result.returncode==0 else None
            check(bound=={**setup,'version':2,'bindings':sorted(bindings,key=lambda item:item['seat'])},
                  'room '+str(room)+' packaged binding matches the exact original device, seat and admission')
            save(label+'-hardware-binding.json',bound)
        else:
            config.write_text(json.dumps(setup),encoding='utf-8')
        report=out/(label+'-hardware-mock.json')
        gateway=subprocess.Popen([dotnet,simulator,'--live',str(config),'--output',str(report)],
            env=gateway_env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
        hardware_processes.append(gateway)
        return {'frames':frames,'mock':mock,'reader':reader,'gateway':gateway,'report':report,
                'devices':{b['playerId']:b['deviceId'] for b in bindings}}

    def exercise_room_combat(entries,clients):
        feeds={}
        if args.check_hardware_feedback:
            for client in clients:
                player=client['player'];room=player['roomId'];sid=client['sessionId']
                path=f'/api/sessions/{sid}/rooms/{room}/hardware-feedback'
                feed=feeds.get(path)
                if feed is None:
                    initial=request(path,role=f'Room{room}')
                    assert initial['resetReason']=='attached' and initial['signals']==[] and initial['state']=='Running'
                    feed={'cursor':initial['throughSequence'],'room':room,'session':sid,'stream':initial['streamId'],'players':{},'signals':[]}
                    feeds[path]=feed
                feed['players'][player['id']]=(player['admissionId'],player['seat'])
        if args.hardware_simulator_package:
            for feed in feeds.values():feed['mock']=start_hardware_mock(feed)
            for feed in feeds.values():
                wait(lambda:any(f['kind']=='hello' and f['roomId']==feed['room'] for f in feed['mock']['frames']),8,'mock handshake')

        def read_feedback():
            for path,feed in feeds.items():
                after=feed['cursor']
                page=request(path+f'?after={after}',role=f"Room{feed['room']}")
                assert page['state']=='Running' and page['resetReason'] is None and page['throughSequence']>=after
                assert page['sessionId']==feed['session'] and page['roomId']==feed['room'] and page['streamId']==feed['stream'] and page['combatOrigin']=='Simulation'
                for signal in page['signals']:
                    assert signal['kind']=='PlayerDamaged' and signal['damage']>0 and after<signal['eventSequence']<=page['throughSequence']
                    assert feed['players'][signal['playerId']]==(signal['admissionId'],signal['seat'])
                    feed['signals'].append(signal)
                feed['cursor']=page['throughSequence']

        def attack(entry,enabled):
            identity=str(uuid.uuid4());session=entry['sessionId']
            response=request('/api/sessions/'+session+'/commands',{'commandId':identity,'action':'SetEnemies',
                'enemies':{'count':entry['combatEnemyCount'],'behavior':'Hold','autoAttack':enabled}})
            check(response['commandId']==identity and not response['duplicate'] and response['session']['id']==session
                  and response['session']['enemies']['autoAttack'] is enabled,entry['label']+' original AI '+('enable' if enabled else 'disable')+' accepted')
            return response['appliedAtSequence']

        venue_changes = []
        def venue_attack(behavior, enabled):
            route = '/api/venue/phase'
            expected = {entry['sessionId']: entry['combatEnemyCount'] for entry in entries}
            preview = request(route)['enemies']
            targets = [{field: row[field] for field in ('sessionId', 'phaseSinceSequence', 'enemiesSinceSequence')} for row in preview]
            check({row['sessionId'] for row in targets} == set(expected)
                  and sorted(room for row in preview for room in row['roomIds']) == list(range(1, 6)),
                  'native enemy policy preview covers the original five rooms')
            policy = {'behavior': behavior, 'autoAttack': enabled}
            key = str(uuid.uuid4())
            body = {'action': 'SetEnemies', 'targets': targets, 'enemyPolicy': policy}
            receipt = request(route, body, request_id=key)
            applied = {row['sessionId']: row['appliedAtSequence'] for row in receipt['sessions']}
            def confirmed():
                rows = request('/api/rooms/readiness')['rooms']
                if len(rows) == 5 and all((status := row.get('venueEnemies')) and status['worldSequence']
                    and status['appliedAtSequence'] == applied.get(row['sessionId'])
                    and all(status[field] == value for field, value in policy.items()) for row in rows):
                    return rows
            observed = wait(confirmed, 20, f'{behavior} native enemy policy confirmations')
            check(not receipt['duplicate'] and receipt['requestId'] == key and set(applied) == set(expected)
                  and all(request('/api/sessions/'+sid)['enemies'] == {'count': count, **policy} for sid, count in expected.items()),
                  f'native {behavior} enemy policy confirms all sources and preserves their original targets')
            venue_changes.append({'policy': policy, 'receipt': receipt, 'rooms': observed})
            return applied

        def stopped_attack(entry, owners, enabled, live, entry_feeds, disabled, behavior):
            def stopped():
                value=observe(entry,owners,disabled,record=False)
                return value if value and not value['packet']['frame']['autoAttack'] and value['packet']['frame']['behavior']==behavior else None
            quiet=wait(stopped,12,entry['label']+' original source disables attack')
            entry['combatWindow']={'owners':owners,'enabledSequence':enabled,'disabledSequence':disabled,
                'allDamaged':live,'disabled':quiet}
            save(entry['label']+'-combat-window.json',entry['combatWindow'])
            check(True,entry['label']+' live damage to every original player and observed attack disabled')
            if entry_feeds:entry['hardwareFeedback']=entry_feeds

        started = venue_attack('Hold', True) if args.check_venue_enemies else None
        windows=[]
        for entry in entries:
            owners={c['player']['id']:c['player']['roomId'] for c in clients if c['sessionId']==entry['sessionId']}
            enabled=started[entry['sessionId']] if started is not None else attack(entry,True)
            windows.append((entry,owners,enabled))
        observations = []
        for entry,owners,enabled in windows:
            entry_feeds=[feed for feed in feeds.values() if feed['session']==entry['sessionId']]
            def damaged():
                read_feedback()
                value=observe(entry,owners,enabled,record=False)
                complete=all({signal['playerId'] for signal in feed['signals']}==set(feed['players']) for feed in entry_feeds)
                if args.hardware_simulator_package:
                    complete=complete and all({item['signal']['playerId'] for frame in feed['mock']['frames'] if frame['kind']=='feedback'
                                               for item in frame['signals']}==set(feed['players']) for feed in entry_feeds)
                if complete and value and value['packet']['frame']['autoAttack'] and {p['playerId'] for p in value['statistics'] if p['damageTaken']>0}==set(owners):
                    return value
            live=wait(damaged,35,entry['label']+' damage to every original admission')
            if args.check_venue_enemies:
                observations.append((entry, owners, enabled, live, entry_feeds))
            else:
                stopped_attack(entry, owners, enabled, live, entry_feeds, attack(entry,False), 'Hold')
        if args.check_venue_enemies:
            disabled = venue_attack('Advance', False)
            for entry, owners, enabled, live, entry_feeds in observations:
                stopped_attack(entry, owners, enabled, live, entry_feeds, disabled[entry['sessionId']], 'Advance')
            mode = 'linked' if len(entries) == 1 else 'independent'
            save(mode+'-venue-enemies.json', venue_changes)
    def finish(entry):
        entry['process'].wait(timeout=80);w=entry['witness'];w.wait();w.close();entry['witness']=None
        report=read(entry['reportPath']);check(entry['process'].returncode==0 and report['complete'] and report['cleanupCompleted'] and report['childExited'] and report['playerResultsAcknowledged'] is None,entry['label']+' dual seal / retained36 / original process terminal')
        check(report['udpBinding'] == entry['ready']['udpBinding'], entry['label'] + ' terminal report preserves the startup UDP observation')
        check(report['peerDiagnosticsEnabled'] is entry['peerDiagnostics'], entry['label']+' terminal report preserves the startup diagnostics choice')
        if 'layoutSession' in entry:
            state=entry['layoutSession'];mission=state['mission']
            preview=request('/api/missions/'+mission['id']+'/layout?mode='+state['mode'])
            routes=preview['routePreview']['seats']
            check(preview['canStart'] and [row['seat'] for row in routes]==list(range(5)) and all(
                row['path'] and row['path'][-1]['z']==0 and any(point['z']==-1 and 0<point['x']<2 for point in row['path'])
                for row in routes),entry['label']+' saved preview routes through the known opening')
            header=report['finalWorld']['header']
            expected={(room,'Sandbag',(room-3)*14+prop['position']['x'],prop['position']['y'],prop['position']['z'],prop['yawDegrees'])
                for room in state['roomIds'] for prop in mission['definition']['props']}
            actual={(prop['roomId'],prop['kind'],prop['feet']['x'],prop['feet']['y'],prop['feet']['z'],prop['yaw']) for prop in header['props']}
            check(actual==expected and len(header['props'])==len(expected),entry['label']+' native world preserves every saved cover coordinate and opening')
            save(entry['label']+'-layout-preview.json',preview)
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
        save(entry['label']+'-replay.json',frames)
        if 'venueOpenxr' in entry:
            window=entry['venueOpenxr']
            check(all(frames[packet['sequence']-1]['packet']==packet for packet in window['packets']),
                  entry['label']+' sealed replay preserves all four OpenXR participation checkpoints')
            _,lost,held,_=window['packets']
            expected=set(window['players'])-{entry['openxrPlayerId']}
            check(all({row['id'] for row in value['packet']['frame']['players'] if row['connected']}==expected
                      and value['packet']['frame']['phase']=='Running' for value in frames[lost['sequence']-1:held['sequence']]),
                  entry['label']+' every replay frame of held tracking loss preserves the other admissions')
        if 'combatWindow' in entry:
            window=entry['combatWindow']
            actual={value['packet']['sequence']:value for value in frames}
            check(all(actual.get(window[key]['packet']['sequence'])==window[key] for key in ('allDamaged','disabled')),
                  entry['label']+' exact live damage and attack-disabled checkpoints survive replay')
            proof=reconcile_ai_damage(frames,window['owners'],window['enabledSequence'],window['disabledSequence'])
            stream=request('/api/sessions/'+entry['sessionId'])['combatStream']
            check(frames[-1]['statistics']==stats['players'] and stream['sealed'] and stream['acceptedSequence']==proof['damageEvents'],
                  entry['label']+' every same-room attack, damage event and per-frame statistic agrees with the sealed ledger')
            save(entry['label']+'-combat-reconciliation.json',proof)
        if 'hardwareFeedback' in entry:
            sid=entry['sessionId'];events={};after=0
            while True:
                rows=request(f'/api/sessions/{sid}/events?after={after}&limit=500')
                events.update({event['eventId']:event for event in rows})
                if len(rows)<500:break
                after=rows[-1]['sequence']
            for feed in entry['hardwareFeedback']:
                room=feed['room']
                ended=request(f'/api/sessions/{sid}/rooms/{room}/hardware-feedback?after={feed["cursor"]}',role=f'Room{room}')
                assert ended['state']=='Ended' and ended['resetReason']=='inactive' and ended['signals']==[] and feed['stream']==entry['ready']['streamId']
                for signal in feed['signals']:
                    source=events[signal['eventId']];record=source['payload'];combat=record['report']
                    assert source['sequence']==signal['eventSequence'] and record['streamSequence']==signal['streamSequence']
                    assert record['observedSequence']==signal['observedSequence'] and record['streamId']==entry['ready']['streamId']
                    assert (combat['reportId'],combat['playerId'],combat['kind'],combat['damage'])==(signal['reportId'],signal['playerId'],signal['kind'],signal['damage'])
                check(len({s['eventId'] for s in feed['signals']})==len(feed['signals']),entry['label']+f' room {room} live hardware signals match original accepted combat reports and stop at End')
                if 'mock' in feed:
                    owned=feed.pop('mock'); log,_=owned['gateway'].communicate(timeout=12)
                    assert owned['gateway'].returncode==0 and not any(key in log for key in keys.values())
                    result=read(owned['report'])
                    assert result['complete'] and result['termination']=='ended' and result['physicalDeliveryConfirmed'] is False
                    assert (result['roomId'],result['sessionId'])==(room,sid)
                    acknowledged=[item for attempt in result['attempts'] if attempt['status']=='simulated-acknowledged' for item in attempt['deliveries']]
                    expected_players=feed.get('expectedAcknowledgedPlayers',feed['players'])
                    check(len(acknowledged)==result['acknowledged'] and {item['signal']['playerId'] for item in acknowledged}==set(expected_players),
                          entry['label']+f' room {room} mock confirmed the expected original admissions')
                    for item in acknowledged:
                        signal=item['signal'];player=signal['playerId'];original=events[signal['eventId']]
                        assert (signal['admissionId'],signal['seat'])==feed['players'][player] and item['deviceId']==owned['devices'][player]
                        assert original['sequence']==signal['eventSequence'] and original['payload']['streamId']==feed['stream']
                        assert original['payload']['report']['reportId']==signal['reportId'] and original['payload']['report']['damage']==signal['damage']
                    if 'mockBatch' in feed:
                        batch=feed['mockBatch']
                        check([frame for frame in owned['frames'] if frame['kind']=='feedback']==[batch]
                              and result['attempts']==[{'connectionId':batch['connectionId'],'batchId':batch['batchId'],
                                  'status':'simulated-acknowledged','deliveries':batch['signals']}]
                              and result['acknowledged']==1 and result['dropped']==0,
                              'the single mock device batch is acknowledged exactly once through End')
                    owned['mock'].terminate();owned['mock'].wait(timeout=5);owned['reader'].join(timeout=5)
                    check(not owned['reader'].is_alive(),entry['label']+f' room {room} mock and original gateway are terminal')
            save(entry['label']+'-hardware-feedback.json',entry['hardwareFeedback'])
        rounds.append({'name':entry['label'],'ready':entry['ready'],'report':report,'journal':closed,'replayFrames':len(frames)})
    def openxr_environment(manifest_name, tracking_loss):
        fixture_manifest=runtime/manifest_name
        fixture_manifest.write_text(json.dumps({'file_format_version':'1.0.0','runtime':
            {'api_version':'1.0','name':'VR Command pose fixture','library_path':str(args.openxr_mock_pose_dll.resolve(strict=True))}}),encoding='utf-8')
        return {'XR_RUNTIME_JSON':str(fixture_manifest),'VR_COMMAND_OPENXR_MOCK_DLL':str(runtime_file),
                'VR_COMMAND_OPENXR_TRACKING_LOSS_FILE':str(tracking_loss)}

    def check_openxr_mock():
        nonlocal observer,observer_log
        stage('native-openxr-mock')
        label='openxr-mock'
        pose_dll=args.openxr_mock_pose_dll.resolve(strict=True)
        tracking_loss=runtime/'openxr-tracking-loss.request'
        trigger_command=runtime/'openxr-trigger.request'
        trigger_ack=runtime/'openxr-trigger-ack.txt'
        trigger_command.write_text('0',encoding='ascii')
        mock_environment={**openxr_environment('openxr-pose-runtime.json',tracking_loss),
                          'VR_COMMAND_OPENXR_TRIGGER_COMMAND':str(trigger_command),'VR_COMMAND_OPENXR_TRIGGER_ACK':str(trigger_ack)}
        reconnect_command=runtime/'openxr-reconnect.request'
        reconnect_ack=runtime/'openxr-reconnect-ack.txt'
        if args.check_openxr_reconnect or args.check_openxr_revocation:
            reconnect_command.write_text('0',encoding='ascii')
            mock_environment.update(VR_COMMAND_OPENXR_RECONNECT_COMMAND=str(reconnect_command),
                                    VR_COMMAND_OPENXR_RECONNECT_ACK=str(reconnect_ack))
        entry=launch(create([1],label),label)
        sid=entry['sessionId']
        session='/api/sessions/'+sid
        owners=[]
        for name,headset in (('Desktop peer','Quest3'),('OpenXR mock','ViveXr')):
            identity=str(uuid.uuid4())
            state=request(session+'/players',{'playerId':identity,'roomId':1,'name':name,'headset':headset},role='Room1')
            owners.append(next(row for row in state['players'] if row['id']==identity))
        target={'address':address,'port':entry['ready']['port']}
        raw,_=request(session+'/rooms/1/join-ticket-bundle',
            dict(target,players=[{'playerId':p['id'],'admissionId':p['admissionId']} for p in owners]),role='Room1',raw_response=True)
        (runtime/'openxr-mock-tickets.zip').write_bytes(raw)
        clients_for_room=[]
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for index,owner in enumerate(owners):
                file=runtime/f'openxr-mock-seat-{index+1}.json'
                file.write_bytes(archive.read(f'room-01-seat-{owner["seat"]+1:02}.json'))
                content=read(file)
                check(content=={'role':'Client',**target,'joinTicket':content['joinTicket']} and content['joinTicket'],
                      'original seat connection file '+str(index+1))
                if index==1 and args.check_openxr_reconnect:
                    udp=module('openxr_reconnect_udp','udp_gate.py')
                    gate=udp.LoopbackGate(target['port'],lambda:False).start()
                    reconnect_gates.append(gate)
                    file.write_text(json.dumps(dict(content,port=gate.port)),encoding='ascii')
                clients_for_room.append(packaged_player(entry,owner,file,mock=mock_environment if index==1 else None))
        desktop,tracked=clients_for_room
        def client_log(client):
            if client['process'].poll() is not None:
                raise RuntimeError('An original player exited before End')
            return client['log'].read_text(encoding='utf-8',errors='replace') if client['log'].exists() else ''

        def replace_fixture_file(path,value):
            pending=path.with_suffix('.new')
            with pending.open('x',encoding='ascii') as output:
                output.write(value)
            deadline=time.monotonic()+1
            while True:
                try:
                    os.replace(pending,path)
                    break
                except PermissionError as error:
                    # The runtime can be opening the current command at the same instant.
                    if error.winerror not in (5,32) or time.monotonic()>=deadline:
                        raise
                    time.sleep(.02)

        reconnect_states=[]
        def confirm_reconnect_sync(state):
            reconnect_states.append(state+' '+state)
            wait(lambda:reconnect_ack.is_file() and reconnect_ack.read_text(encoding='ascii').splitlines()==reconnect_states,
                 12,'OpenXR right Vive menu sync '+state)

        def set_reconnect(value):
            replace_fixture_file(reconnect_command,value)
            confirm_reconnect_sync(value)

        def tracked_connections():
            return re.findall(r'^VR_CLIENT_CONNECTED id=(\d+)$',client_log(tracked),re.M)

        wait(lambda: all('VR_CLIENT_CONNECTED id=' in client_log(c) for c in clients_for_room),35,'both signed OpenXR fixture admissions')
        lines=client_log(tracked).splitlines()
        markers=[line for line in lines if line.startswith(('VR_OPENXR_STARTUP ','VR_NETWORK_STARTED ','VR_CLIENT_CONNECTED '))]
        check(len(markers)==4 and markers[:2]==['VR_OPENXR_STARTUP status=requested','VR_OPENXR_STARTUP status=active']
              and markers[2].startswith('VR_NETWORK_STARTED role=Client started=True ')
              and markers[3].startswith('VR_CLIENT_CONNECTED id=')
              and any('Runtime Name: Unity Mock Runtime' in line for line in lines)
              and 'VR_OPENXR_STARTUP ' not in client_log(desktop),
              'actual packaged mock OpenXR starts before transport and original admission')
        save(label+'-runtime.json',{'packageVersion':mock_package_version,'manifestSha256':package.digest(openxr_mock),
            'runtimeSha256':package.digest(runtime_file),'poseDllSha256':package.digest(pose_dll),'markers':markers})
        tracked_connection_ids=tracked_connections()
        revocation_frames=[]
        expected={owners[0]['id']:(owners[0]['admissionId'],'Simulated'),owners[1]['id']:(owners[1]['admissionId'],'Tracked')}
        latest=None
        def readiness():
            nonlocal latest
            report=request(session+'/readiness')
            latest=report
            actual={row['playerId']:(row['admissionId'],row['rigKind']) for row in report['players'] if row['canParticipate']}
            return report if report['sourceState']=='Fresh' and report['observedSequence']==report['sessionSequence'] and actual==expected else None
        try:
            wait(readiness,25,'exact simulated and tracked accepted admissions')
        finally:
            save(label+'-readiness.json',latest)
        check(True,'management recognizes mock head and hands as tracked, and the separate desktop peer as simulated')
        if args.check_openxr_revocation:
            stage('native-openxr-revocation')
            previous=tracked['player']
            peer_id=desktop['player']['id']
            player_path=session+'/players/'+previous['id']
            old_file=read(tracked['configPath'])
            old_hash=package.digest(tracked['configPath'])
            ticket_route='/api/player-tickets/validate'
            old_ticket={'sessionId':sid,'ticket':old_file['joinTicket'],'protocolVersion':2}
            validation=request(ticket_route,old_ticket,role='GameServer')
            ready_revision=validation['throughSequence']
            check(validation['admissionId']==previous['admissionId'] and validation['playerId']==previous['id'],
                  'the original signed ticket validates before revocation')

            def preparing_checkpoint(revision,owner,connected,after=0):
                report=request(session+'/readiness')
                if report['sourceState']!='Fresh' or report['observedSequence']!=revision or report['sessionSequence']!=revision or report['worldSequence']<=after:
                    return None
                rows={row['playerId']:row for row in report['players']}
                roster_ids={peer_id,owner['id']} if owner else {peer_id}
                if set(rows)!=roster_ids or not rows[peer_id]['canParticipate'] or rows[peer_id]['rigKind']!='Simulated':
                    return None
                expected_rigs={peer_id:'Simulated'}
                if owner:
                    row=rows[owner['id']]
                    if (row['admissionId'],row['seat'],row['roomId'],row['canParticipate'])!=(owner['admissionId'],owner['seat'],owner['roomId'],connected):
                        return None
                    if connected:expected_rigs[owner['id']]='Tracked'
                packet=request(session+'/world/frames/'+str(report['worldSequence']))['packet']
                frame=packet['frame']
                if frame['phase']=='Preparing' and packet['observedSequence']==revision and {
                    row['id']:row['rig']['kind'] for row in frame['players'] if row['connected']}==expected_rigs:
                    return {'packet':packet,'readiness':report}
                return None

            def server_lines():
                return (entry['work']/'server.log').read_text(encoding='utf-8',errors='replace').splitlines()

            ready=wait(lambda:preparing_checkpoint(ready_revision,previous,True),12,'original admission in Preparing')
            confirm_reconnect_sync('0')
            set_reconnect('1')
            request(player_path,method='DELETE',admission=previous['admissionId'],expected=204)
            removed_revision=request(session)['sequence']
            wait(lambda:'VR_CLIENT_DISCONNECTED' in client_log(tracked)
                 and f'VR_SERVER_CLIENT_LEFT id={tracked_connection_ids[0]}' in server_lines(),15,'operator revokes the original native connection')
            removed=wait(lambda:preparing_checkpoint(removed_revision,None,False,ready['packet']['sequence']),12,'original seat removed while peer remains')
            state=request(session+'/players',{'playerId':previous['id'],'roomId':previous['roomId'],
                'name':previous['name'],'headset':previous['headset']},role='Room1')
            replacement=next(row for row in state['players'] if row['id']==previous['id'])
            revision=state['sequence']
            check(removed_revision==ready_revision+1 and revision==removed_revision+1
                  and replacement['admissionId']!=previous['admissionId'] and replacement['seat']==previous['seat'],
                  'the same player and seat receive a different admission after the original is revoked')
            request(player_path,method='DELETE',admission=previous['admissionId'],expected=409)
            rejected=request(ticket_route,old_ticket,role='GameServer',expected=403)
            check(rejected['error']=='Player ticket no longer matches the current admission.' and request(session)['sequence']==revision,
                  'the old signed ticket and the stale operator admission cannot affect the replacement')
            waiting=wait(lambda:preparing_checkpoint(revision,replacement,False,removed['packet']['sequence']+15),12,'replacement remains disconnected with menu held')
            initial_pending=[line for line in server_lines() if line.startswith('VR_SERVER_CLIENT_PENDING id=')]
            check(tracked_connections()==tracked_connection_ids and len(initial_pending)==2,
                  'held menu does not retry when the operator revokes and replaces the seat')
            set_reconnect('0')
            wait(lambda:preparing_checkpoint(revision,replacement,False,waiting['packet']['sequence']+8),12,'release reaches the eligible disconnected player')
            set_reconnect('1')
            wait(lambda:'VR_CLIENT_ADMISSION_REJECTED' in client_log(tracked)
                 and 'VR_SERVER_ADMISSION_REJECTED' in server_lines(),15,'original game server refuses the revoked ticket on a fresh menu press')
            refused=wait(lambda:preparing_checkpoint(revision,replacement,False,waiting['packet']['sequence']),12,'refused ticket never becomes a participating admission')
            pending=[line for line in server_lines() if line.startswith('VR_SERVER_CLIENT_PENDING id=')]
            check(len(pending)==3 and tracked_connections()==tracked_connection_ids
                  and package.digest(tracked['configPath'])==old_hash and server_lines().count('VR_SERVER_ADMISSION_REJECTED')==1,
                  'one old-ticket UDP attempt is refused while the other player remains admitted')
            renewed=request(player_path+'/join-ticket',{},role='Room1',admission=replacement['admissionId'])
            check(renewed['ticket']!=old_file['joinTicket'],'room desk issues a different signed ticket for the replacement admission')
            replace_fixture_file(tracked['configPath'],json.dumps(dict(old_file,joinTicket=renewed['ticket'])))
            cooled=wait(lambda:preparing_checkpoint(revision,replacement,False,refused['packet']['sequence']+24),12,'reconnect cooldown ends with menu held')
            set_reconnect('0')
            released_for_replacement=wait(lambda:preparing_checkpoint(revision,replacement,False,cooled['packet']['sequence']+8),12,'new ticket remains idle after release')
            check(tracked_connections()==tracked_connection_ids and server_lines().count('VR_SERVER_ADMISSION_REJECTED')==1,
                  'refresh and release do not automatically connect with the new ticket')
            set_reconnect('1')
            admitted=wait(lambda:preparing_checkpoint(revision,replacement,True,released_for_replacement['packet']['sequence']),15,
                          'new ticket accepts the replacement in the original process')
            tracked_connection_ids=tracked_connections()
            check(len(set(tracked_connection_ids))==2 and pending[-1].split('=')[-1] not in tracked_connection_ids
                  and tracked['witness'].kernel.WaitForSingleObject(tracked['witness'].handle,0)==258
                  and client_log(tracked).count('VR_OPENXR_STARTUP status=active')==1,
                  'only the new admission restores the tracked rig in the same player process')
            check(client_log(desktop).count('VR_CLIENT_CONNECTED id=')==1 and 'VR_CLIENT_DISCONNECTED' not in client_log(desktop),
                  'roster replacement preserves the desktop peer transport')
            owners[1]=tracked['player']=replacement
            expected[replacement['id']]=(replacement['admissionId'],'Tracked')
            revocation_frames=[row['packet'] for row in (ready,removed,waiting,refused,released_for_replacement,admitted)]
            save(label+'-revocation.json',{'acknowledged':reconnect_states,'connections':tracked_connection_ids,
                'rejectedConnection':pending[-1].split('=')[-1],'ready':ready,'removed':removed,'waiting':waiting,
                'refused':refused,'released':released_for_replacement,'admitted':admitted})
        prior_disconnects=client_log(tracked).count('VR_CLIENT_DISCONNECTED')
        begin=command(sid,'Begin')['appliedAtSequence']
        def running(minimum_tick=1):
            metadata=request(session+'/world')
            packet=request(session+'/world/frames/'+str(metadata['acceptedSequence']))['packet']
            frame=packet['frame']
            rigs={row['id']:row['rig']['kind'] for row in frame['players'] if row['connected']}
            return packet if packet['observedSequence']>=begin and frame['phase']=='Running' and frame['tick']>=minimum_tick and rigs=={key:value[1] for key,value in expected.items()} else None
        packet=wait(running,15,'original Running replay frame with both rig types')
        save(label+'-running-pose.json',packet)
        tracked_pose=next(row for row in packet['frame']['players'] if row['id']==tracked['player']['id'])
        head=tracked_pose['head']
        hands=[tracked_pose['rig']['left'],tracked_pose['rig']['right']]
        check(abs(head['y']-1.65)<.001 and all(
            abs(hand['y']-1.25)<.001 and abs(hand['x']-head['x'])<.001 and abs(hand['z']-head['z']-.4)<.001
            for hand in hands),'accepted head and both hands match the fixture coordinates in the live world')
        tracked_id=tracked['player']['id']
        desktop_id=desktop['player']['id']
        magazine=tracked_pose['magazine']
        original_config_hash=package.digest(tracked['configPath'])
        expected_admissions={(p['id'],p['admissionId'],p['roomId'],p['seat']) for p in owners}
        acknowledged=[]
        feed=None
        if openxr_hardware:
            hardware_route=session+'/rooms/1/hardware-feedback'
            initial=request(hardware_route,role='Room1')
            check(initial['state']=='Running' and initial['resetReason']=='attached' and initial['signals']==[]
                  and initial['streamId']==entry['ready']['streamId'] and initial['runningSinceSequence']==begin,
                  'room hardware reader attaches to the original Running stream with an empty cursor')
            request(hardware_route,role='Room2',expected=403)
            check(True,'another room key cannot read the original hardware route')
            feed={'cursor':initial['throughSequence'],'room':1,'session':sid,'stream':initial['streamId'],
                  'players':{p['id']:(p['admissionId'],p['seat']) for p in owners},'signals':[],
                  'expectedAcknowledgedPlayers':[tracked_id]}
            feed['mock']=start_hardware_mock(feed)
            wait(lambda:any(f['kind']=='hello' and f['roomId']==1 for f in feed['mock']['frames']),8,'OpenXR hardware mock handshake')

        def feedback_page():
            page=request(hardware_route+f'?after={feed["cursor"]}',role='Room1')
            assert page['sessionId']==sid and page['roomId']==1 and page['streamId']==feed['stream']
            assert page['state']=='Running' and page['resetReason'] is None and page['combatOrigin']=='Simulation'
            assert page['runningSinceSequence']==begin and page['throughSequence']>=feed['cursor']
            assert all(feed['cursor']<s['eventSequence']<=page['throughSequence'] for s in page['signals'])
            feed['cursor']=page['throughSequence']
            return page

        def expect_trigger(*states):
            acknowledged.extend(states)
            def synced():
                return trigger_ack.is_file() and trigger_ack.read_text(encoding='ascii').splitlines()==acknowledged
            wait(synced,12,'original OpenXR trigger sync '+states[-1])

        def set_trigger(value,*states):
            replace_fixture_file(trigger_command,value)
            expect_trigger(*states)

        def magazine_at(frame):
            return next(row['magazine'] for row in frame['frame']['players'] if row['id']==tracked_id)
        if args.observe_closure_ui:
            node=shutil.which('node')
            if not node:
                raise RuntimeError('The optional console observation requires Node')
            descriptor=runtime/'openxr-console-private.json'
            end_request=runtime/'openxr-console-end.request'
            descriptor.write_text(json.dumps({'base':uri,'masterKey':keys['Master'],'sessionId':sid,
                'streamId':entry['ready']['streamId'],'endRequestFile':str(end_request),
                'trackedParticipation':{'roomId':1,'seat':tracked['player']['seat']+1},
                'weaponAmmunition':[{'name':c['player']['name'],'ammoUsed':int(c is tracked)} for c in clients_for_room]}),
                encoding='utf-8')
            observer_log=(out/'openxr-console.log').open('xb')
            observer=subprocess.Popen([node,str(ROOT/'tests/browser/check-closure-native.cjs'),
                '--descriptor',str(descriptor),'--output',str(observer_out),'--stop-file',str(observer_stop)],
                stdout=observer_log,stderr=subprocess.STDOUT,cwd=ROOT/'tests/browser')

        def console_observation(name):
            def observed():
                path=observer_out/name
                if path.is_file():
                    return read(path)
                if observer.poll() is not None:
                    raise RuntimeError('OpenXR console observer exited before '+name)
                return None
            return wait(observed,25,'OpenXR console '+name)

        if args.observe_closure_ui:
            check(console_observation('ready.json')['selectedSessionId']==sid,'shipped console observes the original Running room')
        expect_trigger('0 0')

        def tracking_checkpoint(available, minimum_tick, *, revision=begin):
            report=request(session+'/readiness')
            rows={row['playerId']:row for row in report['players']}
            if (report['sourceState']!='Fresh' or report['observedSequence']!=revision or report['sessionSequence']!=revision
                    or {(row['playerId'],row['admissionId'],row['roomId'],row['seat']) for row in rows.values()}!=expected_admissions):
                return None
            owner=rows[tracked_id]
            if (owner['canParticipate'] is not available or owner['state']!=('Participating' if available else 'PoseUnavailable')
                    or (available and owner['rigKind']!='Tracked')
                    or rows[desktop_id]['rigKind']!='Simulated' or not rows[desktop_id]['canParticipate']):
                return None
            frame=request(session+'/world/frames/'+str(report['worldSequence']))['packet']
            players={row['id']:row for row in frame['frame']['players']}
            if (frame['frame']['phase']!='Running' or frame['frame']['tick']<minimum_tick
                    or players[tracked_id]['connected'] is not available or not players[desktop_id]['connected']):
                return None
            if available:
                pose=players[tracked_id]
                joints=[pose['head'],pose['rig']['left'],pose['rig']['right']]
                if pose['rig']['kind']!='Tracked' or any(abs(new['x']-old['x']-.2)>=.001
                    for new,old in zip(joints,[head,*hands],strict=True)):
                    return None
            rooms=request('/api/rooms/readiness',role='Room1')['rooms']
            if len(rooms)!=1:
                return None
            room=rooms[0]
            if (room['sessionId']!=sid or room['sessionSequence']!=revision or room['sourceState']!='Fresh'
                    or room['simulatedReady']!=1 or room['trackedReady']!=int(available)
                    or room['vrParticipation']['awaitingPose']!=([] if available else [tracked['player']['seat']+1])):
                return None
            return {'packet':frame,'readiness':report,'room':room}

        tracking_loss.touch(exist_ok=False)
        try:
            lost=wait(lambda:tracking_checkpoint(False,packet['frame']['tick']+1),12,'tracked seat loses readiness')
            save(label+'-tracking-lost.json',lost)
            set_trigger('1','1 1')
            held=wait(lambda:tracking_checkpoint(False,lost['packet']['frame']['tick']+14),12,'tracked seat stays unavailable during Running')
            save(label+'-tracking-held.json',held)
            if args.observe_closure_ui:
                alert=console_observation('participation-alert.json')
                check(alert['roomId']==1 and alert['seat']==tracked['player']['seat']+1,'shipped console flags only the original OpenXR seat')
        finally:
            tracking_loss.unlink()
        check(True,'same Running room marks only the original OpenXR seat unavailable during controller tracking loss')
        recovered=wait(lambda:tracking_checkpoint(True,held['packet']['frame']['tick']+1),12,'same tracked seat accepts a new pose after recovery')
        save(label+'-tracking-recovered.json',recovered)
        check(package.digest(tracked['configPath'])==original_config_hash
              and tracked_connections()==tracked_connection_ids
              and client_log(tracked).count('VR_CLIENT_DISCONNECTED')==prior_disconnects
              and tracked['witness'].kernel.WaitForSingleObject(tracked['witness'].handle,0)==258,
              'original OpenXR process and connection recover with the same ticket and newly accepted head and hand positions')
        if args.observe_closure_ui:
            restored=console_observation('participation-recovered.json')
            check(restored['roomId']==1 and restored['seat']==tracked['player']['seat']+1,'shipped console clears the OpenXR tracking alert')
        held_recovered=wait(lambda:running(recovered['packet']['frame']['tick']+14),12,'original rig remains ready with the trigger held')
        check(magazine_at(held_recovered)==magazine,'trigger held through tracking recovery cannot fire')
        set_trigger('0','0 0')
        released=wait(lambda:running(held_recovered['frame']['tick']+14),12,'original ready rig after trigger release')
        check(magazine_at(released)==magazine,'trigger release leaves the original magazine unchanged')
        if feed is not None:
            quiet=feedback_page()
            check(quiet['signals']==[] and feed['mock']['gateway'].poll() is None
                  and not any(frame['kind']=='feedback' for frame in feed['mock']['frames']),
                  'tracking loss, held recovery and trigger release generate no feedback for either bound device')
            save(label+'-hardware-before-tap.json',quiet)
        set_trigger('2','2 1','2 0')
        if feed is not None:
            page=wait(lambda:(value if (value:=feedback_page())['signals'] else None),5,'one original live OpenXR hardware signal')
            check(len(page['signals'])==1,'one live hardware signal follows the new OpenXR tap')
            signal=page['signals'][0]
            check(signal['kind']=='ShotFired' and signal['playerId']==tracked_id and signal['damage']==0
                  and (signal['admissionId'],signal['seat'])==feed['players'][tracked_id] and signal['observedSequence']==begin,
                  'live logical recoil signal belongs to the original tracked admission and seat')
            batch=wait(lambda:next((f for f in feed['mock']['frames'] if f['kind']=='feedback'),None),5,'original mock device feedback batch')
            check(batch['mode']=='simulation' and batch['roomId']==1 and batch['streamId']==feed['stream']
                  and batch['runningSinceSequence']==begin
                  and batch['signals']==[{'deviceId':feed['mock']['devices'][tracked_id],'signal':signal}],
                  'TCP mock device receives the original shot for the tracked device only')
            feed['signals']=page['signals']
            feed['mockBatch']=batch
            entry['hardwareFeedback']=[feed]

        def shot():
            frame=running(released['frame']['tick']+1)
            if frame and magazine_at(frame)<magazine-1:
                raise RuntimeError('One test tap consumed more than one round')
            return frame if frame and magazine_at(frame)==magazine-1 else None

        fired=wait(shot,12,'one accepted shot from the new OpenXR trigger press')
        after_tap=wait(lambda:running(fired['frame']['tick']+14),12,'original world after the single trigger tap')
        check(magazine_at(after_tap)==magazine-1,'one new OpenXR trigger press consumes exactly one round')
        save(label+'-trigger.json',{'acknowledged':acknowledged,'heldAfterRecovery':held_recovered,
                                    'released':released,'fired':fired,'afterTap':after_tap})
        reconnect_frames=[]
        reconnect_ids=[]
        if args.check_openxr_reconnect:
            stage('native-openxr-reconnect')
            reconnect_revision=request(session)['sequence']
            confirm_reconnect_sync('0')
            set_reconnect('1')
            reconnect_ids=tracked_connections()
            check(len(reconnect_ids)==1 and markers[2].endswith('port='+str(gate.port))
                  and gate.counts['upstream']>0 and gate.counts['downstream']>0,
                  'original tracked player passes real NGO UDP through its private relay')
            gate.close()
            gate_report=gate.report()
            check(gate_report['threadStopped'] and gate_report['error'] is None,'owned UDP relay closes before original client disconnect')
            server_log=entry['work']/'server.log'
            wait(lambda:'VR_CLIENT_DISCONNECTED' in client_log(tracked)
                 and f'VR_SERVER_CLIENT_LEFT id={reconnect_ids[0]}' in server_log.read_text(encoding='utf-8',errors='replace').splitlines(),
                 45,'original client and server report the UDP disconnect')
            lost_udp=wait(lambda:tracking_checkpoint(False,after_tap['frame']['tick']+1,revision=reconnect_revision),12,
                          'only original tracked player loses participation after UDP disconnect')
            updated=request(session+'/players/'+tracked_id+'/join-ticket',{},role='Room1',admission=tracked['player']['admissionId'])
            original=read(tracked['configPath'])
            check(updated['ticket']!=original['joinTicket'] and updated['ticket'] and request(session)['sequence']==reconnect_revision,
                  'room desk issues a fresh signed ticket for the original admission without mutating the room')
            replace_fixture_file(tracked['configPath'],json.dumps({'role':'Client',**target,'joinTicket':updated['ticket']}))
            updated_hash=package.digest(tracked['configPath'])
            held_button=wait(lambda:tracking_checkpoint(False,lost_udp['packet']['frame']['tick']+50,revision=reconnect_revision),12,
                        'right Vive menu stays held after eligible disconnect')
            check(tracked_connections()==reconnect_ids and 'VR_CLIENT_ADMISSION_REJECTED' not in client_log(tracked),
                  'held right Vive menu cannot reconnect after the UDP interruption and ticket refresh')
            set_reconnect('0')
            released_button=wait(lambda:tracking_checkpoint(False,held_button['packet']['frame']['tick']+14,revision=reconnect_revision),12,
                            'right Vive menu release without reconnect')
            check(tracked_connections()==reconnect_ids,'right Vive menu release alone does not reconnect')
            set_reconnect('1')
            wait(lambda:len(tracked_connections())==2,15,'new original NGO connection from right Vive menu')
            renewed=wait(lambda:tracking_checkpoint(True,released_button['packet']['frame']['tick']+1,revision=reconnect_revision),15,
                         'original admission recovers its tracked pose through the game UDP endpoint')
            reconnect_ids=tracked_connections()
            prior_pose,next_pose=(next(p for p in frame['frame']['players'] if p['id']==tracked_id)
                                  for frame in (after_tap,renewed['packet']))
            check(len(set(reconnect_ids))==2 and package.digest(tracked['configPath'])==updated_hash
                  and tracked['witness'].kernel.WaitForSingleObject(tracked['witness'].handle,0)==258
                  and client_log(tracked).count('VR_OPENXR_STARTUP status=active')==1
                  and client_log(tracked).count('VR_CLIENT_DISCONNECTED')==1
                  and 'VR_CLIENT_ADMISSION_REJECTED' not in client_log(tracked)
                  and all(prior_pose[key]==next_pose[key] for key in ('health','magazine','reserve')),
                  'new right Vive menu press reloads the ticket in the same tracked player process and preserves combat state')
            tracked_connection_ids=reconnect_ids
            reconnect_frames=[lost_udp['packet'],held_button['packet'],released_button['packet'],renewed['packet']]
            save(label+'-reconnect.json',{'relay':gate_report,'acknowledged':reconnect_states,'connections':reconnect_ids,
                'refreshedConfigSha256':updated_hash,'managementRevision':reconnect_revision,
                'before':after_tap,'lost':lost_udp,'held':held_button,'released':released_button,'renewed':renewed})
        if args.observe_closure_ui:
            ammunition=console_observation('weapon-ammunition.json')
            check({row['name']:row['ammoUsed'] for row in ammunition}
                  == {c['player']['name']:str(int(c is tracked)) for c in clients_for_room},
                  'shipped console shows the exact OpenXR and desktop ammunition counts before End')
            end_request.touch(exist_ok=False)
            check(console_observation('end-receipt.json')['sessionId']==sid,'shipped console ends the original OpenXR room')
        else:
            command(sid,'End')
        finish(entry)
        if args.observe_closure_ui:
            observer.wait(timeout=45)
            ui=read(observer_out/'checks.json')
            check(observer.returncode==0 and ui['complete'] and ui['browserClosed']
                  and ui['acceptedWorldSequence']==entry['sealed']['world']['acceptedSequence'],
                  'shipped console observes the exact OpenXR world seal and closes')
            observer_log.close()
            observer_log=None
            observer=None
        replay=read(out/(label+'-replay.json'))
        checkpoints=[packet,lost['packet'],held['packet'],recovered['packet'],held_recovered,released,fired,after_tap,*reconnect_frames]
        check(all(replay[frame['sequence']-1]['packet']==frame for frame in checkpoints),
              'exact tracked, lost and recovered Running checkpoints survive in the sealed replay')
        held_frames=replay[lost['packet']['sequence']-1:held['packet']['sequence']]
        check(len(held_frames)>1 and all({row['id']:row['connected'] for row in frame['packet']['frame']['players']}
              == {desktop_id:True,tracked_id:False} for frame in held_frames),
              'every saved frame during the held loss preserves desktop participation and OpenXR unavailability')
        if reconnect_frames:
            interrupted=replay[reconnect_frames[0]['sequence']-1:reconnect_frames[2]['sequence']]
            check(len(interrupted)>1 and all({row['id']:row['connected'] for row in frame['packet']['frame']['players']}
                  == {desktop_id:True,tracked_id:False} for frame in interrupted),
                  'sealed replay preserves only the tracked UDP outage through the release of right Vive menu')
        if revocation_frames:
            check(all(replay[frame['sequence']-1]['packet']==frame for frame in revocation_frames),
                  'sealed replay preserves each original admission, revocation, refusal and replacement checkpoint')
            inactive=replay[revocation_frames[1]['sequence']-1:revocation_frames[-2]['sequence']]
            peer_ready_by_revision={}
            for value in inactive:
                saved=value['packet']
                frame=saved['frame']
                connected={row['id'] for row in frame['players'] if row['connected']}
                assert frame['phase']=='Preparing' and not saved['suspended'] and connected<={desktop_id}
                peer_ready_by_revision.setdefault(saved['observedSequence'],[]).append(desktop_id in connected)
            # Preparing rebuilds pose state when the roster changes. Only the prefix before the next valid pose may be empty.
            check(set(peer_ready_by_revision)=={revocation_frames[1]['observedSequence'],revocation_frames[-2]['observedSequence']}
                  and all(any(rows) and all(rows[rows.index(True):]) for rows in peer_ready_by_revision.values()),
                  'sealed replay excludes the old ticket and retains the peer after pose reacquisition in each roster revision')
            result=request('/api/player-tickets/validate',{'sessionId':sid,'ticket':renewed['ticket'],'protocolVersion':2},role='GameServer',expected=403)
            check(result['error']=='Player ticket no longer matches the current admission.',
                  'the replacement ticket also becomes invalid when the original session ends')
        check(all(magazine_at(frame['packet'])==magazine for frame in replay[packet['sequence']-1:released['sequence']]),
              'sealed playback confirms no firing throughout tracking loss, held recovery and release')
        shots=[(frame['packet']['sequence'],event) for frame in replay
               for event in frame['packet']['events'] if event['kind']=='ShotFired']
        check(len(shots)==1 and released['sequence']<shots[0][0]<=fired['sequence']
              and shots[0][1]['playerId']==tracked_id and shots[0][1]['hasRay'],
              'sealed playback contains one ray-bearing shot by the original OpenXR player after the new press')
        if feed is not None:
            event=shots[0][1]
            accepted=next(row for row in request(session+'/events?limit=500') if row['eventId']==signal['eventId'])
            report=accepted['payload']['report']
            check(report['reportId']==signal['reportId']==event['eventId'] and report['shotId']==event['shotId'],
                  'the acknowledged recoil signal matches the original accepted combat report and sealed shot identifiers')
        for client in clients_for_room:
            log=client_log(client)
            finals=[json.loads(line.removeprefix('VR_CLIENT_DEBRIEF_FINAL ')) for line in log.splitlines() if line.startswith('VR_CLIENT_DEBRIEF_FINAL ')]
            connections=re.findall(r'^VR_CLIENT_CONNECTED id=(\d+)$',log,re.M)
            expected_connections=tracked_connection_ids if client is tracked else connections[:1]
            check(venue.player_result_phase(log)=='acknowledged' and len(finals)==1 and connections and connections==expected_connections,
                  'original result and terminal disconnect on the last accepted connection')
            debrief.validate_result(finals[0],{'id':sid},client['player'],entry['sealed'])
            check(finals[0]['ammoUsed']==int(client is tracked),'sealed ammunition matches the original player input')
            client.update(final=finals[0],connection=int(connections[-1]))
            save(client['player']['id']+'-result.json',client['final'])
            stop_player(client)
        verify_delivery(entry,clients_for_room)

    def verify_interrupted_replay(entry, client):
        session = '/api/sessions/' + entry['sessionId']
        path = session + '/world'
        saved = request(path)
        state = request(session)
        stats = request(session + '/statistics')
        check(state['state'] == 'Ended' and not state['combatStream']['sealed'] and stats['pendingTelemetry']
              and not saved['complete'] and saved['acceptedSequence'] > 1,
              'interrupted source leaves accepted frames and pending combat after End')
        raw, headers = request(path + '/watch?mode=replay&fromFrame=1&throughFrame=latest&rate=4', role='Room1', raw_response=True)
        messages = []
        for block in raw.decode('utf-8').strip().split('\n\n'):
            kind, data = block.split('\n', maxsplit=1)
            messages.append((kind.removeprefix('event: '), json.loads(data.removeprefix('data: '))))
        frames = [value for kind, value in messages if kind == 'frame']
        tail = saved['acceptedSequence']
        check(headers.get_content_type() == 'text/event-stream' and messages[0] == ('header', saved)
              and messages[-1] == ('saved-end', saved) and all(kind != 'complete' for kind, _ in messages)
              and [frame['packet']['sequence'] for frame in frames] == list(range(1, tail + 1)),
              'interrupted native replay closes at the exact saved boundary without a seal')
        exact = request(path + f'/frames/{tail}', role='Room1')
        check(frames[-1] == exact and exact['packet']['frame']['phase'] == 'Running'
              and any(row['damageTaken'] > 0 for row in exact['statistics']) and request(path) == saved,
              'saved native tail retains exact original damage and statistics')
        request(session + '/report.csv', expected=409)
        request(session + '/rooms/1/report.csv', role='Room1', expected=409)
        stop_player(client)
        check('VR_CLIENT_DEBRIEF_FINAL ' not in client['log'].read_text(encoding='utf-8', errors='replace'),
              'interrupted run gives neither a final operator CSV nor a player final result')
        save('parent-exit-saved-replay.json', {'world': saved, 'combatAcceptedSequence': state['combatStream']['acceptedSequence'],
             'terminalEvent': messages[-1][0], 'frames': frames, 'finalCsvAvailable': False, 'playerFinalReceived': False})
    def verify_quest_tracking(linked, target_status='not-tracked', checkpoint=None):
        mode='linked' if linked else 'independent'
        bundle=runtime/(mode+'-vr-venue-connections.zip')
        full_venue=['-AllHeadsets'] if args.check_quest_vr_partial_map else []
        tracking=subprocess.run([shutil.which('pwsh'),'-NoProfile','-File',str(ROOT/'scripts/deploy-quest.ps1'),
            '-VenueBundle',str(bundle),'-ManagementApi',uri,'-VerifyTrackedSeats','-AdbPath',str(runtime/'absent-adb.exe'),
            *full_venue],env={**os.environ,'VR_COMMAND_MASTER_KEY':keys['Master']},timeout=25,encoding='utf-8',capture_output=True)
        report=json.loads(tracking.stdout)
        suffix='-'+checkpoint if checkpoint else ''
        save(mode+'-vr-venue-tracked-readiness'+suffix+'.json',report)
        check(tracking.returncode==1 and report['complete'] is False and report['managementVerified'] is True
              and [(row['roomId'],row['seat'],row['status'],row['sourceState']) for row in report['seats']]==
                  [(room,seat,target_status if (room,seat)==(5,2) else 'not-tracked','Fresh')
                   for room in range(1,6) for seat in range(1,6)],
              mode+' original venue ZIP reports room 5 seat 2 '+target_status+' and the remaining seats not-tracked')
        if full_venue:
            check(report['scope']=='venue' and [(row['roomId'],row['seat'],row['registeredHeadset']) for row in report['seats']]==
                  [(room,seat,'ViveXr' if seat in (2,4) else 'Quest3') for room in range(1,6) for seat in range(1,6)],
                  mode+' venue tracking includes all original Quest and VIVE admissions')

    def verify_venue_openxr(entries,round_clients,linked):
        mode='linked' if linked else 'independent'
        entry=next(item for item in entries if 'openxrPlayerId' in item)
        tracked=entry['openxrPlayerId'];sid=entry['sessionId'];session='/api/sessions/'+sid
        original=next(c for c in round_clients if c['player']['id']==tracked)
        scoped={c['player']['id']:c['player'] for c in round_clients if c['sessionId']==sid}
        sessions_by_room={c['player']['roomId']:c['sessionId'] for c in round_clients}
        begin=read(out/(entry['label']+'-running.json'))['acceptedBeginSequence']
        config_hash=package.digest(original['configPath'])

        def checkpoint(available, minimum_tick):
            rooms=request('/api/rooms/readiness')['rooms']
            if {row['roomId']:row['sessionId'] for row in rooms}!=sessions_by_room or len(rooms)!=5:
                return None
            if any(row['sourceState']!='Fresh' or row['registered']!=5 or row['simulatedReady']!=(4 if row['roomId']==5 else 5)
                   or row['trackedReady']!=int(row['roomId']==5 and available)
                   or row['vrParticipation']['awaitingPose']!=([2] if row['roomId']==5 and not available else []) for row in rooms):
                return None
            report=request(session+'/readiness')
            if report['sourceState']!='Fresh' or report['observedSequence']!=begin or report['sessionSequence']!=begin:
                return None
            expected={(pid,row['admissionId'],row['roomId'],row['seat'],pid!=tracked or available) for pid,row in scoped.items()}
            if {(row['playerId'],row['admissionId'],row['roomId'],row['seat'],row['canParticipate']) for row in report['players']}!=expected:
                return None
            packet=request(session+'/world/frames/'+str(report['worldSequence']))['packet']
            frame=packet['frame']
            rigs={row['id']:row['rig']['kind'] for row in frame['players'] if row['connected']}
            expected_rigs={pid:'Tracked' if pid==tracked else 'Simulated' for pid in scoped if pid!=tracked or available}
            if packet['observedSequence']==begin and frame['phase']=='Running' and frame['tick']>=minimum_tick and rigs==expected_rigs:
                return {'packet':packet,'rooms':rooms,'readiness':report}
            return None

        stage('running-venue-openxr',mode=mode)
        ready=wait(lambda:checkpoint(True,1),20,mode+' original OpenXR venue seat')
        verify_quest_tracking(linked,'tracked-ready','initial')
        marker=entry['openxrLossMarker']
        marker.touch(exist_ok=False)
        try:
            lost=wait(lambda:checkpoint(False,ready['packet']['frame']['tick']+1),15,mode+' original OpenXR loss')
            verify_quest_tracking(linked,'awaiting-tracked-pose','lost')
            held=wait(lambda:checkpoint(False,lost['packet']['frame']['tick']+14),15,mode+' isolated held tracking loss')
        finally:
            marker.unlink()
        recovered=wait(lambda:checkpoint(True,held['packet']['frame']['tick']+1),15,mode+' original OpenXR recovery')
        verify_quest_tracking(linked,'tracked-ready','recovered')
        packets=[value['packet'] for value in (ready,lost,held,recovered)]
        first,last=(next(row for row in packet['frame']['players'] if row['id']==tracked) for packet in (packets[0],packets[-1]))
        x_offsets=[last['head']['x']-first['head']['x'],*[last['rig'][hand]['x']-first['rig'][hand]['x'] for hand in ('left','right')]]
        log=original['log'].read_text(encoding='utf-8',errors='replace')
        check(all(abs(offset-.2)<.001 for offset in x_offsets) and package.digest(original['configPath'])==config_hash
              and log.count('VR_CLIENT_CONNECTED id=')==1 and 'VR_CLIENT_DISCONNECTED' not in log
              and 'VR_OPENXR_STARTUP status=active' in log and 'Runtime Name: Unity Mock Runtime' in log
              and original['witness'].kernel.WaitForSingleObject(original['witness'].handle,0)==258,
              mode+' only room 5 seat 2 loses tracked readiness and recovers new poses on the original OpenXR connection')
        entry['venueOpenxr']={'packets':packets,'players':list(scoped)}
        save(mode+'-venue-openxr-checkpoints.json',{'ready':ready,'lost':lost,'held':held,'recovered':recovered,
            'mockRuntimeSha256':package.digest(runtime_file),'fixtureSha256':package.digest(args.openxr_mock_pose_dll)})

    def verify_room_readiness(round_clients,linked):
        expected={client['player']['roomId']:client['sessionId'] for client in round_clients}
        def all_ready():
            summary=request('/api/rooms/readiness')
            rows=summary['rooms']
            if summary['version']!=1 or len(rows)!=5 or {row['roomId']:row['sessionId'] for row in rows}!=expected:
                return None
            return summary if all(row['sourceState']=='Fresh' and row['registered']==5 and
                row['trackedReady']==int(args.check_venue_openxr and row['roomId']==5)
                and row['simulatedReady']==5-row['trackedReady'] for row in rows) else None
        save(('linked' if linked else 'independent')+'-room-readiness.json',wait(all_ready,20,'five fresh room aggregates'))
        check(True,('Linked' if linked else 'Independent')+' has five fresh 5/5 room counts with expected rig types')
        room=request('/api/rooms/readiness',role='Room1')
        check(room['version']==1 and len(room['rooms'])==1 and room['rooms'][0]['roomId']==1
            and room['rooms'][0]['sessionId']==expected[1],'room operator only receives its own active room aggregate')
    def verify_room_participation(entries, round_clients, linked):
        mode = 'Linked' if linked else 'Independent'
        room, seat = 4, 3
        index = next(i for i, client in enumerate(round_clients)
                     if (client['player']['roomId'], client['player']['seat'] + 1) == (room, seat))
        original = round_clients[index]
        entry = next(item for item in entries if item['sessionId'] == original['sessionId'])
        connections = re.findall(r'^VR_CLIENT_CONNECTED id=(\d+)$', original['log'].read_text(encoding='utf-8'), re.M)
        if len(connections) != 1: raise RuntimeError('Expected one original connection for the target seat')
        initial = original['configPath'].read_bytes()
        expected = {client['player']['roomId']:client['sessionId'] for client in round_clients}

        def snapshot(missing):
            rows = request('/api/rooms/readiness')['rooms']
            if {row['roomId']:row['sessionId'] for row in rows} != expected: return None
            return rows if all(row['sourceState'] == 'Fresh' and row['registered'] == 5 and row['trackedReady'] == 0
                and row['simulatedReady'] == (4 if missing and row['roomId'] == room else 5)
                and row.get('vrParticipation') == {'awaitingAdmission': [], 'awaitingPose': [seat] if missing and row['roomId'] == room else [], 'eliminated': []}
                for row in rows) else None

        before = wait(lambda:snapshot(False), 15, mode+' original 25 VR seats')
        stop_player(original)
        missing = wait(lambda:snapshot(True), 20, mode+' only room 4 seat 3 missing its pose')
        check(True, mode+' loss identifies the exact original VR seat while the other 24 remain participating')
        scoped = request('/api/rooms/readiness', role='Room4')['rooms']
        check(len(scoped) == 1 and scoped[0]['roomId'] == room and scoped[0]['vrParticipation']['awaitingPose'] == [seat],
              mode+' only the affected room details are visible to its room controller')
        if args.observe_closure_ui and not linked:
            alert = wait(lambda:read(observer_out/'participation-alert.json') if (observer_out/'participation-alert.json').is_file() else None,
                         10, 'actual console highlights only the missing VR seat')
            check(alert['roomId'] == room and alert['seat'] == seat, 'shipped console identifies the affected native VR seat')
        server_log = entry['work']/'server.log'
        wait(lambda:f'VR_SERVER_CLIENT_LEFT id={connections[0]}\n' in server_log.read_text(encoding='utf-8'), 50,
             mode+' original UDP transport release')
        config = original['configPath'].with_stem(original['configPath'].stem+'-reconnected')
        with config.open('xb') as stream: stream.write(initial)
        recovered = packaged_player(entry, original['player'], config)
        round_clients[index] = recovered
        after = wait(lambda:snapshot(False), 30, mode+' original admission restores all five room counts')
        new_connections = re.findall(r'^VR_CLIENT_CONNECTED id=(\d+)$', recovered['log'].read_text(encoding='utf-8'), re.M)
        check(len(new_connections) == 1 and new_connections != connections and recovered['nativePid'] != original['nativePid']
              and original['configPath'].read_bytes() == initial, mode+' replacement process uses the same original admission and clears the alert')
        if args.observe_closure_ui and not linked:
            recovered_ui = wait(lambda:read(observer_out/'participation-recovered.json') if (observer_out/'participation-recovered.json').is_file() else None,
                                10, 'actual console clears the original VR alert')
            check(recovered_ui['rooms'] == [1,2,3,4,5], 'shipped console clears the seat warning and restores all five actual room counts')
        save(mode.lower()+'-room-participation.json', {'before':before,'missing':missing,'after':after,
             'roomId':room,'seat':seat,'oldConnectionId':connections[0],'newConnectionId':new_connections[0]})
    def verify_venue_environment(entries, linked):
        route = '/api/venue/phase'
        mode = 'linked' if linked else 'independent'
        sessions = {entry['sessionId'] for entry in entries}
        evidence = []
        for weather, time_of_day, lightning in [('Storm', 'Night', True), ('Clear', 'Day', False)]:
            preview = request(route)['environment']
            targets = [{key: row[key] for key in ('sessionId', 'phaseSinceSequence', 'environmentSinceSequence')} for row in preview]
            check({row['sessionId'] for row in targets} == sessions
                  and sorted(room for row in preview for room in row['roomIds']) == list(range(1, 6)),
                  f'{mode} {weather} environment preview covers the original five rooms')
            climate = {'weather': weather, 'timeOfDay': time_of_day, 'lightning': lightning}
            body = {'action': 'SetEnvironment', 'targets': targets, 'environment': climate}
            key = str(uuid.uuid4())
            receipt = request(route, body, request_id=key)
            applied = {row['sessionId']: row['appliedAtSequence'] for row in receipt['sessions']}
            def observed():
                rows = request('/api/rooms/readiness')['rooms']
                if len(rows) == 5 and all((status := row.get('venueEnvironment')) and status['worldSequence']
                   and status['appliedAtSequence'] == applied.get(row['sessionId'])
                   and all(status[field] == value for field, value in climate.items()) for row in rows):
                    return rows
            confirmed = wait(observed, 20, f'{mode} {weather} native environment confirmations')
            frames = {}
            for row in confirmed:
                sid = row['sessionId']
                if sid in frames:
                    continue
                sequence = row['venueEnvironment']['worldSequence']
                frames[sid] = request(f'/api/sessions/{sid}/world/frames/{sequence}')['packet']
            check(not receipt['duplicate'] and receipt['requestId'] == key and set(frames) == sessions
                  and all(packet['observedSequence'] >= applied[sid] and packet['weather'] == weather and packet['lightning'] == lightning
                          and packet['frame']['night'] == (time_of_day == 'Night') and packet['frame']['phase'] == 'Running'
                          for sid, packet in frames.items()),
                  f'{mode} {weather} original accepted frames record all three values and their receipt sequence')
            evidence.append({'receipt': receipt, 'rooms': confirmed, 'frames': frames})
        save(mode+'-venue-environment.json', evidence)

    def verify_room_clocks(entries, linked):
        mode = 'linked' if linked else 'independent'
        expected = {room: entries[0 if linked else room-1]['sessionId'] for room in range(1, 6)}
        def snapshot(phase, after=None, minimum=None):
            response = request('/api/rooms/readiness')
            rows = response['rooms']
            if [(row['roomId'], row['sessionId']) for row in rows] != list(expected.items()): return None
            for row in rows:
                room = row['roomId']; clock = row.get('clock')
                if not clock or row['sourceState'] != 'Fresh' or clock['phase'] != (phase if linked or room == 1 else 'Running') \
                    or clock['durationSeconds'] != 600 or clock['remainingSeconds'] != max(0, 600-clock['elapsedSeconds']) \
                    or clock['autoEnd'] != (linked or room == 1): return None
                if after and (linked or room == 1) and row['sessionSequence'] < after: return None
            if linked and any(row['clock'] != rows[0]['clock'] for row in rows): return None
            if minimum and rows[minimum[0]-1]['clock']['elapsedSeconds'] <= minimum[1]: return None
            return rows
        running = wait(lambda: snapshot('Running'), 15, mode+' five native room clocks')
        check(True, mode+' original active clocks publish per-room policy and one identical value for a linked source')
        own = request('/api/rooms/readiness', role='Room2')['rooms']
        check(len(own) == 1 and own[0]['roomId'] == 2 and own[0]['sessionId'] == expected[2], mode+' Room2 receives only its scoped clock row')
        pause = command(expected[1], 'Pause')['appliedAtSequence']
        first = wait(lambda: snapshot('Paused', pause), 15, mode+' accepted native paused clock')
        if linked:
            time.sleep(1.1)
            frozen = wait(lambda: snapshot('Paused', pause), 15, mode+' linked clock remains paused')
        else:
            frozen = wait(lambda: snapshot('Paused', pause, (2, first[1]['clock']['elapsedSeconds'])), 15, 'another independent room advances')
        check(frozen[0]['clock'] == first[0]['clock'], mode+' original pause retains exactly the accepted activity time')
        resume = command(expected[1], 'Resume')['appliedAtSequence']
        resumed = wait(lambda: snapshot('Running', resume, (1, first[0]['clock']['elapsedSeconds'])), 15, mode+' resume advances original clock')
        check(True, mode+' accepts a new running clock after the original Resume')
        save(mode+'-room-clocks.json', {'running':running, 'paused':first, 'frozen':frozen, 'resumed':resumed})
    def verify_venue_phase(entries, linked):
        mode = 'linked' if linked else 'independent'
        room_two = None if linked else entries[1]['sessionId']
        if room_two: command(room_two, 'Pause')
        route = '/api/venue/phase'
        def submit(action):
            targets = request(route)[action.lower()]
            wanted = {entry['sessionId'] for entry in entries if entry['sessionId'] != room_two}
            assert {row['sessionId'] for row in targets} == wanted
            body = {'action': action, 'targets': [{key: row[key] for key in ('sessionId', 'phaseSinceSequence')} for row in targets]}
            key = str(uuid.uuid4())
            receipt = request(route, body, request_id=key)
            assert not receipt['duplicate'] and receipt['requestId'] == key and receipt['action'] == action
            assert {row['sessionId'] for row in receipt['sessions']} == wanted
            return body, key, receipt
        def observe_phase(phase, receipt, previous=None):
            rows = request('/api/rooms/readiness')['rooms']
            applied = {row['sessionId']: row['appliedAtSequence'] for row in receipt['sessions']}
            if len(rows) != 5: return None
            for row in rows:
                clock = row.get('clock'); manual = row['sessionId'] == room_two
                if not clock or clock['phase'] != ('Paused' if manual else phase): return None
                if not manual and (row['sessionId'] not in applied or row['sessionSequence'] < applied[row['sessionId']]): return None
                status = row.get('venuePhase')
                if manual and status is not None: return None
                if not manual and (not status or status['action'] != receipt['action'] or status['appliedAtSequence'] != applied[row['sessionId']]
                    or not status['worldSequence'] or status['readyToResume'] != (phase == 'Paused')): return None
                if previous:
                    before = previous[row['roomId']-1]['clock']['elapsedSeconds']
                    if manual and clock['elapsedSeconds'] != before or not manual and clock['elapsedSeconds'] <= before: return None
            return rows
        body, key, pause = submit('Pause')
        paused = wait(lambda: observe_phase('Paused', pause), 15, mode+' all original paused sources observe venue command')
        check(True, mode+' venue Pause reaches all targeted native sources with one management receipt')
        _, _, resume = submit('Resume')
        resumed = wait(lambda: observe_phase('Running', resume, paused), 15, mode+' venue Resume advances only targeted native sources')
        check(True, mode+' venue Resume advances the target clocks and preserves a manual pause when present')
        retry = request(route, body, request_id=key)
        check(retry['duplicate'] and retry['sessions'] == pause['sessions'] and request(route)['resume'] == [],
              mode+' late venue Pause retry keeps the original receipt without pausing again')
        save(mode+'-venue-phase.json', {'pause': pause, 'paused': paused, 'resume': resume, 'resumed': resumed, 'pauseRetry': retry})
        if room_two: command(room_two, 'Resume')
    def verify_mr_alignment_archive(entry, files):
        sid = entry['sessionId']
        terminal = request('/api/sessions/'+sid)
        report = read(entry['reportPath'])
        header = report['finalWorld']['header']
        supplied = {room: files[room] for room in terminal['roomIds']}
        proofs = field.verify_room_alignments(terminal, header, supplied)
        check(terminal['state'] == 'Ended' and proofs == [{'roomId': room, 'sha256': package.digest(path)}
              for room, path in sorted(supplied.items())], entry['label']+' sealed MR source matches the exact locked room exports')
        room = terminal['roomIds'][0]
        other = next(path for number, path in files.items() if number != room)
        try:
            field.verify_room_alignments(terminal, header, dict(supplied) | {room: other})
        except field.EvidenceError as error:
            check('bytes differ' in str(error), entry['label']+' archive rejects an original export from another room')
        else:
            raise RuntimeError('MR archive unexpectedly accepted another room export')
        journal = entry['work']/'telemetry'/(sid+'.worldlog')
        try:
            field.verify_world_journal(journal, report['finalWorld'], report['finalCombatStream']['acceptedSequence'], terminal['sequence'], None)
        except field.EvidenceError as error:
            check('active play' in str(error) and read(out/(entry['label']+'-journal.json'))['runningFrames'] == 0,
                  entry['label']+' Preparing-only archive still cannot satisfy played field evidence')
        else:
            raise RuntimeError('MR Preparing-only archive unexpectedly satisfied the played-session gate')
        save(entry['label']+'-alignment-archive.json', {'rooms': proofs, 'scope': 'Native MR Preparing seal and original export locks',
              'playedFieldEvidenceAccepted': False})

    def save_room_alignment_exports(files):
        paths = {room: out/f'room-{room:02}-locked-alignment.json' for room in files}
        for room, path in paths.items():
            path.write_bytes(files[room])
        return paths

    def check_mr_venue_bundle():
        pwsh = shutil.which('pwsh')
        if not pwsh: raise RuntimeError('PowerShell is required for Quest venue preflight')
        room_ids = list(range(1, 6))
        markers = [{'room': {'x': x, 'z': z}, 'tracking': {'x': x, 'z': z}} for x, z in [(-2, -2), (2, -2), (-2, 2)]]
        files = {room: json.dumps(request('/api/room-alignment', {'roomId': room, 'markers': markers})).encode() for room in room_ids}
        hashes = {room: hashlib.sha256(data).hexdigest() for room, data in files.items()}
        alignment_exports = save_room_alignment_exports(files)
        for mode in ('Linked', 'Independent'):
            stage('native-mr-venue-bundle', mode=mode)
            if mode == 'Linked':
                states = [create(room_ids, 'MR venue linked', experience='MR')]
            else:
                mission = save_mission('MR venue independent', experience='MR')
                states = request('/api/sessions/independent-set', {'missionId': mission['id']}, expected=201, request_id=str(uuid.uuid4()))['sessions']
                sessions.extend(state['id'] for state in states)
            entries, rooms = [], []
            for state in states:
                sid = state['id']; route = '/api/sessions/' + sid
                pins = {f'room{room}': hashes[room] for room in state['roomIds']}
                request(route + '/commands', {'commandId': str(uuid.uuid4()), 'action': 'SetRoomAlignment', 'roomAlignment': pins})
                for room in state['roomIds']:
                    for seat in range(1, 6):
                        state = request(route + '/players', {'playerId': str(uuid.uuid4()), 'roomId': room, 'name': f'MR venue {room}/{seat}', 'headset': 'Quest3'})
                    rooms.append({'roomId': room, 'sessionId': sid, 'alignmentFile': base64.b64encode(files[room]).decode(),
                        'players': [{'playerId': row['id'], 'admissionId': row['admissionId']} for row in state['players'] if row['roomId'] == room]})
                entries.append(launch(state, f'mr-venue-{mode.lower()}-{state["roomIds"][0]}'))
            before = request('/api/sessions')
            raw, headers = request('/api/mr-deployment/venue-bundle', {'topology': mode, 'rooms': rooms}, raw_response=True)
            check(headers['Cache-Control'] == 'no-store' and headers.get_content_type() == 'application/zip', mode + ' native endpoint export is a non-cacheable ZIP')
            with tempfile.TemporaryDirectory(prefix='deployment-', dir=runtime) as scratch:
                destination = Path(scratch).resolve()
                if destination.parent != runtime: raise RuntimeError('Invalid owned deployment scratch directory')
                expected = {'venue.json', *(f'room-{room:02}-{suffix}' for room in room_ids for suffix in ('alignment.json', 'connections.zip'))}
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    assert len(archive.namelist()) == len(expected) and set(archive.namelist()) == expected
                    manifest_rooms = json.loads(archive.read('venue.json'))['rooms']
                    assert [(row['roomId'], row['sessionId']) for row in manifest_rooms] == [(row['roomId'], row['sessionId']) for row in rooms]
                    assert all(archive.read(f'room-{room:02}-alignment.json') == files[room] for room in room_ids)
                bundle = destination / 'quest-mr-venue.zip'
                bundle.write_bytes(raw)
                deploy = [pwsh, '-NoProfile', '-File', str(ROOT/'scripts/deploy-quest.ps1'), '-VenueBundle', str(bundle), '-ManagementApi', uri]
                environment = {**os.environ, 'VR_COMMAND_MASTER_KEY': keys['Master']}
                report = json.loads(subprocess.check_output(deploy, env=environment, timeout=25, encoding='utf-8', cwd=destination))
                seat = json.loads(subprocess.check_output([*deploy, '-RoomId', '4', '-Seat', '2', '-CheckOnly'],
                    env=environment, timeout=25, encoding='utf-8', cwd=destination))
                assert list(destination.iterdir()) == [bundle]
                if args.check_mapped_quest:
                    verify_mapped_quest(deploy, destination, environment, raw, mode, files, hashes)
                    subset = destination / 'partial'
                    subset.mkdir()
                    verify_mapped_quest(deploy, subset, environment, raw, mode, files, hashes, partial=True)
            endpoints = {entry['sessionId']: f'{address}:{entry["ready"]["port"]}' for entry in entries}
            check(report['managementVerified'] and report['alignmentPinsVerified'] and report['topology'] == mode and report['seats'] == 25
                and [(row['roomId'], row['seats'], row['endpoint'], row['alignmentSha256']) for row in report['rooms']] == [
                    (room['roomId'], 5, endpoints[room['sessionId']], hashes[room['roomId']]) for room in rooms]
                and request('/api/sessions') == before,
                mode + ' actual Quest preflight verifies 25 signed files, original calibration and owned UDP endpoints without writing session events')
            save(f'mr-venue-{mode.lower()}-deployment.json', report)
            check(seat['roomId'] == 4 and seat['seat'] == 2 and seat['mode'] == 'MR' and seat['managementVerified']
                and seat['alignmentPinsVerified'] and seat['alignmentSha256'] == hashes[4],
                mode + ' direct ZIP preflight selects the original room 4 seat 2 without extraction or ADB')
            save(f'mr-venue-{mode.lower()}-seat.json', seat)
            for entry in entries: command(entry['sessionId'], 'End')
            for entry in entries:
                finish(entry)
                verify_mr_alignment_archive(entry, alignment_exports)
    def check_mixed_venue_bundle():
        stage('native-mixed-venue-bundle')
        markers = [{'room': {'x': x, 'z': z}, 'tracking': {'x': x, 'z': z}} for x, z in [(-2, -2), (2, -2), (-2, 2)]]
        files = {room: b'\xef\xbb\xbf' + json.dumps(request('/api/room-alignment', {'roomId': room, 'markers': markers})).encode() + b'\r\n'
                 for room in (2, 4)}
        hashes = {room: hashlib.sha256(raw).hexdigest() for room, raw in files.items()}
        alignment_exports = save_room_alignment_exports(files)
        endpoint = '/api/mixed-deployment/venue'
        staged = []
        for room in range(1, 6):
            mode = 'MR' if room in files else 'VR'
            state = create([room], f'Mixed venue {room}', experience=mode)
            route = '/api/sessions/' + state['id']
            if room in files:
                request(route + '/commands', {'commandId': str(uuid.uuid4()), 'action': 'SetRoomAlignment',
                                              'roomAlignment': {f'room{room}': hashes[room]}})
            for seat in range(1, 6):
                headset = 'ViveXr' if room == 1 and seat == 2 else 'Quest3'
                state = request(route + '/players', {'playerId': str(uuid.uuid4()), 'roomId': room,
                                'name': f'Mixed venue {room}/{seat}', 'headset': headset})
            staged.append((state, launch(state, f'mixed-room-{room}')))
        before = request('/api/sessions')
        preview_raw, headers = request(endpoint, raw_response=True)
        preview = json.loads(preview_raw)
        check(preview['ready'] and headers['Cache-Control'] == 'no-store'
              and all((row['roomId'], row['sessionId'], row['mode'], row.get('alignmentSha256')) ==
                      (room, state['id'], state['environment']['mode'], hashes.get(room))
                      and (row['endpoint']['address'], row['endpoint']['port'], row['endpoint']['streamId']) ==
                      (address, entry['ready']['port'], entry['ready']['streamId'])
                      and [(seat['number'], seat['playerId'], seat['admissionId']) for seat in row['seats']] ==
                      [(seat['seat']+1, seat['id'], seat['admissionId']) for seat in state['players']]
                      for room, (row, (state, entry)) in enumerate(zip(preview['rooms'], staged, strict=True), 1)),
              'mixed preview binds all 25 current admissions, modes, original streams and locked MR hashes')
        bundle_rooms = [{'roomId': row['roomId'], 'sessionId': row['sessionId'], 'mode': row['mode'],
                         'streamId': row['endpoint']['streamId'],
                         'players': [{key: seat[key] for key in ('playerId', 'admissionId')} for seat in row['seats']],
                         **({'alignmentFile': base64.b64encode(files[row['roomId']]).decode()} if row['roomId'] in files else {})}
                        for row in preview['rooms']]
        request(endpoint, role='Room1', expected=403)
        request(endpoint+'-bundle', {'rooms': bundle_rooms}, role='Room1', expected=403)
        wrong_hash = [dict(row, alignmentFile=base64.b64encode(files[2] + b'\n').decode()) if row['roomId'] == 2 else row for row in bundle_rooms]
        wrong_stream = [dict(row, streamId=str(uuid.uuid4())) if row['roomId'] == 5 else row for row in bundle_rooms]
        check(request(endpoint+'-bundle', {'rooms': wrong_hash}, expected=409)['code'] == 'venue-alignment-mismatch'
              and request(endpoint+'-bundle', {'rooms': wrong_stream}, expected=409)['code'] == 'venue-source-changed',
              'mixed issuance rejects changed alignment bytes or a stale native stream')
        node, pwsh = shutil.which('node'), shutil.which('pwsh')
        if not node or not pwsh: raise RuntimeError('Node and PowerShell are required for the mixed ZIP check')
        with tempfile.TemporaryDirectory(prefix='mixed-', dir=runtime) as scratch:
            destination = Path(scratch).resolve()
            paths = {}
            for room, original in files.items():
                path = destination/f'original-{room}.json'
                path.write_bytes(original)
                paths[room] = str(path)
            descriptor, bundle = destination/'descriptor.json', destination/'vr-mr-venue-deployment.zip'
            descriptor.write_text(json.dumps({'base':uri,'masterKey':keys['Master'],'mode':'Mixed','alignments':paths,
                                              **room_endpoint_descriptor(preview)}),encoding='utf-8')
            with (out/'mixed-venue-browser.log').open('xb') as log:
                subprocess.run([node, str(ROOT/'tests/browser/check-vr-venue-tickets-native.cjs'), str(descriptor), str(bundle),
                                str(out/'mixed-venue-browser.json')], stdout=log, stderr=subprocess.STDOUT, check=True, timeout=65)
            check(read(out/'mixed-venue-browser.json')['complete'], 'shipped browser uploads only the two MR files and downloads the mixed ZIP')
            if args.check_room_endpoints:
                check(read(out/'mixed-venue-browser.json')['verifiedRoomEndpoints'] == 5, 'mixed shipped room cards show five original UDP endpoints')
            raw = bundle.read_bytes()
            live = {'topology': 'Independent', 'rooms': []}
            expected = {'venue.json'}
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                manifest = json.loads(archive.read('venue.json'))
                assert (manifest['version'], manifest['mode'], manifest['topology']) == (2, 'Mixed', 'Independent')
                for row, source in zip(manifest['rooms'], preview['rooms'], strict=True):
                    room = row['roomId']
                    assert row == {'roomId': source['roomId'], 'sessionId': source['sessionId'], 'mode': source['mode'],
                                   'address': address, 'port': source['endpoint']['port'], 'ticketsZip': f'room-{room:02}-connections.zip',
                                   **({'alignmentFile': f'room-{room:02}-alignment.json'} if room in files else {})}
                    expected.add(row['ticketsZip'])
                    wanted = {key: row[key] for key in ('roomId', 'sessionId', 'mode')}
                    if room in files:
                        expected.add(row['alignmentFile'])
                        assert archive.read(row['alignmentFile']) == files[room]
                        wanted['alignmentFile'] = base64.b64encode(files[room]).decode()
                    with zipfile.ZipFile(io.BytesIO(archive.read(row['ticketsZip']))) as inner:
                        names = [f'room-{room:02}-seat-{seat:02}.json' for seat in range(1, 6)]
                        assert sorted(inner.namelist()) == names
                        wanted['connectionFiles'] = [base64.b64encode(inner.read(name)).decode() for name in names]
                    live['rooms'].append(wanted)
                assert sorted(archive.namelist()) == sorted(expected)
            check(True, 'mixed ZIP contains five original room ticket bundles and exactly two unchanged MR alignment files')
            request(endpoint+'-check', live, role='Room1', expected=403)
            accepted = request(endpoint+'-check', live)
            check(accepted['allMatched'] and [(row['roomId'], row['seat'], row['status'], row['headset']) for row in accepted['seats']] ==
                  [(room, seat, 'matched', 'ViveXr' if (room, seat) == (1, 1) else 'Quest3')
                   for room in range(1, 6) for seat in range(5)], 'mixed live check validates all 25 signatures and current headset assignments')
            for room_id in (1, 2):
                room = live['rooms'][room_id-1]
                first = room['connectionFiles'][0]
                changed = json.loads(base64.b64decode(first))
                changed['port'] = 7777 if changed['port'] != 7777 else 7778
                room['connectionFiles'][0] = base64.b64encode(json.dumps(changed).encode()).decode()
                rejected_check = request(endpoint+'-check', live)
                room['connectionFiles'][0] = first
                check(not rejected_check['allMatched'] and [(row['roomId'], row['seat'], row['status']) for row in rejected_check['seats']
                      if row['status'] != 'matched'] == [(room_id, 0, 'endpoint-mismatch')],
                      f'mixed live check rejects a changed {room["mode"]} destination')
            deploy = [pwsh, '-NoProfile', '-File', str(ROOT/'scripts/deploy-quest.ps1'), '-VenueBundle', str(bundle), '-ManagementApi', uri]
            environment = {**os.environ, 'VR_COMMAND_MASTER_KEY': keys['Master']}
            report = json.loads(subprocess.check_output(deploy, env=environment, timeout=25, encoding='utf-8', cwd=destination))
            check(report['mode'] == 'Mixed' and report['managementVerified'] and report['alignmentPinsVerified']
                  and report['seats'] == 25 and [row['mode'] for row in report['rooms']] == ['VR','MR','VR','MR','VR'],
                  'Quest CLI confirms the whole mixed ZIP against the packaged API before selecting seats')
            save('mixed-venue-deployment.json', report)
            if args.check_windows_venue_staging:
                seat_map = destination / 'windows-seat-map.json'
                delivery = destination / 'windows-delivery'
                stage_windows = [*deploy, '-WindowsSeatMap', str(seat_map), '-WindowsOutputDirectory', str(delivery)]
                for room, seat, message in ((2, 1, 'belongs to an MR room'), (1, 1, 'not assigned to VIVE XR')):
                    seat_map.write_text(json.dumps({'version': 1, 'seats': [{'roomId': room, 'seat': seat, 'station': 'PC-A'}]}), encoding='utf-8')
                    denied = subprocess.run(stage_windows, env=environment, timeout=25, encoding='utf-8', capture_output=True)
                    check(denied.returncode != 0 and message in denied.stderr and not delivery.exists(),
                          f'Mixed Windows staging refuses room {room} seat {seat} without publishing files')
                seat_map.write_text(json.dumps({'version': 1, 'seats': [{'roomId': 1, 'seat': 2, 'station': 'PC-A'}]}), encoding='utf-8')
                windows = json.loads(subprocess.check_output(stage_windows, env=environment, timeout=25, encoding='utf-8'))
                file = delivery / 'pc-PC-A-room-01-seat-02.json'
                check(windows['managementVerified'] and windows['topology'] == 'Independent' and len(windows['seats']) == 1
                      and windows['seats'][0]['file'] == file.name and list(delivery.iterdir()) == [file]
                      and file.read_bytes() == base64.b64decode(live['rooms'][0]['connectionFiles'][1]),
                      'Mixed Windows staging preserves only the original signed VR seat')
                save('mixed-venue-windows-staging.json', windows)
            tracking = subprocess.run([*deploy, '-VerifyTrackedSeats', '-AdbPath', str(destination/'absent-adb.exe')],
                env=environment, timeout=25, encoding='utf-8', cwd=destination, capture_output=True)
            tracked = json.loads(tracking.stdout)
            save('mixed-venue-tracked-readiness.json', tracked)
            quest_seats = [(row['roomId'], row['seat'] + 1) for row in accepted['seats'] if row['headset'] == 'Quest3']
            check(tracking.returncode == 1 and tracked['complete'] is False and tracked['managementVerified'] is True
                  and [(row['roomId'], row['seat'], row['status'], row['sourceState']) for row in tracked['seats']] ==
                      [(room, seat, 'awaiting-tracked-pose', 'Fresh') for room, seat in quest_seats],
                  'mixed Quest tracking check distinguishes 24 untracked Quest seats from one VIVE seat')
            tracking = subprocess.run([*deploy, '-VerifyTrackedSeats', '-AllHeadsets', '-AdbPath', str(destination/'absent-adb.exe')],
                env=environment, timeout=25, encoding='utf-8', cwd=destination, capture_output=True)
            tracked = json.loads(tracking.stdout)
            save('mixed-all-headset-readiness.json', tracked)
            check(tracking.returncode == 1 and tracked['complete'] is False and tracked['managementVerified'] is True and tracked['scope'] == 'venue'
                  and [(row['roomId'], row['seat'], row['registeredHeadset'], row['status'], row['sourceState']) for row in tracked['seats']] ==
                      [(row['roomId'], row['seat'] + 1, row['headset'], 'awaiting-tracked-pose', 'Fresh') for row in accepted['seats']],
                  'mixed VR and MR venue tracking checks all 25 original admissions without ADB')
            for room_id, mode in ((1, 'VR'), (2, 'MR')):
                seat = json.loads(subprocess.check_output([*deploy, '-RoomId', str(room_id), '-Seat', '1', '-CheckOnly'],
                                  env=environment, timeout=25, encoding='utf-8', cwd=destination))
                check(seat['roomId'] == room_id and seat['seat'] == 1 and seat['mode'] == mode and seat['managementVerified']
                      and seat.get('alignmentSha256') == hashes.get(room_id), f'single-seat mixed preflight uses the {mode} room settings')
                save(f'mixed-venue-seat-{room_id}.json', seat)
            verify_mapped_quest(deploy, destination, environment, raw, 'Independent', files, hashes, partial=True, mixed=True)
        check(request('/api/sessions') == before, 'mixed issuance, online verification and mock ADB leave management sessions unchanged')
        for state, _ in staged: command(state['id'], 'End')
        for state, entry in staged:
            finish(entry)
            if state['environment']['mode'] == 'MR':
                verify_mr_alignment_archive(entry, alignment_exports)
    def verify_mapped_quest(deploy, destination, environment, raw, mode, files=None, hashes=None, *, partial=False, mixed=False):
        is_vr = files is None
        rows = [{'roomId': room, 'seat': seat, 'serial': f'fixture-{(room-1)*5+seat:02}'} for room in range(1, 6) for seat in range(1, 6)]
        if partial:
            rows = [row for row in rows if row['seat'] == {1:1, 2:3, 3:5, 4:1, 5:3}[row['roomId']]]
        mapping = destination / 'device-map.json'
        mapping.write_text(json.dumps({'version': 1, 'seats': rows[::-1]}), encoding='utf-8')
        mapped = [*deploy, '-DeviceMap', str(mapping), '-ExpectedVersionCode', '61', '-AdbPath', str(ROOT/'tests/fixtures/mock-quest-fleet.ps1')]
        environment = {**environment, 'VR_QUEST_FLEET_FIXTURE': str(destination), 'VR_QUEST_FLEET_FAULTS': ''}
        if partial:
            mapped.append('-AllowPartialMap')
        if partial and is_vr:
            mapping.write_text(json.dumps({'version': 1, 'seats': [*rows, {'roomId': 2, 'seat': 2, 'serial': 'fixture-07'}]}), encoding='utf-8')
            refused = subprocess.run([*mapped, '-DeployMappedSeats'], env=environment, timeout=45, encoding='utf-8',
                                     cwd=destination, capture_output=True)
            result = json.loads(refused.stdout)
            check(refused.returncode == 1 and result['complete'] is False and result['managementVerified'] is True
                  and result['mappedSeats'] == 6 and not any(destination.glob('fixture-*'))
                  and [row for row in result['devices'] if row['status'] != 'ready'] ==
                      [{'roomId': 2, 'seat': 2, 'status': 'seat-headset-mismatch', 'versionCode': 61}],
                  mode + ' a live VIVE assignment blocks all requested Quest writes')
            save(f'vr-venue-{mode.lower()}-partial-rejection.json', result)
            (destination/'adb.log').unlink()
            mapping.write_text(json.dumps({'version': 1, 'seats': rows[::-1]}), encoding='utf-8')
        if partial:
            environment['VR_QUEST_FLEET_FAULTS'] = json.dumps({'fixture-07': 'offline', 'fixture-25': 'wrong-model'})
        count = len(rows)
        def invoke(flag):
            return json.loads(subprocess.check_output([*mapped, flag], env=environment, timeout=45, encoding='utf-8', cwd=destination))
        preview = invoke('-CheckOnly')
        check(preview['complete'] and preview['managementVerified'] and preview['phase'] == 'preflight'
              and (preview.get('mode') == 'VR' if is_vr else preview.get('alignmentPinsVerified') is True)
              and (not mixed or preview.get('mode') == 'Mixed')
              and [row['status'] for row in preview['devices']] == ['ready']*count
              and (not partial or (preview['mappedSeats'], preview['unmappedSeats']) == (count, 25-count))
              and not any(destination.glob('fixture-*')), mode + f' mapped preflight confirms {count} mocked devices with no configuration writes')
        (destination/'adb.log').unlink()
        applied = invoke('-DeployMappedSeats')
        check(applied['complete'] and applied['managementVerified'] and applied['phase'] == 'deployment'
              and (applied.get('mode') == 'VR' if is_vr else applied.get('alignmentPinsVerified') is True)
              and (not mixed or applied.get('mode') == 'Mixed')
              and (not partial or (applied['mappedSeats'], applied['unmappedSeats']) == (count, 25-count))
              and applied['devices'] == [{'roomId': row['roomId'], 'seat': row['seat'], 'status': 'launch-requested', 'versionCode': 61} for row in rows],
              mode + f' mapped deployment submits launch for exactly the {count} requested mock devices')
        with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
            for row in rows:
                room, seat = row['roomId'], row['seat']; remote = destination / row['serial']
                with zipfile.ZipFile(io.BytesIO(bundle.read(f'room-{room:02}-connections.zip'))) as tickets:
                    config = json.loads(tickets.read(f'room-{room:02}-seat-{seat:02}.json'))
                names = {'vr-connection.json'}
                if files is not None and room in files:
                    config.update(questPassthrough=True, requestMixedReality=True)
                    alignment = f'vr-room-alignment-{hashes[room]}.json'
                    assert (remote/alignment).read_bytes() == files[room]
                    names.add(alignment)
                assert read(remote/'vr-connection.json') == config
                assert {item.name for item in remote.iterdir()} == names
        commands = (destination/'adb.log').read_text(encoding='utf-8').splitlines()
        targeted = {line.split()[1] for line in commands if line.startswith('-s ')}
        mr_count = sum(files is not None and row['roomId'] in files for row in rows)
        check(len(commands) == 1 + count * 7 + mr_count * 2 and sum(' shell monkey ' in line for line in commands) == count
              and targeted == {row['serial'] for row in rows}
              and all(' install ' not in line and 'unmapped-device' not in line for line in commands),
              mode + f' all {count} mapped original signed configs are isolated by serial with the expected mode files and no APK installs')
        prefix = 'mixed' if mixed else 'vr' if is_vr else 'mr'
        kind = 'partial' if partial else 'mapped'
        save(f'{prefix}-venue-{mode.lower()}-{kind}-preflight.json', preview)
        save(f'{prefix}-venue-{mode.lower()}-{kind}-deployment.json', applied)
    try:
        subprocess.run([str(control_exe),'--init',str(data),'--port',str(free()),'--report',str(out/'control-init.json')],env=env,check=True,timeout=30);keys=read(data/'operator-keys.json')['OperatorKeys'];marker=read(data/'control-instance.json');uri='http://127.0.0.1:'+str(marker['port'])
        api_ready=out/'control-ready.json';api_stop=out/'control-stop.request';api=subprocess.Popen([str(control_exe),'--run',str(data),'--seconds','1800','--ready-report',str(api_ready),'--stop-file',str(api_stop),'--report',str(out/'control-final.json')],env=env,cwd=out)
        info=wait(lambda:read(api_ready) if api_ready.exists() else None,40,'control startup');api_witness=control.ChildWitness(info['childPid']);check(info['status']=='ready','packaged control API without SDK on PATH');call('verify',['--verify','package'],True)
        if args.check_room_readiness:request('/api/rooms/readiness',role='GameServer',expected=403)
        seed=create([1],'preflight');base=config(seed['id'])
        for name,change in [('master',{'gameServerKey':keys['Master']}),('room-key',{'gameServerKey':keys['Room1']}),('client-role',{'role':'Client'}),('host-role',{'role':'Host'}),('ambiguous-ip',{'address':'127.1'}),('wildcard-advertise',{'address':'0.0.0.0'}),('multicast',{'address':'224.0.0.1'}),('overflow-port',{'port':4294975073}),('extra-key',{'masterKey':'never-pass-to-unity'}),('url-userinfo',{'managementApiUrl':uri.replace('http://','http://user@')})]:rejected(name,dict(base,**change))
        rejected('short-timeout',base,seconds=59)
        if args.peer_diagnostics:rejected('invalid-peer-diagnostics',base,extra=['--peer-diagnostics','off'])
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as occupied:
            occupied.bind((address,0));rejected('occupied-udp',dict(base,port=occupied.getsockname()[1]))
            request('/api/sessions/' + seed['id'] + '/connection-endpoint', expected=404)
            check(request('/api/sessions/' + seed['id'])['combatStream'] is None,
                  'occupied UDP preflight leaves the management session and endpoint unbound')
        command(seed['id'],'End');rejected('ended-session',base)
        # Run both topologies with separate native processes and fresh admissions.
        archived_batch_report = None
        earlier_field_archive = None
        earlier_closure = None
        imported_mission = None
        if args.mission_template:
            with args.mission_template.open('rb') as source:
                raw = source.read(512*1024+1)
            template = request('/api/mission-templates/check-file',raw,method='POST')
            check(template==json.loads(raw) and template['definition']['environment']['mode']=='VR',
                  'destination management verifies the exact exported VR template')
            imported_mission=request('/api/missions',template['definition'],expected=201,request_id=str(uuid.uuid4()))
            check(imported_mission['definition']==template['definition'],'destination management explicitly saves the template as a new mission')
            save('imported-mission.json',imported_mission)
        if args.openxr_mock_only:
            check_openxr_mock()
        for linked in ([] if venue_only or args.openxr_mock_only else [False,True]):
            entries=[];round_clients=[];staged=[]
            batch=None
            if args.prepare_independent_set and not linked:
                if args.check_independent_room_missions:
                    missions=[]
                    for room, weather in enumerate(('Clear','Rain','Fog','Storm','Rain'),1):
                        definition={'name':f'Portable distinct room {room}','briefing':f'Only room {room}', 'durationSeconds':180+30*room,
                            'environment':{'mode':'VR','weather':weather,'timeOfDay':'Night' if room%2 else 'Day','lightning':weather=='Storm'},
                            'enemies':{'count':room+1,'behavior':('Hold','Patrol','Advance')[(room-1)%3],'autoAttack':False},
                            'props':[{'assetId':'barrel','position':{'x':2*room-6,'y':0,'z':2},'yawDegrees':15*room}]}
                        missions.append(request('/api/missions',definition,expected=201))
                    body={'rooms':[{'roomId':room,'missionId':mission['id']} for room,mission in enumerate(missions,1)]}
                else:
                    mission=imported_mission or save_mission('five independently prepared rooms',enemy_count=5 if args.check_room_combat else 1)
                    missions=[mission]*5
                    body={'missionId':mission['id']}
                key=str(uuid.uuid4()); route='/api/sessions/independent-set'
                prepared=request(route,body,expected=201,request_id=key)
                batch=prepared['sessions']
                sessions.extend(state['id'] for state in batch)
                retry=request(route,body,request_id=key)
                check(not prepared['duplicate'] and retry['duplicate'] and retry['sessions']==batch
                      and [state['roomIds'] for state in batch]==[[room] for room in range(1,6)]
                      and all(state['mission']==mission and state['mode']=='Independent' and state['state']=='Preparing' for state,mission in zip(batch,missions)),
                      'one real management request prepares all five native independent sessions and its retry returns the same IDs')
                save('independent-preparation-receipt.json',prepared)
            for rooms in ([[1,2,3,4,5]] if linked else [[r] for r in range(1,6)]):
                enemy_count=5*len(rooms) if args.check_room_combat else 1
                if batch is not None:
                    state=batch[rooms[0]-1]
                elif imported_mission:
                    state=request('/api/sessions',{'missionId':imported_mission['id'],'mode':'Linked','roomIds':rooms},expected=201)
                    sessions.append(state['id'])
                else:
                    state=create(rooms,'linked' if linked else 'independent',enemy_count=enemy_count)
                entry=launch(state,('linked' if linked else 'room-'+str(rooms[0])));entries.append(entry)
                if args.check_room_clocks and (linked or rooms == [1]):
                    request('/api/sessions/'+state['id']+'/commands', {'commandId':str(uuid.uuid4()),'action':'SetMissionClock','missionClock':{'autoEnd':True}})
                entry['combatEnemyCount']=enemy_count
                if not linked and rooms==[1]:rejected('bound-preparing',config(state['id']))
                for room in rooms:
                    if args.check_vr_venue_tickets: staged.append((entry, room, prepare_room_roster(entry, room)))
                    else: round_clients.extend(room_players(entry,room) if player_folder else [player(entry,room)])
            if args.check_vr_venue_tickets: round_clients=venue_ticket_players(staged,linked)
            owner_ids={entry['sessionId']:[c['player']['id'] for c in round_clients if c['sessionId']==entry['sessionId']] for entry in entries}
            if args.check_venue_begin:
                route='/api/venue/phase'
                preview=request(route)['begin']
                targets=[{key:row[key] for key in ('sessionId','phaseSinceSequence','sessionSequence')} for row in preview]
                check({row['sessionId'] for row in targets}==set(owner_ids)
                      and sorted(room for row in preview for room in row['roomIds'])==list(range(1,6)),
                      'native Begin preview covers exactly the original five rooms')
                expected={row['sessionId']:row['sessionSequence'] for row in targets}
                def begin_when_ready():
                    rows=request('/api/rooms/readiness')['rooms']
                    if len(rows)==5 and all(row['venueBeginReady'] and row['sessionSequence']==expected.get(row['sessionId']) for row in rows):
                        return rows
                preparing=wait(begin_when_ready,60,'five fresh original Preparing room aggregates')
                body={'action':'Begin','targets':targets};key=str(uuid.uuid4())
                if args.check_venue_tracking_gate:
                    denied=request(route,{**body,'requireFullTracking':True},request_id=str(uuid.uuid4()),expected=409)
                    unchanged=request(route)['begin']
                    check(all(row['registered']==5 and row['trackedReady']<5 for row in preparing)
                          and denied['code']=='venue-begin-not-ready' and denied['roomIds']==list(range(1,6))
                          and unchanged==preview, 'full tracking Begin refuses the native simulated roster without advancing any room')
                    save(('linked' if linked else 'independent')+'-full-tracking-denied.json',denied)
                receipt=request(route,body,request_id=key)
                applied={row['sessionId']:row['appliedAtSequence'] for row in receipt['sessions']}
                check(not receipt['duplicate'] and applied=={sid:sequence+1 for sid,sequence in expected.items()},
                      'one native Begin reaches exactly the previewed session revisions')
            for entry in entries:
                sid=entry['sessionId'];ids=owner_ids[sid]
                if args.check_venue_begin:
                    sequence=applied[sid]
                else:
                    wait(lambda:observe(entry,ids),60,entry['label']+' original player rigs')
                    sequence=command(sid,'Begin')['session']['sequence']
                running=wait(lambda:observe(entry,ids,sequence),20,entry['label']+' original Begin applied')
                if imported_mission:
                    verify_template_world(entry,imported_mission,running)
                if args.check_independent_room_missions and not linked:
                    room=entries.index(entry)+1
                    mission=missions[room-1]
                    definition=mission['definition']; environment=definition['environment']; enemies=definition['enemies']
                    info=request(f'/api/sessions/{sid}/world')
                    packet=running['packet']; frame=packet['frame']; props=info['header']['props']
                    check(info['header']['roomIds']==[room] and info['header']['missionDurationSeconds']==definition['durationSeconds']
                          and packet['weather']==environment['weather'] and packet['lightning']==environment['lightning']
                          and frame['night']==(environment['timeOfDay']=='Night') and frame['behavior']==enemies['behavior']
                          and frame['autoAttack']==enemies['autoAttack'] and len(frame['enemies'])==enemies['count']
                          and all(enemy['roomId']==room for enemy in frame['enemies']) and len(props)==1
                          and (props[0]['roomId'],props[0]['kind'],props[0]['feet'],props[0]['yaw']) ==
                              (room,'Barrel',{'x':(room-3)*14+2*room-6,'y':0,'z':2},15*room),
                          entry['label']+' native duration, environment, enemies and cover match its own saved mission')
                    save(entry['label']+'-assigned-mission.json',{'mission':mission,'worldHeader':info['header'],'runningSequence':packet['sequence']})
            if args.check_venue_begin:
                def observed_begin():
                    rows=request('/api/rooms/readiness')['rooms']
                    if len(rows)==5 and all((phase:=row.get('venuePhase')) and phase['action']=='Begin'
                       and phase['appliedAtSequence']==applied.get(row['sessionId']) and phase['worldSequence'] for row in rows):
                        return rows
                observed=wait(observed_begin,20,'five fresh Running confirmations of original Begin')
                retry=request(route,body,request_id=key)
                check(retry['duplicate'] and retry['sessions']==receipt['sessions'],
                      'the late native Begin retry returns the same original receipt')
                save(('linked' if linked else 'independent')+'-venue-begin.json',
                     {'preview':preview,'preparing':preparing,'receipt':receipt,'observed':observed,'retry':retry})
            if args.observe_closure_ui and not linked:
                observer_entry=entries[0];descriptor=runtime/'closure-ui-private.json';descriptor.write_text(json.dumps({'base':uri,'masterKey':keys['Master'],'sessionId':observer_entry['sessionId'],'streamId':observer_entry['ready']['streamId'],'endRequestFile':str(out/'closure-end.request'),'roomReadiness':args.check_room_readiness,'roomParticipation':args.check_room_participation}),encoding='utf-8');observer_log=(runtime/'closure-ui.log').open('xb')
                node=shutil.which('node')
                if not node:raise RuntimeError('Test observer requires installed Node; shipped launchers do not')
                observer=subprocess.Popen([node,str(ROOT/'tests/browser/check-closure-native.cjs'),'--descriptor',str(descriptor),'--output',str(observer_out),'--stop-file',str(observer_stop)],stdout=observer_log,stderr=subprocess.STDOUT,cwd=ROOT/'tests/browser')
                def watching():
                    if observer.poll() is not None:raise RuntimeError('Archive UI observer exited before watching')
                    return read(observer_out/'ready.json') if (observer_out/'ready.json').exists() else None
                ready_ui=wait(watching,45,'actual Running console observer');check(ready_ui['selectedSessionId']==observer_entry['sessionId'],'shipped console watches original native Running session')
                if args.check_room_readiness:
                    check(ready_ui['roomReadiness']==[1,2,3,4,5],'shipped console shows all five actual native room counts')
            stage('running-linked' if linked else 'running-five-independent')
            time.sleep(3)
            if player_folder:
                for entry in entries:
                    owners=[c for c in round_clients if c['sessionId']==entry['sessionId']]
                    rooms_by_player={c['player']['id']:c['player']['roomId'] for c in owners}
                    accepted=read(out/(entry['label']+'-running.json'))['acceptedBeginSequence']
                    frame=wait(lambda:observe(entry,rooms_by_player,accepted),20,entry['label']+' live room roster')
                    players=frame['packet']['frame']['players']
                    check(len(players)==len(owners) and {p['id']:p['roomId'] for p in players}==rooms_by_player,
                        entry['label']+' exact connected room roster')
                check(len({c['nativePid'] for c in round_clients})==25 and all(
                    c['process'].poll() is None and c['witness'].kernel.WaitForSingleObject(c['witness'].handle,0)==258
                    for c in round_clients),'25 simultaneous owned native players '+('Linked' if linked else 'Independent'))
            if args.check_venue_openxr:verify_venue_openxr(entries,round_clients,linked)
            elif args.check_quest_vr_deploy or args.check_quest_vr_partial_map:verify_quest_tracking(linked)
            if args.check_room_readiness:verify_room_readiness(round_clients,linked)
            if args.check_room_observer and linked:
                node = shutil.which('node')
                if not node: raise RuntimeError('Node is required to observe the shipped console')
                descriptor = runtime/'room-observer-private.json'
                descriptor.write_text(json.dumps({'base':uri,'masterKey':keys['Master'],'sessionId':entries[0]['sessionId'],
                    'players':[{key:client['player'][key] for key in ('id','roomId','name')} for client in round_clients]}), encoding='utf-8')
                browser_out = out/'room-observer'
                subprocess.run([node, str(ROOT/'tests/browser/check-room-observer-native.cjs'), str(descriptor), str(browser_out)],
                               cwd=ROOT/'tests/browser', check=True, timeout=70)
                observed = read(browser_out/'checks.json')
                check(observed['complete'] and observed['players']==25 and observed['sessionId']==entries[0]['sessionId']
                      and len(observed['checks'])==5 and observed['recent']['roomId']==2
                      and observed['recent']['resumedFrame']>observed['recent']['tail'],
                      'shipped console scopes actors and returns to the same 25-player Linked source after instant replay')
            if args.check_room_participation:verify_room_participation(entries,round_clients,linked)
            if args.check_room_clocks:verify_room_clocks(entries,linked)
            if args.check_venue_environment:verify_venue_environment(entries,linked)
            if args.check_room_combat:
                stage('running-native-ai-combat',mode='Linked' if linked else 'Independent')
                exercise_room_combat(entries,round_clients)
            if args.check_venue_phase:verify_venue_phase(entries,linked)
            if args.venue_concurrent_roster_seconds is not None:
                stage('observing-concurrent-roster', mode='Linked' if linked else 'Independent',
                      requiredSeconds=args.venue_concurrent_roster_seconds)
                time.sleep(args.venue_concurrent_roster_seconds + 3)
            if args.check_venue_end:
                route = '/api/venue/phase'
                preview = request(route)['end']
                targets = [{field: row[field] for field in ('sessionId', 'phaseSinceSequence')} for row in preview]
                check({row['sessionId'] for row in targets} == set(owner_ids)
                      and sorted(room for row in preview for room in row['roomIds']) == list(range(1, 6)),
                      'native End preview covers exactly the original five rooms')
                body = {'action': 'End', 'targets': targets}
                key = str(uuid.uuid4())
                receipt = request(route, body, request_id=key)
                applied = {row['sessionId']: row['appliedAtSequence'] for row in receipt['sessions']}
                initial = request('/api/venue/closure')['batch']
                check(not receipt['duplicate'] and receipt['requestId'] == key and set(applied) == set(owner_ids)
                      and initial['requestId'] == key
                      and {row['sessionId']: row['appliedAtSequence'] for row in initial['sessions']} == applied,
                      'the native End receipt and closure overview identify the same original sessions')
            else:
                for entry in entries:
                    if args.observe_closure_ui and not linked and entry is observer_entry:(out/'closure-end.request').write_text('request one normal UI End',encoding='utf-8')
                    else:command(entry['sessionId'],'End')
            for entry in entries:finish(entry)
            if args.check_venue_end:
                closed = request('/api/venue/closure')['batch']
                retry = request(route, body, request_id=key)
                check(closed['requestId'] == key
                      and {row['sessionId']: row['appliedAtSequence'] for row in closed['sessions']} == applied
                      and sorted(room for row in closed['sessions'] for room in row['roomIds']) == list(range(1, 6))
                      and all(row['combat'] == row['world'] == 'Sealed' for row in closed['sessions']),
                      'the native closure overview confirms both original archive seals for every room')
                check(retry['duplicate'] and retry['sessions'] == receipt['sessions'],
                      'the late native End retry preserves the original batch after sealing')
                save(('linked' if linked else 'independent')+'-venue-end.json',
                     {'preview': preview, 'receipt': receipt, 'initial': initial, 'closed': closed, 'retry': retry})
                if args.check_venue_replay_ui:
                    verify_venue_replay_ui(entries, closed, linked, earlier_closure if args.check_venue_history_ui else None)
                    earlier_closure = closed
            if args.observe_closure_ui and not linked:
                observer.wait(timeout=70);observer_log.close();observer_log=None;ui=read(observer_out/'checks.json');native=read(observer_entry['reportPath'])
                check(observer.returncode==0 and ui['complete'] and ui['browserClosed'],'actual archive UI observer and browser completed / terminal')
                check(ui['sessionId']==observer_entry['sessionId'] and ui['streamId']==native['streamId'] and ui['acceptedWorldSequence']==native['finalWorld']['acceptedSequence'],'shipped UI archive matches exact original native final world boundary')
            for client in round_clients:
                text=client['log'].read_text(encoding='utf-8',errors='replace');check(venue.player_result_phase(text)=='acknowledged','original player result / disconnect '+client['player']['id']);finals=[json.loads(line.split('VR_CLIENT_DEBRIEF_FINAL ',1)[1]) for line in text.splitlines() if 'VR_CLIENT_DEBRIEF_FINAL ' in line];check(len(finals)==1,'one original final result '+client['player']['id']);final=finals[0];entry=next(e for e in entries if e['sessionId']==client['sessionId']);debrief.validate_result(final,{'id':entry['sessionId']},client['player'],entry['sealed']);check(True,'original admission / exact final seals / stats '+client['player']['id']);save(client['player']['id']+'-result.json',final)
                if player_folder:
                    connections=set(re.findall(r'VR_CLIENT_CONNECTED id=(\d+)',text))
                    if len(connections)!=1:raise RuntimeError('Player did not have one original native connection')
                    client['connection']=int(connections.pop())
                    client['final']=final
                else:
                    report_csv=request('/api/sessions/'+client['sessionId']+'/report.csv')
                    (out/(client['player']['id']+'.csv')).write_text(report_csv,encoding='utf-8')
                stop_player(client)
                if player_folder:check(True,'player launcher confirmed original child exit '+client['player']['id'])
            if player_folder:
                evidence_entries = [verify_delivery(entry,[c for c in round_clients if c['sessionId']==entry['sessionId']])
                                    for entry in entries]
                if args.venue_field_evidence:
                    mode = 'Linked' if linked else 'Independent'
                    field_archive = verify_venue_field_evidence(mode, closed, evidence_entries)
                    if earlier_field_archive:
                        check(request(earlier_field_archive['route'], raw_response=True)[0] == Path(earlier_field_archive['zip']).read_bytes(),
                              'The original independent field bundle is byte-identical after the newer Linked batch')
                    if args.check_venue_field_ui:
                        verify_venue_field_ui(mode.lower(), field_archive, earlier_field_archive)
                    earlier_field_archive = field_archive
            if args.check_venue_reports:
                current_batch_report = verify_venue_reports(entries, receipt, linked)
                if archived_batch_report:
                    old_route, old_zip = archived_batch_report
                    check(request(old_route, raw_response=True)[0] == old_zip,
                          'The original independent ZIP is byte-identical after the newer Linked batch')
                archived_batch_report = current_batch_report
        if args.mr_venue_bundle_only: check_mr_venue_bundle()
        if args.mixed_venue_bundle_only: check_mixed_venue_bundle()
        if args.check_managed_mr:
            state=create([1],'managed-mr',experience='MR')
            session='/api/sessions/'+state['id']
            unpinned_file=runtime/'mr-unpinned.json';unpinned_log=runtime/'mr-unpinned.log'
            telemetry=runtime/'mr-unpinned-telemetry'
            unpinned_file.write_text(json.dumps(config(state['id'],telemetryOrigin='GameServer',telemetryDirectory=str(telemetry))),encoding='utf-8')
            child=subprocess.Popen([str(folder/'Runtime/VrCommand.exe'),'-batchmode','-nographics','-job-worker-count','2',
                '-logFile',str(unpinned_log),'--vr-config',str(unpinned_file)],cwd=runtime,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                wait(lambda: unpinned_log.exists() and 'MR REQUIRES PINNED ROOM ALIGNMENT FILES' in unpinned_log.read_text(encoding='utf-8',errors='replace'),30,'MR startup refuses missing pins')
                check('VR_NETWORK_STARTED' not in unpinned_log.read_text(encoding='utf-8',errors='replace')
                      and not telemetry.exists() and request(session)==state,'unpinned MR server does not start networking, attach, or write telemetry')
            finally:
                if child.poll() is None: child.terminate()
                child.wait(timeout=15)
            markers=[{'room':{'x':x,'z':z},'tracking':{'x':x,'z':z}} for x,z in [(-2,-2),(2,-2),(-2,2)]]
            alignment=request('/api/room-alignment',{'roomId':1,'markers':markers})
            alignment_file=out/'managed-mr-room-1-alignment.json';alignment_file.write_text(json.dumps(alignment)+'\n',encoding='utf-8')
            pin={'commandId':str(uuid.uuid4()),'action':'SetRoomAlignment','expectedSequence':state['sequence'],
                 'roomAlignment':{'room1':package.digest(alignment_file)}}
            pinned=request(session+'/commands',pin)
            check(pinned['session']['roomAlignment']['room1']==pin['roomAlignment']['room1']
                  and request(session+'/commands',pin)['duplicate'],'real control service pins the original checked room export before launch')
            mr=launch(pinned['session'],'managed-mr')
            check(read(mr['work']/'server-config.json')['telemetryOrigin']=='GameServer','actual launcher selects GameServer telemetry for MR')
            session='/api/sessions/'+mr['sessionId'];client=player(mr,1)
            server_log=mr['work']/'server.log'
            wait(lambda: 'VR_SERVER_ADMISSION_REJECTED' in server_log.read_text(encoding='utf-8',errors='replace'),30,'MR desktop admission rejection')
            check('VR_SERVER_ADMISSION_APPROVED' not in server_log.read_text(encoding='utf-8',errors='replace'),'ordinary desktop ticket was rejected by the original MR game server')
            stop_player(client)
            request(session+'/commands',{'commandId':str(uuid.uuid4()),'action':'Begin'},expected=409)
            check(request(session)['state']=='Preparing','MR Begin remains Preparing after the missing tracked roster rejection')
            receipt=request(session+'/commands',{'commandId':str(uuid.uuid4()),'action':'SetEnvironment',
                'environment':{'mode':'MR','weather':'Storm','timeOfDay':'Night','lightning':True}})
            def mr_weather():
                metadata=request(session+'/world')
                if metadata['acceptedSequence']==0:return None
                frame=request(session+'/world/frames/'+str(metadata['acceptedSequence']))['packet']
                if frame['observedSequence']>=receipt['session']['sequence']:
                    return metadata,frame
            metadata,frame=wait(mr_weather,20,'original MR environment applied')
            check(metadata['header']['origin']=='GameServer' and metadata['header']['calibration']=='quest-room-mr-v1'
                  and frame['weather']=='Storm' and frame['frame']['night'] and frame['lightning'] and frame['frame']['phase']=='Preparing'
                  and not any(p['connected'] for p in frame['frame']['players']),'real MR source records its profile and operator weather without a connected desktop')
            command(mr['sessionId'],'End');finish(mr)
        if args.check_live_reinforcement:
            props=[{'assetId':'sandbag','position':{'x':x,'y':0,'z':z},'yawDegrees':0} for z in (2,4) for x in (-3,-1,1,3)]
            entry=launch(create([1],'live-reinforcement',props=props),'live-reinforcement',verify_layout=False)
            session='/api/sessions/'+entry['sessionId']
            client=player(entry,1); roster=[client['player']['id']]
            wait(lambda: observe(entry,roster),60,'reinforcement original player')
            begun=command(entry['sessionId'],'Begin')
            original=wait(lambda: observe(entry,roster,begun['appliedAtSequence']),20,'reinforcement Running source')['packet']
            body={'commandId':str(uuid.uuid4()),'action':'SetEnemies','expectedSequence':begun['appliedAtSequence'],
                  'enemies':{'count':85,'behavior':'Hold','autoAttack':False}}
            denied=request(session+'/commands',body,expected=400)
            check(denied['code']=='enemy-capacity-exceeded' and denied['maxCount']==84
                  and request(session)['sequence']==begun['appliedAtSequence'],'Running reinforcement beyond the layout capacity is rejected before mutation')
            body['enemies']['count']=84
            added=request(session+'/commands',body)
            def applied(receipt,phase,count):
                meta=request(session+'/world')
                packet=request(session+'/world/frames/'+str(meta['acceptedSequence']))['packet']
                if (packet['observedSequence']>=receipt['appliedAtSequence'] and packet['frame']['phase']==phase
                        and len(packet['frame']['enemies'])==count):
                    return meta,packet
            metadata,reinforced=wait(lambda: applied(added,'Running',84),20,'original server spawns the accepted count')
            original_id=original['frame']['enemies'][0]['id']
            check(metadata['header']['reinforcementVersion']==1 and reinforced['frame']['enemies'][0]['id']==original_id
                  and all(enemy['roomId']==1 for enemy in reinforced['frame']['enemies']),'recorded native reinforcement preserves the existing enemy and room allocation')
            reduced=request(session+'/commands',{'commandId':str(uuid.uuid4()),'action':'SetEnemies',
                            'enemies':{'count':1,'behavior':'Hold','autoAttack':False}})
            paused=command(entry['sessionId'],'Pause')
            _,after=wait(lambda: applied(paused,'Paused',1),20,'reduced target and Pause apply together')
            check(after['observedSequence']>=reduced['appliedAtSequence'] and after['frame']['enemies'][0]['id']==original_id,
                  'operator can remove the new enemies and pause with the original enemy retained')
            save('live-reinforcement-controls.json',{'denied':denied,'added':added,'reinforced':reinforced,'reduced':reduced,'paused':paused,'after':after})
            command(entry['sessionId'],'End');finish(entry)
            text=client['log'].read_text(encoding='utf-8',errors='replace')
            check(venue.player_result_phase(text)=='acknowledged','reinforcement player confirms its sealed result')
            finals=[json.loads(line.split('VR_CLIENT_DEBRIEF_FINAL ',1)[1]) for line in text.splitlines() if 'VR_CLIENT_DEBRIEF_FINAL ' in line]
            check(len(finals)==1,'reinforcement player receives one original final result')
            debrief.validate_result(finals[0],{'id':entry['sessionId']},client['player'],entry['sealed'])
            save(client['player']['id']+'-result.json',finals[0])
            stop_player(client)
        # A killed launcher must close its already-assigned Job and stop the exact owned native handle.
        crash=launch(create([1],'parent-exit',auto_attack=args.check_interrupted_replay),'parent-exit',listen_address='0.0.0.0')
        if args.check_interrupted_replay:
            crash_client = player(crash, 1)
            roster = [crash_client['player']['id']]
            wait(lambda: observe(crash, roster), 60, 'interrupted round original player')
            begun = command(crash['sessionId'], 'Begin')['session']['sequence']
            def damaged():
                frame = observe(crash, roster, begun)
                return frame and any(row['damageTaken'] > 0 for row in frame['statistics'])
            wait(damaged, 20, 'original player damaged before the owned server exits')
            check(True, 'interrupted native round records original player damage before the crash')
        crash['process'].kill();crash['process'].wait(timeout=10);w=crash['witness'];check(w.kernel.WaitForSingleObject(w.handle,15000)==0,'parent death stops original job child');w.close();crash['witness']=None;check(not crash['reportPath'].exists(),'killed parent cannot publish success');command(crash['sessionId'],'End')
        if args.check_interrupted_replay:
            verify_interrupted_replay(crash, crash_client)
        check(all(x['state']=='Ended' for x in request('/api/sessions?includeEnded=true')),'no active management sessions')
        if args.check_room_endpoints:
            room_rows=request('/api/rooms/readiness')['rooms']
            check(len(room_rows) == 5 and all(row['sessionId'] is None and 'endpoint' not in row for row in room_rows),
                  'ended native sources leave no endpoint in the five current room rows')
        save('evidence.json',{'rounds':rounds,'scope':('One packaged graphical Unity mock OpenXR client and one desktop peer on the same host.' if args.openxr_mock_only else
            'One graphical Unity mock OpenXR client and 24 desktop peers in each same-host venue topology.' if args.check_venue_openxr else
            'Five Windows VR/MR Preparing endpoints and 25 signed files from the console mixed ZIP.' if args.mixed_venue_bundle_only else
            'Real Windows MR Preparing endpoints and 25 signed files per topology.' if args.mr_venue_bundle_only else
            'Three portable packages, five Independent rooms then Linked, 25 simultaneous same-PC Simulation clients per topology.'
            if player_folder else 'Two portable packages, five Independent rooms then Linked, five same-PC Simulation clients per topology.'),
            'managedMrPreparing':args.check_managed_mr,
            'roomCombat':args.check_room_combat,
            'roomParticipation':args.check_room_participation,
            'roomObserver':args.check_room_observer,
            'roomClocks':args.check_room_clocks,
            'venuePhase':args.check_venue_phase,
            'venueBegin':args.check_venue_begin,
            'venueEnd':args.check_venue_end,
            'venueReports':args.check_venue_reports,
            'venueReplayUi':args.check_venue_replay_ui,
            'venueHistoryUi':args.check_venue_history_ui,
            'venueFieldEvidence':args.venue_field_evidence,
            'venueFieldUi':args.check_venue_field_ui,
            'lanPreflight':args.check_lan_preflight,
            'vrVenueTickets':args.check_vr_venue_tickets,
            'questVrDeploy':args.check_quest_vr_deploy,
            'questVrPartialMap':args.check_quest_vr_partial_map,
            'venueOpenxr':args.check_venue_openxr,
            'openxrReconnect':args.check_openxr_reconnect,
            'openxrRevocation':args.check_openxr_revocation,
            'venueEnvironment':args.check_venue_environment,
            'venueEnemies':args.check_venue_enemies,
            'hardwareFeedback':args.check_hardware_feedback or openxr_hardware,
            'hardwareMockPackage':hardware_manifest['toolVersion'] if args.hardware_simulator_package else None,
            'preparedIndependentSet':args.prepare_independent_set,
            'independentRoomMissions':args.check_independent_room_missions,
            'importedMissionTemplate':imported_mission['id'] if imported_mission else None,
            'sourceFingerprint':manifest['build']['sourceFingerprint'],'gameAddress':address})
    except BaseException as error:stage('failed',errorType=type(error).__name__);raise
    finally:
        for gate in reconnect_gates:
            try:gate.close()
            except Exception as e:cleanup.append({'kind':'openxr-reconnect-udp','errorType':type(e).__name__})
        if observer:
            try:
                if observer.poll() is None:observer_stop.write_text('stop owned observer',encoding='utf-8');observer.wait(timeout=20)
                observed=read(observer_out/'checks.json')
                if not observed['browserClosed']:raise RuntimeError('Observer browser cleanup unknown')
                if observer_log:observer_log.close();observer_log=None
            except Exception as e:cleanup.append({'kind':'observer','errorType':type(e).__name__})
        for client in clients:
            try:
                stop_player(client)
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
        for process in hardware_processes:
            try:
                if process.poll() is None:process.terminate()
                process.wait(timeout=10)
            except Exception as e:cleanup.append({'kind':'hardware-mock','errorType':type(e).__name__})
        try:
            if api and api.poll() is None:api_stop.write_text('stop own API',encoding='utf-8');api.wait(timeout=50)
            if api_witness:api_witness.wait();api_witness.close()
        except Exception as e:cleanup.append({'kind':'api','errorType':type(e).__name__})
        remaining={'errors':cleanup,'remainingRunners':[e['label'] for e in runners if e['process'].poll() is None],
                   'remainingClients':[c['player']['id'] for c in clients if c['process'].poll() is None],'apiRemaining':api is not None and api.poll() is None}
        if args.hardware_simulator_package:remaining['remainingHardware']=[process.pid for process in hardware_processes if process.poll() is None]
        if args.check_openxr_reconnect:remaining['remainingReconnectRelays']=sum(gate.thread.is_alive() for gate in reconnect_gates)
        save('cleanup.json',remaining)
        if cleanup:raise RuntimeError('Cleanup not confirmed; do not snapshot live runtime')
        venue.snapshot_runtime(runtime,out/'runtime-snapshot')
    for file in out.glob('*.json'):
        text=file.read_text(encoding='utf-8')
        if keys and any(k in text for k in keys.values()):raise RuntimeError('Public metadata contains a key')
    save('checks.json',{'complete':True,'checks':len(checks),'findings':checks,'runtimeDirectory':str(runtime),
        'packageDirectory':str(folder),'playerPackageDirectory':str(player_folder) if player_folder else None,
        'scope':('Same-machine tracked rig from Unity mock OpenXR and a simulated desktop peer, no physical headset.' if args.openxr_mock_only else
                 'Five Independent rooms then Linked, one Unity mock OpenXR rig and 24 desktop peers per topology, same host.' if args.check_venue_openxr else
                 'Same-machine VR/MR servers in Preparing and mock ADB with no headset client.' if args.mixed_venue_bundle_only else
                 'Same-machine native MR servers in Preparing with no headset client.' if args.mr_venue_bundle_only else
                 'Same-machine VR simulation and a separate MR Preparing admission and seal check.' if args.check_managed_mr else 'Same-machine Simulation only.')
                +' The separate parent-death case intentionally leaves the world unsealed.'})
    print(json.dumps({'complete':True,'checks':len(checks),'directory':str(out)}))
if __name__=='__main__':main()
