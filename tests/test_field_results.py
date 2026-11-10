import asyncio
import base64
from contextlib import redirect_stderr
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import importlib.util
import ipaddress
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import uuid
import zipfile
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/verify-field-results.py'
spec = importlib.util.spec_from_file_location('field_results', SCRIPT)
field = importlib.util.module_from_spec(spec)
spec.loader.exec_module(field)
capture_spec = importlib.util.spec_from_file_location('quest_capture', SCRIPT.with_name('capture-quest-field-log.py'))
capture_tool = importlib.util.module_from_spec(capture_spec)
capture_spec.loader.exec_module(capture_tool)
HAS_POWERSHELL = shutil.which('powershell.exe') or shutil.which('pwsh')


def id_for(number):
    return str(uuid.UUID(int=number))


def logcat_line(message, pid=7342, tag='Unity'):
    return f'11-09 14:30:00.000 {pid:5} 14325 I {tag:8}: {message}\n'


def quest_logcat(log, port=7777, pid=7342):
    return ('--------- beginning of main\n'
            + logcat_line('VR_CLIENT_CONNECTED id=99', pid, tag='Other')
            + logcat_line(f'VR_NETWORK_STARTED role=Client started=True background=False port={port}', pid)
            + logcat_line('UnityEngine.DebugLogHandler:Internal_Log(LogType, LogOption, String, Object)', pid)
            + ''.join(logcat_line(line, pid) for line in log.splitlines()))


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


def world_journal(path, world, *, header_changes=None, combat=0, active=True, sealed=True, end_sequence=8, players=None,
                  preparing_sequence=7, running_sequence=7, capture_start='2026-11-09T00:00:00+00:00', edit_packet=None):
    def record(tag, body):
        payload = bytes([tag]) + body
        return struct.pack('<i', len(payload)) + payload + hashlib.sha256(payload).digest()

    count = world['acceptedSequence']
    world['header'].update(schemaVersion=1, captureStartedAtUtc=capture_start)
    world['header'].setdefault('calibration', 'uncalibrated-vr')
    header = dict(world['header'], **(header_changes or {}))
    raw = [b'VRWORLD1', record(0, json.dumps(header).encode())]
    for number in range(1, count + 1):
        phase = 'Ended' if number == count else 'Running' if active and number > 1 else 'Preparing'
        packet = {'sequence': number, 'observedSequence': {'Preparing': preparing_sequence, 'Running': running_sequence, 'Ended': end_sequence}[phase],
                  'elapsedMilliseconds': number * 100, 'suspended': False, 'throughCombatSequence': combat,
                  'frame': {'phase': phase, 'tick': number if phase == 'Running' else 0}}
        if players is not None:
            packet['frame']['players'] = players(number, phase)
        if edit_packet is not None:
            edit_packet(packet)
        raw += [record(1, json.dumps(packet).encode()), record(2, struct.pack('<q', number))]
    duration = packet['elapsedMilliseconds']
    world.update(durationMilliseconds=duration, capturedAtUtc=(datetime.fromisoformat(capture_start) + timedelta(milliseconds=duration)).isoformat())
    if sealed:
        raw += [record(3, struct.pack('<q', count)), record(4, struct.pack('<q', count))]
    path.write_bytes(b''.join(raw))


def combat_journal(path, launcher, records=(), *, sealed=True, receipt=None):
    def frame(payload):
        return struct.pack('<i', len(payload)) + payload + hashlib.sha256(payload).digest()

    def guid(value):
        return uuid.UUID(value).bytes_le if value else bytes(16)

    origin = launcher['finalCombatStream']['origin'].encode('ascii')
    header = (struct.pack('<Bi', 1, 1) + guid(launcher['sessionId']) + guid(launcher['streamId'])
              + bytes([len(origin)]) + origin)
    raw = [frame(header)]
    if records:
        events = b''.join(struct.pack('<qq16sB16s16s16si', sequence, 7, guid(id_for(900 + sequence)),
                                      kind, guid(player), guid(shot), guid(enemy), damage)
                          for sequence, (kind, player, shot, enemy, damage) in enumerate(records, 1))
        raw.append(frame(struct.pack('<Bi', 2, len(records)) + events))
        raw.append(frame(struct.pack('<Bq16s', 4, len(records), guid(receipt or id_for(900 + len(records))))))
    raw.append(frame(struct.pack('<Bq', 3, len(records))))
    if sealed:
        raw.append(frame(b'\x05'))
    path.write_bytes(b''.join(raw))


