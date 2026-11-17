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
from types import SimpleNamespace
import unittest
import uuid
import zipfile
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/verify-field-results.py'
sys.path.insert(0, str(SCRIPT.parent))
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


def insert_quest_link_metrics(log, pid, connection, *, process_id=None, report_connection=None, frame_pid=None, drop=False, reply_offset=0):
    samples = [{'sequence': i + 1, 'tick': 20 * (i + 1), 'playerLoopFrames': 72,
                'windowSeconds': 1, 'roundTripMilliseconds': 20 + reply_offset + i if i < 28 else 0,
                'result': 'Reply' if i < 28 else 'Timeout' if i == 28 else 'Interrupted'} for i in range(30)]
    data = json.dumps({'version': 1, 'processId': pid if process_id is None else process_id,
                       'connection': int(connection if report_connection is None else report_connection), 'complete': True,
                       'batchMode': False, 'graphicsDeviceActive': True, 'reason': 'Limit', 'samples': samples}, separators=(',', ':'))
    chunks = [data[i:i + 480] for i in range(0, len(data), 480)]
    lines = ''.join(logcat_line(f'VR_QUEST_LINK_METRICS id={connection} part={index}/{len(chunks)} {chunk}', frame_pid or pid)
                    for index, chunk in enumerate(chunks, 1) if not drop or index != 2)
    marker = logcat_line(f'VR_CLIENT_CONNECTED id={connection}', pid)
    assert marker in log
    return log.replace(marker, marker + lines, 1)


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


