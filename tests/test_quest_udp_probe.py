import base64
from contextlib import redirect_stderr
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
from threading import Barrier, Event, Lock
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
SPEC = importlib.util.spec_from_file_location('quest_udp', ROOT / 'scripts/probe-quest-udp.py')
quest_udp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(quest_udp)
VENUE_SPEC = importlib.util.spec_from_file_location('quest_venue', ROOT / 'scripts/probe-quest-venue.py')
quest_venue = importlib.util.module_from_spec(VENUE_SPEC)
VENUE_SPEC.loader.exec_module(quest_venue)
SERVER = '127.0.0.1'
PEER = '127.0.0.2'
POWERSHELL = shutil.which('powershell.exe' if os.name == 'nt' else 'pwsh')
EDITOR_JDK = Path('F:/Tools/UnityEditors/6000.3.27f1/Editor/Data/PlaybackEngines/AndroidPlayer/OpenJDK')


class DiagnosticInstallTests(unittest.TestCase):
    def test_only_missing_diagnostic_is_installed_on_the_selected_quest(self):
        spec = importlib.util.spec_from_file_location('install_probe', ROOT / 'scripts/install-quest-udp-probe.py')
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as directory:
            adb, apk = (Path(directory) / name for name in ('adb.exe', 'diagnostic.apk'))
            adb.touch()
            apk.write_bytes(b'fixture diagnostic')
            digest = hashlib.sha256(apk.read_bytes()).hexdigest()
            for model, installed, remote, success in (
                    ('Quest 3', False, digest, True), ('Quest 3', True, digest, True),
                    ('Quest 3', True, '0'*64, False), ('Other', False, digest, False)):
                with self.subTest(model=model, installed=installed, remote=remote):
                    installs = []
                    def invoke(command, **options):
                        if command[1:] == ['devices', '-l']:
                            response = 'List of devices attached\nfixture device transport_id:31'
                        else:
                            self.assertEqual(command[:3], [str(adb), '-t', '31'])
                            args = command[3:]
                            if args == ['shell', 'getprop', 'ro.product.model']:
                                response = model
                            elif args == ['shell', 'pm', 'list', 'packages', installer.PACKAGE]:
                                response = 'package:' + installer.PACKAGE if installed else ''
                            elif args[0] == 'install':
                                staged = Path(args[1])
                                self.assertNotEqual(staged, apk)
                                self.assertEqual(staged.read_bytes(), apk.read_bytes())
                                installs.append(staged)
                                response = 'Success'
                            elif args == ['shell', 'pm', 'path', installer.PACKAGE]:
                                response = 'package:/data/app/fixture/base.apk'
                            else:
                                self.assertEqual(args, ['shell', 'sha256sum', '/data/app/fixture/base.apk'])
                                response = remote + '  /data/app/fixture/base.apk'
                        return subprocess.CompletedProcess(command, 0, response.encode())
                    with patch.object(installer, 'APK_SHA256', digest), patch('subprocess.run', side_effect=invoke) as child, \
                            patch('windows_firewall.require_silent_windows_launch') as guard:
                        if success:
                            self.assertEqual(installer.install(adb, 'fixture', apk)['status'],
                                             'already-installed' if installed else 'installed')
                        else:
                            with self.assertRaises(ValueError):
                                installer.install(adb, 'fixture', apk)
                        self.assertEqual(len(installs), int(not installed and model == 'Quest 3'))
                        self.assertTrue(all(not path.exists() for path in installs))
                        self.assertEqual(guard.call_count, child.call_count)
            with patch('subprocess.run') as child:
                with self.assertRaisesRegex(ValueError, 'differs'):
                    installer.install(adb, 'fixture', apk)
                child.assert_not_called()


def java_tool(name):
    suffix = '.exe' if os.name == 'nt' else ''
    for root in (os.environ.get('VR_COMMAND_JDK'), os.environ.get('JAVA_HOME'), EDITOR_JDK if os.name == 'nt' else None):
        if root:
            candidate = Path(root) / 'bin' / (name + suffix)
            if candidate.is_file():
                return str(candidate)
    return shutil.which(name)


def write_guarded_launch(directory, mode, endpoints, prefix):
    address = endpoints[0]['address']
    binding = {'address': address, 'listenAddress': address}
    rows = [{'roomIds': endpoint['roomIds'], 'sessionId': f'00000000-0000-4000-8000-{index:012}',
             'missionId': f'00000000-0000-4000-8000-{index + 10:012}', 'sessionSequence': 3, 'port': endpoint['port']}
            for index, endpoint in enumerate(endpoints, 1)]
    launch, preview = directory / f'{prefix}-launch.json', directory / f'{prefix}-preview.json'
    launch.write_text(json.dumps({'version': 4, 'controlInstance': 'fixture/control-instance.json', 'topology': mode,
                                  **binding, 'servers': rows}), encoding='utf-8')
    preview.write_text(json.dumps({'schemaVersion': 1, 'complete': True, 'status': 'venue-checked', 'topology': mode,
                                   'servers': [{**row, **binding} for row in rows]}), encoding='utf-8')
    return launch, preview


