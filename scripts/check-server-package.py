"""Exercise portable Windows packages, five rooms, Linked and owned process cleanup."""
import argparse,csv,importlib.util,io,ipaddress,json,os,re,shutil,socket,subprocess,sys,threading,time,urllib.error,urllib.request,uuid,zipfile
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
    p.add_argument('--peer-diagnostics',action='store_true',help='Verify observed UDP peers in Linked and absence in default Independent runs')
    p.add_argument('--field-evidence',action='store_true',help='Verify the management ZIP with the original Linked player and server logs')
    p.add_argument('--check-room-readiness',action='store_true',help='Verify live aggregate pose counts from the management package in both modes')
    p.add_argument('--check-layout-preview',action='store_true',help='Load a saved barricade opening and compare its preview with native world geometry')
    p.add_argument('--check-room-reports',action='store_true',help='Verify scoped Linked CSVs and the ZIP against the full sealed native report')
    p.add_argument('--check-room-combat',action='store_true',help='Require actual enemy damage on every original admission and reconcile each replay frame and final report')
    p.add_argument('--check-hardware-feedback',action='store_true',help='Match live room feedback to the native combat reports')
    p.add_argument('--hardware-simulator-package',type=Path,help='Pass native live feedback through this extracted mock gateway package')
    p.add_argument('--prepare-independent-set',action='store_true',help='Prepare the five independent native sessions in one management request')
    p.add_argument('--check-interrupted-replay', action='store_true', help='Play the saved native prefix after the owned launcher is killed')
    p.add_argument('--check-managed-mr', action='store_true', help='Verify the MR alignment startup gate, desktop rejection and Preparing seal')
    p.add_argument('--check-live-reinforcement', action='store_true', help='Verify a native server accepts only supported live enemy targets and records the result')
    args=p.parse_args()
    if os.name!='nt':p.error('Actual Windows processes required')
    if bool(args.player_package)!=bool(args.game_address):p.error('Provide --player-package and --game-address together')
    if args.peer_diagnostics and not args.player_package:p.error('--peer-diagnostics requires the three-package check')
    if args.field_evidence and not args.peer_diagnostics:p.error('--field-evidence requires --peer-diagnostics')
    if args.check_room_readiness and not args.player_package:p.error('--check-room-readiness requires five players per room')
    if args.check_room_reports and not args.player_package:p.error('--check-room-reports requires the three-package check')
    if args.check_room_combat and not args.check_room_reports:p.error('--check-room-combat requires --check-room-reports')
    if args.check_hardware_feedback and not args.check_room_combat:p.error('--check-hardware-feedback requires --check-room-combat')
    if args.hardware_simulator_package and not args.check_hardware_feedback:p.error('--hardware-simulator-package requires --check-hardware-feedback')
    if args.prepare_independent_set and not args.player_package:p.error('--prepare-independent-set requires the player package')
    address='127.0.0.1'
    if args.game_address:
        if not any(args.game_address in ipaddress.IPv4Network(net) for net in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')):
            p.error('--game-address must be a local private IPv4 address')
        address=str(args.game_address)
        try:free(socket.SOCK_DGRAM,address)
        except OSError:p.error('--game-address must be assigned to this PC')
    folder=args.package.resolve();manifest=package.verify(folder);assert manifest['launcherSourceSha256']==package.digest(ROOT/'tools/WindowsServerLauncher/ServerLauncher.cs')
    player_folder=None
    if args.player_package:
        player_folder=args.player_package.resolve()
        player_package=module('portable_player_package','package-windows-player.py')
        player_manifest=player_package.verify(player_folder)
        if player_manifest['build']['sourceFingerprint']!=manifest['build']['sourceFingerprint']:
            p.error('Player and server packages must share the Unity build source')
    control.package.verify(args.control_package);out=ROOT/'artifacts/server-package-checks'/('run-'+uuid.uuid4().hex);out.mkdir(parents=True,exist_ok=False);runtime=args.runtime_root.resolve()/out.name;runtime.mkdir(parents=True,exist_ok=False)
    (ROOT/'artifacts/server-package-checks-latest-path.txt').write_text(str(out),encoding='utf-8');print(json.dumps({'stage':'starting','directory':str(out)}),flush=True)
    env=dict(os.environ);env.update(PATH=str(Path(os.environ['WINDIR'])/'System32'),DOTNET_ROOT=str(runtime/'absent-dotnet'),DOTNET_MULTILEVEL_LOOKUP='0');exe=folder/'Launch-Server.exe';control_exe=args.control_package.resolve()/'Start-Control.exe';data=runtime/'control';checks=[];runners=[];clients=[];cleanup=[];witnesses=[];api=None;api_witness=None;keys=None;sessions=[];rounds=[];observer=None;observer_log=None;observer_out=out/'closure-ui';observer_stop=out/'closure-ui-stop.request';observer_entry=None
    hardware_processes=[]
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
        req=urllib.request.Request(uri+path,data=None if body is None else json.dumps(body).encode(),headers=h,method=method)
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
    def launch(state,label, *, listen_address=None, verify_layout=True):
        value=config(state['id'], listenAddress=listen_address or address);file=runtime/(label+'.json');file.write_text(json.dumps(value),encoding='utf-8');ready=out/(label+'-ready.json');report=out/(label+'-final.json');work=runtime/(label+'-work')
        diagnostics=args.peer_diagnostics and label=='linked'
        options=['--peer-diagnostics','on'] if diagnostics else []
        child=subprocess.Popen([str(exe),'--run',str(file),'--work',str(work),'--seconds','600','--ready-report',str(ready),'--report',str(report),*options],cwd=out,env=env);entry={'process':child,'readyPath':ready,'reportPath':report,'work':work,'config':value,'label':label,'sessionId':state['id'],'witness':None,'peerDiagnostics':diagnostics};runners.append(entry)
        def is_ready():
            if child.poll() is not None:raise RuntimeError('Server launcher exited before ready '+label)
            return read(ready) if ready.exists() else None
        info=wait(is_ready,100,label+' ready');w=control.ChildWitness(info['childPid']);entry['witness']=w;witnesses.append(w);entry['ready']=info
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
        return entry
    def player(entry,room):
        state=request('/api/sessions/'+entry['sessionId']+'/players',{'playerId':str(uuid.uuid4()),'roomId':room,'name':'Portable server room '+str(room),'headset':'Quest3'},role='Room'+str(room));person=next(x for x in state['players'] if x['roomId']==room)
        invitation=request('/api/sessions/'+state['id']+'/players/'+person['id']+'/join-ticket',{},role='Room'+str(room),admission=person['admissionId']);file=runtime/(entry['label']+'-client-'+str(room)+'.json');file.write_text(json.dumps({'role':'Client','address':address,'port':entry['ready']['port'],'joinTicket':invitation['ticket']}),encoding='utf-8');log=runtime/(file.stem+'.log')
        child=subprocess.Popen([str(folder/'Runtime/VrCommand.exe'),'-batchmode','-nographics','-job-worker-count','2','-logFile',str(log),'--vr-config',str(file)],cwd=runtime,env=env,creationflags=subprocess.CREATE_NO_WINDOW);client={'process':child,'log':log,'player':person,'sessionId':state['id']};clients.append(client);return client
    def room_players(entry,room):
        path='/api/sessions/'+entry['sessionId']
        role='Room'+str(room)
        for seat in range(1,6):
            state=request(path+'/players',{'playerId':str(uuid.uuid4()),'roomId':room,
                'name':f'Portable room {room} seat {seat}','headset':'Quest3'},role=role)
        people=sorted((p for p in state['players'] if p['roomId']==room),key=lambda p:p['seat'])
        names=[f'room-{room:02}-seat-{seat:02}.json' for seat in range(1,6)]
        destination={'address':address,'port':entry['ready']['port']}
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
                file=directory/name
                file.write_bytes(content)
                prepared.append((person,file))
        return [packaged_player(entry,person,file) for person,file in prepared]
    def packaged_player(entry,person,file):
        log=file.with_suffix('.log')
        report=file.with_suffix('.launcher.json')
        child=subprocess.Popen([str(player_folder/'Launch-Player.exe'),'--config',str(file),'--launch',
            '--headless','--wait','--log',str(log),'--report',str(report)],cwd=runtime,env=env)
        client={'process':child,'log':log,'player':person,'sessionId':entry['sessionId'],
            'launcherReport':report,'witness':None}
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
                    check(True,entry['label']+' room controller denied the full Linked evidence ZIP')
                    (out/(entry['label']+'-field-evidence.zip')).write_bytes(raw)
                    session,statistics,endpoint=exported
                ip=ipaddress.IPv4Address(address)
                result=field.verify('same-host',{ip},read(entry['reportPath']),session,statistics,endpoint,server,
                    [(ip,field.content(c['log'])) for c in owners])
                save(entry['label']+'-field-results.json',result)
                check(result['serverAcknowledgements']==len(acks),entry['label']+' field report matches same-PC endpoints and sealed player results')
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
                    if connected==set(expected) and (begin is None or packet['frame']['phase']=='Running' and packet['frame']['tick']>0 and not packet['suspended'] and packet['observedSequence']>=begin and -1<=age<1.5):
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
        config=runtime/(label+'-hardware.json');config.write_text(json.dumps(setup),encoding='utf-8')
        report=out/(label+'-hardware-mock.json')
        gateway=subprocess.Popen([dotnet,str(hardware/'VrCommand.HardwareSimulator.dll'),'--live',str(config),'--output',str(report)],
            env={**mock_env,'VR_COMMAND_ROOM_KEY':keys[f'Room{room}']},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
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

        windows=[]
        for entry in entries:
            owners={c['player']['id']:c['player']['roomId'] for c in clients if c['sessionId']==entry['sessionId']}
            enabled=attack(entry,True)
            windows.append((entry,owners,enabled))
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
            disabled=attack(entry,False)
            def stopped():
                value=observe(entry,owners,disabled,record=False)
                return value if value and not value['packet']['frame']['autoAttack'] else None
            quiet=wait(stopped,12,entry['label']+' original source disables attack')
            entry['combatWindow']={'owners':owners,'enabledSequence':enabled,'disabledSequence':disabled,
                'allDamaged':live,'disabled':quiet}
            save(entry['label']+'-combat-window.json',entry['combatWindow'])
            check(True,entry['label']+' live damage to every original player and observed attack disabled')
            if entry_feeds:entry['hardwareFeedback']=entry_feeds
    def finish(entry):
        entry['process'].wait(timeout=80);w=entry['witness'];w.wait();w.close();entry['witness']=None
        report=read(entry['reportPath']);check(entry['process'].returncode==0 and report['complete'] and report['cleanupCompleted'] and report['childExited'] and report['playerResultsAcknowledged'] is None,entry['label']+' dual seal / retained36 / original process terminal')
        check(report['udpBinding'] == entry['ready']['udpBinding'], entry['label'] + ' terminal report preserves the startup UDP observation')
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
                check(len({s['eventId'] for s in feed['signals']})==len(feed['signals']),entry['label']+f' room {room} live hardware signals match original accepted damage and stop at End')
                if 'mock' in feed:
                    owned=feed.pop('mock'); log,_=owned['gateway'].communicate(timeout=12)
                    assert owned['gateway'].returncode==0 and not any(key in log for key in keys.values())
                    result=read(owned['report'])
                    assert result['complete'] and result['termination']=='ended' and result['physicalDeliveryConfirmed'] is False
                    assert (result['roomId'],result['sessionId'])==(room,sid)
                    acknowledged=[item for attempt in result['attempts'] if attempt['status']=='simulated-acknowledged' for item in attempt['deliveries']]
                    check(len(acknowledged)==result['acknowledged'] and {item['signal']['playerId'] for item in acknowledged}==set(feed['players']),
                          entry['label']+f' room {room} mock confirmed all original admissions')
                    for item in acknowledged:
                        signal=item['signal'];player=signal['playerId'];original=events[signal['eventId']]
                        assert (signal['admissionId'],signal['seat'])==feed['players'][player] and item['deviceId']==owned['devices'][player]
                        assert original['sequence']==signal['eventSequence'] and original['payload']['streamId']==feed['stream']
                        assert original['payload']['report']['reportId']==signal['reportId'] and original['payload']['report']['damage']==signal['damage']
                    owned['mock'].terminate();owned['mock'].wait(timeout=5);owned['reader'].join(timeout=5)
                    check(not owned['reader'].is_alive(),entry['label']+f' room {room} mock and original gateway are terminal')
            save(entry['label']+'-hardware-feedback.json',entry['hardwareFeedback'])
        rounds.append({'name':entry['label'],'ready':entry['ready'],'report':report,'journal':closed,'replayFrames':len(frames)})
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
    def verify_room_readiness(round_clients,linked):
        expected={client['player']['roomId']:client['sessionId'] for client in round_clients}
        def all_ready():
            summary=request('/api/rooms/readiness')
            rows=summary['rooms']
            if summary['version']!=1 or len(rows)!=5 or {row['roomId']:row['sessionId'] for row in rows}!=expected:
                return None
            return summary if all(row['sourceState']=='Fresh' and row['registered']==5 and
                row['simulatedReady']==5 and row['trackedReady']==0 for row in rows) else None
        save(('linked' if linked else 'independent')+'-room-readiness.json',wait(all_ready,20,'five fresh room aggregates'))
        check(True,('Linked' if linked else 'Independent')+' has five real 5/5 synthetic room counts')
        room=request('/api/rooms/readiness',role='Room1')
        check(room['version']==1 and len(room['rooms'])==1 and room['rooms'][0]['roomId']==1
            and room['rooms'][0]['sessionId']==expected[1],'room operator only receives its own active room aggregate')
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
        for linked in [False,True]:
            entries=[];round_clients=[]
            batch=None
            if args.prepare_independent_set and not linked:
                mission=save_mission('five independently prepared rooms',enemy_count=5 if args.check_room_combat else 1)
                body={'missionId':mission['id']}; key=str(uuid.uuid4()); route='/api/sessions/independent-set'
                prepared=request(route,body,expected=201,request_id=key)
                batch=prepared['sessions']
                sessions.extend(state['id'] for state in batch)
                retry=request(route,body,request_id=key)
                check(not prepared['duplicate'] and retry['duplicate'] and retry['sessions']==batch
                      and [state['roomIds'] for state in batch]==[[room] for room in range(1,6)]
                      and all(state['mission']['id']==mission['id'] and state['mode']=='Independent' and state['state']=='Preparing' for state in batch),
                      'one real management request prepares all five native independent sessions and its retry returns the same IDs')
                save('independent-preparation-receipt.json',prepared)
            for rooms in ([[1,2,3,4,5]] if linked else [[r] for r in range(1,6)]):
                enemy_count=5*len(rooms) if args.check_room_combat else 1
                state=batch[rooms[0]-1] if batch is not None else create(rooms,'linked' if linked else 'independent',enemy_count=enemy_count)
                entry=launch(state,('linked' if linked else 'room-'+str(rooms[0])));entries.append(entry)
                entry['combatEnemyCount']=enemy_count
                if not linked and rooms==[1]:rejected('bound-preparing',config(state['id']))
                for room in rooms:
                    round_clients.extend(room_players(entry,room) if player_folder else [player(entry,room)])
            for entry in entries:
                ids=[c['player']['id'] for c in round_clients if c['sessionId']==entry['sessionId']];wait(lambda:observe(entry,ids),60,entry['label']+' simulated bodies');begin=command(entry['sessionId'],'Begin');wait(lambda:observe(entry,ids,begin['session']['sequence']),20,entry['label']+' original Begin applied')
            if args.observe_closure_ui and not linked:
                observer_entry=entries[0];descriptor=runtime/'closure-ui-private.json';descriptor.write_text(json.dumps({'base':uri,'masterKey':keys['Master'],'sessionId':observer_entry['sessionId'],'streamId':observer_entry['ready']['streamId'],'endRequestFile':str(out/'closure-end.request'),'roomReadiness':args.check_room_readiness}),encoding='utf-8');observer_log=(runtime/'closure-ui.log').open('xb')
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
            if args.check_room_readiness:verify_room_readiness(round_clients,linked)
            if args.check_room_combat:
                stage('running-native-ai-combat',mode='Linked' if linked else 'Independent')
                exercise_room_combat(entries,round_clients)
            for entry in entries:
                if args.observe_closure_ui and not linked and entry is observer_entry:(out/'closure-end.request').write_text('request one normal UI End',encoding='utf-8')
                else:command(entry['sessionId'],'End')
            for entry in entries:finish(entry)
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
                for entry in entries:verify_delivery(entry,[c for c in round_clients if c['sessionId']==entry['sessionId']])
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
        save('evidence.json',{'rounds':rounds,'scope':(
            'Three portable packages, five Independent rooms then Linked, 25 simultaneous same-PC Simulation clients per topology.'
            if player_folder else 'Two portable packages, five Independent rooms then Linked, five same-PC Simulation clients per topology.'),
            'managedMrPreparing':args.check_managed_mr,
            'roomCombat':args.check_room_combat,
            'hardwareFeedback':args.check_hardware_feedback,
            'hardwareMockPackage':hardware_manifest['toolVersion'] if args.hardware_simulator_package else None,
            'preparedIndependentSet':args.prepare_independent_set,
            'sourceFingerprint':manifest['build']['sourceFingerprint'],'gameAddress':address})
    except BaseException as error:stage('failed',errorType=type(error).__name__);raise
    finally:
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
        save('cleanup.json',remaining)
        if cleanup:raise RuntimeError('Cleanup not confirmed; do not snapshot live runtime')
        venue.snapshot_runtime(runtime,out/'runtime-snapshot')
    for file in out.glob('*.json'):
        text=file.read_text(encoding='utf-8')
        if keys and any(k in text for k in keys.values()):raise RuntimeError('Public metadata contains a key')
    save('checks.json',{'complete':True,'checks':len(checks),'findings':checks,'runtimeDirectory':str(runtime),
        'packageDirectory':str(folder),'playerPackageDirectory':str(player_folder) if player_folder else None,
        'scope':('Same-machine VR simulation and a separate MR Preparing admission and seal check.'
                 if args.check_managed_mr else 'Same-machine Simulation only.')
                +' The separate parent-death case intentionally leaves the world unsealed.'})
    print(json.dumps({'complete':True,'checks':len(checks),'directory':str(out)}))
if __name__=='__main__':main()