def combat_journal(path, launcher, records=(), *, sealed=True, receipt=None, observed=7):
    def frame(payload):
        return struct.pack('<i', len(payload)) + payload + hashlib.sha256(payload).digest()

    def guid(value):
        return uuid.UUID(value).bytes_le if value else bytes(16)

    origin = launcher['finalCombatStream']['origin'].encode('ascii')
    header = (struct.pack('<Bi', 1, 1) + guid(launcher['sessionId']) + guid(launcher['streamId'])
              + bytes([len(origin)]) + origin)
    raw = [frame(header)]
    if records:
        events = b''.join(struct.pack('<qq16sB16s16s16si', sequence, observed, guid(id_for(900 + sequence)),
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


def quest_capture_venue_fixture(root, mode, *, quest_per_room=2, batches=2, use_capture_tool=False, interrupt_first=False,
                                with_journals=False, room_sizes=(5,) * 5, id_offset=0, minutes_after=0):
    path, manifest, _ = venue_fixture(root, mode, remote=True, quest_per_room=quest_per_room, with_journals=with_journals,
                                     room_sizes=room_sizes, id_offset=id_offset, minutes_after=minutes_after)
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
root = Path(__file__).parent
transports = {str(index): path.stem for index, path in enumerate(sorted(root.glob('mock-*.log')), 1)}
if sys.argv[1:] == ['devices', '-l']:
    print('List of devices attached')
    for transport, serial in transports.items():
        print(f'{serial} device transport_id:{transport}')
    sys.exit(0)
assert sys.argv[1] == '-t'
serial = transports[sys.argv[2]]
if sys.argv[3:] == ['shell', 'pidof', 'com.vrcommand.quest']:
    print(7342)
else:
    assert sys.argv[3:] == ['logcat', '-b', 'main', '--pid=7342', '-v', 'threadtime', '-s', 'Unity:I']
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
            plan = {'version': 1, 'topology': mode, 'seats': seats, 'venueSha256': '1' * 64}
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
    def test_inventory_uses_only_unique_authorized_adb_transports(self):
        output = (b'List of devices attached\r\n'
                  b'good device product:quest3 transport_id:41\r\n'
                  b'offline offline transport_id:42\r\n'
                  b'pair device transport_id:43\r\n'
                  b'other unauthorized transport_id:43\r\n'
                  b'twice device transport_id:44\r\n'
                  b'twice device transport_id:45\r\n'
                  b'no-id device\r\n'
                  b'bad-fields device transport_id:47 transport_id:broken\r\n'
                  b'huge device transport_id:9223372036854775808\r\n')
        response = subprocess.CompletedProcess(['adb', 'devices', '-l'], 0, stdout=output)
        with patch.object(capture_tool.subprocess, 'run', return_value=response) as run:
            transports = capture_tool.read_adb_transports(['adb'], 2)
        self.assertEqual({'good': '41'}, transports)
        self.assertEqual(['adb', 'devices', '-l'], run.call_args.args[0])
        self.assertEqual(2, run.call_args.kwargs['timeout'])

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
        scope = 'b' * 64
        self.prepare(raw, deviceSerials=['headset-a'])
        with self.assertRaisesRegex(capture_tool.field.EvidenceError, 'differs from the original venue device proof'):
            asyncio.run(capture_tool.capture(self.adb, port, expected, self.output, 10, device_identity=proof,
                                             venue_device=(scope, field.quest_deployment_fingerprint(scope, 'HEADSET-B'))))
        self.assertFalse((self.root / 'pid-count').exists())
        self.prepare(raw, deviceSerials=['headset-a', 'HEADSET-A'])
        report = asyncio.run(capture_tool.capture(self.adb, port, expected, self.output, 10, device_identity=proof,
                                                 venue_device=(scope, field.quest_deployment_fingerprint(scope, 'HEADSET-A'))))
        self.assertTrue(report['complete'])
        self.assertEqual(raw, self.output.read_bytes())
        self.assertEqual('2', (self.root / 'serial-count').read_text())

    def test_bound_capture_requires_original_openxr_process_and_marker_before_ready(self):
        port, expected = capture_tool.read_connection(self.original)
        nonce = 'a1' * 16
        marker = f'VR_QUEST_OPENXR nonce={nonce} loader=1 display=1 input=1'
        original = quest_logcat(self.player_log)
        ready = []

        def capture():
            return asyncio.run(capture_tool.capture(self.adb, port, expected, self.output, 4, ready.append,
                                                   openxr=(7342, nonce)))

        self.prepare((logcat_line(marker) + original).encode(), initialPid='7450')
        with self.assertRaisesRegex(capture_tool.field.EvidenceError, 'process differs from the original OpenXR launch'):
            capture()
        self.assertFalse(self.partial.exists())
        self.assertFalse((self.root / 'logcat-child').exists())

        self.prepare((logcat_line(marker, pid=7450) + original).encode())
        with self.assertRaisesRegex(capture_tool.field.EvidenceError, 'OpenXR launch marker is unavailable'):
            capture()
        self.assertFalse(ready)
        self.partial.unlink()
        first, tail = original.split(logcat_line('VR_CLIENT_CONNECTED id=2'), 1)
        raw = (first + logcat_line(marker) + logcat_line('VR_CLIENT_CONNECTED id=2') + tail).encode()
        self.prepare(raw)
        self.assertTrue(capture()['complete'])
        self.assertEqual([7342], ready)
        self.assertEqual(raw, self.output.read_bytes())

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

    def test_capture_waits_for_the_first_original_connection_before_reporting_ready(self):
        port, admission = capture_tool.read_connection(self.original)
        ready = []

        async def lines():
            yield logcat_line(f'VR_NETWORK_STARTED role=Client started=True background=False port={port}').encode()
            self.assertEqual([], ready, 'Starting the client does not establish a connection')
            yield logcat_line('VR_CLIENT_ADMISSION_REJECTED').encode()
            self.assertEqual([], ready)
            for message in self.player_log.splitlines():
                yield logcat_line(message).encode()
                if message.startswith('VR_CLIENT_CONNECTED '):
                    self.assertEqual([7342], ready)

        child = SimpleNamespace(stdout=SimpleNamespace(readline=lines().__anext__))

        async def collect():
            return await capture_tool.read_capture(child, self.adb, 7342, port, admission, io.BytesIO(),
                                                   asyncio.get_running_loop().time() + 4, ready.append)

        with patch.object(capture_tool, 'quest_pid', return_value=7342):
            self.assertTrue(asyncio.run(collect())['complete'])

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

    def test_capture_never_opens_final_log_for_incremental_writing(self):
        raw = quest_logcat(self.player_log).encode('utf-8')
        self.prepare(raw)
        open_path = Path.open
        final_writes = []

        def observe(path, mode='r', *args, **kwargs):
            handle = open_path(path, mode, *args, **kwargs)
            if path == self.output and any(flag in mode for flag in 'wx+a'):
                final_writes.append(path.stat().st_size)
            return handle

        with patch.object(Path, 'open', observe):
            self.assertTrue(self.capture()['complete'])
        self.assertEqual([], final_writes, 'A consumer could see an incomplete file at the final path')
        self.assertEqual(raw, self.output.read_bytes())
        self.assertFalse(self.partial.exists())

    def test_capture_preserves_competing_final_filename_and_complete_partial(self):
        raw = quest_logcat(self.player_log).encode('utf-8')
        self.prepare(raw)
        port, admission = capture_tool.read_connection(self.original)

        def already_published(_pid):
            with self.output.open('xb') as existing:
                existing.write(b'published by another writer')

        with self.assertRaisesRegex(capture_tool.field.EvidenceError, 'output already exists'):
            asyncio.run(capture_tool.capture(self.adb, port, admission, self.output, 10, already_published))
        self.assertEqual(b'published by another writer', self.output.read_bytes())
        self.assertEqual(raw, self.partial.read_bytes())

    def test_capture_venue_never_opens_final_report_for_incremental_writing(self):
        raw = quest_logcat(self.player_log).encode('utf-8')
        self.prepare(raw)
        port, admission = capture_tool.read_connection(self.original)
        directory = self.root / 'venue'
        report_path = directory / 'capture-report.json'
        plan = {'topology': 'Linked', 'venueSha256': 'a' * 64,
                'seats': [dict(admission, seat=1, port=port, serial='fixture-device')]}
        open_path = Path.open
        final_writes = []

        def observe(path, mode='r', *args, **kwargs):
            handle = open_path(path, mode, *args, **kwargs)
            if path == report_path and any(flag in mode for flag in 'wx+a'):
                final_writes.append(path.stat().st_size)
            return handle

        with (patch.object(Path, 'open', observe), patch.object(capture_tool, 'read_adb_transports'),
              patch.object(capture_tool, 'select_adb_transport', return_value=self.adb)):
            summary = asyncio.run(capture_tool.capture_venue(self.adb, plan, directory, 10))
        self.assertTrue(summary['complete'])
        self.assertEqual([], final_writes, 'A consumer could see an incomplete report at the final path')
        self.assertEqual(hashlib.sha256(raw).hexdigest(), json.loads(report_path.read_bytes())['seats'][0]['sha256'])
        self.assertFalse(list(directory.glob('*.partial')))

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
    def test_quest_link_metrics_verify_original_pid_connection_and_seat_in_both_modes(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, mode, remote=True, quest_per_room=1, room_sizes=(2,) * 5)
                manifest['expectedPlayersPerRoom'] = 2
                manifest['requireQuestLinkMetrics'] = True
                path.write_text(json.dumps(manifest), encoding='utf-8')
                original_logs = []
                for session in manifest['sessions']:
                    port = json.loads((root / session['launcherReport']).read_bytes())['udpBinding']['port']
                    for player in session['players']:
                        if 'logcatPid' not in player:
                            continue
                        source = root / player['log']
                        log, pid = source.read_text(encoding='utf-8'), player['logcatPid']
                        connection, _ = field.quest_client_result(log, pid, port)
                        source.write_text(insert_quest_link_metrics(log, pid, connection), encoding='utf-8')
                        original_logs.append((source, log, pid, connection))
                result = field.verify_venue(path)
                self.assertEqual(5, result['questLinkMetricsVerified'])
                rows = [row for session in result['sessions'] for row in session['questLinkMetrics']]
                self.assertEqual([(room, 2) for room in range(1, 6)], [(r['roomId'], r['seat']) for r in rows])
                self.assertTrue(all((row['replies'], row['timeouts'], row['interrupted'], row['p95RoundTripMs'], row['playerLoopFramesPerSecond'])
                                    == (28, 1, 1, 46, 72) for row in rows))
                self.assertFalse(result['networkCapacityAccepted'])

                if mode == 'Independent':
                    session = manifest['sessions'][0]
                    windows, quest = session['players']
                    command = [sys.executable, str(SCRIPT), '--topology', 'direct-lan', '--server-ip', manifest['serverIps'][0],
                               '--launcher-report', str(root / session['launcherReport']), '--server-log', str(root / session['serverLog']),
                               '--evidence-zip', str(root / session['evidenceZip']), '--player', windows['address'], str(root / windows['log']),
                               '--quest-player', quest['address'], str(root / quest['log']), str(quest['logcatPid']), '--require-quest-link-metrics']
                    cli = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=12)
                    self.assertEqual(0, cli.returncode, cli.stderr)
                    self.assertEqual(rows[:1], json.loads(cli.stdout)['questLinkMetrics'])
                    thresholds = [*command[:-1], '--quest-minimum-replies', '28', '--quest-maximum-p95-ms']
                    accepted = subprocess.run([*thresholds, '46'], capture_output=True, text=True, encoding='utf-8', timeout=12)
                    self.assertEqual(0, accepted.returncode, accepted.stderr)
                    self.assertEqual({'minimumReplies': 28, 'maximumP95RoundTripMs': 46, 'seatsVerified': 1},
                                     json.loads(accepted.stdout)['questLinkCriteria'])
                    rejected = subprocess.run([*thresholds, '45'], capture_output=True, text=True, encoding='utf-8', timeout=12)
                    self.assertEqual(1, rejected.returncode)
                    self.assertIn('Quest link criteria not met at room 1 seat 2', rejected.stderr)

                source, log, pid, connection = original_logs[0]
                for changes, reason in [({'process_id': pid + 1}, 'original graphical client process'),
                                        ({'report_connection': 1}, 'original graphical client process'),
                                        ({'frame_pid': pid + 1}, 'Missing complete Quest link report'),
                                        ({'drop': True}, 'missing, reordered or repeated fragments')]:
                    with self.subTest(changes=changes):
                        source.write_text(insert_quest_link_metrics(log, pid, connection, **changes), encoding='utf-8')
                        with self.assertRaisesRegex(field.EvidenceError, f'room 1 seat 2: .*{reason}'):
                            field.verify_venue(path)
                source.write_text(log, encoding='utf-8')
                manifest['requireQuestLinkMetrics'] = False
                path.write_text(json.dumps(manifest), encoding='utf-8')
                self.assertNotIn('questLinkMetricsVerified', field.verify_venue(path))

    def staged_batch(self, root, mode, count, id_offset, minutes_after, *, remote=False, tracked_fire=False,
                     missing_shot=False, runtime='Test OpenXR Runtime', windows_inbox=False, windows_links=False,
                     quest_links=False, server_digest=None):
        root.mkdir()
        path, manifest, closure = venue_fixture(root, mode, remote=remote, with_journals=True, quest_per_room=int(quest_links),
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
        release_path = self.add_shared_release(root, manifest, int(quest_links))
        if quest_links:
            for entry in manifest['sessions']:
                port = json.loads((root / entry['launcherReport']).read_bytes())['udpBinding']['port']
                for player in entry['players']:
                    if 'logcatPid' in player:
                        path_to_log, pid = root / player['log'], player['logcatPid']
                        log = path_to_log.read_text(encoding='utf-8')
                        connection, _ = field.quest_client_result(log, pid, port)
                        path_to_log.write_text(insert_quest_link_metrics(log, pid, connection), encoding='utf-8')
        if windows_links:
            self.add_windows_links(root, manifest)
        if server_digest is not None:
            release = json.loads(release_path.read_bytes())
            release['windows']['serverManifestSha256'] = server_digest
            release_path.write_text(json.dumps(release), encoding='utf-8')
            terminal_path, terminal, _ = self.terminal_venue_fixture(root, manifest, closure)
            terminal['serverManifestSha256'] = server_digest
            terminal['venueReleaseReportSha256'] = hashlib.sha256(release_path.read_bytes()).hexdigest()
            terminal_path.write_text(json.dumps(terminal), encoding='utf-8')
        if count != 5:
            manifest['expectedPlayersPerRoom'] = count
        if windows_inbox:
            manifest = self.windows_inbox_fixture(root, manifest)
        elif mode == 'Linked':
            manifest = self.pack_venue(root, manifest)
            if not manifest['windowsPlayers']:
                del manifest['windowsPlayers']
        path.write_text(json.dumps(manifest), encoding='utf-8')
        return str(path.relative_to(root.parent))

    def staged_plan(self, root, *, remote=False, tracked_fire=False, windows_inbox=False, windows_links=False, quest_links=False):
        names = [self.staged_batch(root / f'{count}-{mode}', mode, count, index * 10000, minutes, remote=remote,
                                   tracked_fire=tracked_fire, windows_inbox=windows_inbox and count == 1,
                                   windows_links=windows_links, quest_links=quest_links)
                 for minutes, count in enumerate((1, 2, 5), 1)
                 for index, mode in ((minutes * 2, 'Independent'), (minutes * 2 + 1, 'Linked'))]
        return {'version': 1, 'topology': 'direct-lan' if remote else 'same-host',
                'minimumConcurrentMilliseconds': 2000, 'venueManifests': names}

    def test_staged_quest_openxr_requires_original_launch_proof_in_every_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.staged_plan(root, remote=True, quest_links=True)
            paths = [root / name for name in plan['venueManifests']]
            stamps, logs = [], []
            for path in paths:
                batch = json.loads(path.read_bytes())
                batch['requireQuestOpenXR'] = False  # Local configuration cannot relax the staged requirement.
                path.write_text(json.dumps(batch), encoding='utf-8')
                release_path = path.with_name('release.json')
                release = json.loads(release_path.read_bytes())
                release['quest']['versionCode'] = 76
                release_path.write_text(json.dumps(release), encoding='utf-8')
                report_path = path.with_name('deployment.json')
                report = json.loads(report_path.read_bytes())
                rows = {row['playerId']: row for row in report['devices']}
                for entry in batch['sessions']:
                    port = json.loads(path.with_name(entry['launcherReport']).read_bytes())['udpBinding']['port']
                    for proof in entry.get('players', ()):
                        if 'logcatPid' not in proof:
                            continue
                        log_path, pid = path.with_name(proof['log']), proof['logcatPid']
                        raw = log_path.read_text(encoding='utf-8')
                        _, result = field.quest_client_result(raw, pid, port)
                        row = rows[result['playerId']]
                        nonce = f"{row['roomId']:032x}"
                        marker = logcat_line(f'VR_QUEST_OPENXR nonce={nonce} loader=1 display=1 input=1', pid)
                        row.update(versionCode=76, openXR={'processId': pid, 'nonce': nonce})
                        log_path.write_text(marker + raw, encoding='utf-8')
                        logs.append((log_path, raw, row['roomId'], row['seat']))
                report.update(requireOpenXR=True, expectedVersionCode=76)
                report_path.write_text(json.dumps(report), encoding='utf-8')
                stamps.append(report_path)

            path = root / 'stages.json'
            made = subprocess.run([sys.executable, str(SCRIPT.with_name('prepare-venue-stages.py')),
                '--topology', 'direct-lan', '--minimum-concurrent-ms', '2000', '--require-quest-openxr',
                '--output', str(path), *map(str, paths)], capture_output=True, timeout=30)
            self.assertEqual(0, made.returncode, made.stderr)
            command = [sys.executable, str(SCRIPT), '--venue-stages', str(path)]
            accepted = json.loads(subprocess.check_output(command, timeout=30))
            self.assertIs(accepted['requireQuestOpenXR'], True)
            self.assertEqual(80, accepted['serverAcknowledgements'])
            self.assertEqual([5] * 6, [row['questOpenXR']['verifiedSeats'] for row in accepted['stages']])
            self.assertFalse(accepted['physicalHostsVerified'])

            value = json.loads(stamps[0].read_bytes())
            value['requireOpenXR'] = False
            for row in value['devices']:
                row.pop('openXR')
            stamps[0].write_text(json.dumps(value), encoding='utf-8')
            invalid_log, raw, room, seat = logs[5]
            invalid_log.write_text(raw, encoding='utf-8')
            inspected = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True, timeout=30)
            self.assertEqual(1, inspected.returncode, inspected.stderr)
            absent, invalid = json.loads(inspected.stdout)['issues']
            self.assertEqual([1], absent['entries'])
            self.assertEqual({'expectedSeats': 5, 'verifiedSeats': 0, 'invalidReports': [],
                              'missingSeats': [{'roomId': n, 'seat': 1} for n in range(1, 6)]}, absent['questOpenXR'])
            self.assertEqual([2], invalid['entries'])
            self.assertEqual(4, invalid['questOpenXR']['verifiedSeats'])
            self.assertEqual([{'roomId': room, 'seat': seat, 'reason': 'Original Quest OpenXR launch marker must precede the final result'}],
                             invalid['questOpenXR']['invalidReports'])
            refused = subprocess.run(command, capture_output=True, timeout=30)
            self.assertEqual(1, refused.returncode)
            self.assertFalse(refused.stdout)

    def test_required_quest_openxr_does_not_accept_an_all_windows_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            path, manifest, _ = venue_fixture(Path(directory), 'Independent')
            self.assertNotIn('questOpenXR', field.verify_venue(path))
            manifest['requireQuestOpenXR'] = 'true'
            path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'must be a boolean'):
                field.verify_venue(path)
            manifest['requireQuestOpenXR'] = True
            path.write_text(json.dumps(manifest), encoding='utf-8')
            refused = subprocess.run([sys.executable, str(SCRIPT), '--venue-manifest', str(path)],
                                     capture_output=True, timeout=30)
            self.assertEqual(1, refused.returncode)
            self.assertEqual({'expectedSeats': 0, 'verifiedSeats': 0, 'missingSeats': [], 'invalidReports': []},
                             json.loads(refused.stdout)['questOpenXR'])

    def test_verified_start_reports_each_original_digest_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            terminal_path = root / 'venue-final.json'
            readiness_path = root / 'venue-udp.json'
            ready_path = root / 'venue-ready.json'
            receipt_path = root / 'verified-start.json'
            checked = '2026-11-09T00:00:00+00:00'
            readiness_path.write_text(json.dumps({'scope': 'venue-udp-preflight-only', 'complete': True,
                'mode': 'Linked', 'launchBinding': {}, 'checkedAtUtc': checked}), encoding='utf-8')
            ready_path.write_text(json.dumps({'schemaVersion': 1, 'status': 'venue-ready', 'topology': 'Linked',
                'instanceId': id_for(1), 'servers': []}), encoding='utf-8')
            terminal = {'sha256': 'a' * 64, 'instanceId': id_for(1), 'launchId': id_for(2)}
            receipt = {'version': 1, 'scope': 'verified-windows-venue-start', 'mode': 'Linked',
                       'checkedAtUtc': checked, 'terminalSha256': terminal['sha256'], 'readyReport': ready_path.name,
                       'readinessSha256': hashlib.sha256(readiness_path.read_bytes()).hexdigest(),
                       'readySha256': hashlib.sha256(ready_path.read_bytes()).hexdigest()}
            for key, kind, original in (('terminalSha256', 'venueLauncherReport', terminal_path),
                                        ('readinessSha256', 'udpPreflightBatch', readiness_path),
                                        ('readySha256', 'windowsReadyReport', ready_path)):
                with self.subTest(kind=kind):
                    receipt_path.write_text(json.dumps(receipt | {key: '0' * 64}), encoding='utf-8')
                    with self.assertRaises(field.EvidenceDigestMismatch) as raised:
                        field.read_verified_venue_start(receipt_path, readiness_path, terminal, {}, 'Linked',
                                                       terminal_path=terminal_path)
                    self.assertEqual({'kind': kind, 'name': original.name, 'status': 'sha256-mismatch'},
                                     raised.exception.evidence)

    def test_verified_start_compares_server_release_in_ready_terminal_and_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preview, ready, terminal_path, readiness, receipt_path = (root / f'{name}.json' for name in
                ('preview', 'ready', 'terminal', 'readiness', 'receipt'))
            expected = '1' * 64
            checked = '2026-11-09T00:00:00+00:00'
            terminal = {'sha256': 'b' * 64, 'instanceId': id_for(1), 'launchId': id_for(2), 'serverManifestSha256': expected}

            def write(path, value):
                raw = json.dumps(value).encode()
                path.write_bytes(raw)
                return hashlib.sha256(raw).hexdigest()

            def verify(ready_digest, preview_digest, *, ready_report=None, preview_report=None):
                preview_hash = write(preview, {'serverManifestSha256': preview_digest,
                    **({'venueReleaseReportSha256': preview_report} if preview_report is not None else {})})
                ready_hash = write(ready, {'schemaVersion': 1, 'status': 'venue-ready', 'topology': 'Linked',
                    'instanceId': id_for(1), 'servers': [],
                    **({'serverManifestSha256': ready_digest} if ready_digest is not None else {}),
                    **({'venueReleaseReportSha256': ready_report} if ready_report is not None else {})})
                readiness_hash = write(readiness, {'scope': 'venue-udp-preflight-only', 'complete': True, 'mode': 'Linked',
                    'checkedAtUtc': checked, 'launchBinding': {'preview': preview.name, 'previewSha256': preview_hash}})
                write(receipt_path, {'version': 1, 'scope': 'verified-windows-venue-start', 'mode': 'Linked',
                    'checkedAtUtc': checked, 'terminalSha256': terminal['sha256'], 'readyReport': ready.name,
                    'readinessSha256': readiness_hash, 'readySha256': ready_hash})
                return field.read_verified_venue_start(receipt_path, readiness, terminal, {}, 'Linked',
                                                       terminal_path=terminal_path)

            self.assertEqual(id_for(2), verify(expected, expected)['launchId'])
            with self.assertRaisesRegex(field.EvidenceError, 'ready and terminal reports do not share'):
                verify('2' * 64, expected)
            with self.assertRaisesRegex(field.EvidenceError, 'launch preview does not match'):
                verify(expected, '3' * 64)

            report_digest = '4' * 64
            terminal['venueReleaseReportSha256'] = report_digest
            self.assertEqual(id_for(2), verify(expected, expected, ready_report=report_digest,
                                               preview_report=report_digest)['launchId'])
            with self.assertRaisesRegex(field.EvidenceError, 'preview and terminal reports used different original'):
                verify(expected, expected, ready_report=report_digest, preview_report='5' * 64)
            terminal.pop('venueReleaseReportSha256')
            terminal.pop('serverManifestSha256')
            with self.assertRaisesRegex(field.EvidenceError, 'launch preview does not match'):
                verify(None, expected, preview_report=report_digest)

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

    def test_prepare_staged_venue_plan_from_unordered_batch_manifests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.staged_plan(root, windows_inbox=True, windows_links=True)
            names = [root / name for name in plan['venueManifests']]
            plan_folder = root / 'operator plan'
            plan_folder.mkdir()
            output = plan_folder / 'stages.json'
            command = [sys.executable, str(SCRIPT.with_name('prepare-venue-stages.py')),
                       '--topology', 'same-host', '--minimum-concurrent-ms', '2000',
                       '--windows-minimum-replies', '28', '--windows-maximum-p95-ms', '14']

            def prepare(paths=names[::-1], options=command, target=output):
                return subprocess.run([*options, '--output', str(target),
                                       *(str(path) for path in paths)], capture_output=True)

            inbox = names[0].parent / 'returned'
            archive = sorted(inbox.glob('*.ZIP'))[0]
            original_zip = archive.read_bytes()
            archive.unlink()
            result = prepare()
            self.assertEqual(0, result.returncode, result.stderr.decode())
            self.assertEqual({'prepared': True, 'batches': 6}, json.loads(result.stdout))
            original = output.read_bytes()
            generated = json.loads(original)
            self.assertEqual(names, [(output.parent / name).resolve() for name in generated['venueManifests']])
            self.assertTrue(all(not Path(name).is_absolute() for name in generated['venueManifests']))
            self.assertEqual([{'mode': mode, 'players': size} for size in (5, 10, 25)
                              for mode in ('Independent', 'Linked')], generated['expectedStages'])
            self.assertEqual({'minimumReplies': 28, 'maximumP95RoundTripMs': 14}, generated['windowsLinkCriteria'])
            inspection = field.verify_venue_stages(output, inspect=True)
            self.assertFalse(inspection['complete'])
            self.assertEqual([[1]], [row['entries'] for row in inspection['issues']])
            self.assertEqual(4, inspection['issues'][0]['windowsInbox']['receivedWindowsSeats'])
            self.assertEqual(generated['expectedStages'][0], inspection['entries'][0]['expectedStage'])
            archive.write_bytes(original_zip)
            accepted = field.verify_venue_stages(output)
            self.assertEqual(80, accepted['serverAcknowledgements'])
            self.assertNotIn('expectedStages', accepted)

            swapped = plan_folder / 'swapped.json'
            references = generated['venueManifests'].copy()
            references[0], references[1] = references[1], references[0]
            references[-1] = 'missing folder/venue.json'
            swapped.write_text(json.dumps(dict(generated, venueManifests=references)), encoding='utf-8')
            inspection = field.verify_venue_stages(swapped, inspect=True)
            self.assertEqual([[1], [2], [6]], [row['entries'] for row in inspection['issues']])
            self.assertEqual(generated['expectedStages'][0], inspection['issues'][0]['expectedStage'])
            self.assertEqual(generated['expectedStages'][1], inspection['issues'][0]['observedStage'])
            self.assertEqual(generated['expectedStages'][-1], inspection['entries'][-1]['expectedStage'])
            self.assertEqual({'kind': 'venueManifest', 'name': 'venue.json'}, inspection['issues'][-1]['missingFile'])
            self.assertNotIn('missing folder', json.dumps(inspection))
            with self.assertRaisesRegex(field.EvidenceError, 'Venue manifest entry 1: expected Independent with 5'):
                field.verify_venue_stages(swapped)

            for invalid in (None, generated['expectedStages'][:-1],
                            [generated['expectedStages'][0]] * 6):
                swapped.write_text(json.dumps(dict(generated, expectedStages=invalid)), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'Expected staged venue entries'):
                    field.verify_venue_stages(swapped, inspect=True)

            self.assertNotEqual(0, prepare().returncode)
            self.assertEqual(original, output.read_bytes())
            rejected = plan_folder / 'rejected.json'
            for paths, options, reason in (
                (names[:-1] + [names[0]], command, b'paths must be distinct'),
                (names, command[:3] + ['direct-lan'] + command[4:], b'topology differs'),
                (names, command[:-2], b'Provide both Windows link criteria'),
            ):
                result = prepare(paths, options, rejected)
                self.assertNotEqual(0, result.returncode)
                self.assertIn(reason, result.stderr)
                self.assertFalse(rejected.exists())
            wrong = names[-1]
            batch = json.loads(wrong.read_bytes())
            wrong.write_text(json.dumps(dict(batch, expectedPlayersPerRoom=2)), encoding='utf-8')
            result = prepare(target=rejected)
            self.assertEqual(1, result.returncode)
            self.assertIn(b'each mode and seat count exactly once', result.stderr)
            wrong.write_text(json.dumps(batch), encoding='utf-8')
            release = wrong.parent / batch['venueReleaseReport']
            release.write_bytes(release.read_bytes() + b'\n')
            result = prepare(target=rejected)
            self.assertEqual(1, result.returncode)
            self.assertIn(b'same original verified release', result.stderr)
            self.assertFalse(rejected.exists())

    def test_staged_server_release_policy_reports_missing_and_different_originals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            digest = 'a' * 64
            names = [self.staged_batch(root / f'{size}-{mode}', mode, size // 5, index * 10000, index,
                                       server_digest=digest)
                     for index, (mode, size) in enumerate(field.VENUE_STAGE_KEYS, 1)]
            manifests = [root / name for name in names]
            plan_path = root / 'stages.json'
            built = subprocess.run([sys.executable, str(SCRIPT.with_name('prepare-venue-stages.py')),
                '--topology', 'same-host', '--minimum-concurrent-ms', '2000', '--require-server-release',
                '--output', str(plan_path), *map(str, reversed(manifests))], capture_output=True, timeout=30)
            self.assertEqual(0, built.returncode, built.stderr)
            plan = json.loads(plan_path.read_bytes())
            self.assertIs(plan['requireServerRelease'], True)
            result = field.verify_venue_stages(plan_path)
            self.assertIs(result['requireServerRelease'], True)
            self.assertEqual(80, result['serverAcknowledgements'])
            release_hash = hashlib.sha256(manifests[0].with_name('release.json').read_bytes()).hexdigest()
            releases = [{'serverManifestSha256': digest, 'venueReleaseReportSha256': release_hash,
                         'sessionsVerified': 5 if mode == 'Independent' else 1}
                        for mode, _ in field.VENUE_STAGE_KEYS]
            self.assertEqual(releases, [stage['serverRelease'] for stage in result['stages']])
            inspected = field.verify_venue_stages(plan_path, inspect=True)
            self.assertIs(inspected['complete'], True)
            self.assertEqual(releases, [entry['serverRelease'] for entry in inspected['entries']])

            terminals = [path.with_name('venue-launcher.json') for path in manifests]
            missing, different = (json.loads(terminals[index].read_bytes()) for index in (1, 4))
            missing.pop('serverManifestSha256')
            missing.pop('venueReleaseReportSha256')
            terminals[1].write_text(json.dumps(missing), encoding='utf-8')
            terminals[4].write_text(json.dumps(dict(different, serverManifestSha256='b' * 64)), encoding='utf-8')
            command = [sys.executable, str(SCRIPT), '--venue-stages', str(plan_path)]
            rejected = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True, timeout=30)
            self.assertEqual(1, rejected.returncode, rejected.stderr)
            inspected = json.loads(rejected.stdout)
            self.assertIs(inspected['requireServerRelease'], True)
            self.assertEqual([[2], [5]], [row['entries'] for row in inspected['issues']])
            self.assertEqual([{'kind': 'venueLauncherReport', 'name': 'venue-launcher.json', 'status': status}
                              for status in ('missing-server-manifest', 'server-manifest-mismatch')],
                             [row['evidenceMismatch'] for row in inspected['issues']])
            self.assertEqual([plan['expectedStages'][index] for index in (1, 4)], inspected['missingStages'])
            self.assertEqual(['verified', 'needs-evidence', 'verified', 'verified', 'needs-evidence', 'verified'],
                             [entry['status'] for entry in inspected['entries']])
            rejected = subprocess.run(command, capture_output=True, timeout=30)
            self.assertEqual(1, rejected.returncode)
            self.assertIn(b'original release-bound terminal venue launch report', rejected.stderr)

            terminals[4].write_text(json.dumps(different), encoding='utf-8')
            release = manifests[4].with_name('release.json')
            original_release = release.read_bytes()
            release.write_bytes(original_release + b'\n')
            inspected = field.verify_venue_stages(plan_path, inspect=True)
            self.assertEqual([[2], [5]], [row['entries'] for row in inspected['issues']])
            self.assertEqual({'kind': 'venueReleaseReport', 'name': release.name, 'status': 'venue-release-report-mismatch'},
                             inspected['issues'][1]['evidenceMismatch'])
            release.write_bytes(original_release)
            plan_path.write_text(json.dumps(dict(plan, requireServerRelease=False)), encoding='utf-8')
            self.assertNotIn('serverRelease', field.verify_venue_stages(plan_path)['stages'][1])
            single = json.loads(manifests[1].read_bytes())
            manifests[1].write_text(json.dumps(dict(single, requireServerRelease=True)), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'original release-bound terminal venue launch report'):
                field.verify_venue_stages(plan_path)

    def test_complete_staged_venue_release_pins_the_report_and_requires_every_seat(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [root / self.staged_batch(root / f'{players}-{mode}', mode, players // 5, index * 10000, index,
                                              remote=True, quest_links=True, server_digest='a' * 64)
                     for index, (mode, players) in enumerate(field.VENUE_STAGE_KEYS, 1)]
            release_paths, windows_reports = [], []
            for path in paths:
                batch = json.loads(path.read_bytes())
                release = path.parent / batch['venueReleaseReport']
                release_paths.append(release)
                stamp = hashlib.sha256(release.read_bytes()).hexdigest()
                seats = [*batch.get('windowsPlayers', ()), *(seat for row in batch['sessions']
                         for seat in row.get('players', ()) if 'logcatPid' not in seat)]
                windows_reports.append([path.parent / seat['launcherReport'] for seat in seats])
                for report in [*windows_reports[-1], path.with_name('deployment.json')]:
                    value = json.loads(report.read_bytes())
                    report.write_text(json.dumps(dict(value, venueReleaseReportSha256=stamp)), encoding='utf-8')

            path = root / 'stages.json'
            built = subprocess.run([sys.executable, str(SCRIPT.with_name('prepare-venue-stages.py')),
                '--topology', 'direct-lan', '--minimum-concurrent-ms', '2000', '--require-complete-venue-release',
                '--output', str(path), *map(str, reversed(paths))], capture_output=True, timeout=30)
            self.assertEqual(0, built.returncode, built.stderr)
            plan = json.loads(path.read_bytes())
            release_hash = hashlib.sha256(release_paths[0].read_bytes()).hexdigest()
            self.assertIs(plan['requireCompleteVenueRelease'], True)
            self.assertEqual(release_hash, plan['venueReleaseReportSha256'])
            command = [sys.executable, str(SCRIPT), '--venue-stages', str(path)]
            result = json.loads(subprocess.check_output(command, timeout=30))
            self.assertEqual(80, result['serverAcknowledgements'])
            self.assertEqual(release_hash, result['venueReleaseSha256'])
            self.assertEqual(18, sum(stage['serverRelease']['sessionsVerified'] for stage in result['stages']))
            self.assertEqual(30, sum(stage['questRelease']['releaseReportSeatsVerified'] for stage in result['stages']))
            self.assertEqual(50, sum(stage.get('windowsRelease', {}).get('releaseReportSeatsVerified', 0)
                                     for stage in result['stages']))

            affected = paths[2]
            originals = {source: source.read_bytes() for source in (affected.with_name('venue-launcher.json'),
                         windows_reports[2][0], affected.with_name('deployment.json'))}
            for source, raw in originals.items():
                value = json.loads(raw)
                value.pop('venueReleaseReportSha256')
                source.write_text(json.dumps(value), encoding='utf-8')
            intake = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True, timeout=30)
            self.assertEqual(1, intake.returncode, intake.stderr)
            [issue] = json.loads(intake.stdout)['issues']
            self.assertEqual([3], issue['entries'])
            self.assertEqual({'venueReleaseReportSha256': release_hash,
                'server': {'expectedSessions': 5, 'verifiedSessions': 0, 'missingRoomGroups': [[room] for room in range(1, 6)]},
                'windows': {'expectedSeats': 5, 'verifiedSeats': 4, 'missingSeats': [{'roomId': 1, 'seat': 1}]},
                'quest': {'expectedSeats': 5, 'verifiedSeats': 0, 'missingSeats': [{'roomId': room, 'seat': 2} for room in range(1, 6)]},
            }, issue['venueReleaseCoverage'])
            refused = subprocess.run(command, capture_output=True, timeout=30)
            self.assertEqual(1, refused.returncode)
            self.assertIn(b'Original venue release report digest is missing', refused.stderr)
            for source, raw in originals.items():
                source.write_bytes(raw)

            for release in release_paths:
                release.write_bytes(release.read_bytes() + b'\n')
            changed = field.verify_venue_stages(path, inspect=True)
            self.assertEqual([[index] for index in range(1, 7)], [issue['entries'] for issue in changed['issues']])
            self.assertTrue(all(issue['evidenceMismatch'] == {'kind': 'venueReleaseReport', 'name': 'release.json',
                'status': 'venue-release-report-mismatch'} for issue in changed['issues']))
            path.write_text(json.dumps({**plan, 'venueReleaseReportSha256': None}), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'requires a pinned original release report digest'):
                field.verify_venue_stages(path, inspect=True)

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
            self.assertEqual({'kind': 'venueManifest', 'name': Path(names[1]).name}, inspection['issues'][0]['missingFile'])
            self.assertEqual([{'mode': 'Linked', 'players': 5}, {'mode': 'Independent', 'players': 10},
                              {'mode': 'Linked', 'players': 10}], inspection['missingStages'])
            self.assertNotIn(str(root), result.stdout.decode())

            document = json.loads((root / names[4]).read_bytes())
            document['sessions'][0]['worldJournal'] = str(root / 'private-directory' / 'room-01.worldlog')
            document['sessions'][2]['serverLog'] = str(root / 'other-private-directory' / 'room-03-server.log')
            (root / names[4]).write_text(json.dumps(document), encoding='utf-8')
            inspection = field.verify_venue_stages(path, inspect=True)
            self.assertEqual({'entries': [5], 'reason': 'Venue manifest entry 5: missing original evidence file',
                              'missingFile': {'kind': 'worldJournal', 'name': 'room-01.worldlog'},
                              'missingFiles': [
                                  {'kind': 'worldJournal', 'name': 'room-01.worldlog', 'sessionEntry': 1, 'roomIds': [1]},
                                  {'kind': 'serverLog', 'name': 'room-03-server.log', 'sessionEntry': 3, 'roomIds': [3]}
                              ]}, inspection['issues'][-1])
            self.assertNotIn('private-directory', json.dumps(inspection))

    def test_staged_inspection_lists_missing_player_originals_without_guessing_seats(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.staged_plan(root, windows_links=True)
            plan_path = root / 'stages.json'
            plan_path.write_text(json.dumps(plan), encoding='utf-8')
            before = field.verify_venue_stages(plan_path)
            independent, linked = (root / name for name in plan['venueManifests'][:2])
            originals = {path: path.read_bytes() for path in (independent, linked)}
            first, second = (json.loads(raw) for raw in originals.values())
            windows = first['sessions'][0]['players'][0]
            windows['launcherReport'] = 'private-folder/missing-launch.json'
            windows['linkMetrics'] = 'private-folder/missing-metrics.json'
            first['sessions'][2]['players'][0] = {
                'address': '127.0.0.1', 'logcatPid': 7342, 'log': 'private-folder/missing-quest.log'}
            second['windowsPlayers'][1] = {'address': '127.0.0.1', 'evidenceZip': 'private-folder/missing-player.zip'}
            independent.write_text(json.dumps(first), encoding='utf-8')
            linked.write_text(json.dumps(second), encoding='utf-8')

            command = [sys.executable, str(SCRIPT), '--venue-stages', str(plan_path)]
            inspected = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True)
            self.assertEqual(1, inspected.returncode, inspected.stderr)
            self.assertFalse(inspected.stderr)
            report = json.loads(inspected.stdout)
            self.assertEqual([[1], [2]], [issue['entries'] for issue in report['issues']])
            windows_location = {'sessionEntry': 1, 'playerEntry': 1, 'roomIds': [1], 'roomId': 1, 'seat': 1}
            self.assertEqual([
                {'kind': 'playerLauncherReport', 'name': 'missing-launch.json', **windows_location},
                {'kind': 'playerLinkMetrics', 'name': 'missing-metrics.json', **windows_location},
                {'kind': 'questLogcat', 'name': 'missing-quest.log', 'sessionEntry': 3, 'playerEntry': 1, 'roomIds': [3]},
            ], report['issues'][0]['missingFiles'])
            self.assertEqual([{'kind': 'playerEvidenceZip', 'name': 'missing-player.zip', 'playerEntry': 2}],
                             report['issues'][1]['missingFiles'])
            self.assertNotIn(b'private-folder', inspected.stdout)
            self.assertNotIn(b'127.0.0.1', inspected.stdout)
            rejected = subprocess.run(command, capture_output=True)
            self.assertEqual(1, rejected.returncode)
            self.assertFalse(rejected.stdout)
            for path, raw in originals.items():
                path.write_bytes(raw)
            self.assertEqual(before, field.verify_venue_stages(plan_path))

    def test_staged_inspection_locates_incomplete_venue_and_quest_udp_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.staged_plan(root)
            plan_path = root / 'stages.json'
            plan_path.write_text(json.dumps(plan), encoding='utf-8')
            first, second = (root / name for name in plan['venueManifests'][:2])
            originals = {path: path.read_bytes() for path in (first, second)}
            venue_groups = [{'roomIds': [room], 'complete': room != 5,
                             'sources': [{'seats': [{'roomId': room, 'seat': 1}],
                                          'status': 'verified' if room != 5 else 'invalid-or-expired'}]}
                            for room in range(1, 6)]
            venue = {'version': 1, 'scope': 'venue-udp-preflight-only', 'mode': 'Independent', 'complete': False,
                     'groups': venue_groups, 'expectedSources': 5, 'verifiedSources': 4, 'unmatchedPairs': 1,
                     'unreadablePairs': 0, 'inbox': {'issues': [{'files': ['private-file.json']},
                        {'status': 'missing-counterpart', 'files': ['private-file.json'],
                         'seats': [{'roomId': 5, 'seat': 1}], 'missingRole': 'probe'}]},
                     'launcherPreview': {'complete': True}, 'launchBinding': {'complete': True}}
            quest = {'version': 1, 'scope': 'quest-udp-preflight-only', 'mode': 'Linked', 'complete': False,
                     'groups': [{'roomIds': [1, 2, 3, 4, 5], 'complete': False, 'seats': [
                         {'roomId': 1, 'seat': 1, 'stage': 'verified', 'complete': True, 'listener': 'private-file.json'},
                         {'roomId': 3, 'seat': 1, 'stage': 'device', 'complete': False}]}],
                     'expectedSeats': 2, 'verifiedSeats': 1}
            for path, evidence in ((first, venue), (second, quest)):
                report = path.parent / 'udp.json'
                report.write_text(json.dumps(evidence), encoding='utf-8')
                manifest = json.loads(originals[path])
                manifest['udpPreflightBatch' if path == first else 'udpPreflightBatches'] = (
                    report.name if path == first else [report.name, 'private-directory/missing-quest-udp.json'])
                path.write_text(json.dumps(manifest), encoding='utf-8')
            command = [sys.executable, str(SCRIPT), '--venue-stages', str(plan_path)]
            result = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True)
            self.assertEqual(1, result.returncode, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual([[1], [2]], [issue['entries'] for issue in report['issues']])
            self.assertEqual([{'roomId': 5, 'seat': 1, 'status': 'invalid-or-expired'}],
                             report['issues'][0]['udpPreflight'][0]['pendingSeats'])
            self.assertEqual(2, report['issues'][0]['udpPreflight'][0]['inboxIssues'])
            self.assertEqual([{'status': 'missing-counterpart', 'seats': [{'roomId': 5, 'seat': 1}], 'missingRole': 'probe'}],
                             report['issues'][0]['udpPreflight'][0]['inboxSeatIssues'])
            self.assertEqual([{'roomId': 3, 'seat': 1, 'status': 'device'}], report['issues'][1]['udpPreflight'][0]['pendingSeats'])
            self.assertEqual({'report': 2, 'name': 'missing-quest-udp.json', 'status': 'missing-report'},
                             report['issues'][1]['udpPreflight'][1])
            self.assertNotIn(b'private-file.json', result.stdout)
            self.assertNotIn(b'private-directory', result.stdout)
            self.assertNotIn(str(root).encode(), result.stdout)
            rejected = subprocess.run(command, capture_output=True)
            self.assertEqual(1, rejected.returncode)
            self.assertIn(b'Provide a complete UDP preflight batch', rejected.stderr)

            source = venue['groups'][-1]['sources'][0]
            for status, details in (
                    ('invalid-or-expired', {'reason': 'changed-original'}),
                    ('invalid-or-expired', {'reason': 'expired'}),
                    ('missing', {'reason': 'unreadable-original', 'missingRole': 'listener'}),
                    ('missing', {'reason': 'unreadable-original', 'missingRole': 'probe'})):
                with self.subTest(status=status, details=details):
                    venue['groups'][-1]['sources'][0] = {**source, 'status': status, **details}
                    (first.parent / 'udp.json').write_text(json.dumps(venue), encoding='utf-8')
                    checked = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True)
                    self.assertEqual(1, checked.returncode, checked.stderr)
                    self.assertEqual([{'roomId': 5, 'seat': 1, 'status': status, **details}],
                                     json.loads(checked.stdout)['issues'][0]['udpPreflight'][0]['pendingSeats'])
                    self.assertNotIn(b'private-file.json', checked.stdout)
            for details in ({'reason': 'private-directory/listener.ndjson'},
                            {'reason': ['changed-original']},
                            {'reason': 'changed-original', 'missingRole': 'probe'},
                            {'reason': 'unreadable-original'}):
                with self.subTest(invalid_details=details):
                    venue['groups'][-1]['sources'][0] = {**source, **details}
                    (first.parent / 'udp.json').write_text(json.dumps(venue), encoding='utf-8')
                    checked = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True)
                    self.assertEqual(1, checked.returncode, checked.stderr)
                    issue = json.loads(checked.stdout)['issues'][0]
                    self.assertNotIn('udpPreflight', issue)
                    self.assertIn('Invalid', issue['reason'])
                    self.assertNotIn(b'private-directory/listener.ndjson', checked.stdout)
            venue['groups'][-1]['sources'][0] = source
            venue['inbox']['issues'][1]['seats'].append({'roomId': 4, 'seat': 1})
            (first.parent / 'udp.json').write_text(json.dumps(venue), encoding='utf-8')
            bad_inbox = field.verify_venue_stages(plan_path, inspect=True)['issues'][0]
            self.assertIn('does not match an original source', bad_inbox['reason'])

            venue['groups'][-1]['complete'] = True
            venue['groups'][-1]['sources'][0]['status'] = 'verified'
            venue.update(verifiedSources=5, unmatchedPairs=0, launchBinding={'complete': False})
            venue.pop('inbox')
            (first.parent / 'udp.json').write_text(json.dumps(venue), encoding='utf-8')
            only_binding = field.verify_venue_stages(plan_path, inspect=True)['issues'][0]['udpPreflight'][0]
            self.assertFalse(only_binding['launchBindingComplete'])
            self.assertEqual([], only_binding['pendingSeats'])

            quest['groups'][0]['seats'][1]['roomId'] = 1
            (second.parent / 'udp.json').write_text(json.dumps(quest), encoding='utf-8')
            bad = field.verify_venue_stages(plan_path, inspect=True)['issues'][1]
            self.assertIn('repeats a seat', bad['reason'])
            self.assertNotIn('udpPreflight', bad)
            for path, original in originals.items():
                path.write_bytes(original)
            self.assertEqual(80, field.verify_venue_stages(plan_path)['serverAcknowledgements'])

    def test_staged_inspection_lists_windows_inbox_seats_and_files_by_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.staged_plan(root, windows_inbox=True)
            names = plan['venueManifests']
            path = root / 'stages.json'
            path.write_text(json.dumps(plan), encoding='utf-8')
            command = [sys.executable, str(SCRIPT), '--venue-stages', str(path)]

            first, second = ((root / name).parent / 'returned' for name in names[:2])
            original = first / 'box-00.ZIP'
            missing_bytes = original.read_bytes()
            original.unlink()
            foreign = second / 'wrong-batch.ZIP'
            foreign.write_bytes(missing_bytes)

            result = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True)
            self.assertEqual(1, result.returncode, result.stderr)
            self.assertFalse(result.stderr)
            inspection = json.loads(result.stdout)
            self.assertEqual(['needs-evidence', 'needs-evidence', *(['verified'] * 4)],
                             [row['status'] for row in inspection['entries']])
            first_issue, second_issue = inspection['issues']
            self.assertEqual([1], first_issue['entries'])
            self.assertEqual([2], second_issue['entries'])
            first_report, second_report = first_issue['windowsInbox'], second_issue['windowsInbox']
            self.assertEqual((5, 4), (first_report['expectedWindowsSeats'], first_report['receivedWindowsSeats']))
            self.assertEqual([{'roomId': 5, 'seat': 1}], first_report['missingSeats'])
            self.assertEqual([], first_report['issues'])
            self.assertEqual((5, 5), (second_report['expectedWindowsSeats'], second_report['receivedWindowsSeats']))
            self.assertEqual([], second_report['missingSeats'])
            self.assertEqual([{'file': foreign.name, 'reason': 'Player ZIP belongs to another venue batch'}], second_report['issues'])
            self.assertNotIn(str(root), result.stdout.decode())
            rejected = subprocess.run(command, capture_output=True)
            self.assertEqual(1, rejected.returncode)
            self.assertIn(b'Windows inbox is incomplete', rejected.stderr)

            original.write_bytes(missing_bytes)
            foreign.unlink()
            clean = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True, check=True)
            self.assertTrue(json.loads(clean.stdout)['complete'])
            verified = subprocess.run(command, capture_output=True, check=True)
            self.assertEqual(80, json.loads(verified.stdout)['serverAcknowledgements'])

            batch = root / names[0]
            release = batch.parent / json.loads(batch.read_bytes())['venueReleaseReport']
            release_hash = hashlib.sha256(release.read_bytes()).hexdigest()
            with zipfile.ZipFile(original) as archive:
                log = archive.read('player.log')
                launch = json.loads(archive.read('launch-report.json'))

            def write_stamped(stamp):
                with zipfile.ZipFile(original, 'w') as archive:
                    archive.writestr('player.log', log)
                    archive.writestr('launch-report.json', json.dumps(dict(launch, venueReleaseReportSha256=stamp)))

            write_stamped(release_hash)
            stage = field.verify_venue_stages(path)['stages'][0]
            self.assertEqual({'venueReleaseReportSha256': release_hash, 'releaseReportSeatsVerified': 1}, stage['windowsRelease'])
            write_stamped('f' * 64)
            [problem] = field.verify_venue_stages(path, inspect=True)['issues']
            self.assertEqual([1], problem['entries'])
            inbox = problem['windowsInbox']
            self.assertEqual([{'roomId': 5, 'seat': 1}], inbox['missingSeats'])
            [rejected] = inbox['issues']
            self.assertEqual({'kind': 'windowsPlayerReport', 'name': original.name, 'status': 'venue-release-report-mismatch'},
                             rejected['evidenceMismatch'])

    def test_staged_inspection_lists_failed_and_missing_windows_measurements(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.staged_plan(root)
            plan['venueManifests'][0] = self.staged_batch(root / 'link-measurements', 'Independent', 1, 99000, 1,
                                                          windows_links=True)
            names = plan['venueManifests']
            criteria = {'minimumReplies': 29, 'maximumP95RoundTripMs': 13}
            originals = []
            for name in names[:2]:
                manifest_path = root / name
                manifest = json.loads(manifest_path.read_bytes())
                originals.append(manifest_path.read_bytes())
                manifest['windowsLinkCriteria'] = criteria
                manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            path = root / 'stages.json'
            path.write_text(json.dumps(plan), encoding='utf-8')
            command = [sys.executable, str(SCRIPT), '--venue-stages', str(path)]
            result = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True)
            self.assertEqual(1, result.returncode, result.stderr)
            self.assertFalse(result.stderr)
            inspection = json.loads(result.stdout)
            self.assertEqual(['needs-evidence', 'needs-evidence', *(['verified'] * 4)],
                             [row['status'] for row in inspection['entries']])
            self.assertEqual([[1], [2]], [issue['entries'] for issue in inspection['issues']])
            measured, missing = [issue['windowsLinkMetrics'] for issue in inspection['issues']]
            for report in (measured, missing):
                self.assertEqual(criteria, report['criteria'])
                self.assertFalse(report['meetsCriteria'])
            self.assertEqual(5, measured['verifiedSeats'])
            self.assertEqual([], measured['missingSeats'])
            self.assertEqual([(room, 1, 28, 13.5, ['minimumReplies', 'maximumP95RoundTripMs']) for room in range(1, 6)],
                             [(row['roomId'], row['seat'], row['replies'], row['p95RoundTripMs'], row['criteriaFailures'])
                              for row in measured['seats']])
            self.assertEqual(0, missing['verifiedSeats'])
            self.assertEqual([{'roomId': room, 'seat': 1} for room in range(1, 6)], missing['missingSeats'])
            self.assertEqual([], missing['seats'])
            self.assertNotIn(str(root), result.stdout.decode())
            rejected = subprocess.run(command, capture_output=True)
            self.assertEqual(1, rejected.returncode)
            self.assertIn(b'Windows link criteria not met at room 1 seat 1', rejected.stderr)

            first_path = root / names[0]
            partial = json.loads(first_path.read_bytes())
            partial['sessions'][0]['players'][0].pop('linkMetrics')
            first_path.write_text(json.dumps(partial), encoding='utf-8')
            incomplete = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True)
            self.assertEqual(1, incomplete.returncode)
            partial_report = json.loads(incomplete.stdout)['issues'][0]['windowsLinkMetrics']
            self.assertEqual(4, partial_report['verifiedSeats'])
            self.assertEqual([{'roomId': 1, 'seat': 1}], partial_report['missingSeats'])
            self.assertFalse(partial_report['meetsCriteria'])

            for name, original in zip(names[:2], originals, strict=True):
                (root / name).write_bytes(original)
            accepted = subprocess.run(command, capture_output=True, check=True)
            self.assertEqual(80, json.loads(accepted.stdout)['serverAcknowledgements'])

    def test_staged_windows_link_criteria_apply_to_all_batches_and_keep_stricter_local_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.staged_plan(root, windows_links=True, windows_inbox=True)
            base = {'minimumReplies': 28, 'maximumP95RoundTripMs': 14}
            plan['windowsLinkCriteria'] = base
            path = root / 'stages.json'
            path.write_text(json.dumps(plan), encoding='utf-8')
            command = [sys.executable, str(SCRIPT), '--venue-stages', str(path)]
            names = plan['venueManifests']

            def set_criteria(index, criteria):
                batch = root / names[index]
                manifest = json.loads(batch.read_bytes())
                manifest['windowsLinkCriteria'] = criteria
                batch.write_text(json.dumps(manifest), encoding='utf-8')

            set_criteria(0, {'minimumReplies': 1, 'maximumP95RoundTripMs': 900})
            report = json.loads(subprocess.check_output(command))
            self.assertEqual(base, report['windowsLinkCriteria'])
            self.assertEqual([dict(base, seatsVerified=count) for count in (5, 5, 10, 10, 25, 25)],
                             [stage['windowsLinkCriteria'] for stage in report['stages']])
            self.assertEqual([{
                'lowestReplies': {'roomId': 1, 'seat': 1, 'replies': 28},
                'highestP95RoundTripMs': {'roomId': 1, 'seat': 1, 'p95RoundTripMs': 13.5},
            }] * 6, [stage['windowsLinkObserved'] for stage in report['stages']])
            self.assertEqual(80, report['serverAcknowledgements'])

            set_criteria(0, {'minimumReplies': 29, 'maximumP95RoundTripMs': 900})
            set_criteria(3, {'minimumReplies': 1, 'maximumP95RoundTripMs': 13})
            inspected = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True)
            self.assertEqual(1, inspected.returncode)
            self.assertFalse(inspected.stderr)
            report = json.loads(inspected.stdout)
            self.assertEqual(base, report['windowsLinkCriteria'])
            self.assertEqual([[1], [4]], [issue['entries'] for issue in report['issues']])
            self.assertEqual([2, 3, 5, 6], [row['entry'] for row in report['entries'] if 'windowsLinkObserved' in row])
            failures = [issue['windowsLinkMetrics'] for issue in report['issues']]
            for failure, criteria, name, count in zip(
                failures,
                [{'minimumReplies': 29, 'maximumP95RoundTripMs': 14}, {'minimumReplies': 28, 'maximumP95RoundTripMs': 13}],
                ['minimumReplies', 'maximumP95RoundTripMs'], [5, 10], strict=True,
            ):
                self.assertEqual(criteria, failure['criteria'])
                self.assertEqual(count, failure['verifiedSeats'])
                self.assertFalse(failure['meetsCriteria'])
                self.assertTrue(all(seat['criteriaFailures'] == [name] for seat in failure['seats']))
            rejected = subprocess.run(command, capture_output=True)
            self.assertEqual(1, rejected.returncode)
            self.assertIn(b'Venue manifest entry 1: Windows link criteria not met', rejected.stderr)

    def test_staged_quest_link_criteria_report_missing_invalid_and_below_threshold_seats(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.staged_plan(root, remote=True, quest_links=True)
            names = [root / name for name in plan['venueManifests']]
            path = root / 'stages.json'
            criteria = {'minimumReplies': 28, 'maximumP95RoundTripMs': 46}
            prepare = [sys.executable, str(SCRIPT.with_name('prepare-venue-stages.py')), '--topology', 'direct-lan',
                       '--minimum-concurrent-ms', '2000', '--output', str(path), '--quest-minimum-replies', '28']
            manifests = list(map(str, reversed(names)))
            rejected = subprocess.run([*prepare, *manifests], capture_output=True)
            self.assertEqual(1, rejected.returncode)
            self.assertIn(b'Provide both Quest link criteria', rejected.stderr)
            self.assertFalse(path.exists())
            subprocess.run([*prepare, '--quest-maximum-p95-ms', '46', *manifests], capture_output=True, check=True)
            self.assertEqual(criteria, json.loads(path.read_bytes())['questLinkCriteria'])

            def set_local(index, values):
                manifest = json.loads(names[index].read_bytes())
                manifest['questLinkCriteria'] = values
                names[index].write_text(json.dumps(manifest), encoding='utf-8')
                return manifest

            set_local(0, {'minimumReplies': 1, 'maximumP95RoundTripMs': 900})
            command = [sys.executable, str(SCRIPT), '--venue-stages', str(path)]
            valid = json.loads(subprocess.check_output(command))
            self.assertEqual(criteria, valid['questLinkCriteria'])
            self.assertEqual(80, valid['serverAcknowledgements'])
            self.assertFalse(valid['networkCapacityAccepted'])
            self.assertEqual([dict(criteria, seatsVerified=5)] * 6, [stage['questLinkCriteria'] for stage in valid['stages']])
            self.assertEqual({'lowestReplies': {'roomId': 1, 'seat': 1, 'replies': 28},
                              'highestP95RoundTripMs': {'roomId': 1, 'seat': 1, 'p95RoundTripMs': 46}},
                             valid['stages'][0]['questLinkObserved'])

            deployment_path = names[0].with_name('deployment.json')
            deployment = json.loads(deployment_path.read_bytes())
            original_release = names[0].with_name('release.json').read_bytes()
            release_hash = hashlib.sha256(original_release).hexdigest()
            deployment_path.write_text(json.dumps(dict(deployment, venueReleaseReportSha256=release_hash)), encoding='utf-8')
            bound = json.loads(subprocess.check_output(command))
            self.assertEqual({'venueReleaseReportSha256': release_hash, 'releaseReportSeatsVerified': 5},
                             bound['stages'][0]['questRelease'])
            self.assertNotIn('questRelease', bound['stages'][1])
            deployment_path.write_text(json.dumps(dict(deployment, venueReleaseReportSha256='a' * 64)), encoding='utf-8')
            inspection = field.verify_venue_stages(path, inspect=True)
            [issue] = inspection['issues']
            self.assertEqual([1], issue['entries'])
            self.assertEqual({'kind': 'questDeploymentReport', 'name': deployment_path.name, 'status': 'venue-release-report-mismatch'},
                             issue['evidenceMismatch'])
            deployment_path.write_text(json.dumps(deployment), encoding='utf-8')

            set_local(0, {'minimumReplies': 29, 'maximumP95RoundTripMs': 900})
            set_local(1, {'minimumReplies': 1, 'maximumP95RoundTripMs': 45})
            mixed = json.loads(names[3].read_bytes())
            first, second, *_ = (names[3].parent / row['log'] for row in mixed['sessions'][0]['players'])
            original_first, original_second = first.read_bytes(), second.read_bytes()
            first.write_bytes(b''.join(line for line in original_first.splitlines(keepends=True) if b'VR_QUEST_LINK_METRICS ' not in line))
            second.write_bytes(original_second.replace(b' part=1/', b' part=2/', 1))
            audit = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True)
            self.assertEqual(1, audit.returncode, audit.stderr.decode())
            report = json.loads(audit.stdout)
            self.assertEqual([[1], [2], [4]], [issue['entries'] for issue in report['issues']])
            below_minimum, above_p95, intake = [issue['questLinkMetrics'] for issue in report['issues']]
            self.assertEqual(dict(criteria, minimumReplies=29), below_minimum['criteria'])
            self.assertEqual(dict(criteria, maximumP95RoundTripMs=45), above_p95['criteria'])
            for observed, failure in ((below_minimum, 'minimumReplies'), (above_p95, 'maximumP95RoundTripMs')):
                self.assertEqual(5, observed['verifiedSeats'])
                self.assertTrue(all(row['criteriaFailures'] == [failure] for row in observed['seats']))
            self.assertEqual(3, intake['verifiedSeats'])
            self.assertEqual([{'roomId': 1, 'seat': 2}], intake['missingSeats'])
            [invalid] = intake['invalidReports']
            self.assertEqual((2, 2), (invalid['roomId'], invalid['seat']))
            self.assertIn('missing, reordered or repeated fragments', invalid['reason'])
            self.assertNotIn(str(root), audit.stdout.decode())
            self.assertNotIn('192.168.', audit.stdout.decode())

            first.write_bytes(original_first)
            second.write_bytes(original_second)
            set_local(0, criteria)
            set_local(1, criteria)
            accepted = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True, check=True)
            self.assertTrue(json.loads(accepted.stdout)['complete'])

            for invalid in (None, {}, {'minimumReplies': True, 'maximumP95RoundTripMs': 14}):
                path.write_text(json.dumps(dict(plan, windowsLinkCriteria=invalid)), encoding='utf-8')
                with self.assertRaises(field.EvidenceError):
                    field.verify_venue_stages(path)

    def test_staged_inspection_lists_missing_quest_captures_and_recovers_original_batches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.staged_plan(root, remote=True)
            names = plan['venueManifests']
            replacements = {}
            for index, mode, count, minutes in ((2, 'Independent', 2, 2), (5, 'Linked', 5, 3)):
                folder = root / f'quest-{mode}'
                folder.mkdir()
                path, manifest = quest_capture_venue_fixture(folder, mode, quest_per_room=1, with_journals=True,
                    room_sizes=(count,) * 5, id_offset=100000 + index * 10000, minutes_after=minutes)
                offsets = [0] if mode == 'Linked' else [0, 100, 200, 300, 400]
                start = datetime.fromisoformat('2026-11-09T08:00:00+08:00') + timedelta(minutes=minutes)
                self.concurrent_journals(folder, manifest, offsets, capture_start=start)
                manifest.update(expectedPlayersPerRoom=count, minimumConcurrentMilliseconds=2000)
                release = self.add_shared_release(folder, manifest, 1).read_bytes()
                if index == 5:
                    manifest['questCaptures'] = observed_quest_capture_spec(folder, manifest['questCaptures'])
                manifest['questCaptures']['reports'].pop()
                path.write_text(json.dumps(manifest), encoding='utf-8')
                replacements[index] = (path, manifest)
                names[index] = str(path.relative_to(root))
            for name in names:
                (root / name).with_name('release.json').write_bytes(release)
            plan_path = root / 'stages.json'
            plan_path.write_text(json.dumps(plan), encoding='utf-8')
            command = [sys.executable, str(SCRIPT), '--venue-stages', str(plan_path)]
            result = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True)
            self.assertEqual(1, result.returncode, result.stderr)
            self.assertFalse(result.stderr)
            inspection = json.loads(result.stdout)
            self.assertEqual([[3], [6]], [issue['entries'] for issue in inspection['issues']])
            self.assertEqual(['verified', 'verified', 'needs-evidence', 'verified', 'verified', 'needs-evidence'],
                             [row['status'] for row in inspection['entries']])
            for issue, seat in zip(inspection['issues'], (2, 5), strict=True):
                captures = issue['questCaptures']
                self.assertEqual((5, 3, 1, 0), (captures['expectedSeats'], captures['reportedCompleteSeats'],
                                               captures['reportsRead'], captures['failedAttempts']))
                self.assertEqual([{'roomId': room, 'seat': seat} for room in (2, 4)], captures['missingSeats'])
            for secret in (str(root), '192.168.', 'fixture-1-5'):
                self.assertNotIn(secret, result.stdout.decode())
            rejected = subprocess.run(command, capture_output=True)
            self.assertEqual(1, rejected.returncode)
            self.assertIn(b'Venue manifest entry 3: Quest capture reports must cover', rejected.stderr)
            batch_path, manifest = replacements[2]
            report_path = batch_path.parent / manifest['questCaptures']['reports'][0]
            raw_report = report_path.read_bytes()
            report_path.unlink()
            missing_file = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True)
            self.assertEqual(1, missing_file.returncode)
            self.assertEqual({'kind': 'questCaptureReport', 'name': 'capture-report.json'},
                             json.loads(missing_file.stdout)['issues'][0]['missingFile'])
            report_path.write_bytes(raw_report)
            report = json.loads(raw_report)
            failed = report['seats'][-1]
            report['seats'][-1] = {key: failed[key] for key in ('roomId', 'seat', 'sessionId', 'port')} | {
                'complete': False, 'reason': 'fixture interruption'}
            report.update(complete=False, capturedSeats=2)
            report_path.write_text(json.dumps(report), encoding='utf-8')
            interrupted = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True)
            self.assertEqual(1, interrupted.returncode)
            captures = json.loads(interrupted.stdout)['issues'][0]['questCaptures']
            self.assertEqual(1, captures['failedAttempts'])
            self.assertEqual(2, captures['reportedCompleteSeats'])
            self.assertEqual([{'roomId': room, 'seat': 2} for room in (2, 4, 5)], captures['missingSeats'])
            report_path.write_bytes(raw_report)
            for path, manifest in replacements.values():
                manifest['questCaptures']['reports'].append('capture batch 2/capture-report.json')
                path.write_text(json.dumps(manifest), encoding='utf-8')
            accepted_raw = subprocess.check_output(command)
            accepted = json.loads(accepted_raw)
            self.assertEqual(80, accepted['serverAcknowledgements'])
            self.assertFalse(accepted['physicalHostsVerified'])

            other_path, other_manifest = replacements[5]
            other_report = other_path.parent / other_manifest['questCaptures']['reports'][0]
            raw_other_report = other_report.read_bytes()
            other_rows = json.loads(raw_other_report)
            linked_row, invalid_row = other_rows['seats'][:2]
            missing_row, changed_row, unreadable_row = json.loads(raw_report)['seats']
            missing_log = report_path.with_name(missing_row['log'])
            changed_log = report_path.with_name(changed_row['log'])
            unreadable_log = report_path.with_name(unreadable_row['log'])
            linked_log = other_report.with_name(linked_row['log'])
            invalid_log = other_report.with_name(invalid_row['log'])
            originals = {path: path.read_bytes() for path in
                         (missing_log, changed_log, unreadable_log, linked_log, invalid_log)}
            missing_log.unlink()
            data = originals[changed_log]
            changed_log.write_bytes(bytes([data[0] ^ 1]) + data[1:])
            unreadable_log.unlink()
            unreadable_log.mkdir()
            linked_log.write_bytes(originals[linked_log][:-1])
            invalid_data = b'\xff'
            invalid_log.write_bytes(invalid_data)
            invalid_row.update(bytes=len(invalid_data), sha256=hashlib.sha256(invalid_data).hexdigest())
            other_report.write_text(json.dumps(other_rows), encoding='utf-8')

            damaged = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True)
            self.assertEqual(1, damaged.returncode)
            self.assertFalse(damaged.stderr)
            inspection = json.loads(damaged.stdout)
            self.assertEqual([[3], [6]], [issue['entries'] for issue in inspection['issues']])
            self.assertEqual(['verified', 'verified', 'needs-evidence', 'verified', 'verified', 'needs-evidence'],
                             [row['status'] for row in inspection['entries']])
            expected_issues = (
                ((missing_row, 'missing'), (changed_row, 'size-or-digest-mismatch'), (unreadable_row, 'unreadable')),
                ((linked_row, 'size-or-digest-mismatch'), (invalid_row, 'invalid-encoding')),
            )
            for issue, expected in zip(inspection['issues'], expected_issues, strict=True):
                captures = issue['questCaptures']
                self.assertEqual(5, captures['reportedCompleteSeats'])
                self.assertEqual([], captures['missingSeats'])
                self.assertEqual([
                    {'roomId': row['roomId'], 'seat': row['seat'], 'file': row['log'], 'reason': reason}
                    for row, reason in expected
                ], captures['logIssues'])
            for secret in (str(root), '192.168.', 'fixture-1-5'):
                self.assertNotIn(secret, damaged.stdout.decode())
            rejected = subprocess.run(command, capture_output=True)
            self.assertEqual(1, rejected.returncode)
            self.assertIn(b'Venue manifest entry 3: missing original evidence file', rejected.stderr)
            unreadable_log.rmdir()
            other_report.write_bytes(raw_other_report)
            for path, original in originals.items():
                path.write_bytes(original)
            self.assertEqual(accepted_raw, subprocess.check_output(command))

            deployment = batch_path.with_name('deployment.json')
            deployment.unlink()
            missing_file = subprocess.run([*command, '--inspect-venue-stages'], capture_output=True)
            self.assertEqual(1, missing_file.returncode)
            self.assertEqual({'kind': 'questDeploymentReport', 'name': 'deployment.json'},
                             json.loads(missing_file.stdout)['issues'][0]['missingFile'])

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
            inspection = field.verify_venue_stages(path, inspect=True)
            self.assertFalse(inspection['complete'])
            self.assertEqual(6, len(inspection['issues']))
            for issue in inspection['issues']:
                overlap = issue['concurrentRoster']
                self.assertEqual('insufficient-overlap', overlap['status'])
                self.assertEqual(9000, overlap['minimumMilliseconds'])
                self.assertGreater(overlap['longestMilliseconds'], 0)
                self.assertLess(overlap['longestMilliseconds'], 9000)
                self.assertEqual(list(range(1, 6)), [room for group in overlap['groups'] for room in group['roomIds']])
                self.assertGreaterEqual(min(group['longestMilliseconds'] for group in overlap['groups']),
                                        overlap['longestMilliseconds'])
            first = root / names[0]
            raw_first = first.read_bytes()
            first.write_text(json.dumps(dict(json.loads(raw_first), minimumConcurrentMilliseconds=9000)), encoding='utf-8')
            path.write_text(json.dumps(plan), encoding='utf-8')
            local_minimum = field.verify_venue_stages(path, inspect=True)
            self.assertEqual([[1]], [issue['entries'] for issue in local_minimum['issues']])
            self.assertEqual(inspection['issues'][0]['concurrentRoster'], local_minimum['issues'][0]['concurrentRoster'])
            first.write_bytes(raw_first)
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
                    if label == 'missing-shot':
                        result = field.verify_venue_stages(path, inspect=True)
                        self.assertFalse(result['complete'])
                        self.assertEqual([[6]], [issue['entries'] for issue in result['issues']])
                        overlap = result['issues'][0]['concurrentRoster']
                        self.assertEqual('missing-fire', overlap['status'])
                        self.assertEqual(24, overlap['playersWithConfirmedFire'])
                        self.assertEqual([{'roomId': 5, 'seat': 5}], overlap['missingFireSeats'])
                        self.assertGreaterEqual(overlap['bestFireWindowMilliseconds'], overlap['minimumMilliseconds'])
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

    def test_independent_environment_batch_witnesses_exactly_the_selected_rooms(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, closure = venue_fixture(root, 'Independent', with_journals=True)
            reference = {'action': 'SetEnvironment', 'phaseReport': 'weather.json', 'roomIds': [4, 1]}
            manifest['venueControlBatches'] = [reference]
            policy = {'weather': 'Storm', 'timeOfDay': 'Night', 'lightning': True}
            targets = [dict(sessionId=row['sessionId'], roomIds=row['roomIds'], appliedAtSequence=sequence, state=state)
                       for row, sequence, state in ((closure['sessions'][0], 4, 'Ended'), (closure['sessions'][3], 6, 'Superseded'))]
            batch = {'requestId': id_for(2019), 'recordedAtUtc': '2026-11-09T00:00:01+00:00', 'sessions': targets, **policy}
            phase = root / reference['phaseReport']

            def write_report(value=batch):
                phase.write_text(json.dumps({'latestEnvironment': value, 'latestEnemies': value}), encoding='utf-8')

            def write_reference(value=reference):
                path.write_text(json.dumps(dict(manifest, venueControlBatches=[value])), encoding='utf-8')

            for room in (1, 4):
                entry = manifest['sessions'][room - 1]
                world = json.loads((root / entry['launcherReport']).read_text(encoding='utf-8'))['finalWorld']

                def apply_weather(packet):
                    if packet['frame']['phase'] == 'Running':
                        packet.update(weather='Storm', lightning=True, observedSequence=4 if room == 1 else 6)
                        packet['frame']['night'] = True

                world_journal(root / entry['worldJournal'], world, preparing_sequence=3, edit_packet=apply_weather)

            write_report()
            write_reference()
            result = field.verify_venue(path)
            self.assertEqual(result['venueControlBatches'], [dict(requestId=batch['requestId'], action='SetEnvironment',
                                                                 sessionsVerified=2, roomIds=[1, 4], **policy)])
            frames = {row['roomIds'][0]: row['worldJournal'].get('venueControlFrames') for row in result['sessions']}
            self.assertEqual({room: [(frame['appliedAtSequence'], frame['worldSequence']) for frame in rows]
                              for room, rows in frames.items() if rows}, {1: [(4, 2)], 4: [(6, 2)]})
            self.assertEqual(result['players'], 25)

            for updated, error in (
                ({'action': 'SetEnemies'}, 'requires an Independent environment batch'),
                ({'roomIds': []}, 'distinct room numbers'),
                ({'roomIds': [1, 1]}, 'distinct room numbers'),
                ({'roomIds': [True, 4]}, 'distinct room numbers'),
                ({'roomIds': [1, 6]}, 'distinct room numbers'),
                ({'roomIds': [1, 2]}, 'differs from the original room or session'),
                ({'roomIds': [1, 2, 4]}, 'cover exactly the selected rooms'),
            ):
                with self.subTest(reference=updated):
                    write_reference(reference | updated)
                    with self.assertRaisesRegex(field.EvidenceError, error):
                        field.verify_venue(path)
            write_reference({key: value for key, value in reference.items() if key != 'roomIds'})
            with self.assertRaisesRegex(field.EvidenceError, 'cover every original session'):
                field.verify_venue(path)
            write_reference()
            for rows, error in (
                (targets[:1], 'cover exactly the selected rooms'),
                (targets + targets[:1], 'cover exactly the selected rooms'),
                ([targets[0], targets[0]], 'differs from the original room or session'),
                ([targets[0], dict(targets[1], roomIds=[2])], 'differs from the original room or session'),
                ([targets[0], dict(targets[1], appliedAtSequence=5)], 'lacks an exact Running frame'),
            ):
                with self.subTest(targets=rows):
                    write_report(dict(batch, sessions=rows))
                    with self.assertRaisesRegex(field.EvidenceError, error):
                        field.verify_venue(path)

            _, _, linked = venue_fixture(root, 'Linked')
            linked_time = datetime.fromisoformat(linked['recordedAtUtc'])
            with self.assertRaisesRegex(field.EvidenceError, 'requires an Independent environment batch'):
                field.read_venue_control_batches([reference], {row['sessionId']: row for row in linked['sessions']},
                                                 linked, linked_time, root.joinpath, mode='Linked')

    def test_linked_room_enemy_policy_checks_use_the_exact_original_running_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Linked', with_journals=True)
            entry, = manifest['sessions']
            world = json.loads((root / entry['launcherReport']).read_text(encoding='utf-8'))['finalWorld']
            checks = [
                {'roomId': 2, 'appliedAtSequence': 5, 'inherited': False, 'behavior': 'Patrol', 'autoAttack': True},
                {'roomId': 1, 'appliedAtSequence': 5, 'inherited': True, 'behavior': 'Hold', 'autoAttack': False},
                {'roomId': 2, 'appliedAtSequence': 6, 'inherited': True, 'behavior': 'Hold', 'autoAttack': False},
            ]
            original_override = {'roomId': 2, 'behavior': 'Patrol', 'autoAttack': True}

            def verify(rows, *, override=None, suspend_override=False):
                path.write_text(json.dumps(dict(manifest, roomEnemyPolicyChecks=rows)), encoding='utf-8')

                def configure(packet):
                    frame = packet['frame']
                    if frame['phase'] != 'Running':
                        return
                    frame.update(behavior='Hold', autoAttack=False)
                    if packet['sequence'] < 10:
                        packet.update(observedSequence=5, suspended=suspend_override)
                        frame['roomEnemyPolicies'] = [original_override] if override is None else override
                    else:
                        packet.update(observedSequence=6)
                        frame['roomEnemyPolicies'] = []

                world_journal(root / entry['worldJournal'], world, preparing_sequence=4, edit_packet=configure)
                return field.verify_venue(path)

            result = verify(checks)
            self.assertEqual(result['sessions'][0]['worldJournal']['roomEnemyPolicyFrames'], [
                dict(checks[1], worldSequence=2), dict(checks[0], worldSequence=2), dict(checks[2], worldSequence=10),
            ])
            for replacement, error in (
                (dict(checks[0], roomId=3), 'disagrees with room 3'),
                (dict(checks[0], inherited=True), 'disagrees with room 2'),
                (dict(checks[0], autoAttack=False), 'disagrees with room 2'),
                (dict(checks[0], appliedAtSequence=4), 'lacks an exact Running frame'),
                (dict(checks[0], appliedAtSequence=6), 'disagrees with room 2'),
                (dict(checks[0], inherited=1), 'Invalid room enemy policy check'),
                (dict(checks[0], roomId=6), 'Invalid numeric evidence'),
                (dict(checks[0], appliedAtSequence=8), 'Invalid numeric evidence'),
            ):
                with self.subTest(replacement=replacement), self.assertRaisesRegex(field.EvidenceError, error):
                    verify([replacement])
            with self.assertRaisesRegex(field.EvidenceError, 'Duplicate room enemy policy check'):
                verify([checks[0], checks[0]])
            with self.assertRaisesRegex(field.EvidenceError, 'lacks an exact Running frame'):
                verify(checks, suspend_override=True)
            with self.assertRaisesRegex(field.EvidenceError, 'Invalid room enemy policies'):
                verify(checks, override=[original_override, original_override])
            with self.assertRaisesRegex(field.EvidenceError, 'disagrees with room 2'):
                verify([dict(checks[0], behavior='Hold', autoAttack=False)], override=[])

            entry.pop('worldJournal')
            path.write_text(json.dumps(dict(manifest, roomEnemyPolicyChecks=checks)), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'Linked venue with its original world journal'):
                field.verify_venue(path)

    def test_prepared_venue_manifest_verifies_original_control_reports_before_publication(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, closure = venue_fixture(root, mode, with_journals=True)
                selected = [1, 4] if mode == 'Independent' else list(range(1, 6))
                policy = {'weather': 'Storm', 'timeOfDay': 'Night', 'lightning': True}
                enemies = {'behavior': 'Patrol', 'autoAttack': False}
                rooms = closure['sessions']
                targets = [row for row in rooms if set(row['roomIds']) <= set(selected)]

                def phase_report(ordinal, observed, rows, fields):
                    return dict(requestId=id_for(ordinal), recordedAtUtc='2026-11-09T00:00:01+00:00',
                                sessions=[dict(sessionId=row['sessionId'], roomIds=row['roomIds'], state='Ended',
                                               appliedAtSequence=observed) for row in rows], **fields)

                phase = phase_report(2091, 4, targets, policy)
                weather = root / 'original weather.json'
                weather.write_text(json.dumps({'latestEnvironment': phase}), encoding='utf-8-sig')
                enemy = root / 'original enemies.json'
                enemy.write_text(json.dumps({'latestEnemies': phase_report(2092, 6, rooms, enemies)}), encoding='utf-8')
                for entry, row in zip(manifest['sessions'], rooms, strict=True):
                    launcher = root / entry['launcherReport']
                    original = json.loads(launcher.read_bytes())
                    scoped = row in targets

                    def configure(packet):
                        if packet['frame']['phase'] != 'Running':
                            return
                        first = packet['sequence'] < 10
                        packet.update(observedSequence=4 if first else 6, weather='Storm' if scoped else 'Clear', lightning=scoped)
                        packet['frame'].update(night=scoped, **({'behavior': 'Hold', 'autoAttack': False} if first else enemies))

                    world_journal(root / entry['worldJournal'], original['finalWorld'], preparing_sequence=3, edit_packet=configure)
                    launcher.write_text(json.dumps(original), encoding='utf-8')
                terminal, _, moved = self.terminal_venue_fixture(root, manifest, closure)
                packed = self.pack_venue(root, manifest)
                scope = (['--scoped-environment-batch', '4, 1'] if mode == 'Independent'
                         else ['--venue-control-batch', 'SetEnvironment'])
                command = [sys.executable, str(SCRIPT.with_name('prepare-venue-field-manifest.py')),
                           '--venue-bundle', packed['venueBundle'], '--launcher-report', terminal.name,
                           '--topology', 'same-host', '--server-ip', manifest['serverIps'][0], '--server-work-root', moved.name]
                options = [*scope, weather.name, '--venue-control-batch', 'SetEnemies', enemy.name]
                output = root / 'delivery' / 'prepared.json'
                output.parent.mkdir()
                call = subprocess.run([*command, '--output', str(output), *options], cwd=root, capture_output=True)
                self.assertEqual(0, call.returncode, call.stderr.decode())
                actual = json.loads(output.read_bytes())
                refs = {batch['action']: batch for batch in actual['venueControlBatches']}
                self.assertEqual((output.parent / refs['SetEnvironment']['phaseReport']).resolve(), weather)
                self.assertEqual(refs['SetEnvironment'].get('roomIds'), [1, 4] if mode == 'Independent' else None)
                self.assertEqual((output.parent / refs['SetEnemies']['phaseReport']).resolve(), enemy)

                actual['windowsPlayers'] = [dict(player, log=str(Path('..') / player['log'])) for player in packed['windowsPlayers']]
                output.write_text(json.dumps(actual), encoding='utf-8')
                verified = field.verify_venue(output)
                batch_counts = {batch['action']: batch['sessionsVerified'] for batch in verified['venueControlBatches']}
                self.assertEqual(batch_counts, {'SetEnvironment': len(targets), 'SetEnemies': len(rooms)})

                rejected = root / 'rejected.json'
                cases = [(['--scoped-environment-batch', '1,1', weather.name],
                          'distinct room numbers' if mode == 'Independent' else 'requires an Independent environment batch'),
                         (['--scoped-environment-batch', '1;4', weather.name], 'comma-separated list'),
                         (['--venue-control-batch', 'Pause', weather.name], 'must be SetEnvironment or SetEnemies'),
                         ([*options, *scope, weather.name], 'distinct across the venue')]
                if mode == 'Independent':
                    cases.append((['--scoped-environment-batch', '1,3', weather.name], 'differs from the original room or session'))
                for flags, message in cases:
                    with self.subTest(flags=flags):
                        call = subprocess.run([*command, '--output', str(rejected), *flags], cwd=root, capture_output=True)
                        self.assertEqual(1, call.returncode)
                        self.assertIn(message.encode(), call.stderr)
                        self.assertFalse(rejected.exists())

                weather.write_text(json.dumps({'latestEnvironment': dict(phase, lightning=False)}), encoding='utf-8')
                call = subprocess.run([*command, '--output', str(rejected), *options], cwd=root, capture_output=True)
                self.assertEqual(1, call.returncode)
                self.assertIn(b'disagrees with the venue environment', call.stderr)
                self.assertFalse(rejected.exists())

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

    def reconnect_window_fixture(self, root, mode, defect=None, *, repeat=False):
        path, manifest, _ = venue_fixture(root, mode, with_journals=True)
        manifest['verifyReconnectHistory'] = True
        manifest['reconnectWindow'] = {'roomId': 5, 'seat': 2, 'firstUnavailableSequence': 20, 'recoveredSequence': 31}
        if repeat:
            manifest['reconnectWindows'] = [manifest.pop('reconnectWindow'),
                                            {'roomId': 5, 'seat': 2, 'firstUnavailableSequence': 40, 'recoveredSequence': 51}]
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
                    previous = (99, 98) if repeat and defect != 'one release' else (99,)
                    original = ''.join(f'VR_CLIENT_CONNECTED id={connection}\nVR_CLIENT_DISCONNECTED\n'
                                       for connection in previous) + original
                    server_path = root / entry['serverLog']
                    first, rest = server_path.read_text(encoding='utf-8').split('\n', 1)
                    earlier = ''.join(f'VR_SERVER_ADMISSION_APPROVED id={connection}\n'
                                      f"VR_SERVER_PEER id={connection} endpoint={log['address']}:{5200 + connection}\n"
                                      f'VR_SERVER_CLIENT_LEFT id={connection}\n' for connection in previous)
                    server_path.write_text(first + '\n' + earlier + rest, encoding='utf-8')
                log_path.write_text(startup + original, encoding='utf-8')

            def edit(packet):
                number = packet['sequence']
                frame = packet['frame']
                if target and (20 <= number < (32 if defect == 'no recovery' else 31) or repeat and 40 <= number < 51):
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

    def test_venue_multiple_reconnect_windows_require_distinct_releases_and_verify_both(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                path, manifest = self.reconnect_window_fixture(Path(directory), mode, repeat=True)
                if mode == 'Linked':
                    manifest['reconnectWindows'].reverse()
                    path.write_text(json.dumps(manifest), encoding='utf-8')
                report = field.verify_venue(path)
                self.assertNotIn('reconnectWindow', report)
                rows = report['reconnectWindows']
                self.assertEqual([(5, 2, 20, 31, 24), (5, 2, 40, 51, 24)],
                                 [(row['roomId'], row['seat'], row['firstUnavailableSequence'],
                                   row['recoveredSequence'], row['unaffectedSeats']) for row in rows])
                self.assertEqual(2, report['reconnectHistory']['retiredConnections'])
                self.assertEqual(25, report['serverAcknowledgements'])
            with self.subTest(mode=mode, defect='one release'), tempfile.TemporaryDirectory() as directory:
                path, _ = self.reconnect_window_fixture(Path(directory), mode, 'one release', repeat=True)
                with self.assertRaisesRegex(field.EvidenceError, 'fewer verified retired connections'):
                    field.verify_venue(path)

    def test_venue_multiple_reconnect_windows_reject_conflicting_or_unbounded_selections(self):
        with tempfile.TemporaryDirectory() as directory:
            path, manifest = self.reconnect_window_fixture(Path(directory), 'Linked', repeat=True)
            first, second = manifest['reconnectWindows']
            for changes, error in (
                ({'verifyReconnectHistory': False}, 'requires verified reconnect history'),
                ({'reconnectWindow': first}, 'Use either reconnectWindow or reconnectWindows'),
                ({'reconnectWindows': []}, 'Provide 1 to 32 reconnect windows'),
                ({'reconnectWindows': [first] * 33}, 'Provide 1 to 32 reconnect windows'),
                ({'reconnectWindows': [first, first]}, 'repeat the same room, seat and frame boundaries'),
                ({'reconnectWindows': [first, dict(second, firstUnavailableSequence=41)]}, 'does not isolate the selected seat'),
            ):
                with self.subTest(error=error):
                    path.write_text(json.dumps(dict(manifest, **changes)), encoding='utf-8')
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

                plan = {'version': 1, 'mode': mode, 'endpoints': [], 'sources': []}
                for entry in manifest['sessions']:
                    session, _, endpoint = field.management_zip(root / entry['evidenceZip'])
                    plan['endpoints'].append({'roomIds': session['roomIds'], 'address': endpoint['address'], 'port': endpoint['port']})
                    plan['sources'].extend({'roomId': owner['roomId'], 'seat': owner['seat'] + 1, 'address': player['address']}
                                           for owner, player in zip(session['players'], entry['players'], strict=True))
                plan_path = root / 'distinct-network.json'
                extra_server = '192.168.5.254'
                plan['serverIps'] = sorted({row['address'] for row in plan['endpoints']} | {extra_server})
                plan_path.write_text(json.dumps(plan), encoding='utf-8')
                path.write_text(json.dumps(dict(manifest, venueNetworkPlan=plan_path.name)), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'omits addresses from the venue network plan'):
                    field.verify_venue(path)
                path.write_text(json.dumps(dict(manifest, venueNetworkPlan=plan_path.name,
                                                serverIps=manifest['serverIps'] + [extra_server])), encoding='utf-8')
                self.assertEqual(field.verify_venue(path)['venueNetworkPlan']['verifiedSeats'], 25)
                last_source = plan['sources'][-1]
                last_source['address'] = extra_server
                plan_path.write_text(json.dumps(plan), encoding='utf-8')
                path.write_text(json.dumps(dict(manifest, venueNetworkPlan=plan_path.name,
                                                serverIps=manifest['serverIps'] + [extra_server])), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, f"server or non-private source: room {last_source['roomId']} seat {last_source['seat']}"):
                    field.verify_venue(path)
                path.write_text(json.dumps(manifest), encoding='utf-8')

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
            with self.assertRaises(field.ConcurrentRosterIncomplete) as rejected:
                field.verify_venue_batch(path, inspect_roster_minimum=1000)
            overlap = rejected.exception.overlap
            self.assertEqual(0, overlap['longestMilliseconds'])
            self.assertEqual([[1], [2], [3], [4], [5]], [row['roomIds'] for row in overlap['groups']])
            first, fifth = overlap['groups'][0], overlap['groups'][4]
            self.assertEqual(7700, fifth['longestMilliseconds'])
            self.assertLess(first['longestWindow']['throughUtc'], fifth['longestWindow']['fromUtc'])
            self.assertTrue(all(row['continuousWindows'] == 1 and row['interruptions'] == []
                                and row['affectedSeats'] == [] for row in overlap['groups']))
            result = subprocess.run([sys.executable, str(SCRIPT), '--venue-manifest', str(path),
                                     '--inspect-concurrent-roster'], capture_output=True)
            self.assertEqual(1, result.returncode)
            self.assertEqual({'version': 1, 'consistent': False, 'concurrentRoster': overlap}, json.loads(result.stdout))

    def test_venue_concurrent_roster_does_not_bridge_interruptions(self):
        def interrupt(packet):
            number = packet['sequence']
            frame = packet['frame']
            if cause in ('gap', 'at-gap-limit') and number >= 40:
                packet['elapsedMilliseconds'] += 401 if cause == 'gap' else 400
            if cause == 'stalled-tick' and 40 <= number <= 44:
                frame['tick'] = 39
            if number != 40:
                return
            if cause == 'paused':
                frame['phase'] = 'Paused'
            if cause == 'suspended':
                packet['suspended'] = True
            if cause == 'rewound-tick':
                frame['tick'] -= 2
            if cause == 'missing-player':
                frame['tick'] -= 1
                frame['players'][-1]['connected'] = False
            if cause == 'wrong-room':
                frame['players'][-1]['roomId'] = 1

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Linked', with_journals=True)
            manifest['minimumConcurrentMilliseconds'] = 6000
            path.write_text(json.dumps(manifest), encoding='utf-8')
            for cause in ('paused', 'suspended', 'stalled-tick', 'rewound-tick', 'missing-player', 'wrong-room', 'gap', 'at-gap-limit'):
                with self.subTest(cause=cause):
                    self.concurrent_journals(root, manifest, [0], interrupt)
                    if cause == 'at-gap-limit':
                        self.assertEqual(field.verify_venue(path)['concurrentRoster']['longestMilliseconds'], 8100)
                    else:
                        with self.assertRaisesRegex(field.EvidenceError, 'continuous concurrent roster'):
                            field.verify_venue(path)
                        with self.assertRaises(field.ConcurrentRosterIncomplete) as rejected:
                            field.verify_venue_batch(path, inspect_roster_minimum=6000)
                        group, = rejected.exception.overlap['groups']
                        reason = {'stalled-tick': 'tick-not-advancing', 'rewound-tick': 'tick-not-advancing', 'missing-player': 'roster-mismatch',
                                  'wrong-room': 'roster-mismatch', 'gap': 'frame-gap'}.get(cause, cause)
                        self.assertEqual(2, group['continuousWindows'])
                        issue, = group['interruptions']
                        sequence = 45 if cause == 'stalled-tick' else 40
                        self.assertEqual((reason, 1, sequence), (issue['reason'], issue['frameCount'], issue['first']['worldSequence']))
                        self.assertEqual(issue['first'], issue['last'])
                        if cause in ('missing-player', 'wrong-room'):
                            row, = group['affectedSeats']
                            self.assertEqual((5, 5, 'disconnected' if cause == 'missing-player' else 'wrong-room'),
                                             (row['roomId'], row['seat'], row['reason']))
                            self.assertEqual(issue['first'], row['first'])
                        else:
                            self.assertEqual([], group['affectedSeats'])

    def test_venue_concurrent_roster_same_tick_requires_a_later_advancing_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, manifest, _ = venue_fixture(root, 'Linked', with_journals=True)
            manifest['minimumConcurrentMilliseconds'] = 7700
            path.write_text(json.dumps(manifest), encoding='utf-8')

            def repeat_tick(packet):
                if 40 <= packet['sequence'] <= 43:
                    packet['frame']['tick'] = 39

            self.concurrent_journals(root, manifest, [0], repeat_tick)
            report = field.verify_venue(path)['concurrentRoster']
            self.assertEqual(7700, report['longestMilliseconds'])

            def one_ms_late(packet):
                repeat_tick(packet)
                if packet['sequence'] >= 44:
                    packet['elapsedMilliseconds'] += 1

            self.concurrent_journals(root, manifest, [0], one_ms_late)
            with self.assertRaises(field.ConcurrentRosterIncomplete) as rejected:
                field.verify_venue_batch(path, inspect_roster=True)
            late, = rejected.exception.overlap['groups'][0]['interruptions']
            self.assertEqual(('tick-not-advancing', 44), (late['reason'], late['first']['worldSequence']))

            def repeat_at_tail(packet):
                if packet['frame']['phase'] == 'Running' and packet['sequence'] >= 77:
                    packet['frame']['tick'] = 76

            self.concurrent_journals(root, manifest, [0], repeat_at_tail)
            with self.assertRaises(field.ConcurrentRosterIncomplete) as rejected:
                field.verify_venue_batch(path, inspect_roster=True)
            overlap = rejected.exception.overlap
            self.assertEqual(7400, overlap['longestMilliseconds'])
            self.assertEqual('2026-11-09T00:00:07.600000+00:00', overlap['groups'][0]['longestWindow']['throughUtc'])

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
                        for player in session['players']
                        if player['seat'] >= sum(other['roomId'] == player['roomId'] for other in session['players']) - quest_per_room)
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

    def test_prepare_measured_windows_inbox_with_concurrent_roster(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, manifest, closure = venue_fixture(root, 'Independent', with_journals=True, room_sizes=(1,) * 5)
            self.concurrent_journals(root, manifest, [0, 100, 200, 300, 400])
            terminal, _, moved = self.terminal_venue_fixture(root, manifest, closure)
            release = self.add_shared_release(root, manifest, 0)
            self.add_windows_links(root, manifest)
            inbox = self.windows_inbox_fixture(root, manifest)
            returned = root / inbox['windowsEvidenceDirectory']
            output = root / 'prepared.json'
            command = [sys.executable, str(SCRIPT.with_name('prepare-venue-field-manifest.py')),
                       '--venue-bundle', str(root / inbox['venueBundle']), '--launcher-report', str(terminal),
                       '--topology', 'same-host', '--server-ip', manifest['serverIps'][0],
                       '--server-work-root', str(moved), '--players-per-room', '1', '--windows-inbox', str(returned),
                       '--venue-release-report', str(release), '--output', str(output)]
            limits = ['--windows-minimum-replies', '28', '--windows-maximum-p95-ms', '14']
            first_archive = sorted(returned.glob('*.ZIP'))[0]
            raw = first_archive.read_bytes()
            first_archive.unlink()
            result = subprocess.run([*command, *limits, '--minimum-concurrent-ms', '2000'], capture_output=True)
            self.assertEqual(0, result.returncode, result.stderr.decode())
            prepared = json.loads(output.read_bytes())
            criteria = {'minimumReplies': 28, 'maximumP95RoundTripMs': 14}
            self.assertEqual(criteria, prepared['windowsLinkCriteria'])
            self.assertEqual(2000, prepared['minimumConcurrentMilliseconds'])
            self.assertEqual(1, prepared['expectedPlayersPerRoom'])
            inspection, _ = field.verify_venue_batch(output, inspect_windows=True)
            self.assertFalse(inspection['complete'])
            self.assertEqual(4, inspection['receivedWindowsSeats'])
            self.assertEqual(1, len(inspection['missingSeats']))
            first_archive.write_bytes(raw)
            accepted = field.verify_venue(output)
            self.assertEqual(dict(criteria, seatsVerified=5), accepted['windowsLinkCriteria'])
            self.assertGreaterEqual(accepted['concurrentRoster']['longestMilliseconds'], 2000)
            self.assertEqual(5, accepted['serverAcknowledgements'])

            for options, message in (
                (limits[:2], b'Provide both Windows link criteria'),
                ([*limits[:2], '--windows-maximum-p95-ms', '901'], b'Invalid numeric evidence'),
                (['--minimum-concurrent-ms', '999'], b'Invalid numeric evidence'),
            ):
                with self.subTest(options=options):
                    invalid = root / 'invalid.json'
                    result = subprocess.run([*command[:-1], str(invalid), *options], capture_output=True)
                    self.assertNotEqual(0, result.returncode)
                    self.assertIn(message, result.stderr)
                    self.assertFalse(invalid.exists())

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

    def test_network_plan_with_launch_sessions_requires_same_sealed_revision_and_mission(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, _ = venue_fixture(root, mode, remote=True, room_sizes=(2,) * 5)
                manifest.update(expectedPlayersPerRoom=2, venueNetworkPlan='network.json')
                plan = {'version': 1, 'mode': mode, 'endpoints': [], 'sources': []}
                for index, entry in enumerate(manifest['sessions'], 1):
                    evidence = root / entry['evidenceZip']
                    session, stats, endpoint = field.management_zip(evidence)
                    session['mission']['id'] = id_for(800 + index)
                    session['combatStream']['expectedSequence'] = 6
                    launch = root / entry['launcherReport']
                    report = json.loads(launch.read_bytes())
                    report['finalCombatStream']['expectedSequence'] = 6
                    launch.write_text(json.dumps(report), encoding='utf-8')
                    with zipfile.ZipFile(evidence, 'w') as archive:
                        for name, record in (('session', session), ('statistics', stats), ('endpoint', endpoint)):
                            archive.writestr(name + '.json', json.dumps(record))
                    plan['endpoints'].append({'roomIds': session['roomIds'], 'address': endpoint['address'], 'port': endpoint['port'],
                        'sessionId': session['id'], 'missionId': session['mission']['id'], 'sessionSequence': 6})
                    plan['sources'].extend({'roomId': owner['roomId'], 'seat': owner['seat'] + 1, 'address': player['address']}
                                           for owner, player in zip(session['players'], entry['players'], strict=True))
                path.write_text(json.dumps(manifest), encoding='utf-8')
                network = root / manifest['venueNetworkPlan']
                network.write_text(json.dumps(plan), encoding='utf-8')
                self.assertEqual(10, field.verify_venue(path)['venueNetworkPlan']['verifiedSeats'])
                for key, value in (('sessionId', id_for(2265)), ('missionId', id_for(2266)), ('sessionSequence', 7)):
                    with self.subTest(key=key):
                        changed = deepcopy(plan)
                        changed['endpoints'][-1][key] = value
                        network.write_text(json.dumps(changed), encoding='utf-8')
                        with self.assertRaisesRegex(field.EvidenceError, 'launch identity or revision differs from the original sealed session'):
                            field.verify_venue(path)

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

    def test_venue_departures_keep_scores_and_exact_final_room_counts(self):
        irregular = (0, 1, 1, 2, 1)
        for mode, room_sizes in (('Independent', irregular), ('Linked', irregular), ('Linked', (0,) * 5)):
            with self.subTest(mode=mode, seats=room_sizes), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                counts = {str(room): size for room, size in enumerate(room_sizes, 1)}
                remaining = sum(room_sizes)
                path, manifest, closure = venue_fixture(root, mode, remote=True, with_journals=True,
                                                        room_sizes=room_sizes, game_server=True)
                first = manifest['sessions'][0]
                evidence_path, launcher_path = root / first['evidenceZip'], root / first['launcherReport']
                session, _, _ = field.management_zip(evidence_path)
                departed = {'playerId': id_for(999), 'admissionId': id_for(998), 'roomId': 1,
                            'joinedAtSequence': 3, 'leftAtSequence': 7}
                launcher = json.loads(launcher_path.read_bytes())
                bodies = [{'id': player['id'], 'roomId': player['roomId'], 'connected': True, 'health': 100,
                           'rig': {'kind': 'Tracked'}} for player in session['players']]
                removed_body = {'id': departed['playerId'], 'roomId': 1, 'connected': True, 'health': 100, 'rig': {'kind': 'Tracked'}}
                world_journal(root / first['worldJournal'], launcher['finalWorld'], preparing_sequence=5, running_sequence=6,
                              players=lambda _, phase: bodies if phase == 'Ended' else [*bodies, removed_body])
                launcher_path.write_text(json.dumps(launcher), encoding='utf-8')
                with (root / first['serverLog']).open('a', encoding='utf-8') as log:
                    log.write('VR_SERVER_ADMISSION_APPROVED id=999\nVR_SERVER_PEER id=999 endpoint=192.168.5.99:5999\n')
                terminal, _, work = self.terminal_venue_fixture(root, manifest, closure)
                session, stats, endpoint = field.management_zip(evidence_path)
                stats['players'].append({name: 0 for name in field.COMBAT} | {'playerId': departed['playerId'], 'roomId': 1,
                                                                            'health': 100, 'accuracyPercent': 0})
                document = {'version': 1, 'sessionId': session['id'], 'streamId': endpoint['streamId'], 'throughSequence': 9,
                            'endedAtSequence': 8, 'players': [departed]}

                def write_evidence(departures):
                    with zipfile.ZipFile(evidence_path, 'w') as archive:
                        for name, record in [('session', session), ('statistics', stats), ('endpoint', endpoint),
                                             ('roster-departures', departures)]:
                            archive.writestr(name + '.json', json.dumps(record))

                def verify(draft):
                    path.write_text(json.dumps(draft), encoding='utf-8')
                    return field.verify_venue(path)

                write_evidence(document)
                closure['sessions'][0]['rosterDepartureCount'] = 1
                (root / manifest['closure']).write_text(json.dumps({'batch': closure}), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'expectedFinalPlayersByRoom'):
                    verify(manifest)
                manifest['expectedFinalPlayersByRoom'] = counts
                verified = verify(manifest)
                self.assertEqual(room_sizes, tuple(room['players'] for room in verified['rooms']))
                self.assertEqual((remaining, remaining, 1),
                                 (verified['players'], verified['serverAcknowledgements'], verified['departedScoresVerified']))
                self.assertEqual({'scoresVerified': 1, 'endedAtSequence': 8}, verified['sessions'][0]['rosterDepartures'])
                self.assertFalse(verified['networkCapacityAccepted'])
                with self.assertRaisesRegex(field.EvidenceError, 'fixed full roster'):
                    field.verify_venue_batch(path, staged=True)
                if remaining:
                    with self.assertRaisesRegex(field.EvidenceError, 'expected seats'):
                        verify(dict(manifest, expectedFinalPlayersByRoom=counts | {'1': 1, '2': 0}))
                else:
                    self.assertEqual(0, verified['distinctAddressesOutsideDeclaredServer'])
                write_evidence(dict(document, endedAtSequence=9))
                with self.assertRaisesRegex(field.EvidenceError, 'original End revision'):
                    verify(manifest)
                write_evidence(document)
                incomplete = deepcopy(manifest)
                del incomplete['sessions'][0]['combatJournal']
                with self.assertRaisesRegex(field.EvidenceError, 'combat.*journal'):
                    verify(incomplete)
                packed = self.pack_venue(root, manifest)
                logs = packed.pop('windowsPlayers')
                if logs:
                    packed['windowsPlayers'] = logs
                else:
                    packed['sessions'][0]['players'] = []
                self.assertEqual(verified, verify(packed))

                output = root / 'prepared.json'
                command = [sys.executable, str(SCRIPT.with_name('prepare-venue-field-manifest.py')),
                           '--venue-bundle', str(root / packed['venueBundle']), '--launcher-report', str(terminal),
                           '--server-work-root', str(work), '--topology', 'direct-lan', '--server-ip', manifest['serverIps'][0],
                           '--output', str(output)]
                missing = subprocess.run(command, capture_output=True, encoding='utf-8', timeout=10)
                self.assertEqual(1, missing.returncode, missing.stderr)
                self.assertIn('--final-players-by-room', missing.stderr)
                prepared = subprocess.run([*command, '--final-players-by-room', *map(str, room_sizes)],
                                          capture_output=True, encoding='utf-8', timeout=10)
                self.assertEqual(0, prepared.returncode, prepared.stderr)
                draft = json.loads(output.read_bytes())
                self.assertEqual(counts, draft['expectedFinalPlayersByRoom'])
                if logs:
                    draft['windowsPlayers'] = logs
                self.assertEqual(verified, verify(draft))

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

                # A deployment interrupted after its first successful seats can share one
                # original sample with a new batch that covered the remaining seats.
                first_deployment = root / manifest['questDeployments']['reports'][0]
                interrupted = json.loads(first_deployment.read_bytes())
                interrupted['complete'] = False
                interrupted['devices'].extend({'roomId': row['roomId'], 'seat': row['seat'], 'status': 'not-attempted'}
                                              for row in devices[2:])
                interrupted['retry']['devices'] = [f'{index:064x}' for index in range(25)]
                first_deployment.write_text(json.dumps(interrupted), encoding='utf-8')
                combined_path = root / 'combined-readiness.json'
                combined = {key: value for key, value in report.items() if key not in ('deploymentSha256', 'seats')}
                combined['evidenceVersion'] = 2
                combined['seats'] = []
                for ready_name, deploy_name in zip(manifest['questReadinessReports'], manifest['questDeployments']['reports'], strict=True):
                    current = json.loads((root / ready_name).read_bytes())
                    digest = hashlib.sha256((root / deploy_name).read_bytes()).hexdigest()
                    combined['seats'].extend(dict(row, deploymentSha256=digest) for row in current['seats'])
                combined_path.write_text(json.dumps(combined), encoding='utf-8')
                path.write_text(json.dumps(dict(manifest, questReadinessReports=[combined_path.name])), encoding='utf-8')
                expected = {'reportsVerified': 1, 'seatsVerified': 25, 'sessionsVerified': len(manifest['sessions']),
                            'deploymentReportsMatched': 2}
                self.assertEqual(expected, field.verify_venue(path)['questReadiness'])

                for change, message in (
                    ({'deploymentSha256': 'd'*64}, 'requires its exact deployment report'),
                    ({'deploymentSha256': combined['seats'][0]['deploymentSha256']}, 'does not match its original deployed session'),
                    ({'worldSequence': 3}, 'different frames for one session in the same sample'),
                ):
                    broken = deepcopy(combined)
                    # The third seat shares the session of the first seat in either topology.
                    broken['seats'][2].update(change)
                    combined_path.write_text(json.dumps(broken), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, message):
                        field.verify_venue(path)
                combined_path.write_text(json.dumps(combined), encoding='utf-8')
                path.write_text(json.dumps(dict(manifest, questReadinessReports=[combined_path.name, report_path.name])), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'one original sample with per-seat deployment references'):
                    field.verify_venue(path)

                closure_path = root / manifest['closure']
                original_closure = json.loads(closure_path.read_bytes())
                original_worlds = {server['result']['sessionId']: server['result']['finalWorld']
                                   for server in json.loads(terminal.read_bytes())['servers']}
                for entry, row in zip(manifest['sessions'], original_closure['batch']['sessions'], strict=True):
                    session, _, _ = field.management_zip(root / entry['evidenceZip'])
                    source = original_worlds[session['id']]
                    tracked = [{'id': owner['id'], 'roomId': owner['roomId'], 'connected': True, 'health': 100,
                                'rig': {'kind': 'Tracked'}} for owner in session['players']]

                    def second_preparing_frame(packet):
                        if packet['sequence'] == 2:
                            packet['observedSequence'] = 6
                            packet['frame'].update(phase='Preparing', tick=0)

                    world_journal(root / entry['worldJournal'], source, capture_start=source['header']['captureStartedAtUtc'],
                                  players=lambda _, __: tracked, preparing_sequence=6, edit_packet=second_preparing_frame)
                    row['trackingBegin'] = {'requestId': id_for(996), 'appliedAtSequence': 7, 'frame': {
                        'streamId': source['header']['streamId'], 'worldSequence': 2, 'elapsedMilliseconds': 200}}

                combined['sampledAtUtc'] = (captured + timedelta(milliseconds=150)).isoformat()
                for seat in combined['seats']:
                    seat['observedSequence'] = 6
                joint_manifest = dict(manifest, questReadinessReports=[combined_path.name], verifyTrackingBegin=True)
                closure_path.write_text(json.dumps(original_closure), encoding='utf-8')
                combined_path.write_text(json.dumps(combined), encoding='utf-8')
                path.write_text(json.dumps(joint_manifest), encoding='utf-8')
                both = field.verify_venue(path)
                self.assertEqual(expected, both['questReadiness'])
                self.assertTrue(all(row['worldJournal']['trackingBegin']['firstRunningFrame'] == 3 for row in both['sessions']))

                target = next(row for row in original_closure['batch']['sessions'] if 3 in row['roomIds'])
                for seat in combined['seats']:
                    if seat['sessionId'] == target['sessionId']:
                        seat.update(worldSequence=2, capturedAtUtc=(captured + timedelta(milliseconds=100)).isoformat())
                combined_path.write_text(json.dumps(combined), encoding='utf-8')
                self.assertEqual(expected, field.verify_venue(path)['questReadiness'])

                target['trackingBegin']['frame'].update(worldSequence=1, elapsedMilliseconds=100)
                closure_path.write_text(json.dumps(original_closure), encoding='utf-8')
                path.write_text(json.dumps(dict(joint_manifest, verifyTrackingBegin=False)), encoding='utf-8')
                self.assertEqual(expected, field.verify_venue(path)['questReadiness'])
                guard_only = joint_manifest.copy()
                del guard_only['questReadinessReports']
                path.write_text(json.dumps(guard_only), encoding='utf-8')
                self.assertEqual(25, field.verify_venue(path)['trackingBegin']['trackedPlayers'])
                path.write_text(json.dumps(joint_manifest), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'Quest readiness frame is later than the guarded Begin frame'):
                    field.verify_venue(path)

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
                release_bytes = release.read_bytes()
                release_hash = hashlib.sha256(release_bytes).hexdigest()
                deployment['venueReleaseReportSha256'] = release_hash
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
                self.assertEqual((release_hash, 5), (expected['questDeployment']['venueReleaseReportSha256'],
                                                    expected['questDeployment']['releaseReportSeatsVerified']))
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
                release.write_bytes(release_bytes + b'\n')
                rejected = subprocess.run([*command, '--output', str(output)], capture_output=True)
                self.assertEqual(1, rejected.returncode)
                self.assertIn(b'Quest deployment report used different original venue release report bytes', rejected.stderr)
                self.assertFalse(output.exists())
                release.write_bytes(release_bytes)
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
                thresholds = output.with_name('venue-with-quest-criteria.json')
                prepared = subprocess.run([*command, '--quest-minimum-replies', '28', '--quest-maximum-p95-ms', '46',
                                           '--output', str(thresholds)], capture_output=True)
                self.assertEqual(0, prepared.returncode, prepared.stderr.decode())
                self.assertEqual({'minimumReplies': 28, 'maximumP95RoundTripMs': 46},
                                 json.loads(thresholds.read_bytes())['questLinkCriteria'])
                with self.assertRaises(field.QuestLinkCriteriaFailed) as missing:
                    field.verify_venue(thresholds)
                self.assertEqual(5, len(missing.exception.metrics['missingSeats']))
                openxr_path = output.with_name('venue-with-required-openxr.json')
                prepared = subprocess.run([*command, '--require-quest-openxr', '--output', str(openxr_path)], capture_output=True)
                self.assertEqual(0, prepared.returncode, prepared.stderr.decode())
                self.assertIs(json.loads(openxr_path.read_bytes())['requireQuestOpenXR'], True)
                with self.assertRaises(field.QuestOpenXRIncomplete) as missing_openxr:
                    field.verify_venue(openxr_path)
                self.assertEqual(5, len(missing_openxr.exception.coverage['missingSeats']))
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

                release_hash = hashlib.sha256(release.read_bytes()).hexdigest()
                for row in manifest['sessions']:
                    for player in row['players']:
                        if 'launcherReport' in player:
                            launch_path = root / player['launcherReport']
                            launch = json.loads(launch_path.read_bytes())
                            launch_path.write_text(json.dumps(dict(launch, venueReleaseReportSha256=release_hash)), encoding='utf-8')
                deployment_path = root / manifest['questDeployments']['reports'][0]
                deployment = json.loads(deployment_path.read_bytes())
                deployment_path.write_text(json.dumps(dict(deployment, venueReleaseReportSha256=release_hash)), encoding='utf-8')
                mixed = field.verify_venue(path)['venueRelease']
                self.assertEqual(release_hash, mixed['windows']['venueReleaseReportSha256'])
                self.assertEqual(release_hash, mixed['quest']['venueReleaseReportSha256'])
                self.assertEqual((15, 10), (mixed['windows']['releaseReportSeatsVerified'], mixed['quest']['releaseReportSeatsVerified']))

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
            release_path = root / manifest['venueReleaseReport']
            original_release = release_path.read_bytes()
            launch['venueReleaseReportSha256'] = hashlib.sha256(original_release).hexdigest()
            launch_path.write_text(json.dumps(launch), encoding='utf-8')
            release_path.write_bytes(original_release + b'\n')
            with self.assertRaisesRegex(field.EvidenceError, 'Windows player launch used different original venue release report bytes'):
                field.verify_venue(path)
            release_path.write_bytes(original_release)
            launch['playerManifestSha256'] = '11' * 32
            launch_path.write_text(json.dumps(launch), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'original venue release manifest'):
                field.verify_venue(path)
            release = json.loads(release_path.read_bytes())
            release['quest']['sha256'] = '35' * 32
            release_path.write_text(json.dumps(release), encoding='utf-8')
            with self.assertRaisesRegex(field.EvidenceError, 'differs from the original release APK'):
                field.verify_venue(path)

    def test_server_release_matches_original_terminal_batch_for_both_topologies(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, closure = venue_fixture(root, mode, with_journals=True)
                terminal_path, terminal, moved = self.terminal_venue_fixture(root, manifest, closure)
                release_path = self.add_shared_release(root, manifest, 0)
                release = json.loads(release_path.read_text(encoding='utf-8-sig'))
                digest = '4' * 64
                release['windows']['serverManifestSha256'] = digest
                release_path.write_text(json.dumps(release), encoding='utf-8')
                path.write_text(json.dumps(manifest), encoding='utf-8')
                self.assertNotIn('server', field.verify_venue(path)['venueRelease'])
                manifest['requireServerRelease'] = True
                path.write_text(json.dumps(manifest), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'original release-bound terminal venue launch report'):
                    field.verify_venue(path)

                terminal['serverManifestSha256'] = digest
                terminal_path.write_text(json.dumps(terminal), encoding='utf-8')
                verified = field.verify_venue(path)
                expected = {'serverManifestSha256': digest, 'sessionsVerified': len(manifest['sessions'])}
                self.assertEqual(expected, verified['venueRelease']['server'])
                self.assertEqual(25, verified['venueRelease']['windows']['seatsVerified'])

                release_raw = release_path.read_bytes()
                expected['venueReleaseReportSha256'] = hashlib.sha256(release_raw).hexdigest()
                terminal['venueReleaseReportSha256'] = expected['venueReleaseReportSha256']
                terminal_path.write_text(json.dumps(terminal), encoding='utf-8')
                packed = self.pack_venue(root, manifest)
                command = [sys.executable, str(SCRIPT.with_name('prepare-venue-field-manifest.py')),
                           '--venue-bundle', str(root / packed['venueBundle']), '--launcher-report', str(terminal_path),
                           '--topology', 'same-host', '--server-ip', manifest['serverIps'][0], '--server-work-root', str(moved),
                           '--venue-release-report', str(release_path), '--require-server-release']
                prepared_path = root / 'prepared.json'
                written = subprocess.run([*command, '--output', str(prepared_path)], capture_output=True, encoding='utf-8', timeout=30)
                self.assertEqual(0, written.returncode, written.stderr)
                prepared = json.loads(prepared_path.read_bytes())
                self.assertIs(prepared['requireServerRelease'], True)
                players = {entry['sessionId']: entry['players'] for entry in manifest['sessions']}
                for entry in prepared['sessions']:
                    entry['players'] = players[entry['sessionId']]
                prepared_path.write_text(json.dumps(prepared), encoding='utf-8')
                self.assertEqual(expected, field.verify_venue(prepared_path)['venueRelease']['server'])

                changed_release_path = root / 'rejected-release.json'
                release_path.write_bytes(release_raw + b'\n')
                failed = subprocess.run([*command, '--output', str(changed_release_path)], capture_output=True, encoding='utf-8', timeout=30)
                self.assertEqual(1, failed.returncode, failed.stderr)
                self.assertIn('used different original venue release report bytes', failed.stderr)
                self.assertFalse(changed_release_path.exists())
                release_path.write_bytes(release_raw)

                terminal['serverManifestSha256'] = '5' * 64
                terminal_path.write_text(json.dumps(terminal), encoding='utf-8')
                path.write_text(json.dumps(dict(manifest, requireServerRelease=False)), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'does not match the original venue server release'):
                    field.verify_venue(path)
                rejected_path = root / 'rejected.json'
                failed = subprocess.run([*command, '--output', str(rejected_path)], capture_output=True, encoding='utf-8', timeout=30)
                self.assertEqual(1, failed.returncode, failed.stderr)
                self.assertIn('does not match the original venue server release', failed.stderr)
                self.assertFalse(rejected_path.exists())

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

                release = root / 'release.json'
                raw_release = release.read_bytes()
                release_hash = hashlib.sha256(raw_release).hexdigest()
                retry_path = root / 'retry.json'
                retry_path.write_text(json.dumps(dict(report, devices=rows[3:], venueReleaseReportSha256=release_hash)), encoding='utf-8')
                bound = field.verify_venue(path)['questDeployment']
                self.assertEqual((release_hash, len(rows) - 3),
                                 (bound['venueReleaseReportSha256'], bound['releaseReportSeatsVerified']))
                release.write_bytes(raw_release + b'\n')
                with self.assertRaisesRegex(field.EvidenceError, 'Quest deployment report used different original venue release report bytes'):
                    field.verify_venue(path)

    def test_quest_openxr_proof_matches_each_of_25_original_seats_in_both_modes(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest = quest_capture_venue_fixture(root, mode, quest_per_room=5, batches=1)
                deployment = self.quest_deployment_evidence(root, manifest, 5)
                deployment.update(requireOpenXR=True, expectedVersionCode=76, retry={
                    'version': 1, 'venueSha256': '1' * 64, 'mapSha256': '2' * 64, 'salt': '3' * 32,
                    'devices': [f'{index:064x}' for index in range(1, 26)]})
                release_path = root / 'release.json'
                release = json.loads(release_path.read_bytes())
                release['quest']['versionCode'] = 76
                release_path.write_text(json.dumps(release), encoding='utf-8')
                capture_path = root / manifest['questCaptures']['reports'][0]
                report = json.loads(capture_path.read_bytes())
                captures = {(row['roomId'], row['seat']): row for row in report['seats']}
                originals = []
                for index, row in enumerate(deployment['devices'], 1):
                    captured = captures[row['roomId'], row['seat']]
                    nonce, pid = f'{index:032x}', captured['logcatPid']
                    row.update(versionCode=76, openXR={'processId': pid, 'nonce': nonce})
                    marker = logcat_line(f'VR_QUEST_OPENXR nonce={nonce} loader=1 display=1 input=1', pid).encode()
                    source = capture_path.with_name(captured['log'])
                    raw = source.read_bytes()
                    source.write_bytes(marker + raw)
                    captured.update(bytes=len(marker + raw), sha256=hashlib.sha256(marker + raw).hexdigest())
                    originals.append((captured, source, marker, raw))
                deployment_path = root / 'deployment.json'
                deployment_path.write_text(json.dumps(deployment), encoding='utf-8')
                report['deploymentSha256'] = hashlib.sha256(deployment_path.read_bytes()).hexdigest()
                capture_path.write_text(json.dumps(report), encoding='utf-8')
                path.write_text(json.dumps(manifest), encoding='utf-8')
                accepted = field.verify_venue(path)
                self.assertEqual(25, accepted['questDeployment']['openXRSeatsVerified'])
                self.assertEqual(25, accepted['serverAcknowledgements'])
                self.assertFalse(accepted['physicalHostsVerified'])

                captured, source, marker, raw = originals[0]
                for changed, reason in ((raw, 'marker must precede the final result'),
                                        (raw + marker, 'marker must precede the final result'),
                                        (marker.replace(b'input=1', b'input=0') + raw, 'all subsystems ready'),
                                        (marker + marker + raw, 'lacks one matching original OpenXR launch marker')):
                    source.write_bytes(changed)
                    captured.update(bytes=len(changed), sha256=hashlib.sha256(changed).hexdigest())
                    capture_path.write_text(json.dumps(report), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, reason):
                        field.verify_venue(path)
                    manifest['requireQuestOpenXR'] = True
                    path.write_text(json.dumps(manifest), encoding='utf-8')
                    with self.assertRaises(field.QuestOpenXRIncomplete) as refused:
                        field.verify_venue(path)
                    self.assertEqual(24, refused.exception.coverage['verifiedSeats'])
                    [issue] = refused.exception.coverage['invalidReports']
                    self.assertEqual((captured['roomId'], captured['seat']), (issue['roomId'], issue['seat']))
                    self.assertIn(reason, issue['reason'])
                    manifest.pop('requireQuestOpenXR')
                    path.write_text(json.dumps(manifest), encoding='utf-8')
                source.write_bytes(marker + raw)
                captured.update(bytes=len(marker + raw), sha256=hashlib.sha256(marker + raw).hexdigest())
                capture_path.write_text(json.dumps(report), encoding='utf-8')
                manifest['requireQuestOpenXR'] = True
                path.write_text(json.dumps(manifest), encoding='utf-8')
                strict = field.verify_venue(path)
                self.assertEqual({'expectedSeats': 25, 'verifiedSeats': 25, 'missingSeats': [], 'invalidReports': []},
                                 strict['questOpenXR'])

    def test_quest_venue_device_proof_rejects_reuse_across_separate_deployments(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest = quest_capture_venue_fixture(root, mode, quest_per_room=2, batches=1)
                deployment = self.quest_deployment_evidence(root, manifest, 2)
                rows = deployment['devices']
                self.assertEqual(10, len(rows))
                scope = field.quest_venue_device_scope(mode, {row['sessionId'] for row in rows})
                serials = [f'PRIVATE-FIXTURE-HEADSET-{index}' for index in range(len(rows))]

                def proof(batch_number, source_serials, scope_digest=scope):
                    salt = f'{batch_number:032x}'
                    return {'version': 1, 'salt': salt, 'venueSha256': f'{batch_number:064x}', 'mapSha256': '1' * 64,
                            'devices': [field.quest_deployment_fingerprint(salt, value) for value in source_serials],
                            'venueDevices': {'scopeSha256': scope_digest,
                                             'devices': [field.quest_deployment_fingerprint(scope_digest, value)
                                                         for value in source_serials]}}

                waiting = dict(roomId=rows[1]['roomId'], seat=rows[1]['seat'], status='not-attempted')
                early = dict(deployment, complete=False, devices=[rows[0], waiting], retry=proof(1, serials[:2]))
                later = dict(deployment, devices=rows[1:], retry=proof(2, serials[1:]))
                (root / 'deployment.json').write_text(json.dumps(early), encoding='utf-8')
                later_path = root / 'independent-retry.json'
                later_path.write_text(json.dumps(later), encoding='utf-8')
                manifest['questDeployments']['reports'].append(later_path.name)
                path.write_text(json.dumps(manifest), encoding='utf-8')
                accepted = field.verify_venue(path)
                self.assertEqual(10, accepted['questDeployment']['venueDeviceSeatsVerified'])
                self.assertFalse(accepted['physicalHostsVerified'])
                self.assertNotIn('PRIVATE-FIXTURE-HEADSET', json.dumps(accepted))
                self.assertNotIn(scope, json.dumps(accepted))

                # A new mapping and a refreshed bundle still cannot reuse a launched headset.
                later['retry'] = proof(2, serials[:1] + serials[2:])
                later_path.write_text(json.dumps(later), encoding='utf-8')
                message = (f"room {rows[0]['roomId']} seat {rows[0]['seat']} "
                           f"and room {rows[1]['roomId']} seat {rows[1]['seat']}")
                with self.assertRaisesRegex(field.EvidenceError, f'reused the same device for {message}'):
                    field.verify_venue(path)

                later['retry'] = proof(2, serials[1:], 'c' * 64)
                later_path.write_text(json.dumps(later), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'different set of original sessions'):
                    field.verify_venue(path)

                later['retry'] = proof(2, serials[1:])
                later['retry'].pop('venueDevices')
                later_path.write_text(json.dumps(later), encoding='utf-8')
                compatibility = field.verify_venue(path)
                self.assertEqual(10, compatibility['questDeployment']['seatsVerified'])
                self.assertEqual(1, compatibility['questDeployment']['venueDeviceSeatsVerified'])

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
                legacy_path = root / 'legacy-partial-capture.json'
                rows = report['seats']
                failed = {key: rows[0][key] for key in ('roomId', 'seat', 'sessionId', 'port')}
                legacy_path.write_text(json.dumps({**report, 'complete': False, 'capturedSeats': len(rows) - 1,
                                                   'seats': [dict(failed, complete=False, reason='ADB ended'), *rows[1:]]}),
                                       encoding='utf-8')
                plan = {'topology': mode, 'venueSha256': deployment['retry']['venueSha256'],
                        'deploymentSha256': report['deploymentSha256'],
                        'seats': [dict(row, serial=f'mock-{index}') for index, row in enumerate(rows)]}
                retry = capture_tool.retry_capture_plan(plan, legacy_path)
                self.assertEqual(plan['seats'][:1], retry['seats'])
                self.assertEqual(plan['venueSha256'], retry['captureBinding']['venueSha256'])
                path.write_text(json.dumps({key: value for key, value in manifest.items() if key != 'questDeployments'}), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'original Quest deployment reports referenced'):
                    field.verify_venue(path)
                path.write_text(json.dumps(manifest), encoding='utf-8')
                original.write_bytes(original.read_bytes() + b'\n')
                with self.assertRaisesRegex(field.EvidenceError, 'exact completed Quest deployment report'):
                    field.verify_venue(path)

    def test_quest_captures_preserve_the_launched_prefix_of_an_incomplete_deployment(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest = quest_capture_venue_fixture(root, mode, quest_per_room=5, batches=1)
                capture_spec = manifest['questCaptures']
                capture_spec['deviceMap'] = observed_quest_capture_spec(root, capture_spec)['deviceMap']
                map_path = root / capture_spec['deviceMap']
                mapping = json.loads(map_path.read_bytes())
                serials = {(row['roomId'], row['seat']): row['serial'] for row in mapping['seats']}
                original = self.quest_deployment_evidence(root, manifest, 5)
                devices = original['devices']
                prefix, pending = devices[:12], devices[12:]

                def proof_for(rows, salt):
                    selected = {(row['roomId'], row['seat']): serials[row['roomId'], row['seat']] for row in rows}
                    return {'version': 1, 'venueSha256': '1' * 64, 'salt': salt,
                            'mapSha256': field.quest_deployment_map_fingerprint(salt, selected),
                            'devices': [hashlib.sha256(serial.encode()).hexdigest() for serial in selected.values()]}

                original['retry'] = proof_for(devices, '2' * 32)
                early = dict(original, complete=False, devices=prefix + [
                    {'roomId': row['roomId'], 'seat': row['seat'],
                     'status': 'deployment-failed' if index == 0 else 'not-attempted'}
                    for index, row in enumerate(pending)])
                (root / 'deployment.json').write_text(json.dumps(early), encoding='utf-8')
                early_hash = hashlib.sha256((root / 'deployment.json').read_bytes()).hexdigest()

                capture_path = root / capture_spec['reports'][0]
                capture = json.loads(capture_path.read_bytes())
                seats = {(row['roomId'], row['seat']): row for row in capture['seats']}
                initial_keys = {(row['roomId'], row['seat']) for row in prefix}
                early_rows = [row for key, row in seats.items() if key in initial_keys]
                later_rows = [row for key, row in seats.items() if key not in initial_keys]
                early_capture = dict(capture, partialDeployment=True, deploymentSha256=early_hash,
                                     expectedSeats=12, capturedSeats=12, seats=early_rows)
                capture_path.write_text(json.dumps(early_capture), encoding='utf-8')
                later_path = capture_path.with_name('capture-remaining.json')
                capture_spec['reports'].append(str(later_path.relative_to(root)))
                manifest['questDeployments']['reports'].append('deployment-remaining.json')
                path.write_text(json.dumps(manifest), encoding='utf-8')

                for cumulative in (True, False):
                    with self.subTest(cumulative=cumulative):
                        later = (dict(original, previousDeploymentSha256=early_hash) if cumulative
                                 else dict(original, devices=pending, retry=proof_for(pending, '3' * 32)))
                        later_deployment = root / 'deployment-remaining.json'
                        later_deployment.write_text(json.dumps(later), encoding='utf-8')
                        later_capture = dict(capture, expectedSeats=13, capturedSeats=13, seats=later_rows,
                                             deploymentSha256=hashlib.sha256(later_deployment.read_bytes()).hexdigest())
                        later_path.write_text(json.dumps(later_capture), encoding='utf-8')
                        result = field.verify_venue(path)
                        self.assertEqual((25, 25, 1, 2), tuple(result[key] for key in (
                            'questCaptureSeatsVerified', 'serverAcknowledgements',
                            'questPartialDeploymentsReferenced', 'questCaptureDeploymentReportsMatched')))
                        self.assertEqual(2, result['questDeployment']['deviceMapsMatched'])
                        self.assertEqual(int(cumulative), result['questDeployment'].get('retryReportsLinked', 0))
                        self.assertFalse(result['physicalHostsVerified'])

                # A capture cannot claim an unfinished seat even if a later report proves it was deployed.
                capture_path.write_text(json.dumps(dict(early_capture, expectedSeats=13, capturedSeats=13,
                                                        seats=[*early_rows, later_rows[0]])), encoding='utf-8')
                later_path.write_text(json.dumps(dict(later_capture, expectedSeats=12, capturedSeats=12,
                                                      seats=later_rows[1:])), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'Quest capture seat does not match its referenced deployment'):
                    field.verify_venue(path)
                capture_path.write_text(json.dumps(early_capture), encoding='utf-8')
                later_path.write_text(json.dumps(later_capture), encoding='utf-8')

                # The original report and explicit subset marker are both required.
                no_marker = {key: value for key, value in early_capture.items() if key != 'partialDeployment'}
                capture_path.write_text(json.dumps(no_marker), encoding='utf-8')
                with self.assertRaisesRegex(field.EvidenceError, 'exact completed Quest deployment report'):
                    field.verify_venue(path)
                capture_path.write_text(json.dumps(early_capture), encoding='utf-8')
                manifest['questCaptures']['reports'].pop()
                path.write_text(json.dumps(manifest), encoding='utf-8')
                with self.assertRaises(field.QuestCapturesIncomplete) as incomplete:
                    field.verify_venue(path)
                self.assertEqual(13, len(incomplete.exception.captures['missingSeats']))

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
    def test_venue_udp_reports_match_sealed_revision_without_the_network_plan(self):
        for mode in ('Independent', 'Linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, closure = venue_fixture(root, mode, with_journals=True, room_sizes=(1,) * 5)
                manifest['expectedPlayersPerRoom'] = 1
                groups, revisions = [], []
                for index, entry in enumerate(manifest['sessions'], 1):
                    archive = root / entry['evidenceZip']
                    session, stats, endpoint = field.management_zip(archive)
                    session['mission']['id'] = id_for(810 + index)
                    with zipfile.ZipFile(archive, 'w') as bundle:
                        for name, value in (('session', session), ('statistics', stats), ('endpoint', endpoint)):
                            bundle.writestr(name + '.json', json.dumps(value))
                    launcher_path = root / entry['launcherReport']
                    launcher = json.loads(launcher_path.read_bytes())
                    launcher['udpBinding']['observedAtUtc'] = '2026-11-08T23:59:59Z'
                    launcher_path.write_text(json.dumps(launcher), encoding='utf-8')
                    listener, probe = preflight_fixture(root, f'room-{index}', server=endpoint['address'],
                                                        peer=entry['players'][0]['address'], port=endpoint['port'])
                    groups.append({'roomIds': session['roomIds'], 'complete': True,
                                   'udpSourcePreflights': [{'listener': listener.name, 'probe': probe.name}]})
                    revisions.append({'roomIds': session['roomIds'], 'sessionId': session['id'],
                                      'missionId': session['mission']['id'], 'sessionSequence': 5})
                terminal, _, moved = self.terminal_venue_fixture(root, manifest, closure)
                packed = self.pack_venue(root, manifest)
                report = root / 'udp-batch.json'
                path.write_text(json.dumps(dict(packed, udpPreflightBatch=report.name)), encoding='utf-8')
                prepare = [sys.executable, str(SCRIPT.with_name('prepare-venue-field-manifest.py')),
                           '--venue-bundle', str(root / packed['venueBundle']), '--launcher-report', str(terminal),
                           '--server-work-root', str(moved), '--topology', 'same-host', '--server-ip', manifest['serverIps'][0],
                           '--players-per-room', '1', '--udp-preflight-batch', str(report)]
                for scope, digest in (('venue-udp-preflight-only', 'networkPlanSha256'), ('quest-udp-preflight-only', 'planSha256')):
                    with self.subTest(scope=scope):
                        batch = {'version': 1, 'scope': scope, 'mode': mode, 'complete': True, 'groups': groups,
                                 'networkPlanSessions': revisions, digest: 'a' * 64}
                        report.write_text(json.dumps(batch), encoding='utf-8')
                        verified = field.verify_venue(path)
                        self.assertEqual(len(groups), verified['udpSourcePreflightsVerified'])
                        self.assertEqual(5, verified['serverAcknowledgements'])
                        output = root / f'{scope}-accepted.json'
                        result = subprocess.run([*prepare, '--output', str(output)], capture_output=True, timeout=30)
                        self.assertEqual(0, result.returncode, result.stderr)

                        for key, changed in (('missionId', id_for(990)), ('sessionSequence', 6)):
                            edited = deepcopy(batch)
                            edited['networkPlanSessions'][-1][key] = changed
                            report.write_text(json.dumps(edited), encoding='utf-8')
                            with self.assertRaisesRegex(field.EvidenceError, 'UDP report launch revision differs from the sealed session'):
                                field.verify_venue(path)
                            denied = root / f'{scope}-denied.json'
                            result = subprocess.run([*prepare, '--output', str(denied)], capture_output=True, timeout=30)
                            self.assertEqual(1, result.returncode, result.stdout)
                            self.assertIn(b'UDP report launch revision differs from the sealed session', result.stderr)
                            self.assertFalse(denied.exists())

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
        seats = manifest.get('expectedPlayersPerRoom', 5)
        if seats != 5:
            venue['playersPerRoom'] = seats
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
                connections = io.BytesIO()
                with zipfile.ZipFile(connections, 'w', zipfile.ZIP_DEFLATED) as archive:
                    for seat in range(1, seats + 1):
                        archive.writestr(f'room-{room:02}-seat-{seat:02}.json', b'opaque private connection member')
                members[ticket] = connections.getvalue()
        return venue, members

    def write_alignment_bundle(self, path, venue, members):
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('venue.json', json.dumps(venue))
            for name, raw in members.items():
                archive.writestr(name, raw)

    def test_prepare_and_verify_original_deployment_zip_alignment(self):
        all_rooms = (1, 2, 3, 4, 5)
        for mode, mr_rooms in (('Independent', (2,)), ('Independent', all_rooms), ('Linked', all_rooms)):
            for seats in (1, 2, 5):
                with self.subTest(mode=mode, mr_rooms=mr_rooms, seats=seats), tempfile.TemporaryDirectory() as directory:
                    self.verify_original_deployment_zip_alignment(Path(directory), mode, mr_rooms, seats)

    def verify_original_deployment_zip_alignment(self, root, mode, mr_rooms, seats):
        path, manifest, closure = venue_fixture(root, mode, remote=True, with_journals=True, mr_rooms=mr_rooms, room_sizes=(seats,) * 5)
        if seats != 5:
            manifest['expectedPlayersPerRoom'] = seats
        venue, members = self.alignment_bundle_fixture(root, manifest)
        bundle = root / 'deployment.zip'
        self.write_alignment_bundle(bundle, venue, members)
        digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
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
                   '--room-alignment-bundle', bundle.name, '--players-per-room', str(seats), '--output', str(output)]
        prepared = subprocess.run(command, cwd=root, capture_output=True)
        self.assertEqual(0, prepared.returncode, prepared.stderr.decode())
        raw_output = output.read_bytes()
        self.assertNotIn(b'opaque private connection member', raw_output)
        generated = json.loads(raw_output)
        self.assertEqual(bundle.name, generated['roomAlignmentBundle'])
        self.assertEqual(digest, generated['roomAlignmentBundleSha256'])
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
        self.assertEqual(digest, result.pop('roomAlignmentBundleSha256'))
        self.assertEqual(original, result)
        self.assertEqual(len(mr_rooms), result['roomAlignmentsVerified'])
        self.assertEqual(5 * seats, result['serverAcknowledgements'])

        with zipfile.ZipFile(bundle, 'a') as archive:
            archive.comment = b'repacked after preparation'
        with self.assertRaisesRegex(field.EvidenceError, 'ZIP SHA-256 differs'):
            field.verify_venue(output)

    def test_staged_alignment_bundle_reports_missing_or_changed_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.staged_plan(root, remote=True, quest_links=True)
            folder = root / 'mr-pilot'
            folder.mkdir()
            rooms = (1, 2, 3, 4, 5)
            path, manifest, _ = venue_fixture(folder, 'Linked', remote=True, with_journals=True, mr_rooms=rooms,
                                              room_sizes=(1,) * 5, id_offset=99000, minutes_after=1)
            start = datetime.fromisoformat('2026-11-09T08:01:00+08:00')
            self.concurrent_journals(folder, manifest, [0], tracked=True, capture_start=start)
            self.add_shared_release(folder, manifest, 1)
            manifest.update(expectedPlayersPerRoom=1, minimumConcurrentMilliseconds=2000)
            bundle = folder / 'mr-pilot.zip'
            self.write_alignment_bundle(bundle, *self.alignment_bundle_fixture(folder, manifest))
            raw = bundle.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            manifest.update(roomAlignmentBundle=bundle.name, roomAlignmentBundleSha256=digest)
            manifest['sessions'][0].pop('roomAlignments')
            path.write_text(json.dumps(manifest), encoding='utf-8')
            plan['venueManifests'][1] = str(path.relative_to(root))
            total = root / 'stages.json'
            total.write_text(json.dumps(plan), encoding='utf-8')
            accepted = field.verify_venue_stages(total)
            self.assertEqual(80, accepted['serverAcknowledgements'])
            stage = accepted['stages'][1]
            self.assertEqual((digest, 5), (stage['roomAlignmentBundleSha256'], stage['roomAlignmentsVerified']))

            archive_path = folder / manifest['sessions'][0]['evidenceZip']
            original = archive_path.read_bytes()
            session, statistics, endpoint = field.management_zip(archive_path)
            session['players'][0]['seat'] = 1
            with zipfile.ZipFile(archive_path, 'w') as archive:
                for name, record in (('session', session), ('statistics', statistics), ('endpoint', endpoint)):
                    archive.writestr(name + '.json', json.dumps(record))
            with self.assertRaisesRegex(field.EvidenceError, 'Deployment ZIP seats differ from the original sealed roster'):
                field.verify_venue(path)
            archive_path.write_bytes(original)

            bundle.unlink()
            missing = field.verify_venue_stages(total, inspect=True)
            self.assertEqual({'kind': 'roomAlignmentBundle', 'name': bundle.name}, missing['issues'][0]['missingFile'])
            bundle.write_bytes(raw)
            with zipfile.ZipFile(bundle, 'a') as archive:
                archive.comment = b'changed after manifest preparation'
            changed = field.verify_venue_stages(total, inspect=True)
            self.assertEqual([2], changed['issues'][0]['entries'])
            self.assertEqual({'kind': 'roomAlignmentBundle', 'name': bundle.name, 'status': 'sha256-mismatch'},
                             changed['issues'][0]['evidenceMismatch'])

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
            for seats, message in ((2, 'seat count differs from the declared stage'), (True, 'requires 1, 2 or 5 seats')):
                self.write_alignment_bundle(bundle, dict(venue, playersPerRoom=seats), members)
                with self.assertRaisesRegex(field.EvidenceError, message):
                    field.verify_venue(path)
                rejected = subprocess.run(command, capture_output=True)
                self.assertEqual(1, rejected.returncode)
                self.assertIn(message.encode(), rejected.stderr)
                self.assertFalse(output.exists())
            alignment = 'room-02-alignment.json'
            wrong_stations = io.BytesIO()
            with zipfile.ZipFile(wrong_stations, 'w') as archive:
                for seat in range(2, 7):
                    archive.writestr(f'room-02-seat-{seat:02}.json', b'opaque')
            for changed, message in (
                ({name: raw for name, raw in members.items() if name != alignment}, 'alignment ZIP member for every MR room'),
                ({**members, 'extra.json': b'{}'}, 'Invalid MR or mixed deployment ZIP members'),
                ({**members, alignment: members[alignment].rstrip()}, 'bytes differ from the sealed session lock'),
                ({**members, 'room-02-connections.zip': wrong_stations.getvalue()}, 'room 2 connection files differ'),
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

    def test_single_session_cli_matches_quest_readiness_to_original_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, manifest, _ = venue_fixture(root, 'Independent', remote=True, quest_per_room=2, with_journals=True,
                                           room_sizes=(3,) * 5, game_server=True)
            entry = manifest['sessions'][0]
            session, stats, endpoint = field.management_zip(root / entry['evidenceZip'])
            started = datetime.fromisoformat(session['startedAtUtc'])
            captured = started - timedelta(seconds=1)
            launcher_path = root / entry['launcherReport']
            launcher = json.loads(launcher_path.read_bytes())
            journal = root / entry['worldJournal']
            bodies = [{'id': owner['id'], 'roomId': owner['roomId'], 'connected': True, 'health': 100,
                       'rig': {'kind': 'Tracked'}} for owner in session['players']]
            world_journal(journal, launcher['finalWorld'], capture_start=(captured - timedelta(milliseconds=100)).isoformat(),
                          players=lambda _, __: bodies)
            launcher_path.write_text(json.dumps(launcher), encoding='utf-8')
            command = [sys.executable, str(SCRIPT), '--topology', 'direct-lan', '--server-ip', manifest['serverIps'][0],
                       '--launcher-report', str(launcher_path), '--server-log', str(root / entry['serverLog'])]
            for name, record in [('session', session), ('statistics', stats), ('endpoint', endpoint)]:
                path = root / f'{name}.json'
                path.write_text(json.dumps(record), encoding='utf-8')
                command += ['--' + name, str(path)]
            for player in entry['players']:
                source = [player['address'], str(root / player['log'])]
                command += ['--quest-player', *source, str(player['logcatPid'])] if 'logcatPid' in player else ['--player', *source]

            def make_receipt(owner):
                identity = f"quest-player-readiness-v1/{session['id']}/{owner['id']}/{owner['admissionId']}"
                return {'evidenceVersion': 1, 'phase': 'tracked-readiness', 'scope': 'player', 'complete': True,
                        'sampledAtUtc': (captured + timedelta(milliseconds=50)).isoformat(),
                        'seats': [{'roomId': owner['roomId'], 'seat': owner['seat'] + 1, 'sessionId': session['id'],
                                   'admissionSha256': hashlib.sha256(identity.encode('ascii')).hexdigest(),
                                   'status': 'tracked-ready', 'sourceState': 'Fresh', 'worldSequence': 1,
                                   'observedSequence': 7, 'capturedAtUtc': captured.isoformat()}]}

            first_path, second_path = root / 'first.json', root / 'second.json'
            original = make_receipt(session['players'][1])
            first_path.write_text(json.dumps(original), encoding='utf-8')
            second_path.write_text(json.dumps(make_receipt(session['players'][2])), encoding='utf-8')
            receipts = ['--quest-readiness-report', str(second_path), '--quest-readiness-report', str(first_path)]
            world = ['--world-journal', str(journal)]

            def run(*args):
                return subprocess.run(command + list(args), capture_output=True, encoding='utf-8', timeout=10)

            result = run(*world, *receipts)
            self.assertEqual(0, result.returncode, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(2, report['questLogcatPlayers'])
            self.assertEqual([{'worldSequence': 1, 'observedSequence': 7, 'seatsVerified': 2}],
                             report['worldJournal']['questReadinessFrames'])
            self.assertNotIn('questReadinessFrames', json.loads(run(*world).stdout)['worldJournal'])
            self.assertNotIn(directory, result.stdout)
            self.assertNotIn(original['seats'][0]['admissionSha256'], result.stdout)

            for args, message in ((receipts, 'closed world journal'),
                                  (world + receipts[:2], 'one Quest readiness report per original Quest log'),
                                  (world + receipts[:2] * 2, 'Evidence paths must be distinct')):
                result = run(*args)
                self.assertEqual(1, result.returncode, result.stderr)
                self.assertIn(message, result.stderr)

            for changes, row_changes, replacement, message in (
                ({}, {'admissionSha256': 'b' * 64}, None, 'original admission'),
                ({}, {'worldSequence': 2}, None, 'original Preparing frame'),
                ({'sampledAtUtc': (started + timedelta(milliseconds=10)).isoformat()}, {}, None, 'before the original Begin'),
                ({'complete': False}, {}, None, 'completed single-player'),
                ({}, {}, 0, 'original Quest log for its admission'),
                ({}, {}, 2, 'distinct, fresh seat'),
            ):
                with self.subTest(message=message):
                    invalid = deepcopy(original) if replacement is None else make_receipt(session['players'][replacement])
                    invalid.update(changes)
                    invalid['seats'][0].update(row_changes)
                    first_path.write_text(json.dumps(invalid), encoding='utf-8')
                    result = run(*world, *receipts)
                    self.assertEqual(1, result.returncode, result.stderr)
                    self.assertIn(message, result.stderr)
                    self.assertNotIn(directory, result.stderr)

    def test_single_session_evidence_zip_verifies_saved_tracked_vr_opening(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, manifest, _ = venue_fixture(root, 'Independent', remote=True, quest_per_room=1, with_journals=True,
                                           room_sizes=(1,) * 5, game_server=True)
            entry = manifest['sessions'][0]
            values = field.management_zip(root / entry['evidenceZip'])
            session = values[0]
            owner, = session['players']
            launcher_path = root / entry['launcherReport']
            launcher = json.loads(launcher_path.read_bytes())
            journal = root / entry['worldJournal']
            departed = id_for(999)
            bodies = [{'id': player, 'roomId': 1, 'connected': True, 'health': 100, 'rig': {'kind': 'Tracked'}}
                      for player in (owner['id'], departed)]

            def journal_with(rig='Tracked', running_sequence=8):
                opening = [bodies[0], dict(bodies[1], rig={'kind': rig})]
                world_journal(journal, launcher['finalWorld'], running_sequence=running_sequence, end_sequence=9,
                              players=lambda number, _: opening if number == 1 else bodies[:1])
                launcher_path.write_text(json.dumps(launcher), encoding='utf-8')

            journal_with()
            evidence = {'version': 1, 'trackedVrStart': {'sessionId': session['id'], 'streamId': launcher['streamId'],
                'appliedAtSequence': 8, 'worldSequence': 1, 'elapsedMilliseconds': 100,
                'players': [{'playerId': body['id'], 'roomId': body['roomId']} for body in bodies]}}
            evidence_zip = root / 'original.zip'

            def pack(value=evidence, extra=None):
                with zipfile.ZipFile(evidence_zip, 'w') as archive:
                    for name, record in zip(('session.json', 'statistics.json', 'endpoint.json'), values):
                        archive.writestr(name, json.dumps(record))
                    if value is not None:
                        archive.writestr('tracked-vr-start.json', json.dumps(value))
                    if extra:
                        archive.writestr(extra, '{}')

            pack()
            quest, = entry['players']
            command = [sys.executable, str(SCRIPT), '--topology', 'direct-lan', '--server-ip', manifest['serverIps'][0],
                       '--launcher-report', str(launcher_path), '--server-log', str(root / entry['serverLog']),
                       '--quest-player', quest['address'], str(root / quest['log']), str(quest['logcatPid']),
                       '--evidence-zip', str(evidence_zip)]
            required = ['--world-journal', str(journal), '--require-tracked-vr-start']

            def run(*arguments, expected=1, message=None):
                result = subprocess.run(command + list(arguments), capture_output=True, encoding='utf-8', timeout=10)
                self.assertEqual(expected, result.returncode, result.stderr)
                self.assertNotIn(directory, result.stderr + result.stdout)
                if message is not None:
                    self.assertIn(message, result.stderr)
                return json.loads(result.stdout) if expected == 0 else None

            report = run(*required, expected=0)
            self.assertEqual(1, report['players'])
            self.assertEqual({'appliedAtSequence': 8, 'preparingFrame': 1, 'firstRunningFrame': 2, 'trackedPlayers': 2},
                             report['worldJournal']['trackedVrStart'])
            self.assertNotIn(departed, json.dumps(report))
            run(message='requires the original closed world journal')
            run(*required, '--session', str(root / 'mixed.json'), expected=2, message='Use --evidence-zip or all three')

            for modifications, message in (
                ({'streamId': id_for(998)}, 'original VR GameServer recording'),
                ({'worldSequence': 2}, 'original Preparing boundary'),
                ({'elapsedMilliseconds': 110}, 'original Preparing boundary'),
                ({'players': evidence['trackedVrStart']['players'][:1]}, 'Player count differs'),
            ):
                with self.subTest(modifications=modifications):
                    pack(dict(evidence, trackedVrStart=dict(evidence['trackedVrStart'], **modifications)))
                    run(*required, message=message)
            pack(extra='unrelated.json')
            run(*required, message='exactly the original JSON records')
            pack()
            journal_with(rig='Simulated')
            run(*required, message='original tracked roster')
            journal_with(running_sequence=7)
            run(*required, message='subsequent application')
            pack(None)
            self.assertNotIn('worldJournal', run(expected=0))
            run(*required, message='missing the original tracked VR opening evidence')

    def test_single_session_zip_recomputes_departed_scores_without_claiming_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, manifest, _ = venue_fixture(root, 'Independent', remote=True, quest_per_room=1, with_journals=True,
                                           room_sizes=(1,) * 5, game_server=True)
            entry = manifest['sessions'][0]
            session, stats, endpoint = field.management_zip(root / entry['evidenceZip'])
            owner, = session['players']
            retained = owner['id']
            departed = id_for(999)
            departure = {'playerId': departed, 'admissionId': id_for(998), 'roomId': 1, 'joinedAtSequence': 3, 'leftAtSequence': 8}
            evidence = {'version': 1, 'sessionId': session['id'], 'streamId': endpoint['streamId'], 'throughSequence': 9,
                        'endedAtSequence': 9, 'players': [departure]}
            stats.update(origin='GameServer', players=[*stats['players'], dict(stats['players'][0], playerId=departed, ammoUsed=1)])
            launcher_path = root / entry['launcherReport']
            launcher = json.loads(launcher_path.read_bytes())
            launcher['finalCombatStream']['acceptedSequence'] = 1
            session['combatStream'] = launcher['finalCombatStream']
            journal, battle = root / entry['worldJournal'], root / 'opening.journal'
            bodies = [{'id': pid, 'roomId': 1, 'connected': True, 'health': 100, 'rig': {'kind': 'Tracked'}}
                      for pid in (retained, departed)]

            def seal_world(late_departure=False):
                world_journal(journal, launcher['finalWorld'], combat=1, end_sequence=9,
                              players=lambda _, phase: bodies if phase != 'Ended' or late_departure else bodies[:1])
                launcher_path.write_text(json.dumps(launcher), encoding='utf-8')

            seal_world()
            shots = [(field.SHOT_FIRED, departed, id_for(997), None, 0)]
            combat_journal(battle, launcher, shots)
            quest, = entry['players']
            log_path = root / quest['log']
            log_path.write_text(log_path.read_text(encoding='utf-8').replace('"finalStreamSequence": 0', '"finalStreamSequence": 1'), encoding='utf-8')
            archive_path = root / 'field.zip'

            def pack(document=evidence):
                with zipfile.ZipFile(archive_path, 'w') as archive:
                    for name, record in [('session', session), ('statistics', stats), ('endpoint', endpoint)]:
                        archive.writestr(name + '.json', json.dumps(record))
                    if document is not None:
                        archive.writestr('roster-departures.json', json.dumps(document))

            pack()
            server_log = root / entry['serverLog']
            command = [sys.executable, str(SCRIPT), '--topology', 'direct-lan', '--server-ip', manifest['serverIps'][0],
                       '--launcher-report', str(launcher_path), '--server-log', str(server_log), '--evidence-zip', str(archive_path)]
            logs = ['--quest-player', quest['address'], str(log_path), str(quest['logcatPid'])]
            journals = ['--world-journal', str(journal), '--combat-journal', str(battle)]

            def run(args, expected=1, message=None):
                result = subprocess.run(command + args, capture_output=True, encoding='utf-8', timeout=10)
                self.assertEqual(expected, result.returncode, result.stderr)
                if message:
                    self.assertIn(message, result.stderr)
                self.assertNotIn(departed, result.stdout + result.stderr)
                return json.loads(result.stdout) if expected == 0 else None

            verified = run(logs + journals + ['--verify-player-sources'], expected=0)
            self.assertEqual({'scoresVerified': 1, 'endedAtSequence': 9}, verified['rosterDepartures'])
            self.assertEqual((1, 1, 2), (verified['players'], verified['serverAcknowledgements'], verified['combatJournal']['players']))
            run(logs + journals[:2], message='original closed combat and world journals')
            pack(None)
            run(logs + journals, message='Player count differs')
            pack(dict(evidence, players=[dict(departure, roomId=2)]))
            run(logs + journals, message='different room')
            pack()
            combat_journal(battle, launcher, shots, observed=8)
            run(logs + journals, message='outside the departed admission')
            combat_journal(battle, launcher, shots)
            seal_world(late_departure=True)
            run(logs + journals, message='connected departed player outside the original admission')

            # The historical server still records a LAN peer, but an empty terminal roster has no delivery witnesses.
            session['players'] = []
            removed = dict(departure, playerId=retained, admissionId=owner['admissionId'], joinedAtSequence=2, leftAtSequence=7)
            pack(dict(evidence, players=[departure, removed]))
            server_log.write_text(''.join(line + '\n' for line in server_log.read_text(encoding='utf-8').splitlines()
                                          if not line.startswith('VR_SERVER_DEBRIEF_ACK')), encoding='utf-8')
            world_journal(journal, launcher['finalWorld'], combat=1, end_sequence=9,
                          players=lambda _, phase: [bodies[1]] if phase != 'Ended' else [])
            launcher_path.write_text(json.dumps(launcher), encoding='utf-8')
            verified = run(journals, expected=0)
            self.assertEqual((0, 0, 2), (verified['players'], verified['serverAcknowledgements'], verified['rosterDepartures']['scoresVerified']))

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

    def test_quest_link_metrics_use_reconnected_seat_final_acknowledged_link(self):
        data = self.reconnect_history_fixture()
        data[3]['players'][1]['headset'] = 'Quest3'
        address, log = data[7].pop()
        pid = 7342
        old_link = insert_quest_link_metrics(quest_logcat(log.split('\n', 1)[1], pid=pid), pid, '8')
        final_link = insert_quest_link_metrics(old_link, pid, '2', reply_offset=10)

        report = field.verify(*data, quest_player_logs=[(address, final_link, pid)], verify_reconnect_history=True,
                              require_quest_link_metrics=True)
        self.assertEqual((1, 2, 30, 56), tuple(report['questLinkMetrics'][0][key]
                         for key in ('roomId', 'seat', 'attempts', 'p95RoundTripMs')))
        self.assertEqual(1, report['reconnectHistory']['retiredConnections'])

        with self.assertRaisesRegex(field.EvidenceError, 'Missing complete Quest link report'):
            field.verify(*data, quest_player_logs=[(address, old_link, pid)], verify_reconnect_history=True,
                         require_quest_link_metrics=True)

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

    def test_venue_guarded_pilot_requires_the_original_count_and_frame(self):
        for mode, count, kind, policy in (('Linked', 1, 'trackingBegin', 'verifyTrackingBegin'),
                                         ('Independent', 2, 'participationBegin', 'verifyParticipationBegin')):
            with self.subTest(mode=mode, count=count), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, manifest, batch = venue_fixture(root, mode, remote=True, with_journals=True, room_sizes=(count,) * 5,
                                                      mr_rooms=(2, 4) if mode == 'Independent' else ())
                manifest.update(expectedPlayersPerRoom=count, **{policy: True})
                path.write_text(json.dumps(manifest), encoding='utf-8')
                closure = root / manifest['closure']
                for entry, row in zip(manifest['sessions'], batch['sessions'], strict=True):
                    session, _, _ = field.management_zip(root / entry['evidenceZip'])
                    world = json.loads((root / entry['launcherReport']).read_bytes())['finalWorld']
                    rig = 'Tracked' if kind == 'trackingBegin' or session['environment']['mode'] == 'MR' else 'Simulated'
                    players = [{'id': p['id'], 'roomId': p['roomId'], 'connected': True, 'health': 100,
                                'rig': {'kind': rig}} for p in session['players']]
                    world_journal(root / entry['worldJournal'], world,
                                  players=lambda _, phase: players if phase == 'Preparing' else [], preparing_sequence=6)
                    row[kind] = {'requestId': id_for(999), 'appliedAtSequence': 7, 'playersPerRoom': count, 'frame': {
                        'streamId': world['header']['streamId'], 'worldSequence': 1, 'elapsedMilliseconds': 100}}
                closure.write_text(json.dumps({'batch': batch}), encoding='utf-8')
                result = field.verify_venue(path)[kind]
                self.assertEqual(count, result['playersPerRoom'])
                self.assertEqual(5 * count, result.get('participants', result['trackedPlayers']))
                witness = batch['sessions'][-1][kind]
                for changed in (None, 2 if count == 1 else 1):
                    if changed is None:
                        del witness['playersPerRoom']
                    else:
                        witness['playersPerRoom'] = changed
                    closure.write_text(json.dumps({'batch': batch}), encoding='utf-8')
                    with self.assertRaisesRegex(field.EvidenceError, 'Guarded Begin seats per room differ'):
                        field.verify_venue(path)

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
