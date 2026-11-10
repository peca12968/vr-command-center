"""Exercise direct HTTPS in the actual Windows control package with isolated data and a test CA."""
import argparse
from contextlib import closing
import http.client
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = 'VR_COMMAND_CONTROL_PFX_PASSWORD'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def free_port(address):
    with socket.socket() as probe:
        probe.bind((address, 0))
        return probe.getsockname()[1]


def verify_native(server_folder, runtime, output, keys, tls, request, mission, management_uri, check, game_pin=None):
    state = request(tls, '/api/sessions', keys['Master'], status=201,
                    body={'missionId': mission['id'], 'mode': 'Independent', 'roomIds': [1]})
    route = '/api/sessions/' + state['id']
    roster = request(tls, route + '/players', keys['Room1'], body={
        'playerId': str(uuid.uuid4()), 'roomId': 1, 'name': 'HTTPS fixture player', 'headset': 'Quest3'})
    player, = roster['players']

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.bind(('127.0.0.1', 0))
        udp_port = probe.getsockname()[1]
    config = runtime / 'server-config.json'
    game_settings = {'role': 'Server', 'managementApiUrl': management_uri, 'gameServerKey': keys['GameServer'],
                     'sessionId': state['id'], 'address': '127.0.0.1', 'listenAddress': '127.0.0.1', 'port': udp_port}
    launcher = str(server_folder / 'Launch-Server.exe')
    if game_pin:
        for label, invalid in [('missing-game-pin', game_settings), ('wrong-game-pin', dict(game_settings, managementCertificateSha256='0' * 64)),
                               ('invalid-game-pin', dict(game_settings, managementCertificateSha256='A' * 64))]:
            rejected = output / (label + '.json')
            unused_ready = output / (label + '-ready.json')
            unused_work = runtime / (label + '-work')
            config.write_text(json.dumps(invalid), encoding='utf-8')
            failure = subprocess.run([launcher, '--run', str(config), '--work', str(unused_work), '--seconds', '60',
                                      '--ready-report', str(unused_ready), '--report', str(rejected)], cwd=runtime, timeout=25)
            report = read(rejected)
            check(failure.returncode == 1 and not unused_ready.exists() and not unused_work.exists()
                  and report['status'] == ('incomplete' if label == 'wrong-game-pin' else 'rejected')
                  and report.get('childPid') is None, label + ' rejected before native launch')
        game_settings['managementCertificateSha256'] = game_pin
    config.write_text(json.dumps(game_settings), encoding='utf-8')
    ready, final = output / 'server-ready.json', output / 'server-final.json'
    work = runtime / 'server-work'
    runner = subprocess.Popen([launcher, '--run', str(config), '--work', str(work),
                               '--seconds', '120', '--ready-report', str(ready), '--report', str(final), '--peer-diagnostics', 'on'],
                              cwd=runtime)
    client = None
    ended = False

    def wait_until(condition, process, limit, label):
        deadline = time.monotonic() + limit
        while not condition():
            if process.poll() is not None or time.monotonic() >= deadline:
                raise RuntimeError(label)
            time.sleep(.05)

    def command(action):
        return request(tls, route + '/commands', keys['Master'], body={'commandId': str(uuid.uuid4()), 'action': action})

    try:
        wait_until(ready.exists, runner, 45, 'Native game server did not publish its ready report.')
        origin = read(ready)
        endpoint = request(tls, route + '/connection-endpoint', keys['Room1'])
        check(endpoint['streamId'] == origin['streamId'] and endpoint['port'] == udp_port,
              'HTTPS room sees the original game endpoint')
        ticket = request(tls, route + '/players/' + player['id'] + '/join-ticket', keys['Room1'], body={},
                         admission=player['admissionId'])
        player_config = runtime / 'player-config.json'
        player_config.write_text(json.dumps({'role': 'Client', 'address': '127.0.0.1', 'port': udp_port,
                                             'joinTicket': ticket['ticket']}), encoding='utf-8')
        log = runtime / 'player.log'
        client = subprocess.Popen([str(server_folder / 'Runtime/VrCommand.exe'), '-batchmode', '-nographics',
                                   '-job-worker-count', '2', '-logFile', str(log), '--vr-config', str(player_config)],
                                  cwd=runtime, creationflags=subprocess.CREATE_NO_WINDOW)
        wait_until(lambda: log.exists() and 'VR_CLIENT_CONNECTED id=' in log.read_text(encoding='utf-8', errors='replace'),
                   client, 35, 'Native player did not connect with the HTTPS room ticket.')
        begin = command('Begin')['session']['sequence']
        request(tls, route + '/world', keys['Room2'], status=403)
        running = None
        with closing(tls()) as watcher:
            watcher.request('GET', route + '/world/watch?mode=live', headers={'Authorization': 'Bearer ' + keys['Room1']})
            with watcher.getresponse() as response:
                if response.status != 200 or not response.getheader('Content-Type', '').startswith('text/event-stream'):
                    raise RuntimeError('HTTPS room did not open live observation.')
                deadline = time.monotonic() + 20
                event = ''
                while time.monotonic() < deadline:
                    line = response.readline().decode().rstrip()
                    if line.startswith('event: '):
                        event = line[7:]
                    if event != 'frame' or not line.startswith('data: '):
                        continue
                    packet = json.loads(line[6:])['packet']
                    frame = packet['frame']
                    if frame['phase'] == 'Running' and frame['tick'] > 0 and packet['observedSequence'] >= begin:
                        running = {'sessionId': state['id'], 'streamId': endpoint['streamId'], 'tick': frame['tick'],
                                   'worldSequence': packet['sequence'],
                                   'beginSequence': begin, 'observedSequence': packet['observedSequence']}
                        running_packet = packet
                        break
        check(running is not None, 'authorized HTTPS room sees original running frames; other room is denied')
        (output / 'native-running.json').write_text(json.dumps(running), encoding='utf-8')
        command('End')
        ended = True
        check(runner.wait(timeout=65) == 0, 'native server retains and closes the original sealed round')
        server_report = read(final)
        world = request(tls, route + '/world', keys['Room1'])
        terminal = request(tls, route, keys['Master'])
        combat = terminal['combatStream']
        check(server_report['complete'] and server_report['childExited'] and world['complete'] and combat['sealed']
              and world['acceptedSequence'] == server_report['finalWorld']['acceptedSequence']
              and combat['acceptedSequence'] == server_report['finalCombatStream']['acceptedSequence'],
              'HTTPS reads the original world and combat seals')
        replay = request(tls, route + '/world/frames/' + str(running['worldSequence']), keys['Room1'])
        check(replay['packet'] == running_packet, 'HTTPS replay reads the exact original live packet after sealing')
        from importlib.util import module_from_spec, spec_from_file_location
        field_spec = spec_from_file_location('https_field', ROOT / 'scripts/verify-field-results.py')
        field = module_from_spec(field_spec)
        field_spec.loader.exec_module(field)
        local = ipaddress.IPv4Address('127.0.0.1')
        closed_endpoint = request(tls, route + '/connection-endpoint', keys['Room1'])
        evidence = field.verify('same-host', {local}, server_report, terminal,
                                request(tls, route + '/statistics', keys['Master']), closed_endpoint,
                                field.content(work / 'server.log'), [(local, field.content(log))])
        check(evidence['serverAcknowledgements'] == 1, 'HTTPS-issued player ticket leads to one original acknowledged result')
        (output / 'native-field-results.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    finally:
        try:
            if not ended:
                command('End')
        finally:
            if client and client.poll() is None:
                client.terminate()
                client.wait(timeout=10)
            if runner.poll() is None:
                runner.terminate()
                runner.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--listen-address', type=ipaddress.IPv4Address, default=ipaddress.IPv4Address('127.0.0.1'))
    parser.add_argument('--server-package', type=Path, help='Also verify one native Windows game round through both listeners')
    parser.add_argument('--game-management-https', action='store_true', help='Use HTTPS and WSS from the native game server too')
    parser.add_argument('--operator-network', action='store_true', help='Check direct workstation witnesses and reject the same-PC inventory')
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('Run the actual Windows launcher on Windows.')
    if args.game_management_https and not args.server_package:
        parser.error('--game-management-https requires --server-package.')
    if args.operator_network and not any(args.listen_address in ipaddress.IPv4Network(net)
                                         for net in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')):
        parser.error('--operator-network requires an assigned private --listen-address.')

    from importlib.util import module_from_spec, spec_from_file_location

    def load_module(filename):
        spec = spec_from_file_location(filename, ROOT / 'scripts' / (filename + '.py'))
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    legacy = load_module('check-control-package')
    preflight = load_module('check-venue-operator')
    folder = args.package.resolve()
    manifest = legacy.package.verify(folder)
    assert manifest['launcherSourceSha256'] == legacy.sha(ROOT / 'tools/WindowsControlLauncher/ControlLauncher.cs')
    server_folder = args.server_package.resolve() if args.server_package else None
    if server_folder:
        load_module('package-windows-server').verify(server_folder)
    name = 'run-' + uuid.uuid4().hex
    output = ROOT / 'artifacts/control-https-checks' / name
    output.mkdir(parents=True)
    runtime = args.runtime_root.resolve() / name
    runtime.mkdir(parents=True)
    instance = runtime / 'instance'
    address = str(args.listen_address)
    local_port = free_port('127.0.0.1')
    venue_port = free_port(address)
    while venue_port == local_port:
        venue_port = free_port(address)
    other_port = free_port(address)
    while other_port in (local_port, venue_port):
        other_port = free_port(address)
    exe = str(folder / 'Start-Control.exe')
    password = secrets.token_hex(24)
    env = dict(os.environ)
    env.update({PASSWORD: password, 'ASPNETCORE_PREFERHOSTINGURLS': 'true',
                'Kestrel__Endpoints__Unwanted__Url': f'http://{address}:{other_port}',
                'VR_COMMAND_MANAGED_TLS_ADDRESS': '0.0.0.0', 'VR_COMMAND_MANAGED_TLS_PORT': str(other_port)})
    checks = []
    reports = {}

    def check(condition, label):
        if not condition:
            raise AssertionError(label)
        checks.append(label)

    def must_be_closed(ip, port, label):
        with socket.socket() as probe:
            probe.settimeout(2)
            check(probe.connect_ex((ip, port)) != 0, label)

    def invoke_init(path, port, label, *extra):
        subprocess.run([exe, '--init', str(path), '--port', str(port), '--report', str(output / (label + '.json')), *extra],
                       env=env, timeout=40, check=True)

    def start(path, label, launch_env):
        ready, final, stop = (output / (label + suffix) for suffix in ('-ready.json', '-final.json', '-stop.request'))
        cmd = [exe, '--run', str(path), '--seconds', '180', '--ready-report', str(ready), '--report', str(final), '--stop-file', str(stop)]
        return subprocess.Popen(cmd, env=launch_env), ready, final, stop

    def reject(path, label, launch_env, *, starts_child=False):
        runner, ready, final, stop = start(path, label, launch_env)
        try:
            code = runner.wait(timeout=40)
        finally:
            if runner.poll() is None:
                stop.touch()
                runner.wait(timeout=185)
        result = read(final)
        check(code == 1 and not ready.exists() and result['status'] == 'rejected'
              and result['childExited'] and (result['childPid'] > 0) == starts_child, label)

    def request(connect, path, key, *, body=None, status=200, admission=None, extra_headers=None):
        headers = {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}
        if admission:
            headers['If-Match-Admission'] = admission
        headers.update(extra_headers or {})
        with closing(connect()) as client:
            client.request('POST' if body is not None else 'GET', path, body=None if body is None else json.dumps(body),
                           headers=headers)
            with client.getresponse() as response:
                if response.status != status:
                    raise AssertionError((path, response.status, status))
                return json.loads(response.read())

    complete = False
    try:
        invoke_init(instance, local_port, 'init')
        config = instance / 'control-https.json'
        settings = {'schemaVersion': 1, 'bindAddress': address, 'port': venue_port}
        config.write_text(json.dumps(settings), encoding='utf-8')
        reject(instance, 'missing-pfx', env)
        subprocess.run(['pwsh', '-NoProfile', '-NonInteractive', '-File',
                        str(ROOT / 'tools/WindowsControlLauncher/Tests/New-HttpsFixture.ps1'),
                        '-Directory', str(instance), '-Address', address], env=env, timeout=30, check=True)
        reject(instance, 'missing-password', {name: value for name, value in env.items() if name != PASSWORD})
        reject(instance, 'wrong-password', dict(env, **{PASSWORD: 'incorrect-' + password}), starts_child=True)
        config.write_text(json.dumps(dict(settings, bindAddress='0.0.0.0')), encoding='utf-8')
        reject(instance, 'wildcard-tls-bind', env)
        config.write_text(json.dumps(dict(settings, port=local_port)), encoding='utf-8')
        reject(instance, 'shared-http-tls-port', env)
        config.write_text(json.dumps(settings), encoding='utf-8')
        with socket.socket() as occupant:
            occupant.bind((address, venue_port))
            occupant.listen()
            reject(instance, 'occupied-tls-port', env, starts_child=True)
        if address != '127.0.0.1':
            remote_http = runtime / 'remote-http'
            invoke_init(remote_http, local_port, 'init-remote-http', '--bind', address)
            (remote_http / config.name).write_bytes(config.read_bytes())
            reject(remote_http, 'external-http-with-https', env)
        private_files = ('control-instance.json', 'control-https.json', 'control-https.pfx', 'operator-keys.json')
        original = {name: legacy.sha(instance / name) for name in private_files}
        keys = read(instance / 'operator-keys.json')['OperatorKeys']
        fingerprint = legacy.sha(instance / 'leaf.cer')
        ca = instance / 'root.pem'
        context = preflight.tls_context(ca)

        runner, ready, final, stop = start(instance, 'https', env)
        witness = None
        try:
            deadline = time.monotonic() + 35
            while not ready.exists():
                if time.monotonic() >= deadline or runner.poll() is not None:
                    raise RuntimeError('HTTPS launcher exited or timed out before ready.')
                time.sleep(.05)
            status = read(ready)
            witness = legacy.ChildWitness(status['childPid'])
            check(status['uri'] == f'http://127.0.0.1:{local_port}'
                  and status['httpsBinding'] == f'https://{address}:{venue_port}'
                  and Path(status['runtimeCoreClr']).resolve() == (folder / 'Runtime/coreclr.dll').resolve(),
                  'owned API reports separate HTTP and HTTPS bindings')
            must_be_closed(address, other_port, 'ambient endpoint configuration does not open an extra listener')
            if address != '127.0.0.1':
                must_be_closed(address, local_port, 'loopback HTTP does not listen on the venue IPv4')
            with closing(http.client.HTTPConnection(address, venue_port, timeout=5)) as plain:
                try:
                    plain.request('GET', '/console/')
                    with plain.getresponse() as response:
                        check(response.status == 400, 'venue listener rejects plaintext requests')
                except (ConnectionError, http.client.RemoteDisconnected):
                    checks.append('venue listener rejects plaintext requests')

            challenge = str(uuid.uuid4())
            workstation_option = ['--venue-challenge', challenge] if args.operator_network else []
            for role in preflight.ROLES:
                result = subprocess.run([sys.executable, str(ROOT / 'scripts/check-venue-operator.py'),
                                         status['httpsBinding'], '--role', role, '--ca-file', str(ca),
                                         '--certificate-sha256', fingerprint, *workstation_option],
                                        env=dict(os.environ, VR_COMMAND_OPERATOR_KEY=keys[role.capitalize()]),
                                        timeout=20, capture_output=True, text=True)
                report = json.loads(result.stdout)
                check(result.returncode == 0 and report['complete'] and not result.stderr,
                      'trusted HTTPS chain and room scope: ' + role)
                reports[role] = report

            def tls():
                return http.client.HTTPSConnection(address, venue_port, context=context, timeout=5)

            def local():
                return http.client.HTTPConnection('127.0.0.1', local_port, timeout=5)

            if args.operator_network:
                witnesses = [report['networkWitness'] for report in reports.values()]
                check(all(witness['source'] == address and witness['listener'] == address and witness['port'] == venue_port
                          for witness in witnesses), 'six signed roles retain the actual same-PC socket source')
                witness_path = '/api/operator-network/witness?challenge=' + challenge
                verify_path = '/api/operator-network/verify'
                forwarded = request(tls, witness_path, keys['Room1'], extra_headers={'X-Forwarded-For': '10.55.1.2'})
                check(forwarded['source'] == address, 'a forwarded source header cannot change the captured socket address')
                request(local, witness_path, keys['Master'], status=400)
                request(tls, witness_path, keys['GameServer'], status=403)
                request(tls, verify_path, keys['Room1'], body={}, status=403)
                request(tls, verify_path, keys['Master'], body={'large': 'x' * 8192}, status=400)
                check(True, 'plain HTTP, game-server issue, room verification and oversized submissions are rejected')
                room_addresses = [f'10.211.54.{index}' for index in range(11, 17) if f'10.211.54.{index}' != address][:5]
                inventory = {'masterAddress': address, 'roomAddresses': room_addresses}
                mismatch = request(tls, verify_path, keys['Master'], status=400,
                                   body={'challenge': challenge, 'inventory': inventory, 'witnesses': witnesses})
                check('differs from this venue and expected source' in mismatch['error'],
                      'validly formed same-PC receipts fail at the declared source check')
                inventory_file = output / 'workstation-inventory.json'
                inventory_file.write_text(json.dumps(inventory), encoding='utf-8')
                files = []
                for role, report in reports.items():
                    path = output / ('workstation-' + role + '.json')
                    path.write_text(json.dumps(report), encoding='utf-8')
                    files.append(str(path))
                rejected = subprocess.run([sys.executable, str(ROOT / 'scripts/check-venue-operator.py'), status['httpsBinding'],
                                           '--role', 'master', '--ca-file', str(ca), '--certificate-sha256', fingerprint,
                                           '--venue-challenge', challenge, '--verify-workstations', str(inventory_file), *files],
                                          env=dict(os.environ, VR_COMMAND_OPERATOR_KEY=keys['Master']),
                                          timeout=20, capture_output=True, text=True)
                verdict = json.loads(rejected.stdout)
                check(rejected.returncode == 1 and verdict == {'schemaVersion': 1, 'complete': False, 'failedCheck': 'workstations',
                                                              'error': 'unexpected-http-400'} and not rejected.stderr,
                      'the master CLI cannot claim six workstations from six same-PC signed reports')
                (output / 'workstation-same-pc-rejected.json').write_text(json.dumps(verdict), encoding='utf-8')

            check(request(local, '/api/me', keys['GameServer'])['role'] == 'GameServer', 'local game server identity still works')
            mission = {'name': 'HTTPS fixture', 'briefing': 'Isolated management', 'durationSeconds': 60,
                       'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
                       'enemies': {'count': 1, 'behavior': 'Hold', 'autoAttack': False}, 'props': []}
            request(tls, '/api/missions', keys['Room1'], body=mission, status=403)
            created = request(tls, '/api/missions', keys['Master'], body=mission, status=201)
            check(request(local, '/api/missions/' + created['id'], keys['Master']) == created,
                  'HTTPS Master writes and local API sees the same mission; room authoring denied')
            if server_folder:
                game_uri = status['httpsBinding'] if args.game_management_https else status['uri']
                verify_native(server_folder, runtime, output, keys, tls, request, created, game_uri, check,
                              game_pin=fingerprint if args.game_management_https else None)
        finally:
            if runner.poll() is None:
                stop.touch()
            runner.wait(timeout=185)
            if witness:
                try:
                    witness.wait()
                finally:
                    witness.close()
        closed = read(final)
        check(runner.returncode == 0 and closed['complete'] and closed['graceful'] and closed['childExited'],
              'owned dual-listener child stops normally')
        must_be_closed(address, venue_port, 'owned HTTPS listener closes after stop')
        must_be_closed('127.0.0.1', local_port, 'owned local HTTP listener closes after stop')
        check(original == {name: legacy.sha(instance / name) for name in private_files}, 'instance config, PFX and operator keys remain byte-identical')
        check(all(secret not in item.read_text(encoding='utf-8') for item in output.glob('*.json')
                  for secret in [password, *keys.values()]), 'launcher reports contain no password or operator key')
        complete = True
    finally:
        scope = 'One Windows PC, its own IPv4, packaged API and synthetic CA.'
        if server_folder:
            scope += ' One native server and Windows Simulation client on the same PC.'
        if args.game_management_https:
            scope += ' Game management uses pinned HTTPS and WSS.'
        (output / 'checks.json').write_text(json.dumps({'complete': complete, 'checks': checks, 'preflights': reports,
                                                       'scope': scope}, indent=2) + '\n', encoding='utf-8')
        print(output / 'checks.json', flush=True)


if __name__ == '__main__':
    main()