@unittest.skipUnless(java_tool('javac') and java_tool('java'), 'A JDK is required for the Quest probe protocol checks')
class QuestUdpProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from windows_firewall import WindowsFirewallLaunchError, require_silent_windows_launch

        java = java_tool('java')
        try:
            require_silent_windows_launch(sys.executable)
            require_silent_windows_launch(java)
            if POWERSHELL:
                require_silent_windows_launch(POWERSHELL)
        except WindowsFirewallLaunchError as error:
            raise unittest.SkipTest(str(error)) from error
        work = tempfile.TemporaryDirectory(prefix='quest-udp-test-')
        cls.addClassCleanup(work.cleanup)
        cls.classes = Path(work.name)
        subprocess.run([java_tool('javac'), '--release', '8', '-d', str(cls.classes),
                        str(ROOT / 'tools/QuestUdpProbe/Probe.java')], check=True, capture_output=True, timeout=20)
        cls.java = [java, '-cp', str(cls.classes), 'com.vrcommand.udpprobe.Probe']

    def setUp(self):
        work = tempfile.TemporaryDirectory(prefix='quest-udp-session-')
        self.addCleanup(work.cleanup)
        self.work = Path(work.name)
        self.secret = bytes(range(32))
        self.key = self.work / 'probe.key'
        self.key.write_bytes(base64.b64encode(self.secret))

    def command(self, port, count, timeout, peer=SERVER):
        return [*self.java, str(self.key), PEER, peer, str(port), str(count), str(timeout)]

    @unittest.skipUnless(POWERSHELL, 'PowerShell is required for Windows listener interoperability')
    def test_java_probe_pairs_with_original_windows_listener(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserve:
            reserve.bind((SERVER, 0))
            port = reserve.getsockname()[1]
        shell = [POWERSHELL, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'RemoteSigned',
                 '-File', str(ROOT / 'scripts/check-lan-udp.ps1')]
        listener_report = self.work / 'listener.ndjson'
        with listener_report.open('xb') as stream, subprocess.Popen(
            [*shell, '-Mode', 'Listen', '-KeyFile', str(self.key), '-LocalAddress', SERVER, '-PeerAddress', PEER,
             '-Port', str(port), '-Count', '3', '-Seconds', '10'], stdout=stream, stderr=subprocess.STDOUT,
        ) as listener:
            try:
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    if b'\n' in listener_report.read_bytes():
                        self.assertEqual('listening', json.loads(listener_report.read_bytes().splitlines()[0])['stage'])
                        break
                    self.assertIsNone(listener.poll())
                    time.sleep(.04)
                else:
                    self.fail('Windows listener did not bind')
                probe = subprocess.run(self.command(port, 3, 900), capture_output=True, check=True, timeout=8)
                self.assertEqual(0, listener.wait(timeout=5))
            finally:
                if listener.poll() is None:
                    listener.kill()
        listener_final = json.loads(listener_report.read_bytes().splitlines()[-1])
        probe_final = json.loads(probe.stdout)
        self.assertEqual(3, probe_final['matched'])
        self.assertEqual(listener_final['exchangeSha256'], probe_final['exchangeSha256'])
        self.assertEqual([1, 2, 3], [sample['sample'] for sample in probe_final['samples']])
        probe_report = self.work / 'quest-probe.json'
        probe_report.write_bytes(probe.stdout)
        bind = (datetime.now(timezone.utc) + timedelta(seconds=2)).isoformat()
        paired = subprocess.run([*shell, '-ListenerReport', str(listener_report), '-ProbeReport', str(probe_report),
                                '-ExpectedServerAddress', SERVER, '-ExpectedGamePort', str(port),
                                '-ExpectedPeerAddresses', f'{SERVER},{PEER}', '-BindingObservedAtUtc', bind],
                               capture_output=True, check=True, timeout=8)
        self.assertEqual(1, json.loads(paired.stdout)['verifiedPeerIndex'])
        self.assertNotIn(PEER.encode(), paired.stdout)

    def test_rejects_wrong_port_bad_tag_and_oversized_reply(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as other:
            server.bind((SERVER, 0))
            other.bind((SERVER, 0))
            server.settimeout(5)
            with subprocess.Popen(self.command(server.getsockname()[1], 1, 600),
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE) as probe:
                try:
                    request, source = server.recvfrom(256)
                    self.assertEqual(PEER, source[0])
                    nonce = request.split(b':')[1]
                    prefix = b'VRLAN1R:' + nonce
                    reply = prefix + b':' + hmac.new(self.secret, prefix, hashlib.sha256).hexdigest().encode()
                    other.sendto(reply, source)
                    server.sendto(prefix + b':' + b'0' * 64, source)
                    server.sendto(reply + b'X', source)
                    output, _ = probe.communicate(timeout=5)
                finally:
                    if probe.poll() is None:
                        probe.kill()
        self.assertEqual(1, probe.returncode)
        report = json.loads(output)
        self.assertFalse(report['complete'])
        self.assertEqual(0, report['matched'])
        self.assertEqual([{'sample': 1, 'roundTripMs': None}], report['samples'])
        self.assertIsNone(report['exchangeSha256'])

    def test_key_and_address_failures_do_not_echo_inputs(self):
        invalid_address = subprocess.run(self.command(7777, 1, 200, '8.8.8.8'), capture_output=True, timeout=8)
        self.assertEqual(1, invalid_address.returncode)
        self.assertEqual('address', json.loads(invalid_address.stdout)['step'])
        self.assertNotIn(b'8.8.8.8', invalid_address.stdout + invalid_address.stderr)
        self.key.write_bytes(b'secret-invalid-key')
        invalid_key = subprocess.run(self.command(7777, 1, 200), capture_output=True, timeout=8)
        self.assertEqual(1, invalid_key.returncode)
        self.assertEqual('key', json.loads(invalid_key.stdout)['step'])
        self.assertNotIn(b'secret-invalid-key', invalid_key.stdout + invalid_key.stderr)

    @unittest.skipUnless(POWERSHELL, 'PowerShell is required for the Quest venue listener')
    def test_venue_runs_two_java_sources_sequentially_on_original_shared_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reservation:
            reservation.bind((SERVER, 0))
            port = reservation.getsockname()[1]
        shell = [POWERSHELL, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'RemoteSigned',
                 '-File', str(ROOT / 'scripts/check-lan-udp.ps1')]
        devices = [{'roomId': 1, 'seat': 2, 'serial': 'fixture-a', 'address': PEER},
                   {'roomId': 4, 'seat': 5, 'serial': 'fixture-b', 'address': '127.0.0.3'}]
        rooms = list(range(1, 6))
        launch, preview = write_guarded_launch(self.work, 'Linked', [{'roomIds': rooms, 'address': SERVER, 'port': port}], 'prepared')
        source_addresses = {(row['roomId'], row['seat']): row['address'] for row in devices}
        seat_addresses, device_map, network = (self.work / f'prepared-{name}.json' for name in ('seats', 'devices', 'network'))
        seat_addresses.write_text(json.dumps({'version': 1, 'seats': [
            {'roomId': room, 'seat': seat, 'address': source_addresses.get((room, seat), PEER)}
            for room in rooms for seat in rooms]}), encoding='utf-8')
        device_map.write_text(json.dumps({'version': 1, 'seats': [
            {key: value for key, value in row.items() if key != 'address'} for row in devices]}), encoding='utf-8')
        prepared = subprocess.run([sys.executable, str(ROOT / 'scripts/prepare-venue-network-plan.py'),
                                   '--launch-plan', str(launch), '--launcher-preview', str(preview), '--seat-addresses', str(seat_addresses),
                                   '--quest-device-map', str(device_map), '--output', str(network)], capture_output=True, text=True, timeout=15)
        self.assertEqual(0, prepared.returncode, prepared.stderr)
        output = self.work / 'actual-batch'
        launcher, parsed = quest_venue.launcher_proof(launch, preview, output)
        mode, groups = quest_venue.load_plan(device_map, network, launcher_preview=parsed)
        self.assertEqual('Linked', mode)
        launch_session = {key: parsed[2][tuple(rooms)][key] for key in ('sessionId', 'missionId', 'sessionSequence')}
        self.assertEqual([{'roomIds': rooms, 'address': SERVER, 'port': port, 'devices': devices,
                           'launchSession': launch_session}], groups)

        def java_probe(args, *, target):
            command = [*self.java, str(args.key_file), args.local_address, args.peer_address, str(args.port),
                       str(args.count), str(args.timeout_ms)]
            return json.loads(subprocess.run(command, capture_output=True, check=True, timeout=8).stdout)

        with patch.object(quest_venue.quest_udp, 'probe_target', return_value=['adb', '-t', '41']), patch.object(
                quest_venue.quest_udp, 'run_probe', side_effect=java_probe) as probes, redirect_stderr(io.StringIO()):
            report = quest_venue.probe_venue(shell, self.work / 'adb-fixture.exe', mode, groups, output, 2, 900, launcher=launcher)
        self.assertTrue(report['complete'])
        self.assertEqual(2, report['verifiedSeats'])
        self.assertEqual([PEER, '127.0.0.3'], [call.args[0].local_address for call in probes.call_args_list])
        self.assertEqual({port}, {call.args[0].port for call in probes.call_args_list})
        self.assertFalse(any(call.args[0].key_file.exists() for call in probes.call_args_list))
        for pair in report['groups'][0]['udpSourcePreflights']:
            self.assertTrue((output / pair['probe']).is_file())
            self.assertTrue((output / pair['listener']).is_file())
        self.assertEqual(5, len(list(output.iterdir())))
        self.assertNotIn('127.0.0.', (output / 'preflight-report.json').read_text(encoding='utf-8'))
        pairs, (verified, bindings) = quest_venue.field.read_udp_preflight_batch(output / 'preflight-report.json', mode, [rooms])
        self.assertEqual(2, len(pairs[tuple(rooms)]))
        self.assertEqual(port, bindings[tuple(rooms)]['port'])
        self.assertEqual(hashlib.sha256(launch.read_bytes()).hexdigest(), verified['planSha256'])
        self.assertEqual(hashlib.sha256(preview.read_bytes()).hexdigest(), verified['previewSha256'])
        full_network = self.work / 'full-network.json'
        prepared = subprocess.run([sys.executable, str(ROOT / 'scripts/prepare-venue-network-plan.py'),
                                   '--launch-plan', str(launch), '--launcher-preview', str(preview), '--seat-addresses', str(seat_addresses),
                                   '--output', str(full_network)], capture_output=True, text=True, timeout=15)
        self.assertEqual(0, prepared.returncode, prepared.stderr)
        venue_report = self.work / 'ready.json'
        checked = subprocess.run([sys.executable, str(ROOT / 'scripts/check-venue-udp-preflight.py'),
                                  '--network-plan', str(full_network), '--launch-plan', str(launch), '--launcher-preview', str(preview),
                                  '--batch', str(output / 'preflight-report.json'), '--output', str(venue_report)],
                                 capture_output=True, text=True, timeout=20)
        self.assertEqual(0, checked.returncode, checked.stderr or checked.stdout)
        self.assertEqual(2, json.loads(checked.stdout)['verifiedSources'])
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as game:
            game.bind((SERVER, port))
            busy_output = self.work / 'busy'
            with patch.object(quest_venue.quest_udp, 'probe_target', return_value=['adb', '-t', '41']), patch.object(
                    quest_venue.quest_udp, 'run_probe') as probes, redirect_stderr(io.StringIO()):
                busy = quest_venue.probe_venue(shell, self.work / 'adb-fixture.exe', mode, groups, busy_output, 2, 900)
            self.assertFalse(busy['complete'])
            self.assertEqual(['listener', 'listener'], [seat['stage'] for seat in busy['groups'][0]['seats']])
            probes.assert_not_called()
            self.assertEqual((SERVER, port), game.getsockname())

    @unittest.skipUnless(POWERSHELL, 'PowerShell is required for the Quest venue listener')
    def test_venue_retry_reuses_original_pairs_and_reprobes_changed_or_expired_evidence(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reservation:
            reservation.bind((SERVER, 0))
            port = reservation.getsockname()[1]
        shell = [POWERSHELL, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'RemoteSigned',
                 '-File', str(ROOT / 'scripts/check-lan-udp.ps1')]
        devices = [{'roomId': room, 'seat': 1, 'serial': f'fixture-{room}', 'address': f'127.0.0.{room + 1}'}
                   for room in range(1, 4)]
        groups = [{'roomIds': [1, 2, 3, 4, 5], 'address': SERVER, 'port': port, 'devices': devices}]
        launch, preview = write_guarded_launch(self.work, 'Linked', groups, 'retry')

        def java_probe(args, *, target):
            command = [*self.java, str(args.key_file), args.local_address, args.peer_address, str(args.port),
                       str(args.count), str(args.timeout_ms)]
            return json.loads(subprocess.run(command, capture_output=True, check=True, timeout=8).stdout)

        def run(name, retry_report=None, offline=None):
            output = self.work / name
            launcher, _ = quest_venue.launcher_proof(launch, preview, output)
            def target_device(_, serial):
                if serial == offline:
                    raise ValueError('Unavailable fixture seat')
                return ['adb', '-t', serial.rsplit('-', 1)[-1]]

            with patch.object(quest_venue.quest_udp, 'probe_target', side_effect=target_device), patch.object(
                    quest_venue.quest_udp, 'run_probe', side_effect=java_probe) as probes, redirect_stderr(io.StringIO()):
                report = quest_venue.probe_venue(shell, self.work / 'adb-fixture.exe', 'Linked', groups, output, 2, 900, retry_report, launcher=launcher)
            return report, [call.args[0].serial for call in probes.call_args_list]

        first, first_calls = run('first', offline='fixture-2')
        self.assertEqual(['fixture-1', 'fixture-3'], first_calls)
        self.assertFalse(first['complete'])
        self.assertEqual(2, first['verifiedSeats'])
        self.assertEqual(['verified', 'device', 'verified'], [seat['stage'] for seat in first['groups'][0]['seats']])
        original_dir = self.work / 'first'
        original = {path.name: path.read_bytes() for path in original_dir.iterdir()}
        original_report = original_dir / 'preflight-report.json'
        replaced_plan, replaced_preview = write_guarded_launch(self.work, 'Linked', groups, 'replaced')
        for path in (replaced_plan, replaced_preview):
            replacement = json.loads(path.read_bytes())
            replacement['servers'][0]['sessionId'] = '00000000-0000-4000-8000-000000000050'
            path.write_text(json.dumps(replacement), encoding='utf-8')
        rejected = self.work / 'rejected'
        other, _ = quest_venue.launcher_proof(replaced_plan, replaced_preview, rejected)
        with patch.object(quest_venue, 'probe_seat') as probe:
            with self.assertRaisesRegex(ValueError, 'original Windows launch plan and preview bytes'):
                quest_venue.probe_venue(shell, Path('adb'), 'Linked', groups, rejected, 2, 900, original_report, launcher=other)
            with self.assertRaisesRegex(ValueError, 'preserve the original Windows launch proof'):
                quest_venue.probe_venue(shell, Path('adb'), 'Linked', groups, rejected, 2, 900, original_report)
            probe.assert_not_called()
        self.assertFalse(rejected.exists())
        second, second_calls = run('retry', original_dir / 'preflight-report.json')
        self.assertTrue(second['complete'])
        self.assertEqual(['fixture-2'], second_calls)
        self.assertEqual(2, second['reusedSeats'])
        self.assertEqual(original, {path.name: path.read_bytes() for path in original_dir.iterdir()})
        retry_dir = self.work / 'retry'
        retained, _, changed = second['groups'][0]['seats']
        self.assertEqual(original_dir / 'room-01-seat-01-listener.ndjson', (retry_dir / retained['listener']).resolve())
        altered_probe = retry_dir / 'changed-probe.json'
        altered_probe.write_bytes((retry_dir / changed['probe']).read_bytes() + b'\n')
        changed['probe'] = altered_probe.name

        # Keep exact hashes for the synthetic expired input so the time guard is the reason it cannot be retained.
        old_listener = retry_dir / retained['listener']
        lines = old_listener.read_bytes().splitlines()
        terminal = json.loads(lines[-1])
        terminal['completedAtUtc'] = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()
        expired_listener = retry_dir / 'expired-listener.ndjson'
        expired_listener.write_bytes(lines[0] + b'\n' + json.dumps(terminal).encode() + b'\n')
        retained.update(listener=expired_listener.name, completedAtUtc=terminal['completedAtUtc'],
                        listenerSha256=hashlib.sha256(expired_listener.read_bytes()).hexdigest())
        modified_report = retry_dir / 'expired-report.json'
        modified_report.write_text(json.dumps(second), encoding='utf-8')
        third, third_calls = run('refresh', modified_report)
        self.assertTrue(third['complete'])
        self.assertEqual(1, third['reusedSeats'])
        self.assertEqual(['fixture-1', 'fixture-3'], third_calls)


class QuestUdpVenuePlanTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory(prefix='quest-udp-plan-test-')
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)
        self.device_map = self.root / 'devices.json'
        self.network_plan = self.root / 'network.json'
        self.devices = {'version': 1, 'seats': [
            {'roomId': room, 'seat': seat, 'serial': f'device-{room}-{seat}'}
            for room in range(5, 0, -1) for seat in range(5, 0, -1)]}
        self.network = {'version': 1, 'mode': 'Independent', 'endpoints': [
            {'roomIds': [room], 'address': '192.168.10.10', 'port': 7776 + room} for room in range(5, 0, -1)],
            'sources': [{'roomId': row['roomId'], 'seat': row['seat'], 'address': f"192.168.10.{20 + row['roomId'] * 5 + row['seat']}"}
                        for row in self.devices['seats']]}

    def plan(self):
        self.device_map.write_text(json.dumps(self.devices), encoding='utf-8-sig')
        self.network_plan.write_text(json.dumps(self.network), encoding='utf-8')
        return quest_venue.load_plan(self.device_map, self.network_plan)

    def test_list_retest_seats_reads_incomplete_venue_offline(self):
        self.plan()
        self.device_map.write_text(json.dumps({'version': 1, 'seats': self.devices['seats'][:1]}))
        inbox = self.root / 'first'
        inbox.mkdir()
        report = self.root / 'readiness.json'
        readiness = quest_venue.preflight.check_venue(self.network_plan, None, [], report, inbox=inbox)
        self.assertFalse(readiness['complete'])
        report.write_text(json.dumps(readiness))
        files = {path: path.read_bytes() for path in self.root.iterdir() if path.is_file()}
        result = subprocess.run([sys.executable, '-B', quest_venue.__file__, '--list-retest-seats',
            '--device-map', str(self.device_map), '--network-plan', str(self.network_plan), '--venue-retry-report', str(report)],
            cwd=inbox, capture_output=True, text=True, timeout=15)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'mode': 'Independent', 'pendingQuestSeats': [{'roomId': 5, 'seat': 5}],
                                                    'pendingOtherSeats': 24})
        self.assertEqual(files, {path: path.read_bytes() for path in self.root.rglob('*') if path.is_file()})

    def test_plan_sorts_all_25_seats_for_both_venue_modes_and_accepts_exact_partial_map(self):
        mode, groups = self.plan()
        self.assertEqual('Independent', mode)
        self.assertEqual([[1], [2], [3], [4], [5]], [group['roomIds'] for group in groups])
        self.assertEqual(list(range(7777, 7782)), [group['port'] for group in groups])
        self.assertEqual([5] * 5, [len(group['devices']) for group in groups])
        self.network.update(mode='Linked', endpoints=[{'roomIds': [1, 2, 3, 4, 5], 'address': '192.168.10.10', 'port': 7777}])
        mode, groups = self.plan()
        self.assertEqual('Linked', mode)
        self.assertEqual([(room, seat) for room in range(1, 6) for seat in range(1, 6)],
                         [(row['roomId'], row['seat']) for row in groups[0]['devices']])
        self.devices['seats'] = self.devices['seats'][:1]
        self.network['sources'] = self.network['sources'][:1]
        _, groups = self.plan()
        self.assertEqual([(5, 5)], [(row['roomId'], row['seat']) for row in groups[0]['devices']])

    def test_plan_rejects_missing_source_duplicate_ipv4_and_reused_binding(self):
        source = self.network['sources'].pop()
        with self.assertRaisesRegex(ValueError, 'mapped Quest seats exactly'):
            self.plan()
        self.network['sources'].append(source)
        address = source['address']
        source['address'] = self.network['sources'][0]['address']
        with self.assertRaisesRegex(ValueError, 'distinct IPv4'):
            self.plan()
        source['address'] = address
        self.network['endpoints'][1]['port'] = self.network['endpoints'][0]['port']
        with self.assertRaisesRegex(ValueError, 'binding is used'):
            self.plan()

    def test_quest_subset_report_stays_with_the_original_session_revision(self):
        self.devices['seats'] = self.devices['seats'][:1]
        full_sources = [{'roomId': room, 'seat': 5, 'address': f'192.168.10.{25 + room * 5}'} for room in range(1, 6)]
        self.network['sources'] = full_sources[-1:]

        def sample(shell, adb, directory, group, device, count, timeout_ms):
            completed = (datetime.now(timezone.utc) - timedelta(seconds=2)).isoformat()
            common = {'version': 1, 'scope': 'authenticated-udp-only', 'stage': 'finished', 'complete': True,
                      'port': group['port'], 'requested': count, 'matched': count, 'completedAtUtc': completed,
                      'exchangeSha256': 'a' * 64}
            listener, probe = directory / 'listener.json', directory / 'probe.json'
            listener.write_text(json.dumps(dict(common, mode='listen', localAddress=group['address'],
                                                peerAddress=device['address'], samples=[])), encoding='utf-8')
            probe.write_text(json.dumps(dict(common, mode='probe', localAddress=device['address'], peerAddress=group['address'],
                                             samples=[{'sample': 1, 'roundTripMs': 2}])), encoding='utf-8')
            metadata, _ = quest_venue.pair_metadata(listener, probe)
            return {'roomId': device['roomId'], 'seat': device['seat'], 'complete': True, 'stage': 'verified',
                    'listener': listener.name, 'probe': probe.name, 'exchangeSha256': common['exchangeSha256'], **metadata}

        for topology in ('Independent', 'Linked'):
            with self.subTest(mode=topology):
                if topology == 'Linked':
                    self.network.update(mode=topology, endpoints=[
                        {'roomIds': [1, 2, 3, 4, 5], 'address': '192.168.10.10', 'port': 7777}])
                for number, endpoint in enumerate(self.network['endpoints'], 1):
                    endpoint.update(sessionId=f'00000000-0000-4000-8000-{number:012}',
                                    missionId=f'00000000-0000-4000-8000-{100 + number:012}', sessionSequence=3)
                mode, groups = self.plan()
                original = self.root / f'{mode}-original'
                with patch.object(quest_venue, 'probe_seat', side_effect=sample), redirect_stderr(io.StringIO()):
                    batch = quest_venue.probe_venue([], Path('adb'), mode, groups, original, 1, 900)
                old_report = original / 'preflight-report.json'
                self.assertTrue(batch['complete'])
                target = next(endpoint for endpoint in self.network['endpoints'] if 5 in endpoint['roomIds'])
                fields = ('roomIds', 'sessionId', 'missionId', 'sessionSequence')
                self.assertEqual([{key: target[key] for key in fields}], batch['networkPlanSessions'])
                self.assertNotIn('device-5-5', old_report.read_text(encoding='utf-8'))
                retry = self.root / f'{mode}-retry'
                with patch.object(quest_venue, 'probe_seat', side_effect=AssertionError('Unexpected probe')) as unexpected, redirect_stderr(io.StringIO()):
                    reused = quest_venue.probe_venue([], Path('adb'), mode, groups, retry, 1, 900, old_report)
                self.assertEqual(1, reused['reusedSeats'])
                unexpected.assert_not_called()

                full = self.root / f'{mode}-full.json'
                full.write_text(json.dumps(dict(self.network, sources=full_sources)), encoding='utf-8')
                output = self.root / f'{mode}-merged.json'
                merged = quest_venue.preflight.check_venue(full, None, [old_report], output)
                self.assertEqual(1, merged['verifiedSources'])
                self.assertEqual(5, merged['expectedSources'])
                field = quest_venue.field
                venue_network = field.read_venue_network_plan(full, mode, 1)
                expected_rooms = [row['roomIds'] for row in self.network['endpoints']]
                expected_sessions = {tuple(row['roomIds']): row['sessionId'] for row in self.network['endpoints']}
                pairs, binding = field.read_udp_preflight_batch(old_report, mode, expected_rooms,
                    expected_sessions=expected_sessions, venue_network=venue_network)
                self.assertEqual({tuple(target['roomIds'])}, pairs.keys())
                self.assertIsNone(binding)

                malformed = dict(batch, networkPlanSessions=[])
                malformed_report = self.root / f'{mode}-malformed.json'
                malformed_report.write_text(json.dumps(malformed), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'Invalid UDP report launch sessions'):
                    quest_venue.preflight.check_venue(full, None, [malformed_report], output)

                target['sessionSequence'] += 1
                _, replacement = self.plan()
                refused = self.root / f'{mode}-refused'
                with patch.object(quest_venue, 'probe_seat', side_effect=AssertionError('Unexpected probe')) as unexpected, redirect_stderr(io.StringIO()):
                    with self.assertRaisesRegex(ValueError, 'original Quest plan'):
                        quest_venue.probe_venue([], Path('adb'), mode, replacement, refused, 1, 900, old_report)
                unexpected.assert_not_called()
                self.assertFalse(refused.exists())

                full.write_text(json.dumps(dict(self.network, sources=full_sources)), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'launch sessions differ from the original network plan'):
                    quest_venue.preflight.check_venue(full, None, [old_report], output)
                new_network = field.read_venue_network_plan(full, mode, 1)
                with self.assertRaisesRegex(ValueError, 'launch sessions differ from the original network plan'):
                    field.read_udp_preflight_batch(old_report, mode, expected_rooms, expected_sessions=expected_sessions,
                                                   venue_network=new_network)

    def test_cli_rejects_unused_room_binding_before_touching_adb_or_output(self):
        launch, preview = write_guarded_launch(self.root, 'Independent', self.network['endpoints'], 'original')
        self.devices['seats'] = self.devices['seats'][-1:]
        self.network['sources'] = self.network['sources'][-1:]
        self.network['endpoints'][0]['port'] = 9999
        self.plan()
        output = self.root / 'no-output'
        command = [sys.executable, str(ROOT / 'scripts/probe-quest-venue.py'), '--adb', str(self.root / 'absent-adb.exe'),
                   '--device-map', str(self.device_map), '--network-plan', str(self.network_plan),
                   '--launch-plan', str(launch), '--launcher-preview', str(preview), '--output-directory', str(output)]
        rejected = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(1, rejected.returncode)
        self.assertIn('Windows endpoint for room(s) 5 (port-mismatch)', rejected.stderr)
        self.assertEqual('', rejected.stdout)
        self.assertFalse(output.exists())

    def test_legacy_quest_retry_can_use_its_original_windows_launch_proof(self):
        self.devices['seats'] = self.devices['seats'][:1]
        self.network['sources'] = self.network['sources'][:1]
        mode, groups = self.plan()
        launch, preview = write_guarded_launch(self.root, mode, self.network['endpoints'], 'original')
        original = self.root / 'legacy'
        launcher, _ = quest_venue.launcher_proof(launch, preview, original)
        failed_seat = {'roomId': 5, 'seat': 5, 'stage': 'device', 'complete': False}
        with patch.object(quest_venue, 'probe_seat', return_value=failed_seat), redirect_stderr(io.StringIO()):
            old = quest_venue.probe_venue([], Path('adb'), mode, groups, original, 1, 900, launcher=launcher)
        self.assertNotIn('networkPlanSessions', old)

        stamps = quest_venue.field.read_udp_launcher_document(launch, preview=False)[2]
        for row in self.network['endpoints']:
            original_session = stamps[tuple(row['roomIds'])]
            row.update({key: original_session[key] for key in ('sessionId', 'missionId', 'sessionSequence')})
        _, current_groups = self.plan()
        retry = self.root / 'migrated'
        launcher, _ = quest_venue.launcher_proof(launch, preview, retry)
        with patch.object(quest_venue, 'probe_seat', return_value=failed_seat) as probe, redirect_stderr(io.StringIO()):
            migrated = quest_venue.probe_venue([], Path('adb'), mode, current_groups, retry, 1, 900,
                                               original / 'preflight-report.json', launcher=launcher)
        probe.assert_called_once()
        self.assertEqual([5], migrated['networkPlanSessions'][0]['roomIds'])
        self.assertNotEqual(old['planSha256'], migrated['planSha256'])

    def test_failed_seat_and_duplicate_exchange_do_not_claim_complete_group(self):
        mode, groups = self.plan()
        output = self.root / 'batch'

        def seat(shell, adb, directory, group, device, count, timeout_ms):
            room, number = device['roomId'], device['seat']
            result = {'roomId': room, 'seat': number, 'stage': 'device', 'complete': False}
            if (room, number) != (1, 2):
                exchange = 'shared' if (room, number) in ((1, 1), (1, 3)) else f'{room}-{number}'
                result.update(stage='verified', complete=True, exchangeSha256=exchange, listener='listener.ndjson', probe='probe.json',
                              completedAtUtc=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat())
            return result

        with patch.object(quest_venue, 'probe_seat', side_effect=seat) as checked, redirect_stderr(io.StringIO()) as diagnostics:
            summary = quest_venue.probe_venue([], Path('adb'), mode, groups, output, 3, 900)
        self.assertEqual(25, checked.call_count)
        self.assertEqual(23, summary['verifiedSeats'])
        self.assertFalse(summary['complete'])
        self.assertEqual(['verified', 'device', 'duplicate'], [row['stage'] for row in summary['groups'][0]['seats'][:3]])
        self.assertNotIn('udpSourcePreflights', summary['groups'][0])
        self.assertTrue(all(len(group['udpSourcePreflights']) == 5 for group in summary['groups'][1:]))
        self.assertNotIn('device-1-2', diagnostics.getvalue())
        with self.assertRaises(FileExistsError):
            quest_venue.probe_venue([], Path('adb'), mode, groups, output, 3, 900)

    def test_venue_interrupt_saves_partial_batch_and_rejects_changed_retry_map(self):
        self.network.update(mode='Linked', endpoints=[{'roomIds': [1, 2, 3, 4, 5], 'address': '192.168.10.10', 'port': 7777}])
        mode, groups = self.plan()
        output = self.root / 'interrupted'
        first = {'roomId': 1, 'seat': 1, 'complete': True, 'stage': 'verified', 'exchangeSha256': 'a' * 64,
                 'listener': 'listener.ndjson', 'probe': 'probe.json',
                 'completedAtUtc': (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()}
        with patch.object(quest_venue, 'probe_seat', side_effect=[first, KeyboardInterrupt]) as probe, redirect_stderr(io.StringIO()):
            result = quest_venue.probe_venue([], Path('adb'), mode, groups, output, 3, 900)
        self.assertEqual(2, probe.call_count)
        self.assertTrue(result['interrupted'])
        self.assertFalse(result['complete'])
        self.assertEqual(1, result['verifiedSeats'])
        self.assertEqual(['verified', 'interrupted'] + ['not-attempted'] * 23,
                         [row['stage'] for row in result['groups'][0]['seats']])
        self.assertEqual(result, json.loads((output / 'preflight-report.json').read_bytes()))
        retry = self.root / 'retry'
        groups[0]['devices'][0]['serial'] = 'replacement'
        with self.assertRaisesRegex(ValueError, 'original Quest plan and sample count'):
            quest_venue.probe_venue([], Path('adb'), mode, groups, retry, 3, 900, output / 'preflight-report.json')
        self.assertFalse(retry.exists())

    def test_independent_rooms_probe_together_without_overlapping_seats_on_a_port(self):
        mode, groups = self.plan()
        output = self.root / 'parallel'
        start = Barrier(5, timeout=5)
        active, order = set(), {group['port']: [] for group in groups}
        lock = Lock()

        def probe(shell, adb, directory, group, device, count, timeout_ms):
            port, seat = group['port'], device['seat']
            with lock:
                self.assertNotIn(port, active)
                active.add(port)
                order[port].append(seat)
            if seat == 1:
                start.wait()
            with lock:
                active.remove(port)
            return {**{key: device[key] for key in ('roomId', 'seat')}, 'complete': True, 'stage': 'verified',
                    'exchangeSha256': f'{port}-{seat}', 'listener': 'listener.ndjson', 'probe': 'probe.json',
                    'completedAtUtc': (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()}

        with patch.object(quest_venue, 'probe_seat', side_effect=probe), redirect_stderr(io.StringIO()) as diagnostics:
            report = quest_venue.probe_venue([], Path('adb'), mode, groups, output, 3, 900)
        self.assertEqual([[1, 2, 3, 4, 5]] * 5, list(order.values()))
        self.assertEqual((True, 25), (report['complete'], report['verifiedSeats']))
        self.assertEqual([[room] for room in range(1, 6)], [group['roomIds'] for group in report['groups']])
        self.assertEqual(report, json.loads((output / 'preflight-report.json').read_bytes()))
        rows = [json.loads(line) for line in diagnostics.getvalue().splitlines()]
        self.assertEqual([(room, seat) for room in range(1, 6) for seat in range(1, 6)],
                         sorted((row['roomId'], row['seat']) for row in rows))

    def test_independent_interrupt_drains_each_active_port_before_saving(self):
        mode, groups = self.plan()
        output = self.root / 'parallel-interrupt'
        start, drained = Barrier(6, timeout=5), []
        stopped = Event()

        def interrupt(*args, **kwargs):
            start.wait()
            raise KeyboardInterrupt

        def probe(shell, adb, directory, group, device, count, timeout_ms):
            room, seat = device['roomId'], device['seat']
            self.assertEqual(1, seat)
            start.wait()
            self.assertTrue(stopped.wait(5))
            self.assertFalse((output / 'preflight-report.json').exists())
            drained.append(room)
            return {'roomId': room, 'seat': seat, 'complete': True, 'stage': 'verified', 'exchangeSha256': f'{room}-{seat}',
                    'listener': 'listener.ndjson', 'probe': 'probe.json',
                    'completedAtUtc': (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()}

        with (patch.object(quest_venue, 'Event', return_value=stopped), patch.object(quest_venue, 'wait', side_effect=interrupt),
              patch.object(quest_venue, 'probe_seat', side_effect=probe) as probes, redirect_stderr(io.StringIO())):
            report = quest_venue.probe_venue([], Path('adb'), mode, groups, output, 3, 900)
        self.assertEqual([1, 2, 3, 4, 5], sorted(drained))
        self.assertEqual(5, probes.call_count)
        self.assertEqual((True, False, 5), (report['interrupted'], report['complete'], report['verifiedSeats']))
        self.assertTrue(all(group['seats'][0]['stage'] == 'verified' for group in report['groups']))
        self.assertTrue(all(seat['stage'] == 'not-attempted' for group in report['groups'] for seat in group['seats'][1:]))
        self.assertEqual(report, json.loads((output / 'preflight-report.json').read_bytes()))

    def test_venue_retry_rejects_changed_or_missing_sample_timeout_before_probe(self):
        mode, groups = self.plan()
        output = self.root / 'original'
        with patch.object(quest_venue, 'probe_seat', side_effect=KeyboardInterrupt), redirect_stderr(io.StringIO()):
            original = quest_venue.probe_venue([], Path('adb'), mode, groups, output, 3, 900)
        original_path = output / 'preflight-report.json'
        original_bytes = original_path.read_bytes()

        legacy_path = output / 'legacy.json'
        legacy = {key: value for key, value in original.items() if key != 'sampleTimeoutMs'}
        legacy_path.write_text(json.dumps(legacy), encoding='utf-8')
        for label, timeout, source in (('shorter-timeout', 200, original_path), ('legacy-report', 900, legacy_path)):
            with self.subTest(label=label):
                retry = self.root / label
                with patch.object(quest_venue, 'probe_seat', side_effect=KeyboardInterrupt) as probe, \
                        redirect_stderr(io.StringIO()):
                    with self.assertRaisesRegex(ValueError, 'recorded Quest sample timeout'):
                        quest_venue.probe_venue([], Path('adb'), mode, groups, retry, 3, timeout, source)
                    probe.assert_not_called()
                self.assertFalse(retry.exists())
        self.assertEqual(original_bytes, original_path.read_bytes())

    @unittest.skipUnless(POWERSHELL, 'PowerShell is required for the original UDP listener and probe')
    def test_venue_retry_reprobes_an_original_sample_outside_the_recorded_timeout(self):
        from windows_firewall import WindowsFirewallLaunchError, require_silent_windows_launch

        try:
            require_silent_windows_launch(sys.executable)
            require_silent_windows_launch(POWERSHELL)
        except WindowsFirewallLaunchError as error:
            self.skipTest(str(error))
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reservation:
            reservation.bind((SERVER, 0))
            port = reservation.getsockname()[1]
        shell = [POWERSHELL, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'RemoteSigned',
                 '-File', str(ROOT / 'scripts/check-lan-udp.ps1')]
        rooms = list(range(1, 6))
        groups = [{'roomIds': rooms, 'address': SERVER, 'port': port, 'devices': [
            {'roomId': room, 'seat': 1, 'serial': f'fixture-{room}', 'address': f'127.0.0.{room + 1}'}
            for room in (1, 2)]}]

        def local_probe(args, *, target):
            command = [*shell, '-Mode', 'Probe', '-KeyFile', str(args.key_file), '-LocalAddress', args.local_address,
                       '-PeerAddress', args.peer_address, '-Port', str(args.port), '-Count', str(args.count),
                       '-TimeoutMs', str(args.timeout_ms)]
            result = subprocess.run(command, capture_output=True, check=True, timeout=10,
                                    creationflags=quest_venue.CREATE_NO_WINDOW)
            return json.loads(result.stdout)

        original = self.root / 'original-exchanges'
        retry = self.root / 'retry-exchanges'
        with patch.object(quest_venue.quest_udp, 'probe_target', return_value=['adb', '-t', '41']), patch.object(
                quest_venue.quest_udp, 'run_probe', side_effect=local_probe) as probes, redirect_stderr(io.StringIO()):
            first = quest_venue.probe_venue(shell, Path('adb'), 'Linked', groups, original, 2, 900)
            self.assertTrue(first['complete'])
            self.assertEqual(900, first['sampleTimeoutMs'])
            raw_files = {path.name: path.read_bytes() for path in original.iterdir()}
            slow, retained = first['groups'][0]['seats']
            probe_data = json.loads(raw_files[slow['probe']])
            probe_data['samples'][0]['roundTripMs'] = 901
            slow_probe = original / 'slow-probe.json'
            slow_probe.write_text(json.dumps(probe_data), encoding='utf-8')
            slow.update(probe=slow_probe.name, probeSha256=hashlib.sha256(slow_probe.read_bytes()).hexdigest())
            source = original / 'slow-batch.json'
            source.write_text(json.dumps(first), encoding='utf-8')
            probes.reset_mock()
            second = quest_venue.probe_venue(shell, Path('adb'), 'Linked', groups, retry, 2, 900, source)
            self.assertEqual(['fixture-1'], [call.args[0].serial for call in probes.call_args_list])

        self.assertTrue(second['complete'])
        self.assertEqual((900, 1), (second['sampleTimeoutMs'], second['reusedSeats']))
        self.assertEqual(['verified', 'reused'], [row['stage'] for row in second['groups'][0]['seats']])
        self.assertEqual(retained['exchangeSha256'], second['groups'][0]['seats'][1]['exchangeSha256'])
        for name, raw in raw_files.items():
            self.assertEqual(raw, (original / name).read_bytes())


class QuestUdpAdbTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory(prefix='quest-udp-adb-test-')
        self.addCleanup(work.cleanup)
        root = Path(work.name)
        adb, key = root / 'adb.exe', root / 'probe.key'
        adb.touch()
        self.key = base64.b64encode(bytes(range(32)))
        key.write_bytes(self.key)
        self.args = SimpleNamespace(adb=adb, key_file=key, serial='probe-device', local_address=PEER, peer_address=SERVER,
                                    port=7777, count=1, timeout_ms=900)
        self.report = {'version': 1, 'stage': 'finished', 'mode': 'probe', 'localAddress': PEER, 'peerAddress': SERVER,
                       'port': 7777, 'requested': 1, 'matched': 1, 'samples': [{'sample': 1, 'roundTripMs': 2.3}],
                       'exchangeSha256': 'a' * 64, 'complete': True, 'scope': 'authenticated-udp-only',
                       'completedAtUtc': '2026-11-10T00:00:00Z'}

    @staticmethod
    def result(text=b''):
        return subprocess.CompletedProcess([], 0, text, b'')

    def output(self):
        return (quest_udp.PREFIX + json.dumps(self.report) + '\r\nINSTRUMENTATION_CODE: -1\r\n').encode()

    def inventory(self):
        return self.result(b'List of devices attached\r\nprobe-device device transport_id:41\r\n')

    def test_rebound_serial_cannot_continue_or_clean_up_an_original_probe(self):
        phases = []
        rebound = False

        def adb_call(command, **kwargs):
            nonlocal rebound
            if command[1:] == ['devices', '-l']:
                return self.inventory()
            target = command[1:3]
            phase = 'transfer' if kwargs['input'] is not None else 'instrument' if 'instrument' in command else 'cleanup'
            phases.append((phase, target))
            if phase == 'transfer':
                self.assertEqual(self.key, kwargs['input'])
                rebound = True
                return self.result()
            self.assertTrue(rebound)
            # The same serial is now routed to a replacement, which would report success.
            if target == ['-s', 'probe-device']:
                return self.result(self.output() if phase == 'instrument' else b'')
            return subprocess.CompletedProcess(command, 1, b'', b'no device with transport id 41')

        with patch.object(quest_udp.subprocess, 'run', side_effect=adb_call):
            with self.assertRaisesRegex(ValueError, 'ADB could not run the Quest probe'):
                quest_udp.run_probe(self.args)
        self.assertEqual([(phase, ['-t', '41']) for phase in ('transfer', 'instrument', 'cleanup')], phases)

    def test_adb_key_is_sent_only_on_private_stdin_and_cleaned(self):
        with patch.object(quest_udp.subprocess, 'run',
                          side_effect=[self.inventory(), self.result(), self.result(self.output()), self.result()]) as calls:
            self.assertEqual(self.report, quest_udp.run_probe(self.args))
        inventory, transfer, probe, cleanup = calls.call_args_list
        self.assertEqual(['devices', '-l'], inventory.args[0][1:])
        self.assertEqual(self.key, transfer.kwargs['input'])
        self.assertIsNone(probe.kwargs['input'])
        self.assertIsNone(cleanup.kwargs['input'])
        self.assertNotIn(self.key.decode(), repr([call.args for call in calls.call_args_list]))
        for call in (transfer, probe, cleanup):
            self.assertEqual(['-t', '41'], call.args[0][1:3])
        key_path = cleanup.args[0][-1]
        self.assertRegex(key_path, r'\Afiles/udp-[0-9a-f]{32}\.key\Z')
        self.assertIn(key_path, transfer.args[0][-1])
        self.assertIn(Path(key_path).name, probe.args[0])

    def test_bad_report_is_rejected_and_private_file_is_cleaned(self):
        self.report['peerAddress'] = '127.0.0.3'
        with patch.object(quest_udp.subprocess, 'run',
                          side_effect=[self.inventory(), self.result(), self.result(self.output()), self.result()]) as calls:
            with self.assertRaisesRegex(ValueError, 'requested probe'):
                quest_udp.run_probe(self.args)
        self.assertEqual(4, calls.call_count)
        self.assertIn('rm', calls.call_args.args[0])
        self.report['peerAddress'] = SERVER
        self.report.update(matched=0, complete=False, exchangeSha256=None, samples=[{'sample': 1, 'roundTripMs': None}])
        self.assertFalse(quest_udp.android_report(self.output(), self.args)['complete'])

    def test_disconnect_after_android_completion_prevents_publishing_success(self):
        rejected = subprocess.CompletedProcess([], 1, b'', b'no device with transport id 41')
        with patch.object(quest_udp.subprocess, 'run', side_effect=[
            self.inventory(), self.result(), self.result(self.output()), rejected
        ]) as calls, self.assertRaisesRegex(ValueError, 'ADB could not run the Quest probe'):
            quest_udp.run_probe(self.args)
        self.assertEqual(['-t', '41', 'shell', 'run-as', quest_udp.PACKAGE, 'rm', '-f'],
                         calls.call_args.args[0][1:-1])
