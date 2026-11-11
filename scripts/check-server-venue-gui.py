"""Verify real five-room Windows launcher startup and sealed results with an isolated API.

The operator uses the launcher window. This fixture only observes the window's
processes and reports, then drives the prepared game through the management API.
"""

import argparse
import csv
import io
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
import uuid

from importlib import import_module


gui_check = import_module('check-server-gui')
ROOT = gui_check.ROOT
field = gui_check.module('venue_gui_field_results', 'verify-field-results.py')
ROOMS = [1, 2, 3, 4, 5]
LOOPBACK = '127.0.0.1'


def wait_for(read, seconds, label, process=None):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(f'{label}: launcher exited with code {process.returncode}')
        value = read()
        if value:
            return value
        time.sleep(.15)
    raise TimeoutError(label)


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def review(path, key, value):
    return path.exists() and gui_check.read(path) == {key: value}


def child_servers(pid, executable):
    powershell = Path(os.environ['WINDIR']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    script = f'''$children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = {pid}" |
        Where-Object Name -eq 'VrCommand.exe' | Select-Object ProcessId, ExecutablePath)
        ConvertTo-Json -InputObject $children -Compress'''
    process = subprocess.run([str(powershell), '-NoProfile', '-NonInteractive', '-Command', script],
                             capture_output=True, timeout=15, check=True)
    rows = json.loads(process.stdout.decode('utf-8-sig'))
    return {row['ProcessId'] for row in rows if Path(row['ExecutablePath']).resolve() == executable}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--control-package', type=Path, required=True)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--topology', choices=['Independent', 'Linked'], required=True)
    parser.add_argument('--players-per-room', type=int, choices=range(1, 6), default=1)
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('The actual launcher window requires Windows')

    folder = args.package.resolve()
    manifest = gui_check.package.verify(folder)
    executable = (folder / 'Runtime/VrCommand.exe').resolve(strict=True)
    if manifest['launcherSourceSha256'] != gui_check.package.digest(ROOT / 'tools/WindowsServerLauncher/ServerLauncher.cs'):
        raise RuntimeError('Launcher package does not match the repository source')
    out = ROOT / 'artifacts/server-venue-gui' / ('run-' + uuid.uuid4().hex)
    out.mkdir(parents=True)
    runtime = args.runtime_root.resolve() / out.name
    runtime.mkdir(parents=True)
    data = runtime / 'control'
    reports = Path(os.environ['LOCALAPPDATA']) / 'VrCommand/GameServerReports'
    old_reports = set(reports.glob('venue-*.json'))
    control = args.control_package.resolve() / 'Start-Control.exe'
    api = window = api_handle = None
    native_handles = {}
    clients = []
    session_ids = set()
    stage_log = []
    ready = None

    def save(name, value):
        write_json(out / name, value)

    def stage(name, **info):
        row = {'stage': name, 'directory': str(out), 'topology': args.topology, **info}
        stage_log.append(row)
        print(json.dumps(row, ensure_ascii=True), flush=True)

    def request(path, body=None, *, key=None, admission=None, status=200, raw=False):
        headers = {'Authorization': 'Bearer ' + keys['Master'], 'Content-Type': 'application/json'}
        if key:
            headers['Idempotency-Key'] = key
        if admission:
            headers['If-Match-Admission'] = admission
        req = urllib.request.Request(base + '/api' + path, headers=headers,
                                     data=None if body is None else json.dumps(body).encode('utf-8'))
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                if response.status != status:
                    raise RuntimeError(f'Unexpected status {response.status} for {path}')
                return response.read() if raw else json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f'HTTP {error.code} for {path}') from error

    def phase(action, fields):
        targets = request('/venue/phase')[action.lower()]
        assert {row['sessionId'] for row in targets} == session_ids
        assert sorted(room for row in targets for room in row['roomIds']) == ROOMS
        request_id = str(uuid.uuid4())
        body = {'action': action, 'targets': [{name: row[name] for name in fields} for row in targets]}
        receipt = request('/venue/phase', body, key=request_id)
        assert receipt['requestId'] == request_id and receipt['action'] == action and not receipt['duplicate']
        assert {row['sessionId'] for row in receipt['sessions']} == session_ids
        save(action.lower() + '.json', receipt)
        return {row['sessionId']: row['appliedAtSequence'] for row in receipt['sessions']}

    def launcher_report(suffix, item_key):
        matches = []
        for path in reports.glob('venue-*-' + suffix + '.json'):
            if path in old_reports:
                continue
            value = gui_check.read(path)
            if {entry[item_key]['sessionId'] for entry in value['servers']} == session_ids:
                matches.append((path, value))
        if len(matches) > 1:
            raise RuntimeError('Multiple launcher reports identify the same isolated sessions')
        return matches[0] if matches else None

    def full_readiness(running=None):
        if any(process.poll() is not None for _, process, _, _ in clients):
            raise RuntimeError('A fixture player exited before the original game started')
        rooms = request('/rooms/readiness')['rooms']
        if [row['roomId'] for row in rooms] != ROOMS:
            return None
        for row in rooms:
            if row['sessionId'] != room_sessions[row['roomId']] or row['simulatedReady'] != args.players_per_room:
                return None
            if running is None:
                if not row['venueBeginReady']:
                    return None
            else:
                marker = row.get('venuePhase')
                if (not row.get('clock') or row['clock']['phase'] != 'Running' or not marker
                        or marker['action'] != 'Begin' or not marker['worldSequence']
                        or marker['appliedAtSequence'] != running[row['sessionId']]):
                    return None
        return rooms

    try:
        subprocess.run([str(control), '--init', str(data), '--port', str(gui_check.free()),
                        '--report', str(out / 'init.json')], check=True, timeout=45)
        marker = gui_check.read(data / 'control-instance.json')
        base = f'http://{LOOPBACK}:{marker["port"]}'
        api = subprocess.Popen([str(control), '--run', str(data), '--seconds', '900',
                                '--ready-report', str(out / 'api-ready.json'),
                                '--stop-file', str(out / 'api-stop.request'), '--report', str(out / 'api-final.json')])
        api_ready = wait_for(lambda: (out / 'api-ready.json').is_file() and gui_check.read(out / 'api-ready.json'),
                             45, 'isolated management API readiness', api)
        api_handle = gui_check.checks.ChildWitness(api_ready['childPid'])
        original_hashes = {name: gui_check.checks.sha(data / name) for name in
                           ('control-instance.json', 'operator-keys.json', 'player-ticket-signing.key')}
        keys = gui_check.read(data / 'operator-keys.json')['OperatorKeys']
        mission = request('/missions', {
            'name': 'Five-room Windows launcher check', 'briefing': 'Loopback Windows simulation',
            'durationSeconds': 300, 'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
            'enemies': {'count': 1, 'behavior': 'Hold', 'autoAttack': False}, 'props': []
        }, status=201)
        groups = [ROOMS] if args.topology == 'Linked' else [[room] for room in ROOMS]
        states = []
        room_sessions = {}
        for rooms in groups:
            session = request('/sessions', {'missionId': mission['id'], 'mode': args.topology, 'roomIds': rooms}, status=201)
            sid = session['id']
            session_ids.add(sid)
            for room in rooms:
                room_sessions[room] = sid
                for seat in range(1, args.players_per_room + 1):
                    session = request(f'/sessions/{sid}/players', {'playerId': str(uuid.uuid4()),
                                      'roomId': room, 'name': f'Fixture {room}-{seat}', 'headset': 'Quest3'})
            states.append(session)

        ports = set()
        entries = []
        for state in states:
            port = gui_check.free(socket.SOCK_DGRAM)
            while port in ports:
                port = gui_check.free(socket.SOCK_DGRAM)
            ports.add(port)
            entries.append({'roomIds': state['roomIds'], 'sessionId': state['id'], 'port': port,
                            'sessionSequence': state['sequence'], 'missionId': mission['id']})
        plan = {'version': 4, 'controlInstance': str(data / 'control-instance.json'), 'topology': args.topology,
                'address': LOOPBACK, 'listenAddress': LOOPBACK, 'servers': entries}
        plan_path = runtime / 'venue-plan.json'
        write_json(plan_path, plan)
        save('plan.json', plan)
        window = subprocess.Popen([str(folder / 'Launch-Server.exe'), '--venue-window', str(plan_path)], cwd=runtime)
        stage('review-and-start-window', guiPid=window.pid, plan=str(plan_path), servers=entries)
        wait_for(lambda: review(out / 'preview.review.json', 'topology', args.topology), 360, 'reviewed GUI plan', window)
        ready_path, ready = wait_for(lambda: launcher_report('ready', 'ready'), 120, 'actual GUI launcher readiness', window)
        assert ready['status'] == 'venue-ready' and ready['topology'] == args.topology
        bindings = {item['ready']['sessionId']: item['ready'] for item in ready['servers']}
        pids = {item['childPid'] for item in bindings.values()}
        assert len(pids) == len(entries) and child_servers(window.pid, executable) == pids
        for pid in pids:
            native_handles[pid] = gui_check.checks.ChildWitness(pid)
        for entry in entries:
            sid = entry['sessionId']
            item = bindings[sid]
            endpoint = request(f'/sessions/{sid}/connection-endpoint')
            assert item['address'] == endpoint['address'] == LOOPBACK
            assert item['port'] == endpoint['port'] == entry['port'] and item['streamId'] == endpoint['streamId']
            assert item['peerDiagnosticsEnabled'] is True
        save('venue-ready.json', ready)
        stage('venue-ready', guiPid=window.pid, childPids=sorted(pids))

        for state in states:
            sid = state['id']
            for player in state['players']:
                invite = request(f'/sessions/{sid}/players/{player["id"]}/join-ticket', {}, admission=player['admissionId'])
                log = runtime / f'player-{player["roomId"]}-{player["seat"]}.log'
                config = log.with_suffix('.private.json')
                write_json(config, {'role': 'Client', 'address': LOOPBACK, 'port': bindings[sid]['port'],
                                    'joinTicket': invite['ticket']})
                player_process = subprocess.Popen([str(executable), '-batchmode', '-nographics', '-job-worker-count', '2',
                    '-logFile', str(log), '--vr-config', str(config)], cwd=runtime, creationflags=subprocess.CREATE_NO_WINDOW)
                clients.append((sid, player_process, log, config))
                time.sleep(.12)

        save('preparing.json', wait_for(full_readiness, 90, 'all simulated seats preparing', window))
        begin = phase('Begin', ('sessionId', 'phaseSinceSequence', 'sessionSequence'))
        save('running.json', wait_for(lambda: full_readiness(begin), 60, 'all simulated seats running', window))
        stage('running', seats=len(clients))
        ended = phase('End', ('sessionId', 'phaseSinceSequence'))
        stage('waiting-for-seals', guiPid=window.pid)
        final_path, final = wait_for(lambda: launcher_report('final', 'result'), 110, 'original GUI final report', window)
        assert final['complete'] and final['readyPublished'] and final['topology'] == args.topology
        assert final_path.name == ready_path.name.removesuffix('-ready.json') + '-final.json'
        assert final['instanceId'] == ready['instanceId'] == marker['instanceId']
        assert final['sourceAttachment'] == final['endpointPublication'] == 'confirmed'
        assert all(handle.kernel.WaitForSingleObject(handle.handle, 5000) == 0 for handle in native_handles.values())
        save('venue-final.json', final)
        stage('close-completed-window', guiPid=window.pid)
        if window.wait(timeout=120) != 0:
            raise RuntimeError('Launcher window did not close normally')
        wait_for(lambda: review(out / 'closed.review.json', 'closed', True), 30, 'window close review')

        rows = []
        for item in final['servers']:
            result = item['result']
            sid = result['sessionId']
            started = bindings[sid]
            assert result['childPid'] == started['childPid'] and result['streamId'] == started['streamId']
            work = Path(started['workDirectory'])
            route = f'/sessions/{sid}'
            logs = [(ipaddress.IPv4Address(LOOPBACK), field.content(log)) for owner, _, log, _ in clients if owner == sid]
            evidence, _ = field.verify_session('same-host', {ipaddress.IPv4Address(LOOPBACK)}, result, request(route),
                request(route + '/statistics'), request(route + '/connection-endpoint'), field.content(work / 'server.log'),
                len(logs), logs, world_journal=work / 'telemetry' / (sid + '.worldlog'),
                combat_journal=work / 'telemetry' / (sid + '.journal'), applied_end=ended[sid], verify_player_sources=True)
            assert evidence['serverAcknowledgements'] == len(logs) and evidence['worldJournal']['runningFrames'] > 0
            report = request(route + '/report.csv', raw=True)
            csv_rows = list(csv.DictReader(io.StringIO(report.decode('utf-8-sig'))))
            assert len(csv_rows) == len(logs) and {int(row['playerRoomId']) for row in csv_rows} == set(item['roomIds'])
            (out / (sid + '.csv')).write_bytes(report)
            rows.append({'roomIds': item['roomIds'], 'sessionId': sid, 'evidence': evidence})
        assert request('/sessions') == []
        assert all(gui_check.checks.sha(data / name) == digest for name, digest in original_hashes.items())
        result = {'complete': True, 'topology': args.topology, 'playersPerRoom': args.players_per_room,
                  'guiExitCode': window.returncode, 'servers': rows, 'scope': 'WinForms, loopback and simulated Windows players'}
    except BaseException as error:
        stage('failed', errorType=type(error).__name__, message=str(error))
        raise
    finally:
        cleanup = []

        def stop(label, action):
            try:
                action()
            except Exception as error:
                cleanup.append({'label': label, 'errorType': type(error).__name__, 'message': str(error)})

        if window is not None and window.poll() is None:
            stop('window', lambda: (window.terminate(), window.wait(timeout=15)))
        for _, process, _, config in clients:
            if process.poll() is None:
                stop('client', lambda: (process.terminate(), process.wait(timeout=15)))
            if process.poll() is not None:
                stop('expired fixture ticket', lambda: config.unlink(missing_ok=True))
        for pid, handle in native_handles.items():
            if handle.kernel.WaitForSingleObject(handle.handle, 15000) != 0:
                cleanup.append({'label': 'original GUI child', 'pid': pid, 'errorType': 'ProcessStillLive'})
            handle.close()
        if window is not None:
            def check_no_servers():
                if child_servers(window.pid, executable):
                    raise RuntimeError('The launcher still owns native server processes')
            stop('native server cleanup', check_no_servers)
        if api is not None and api.poll() is None:
            stop('management runner', lambda: ((out / 'api-stop.request').touch(exist_ok=False), api.wait(timeout=50)))
        if api_handle is not None:
            stop('management child', api_handle.wait)
            api_handle.close()
        save('cleanup.json', {'errors': cleanup, 'remainingWindow': window is not None and window.poll() is None,
                              'remainingClients': sum(process.poll() is None for _, process, _, _ in clients),
                              'remainingApiRunner': api is not None and api.poll() is None})
        save('stages.json', stage_log)
        if cleanup:
            raise RuntimeError('Original process cleanup was not verified; runtime left in place')
        if ready:
            for item in ready['servers']:
                start = item['ready']
                shutil.copytree(start['workDirectory'], runtime / ('server-' + start['sessionId']))
        gui_check.venue.snapshot_runtime(runtime, out / 'runtime-snapshot')
    save('checks.json', result)
    stage('passed')


if __name__ == '__main__':
    main()
