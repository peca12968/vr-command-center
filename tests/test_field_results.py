from copy import deepcopy
import importlib.util
import ipaddress
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/verify-field-results.py'
spec = importlib.util.spec_from_file_location('field_results', SCRIPT)
field = importlib.util.module_from_spec(spec)
spec.loader.exec_module(field)


def id_for(number):
    return str(uuid.UUID(int=number))


def fixture(*, remote=True):
    server_ip = ipaddress.IPv4Address('192.168.5.10')
    peer = ipaddress.IPv4Address('192.168.5.20') if remote else server_ip
    session_id, stream = id_for(1), id_for(2)
    row = {name: 0 for name in field.COMBAT} | {'health': 100, 'accuracyPercent': 0, 'roomId': 1}
    owners = [{'id': id_for(i), 'admissionId': id_for(i + 10), 'roomId': 1} for i in (3, 4)]
    session = {'id': session_id, 'mode': 'Independent', 'state': 'Ended', 'sequence': 9, 'roomIds': [1], 'players': owners}
    stats = {'sessionId': session_id, 'throughSequence': 9, 'origin': None, 'pendingTelemetry': False,
             'players': [dict(row, playerId=p['id']) for p in owners]}
    launcher = {'schemaVersion': 1, 'status': 'sealed-stopped', 'complete': True, 'childExited': True,
                'cleanupCompleted': True, 'exitCode': 0, 'childPid': 100, 'sessionId': session_id, 'streamId': stream,
                'udpBinding': {'processId': 100, 'port': 7777, 'address': str(server_ip)},
                'finalWorld': {'complete': True, 'acceptedSequence': 80, 'header': {
                    'sessionId': session_id, 'streamId': stream, 'roomIds': [1], 'origin': 'Simulation'}},
                'finalCombatStream': {'sealed': True, 'acceptedSequence': 0, 'streamId': stream, 'origin': 'Simulation'}}
    session.update(combatStream=deepcopy(launcher['finalCombatStream']),
                   startedAtUtc='2026-11-09T00:00:00+00:00', endedAtUtc='2026-11-09T00:01:00+00:00')
    endpoint = {'version': 1, 'sessionEnded': True, 'sessionId': session_id, 'streamId': stream,
                'port': 7777, 'address': str(server_ip)}
    server = 'VR_NETWORK_STARTED role=Server started=True background=True port=7777\n'
    clients = []
    for i, (owner, address) in enumerate(zip(owners, (server_ip, peer)), 1):
        server += f'VR_SERVER_ADMISSION_APPROVED id={i}\nVR_SERVER_PEER id={i} endpoint={address}:{5000+i}\nVR_SERVER_DEBRIEF_ACK id={i}\n'
        result = dict(row, version=1, playerId=owner['id'], admissionId=owner['admissionId'], sessionId=session_id,
                      origin='Simulation', streamId=stream, throughSequence=9, finalStreamSequence=0, worldSequence=80)
        clients.append((address, f'VR_CLIENT_CONNECTED id={i}\nVR_CLIENT_DEBRIEF_FINAL {json.dumps(result)}\nVR_CLIENT_DISCONNECTED\n'))
    return ['direct-lan' if remote else 'same-host', {server_ip}, launcher, session, stats, endpoint, server, clients]


