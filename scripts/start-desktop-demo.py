"""Run a playable Windows Simulation in its own API, without changing preview data.

Build Desktop and the API first. Close the game window or press Ctrl+C to finish.
Connection files, private local keys and journals stay under ignored artifacts/.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--player-exe', type=Path, default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER', ROOT / 'artifacts/desktop/VrCommand.exe')))
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    parser.add_argument('--duration', type=int, choices=range(60, 1801), default=900, metavar='60..1800')
    parser.add_argument('--enemies', type=int, choices=range(0, 13), default=3, metavar='0..12')
    parser.add_argument('--peers', type=int, choices=range(0, 5), default=1, help='Additional headless desktop clients, 0..4')
    args = parser.parse_args()
    if os.name != 'nt' or not args.player_exe.is_file() or not args.api_dll.is_file():
        parser.error('Windows and current Unity Desktop / API builds are required')
    receipt_file = args.player_exe.parent / 'build-receipt.json'
    if not receipt_file.is_file():
        parser.error('The player needs its successful build-receipt.json')
    player_receipt = json.loads(receipt_file.read_text(encoding='utf-8'))
    if player_receipt.get('schemaVersion') != 1 or player_receipt.get('target') != 'StandaloneWindows64':
        parser.error('The build receipt must describe a Windows player')
    directory = ROOT / 'artifacts/desktop-demo' / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    directory.mkdir(parents=True)
    tokens = {name: secrets.token_hex(32) for name in ['Master', 'GameServer']}
    key_file = directory / 'keys.json'
    key_file.write_text(json.dumps({'OperatorKeys': tokens}), encoding='utf-8')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); http_port = probe.getsockname()[1]
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.bind(('127.0.0.1', 0)); game_port = probe.getsockname()[1]
    base = f'http://127.0.0.1:{http_port}'
    environment = {key: value for key, value in os.environ.items()
                   if not key.lower().startswith('operatorkeys__') and key.lower() not in ['operatorkeyfile', 'playerticketsigningkey']}
    environment.update(DataDirectory=str(directory / 'missions'), SessionDataDirectory=str(directory / 'sessions'),
                       OperatorKeyFile=str(key_file), Logging__LogLevel__Default='Warning')
    processes = []
    session = None
    api_log = (directory / 'api.log').open('wb')

    def request(route, body=None, admission=None):
        headers = {'Authorization': 'Bearer ' + tokens['Master'], 'Content-Type': 'application/json'}
        if admission:
            headers['If-Match-Admission'] = admission
        message = urllib.request.Request(base + route, data=None if body is None else json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(message, timeout=5) as response:
            return json.load(response)

    def control(action):
        return request('/api/sessions/' + session + '/commands', {'commandId': str(uuid.uuid4()), 'action': action})

    def wait_for(predicate, timeout, label):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if any(process.poll() is not None for process in processes):
                raise RuntimeError('A demo process exited during ' + label)
            try:
                value = predicate()
                if value:
                    return value
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(.25)
        raise RuntimeError('Timed out waiting for ' + label)

    def frame():
        route = base + '/api/sessions/' + session + '/world/watch?mode=live'
        with urllib.request.urlopen(urllib.request.Request(route, headers={'Authorization': 'Bearer ' + tokens['Master']}), timeout=5) as response:
            kind = ''
            for _ in range(60):
                line = response.readline().decode().strip()
                if line.startswith('event: '): kind = line[7:]
                if kind == 'frame' and line.startswith('data: '): return json.loads(line[6:])
        return None

    def launch(name, config, visible=False):
        path = directory / (name + '.json')
        path.write_text(json.dumps(config), encoding='utf-8')
        flags = ['-screen-fullscreen', '0', '-screen-width', '1100', '-screen-height', '760'] if visible else ['-batchmode', '-nographics']
        process = subprocess.Popen([str(args.player_exe.resolve()), *flags, '-logFile', str(directory / (name + '.log')),
                                    '--vr-config', str(path)], cwd=args.player_exe.resolve().parent, creationflags=subprocess.CREATE_NO_WINDOW)
        processes.append(process)
        return process

    try:
        api = subprocess.Popen(['dotnet', str(args.api_dll.resolve()), '--urls', base], cwd=ROOT, env=environment,
                               stdout=api_log, stderr=api_log, creationflags=subprocess.CREATE_NO_WINDOW)
        processes.append(api)
        wait_for(lambda: request('/health'), 30, 'isolated API')
        if request('/').get('version') != '0.20.0':
            raise RuntimeError('This player requires API 0.20.0. Build the current Release API or pass --api-dll with the matching build; an older DLL cannot read the new field-prop recording profile.')
        mission = request('/api/missions', {'name': 'Desktop practice - Simulation', 'briefing': 'Keyboard / mouse preview; synthetic head and hands, no headset.',
            'durationSeconds': args.duration, 'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
            'enemies': {'count': args.enemies, 'behavior': 'Hold', 'autoAttack': False},
            'props': [{'assetId': 'sandbag', 'position': {'x': 0, 'y': 0, 'z': 2}, 'yawDegrees': 0},
                      {'assetId': 'barrel', 'position': {'x': 2, 'y': 0, 'z': 2}, 'yawDegrees': 30}]})
        state = request('/api/sessions', {'missionId': mission['id'], 'mode': 'Independent', 'roomIds': [5]})
        session = state['id']
        players = [str(uuid.uuid4()) for _ in range(args.peers + 1)]
        for index, identity in enumerate(players):
            state = request('/api/sessions/' + session + '/players', {'playerId': identity, 'name': 'Desktop ' + str(index + 1), 'roomId': 5, 'headset': 'Quest3'})
        launch('server', {'role': 'Server', 'address': '127.0.0.1', 'port': game_port, 'sessionId': session,
                         'managementApiUrl': base, 'gameServerKey': tokens['GameServer'], 'telemetryOrigin': 'Simulation', 'telemetryDirectory': str(directory / 'telemetry')})
        wait_for(lambda: request('/api/sessions/' + session + '/world'), 90, 'Unity server')
        # Open the visible client last so the playable view receives focus.
        visible = None
        for index in reversed(range(len(players))):
            player = next(player for player in state['players'] if player['id'] == players[index])
            ticket = request('/api/sessions/' + session + '/players/' + player['id'] + '/join-ticket', {}, player['admissionId'])
            process = launch('client' + str(index + 1), {'role': 'Client', 'address': '127.0.0.1', 'port': game_port, 'joinTicket': ticket['ticket']}, index == 0)
            if index == 0: visible = process
        wait_for(lambda: (value if (value := frame()) and sum(player['connected'] for player in value['packet']['frame']['players']) == len(players) else None), 100, 'desktop clients')
        control('Begin')
        ready = {'schemaVersion': 1, 'baseUrl': base, 'sessionId': session, 'directory': str(directory), 'playerIds': players,
                 'source': 'Simulation', 'headsets': 0, 'processIds': [process.pid for process in processes], 'playerBuildReceipt': player_receipt}
        (directory / 'ready.json').write_text(json.dumps(ready, indent=2), encoding='utf-8')
        (ROOT / 'artifacts/latest-desktop-demo-path.txt').write_text(str(directory), encoding='utf-8')
        print(json.dumps({'ready': True, 'directory': str(directory), 'consoleUrl': base + '/console/', 'source': 'Simulation', 'headsets': 0}), flush=True)
        print('WASD: move; right drag / arrows: aim; click / Space: fire; R: reload. Close the game or Ctrl+C to finish.', flush=True)
        print('Isolated console credentials: keys.json in the demo directory. These are not preview credentials.', flush=True)
        deadline = time.monotonic() + args.duration
        try:
            while time.monotonic() < deadline and visible.poll() is None and not (directory / 'end.request').exists():
                if api.poll() is not None or processes[1].poll() is not None:
                    raise RuntimeError('Demo API or game server stopped')
                value = frame()
                if value: (directory / 'latest-frame.json').write_text(json.dumps(value), encoding='utf-8')
                stats = request('/api/sessions/' + session + '/statistics')
                (directory / 'latest-statistics.json').write_text(json.dumps(stats), encoding='utf-8')
                time.sleep(.25)
        except KeyboardInterrupt:
            pass
        control('End')
        # The visible client may already be closed; only the API / server are needed to seal.
        deadline = time.monotonic() + 30
        world = request('/api/sessions/' + session + '/world')
        while not world['complete'] and time.monotonic() < deadline:
            time.sleep(.25); world = request('/api/sessions/' + session + '/world')
        stats = request('/api/sessions/' + session + '/statistics')
        final = frame()
        if not world['complete'] or stats['pendingTelemetry'] or final is None:
            raise RuntimeError('Demo did not seal; preserve journals for recovery')
        nonempty = any(player[field] for player in stats['players'] for field in ['ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken'])
        if world['header']['origin'] != 'Simulation' or stats['origin'] not in (None, 'Simulation') or stats['origin'] is None and nonempty:
            raise RuntimeError('Desktop practice cannot mix GameServer and Simulation sources')
        if sorted(final['statistics'], key=lambda player: player['playerId']) != sorted(stats['players'], key=lambda player: player['playerId']):
            raise RuntimeError('Replay statistics disagree with final combat statistics')
        active = len(request('/api/sessions'))
        if final['packet']['frame']['phase'] != 'Ended' or active != 0:
            raise RuntimeError('Demo did not release its session')
        summary = {'source': 'Simulation', 'headsets': 0, 'completedAtUtc': datetime.now(timezone.utc).isoformat(),
                   'world': world, 'statistics': stats, 'replayStatisticsMatch': True, 'activeSessions': active}
        (directory / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        print(json.dumps({'sealed': True, 'summary': str(directory / 'summary.json')}), flush=True)
    finally:
        if session:
            try: control('End')
            except (OSError, urllib.error.URLError): pass
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        api_log.close()


if __name__ == '__main__':
    main()