class PlayerSourceEvidenceTests(unittest.TestCase):
    desktop_startup = 'VR_NETWORK_STARTED role=Client started=True background=True port=7777\n'

    @classmethod
    def openxr_startup(cls, runtime):
        return ('VR_OPENXR_STARTUP status=requested\n'
                f'[XR] [123] [01:09:33.229][Info   ] Runtime Name: {runtime}\n'
                'VR_OPENXR_STARTUP status=active\n' + cls.desktop_startup)

    def test_windows_mock_and_other_runtime_are_distinct_from_desktop_and_quest(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / 'original.worldlog'
            data = fixture()
            owners = data[3]['players']
            for index, owner in enumerate(owners):
                owner.update(seat=index, headset='Quest3')
            (desktop_ip, desktop_log), (peer_ip, peer_log) = data[-1]
            rows = [{'id': owner['id'], 'roomId': 1, 'connected': True, 'rig': {'kind': kind}}
                    for owner, kind in zip(owners, ('Simulated', 'Tracked'), strict=True)]
            world_journal(journal, data[2]['finalWorld'], players=lambda _, phase: rows if phase == 'Running' else [])
            cases = [('windows-openxr-mock-tracked', [(peer_ip, self.openxr_startup('Unity Mock Runtime') + peer_log)], []),
                     ('windows-openxr-tracked', [(peer_ip, self.openxr_startup('Example private runtime') + peer_log)], []),
                     ('quest-logcat-tracked', [], [(peer_ip, quest_logcat(peer_log), 7342)])]
            for expected, windows, quest in cases:
                with self.subTest(expected=expected):
                    data[-1] = [(desktop_ip, self.desktop_startup + desktop_log), *windows]
                    report = field.verify(*data, quest_player_logs=quest, world_journal=journal, verify_player_sources=True)
                    self.assertEqual([{'roomId': 1, 'seat': 1, 'source': 'windows-desktop-simulated', 'rigKind': 'Simulated', 'runningFrames': 78},
                                      {'roomId': 1, 'seat': 2, 'source': expected, 'rigKind': 'Tracked', 'runningFrames': 78}], report['playerSources'])
                    self.assertFalse(report['physicalHostsVerified'])
                    self.assertNotIn('Example private runtime', json.dumps(report))
                    self.assertNotIn(owners[1]['id'], json.dumps(report))

    def test_tracked_claim_requires_matching_active_frames_and_original_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / 'original.worldlog'
            data = fixture()
            owners = data[3]['players']
            for index, owner in enumerate(owners):
                owner['seat'] = index
            (desktop_ip, desktop_log), (peer_ip, peer_log) = data[-1]
            windows = self.openxr_startup('Unity Mock Runtime')
            rows = [{'id': owner['id'], 'roomId': 1, 'connected': True, 'rig': {'kind': kind}}
                    for owner, kind in zip(owners, ('Simulated', 'Tracked'), strict=True)]
            for startup, second, error in (
                (windows.replace('port=7777', 'port=7778'), rows[1], 'original desktop or OpenXR startup'),
                (self.desktop_startup, rows[1], 'rig differs'),
                (windows, dict(rows[1], rig={'kind': 'Simulated'}), 'rig differs'),
                (windows, dict(rows[1], connected=False), 'lacks an active accepted pose'),
                (windows, dict(rows[1], roomId=2), 'room or rig differs'),
            ):
                with self.subTest(error=error, startup=startup, second=second):
                    data[-1] = [(desktop_ip, self.desktop_startup + desktop_log), (peer_ip, startup + peer_log)]
                    world_journal(journal, data[2]['finalWorld'], players=lambda _, phase: [rows[0], second] if phase == 'Running' else rows)
                    with self.assertRaisesRegex(field.EvidenceError, error):
                        field.verify(*data, world_journal=journal, verify_player_sources=True)
                    self.assertNotIn('playerSources', field.verify(*data, world_journal=journal))
            with self.assertRaisesRegex(field.EvidenceError, 'requires the original closed world journal'):
                field.verify(*data, verify_player_sources=True)


def venue_fixture(root, mode, *, remote=False, quest_per_room=0, with_journals=False, mr_rooms=()):
    def write_json(path, value):
        path.write_text(json.dumps(value), encoding='utf-8')

    server_ip, remote_ip = '192.168.5.10', '192.168.5.20'
    groups = [[1, 2, 3, 4, 5]] if mode == 'Linked' else [[room] for room in range(1, 6)]
    batch = {'requestId': id_for(1000), 'recordedAtUtc': '2026-11-09T00:01:00+00:00', 'sessions': []}
    manifest = {'version': 1, 'mode': mode, 'topology': 'direct-lan' if remote else 'same-host',
                'serverIps': [server_ip], 'closure': 'closure.json', 'sessions': []}
    for rooms in groups:
        prefix = f'Room {rooms[0]}'
        experience = 'MR' if rooms[0] in mr_rooms else 'VR'
        origin = 'GameServer' if experience == 'MR' else 'Simulation'
        _, _, launcher, session, stats, endpoint, _, _ = fixture(remote=False)
        session_id, stream = id_for(100 + rooms[0]), id_for(200 + rooms[0])
        port = 7776 + rooms[0]
        launcher.update(sessionId=session_id, streamId=stream)
        launcher['udpBinding']['port'] = port
        launcher['finalWorld']['header'].update(sessionId=session_id, streamId=stream, roomIds=rooms, origin=origin,
            calibration='quest-room-mr-v1' if experience == 'MR' else 'uncalibrated-vr')
        launcher['finalCombatStream'].update(streamId=stream, origin=origin)
        session.update(id=session_id, mode=mode, roomIds=rooms, players=[], combatStream=launcher['finalCombatStream'],
                       environment={'mode': experience}, mission={'definition': {'name': prefix, 'environment': {'mode': experience}}})
        stats.update(sessionId=session_id, players=[])
        endpoint.update(sessionId=session_id, streamId=stream, port=port)
        batch['sessions'].append({'sessionId': session_id, 'roomIds': rooms, 'missionName': prefix,
                                  'appliedAtSequence': 8, 'combat': 'Sealed', 'world': 'Sealed',
                                  'replay': {'streamId': stream, 'throughSequence': 80}})
        entry = {'evidenceZip': prefix + '.zip', 'launcherReport': prefix + ' launcher.json',
                 'serverLog': prefix + ' server.log', 'players': []}
        if with_journals:
            entry['worldJournal'] = prefix + '.worldlog'
            world_journal(root / entry['worldJournal'], launcher['finalWorld'])
        if experience == 'MR':
            entry['roomAlignments'] = {}
            session['roomAlignment'] = {}
            for room in rooms:
                name = f'Room {room} alignment.json'
                raw = b'\xef\xbb\xbf' + json.dumps({'version': 1, 'profile': 'room-floor-alignment-v1',
                    'roomId': room, 'withinTolerance': True}).encode() + b'\r\n'
                (root / name).write_bytes(raw)
                entry['roomAlignments'][str(room)] = name
                session['roomAlignment'][f'room{room}'] = hashlib.sha256(raw).hexdigest()
        manifest['sessions'].append(entry)
        server = f'VR_NETWORK_STARTED role=Server started=True background=True port={port}\n'
        for room in rooms:
            for seat in range(5):
                connection = room * 5 + seat
                player, admission = id_for(300 + connection), id_for(400 + connection)
                is_quest = experience == 'MR' or seat >= 5 - quest_per_room
                peer = f'192.168.5.{30 + connection}' if is_quest else remote_ip if remote and room == 5 and seat == 4 else server_ip
                session['players'].append({'id': player, 'admissionId': admission, 'roomId': room, 'seat': seat, 'headset': 'Quest3'})
                row = {field_name: 0 for field_name in field.COMBAT} | {'playerId': player, 'roomId': room, 'health': 100, 'accuracyPercent': 0}
                stats['players'].append(row)
                result = dict(row, version=1, admissionId=admission, sessionId=session_id, origin=origin,
                              streamId=stream, throughSequence=9, finalStreamSequence=0, worldSequence=80)
                log = f'Player {connection}.log'
                entry['players'].append({'address': peer, 'log': log, **({'logcatPid': 7342} if is_quest else {})})
                player_log = f'VR_CLIENT_CONNECTED id={connection}\nVR_CLIENT_DEBRIEF_FINAL {json.dumps(result)}\nVR_CLIENT_DISCONNECTED\n'
                (root / log).write_text(quest_logcat(player_log, port) if is_quest else player_log, encoding='utf-8')
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


def quest_capture_venue_fixture(root, mode, *, quest_per_room=2, batches=2, use_capture_tool=False):
    path, manifest, _ = venue_fixture(root, mode, remote=True, quest_per_room=quest_per_room)
    network = {'version': 1, 'mode': mode, 'endpoints': [], 'sources': []}
    mapped, inputs = [], {}
    for entry in manifest['sessions']:
        session, _, endpoint = field.management_zip(root / entry['evidenceZip'])
        network['endpoints'].append({'roomIds': session['roomIds'], 'address': endpoint['address'], 'port': endpoint['port']})
        for owner, player in zip(session['players'], entry['players']):
            if 'logcatPid' not in player:
                continue
            room, seat = owner['roomId'], owner['seat'] + 1
            serial = f'mock-{room}-{seat}'
            network['sources'].append({'roomId': room, 'seat': seat, 'address': player['address']})
            mapped.append({'roomId': room, 'seat': seat, 'serial': serial, 'port': endpoint['port'],
                           'sessionId': session['id'], 'playerId': owner['id'], 'admissionId': owner['admissionId']})
            # Keep CRLF bytes so the capture and verifier check the original encoding.
            inputs[serial] = (root / player['log']).read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
        entry['players'] = [player for player in entry['players'] if 'logcatPid' not in player]
        if not entry['players']:
            del entry['players']
    if use_capture_tool:
        adb = root / 'mock-adb.py'
        adb.write_text("""from pathlib import Path
import sys
assert sys.argv[1] == '-s'
serial = sys.argv[2]
if sys.argv[3:] == ['shell', 'pidof', 'com.vrcommand.quest']:
    print(7342)
else:
    assert sys.argv[3:] == ['logcat', '-b', 'main', '--pid=7342', '-v', 'threadtime', '-s', 'Unity:I']
    sys.stdout.buffer.write((Path(__file__).parent / (serial + '.log')).read_bytes())
""", encoding='utf-8')
        for serial, raw in inputs.items():
            (root / (serial + '.log')).write_bytes(raw)
    reports = []
    for index in range(batches):
        directory = root / f'capture batch {index + 1}'
        seats = mapped[index::batches]
        if use_capture_tool:
            plan = {'version': 1, 'topology': mode, 'seats': seats}
            with redirect_stderr(io.StringIO()):
                result = asyncio.run(capture_tool.capture_venue([sys.executable, str(adb)], plan, directory, 25))
            assert result['complete'] and result['capturedSeats'] == len(seats)
        else:
            directory.mkdir()
            captured = []
            for row in seats:
                log = f"room-{row['roomId']:02}-seat-{row['seat']:02}-logcat.txt"
                raw = inputs[row['serial']]
                (directory / log).write_bytes(raw)
                captured.append({key: row[key] for key in ('roomId', 'seat', 'sessionId', 'port')} |
                                {'complete': True, 'log': log, 'logcatPid': 7342, 'bytes': len(raw),
                                 'sha256': hashlib.sha256(raw).hexdigest()})
            (directory / 'capture-report.json').write_text(json.dumps(
                {'version': 1, 'complete': True, 'topology': mode, 'expectedSeats': len(seats),
                 'capturedSeats': len(seats), 'scope': 'quest-logcat-only', 'seats': captured}), encoding='utf-8')
        reports.append(str((directory / 'capture-report.json').relative_to(root)))
    (root / 'network-plan.json').write_text(json.dumps(network), encoding='utf-8')
    manifest['questCaptures'] = {'networkPlan': 'network-plan.json', 'reports': reports}
    path.write_text(json.dumps(manifest), encoding='utf-8')
    return path, manifest


class QuestCaptureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='quest-live-capture-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / 'original logcat.txt'
        self.partial = self.root / 'original logcat.txt.partial'
        self.original = self.root / 'original-player.json'
        fake = self.root / 'fake-adb.py'
        fake.write_text('''import json, os, sys, time
from pathlib import Path
root = Path(__file__).parent
args = sys.argv[1:]
settings = json.loads((root/'settings.json').read_text())
assert args[:2] == ['-s', 'fixture-device']
if args[2:] == ['shell', 'pidof', 'com.vrcommand.quest']:
    count = root/'pid-count'
    calls = int(count.read_text()) if count.exists() else 0
    count.write_text(str(calls+1))
    print(settings.get('replacement', '7342') if calls else settings.get('initialPid', '7342'))
    sys.exit(0)
assert args[2:] == ['logcat','-b','main','--pid=7342','-v','threadtime','-s','Unity:I']
(root/'logcat-child').write_text(str(os.getpid()))
for line in (root/'logcat.bin').read_bytes().splitlines(keepends=True):
    sys.stdout.buffer.write(line)
    sys.stdout.buffer.flush()
    time.sleep(.015)
if settings.get('keepRunning', True):
    time.sleep(90)
''', encoding='utf-8')
        self.adb = [sys.executable, str(fake), '-s', 'fixture-device']
        self.records = fixture()
        self.records[3]['players'][1]['headset'] = 'Quest3'
        self.address, self.player_log = self.records[7].pop()
        self.expected = {'sessionId': id_for(1), 'playerId': id_for(4), 'admissionId': id_for(14), 'roomId': 1}
        payload = bytearray(75)
        payload[0], payload[49], payload[50] = 2, 1, 1
        for key, offset in (('sessionId', 1), ('playerId', 17), ('admissionId', 33)):
            payload[offset:offset+16] = uuid.UUID(self.expected[key]).bytes_le
        self.ticket = 'v2.' + base64.urlsafe_b64encode(payload).decode('ascii') + '.' + 'a' * 43
        self.original.write_text(json.dumps({'role': 'Client', 'port': 7777, 'joinTicket': self.ticket}), encoding='utf-8-sig')

    def prepare(self, log, **settings):
        (self.root/'logcat.bin').write_bytes(log)
        (self.root/'settings.json').write_text(json.dumps(settings), encoding='utf-8')
        (self.root/'pid-count').unlink(missing_ok=True)

    def capture(self, seconds=4):
        port, expected = capture_tool.read_connection(self.original)
        return asyncio.run(capture_tool.capture(self.adb, port, expected, self.output, seconds))

    def test_live_capture_preserves_bytes_and_existing_verifier_accepts_original_reconnect(self):
        earlier = 'VR_CLIENT_CONNECTED id=8\nVR_CLIENT_DISCONNECTED\n'
        startup, rest = self.records[6].split('\n', 1)
        self.records[6] = startup + '\nVR_SERVER_ADMISSION_APPROVED id=8\nVR_SERVER_PEER id=8 endpoint=unavailable\n' + rest
        raw = quest_logcat(earlier + self.player_log).replace('\n', '\r\n').encode('utf-8')
        self.prepare(raw + logcat_line('post-disconnect line').encode('utf-8'))
        report = self.capture()
        self.assertEqual(raw, self.output.read_bytes())
        self.assertFalse(self.partial.exists())
        self.assertEqual({'version': 1, 'complete': True, 'logcatPid': 7342, 'port': 7777, 'roomId': 1,
                          'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'scope': 'quest-logcat-only'}, report)
        self.assertGreaterEqual(int((self.root/'pid-count').read_text()), 2)
        readback = field.verify(*self.records, quest_player_logs=[(self.address, field.content(self.output), report['logcatPid'])])
        self.assertEqual(1, readback['questLogcatPlayers'])
        self.assertEqual(2, readback['serverAcknowledgements'])

    def test_capture_rejects_stale_admission_on_same_port(self):
        self.prepare(quest_logcat(self.player_log.replace(id_for(14), id_for(99))).encode('utf-8'))
        with self.assertRaisesRegex(capture_tool.field.EvidenceError, 'differs from the original player admission'):
            self.capture()
        self.assertTrue(self.partial.exists())
        self.assertFalse(self.output.exists())

    def test_capture_rejects_game_process_replacement_after_terminal_marker(self):
        self.prepare(quest_logcat(self.player_log).encode('utf-8'), replacement='7450')
        with self.assertRaisesRegex(capture_tool.field.EvidenceError, 'original Quest process changed'):
            self.capture()
        self.assertTrue(self.partial.exists())
        self.assertFalse(self.output.exists())

    def test_capture_rechecks_pid_while_stream_is_idle(self):
        self.prepare(quest_logcat('').encode('utf-8'), replacement='7450')
        with patch.object(capture_tool, 'PID_CHECK_SECONDS', .15):
            with self.assertRaisesRegex(capture_tool.field.EvidenceError, 'original Quest process changed'):
                self.capture()
        self.assertFalse(self.output.exists())

    def test_capture_rejects_multiple_processes_before_opening_a_log(self):
        self.prepare(b'', initialPid='7342 7450')
        with self.assertRaisesRegex(capture_tool.field.EvidenceError, 'one running Quest game process'):
            self.capture()
        self.assertFalse((self.root/'logcat-child').exists())
        self.assertFalse(self.partial.exists())
        self.assertFalse(self.output.exists())

    def test_capture_incomplete_stream_is_bounded_and_keeps_raw_partial(self):
        raw = quest_logcat('VR_CLIENT_CONNECTED id=2').encode('utf-8')
        for settings, message in (({'keepRunning': False}, 'logcat ended'), ({}, 'timed out')):
            with self.subTest(settings=settings):
                self.prepare(raw, **settings)
                with self.assertRaisesRegex(capture_tool.field.EvidenceError, message):
                    self.capture(seconds=2)
                self.assertEqual(raw, self.partial.read_bytes())
                self.partial.unlink()
                self.assertFalse(self.output.exists())

    def test_capture_checks_source_startup_before_publishing(self):
        for raw, message in (
            (quest_logcat(self.player_log, port=7778), 'startup differs'),
            (quest_logcat(self.player_log, pid=7450), 'startup differs'),
            (logcat_line('VR_CLIENT_CONNECTED id=2'), 'outside the original Quest startup'),
        ):
            with self.subTest(message=message):
                self.prepare(raw.encode('utf-8'))
                with self.assertRaisesRegex(capture_tool.field.EvidenceError, message):
                    self.capture()
                self.assertFalse(self.output.exists())
                self.partial.unlink()

    def test_capture_keeps_existing_log_and_rejects_size_limit(self):
        raw = quest_logcat(self.player_log).encode('utf-8')
        self.prepare(raw)
        self.output.write_bytes(b'existing')
        with self.assertRaisesRegex(capture_tool.field.EvidenceError, 'new capture output'):
            self.capture()
        self.assertFalse((self.root/'pid-count').exists())
        self.assertEqual(b'existing', self.output.read_bytes())
        self.output.unlink()
        with patch.object(capture_tool.field, 'MAX_FILE_BYTES', len(raw) - 1):
            with self.assertRaisesRegex(capture_tool.field.EvidenceError, 'capture size limit'):
                self.capture()
        self.assertFalse(self.output.exists())

    def test_capture_cli_rejects_bad_ticket_without_echoing_private_inputs(self):
        self.original.write_text(json.dumps({'role': 'Client', 'port': 7777, 'joinTicket': 'private-test-ticket'}))
        run = subprocess.run([sys.executable, str(capture_spec.origin), '--adb', sys.executable, '--serial', 'fixture-device',
            '--connection-file', str(self.original), '--output', str(self.output)], capture_output=True, text=True, timeout=5)
        self.assertEqual(1, run.returncode)
        self.assertIn('v2 player connection file', run.stderr)
        for secret in ('fixture-device', 'private-test-ticket', str(self.root)):
            self.assertNotIn(secret, run.stderr + run.stdout)
        self.assertFalse(self.partial.exists())


def preflight_fixture(root, label, *, server, peer, port, exchange=None):
    common = {'version': 1, 'stage': 'finished', 'port': port, 'requested': 1, 'matched': 1,
              'complete': True, 'scope': 'authenticated-udp-only', 'completedAtUtc': '2026-11-08T23:59:58Z',
              'exchangeSha256': exchange or hashlib.sha256(label.encode()).hexdigest()}
    listener = root / (label + '-listener.ndjson')
    probe = root / (label + '-probe.json')
    listener.write_text(json.dumps(dict(common, mode='listen', localAddress=server, peerAddress=peer, samples=[]))+'\n', encoding='utf-16')
    probe.write_text(json.dumps(dict(common, mode='probe', localAddress=peer, peerAddress=server,
                                     samples=[{'sample': 1, 'roundTripMs': 2.0}])), encoding='utf-8-sig')
    return listener, probe


class FieldResultsTests(unittest.TestCase):
    def concurrent_journals(self, root, manifest, offsets, edit_packet=None, *, tracked=False):
        for entry, offset in zip(manifest['sessions'], offsets, strict=True):
            session, _, _ = field.management_zip(root / entry['evidenceZip'])
            members = [{'id': player['id'], 'roomId': player['roomId'], 'connected': True} for player in session['players']]
            if tracked:
                for member in members:
                    member['rig'] = {'kind': 'Tracked'}
            launch = root / entry['launcherReport']
            launcher = json.loads(launch.read_text(encoding='utf-8'))
            start = datetime.fromisoformat('2026-11-09T08:00:00+08:00') + timedelta(milliseconds=offset)
            world_journal(root / entry['worldJournal'], launcher['finalWorld'], capture_start=start.isoformat(),
                          players=lambda _, phase: deepcopy(members) if phase == 'Running' else [], edit_packet=edit_packet)
            launch.write_text(json.dumps(launcher), encoding='utf-8')

    def test_venue_concurrent_roster_uses_the_longest_common_capture_interval(self):
        for mode, offsets, duration in (('Linked', [0], 7700), ('Independent', [0, 150, 300, 450, 600], 7100)):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, mode, with_journals=True)
                self.concurrent_journals(root, manifest, offsets)
                packed = self.pack_venue(root, manifest)
                packed['minimumConcurrentMilliseconds'] = duration
                path.write_text(json.dumps(packed), encoding='utf-8')
                report = field.verify_venue(path)
                self.assertEqual(report['concurrentRoster'], {'players': 25, 'minimumMilliseconds': duration,
                    'longestMilliseconds': duration, 'maxFrameGapMilliseconds': 500,
                    'fromUtc': '2026-11-09T00:00:00.200000+00:00' if mode == 'Linked' else '2026-11-09T00:00:00.800000+00:00',
                    'throughUtc': '2026-11-09T00:00:07.900000+00:00'})
                self.assertFalse(report['networkCapacityAccepted'])
                packed['minimumConcurrentMilliseconds'] += 1
                path.write_text(json.dumps(packed), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'continuous concurrent roster'):
                    field.verify_venue(path)

    def test_venue_concurrent_roster_rejects_full_rooms_at_different_times(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Independent', with_journals=True)
            self.concurrent_journals(root, manifest, [0, 0, 0, 0, 20000])
            self.assertTrue(field.verify_venue(path)['consistent'])
            manifest['minimumConcurrentMilliseconds'] = 1000
            path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'continuous concurrent roster'):
                field.verify_venue(path)

    def test_venue_concurrent_roster_does_not_bridge_interruptions(self):
        def interrupt(packet):
            number = packet['sequence']
            frame = packet['frame']
            if cause in ('gap', 'at-gap-limit') and number >= 40:
                packet['elapsedMilliseconds'] += 401 if cause == 'gap' else 400
            if number != 40:
                return
            if cause == 'paused':
                frame['phase'] = 'Paused'
            if cause == 'suspended':
                packet['suspended'] = True
            if cause == 'stalled-tick':
                frame['tick'] -= 1
            if cause == 'missing-player':
                frame['players'][-1]['connected'] = False
            if cause == 'wrong-room':
                frame['players'][-1]['roomId'] = 1

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Linked', with_journals=True)
            manifest['minimumConcurrentMilliseconds'] = 6000
            path.write_text(json.dumps(manifest), encoding='utf-8')
            for cause in ('paused', 'suspended', 'stalled-tick', 'missing-player', 'wrong-room', 'gap', 'at-gap-limit'):
                with self.subTest(cause=cause):
                    self.concurrent_journals(root, manifest, [0], interrupt)
                    if cause == 'at-gap-limit':
                        self.assertEqual(field.verify_venue(path)['concurrentRoster']['longestMilliseconds'], 8100)
                    else:
                        with self.assertRaisesRegex(field.EvidenceError, 'continuous concurrent roster'):
                            field.verify_venue(path)

    def test_venue_concurrent_roster_requires_original_journals_and_bounded_integer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Linked')
            manifest['minimumConcurrentMilliseconds'] = 1000
            path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'original world journals'):
                field.verify_venue(path)
            path, manifest, _ = venue_fixture(root, 'Linked', with_journals=True)
            for value in (None, True, 999, 900001):
                with self.subTest(value=value):
                    manifest['minimumConcurrentMilliseconds'] = value
                    path.write_text(json.dumps(manifest), encoding='utf-8')
                    with self.assertRaises(field.EvidenceError):
                        field.verify_venue(path)

    def test_venue_tracked_roster_checks_original_logs_and_continuous_overlap(self):
        for mode, offsets, duration in (('Linked', [0], 7700), ('Independent', [0, 150, 300, 450, 600], 7100)):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, mode, remote=True, quest_per_room=5, with_journals=True)
                self.concurrent_journals(root, manifest, offsets, tracked=True)
                packed = self.pack_venue(root, manifest)
                packed.pop('windowsPlayers')
                packed.update(minimumConcurrentMilliseconds=duration, requireTrackedRoster=True)
                path.write_text(json.dumps(packed), encoding='utf-8')
                result = field.verify_venue(path)
                self.assertEqual('Tracked', result['concurrentRoster']['rigKind'])
                self.assertEqual(duration, result['concurrentRoster']['longestMilliseconds'])
                sources = [row for session in result['sessions'] for row in session['playerSources']]
                self.assertEqual(25, len(sources))
                self.assertTrue(all(row['source'] == 'quest-logcat-tracked' for row in sources))
                self.assertFalse(result['physicalHostsVerified'])
                self.assertFalse(result['networkCapacityAccepted'])

                def lose_tracking(packet):
                    if packet['sequence'] == 40:
                        packet['frame']['players'][-1].update(connected=False, rig={'kind': 'None'})

                self.concurrent_journals(root, manifest, offsets, lose_tracking, tracked=True)
                with self.assertRaisesRegex(field.EvidenceError, 'continuous concurrent roster'):
                    field.verify_venue(path)

                def replace_rig(packet):
                    if packet['sequence'] == 40:
                        packet['frame']['players'][-1]['rig']['kind'] = 'Simulated'

                self.concurrent_journals(root, manifest, offsets, replace_rig, tracked=True)
                with self.assertRaisesRegex(field.EvidenceError, 'room or rig differs from the original player log'):
                    field.verify_venue(path)

    def test_venue_tracked_roster_rejects_simulated_and_mock_sources(self):
        for runtime in (None, 'Unity Mock Runtime', 'Example private runtime'):
            with self.subTest(runtime=runtime), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, 'Linked', remote=True, quest_per_room=4, with_journals=True)
                startup = PlayerSourceEvidenceTests.openxr_startup(runtime) if runtime else PlayerSourceEvidenceTests.desktop_startup
                for row in manifest['sessions'][0]['players']:
                    if 'logcatPid' not in row:
                        log = root / row['log']
                        log.write_text(startup + log.read_text(encoding='utf-8'), encoding='utf-8')
                self.concurrent_journals(root, manifest, [0], tracked=True)
                manifest['minimumConcurrentMilliseconds'] = 1000
                path.write_text(json.dumps(manifest), encoding='utf-8')
                self.assertTrue(field.verify_venue(path)['consistent'])
                manifest['requireTrackedRoster'] = True
                path.write_text(json.dumps(manifest), encoding='utf-8')
                if runtime == 'Example private runtime':
                    result = field.verify_venue(path)
                    sources = result['sessions'][0]['playerSources']
                    self.assertEqual(5, sum(row['source'] == 'windows-openxr-tracked' for row in sources))
                else:
                    with self.assertRaisesRegex(field.EvidenceError, 'original Quest or non-mock Windows OpenXR'):
                        field.verify_venue(path)

    def test_venue_tracked_roster_requires_a_boolean_and_concurrent_threshold(self):
        with tempfile.TemporaryDirectory() as directory:
            path, manifest, _ = venue_fixture(Path(directory), 'Linked')
            for value, message in (('true', 'boolean'), (None, 'boolean'), (True, 'minimumConcurrentMilliseconds')):
                with self.subTest(value=value):
                    manifest['requireTrackedRoster'] = value
                    path.write_text(json.dumps(manifest), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, message):
                        field.verify_venue(path)

    def pack_venue(self, root, manifest):
        packed = deepcopy(manifest)
        packed['venueBundle'] = 'venue download.zip'
        with zipfile.ZipFile(root / packed['venueBundle'], 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.write(root / packed.pop('closure'), 'closure.json')
            for room, entry in enumerate(packed['sessions'], 1):
                name = 'linked.zip' if packed['mode'] == 'Linked' else f'room-{room:02}.zip'
                archive.write(root / entry.pop('evidenceZip'), name)
        packed['windowsPlayers'] = []
        for entry in reversed(packed['sessions']):
            players = entry.pop('players', [])
            packed['windowsPlayers'].extend(player for player in reversed(players) if 'logcatPid' not in player)
            quest = [player for player in players if 'logcatPid' in player]
            if quest:
                entry['players'] = quest
        packed['sessions'].reverse()
        return packed

    def test_packed_venue_and_unsorted_windows_match_original_split_summary(self):
        for mode in ('Linked', 'Independent'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, split, _ = venue_fixture(root, mode, remote=True, quest_per_room=1,
                                                with_journals=True, mr_rooms=(2, 4))
                original = field.verify_venue(path)
                packed = self.pack_venue(root, split)
                path.write_text(json.dumps(packed), encoding='utf-8')
                for name in [split['closure'], *(entry['evidenceZip'] for entry in split['sessions'])]:
                    (root / name).unlink()
                original_files = {file: file.read_bytes() for file in root.iterdir()}
                self.assertEqual(field.verify_venue(path), original)
                self.assertEqual({file: file.read_bytes() for file in root.iterdir()}, original_files)

    def test_packed_venue_combines_windows_with_original_quest_capture_batches(self):
        for mode in ('Linked', 'Independent'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, split = quest_capture_venue_fixture(root, mode)
                original = field.verify_venue(path)
                packed = self.pack_venue(root, split)
                path.write_text(json.dumps(packed), encoding='utf-8')
                self.assertEqual(field.verify_venue(path), original)
                packed['closure'] = split['closure']
                del packed['venueBundle']
                for entry, source in zip(packed['sessions'], reversed(split['sessions'])):
                    entry['evidenceZip'] = source['evidenceZip']
                path.write_text(json.dumps(packed), encoding='utf-8')
                self.assertEqual(field.verify_venue(path), original)

    def test_packed_venue_rejects_ambiguous_and_incorrect_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, split, _ = venue_fixture(root, 'Independent')
            packed = self.pack_venue(root, split)

            def rejected(manifest, message):
                path.write_text(json.dumps(manifest), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, message):
                    field.verify_venue(path)

            rejected(dict(packed, closure=split['closure']), 'either venueBundle')
            changed = deepcopy(packed)
            changed['sessions'][0]['evidenceZip'] = split['sessions'][-1]['evidenceZip']
            rejected(changed, 'Omit per-session evidenceZip')
            changed = deepcopy(packed)
            changed['sessions'][0]['players'] = [changed['windowsPlayers'].pop(0)]
            rejected(changed, 'per-session Windows logs')
            changed = deepcopy(packed)
            changed['windowsPlayers'][1] = changed['windowsPlayers'][0]
            rejected(changed, 'Evidence paths must be distinct')
            changed = deepcopy(packed)
            changed['windowsPlayers'][0]['address'] = '192.168.5.250'
            rejected(changed, 'UDP peer differs')
            changed = deepcopy(packed)
            foreign = root / 'foreign.log'
            source = root / changed['windowsPlayers'][0]['log']
            foreign.write_bytes(source.read_bytes().replace(id_for(105).encode(), id_for(9000).encode()))
            changed['windowsPlayers'][0]['log'] = foreign.name
            rejected(changed, 'different venue session')

            bundle = root / packed['venueBundle']
            with zipfile.ZipFile(bundle) as archive:
                members = {name: archive.read(name) for name in archive.namelist()}
            for name in ('unexpected.json', '../room-01.zip', None):
                with self.subTest(extra=name), zipfile.ZipFile(bundle, 'w') as archive:
                    for entry, data in members.items():
                        if name is not None or entry != 'room-01.zip':
                            archive.writestr(entry, data)
                    if name is not None:
                        archive.writestr(name, b'')
                rejected(packed, 'exact session ZIPs')
            with zipfile.ZipFile(bundle, 'w') as archive:
                for name, data in members.items():
                    archive.writestr(name, members['room-02.zip'] if name == 'room-01.zip' else data)
            rejected(packed, 'differs from its original launcher session')
            with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
                for name, data in members.items():
                    archive.writestr(name, b'0' * field.MAX_FILE_BYTES if name == 'room-01.zip' else data)
            rejected(packed, 'expanded size limit')

    def test_venue_verifies_mixed_windows_and_original_capture_batches_for_both_modes(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, _ = quest_capture_venue_fixture(root, mode, use_capture_tool=True)
                report = field.verify_venue(path)
                self.assertEqual(25, report['serverAcknowledgements'])
                self.assertEqual(10, report['questLogcatPlayers'])
                self.assertEqual(10, report['questCaptureSeatsVerified'])
                self.assertEqual(2, report['questCaptureBatchesVerified'])
                self.assertFalse(report['physicalHostsVerified'])
                self.assertFalse(report['networkCapacityAccepted'])
                self.assertNotIn('192.168.', json.dumps(report))
                self.assertNotIn('logcat.txt', json.dumps(report))

    def test_venue_accepts_all_quest_seats_without_a_manual_player_list(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                path, _ = quest_capture_venue_fixture(Path(directory), mode, quest_per_room=5, batches=1)
                report = field.verify_venue(path)
                self.assertEqual(25, report['questCaptureSeatsVerified'])
                self.assertEqual(25, report['serverAcknowledgements'])
                self.assertEqual(1, report['questCaptureBatchesVerified'])

    def test_venue_rejects_incomplete_wrong_and_tampered_capture_evidence(self):
        cases = {
            'incomplete report': 'incomplete or has the wrong topology',
            'wrong topology': 'incomplete or has the wrong topology',
            'wrong session': 'original session and room',
            'wrong port': 'capture port differs',
            'wrong pid': 'Quest',
            'wrong hash': 'size or digest differs',
            'wrong size': 'size or digest differs',
            'changed log': 'size or digest differs',
            'missing batch': 'cover the planned Quest seats',
            'duplicate batch': 'distinct across the venue',
            'wrong endpoint': 'plan endpoint differs',
            'wrong address': 'UDP peer differs',
            'manual logcat': 'or manual Quest logs',
        }
        for case, error in cases.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest = quest_capture_venue_fixture(root, 'Independent')
                reports = manifest['questCaptures']['reports']
                report_path = root / reports[0]
                report = json.loads(report_path.read_text(encoding='utf-8'))
                seat = report['seats'][0]
                network_path = root / manifest['questCaptures']['networkPlan']
                network = json.loads(network_path.read_text(encoding='utf-8'))
                if case == 'incomplete report': report['complete'] = False
                if case == 'wrong topology': report['topology'] = 'Linked'
                if case == 'wrong session': seat['sessionId'] = id_for(999)
                if case == 'wrong port': seat['port'] += 1
                if case == 'wrong pid': seat['logcatPid'] += 1
                if case == 'wrong hash': seat['sha256'] = '0' * 64
                if case == 'wrong size': seat['bytes'] += 1
                if case == 'changed log':
                    with (report_path.parent / seat['log']).open('ab') as log:
                        log.write(b'changed')
                if case == 'missing batch': reports.pop()
                if case == 'duplicate batch': reports.append(reports[0])
                if case == 'wrong endpoint': network['endpoints'][0]['address'] = '192.168.5.99'
                if case == 'wrong address': network['sources'][0]['address'] = '192.168.5.99'
                if case == 'manual logcat': manifest['sessions'][0]['players'][0]['logcatPid'] = 7342
                report_path.write_text(json.dumps(report), encoding='utf-8')
                network_path.write_text(json.dumps(network), encoding='utf-8')
                path.write_text(json.dumps(manifest), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, error):
                    field.verify_venue(path)

    @unittest.skipUnless(HAS_POWERSHELL, 'UDP evidence requires PowerShell')
    def test_venue_combines_all_quest_capture_seats_with_all_source_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest = quest_capture_venue_fixture(root, 'Linked', quest_per_room=5, batches=2)
            entry, = manifest['sessions']
            launcher_path = root / entry['launcherReport']
            launcher = json.loads(launcher_path.read_text(encoding='utf-8'))
            binding = launcher['udpBinding']
            binding['observedAtUtc'] = '2026-11-08T23:59:59Z'
            launcher_path.write_text(json.dumps(launcher), encoding='utf-8')
            network = json.loads((root / 'network-plan.json').read_text(encoding='utf-8'))
            entry['udpSourcePreflights'] = []
            for index, source in enumerate(network['sources']):
                listener, probe = preflight_fixture(root, f'quest-{index}', server=binding['address'],
                                                    peer=source['address'], port=binding['port'])
                entry['udpSourcePreflights'].append({'listener': listener.name, 'probe': probe.name})
            path.write_text(json.dumps(manifest), encoding='utf-8')
            report = field.verify_venue(path)
            self.assertEqual(25, report['questCaptureSeatsVerified'])
            self.assertEqual(25, report['udpSourcePreflightsVerified'])
            self.assertEqual(25, report['serverAcknowledgements'])

    def test_venue_checks_capture_seat_even_when_swapped_logs_and_addresses_agree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest = quest_capture_venue_fixture(root, 'Linked', batches=1)
            report_path = root / manifest['questCaptures']['reports'][0]
            report = json.loads(report_path.read_text(encoding='utf-8'))
            left, right = report['seats'][:2]
            self.assertEqual(left['roomId'], right['roomId'])
            a, b = [report_path.parent / seat['log'] for seat in (left, right)]
            raw_a, raw_b = a.read_bytes(), b.read_bytes()
            a.write_bytes(raw_b)
            b.write_bytes(raw_a)
            for key in ('bytes', 'sha256', 'logcatPid'):
                left[key], right[key] = right[key], left[key]
            report_path.write_text(json.dumps(report), encoding='utf-8')
            network_path = root / manifest['questCaptures']['networkPlan']
            network = json.loads(network_path.read_text(encoding='utf-8'))
            first, second = network['sources'][:2]
            first['address'], second['address'] = second['address'], first['address']
            network_path.write_text(json.dumps(network), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'capture room or seat differs'):
                field.verify_venue(path)

    @unittest.skipUnless(HAS_POWERSHELL, 'UDP evidence requires PowerShell')
    def test_all_source_preflight_requires_exact_acknowledged_addresses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = fixture()
            binding = data[2]['udpBinding']
            binding['observedAtUtc'] = '2026-11-08T23:59:59.5000000+00:00'
            server = binding['address']
            local = preflight_fixture(root, 'local', server=server, peer=server, port=7777)
            remote = preflight_fixture(root, 'remote', server=server, peer='192.168.5.20', port=7777)
            summary = field.verify(*data, udp_source_preflights=[remote, local])
            coverage = summary['udpSourcePreflight']
            self.assertEqual((2, 2), (coverage['observedSourceAddresses'], coverage['verifiedSourceAddresses']))
            self.assertEqual([1, 1], [pair['samples'] for pair in coverage['pairs']])
            self.assertNotIn('192.168', json.dumps(summary))
            self.assertFalse(summary['physicalHostsVerified'])
            self.assertFalse(summary['networkCapacityAccepted'])
            duplicate = preflight_fixture(root, 'duplicate', server=server, peer=server, port=7777)
            unknown = preflight_fixture(root, 'unknown', server=server, peer='192.168.5.21', port=7777)
            reused = preflight_fixture(root, 'reused', server=server, peer='192.168.5.20', port=7777,
                                       exchange=hashlib.sha256(b'local').hexdigest())
            for pairs, message in (([remote], 'each acknowledged source'), ([local, duplicate], 'same source more than once'),
                                   ([local, unknown], 'game binding, accepted peer'), ([local, reused], 'reused an exchange')):
                with self.subTest(message=message), self.assertRaisesRegex(field.EvidenceError, message):
                    field.verify(*data, udp_source_preflights=pairs)

            topology, ips, launcher, session, statistics, endpoint, server_log, clients = data
            command = [sys.executable, str(SCRIPT), '--topology', topology, '--server-ip', str(next(iter(ips)))]
            for option, value in [('launcher-report', launcher), ('session', session), ('statistics', statistics),
                                  ('endpoint', endpoint), ('server-log', server_log)]:
                path = root / option
                path.write_text(value if type(value) is str else json.dumps(value), encoding='utf-8')
                command += ['--' + option, str(path)]
            for index, (address, log) in enumerate(clients):
                path = root / f'player-{index}.log'
                path.write_text(log, encoding='utf-8')
                command += ['--player', str(address), str(path)]
            for pair in (local, remote):
                command += ['--udp-source-preflight', *map(str, pair)]
            verified = subprocess.run(command, capture_output=True, text=True, check=True, timeout=15)
            self.assertEqual(json.loads(json.dumps(summary)), json.loads(verified.stdout))
            rejected = subprocess.run([*command, '--udp-preflight', *map(str, remote)], capture_output=True, text=True, timeout=15)
            self.assertEqual(2, rejected.returncode)
            self.assertNotIn(directory, rejected.stdout + rejected.stderr)

    @unittest.skipUnless(HAS_POWERSHELL, 'UDP evidence requires PowerShell')
    def test_linked_all_source_preflight_checks_each_of_25_observed_addresses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Linked', remote=True, quest_per_room=5)
            entry = manifest['sessions'][0]
            launcher_path = root / entry['launcherReport']
            launcher = json.loads(launcher_path.read_text(encoding='utf-8'))
            binding = launcher['udpBinding']
            binding['observedAtUtc'] = '2026-11-08T23:59:59Z'
            launcher_path.write_text(json.dumps(launcher), encoding='utf-8')
            pairs = []
            for index, player in enumerate(entry['players']):
                listener, probe = preflight_fixture(root, f'udp-seat-{index}', server=binding['address'],
                                                    peer=player['address'], port=binding['port'])
                pairs.append({'listener': listener.name, 'probe': probe.name})
            entry['udpSourcePreflights'] = pairs[:-1]
            path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'each acknowledged source'):
                field.verify_venue(path)
            entry['udpSourcePreflights'] = pairs
            path.write_text(json.dumps(manifest), encoding='utf-8')
            report = field.verify_venue(path)
            self.assertEqual(25, report['udpSourcePreflightsVerified'])
            self.assertEqual(25, report['serverAcknowledgements'])
            self.assertEqual(25, report['sessions'][0]['udpSourcePreflight']['verifiedSourceAddresses'])
            self.assertNotIn('192.168', json.dumps(report))
            self.assertFalse(report['physicalHostsVerified'])
            self.assertFalse(report['networkCapacityAccepted'])

    @unittest.skipUnless(HAS_POWERSHELL, 'UDP evidence requires PowerShell')
    def test_venue_rechecks_original_pairs_relative_to_a_quest_batch_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Independent')
            batch_folder = root / 'network-check'
            batch_folder.mkdir()
            batch_path = batch_folder / 'preflight-report.json'
            groups = []
            for index, entry in enumerate(manifest['sessions'], 1):
                launcher_path = root / entry['launcherReport']
                launcher = json.loads(launcher_path.read_text(encoding='utf-8'))
                binding = launcher['udpBinding']
                binding['observedAtUtc'] = '2026-11-08T23:59:59Z'
                launcher_path.write_text(json.dumps(launcher), encoding='utf-8')
                listener, probe = preflight_fixture(batch_folder, f'room-{index}', server=binding['address'],
                                                    peer=entry['players'][0]['address'], port=binding['port'])
                groups.append({'roomIds': [index], 'complete': True,
                               'udpSourcePreflights': [{'listener': listener.name, 'probe': probe.name}]})
            batch = {'version': 1, 'scope': 'quest-udp-preflight-only', 'mode': 'Independent', 'complete': True,
                     'groups': groups[::-1]}
            batch_path.write_text(json.dumps(batch), encoding='utf-8')
            manifest['udpPreflightBatch'] = 'network-check/preflight-report.json'
            path.write_text(json.dumps(manifest), encoding='utf-8')
            report = field.verify_venue(path)
            self.assertEqual(5, report['udpSourcePreflightsVerified'])
            self.assertEqual(25, report['serverAcknowledgements'])
            self.assertFalse(report['physicalHostsVerified'])
            entry = manifest['sessions'][0]
            entry['udpPreflight'] = groups[0]['udpSourcePreflights'][0]
            path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'only one UDP preflight mode'):
                field.verify_venue(path)
            entry.pop('udpPreflight')
            path.write_text(json.dumps(manifest), encoding='utf-8')
            batch['groups'] = groups[1:]
            batch_path.write_text(json.dumps(batch), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'cover every original endpoint'):
                field.verify_venue(path)
            batch['groups'] = groups
            batch_path.write_text(json.dumps(batch), encoding='utf-8')
            wrong = batch_folder / groups[0]['udpSourcePreflights'][0]['probe']
            wrong_report = json.loads(wrong.read_text(encoding='utf-8-sig'))
            wrong_report['port'] += 1
            wrong.write_text(json.dumps(wrong_report), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'game binding, accepted peer'):
                field.verify_venue(path)

    @unittest.skipUnless(HAS_POWERSHELL, 'UDP evidence requires PowerShell')
    def test_venue_combines_partial_quest_batches_with_windows_original_pairs(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, closure = venue_fixture(root, mode, remote=True, quest_per_room=2)
                folders = {kind: root / kind for kind in ('quest-a', 'quest-b', 'windows')}
                for folder in folders.values():
                    folder.mkdir()
                groups = {'quest-a': [], 'quest-b': []}

                def pair(kind, label, binding, source):
                    digest = hashlib.sha256(f'{kind}-{label}-{source}'.encode()).hexdigest()
                    listener, probe = preflight_fixture(folders[kind], label, server=binding['address'],
                                                        peer=source, port=binding['port'], exchange=digest)
                    return {'listener': listener.name, 'probe': probe.name}

                for index, (entry, original) in enumerate(zip(manifest['sessions'], closure['sessions'], strict=True)):
                    launcher_path = root / entry['launcherReport']
                    launcher = json.loads(launcher_path.read_text(encoding='utf-8'))
                    binding = launcher['udpBinding']
                    binding['observedAtUtc'] = '2026-11-08T23:59:59Z'
                    launcher_path.write_text(json.dumps(launcher), encoding='utf-8')
                    quests = [row['address'] for row in entry['players'] if 'logcatPid' in row]
                    windows = sorted({row['address'] for row in entry['players'] if 'logcatPid' not in row})
                    self.assertEqual(1, len(windows))
                    # For the last Independent room, demonstrate a complete supplemental list and no Quest group.
                    manual = windows + quests if mode == 'Independent' and index == 4 else windows
                    entry['udpSourcePreflights'] = [
                        {key: 'windows/' + value for key, value in pair('windows', f'{index}-{i}', binding, source).items()}
                        for i, source in enumerate(manual)]
                    if manual == windows:
                        for kind, sources in (('quest-a', quests[::2]), ('quest-b', quests[1::2])):
                            groups[kind].append({'roomIds': original['roomIds'], 'complete': True,
                                                 'udpSourcePreflights': [pair(kind, f'{index}-{i}', binding, source)
                                                                         for i, source in enumerate(sources)]})
                for kind, rows in groups.items():
                    (folders[kind] / 'preflight-report.json').write_text(json.dumps({
                        'version': 1, 'scope': 'quest-udp-preflight-only', 'mode': mode, 'complete': True, 'groups': rows}),
                        encoding='utf-8')
                indexes = ['quest-b/preflight-report.json', 'quest-a/preflight-report.json']
                manifest['udpPreflightBatches'] = indexes
                path.write_text(json.dumps(manifest), encoding='utf-8')
                report = field.verify_venue(path)
                self.assertEqual(25, report['serverAcknowledgements'])
                self.assertEqual(15 if mode == 'Independent' else 11, report['udpSourcePreflightsVerified'])
                self.assertEqual([3] * 5 if mode == 'Independent' else [11],
                                 [row['udpSourcePreflight']['verifiedSourceAddresses'] for row in report['sessions']])
                self.assertNotIn('192.168', json.dumps(report))
                self.assertFalse(report['physicalHostsVerified'])

                first = manifest['sessions'][0]
                if mode == 'Linked':
                    original_manual = first['udpSourcePreflights']
                    first['udpSourcePreflights'] = original_manual + [
                        {key: 'quest-a/' + value for key, value in pair.items()}
                        for pair in groups['quest-a'][0]['udpSourcePreflights']]
                    manifest.pop('udpPreflightBatches')
                    manifest['udpPreflightBatch'] = indexes[0]
                    path.write_text(json.dumps(manifest), encoding='utf-8')
                    self.assertEqual(report, field.verify_venue(path))
                    manifest.pop('udpPreflightBatch')
                    manifest['udpPreflightBatches'] = indexes
                    first['udpSourcePreflights'] = original_manual
                saved = first.pop('udpSourcePreflights')
                if mode == 'Linked':
                    path.write_text(json.dumps(manifest), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, 'each acknowledged source address'):
                        field.verify_venue(path)
                original_pair = groups['quest-a'][0]['udpSourcePreflights'][0]
                first['udpSourcePreflights'] = [{key: 'quest-a/' + value for key, value in original_pair.items()}]
                path.write_text(json.dumps(manifest), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'Evidence paths must be distinct'):
                    field.verify_venue(path)
                first['udpSourcePreflights'] = saved
                manifest['udpPreflightBatches'] = [indexes[0], indexes[0]]
                path.write_text(json.dumps(manifest), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'Evidence paths must be distinct'):
                    field.verify_venue(path)

    @unittest.skipUnless(HAS_POWERSHELL, 'UDP evidence requires PowerShell')
    def test_preflight_uses_the_observed_server_and_a_peer_with_a_final_ack(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = fixture()
            binding = data[2]['udpBinding']
            binding['observedAtUtc'] = '2026-11-08T23:59:59.5000000+00:00'
            for name, peer, port, matches in (('original', '192.168.5.20', 7777, True),
                                               ('wrong-port', '192.168.5.20', 7778, False),
                                               ('unknown-peer', '192.168.5.21', 7777, False)):
                with self.subTest(case=name):
                    pair = preflight_fixture(root, name, server=binding['address'], peer=peer, port=port)
                    if matches:
                        report = field.verify(*data, udp_preflight=pair)
                        self.assertEqual(1, report['udpPreflight']['samples'])
                        self.assertNotIn(peer, json.dumps(report))
                        self.assertFalse(report['physicalHostsVerified'])
                    else:
                        with self.assertRaisesRegex(field.EvidenceError, 'game binding, accepted peer or preflight window'):
                            field.verify(*data, udp_preflight=pair)

    @unittest.skipUnless(HAS_POWERSHELL, 'UDP evidence requires PowerShell')
    def test_venue_requires_a_distinct_original_preflight_pair_for_each_binding(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, mode)
                for index, entry in enumerate(manifest['sessions']):
                    launch = root / entry['launcherReport']
                    launcher = json.loads(launch.read_text(encoding='utf-8'))
                    binding = launcher['udpBinding']
                    binding['observedAtUtc'] = '2026-11-08T23:59:59Z'
                    launch.write_text(json.dumps(launcher), encoding='utf-8')
                    listener, probe = preflight_fixture(root, f'udp-{index}', server=binding['address'],
                                                        peer=entry['players'][0]['address'], port=binding['port'])
                    entry['udpPreflight'] = {'listener': listener.name, 'probe': probe.name}
                path.write_text(json.dumps(manifest), encoding='utf-8')
                result = field.verify_venue(path)
                self.assertEqual(len(manifest['sessions']), result['udpPreflightsVerified'])
                self.assertEqual(25, result['serverAcknowledgements'])
                self.assertNotIn('192.168', json.dumps(result))
                if mode == 'Independent':
                    absent = deepcopy(manifest)
                    absent['sessions'][-1].pop('udpPreflight')
                    path.write_text(json.dumps(absent), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, 'for every session'):
                        field.verify_venue(path)
                    path.write_text(json.dumps(manifest), encoding='utf-8')
                    duplicate = result['sessions'][0]['udpPreflight']['exchangeSha256']
                    files = manifest['sessions'][1]['udpPreflight']
                    for filename, encoding in ((files['listener'], 'utf-16'), (files['probe'], 'utf-8-sig')):
                        report_path = root / filename
                        report = json.loads(report_path.read_text(encoding=encoding))
                        report['exchangeSha256'] = duplicate
                        report_path.write_text(json.dumps(report), encoding=encoding)
                    with self.assertRaisesRegex(field.EvidenceError, 'reused a UDP preflight exchange'):
                        field.verify_venue(path)

    def test_alignment_evidence_binds_mixed_and_linked_mr_to_locked_bytes(self):
        for mode, mr_rooms in (('Independent', (2, 4)), ('Linked', (1, 2, 3, 4, 5))):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, mode, remote=True, with_journals=True, mr_rooms=mr_rooms)
                report = field.verify_venue(path)
                self.assertEqual(len(mr_rooms), report['roomAlignmentsVerified'])
                self.assertEqual(len(mr_rooms) * 5, report['questLogcatPlayers'])
                self.assertEqual(25, report['serverAcknowledgements'])
                self.assertFalse(report['physicalHostsVerified'])
                self.assertFalse(report['networkCapacityAccepted'])
                rooms = [row['roomId'] for entry in report['sessions'] for row in entry.get('roomAlignments', [])]
                self.assertEqual(list(mr_rooms), rooms)
                mr = next(entry for entry in manifest['sessions'] if 'roomAlignments' in entry)
                locked = root / next(iter(mr['roomAlignments'].values()))
                saved = locked.read_bytes()
                locked.write_bytes(saved.rstrip())
                with self.assertRaisesRegex(field.EvidenceError, 'bytes differ from the sealed session lock'):
                    field.verify_venue(path)
                locked.write_bytes(saved)
                lost = deepcopy(manifest)
                original = next(entry for entry in lost['sessions'] if 'roomAlignments' in entry)
                original.pop('roomAlignments')
                if mode == 'Linked':
                    original['roomAlignments'] = {}
                path.write_text(json.dumps(lost), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'for every original MR room'):
                    field.verify_venue(path)

    def test_mr_alignment_requires_original_game_profile_room_and_quest_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Independent', remote=True, with_journals=True, mr_rooms=(2, 4))
            mr = manifest['sessions'][1]
            session, _, _ = field.management_zip(root / mr['evidenceZip'])
            launcher = json.loads((root / mr['launcherReport']).read_text())
            header = launcher['finalWorld']['header']
            alignment = root / mr['roomAlignments']['2']
            wrong_room = root / manifest['sessions'][3]['roomAlignments']['4']
            with self.assertRaisesRegex(field.EvidenceError, 'calibrated game source'):
                field.verify_room_alignments(session, dict(header, origin='Simulation'), {2: alignment})
            session['roomAlignment']['room2'] = hashlib.sha256(wrong_room.read_bytes()).hexdigest()
            with self.assertRaisesRegex(field.EvidenceError, 'does not identify the original MR room'):
                field.verify_room_alignments(session, header, {2: wrong_room})
            no_journals = deepcopy(manifest)
            for entry in no_journals['sessions']:
                entry.pop('worldJournal')
            path.write_text(json.dumps(no_journals), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'journals for the full batch'):
                field.verify_venue(path)
            player = mr['players'][0]
            player.pop('logcatPid')
            log = root / player['log']
            markers = [match[2] for line in log.read_text().splitlines() if (match := field.LOGCAT_UNITY.fullmatch(line))
                       and match[2].startswith(field.PLAYER_MARKERS)]
            log.write_text('\n'.join(markers), encoding='utf-8')
            path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'all original Quest logs'):
                field.verify_venue(path)

    def test_single_session_cli_accepts_original_mr_alignment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, manifest, _ = venue_fixture(root, 'Independent', remote=True, with_journals=True, mr_rooms=(2,))
            mr = manifest['sessions'][1]
            command = [sys.executable, str(SCRIPT), '--topology', 'direct-lan', '--server-ip', manifest['serverIps'][0],
                       '--world-journal', str(root / mr['worldJournal']), '--room-alignment', '2', str(root / mr['roomAlignments']['2']),
                       '--launcher-report', str(root / mr['launcherReport']), '--server-log', str(root / mr['serverLog'])]
            session, stats, endpoint = field.management_zip(root / mr['evidenceZip'])
            for option, data in [('session', session), ('statistics', stats), ('endpoint', endpoint)]:
                path = root / f'{option}.json'
                path.write_text(json.dumps(data), encoding='utf-8')
                command += ['--' + option, str(path)]
            for player in mr['players']:
                command += ['--quest-player', player['address'], str(root / player['log']), str(player['logcatPid'])]
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(2, json.loads(result.stdout)['roomAlignments'][0]['roomId'])
            self.assertNotIn(directory, result.stdout)
            duplicate = subprocess.run(command + ['--room-alignment', '2', str(root / mr['roomAlignments']['2'])],
                                       capture_output=True, text=True, timeout=10)
            self.assertEqual(1, duplicate.returncode)
            self.assertNotIn(directory, duplicate.stderr)

    def test_original_world_journal_matches_the_sealed_evidence(self):
        data = fixture()
        world = data[2]['finalWorld']
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.worldlog'
            world_journal(path, world)
            result = field.verify(*data, world_journal=path)
            self.assertEqual({'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'frames': 80, 'runningFrames': 78},
                             result['worldJournal'])
            self.assertNotIn('worldJournal', field.verify(*data))
            for changes, message in (
                ({'header_changes': {'streamId': id_for(3)}}, 'source or record integrity'),
                ({'header_changes': {'calibration': 'quest-room-mr-v1'}}, 'source or record integrity'),
                ({'active': False}, 'active play'),
                ({'sealed': False}, 'durable world and combat seals'),
                ({'combat': 1}, 'durable world and combat seals'),
                ({'end_sequence': 10}, 'Invalid numeric evidence'),
            ):
                with self.subTest(changes=changes):
                    world_journal(path, world, **changes)
                    with self.assertRaisesRegex(field.EvidenceError, message):
                        field.verify(*data, world_journal=path)
            world_journal(path, world)
            world['capturedAtUtc'] = '2026-11-09T00:00:09+00:00'
            with self.assertRaisesRegex(field.EvidenceError, 'terminal capture'):
                field.verify(*data, world_journal=path)
            corrupted = bytearray(path.read_bytes())
            corrupted[-1] ^= 1
            path.write_bytes(corrupted)
            with self.assertRaisesRegex(field.EvidenceError, 'source or record integrity'):
                field.verify(*data, world_journal=path)

    def test_venue_requires_all_original_journals_when_supplied(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, mode, with_journals=True)
                report = field.verify_venue(path)
                self.assertEqual(5 if mode == 'Independent' else 1, report['worldJournalsVerified'])
                self.assertTrue(all(row['worldJournal']['frames'] == row['worldSequence'] for row in report['sessions']))
                source = root / manifest['sessions'][0]['worldJournal']
                launcher = json.loads((root / manifest['sessions'][0]['launcherReport']).read_text())
                world_journal(source, launcher['finalWorld'], end_sequence=7)
                with self.assertRaisesRegex(field.EvidenceError, 'management boundary'):
                    field.verify_venue(path)
                if mode == 'Independent':
                    manifest['sessions'][0].pop('worldJournal')
                    path.write_text(json.dumps(manifest), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, 'journal for every session'):
                        field.verify_venue(path)

    def test_quest_logcat_reconnect_uses_the_server_acknowledged_connection(self):
        data = fixture()
        data[3]['players'][1]['headset'] = 'Quest3'
        address, log = data[7].pop()
        earlier = 'VR_CLIENT_CONNECTED id=8\nVR_CLIENT_DISCONNECTED\n'
        startup, rest = data[6].split('\n', 1)
        data[6] = startup + '\nVR_SERVER_ADMISSION_APPROVED id=8\nVR_SERVER_PEER id=8 endpoint=unavailable\n' + rest
        report = field.verify(*data, quest_player_logs=[(address, quest_logcat(earlier + log), 7342)])
        self.assertEqual((2, 1), (report['serverAcknowledgements'], report['questLogcatPlayers']))
        self.assertFalse(report['physicalHostsVerified'])
        self.assertFalse(report['networkCapacityAccepted'])

    def test_quest_logcat_rejects_wrong_source_or_missing_original_records(self):
        for case, error in (
            ('wrong pid', 'original client startup'),
            ('foreign marker', 'outside the original client process'),
            ('wrong port', 'original client startup'),
            ('duplicate startup', 'original client startup'),
            ('missing startup', 'outside the original client process'),
            ('missing disconnect', 'terminal disconnect'),
            ('wrong headset', 'Quest 3 admission'),
            ('local quest', 'own direct LAN address'),
            ('wrong admission', 'admission or room'),
            ('wrong udp source', 'UDP peer differs'),
            ('wrong sealed world', 'final seals'),
        ):
            with self.subTest(case=case):
                data = fixture(remote=case != 'local quest')
                data[3]['players'][1]['headset'] = 'ViveXr' if case == 'wrong headset' else 'Quest3'
                address, log = data[7].pop()
                log = quest_logcat(log, port=7778 if case == 'wrong port' else 7777)
                if case == 'foreign marker':
                    log = log.replace(logcat_line('VR_CLIENT_DISCONNECTED'), logcat_line('VR_CLIENT_DISCONNECTED', 7343))
                elif case == 'duplicate startup':
                    log += logcat_line('VR_NETWORK_STARTED role=Client started=True background=False port=7777')
                elif case == 'missing startup':
                    log = ''.join(line for line in log.splitlines(keepends=True) if 'VR_NETWORK_STARTED' not in line)
                elif case == 'missing disconnect':
                    log = log.replace(logcat_line('VR_CLIENT_DISCONNECTED'), '')
                elif case == 'wrong admission':
                    log = log.replace(id_for(14), id_for(500))
                elif case == 'wrong udp source':
                    address = ipaddress.IPv4Address('192.168.5.22')
                elif case == 'wrong sealed world':
                    log = log.replace('"worldSequence": 80', '"worldSequence": 79')
                with self.assertRaisesRegex(field.EvidenceError, error):
                    field.verify(*data, quest_player_logs=[(address, log, 7343 if case == 'wrong pid' else 7342)])

    def test_quest_logcat_and_windows_cli_reports_remain_private(self):
        topology, ips, launcher, session, stats, endpoint, server, clients = fixture()
        session['players'][1]['headset'] = 'Quest3'
        with tempfile.TemporaryDirectory(prefix='quest-field-check-') as directory:
            root = Path(directory)
            command = [sys.executable, str(SCRIPT), '--topology', topology, '--server-ip', str(next(iter(ips)))]
            for option, value in [('launcher-report', launcher), ('session', session), ('statistics', stats), ('endpoint', endpoint), ('server-log', server)]:
                path = root / option
                path.write_text(value if type(value) is str else json.dumps(value), encoding='utf-8')
                command += ['--' + option, str(path)]
            windows, quest = root / 'Player.log', root / 'Quest logcat.txt'
            windows.write_text(clients[0][1], encoding='utf-8')
            quest.write_text(quest_logcat(clients[1][1]), encoding='utf-8')
            command += ['--player', str(clients[0][0]), str(windows), '--quest-player', str(clients[1][0]), str(quest)]
            success = subprocess.run([*command, '7342'], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(success.stdout)['questLogcatPlayers'], 1)
            self.assertNotIn('7342', success.stdout)
            self.assertNotIn('192.168', success.stdout)
            for suffix in (['7343'], ['-1'], ['7342', '--player', str(clients[1][0]), str(quest)]):
                failure = subprocess.run([*command, *suffix], capture_output=True, text=True)
                self.assertEqual(failure.returncode, 1)
                self.assertEqual(failure.stdout, '')
                self.assertNotIn(directory, failure.stderr)
                self.assertNotIn('192.168', failure.stderr)

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

    def test_combat_journal_recomputes_shots_kills_and_clamped_health(self):
        data = fixture()
        launcher, session, stats, clients = data[2], data[3], data[4], data[7]
        shooter, target = (row['id'] for row in session['players'])
        shot_a, shot_b, shot_c, enemy = map(id_for, (21, 22, 23, 24))
        events = [(0, shooter, shot_a, None, 0), (1, shooter, shot_a, enemy, 0), (2, shooter, shot_a, enemy, 0),
                  (0, shooter, shot_b, None, 0), (0, shooter, shot_c, None, 0),
                  (4, target, None, None, 20), (4, target, None, None, 100)]
        launcher['finalCombatStream']['acceptedSequence'] = session['combatStream']['acceptedSequence'] = len(events)
        stats['origin'] = 'Simulation'
        stats['players'][0].update(ammoUsed=3, shotsHit=1, kills=1, accuracyPercent=field.Decimal('33.33'))
        stats['players'][1].update(hitsReceived=2, damageTaken=100, health=0)
        for index, (address, log) in enumerate(clients):
            lines = log.splitlines()
            result = json.loads(lines[1].split(' ', 1)[1])
            result.update(stats['players'][index], finalStreamSequence=len(events))
            result['accuracyPercent'] = float(result['accuracyPercent'])
            lines[1] = 'VR_CLIENT_DEBRIEF_FINAL ' + json.dumps(result)
            clients[index] = address, '\n'.join(lines) + '\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'original.journal'
            combat_journal(path, launcher, events)
            raw = path.read_bytes()
            self.assertEqual(field.verify(*data, combat_journal=path)['combatJournal'],
                             {'sha256': hashlib.sha256(raw).hexdigest(), 'events': 7, 'players': 2})
            self.assertEqual(path.read_bytes(), raw)
            combat_journal(path, launcher, [*events[:-1], (4, target, None, None, 10)])
            self.assertTrue(field.verify(*data)['consistent'])
            with self.assertRaisesRegex(field.EvidenceError, 'replay differs from sealed player statistics'):
                field.verify(*data, combat_journal=path)
            combat_journal(path, launcher, events, receipt=id_for(901))
            with self.assertRaisesRegex(field.EvidenceError, 'combat journal acknowledgement'):
                field.verify(*data, combat_journal=path)
            combat_journal(path, launcher, [events[1], events[0], *events[2:]])
            with self.assertRaisesRegex(field.EvidenceError, 'hit needs the original unscored shot'):
                field.verify(*data, combat_journal=path)
            combat_journal(path, dict(launcher, sessionId=id_for(911)), events)
            with self.assertRaisesRegex(field.EvidenceError, 'header differs'):
                field.verify(*data, combat_journal=path)
            path.write_bytes(raw[:-1])
            with self.assertRaisesRegex(field.EvidenceError, 'Torn combat journal'):
                field.verify(*data, combat_journal=path)
            path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
            with self.assertRaisesRegex(field.EvidenceError, 'checksum mismatch'):
                field.verify(*data, combat_journal=path)

    def test_cli_success_and_private_failure_diagnostics(self):
        topology, ips, launcher, session, stats, endpoint, server, clients = fixture()
        with tempfile.TemporaryDirectory(prefix='field-check-') as directory:
            root = Path(directory)
            command = [sys.executable, str(SCRIPT), '--topology', topology, '--server-ip', str(next(iter(ips)))]
            journal = root / 'original.worldlog'
            world_journal(journal, launcher['finalWorld'])
            for option, value in [('launcher-report', launcher), ('session', session), ('statistics', stats), ('endpoint', endpoint), ('server-log', server)]:
                path = root / option
                path.write_text(value if type(value) is str else json.dumps(value), encoding='utf-8')
                command += ['--' + option, str(path)]
            for number, (address, log) in enumerate(clients, 1):
                path = root / f'Player {number}.log'
                path.write_text(log, encoding='utf-8')
                command += ['--player', str(address), str(path)]
            success = subprocess.run(command, capture_output=True, text=True, check=True)
            legacy = json.loads(success.stdout)
            self.assertTrue(legacy['consistent'])
            self.assertNotIn('worldJournal', legacy)
            archived = subprocess.run([*command, '--world-journal', str(journal)], capture_output=True, text=True, check=True)
            self.assertEqual(80, json.loads(archived.stdout)['worldJournal']['frames'])
            combat = root / 'original.journal'
            combat_journal(combat, launcher)
            closed = subprocess.run([*command, '--world-journal', str(journal), '--combat-journal', str(combat)],
                                    capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(closed.stdout)['combatJournal']['events'], 0)
            self.assertNotIn(directory, closed.stdout)
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

    def test_venue_combat_journal_rejects_unsealed_original_in_either_topology(self):
        for mode in ('Linked', 'Independent'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, mode, with_journals=True)
                for index, entry in enumerate(manifest['sessions']):
                    entry['combatJournal'] = f'Room {index + 1}.journal'
                    launcher = field.read_json((root / entry['launcherReport']).read_text(encoding='utf-8'))
                    combat_journal(root / entry['combatJournal'], launcher, sealed=index != 0)
                path.write_text(json.dumps(manifest), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'combat journal.*seal'):
                    field.verify_venue(path)
                entry = manifest['sessions'][0]
                launcher = field.read_json((root / entry['launcherReport']).read_text(encoding='utf-8'))
                combat_journal(root / entry['combatJournal'], launcher)
                report = field.verify_venue(path)
                self.assertEqual(report['combatJournalsVerified'], len(manifest['sessions']))
                self.assertEqual(sum(row['combatJournal']['players'] for row in report['sessions']), 25)
                if mode == 'Independent':
                    del entry['combatJournal']
                    path.write_text(json.dumps(manifest), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, 'combat journal for every session'):
                        field.verify_venue(path)

    def test_venue_verifies_the_original_guarded_begin_for_both_topologies(self):
        request = id_for(999)
        for mode in ('Linked', 'Independent'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, batch = venue_fixture(root, mode, remote=True, with_journals=True,
                    mr_rooms=(2, 4) if mode == 'Independent' else ())
                manifest['verifyTrackingBegin'] = True
                path.write_text(json.dumps(manifest), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'missing an original guarded Begin witness'):
                    field.verify_venue(path)

                first_source = None
                for entry, row in zip(manifest['sessions'], batch['sessions'], strict=True):
                    session, _, _ = field.management_zip(root / entry['evidenceZip'])
                    world = json.loads((root / entry['launcherReport']).read_text())['finalWorld']
                    players = [{'id': player['id'], 'roomId': player['roomId'], 'connected': True,
                                'health': 100, 'rig': {'kind': 'Tracked'}} for player in session['players']]
                    journal = root / entry['worldJournal']
                    world_journal(journal, world, players=lambda _, phase: players if phase == 'Preparing' else [], preparing_sequence=6)
                    row['trackingBegin'] = {'requestId': request, 'appliedAtSequence': 7, 'frame': {
                        'streamId': world['header']['streamId'], 'worldSequence': 1, 'elapsedMilliseconds': 100}}
                    if first_source is None:
                        first_source = journal, world, players

                closure = root / manifest['closure']
                closure.write_text(json.dumps({'batch': batch}), encoding='utf-8')
                report = field.verify_venue(path)
                self.assertEqual({'requestId': request, 'sessions': len(batch['sessions']), 'trackedPlayers': 25}, report['trackingBegin'])
                self.assertTrue(all(item['worldJournal']['trackingBegin']['firstRunningFrame'] == 2 for item in report['sessions']))
                witness = batch['sessions'][-1]['trackingBegin']
                original_frame = witness['frame'].copy()
                witness['frame']['streamId'] = id_for(888)
                closure.write_text(json.dumps({'batch': batch}), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'another world source'):
                    field.verify_venue(path)
                witness['frame'] = original_frame
                if mode == 'Independent':
                    witness['requestId'] = id_for(997)
                    closure.write_text(json.dumps({'batch': batch}), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, 'one original guarded Begin request'):
                        field.verify_venue(path)
                    witness['requestId'] = request
                closure.write_text(json.dumps({'batch': batch}), encoding='utf-8')

                journal, world, players = first_source
                for sequence, rig, message in ((7, 'Tracked', 'original Preparing boundary'), (6, 'Simulated', 'original tracked roster')):
                    players[0]['rig']['kind'] = rig
                    world_journal(journal, world, players=lambda _, phase: players if phase == 'Preparing' else [], preparing_sequence=sequence)
                    with self.assertRaisesRegex(field.EvidenceError, message):
                        field.verify_venue(path)
                manifest.pop('verifyTrackingBegin')
                path.write_text(json.dumps(manifest), encoding='utf-8')
                self.assertNotIn('trackingBegin', field.verify_venue(path))

    def test_venue_full_participation_requires_original_witness(self):
        for mode in ('Linked', 'Independent'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, batch = venue_fixture(root, mode, remote=True, with_journals=True,
                    mr_rooms=(2, 4) if mode == 'Independent' else ())
                manifest['verifyParticipationBegin'] = True
                path.write_text(json.dumps(manifest), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'missing an original guarded Begin witness'):
                    field.verify_venue(path)

                request_id = id_for(999)
                sources = []
                for entry, row in zip(manifest['sessions'], batch['sessions'], strict=True):
                    session, _, _ = field.management_zip(root / entry['evidenceZip'])
                    world = json.loads((root / entry['launcherReport']).read_bytes())['finalWorld']
                    mr = session['environment']['mode'] == 'MR'
                    players = [{'id': p['id'], 'roomId': p['roomId'], 'connected': True, 'health': 100,
                                'rig': {'kind': 'Tracked' if mr else 'Simulated'}} for p in session['players']]
                    journal = root / entry['worldJournal']
                    world_journal(journal, world, players=lambda _, phase: players if phase == 'Preparing' else [], preparing_sequence=6)
                    row['participationBegin'] = {'requestId': request_id, 'appliedAtSequence': 7,
                        'frame': {'streamId': world['header']['streamId'], 'worldSequence': 1, 'elapsedMilliseconds': 100}}
                    sources.append((journal, world, players, mr))

                (root / manifest['closure']).write_text(json.dumps({'batch': batch}), encoding='utf-8')
                result = field.verify_venue(path)
                tracked = 10 if mode == 'Independent' else 0
                self.assertEqual({'requestId': request_id, 'sessions': len(sources), 'participants': 25,
                    'trackedPlayers': tracked, 'simulatedPlayers': 25 - tracked}, result['participationBegin'])
                self.assertTrue(all(row['worldJournal']['participationBegin']['firstRunningFrame'] == 2 for row in result['sessions']))

                journal, world, players, _ = sources[0]
                players[0]['connected'] = False
                world_journal(journal, world, players=lambda _, phase: players if phase == 'Preparing' else [], preparing_sequence=6)
                with self.assertRaisesRegex(field.EvidenceError, 'original participating roster'):
                    field.verify_venue(path)
                players[0]['connected'] = True
                world_journal(journal, world, players=lambda _, phase: players if phase == 'Preparing' else [],
                              preparing_sequence=6, running_sequence=8)
                with self.assertRaisesRegex(field.EvidenceError, 'subsequent application'):
                    field.verify_venue(path)
                world_journal(journal, world, players=lambda _, phase: players if phase == 'Preparing' else [], preparing_sequence=6)

                path.write_text(json.dumps(dict(manifest, verifyTrackingBegin=True)), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'Choose one guarded Begin'):
                    field.verify_venue(path)
                path.write_text(json.dumps(dict(manifest, verifyTrackingBegin=True, verifyParticipationBegin=False)), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'missing an original guarded Begin witness'):
                    field.verify_venue(path)
                if mode == 'Independent':
                    path.write_text(json.dumps(manifest), encoding='utf-8')
                    journal, world, players, _ = next(source for source in sources if source[3])
                    players[0]['rig']['kind'] = 'Simulated'
                    world_journal(journal, world, players=lambda _, phase: players if phase == 'Preparing' else [], preparing_sequence=6)
                    with self.assertRaisesRegex(field.EvidenceError, 'original participating roster'):
                        field.verify_venue(path)

    def test_venue_accepts_quest_logcat_in_both_topologies(self):
        for mode, quest_per_room in (('Linked', 5), ('Independent', 1)):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                path, manifest, _ = venue_fixture(Path(directory), mode, remote=True, quest_per_room=quest_per_room)
                report = field.verify_venue(path)
                self.assertEqual((25, 5 * quest_per_room), (report['serverAcknowledgements'], report['questLogcatPlayers']))
                self.assertEqual([row['playersOutsideDeclaredServer'] for row in report['rooms']], [quest_per_room] * 5)
                manifest['sessions'][0]['players'][4]['logcatPid'] = '7342'
                path.write_text(json.dumps(manifest), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'Invalid numeric evidence'):
                    field.verify_venue(path)

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