def venue_fixture(root, mode, *, remote=False):
    def write_json(path, value):
        path.write_text(json.dumps(value), encoding='utf-8')

    server_ip, remote_ip = '192.168.5.10', '192.168.5.20'
    groups = [[1, 2, 3, 4, 5]] if mode == 'Linked' else [[room] for room in range(1, 6)]
    batch = {'requestId': id_for(1000), 'recordedAtUtc': '2026-11-09T00:01:00+00:00', 'sessions': []}
    manifest = {'version': 1, 'mode': mode, 'topology': 'direct-lan' if remote else 'same-host',
                'serverIps': [server_ip], 'closure': 'closure.json', 'sessions': []}
    for rooms in groups:
        prefix = f'Room {rooms[0]}'
        _, _, launcher, session, stats, endpoint, _, _ = fixture(remote=False)
        session_id, stream = id_for(100 + rooms[0]), id_for(200 + rooms[0])
        port = 7776 + rooms[0]
        launcher.update(sessionId=session_id, streamId=stream)
        launcher['udpBinding']['port'] = port
        launcher['finalWorld']['header'].update(sessionId=session_id, streamId=stream, roomIds=rooms)
        launcher['finalCombatStream']['streamId'] = stream
        session.update(id=session_id, mode=mode, roomIds=rooms, players=[], combatStream=launcher['finalCombatStream'],
                       mission={'definition': {'name': prefix}})
        stats.update(sessionId=session_id, players=[])
        endpoint.update(sessionId=session_id, streamId=stream, port=port)
        batch['sessions'].append({'sessionId': session_id, 'roomIds': rooms, 'missionName': prefix,
                                  'appliedAtSequence': 8, 'combat': 'Sealed', 'world': 'Sealed',
                                  'replay': {'streamId': stream, 'throughSequence': 80}})
        entry = {'evidenceZip': prefix + '.zip', 'launcherReport': prefix + ' launcher.json',
                 'serverLog': prefix + ' server.log', 'players': []}
        manifest['sessions'].append(entry)
        server = f'VR_NETWORK_STARTED role=Server started=True background=True port={port}\n'
        for room in rooms:
            for seat in range(5):
                connection = room * 5 + seat
                player, admission = id_for(300 + connection), id_for(400 + connection)
                peer = remote_ip if remote and room == 5 and seat == 4 else server_ip
                session['players'].append({'id': player, 'admissionId': admission, 'roomId': room, 'seat': seat})
                row = {field_name: 0 for field_name in field.COMBAT} | {'playerId': player, 'roomId': room, 'health': 100, 'accuracyPercent': 0}
                stats['players'].append(row)
                result = dict(row, version=1, admissionId=admission, sessionId=session_id, origin='Simulation',
                              streamId=stream, throughSequence=9, finalStreamSequence=0, worldSequence=80)
                log = f'Player {connection}.log'
                entry['players'].append({'address': peer, 'log': log})
                (root / log).write_text(f'VR_CLIENT_CONNECTED id={connection}\nVR_CLIENT_DEBRIEF_FINAL {json.dumps(result)}\nVR_CLIENT_DISCONNECTED\n',
                                        encoding='utf-8')
                server += (f'VR_SERVER_ADMISSION_APPROVED id={connection}\nVR_SERVER_PEER id={connection} endpoint={peer}:{5000 + connection}\n'
                           f'VR_SERVER_DEBRIEF_ACK id={connection}\n')
        write_json(root / entry['launcherReport'], launcher)
        (root / entry['serverLog']).write_text(server, encoding='utf-8')
        with zipfile.ZipFile(root / entry['evidenceZip'], 'w') as archive:
            for name, record in [('session.json', session), ('statistics.json', stats), ('endpoint.json', endpoint)]:
                archive.writestr(name, json.dumps(record))
    write_json(root / 'closure.json', {'batch': batch})
    path = root / 'venue.json'
    write_json(path, manifest)
    return path, manifest, batch


