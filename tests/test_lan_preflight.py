import base64
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
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
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
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

    def test_verified_start_receipt_keeps_both_original_server_release_witnesses(self):
        spec = importlib.util.spec_from_file_location('start_verified_venue', ROOT / 'scripts/start-verified-venue.py')
        start = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(start)
        expected = 'a' * 64
        stamps = {'serverManifestSha256': expected, 'venueReleaseReportSha256': 'b' * 64}
        source = {'topology': 'Linked', 'instanceId': 'fixture-instance', **stamps}
        ready = self.store('ready.json', dict(source, status='venue-ready'))
        terminal = self.store('terminal.json', dict(source, status='venue-sealed-stopped', complete=True, readyPublished=True))
        readiness = self.store('readiness.json', {'complete': True})
        checked = {'mode': 'Linked', 'checkedAtUtc': '2026-11-16T00:00:00+00:00'}
        ready_evidence = start.field.read_quest_document(ready)
        accepted = readiness.with_name('accepted.json')
        start.write_start_receipt(accepted, ready, ready_evidence, terminal, readiness, readiness.read_bytes(), checked, stamps)
        receipt = json.loads(accepted.read_bytes())
        self.assertEqual(hashlib.sha256(ready.read_bytes()).hexdigest(), receipt['readySha256'])
        self.assertEqual(hashlib.sha256(terminal.read_bytes()).hexdigest(), receipt['terminalSha256'])
        terminal = self.store('other-terminal.json', dict(source, venueReleaseReportSha256='c' * 64,
                              status='venue-sealed-stopped', complete=True, readyPublished=True))
        rejected = readiness.with_name('rejected.json')
        with self.assertRaisesRegex(start.field.EvidenceError, 'do not share the verified server release'):
            start.write_start_receipt(rejected, ready, ready_evidence, terminal, readiness, readiness.read_bytes(), checked, stamps)
        self.assertFalse(rejected.exists())

    def test_verified_start_binding_uses_each_rooms_exact_windows_deadline(self):
        spec = importlib.util.spec_from_file_location('start_verified_venue', ROOT / 'scripts/start-verified-venue.py')
        start = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(start)
        checked = datetime.fromisoformat('2026-11-16T00:29:59.000000+00:00')
        expiry = start.udp_utc_ticks('2026-11-16T00:30:00.1234567+00:00')
        deadlines = {(room,): expiry for room in range(1, 6)}
        deadlines[(5,)] = start.udp_utc_ticks('2026-11-16T00:30:00.1234569Z')
        ready = {'status': 'venue-ready', 'topology': 'Independent', 'servers': [
            {'roomIds': [room], 'ready': {'udpBinding': {
                'observedAtUtc': '2026-11-16T00:30:00.1234568Z' if room == 5 else '2026-11-16T00:30:00.1234567Z'
            }}} for room in range(1, 6)]}
        start.check_ready_bind_times(ready, 'Independent', checked, deadlines)
        ready['servers'][3]['ready']['udpBinding']['observedAtUtc'] = '2026-11-16T00:30:00.1234568Z'
        with self.assertRaisesRegex(start.field.EvidenceError, r'outside the original preflight window for room\(s\) 4'):
            start.check_ready_bind_times(ready, 'Independent', checked, deadlines)

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
                self.assertEqual([{key: row[key] for key in ('roomIds', 'address', 'port', 'sessionId', 'missionId', 'sessionSequence')}
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

    def test_distinct_remote_mode_names_conflicting_seats_before_creating_the_plan(self):
        for mode, ports in (('Independent', range(7777, 7782)), ('Linked', [7777])):
            with self.subTest(mode=mode):
                launch_value, preview_value = guarded_documents(mode, ports, '192.168.5.10')
                launch = self.store('launch.json', launch_value)
                preview = self.store('preview.json', preview_value)
                rows = [{'roomId': room, 'seat': 1, 'address': f'192.168.5.{20 + room}'} for room in range(1, 6)]
                inventory = self.store('seats.json', {'version': 1, 'seats': rows})
                good = self.root / f'{mode}-direct.json'
                default = self.root / f'{mode}-standard.json'
                arguments = ('--players-per-room', 1)
                result = prepare_network(launch, preview, inventory, good, *arguments, '--require-distinct-remote-roster')
                self.assertEqual(result.returncode, 0, result.stderr)
                result = prepare_network(launch, preview, inventory, default, *arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(good.read_bytes(), default.read_bytes())
                rows[2]['address'] = launch_value['address']
                rows[4]['address'] = rows[0]['address']
                self.store(inventory.name, {'version': 1, 'seats': rows})
                refused = self.root / f'{mode}-refused.json'
                result = prepare_network(launch, preview, inventory, refused, *arguments, '--require-distinct-remote-roster')
                self.assertEqual(result.returncode, 1)
                self.assertIn('server or non-private source: room 3 seat 1', result.stderr)
                self.assertIn('shared source: room 1 seat 1, room 5 seat 1', result.stderr)
                self.assertNotIn('192.168.', result.stderr)
                self.assertFalse(refused.exists())
                fallback = prepare_network(launch, preview, inventory, refused, *arguments)
                self.assertEqual(fallback.returncode, 0, fallback.stderr)
                readiness = self.root / f'{mode}-readiness.json'
                checked = subprocess.run([sys.executable, str(ROOT / 'scripts/check-venue-udp-preflight.py'),
                                          '--network-plan', str(refused), '--output', str(readiness),
                                          '--require-distinct-remote-roster'], capture_output=True, text=True, timeout=15)
                self.assertEqual(checked.returncode, 1)
                self.assertIn('server or non-private source: room 3 seat 1', checked.stderr)
                self.assertIn('shared source: room 1 seat 1, room 5 seat 1', checked.stderr)
                self.assertFalse(readiness.exists())

    def test_roster_preview_rejects_same_size_wrong_seat_before_network_output(self):
        for mode, ports in (('Independent', range(7777, 7782)), ('Linked', [7777])):
            with self.subTest(mode=mode):
                launch, preview = guarded_documents(mode, ports, '192.168.5.10')
                expected = [{'roomId': room, 'seat': 2 if room == 5 else 1} for room in range(1, 6)]
                for group in preview['servers']:
                    group['registeredSeats'] = [seat for seat in expected if seat['roomId'] in group['roomIds']]
                launch_path, preview_path = self.store('launch.json', launch), self.store('preview.json', preview)
                seats = [{**seat, 'address': f"192.168.5.{20 + seat['roomId']}"} for seat in expected]
                wrong = [*seats[:-1], {**seats[-1], 'seat': 1}]
                inventory = self.store('seats.json', {'version': 1, 'seats': wrong})
                output = self.root / f'{mode}-network.json'
                result = prepare_network(launch_path, preview_path, inventory, output, '--players-per-room', 1)
                self.assertEqual(1, result.returncode, result.stderr)
                self.assertIn('missing registered seats: room 5 seat 2', result.stderr)
                self.assertIn('unregistered seats: room 5 seat 1', result.stderr)
                self.assertFalse(output.exists())
                self.store(inventory.name, {'version': 1, 'seats': seats})
                result = prepare_network(launch_path, preview_path, inventory, output, '--players-per-room', 1)
                self.assertEqual(0, result.returncode, result.stderr)
                plan = json.loads(output.read_bytes())
                self.assertEqual(seats, plan['sources'])
                output.write_text(json.dumps({**plan, 'sources': wrong}), encoding='utf-8')
                readiness = self.root / f'{mode}-readiness.json'
                args = [sys.executable, str(ROOT / 'scripts/check-venue-udp-preflight.py'), '--network-plan', str(output),
                        '--launch-plan', str(launch_path), '--launcher-preview', str(preview_path), '--output', str(readiness)]
                result = subprocess.run(args, capture_output=True, text=True, timeout=15)
                self.assertIn('unregistered seats: room 5 seat 1', result.stderr)
                self.assertFalse(readiness.exists())
                output.write_text(json.dumps(plan), encoding='utf-8')
                result = subprocess.run(args, capture_output=True, text=True, timeout=15)
                self.assertEqual(1, result.returncode, result.stderr)
                self.assertEqual(5, json.loads(readiness.read_bytes())['expectedSources'])

    def test_network_plan_rejects_replacement_launch_with_same_endpoints_and_seats(self):
        spec = importlib.util.spec_from_file_location('quest_venue_probe', ROOT / 'scripts/probe-quest-venue.py')
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        for mode, ports in (('Independent', range(7777, 7782)), ('Linked', [7777])):
            with self.subTest(mode=mode):
                launch, preview = guarded_documents(mode, ports, '192.168.5.10')
                launch_path, preview_path = self.store('original-plan.json', launch), self.store('original-preview.json', preview)
                rows = [{'roomId': room, 'seat': 1, 'address': f'192.168.5.{20 + room}'} for room in range(1, 6)]
                seats = self.store('seats.json', {'version': 1, 'seats': rows})
                devices = self.store('devices.json', {'version': 1, 'seats': [{'roomId': 5, 'seat': 1, 'serial': 'fixture'}]})
                network = self.root / f'{mode}-network.json'
                subset = self.root / f'{mode}-subset.json'
                for output, flags in ((network, ()), (subset, ('--quest-device-map', devices))):
                    made = prepare_network(launch_path, preview_path, seats, output, '--players-per-room', 1, *flags)
                    self.assertEqual(0, made.returncode, made.stderr)
                parsed = probe.field.read_udp_launcher_document(preview_path, preview=True)
                self.assertEqual(mode, probe.load_plan(devices, subset, launcher_preview=parsed)[0])

                original = launch['servers'][-1]
                for field, new_value in (('sessionId', '00000000-0000-4000-8000-000000000199'),
                                         ('missionId', '00000000-0000-4000-8000-000000000198'),
                                         ('sessionSequence', original['sessionSequence'] + 1)):
                    with self.subTest(field=field):
                        new_launch = self.store('replacement-plan.json', {**launch, 'servers':
                            [*launch['servers'][:-1], {**original, field: new_value}]})
                        new_preview = self.store('replacement-preview.json', {**preview, 'servers':
                            [*preview['servers'][:-1], {**preview['servers'][-1], field: new_value}]})
                        replacement = probe.field.read_udp_launcher_document(new_preview, preview=True)
                        with self.assertRaisesRegex(probe.field.EvidenceError, 'launch identity or revision differs'):
                            probe.load_plan(devices, subset, launcher_preview=replacement)
                        readiness = self.root / 'unwritten.json'
                        result = subprocess.run([sys.executable, str(ROOT / 'scripts/check-venue-udp-preflight.py'),
                            '--network-plan', str(network), '--launch-plan', str(new_launch), '--launcher-preview', str(new_preview),
                            '--output', str(readiness)], capture_output=True, text=True, timeout=15)
                        self.assertEqual(1, result.returncode, result.stderr)
                        self.assertIn('launch identity or revision differs', result.stderr)
                        self.assertFalse(readiness.exists())

    def test_distinct_requirement_survives_retry_and_batch_recheck(self):
        launch_value, preview_value = guarded_documents('Linked', [7777], '192.168.5.10')
        launch = self.store('launch.json', launch_value)
        preview = self.store('preview.json', preview_value)
        sources = [{'roomId': room, 'seat': 1, 'address': f'192.168.5.{20 + room}'} for room in range(1, 6)]
        inventory = self.store('seats.json', {'version': 1, 'seats': sources})
        network = self.root / 'network.json'
        generated = prepare_network(launch, preview, inventory, network, '--players-per-room', 1,
                                    '--require-distinct-remote-roster')
        self.assertEqual(0, generated.returncode, generated.stderr)
        common = [sys.executable, str(ROOT / 'scripts/check-venue-udp-preflight.py'), '--network-plan', str(network),
                  '--launch-plan', str(launch), '--launcher-preview', str(preview)]

        def preflight(output, *extra):
            return subprocess.run([*common, '--output', str(output), *map(str, extra)],
                                  capture_output=True, text=True, timeout=15)

        partial, retry = self.root / 'partial.json', self.root / 'retry.json'
        checked = preflight(partial, '--require-distinct-remote-roster')
        self.assertEqual(1, checked.returncode, checked.stderr)
        first = json.loads(partial.read_bytes())
        self.assertIs(first['requireDistinctRemoteRoster'], True)
        self.assertEqual(5, first['expectedSources'])
        checked = preflight(retry, '--retry-report', partial)
        self.assertEqual(1, checked.returncode, checked.stderr)
        self.assertIs(json.loads(retry.read_bytes())['requireDistinctRemoteRoster'], True)
        bad = self.store('bad-partial.json', dict(first, requireDistinctRemoteRoster='true'))
        refused = self.root / 'refused.json'
        checked = preflight(refused, '--retry-report', bad)
        self.assertIn('Invalid distinct remote roster option', checked.stderr)
        self.assertFalse(refused.exists())

        # A batch with unavailable original pairs cannot complete, but its requirement still applies.
        first['complete'] = first['groups'][0]['complete'] = True
        first['groups'][0]['udpSourcePreflights'] = [{'listener': 'missing-listener', 'probe': 'missing-probe'}]
        batch = self.store('batch.json', first)
        aggregated = self.root / 'aggregated.json'
        checked = preflight(aggregated, '--batch', batch)
        self.assertEqual(1, checked.returncode, checked.stderr)
        result = json.loads(aggregated.read_bytes())
        self.assertIs(result['requireDistinctRemoteRoster'], True)
        self.assertEqual(1, result['unreadablePairs'])
        network.write_bytes(network.read_bytes() + b'\n')
        checked = preflight(refused, '--batch', batch)
        self.assertIn('Reuse the original venue network plan', checked.stderr)
        self.assertFalse(refused.exists())

    def test_server_inventory_rejects_a_player_on_an_unadvertised_server_address(self):
        launch_value, preview_value = guarded_documents('Linked', [7777], '192.168.5.10')
        launch = self.store('launch.json', launch_value)
        preview = self.store('preview.json', preview_value)
        sources = [{'roomId': room, 'seat': 1, 'address': f'192.168.5.{20 + room}'} for room in range(1, 6)]
        inventory = self.store('seats.json', {'version': 1, 'seats': sources})
        network = self.root / 'network.json'
        extra_server = '192.168.5.40'
        args = ('--players-per-room', 1, '--server-ip', extra_server, '--server-ip', launch_value['address'])
        generated = prepare_network(launch, preview, inventory, network, *args)
        self.assertEqual(0, generated.returncode, generated.stderr)
        plan = json.loads(network.read_bytes())
        self.assertEqual([launch_value['address'], extra_server], plan['serverIps'])
        output = self.root / 'readiness.json'
        command = [sys.executable, str(ROOT / 'scripts/check-venue-udp-preflight.py'),
                   '--output', str(output), '--network-plan']
        checked = subprocess.run([*command, str(network)], capture_output=True, text=True, timeout=15)
        self.assertEqual(1, checked.returncode, checked.stderr)
        self.assertIs(json.loads(output.read_bytes())['requireDistinctRemoteRoster'], True)
        refused = self.root / 'refused.json'
        result = prepare_network(launch, preview, inventory, refused, '--players-per-room', 1, '--server-ip', extra_server)
        self.assertIn('include every advertised endpoint', result.stderr)
        sources[-1]['address'] = extra_server
        self.store(inventory.name, {'version': 1, 'seats': sources})
        result = prepare_network(launch, preview, inventory, refused, *args)
        self.assertIn('server or non-private source: room 5 seat 1', result.stderr)
        self.assertNotIn(extra_server, result.stderr)
        self.assertFalse(refused.exists())
        corrupted = self.store('corrupted-network.json', dict(plan, sources=sources))
        output.unlink()
        checked = subprocess.run([*command, str(corrupted)], capture_output=True, text=True, timeout=15)
        self.assertEqual(1, checked.returncode)
        self.assertIn('server or non-private source: room 5 seat 1', checked.stderr)
        self.assertFalse(output.exists())

    @unittest.skipUnless(os.name == 'nt', 'Verified launch CLI requires Windows')
    def test_launch_enforces_original_distinct_policy_without_repeating_flag(self):
        launch_value, preview_value = guarded_documents('Linked', [7777], '192.168.5.10')
        launch = self.store('launch.json', launch_value)
        preview = self.store('preview.json', preview_value)
        network = self.store('network.json', {'version': 1, 'mode': 'Linked',
            'endpoints': [{'roomIds': list(range(1, 6)), 'address': '192.168.5.10', 'port': 7777}],
            'sources': [{'roomId': room, 'seat': 1, 'address': '192.168.5.21'} for room in range(1, 6)]})
        ready = self.root / 'readiness.json'
        command = [sys.executable, str(ROOT / 'scripts/check-venue-udp-preflight.py'), '--network-plan', str(network),
                   '--launch-plan', str(launch), '--launcher-preview', str(preview), '--output', str(ready)]
        incomplete = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(1, incomplete.returncode, incomplete.stderr)
        report = json.loads(ready.read_bytes())
        report.update(complete=True, requireDistinctRemoteRoster=True)
        claimed = self.store('claimed.json', report)
        launcher = self.root / 'Launch-Server.exe'
        launcher.touch()
        work, launched, terminal = (self.root / name for name in ('work', 'ready.json', 'terminal.json'))
        started = subprocess.run([sys.executable, str(ROOT / 'scripts/start-verified-venue.py'), '--launcher', str(launcher),
                                  '--network-plan', str(network), '--launch-plan', str(launch), '--readiness', str(claimed),
                                  '--seconds', '60', '--work', str(work), '--ready-report', str(launched),
                                  '--report', str(terminal)], capture_output=True, text=True, timeout=15)
        self.assertEqual(1, started.returncode)
        self.assertIn('shared source: room 1 seat 1, room 2 seat 1', started.stderr)
        self.assertEqual('', started.stdout)
        self.assertFalse(any(path.exists() for path in (work, launched, terminal)))


def packet(key, kind, nonce):
    prefix = f'VRLAN1{kind}:{nonce}'.encode('ascii')
    return prefix + b':' + hmac.new(key, prefix, hashlib.sha256).hexdigest().encode('ascii')


@unittest.skipUnless(SHELL, 'PowerShell is required for native UDP preflight checks')
class LanPreflightFixtures(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix='lan-preflight-')
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.key = self.root / 'probe.key'
        self.shell = [SHELL, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'RemoteSigned',
                      '-File', str(ROOT / 'scripts/check-lan-udp.ps1')]
        self.environment = {**os.environ, 'VR_COMMAND_UNATTENDED': '1'}
        result = self.run_script('-NewKey', '-KeyFile', self.key)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'version': 1, 'stage': 'key-created'})

    def run_script(self, *args):
        return subprocess.run([*self.shell, *map(str, args)], env=self.environment, capture_output=True, text=True, timeout=15)

    def options(self, port, count, *, key=None, peer=LOOPBACK, local=LOOPBACK):
        return ['-LocalAddress', local, '-PeerAddress', peer, '-Port', str(port), '-Count', str(count),
                '-KeyFile', str(key or self.key)]


class LanPreflightOfflineTests(LanPreflightFixtures):
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


class LanPreflightTests(LanPreflightFixtures):
    @classmethod
    def setUpClass(cls):
        from windows_firewall import WindowsFirewallLaunchError, require_silent_windows_launch

        try:
            require_silent_windows_launch(sys.executable)
            require_silent_windows_launch(SHELL)
        except WindowsFirewallLaunchError as error:
            raise unittest.SkipTest(str(error)) from error

    @contextmanager
    def listener(self, port, count, *, peer=LOOPBACK, seconds=10, filename='listener.ndjson', endpoint=None):
        path = self.root / filename
        options = self.options(port, count, peer=peer) if endpoint is None else [
            '-EndpointFile', str(endpoint), '-Count', str(count), '-KeyFile', str(self.key)]
        with path.open('xb') as output:
            with subprocess.Popen(self.shell + ['-Mode', 'Listen', '-Seconds', str(seconds), *options],
                                  env=self.environment, stdout=output, stderr=subprocess.STDOUT) as process:
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

    def venue_pair(self, port, peer, label, *, encoding='utf-8', endpoint=None):
        with self.listener(port, 2, peer=peer, filename=f'{label}-listener.ndjson', endpoint=endpoint) as (listener, path):
            options = self.options(port, 2, local=peer) if endpoint is None else [
                '-EndpointFile', str(endpoint), '-Count', '2', '-KeyFile', str(self.key)]
            result = self.run_script('-Mode', 'Probe', *options)
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
        self.assertTrue(report.is_file(), result.stderr)
        return json.loads(report.read_text(encoding='utf-8'))

    def test_windows_retest_exports_one_pending_source_for_both_probe_roles(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserve:
            reserve.bind((LOOPBACK, 0))
            port = reserve.getsockname()[1]
        launch_value, preview_value = guarded_documents('Linked', [port])
        launch = self.venue_json('windows-launch.json', launch_value)
        preview = self.venue_json('windows-preview.json', preview_value)
        rooms = list(range(1, 6))
        roster = [{'roomId': room, 'seat': seat, 'address': '127.0.0.3' if (room, seat) in ((4, 5), (5, 5)) else '127.0.0.2'}
                  for room in rooms for seat in rooms]
        network = self.venue_json('windows-network.json', {'version': 1, 'mode': 'Linked',
            'endpoints': [{'roomIds': rooms, 'address': LOOPBACK, 'port': port}], 'sources': roster})
        first_pair = self.venue_pair(port, '127.0.0.2', 'try-1', encoding='utf-16')
        first_paths = self.venue_json('first-pairs.json', {'version': 1, 'pairs': [first_pair]})
        original = self.root / 'incomplete.json'
        guard = ('--launch-plan', launch, '--launcher-preview', preview)
        first = self.venue_check(network, original.name, '--pairs', first_paths, *guard, status=1)
        self.assertEqual((1, 2), (first['verifiedSources'], first['expectedSources']))
        before = {path: path.read_bytes() for path in (network, original, launch, preview, *(self.root / name for name in first_pair.values()))}

        def export(room, seat, output):
            return subprocess.run([sys.executable, str(ROOT / 'scripts/check-venue-udp-preflight.py'), '--network-plan', str(network),
                '--retry-report', str(original), '--windows-retest-seat', str(room), str(seat), '--output', str(output), *map(str, guard)],
                capture_output=True, text=True, timeout=20)

        skipped = self.root / 'skipped.json'
        success = export(1, 1, skipped)
        self.assertEqual(0, success.returncode, success.stderr)
        self.assertEqual('no-windows-retest', json.loads(success.stdout)['status'])
        self.assertFalse(skipped.exists())
        endpoint = self.root / 'endpoint.json'
        result = export(5, 5, endpoint)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn(LOOPBACK, result.stdout)
        self.assertEqual({'status': 'windows-retest-endpoint', 'coveredSeats': [
            {'roomId': 4, 'seat': 5}, {'roomId': 5, 'seat': 5}]}, json.loads(result.stdout))
        plan = json.loads(endpoint.read_bytes())
        self.assertEqual({'version': 1, 'scope': 'windows-udp-retest-endpoint', 'serverAddress': LOOPBACK,
                          'peerAddress': '127.0.0.3', 'port': port}, plan)
        invalid = self.venue_json('wrong-endpoint.json', {**plan, 'scope': 'venue-udp-preflight-only'})
        refused = self.run_script('-Mode', 'Probe', '-EndpointFile', invalid, '-KeyFile', self.key, '-Count', 1)
        self.assertEqual(1, refused.returncode, refused.stderr)
        self.assertEqual({'version': 1, 'stage': 'failed', 'step': 'endpoint-file', 'complete': False}, json.loads(refused.stdout))
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as port_check:
            port_check.bind((LOOPBACK, port))
        second = self.venue_pair(port, '127.0.0.3', 'try-2', endpoint=endpoint)
        second_paths = self.venue_json('second-pairs.json', {'version': 1, 'pairs': [second]})
        merged = self.venue_check(network, 'complete.json', '--retry-report', original, '--pairs', second_paths, *guard)
        self.assertEqual((2, 1), (merged['verifiedSources'], merged['retainedSources']))
        self.assertEqual(25, sum(len(row['seats']) for group in merged['groups'] for row in group['sources']))
        self.assertEqual(before, {path: path.read_bytes() for path in before})

    def test_quest_retry_targets_only_current_pending_seats_from_a_full_venue_report(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserve:
            reserve.bind((LOOPBACK, 0))
            first_port = reserve.getsockname()[1]
        ports = [first_port, *[port for port in range(7777, 7782) if port != first_port][:4]]
        launch_value, preview_value = guarded_documents('Independent', ports)
        launch = self.venue_json('venue-launch.json', launch_value)
        preview = self.venue_json('venue-preview.json', preview_value)
        network = self.venue_json('venue-network.json', {'version': 1, 'mode': 'Independent', 'endpoints': [
            {'roomIds': [room], 'address': LOOPBACK, 'port': port} for room, port in enumerate(ports, 1)],
            'sources': [{'roomId': room, 'seat': 1, 'address': f'127.0.0.{room + 1}'} for room in range(1, 6)]})
        pair = self.venue_pair(first_port, '127.0.0.2', 'venue-verified')
        pairs = self.venue_json('venue-pairs.json', {'version': 1, 'pairs': [pair]})
        readiness = self.root / 'venue-incomplete.json'
        report = self.venue_check(network, readiness.name, '--pairs', pairs, '--launch-plan', launch,
                                 '--launcher-preview', preview, status=1)
        self.assertEqual(1, report['verifiedSources'])
        evidence = {path: path.read_bytes() for path in (network, launch, preview, readiness, *(self.root / name for name in pair.values()))}
        device = {'roomId': 1, 'seat': 1, 'serial': 'fixture-one'}
        mapping = self.venue_json('mapped.json', {'version': 1, 'seats': [device]})
        output = self.root / 'quest-retest'
        cli = [sys.executable, str(ROOT / 'scripts/probe-quest-venue.py'), '--network-plan', str(network),
               '--device-map', str(mapping), '--venue-retry-report', str(readiness), '--launch-plan', str(launch),
               '--launcher-preview', str(preview), '--adb', str(self.root / 'absent-adb.exe'), '--output-directory', str(output)]
        no_op = subprocess.run(cli, capture_output=True, text=True, timeout=20)
        self.assertEqual(0, no_op.returncode, no_op.stderr)
        self.assertEqual({'status': 'no-quest-retest', 'pendingOtherSeats': 4}, json.loads(no_op.stdout))
        self.assertFalse(output.exists())
        network.write_bytes(evidence[network] + b'\n')
        wrong_network = subprocess.run(cli, capture_output=True, text=True, timeout=20)
        self.assertEqual(1, wrong_network.returncode, wrong_network.stdout)
        self.assertIn('same original venue network plan', wrong_network.stderr)
        self.assertFalse(output.exists())
        network.write_bytes(evidence[network])

        spec = importlib.util.spec_from_file_location('quest_venue_probe', ROOT / 'scripts/probe-quest-venue.py')
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        mapping = self.venue_json('mapped.json', {'version': 1, 'seats': [device, {'roomId': 5, 'seat': 1, 'serial': 'fixture-five'}]})
        launcher, _ = probe.launcher_proof(launch, preview, output)
        retry_args = (mapping, network, readiness, output, launch, preview, launcher)
        mode, groups, outside = probe.load_venue_retry(*retry_args)
        self.assertEqual(('Independent', [[5]], 3), (mode, [group['roomIds'] for group in groups], outside))
        self.assertEqual([{'roomId': 5, 'seat': 1, 'serial': 'fixture-five', 'address': '127.0.0.6'}], groups[0]['devices'])
        modified = self.root / pair['probe']
        modified.write_bytes(evidence[modified] + b'\n')
        _, changed, outside = probe.load_venue_retry(*retry_args)
        self.assertEqual(([[1], [5]], 3), ([group['roomIds'] for group in changed], outside))
        modified.write_bytes(evidence[modified])
        changed_preview = self.root / 'changed-preview.json'
        changed_preview.write_bytes(evidence[preview] + b'\n')
        changed_launcher, _ = probe.launcher_proof(launch, changed_preview, output)
        with self.assertRaisesRegex(probe.field.EvidenceError, 'same original Windows plan and preview'):
            probe.load_venue_retry(mapping, network, readiness, output, launch, changed_preview, changed_launcher)
        self.assertEqual(evidence, {path: path.read_bytes() for path in evidence})
        self.assertFalse(output.exists())

    def test_verified_start_checks_udp_evidence_after_the_live_preview_and_at_binding(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserve:
            reserve.bind((LOOPBACK, 0))
            port = reserve.getsockname()[1]
        launch, preview = guarded_documents('Linked', [port])
        rooms = list(range(1, 6))
        seats = [{'roomId': room, 'seat': 1} for room in rooms]
        preview['servers'][0]['registeredSeats'] = seats
        launch_path = self.venue_json('launch.json', launch)
        preview_path = self.venue_json('preview.json', preview)
        network = self.venue_json('network.json', {'version': 1, 'mode': 'Linked',
            'endpoints': [{'roomIds': rooms, 'address': LOOPBACK, 'port': port}],
            'sources': [{**seat, 'address': '127.0.0.2'} for seat in seats]})
        pair = self.venue_pair(port, '127.0.0.2', 'current', encoding='utf-16')
        pairs = self.venue_json('pairs.json', {'version': 1, 'pairs': [pair]})
        self.venue_check(network, 'readiness.json', '--pairs', pairs, '--launch-plan', launch_path,
                         '--launcher-preview', preview_path)
        listener = self.root / pair['listener']
        probe = self.root / pair['probe']
        inputs = (listener, probe, preview_path, network, launch_path, self.root / 'readiness.json')
        originals = {path: path.read_bytes() for path in inputs}
        completed = datetime.fromisoformat(json.loads(originals[listener].splitlines()[-1])['completedAtUtc'])
        expires = completed + timedelta(minutes=30)
        launcher = self.root / 'package' / 'Launch-Server.exe'
        launcher.parent.mkdir()
        launcher.touch()
        spec = importlib.util.spec_from_file_location('start_verified_venue', ROOT / 'scripts/start-verified-venue.py')
        start = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(start)
        firewall = SimpleNamespace(WindowsFirewallLaunchError=RuntimeError, require_silent_windows_launch=Mock())

        for case, rejected in (
            ('elapsed-during-preview', 'UDP preflight expired before starting room'),
            ('probe-replaced', 'UDP pair differs from its original files'),
            ('network-replaced', 'The original network plan or launch evidence changed'),
            ('bind-too-late', 'UDP binding is outside the original preflight window for room'),
            ('bind-too-late-without-receipt', 'UDP binding is outside the original preflight window for room'),
            ('same-window', None),
            ('launcher-deadline-support', None),
        ):
            with self.subTest(case=case):
                for path, raw in originals.items():
                    if path.read_bytes() != raw:
                        path.write_bytes(raw)
                work = self.root / case
                work.mkdir()
                receipt = work / 'start.json'
                if case == 'launcher-deadline-support':
                    (launcher.parent / 'server-package.json').write_text(
                        json.dumps({'schemaVersion': 1, 'venueUdpDeadlineVersion': 1}), encoding='utf-8')
                args = SimpleNamespace(verify_only=False, launcher=launcher, launch_plan=launch_path, network_plan=network,
                                       readiness=self.root / 'readiness.json', require_distinct_remote_roster=False,
                                       retry_output=None, release_report=None, work=work / 'game',
                                       ready_report=work / 'ready.json', report=work / 'terminal.json',
                                       start_receipt=None if case.endswith('without-receipt') else receipt,
                                       peer_diagnostics=False, tracked_vr=False, seconds=60)
                after_preview = expires + timedelta(seconds=1) if case == 'elapsed-during-preview' else expires - timedelta(seconds=1)
                observed = expires + timedelta(microseconds=1) if case.startswith('bind-too-late') else expires

                def live_preview(command, *, timeout):
                    self.assertEqual('--venue-check', command[1])
                    Path(command[4]).write_bytes(originals[preview_path])
                    if case in ('probe-replaced', 'network-replaced'):
                        replaced = probe if case == 'probe-replaced' else network
                        replaced.write_bytes(originals[replaced] + b'\n')
                    return SimpleNamespace(returncode=0)

                @contextmanager
                def game(command):
                    self.assertEqual('--venue-run', command[1])
                    if case == 'launcher-deadline-support':
                        index = command.index('--udp-deadlines')
                        window = json.loads(Path(command[index + 1]).read_bytes())
                        exact_stamp = json.loads(originals[listener].splitlines()[-1])['completedAtUtc']
                        fractional = exact_stamp.split('+')[0].removesuffix('Z').partition('.')[2]
                        tail = fractional[6:7] or '0'
                        ending = expires.isoformat(timespec='microseconds').replace('+00:00', tail + '+00:00')
                        self.assertEqual({'version': 1, 'planSha256': hashlib.sha256(originals[launch_path]).hexdigest(),
                                          'groups': [{'roomIds': rooms, 'expiresAtUtc': ending}]}, window)
                    else:
                        self.assertNotIn('--udp-deadlines', command)
                    args.ready_report.write_text(json.dumps({'topology': 'Linked', 'status': 'venue-ready', 'instanceId': 'instance',
                        'servers': [{'roomIds': rooms, 'ready': {'udpBinding': {'observedAtUtc': observed.isoformat()}}}]}),
                        encoding='utf-8')
                    args.report.write_text(json.dumps({'topology': 'Linked', 'status': 'venue-sealed-stopped',
                        'instanceId': 'instance', 'complete': True, 'readyPublished': True}), encoding='utf-8')
                    yield SimpleNamespace(wait=lambda: 0)

                process = Mock(side_effect=game)
                with (patch.dict(sys.modules, windows_firewall=firewall), patch.object(start, 'own_launcher_processes'),
                      patch.object(start, 'datetime', SimpleNamespace(now=lambda zone: after_preview, fromisoformat=datetime.fromisoformat)),
                      patch.object(start, 'subprocess', SimpleNamespace(Popen=process, run=live_preview))):
                    if rejected:
                        with self.assertRaisesRegex(start.field.EvidenceError, rejected):
                            start.launch(args)
                    else:
                        self.assertEqual(0, start.launch(args))
                self.assertEqual(case.startswith('bind-too-late') or rejected is None, process.called)
                self.assertEqual(rejected is None, receipt.exists())
                if receipt.exists():
                    self.assertEqual(after_preview.isoformat(), json.loads(receipt.read_bytes())['checkedAtUtc'])

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
        self.assertEqual([[hashlib.sha256(original_reports[pair[role]]).hexdigest() for role in ('listener', 'probe')]
                          for pair in (first, second)], group['udpSourcePreflightSha256'])
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
        verify = [sys.executable, str(ROOT / 'scripts/start-verified-venue.py'), '--verify-only',
                  '--launch-plan', str(original), '--network-plan', str(generated)]
        success = subprocess.run([*verify, '--readiness', str(self.root / 'bound.json')], capture_output=True, timeout=15)
        self.assertEqual(0, success.returncode, success.stderr)
        self.assertEqual({'status': 'udp-evidence-verified', 'mode': 'Linked', 'verifiedSources': 2,
                          'expectedSources': 2, 'unreadablePairs': 0, 'unmatchedPairs': 0, 'pendingSeats': []},
                         json.loads(success.stdout))

        spec = importlib.util.spec_from_file_location('start_verified_venue', ROOT / 'scripts/start-verified-venue.py')
        start = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(start)
        launcher = self.root / 'Launch-Server.exe'
        launcher.touch()
        args = SimpleNamespace(verify_only=False, launcher=launcher, launch_plan=original, network_plan=generated,
                               readiness=self.root / 'bound.json', require_distinct_remote_roster=False,
                               retry_output=None, release_report=None, work=self.root / 'work',
                               ready_report=self.root / 'ready-report.json', report=self.root / 'terminal-report.json',
                               start_receipt=None)
        guard = Mock(side_effect=RuntimeError('Windows Firewall may prompt'))
        firewall = SimpleNamespace(WindowsFirewallLaunchError=RuntimeError, require_silent_windows_launch=guard)
        with patch.dict(sys.modules, windows_firewall=firewall), patch.object(start, 'own_launcher_processes') as own:
            with self.assertRaisesRegex(start.field.EvidenceError, 'Windows Firewall may prompt'):
                start.launch(args)
        guard.assert_called_once_with(launcher.parent / 'Runtime' / 'VrCommand.exe')
        own.assert_not_called()
        self.assertFalse(any(path.exists() for path in (args.work, args.ready_report, args.report)))

        digest = 'a' * 64
        release = self.venue_json('release.json', {'scope': 'offline-package-consistency', 'verified': True,
                                                 'windows': {'serverManifestSha256': digest}})
        raw_release = release.read_bytes()
        pinned = self.venue_json('release-preview.json', dict(json.loads(guarded_preview.read_bytes()),
            serverManifestSha256=digest, venueReleaseReportSha256=hashlib.sha256(raw_release).hexdigest()))
        self.venue_check(generated, 'release-bound.json', '--batch', self.root / 'readiness.json',
                         '--launcher-preview', pinned, '--launch-plan', original)
        args.readiness = self.root / 'release-bound.json'
        guard.reset_mock()
        with patch.dict(sys.modules, windows_firewall=firewall), patch.object(start, 'own_launcher_processes') as own:
            with self.assertRaisesRegex(start.field.EvidenceError, 'Supply --release-report'):
                start.launch(args)
            args.release_report = release
            release.write_bytes(raw_release + b'\n')
            with self.assertRaisesRegex(start.field.EvidenceError, 'Use the exact original venue release report'):
                start.launch(args)
            guard.assert_not_called()
            own.assert_not_called()
            release.write_bytes(raw_release)
            with self.assertRaisesRegex(start.field.EvidenceError, 'Windows Firewall may prompt'):
                start.launch(args)
        guard.assert_called_once_with(launcher.parent / 'Runtime' / 'VrCommand.exe')
        self.assertFalse(any(path.exists() for path in (args.work, args.ready_report, args.report)))

        for missing_roles in [('probe',), ('listener',), ('listener', 'probe')]:
            with self.subTest(missing_roles=missing_roles):
                missing_original = json.loads((self.root / 'bound.json').read_bytes())
                for role in missing_roles:
                    missing_original['groups'][0]['udpSourcePreflights'][0][role] = f'private/absent-{role}.json'
                missing_path = self.venue_json('bound-missing-original.json', missing_original)
                failure = subprocess.run([*verify, '--readiness', str(missing_path)], capture_output=True, timeout=15)
                self.assertEqual(1, failure.returncode, failure.stderr)
                details = {'reason': 'unreadable-original', 'missingRole': missing_roles[0]} if len(missing_roles) == 1 else {}
                self.assertEqual({'status': 'udp-evidence-incomplete', 'mode': 'Linked', 'verifiedSources': 1,
                                  'expectedSources': 2, 'unreadablePairs': 1, 'unmatchedPairs': 0,
                                  'pendingSeats': [{'roomId': room, 'seat': seat, 'status': 'missing', **details}
                                                   for room in rooms for seat in (1, 2, 3)]},
                                 json.loads(failure.stdout))
                self.assertNotIn(b'private', failure.stdout)
        for reason, stamp in [('expired', datetime.now(timezone.utc) - timedelta(minutes=31)),
                              ('clock-ahead', datetime.now(timezone.utc) + timedelta(minutes=2)),
                              ('exchange-mismatch', None), ('invalid-report', None)]:
            with self.subTest(reason=reason):
                variant = json.loads((self.root / 'bound.json').read_bytes())
                pair = variant['groups'][0]['udpSourcePreflights'][0]
                listener = json.loads((self.root / pair['listener']).read_text(encoding='utf-8').splitlines()[-1])
                if stamp is not None:
                    listener['completedAtUtc'] = stamp.isoformat()
                elif reason == 'exchange-mismatch':
                    listener['exchangeSha256'] = '0' * 64
                else:
                    listener['matched'] = 0
                pair['listener'] = self.venue_json(f'{reason}-listener.json', listener).name
                path = self.venue_json(f'{reason}-readiness.json', variant)
                rejected = subprocess.run([*verify, '--readiness', str(path)], capture_output=True, timeout=15)
                self.assertEqual(1, rejected.returncode, rejected.stderr)
                diagnostic = json.loads(rejected.stdout)
                self.assertEqual(1, diagnostic['verifiedSources'])
                self.assertEqual(15, len(diagnostic['pendingSeats']))
                self.assertEqual({('invalid-or-expired', reason)}, {(seat['status'], seat['reason']) for seat in diagnostic['pendingSeats']})
                self.assertNotIn(str(self.root).encode(), rejected.stdout)
        conflicting = subprocess.run([*verify, '--readiness', str(missing_path), '--work', str(self.root / 'work')],
                                     capture_output=True, timeout=15)
        self.assertEqual(2, conflicting.returncode, conflicting.stderr)
        self.assertFalse((self.root / 'work').exists())
        bound_path = self.root / 'bound.json'
        bound_bytes = bound_path.read_bytes()
        replacement = self.venue_pair(port, '127.0.0.2', 'replacement')
        legacy = json.loads(bound_bytes)
        legacy['groups'][0].pop('udpSourcePreflightSha256')
        legacy_path = self.venue_json('legacy-readiness.json', legacy)
        for role in ('listener', 'probe'):
            (self.root / first[role]).write_bytes((self.root / replacement[role]).read_bytes())
        try:
            retry_dir = self.root / 'recheck'
            retry_dir.mkdir()
            retry = retry_dir / 'retry.json'
            command = [*verify, '--readiness', str(bound_path), '--retry-output', str(retry)]
            rejected = subprocess.run(command, capture_output=True, timeout=15)
            self.assertEqual(1, rejected.returncode, rejected.stderr)
            diagnostic = json.loads(rejected.stdout)
            self.assertEqual(1, diagnostic['verifiedSources'])
            self.assertTrue(diagnostic['retryReportSaved'])
            self.assertEqual([{'roomId': room, 'seat': seat, 'status': 'invalid-or-expired', 'reason': 'changed-original'}
                              for room in rooms for seat in (1, 2, 3)], diagnostic['pendingSeats'])
            self.assertNotIn(str(self.root).encode(), rejected.stdout)
            retry_bytes = retry.read_bytes()
            retry_doc = json.loads(retry_bytes)
            self.assertFalse(retry_doc['complete'])
            self.assertEqual(original, (retry_dir / retry_doc['launchBinding']['plan']).resolve())
            retained, = retry_doc['retrySources']
            self.assertEqual({role: self.root / name for role, name in second.items()},
                             {role: (retry_dir / name).resolve() for role, name in retained['pair'].items()})
            collision = subprocess.run(command, capture_output=True, timeout=15)
            self.assertEqual(1, collision.returncode)
            self.assertEqual(retry_bytes, retry.read_bytes())
            additions = self.venue_json('replacement-pairs.json', {'version': 1, 'pairs': [replacement]})
            repaired = self.venue_check(generated, 'repaired-after-recheck.json', '--retry-report', retry, '--pairs', additions,
                                        '--launch-plan', original, '--launcher-preview', guarded_preview)
            self.assertTrue(repaired['complete'])
            self.assertEqual(1, repaired['retainedSources'])
            self.assertEqual([replacement, second], repaired['groups'][0]['udpSourcePreflights'])
            self.assertEqual(retry_bytes, retry.read_bytes())
            fixed_output = retry_dir / 'fixed-retry.json'
            fixed = subprocess.run([*verify, '--readiness', str(self.root / 'repaired-after-recheck.json'),
                                    '--retry-output', str(fixed_output)], capture_output=True, timeout=15)
            self.assertEqual(0, fixed.returncode, fixed.stderr)
            self.assertNotIn('retryReportSaved', json.loads(fixed.stdout))
            self.assertFalse(fixed_output.exists())
            spec = importlib.util.spec_from_file_location('field_results', ROOT / 'scripts/verify-field-results.py')
            field = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(field)
            with self.assertRaisesRegex(field.EvidenceError, 'UDP report bytes differ from the original venue preflight'):
                field.read_udp_preflight_batch(bound_path, 'Linked', [rooms])
            accepted = subprocess.run([*verify, '--readiness', str(legacy_path)], capture_output=True, timeout=15)
            self.assertEqual(0, accepted.returncode, accepted.stderr)
        finally:
            for name, data in original_reports.items():
                (self.root / name).write_bytes(data)
        self.assertEqual(bound_bytes, bound_path.read_bytes())
        restored = subprocess.run([*verify, '--readiness', str(bound_path)], capture_output=True, timeout=15)
        self.assertEqual(0, restored.returncode, restored.stderr)
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
        partial_path = self.root / 'missing.json'
        original_partial = partial_path.read_bytes()
        saved, = missing['retrySources']
        self.assertEqual(first, saved['pair'])
        self.assertEqual([hashlib.sha256(original_reports[first[key]]).hexdigest() for key in ('listener', 'probe')], saved['pairSha256'])
        retry = self.venue_check(plan, 'retry.json', '--retry-report', partial_path, '--batch', batch)
        self.assertEqual(1, retry['retainedSources'])
        self.assertEqual(hashlib.sha256(original_partial).hexdigest(), retry['retryReportSha256'])
        self.assertEqual(report['groups'], retry['groups'])
        self.assertEqual(original_partial, partial_path.read_bytes())
        repeated = self.venue_check(plan, 'retry-duplicate.json', '--retry-report', partial_path, '--pairs', manual, status=1)
        self.assertEqual(['duplicate-pair', 'missing'], [row['status'] for row in repeated['groups'][0]['sources']])
        self.assertEqual(0, repeated['retainedSources'])
        (self.root / first['probe']).write_bytes(original_reports[first['probe']] + b'\n\x00')
        changed = self.venue_check(plan, 'retry-changed.json', '--retry-report', partial_path, '--batch', batch, status=1)
        self.assertEqual(['invalid-or-expired', 'verified'], [row['status'] for row in changed['groups'][0]['sources']])
        self.assertEqual(0, changed['retainedSources'])
        (self.root / first['probe']).write_bytes(original_reports[first['probe']])

        def reject_retry(retry_plan, report_path, *flags):
            output = self.root / 'not-written.json'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/check-venue-udp-preflight.py'),
                                     '--network-plan', str(retry_plan), '--output', str(output),
                                     '--retry-report', str(report_path), *map(str, flags)], capture_output=True, text=True, timeout=15)
            self.assertEqual(1, result.returncode, result.stderr)
            self.assertFalse(output.exists())
            self.assertNotIn(str(self.root), result.stderr)
            return result.stderr

        self.assertIn('same original venue network plan', reject_retry(generated, partial_path))
        self.assertIn('incomplete report', reject_retry(plan, self.root / 'retry.json'))
        bound_partial = self.venue_check(plan, 'bound-partial.json', '--pairs', manual, '--launch-plan', original,
                                         '--launcher-preview', guarded_preview, status=1)
        self.assertEqual(1, len(bound_partial['retrySources']))
        self.assertIn('same original Windows plan and preview', reject_retry(plan, self.root / 'bound-partial.json'))
        bound_retry = self.venue_check(plan, 'bound-retry.json', '--retry-report', self.root / 'bound-partial.json', '--batch', batch,
                                       '--launch-plan', original, '--launcher-preview', guarded_preview)
        self.assertEqual(bound['launchBinding'], bound_retry['launchBinding'])
        self.assertEqual(1, bound_retry['retainedSources'])

        old_probe, old_listener = (self.root / first[key] for key in ('probe', 'listener'))
        stale_at = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()
        probe_doc = json.loads(old_probe.read_text(encoding='utf-16'))
        probe_doc['completedAtUtc'] = stale_at
        old_probe.write_text(json.dumps(probe_doc), encoding='utf-16')
        listener_rows = [json.loads(line) for line in old_listener.read_text(encoding='utf-8').splitlines()]
        listener_rows[-1]['completedAtUtc'] = stale_at
        old_listener.write_text(''.join(json.dumps(row) + '\n' for row in listener_rows), encoding='utf-8')
        stale = json.loads(original_partial)
        stale['retrySources'][0]['pairSha256'] = [hashlib.sha256((self.root / first[key]).read_bytes()).hexdigest() for key in ('listener', 'probe')]
        stale_report = self.venue_json('older-retry.json', stale)
        renewed = self.venue_pair(port, '127.0.0.2', 'renewed')
        fresh = self.venue_json('renewed-pairs.json', {'version': 1, 'pairs': [renewed]})
        expired = self.venue_check(plan, 'retry-expired.json', '--retry-report', stale_report, '--batch', batch, status=1)
        self.assertEqual(['invalid-or-expired', 'verified'], [row['status'] for row in expired['groups'][0]['sources']])
        recovered = self.venue_check(plan, 'retry-recovered.json', '--retry-report', self.root / 'retry-expired.json', '--pairs', fresh)
        self.assertEqual([renewed, second], recovered['groups'][0]['udpSourcePreflights'])
        self.assertEqual(1, recovered['retainedSources'])
        old_probe.write_bytes(original_reports[first['probe']])
        old_listener.write_bytes(original_reports[first['listener']])
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

    def test_venue_inbox_pairs_original_exchanges_and_resumes_without_manual_paths(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserved:
            reserved.bind((LOOPBACK, 0))
            port = reserved.getsockname()[1]
        rooms = list(range(1, 6))
        plan = self.venue_json('inbox-network.json', {'version': 1, 'mode': 'Linked',
            'endpoints': [{'roomIds': rooms, 'address': LOOPBACK, 'port': port}],
            'sources': [{'roomId': room, 'seat': seat, 'address': f'127.0.0.{seat + 1}'
                         } for room in rooms for seat in (1, 2)]})
        first = self.venue_pair(port, '127.0.0.2', 'inbox-first', encoding='utf-16')
        second = self.venue_pair(port, '127.0.0.3', 'inbox-second', encoding='utf-8-sig')
        inbox = self.root / '收件箱'
        inbox.mkdir()
        first_pair = {'listener': '104.JSON', 'probe': '200.NDJSON'}
        second_pair = {'listener': '300.ndjson', 'probe': '101.json'}
        for role, name in first_pair.items():
            shutil.copyfile(self.root / first[role], inbox / name)
        shutil.copyfile(self.root / second['probe'], inbox / second_pair['probe'])
        shutil.copyfile(inbox / first_pair['listener'], inbox / 'copy.json')
        (inbox / 'broken.json').write_text('{', encoding='utf-8')
        (inbox / 'notes.txt').write_text('notes', encoding='utf-8')
        (inbox / 'subfolder.json').mkdir()

        invalid = self.venue_check(plan, 'inbox-invalid.json', '--inbox', inbox, status=1)
        first_seats = [{'roomId': room, 'seat': 1} for room in rooms]
        second_seats = [{'roomId': room, 'seat': 2} for room in rooms]
        missing_listener = {'status': 'missing-counterpart', 'files': ['101.json'], 'seats': second_seats, 'missingRole': 'listener'}
        self.assertEqual({'files': 5, 'pairedExchanges': 0, 'issues': [
            {'status': 'invalid-report', 'files': ['broken.json']},
            missing_listener,
            {'status': 'duplicate-role', 'files': ['104.JSON', '200.NDJSON', 'copy.json'], 'seats': first_seats},
        ]}, invalid['inbox'])
        (inbox / 'copy.json').unlink()
        (inbox / 'broken.json').unlink()
        partial = self.venue_check(plan, 'inbox-partial.json', '--inbox', inbox, status=1)
        self.assertEqual((1, 1), (partial['verifiedSources'], partial['inbox']['pairedExchanges']))
        self.assertEqual([missing_listener], partial['inbox']['issues'])

        retry_inbox = self.root / '補件箱'
        retry_inbox.mkdir()
        shutil.copyfile(inbox / second_pair['probe'], retry_inbox / second_pair['probe'])
        shutil.copyfile(self.root / second['listener'], retry_inbox / second_pair['listener'])
        reports = {path: path.read_bytes() for folder in (inbox, retry_inbox)
                   for path in folder.iterdir() if path.is_file()}
        complete = self.venue_check(plan, 'inbox-complete.json', '--inbox', retry_inbox,
                                    '--retry-report', self.root / 'inbox-partial.json')
        self.assertEqual((2, 1), (complete['verifiedSources'], complete['retainedSources']))
        self.assertEqual({'files': 2, 'pairedExchanges': 1, 'issues': []}, complete['inbox'])
        refs = complete['groups'][0]['udpSourcePreflights']
        self.assertEqual([{role: (folder / name).resolve() for role, name in pair.items()}
                          for folder, pair in ((inbox, first_pair), (retry_inbox, second_pair))],
                         [{role: (self.root / name).resolve() for role, name in pair.items()} for pair in refs])
        self.assertEqual(reports, {path: path.read_bytes() for path in reports})
        shutil.copyfile(self.root / second['listener'], inbox / second_pair['listener'])
        original_inbox = {path: path.read_bytes() for path in inbox.iterdir() if path.is_file()}
        same_inbox = self.venue_check(plan, 'same-inbox-complete.json', '--inbox', inbox,
                                      '--retry-report', self.root / 'inbox-partial.json')
        self.assertEqual((2, 1), (same_inbox['verifiedSources'], same_inbox['retainedSources']))
        self.assertEqual({'files': 4, 'pairedExchanges': 2, 'issues': []}, same_inbox['inbox'])
        self.assertEqual(original_inbox, {path: path.read_bytes() for path in original_inbox})

        original_probe = inbox / first_pair['probe']
        original_probe.write_bytes(original_inbox[original_probe] + b'\n')
        changed = self.venue_check(plan, 'same-inbox-changed.json', '--inbox', inbox,
                                   '--retry-report', self.root / 'inbox-partial.json', status=1)
        self.assertEqual(['invalid-or-expired', 'verified'], [row['status'] for row in changed['groups'][0]['sources']])
        self.assertEqual(0, changed['retainedSources'])
        original_probe.write_bytes(original_inbox[original_probe])

        shutil.copyfile(original_probe, inbox / 'duplicate-probe.json')
        duplicate = self.venue_check(plan, 'same-inbox-duplicate.json', '--inbox', inbox,
                                     '--retry-report', self.root / 'inbox-partial.json', status=1)
        self.assertFalse(duplicate['complete'])
        self.assertEqual('duplicate-role', duplicate['inbox']['issues'][0]['status'])
        self.assertEqual(first_seats, duplicate['inbox']['issues'][0]['seats'])

    def test_partial_quest_batch_supplies_only_its_verified_seats_before_launch(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserved:
            reserved.bind((LOOPBACK, 0))
            port = reserved.getsockname()[1]
        rooms = list(range(1, 6))
        plan = self.venue_json('partial-network.json', {'version': 1, 'mode': 'Linked',
            'endpoints': [{'roomIds': rooms, 'address': LOOPBACK, 'port': port}],
            'sources': [{'roomId': room, 'seat': 1, 'address': f'127.0.0.{min(room + 1, 4)}'} for room in rooms]})
        launch_value, preview_value = guarded_documents('Linked', [port])
        launch = self.venue_json('partial-launch.json', launch_value)
        preview = self.venue_json('partial-preview.json', preview_value)
        spec = importlib.util.spec_from_file_location('quest_batch', ROOT / 'scripts/probe-quest-venue.py')
        quest = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(quest)
        binding, _ = quest.launcher_proof(launch, preview, self.root)
        original = self.venue_pair(port, '127.0.0.2', 'quest-original')
        recovered = self.venue_pair(port, '127.0.0.3', 'quest-recovered')
        windows = self.venue_pair(port, '127.0.0.4', 'windows-peer')
        manual = self.venue_json('windows-pairs.json', {'version': 1, 'pairs': [windows]})

        def verified_row(room, pair, stage):
            metadata, probe = quest.pair_metadata(self.root / pair['listener'], self.root / pair['probe'])
            return dict(roomId=room, seat=1, complete=True, stage=stage,
                        exchangeSha256=json.loads(probe)['exchangeSha256'], **pair, **metadata)

        first = verified_row(1, original, 'verified')
        failed = dict(roomId=2, seat=1, complete=False, stage='probe')
        document = dict(version=1, scope='quest-udp-preflight-only', mode='Linked',
                        complete=False, expectedSeats=2, verifiedSeats=1, sampleCount=2, sampleTimeoutMs=900,
                        groups=[dict(roomIds=rooms, complete=False, seats=[first, failed])], **binding)
        batch = self.venue_json('partial-quest.json', document)
        options = ('--launch-plan', launch, '--launcher-preview', preview)
        readiness = 'partial-readiness.json'
        report = self.venue_check(plan, readiness, '--pairs', manual, '--batch', batch, *options, status=1)
        self.assertEqual((False, 3, 2), (report['complete'], report['expectedSources'], report['verifiedSources']))
        self.assertEqual(['verified', 'missing', 'verified'], [row['status'] for row in report['groups'][0]['sources']])
        self.assertEqual([original, windows], [row['pair'] for row in report['retrySources']])
        verify = [sys.executable, str(ROOT / 'scripts/start-verified-venue.py'), '--verify-only',
                  '--launch-plan', str(launch), '--network-plan', str(plan), '--readiness']
        saved_directory = self.root / 'rechecked'
        saved_directory.mkdir()
        saved = saved_directory / 'retry.json'
        original_readiness = (self.root / readiness).read_bytes()
        blocked = subprocess.run([*verify, str(self.root / readiness), '--retry-output', str(saved)],
                                 capture_output=True, timeout=15)
        self.assertEqual(1, blocked.returncode, blocked.stderr)
        self.assertTrue(blocked.stdout, blocked.stderr)
        self.assertEqual({'status': 'udp-evidence-incomplete', 'mode': 'Linked', 'verifiedSources': 2,
                          'expectedSources': 3, 'unreadablePairs': 0, 'unmatchedPairs': 0,
                          'pendingSeats': [{'roomId': 2, 'seat': 1, 'status': 'missing'}], 'retryReportSaved': True},
                         json.loads(blocked.stdout))
        self.assertEqual(original_readiness, (self.root / readiness).read_bytes())
        saved_report = json.loads(saved.read_bytes())
        self.assertFalse(saved_report['complete'])
        self.assertEqual([self.root / p['probe'] for p in (original, windows)], [
            (saved.parent / row['pair']['probe']).resolve() for row in saved_report['retrySources']])
        self.assertEqual(launch, (saved.parent / saved_report['launchBinding']['plan']).resolve())
        spec = importlib.util.spec_from_file_location('start_verified_venue', ROOT / 'scripts/start-verified-venue.py')
        start = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(start)
        with patch.object(start, 'own_launcher_processes') as own, patch.object(start.subprocess, 'Popen') as child:
            with self.assertRaisesRegex(start.field.EvidenceError, 'Provide a complete venue UDP readiness report'):
                start.launch(SimpleNamespace(readiness=saved, verify_only=False))
        own.assert_not_called()
        child.assert_not_called()

        complete_batch = self.venue_json('recovered-quest.json', {
            **document, 'complete': True, 'verifiedSeats': 2, 'groups': [{
                'roomIds': rooms, 'complete': True, 'seats': [dict(first, stage='reused'), verified_row(2, recovered, 'verified')],
                'udpSourcePreflights': [original, recovered]}]})
        before = {path.name: path.read_bytes() for path in self.root.iterdir() if path.is_file()}
        complete = self.venue_check(plan, 'complete-readiness.json', '--retry-report', saved,
                                    '--batch', complete_batch, *options)
        self.assertEqual((True, 3, 2), (complete['complete'], complete['verifiedSources'], complete['retainedSources']))
        opened = subprocess.run([*verify, str(self.root / 'complete-readiness.json')], capture_output=True, timeout=15)
        self.assertEqual(0, opened.returncode, opened.stderr)
        self.assertEqual(before, {key: (self.root / key).read_bytes() for key in before})

        swapped = self.venue_json('swapped-quest.json', {**document, 'groups': [{
            'roomIds': rooms, 'complete': False, 'seats': [verified_row(1, recovered, 'verified'), failed]}]})
        refused = self.venue_check(plan, 'swapped-readiness.json', '--batch', swapped, *options, status=1)
        self.assertEqual((0, 1), (refused['verifiedSources'], refused['unmatchedPairs']))
        changed = self.root / original['probe']
        changed.write_bytes(before[changed.name] + b'\n')
        changed_readiness = subprocess.run([*verify, str(saved)], capture_output=True, timeout=15)
        self.assertEqual(1, changed_readiness.returncode, changed_readiness.stderr)
        verdict = json.loads(changed_readiness.stdout)
        self.assertEqual(1, verdict['verifiedSources'])
        self.assertEqual([{'roomId': 1, 'seat': 1, 'status': 'invalid-or-expired', 'reason': 'changed-original'},
                          {'roomId': 2, 'seat': 1, 'status': 'missing'}], verdict['pendingSeats'])
        stale = self.venue_check(plan, 'changed-readiness.json', '--batch', batch, *options, status=1)
        self.assertEqual('changed-original', stale['groups'][0]['sources'][0]['reason'])
        probe = json.loads(before[changed.name])
        probe['samples'][0]['roundTripMs'] = 901
        changed.write_text(json.dumps(probe), encoding='utf-8')
        wrong_deadline = self.venue_json('slow-quest.json', {**document, 'groups': [{
            'roomIds': rooms, 'complete': False, 'seats': [verified_row(1, original, 'verified'), failed]}]})
        slow = self.venue_check(plan, 'slow-readiness.json', '--batch', wrong_deadline, *options, status=1)
        self.assertEqual('invalid-report', slow['groups'][0]['sources'][0]['reason'])

    def test_offline_inspection_preserves_unmatched_inputs_when_every_planned_source_is_verified(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserved:
            reserved.bind((LOOPBACK, 0))
            port = reserved.getsockname()[1]
        rooms = list(range(1, 6))
        plan = self.venue_json('complete-roster-network.json', {'version': 1, 'mode': 'Linked',
            'endpoints': [{'roomIds': rooms, 'address': LOOPBACK, 'port': port}],
            'sources': [{'roomId': room, 'seat': 1, 'address': '127.0.0.2'} for room in rooms]})
        launch_value, preview_value = guarded_documents('Linked', [port])
        launch = self.venue_json('unmatched-launch.json', launch_value)
        preview = self.venue_json('unmatched-preview.json', preview_value)
        planned = self.venue_pair(port, '127.0.0.2', 'planned')
        unmatched = self.venue_pair(port, '127.0.0.3', 'unmatched')
        pairs = self.venue_json('candidate-pairs.json', {'version': 1, 'pairs': [planned, unmatched]})
        options = ('--launch-plan', launch, '--launcher-preview', preview)
        first = self.root / 'unmatched-readiness.json'
        report = self.venue_check(plan, first.name, '--pairs', pairs, *options, status=1)
        self.assertEqual((False, 1, 1), (report['complete'], report['verifiedSources'], report['unmatchedPairs']))

        saved = self.root / 'rechecked-unmatched.json'
        command = [sys.executable, str(ROOT / 'scripts/start-verified-venue.py'), '--verify-only',
                   '--launch-plan', str(launch), '--network-plan', str(plan), '--readiness', str(first),
                   '--retry-output', str(saved)]
        rejected = subprocess.run(command, capture_output=True, timeout=15)
        self.assertEqual(1, rejected.returncode, rejected.stderr)
        detail = json.loads(rejected.stdout)
        self.assertEqual(('udp-evidence-incomplete', 1, [], True),
                         (detail['status'], detail['unmatchedPairs'], detail['pendingSeats'], detail['retryReportSaved']))
        retained = json.loads(saved.read_bytes())
        self.assertEqual((False, 1, planned), (retained['complete'], retained['unmatchedPairs'], retained['retrySources'][0]['pair']))
        complete = self.venue_check(plan, 'resolved-readiness.json', '--retry-report', saved, *options)
        self.assertEqual((True, 1, 0), (complete['complete'], complete['retainedSources'], complete['unmatchedPairs']))

        inbox = self.root / 'inbox'
        inbox.mkdir()
        shutil.copyfile(self.root / unmatched['probe'], inbox / 'unpaired-probe.json')
        only_planned = self.venue_json('planned-pairs.json', {'version': 1, 'pairs': [planned]})
        inbox_readiness = self.root / 'inbox-readiness.json'
        inbox_report = self.venue_check(plan, inbox_readiness.name, '--pairs', only_planned, '--inbox', inbox, *options, status=1)
        inbox_retry = self.root / 'rechecked-inbox.json'
        inputs = command[:-3] + [str(inbox_readiness), '--retry-output', str(inbox_retry)]
        result = subprocess.run(inputs, capture_output=True, timeout=15)
        self.assertEqual(1, result.returncode, result.stderr)
        detail = json.loads(result.stdout)
        self.assertEqual(('udp-evidence-incomplete', 1, []), (detail['status'], detail['inboxIssues'], detail['pendingSeats']))
        self.assertEqual(inbox_report['inbox'], json.loads(inbox_retry.read_bytes())['inbox'])

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
        inbox = self.root / 'independent-inbox'
        inbox.mkdir()
        for index, pair in enumerate(pairs):
            shutil.copyfile(self.root / pair['listener'], inbox / f'{len(pairs) - index}.ndjson')
            shutil.copyfile(self.root / pair['probe'], inbox / f'{index + 1}.json')
        collected = self.venue_check(generated, 'independent-inbox.json', '--inbox', inbox,
                                     '--launcher-preview', preview, '--launch-plan', launch)
        self.assertEqual({'files': 10, 'pairedExchanges': 5, 'issues': []}, collected['inbox'])
        self.assertEqual([group['sources'] for group in report['groups']], [group['sources'] for group in collected['groups']])
        for old, new in zip(report['groups'], collected['groups'], strict=True):
            for role, path in old['udpSourcePreflights'][0].items():
                self.assertEqual((self.root / path).read_bytes(),
                                 (self.root / new['udpSourcePreflights'][0][role]).read_bytes())
        plan_value['sources'][4]['address'] = '127.0.0.3'
        wrong = self.venue_json('wrong-source.json', plan_value)
        invalid = self.venue_check(wrong, 'unmatched.json', '--pairs', manifest, status=1)
        self.assertEqual((1, 4), (invalid['unmatchedPairs'], invalid['verifiedSources']))
        self.assertEqual('missing', invalid['groups'][4]['sources'][0]['status'])

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
                                  env=self.environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as probe:
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
