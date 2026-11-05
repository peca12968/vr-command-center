"""Run five independent PC rooms, or verify their isolation and a later Linked round.

All native players use Simulation rigs. Every process, credential and database is
owned by this isolated fixture; the existing preview service is never touched.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    deadline=time.monotonic()+2
    while True:
        try:return json.loads(path.read_text(encoding='utf-8'))
        except OSError as error:
            sharing=getattr(error,'winerror',None) in (32,33) or os.name=='nt' and isinstance(error,PermissionError)
            if not sharing or time.monotonic()>=deadline:raise
            time.sleep(.01)


def atomic_json(path, value):
    """Observation / config files only; journal durability is unchanged."""
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temporary.open('x',encoding='utf-8') as output:output.write(json.dumps(value,indent=2)+'\n')
        deadline=time.monotonic()+2
        while True:
            try:os.replace(temporary,path);return
            except OSError as error:
                sharing=getattr(error,'winerror',None) in (32,33) or os.name=='nt' and isinstance(error,PermissionError)
                if not sharing or time.monotonic()>=deadline:raise
                time.sleep(.01)
    finally:
        if temporary.exists():temporary.unlink()


def snapshot_runtime(source,destination):
    source=source.resolve();destination=destination.resolve()
    if source==destination or destination.is_relative_to(source) or source.is_relative_to(destination):raise ValueError('Snapshot directories must be separate')
    if destination.exists():raise FileExistsError('Preserve the existing snapshot; never overwrite or retry into it')
    deadline=time.monotonic()+5
    while True:
        readers=ExitStack()
        try:
            # All tracked writers have already exited. On Windows keep shared
            # read handles while copying: a FileShare.None writer cannot reopen.
            for name in ('missions/.library-writer.lock','sessions/.writer.lock'):
                path=source/name
                if path.exists():readers.enter_context(path.open('rb'))
            break
        except OSError as error:
            readers.close()
            sharing=getattr(error,'winerror',None) in (32,33) or os.name=='nt' and isinstance(error,PermissionError)
            if not sharing or time.monotonic()>=deadline:raise
            time.sleep(.05)
    with readers:shutil.copytree(source,destination)


def verify_player(args):
    if os.name != 'nt' or not args.player_exe.is_file() or not args.api_dll.is_file():
        raise RuntimeError('Build the Windows player and API first')
    spec = importlib.util.spec_from_file_location('native_admission', ROOT / 'scripts/check-unity-admission.py')
    checker = importlib.util.module_from_spec(spec); spec.loader.exec_module(checker)
    receipt = json.loads((args.player_exe.parent / 'build-receipt.json').read_text())
    if receipt.get('schemaVersion') != 1 or receipt.get('target') != 'StandaloneWindows64' or receipt.get('sourceFingerprint') != checker.source_fingerprint():
        raise RuntimeError('Windows player receipt does not match current sources; build Desktop first')
    subprocess.run([sys.executable, str(ROOT / 'scripts/check-transport-patch.py')], check=True)


def player_result_phase(text):
    connected = text.rfind('VR_CLIENT_CONNECTED id=')
    if connected < 0: return 'notConnected'
    final = text.rfind('VR_CLIENT_DEBRIEF_FINAL ')
    left = text.rfind('VR_CLIENT_DISCONNECTED')
    if final > connected: return 'acknowledged' if left > final else 'received'
    if left > connected: return 'disconnected'
    return 'pending' if text.rfind('VR_CLIENT_DEBRIEF_PENDING ') > connected else 'connected'


class Venue:
    def __init__(self, args, *, artifact_family='desktop-venue'):
        if artifact_family not in ('desktop-venue', 'desktop-demo', 'desktop-capacity', 'desktop-active', 'desktop-debrief', 'desktop-end-race', 'desktop-clock', 'desktop-clock-faults', 'desktop-long', 'desktop-seal-faults', 'desktop-briefing', 'desktop-readiness', 'desktop-first-person', 'desktop-navigation', 'desktop-ai-targeting', 'desktop-crouch', 'desktop-exercise', 'desktop-walkway'):
            raise ValueError('Unknown native fixture artifact family')
        self.args = args
        self.artifact_family = artifact_family
        self.directory = ROOT / 'artifacts' / artifact_family / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
        self.directory.mkdir(parents=True)
        runtime_root = getattr(args, 'runtime_root', None)
        self.runtime_directory = self.directory if runtime_root is None else runtime_root.resolve() / self.directory.name
        if self.runtime_directory != self.directory: self.runtime_directory.mkdir(parents=True, exist_ok=False)
        self.tokens = {role: secrets.token_hex(32) for role in ['Master', 'GameServer', *['Room' + str(i) for i in range(1, 6)]]}
        self.save('keys.json', {'OperatorKeys': self.tokens})
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0)); self.base = 'http://127.0.0.1:' + str(probe.getsockname()[1])
        self.ports, self.processes, self.rounds, self.evidence = set(), {}, [], []
        self.api_log = None
        self.receipt = json.loads((args.player_exe.parent / 'build-receipt.json').read_text())

    def save(self, name, value):
        path=self.directory/name
        if path.parent.resolve()!=self.directory.resolve():raise ValueError('Artifact name must stay in this run directory')
        atomic_json(path,value)

    def stage(self, stage, **extra):
        self.save('stage.json', {'stage': stage, **extra})
        (ROOT / 'artifacts' / ('latest-' + self.artifact_family + '-path.txt')).write_text(str(self.directory), encoding='utf-8')
        print(json.dumps({'stage': stage, 'directory': str(self.directory), **extra}), flush=True)

    def request(self, route, body=None, *, role='Master', expected=200, admission=None, optional=False, method=None, request_id=None):
        headers = {'Authorization': 'Bearer ' + self.tokens[role], 'Content-Type': 'application/json'}
        if admission: headers['If-Match-Admission'] = admission
        if request_id: headers['Idempotency-Key'] = request_id
        message = urllib.request.Request(self.base + route, data=None if body is None else json.dumps(body).encode(), headers=headers, method=method)
        try:
            with urllib.request.urlopen(message, timeout=5) as response:
                status, raw = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, raw = error.code, error.read()
        if optional and status == 404: return None
        if status != expected: raise RuntimeError(f'{route}: expected {expected}, got {status}')
        return json.loads(raw) if raw else None

    def wait(self, predicate, seconds, label, *, required=None):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            failed = [name for name, process in self.processes.items() if process.poll() is not None and (required is None or name in required)]
            if failed: raise RuntimeError('Unexpected child exit during ' + label + ': ' + ', '.join(failed))
            try:
                value = predicate()
                if value: return value
            except (OSError, urllib.error.URLError): pass
            time.sleep(.15)
        raise RuntimeError('Timed out: ' + label)

    def start(self):
        environment = {k: v for k, v in os.environ.items() if not k.lower().startswith('operatorkeys__') and k.lower() not in ['operatorkeyfile', 'playerticketsigningkey']}
        environment.update(DataDirectory=str(self.runtime_directory / 'missions'), SessionDataDirectory=str(self.runtime_directory / 'sessions'),
                           OperatorKeyFile=str(self.directory / 'keys.json'), Logging__LogLevel__Default='Warning')
        self.api_log = (self.directory / 'api.log').open('wb')
        self.processes['api'] = subprocess.Popen(['dotnet', str(self.args.api_dll.resolve()), '--urls', self.base], cwd=ROOT,
            env=environment, stdout=self.api_log, stderr=self.api_log, creationflags=subprocess.CREATE_NO_WINDOW)
        self.wait(lambda: self.request('/health'), 30, 'API startup')
        if self.request('/').get('version') != '0.31.0': raise RuntimeError('Build API 0.31.0 before provisioning the report-capable venue')

    def launch(self, name, config, visible=False, *, extra_args=()):
        self.save(name + '.json', config)
        flags = ['-screen-fullscreen', '0', '-screen-width', '1100', '-screen-height', '760'] if visible else ['-batchmode', '-nographics']
        self.processes[name] = subprocess.Popen([str(self.args.player_exe.resolve()), *flags, '-job-worker-count', str(self.args.job_workers), '-logFile', str(self.directory / (name + '.log')),
            '--vr-config', str(self.directory / (name + '.json')), *extra_args], cwd=self.args.player_exe.resolve().parent, creationflags=subprocess.CREATE_NO_WINDOW)

    def stop(self, name):
        process = self.processes[name]
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        del self.processes[name]

    def mission(self, room):
        weather, night = [('Clear', False), ('Fog', False), ('Rain', True), ('Storm', True), ('Clear', True)][room - 1]
        definition = {'name': f'Room {room} PC venue - Simulation', 'briefing': 'Independent native desktop room, synthetic rigs; no headset',
            'durationSeconds': self.args.duration, 'environment': {'mode': 'VR', 'weather': weather, 'timeOfDay': 'Night' if night else 'Day', 'lightning': weather == 'Storm'},
            'enemies': {'count': room, 'behavior': 'Hold', 'autoAttack': False},
            'props': [{'assetId': 'barrel' if index % 2 else 'sandbag', 'position': {'x': (index - (room - 1) / 2) * 2, 'y': 0, 'z': 3}, 'yawDegrees': room * 15} for index in range(room)]}
        return self.request('/api/missions', definition, expected=201)

    def create(self, mission, rooms, name, role='Master', players=None):
        state = self.request('/api/sessions', {'missionId': mission['id'], 'mode': 'Linked' if len(rooms) == 5 else 'Independent', 'roomIds': rooms}, role=role, expected=201)
        entry = {'name': name, 'id': state['id'], 'roomIds': rooms, 'mission': mission, 'players': [], 'endId': str(uuid.uuid4()), 'sealed': None, 'sourceAges': []}
        self.rounds.append(entry)  # Track immediately so partial setup is always cleaned up.
        for room in rooms:
            player = players[room] if players else str(uuid.uuid4())
            state = self.request(f'/api/sessions/{entry["id"]}/players', {'playerId': player, 'roomId': room, 'name': f'PC room {room}', 'headset': 'Quest3'}, role='Room' + str(room))
            entry['players'].append(next(p for p in state['players'] if p['id'] == player))
        self.start_server(entry)
        return entry

    def adopt(self, state, name):
        # Only this fixture's fresh preparing worlds. Never claim a running source
        # or restart an already bound combat journal as if it were a new world.
        if state['state'] != 'Preparing' or state['combatStream'] is not None or state['environment']['mode'] != 'VR':
            raise RuntimeError('The local PC operator helper requires a fresh Preparing VR session with no bound source')
        entry = {'name': name, 'id': state['id'], 'roomIds': state['roomIds'], 'mission': state['mission'],
                 'players': [], 'endId': str(uuid.uuid4()), 'sealed': None, 'sourceAges': []}
        self.rounds.append(entry)
        self.start_server(entry)
        return entry

    def start_server(self, entry):
        name = entry['name']
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
            if port not in self.ports: break
        self.ports.add(port); entry['port'] = port
        self.launch(name + '-server', {'role': 'Server', 'address': getattr(self.args, 'advertise_address', None) or '127.0.0.1',
            'listenAddress': getattr(self.args, 'listen_address', None) or '127.0.0.1', 'port': port, 'sessionId': entry['id'], 'managementApiUrl': self.base,
            'gameServerKey': self.tokens['GameServer'], 'telemetryOrigin': 'Simulation', 'telemetryDirectory': str(self.runtime_directory / (name + '-telemetry'))})

    def ticket(self, entry, player):
        invitation = self.request(f'/api/sessions/{entry["id"]}/players/{player["id"]}/join-ticket', {}, admission=player['admissionId'], role='Room' + str(player['roomId']))
        player['ticketExpiresAtUtc'] = invitation['expiresAtUtc']
        return invitation['ticket']

    def clients(self, entries):
        for entry in entries:
            self.wait(lambda e=entry: self.request(f'/api/sessions/{e["id"]}/world', optional=True), 90, entry['name'] + ' recording')
        # Open the selected visible player last; other rooms keep their own native clients.
        pairs = [(entry, player) for entry in entries for player in entry['players']]
        pairs.sort(key=lambda pair: pair[1]['roomId'] == self.args.visible_room)
        for entry, player in pairs:
            ticket = self.ticket(entry, player)
            player['ticket'] = ticket  # Private fixture state only; never included in public summaries.
            self.launch(entry['name'] + '-client-' + str(player['roomId']), self.client_config(entry, ticket), player['roomId'] == self.args.visible_room)
        for entry in entries:
            self.wait(lambda e=entry: self.connected(e), 100, entry['name'] + ' accepted rigs')

    @staticmethod
    def client_config(entry, ticket): return {'role': 'Client', 'address': '127.0.0.1', 'port': entry['port'], 'joinTicket': ticket}

    def frame(self, entry, measure=False):
        metadata = self.request(f'/api/sessions/{entry["id"]}/world') if measure else None
        message = urllib.request.Request(self.base + f'/api/sessions/{entry["id"]}/world/watch?mode=live', headers={'Authorization': 'Bearer ' + self.tokens['Master']})
        with urllib.request.urlopen(message, timeout=5) as response:
            kind = ''
            for _ in range(60):
                line = response.readline().decode().strip()
                if line.startswith('event: '): kind = line[7:]
                if kind == 'frame' and line.startswith('data: '):
                    value = json.loads(line[6:])
                    if measure:
                        if not metadata['capturedAtUtc']: raise RuntimeError('Native source capture UTC is missing')
                        age = (datetime.now(timezone.utc) - datetime.fromisoformat(metadata['capturedAtUtc'])).total_seconds()
                        entry['sourceAges'].append(age)
                        if not -1 <= age < 1.5:
                            self.save('freshness-failure.json', {'round': entry['name'], 'metadata': metadata, 'receivedFrame': value, 'sourceAgeSeconds': age})
                            raise RuntimeError(f'{entry["name"]} source age {age}s exceeds the original 1.5s limit')
                    self.save(entry['name'] + '-latest-frame.json', value)
                    return value
        raise RuntimeError('No live frame for ' + entry['name'])

    def connected(self, entry):
        value = self.frame(entry); players = value['packet']['frame']['players']
        expected = {p['id'] for p in entry['players']}
        return value if {p['id'] for p in players if p['connected'] and p['rig']['kind'] == 'Simulated'} == expected else None

    def command(self, entry, action, role=None, expected=200, **extra):
        if role is None: role = 'Master' if len(entry['roomIds']) == 5 else 'Room' + str(entry['roomIds'][0])
        return self.request(f'/api/sessions/{entry["id"]}/commands', {'commandId': entry['endId'] if action == 'End' else str(uuid.uuid4()), 'action': action, **extra}, role=role, expected=expected)

    def state(self, entry): return self.request('/api/sessions/' + entry['id'])

    def seal(self, entry):
        if entry['sealed']: return entry['sealed']
        if self.state(entry)['state'] != 'Ended': self.command(entry, 'End')
        world = self.wait(lambda: (world if (world := self.request(f'/api/sessions/{entry["id"]}/world', optional=True)) and world['complete'] else None), 30, entry['name'] + ' exact seals', required={'api', entry['name'] + '-server'})
        statistics = self.request(f'/api/sessions/{entry["id"]}/statistics'); final = self.frame(entry)
        if statistics['pendingTelemetry'] or final['packet']['frame']['phase'] != 'Ended': raise RuntimeError('Incomplete final telemetry')
        if world['header']['origin'] != 'Simulation' or world['header']['roomIds'] != entry['roomIds']: raise RuntimeError('World source / room isolation failed')
        if statistics['origin'] not in (None, 'Simulation'): raise RuntimeError('Mixed combat sources')
        if statistics['origin'] is None and any(p[field] for p in statistics['players'] for field in ['ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken']):
            raise RuntimeError('Nonempty combat statistics must identify their source')
        if sorted(final['statistics'], key=lambda p: p['playerId']) != sorted(statistics['players'], key=lambda p: p['playerId']): raise RuntimeError('Replay / ledger statistics disagree')
        expected_players = {p['id'] for p in entry['players']}
        if entry.get('dynamicRoster'):
            expected_players, cursor = set(), 0
            while True:
                events = self.request(f'/api/sessions/{entry["id"]}/events?after={cursor}&limit=500')
                if not events: break
                for event in events:
                    if event['kind'] == 'PlayerJoined': expected_players.add(event['payload']['id'])
                if events[-1]['sequence'] <= cursor: raise RuntimeError('Management event history did not advance')
                cursor = events[-1]['sequence']
        if {p['playerId'] for p in statistics['players']} != expected_players: raise RuntimeError('Foreign or missing player statistics')
        entry['sealed'] = {'name': entry['name'], 'world': world, 'statistics': statistics, 'replayStatisticsMatch': True,
                           'maximumSourceAgeSeconds': max(entry['sourceAges'], default=None)}
        self.save(entry['name'] + '-sealed.json', entry['sealed'])
        return entry['sealed']

    def stop_round(self, entry):
        for name in list(self.processes):
            if name.startswith(entry['name'] + '-'): self.stop(name)

    def wait_for_player_results(self, entry):
        if not entry['sealed']: raise RuntimeError('Seal the world before waiting for player results')
        if 'playerResults' in entry: return entry['playerResults']
        names = [n for n in self.processes if n.startswith(entry['name'] + '-')]
        deadline = time.monotonic() + 36
        while True:
            phases = {}
            for name in names:
                child = self.processes.get(name)
                path = self.directory / (name + '.log')
                phase = player_result_phase(path.read_text(encoding='utf-8', errors='replace')) if path.exists() else 'notConnected'
                if phase == 'notConnected': continue  # dedicated server or rejected / never connected client
                phases[name] = 'closed' if child is None or child.poll() is not None else phase
            if not any(p in ('connected', 'pending', 'received') for p in phases.values()) or time.monotonic() >= deadline: break
            time.sleep(.1)
        result = {'phases': phases, 'allAcknowledged': bool(phases) and all(p == 'acknowledged' for p in phases.values()),
                  'timedOut': [n for n, p in phases.items() if p in ('connected', 'pending', 'received')]}
        self.save(entry['name'] + '-player-results.json', result)
        entry['playerResults'] = result  # Retention expiry must not replace a receipt with a later empty set.
        return result

    def inspect_player_results(self, entry, visible_name, seconds):
        deadline = time.monotonic() + seconds
        if not visible_name or visible_name not in self.processes: return
        self.stage('player_results', sessionId=entry['id'], seconds=seconds)
        while time.monotonic() < deadline and self.processes[visible_name].poll() is None:
            if (self.directory / 'dismiss-results.request').exists(): break
            time.sleep(.1)

    def summary(self):
        if self.request('/api/sessions'): raise RuntimeError('Venue still has active sessions')
        self.save('summary.json', {'source': 'Actual Windows Unity UDP / NGO processes; Simulation source',
            'headsets': None if getattr(self.args, 'client_mode', 'local') == 'external' else 0,
            'completedAtUtc': datetime.now(timezone.utc).isoformat(), 'playerBuildReceipt': self.receipt, 'jobWorkersPerProcess': self.args.job_workers,
            'runtimeDirectory': str(self.runtime_directory), 'checks': self.evidence,
            'rounds': [entry['sealed'] for entry in self.rounds], 'activeSessions': 0})
        self.stage('passed' if self.args.check else 'sealed', rounds=len(self.rounds), checks=len(self.evidence))

    def cleanup(self):
        # End all live fixture rounds, then attempt durable seals before stopping native servers.
        # Each cleanup attempt is independent; one rejected command cannot leak other children.
        errors = []
        try:
            for entry in self.rounds:
                try:
                    if self.state(entry)['state'] != 'Ended': self.command(entry, 'End')
                except Exception as error: errors.append({'round': entry['name'], 'operation': 'End', 'errorType': type(error).__name__})
            for entry in self.rounds:
                if not entry['sealed']:
                    try:
                        if self.request(f'/api/sessions/{entry["id"]}/world', optional=True): self.seal(entry)
                    except Exception as error: errors.append({'round': entry['name'], 'operation': 'seal', 'errorType': type(error).__name__})
        finally:
            for name in reversed(list(self.processes)):
                try: self.stop(name)
                except Exception as error: errors.append({'process': name, 'operation': 'stop', 'errorType': type(error).__name__})
            if self.api_log: self.api_log.close()
            # Copy only after all fixture writers have stopped. Keep original journals;
            # never move or delete an existing runtime or preview directory.
            if self.runtime_directory != self.directory and not self.processes:
                try: snapshot_runtime(self.runtime_directory, self.directory / 'runtime-snapshot')
                except Exception as error: errors.append({'operation': 'runtime snapshot', 'errorType': type(error).__name__,'detail':str(error)[:4096]})
            self.save('cleanup.json', {'errors': errors, 'remainingTrackedChildren': list(self.processes)})
        return not errors and not self.processes


def check_venue(venue, rooms):
    def record(message): venue.evidence.append(message); venue.stage('checking', check=message)
    assert len(venue.request('/api/sessions')) == 5
    for entry in rooms:
        room = entry['roomIds'][0]; role = 'Room' + str(room)
        assert [s['id'] for s in venue.request('/api/sessions', role=role)] == [entry['id']]
        wrong = rooms[room % 5]
        for suffix in ['', '/statistics', '/world', '/world/watch?mode=live']:
            venue.request('/api/sessions/' + wrong['id'] + suffix, role=role, expected=403)
        venue.command(wrong, 'Pause', role=role, expected=403)
        frame = venue.frame(entry, measure=True)['packet']; header = venue.request('/api/sessions/' + entry['id'] + '/world')['header']
        assert header['roomIds'] == [room] and len(header['props']) == room
        assert all(prop['roomId'] == room for prop in header['props'])
        for prop, definition in zip(header['props'], entry['mission']['definition']['props']):
            assert prop['feet'] == {'x': (room - 3) * 14 + definition['position']['x'], 'y': 0, 'z': definition['position']['z']}
            assert prop['yaw'] == definition['yawDegrees']
        assert len(frame['frame']['enemies']) == room and all(e['roomId'] == room for e in frame['frame']['enemies'])
        assert frame['weather'] == entry['mission']['definition']['environment']['weather']
        assert frame['frame']['night'] == (entry['mission']['definition']['environment']['timeOfDay'] == 'Night')
    record('Five simultaneous native rooms have distinct missions, geometry, enemies and authorized room scopes')
    venue.launch('wrong-room-probe', venue.client_config(rooms[1], rooms[0]['players'][0]['ticket']))
    log = venue.directory / 'wrong-room-probe.log'
    venue.wait(lambda: log.exists() and 'VR_CLIENT_ADMISSION_REJECTED' in log.read_text(errors='replace'), 30, 'wrong-room native ticket rejection')
    venue.stop('wrong-room-probe')
    for entry in rooms: assert venue.connected(entry)
    record('Valid room-1 ticket rejected by room-2 native server; current bindings survive')
    for entry in rooms: venue.command(entry, 'Begin')
    for entry in rooms: venue.wait(lambda e=entry: (value if (value := venue.frame(e, measure=True))['packet']['frame']['tick'] >= 20 else None), 30, 'all native rooms running')
    baseline = [venue.frame(entry, measure=True) for entry in rooms]
    others = [venue.state(entry) for entry in rooms[1:]]
    venue.command(rooms[0], 'SetEnvironment', environment={'mode': 'VR', 'weather': 'Storm', 'timeOfDay': 'Night', 'lightning': True})
    venue.command(rooms[0], 'SetEnemies', enemies={'count': 6, 'behavior': 'Advance', 'autoAttack': True})
    venue.wait(lambda: venue.request('/api/sessions/' + rooms[0]['id'] + '/statistics')['players'][0]['hitsReceived'] > 0, 30, 'room-1 confirmed AI damage')
    venue.command(rooms[0], 'Pause')
    paused = venue.wait(lambda: (value if (value := venue.frame(rooms[0], measure=True))['packet']['frame']['phase'] == 'Paused' else None), 15, 'only room 1 paused')
    assert paused['packet']['weather'] == 'Storm' and paused['packet']['lightning'] and paused['packet']['frame']['night']
    assert len(paused['packet']['frame']['enemies']) == 6 and paused['packet']['frame']['behavior'] == 'Advance' and paused['packet']['frame']['autoAttack']
    for index, entry in enumerate(rooms[1:], 1):
        advanced = venue.wait(lambda e=entry, i=index: (value if (value := venue.frame(e, measure=True))['packet']['frame']['tick'] >= baseline[i]['packet']['frame']['tick'] + 20 else None), 15, 'other room continues')
        state = venue.state(entry)
        assert state['state'] == 'Running' and state['environment'] == others[index-1]['environment'] and state['enemies'] == others[index-1]['enemies']
        assert advanced['packet']['weather'] == baseline[index]['packet']['weather']
        assert all(p['health'] == 100 for p in advanced['packet']['frame']['players'])
    assert venue.frame(rooms[0], measure=True)['packet']['frame']['tick'] == paused['packet']['frame']['tick']
    record('Room-1 environment / AI changes and Pause leave four other native worlds running unchanged')
    first = venue.seal(rooms[0]); venue.stop_round(rooms[0])
    assert len(venue.request('/api/sessions')) == 4
    occupied = venue.request('/api/rooms')
    assert next(r for r in occupied if r['id'] == 1)['sessionId'] is None
    assert all(next(r for r in occupied if r['id'] == n)['sessionId'] == rooms[n-1]['id'] for n in range(2, 6))
    venue.request('/api/sessions', {'missionId': rooms[0]['mission']['id'], 'mode': 'Linked', 'roomIds': [1,2,3,4,5]}, expected=409)
    replacement = venue.create(rooms[0]['mission'], [1], 'room-1-replacement', role='Room1')
    venue.clients([replacement]); venue.command(replacement, 'Begin')
    venue.wait(lambda: venue.frame(replacement, measure=True)['packet']['frame']['tick'] >= 20, 30, 'reused room 1')
    assert len(venue.request('/api/sessions')) == 5
    assert venue.request('/api/sessions/' + rooms[0]['id'] + '/statistics') == first['statistics']
    for entry in rooms[1:]: assert venue.connected(entry) and venue.state(entry)['state'] == 'Running'
    record('Ended room releases only its seat; reuse preserves old history and four live worlds; premature Linked creation rejected')
    for entry in [*rooms[1:], replacement]: venue.seal(entry); venue.stop_round(entry)
    assert venue.request('/api/sessions') == []
    assert len(venue.request('/api/sessions?includeEnded=true')) == 6
    linked = venue.create(rooms[3]['mission'], [1,2,3,4,5], 'linked', players={e['roomIds'][0]: e['players'][0]['id'] for e in rooms})
    venue.clients([linked])
    venue.command(linked, 'Begin', role='Room1', expected=403)
    venue.command(linked, 'SetEnvironment', role='Room1', expected=403, environment={'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False})
    assert datetime.fromisoformat(rooms[0]['players'][0]['ticketExpiresAtUtc']) > datetime.now(timezone.utc), 'Old-round rejection must be tested before ticket expiry'
    assert all(p['admissionId'] != rooms[p['roomId'] - 1]['players'][0]['admissionId'] for p in linked['players'])
    venue.launch('old-round-probe', venue.client_config(linked, rooms[0]['players'][0]['ticket']))
    log = venue.directory / 'old-round-probe.log'
    venue.wait(lambda: log.exists() and 'VR_CLIENT_ADMISSION_REJECTED' in log.read_text(errors='replace'), 30, 'old independent ticket rejected by Linked server')
    venue.stop('old-round-probe')
    venue.command(linked, 'SetEnemies', enemies={'count': 5, 'behavior': 'Advance', 'autoAttack': True})
    venue.command(linked, 'Begin')
    venue.wait(lambda: venue.frame(linked, measure=True)['packet']['frame']['tick'] >= 40, 30, 'Linked five native players')
    venue.wait(lambda: sum(p['hitsReceived'] for p in venue.request('/api/sessions/' + linked['id'] + '/statistics')['players']) > 0, 30, 'Linked AI damage')
    for room in range(1, 6): assert [s['id'] for s in venue.request('/api/sessions', role='Room' + str(room))] == [linked['id']]
    record('After all independent seals, one Linked world accepts five rooms; old round ticket and room-wide control escalation rejected')
    venue.command(linked, 'Pause')
    paused = venue.wait(lambda: (value if (value := venue.frame(linked, measure=True))['packet']['frame']['phase'] == 'Paused' else None), 15, 'Linked Pause')
    time.sleep(.6)
    assert venue.frame(linked, measure=True)['packet']['frame']['tick'] == paused['packet']['frame']['tick']
    venue.seal(linked)
    assert len(venue.request('/api/sessions?includeEnded=true')) == 7
    streams = [e['sealed']['world']['header']['streamId'] for e in venue.rounds]
    assert len(set(streams)) == 7
    record('Seven rounds retain distinct world streams and exact replay / combat seals; final active count zero')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--player-exe', type=Path, default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER', ROOT / 'artifacts/desktop/VrCommand.exe')))
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    parser.add_argument('--duration', type=int, choices=range(60,1801), default=900, metavar='60..1800')
    parser.add_argument('--visible-room', type=int, choices=range(0,6), default=1, help='One playable PC room; 0 makes all clients headless')
    parser.add_argument('--check', action='store_true', help='Headless native five-room isolation, room reuse and later Linked validation')
    parser.add_argument('--job-workers', type=int, choices=range(1,17), default=2, help='Unity job workers per native process; recorded in evidence')
    parser.add_argument('--runtime-root', type=Path, help='Optional SSD directory for fresh isolated SQLite / journals; closed snapshot is copied back to F artifacts')
    args = parser.parse_args()
    try: verify_player(args)
    except (OSError, RuntimeError, ValueError) as error: parser.error(str(error))
    if args.check: args.visible_room = 0
    venue = Venue(args)
    try:
        venue.stage('starting', source='Simulation', headsets=0, runtimeDirectory=str(venue.runtime_directory))
        venue.start()
        rooms = [venue.create(venue.mission(room), [room], 'room-' + str(room), role='Room' + str(room)) for room in range(1,6)]
        venue.clients(rooms)
        if args.check:
            check_venue(venue, rooms)
        else:
            for entry in rooms: venue.command(entry, 'Begin')
            venue.save('ready.json', {'baseUrl': venue.base, 'consoleUrl': venue.base + '/console/', 'source': 'Simulation', 'headsets': 0,
                'directory': str(venue.directory), 'runtimeDirectory': str(venue.runtime_directory), 'playerBuildReceipt': venue.receipt, 'processIds': {n: p.pid for n,p in venue.processes.items()},
                'rooms': [{'roomId': e['roomIds'][0], 'sessionId': e['id'], 'port': e['port']} for e in rooms]})
            venue.stage('ready', consoleUrl=venue.base + '/console/', visibleRoom=args.visible_room)
            print('Use this directory\'s keys.json for the isolated Master / Room1..5 consoles. No credentials are printed.', flush=True)
            print('Close the visible client, create end.request, press Ctrl+C or wait for duration to end all fixture rooms.', flush=True)
            deadline = time.monotonic() + args.duration
            try:
                while time.monotonic() < deadline and not (venue.directory / 'end.request').exists():
                    visible = 'room-' + str(args.visible_room) + '-client-' + str(args.visible_room)
                    if args.visible_room and venue.processes[visible].poll() is not None:
                        venue.stop(visible)
                        break
                    for entry in rooms: venue.frame(entry)
                    if not venue.request('/api/sessions'): break
                    time.sleep(.3)
            except KeyboardInterrupt: pass
            for entry in rooms: venue.seal(entry)
        venue.summary()
    except BaseException as error:
        venue.stage('failed', errorType=type(error).__name__)
        raise
    finally:
        cleaned = venue.cleanup()
        if not cleaned and sys.exc_info()[0] is None:
            venue.stage('failed', errorType='CleanupError')
            raise RuntimeError('Venue cleanup / snapshot failed; inspect cleanup.json')


if __name__ == '__main__': main()
