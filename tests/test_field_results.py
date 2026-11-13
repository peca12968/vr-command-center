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


def venue_fixture(root, mode, *, remote=False, quest_per_room=0, with_journals=False, mr_rooms=(), room_sizes=(5,) * 5,
                  id_offset=0, minutes_after=0, game_server=False):
    def write_json(path, value):
        path.write_text(json.dumps(value), encoding='utf-8')

    server_ip, remote_ip = '192.168.5.10', '192.168.5.20'
    groups = [[1, 2, 3, 4, 5]] if mode == 'Linked' else [[room] for room in range(1, 6)]
    started = datetime.fromisoformat('2026-11-09T00:00:00+00:00') + timedelta(minutes=minutes_after)
    ended = started + timedelta(minutes=1)
    batch = {'requestId': id_for(1000 + id_offset), 'recordedAtUtc': ended.isoformat(), 'sessions': []}
    manifest = {'version': 1, 'mode': mode, 'topology': 'direct-lan' if remote else 'same-host',
                'serverIps': [server_ip], 'closure': 'closure.json', 'sessions': []}
    for rooms in groups:
        prefix = f'Room {rooms[0]}'
        experience = 'MR' if rooms[0] in mr_rooms else 'VR'
        origin = 'GameServer' if game_server or experience == 'MR' else 'Simulation'
        _, _, launcher, session, stats, endpoint, _, _ = fixture(remote=False)
        session_id, stream = id_for(100 + rooms[0] + id_offset), id_for(200 + rooms[0] + id_offset)
        port = 7776 + rooms[0]
        launcher.update(sessionId=session_id, streamId=stream)
        launcher['udpBinding']['port'] = port
        launcher['finalWorld']['header'].update(sessionId=session_id, streamId=stream, roomIds=rooms, origin=origin,
            calibration='quest-room-mr-v1' if experience == 'MR' else 'uncalibrated-vr')
        launcher['finalCombatStream'].update(streamId=stream, origin=origin)
        session.update(id=session_id, mode=mode, roomIds=rooms, players=[], combatStream=launcher['finalCombatStream'],
                       startedAtUtc=started.isoformat(), endedAtUtc=ended.isoformat(),
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
            for seat in range(room_sizes[room - 1]):
                connection = room * 5 + seat
                player, admission = id_for(300 + connection + id_offset), id_for(400 + connection + id_offset)
                is_quest = experience == 'MR' or seat >= room_sizes[room - 1] - quest_per_room
                peer = f'192.168.5.{30 + connection}' if is_quest else remote_ip if remote and room == 5 and seat == room_sizes[room - 1] - 1 else server_ip
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


def quest_capture_venue_fixture(root, mode, *, quest_per_room=2, batches=2, use_capture_tool=False, interrupt_first=False, with_journals=False):
    path, manifest, _ = venue_fixture(root, mode, remote=True, quest_per_room=quest_per_room, with_journals=with_journals)
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
    root = Path(__file__).parent
    raw = (root / (serial + '.log')).read_bytes()
    if (root / (serial + '.interrupt')).exists():
        for line in raw.splitlines(keepends=True):
            if b'VR_CLIENT_DEBRIEF_FINAL ' in line:
                break
            sys.stdout.buffer.write(line)
    else:
        sys.stdout.buffer.write(raw)
""", encoding='utf-8')
        for serial, raw in inputs.items():
            (root / (serial + '.log')).write_bytes(raw)
    if interrupt_first:
        assert use_capture_tool and batches == 1
        interruption = root / (mapped[0]['serial'] + '.interrupt')
        interruption.touch()
    reports = []
    for index in range(batches):
        directory = root / f'capture batch {index + 1}'
        seats = mapped[index::batches]
        if use_capture_tool:
            plan = {'version': 1, 'topology': mode, 'seats': seats}
            with redirect_stderr(io.StringIO()):
                result = asyncio.run(capture_tool.capture_venue([sys.executable, str(adb)], plan, directory, 25))
            assert result['complete'] is (not interrupt_first) and result['capturedSeats'] == len(seats) - int(interrupt_first)
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
    if interrupt_first:
        retry = capture_tool.retry_capture_plan(plan, root / reports[0])
        assert retry['seats'] == mapped[:1]
        interruption.unlink()
        directory = root / 'retry batch'
        with redirect_stderr(io.StringIO()):
            result = asyncio.run(capture_tool.capture_venue([sys.executable, str(adb)], retry, directory, 25))
        assert result['complete'] and result['capturedSeats'] == 1
        reports.append(str((directory / 'capture-report.json').relative_to(root)))
    (root / 'network-plan.json').write_text(json.dumps(network), encoding='utf-8')
    manifest['questCaptures'] = {'networkPlan': 'network-plan.json', 'reports': reports}
    path.write_text(json.dumps(manifest), encoding='utf-8')
    return path, manifest


def observed_quest_capture_spec(root, spec):
    network = json.loads((root / spec['networkPlan']).read_bytes())
    rows = [{'roomId': row['roomId'], 'seat': row['seat'], 'serial': f"fixture-{row['roomId']}-{row['seat']}"}
            for row in network['sources']]
    (root / 'quest-device-map.json').write_text(json.dumps({'version': 1, 'seats': rows}), encoding='utf-8')
    return {'deviceMap': 'quest-device-map.json', 'reports': spec['reports']}


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
if args[2:] == ['shell', 'getprop', 'ro.serialno']:
    count = root/'serial-count'
    calls = int(count.read_text()) if count.exists() else 0
    count.write_text(str(calls+1))
    values = settings.get('deviceSerials', ['HEADSET-A'])
    print(values[min(calls, len(values)-1)])
    sys.exit(0)
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
        (self.root/'serial-count').unlink(missing_ok=True)

    def capture(self, seconds=4):
        port, expected = capture_tool.read_connection(self.original)
        return asyncio.run(capture_tool.capture(self.adb, port, expected, self.output, seconds))

    def test_bound_capture_checks_original_device_before_read_and_publish(self):
        port, expected = capture_tool.read_connection(self.original)
        raw = quest_logcat(self.player_log, port).encode()
        proof = ('a' * 32, hashlib.sha256(('a' * 32 + '\nHEADSET-A').encode()).hexdigest())
        self.prepare(raw, deviceSerials=['unknown'])
        with self.assertRaisesRegex(capture_tool.field.EvidenceError, 'identity could not be read'):
            asyncio.run(capture_tool.capture(self.adb, port, expected, self.output, 10, device_identity=proof))
        self.assertFalse((self.root / 'pid-count').exists())
        self.assertFalse(self.partial.exists())
        self.prepare(raw, deviceSerials=['HEADSET-B'])
        with self.assertRaisesRegex(capture_tool.field.EvidenceError, 'differs from the original deployment'):
            asyncio.run(capture_tool.capture(self.adb, port, expected, self.output, 10, device_identity=proof))
        self.assertFalse((self.root / 'pid-count').exists())
        self.prepare(raw, deviceSerials=['HEADSET-A', 'HEADSET-B'])
        with self.assertRaisesRegex(capture_tool.field.EvidenceError, 'differs from the original deployment'):
            asyncio.run(capture_tool.capture(self.adb, port, expected, self.output, 10, device_identity=proof))
        self.assertFalse(self.output.exists())
        self.assertEqual(raw, self.partial.read_bytes())
        self.partial.unlink()
        self.prepare(raw, deviceSerials=['headset-a', 'HEADSET-A'])
        report = asyncio.run(capture_tool.capture(self.adb, port, expected, self.output, 10, device_identity=proof))
        self.assertTrue(report['complete'])
        self.assertEqual(raw, self.output.read_bytes())
        self.assertEqual('2', (self.root / 'serial-count').read_text())

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
    def staged_batch(self, root, mode, count, id_offset, minutes_after, *, remote=False, tracked_fire=False,
                     missing_shot=False, runtime='Test OpenXR Runtime'):
        root.mkdir()
        path, manifest, _ = venue_fixture(root, mode, remote=remote, with_journals=True,
            room_sizes=(count,) * 5, id_offset=id_offset, minutes_after=minutes_after)
        offsets = [0] if mode == 'Linked' else [0, 100, 200, 300, 400]
        capture_start = datetime.fromisoformat('2026-11-09T08:00:00+08:00') + timedelta(minutes=minutes_after)
        if tracked_fire:
            def tracked_packet(packet):
                for player in packet['frame']['players']:
                    player['rig'] = {'kind': 'Tracked'}

            def fire_frame(player):
                return None if missing_shot and (player['roomId'], player['seat']) == (5, count - 1) else 16

            self.concurrent_fire_journals(root, manifest, fire_frame=fire_frame, edit_packet=tracked_packet, capture_start=capture_start)
            for entry in manifest['sessions']:
                _, _, endpoint = field.management_zip(root / entry['evidenceZip'])
                startup = PlayerSourceEvidenceTests.openxr_startup(runtime).replace('port=7777', f"port={endpoint['port']}")
                for player in entry['players']:
                    log = root / player['log']
                    log.write_bytes(startup.encode() + log.read_bytes())
        else:
            self.concurrent_journals(root, manifest, offsets, capture_start=capture_start)
            manifest['minimumConcurrentMilliseconds'] = 1000
        self.add_shared_release(root, manifest, 0)
        if count != 5:
            manifest['expectedPlayersPerRoom'] = count
        if mode == 'Linked':
            manifest = self.pack_venue(root, manifest)
        path.write_text(json.dumps(manifest), encoding='utf-8')
        return str(path.relative_to(root.parent))

    def staged_plan(self, root, *, remote=False, tracked_fire=False):
        names = [self.staged_batch(root / f'{count}-{mode}', mode, count, index * 10000, minutes, remote=remote, tracked_fire=tracked_fire)
                 for minutes, count in enumerate((1, 2, 5), 1)
                 for index, mode in ((minutes * 2, 'Independent'), (minutes * 2 + 1, 'Linked'))]
        return {'version': 1, 'topology': 'direct-lan' if remote else 'same-host',
                'minimumConcurrentMilliseconds': 2000, 'venueManifests': names}

    def test_staged_venue_checks_original_batches_and_has_one_report_per_mode_and_size(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.staged_plan(root)
            plan['venueManifests'].reverse()
            path = root / 'stages.json'
            raw = json.dumps(plan).encode('utf-8-sig')
            path.write_bytes(raw)
            result = subprocess.run([sys.executable, str(SCRIPT), '--venue-stages', str(path)],
                                    capture_output=True, check=True)
            report = json.loads(result.stdout)
            self.assertEqual([(mode, size) for size in (5, 10, 25) for mode in ('Independent', 'Linked')],
                             [(item['mode'], item['players']) for item in report['stages']])
            self.assertEqual(80, report['serverAcknowledgements'])
            self.assertEqual(6, len({item['closureRequestId'] for item in report['stages']}))
            self.assertEqual(hashlib.sha256(raw).hexdigest(), report['planSha256'])
            release = root / '1-Independent' / 'release.json'
            self.assertEqual(hashlib.sha256(release.read_bytes()).hexdigest(), report['venueReleaseSha256'])
            self.assertFalse(report['physicalHostsVerified'])
            self.assertFalse(report['networkCapacityAccepted'])
            self.assertNotIn('requireVerifiedVenueStart', report)
            self.assertTrue(all('verifiedVenueStart' not in row for row in report['stages']))
            path.write_text(json.dumps(dict(plan, requireVerifiedVenueStart=True)), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'Venue manifest entry 1: missing verified Windows start receipt'):
                field.verify_venue_stages(path)
            path.write_text(json.dumps(dict(plan, requireVerifiedVenueStart=1)), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'verified Windows start option must be boolean'):
                field.verify_venue_stages(path)

    def test_staged_inspection_reports_missing_bad_and_reused_evidence_in_one_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.staged_plan(root)
            names = plan['venueManifests']
            (root / names[1]).unlink()
            (root / names[2]).write_text('{', encoding='utf-8')
            names[3] = names[0]
            path = root / 'stages.json'
            path.write_text(json.dumps(plan), encoding='utf-8')
            result = subprocess.run([sys.executable, str(SCRIPT), '--venue-stages', str(path), '--inspect-venue-stages'],
                                    capture_output=True, check=False)
            self.assertEqual(1, result.returncode, result.stderr)
            self.assertFalse(result.stderr)
            inspection = json.loads(result.stdout)
            self.assertFalse(inspection['complete'])
            self.assertEqual(['conflict', 'needs-evidence', 'needs-evidence', 'needs-evidence', 'verified', 'verified'],
                             [row['status'] for row in inspection['entries']])
            self.assertEqual([[2], [3], [1, 4]], [issue['entries'] for issue in inspection['issues']])
            self.assertEqual([{'mode': 'Linked', 'players': 5}, {'mode': 'Independent', 'players': 10},
                              {'mode': 'Linked', 'players': 10}], inspection['missingStages'])
            self.assertNotIn(str(root), result.stdout.decode())

    def test_staged_venue_rejects_incomplete_repeated_misordered_or_mismatched_batches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.staged_plan(root)
            names = plan['venueManifests']
            reused = self.staged_batch(root / 'reused', 'Independent', 2, 20000, 2)
            late = self.staged_batch(root / 'late', 'Independent', 1, 80000, 8)
            remote = self.staged_batch(root / 'remote', 'Independent', 1, 90000, 1, remote=True)
            path = root / 'stages.json'
            for changes, error in (
                ({'venueManifests': names[:-1]}, 'six venue manifests'),
                ({'venueManifests': [names[0], *names[:-1]]}, 'paths must be distinct'),
                ({'venueManifests': [*names[:2], reused, *names[3:]]}, 'reuses an original closure identity'),
                ({'venueManifests': [late, *names[1:]]}, 'do not run in 5, 10 and 25 seat order'),
                ({'venueManifests': [remote, *names[1:]]}, 'topology differs from the staged plan'),
                ({'minimumConcurrentMilliseconds': 9000}, 'continuous concurrent roster required'),
            ):
                with self.subTest(changes=changes):
                    path.write_text(json.dumps(dict(plan, **changes)), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, error):
                        field.verify_venue_stages(path)
            changed_release = root / '5-Linked' / 'release.json'
            changed_release.write_bytes(changed_release.read_bytes() + b'\n')
            self.assertEqual(25, field.verify_venue(root / names[-1])['players'])
            path.write_text(json.dumps(plan), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'same original verified release report'):
                field.verify_venue_stages(path)

    def test_staged_distinct_remote_requirement_cannot_use_weaker_lan_batches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.staged_plan(root, remote=True)
            plan['requireDistinctRemoteRoster'] = True
            path = root / 'stages.json'
            path.write_text(json.dumps(plan), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'distinct original remote sources'):
                field.verify_venue_stages(path)

    def test_staged_plan_applies_tracked_and_sealed_fire_to_all_original_batches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.staged_plan(root, remote=True, tracked_fire=True)
            plan.update(requireTrackedRoster=True, requireConcurrentFire=True, minimumConcurrentMilliseconds=3000)
            path = root / 'stages.json'
            path.write_text(json.dumps(plan), encoding='utf-8')
            last = root / plan['venueManifests'][-1]
            batch = json.loads(last.read_bytes())
            batch.update(requireTrackedRoster=False, requireConcurrentFire=False, minimumConcurrentMilliseconds=6000)
            last.write_text(json.dumps(batch), encoding='utf-8')
            result = subprocess.run([sys.executable, str(SCRIPT), '--venue-stages', str(path)], capture_output=True)
            self.assertEqual(0, result.returncode, result.stderr.decode())
            report = json.loads(result.stdout)
            self.assertTrue(report['requireTrackedRoster'])
            self.assertTrue(report['requireConcurrentFire'])
            self.assertEqual(80, report['serverAcknowledgements'])
            self.assertFalse(report['physicalHostsVerified'])
            self.assertEqual([3000] * 5 + [6000], [stage['concurrentRoster']['minimumMilliseconds'] for stage in report['stages']])
            for stage in report['stages']:
                self.assertEqual('Tracked', stage['concurrentRoster']['rigKind'])
                self.assertEqual(stage['players'], stage['concurrentRoster']['playersWithConfirmedFire'])
                self.assertEqual(stage['worldJournalsVerified'], stage['combatJournalsVerified'])
            for option in ('requireTrackedRoster', 'requireConcurrentFire'):
                path.write_text(json.dumps(dict(plan, **{option: 1})), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'options must be boolean'):
                    field.verify_venue_stages(path)

    def test_staged_roster_rejects_one_batch_with_weaker_original_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.staged_plan(root, remote=True, tracked_fire=True)
            plan.update(requireTrackedRoster=True, requireConcurrentFire=True)
            path = root / 'stages.json'
            for label, extra, message in (
                ('missing-shot', {'missing_shot': True}, 'sealed shot from every original seat'),
                ('mock-tracking', {'runtime': 'Unity Mock Runtime'}, 'Quest or non-mock Windows OpenXR'),
            ):
                with self.subTest(label=label):
                    replaced = self.staged_batch(root / label, 'Linked', 5, 95000, 3, remote=True, tracked_fire=True, **extra)
                    self.assertEqual(25, field.verify_venue(root / replaced)['serverAcknowledgements'])
                    invalid = dict(plan, venueManifests=[*plan['venueManifests'][:-1], replaced])
                    path.write_text(json.dumps(invalid), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, 'Venue manifest entry 6: .*' + message):
                        field.verify_venue_stages(path)
            last = root / plan['venueManifests'][-1]
            batch = json.loads(last.read_bytes())
            batch['sessions'][0].pop('combatJournal')
            last.write_text(json.dumps(batch), encoding='utf-8')
            path.write_text(json.dumps(plan), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'Venue manifest entry 6: .*original combat journals'):
                field.verify_venue_stages(path)

    def test_venue_pilot_requires_declared_room_sizes_and_preserves_original_concurrency(self):
        for mode, offsets in (('Linked', [0]), ('Independent', [0, 100, 200, 300, 400])):
            for count in (1, 2):
                with self.subTest(mode=mode, count=count), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    path, manifest, _ = venue_fixture(root, mode, remote=True, with_journals=True, room_sizes=(count,) * 5)
                    with self.assertRaisesRegex(field.EvidenceError, 'player log count'):
                        field.verify_venue(path)
                    self.concurrent_journals(root, manifest, offsets)
                    manifest.update(expectedPlayersPerRoom=count, minimumConcurrentMilliseconds=1000)
                    path.write_text(json.dumps(manifest), encoding='utf-8')
                    split = field.verify_venue(path)
                    path.write_text(json.dumps(self.pack_venue(root, manifest)), encoding='utf-8')
                    self.assertEqual(split, field.verify_venue(path))
                    self.assertEqual((count, count * 5, count * 5),
                                     (split['expectedPlayersPerRoom'], split['players'], split['serverAcknowledgements']))
                    self.assertEqual([count] * 5, [room['players'] for room in split['rooms']])
                    self.assertEqual(count * 5, split['concurrentRoster']['players'])
                    self.assertEqual(1, split['distinctAddressesOutsideDeclaredServer'])
                    self.assertFalse(split['physicalHostsVerified'])
                    self.assertFalse(split['networkCapacityAccepted'])

    def test_linked_venue_pilot_rejects_the_correct_total_in_the_wrong_rooms(self):
        with tempfile.TemporaryDirectory() as directory:
            path, manifest, _ = venue_fixture(Path(directory), 'Linked', room_sizes=(2, 2, 2, 1, 3))
            manifest['expectedPlayersPerRoom'] = 2
            path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'expected seats in an original room'):
                field.verify_venue(path)
            for count in (False, 0, 6, 2.0, '2'):
                with self.subTest(count=count):
                    path.write_text(json.dumps(dict(manifest, expectedPlayersPerRoom=count)), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, 'Invalid numeric evidence'):
                        field.verify_venue(path)

    def test_venue_control_batches_require_exact_original_running_frames(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, closure = venue_fixture(root, mode, with_journals=True)
                climate = {'weather': 'Storm', 'timeOfDay': 'Night', 'lightning': True}
                enemies = {'behavior': 'Advance', 'autoAttack': False}
                reports = {}
                manifest['venueControlBatches'] = []
                for index, (action, key, policy, sequence) in enumerate((
                    ('SetEnvironment', 'latestEnvironment', climate, 4), ('SetEnemies', 'latestEnemies', enemies, 6),
                )):
                    report = {'requestId': id_for(2010 + index), 'recordedAtUtc': '2026-11-09T00:00:01+00:00',
                              'sessions': [{**{key: row[key] for key in ('sessionId', 'roomIds')},
                                            'appliedAtSequence': sequence, 'state': 'Current'} for row in closure['sessions']], **policy}
                    name = root / (action + '.json')
                    name.write_text(json.dumps({key: report}), encoding='utf-8')
                    reports[action] = (name, key, report)
                    manifest['venueControlBatches'].append({'action': action, 'phaseReport': name.name})
                path.write_text(json.dumps(manifest), encoding='utf-8')

                def configure(packet):
                    if packet['frame']['phase'] != 'Running':
                        return
                    first_policy = packet['sequence'] < 10
                    packet.update(weather='Storm', lightning=True, observedSequence=4 if first_policy else 6)
                    packet['frame'].update(night=True, **({'behavior': 'Hold', 'autoAttack': True} if first_policy else enemies))

                for entry in manifest['sessions']:
                    launcher = json.loads((root / entry['launcherReport']).read_text(encoding='utf-8'))
                    world_journal(root / entry['worldJournal'], launcher['finalWorld'], preparing_sequence=3, edit_packet=configure)
                result = field.verify_venue(path)
                self.assertEqual([item['sessionsVerified'] for item in result['venueControlBatches']], [len(manifest['sessions'])] * 2)
                for row in result['sessions']:
                    frames = row['worldJournal']['venueControlFrames']
                    self.assertEqual([(frame['action'], frame['appliedAtSequence'], frame['worldSequence']) for frame in frames],
                                     [('SetEnvironment', 4, 2), ('SetEnemies', 6, 10)])
                for action, change, message in (
                    ('SetEnvironment', {'lightning': False}, 'disagrees with the venue environment'),
                    ('SetEnemies', {'behavior': 'Hold'}, 'disagrees with the venue enemy'),
                    ('SetEnemies', {'recordedAtUtc': '2026-11-10T00:00:01+00:00'}, 'identity or time'),
                    ('SetEnvironment', {'sessions': []}, 'cover every original session'),
                ):
                    with self.subTest(change=change):
                        name, key, report = reports[action]
                        name.write_text(json.dumps({key: {**report, **change}}), encoding='utf-8')
                        with self.assertRaisesRegex(field.EvidenceError, message):
                            field.verify_venue(path)
                        name.write_text(json.dumps({key: report}), encoding='utf-8')
                name, key, report = reports['SetEnvironment']
                late = deepcopy(report)
                late['sessions'][0]['appliedAtSequence'] = 5
                name.write_text(json.dumps({key: late}), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'lacks an exact Running frame'):
                    field.verify_venue(path)

    def test_prepared_venue_manifest_uses_embedded_original_receipts(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, closure = venue_fixture(root, mode, with_journals=True)
                terminal, report, moved = self.terminal_venue_fixture(root, manifest, closure)
                packed = self.pack_venue(root, manifest)
                bundle = root / packed['venueBundle']
                with zipfile.ZipFile(bundle) as archive:
                    originals = {name: archive.read(name) for name in archive.namelist()}
                rows = []
                for entry in manifest['sessions']:
                    session, _, _ = field.management_zip(root / entry['evidenceZip'])
                    launcher = next(row['result'] for row in report['servers'] if row['result']['sessionId'] == session['id'])
                    rows.append({'sessionId': session['id'], 'streamId': launcher['streamId'], 'throughSequence': session['sequence'],
                                 'finalStreamSequence': launcher['finalCombatStream']['acceptedSequence'],
                                 'worldSequence': launcher['finalWorld']['acceptedSequence'],
                                 'players': [{'playerId': p['id'], 'admissionId': p['admissionId'], 'roomId': p['roomId'], 'acknowledged': True}
                                             for p in session['players']]})
                export = {'version': 1, 'requestId': closure['requestId'], 'sessions': rows}

                def write_bundle(payload):
                    with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
                        for name, raw in originals.items():
                            archive.writestr(name, raw)
                        archive.writestr('debrief-receipts.json', payload)

                raw_receipts = json.dumps(export).encode('utf-8-sig')
                external = root / 'receipts.json'
                external.write_bytes(raw_receipts)
                path.write_text(json.dumps(dict(packed, venueDebriefReceipts=external.name)), encoding='utf-8')
                expected = field.verify_venue(path)
                self.assertEqual(25, expected['venueDebriefReceipts']['acknowledgedPlayers'])
                write_bundle(raw_receipts)
                with self.assertRaisesRegex(field.EvidenceError, 'either bundled or separate'):
                    field.verify_venue(path)
                path.write_text(json.dumps(packed), encoding='utf-8')
                external.unlink()
                self.assertEqual(expected, field.verify_venue(path))

                generated = root / 'prepared.json'
                command = [sys.executable, str(SCRIPT.with_name('prepare-venue-field-manifest.py')), '--venue-bundle', str(bundle),
                           '--launcher-report', str(terminal), '--topology', 'same-host', '--server-ip', manifest['serverIps'][0],
                           '--server-work-root', str(moved)]
                result = subprocess.run([*command, '--output', str(generated)], capture_output=True)
                self.assertEqual(0, result.returncode, result.stderr.decode())
                prepared = json.loads(generated.read_bytes())
                self.assertNotIn('venueDebriefReceipts', prepared)
                generated.write_text(json.dumps(dict(prepared, windowsPlayers=packed['windowsPlayers'])), encoding='utf-8')
                self.assertEqual(expected, field.verify_venue(generated))

                rejected = root / 'rejected.json'
                altered = deepcopy(export)
                altered['sessions'][0]['players'][0]['acknowledged'] = False
                for raw, message in ((json.dumps(altered).encode(), 'missing or unconfirmed'),
                                     (json.dumps(dict(export, requestId=id_for(1111))).encode(), 'another End batch'),
                                     (b' ' * (field.MAX_DEBRIEF_BYTES + 1), 'receipt export is too large')):
                    write_bundle(raw)
                    with self.assertRaisesRegex(field.EvidenceError, message):
                        field.verify_venue(path)
                    result = subprocess.run([*command, '--output', str(rejected)], capture_output=True)
                    self.assertEqual(1, result.returncode)
                    self.assertIn(message.encode(), result.stderr)
                    self.assertFalse(rejected.exists())

    def test_venue_receipt_export_matches_original_logs_and_rejects_mismatches(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest_path, manifest, batch = venue_fixture(root, mode)
                receipt_path = root / 'receipts.json'
                manifest['venueDebriefReceipts'] = receipt_path.name
                manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
                rows = []
                for entry in manifest['sessions']:
                    session, _, _ = field.management_zip(root / entry['evidenceZip'])
                    launcher = field.read_json(field.content(root / entry['launcherReport']))
                    rows.append({'sessionId': session['id'], 'streamId': launcher['streamId'],
                                 'throughSequence': session['sequence'], 'finalStreamSequence': 0, 'worldSequence': 80,
                                 'players': [{'playerId': player['id'], 'admissionId': player['admissionId'],
                                              'roomId': player['roomId'], 'acknowledged': True} for player in session['players']]})
                export = {'version': 1, 'requestId': batch['requestId'], 'sessions': rows[::-1]}
                receipt_path.write_text(json.dumps(export), encoding='utf-8')
                summary = field.verify_venue(manifest_path)
                self.assertEqual(summary['venueDebriefReceipts'], {'sessions': len(rows), 'acknowledgedPlayers': 25,
                                 'sha256': hashlib.sha256(receipt_path.read_bytes()).hexdigest()})
                self.assertFalse(summary['physicalHostsVerified'])
                self.assertFalse(summary['networkCapacityAccepted'])
                for field_name, wrong, message in (
                    ('sessionId', id_for(1111), 'boundaries differ'),
                    ('streamId', id_for(1111), 'boundaries differ'),
                    ('throughSequence', 10, 'boundaries differ'),
                    ('finalStreamSequence', 1, 'boundaries differ'),
                    ('worldSequence', 81, 'boundaries differ'),
                    ('players', [], 'cover every acknowledged original player'),
                ):
                    with self.subTest(field=field_name):
                        modified = deepcopy(export)
                        modified['sessions'][0][field_name] = wrong
                        receipt_path.write_text(json.dumps(modified), encoding='utf-8')
                        with self.assertRaisesRegex(field.EvidenceError, message):
                            field.verify_venue(manifest_path)
                for field_name, wrong, message in (
                    ('admissionId', id_for(1111), 'differ from the original admissions'),
                    ('roomId', 3, 'differ from the original admissions'),
                    ('acknowledged', False, 'missing or unconfirmed'),
                    ('acknowledged', 1, 'missing or unconfirmed'),
                ):
                    modified = deepcopy(export)
                    modified['sessions'][0]['players'][0][field_name] = wrong
                    receipt_path.write_text(json.dumps(modified), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, message):
                        field.verify_venue(manifest_path)
                receipt_path.write_text(json.dumps(dict(export, requestId=id_for(1111))), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'identify another End batch'):
                    field.verify_venue(manifest_path)

    def reconnect_window_fixture(self, root, mode, defect=None):
        path, manifest, _ = venue_fixture(root, mode, with_journals=True)
        manifest['verifyReconnectHistory'] = True
        manifest['reconnectWindow'] = {'roomId': 5, 'seat': 2, 'firstUnavailableSequence': 20, 'recoveredSequence': 31}
        for entry in manifest['sessions']:
            session, _, endpoint = field.management_zip(root / entry['evidenceZip'])
            members = [{'id': row['id'], 'roomId': row['roomId'], 'health': 100, 'connected': True, 'rig': {'kind': 'Simulated'}}
                       for row in session['players']]
            target = next((row for row in session['players'] if row['roomId'] == 5 and row['seat'] == 1), None)
            for row, log in zip(session['players'], entry['players'], strict=True):
                log_path = root / log['log']
                original = log_path.read_text(encoding='utf-8')
                startup = f"VR_NETWORK_STARTED role=Client started=True background=True port={endpoint['port']}\n"
                if row is target and defect != 'no history':
                    original = 'VR_CLIENT_CONNECTED id=99\nVR_CLIENT_DISCONNECTED\n' + original
                    server_path = root / entry['serverLog']
                    first, rest = server_path.read_text(encoding='utf-8').split('\n', 1)
                    server_path.write_text(first + '\nVR_SERVER_ADMISSION_APPROVED id=99\n'
                                           f"VR_SERVER_PEER id=99 endpoint={log['address']}:5123\n"
                                           'VR_SERVER_CLIENT_LEFT id=99\n' + rest, encoding='utf-8')
                log_path.write_text(startup + original, encoding='utf-8')

            def edit(packet):
                number = packet['sequence']
                frame = packet['frame']
                if target and 20 <= number < (32 if defect == 'no recovery' else 31):
                    lost = next(row for row in frame['players'] if row['id'] == target['id'])
                    lost.update(connected=False, rig={'kind': 'None'})
                if number == 25 and 1 in session['roomIds'] and defect == 'peer drop':
                    frame['players'][0].update(connected=False, rig={'kind': 'None'})
                if target and number == 25 and defect == 'paused':
                    frame['phase'] = 'Paused'
                if target and number >= 25 and defect == 'capture gap':
                    packet['elapsedMilliseconds'] += 700
                if target and 20 <= number <= 31 and defect == 'stalled clock':
                    packet['elapsedMilliseconds'] = 2000

            launch = root / entry['launcherReport']
            launcher = json.loads(launch.read_bytes())
            capture = '2026-11-09T00:00:03+00:00' if defect == 'late other room' and not target else '2026-11-09T00:00:00+00:00'
            world_journal(root / entry['worldJournal'], launcher['finalWorld'], capture_start=capture,
                          players=lambda _, phase: deepcopy(members) if phase == 'Running' else [], edit_packet=edit)
            launch.write_text(json.dumps(launcher), encoding='utf-8')
        path.write_text(json.dumps(manifest), encoding='utf-8')
        return path, manifest

    def test_venue_reconnect_window_matches_original_pose_and_all_other_rooms(self):
        for mode in ('Linked', 'Independent'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                path, _ = self.reconnect_window_fixture(Path(directory), mode)
                report = field.verify_venue(path)
                self.assertEqual({'roomId': 5, 'seat': 2, 'unaffectedSeats': 24, 'beforeSequence': 19,
                                  'firstUnavailableSequence': 20, 'recoveredSequence': 31, 'unavailableFrames': 11,
                                  'maxFrameGapMilliseconds': 500, 'observedUnavailableMilliseconds': 1100,
                                  'beforeUtc': '2026-11-09T00:00:01.900000+00:00',
                                  'firstUnavailableUtc': '2026-11-09T00:00:02+00:00', 'recoveredUtc': '2026-11-09T00:00:03.100000+00:00'},
                                 report['reconnectWindow'])
                self.assertEqual(1, report['reconnectHistory']['retiredConnections'])

    def test_venue_reconnect_window_rejects_incomplete_or_misaligned_evidence(self):
        for mode, defect, error in (
            ('Linked', 'peer drop', 'does not isolate'), ('Independent', 'peer drop', 'Other rooms do not cover'),
            ('Independent', 'late other room', 'Other rooms do not cover'), ('Linked', 'paused', 'leaves the original Running phase'),
            ('Linked', 'no recovery', 'does not isolate'), ('Linked', 'capture gap', 'capture gap or stalled tick'),
            ('Linked', 'stalled clock', 'capture clock does not advance'),
            ('Linked', 'no history', 'has no verified retired connection'),
        ):
            with self.subTest(mode=mode, defect=defect), tempfile.TemporaryDirectory() as directory:
                path, _ = self.reconnect_window_fixture(Path(directory), mode, defect)
                with self.assertRaisesRegex(field.EvidenceError, error):
                    field.verify_venue(path)

    def test_venue_reconnect_window_requires_bounded_selection_and_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            path, manifest = self.reconnect_window_fixture(Path(directory), 'Linked')
            for changes, error in (
                ({'verifyReconnectHistory': False}, 'requires verified reconnect history'),
                ({'reconnectWindow': dict(manifest['reconnectWindow'], recoveredSequence=21)}, 'Invalid numeric evidence'),
                ({'reconnectWindow': dict(manifest['reconnectWindow'], recoveredSequence=1000)}, 'outside the original Running recording'),
                ({'reconnectWindow': dict(manifest['reconnectWindow'], playerId=id_for(1))}, 'Select one original seat'),
            ):
                with self.subTest(changes=changes):
                    path.write_text(json.dumps(dict(manifest, **changes)), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, error):
                        field.verify_venue(path)

    def concurrent_journals(self, root, manifest, offsets, edit_packet=None, *, tracked=False, capture_start=None):
        for entry, offset in zip(manifest['sessions'], offsets, strict=True):
            session, _, _ = field.management_zip(root / entry['evidenceZip'])
            members = [{'id': player['id'], 'roomId': player['roomId'], 'connected': True} for player in session['players']]
            if tracked:
                for member in members:
                    member['rig'] = {'kind': 'Tracked'}
            launch = root / entry['launcherReport']
            launcher = json.loads(launch.read_text(encoding='utf-8'))
            start = (capture_start or datetime.fromisoformat('2026-11-09T08:00:00+08:00')) + timedelta(milliseconds=offset)
            world_journal(root / entry['worldJournal'], launcher['finalWorld'], capture_start=start.isoformat(),
                          players=lambda _, phase: deepcopy(members) if phase == 'Running' else [], edit_packet=edit_packet)
            launch.write_text(json.dumps(launcher), encoding='utf-8')

    def concurrent_fire_journals(self, root, manifest, *, fire_frame=lambda _: 12, edit_packet=None, capture_start=None):
        for index, entry in enumerate(manifest['sessions']):
            archive_path = root / entry['evidenceZip']
            session, stats, endpoint = field.management_zip(archive_path)
            launch = root / entry['launcherReport']
            launcher = json.loads(launch.read_text(encoding='utf-8'))
            roster = session['players']
            shots = sorted((number, player['id']) for player in roster
                           if (number := fire_frame(player)) is not None)
            records, events = [], {}
            for ordinal, (number, player) in enumerate(shots, 1):
                shot = id_for(800 + ordinal)
                records.append((field.SHOT_FIRED, player, shot, None, 0))
                events.setdefault(number, []).append({'kind': 'ShotFired', 'eventId': id_for(900 + ordinal),
                    'shotId': shot, 'playerId': player, 'tick': number})
            players_who_fired = {player for _, player in shots}
            launcher['finalCombatStream']['acceptedSequence'] = len(shots)
            session['combatStream'] = launcher['finalCombatStream']
            stats['origin'] = launcher['finalCombatStream']['origin']
            for row, source in zip(stats['players'], entry['players'], strict=True):
                row['ammoUsed'] = int(row['playerId'] in players_who_fired)
                log = root / source['log']
                lines = log.read_text(encoding='utf-8').splitlines()
                marker, payload = lines[1].split(' ', 1)
                result = json.loads(payload)
                lines[1] = marker + ' ' + json.dumps(dict(result, ammoUsed=row['ammoUsed'], finalStreamSequence=len(shots)))
                log.write_text('\n'.join(lines) + '\n', encoding='utf-8')
            with zipfile.ZipFile(archive_path, 'w') as archive:
                for name, data in zip(('session', 'statistics', 'endpoint'), (session, stats, endpoint), strict=True):
                    archive.writestr(name + '.json', json.dumps(data))
            entry['combatJournal'] = f'Room {index + 1}.journal'
            combat_journal(root / entry['combatJournal'], launcher, records)
            players = [{'id': player['id'], 'roomId': player['roomId'], 'connected': True} for player in roster]
            start = (capture_start or datetime.fromisoformat('2026-11-09T00:00:00+00:00')) + timedelta(milliseconds=index * 150)

            def packet_at(number, phase):
                return deepcopy(players) if phase == 'Running' else []

            def with_events(packet):
                number = packet['sequence']
                packet.update(events=events.get(number, []), throughCombatSequence=sum(frame <= number for frame, _ in shots))
                if edit_packet is not None:
                    edit_packet(packet)

            world_journal(root / entry['worldJournal'], launcher['finalWorld'], capture_start=start.isoformat(),
                          players=packet_at, edit_packet=with_events)
            launch.write_text(json.dumps(launcher), encoding='utf-8')

    def test_venue_requires_a_sealed_shot_for_every_seat_in_the_common_interval(self):
        for mode in ('Linked', 'Independent'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, mode, with_journals=True)
                self.concurrent_fire_journals(root, manifest)
                manifest.update(minimumConcurrentMilliseconds=1000, requireConcurrentFire=True)
                path.write_text(json.dumps(manifest), encoding='utf-8')
                report = field.verify_venue(path)['concurrentRoster']
                self.assertEqual(report['playersWithConfirmedFire'], 25)
                self.assertEqual(report['longestMilliseconds'], 7700 if mode == 'Linked' else 7100)

    def test_venue_concurrent_fire_rejects_idle_seats_and_shots_straddling_shared_boundary(self):
        for frame in (None, 8):
            with self.subTest(frame=frame), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, 'Independent', with_journals=True)
                self.concurrent_fire_journals(root, manifest, fire_frame=lambda player:
                    frame if (player['roomId'], player['seat']) == (1, 0) else 12)
                manifest.update(minimumConcurrentMilliseconds=1000, requireConcurrentFire=True)
                path.write_text(json.dumps(manifest), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'sealed shot from every original seat'):
                    field.verify_venue(path)
                manifest['requireConcurrentFire'] = False
                path.write_text(json.dumps(manifest), encoding='utf-8')
                self.assertEqual(field.verify_venue(path)['concurrentRoster']['players'], 25)

    def test_venue_concurrent_fire_rejects_substituted_event_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Linked', with_journals=True)

            def substitute(packet):
                if packet['events']:
                    packet['events'][0]['eventId'] = id_for(980)

            self.concurrent_fire_journals(root, manifest, edit_packet=substitute)
            manifest.update(minimumConcurrentMilliseconds=1000, requireConcurrentFire=True)
            path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'original sealed combat event'):
                field.verify_venue(path)

    def test_venue_concurrent_fire_reports_the_longest_window_that_has_all_shots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Linked', with_journals=True)

            def interrupt(packet):
                if packet['sequence'] == 52:
                    packet['suspended'] = True

            self.concurrent_fire_journals(root, manifest, fire_frame=lambda _: 60, edit_packet=interrupt)
            manifest.update(minimumConcurrentMilliseconds=1000, requireConcurrentFire=True)
            path.write_text(json.dumps(manifest), encoding='utf-8')
            report = field.verify_venue(path)['concurrentRoster']
            self.assertEqual(report['longestMilliseconds'], 2600)
            self.assertEqual(report['fromUtc'], '2026-11-09T00:00:05.300000+00:00')

    def test_venue_concurrent_fire_needs_advancement_after_same_tick_packets(self):
        for final_duplicate in (12, 17):
            with self.subTest(final_duplicate=final_duplicate), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, 'Linked', with_journals=True)

                def repeat_tick(packet):
                    if 12 <= packet['sequence'] <= final_duplicate:
                        packet['frame']['tick'] = 11
                        for event in packet['events']:
                            event['tick'] = 11

                self.concurrent_fire_journals(root, manifest, edit_packet=repeat_tick)
                manifest.update(minimumConcurrentMilliseconds=1000, requireConcurrentFire=True)
                path.write_text(json.dumps(manifest), encoding='utf-8')
                if final_duplicate == 12:
                    report = field.verify_venue(path)['concurrentRoster']
                    self.assertEqual(report['playersWithConfirmedFire'], 25)
                    self.assertEqual(report['longestMilliseconds'], 7700)
                else:
                    with self.assertRaisesRegex(field.EvidenceError, 'sealed shot from every original seat'):
                        field.verify_venue(path)

    def test_venue_concurrent_fire_requires_boolean_and_both_original_journals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Linked', with_journals=True)
            for settings, message in (
                ({'requireConcurrentFire': 1}, 'must be a boolean'),
                ({'requireConcurrentFire': True}, 'requires minimumConcurrentMilliseconds'),
                ({'requireConcurrentFire': True, 'minimumConcurrentMilliseconds': 1000}, 'original combat journals'),
            ):
                path.write_text(json.dumps(manifest | settings), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, message):
                    field.verify_venue(path)

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

    def test_distinct_remote_roster_matches_all_sources_and_connection_history(self):
        for mode, offsets in (('Linked', [0]), ('Independent', [0, 100, 200, 300, 400])):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, mode, remote=True, quest_per_room=1, with_journals=True)
                self.concurrent_journals(root, manifest, offsets)
                manifest.update(requireDistinctRemoteRoster=True, minimumConcurrentMilliseconds=5000)
                sources = []
                for entry in manifest['sessions']:
                    session, _, endpoint = field.management_zip(root / entry['evidenceZip'])
                    server_log = root / entry['serverLog']
                    server = server_log.read_text(encoding='utf-8')
                    for owner, source in zip(session['players'], entry['players'], strict=True):
                        connection = owner['roomId'] * 5 + owner['seat']
                        peer = f'192.168.5.{30 + connection}'
                        server = server.replace(f"endpoint={source['address']}:{5000 + connection}",
                                                f'endpoint={peer}:{5000 + connection}')
                        source['address'] = peer
                        if 'logcatPid' not in source:
                            client = root / source['log']
                            startup = f"VR_NETWORK_STARTED role=Client started=True background=True port={endpoint['port']}\n"
                            client.write_text(startup + client.read_text(encoding='utf-8'), encoding='utf-8')
                            sources.append((source, server_log, connection))
                    server_log.write_text(server, encoding='utf-8')
                first, first_server, connection = sources[0]
                client = root / first['log']
                client_text = client.read_text(encoding='utf-8').replace(f'VR_CLIENT_CONNECTED id={connection}\n',
                    f'VR_CLIENT_CONNECTED id=100\nVR_CLIENT_DISCONNECTED\nVR_CLIENT_CONNECTED id={connection}\n')
                client.write_text(client_text, encoding='utf-8')
                server_text = first_server.read_text(encoding='utf-8').replace(f'VR_SERVER_ADMISSION_APPROVED id={connection}\n',
                    f"VR_SERVER_ADMISSION_APPROVED id=100\nVR_SERVER_PEER id=100 endpoint={first['address']}:5100\n"
                    f'VR_SERVER_CLIENT_LEFT id=100\nVR_SERVER_ADMISSION_APPROVED id={connection}\n')
                first_server.write_text(server_text, encoding='utf-8')
                path.write_text(json.dumps(manifest), encoding='utf-8')
                report = field.verify_venue(path)
                self.assertEqual(report['distinctRemoteRoster'],
                    {'seatsVerified': 25, 'distinctSourceAddresses': 25, 'connectionsVerified': 26})
                self.assertEqual([room['playersOutsideDeclaredServer'] for room in report['rooms']], [5] * 5)
                self.assertEqual(report['concurrentRoster']['players'], 25)
                self.assertFalse(report['physicalHostsVerified'])
                self.assertNotIn('192.168', json.dumps(report))

                for changed, error in (
                    (server_text.replace(f"endpoint={first['address']}:5100", 'endpoint=192.168.5.250:5100'), 'Historical UDP peer'),
                    (server_text + 'VR_SERVER_ADMISSION_APPROVED id=101\n', 'every approved connection'),
                ):
                    first_server.write_text(changed, encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, error):
                        field.verify_venue(path)
                first_server.write_text(server_text, encoding='utf-8')
                port = field.management_zip(root / manifest['sessions'][0]['evidenceZip'])[2]['port']
                client.write_text(client_text.replace(f'port={port}', 'port=9876'), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'original Windows client startup'):
                    field.verify_venue(path)
                client.write_text(client_text, encoding='utf-8')

                last, last_server, last_connection = sources[-1]
                last_text = last_server.read_text(encoding='utf-8')
                for replacement in (first['address'], manifest['serverIps'][0]):
                    with self.subTest(replacement=replacement):
                        original = last['address']
                        last['address'] = replacement
                        last_server.write_text(last_text.replace(f'endpoint={original}:{5000 + last_connection}',
                            f'endpoint={replacement}:{5000 + last_connection}'), encoding='utf-8')
                        path.write_text(json.dumps(manifest), encoding='utf-8')
                        with self.assertRaisesRegex(field.EvidenceError, 'one unique observed IPv4'):
                            field.verify_venue(path)
                        last['address'] = original
                last_server.write_text(last_text, encoding='utf-8')

    def test_distinct_remote_roster_requires_direct_lan_and_a_common_window(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Linked', with_journals=True)
            for changes, error in (
                ({'requireDistinctRemoteRoster': 1}, 'must be a boolean'),
                ({'requireDistinctRemoteRoster': True, 'minimumConcurrentMilliseconds': 5000}, 'requires direct-lan'),
                ({'requireDistinctRemoteRoster': True, 'topology': 'direct-lan'}, 'minimumConcurrentMilliseconds'),
            ):
                with self.subTest(changes=changes):
                    path.write_text(json.dumps(dict(manifest, **changes)), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, error):
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

    def add_windows_links(self, root, manifest):
        for entry in manifest['sessions']:
            for player in entry['players']:
                if 'logcatPid' in player:
                    continue
                log = root / player['log']
                raw_connection, _ = field.client_result(field.content(log))
                connection = int(raw_connection)
                metrics = log.with_suffix('.link.json')
                launcher = log.with_suffix('.launch.json')
                report = json.loads(launcher.read_bytes()) if launcher.exists() else {
                    'status': 'exited', 'processId': 8000 + connection, 'exitCode': 0}
                samples = [{'sequence': number, 'tick': number * 20, 'windowSeconds': 1.01, 'playerLoopFrames': 60,
                            'result': 'Reply' if number <= 28 else 'Timeout' if number == 29 else 'Interrupted',
                            'roundTripMilliseconds': number / 2 if number <= 28 else 0} for number in range(1, 31)]
                metrics.write_text(json.dumps({'version': 1, 'processId': report['processId'], 'connection': connection,
                    'complete': True, 'reason': 'Limit', 'batchMode': True, 'graphicsDeviceActive': False, 'samples': samples}), encoding='utf-8')
                report['linkMetrics'] = {
                    'metricsSha256': hashlib.sha256(metrics.read_bytes()).hexdigest(),
                    'logSha256': hashlib.sha256(log.read_bytes()).hexdigest()}
                launcher.write_text(json.dumps(report), encoding='utf-8')
                player.update(launcherReport=launcher.name, linkMetrics=metrics.name)

    def test_venue_link_metrics_cover_all_windows_seats_and_preserve_outcomes(self):
        for mode in ('Linked', 'Independent'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, split, _ = venue_fixture(root, mode, remote=True, quest_per_room=1)
                self.add_windows_links(root, split)
                path.write_text(json.dumps(split), encoding='utf-8')
                report = field.verify_venue(path)
                links = [row for session in report['sessions'] for row in session['windowsLinkMetrics']]
                self.assertEqual(report['windowsLinkMetricsVerified'], 20)
                self.assertEqual(report['questLogcatPlayers'], 5)
                self.assertEqual([(row['roomId'], row['seat']) for row in links],
                                 [(room, seat) for room in range(1, 6) for seat in range(1, 5)])
                self.assertTrue(all((row['attempts'], row['replies'], row['timeouts'], row['interrupted'], row['p95RoundTripMs'])
                                    == (30, 28, 1, 1, 13.5) for row in links))
                path.write_text(json.dumps(self.pack_venue(root, split)), encoding='utf-8')
                self.assertEqual(field.verify_venue(path), report)

    def test_venue_link_metrics_reject_swapped_logs_and_incomplete_seat_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, split, _ = venue_fixture(root, 'Independent')
            self.add_windows_links(root, split)
            packed = self.pack_venue(root, split)
            swapped = deepcopy(packed)
            a, b = swapped['windowsPlayers'][:2]
            a['linkMetrics'], b['linkMetrics'] = b['linkMetrics'], a['linkMetrics']
            path.write_text(json.dumps(swapped), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'original link and player log bytes'):
                field.verify_venue(path)
            missing = deepcopy(packed)
            missing['windowsPlayers'][0].pop('linkMetrics')
            missing['windowsPlayers'][0].pop('launcherReport')
            path.write_text(json.dumps(missing), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'every Windows seat'):
                field.verify_venue(path)
            path.write_text(json.dumps(packed), encoding='utf-8')
            with (root / a['log']).open('ab') as log:
                log.write(b'benign unrelated line\n')
            with self.assertRaisesRegex(field.EvidenceError, 'original link and player log bytes'):
                field.verify_venue(path)

    def test_venue_link_metrics_reject_wrong_connection_or_invalid_sample(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, split, _ = venue_fixture(root, 'Linked')
            self.add_windows_links(root, split)
            path.write_text(json.dumps(split), encoding='utf-8')
            player = split['sessions'][0]['players'][0]
            metrics_path, launcher_path = (root / player[key] for key in ('linkMetrics', 'launcherReport'))
            original = json.loads(metrics_path.read_bytes())
            launcher = json.loads(launcher_path.read_bytes())
            edits = [(dict(original, connection=9001), 'original process and final acknowledged connection'),
                     (dict(original, processId=9002), 'original process and final acknowledged connection'),
                     (dict(original, samples=original['samples'][:-1]), 'complete 30 samples'),
                     (dict(original, samples=[dict(original['samples'][0], roundTripMilliseconds=900), *original['samples'][1:]]),
                      'sample timing')]
            for modified, message in edits:
                with self.subTest(message=message):
                    raw = json.dumps(modified).encode('utf-8')
                    metrics_path.write_bytes(raw)
                    launcher['linkMetrics']['metricsSha256'] = hashlib.sha256(raw).hexdigest()
                    launcher_path.write_text(json.dumps(launcher), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, message):
                        field.verify_venue(path)

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

    def quest_deployment_evidence(self, root, manifest, quest_per_room):
        digest = '2a' * 32
        release = {'verified': True, 'scope': 'offline-package-consistency', 'quest': {'applicationId': 'com.vrcommand.quest',
            'architecture': 'arm64-v8a', 'signatureV2': True, 'versionCode': 64, 'sha256': digest}}
        (root / 'release.json').write_text(json.dumps(release), encoding='utf-8')
        rows = []
        for entry in manifest['sessions']:
            session, _, endpoint = field.management_zip(root / entry['evidenceZip'])
            rows.extend({'roomId': player['roomId'], 'seat': player['seat'] + 1, 'status': 'launch-requested',
                         'apkVerified': True, 'filesVerified': True, 'versionCode': 64, 'port': endpoint['port'],
                         'sessionId': session['id'], 'playerId': player['id'], 'admissionId': player['admissionId']}
                        for player in session['players'] if player['seat'] >= 5 - quest_per_room)
        report = {'phase': 'deployment', 'managementVerified': True, 'apkVerificationVersion': 1, 'topology': manifest['mode'],
                  'complete': True, 'expectedApkSha256': digest, 'expectedVersionCode': 64, 'devices': rows}
        manifest['questDeployments'] = {'releaseReport': 'release.json', 'reports': ['deployment.json']}
        return report

    def add_shared_release(self, root, manifest, quest_per_room):
        if quest_per_room:
            deployment = self.quest_deployment_evidence(root, manifest, quest_per_room)
            (root / 'deployment.json').write_text(json.dumps(deployment), encoding='utf-8')
            manifest['questDeployments'].pop('releaseReport')
        path = root / 'release.json'
        release = json.loads(path.read_bytes()) if path.exists() else {'verified': True, 'scope': 'offline-package-consistency'}
        release['windows'] = {'playerManifestSha256': 'bc' * 32}
        path.write_text(json.dumps(release), encoding='utf-8-sig')
        manifest['venueReleaseReport'] = path.name
        for entry in manifest['sessions']:
            for seat in entry['players']:
                if 'logcatPid' in seat:
                    continue
                log = root / seat['log']
                connection, _ = field.client_result(field.content(log))
                launch = log.with_suffix('.launch.json')
                value = {'status': 'exited', 'exitCode': 0, 'processId': 9000 + int(connection),
                         'playerManifestSha256': 'bc' * 32, 'playerLogSha256': hashlib.sha256(log.read_bytes()).hexdigest()}
                launch.write_text(json.dumps(value), encoding='utf-8')
                seat['launcherReport'] = launch.name
        return path

    def windows_inbox_fixture(self, root, manifest):
        packed = self.pack_venue(root, manifest)
        inbox = root / 'returned'
        inbox.mkdir()
        for index, player in enumerate(packed.pop('windowsPlayers')):
            with zipfile.ZipFile(inbox / f'box-{index:02}.ZIP', 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.write(root / player['log'], 'player.log')
                archive.write(root / player['launcherReport'], 'launch-report.json')
                if 'linkMetrics' in player:
                    archive.write(root / player['linkMetrics'], 'link-metrics.json')
        packed['windowsEvidenceDirectory'] = inbox.name
        return packed

    def test_windows_inbox_verifies_embedded_metrics_against_the_original_connection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Independent', room_sizes=(1,) * 5)
            manifest['expectedPlayersPerRoom'] = 1
            self.add_shared_release(root, manifest, 0)
            self.add_windows_links(root, manifest)
            path.write_text(json.dumps(manifest), encoding='utf-8')
            original = field.verify_venue(path)
            inbox = self.windows_inbox_fixture(root, manifest)
            path.write_text(json.dumps(inbox), encoding='utf-8')
            self.assertEqual(original, field.verify_venue(path))
            inspected, _ = field.verify_venue_batch(path, inspect_windows=True)
            self.assertTrue(inspected['complete'])
            self.assertEqual(inspected['windowsLinkMetrics']['verifiedSeats'], 5)
            self.assertEqual(inspected['windowsLinkMetrics']['missingSeats'], [])
            self.assertEqual(inspected['windowsLinkMetrics']['seats'][0]['p95RoundTripMs'], 13.5)
            self.assertEqual(5, original['windowsLinkMetricsVerified'])

            archives = sorted((root / inbox['windowsEvidenceDirectory']).glob('*.ZIP'))
            archive_path, another, *_ = archives
            with zipfile.ZipFile(archive_path) as archive:
                original_entries = {name: archive.read(name) for name in archive.namelist()}
            with zipfile.ZipFile(another) as archive:
                foreign_metrics = archive.read('link-metrics.json')
            missing = dict(original_entries)
            missing.pop('link-metrics.json')
            launch = json.loads(original_entries['launch-report.json'])
            launch.pop('linkMetrics')
            mixed = dict(missing, **{'launch-report.json': json.dumps(launch).encode()})
            for entries, reason in (
                (missing, 'lacks its recorded Windows link report'),
                (mixed, 'cover every Windows seat'),
                (dict(original_entries, **{'link-metrics.json': foreign_metrics}), 'original link and player log bytes'),
                (dict(original_entries, **{'link-metrics.json': b'x' * (field.MAX_WINDOWS_LINK_BYTES + 1)}), 'exceeds its file limit'),
            ):
                with self.subTest(reason=reason):
                    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
                        for name, data in entries.items():
                            archive.writestr(name, data)
                    inspected, _ = field.verify_venue_batch(path, inspect_windows=True)
                    self.assertFalse(inspected['complete'])
                    self.assertIn(reason, inspected['issues'][0]['reason'])
                    with self.assertRaisesRegex(field.EvidenceError, 'Windows inbox is incomplete'):
                        field.verify_venue(path)

            packed = self.pack_venue(root, manifest)
            first = packed['windowsPlayers'][0]
            metrics_path = first.pop('linkMetrics')
            first.pop('log')
            first.pop('launcherReport')
            first['evidenceZip'] = str(archive_path)
            path.write_text(json.dumps(packed), encoding='utf-8')
            with zipfile.ZipFile(archive_path, 'w') as archive:
                for name, data in original_entries.items():
                    archive.writestr(name, data)
            self.assertEqual(original, field.verify_venue(path))
            first['linkMetrics'] = metrics_path
            path.write_text(json.dumps(packed), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'either in the ZIP or as an original file'):
                field.verify_venue(path)
            with zipfile.ZipFile(archive_path, 'w') as archive:
                for name, data in missing.items():
                    archive.writestr(name, data)
            self.assertEqual(original, field.verify_venue(path))

    def test_windows_link_criteria_report_measurement_failures_by_seat(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Independent', room_sizes=(1,) * 5)
            manifest['expectedPlayersPerRoom'] = 1
            self.add_shared_release(root, manifest, 0)
            self.add_windows_links(root, manifest)
            criteria = {'minimumReplies': 28, 'maximumP95RoundTripMs': 14}
            manifest['windowsLinkCriteria'] = criteria
            path.write_text(json.dumps(manifest), encoding='utf-8')
            self.assertEqual(field.verify_venue(path)['windowsLinkCriteria'], dict(criteria, seatsVerified=5))

            for entry, delayed in zip(manifest['sessions'][:2], (False, True), strict=True):
                player, = entry['players']
                metrics_path, launch_path = (root / player[key] for key in ('linkMetrics', 'launcherReport'))
                metrics = json.loads(metrics_path.read_bytes())
                for row in metrics['samples']:
                    if delayed and row['result'] == 'Reply':
                        row['roundTripMilliseconds'] = 15
                    elif not delayed:
                        row.update(result='Timeout', roundTripMilliseconds=0)
                raw = json.dumps(metrics).encode()
                metrics_path.write_bytes(raw)
                launch = json.loads(launch_path.read_bytes())
                launch['linkMetrics']['metricsSha256'] = hashlib.sha256(raw).hexdigest()
                launch_path.write_text(json.dumps(launch), encoding='utf-8')

            inbox = self.windows_inbox_fixture(root, manifest)
            path.write_text(json.dumps(inbox), encoding='utf-8')
            result = subprocess.run([sys.executable, str(SCRIPT), '--venue-manifest', str(path), '--inspect-windows-inbox'],
                                    capture_output=True)
            self.assertEqual(result.returncode, 1)
            inspection = json.loads(result.stdout)
            self.assertTrue(inspection['complete'])
            self.assertFalse(inspection['windowsLinkMetrics']['meetsCriteria'])
            failures = [(row['roomId'], row['seat'], row['replies'], row['p95RoundTripMs'], row['criteriaFailures'])
                        for row in inspection['windowsLinkMetrics']['seats'] if 'criteriaFailures' in row]
            self.assertEqual(failures, [(1, 1, 0, None, ['minimumReplies', 'maximumP95RoundTripMs']),
                                        (2, 1, 28, 15.0, ['maximumP95RoundTripMs'])])
            for candidate in (manifest, inbox):
                path.write_text(json.dumps(candidate), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'criteria not met at room 1 seat 1, room 2 seat 1'):
                    field.verify_venue(path)

    def test_windows_link_criteria_require_measurements_even_when_all_zips_are_returned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Linked', room_sizes=(1,) * 5)
            manifest['expectedPlayersPerRoom'] = 1
            self.add_shared_release(root, manifest, 0)
            inbox = self.windows_inbox_fixture(root, manifest)
            path.write_text(json.dumps(inbox), encoding='utf-8')
            report, _ = field.verify_venue_batch(path, inspect_windows=True)
            self.assertNotIn('windowsLinkMetrics', report)
            inbox['windowsLinkCriteria'] = {'minimumReplies': 1, 'maximumP95RoundTripMs': 900}
            path.write_text(json.dumps(inbox), encoding='utf-8')
            report, _ = field.verify_venue_batch(path, inspect_windows=True)
            self.assertTrue(report['complete'])
            self.assertFalse(report['windowsLinkMetrics']['meetsCriteria'])
            self.assertEqual(report['windowsLinkMetrics']['verifiedSeats'], 0)
            self.assertEqual(len(report['windowsLinkMetrics']['missingSeats']), 5)
            with self.assertRaisesRegex(field.EvidenceError, 'original link reports for every Windows seat'):
                field.verify_venue(path)
            for invalid in (None, {}, {'minimumReplies': True, 'maximumP95RoundTripMs': 900},
                            {'minimumReplies': 1, 'maximumP95RoundTripMs': 901}):
                path.write_text(json.dumps(dict(inbox, windowsLinkCriteria=invalid)), encoding='utf-8')
                with self.assertRaises(field.EvidenceError):
                    field.verify_venue(path)

    def test_windows_inbox_receives_only_the_mapped_windows_seats_in_a_mixed_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Linked', remote=True, quest_per_room=1)
            self.add_shared_release(root, manifest, 1)
            path.write_text(json.dumps(manifest), encoding='utf-8')
            original = field.verify_venue(path)
            packed = self.windows_inbox_fixture(root, manifest)
            path.write_text(json.dumps(packed), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'Windows seat map'):
                field.verify_venue_batch(path, inspect_windows=True)

            seats = [{'roomId': room, 'seat': seat, 'station': f'PC-{room}-{seat}'}
                     for room in range(1, 6) for seat in range(1, 5)]
            seat_map = root / 'windows-seats.json'
            seat_map.write_text(json.dumps({'version': 1, 'seats': seats}), encoding='utf-8')
            packed['windowsSeatMap'] = seat_map.name
            path.write_text(json.dumps(packed), encoding='utf-8')
            inspection, _ = field.verify_venue_batch(path, inspect_windows=True)
            self.assertTrue(inspection['complete'])
            self.assertEqual(20, inspection['receivedWindowsSeats'])
            self.assertEqual(seats, [{key: row[key] for key in ('roomId', 'seat', 'station')}
                                     for row in inspection['receivedSeats']])
            self.assertNotIn('192.168.', json.dumps(inspection))
            self.assertEqual(original, field.verify_venue(path))
            path.write_text(json.dumps(dict(packed, questDeployments={'reports': ['not-yet-returned.json']})), encoding='utf-8')
            self.assertEqual(inspection, field.verify_venue_batch(path, inspect_windows=True)[0])
            path.write_text(json.dumps(packed), encoding='utf-8')
            seats[-1]['seat'] = 5
            seat_map.write_text(json.dumps({'version': 1, 'seats': seats}), encoding='utf-8')
            wrong, _ = field.verify_venue_batch(path, inspect_windows=True)
            self.assertFalse(wrong['complete'])
            self.assertEqual([seats[-1]], wrong['missingSeats'])
            self.assertIn('expected Windows seat', wrong['issues'][0]['reason'])

    def test_windows_inbox_matches_configured_station_addresses_to_final_server_peers(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, mode, remote=True, room_sizes=(1,) * 5)
                manifest['expectedPlayersPerRoom'] = 1
                self.add_shared_release(root, manifest, 0)
                inbox = self.windows_inbox_fixture(root, manifest)
                seats = [{'roomId': room, 'seat': 1, 'station': f'PC-{room}'} for room in range(1, 6)]
                originals = [player['address'] for entry in manifest['sessions'] for player in entry['players']]
                rows = [{'station': seat['station'].lower(), 'address': address} for seat, address in zip(seats, originals, strict=True)]
                seat_path, addresses_path = root / 'seats.json', root / 'addresses.json'
                seat_path.write_text(json.dumps({'version': 1, 'seats': seats}), encoding='utf-8')
                inbox.update(windowsSeatMap=seat_path.name, windowsStationAddresses=addresses_path.name)
                path.write_text(json.dumps(inbox), encoding='utf-8')

                def write_addresses(stations):
                    addresses_path.write_text(json.dumps({'version': 1, 'stations': stations}), encoding='utf-8')

                write_addresses(rows[::-1])
                inspection, _ = field.verify_venue_batch(path, inspect_windows=True)
                expected = {'expectedSeats': 5, 'verifiedSeats': 5, 'sha256': hashlib.sha256(addresses_path.read_bytes()).hexdigest()}
                self.assertTrue(inspection['complete'])
                self.assertEqual(expected, inspection['windowsStationAddresses'])
                full = field.verify_venue(path)
                self.assertEqual(expected, full['windowsStationAddresses'])
                self.assertFalse(full['physicalHostsVerified'])
                self.assertNotIn('192.168.', json.dumps(inspection))

                swapped = deepcopy(rows)
                swapped[0]['address'], swapped[-1]['address'] = swapped[-1]['address'], swapped[0]['address']
                write_addresses(swapped)
                failed = subprocess.run([sys.executable, str(SCRIPT), '--venue-manifest', str(path), '--inspect-windows-inbox'],
                                        capture_output=True)
                self.assertEqual(1, failed.returncode)
                missing = json.loads(failed.stdout)
                self.assertEqual([seats[0], seats[-1]], missing['missingSeats'])
                self.assertEqual(3, missing['windowsStationAddresses']['verifiedSeats'])
                self.assertEqual({row['file'] for row in inspection['receivedSeats'] if row['roomId'] in (1, 5)},
                                 {issue['file'] for issue in missing['issues']})
                self.assertTrue(all('Server-observed IPv4 differs' in issue['reason'] for issue in missing['issues']))
                self.assertNotIn('192.168.', json.dumps(missing))
                with self.assertRaisesRegex(field.EvidenceError, 'Windows inbox is incomplete'):
                    field.verify_venue(path)

                write_addresses([*rows[:-1], dict(rows[-1], station='PC-1')])
                with self.assertRaisesRegex(field.EvidenceError, 'unknown or repeated station'):
                    field.verify_venue_batch(path, inspect_windows=True)
                write_addresses(rows[:-1])
                with self.assertRaisesRegex(field.EvidenceError, 'address for every mapped Windows station'):
                    field.verify_venue(path)

    def test_venue_network_plan_detects_swapped_windows_seats(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, mode, remote=True, room_sizes=(1,) * 5)
                manifest['expectedPlayersPerRoom'] = 1
                plan = {'version': 1, 'mode': mode, 'endpoints': [], 'sources': []}
                for entry in manifest['sessions']:
                    session, _, endpoint = field.management_zip(root / entry['evidenceZip'])
                    plan['endpoints'].append({'roomIds': session['roomIds'], 'address': endpoint['address'], 'port': endpoint['port']})
                    for owner, player in zip(session['players'], entry['players'], strict=True):
                        plan['sources'].append({'roomId': owner['roomId'], 'seat': 1, 'address': player['address']})
                plan_path = root / 'venue-network.json'
                plan_path.write_text(json.dumps(plan), encoding='utf-8')
                manifest['venueNetworkPlan'] = plan_path.name
                path.write_text(json.dumps(manifest), encoding='utf-8')
                original = field.verify_venue(path)
                self.assertEqual({'sha256': hashlib.sha256(plan_path.read_bytes()).hexdigest(), 'expectedSeats': 5,
                                  'verifiedSeats': 5, 'endpointsVerified': len(plan['endpoints'])}, original['venueNetworkPlan'])

                swapped = deepcopy(plan)
                first, last = swapped['sources'][0], swapped['sources'][-1]
                first['address'], last['address'] = last['address'], first['address']
                plan_path.write_text(json.dumps(swapped), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'venue network plan for room 1 seat 1'):
                    field.verify_venue(path)

                self.add_shared_release(root, manifest, 0)
                inbox = self.windows_inbox_fixture(root, manifest)
                path.write_text(json.dumps(inbox), encoding='utf-8')
                inspection, _ = field.verify_venue_batch(path, inspect_windows=True)
                self.assertEqual([{'roomId': 1, 'seat': 1}, {'roomId': 5, 'seat': 1}], inspection['missingSeats'])
                self.assertEqual(3, inspection['venueNetworkPlan']['verifiedSeats'])
                self.assertEqual(2, len(inspection['issues']))
                self.assertNotIn('192.168.', json.dumps(inspection))
                with self.assertRaisesRegex(field.EvidenceError, 'Windows inbox is incomplete'):
                    field.verify_venue(path)

                changed = deepcopy(plan)
                changed['endpoints'][0]['port'] += 100
                plan_path.write_text(json.dumps(changed), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'endpoint differs from the original sealed game binding'):
                    field.verify_venue_batch(path, inspect_windows=True)
                changed = deepcopy(plan)
                changed['sources'][0]['seat'] = 2
                plan_path.write_text(json.dumps(changed), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'seats differ from the original sealed roster'):
                    field.verify_venue(path)
                plan_path.write_text(json.dumps(plan), encoding='utf-8')
                self.assertEqual(original['venueNetworkPlan'], field.verify_venue(path)['venueNetworkPlan'])

    def test_windows_inbox_reconnect_history_marks_problem_files_before_full_verification(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, mode, room_sizes=(1,) * 5)
                manifest.update(expectedPlayersPerRoom=1, verifyReconnectHistory=True)
                old = 'VR_CLIENT_CONNECTED id=99\nVR_CLIENT_DISCONNECTED\n'
                for entry in manifest['sessions']:
                    session, _, endpoint = field.management_zip(root / entry['evidenceZip'])
                    startup = f"VR_NETWORK_STARTED role=Client started=True background=True port={endpoint['port']}\n"
                    for owner, player in zip(session['players'], entry['players'], strict=True):
                        log = root / player['log']
                        raw = log.read_text(encoding='utf-8')
                        if owner['roomId'] == 5:
                            raw = old + raw
                            target_owner = owner
                            server = root / entry['serverLog']
                            first, rest = server.read_text(encoding='utf-8').split('\n', 1)
                            server.write_text(first + '\nVR_SERVER_ADMISSION_APPROVED id=99\n'
                                              f"VR_SERVER_PEER id=99 endpoint={player['address']}:5123\n"
                                              'VR_SERVER_CLIENT_LEFT id=99\n' + rest, encoding='utf-8')
                        log.write_text(startup + raw, encoding='utf-8')
                self.add_shared_release(root, manifest, 0)
                packed = self.windows_inbox_fixture(root, manifest)
                path.write_text(json.dumps(packed), encoding='utf-8')

                def inspect():
                    return field.verify_venue_batch(path, inspect_windows=True)[0]

                received = inspect()
                self.assertTrue(received['complete'])
                history = {'observedConnections': 6, 'retiredConnections': 1,
                           'reconnectedSeats': [{'roomId': 5, 'seat': 1, 'retiredConnections': 1}]}
                self.assertEqual(history, received['reconnectHistory'])
                self.assertEqual(history, field.verify_venue(path)['reconnectHistory'])
                boxes = {row['roomId']: root / packed['windowsEvidenceDirectory'] / row['file'] for row in received['receivedSeats']}
                server_bytes = server.read_bytes()
                for bad, message in (
                    (server_bytes.replace(b'VR_SERVER_CLIENT_LEFT id=99\r\n', b'').replace(b'VR_SERVER_CLIENT_LEFT id=99\n', b''),
                     'Missing server release'),
                    (server_bytes.replace(b'192.168.5.10:5123', b'192.168.5.21:5123'), 'Historical UDP peer differs'),
                ):
                    server.write_bytes(bad)
                    failed = inspect()
                    self.assertFalse(failed['complete'])
                    self.assertEqual([{'roomId': 5, 'seat': 1}], failed['missingSeats'])
                    self.assertEqual({'observedConnections': 4, 'retiredConnections': 0, 'reconnectedSeats': []},
                                     failed['reconnectHistory'])
                    self.assertEqual(boxes[5].name, failed['issues'][0]['file'])
                    self.assertIn(message, failed['issues'][0]['reason'])
                    self.assertNotIn('192.168', json.dumps(failed))
                    with self.assertRaisesRegex(field.EvidenceError, 'Windows inbox is incomplete'):
                        field.verify_venue(path)
                    path.write_text(json.dumps(dict(packed, verifyReconnectHistory=False)), encoding='utf-8')
                    self.assertTrue(inspect()['complete'])
                    path.write_text(json.dumps(packed), encoding='utf-8')
                server.write_bytes(server_bytes)

                def rewrite(box, change):
                    original = box.read_bytes()
                    with zipfile.ZipFile(box) as archive:
                        log, launch = archive.read('player.log'), json.loads(archive.read('launch-report.json'))
                    log = change(log.decode('utf-8')).encode('utf-8')
                    launch['playerLogSha256'] = hashlib.sha256(log).hexdigest()
                    with zipfile.ZipFile(box, 'w') as archive:
                        archive.writestr('player.log', log)
                        archive.writestr('launch-report.json', json.dumps(launch))
                    return original

                changed = rewrite(boxes[5], lambda log: log.replace(target_owner['admissionId'], id_for(999)))
                failure = inspect()
                self.assertEqual([{'roomId': 5, 'seat': 1}], failure['missingSeats'])
                self.assertIn('admission', failure['issues'][0]['reason'])
                boxes[5].write_bytes(changed)
                if mode == 'Linked':
                    changed = rewrite(boxes[1], lambda log: log.replace('VR_CLIENT_CONNECTED', old + 'VR_CLIENT_CONNECTED', 1))
                    failure = inspect()
                    self.assertEqual([{'roomId': 1, 'seat': 1}, {'roomId': 5, 'seat': 1}], failure['missingSeats'])
                    self.assertEqual({boxes[1].name, boxes[5].name}, {row['file'] for row in failure['issues']})
                    self.assertTrue(all('reused across player logs' in row['reason'] for row in failure['issues']))
                    boxes[1].write_bytes(changed)
                self.assertEqual(received, inspect())

    @unittest.skipUnless(HAS_POWERSHELL, 'UDP evidence requires PowerShell')
    def test_venue_reconnect_source_plan_keeps_original_opening_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, closure = venue_fixture(root, 'Linked', remote=True, room_sizes=(1,) * 5)
            entry, = manifest['sessions']
            session, _, endpoint = field.management_zip(root / entry['evidenceZip'])
            launcher_path = root / entry['launcherReport']
            launcher = json.loads(launcher_path.read_bytes())
            launcher['udpBinding']['observedAtUtc'] = '2026-11-08T23:59:59Z'
            launcher_path.write_text(json.dumps(launcher), encoding='utf-8')
            server = root / entry['serverLog']
            first, rest = server.read_text(encoding='utf-8').split('\n', 1)
            initial, final = '192.168.5.21', '192.168.5.20'
            server.write_text(first + f'\nVR_SERVER_ADMISSION_APPROVED id=99\nVR_SERVER_PEER id=99 endpoint={initial}:5010\n'
                              'VR_SERVER_CLIENT_LEFT id=99\n' + rest, encoding='utf-8')
            startup = f"VR_NETWORK_STARTED role=Client started=True background=True port={endpoint['port']}\n"
            seats = []
            for owner, player in zip(session['players'], entry['players'], strict=True):
                room = owner['roomId']
                file = root / player['log']
                extra = 'VR_CLIENT_CONNECTED id=99\nVR_CLIENT_DISCONNECTED\n' if room == 5 else ''
                file.write_text(startup + extra + file.read_text(encoding='utf-8'), encoding='utf-8')
                seats.append({'roomId': room, 'seat': 1, 'address': initial if room == 5 else player['address']})
            network = {'version': 1, 'mode': 'Linked', 'sources': seats, 'endpoints': [
                {'roomIds': session['roomIds'], 'address': endpoint['address'], 'port': endpoint['port']}]}
            (root / 'network.json').write_text(json.dumps(network), encoding='utf-8')
            (root / 'reconnect.json').write_text(json.dumps({'version': 1, 'closureRequestId': closure['requestId'],
                'seats': [{'roomId': 5, 'seat': 1, 'addresses': [initial, final]}]}), encoding='utf-8')
            manifest.update(expectedPlayersPerRoom=1, verifyReconnectHistory=True, venueNetworkPlan='network.json',
                            reconnectSourcePlan='reconnect.json')
            opening = [preflight_fixture(root, f'source-{i}', server=endpoint['address'], peer=address, port=endpoint['port'])
                       for i, address in enumerate((endpoint['address'], initial))]
            entry['udpSourcePreflights'] = [dict(listener=listener.name, probe=probe.name) for listener, probe in opening]
            path.write_text(json.dumps(manifest), encoding='utf-8')
            report = field.verify_venue(path)
            self.assertEqual(2, report['udpSourcePreflightsVerified'])
            self.assertEqual(1, report['reconnectSourcePlan']['verifiedSeats'])
            listener, probe = preflight_fixture(root, 'final-source', server=endpoint['address'], peer=final, port=endpoint['port'])
            entry['udpSourcePreflights'][-1] = dict(listener=listener.name, probe=probe.name)
            path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'peer|source'):
                field.verify_venue(path)

    def test_venue_reconnect_source_plan_checks_order_in_inbox_and_full_verification(self):
        for mode in ('Linked', 'Independent'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, closure = venue_fixture(root, mode, remote=True, room_sizes=(1,) * 5)
                manifest.update(expectedPlayersPerRoom=1, verifyReconnectHistory=True, venueNetworkPlan='network.json',
                                reconnectSourcePlan='reconnect.json')
                network = {'version': 1, 'mode': mode, 'sources': [], 'endpoints': []}
                initial, final = '192.168.5.21', '192.168.5.20'
                for entry in manifest['sessions']:
                    session, _, endpoint = field.management_zip(root / entry['evidenceZip'])
                    network['endpoints'].append({'roomIds': session['roomIds'], 'address': endpoint['address'], 'port': endpoint['port']})
                    for player, original in zip(session['players'], entry['players'], strict=True):
                        room = player['roomId']
                        network['sources'].append({'roomId': room, 'seat': 1, 'address': initial if room == 5 else original['address']})
                        log = root / original['log']
                        extra = ''
                        if room == 5:
                            extra = 'VR_CLIENT_CONNECTED id=99\nVR_CLIENT_DISCONNECTED\n'
                            server = root / entry['serverLog']
                            startup, rest = server.read_text(encoding='utf-8').split('\n', 1)
                            server.write_text(startup + '\nVR_SERVER_ADMISSION_APPROVED id=99\n'
                                              f'VR_SERVER_PEER id=99 endpoint={initial}:5111\nVR_SERVER_CLIENT_LEFT id=99\n'
                                              + rest, encoding='utf-8')
                        log.write_text(f"VR_NETWORK_STARTED role=Client started=True background=True port={endpoint['port']}\n"
                                       + extra + log.read_text(encoding='utf-8'), encoding='utf-8')
                plan = {'version': 1, 'closureRequestId': closure['requestId'],
                        'seats': [{'roomId': 5, 'seat': 1, 'addresses': [initial, final]}]}
                (root / 'network.json').write_text(json.dumps(network), encoding='utf-8')
                source = root / 'reconnect.json'
                source.write_text(json.dumps(plan), encoding='utf-8')
                self.add_shared_release(root, manifest, 0)
                packed = self.windows_inbox_fixture(root, manifest)
                path.write_text(json.dumps(packed), encoding='utf-8')
                expected = {'sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'plannedSeats': 1,
                            'verifiedSeats': 1, 'connectionsVerified': 2}
                inbox, _ = field.verify_venue_batch(path, inspect_windows=True)
                self.assertTrue(inbox['complete'])
                self.assertEqual(expected, inbox['reconnectSourcePlan'])
                self.assertEqual(expected, field.verify_venue(path)['reconnectSourcePlan'])
                path.write_text(json.dumps(manifest), encoding='utf-8')
                self.assertEqual(expected, field.verify_venue(path)['reconnectSourcePlan'])
                target = next(row for row in inbox['receivedSeats'] if row['roomId'] == 5)
                path.write_text(json.dumps(packed), encoding='utf-8')

                for addresses, reason in (([initial, '192.168.5.22', final], 'Connection count differs'),
                                          ([initial, '192.168.5.22'], 'Final UDP peer differs')):
                    altered = deepcopy(plan)
                    altered['seats'][0]['addresses'] = addresses
                    source.write_text(json.dumps(altered), encoding='utf-8')
                    rejected, _ = field.verify_venue_batch(path, inspect_windows=True)
                    self.assertEqual([{'roomId': 5, 'seat': 1}], rejected['missingSeats'])
                    self.assertEqual(target['file'], rejected['issues'][0]['file'])
                    self.assertIn(reason, rejected['issues'][0]['reason'])
                    self.assertEqual(0, rejected['reconnectSourcePlan']['verifiedSeats'])
                    self.assertNotIn('192.168.', json.dumps(rejected))

                for altered, reason in ((dict(plan, closureRequestId=id_for(997)), 'original End batch'),
                                        (dict(plan, seats=[dict(plan['seats'][0], addresses=[final, initial])]), 'original seat IPv4'),
                                        (dict(plan, seats=[dict(plan['seats'][0], addresses=[initial, '192.168.5.10'])]), 'network topology')):
                    source.write_text(json.dumps(altered), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, reason):
                        field.verify_venue(path)

    def test_windows_inbox_reports_missing_acknowledgement_without_weakening_final_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Linked', room_sizes=(1,) * 5)
            manifest['expectedPlayersPerRoom'] = 1
            self.add_shared_release(root, manifest, 0)
            packed = self.windows_inbox_fixture(root, manifest)
            path.write_text(json.dumps(packed), encoding='utf-8')
            server = root / packed['sessions'][0]['serverLog']
            server.write_text(server.read_text(encoding='utf-8').replace('DEBRIEF_ACK id=5', 'DEBRIEF_TIMEOUT id=5'), encoding='utf-8')
            result = subprocess.run([sys.executable, str(SCRIPT), '--venue-manifest', str(path), '--inspect-windows-inbox'], capture_output=True)
            self.assertEqual(1, result.returncode)
            report = json.loads(result.stdout)
            self.assertEqual([{'roomId': 1, 'seat': 1}], report['missingSeats'])
            self.assertEqual(4, report['receivedWindowsSeats'])
            self.assertIn('lacks an original server acknowledgement', report['issues'][0]['reason'])
            with self.assertRaisesRegex(field.EvidenceError, 'Windows inbox is incomplete'):
                field.verify_venue(path)

    def test_windows_inbox_rejects_result_mismatches_before_full_verification(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, mode, room_sizes=(1,) * 5)
                manifest['expectedPlayersPerRoom'] = 1
                self.add_shared_release(root, manifest, 0)
                inbox = self.windows_inbox_fixture(root, manifest)
                path.write_text(json.dumps(inbox), encoding='utf-8')
                original, _ = field.verify_venue_batch(path, inspect_windows=True)
                self.assertTrue(original['complete'])
                target = original['receivedSeats'][0]
                archive_path = root / inbox['windowsEvidenceDirectory'] / target['file']
                archive_bytes = archive_path.read_bytes()
                with zipfile.ZipFile(archive_path) as archive:
                    player_log = archive.read('player.log').decode('utf-8')
                    launch = json.loads(archive.read('launch-report.json'))

                for name, value in [('health', 80), ('throughSequence', 8), ('worldSequence', 79), ('finalStreamSequence', 1)]:
                    with self.subTest(field=name):
                        old = json.loads(next(line.split('VR_CLIENT_DEBRIEF_FINAL ', 1)[1] for line in player_log.splitlines()
                                              if line.startswith('VR_CLIENT_DEBRIEF_FINAL ')))
                        altered = player_log.replace(json.dumps(old), json.dumps({**old, name: value})).encode()
                        self.assertNotEqual(player_log.encode(), altered)
                        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
                            archive.writestr('player.log', altered)
                            archive.writestr('launch-report.json', json.dumps({**launch, 'playerLogSha256': hashlib.sha256(altered).hexdigest()}))
                        result = subprocess.run([sys.executable, str(SCRIPT), '--venue-manifest', str(path), '--inspect-windows-inbox'],
                                                capture_output=True)
                        self.assertEqual(1, result.returncode)
                        inspection = json.loads(result.stdout)
                        self.assertFalse(inspection['complete'])
                        self.assertEqual(4, inspection['receivedWindowsSeats'])
                        self.assertEqual([{'roomId': target['roomId'], 'seat': target['seat']}], inspection['missingSeats'])
                        self.assertEqual(target['file'], inspection['issues'][0]['file'])
                        self.assertIn('differs from the final seals or statistics', inspection['issues'][0]['reason'])
                        with self.assertRaisesRegex(field.EvidenceError, 'Windows inbox is incomplete'):
                            field.verify_venue(path)
                archive_path.write_bytes(archive_bytes)
                self.assertEqual(original, field.verify_venue_batch(path, inspect_windows=True)[0])

    def terminal_venue_fixture(self, root, manifest, closure):
        mode, launch_id = manifest['mode'], id_for(950)
        report_path = root / 'venue-launcher.json'
        report = {'schemaVersion': 1, 'status': 'venue-sealed-stopped', 'complete': True, 'topology': mode,
                  'instanceId': id_for(951), 'readyPublished': True, 'venueLaunchId': launch_id,
                  'sourceAttachment': 'confirmed', 'endpointPublication': 'confirmed', 'servers': []}
        moved = root / 'copied server workspace'
        for index, (entry, closed) in enumerate(zip(manifest['sessions'], closure['sessions'], strict=True)):
            launcher = json.loads((root / entry.pop('launcherReport')).read_bytes())
            launcher['childPid'] = launcher['udpBinding']['processId'] = 4300 + index
            launcher['finalCombatStream'].update(venueLaunchId=launch_id, expectedSequence=5)
            launcher['workDirectory'] = str(root / 'unavailable original workspace')
            launcher['peerDiagnosticsEnabled'] = True
            report['servers'].append({'roomIds': closed['roomIds'], 'result': launcher})
            entry['sessionId'] = closed['sessionId']
            work = moved / ('linked' if mode == 'Linked' else f'room-{index + 1:02}')
            telemetry = work / 'telemetry'
            telemetry.mkdir(parents=True)
            shutil.copyfile(root / entry['serverLog'], work / 'server.log')
            shutil.copyfile(root / entry['worldJournal'], telemetry / f"{entry['sessionId']}.worldlog")
            combat_path = telemetry / f"{entry['sessionId']}.journal"
            combat_journal(combat_path, launcher)
            entry['combatJournal'] = combat_path.relative_to(root).as_posix()
            archive = root / entry['evidenceZip']
            session, statistics, endpoint = field.management_zip(archive)
            session['combatStream'] = launcher['finalCombatStream']
            with zipfile.ZipFile(archive, 'w') as bundle:
                for name, value in [('session.json', session), ('statistics.json', statistics), ('endpoint.json', endpoint)]:
                    bundle.writestr(name, json.dumps(value))
        manifest['venueLauncherReport'] = report_path.name
        report['servers'].reverse()
        report_path.write_text(json.dumps(report), encoding='utf-8')
        return report_path, report, moved

    def test_venue_accepts_one_original_batch_launcher_report(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, closure = venue_fixture(root, mode, with_journals=True)
                report_path, report, moved = self.terminal_venue_fixture(root, manifest, closure)
                path.write_text(json.dumps(manifest), encoding='utf-8')
                split = field.verify_venue(path)
                self.assertEqual(25, split['serverAcknowledgements'])
                self.assertEqual({'launchId': report['venueLaunchId'], 'sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(),
                                  'sessions': len(closure['sessions'])}, split['venueLauncherReport'])
                packed = self.pack_venue(root, manifest)
                path.write_text(json.dumps(packed), encoding='utf-8')
                self.assertEqual(split, field.verify_venue(path))
                generated = root / 'prepared.json'
                command = [sys.executable, str(SCRIPT.with_name('prepare-venue-field-manifest.py')),
                           '--venue-bundle', str(root / packed['venueBundle']), '--launcher-report', str(report_path),
                           '--topology', 'same-host', '--server-ip', manifest['serverIps'][0]]
                missing = subprocess.run([*command, '--output', str(generated)], capture_output=True)
                self.assertEqual(1, missing.returncode)
                self.assertFalse(generated.exists())
                prepared = subprocess.run([*command, '--server-work-root', str(moved), '--output', str(generated)], capture_output=True)
                self.assertEqual(0, prepared.returncode, prepared.stderr.decode())
                original_generated = generated.read_bytes()
                ready = json.loads(original_generated)
                self.assertEqual([row['sessionId'] for row in closure['sessions']], [row['sessionId'] for row in ready['sessions']])
                self.assertTrue(all(not Path(row['serverLog']).is_absolute() for row in ready['sessions']))
                strict = root / 'prepared-reconnect.json'
                prepared = subprocess.run([*command, '--server-work-root', str(moved), '--verify-reconnect-history',
                                           '--output', str(strict)], capture_output=True)
                self.assertEqual(0, prepared.returncode, prepared.stderr.decode())
                self.assertIs(json.loads(strict.read_bytes()).pop('verifyReconnectHistory'), True)
                ready['windowsPlayers'] = packed['windowsPlayers']
                path.write_text(json.dumps(ready), encoding='utf-8')
                self.assertEqual(split, field.verify_venue(path))
                refused = subprocess.run([*command, '--server-work-root', str(moved), '--output', str(generated)], capture_output=True)
                self.assertEqual(1, refused.returncode)
                self.assertEqual(original_generated, generated.read_bytes())
                path.write_text(json.dumps(packed), encoding='utf-8')

                for field_name, value, message in (
                    ('readyPublished', False, 'terminal Windows venue launch report'),
                    ('venueLaunchId', id_for(952), 'management source belongs to a different venue launch'),
                    ('servers', report['servers'][:-1], 'every original venue session'),
                ):
                    with self.subTest(altered=field_name):
                        report_path.write_text(json.dumps({**report, field_name: value}), encoding='utf-8')
                        with self.assertRaisesRegex(field.EvidenceError, message):
                            field.verify_venue(path)
                invalid = deepcopy(report)
                invalid['servers'][0]['roomIds'] = [2] if mode == 'Linked' else [1]
                report_path.write_text(json.dumps(invalid), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'original closure room or stream'):
                    field.verify_venue(path)
                report_path.write_text(json.dumps(report), encoding='utf-8')
                packed['sessions'][0]['launcherReport'] = 'individual.json'
                path.write_text(json.dumps(packed), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'sessionId instead of a per-session launcher report'):
                    field.verify_venue(path)

    def test_quest_readiness_matches_original_preparing_frames(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, closure = venue_fixture(root, mode, remote=True, quest_per_room=5, with_journals=True,
                                                        game_server=True)
                devices = []
                for entry in manifest['sessions']:
                    session, _, endpoint = field.management_zip(root / entry['evidenceZip'])
                    started = datetime.fromisoformat(session['startedAtUtc'])
                    captured = started - timedelta(seconds=1)
                    capture_start = captured - timedelta(milliseconds=100)
                    launcher_path = root / entry['launcherReport']
                    launcher = json.loads(launcher_path.read_bytes())
                    bodies = [{'id': owner['id'], 'roomId': owner['roomId'], 'connected': True, 'health': 100,
                               'rig': {'kind': 'Tracked'}} for owner in session['players']]
                    journal_path = root / entry['worldJournal']
                    world_journal(journal_path, launcher['finalWorld'], capture_start=capture_start.isoformat(),
                                  players=lambda _, __: bodies)
                    launcher_path.write_text(json.dumps(launcher), encoding='utf-8')
                    devices.extend({'roomId': owner['roomId'], 'seat': owner['seat'] + 1, 'sessionId': session['id'],
                                    'playerId': owner['id'], 'admissionId': owner['admissionId'], 'port': endpoint['port'],
                                    'status': 'launch-requested', 'versionCode': 61, 'apkVerified': True, 'filesVerified': True}
                                   for owner in session['players'])
                apk_digest, venue_digest = 'a' * 64, 'b' * 64
                release = {'verified': True, 'scope': 'offline-package-consistency',
                           'quest': {'applicationId': 'com.vrcommand.quest', 'architecture': 'arm64-v8a', 'signatureV2': True,
                                     'versionCode': 61, 'sha256': apk_digest}}
                (root / 'release.json').write_text(json.dumps(release), encoding='utf-8')
                manifest.update(questDeployments={'releaseReport': 'release.json', 'reports': []},
                                questReadinessReports=[])
                for index, rows in enumerate((devices[:2], devices[2:]), 1):
                    deployment = {'phase': 'deployment', 'topology': mode, 'managementVerified': True, 'complete': True,
                                  'expectedApkSha256': apk_digest, 'expectedVersionCode': 61, 'apkVerificationVersion': 1,
                                  'devices': rows, 'retry': {'version': 1, 'venueSha256': venue_digest, 'mapSha256': 'c' * 64,
                                                           'salt': f'{index:032x}', 'devices': [f'{i:064x}' for i in range(len(rows))]}}
                    deployment_path = root / f'deployment-{index}.json'
                    deployment_path.write_text(json.dumps(deployment), encoding='utf-8')
                    manifest['questDeployments']['reports'].append(deployment_path.name)
                    report = {'evidenceVersion': 1, 'phase': 'tracked-readiness', 'topology': mode, 'managementVerified': True,
                              'complete': True, 'venueSha256': venue_digest, 'sampledAtUtc': (captured + timedelta(milliseconds=50)).isoformat(),
                              'deploymentSha256': hashlib.sha256(deployment_path.read_bytes()).hexdigest(),
                              'seats': [{key: row[key] for key in ('roomId', 'seat', 'sessionId')} |
                                        {'status': 'tracked-ready', 'sourceState': 'Fresh', 'worldSequence': 1,
                                         'observedSequence': 7, 'capturedAtUtc': captured.isoformat()} for row in rows]}
                    report_path = root / f'readiness-{index}.json'
                    report_path.write_text(json.dumps(report), encoding='utf-8')
                    manifest['questReadinessReports'].append(report_path.name)
                path.write_text(json.dumps(manifest), encoding='utf-8')
                verified = field.verify_venue(path)
                self.assertEqual({'reportsVerified': 2, 'seatsVerified': 25, 'sessionsVerified': len(manifest['sessions'])},
                                 verified['questReadiness'])
                self.assertFalse(verified['physicalHostsVerified'])
                self.assertEqual(25, verified['serverAcknowledgements'])
                for session in verified['sessions']:
                    self.assertEqual([{'worldSequence': 1, 'observedSequence': 7, 'seatsVerified': 5 * len(session['roomIds'])}],
                                     session['worldJournal']['questReadinessFrames'])

                for name, changes, seats, message in (
                    ('other-deployment', {'deploymentSha256': 'd' * 64}, {}, 'exact completed deployment report'),
                    ('other-zip', {'venueSha256': 'd' * 64}, {}, 'original venue ZIP digest'),
                    ('incomplete', {'complete': False}, {}, 'completed tracked sample'),
                    ('stale', {'sampledAtUtc': (started + timedelta(seconds=2)).isoformat()}, {}, 'freshness window'),
                    ('after-begin', {'sampledAtUtc': (started + timedelta(milliseconds=10)).isoformat()}, {}, 'before the original Begin'),
                    ('other-session', {}, {'sessionId': id_for(999)}, 'original deployed session'),
                    ('running', {}, {'worldSequence': 2}, 'original Preparing frame'),
                    ('other-revision', {}, {'observedSequence': 6}, 'original Preparing frame'),
                    ('other-capture', {}, {'capturedAtUtc': (captured + timedelta(milliseconds=1)).isoformat()}, 'original Preparing frame'),
                    ('missing-frame', {}, {'worldSequence': 81}, 'missing from the original world journal'),
                ):
                    with self.subTest(name=name):
                        invalid = deepcopy(report)
                        invalid.update(changes)
                        for row in invalid['seats']:
                            row.update(seats)
                        report_path.write_text(json.dumps(invalid), encoding='utf-8')
                        with self.assertRaisesRegex(field.EvidenceError, message):
                            field.verify_venue(path)
                report_path.write_text(json.dumps(report), encoding='utf-8')
                first = root / manifest['questReadinessReports'][0]
                path.write_text(json.dumps(dict(manifest, questReadinessReports=[first.name])), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'cover every original deployed Quest seat'):
                    field.verify_venue(path)
                path.write_text(json.dumps(manifest), encoding='utf-8')
                original_journal = journal_path.read_bytes()
                bodies[0]['rig']['kind'] = 'Simulated'
                world_journal(journal_path, launcher['finalWorld'], capture_start=capture_start.isoformat(),
                              players=lambda _, __: bodies)
                with self.assertRaisesRegex(field.EvidenceError, 'lacks the original tracked player'):
                    field.verify_venue(path)
                journal_path.write_bytes(original_journal)

                terminal, _, moved = self.terminal_venue_fixture(root, manifest, closure)
                packed = self.pack_venue(root, manifest)
                prepared = root / 'prepared.json'
                command = [sys.executable, str(SCRIPT.with_name('prepare-venue-field-manifest.py')),
                           '--venue-bundle', str(root / packed['venueBundle']), '--launcher-report', str(terminal),
                           '--topology', 'direct-lan', '--server-ip', manifest['serverIps'][0], '--server-work-root', str(moved),
                           '--venue-release-report', str(root / 'release.json'), '--output', str(prepared)]
                for name in manifest['questDeployments']['reports']:
                    command += ['--quest-deployment-report', str(root / name)]
                for name in manifest['questReadinessReports']:
                    command += ['--quest-readiness-report', str(root / name)]
                result = subprocess.run(command, capture_output=True, encoding='utf-8', timeout=30)
                self.assertEqual(0, result.returncode, result.stderr)
                prepared_manifest = json.loads(prepared.read_bytes())
                self.assertEqual(manifest['questReadinessReports'], prepared_manifest['questReadinessReports'])
                players = {entry['sessionId']: entry['players'] for entry in manifest['sessions']}
                for entry in prepared_manifest['sessions']:
                    entry['players'] = players[entry['sessionId']]
                prepared.write_text(json.dumps(prepared_manifest), encoding='utf-8')
                self.assertEqual(verified['questReadiness'], field.verify_venue(prepared)['questReadiness'])

    def test_prepare_mixed_venue_keeps_original_quest_and_windows_evidence(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest = quest_capture_venue_fixture(root, mode, quest_per_room=1, batches=1, with_journals=True)
                closure = json.loads((root / manifest['closure']).read_bytes())['batch']
                terminal, _, moved = self.terminal_venue_fixture(root, manifest, closure)
                release = self.add_shared_release(root, manifest, 1)
                capture = manifest['questCaptures']
                capture.update(observed_quest_capture_spec(root, capture))
                capture_path = root / capture['reports'][0]
                map_path, network_path = (root / capture[key] for key in ('deviceMap', 'networkPlan'))
                whole = json.loads(network_path.read_bytes())
                for entry in manifest['sessions']:
                    session, _, _ = field.management_zip(root / entry['evidenceZip'])
                    owners = {owner['id']: owner for owner in session['players']}
                    for player in entry['players']:
                        _, result = field.client_result((root / player['log']).read_text(encoding='utf-8'))
                        owner = owners[result['playerId']]
                        whole['sources'].append({'roomId': owner['roomId'], 'seat': owner['seat'] + 1, 'address': player['address']})
                whole_path = root / 'venue-network.json'
                whole_path.write_text(json.dumps(whole), encoding='utf-8')
                manifest['venueNetworkPlan'] = whole_path.name
                deployment_path = root / manifest['questDeployments']['reports'][0]
                deployment = json.loads(deployment_path.read_bytes())
                salt = '1' * 32
                serials = field.read_quest_device_map(map_path)
                deployment['retry'] = {'version': 1, 'venueSha256': '2' * 64, 'salt': salt,
                                       'mapSha256': field.quest_deployment_map_fingerprint(salt, serials),
                                       'devices': [f'{index:064x}' for index in range(1, 6)]}
                deployment_path.write_text(json.dumps(deployment), encoding='utf-8')
                captured = json.loads(capture_path.read_bytes())
                captured['deploymentSha256'] = hashlib.sha256(deployment_path.read_bytes()).hexdigest()
                capture_path.write_text(json.dumps(captured), encoding='utf-8')
                packed = self.windows_inbox_fixture(root, manifest)
                seats = [{'roomId': room, 'seat': seat, 'station': f'PC-{room}-{seat}'}
                         for room in range(1, 6) for seat in range(1, 5)]
                seats_path = root / 'windows-seats.json'
                seats_path.write_text(json.dumps({'version': 1, 'seats': seats}), encoding='utf-8')
                packed['windowsSeatMap'] = seats_path.name
                path.write_text(json.dumps(packed), encoding='utf-8')
                expected = field.verify_venue(path)
                self.assertEqual(5, expected['questCaptureSeatsVerified'])
                self.assertEqual(20, expected['venueRelease']['windows']['seatsVerified'])
                self.assertEqual(1, expected['questDeployment']['deviceMapsMatched'])
                self.assertEqual(25, expected['venueNetworkPlan']['verifiedSeats'])

                output = root / 'handoff' / 'venue.json'
                output.parent.mkdir()
                inbox = root / packed['windowsEvidenceDirectory']
                command = [sys.executable, str(SCRIPT.with_name('prepare-venue-field-manifest.py')),
                           '--venue-bundle', str(root / packed['venueBundle']), '--launcher-report', str(terminal),
                           '--topology', 'direct-lan', '--server-ip', manifest['serverIps'][0], '--server-work-root', str(moved),
                           '--venue-release-report', str(release), '--windows-inbox', str(inbox), '--windows-seat-map', str(seats_path),
                           '--venue-network-plan', str(whole_path),
                           '--quest-capture-report', str(capture_path), '--quest-device-map', str(map_path), '--quest-network-plan', str(network_path),
                           '--quest-deployment-report', str(deployment_path)]
                returning = next(inbox.glob('*.ZIP'))
                delayed = returning.rename(root / 'not-yet-returned.zip')
                prepared = subprocess.run([*command, '--output', str(output)], capture_output=True)
                self.assertEqual(0, prepared.returncode, prepared.stderr.decode())
                inspection, _ = field.verify_venue_batch(output, inspect_windows=True)
                self.assertEqual(19, inspection['receivedWindowsSeats'])
                self.assertEqual(19, inspection['venueNetworkPlan']['verifiedSeats'])
                delayed.rename(returning)
                self.assertEqual(expected, field.verify_venue(output))
                generated = json.loads(output.read_bytes())
                self.assertTrue(all(not Path(value).is_absolute() for value in (
                    generated['questCaptures']['deviceMap'], generated['questCaptures']['networkPlan'],
                    generated['venueNetworkPlan'],
                    *generated['questCaptures']['reports'], *generated['questDeployments']['reports'])))

                original_network = network_path.read_bytes()
                changed = json.loads(original_network)
                changed['sources'][0]['address'] = '192.168.5.210'
                network_path.write_text(json.dumps(changed), encoding='utf-8')
                rejected_path = output.with_name('wrong-source.json')
                result = subprocess.run([*command, '--output', str(rejected_path)], capture_output=True)
                self.assertEqual(1, result.returncode)
                self.assertIn(b'Quest capture IPv4 differs', result.stderr)
                self.assertFalse(rejected_path.exists())
                network_path.write_bytes(original_network)
                changed = deepcopy(whole)
                first, second = changed['sources'][:2]
                first['address'], second['address'] = second['address'], first['address']
                original_whole = whole_path.read_bytes()
                whole_path.write_text(json.dumps(changed), encoding='utf-8')
                rejected_path = output.with_name('swapped-quest-seats.json')
                result = subprocess.run([*command, '--output', str(rejected_path)], capture_output=True)
                self.assertEqual(1, result.returncode)
                self.assertIn(b'IPv4 differs from the venue network plan for room 1 seat 5', result.stderr)
                self.assertFalse(rejected_path.exists())
                whole_path.write_bytes(original_whole)
                # Keep the opening plan fixed. Only the simulated server's final peer changes.
                first = whole['sources'][0]
                first_seat = (first['roomId'], first['seat'])
                first_capture = next(row for row in captured['seats'] if (row['roomId'], row['seat']) == first_seat)
                original_log = capture_path.parent / first_capture['log']
                log_bytes = original_log.read_bytes()
                capture_bytes = capture_path.read_bytes()
                connection = field.quest_client_result(log_bytes.decode('utf-8'), first_capture['logcatPid'], first_capture['port'])[0]
                start = log_bytes.index(b'\n', log_bytes.index(b'VR_NETWORK_STARTED')) + 1
                added = (logcat_line('VR_CLIENT_CONNECTED id=99') + logcat_line('VR_CLIENT_DISCONNECTED')).encode()
                updated = log_bytes[:start] + added + log_bytes[start:]
                original_log.write_bytes(updated)
                first_capture.update(bytes=len(updated), sha256=hashlib.sha256(updated).hexdigest())
                capture_path.write_text(json.dumps(captured), encoding='utf-8')
                server = moved / ('linked' if mode == 'Linked' else 'room-01') / 'server.log'
                server_bytes = server.read_bytes()
                startup, rest = server_bytes.split(b'\n', 1)
                original_address = first['address']
                new_address = '192.168.5.220'
                marker = b'VR_SERVER_PEER id=' + connection.encode() + b' endpoint='
                assert marker + original_address.encode() in rest
                history = (f'VR_SERVER_ADMISSION_APPROVED id=99\nVR_SERVER_PEER id=99 endpoint={original_address}:5100\n'
                           'VR_SERVER_CLIENT_LEFT id=99\n').encode()
                server.write_bytes(startup + b'\n' + history + rest.replace(marker + original_address.encode(), marker + new_address.encode()))
                for log in inbox.glob('*.ZIP'):
                    # The strict history option requires the original startup line in every Windows fixture ZIP.
                    with zipfile.ZipFile(log) as archive:
                        data = {name: archive.read(name) for name in archive.namelist()}
                    owner_id = field.client_result(data['player.log'].decode())[1]['sessionId']
                    port = next(row['port'] for row in deployment['devices'] if row['sessionId'] == owner_id)
                    data['player.log'] = f'VR_NETWORK_STARTED role=Client started=True background=True port={port}\n'.encode() + data['player.log']
                    launch = json.loads(data['launch-report.json'])
                    launch['playerLogSha256'] = hashlib.sha256(data['player.log']).hexdigest()
                    data['launch-report.json'] = json.dumps(launch).encode()
                    with zipfile.ZipFile(log, 'w') as archive:
                        for name, raw in data.items():
                            archive.writestr(name, raw)
                change_plan = root / 'reconnect-sources.json'
                change_plan.write_text(json.dumps({'version': 1, 'closureRequestId': closure['requestId'], 'seats': [
                    {'roomId': first_seat[0], 'seat': first_seat[1], 'addresses': [original_address, new_address]}]}), encoding='utf-8')
                handoff = output.with_name('with-reconnect.json')
                result = subprocess.run([*command, '--verify-reconnect-history', '--reconnect-source-plan', str(change_plan),
                                         '--output', str(handoff)], capture_output=True)
                self.assertEqual(0, result.returncode, result.stderr)
                verified = field.verify_venue(handoff)
                self.assertEqual(1, verified['reconnectSourcePlan']['verifiedSeats'])
                self.assertEqual(2, verified['reconnectSourcePlan']['connectionsVerified'])
                self.assertEqual(5, verified['questCaptureSeatsVerified'])
                server.write_bytes(server_bytes)
                original_log.write_bytes(log_bytes)
                capture_path.write_bytes(capture_bytes)
                seats[0]['seat'] = 5
                seats_path.write_text(json.dumps({'version': 1, 'seats': seats}), encoding='utf-8')
                rejected_path = output.with_name('overlapping-seats.json')
                result = subprocess.run([*command, '--output', str(rejected_path)], capture_output=True)
                self.assertEqual(1, result.returncode)
                self.assertIn(b'without overlapping seats', result.stderr)
                self.assertFalse(rejected_path.exists())

    def test_windows_player_zip_matches_loose_evidence_and_rejects_changed_members(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, mode, room_sizes=(1,) * 5)
                manifest['expectedPlayersPerRoom'] = 1
                self.add_shared_release(root, manifest, 0)
                packed = self.pack_venue(root, manifest)
                path.write_text(json.dumps(packed), encoding='utf-8')
                original = field.verify_venue(path)
                zipped = deepcopy(packed)
                player = zipped['windowsPlayers'][0]
                log = (root / player.pop('log')).read_bytes()
                report = (root / player.pop('launcherReport')).read_bytes()
                player['evidenceZip'] = 'returned player.zip'
                path.write_text(json.dumps(zipped), encoding='utf-8')

                def write_zip(player_log, launcher_report, extra=False):
                    with zipfile.ZipFile(root / player['evidenceZip'], 'w', zipfile.ZIP_DEFLATED) as archive:
                        archive.writestr('player.log', player_log)
                        archive.writestr('launch-report.json', launcher_report)
                        if extra:
                            archive.writestr('unrelated.json', '{}')

                write_zip(log, report)
                self.assertEqual(original, field.verify_venue(path))
                for bad_log, bad_report, extra, message in (
                    (log + b'\nextra log bytes\n', report, False, 'original player log bytes'),
                    (log, b'x' * 4097, False, 'ZIP entry limit'),
                    (log, report, True, 'must contain the original player log and launcher report'),
                ):
                    with self.subTest(message=message):
                        write_zip(bad_log, bad_report, extra)
                        with self.assertRaisesRegex(field.EvidenceError, message):
                            field.verify_venue(path)

    def test_shared_venue_release_accepts_both_topologies_and_original_mixed_seats(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, mode, remote=True, quest_per_room=2)
                release = self.add_shared_release(root, manifest, 2)
                path.write_text(json.dumps(manifest), encoding='utf-8')
                split = field.verify_venue(path)
                self.assertEqual(split['venueRelease'], {'reportSha256': hashlib.sha256(release.read_bytes()).hexdigest(),
                    'windows': {'playerManifestSha256': 'bc' * 32, 'seatsVerified': 15},
                    'quest': {'versionCode': 64, 'apkSha256': '2a' * 32, 'reportsVerified': 1, 'seatsVerified': 10}})
                self.assertEqual([seat for session in split['sessions'] for seat in session['windowsReleaseSeats']],
                                 [{'roomId': room, 'seat': seat} for room in range(1, 6) for seat in range(1, 4)])
                self.assertNotIn('windowsLinkMetricsVerified', split)
                self.assertFalse(split['physicalHostsVerified'])
                path.write_text(json.dumps(self.pack_venue(root, manifest)), encoding='utf-8')
                self.assertEqual(field.verify_venue(path), split)

    def test_shared_venue_release_rejects_swapped_or_incomplete_proofs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Independent', remote=True, quest_per_room=2)
            self.add_shared_release(root, manifest, 2)
            swapped, missing_windows, missing_quest, duplicate_release = (deepcopy(manifest) for _ in range(4))
            first, second = swapped['sessions'][0]['players'][:2]
            first['launcherReport'], second['launcherReport'] = second['launcherReport'], first['launcherReport']
            missing_windows['sessions'][0]['players'][0].pop('launcherReport')
            missing_quest.pop('questDeployments')
            duplicate_release['questDeployments']['releaseReport'] = 'other-release.json'
            for candidate, message in [(swapped, 'original player log bytes'), (missing_windows, 'every Windows seat'),
                                       (missing_quest, 'every Quest seat'), (duplicate_release, 'exactly one release report')]:
                with self.subTest(message=message):
                    path.write_text(json.dumps(candidate), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, message):
                        field.verify_venue(path)
            path.write_text(json.dumps(manifest), encoding='utf-8')
            launch_path = root / manifest['sessions'][0]['players'][0]['launcherReport']
            launch = json.loads(launch_path.read_bytes())
            launch['playerManifestSha256'] = '11' * 32
            launch_path.write_text(json.dumps(launch), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'original venue release manifest'):
                field.verify_venue(path)
            release_path = root / manifest['venueReleaseReport']
            release = json.loads(release_path.read_bytes())
            release['quest']['sha256'] = '35' * 32
            release_path.write_text(json.dumps(release), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'differs from the original release APK'):
                field.verify_venue(path)

    def test_shared_venue_release_can_recheck_original_link_metrics_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Linked')
            self.add_shared_release(root, manifest, 0)
            self.add_windows_links(root, manifest)
            for entry in manifest['sessions']:
                for seat in entry['players']:
                    launch_path = root / seat['launcherReport']
                    launch = json.loads(launch_path.read_bytes())
                    del launch['playerLogSha256']  # This earlier launcher recorded the log digest only in linkMetrics.
                    launch_path.write_text(json.dumps(launch), encoding='utf-8')
            path.write_text(json.dumps(manifest), encoding='utf-8')
            result = field.verify_venue(path)
            self.assertEqual(result['windowsLinkMetricsVerified'], 25)
            self.assertEqual(result['venueRelease']['windows']['seatsVerified'], 25)
            manifest['sessions'][0]['players'][0].pop('linkMetrics')
            path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'original player log bytes'):
                field.verify_venue(path)

    def test_quest_deployments_bind_original_release_and_retried_seats_to_both_venue_modes(self):
        for mode, quest_per_room in (('Independent', 2), ('Linked', 5)):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest = quest_capture_venue_fixture(root, mode, quest_per_room=quest_per_room)
                report = self.quest_deployment_evidence(root, manifest, quest_per_room)
                rows = report['devices']
                interrupted = dict(report, complete=False, devices=rows[:3] + [
                    {'roomId': row['roomId'], 'seat': row['seat'], 'status': 'apk-hash-mismatch' if index == 0 else 'not-attempted'}
                    for index, row in enumerate(rows[3:])])
                (root / 'deployment.json').write_text(json.dumps(interrupted), encoding='utf-8')
                (root / 'retry.json').write_text(json.dumps(dict(report, devices=rows[3:])), encoding='utf-8')
                manifest['questDeployments']['reports'].insert(0, 'retry.json')
                if mode == 'Linked':
                    manifest = self.pack_venue(root, manifest)
                    manifest.pop('windowsPlayers')
                path.write_text(json.dumps(manifest), encoding='utf-8')
                result = field.verify_venue(path)
                self.assertEqual({'versionCode': 64, 'apkSha256': '2a' * 32, 'reportsVerified': 2, 'seatsVerified': 5 * quest_per_room},
                                 result['questDeployment'])
                self.assertEqual(25, result['serverAcknowledgements'])
                self.assertFalse(result['physicalHostsVerified'])
                self.assertNotIn(rows[0]['admissionId'], json.dumps(result))

    def test_quest_capture_matches_exact_referenced_deployment(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest = quest_capture_venue_fixture(root, mode, quest_per_room=1, batches=1)
                deployment = self.quest_deployment_evidence(root, manifest, 1)
                deployment['retry'] = {'version': 1, 'venueSha256': '1' * 64, 'mapSha256': '2' * 64,
                                       'salt': '3' * 32, 'devices': [f'{index:064x}' for index in range(1, 6)]}
                original = root / 'deployment.json'
                original.write_text(json.dumps(deployment), encoding='utf-8')
                capture_path = root / manifest['questCaptures']['reports'][0]
                report = json.loads(capture_path.read_bytes())
                report['deploymentSha256'] = hashlib.sha256(original.read_bytes()).hexdigest()
                capture_path.write_text(json.dumps(report), encoding='utf-8')
                path.write_text(json.dumps(manifest), encoding='utf-8')
                checked = field.verify_venue(path)
                self.assertEqual(1, checked['questCaptureDeploymentReportsMatched'])
                self.assertEqual(deployment['expectedApkSha256'], checked['questDeployment']['apkSha256'])

                with self.assertRaisesRegex(capture_tool.field.EvidenceError, 'same original Quest deployment report'):
                    capture_tool.retry_capture_plan({'topology': mode, 'seats': [], 'deploymentSha256': '4' * 64}, capture_path)
                path.write_text(json.dumps({key: value for key, value in manifest.items() if key != 'questDeployments'}), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'original Quest deployment reports referenced'):
                    field.verify_venue(path)
                path.write_text(json.dumps(manifest), encoding='utf-8')
                original.write_bytes(original.read_bytes() + b'\n')
                with self.assertRaisesRegex(field.EvidenceError, 'exact completed Quest deployment report'):
                    field.verify_venue(path)

    def test_quest_capture_checks_device_map_and_network_plan_for_separate_deployments(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest = quest_capture_venue_fixture(root, mode, quest_per_room=1, batches=2)
                capture_spec = manifest['questCaptures']
                device_spec = observed_quest_capture_spec(root, capture_spec)
                capture_spec.update(deviceMap=device_spec['deviceMap'])
                map_path, network_path = (root / capture_spec[key] for key in ('deviceMap', 'networkPlan'))
                raw_map, raw_network = map_path.read_bytes(), network_path.read_bytes()
                serials = {(row['roomId'], row['seat']): row['serial'] for row in json.loads(raw_map)['seats']}
                deployment = self.quest_deployment_evidence(root, manifest, 1)
                devices = {(row['roomId'], row['seat']): row for row in deployment['devices']}
                manifest['questDeployments']['reports'] = []
                for batch, capture_name in enumerate(capture_spec['reports'], 1):
                    capture_path = root / capture_name
                    captured = json.loads(capture_path.read_bytes())
                    seats = sorted((row['roomId'], row['seat']) for row in captured['seats'])
                    assignments = '\n'.join(f'{room}/{seat}={serials[room, seat]}' for room, seat in seats)
                    salt = f'{batch:032x}'
                    proof = {'version': 1, 'venueSha256': '1' * 64, 'salt': salt,
                             'mapSha256': hashlib.sha256(f'{salt}\n{assignments}'.encode()).hexdigest(),
                             'devices': [f'{index:064x}' for index in range(1, len(seats) + 1)]}
                    deployment_path = root / f'deployment-{batch}.json'
                    deployment_path.write_text(json.dumps(dict(deployment, retry=proof, devices=[devices[seat] for seat in seats])), encoding='utf-8')
                    manifest['questDeployments']['reports'].insert(0, deployment_path.name)
                    captured['deploymentSha256'] = hashlib.sha256(deployment_path.read_bytes()).hexdigest()
                    capture_path.write_text(json.dumps(captured), encoding='utf-8')
                path.write_text(json.dumps(manifest), encoding='utf-8')
                checked = field.verify_venue(path)
                self.assertEqual(2, checked['questCaptureDeploymentReportsMatched'])
                self.assertEqual(2, checked['questDeployment']['deviceMapsMatched'])
                self.assertEqual(deployment['expectedApkSha256'], checked['questDeployment']['apkSha256'])
                self.assertNotIn('questCaptureAddressSource', checked)
                self.assertNotIn('fixture-', json.dumps(checked))

                changed = json.loads(raw_map)
                changed['seats'][0]['serial'] = 'another-adb-label'
                map_path.write_text(json.dumps(changed), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'device map differs from the original referenced deployment'):
                    field.verify_venue(path)
                map_path.write_bytes(raw_map)
                changed = json.loads(raw_network)
                changed['sources'][0]['address'] = '192.168.5.210'
                network_path.write_text(json.dumps(changed), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'UDP peer differs from the declared source'):
                    field.verify_venue(path)
                network_path.write_bytes(raw_network)
                changed = json.loads(raw_map)
                changed['seats'].pop()
                map_path.write_text(json.dumps(changed), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'network plan and device map must cover the same seats'):
                    field.verify_venue(path)
                map_path.write_bytes(raw_map)
                del capture_spec['networkPlan']
                path.write_text(json.dumps(manifest), encoding='utf-8')
                observed = field.verify_venue(path)
                self.assertEqual('server-observed', observed['questCaptureAddressSource'])
                self.assertEqual(checked['questDeployment'], observed['questDeployment'])

    def test_quest_deployments_reject_swapped_originals_and_incomplete_or_duplicate_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Independent', remote=True, quest_per_room=2)
            original = self.quest_deployment_evidence(root, manifest, 2)
            path.write_text(json.dumps(manifest), encoding='utf-8')
            deploy = root / 'deployment.json'
            cases = (
                ('preflight', 'lacks verified deployment', lambda report: report.update(phase='preflight')),
                ('different APK', 'differs from the original release APK', lambda report: report.update(expectedApkSha256='9b' * 32)),
                ('missing verification', 'lacks verified APK', lambda report: report['devices'][0].pop('apkVerified')),
                ('wrong session', 'original admission and endpoint', lambda report: report['devices'][0].update(sessionId=id_for(2000))),
                ('wrong player', 'original admission and endpoint', lambda report: report['devices'][0].update(playerId=id_for(2001))),
                ('wrong admission', 'original admission and endpoint', lambda report: report['devices'][0].update(admissionId=id_for(2002))),
                ('wrong endpoint', 'original admission and endpoint', lambda report: report['devices'][0].update(port=7999)),
                ('missing seat', 'original admission and endpoint', lambda report: report['devices'].pop()),
                ('duplicate seat', 'repeats a device seat', lambda report: report['devices'].append(report['devices'][0])),
                ('non-prefix launch', 'consistent successful prefix', lambda report: report['devices'][0].update(status='not-attempted')),
                ('extra Windows seat', 'without original Quest logcat', lambda report: report['devices'].append(dict(report['devices'][0], seat=1))),
            )
            for label, message, change in cases:
                with self.subTest(label=label):
                    report = deepcopy(original)
                    change(report)
                    deploy.write_text(json.dumps(report), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, message):
                        field.verify_venue(path)
            deploy.write_text(json.dumps(original), encoding='utf-8')
            self.assertEqual(10, field.verify_venue(path)['questDeployment']['seatsVerified'])
            (root / 'duplicate.json').write_bytes(deploy.read_bytes())
            manifest['questDeployments']['reports'].append('duplicate.json')
            path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'repeats a successful seat'):
                field.verify_venue(path)

    def test_quest_deployment_history_accepts_exact_cumulative_retries_in_both_modes(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest = quest_capture_venue_fixture(root, mode, quest_per_room=1)
                complete = self.quest_deployment_evidence(root, manifest, 1)
                rows = complete['devices']
                proof = dict(version=1, venueSha256='12'*32, mapSha256='34'*32, salt='56'*16,
                             devices=[f'{seat:064x}' for seat in range(1, len(rows)+1)])

                def save_report(name, value):
                    raw = (json.dumps(value) + '\r\n').encode('utf-8-sig')
                    (root/name).write_bytes(raw)
                    return hashlib.sha256(raw).hexdigest()

                def incomplete(count, **fields):
                    return dict(complete, retry=proof, complete=False, devices=rows[:count] + [
                        dict(roomId=row['roomId'], seat=row['seat'], status='not-attempted') for row in rows[count:]], **fields)

                first = incomplete(0)
                first_hash = save_report('deployment.json', first)
                second = incomplete(2, previousDeploymentSha256=first_hash)
                second_hash = save_report('second.json', second)
                final = dict(complete, retry=proof, previousDeploymentSha256=second_hash)
                save_report('final.json', final)
                reports = manifest['questDeployments']['reports']
                reports[:] = ['final.json', 'deployment.json', 'second.json']
                path.write_text(json.dumps(manifest), encoding='utf-8')
                checked = field.verify_venue(path)
                self.assertEqual((3, 2, 5), tuple(checked['questDeployment'][key] for key in
                    ('reportsVerified', 'retryReportsLinked', 'seatsVerified')))
                self.assertEqual(25, checked['serverAcknowledgements'])

                reports[:] = ['final.json']
                path.write_text(json.dumps(manifest), encoding='utf-8')
                latest = field.verify_venue(path)
                self.assertEqual(5, latest['questDeployment']['seatsVerified'])
                self.assertNotIn('retryReportsLinked', latest['questDeployment'])

                cases = (
                    ('changed proof', 'changes its original proof', dict(final, retry=dict(proof, mapSha256='78'*32))),
                    ('changed completed seat', 'changes its original proof', dict(final, devices=[dict(rows[0], port=7999), *rows[1:]])),
                    ('different predecessor', 'history is disconnected', dict(final, previousDeploymentSha256='9a'*32)),
                    ('unlinked old cumulative', 'history is disconnected', dict(complete, retry=proof)),
                )
                reports[:] = ['deployment.json', 'second.json', 'final.json']
                path.write_text(json.dumps(manifest), encoding='utf-8')
                for label, message, report in cases:
                    with self.subTest(label=label):
                        save_report('final.json', report)
                        with self.assertRaisesRegex(field.EvidenceError, message):
                            field.verify_venue(path)
                save_report('final.json', final)
                save_report('fork.json', incomplete(3, previousDeploymentSha256=second_hash))
                reports.append('fork.json')
                path.write_text(json.dumps(manifest), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'Conflicting Quest deployment retry branches'):
                    field.verify_venue(path)

    def test_venue_rejects_incomplete_wrong_and_tampered_capture_evidence(self):
        cases = {
            'incomplete report': 'completeness differs',
            'wrong topology': 'wrong topology',
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

    def test_venue_recovers_one_interrupted_adb_seat_without_replacing_completed_captures(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest = quest_capture_venue_fixture(root, mode, quest_per_room=1, batches=1,
                                                               use_capture_tool=True, interrupt_first=True)
                first_name, retry_name = manifest['questCaptures']['reports']
                first_path, retry_path = root / first_name, root / retry_name
                first_bytes = first_path.read_bytes()
                first = json.loads(first_bytes)
                retry = json.loads(retry_path.read_bytes())
                self.assertFalse(first['complete'])
                self.assertEqual((5, 4), (first['expectedSeats'], first['capturedSeats']))
                missing, = [row for row in first['seats'] if not row['complete']]
                partial = first_path.parent / missing['partial']
                raw_partial = partial.read_bytes()
                self.assertTrue(raw_partial)
                self.assertNotIn(b'VR_CLIENT_DEBRIEF_FINAL', raw_partial)
                self.assertEqual((missing['roomId'], missing['seat']), (retry['seats'][0]['roomId'], retry['seats'][0]['seat']))
                report = field.verify_venue(path)
                self.assertEqual(25, report['serverAcknowledgements'])
                self.assertEqual((2, 5, 1, 1), (report['questCaptureBatchesVerified'], report['questCaptureSeatsVerified'],
                                               report['questCaptureIncompleteReports'], report['questCaptureFailedAttempts']))
                self.assertEqual(first_bytes, first_path.read_bytes())
                self.assertEqual(raw_partial, partial.read_bytes())
                manifest['questCaptures']['reports'] = [first_name]
                path.write_text(json.dumps(manifest), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'cover the planned Quest seats'):
                    field.verify_venue(path)
                duplicate = root / 'duplicate'
                shutil.copytree(retry_path.parent, duplicate)
                manifest['questCaptures']['reports'] = [first_name, retry_name, 'duplicate/capture-report.json']
                path.write_text(json.dumps(manifest), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'repeats a completed seat'):
                    field.verify_venue(path)

    def test_mixed_venue_uses_original_quest_device_map_and_windows_inbox(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest = quest_capture_venue_fixture(root, mode, quest_per_room=1, batches=1,
                    use_capture_tool=True, interrupt_first=True)
                self.add_shared_release(root, manifest, 1)
                path.write_text(json.dumps(manifest), encoding='utf-8')
                baseline = field.verify_venue(path)
                observed = self.windows_inbox_fixture(root, manifest)
                observed['questCaptures'] = observed_quest_capture_spec(root, manifest['questCaptures'])
                windows = [{'roomId': room, 'seat': seat, 'station': f'PC-{room}-{seat}'}
                           for room in range(1, 6) for seat in range(1, 5)]
                (root / 'windows-seats.json').write_text(json.dumps({'version': 1, 'seats': windows}), encoding='utf-8')
                observed['windowsSeatMap'] = 'windows-seats.json'
                path.write_text(json.dumps(observed), encoding='utf-8')
                report = field.verify_venue(path)
                self.assertEqual('server-observed', report.pop('questCaptureAddressSource'))
                self.assertEqual(baseline, report)
                self.assertEqual((5, 20, 25), (report['questCaptureSeatsVerified'],
                    report['venueRelease']['windows']['seatsVerified'], report['serverAcknowledgements']))
                self.assertNotIn('192.168.', json.dumps(report))

    def test_observed_quest_capture_rejects_duplicate_or_local_sources_and_wrong_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest = quest_capture_venue_fixture(root, 'Independent', quest_per_room=1, batches=1)
            network = json.loads((root / manifest['questCaptures']['networkPlan']).read_bytes())
            sources = {row['roomId']: row['address'] for row in network['sources']}
            manifest['questCaptures'] = observed_quest_capture_spec(root, manifest['questCaptures'])
            path.write_text(json.dumps(manifest), encoding='utf-8')
            server = root / manifest['sessions'][1]['serverLog']
            original = server.read_text(encoding='utf-8')
            for address, error in ((sources[1], 'distinct observed IPv4'),
                                   (network['endpoints'][0]['address'], 'own direct LAN address')):
                with self.subTest(address=address):
                    server.write_text(original.replace(f'endpoint={sources[2]}:', f'endpoint={address}:'), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, error):
                        field.verify_venue(path)
            server.write_text(original, encoding='utf-8')
            report_path = root / manifest['questCaptures']['reports'][0]
            capture = json.loads(report_path.read_bytes())
            capture['seats'][0]['port'] += 1
            report_path.write_text(json.dumps(capture), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'port differs from the original game binding'):
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
            plan_path = root / 'network-plan.json'
            network = json.loads(plan_path.read_bytes())
            entry['udpSourcePreflights'] = []
            for index, source in enumerate(network['sources']):
                listener, probe = preflight_fixture(root, f'quest-{index}', server=binding['address'],
                                                    peer=source['address'], port=binding['port'])
                entry['udpSourcePreflights'].append({'listener': listener.name, 'probe': probe.name})
            manifest['venueNetworkPlan'] = plan_path.name
            batch = {'version': 1, 'scope': 'venue-udp-preflight-only', 'mode': 'Linked', 'complete': True,
                     'networkPlanSha256': hashlib.sha256(plan_path.read_bytes()).hexdigest(),
                     'groups': [{'roomIds': list(range(1, 6)), 'complete': True,
                                 'udpSourcePreflights': entry.pop('udpSourcePreflights')}]}
            batch_path = root / 'readiness.json'
            batch_path.write_text(json.dumps(batch), encoding='utf-8')
            manifest['udpPreflightBatch'] = batch_path.name
            path.write_text(json.dumps(manifest), encoding='utf-8')
            report = field.verify_venue(path)
            self.assertEqual(25, report['questCaptureSeatsVerified'])
            self.assertEqual(25, report['udpSourcePreflightsVerified'])
            self.assertEqual(25, report['serverAcknowledgements'])
            self.assertEqual(25, report['venueNetworkPlan']['verifiedSeats'])
            plan_path.write_bytes(plan_path.read_bytes() + b'\n')
            with self.assertRaisesRegex(field.EvidenceError, 'different original venue network plan'):
                field.verify_venue(path)

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
            plan = {'version': 4, 'topology': 'Independent', 'controlInstance': 'fixture/control-instance.json', 'servers': []}
            preview = {'schemaVersion': 1, 'status': 'venue-checked', 'complete': True, 'topology': 'Independent', 'servers': []}
            for index, entry in enumerate(manifest['sessions'], 1):
                archive = root / entry['evidenceZip']
                session, statistics, endpoint = field.management_zip(archive)
                session['mission']['id'] = id_for(100 + index)
                with zipfile.ZipFile(archive, 'w') as bundle:
                    for name, value in [('session.json', session), ('statistics.json', statistics), ('endpoint.json', endpoint)]:
                        bundle.writestr(name, json.dumps(value))
                plan.update(address=endpoint['address'], listenAddress=endpoint['address'])
                plan['servers'].append({'sessionId': session['id'], 'missionId': session['mission']['id'],
                                        'roomIds': [index], 'sessionSequence': 5, 'port': endpoint['port']})
                preview['servers'].append({**plan['servers'][-1], 'address': endpoint['address'], 'listenAddress': endpoint['address']})
            plan_path = batch_folder / 'launch.json'
            preview_path = batch_folder / 'preview.json'

            def save_binding(scope='quest-udp-preflight-only'):
                plan_path.write_text(json.dumps(plan), encoding='utf-8')
                preview_path.write_text(json.dumps(preview), encoding='utf-8')
                original = field.read_udp_launcher_document(plan_path, preview=False)
                current = field.read_udp_launcher_document(preview_path, preview=True)
                checked = field.compare_udp_launch_documents(original, current)
                endpoints = {rooms: (row['address'], row['port']) for rooms, row in original[2].items()}
                summary = (field.check_udp_launcher_endpoints(current, 'Independent', endpoints) if scope == 'quest-udp-preflight-only'
                           else {'sha256': checked['previewSha256'], 'complete': True})
                bound = dict(batch, scope=scope,
                             launchBinding={'plan': plan_path.name, 'preview': preview_path.name, **checked},
                             launcherPreview=summary)
                batch_path.write_text(json.dumps(bound), encoding='utf-8')

            save_binding('venue-udp-preflight-only')
            legacy = field.verify_venue(path)
            save_binding()
            self.assertEqual(legacy, field.verify_venue(path))
            self.assertEqual(5, field.verify_venue(path)['udpSourcePreflightsVerified'])
            preview_path.write_bytes(preview_path.read_bytes() + b'\n')
            with self.assertRaisesRegex(field.EvidenceError, 'differs from the UDP readiness proof'):
                field.verify_venue(path)
            original_session = plan['servers'][-1]['sessionId']
            plan['servers'][-1]['sessionId'] = preview['servers'][-1]['sessionId'] = id_for(999)
            save_binding()
            with self.assertRaisesRegex(field.EvidenceError, 'sessions differ from the original sealed batch'):
                field.verify_venue(path)
            plan['servers'][-1]['sessionId'] = preview['servers'][-1]['sessionId'] = original_session
            for key, altered in [('port', 17777), ('missionId', id_for(998)), ('sessionSequence', 999)]:
                with self.subTest(sealed_binding=key):
                    original_value = plan['servers'][-1][key]
                    plan['servers'][-1][key] = preview['servers'][-1][key] = altered
                    save_binding()
                    with self.assertRaisesRegex(field.EvidenceError, 'does not match the sealed mission and game binding'):
                        field.verify_venue(path)
                    plan['servers'][-1][key] = preview['servers'][-1][key] = original_value
            batch_path.write_text(json.dumps(batch), encoding='utf-8')
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

                merged = [{'roomIds': original['roomIds'], 'complete': True,
                           'udpSourcePreflights': list(session['udpSourcePreflights'])}
                          for original, session in zip(closure['sessions'], manifest['sessions'], strict=True)]
                by_rooms = {tuple(group['roomIds']): group['udpSourcePreflights'] for group in merged}
                for folder, rows in groups.items():
                    for row in rows:
                        by_rooms[tuple(row['roomIds'])].extend({key: f'{folder}/{value}' for key, value in source.items()}
                                                              for source in row['udpSourcePreflights'])
                (root / 'venue-readiness.json').write_text(json.dumps({'version': 1, 'scope': 'venue-udp-preflight-only',
                    'mode': mode, 'complete': True, 'groups': merged}), encoding='utf-8')
                merged_manifest = {key: value for key, value in manifest.items() if key != 'udpPreflightBatches'}
                merged_manifest['udpPreflightBatch'] = 'venue-readiness.json'
                merged_manifest['sessions'] = [{key: value for key, value in session.items() if key != 'udpSourcePreflights'}
                                               for session in manifest['sessions']]
                path.write_text(json.dumps(merged_manifest), encoding='utf-8')
                self.assertEqual(report, field.verify_venue(path))

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

    def alignment_bundle_fixture(self, root, manifest):
        mixed = any('roomAlignments' not in entry for entry in manifest['sessions'])
        venue = {'version': 2 if mixed else 1, 'topology': manifest['mode'], 'rooms': []}
        if mixed:
            venue['mode'] = 'Mixed'
        members = {}
        for entry in manifest['sessions']:
            session, _, endpoint = field.management_zip(root / entry['evidenceZip'])
            for room in session['roomIds']:
                ticket = f'room-{room:02}-connections.zip'
                row = {'roomId': room, 'sessionId': session['id'], 'ticketsZip': ticket}
                if mixed:
                    row.update(mode=session['environment']['mode'], address=endpoint['address'], port=endpoint['port'])
                if 'roomAlignments' in entry:
                    name = f'room-{room:02}-alignment.json'
                    row['alignmentFile'] = name
                    members[name] = (root / entry['roomAlignments'][str(room)]).read_bytes()
                venue['rooms'].append(row)
                members[ticket] = b'opaque private connection member'
        return venue, members

    def write_alignment_bundle(self, path, venue, members):
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('venue.json', json.dumps(venue))
            for name, raw in members.items():
                archive.writestr(name, raw)

    def test_prepare_and_verify_original_deployment_zip_alignment(self):
        for mode, mr_rooms in (('Independent', (2,)), ('Independent', (1, 2, 3, 4, 5)), ('Linked', (1, 2, 3, 4, 5))):
            with self.subTest(mode=mode, mr_rooms=mr_rooms), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, closure = venue_fixture(root, mode, remote=True, with_journals=True, mr_rooms=mr_rooms)
                venue, members = self.alignment_bundle_fixture(root, manifest)
                bundle = root / 'deployment.zip'
                self.write_alignment_bundle(bundle, venue, members)
                terminal, _, moved = self.terminal_venue_fixture(root, manifest, closure)
                packed = self.pack_venue(root, manifest)
                if not packed['windowsPlayers']:
                    packed.pop('windowsPlayers')
                path.write_text(json.dumps(packed), encoding='utf-8')
                original = field.verify_venue(path)
                output = root / 'prepared.json'
                command = [sys.executable, str(SCRIPT.with_name('prepare-venue-field-manifest.py')),
                           '--venue-bundle', str(root / packed['venueBundle']), '--launcher-report', str(terminal),
                           '--topology', 'direct-lan', '--server-ip', manifest['serverIps'][0], '--server-work-root', str(moved),
                           '--room-alignment-bundle', bundle.name, '--output', str(output)]
                prepared = subprocess.run(command, cwd=root, capture_output=True)
                self.assertEqual(0, prepared.returncode, prepared.stderr.decode())
                raw_output = output.read_bytes()
                self.assertNotIn(b'opaque private connection member', raw_output)
                generated = json.loads(raw_output)
                self.assertEqual(bundle.name, generated['roomAlignmentBundle'])
                if 'windowsPlayers' in packed:
                    generated['windowsPlayers'] = packed['windowsPlayers']
                by_id = {entry['sessionId']: entry for entry in packed['sessions']}
                for entry in generated['sessions']:
                    self.assertNotIn('roomAlignments', entry)
                    source = by_id[entry['sessionId']]
                    if 'players' in source:
                        entry['players'] = source['players']
                    for name in source.get('roomAlignments', {}).values():
                        (root / name).unlink()
                output.write_text(json.dumps(generated), encoding='utf-8')
                result = field.verify_venue(output)
                self.assertEqual(original, result)
                self.assertEqual(len(mr_rooms), result['roomAlignmentsVerified'])

    def test_deployment_zip_alignment_rejects_mismatched_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, closure = venue_fixture(root, 'Independent', remote=True, with_journals=True, mr_rooms=(2, 4))
            venue, members = self.alignment_bundle_fixture(root, manifest)
            bundle = root / 'deployment.zip'
            terminal, _, moved = self.terminal_venue_fixture(root, manifest, closure)
            packed = self.pack_venue(root, manifest)
            packed['roomAlignmentBundle'] = bundle.name
            path.write_text(json.dumps(packed), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'either roomAlignmentBundle or individual'):
                field.verify_venue(path)
            for entry in packed['sessions']:
                entry.pop('roomAlignments', None)
            path.write_text(json.dumps(packed), encoding='utf-8')
            output = root / 'rejected.json'
            command = [sys.executable, str(SCRIPT.with_name('prepare-venue-field-manifest.py')),
                       '--venue-bundle', str(root / packed['venueBundle']), '--launcher-report', str(terminal),
                       '--topology', 'direct-lan', '--server-ip', manifest['serverIps'][0], '--server-work-root', str(moved),
                       '--room-alignment-bundle', str(bundle), '--output', str(output)]
            for altered, message in (
                ({'topology': 'Linked'}, 'topology differs'),
                ({'sessionId': venue['rooms'][3]['sessionId']}, 'differs from the original closure session'),
                ({'port': 12000}, 'endpoint differs'),
                ({'mode': 'VR', 'alignmentFile': None}, 'only for MR sessions'),
            ):
                with self.subTest(altered=altered):
                    invalid = deepcopy(venue)
                    (invalid if 'topology' in altered else invalid['rooms'][1]).update(altered)
                    self.write_alignment_bundle(bundle, invalid, members)
                    with self.assertRaisesRegex(field.EvidenceError, message):
                        field.verify_venue(path)
            alignment = 'room-02-alignment.json'
            for changed, message in (
                ({name: raw for name, raw in members.items() if name != alignment}, 'alignment ZIP member for every MR room'),
                ({**members, 'extra.json': b'{}'}, 'Invalid MR or mixed deployment ZIP members'),
                ({**members, alignment: members[alignment].rstrip()}, 'bytes differ from the sealed session lock'),
            ):
                with self.subTest(message=message):
                    self.write_alignment_bundle(bundle, venue, changed)
                    with self.assertRaisesRegex(field.EvidenceError, message):
                        field.verify_venue(path)
                    rejected = subprocess.run(command, capture_output=True)
                    self.assertEqual(1, rejected.returncode)
                    self.assertIn(message.encode(), rejected.stderr)
                    self.assertFalse(output.exists())

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
        prop = {'id': id_for(17), 'kind': 'Barrel', 'roomId': 1, 'feet': {'x': 0.1, 'y': 0, 'z': 2}, 'yaw': 45}
        world['header'].update(props=[prop], rulesVersion='0.8.0', assetSet='field-props-v1',
                               missionClockVersion=1, missionDurationSeconds=60)
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
                ({'header_changes': {'props': []}}, 'source or record integrity'),
                ({'header_changes': {'props': [dict(prop, feet=dict(prop['feet'], x=0.125))]}}, 'source or record integrity'),
                ({'header_changes': {'props': [dict(prop, feet=dict(prop['feet'], y=False))]}}, 'source or record integrity'),
                ({'header_changes': {'props': [dict(prop, yaw=46)]}}, 'source or record integrity'),
                ({'header_changes': {'rulesVersion': '0.9.0'}}, 'source or record integrity'),
                ({'header_changes': {'assetSet': 'primitives-v1'}}, 'source or record integrity'),
                ({'header_changes': {'missionDurationSeconds': 61}}, 'source or record integrity'),
                ({'header_changes': {'missionClockVersion': True}}, 'source or record integrity'),
                ({'header_changes': {'enemyPresentationVersion': 1}}, 'source or record integrity'),
                ({'header_changes': {'unknownCapability': 1}}, 'source or record integrity'),
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

    def test_original_world_header_accepts_native_float_encoding_and_legacy_zero_defaults(self):
        data = fixture()
        world = data[2]['finalWorld']
        prop = {'id': id_for(17), 'kind': 'Barrel', 'roomId': 1, 'feet': {'x': 0.1, 'y': 0, 'z': 2}, 'yaw': 45}
        world['header']['props'] = [prop]
        raw_prop = dict(prop, feet={'x': 0.10000000149011612, 'y': -0.0, 'z': 2.0}, yaw=45.0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.worldlog'
            world_journal(path, world, header_changes={'props': [raw_prop]})
            world['header'].update(environmentVersion=0, missionClockVersion=0, missionDurationSeconds=0)
            self.assertEqual(80, field.verify(*data, world_journal=path)['worldJournal']['frames'])
            world['header']['environmentVersion'] = 1
            with self.assertRaisesRegex(field.EvidenceError, 'source or record integrity'):
                field.verify(*data, world_journal=path)

    def test_venue_requires_all_original_journals_when_supplied(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, mode, with_journals=True)
                entry = manifest['sessions'][0]
                source = root / entry['worldJournal']
                launcher_path = root / entry['launcherReport']
                launcher = json.loads(launcher_path.read_text())
                launcher['finalWorld']['header']['props'] = [{'id': id_for(17), 'kind': 'Barrel', 'roomId': 1,
                    'feet': {'x': 0.1, 'y': 0, 'z': 2.5}, 'yaw': 45}]
                world_journal(source, launcher['finalWorld'])
                launcher_path.write_text(json.dumps(launcher), encoding='utf-8')
                report = field.verify_venue(path)
                self.assertEqual(5 if mode == 'Independent' else 1, report['worldJournalsVerified'])
                self.assertTrue(all(row['worldJournal']['frames'] == row['worldSequence'] for row in report['sessions']))
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

    def reconnect_history_fixture(self):
        data = fixture()
        data[3]['players'][0]['seat'] = 0
        data[3]['players'][1]['seat'] = 1
        address, log = data[7][1]
        data[7][1] = (address, 'VR_CLIENT_CONNECTED id=8\nVR_CLIENT_DISCONNECTED\n' + log)
        startup_marker = 'VR_NETWORK_STARTED role=Client started=True background=True port=7777\n'
        data[7] = [(address, startup_marker + log) for address, log in data[7]]
        startup, rest = data[6].split('\n', 1)
        data[6] = (startup + '\nVR_SERVER_ADMISSION_APPROVED id=8\nVR_SERVER_PEER id=8 endpoint=192.168.5.20:5010\n'
                   'VR_SERVER_CLIENT_LEFT id=8\n' + rest)
        return data

    def test_reconnect_history_verifies_original_windows_and_quest_connection_order(self):
        for quest in (False, True):
            with self.subTest(quest=quest), tempfile.TemporaryDirectory() as directory:
                data = self.reconnect_history_fixture()
                address, log = data[7].pop()
                player_markers = log.split('\n', 1)[1]
                quest_logs = []
                if quest:
                    data[3]['players'][1]['headset'] = 'Quest3'
                    quest_logs.append((address, quest_logcat(player_markers), 7342))
                else:
                    data[7].append((address, PlayerSourceEvidenceTests.openxr_startup('Unity Mock Runtime') + player_markers))
                journal = Path(directory) / 'original.worldlog'
                owners = data[3]['players']
                rows = [{'id': owner['id'], 'roomId': 1, 'connected': True, 'rig': {'kind': kind}}
                        for owner, kind in zip(owners, ('Simulated', 'Tracked'), strict=True)]
                world_journal(journal, data[2]['finalWorld'], players=lambda _, phase: rows if phase == 'Running' else [])
                report = field.verify(*data, quest_player_logs=quest_logs, world_journal=journal,
                                      verify_player_sources=True, verify_reconnect_history=True)
                self.assertEqual({'observedConnections': 3, 'retiredConnections': 1,
                                  'reconnectedSeats': [{'roomId': 1, 'seat': 2, 'retiredConnections': 1}]},
                                 report['reconnectHistory'])
                self.assertEqual(2, report['serverAcknowledgements'])
                self.assertEqual('quest-logcat-tracked' if quest else 'windows-openxr-mock-tracked', report['playerSources'][1]['source'])
                self.assertNotIn('192.168', json.dumps(report))

    def test_reconnect_history_rejects_missing_reordered_or_shared_prior_connections(self):
        for case, error in (
            ('missing', 'Missing server release'), ('late', 'Missing server release'),
            ('wrong source', 'Historical UDP peer differs'), ('shared', 'reused across player logs'),
            ('extra peer', 'unmatched UDP peer records'), ('ack after release', 'acknowledgement follows server release'),
            ('second startup', 'one original Windows client startup'), ('missing startup', 'precedes the original client startup'),
        ):
            with self.subTest(case=case):
                data = self.reconnect_history_fixture()
                left = 'VR_SERVER_CLIENT_LEFT id=8\n'
                if case in ('missing', 'late'):
                    data[6] = data[6].replace(left, '') + (left if case == 'late' else '')
                elif case == 'wrong source':
                    data[6] = data[6].replace('192.168.5.20:5010', '192.168.5.22:5010')
                elif case == 'shared':
                    _, log = data[7][0]
                    startup, log = log.split('\n', 1)
                    data[7][0] = (data[7][1][0], startup + '\nVR_CLIENT_CONNECTED id=8\nVR_CLIENT_DISCONNECTED\n' + log)
                    data[6] = data[6].replace('192.168.5.10:5001', '192.168.5.20:5001')
                elif case == 'extra peer':
                    address, log = data[7][1]
                    startup, _, _, remaining = log.split('\n', 3)
                    data[7][1] = (address, startup + '\n' + remaining)
                elif case == 'ack after release':
                    data[6] = data[6].replace('VR_SERVER_DEBRIEF_ACK id=2', 'VR_SERVER_CLIENT_LEFT id=2\nVR_SERVER_DEBRIEF_ACK id=2')
                else:
                    address, log = data[7][1]
                    startup, remaining = log.split('\n', 1)
                    data[7][1] = (address, startup + '\n' + log if case == 'second startup' else remaining)
                with self.assertRaisesRegex(field.EvidenceError, error):
                    field.verify(*data, verify_reconnect_history=True)
                self.assertEqual(2, field.verify(*data)['serverAcknowledgements'])

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
        topology, ips, launcher, session, stats, endpoint, server, clients = self.reconnect_history_fixture()
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
            self.assertNotIn('reconnectHistory', legacy)
            archived = subprocess.run([*command, '--world-journal', str(journal)], capture_output=True, text=True, check=True)
            self.assertEqual(80, json.loads(archived.stdout)['worldJournal']['frames'])
            combat = root / 'original.journal'
            combat_journal(combat, launcher)
            closed = subprocess.run([*command, '--world-journal', str(journal), '--combat-journal', str(combat), '--verify-reconnect-history'],
                                    capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(closed.stdout)['combatJournal']['events'], 0)
            self.assertEqual(json.loads(closed.stdout)['reconnectHistory']['retiredConnections'], 1)
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
