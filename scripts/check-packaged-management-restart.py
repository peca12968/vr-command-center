"""Terminate only a fixture-owned management API and observe the packaged game server."""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.error
import urllib.request
import uuid
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def free(kind=socket.SOCK_STREAM):
    with socket.socket(socket.AF_INET, kind) as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def main():
    from windows_firewall import require_silent_windows_launch

    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('control-package', 'server-package', 'runtime-root'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--expect', choices=('legacy-stop', 'recover', 'timeout'), required=True)
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('Actual packaged Windows processes are required')

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
    run = 'run-' + uuid.uuid4().hex
    out = ROOT / 'artifacts' / 'packaged-management-restart' / run
    runtime = args.runtime_root.resolve() / run
    out.mkdir(parents=True, exist_ok=False)
    runtime.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PATH=str(Path(os.environ['WINDIR']) / 'System32'), DOTNET_ROOT=str(runtime / 'absent-dotnet'))
    data, work = runtime / 'control', runtime / 'server'
    control_exe, server_exe = control_root / 'Start-Control.exe', server_root / 'Launch-Server.exe'
    api_port, udp_port = free(), free(socket.SOCK_DGRAM)
    base = f'http://127.0.0.1:{api_port}'
    children, api_runs, checks = {}, [], []
    server_witness = None
    session_id = None
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
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        entry['witness'] = controls.ChildWitness(receipt['childPid'], allow_terminate=True)
        check(receipt['uri'] == base and Path(receipt['runtimeCoreClr']).resolve() == (control_root / 'Runtime/coreclr.dll').resolve(),
              label + ' uses the original address and packaged runtime')
        return entry

    def request(route, body=None, *, role='Master', expected=200, admission=None, raw=False):
        headers = {'Authorization': 'Bearer ' + keys[role], 'Content-Type': 'application/json'}
        if admission:
            headers['If-Match-Admission'] = admission
        req = urllib.request.Request(base + route, data=None if body is None else json.dumps(body).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=4) as response:
                status, value = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, value = error.code, error.read()
        if status != expected:
            raise RuntimeError(f'{route} returned {status}, expected {expected}')
        return value if raw else json.loads(value)

    def log(name):
        return (work / 'server.log' if name == 'server' else runtime / 'player.log').read_text(encoding='utf-8', errors='replace')

    def replay(route, world):
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
        save(out / 'full-replay.json', frames)
        return {'frames': len(frames), 'suspendedFrames': sum(row['packet']['suspended'] for row in frames)}

    print(json.dumps({'run': run, 'expect': args.expect, 'directory': str(out)}), flush=True)
    try:
        subprocess.run(list(map(str, [control_exe, '--init', data, '--port', api_port, '--report', out / 'control-init.json'])),
                       env=env, cwd=runtime, check=True, timeout=45)
        keys = read(data / 'operator-keys.json')['OperatorKeys']
        first = start_api('control-original')
        private_hashes = {name: controls.sha(data / name) for name in ('control-instance.json', 'operator-keys.json', 'player-ticket-signing.key')}
        mission = request('/api/missions', {'name': 'Packaged management restart', 'briefing': 'Owned simulation fixture',
            'durationSeconds': 180, 'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
            'enemies': {'count': 1, 'behavior': 'Hold', 'autoAttack': True}, 'props': []}, expected=201)
        session_id = request('/api/sessions', {'missionId': mission['id'], 'mode': 'Independent', 'roomIds': [1]}, expected=201)['id']
        session = '/api/sessions/' + session_id
        player = request(session + '/players', {'playerId': str(uuid.uuid4()), 'roomId': 1, 'name': 'Fixture player', 'headset': 'Quest3'})['players'][0]
        config = runtime / 'server.json'
        save(config, {'role': 'Server', 'managementApiUrl': base, 'gameServerKey': keys['GameServer'],
                      'sessionId': session_id, 'address': '127.0.0.1', 'listenAddress': '127.0.0.1', 'port': udp_port})
        ready, final = out / 'server-ready.json', out / 'server-final.json'
        runner = spawn('server', [server_exe, '--run', config, '--work', work, '--seconds', '180', '--ready-report', ready,
                                  '--report', final, '--peer-diagnostics', 'on'])
        receipt = wait(lambda: read(ready) if ready.is_file() else None, 95, 'original game source readiness', runner)
        server_witness = controls.ChildWitness(receipt['childPid'])
        ticket = request(session + f'/players/{player["id"]}/join-ticket', {}, role='Room1', admission=player['admissionId'])['ticket']
        player_config = runtime / 'player.json'
        save(player_config, {'role': 'Client', 'address': '127.0.0.1', 'port': udp_port, 'joinTicket': ticket})
        client = spawn('player', [server_root / 'Runtime/VrCommand.exe', '-batchmode', '-nographics', '-job-worker-count', '2',
                                  '-logFile', runtime / 'player.log', '--vr-config', player_config])
        player_log = runtime / 'player.log'
        wait(lambda: player_log.is_file() and 'VR_CLIENT_CONNECTED id=' in log('player'), 40, 'original player connection', runner, client)
        request(session + '/commands', {'commandId': str(uuid.uuid4()), 'action': 'Begin'})
        def damaged():
            statistics = request(session + '/statistics')
            return statistics if any(row['damageTaken'] > 0 for row in statistics['players']) else None

        before = wait(damaged, 25, 'actual combat damage before the outage', runner, client)
        original = request(session)
        before_world = request(session + '/world')
        before_frame = request(session + '/world/frames/' + str(before_world['acceptedSequence']))['packet']
        save(out / 'before-restart.json', {'session': original, 'world': before_world, 'statistics': before})
        check(original['state'] == 'Running' and original['combatStream']['streamId'] == receipt['streamId'], 'Original source has accepted combat while Running')
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
        check(first['process'].returncode != 0 and not read(first['final'])['complete'], 'Abrupt API exit is reported incomplete by its own launcher')

        if args.expect == 'recover':
            # Outlast the launcher's five-second request timeout so this proves
            # a failed poll and recovery, rather than a single delayed HTTP read.
            wait(lambda: time.monotonic() - outage_started >= 8, 10, 'eight seconds of management outage', runner, client)
            check(server_witness.kernel.WaitForSingleObject(server_witness.handle, 0) == 258 and not final.exists(),
                  'Original server child and player are still live while the API is down')
        else:
            if args.expect == 'timeout':
                wait(lambda: time.monotonic() - outage_started >= 3, 5, 'bounded temporary hold', runner, client)
            runner.wait(timeout=23 if args.expect == 'timeout' else 8)
            save(out / 'server-exit-observation.json', {'secondsAfterApiExit': time.monotonic() - outage_started})
            server_witness.wait()
            report = read(final)
            check(runner.returncode != 0 and report['status'] == 'incomplete' and not report['complete'] and report['childExited'],
                  'Unavailable management ends the owned launcher with an incomplete result')
            if args.expect == 'timeout':
                check('等待恢復逾時' in report['error'], 'Persistent outage reaches the explicit recovery deadline')
                recovery = report['managementRecovery']
                check(recovery['outages'] == 1 and recovery['recoveries'] == 0 and 15000 <= recovery['longestMilliseconds'] < 21000,
                      'Persistent outage has one bounded wait and no fabricated recovery')

        reopened = start_api('control-reopened')
        outage_seconds = time.monotonic() - outage_started
        after = request(session)
        check(after['id'] == session_id and after['combatStream']['streamId'] == receipt['streamId'] and after['players'] == original['players']
              and after['state'] == 'Running' and after['sequence'] >= original['sequence'], 'Reopened instance retains the original session, stream and admissions')
        check(all(controls.sha(data / name) == digest for name, digest in private_hashes.items()), 'Private instance and key files retain their original hashes')
        after_world = request(session + '/world')
        if args.expect != 'recover':
            check(not after_world['complete'] and 'VR_CLIENT_DEBRIEF_FINAL ' not in log('player'), 'Interrupted game leaves its saved world without a final player result')
        else:
            def resumed():
                latest = request(session + '/world')
                if latest['acceptedSequence'] <= before_world['acceptedSequence']:
                    return None
                frame = request(session + '/world/frames/' + str(latest['acceptedSequence']))['packet']
                return frame if frame['frame']['phase'] == 'Running' and not frame['suspended'] and frame['frame']['tick'] > before_frame['frame']['tick'] else None

            frame = wait(resumed, 15, 'original world advances after management returns', runner, client)
            check(any(row['id'] == player['id'] and row['connected'] for row in frame['frame']['players']),
                  'Original Running world advances with the same player after recovery')
            request(session + '/commands', {'commandId': str(uuid.uuid4()), 'action': 'End'})
            runner.wait(timeout=75)
            server_witness.wait()
            report = read(final)
            check(runner.returncode == 0 and report['complete'] and report['status'] == 'sealed-stopped'
                  and report['childPid'] == receipt['childPid'] and report['streamId'] == receipt['streamId'], 'Original game child finishes only after both seals and normal retention')
            recovery = report['managementRecovery']
            check(recovery['outages'] == recovery['recoveries'] == 1 and 2500 <= recovery['longestMilliseconds'] < 15000,
                  'Launcher records one measured outage and one recovery before its deadline')
            current = request(session)
            statistics = request(session + '/statistics')
            world = request(session + '/world')
            endpoint = request(session + '/connection-endpoint')
            evidence = request(session + '/field-evidence.zip', raw=True)
            with zipfile.ZipFile(io.BytesIO(evidence)) as bundle:
                exported = [field.read_json(bundle.read(name)) for name in ('session.json', 'statistics.json', 'endpoint.json')]
            check(exported == [current, statistics, endpoint] and report['finalWorld'] == world, 'Recovered management ZIP matches the terminal API and launcher seals')
            (out / 'field-evidence.zip').write_bytes(evidence)
            player_text = log('player')
            verified = field.verify('same-host', {field.ipv4('127.0.0.1')}, report, *exported, log('server'), [(field.ipv4('127.0.0.1'), player_text)])
            # The verifier above already checks there is one final marker and
            # compares its decimal statistics to the sealed archive.
            result = json.loads(next(line.removeprefix('VR_CLIENT_DEBRIEF_FINAL ') for line in player_text.splitlines()
                                     if line.startswith('VR_CLIENT_DEBRIEF_FINAL ')))
            debrief.validate_result(result, {'id': session_id}, player, {'world': world, 'statistics': statistics})
            check(verified['serverAcknowledgements'] == 1 and player_text.count('VR_CLIENT_CONNECTED id=') == 1
                  and result['damageTaken'] >= before['players'][0]['damageTaken'] > 0, 'Same player connection receives the original confirmed nonzero result')
            csv_data = request(session + '/report.csv', raw=True)
            rows = list(csv.DictReader(io.StringIO(csv_data.decode('utf-8-sig'))))
            check(len(rows) == 1 and rows[0]['playerId'] == player['id'] and int(rows[0]['damageTaken']) == result['damageTaken'], 'Final CSV retains original accepted damage')
            (out / 'final.csv').write_bytes(csv_data)
            journal = journals.analyze(work / 'telemetry' / (session_id + '.worldlog'), expected_session=session_id)
            check(journal['complete'] and journal['sealed'] and journal['unacknowledgedFrames'] == 0
                  and journal['lastFrame']['worldSequence'] == world['acceptedSequence'], 'Original closed journal matches the final world boundary')
            save(out / 'terminal-evidence.json', {'verified': verified, 'journal': journal, 'playerResult': result, 'replay': replay(session, world)})
        save(out / 'after-restart.json', {'outageSeconds': outage_seconds, 'session': after, 'world': after_world})
        if request(session)['state'] != 'Ended':
            request(session + '/commands', {'commandId': str(uuid.uuid4()), 'action': 'End'})
        check(request('/api/sessions') == [], 'No active management sessions remain')
    finally:
        for label in ('player', 'server'):
            child = children.get(label)
            try:
                if child is not None and child.poll() is None:
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
        if server_witness:
            try:
                server_witness.wait()
                server_witness.close()
            except Exception as error:
                errors.append(type(error).__name__)
        live = [name for name, child in children.items() if child.poll() is None]
        save(out / 'cleanup.json', {'errors': errors, 'remainingChildren': live})
        if errors or live:
            raise RuntimeError('Owned fixture cleanup is not confirmed')
        controls.venue.snapshot_runtime(runtime, out / 'runtime-snapshot')
    save(out / 'checks.json', {'complete': True, 'expect': args.expect, 'checks': checks, 'runtimeDirectory': str(runtime),
        'consoleVersion': control_manifest['consoleVersion'], 'launcherVersion': server_manifest['launcherVersion'],
        'launcherSourceSha256': server_manifest['launcherSourceSha256'], 'gameFingerprint': server_manifest['build']['sourceFingerprint']})
    print(json.dumps({'complete': True, 'checks': len(checks), 'directory': str(out)}), flush=True)


if __name__ == '__main__':
    main()
