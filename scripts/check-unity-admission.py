"""Check real Windows Unity ticket fencing and reconnect preservation.

--interactive opens a client for Reconnect, Space and W input stages.
No test RPC or injected combat/pose data is used. All rigs remain Simulation.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import secrets
import socket
import struct
import subprocess
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def source_fingerprint():
    project = ROOT / 'clients/unity'
    files = [p for folder in ['Assets/VrCommand', 'Packages/com.vrcommand.simulation', 'Packages/com.unity.transport']
             for p in (project / folder).rglob('*') if p.suffix in ('.cs', '.asmdef')]
    files += [p for p in (project / 'Assets/VrCommand/Resources').rglob('*') if p.suffix in ('.json', '.shader')]
    files += [project / p for p in ['Packages/manifest.json', 'Packages/packages-lock.json', 'Packages/com.unity.transport/UPSTREAM.json', 'ProjectSettings/ProjectVersion.txt']]
    digest = hashlib.sha256()
    for path in sorted(files, key=lambda p: p.relative_to(project).as_posix()):
        name = path.relative_to(project).as_posix().encode()
        length = len(name)
        while length >= 128:
            digest.update(bytes([(length & 127) | 128])); length >>= 7
        digest.update(bytes([length])); digest.update(name)
        content = path.read_bytes(); digest.update(struct.pack('<i', len(content))); digest.update(content)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interactive', action='store_true')
    parser.add_argument('--player-exe', type=Path, default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER', ROOT / 'artifacts/desktop/VrCommand.exe')))
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    args = parser.parse_args()
    if os.name != 'nt' or not args.player_exe.is_file() or not args.api_dll.is_file(): parser.error('Build the Windows player and API first')
    receipt = json.loads((args.player_exe.parent / 'build-receipt.json').read_text())
    if receipt['target'] != 'StandaloneWindows64' or receipt['sourceFingerprint'] != source_fingerprint():
        parser.error('Player receipt does not match current sources; build Desktop before this check')
    directory = ROOT / 'artifacts/unity-admission' / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    directory.mkdir(parents=True)
    keys = {role: secrets.token_hex(32) for role in ['Master', 'GameServer']}
    (directory / 'keys.json').write_text(json.dumps({'OperatorKeys': keys}), encoding='utf-8')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); http_port = probe.getsockname()[1]
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.bind(('127.0.0.1', 0)); game_port = probe.getsockname()[1]
    base = f'http://127.0.0.1:{http_port}'
    environment = {k: v for k, v in os.environ.items() if not k.lower().startswith('operatorkeys__') and k.lower() not in ['operatorkeyfile', 'playerticketsigningkey']}
    environment.update(DataDirectory=str(directory / 'missions'), SessionDataDirectory=str(directory / 'sessions'),
                       OperatorKeyFile=str(directory / 'keys.json'), Logging__LogLevel__Default='Warning')
    all_processes, live = [], {}
    session = None
    end_command_id = str(uuid.uuid4())
    events = []
    api_log = (directory / 'api.log').open('wb')

    def request(route, body=None, *, method=None, admission=None, role='Master', expected=200, optional=False):
        headers = {'Authorization': 'Bearer ' + keys[role], 'Content-Type': 'application/json'}
        if admission: headers['If-Match-Admission'] = admission
        message = urllib.request.Request(base + route, data=None if body is None else json.dumps(body).encode(), headers=headers, method=method)
        try:
            with urllib.request.urlopen(message, timeout=5) as response:
                status, raw = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, raw = error.code, error.read()
        if optional and status == 404: return None
        if status != expected: raise RuntimeError(f'{method or ("POST" if body is not None else "GET")} {route}: expected {expected}, got {status}')
        return json.loads(raw) if raw else None

    def control(action, **options):
        return request(f'/api/sessions/{session}/commands', {'commandId': end_command_id if action == 'End' else str(uuid.uuid4()), 'action': action, **options})

    def world_frame():
        message = urllib.request.Request(base + f'/api/sessions/{session}/world/watch?mode=live', headers={'Authorization': 'Bearer ' + keys['Master']})
        with urllib.request.urlopen(message, timeout=5) as response:
            kind = ''
            for _ in range(60):
                line = response.readline().decode().strip()
                if line.startswith('event: '): kind = line[7:]
                if kind == 'frame' and line.startswith('data: '):
                    value = json.loads(line[6:]); (directory / 'latest-frame.json').write_text(json.dumps(value), encoding='utf-8'); return value
        return None

    def wait_for(predicate, seconds, label):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if any(process.poll() is not None for process in live.values()): raise RuntimeError('Unexpected child exit during ' + label)
            try:
                result = predicate()
                if result: return result
            except (OSError, urllib.error.URLError, RuntimeError): pass
            time.sleep(.15)
        raise RuntimeError('Timed out: ' + label)

    def stage(name, **extra):
        value = {'stage': name, 'directory': str(directory), 'interactive': args.interactive, **extra}
        (directory / 'stage.json').write_text(json.dumps(value, indent=2), encoding='utf-8')
        (ROOT / 'artifacts/latest-unity-admission-path.txt').write_text(str(directory), encoding='utf-8')
        print(json.dumps(value), flush=True)

    def launch(name, config, visible=False):
        path = directory / (name + '.json'); path.write_text(json.dumps(config), encoding='utf-8')
        flags = ['-screen-fullscreen', '0', '-screen-width', '1100', '-screen-height', '760'] if visible else ['-batchmode', '-nographics']
        process = subprocess.Popen([str(args.player_exe.resolve()), *flags, '-logFile', str(directory / (name + '.log')), '--vr-config', str(path)],
                                   cwd=args.player_exe.resolve().parent, creationflags=subprocess.CREATE_NO_WINDOW)
        live[name] = process; all_processes.append(process); return process

    def stop(name):
        process = live.pop(name)
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)

    def log_count(name, marker):
        path = directory / (name + '.log')
        return path.read_text(encoding='utf-8', errors='replace').count(marker) if path.exists() else 0

    def connected(player, expected=True):
        value = world_frame()
        if not value: return None
        body = next((p for p in value['packet']['frame']['players'] if p['id'] == player), None)
        return value if (body is not None and body['connected']) == expected else None

    try:
        api = subprocess.Popen(['dotnet', str(args.api_dll.resolve()), '--urls', base], cwd=ROOT, env=environment,
                               stdout=api_log, stderr=api_log, creationflags=subprocess.CREATE_NO_WINDOW)
        live['api'] = api; all_processes.append(api)
        wait_for(lambda: request('/health'), 30, 'API')
        if request('/').get('version') != '0.22.0': raise RuntimeError('Use API 0.22.0 for the versioned field-prop contract')
        mission = request('/api/missions', {'name': 'Native admission check - Simulation', 'briefing': 'Synthetic desktop rigs, no headset', 'durationSeconds': 1800,
            'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
            'enemies': {'count': 2, 'behavior': 'Hold', 'autoAttack': False}, 'props': []}, expected=201)
        state = request('/api/sessions', {'missionId': mission['id'], 'mode': 'Independent', 'roomIds': [5]}, expected=201); session = state['id']
        players = [str(uuid.uuid4()), str(uuid.uuid4())]
        def join(identity, name):
            return request(f'/api/sessions/{session}/players', {'playerId': identity, 'name': name, 'roomId': 5, 'headset': 'Quest3'})
        for index, identity in enumerate(players): state = join(identity, 'Desktop ' + str(index + 1))
        def invitation(state, identity):
            admission = next(p['admissionId'] for p in state['players'] if p['id'] == identity)
            return admission, request(f'/api/sessions/{session}/players/{identity}/join-ticket', {}, admission=admission)['ticket']
        old_admission, old_ticket = invitation(state, players[0])
        _, peer_ticket = invitation(state, players[1])
        def client(ticket): return {'role': 'Client', 'address': '127.0.0.1', 'port': game_port, 'joinTicket': ticket}
        launch('server', {'role': 'Server', 'address': '127.0.0.1', 'port': game_port, 'sessionId': session, 'managementApiUrl': base,
                          'gameServerKey': keys['GameServer'], 'telemetryOrigin': 'Simulation', 'telemetryDirectory': str(directory / 'telemetry')})
        wait_for(lambda: request(f'/api/sessions/{session}/world', optional=True), 90, 'server recording')
        launch('peer', client(peer_ticket)); persistent = launch('client', client(old_ticket), args.interactive)
        wait_for(lambda: connected(players[0]) and connected(players[1]), 90, 'both clients')
        launch('duplicate', client(old_ticket))
        wait_for(lambda: log_count('duplicate', 'VR_CLIENT_ADMISSION_REJECTED') == 1, 30, 'duplicate ticket rejection')
        events.append('duplicate connected player rejected')
        request(f'/api/sessions/{session}/players/{players[0]}', method='DELETE', admission=old_admission, expected=204)
        wait_for(lambda: connected(players[0], False) and log_count('client', 'VR_CLIENT_DISCONNECTED') >= 1, 20, 'roster revocation')
        state = join(players[0], 'Desktop 1'); admission, ticket = invitation(state, players[0])
        assert admission != old_admission
        request(f'/api/sessions/{session}/players/{players[0]}', method='DELETE', admission=old_admission, expected=409)
        request('/api/player-tickets/validate', {'sessionId': session, 'ticket': old_ticket, 'protocolVersion': 2}, role='GameServer', expected=403)
        launch('revoked', client(old_ticket))
        wait_for(lambda: log_count('revoked', 'VR_CLIENT_ADMISSION_REJECTED') == 1, 30, 'revoked ticket rejection')
        (directory / 'client.json').write_text(json.dumps(client(ticket)), encoding='utf-8')
        if args.interactive:
            stage('click_reconnect', clientPid=persistent.pid)
            wait_for(lambda: log_count('client', 'VR_CLIENT_CONNECTED') >= 2 and connected(players[0]), 300, 'same-process reconnect using reissued ticket')
            assert live['client'].pid == persistent.pid
        else:
            stop('client'); launch('client-new', client(ticket))
            wait_for(lambda: connected(players[0]), 45, 'replacement admission')
        stop('duplicate'); stop('revoked')
        stable = wait_for(lambda: connected(players[0]) and connected(players[1]), 15, 'new binding survives old probe exits')
        events += ['roster revoked old client', 'same-ID reentry fenced', 'stale removal rejected', 'old ticket rejected by API and transport', 'late old exits preserve current binding']
        control('Begin')
        wait_for(lambda: (value if (value := world_frame()) and value['packet']['frame']['phase'] == 'Running' else None), 15, 'Running')
        if args.interactive:
            stage('fire_once')
            wait_for(lambda: next(p for p in request(f'/api/sessions/{session}/statistics')['players'] if p['playerId'] == players[0])['ammoUsed'] >= 1, 300, 'actual window shot')
        control('SetEnemies', enemies={'count': 2, 'behavior': 'Advance', 'autoAttack': True})
        wait_for(lambda: next(p for p in request(f'/api/sessions/{session}/statistics')['players'] if p['playerId'] == players[0])['hitsReceived'] > 0, 30, 'AI damage')
        control('Pause')
        paused = wait_for(lambda: (value if (value := world_frame()) and value['packet']['frame']['phase'] == 'Paused' else None), 15, 'Paused')
        original = next(p for p in paused['packet']['frame']['players'] if p['id'] == players[0])
        if args.interactive:
            stage('move_forward', minimumMetres=.64)
            paused = wait_for(lambda: (value if (value := world_frame()) and abs(next(p for p in value['packet']['frame']['players'] if p['id'] == players[0])['head']['z'] - original['head']['z']) >= .64 else None), 300, 'actual movement beyond admission distance')
        before = next(p for p in paused['packet']['frame']['players'] if p['id'] == players[0])
        (directory / 'before-reconnect.json').write_text(json.dumps(paused, indent=2), encoding='utf-8')
        ticket = request(f'/api/sessions/{session}/players/{players[0]}/join-ticket', {}, admission=admission)['ticket']
        current_client = 'client' if args.interactive else 'client-new'
        connection_ids = re.findall(r'VR_CLIENT_CONNECTED id=(\d+)', (directory / (current_client + '.log')).read_text(encoding='utf-8'))
        assert connection_ids, 'Current client did not log its transport connection'
        connection_id = connection_ids[-1]
        stop(current_client)
        # A stale pose is not a transport disconnect. Abrupt process loss must wait
        # for the real NGO/UDP callback before the same admission can bind again.
        stage('waiting_transport_release', connectionId=connection_id)
        wait_for(lambda: log_count('server', 'VR_SERVER_CLIENT_LEFT id=' + connection_id + '\n') >= 1 and connected(players[0], False), 60, 'actual transport release')
        launch('reconnected', client(ticket))
        stage('reconnecting')
        resumed = wait_for(lambda: connected(players[0]), 90, 'same-admission body with accepted pose')
        after = next(p for p in resumed['packet']['frame']['players'] if p['id'] == players[0])
        assert all(after[field] == before[field] for field in ['health', 'magazine', 'reserve', 'reloading'])
        assert sum((after['head'][axis] - before['head'][axis]) ** 2 for axis in ['x', 'y', 'z']) < .0001
        assert after['rig']['kind'] == 'Simulated' and after['health'] < 100
        (directory / 'after-reconnect.json').write_text(json.dumps(resumed, indent=2), encoding='utf-8')
        events.append('same-admission reconnect preserves accepted position, health and ammunition')
        control('End')
        world = wait_for(lambda: (info if (info := request(f'/api/sessions/{session}/world'))['complete'] else None), 30, 'combat and world seal')
        stats = request(f'/api/sessions/{session}/statistics'); final = world_frame()
        assert stats['origin'] == 'Simulation' and not stats['pendingTelemetry'] and request('/api/sessions') == []
        assert sorted(final['statistics'], key=lambda p: p['playerId']) == sorted(stats['players'], key=lambda p: p['playerId'])
        request(f'/api/sessions/{session}/players/{players[0]}/join-ticket', {}, admission=admission, expected=409)
        launch('ended', client(ticket))
        wait_for(lambda: log_count('ended', 'VR_CLIENT_ADMISSION_REJECTED') == 1, 30, 'ended ticket rejection')
        assert request(f'/api/sessions/{session}/statistics') == stats
        summary = {'source': 'Actual Unity Windows server / clients; Simulation rigs', 'headsets': 0, 'interactive': args.interactive,
                   'playerBuildReceipt': receipt, 'events': events + ['ended admission rejected without changing final statistics'],
                   'beforeReconnect': before, 'afterReconnect': after, 'world': world, 'statistics': stats, 'replayStatisticsMatch': True, 'activeSessions': 0}
        (directory / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        stage('passed', checks=len(summary['events']), frames=world['acceptedSequence'])
    finally:
        if session:
            try: control('End')
            except (OSError, urllib.error.URLError, RuntimeError): pass
        for process in reversed(all_processes):
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        api_log.close()


if __name__ == '__main__':
    main()