class FieldResultsTests(unittest.TestCase):
    def test_direct_consistency_does_not_certify_physical_hosts(self):
        data = fixture()
        report = field.verify(*data)
        self.assertEqual(report['serverAcknowledgements'], 2)
        self.assertEqual(report['distinctAddressesOutsideDeclaredServer'], 1)
        self.assertFalse(report['physicalHostsVerified'])
        self.assertFalse(report['networkCapacityAccepted'])
        self.assertNotIn('192.168', json.dumps(report))
        self.assertNotIn(data[3]['id'], json.dumps(report))

    def test_same_host_cannot_be_relabelled_direct(self):
        data = fixture(remote=False)
        self.assertTrue(field.verify(*data)['consistent'])
        data[0] = 'direct-lan'
        with self.assertRaisesRegex(field.EvidenceError, 'Direct LAN'):
            field.verify(*data)
        data = fixture()
        data[1].add(data[7][1][0])
        with self.assertRaisesRegex(field.EvidenceError, 'Direct LAN'):
            field.verify(*data)

    def test_requires_observed_peers_and_acknowledgements(self):
        for old, new in [('192.168.5.20:5002', 'unavailable'), ('192.168.5.20:5002', '192.168.5.30:5002'),
                         ('VR_SERVER_DEBRIEF_ACK id=2', 'VR_SERVER_DEBRIEF_TIMEOUT id=2'),
                         ('VR_SERVER_DEBRIEF_ACK id=2', 'VR_SERVER_DEBRIEF_ACK id=1'),
                         ('VR_SERVER_DEBRIEF_ACK id=2', ''), ('VR_SERVER_ADMISSION_APPROVED id=2', '')]:
            with self.subTest(new=new):
                data = fixture()
                data[6] = data[6].replace(old, new)
                with self.assertRaises(field.EvidenceError):
                    field.verify(*data)

    def test_reconnect_uses_final_connection_and_its_peer(self):
        data = fixture()
        address, log = data[7][1]
        data[7][1] = (address, 'VR_CLIENT_CONNECTED id=8\nVR_CLIENT_DISCONNECTED\n' + log)
        first, rest = data[6].split('\n', 1)
        data[6] = first + '\nVR_SERVER_ADMISSION_APPROVED id=8\nVR_SERVER_PEER id=8 endpoint=unavailable\n' + rest
        self.assertEqual(field.verify(*data)['players'], 2)
        data[7][1] = (address, log.removesuffix('VR_CLIENT_DISCONNECTED\n'))
        with self.assertRaisesRegex(field.EvidenceError, 'terminal disconnect'):
            field.verify(*data)

    def test_requires_current_admission_and_all_three_sequence_boundaries(self):
        base = fixture()
        for old, new in [(id_for(14), id_for(999)), ('"worldSequence": 80', '"worldSequence": 79'),
                         ('"finalStreamSequence": 0', '"finalStreamSequence": 1'),
                         ('"throughSequence": 9', '"throughSequence": 8'), ('"health": 100', '"health": 80')]:
            with self.subTest(old=old):
                data = deepcopy(base)
                address, log = data[7][1]
                data[7][1] = (address, log.replace(old, new))
                with self.assertRaises(field.EvidenceError):
                    field.verify(*data)

    def test_requires_owned_binding_and_both_seals(self):
        for part, key, value in [(('finalWorld',), 'complete', False), (('finalCombatStream',), 'sealed', False),
                                 (('udpBinding',), 'processId', 101), ((), 'childExited', False)]:
            data = fixture()
            report = data[2][part[0]] if part else data[2]
            report[key] = value
            with self.assertRaises(field.EvidenceError):
                field.verify(*data)
        data = fixture()
        data[5]['port'] = 7778
        with self.assertRaisesRegex(field.EvidenceError, 'Published endpoint'):
            field.verify(*data)
        data = fixture()
        data[6] = data[6].replace('port=7777', 'port=7778')
        with self.assertRaisesRegex(field.EvidenceError, 'Server log startup'):
            field.verify(*data)
        data = fixture()
        data[3]['combatStream']['acceptedSequence'] = 1
        with self.assertRaisesRegex(field.EvidenceError, 'combat seals'):
            field.verify(*data)

    def test_nonempty_combat_and_decimal_accuracy(self):
        data = fixture()
        data[2]['finalCombatStream']['acceptedSequence'] = data[3]['combatStream']['acceptedSequence'] = 4
        data[4]['origin'] = 'Simulation'
        data[4]['players'][0].update(field.read_json('{"ammoUsed":3,"shotsHit":1,"accuracyPercent":33.33}'))
        for index, (address, log) in enumerate(data[7]):
            log = log.replace('"finalStreamSequence": 0', '"finalStreamSequence": 4')
            if index == 0:
                log = log.replace('"ammoUsed": 0', '"ammoUsed": 3').replace('"shotsHit": 0', '"shotsHit": 1').replace('"accuracyPercent": 0', '"accuracyPercent": 33.33')
            data[7][index] = (address, log)
        self.assertEqual(field.verify(*data)['combatSequence'], 4)
        data[4]['origin'] = None
        with self.assertRaisesRegex(field.EvidenceError, 'nonempty combat'):
            field.verify(*data)

    def test_cli_success_and_private_failure_diagnostics(self):
        topology, ips, launcher, session, stats, endpoint, server, clients = fixture()
        with tempfile.TemporaryDirectory(prefix='field-check-') as directory:
            root = Path(directory)
            command = [sys.executable, str(SCRIPT), '--topology', topology, '--server-ip', str(next(iter(ips)))]
            for option, value in [('launcher-report', launcher), ('session', session), ('statistics', stats), ('endpoint', endpoint), ('server-log', server)]:
                path = root / option
                path.write_text(value if type(value) is str else json.dumps(value), encoding='utf-8')
                command += ['--' + option, str(path)]
            for number, (address, log) in enumerate(clients, 1):
                path = root / f'Player {number}.log'
                path.write_text(log, encoding='utf-8')
                command += ['--player', str(address), str(path)]
            success = subprocess.run(command, capture_output=True, text=True, check=True)
            self.assertTrue(json.loads(success.stdout)['consistent'])
            (root / 'server-log').write_text(server.replace('192.168.5.20', '192.168.5.50'), encoding='utf-8')
            failure = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(failure.returncode, 1)
            self.assertEqual(failure.stdout, '')
            self.assertNotIn('192.168', failure.stderr)
            self.assertNotIn(directory, failure.stderr)

    def test_venue_checks_all_original_seats_in_both_modes(self):
        for mode in ('Linked', 'Independent'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                path, _, _ = venue_fixture(Path(directory), mode, remote=True)
                report = field.verify_venue(path)
                self.assertEqual(report['players'], report['serverAcknowledgements'])
                self.assertEqual(report['players'], 25)
                self.assertEqual([row['players'] for row in report['rooms']], [5] * 5)
                self.assertEqual([row['playersOutsideDeclaredServer'] for row in report['rooms']], [0, 0, 0, 0, 1])
                self.assertFalse(report['physicalHostsVerified'])
                self.assertFalse(report['networkCapacityAccepted'])
                self.assertNotIn('192.168', json.dumps(report))

    def test_venue_rejects_changed_batch_source_or_missing_room(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, batch = venue_fixture(root, 'Independent')
            for patch in ('batch-time', 'seal-tail', 'omitted-room', 'mixed-session', 'reused-log'):
                with self.subTest(patch=patch):
                    modified, closure = deepcopy(manifest), deepcopy(batch)
                    if patch == 'batch-time':
                        closure['recordedAtUtc'] = '2026-11-09T00:02:00+00:00'
                    elif patch == 'seal-tail':
                        closure['sessions'][4]['replay']['throughSequence'] = 81
                    elif patch == 'omitted-room':
                        modified['sessions'].pop()
                    elif patch == 'mixed-session':
                        closure['sessions'][4]['sessionId'] = id_for(999)
                    else:
                        modified['sessions'][4]['players'][0]['log'] = modified['sessions'][0]['players'][0]['log']
                    path.write_text(json.dumps(modified), encoding='utf-8')
                    (root / 'closure.json').write_text(json.dumps({'batch': closure}), encoding='utf-8')
                    with self.assertRaises(field.EvidenceError):
                        field.verify_venue(path)

    def test_venue_rejects_duplicate_seat_and_archive_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Linked')
            archive_path = root / manifest['sessions'][0]['evidenceZip']
            with zipfile.ZipFile(archive_path) as archive:
                records = {name: json.loads(archive.read(name)) for name in archive.namelist()}
            records['session.json']['players'][1]['seat'] = 0
            with zipfile.ZipFile(archive_path, 'w') as archive:
                for name, record in records.items():
                    archive.writestr(name, json.dumps(record))
            with self.assertRaisesRegex(field.EvidenceError, 'room seat'):
                field.verify_venue(path)
            with zipfile.ZipFile(archive_path, 'a') as archive:
                archive.writestr('other/session.json', '{}')
            with self.assertRaisesRegex(field.EvidenceError, 'exactly the three'):
                field.verify_venue(path)

    def test_venue_cli_does_not_treat_same_host_as_direct_lan(self):
        with tempfile.TemporaryDirectory() as directory:
            path, manifest, _ = venue_fixture(Path(directory), 'Independent')
            command = [sys.executable, str(SCRIPT), '--venue-manifest', str(path)]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout)['serverAcknowledgements'], 25)
            manifest['topology'] = 'direct-lan'
            path.write_text(json.dumps(manifest), encoding='utf-8')
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, '')
            self.assertIn('outside the declared server addresses', result.stderr)
            self.assertNotIn(directory, result.stderr)
            self.assertNotIn('192.168', result.stderr)


if __name__ == '__main__':
    unittest.main()
