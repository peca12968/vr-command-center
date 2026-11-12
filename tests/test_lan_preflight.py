import base64
from contextlib import contextmanager
from datetime import datetime, timedelta
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
SHELL = shutil.which(os.environ.get('VR_COMMAND_POWERSHELL', 'powershell.exe' if os.name == 'nt' else 'pwsh'))
LOOPBACK = '127.0.0.1'
PLAN_SCRIPT = ROOT / 'scripts/prepare-venue-network-plan.py'


def guarded_documents(mode, ports, address=LOOPBACK, listen=None):
    groups = [list(range(1, 6))] if mode == 'Linked' else [[room] for room in range(1, 6)]
    rows = [{'roomIds': group, 'sessionId': f'00000000-0000-4000-8000-{index:012}',
             'missionId': f'00000000-0000-4000-8000-{index + 10:012}', 'sessionSequence': index + 2, 'port': port}
            for index, (group, port) in enumerate(zip(groups, ports, strict=True), 1)]
    binding = {'address': address, 'listenAddress': listen if listen is not None else address}
    return ({'version': 4, 'topology': mode, 'controlInstance': 'fixture/control-instance.json', **binding, 'servers': rows},
            {'schemaVersion': 1, 'status': 'venue-checked', 'complete': True, 'topology': mode,
             'servers': [{**row, **binding} for row in rows]})


def prepare_network(launch, preview, seats, output, *options):
    return subprocess.run([sys.executable, str(PLAN_SCRIPT), '--launch-plan', str(launch), '--launcher-preview', str(preview),
                           '--seat-addresses', str(seats), '--output', str(output), *map(str, options)],
                          capture_output=True, text=True, timeout=15)


class NetworkPlanPreparationTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix='venue-network-plan-')
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)

    def store(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    def test_prepare_both_topologies_and_a_quest_subset_consumed_by_the_original_probe(self):
        spec = importlib.util.spec_from_file_location('quest_venue_probe', ROOT / 'scripts/probe-quest-venue.py')
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        rows = [{'roomId': room, 'seat': seat, 'address': f'192.168.5.{20 + room if seat == 2 else 15}'}
                for room in range(1, 6) for seat in (1, 2)]
        seats = self.store('seats.json', {'version': 1, 'seats': rows[::-1]})
        devices = self.store('devices.json', {'version': 1, 'seats': [
            {'roomId': 5, 'seat': 2, 'serial': 'fixture-late'}, {'roomId': 1, 'seat': 2, 'serial': 'fixture-first'}]})
        for mode, ports in (('Independent', range(7777, 7782)), ('Linked', [7777])):
            with self.subTest(mode=mode):
                launch_value, preview_value = guarded_documents(mode, ports, '192.168.5.10')
                launch_value['servers'].reverse()
                launch, preview = (self.store(name, value) for name, value in (('launch.json', launch_value), ('preview.json', preview_value)))
                before = {path: path.read_bytes() for path in (launch, preview, seats, devices)}
                output = self.root / f'{mode}-all.json'
                prepared = prepare_network(launch, preview, seats, output, '--players-per-room', 2)
                self.assertEqual(0, prepared.returncode, prepared.stderr)
                plan = json.loads(output.read_bytes())
                self.assertEqual({'version', 'mode', 'endpoints', 'sources'}, plan.keys())
                self.assertEqual(rows, plan['sources'])
                self.assertEqual([{'roomIds': row['roomIds'], 'address': '192.168.5.10', 'port': row['port']}
                                  for row in preview_value['servers']], plan['endpoints'])
                self.assertEqual({'prepared': True, 'mode': mode, 'plannedSeats': 10, 'includedSeats': 10,
                                  'endpointCount': len(ports), 'planSha256': hashlib.sha256(before[launch]).hexdigest(),
                                  'previewSha256': hashlib.sha256(before[preview]).hexdigest()}, json.loads(prepared.stdout))
                quest = self.root / f'{mode}-quest.json'
                prepared = prepare_network(launch, preview, seats, quest, '--players-per-room', 2, '--quest-device-map', devices)
                self.assertEqual(0, prepared.returncode, prepared.stderr)
                self.assertEqual(2, json.loads(prepared.stdout)['includedSeats'])
                self.assertEqual(plan['endpoints'], json.loads(quest.read_bytes())['endpoints'])
                self.assertNotIn('fixture-', prepared.stdout + quest.read_text(encoding='utf-8'))
                self.assertNotIn('192.168.', prepared.stdout)
                original_mode, groups = probe.load_plan(devices, quest)
                self.assertEqual(mode, original_mode)
                self.assertEqual([(1, 2, '192.168.5.21'), (5, 2, '192.168.5.25')], [
                    (device['roomId'], device['seat'], device['address']) for group in groups for device in group['devices']])
                self.assertEqual(before, {path: path.read_bytes() for path in before})
                previous = quest.read_bytes()
                refused = prepare_network(launch, preview, seats, quest, '--players-per-room', 2)
                self.assertEqual(1, refused.returncode)
                self.assertEqual(previous, quest.read_bytes())

    def test_rejects_mismatches_in_plan_preview_and_seat_inventory_before_output(self):
        launch_value, preview_value = guarded_documents('Independent', range(7777, 7782))
        seats_value = {'version': 1, 'seats': [{'roomId': room, 'seat': 1, 'address': '127.0.0.2'} for room in range(1, 6)]}
        launch = self.store('launch.json', launch_value)
        preview = self.store('preview.json', preview_value)
        seats = self.store('seats.json', seats_value)
        output = self.root / 'refused.json'

        def rejects(message, *options):
            result = prepare_network(launch, preview, seats, output, '--players-per-room', 1, *options)
            self.assertEqual(1, result.returncode, result.stderr)
            self.assertIn(message, result.stderr)
            self.assertFalse(output.exists())

        for key, value, message in (('sessionId', '00000000-0000-4000-8000-000000000099', 'session-mismatch'),
                                    ('missionId', '00000000-0000-4000-8000-000000000099', 'mission-mismatch'),
                                    ('sessionSequence', 25, 'session-sequence-mismatch'),
                                    ('port', 9000, 'port-mismatch')):
            with self.subTest(key=key):
                self.store(preview.name, {**preview_value, 'servers': [*preview_value['servers'][:4], {**preview_value['servers'][4], key: value}]})
                rejects(f'Room(s) 5 differ between the launch plan and preview ({message})')
        _, wrong_mode = guarded_documents('Linked', [7777])
        self.store(preview.name, wrong_mode)
        rejects('different venue modes')
        wildcard_launch, wildcard_preview = guarded_documents('Independent', range(7777, 7782), listen='0.0.0.0')
        self.store(launch.name, wildcard_launch)
        self.store(preview.name, wildcard_preview)
        rejects('one concrete advertised and listening IPv4 address')
        self.store(launch.name, launch_value)
        self.store(preview.name, preview_value)
        self.store(seats.name, {'version': 1, 'seats': seats_value['seats'][:-1]})
        rejects('requested stage in room(s) 5')
        self.store(seats.name, {'version': 1, 'seats': [{**seats_value['seats'][0], 'address': '192.168.5.20'}, *seats_value['seats'][1:]]})
        rejects('only loopback or only private LAN')
        self.store(seats.name, seats_value)
        devices = self.store('devices.json', {'version': 1, 'seats': [{'roomId': 1, 'seat': 2, 'serial': 'fixture-a'}]})
        rejects('room 1 seat 2', '--quest-device-map', devices)
        self.store(devices.name, {'version': 1, 'seats': [
            {'roomId': 1, 'seat': 1, 'serial': 'fixture-a'}, {'roomId': 5, 'seat': 1, 'serial': 'fixture-b'}]})
        rejects('distinct IPv4 for each mapped Quest', '--quest-device-map', devices)


def packet(key, kind, nonce):
    prefix = f'VRLAN1{kind}:{nonce}'.encode('ascii')
    return prefix + b':' + hmac.new(key, prefix, hashlib.sha256).hexdigest().encode('ascii')


@unittest.skipUnless(SHELL, 'PowerShell is required for native UDP preflight checks')
class LanPreflightTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix='lan-preflight-')
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.key = self.root / 'probe.key'
        self.shell = [SHELL, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'RemoteSigned',
                      '-File', str(ROOT / 'scripts/check-lan-udp.ps1')]
        result = self.run_script('-NewKey', '-KeyFile', self.key)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'version': 1, 'stage': 'key-created'})

    def run_script(self, *args):
        return subprocess.run([*self.shell, *map(str, args)], capture_output=True, text=True, timeout=15)

    def options(self, port, count, *, key=None, peer=LOOPBACK, local=LOOPBACK):
        return ['-LocalAddress', local, '-PeerAddress', peer, '-Port', str(port), '-Count', str(count),
                '-KeyFile', str(key or self.key)]

    @contextmanager
    def listener(self, port, count, *, peer=LOOPBACK, seconds=10, filename='listener.ndjson'):
        path = self.root / filename
        with path.open('xb') as output:
            with subprocess.Popen(self.shell + ['-Mode', 'Listen', '-Seconds', str(seconds), *self.options(port, count, peer=peer)],
                                  stdout=output, stderr=subprocess.STDOUT) as process:
                try:
                    end = time.monotonic() + 8
                    while time.monotonic() < end:
                        log = path.read_text(encoding='utf-8')
                        if '\n' in log:
                            ready = json.loads(log.splitlines()[0])
                            self.assertEqual(ready, {'version': 1, 'stage': 'listening', 'localAddress': LOOPBACK,
                                                     'peerAddress': peer, 'port': port})
                            break
                        if process.poll() is not None:
                            self.fail(log)
                        time.sleep(.04)
                    else:
                        self.fail('Listener did not report its bound socket')
                    yield process, path
                finally:
                    if process.poll() is None:
                        process.kill()

    def venue_pair(self, port, peer, label, *, encoding='utf-8'):
        with self.listener(port, 2, peer=peer, filename=f'{label}-listener.ndjson') as (listener, path):
            result = self.run_script('-Mode', 'Probe', *self.options(port, 2, local=peer))
            self.assertEqual(0, result.returncode, result.stderr or result.stdout)
            self.assertEqual(0, listener.wait(timeout=5))
        probe = self.root / f'{label}-probe.json'
        probe.write_text(result.stdout, encoding=encoding)
        return {'listener': path.name, 'probe': probe.name}

    def venue_json(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    def venue_check(self, plan, output, *inputs, status=0):
        report = self.root / output
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/check-venue-udp-preflight.py'),
                                 '--network-plan', str(plan), '--output', str(report), *map(str, inputs)],
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(status, result.returncode, result.stderr or result.stdout)
        self.assertNotIn(LOOPBACK, result.stdout + result.stderr)
        self.assertNotIn(str(self.root), result.stdout + result.stderr)
        return json.loads(report.read_text(encoding='utf-8'))

    def test_venue_linked_shared_sources_and_original_batch(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserved:
            reserved.bind((LOOPBACK, 0))
            port = reserved.getsockname()[1]
        rooms = list(range(1, 6))
        plan = self.venue_json('plan.json', {'version': 1, 'mode': 'Linked',
            'endpoints': [{'roomIds': rooms, 'address': LOOPBACK, 'port': port}],
            'sources': [{'roomId': room, 'seat': seat, 'address': f'127.0.0.{2 if seat <= 3 else 3}'}
                        for room in rooms for seat in rooms]})
        first = self.venue_pair(port, '127.0.0.2', 'first', encoding='utf-16')
        second = self.venue_pair(port, '127.0.0.3', 'second', encoding='utf-8-sig')
        original_reports = {name: (self.root / name).read_bytes() for name in (*first.values(), *second.values())}
        manual = self.venue_json('pairs.json', {'version': 1, 'pairs': [first]})
        batch = self.venue_json('batch.json', {'version': 1, 'scope': 'quest-udp-preflight-only',
            'mode': 'Linked', 'complete': True,
            'groups': [{'roomIds': rooms, 'complete': True, 'udpSourcePreflights': [second]}]})
        report = self.venue_check(plan, 'readiness.json', '--pairs', manual, '--batch', batch)
        self.assertEqual(hashlib.sha256(plan.read_bytes()).hexdigest(), report['networkPlanSha256'])
        self.assertEqual(('same-host', 2, 2), (report['network'], report['expectedSources'], report['verifiedSources']))
        group, = report['groups']
        self.assertTrue(report['complete'])
        self.assertEqual([15, 10], [len(row['seats']) for row in group['sources']])
        self.assertEqual([first, second], group['udpSourcePreflights'])
        copied = self.venue_check(plan, 'copied.json', '--batch', self.root / 'readiness.json')
        self.assertEqual(group, copied['groups'][0])

        launch_row = {'roomIds': rooms, 'sessionId': '5bc170f1-5b9b-4da4-bc94-9c51e464431b', 'port': port,
                      'address': LOOPBACK, 'listenAddress': LOOPBACK}
        launch = {'schemaVersion': 1, 'status': 'venue-checked', 'complete': True, 'topology': 'Linked', 'servers': [launch_row]}
        preview = self.venue_json('preview.json', launch)
        accepted = self.venue_check(plan, 'with-preview.json', '--batch', self.root / 'readiness.json', '--launcher-preview', preview)
        self.assertEqual({'sha256': hashlib.sha256(preview.read_bytes()).hexdigest(), 'complete': True,
                          'topologyMatches': True, 'groups': [{'roomIds': rooms, 'issues': []}]}, accepted['launcherPreview'])
        guarded = {**launch_row, 'missionId': '00000000-0000-4000-8000-000000000071', 'sessionSequence': 7}
        original = self.venue_json('guarded-plan.json', {'version': 4, 'topology': 'Linked', 'controlInstance': 'fixture/control-instance.json',
            'address': LOOPBACK, 'listenAddress': LOOPBACK,
            'servers': [{key: value for key, value in guarded.items() if key not in ('address', 'listenAddress')}]})
        guarded_preview = self.venue_json('guarded-preview.json', {**launch, 'servers': [guarded]})
        inventory = self.venue_json('seat-addresses.json', {'version': 1, 'seats': json.loads(plan.read_bytes())['sources']})
        generated = self.root / 'prepared-network.json'
        prepared = prepare_network(original, guarded_preview, inventory, generated)
        self.assertEqual(0, prepared.returncode, prepared.stderr)
        self.assertEqual(json.loads(plan.read_bytes()), json.loads(generated.read_bytes()))
        bound = self.venue_check(generated, 'bound.json', '--batch', self.root / 'readiness.json',
                                 '--launcher-preview', guarded_preview, '--launch-plan', original)
        self.assertEqual({'plan': original.name, 'preview': guarded_preview.name, 'complete': True, 'mode': 'Linked',
                          'planSha256': hashlib.sha256(original.read_bytes()).hexdigest(),
                          'previewSha256': hashlib.sha256(guarded_preview.read_bytes()).hexdigest(),
                          'groups': [{'roomIds': rooms, 'issues': []}]}, bound['launchBinding'])
        again = self.venue_check(plan, 'rechecked.json', '--batch', self.root / 'bound.json',
                                 '--launcher-preview', guarded_preview, '--launch-plan', original)
        self.assertEqual(bound['launchBinding'], again['launchBinding'])
        outdated = self.venue_json('outdated-preview.json', {**launch, 'servers': [dict(guarded,
            sessionId='00000000-0000-4000-8000-000000000072', missionId='00000000-0000-4000-8000-000000000073', sessionSequence=6)]})
        refused = self.venue_check(plan, 'outdated.json', '--batch', self.root / 'readiness.json',
                                   '--launcher-preview', outdated, '--launch-plan', original, status=1)
        self.assertTrue(refused['launcherPreview']['complete'])
        self.assertEqual(2, refused['verifiedSources'])
        self.assertEqual(['session-mismatch', 'mission-mismatch', 'session-sequence-mismatch'], refused['launchBinding']['groups'][0]['issues'])
        launch_row.update(address='127.0.0.3', listenAddress='0.0.0.0')
        different = self.venue_json('different-preview.json', launch)
        mismatched = self.venue_check(plan, 'mismatched.json', '--batch', self.root / 'readiness.json',
                                      '--launcher-preview', different, status=1)
        self.assertEqual(2, mismatched['verifiedSources'])
        self.assertFalse(mismatched['complete'])
        self.assertEqual([{'roomIds': rooms, 'issues': ['advertised-address-mismatch', 'listen-address-mismatch']}],
                         mismatched['launcherPreview']['groups'])
        split = {**launch, 'topology': 'Independent', 'servers': [
            {**launch_row, 'roomIds': [room], 'sessionId': f'00000000-0000-4000-8000-{room:012}', 'port': 3000 + room}
            for room in rooms]}
        split_preview = self.venue_json('split-preview.json', split)
        other_topology = self.venue_check(plan, 'other-topology.json', '--launcher-preview', split_preview, status=1)
        self.assertFalse(other_topology['launcherPreview']['topologyMatches'])
        self.assertCountEqual(['missing-launch-endpoint', *['unexpected-launch-endpoint'] * 5],
                              [row['issues'][0] for row in other_topology['launcherPreview']['groups']])

        missing = self.venue_check(plan, 'missing.json', '--pairs', manual, status=1)
        self.assertEqual(['verified', 'missing'], [row['status'] for row in missing['groups'][0]['sources']])
        self.assertNotIn('udpSourcePreflights', missing['groups'][0])
        self.assertFalse(missing['complete'])
        duplicate = self.venue_check(plan, 'duplicate.json', '--pairs', manual, '--batch', self.root / 'readiness.json', status=1)
        self.assertEqual(['duplicate-pair', 'verified'], [row['status'] for row in duplicate['groups'][0]['sources']])
        wrong = self.venue_json('wrong.json', {'version': 1, 'pairs': [{**first, 'listener': second['listener']},
                                                                     {'listener': 'absent', 'probe': 'absent'}]})
        invalid = self.venue_check(plan, 'invalid.json', '--pairs', wrong, status=1)
        self.assertEqual(1, invalid['unreadablePairs'])
        self.assertEqual(['invalid-or-expired', 'missing'], [row['status'] for row in invalid['groups'][0]['sources']])
        before = (self.root / 'readiness.json').read_bytes()
        self.venue_check(plan, 'readiness.json', '--batch', batch, status=1)
        self.assertEqual(before, (self.root / 'readiness.json').read_bytes())
        self.assertEqual(original_reports, {name: (self.root / name).read_bytes() for name in original_reports})

    def test_venue_independent_requires_a_pair_per_port_for_the_same_source(self):
        ports = []
        sockets = []
        try:
            for _ in range(5):
                reserved = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sockets.append(reserved)
                reserved.bind((LOOPBACK, 0))
                ports.append(reserved.getsockname()[1])
        finally:
            for reserved in sockets:
                reserved.close()
        peer = '127.0.0.2'
        pairs = [self.venue_pair(port, peer, f'room-{room}') for room, port in enumerate(ports, 1)]
        plan_value = {'version': 1, 'mode': 'Independent',
            'endpoints': [{'roomIds': [room], 'address': LOOPBACK, 'port': port} for room, port in enumerate(ports, 1)],
            'sources': [{'roomId': room, 'seat': 1, 'address': peer} for room in range(1, 6)]}
        plan = self.venue_json('plan.json', plan_value)
        manifest = self.venue_json('pairs.json', {'version': 1, 'pairs': list(reversed(pairs))})
        launch_value, preview_value = guarded_documents('Independent', ports)
        launch = self.venue_json('launch.json', launch_value)
        preview = self.venue_json('preview.json', preview_value)
        inventory = self.venue_json('seat-addresses.json', {'version': 1, 'seats': plan_value['sources']})
        generated = self.root / 'prepared-network.json'
        prepared = prepare_network(launch, preview, inventory, generated, '--players-per-room', 1)
        self.assertEqual(0, prepared.returncode, prepared.stderr)
        self.assertEqual(plan_value, json.loads(generated.read_bytes()))
        report = self.venue_check(generated, 'readiness.json', '--pairs', manifest, '--launcher-preview', preview, '--launch-plan', launch)
        self.assertEqual((5, 5), (report['expectedSources'], report['verifiedSources']))
        self.assertTrue(report['complete'])
        self.assertTrue(report['launchBinding']['complete'])
        self.assertEqual([[1], [2], [3], [4], [5]], [group['roomIds'] for group in report['groups']])
        self.assertEqual([[pair] for pair in pairs], [group['udpSourcePreflights'] for group in report['groups']])
        plan_value['sources'][4]['address'] = '127.0.0.3'
        wrong = self.venue_json('wrong-source.json', plan_value)
        invalid = self.venue_check(wrong, 'unmatched.json', '--pairs', manifest, status=1)
        self.assertEqual((1, 4), (invalid['unmatchedPairs'], invalid['verifiedSources']))
        self.assertEqual('missing', invalid['groups'][4]['sources'][0]['status'])

    def test_key_is_created_once_and_errors_hide_private_values(self):
        original = self.key.read_bytes()
        self.assertEqual(len(base64.b64decode(original, validate=True)), 32)
        duplicate = self.run_script('-NewKey', '-KeyFile', self.key)
        self.assertEqual(duplicate.returncode, 1)
        self.assertEqual(json.loads(duplicate.stdout)['step'], 'key')
        self.assertEqual(self.key.read_bytes(), original)
        self.assertNotIn(original.decode('ascii'), duplicate.stdout)
        self.assertNotIn(str(self.key), duplicate.stdout)
        invalid = self.run_script('-Mode', 'Probe', *self.options(7777, 1, peer='192.168.050.2'))
        self.assertEqual(invalid.returncode, 1)
        self.assertEqual(json.loads(invalid.stdout)['step'], 'address')

    def test_both_processes_finish_and_the_port_can_be_reused(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserved:
            reserved.bind((LOOPBACK, 0))
            port = reserved.getsockname()[1]
        probe_address = '127.0.0.2'
        with self.listener(port, 3, peer=probe_address) as (listener, path):
            occupied = self.run_script('-Mode', 'Listen', *self.options(port, 1))
            self.assertEqual(occupied.returncode, 1)
            self.assertEqual(json.loads(occupied.stdout)['step'], 'bind')
            result = self.run_script('-Mode', 'Probe', *self.options(port, 3, local=probe_address))
            self.assertEqual(result.returncode, 0, result.stderr)
            probe = json.loads(result.stdout)
            self.assertTrue(probe['complete'])
            self.assertEqual(probe['scope'], 'authenticated-udp-only')
            self.assertEqual([item['sample'] for item in probe['samples']], [1, 2, 3])
            self.assertTrue(all(0 <= item['roundTripMs'] <= 900 for item in probe['samples']))
            self.assertEqual(listener.wait(timeout=5), 0)
            final = json.loads(path.read_text(encoding='utf-8').splitlines()[-1])
            self.assertEqual(final['matched'], 3)
            self.assertRegex(probe['exchangeSha256'], r'\A[0-9a-f]{64}\Z')
            self.assertEqual(probe['exchangeSha256'], final['exchangeSha256'])
        report = self.root / 'probe.json'
        report.write_text(result.stdout, encoding='utf-8-sig')
        listener_report = self.root / 'listener-tee.ndjson'
        listener_report.write_text(path.read_text(encoding='utf-8'), encoding='utf-16')
        paired = self.run_script('-ListenerReport', listener_report, '-ProbeReport', report)
        self.assertEqual(paired.returncode, 0, paired.stderr or paired.stdout)
        self.assertEqual(json.loads(paired.stdout), {'version': 1, 'stage': 'pair-verified', 'complete': True,
            'port': port, 'matched': 3, 'scope': 'authenticated-udp-only', 'exchangeSha256': probe['exchangeSha256']})
        finished = datetime.fromisoformat(final['completedAtUtc'])
        bind = (finished + timedelta(seconds=2)).isoformat()
        expected = ['-ExpectedServerAddress', LOOPBACK, '-ExpectedGamePort', str(port),
                    '-ExpectedPeerAddresses', f'{LOOPBACK},{probe_address}', '-BindingObservedAtUtc', bind]
        options = ['-ListenerReport', listener_report, '-ProbeReport', report]
        matched = self.run_script(*options, *expected)
        self.assertEqual(matched.returncode, 0, matched.stdout or matched.stderr)
        receipt = json.loads(matched.stdout)
        self.assertIs(receipt['endpointVerified'], True)
        self.assertEqual(1, receipt['verifiedPeerIndex'])
        self.assertNotIn(probe_address, matched.stdout)
        for index, wrong in ((1, '127.0.0.3'), (3, str(port-1)), (5, LOOPBACK),
                             (7, (finished - timedelta(seconds=1)).isoformat()),
                             (7, (finished + timedelta(minutes=31)).isoformat())):
            with self.subTest(index=index):
                mismatch = expected.copy(); mismatch[index] = wrong
                rejected = self.run_script(*options, *mismatch)
                self.assertEqual(rejected.returncode, 1, rejected.stdout or rejected.stderr)
                self.assertEqual(json.loads(rejected.stdout)['step'], 'binding')
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as next_owner:
            next_owner.bind((LOOPBACK, port))
        with self.listener(port, 3, filename='listener-local.ndjson') as (listener, local_path):
            local_probe = self.run_script('-Mode', 'Probe', *self.options(port, 3))
            self.assertEqual(0, local_probe.returncode, local_probe.stderr or local_probe.stdout)
            self.assertEqual(0, listener.wait(timeout=5))
            local_finished = json.loads(local_path.read_text(encoding='utf-8').splitlines()[-1])
        local_report = self.root / 'probe-local.json'
        local_report.write_text(local_probe.stdout, encoding='utf-16')
        expected[-1] = (datetime.fromisoformat(local_finished['completedAtUtc']) + timedelta(seconds=2)).isoformat()
        local_pair = self.run_script('-ListenerReport', local_path, '-ProbeReport', local_report, *expected)
        self.assertEqual(0, local_pair.returncode, local_pair.stderr or local_pair.stdout)
        local_receipt = json.loads(local_pair.stdout)
        self.assertEqual(0, local_receipt['verifiedPeerIndex'])
        self.assertNotEqual(receipt['exchangeSha256'], local_receipt['exchangeSha256'])
        self.assertNotIn(LOOPBACK, local_pair.stdout)

    def test_wrong_authentication_and_replay_are_not_echoed(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.bind((LOOPBACK, 0))
            sender.settimeout(.35)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserved:
                reserved.bind((LOOPBACK, 0))
                port = reserved.getsockname()[1]
            key = base64.b64decode(self.key.read_bytes())
            with self.listener(port, 2) as (listener, path):
                target = (LOOPBACK, port)
                nonce = 'b' * 32
                sender.sendto(packet(bytes(byte ^ 255 for byte in key), 'Q', nonce), target)
                with self.assertRaises(socket.timeout):
                    sender.recvfrom(256)
                original = packet(key, 'Q', nonce)
                sender.sendto(original, target)
                self.assertEqual(sender.recvfrom(256), (packet(key, 'R', nonce), target))
                sender.sendto(original, target)
                with self.assertRaises(socket.timeout):
                    sender.recvfrom(256)
                fresh = 'a' * 32
                sender.sendto(packet(key, 'Q', fresh), target)
                self.assertEqual(sender.recvfrom(256), (packet(key, 'R', fresh), target))
                self.assertEqual(listener.wait(timeout=5), 0)
            final = json.loads(path.read_text(encoding='utf-8').splitlines()[-1])
            self.assertEqual(final['matched'], 2)
            text = f'VRLAN1\n{LOOPBACK}\n{LOOPBACK}\n{port}\n{fresh}\n{nonce}'
            self.assertEqual(final['exchangeSha256'], hashlib.sha256(text.encode('ascii')).hexdigest())

    def test_pair_rejects_reports_from_different_exchanges_on_the_same_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserved:
            reserved.bind((LOOPBACK, 0))
            port = reserved.getsockname()[1]
        reports = []
        for index in range(2):
            with self.listener(port, 2, filename=f'listener-{index}.ndjson') as (listener, path):
                completed = self.run_script('-Mode', 'Probe', *self.options(port, 2))
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(listener.wait(timeout=5), 0)
                reports.append((path, json.loads(completed.stdout)))
        path, first = reports[0]
        second = reports[1][1]
        self.assertNotEqual(first['exchangeSha256'], second['exchangeSha256'])
        self.assertEqual((first['port'], first['matched']), (second['port'], second['matched']))
        report = self.root / 'probe.json'
        for changed in (second, {**first, 'localAddress': '127.0.0.2'}, {**first, 'complete': False},
                        {**first, 'samples': []}, {**first, 'exchangeSha256': None}):
            with self.subTest(changed=changed):
                report.write_text(json.dumps(changed), encoding='utf-16')
                paired = self.run_script('-ListenerReport', path, '-ProbeReport', report)
                self.assertEqual(paired.returncode, 1, paired.stderr)
                self.assertEqual(json.loads(paired.stdout), {'version': 1, 'stage': 'failed', 'step': 'reports', 'complete': False})

    def test_probe_rejects_a_signed_reply_from_another_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as other:
            server.bind((LOOPBACK, 0))
            other.bind((LOOPBACK, 0))
            server.settimeout(6)
            options = self.options(server.getsockname()[1], 1)
            with subprocess.Popen(self.shell + ['-Mode', 'Probe', '-TimeoutMs', '600', *options],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as probe:
                try:
                    incoming, source = server.recvfrom(256)
                    nonce = incoming.decode('ascii').split(':')[1]
                    key = base64.b64decode(self.key.read_bytes())
                    other.sendto(packet(key, 'R', nonce), source)
                    stdout, stderr = probe.communicate(timeout=5)
                    self.assertEqual(probe.returncode, 1, stderr)
                    result = json.loads(stdout)
                    self.assertEqual(result['matched'], 0)
                    self.assertEqual(result['samples'], [{'sample': 1, 'roundTripMs': None}])
                finally:
                    if probe.poll() is None:
                        probe.kill()

    def test_listener_expires_with_no_packets_from_the_expected_peer(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.bind((LOOPBACK, 0))
            sender.settimeout(.4)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserved:
                reserved.bind((LOOPBACK, 0))
                port = reserved.getsockname()[1]
            with self.listener(port, 1, peer='127.0.0.2', seconds=5) as (listener, path):
                key = base64.b64decode(self.key.read_bytes())
                sender.sendto(packet(key, 'Q', 'c' * 32), (LOOPBACK, port))
                with self.assertRaises(socket.timeout):
                    sender.recvfrom(256)
                self.assertEqual(listener.wait(timeout=8), 1)
                result = json.loads(path.read_text(encoding='utf-8').splitlines()[-1])
                self.assertEqual(result['matched'], 0)
                self.assertFalse(result['complete'])


if __name__ == '__main__':
    unittest.main()
