"""Restart only a fixture-owned management API while packaged games stay connected."""
import argparse
from contextlib import ExitStack
import csv
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def free_ports(count, kind):
    with ExitStack() as sockets:
        probes = [sockets.enter_context(socket.socket(socket.AF_INET, kind)) for _ in range(count)]
        for probe in probes:
            probe.bind(('127.0.0.1', 0))
        return [probe.getsockname()[1] for probe in probes]


def main():
    from windows_firewall import require_silent_windows_launch

    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('control-package', 'server-package', 'runtime-root'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--expect', choices=('legacy-stop', 'recover', 'timeout'), required=True)
    parser.add_argument('--topology', choices=('single', 'independent', 'linked'), default='single',
                        help='Exercise one room, five separate servers, or a shared five-room server')
    parser.add_argument('--players-per-room', type=int, choices=range(1, 6), default=1,
                        help='Connect this many actual Windows clients in each room')
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('Actual packaged Windows processes are required')
    if args.topology != 'single' and args.expect != 'recover':
        parser.error('Five-room topologies require --expect recover')
    if args.topology == 'single' and args.players_per_room != 1:
        parser.error('--players-per-room above one requires a five-room topology')
    rooms = [1] if args.topology == 'single' else list(range(1, 6))
    groups = [rooms] if args.topology == 'linked' else [[room] for room in rooms]

    import importlib.util

    def module(name):
        spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
        value = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(value)
        return value

    controls = module('check-control-package')
    server_package = module('package-windows-server')
    debrief = module('check-desktop-debrief')
    journals = module('analyze-world-journal')
    field = module('verify-field-results')
    control_root, server_root = args.control_package.resolve(), args.server_package.resolve()
    control_manifest = controls.package.verify(control_root)
    server_manifest = server_package.verify(server_root)
    require_silent_windows_launch(control_root / 'Runtime/VrCommand.Api.exe')
    require_silent_windows_launch(server_root / 'Launch-Server.exe')
    require_silent_windows_launch(server_root / 'Runtime/VrCommand.exe')
    require_silent_windows_launch(sys.executable)
    run = 'run-' + uuid.uuid4().hex
    out = ROOT / 'artifacts' / 'packaged-management-restart' / run
    runtime = args.runtime_root.resolve() / run
    out.mkdir(parents=True, exist_ok=False)
    runtime.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PATH=str(Path(os.environ['WINDIR']) / 'System32'), DOTNET_ROOT=str(runtime / 'absent-dotnet'))
    data = runtime / 'control'
    control_exe, server_exe = control_root / 'Start-Control.exe', server_root / 'Launch-Server.exe'
    api_port, = free_ports(1, socket.SOCK_STREAM)
    udp_ports = free_ports(len(groups), socket.SOCK_DGRAM)
    base = f'http://127.0.0.1:{api_port}'
    children, api_runs, checks, entries = {}, [], [], []
    errors = []

    def check(condition, label):
        if not condition:
            raise RuntimeError(label)
        checks.append(label)
        print('PASS:', label, flush=True)

    def save(path, value):
        path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

    def read(path):
        return json.loads(path.read_text(encoding='utf-8'))

    def spawn(name, command):
        child = subprocess.Popen(list(map(str, command)), cwd=runtime, env=env,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        children[name] = child
        return child

    def wait(predicate, seconds, label, *live):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if any(process.poll() is not None for process in live):
                raise RuntimeError('An owned process exited while waiting for ' + label)
            value = predicate()
            if value:
                return value
            time.sleep(.1)
        raise RuntimeError('Timed out waiting for ' + label)

    def start_api(label):
        ready, final, stop = (out / (label + suffix) for suffix in ('-ready.json', '-final.json', '-stop.request'))
        runner = spawn(label, [control_exe, '--run', data, '--seconds', '240', '--ready-report', ready,
                               '--stop-file', stop, '--report', final])
        entry = {'process': runner, 'stop': stop, 'final': final, 'witness': None}
        api_runs.append(entry)
        receipt = wait(lambda: read(ready) if ready.is_file() else None, 35, label + ' readiness', runner)
        entry['receipt'] = receipt
        entry['witness'] = controls.ChildWitness(receipt['childPid'], allow_terminate=True)
        check(receipt['uri'] == base and Path(receipt['runtimeCoreClr']).resolve() == (control_root / 'Runtime/coreclr.dll').resolve(),
              label + ' uses the original address and packaged runtime')
        return entry

    def request(route, body=None, *, role='Master', expected=200, admission=None, request_id=None, raw=False):
        headers = {'Authorization': 'Bearer ' + keys[role], 'Content-Type': 'application/json'}
        if admission:
            headers['If-Match-Admission'] = admission
        if request_id:
            headers['Idempotency-Key'] = request_id
        req = urllib.request.Request(base + route, data=None if body is None else json.dumps(body).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=4) as response:
                status, value = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, value = error.code, error.read()
        if status != expected:
            code = None
            try:
                body_data = json.loads(value)
                code = body_data.get('code') if isinstance(body_data, dict) else None
            except (UnicodeError, ValueError):
                pass
            detail = f' ({code})' if isinstance(code, str) and len(code) <= 64 and code.replace('-', '').isalnum() else ''
            raise RuntimeError(f'{route} returned {status}{detail}, expected {expected}')
        return value if raw else json.loads(value)

    def log(path):
        return path.read_text(encoding='utf-8', errors='replace')

    def replay(route, world, destination):
        req = urllib.request.Request(base + route + '/world/watch?mode=replay&rate=4',
                                     headers={'Authorization': 'Bearer ' + keys['Master']})
        frames = []
        kind, terminal = '', False
        deadline = time.monotonic() + world['durationMilliseconds'] / 4000 + 12
        with urllib.request.urlopen(req, timeout=5) as response:
            for raw in response:
                if time.monotonic() >= deadline:
                    raise RuntimeError('Replay exceeded the expected recording interval')
                line = raw.decode('utf-8').strip()
                if line.startswith('event: '):
                    kind = line[7:]
                elif line.startswith('data: ') and kind == 'frame':
                    frames.append(json.loads(line[6:]))
                elif line.startswith('data: ') and kind == 'complete':
                    terminal = True
        check(terminal and [row['packet']['sequence'] for row in frames] == list(range(1, world['acceptedSequence'] + 1))
              and frames[-1] == request(route + '/world/frames/' + str(world['acceptedSequence'])),
              'Entire recovered replay ends at the original sealed world boundary')
        paused = [row['packet'] for row in frames if row['packet']['suspended']]
        check(paused and {packet['frame']['phase'] for packet in paused} == {'Paused'}
              and len({packet['frame']['tick'] for packet in paused}) == 1
              and any(row['packet']['frame']['phase'] == 'Running' and not row['packet']['suspended']
                      and row['packet']['sequence'] > paused[-1]['sequence'] for row in frames),
              f'{route} records a frozen activity clock and a later Running frame')
        save(destination / 'full-replay.json', frames)
        return {'frames': len(frames), 'suspendedFrames': len(paused), 'suspendedTick': paused[0]['frame']['tick']}

    def start_server(mission_id, room_ids, port):
        name = 'server' if args.topology == 'single' else 'linked' if args.topology == 'linked' else f'room-{room_ids[0]}'
        state = request('/api/sessions', {'missionId': mission_id, 'mode': 'Linked' if args.topology == 'linked' else 'Independent',
                                         'roomIds': room_ids}, expected=201)
        route = '/api/sessions/' + state['id']
        evidence = out if args.topology == 'single' else out / name
        evidence.mkdir(exist_ok=True)
        players = []
        for room in room_ids:
            for seat in range(1, args.players_per_room + 1):
                player_id = str(uuid.uuid4())
                roster = request(route + '/players', {'playerId': player_id, 'roomId': room,
                                 'name': f'Fixture player {room}-{seat}', 'headset': 'Quest3'})
                players.append(next(player for player in roster['players'] if player['id'] == player_id))
        config, work = runtime / (name + '.json'), runtime / name
        save(config, {'role': 'Server', 'managementApiUrl': base, 'gameServerKey': keys['GameServer'],
                      'sessionId': state['id'], 'address': '127.0.0.1', 'listenAddress': '127.0.0.1', 'port': port})
        ready, final = evidence / 'server-ready.json', evidence / 'server-final.json'
        runner = spawn(name, [server_exe, '--run', config, '--work', work, '--seconds', '180', '--ready-report', ready,
                              '--report', final, '--peer-diagnostics', 'on'])
        return {'id': state['id'], 'route': route, 'name': name, 'rooms': room_ids, 'port': port, 'work': work, 'evidence': evidence,
                'players': players, 'runner': runner, 'ready': ready, 'final': final, 'clients': [], 'witness': None}

    def connect_players(entry):
        for player in entry['players']:
            room = player['roomId']
            name = 'player' if args.topology == 'single' else f'player-{room}'
            if args.players_per_room > 1:
                name += f'-{player["seat"] + 1}'
            ticket = request(entry['route'] + f'/players/{player["id"]}/join-ticket', {},
                             role=f'Room{room}', admission=player['admissionId'])['ticket']
            config, path = runtime / (name + '.json'), runtime / (name + '.log')
            save(config, {'role': 'Client', 'address': '127.0.0.1', 'port': entry['port'], 'joinTicket': ticket})
            process = spawn(name, [server_root / 'Runtime/VrCommand.exe', '-batchmode', '-nographics', '-job-worker-count', '2',
                                   '-logFile', path, '--vr-config', config])
            entry['clients'].append({'player': player, 'process': process, 'log': path})

    def phase(action):
        if args.topology == 'single':
            return request(entries[0]['route'] + '/commands', {'commandId': str(uuid.uuid4()), 'action': action})
        route = '/api/venue/phase'
        preview = request(route)[action.lower()]
        owner_ids = {entry['id'] for entry in entries}
        if ({row['sessionId'] for row in preview} != owner_ids
                or sorted(room for row in preview for room in row['roomIds']) != rooms):
            raise RuntimeError(action + ' preview did not cover the original five rooms')
        fields = ('sessionId', 'phaseSinceSequence', 'sessionSequence') if action == 'Begin' else ('sessionId', 'phaseSinceSequence')
        targets = [{field: row[field] for field in fields} for row in preview]
        if action == 'Begin':
            expected = {row['sessionId']: row['sessionSequence'] for row in targets}
            room_owners = {room: entry['id'] for entry in entries for room in entry['rooms']}

            def ready_rooms():
                rows = request('/api/rooms/readiness')['rooms']
                if (sorted(row['roomId'] for row in rows) == rooms
                        and all(row['venueBeginReady'] and row['registered'] == args.players_per_room
                                and row['sessionId'] == room_owners[row['roomId']]
                                and row['sessionSequence'] == expected.get(row['sessionId']) for row in rows)):
                    return rows
                return None

            save(out / 'begin-readiness.json', wait(ready_rooms, 60, 'five original Preparing room readiness aggregates'))
        key = str(uuid.uuid4())
        receipt = request(route, {'action': action, 'targets': targets}, request_id=key)
        check(not receipt['duplicate'] and receipt['requestId'] == key and {row['sessionId'] for row in receipt['sessions']} == owner_ids,
              f'One normal venue {action} applies to exactly the original five rooms')
        save(out / (action.lower() + '-receipt.json'), receipt)
        return receipt

    def capture_before(entry):
        session = entry['route']

        def damaged():
            statistics = request(session + '/statistics')
            damaged_ids = {row['playerId'] for row in statistics['players'] if row['damageTaken'] > 0}
            damaged_rooms = {player['roomId'] for player in entry['players'] if player['id'] in damaged_ids}
            return statistics if damaged_rooms == set(entry['rooms']) else None

        statistics = wait(damaged, 25, 'actual combat damage in every original room', entry['runner'])
        original = request(session)
        world = request(session + '/world')
        frame = request(session + '/world/frames/' + str(world['acceptedSequence']))['packet']
        check(original['state'] == 'Running' and original['combatStream']['streamId'] == entry['receipt']['streamId']
              and world['header']['roomIds'] == entry['rooms']
              and {row['id'] for row in frame['frame']['players'] if row['connected']} == {player['id'] for player in entry['players']},
              entry['name'] + ' has accepted combat and the original connected roster in its Running world')
        before = {'session': original, 'world': world, 'statistics': statistics}
        save(entry['evidence'] / 'before-restart.json', before)
        return before, frame

    def resume(entry):
        session, before = entry['route'], entry['before']
        original, before_world = before['session'], before['world']
        after = request(session)
        check(after['id'] == entry['id'] and after['combatStream']['streamId'] == entry['receipt']['streamId']
              and after['players'] == original['players'] and after['state'] == 'Running' and after['sequence'] >= original['sequence'],
              entry['name'] + ' retains its original session, stream and admissions')
        after_world = request(session + '/world')
        if args.expect != 'recover':
            check(not after_world['complete'] and 'VR_CLIENT_DEBRIEF_FINAL ' not in log(entry['clients'][0]['log']),
                  'Interrupted game leaves its saved world without a final player result')
            return after, after_world

        def resumed():
            latest = request(session + '/world')
            if latest['acceptedSequence'] <= before_world['acceptedSequence']:
                return None
            packet = request(session + '/world/frames/' + str(latest['acceptedSequence']))['packet']
            if (packet['frame']['phase'] == 'Running' and not packet['suspended']
                    and packet['frame']['tick'] > entry['before_frame']['frame']['tick']):
                return packet
            return None

        frame = wait(resumed, 15, 'original world advances after management returns', entry['runner'],
                     *(client['process'] for client in entry['clients']))
        check({(row['id'], row['roomId']) for row in frame['frame']['players'] if row['connected']}
              == {(player['id'], player['roomId']) for player in entry['players']},
              entry['name'] + ' advances with the original connected players in their original rooms')
        save(entry['evidence'] / 'first-resumed-frame.json', frame)
        return after, after_world

    def finish(entry):
        name, session, original = entry['name'], entry['route'], entry['receipt']
        runner, evidence = entry['runner'], entry['evidence']
        runner.wait(timeout=75)
        entry['witness'].wait()
        report = read(entry['final'])
        check(runner.returncode == 0 and report['complete'] and report['status'] == 'sealed-stopped'
              and report['childPid'] == original['childPid'] and report['streamId'] == original['streamId'],
              name + ' original game child finishes after both seals and normal retention')
        recovery = report['managementRecovery']
        check(recovery['outages'] == recovery['recoveries'] == 1 and 2500 <= recovery['longestMilliseconds'] < 15000,
              name + ' reports one measured outage and one recovery before its deadline')
        current, statistics, world, endpoint = (request(session + suffix) for suffix in ('', '/statistics', '/world', '/connection-endpoint'))
        raw_zip = request(session + '/field-evidence.zip', raw=True)
        with zipfile.ZipFile(io.BytesIO(raw_zip)) as bundle:
            exported = [field.read_json(bundle.read(member)) for member in ('session.json', 'statistics.json', 'endpoint.json')]
        check(exported == [current, statistics, endpoint] and report['finalWorld'] == world,
              name + ' management ZIP matches the terminal API and launcher seals')
        (evidence / 'field-evidence.zip').write_bytes(raw_zip)
        loopback = field.ipv4('127.0.0.1')
        player_logs = [(loopback, log(client['log'])) for client in entry['clients']]
        verified = field.verify('same-host', {loopback}, report, *exported, log(entry['work'] / 'server.log'), player_logs)
        before_damage = {row['playerId']: row['damageTaken'] for row in entry['before']['statistics']['players']}
        results = {}
        for client, (_, player_text) in zip(entry['clients'], player_logs):
            player = client['player']
            result = json.loads(next(line.removeprefix('VR_CLIENT_DEBRIEF_FINAL ') for line in player_text.splitlines()
                                     if line.startswith('VR_CLIENT_DEBRIEF_FINAL ')))
            debrief.validate_result(result, {'id': entry['id']}, player, {'world': world, 'statistics': statistics})
            check(player_text.count('VR_CLIENT_CONNECTED id=') == 1 and result['damageTaken'] >= before_damage[player['id']],
                  f'Room {player["roomId"]} seat {player["seat"] + 1} receives its result on the original connection')
            results[player['id']] = result
        check(verified['serverAcknowledgements'] == len(results), name + ' server acknowledges every original result exactly once')
        csv_data = request(session + '/report.csv', raw=True)
        rows = list(csv.DictReader(io.StringIO(csv_data.decode('utf-8-sig'))))
        check(len(rows) == len(results) and {row['playerId']: int(row['damageTaken']) for row in rows}
              == {player_id: result['damageTaken'] for player_id, result in results.items()},
              name + ' final CSV retains every original player and accepted damage')
        (evidence / 'final.csv').write_bytes(csv_data)
        journal = journals.analyze(entry['work'] / 'telemetry' / (entry['id'] + '.worldlog'), expected_session=entry['id'])
        check(journal['complete'] and journal['sealed'] and journal['unacknowledgedFrames'] == 0
              and journal['lastFrame']['worldSequence'] == world['acceptedSequence'], name + ' closed journal matches the final world boundary')
        outcome = {'verified': verified, 'journal': journal, 'replay': replay(session, world, evidence)}
        if args.topology == 'single':
            outcome['playerResult'], = results.values()
        else:
            outcome['playerResults'] = list(results.values())
        save(evidence / 'terminal-evidence.json', outcome)
        return {'sessionId': entry['id'], 'rooms': entry['rooms'], 'recovery': recovery, 'replay': outcome['replay'],
                'acknowledgements': len(results)}

    print(json.dumps({'run': run, 'expect': args.expect, 'topology': args.topology, 'playersPerRoom': args.players_per_room,
                      'directory': str(out)}), flush=True)
    try:
        subprocess.run(list(map(str, [control_exe, '--init', data, '--port', api_port, '--report', out / 'control-init.json'])),
                       env=env, cwd=runtime, check=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        keys = read(data / 'operator-keys.json')['OperatorKeys']
        first = start_api('control-original')
        private_hashes = {name: controls.sha(data / name) for name in ('control-instance.json', 'operator-keys.json', 'player-ticket-signing.key')}
        mission = request('/api/missions', {'name': 'Packaged management restart', 'briefing': 'Owned simulation fixture',
            'durationSeconds': 180, 'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
            'enemies': {'count': len(rooms) if args.topology == 'linked' else 1, 'behavior': 'Hold', 'autoAttack': True},
            'props': []}, expected=201)
        for room_ids, port in zip(groups, udp_ports):
            entries.append(start_server(mission['id'], room_ids, port))
        for entry in entries:
            path = entry['ready']
            receipt = wait(lambda: read(path) if path.is_file() else None, 95, entry['name'] + ' original readiness', entry['runner'])
            entry['witness'] = controls.ChildWitness(receipt['childPid'])
            entry['receipt'] = receipt
            binding = receipt['udpBinding']
            check(receipt['sessionId'] == entry['id'] and binding['address'] == '127.0.0.1'
                  and binding['port'] == entry['port'] and binding['processId'] == receipt['childPid'],
                  entry['name'] + ' publishes its own original Windows UDP binding')
        for entry in entries:
            connect_players(entry)
        clients = [client for entry in entries for client in entry['clients']]
        game_processes = [entry['runner'] for entry in entries] + [client['process'] for client in clients]
        wait(lambda: all(client['log'].is_file() and 'VR_CLIENT_CONNECTED id=' in log(client['log']) for client in clients),
             45, 'all original player connections', *game_processes)
        phase('Begin')
        for entry in entries:
            entry['before'], entry['before_frame'] = capture_before(entry)
        if any(process.poll() is not None for process in game_processes):
            raise RuntimeError('An original game process exited before the outage')
        first['witness'].terminate()
        first['witness'].wait()
        outage_started = time.monotonic()
        first['process'].wait(timeout=12)
        try:
            urllib.request.urlopen(base + '/health', timeout=1).close()
        except urllib.error.URLError:
            pass
        else:
            raise RuntimeError('The original management HTTP service is still reachable')
        check(first['process'].returncode != 0 and not read(first['final'])['complete'], 'Abrupt API exit is reported incomplete by its launcher')

        if args.expect == 'recover':
            # A lost HTTP listener stays down past the existing per-request timeout.
            wait(lambda: time.monotonic() - outage_started >= 8, 10, 'eight seconds of management outage', *game_processes)
            check(all(entry['witness'].kernel.WaitForSingleObject(entry['witness'].handle, 0) == 258
                      and not entry['final'].exists() for entry in entries),
                  'Every original server child and player remains live while the API is down')
            save(out / 'outage.json', {'apiPid': first['receipt']['childPid'], 'httpReachable': False,
                'minimumObservedSeconds': time.monotonic() - outage_started,
                'servers': [{key: entry['receipt'][key] for key in ('sessionId', 'streamId', 'childPid', 'udpBinding')} for entry in entries],
                'players': [{'roomId': client['player']['roomId'], 'pid': client['process'].pid} for client in clients]})
        else:
            entry, = entries
            if args.expect == 'timeout':
                wait(lambda: time.monotonic() - outage_started >= 3, 5, 'bounded temporary hold', *game_processes)
            entry['runner'].wait(timeout=23 if args.expect == 'timeout' else 8)
            save(out / 'server-exit-observation.json', {'secondsAfterApiExit': time.monotonic() - outage_started})
            entry['witness'].wait()
            report = read(entry['final'])
            check(entry['runner'].returncode != 0 and report['status'] == 'incomplete' and not report['complete'] and report['childExited'],
                  'Unavailable management ends the owned launcher with an incomplete result')
            if args.expect == 'timeout':
                check('等待恢復逾時' in report['error'], 'Persistent outage reaches the explicit recovery deadline')
                recovery = report['managementRecovery']
                check(recovery['outages'] == 1 and recovery['recoveries'] == 0 and 15000 <= recovery['longestMilliseconds'] < 21000,
                      'Persistent outage has one bounded wait and no fabricated recovery')

        reopened = start_api('control-reopened')
        outage_seconds = time.monotonic() - outage_started
        check(reopened['receipt']['childPid'] != first['receipt']['childPid'], 'A new API process serves the original management instance')
        check(all(controls.sha(data / name) == digest for name, digest in private_hashes.items()), 'Private instance and key files retain their original hashes')
        for entry in entries:
            session, world = resume(entry)
            save(entry['evidence'] / 'after-restart.json', {'outageSeconds': outage_seconds, 'session': session, 'world': world})
        ended = phase('End')
        summaries = [finish(entry) for entry in entries] if args.expect == 'recover' else []
        if args.topology != 'single':
            closed = request('/api/venue/closure')['batch']
            applied = {row['sessionId']: row['appliedAtSequence'] for row in ended['sessions']}
            check(closed['requestId'] == ended['requestId']
                  and {row['sessionId']: row['appliedAtSequence'] for row in closed['sessions']} == applied
                  and all(row['combat'] == row['world'] == 'Sealed' for row in closed['sessions']),
                  'The original venue End receipt identifies every recovered double seal')
            save(out / 'venue-closure.json', closed)
        check(request('/api/sessions') == [], 'No active management sessions remain')
    finally:
        for child in reversed([process for label, process in children.items() if not label.startswith('control-')]):
            try:
                if child.poll() is None:
                    child.terminate()
                    child.wait(timeout=15)
            except Exception as error:
                errors.append(type(error).__name__)
        for entry in reversed(api_runs):
            try:
                if entry['process'].poll() is None:
                    entry['stop'].write_text('stop owned management process', encoding='utf-8')
                    entry['process'].wait(timeout=50)
                if entry['witness']:
                    entry['witness'].wait()
                    entry['witness'].close()
            except Exception as error:
                errors.append(type(error).__name__)
        for entry in entries:
            witness = entry['witness']
            if witness:
                try:
                    witness.wait()
                except Exception as error:
                    errors.append(type(error).__name__)
                finally:
                    witness.close()
        live = [name for name, child in children.items() if child.poll() is None]
        save(out / 'cleanup.json', {'errors': errors, 'remainingChildren': live})
        if errors or live:
            raise RuntimeError('Owned fixture cleanup is not confirmed')
        controls.venue.snapshot_runtime(runtime, out / 'runtime-snapshot')
    save(out / 'checks.json', {'complete': True, 'expect': args.expect, 'topology': args.topology, 'checks': checks,
        'playersPerRoom': args.players_per_room,
        'sessions': summaries, 'runtimeDirectory': str(runtime),
        'consoleVersion': control_manifest['consoleVersion'], 'launcherVersion': server_manifest['launcherVersion'],
        'launcherSourceSha256': server_manifest['launcherSourceSha256'], 'gameFingerprint': server_manifest['build']['sourceFingerprint']})
    print(json.dumps({'complete': True, 'checks': len(checks), 'directory': str(out)}), flush=True)


if __name__ == '__main__':
    main()
