import base64
import copy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
from threading import Event, Thread
import time
import unittest
import uuid
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ADB_FIXTURE = r"""
$remote = Join-Path $env:QUEST_TEST_ROOT 'remote'
[IO.File]::AppendAllText((Join-Path $env:QUEST_TEST_ROOT 'adb.log'), (($args -join ' ') + "`n"))
if ($args[0] -eq 'devices') {
    "List of devices attached"
    "other`tunauthorized"
    "fixture`tdevice"
    exit 0
}
if ($args[0] -ne '-s' -or $args[1] -ne 'fixture') { exit 99 }
switch ($args[2]) {
    'install' {
        if ($env:QUEST_TEST_ALTER_ALIGNMENT) {
            [IO.File]::WriteAllText($env:QUEST_TEST_ALTER_ALIGNMENT, '{}')
        }
        exit 0
    }
    'push' {
        Copy-Item -LiteralPath $args[3] -Destination (Join-Path $remote ($args[4].Split('/')[-1]))
        exit 0
    }
    'shell' {
        switch ($args[3]) {
            'getprop' {
                if ($env:QUEST_TEST_FAIL -eq 'getprop') { exit 1 }
                if ($env:QUEST_TEST_FAIL -eq 'model') { 'Quest 2' } else { 'Quest 3' }
                exit 0
            }
            'mv' {
                $name = $args[5].Split('/')[-1]
                if ($name -eq 'vr-connection.json' -and $env:QUEST_TEST_FAIL -eq 'config-move') { exit 1 }
                Move-Item -Force -LiteralPath (Join-Path $remote ($args[4].Split('/')[-1])) -Destination (Join-Path $remote $name)
                exit 0
            }
            'rm' {
                Remove-Item -LiteralPath (Join-Path $remote ($args[5].Split('/')[-1])) -ErrorAction SilentlyContinue
                exit 0
            }
            { $_ -in @('am', 'mkdir', 'monkey') } { exit 0 }
        }
    }
}
exit 98
"""


def make_ticket(room, seat, expiry, session=None, player=None, admission=None):
    payload = bytearray(75)
    payload[0], payload[49], payload[50] = 2, room, seat
    for offset, identity in ((1, session), (17, player), (33, admission)):
        if identity is not None:
            payload[offset:offset+16] = identity.bytes_le
    struct.pack_into('>q', payload, 51, expiry)
    def encode(value):
        return base64.urlsafe_b64encode(value).decode('ascii').rstrip('=')
    return f'v2.{encode(payload)}.{encode(bytes(32))}'


class QuestDeployTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='vr-quest-deploy-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.remote = self.root / 'remote'
        self.remote.mkdir()
        self.scripts = self.root / 'scripts'
        self.scripts.mkdir()
        self.script = self.scripts / 'deploy-quest.ps1'
        shutil.copyfile(ROOT / 'scripts' / self.script.name, self.script)
        self.adb = self.scripts / 'mock-adb.ps1'
        self.adb.write_text(ADB_FIXTURE, encoding='utf-8')
        self.commands = self.root / 'adb.log'
        self.config = self.root / 'player.json'
        self.plan = self.root / 'room.json'
        self.expiry = int(time.time()) + 240
        self.player = {'role':'Client', 'address':'192.168.1.10', 'port':7777, 'joinTicket':make_ticket(5, 1, self.expiry)}
        markers = [{'x':-2,'z':-2}, {'x':2,'z':-2}, {'x':0,'z':2}]
        self.alignment = {'version':1, 'profile':'room-floor-alignment-v1', 'roomId':5, 'withinTolerance':True,
                          'roomOrigin':{'x':28,'z':0}, 'markers':[
                              {'name':name,'room':point,'tracking':point.copy()} for name, point in zip('ABC',markers)]}
        self.write(self.config, self.player)
        self.write(self.plan, self.alignment)

    @staticmethod
    def write(path, document):
        path.write_text(json.dumps(document), encoding='utf-8')

    def run_script(self, *flags, failure='', alter=False):
        env = {**os.environ, 'QUEST_TEST_ROOT':str(self.root), 'QUEST_TEST_FAIL':failure,
               'QUEST_TEST_ALTER_ALIGNMENT':str(self.plan) if alter else ''}
        return subprocess.run(['pwsh','-NoProfile','-NonInteractive','-File',str(self.script),
                               '-ClientConfig',str(self.config),'-AdbPath',str(self.adb),*flags],
                              env=env, capture_output=True, encoding='utf-8', timeout=20)

    def run_mr(self, *flags, **kwargs):
        return self.run_script('-AlignmentFile', str(self.plan), '-MixedReality', *flags, **kwargs)

    def assert_rejected(self, result, message):
        self.assertNotEqual(0, result.returncode)
        self.assertIn(message, result.stderr)
        ticket = json.loads(self.config.read_text(encoding='utf-8'))['joinTicket']
        if ticket.startswith('v2.'):
            self.assertNotIn(ticket, result.stdout + result.stderr)

    def provision_apk(self):
        apk = self.root / 'artifacts/quest/VrCommand.apk'
        apk.parent.mkdir(parents=True)
        apk.write_bytes(b'mock APK')

    def test_preflight_is_offline_and_does_not_print_ticket(self):
        result = self.run_mr('-CheckOnly')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn(self.player['joinTicket'], result.stdout)
        value = json.loads(result.stdout)
        self.assertEqual({'roomId','seat','mode','expiresAtUtc','alignmentSha256'}, set(value))
        self.assertEqual((5,2,'MR'), (value['roomId'],value['seat'],value['mode']))
        self.assertEqual(hashlib.sha256(self.plan.read_bytes()).hexdigest(), value['alignmentSha256'])
        self.assertFalse(self.commands.exists())

    def test_plain_vr_and_passthrough_preflight(self):
        for mode, flags in (('VR', []), ('VR with passthrough', ['-Passthrough','-AlignmentFile',str(self.plan)])):
            with self.subTest(mode=mode):
                result = self.run_script('-CheckOnly', *flags)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(mode, json.loads(result.stdout)['mode'])
        self.assert_rejected(self.run_script('-CheckOnly', '-MixedReality'), 'requires a checked room alignment')
        self.assertFalse(self.commands.exists())

    def test_mismatched_room_is_rejected_before_device_access(self):
        self.provision_apk()
        self.write(self.config, {**self.player, 'joinTicket':make_ticket(1, 1, self.expiry)})
        self.assert_rejected(self.run_mr(), 'player ticket is for room 1; the alignment export is for room 5')
        self.assertFalse(self.commands.exists())

    def test_expired_invalid_and_server_config_are_rejected_before_adb(self):
        for value, message in (
                ({'joinTicket':make_ticket(5, 1, self.expiry - 300)}, 'Player ticket has expired'),
                ({'joinTicket':make_ticket(5, 5, self.expiry)}, 'Use a current v2 player ticket'),
                ({'joinTicket':'invalid'}, 'Use a current v2 player ticket'),
                ({'gameServerKey':'mock private credential'}, 'Use a player-only connection file'),
                ({'role':['Client']}, 'Use a player-only connection file'),
                ({'port':'7777'}, 'Use a player-only connection file')):
            with self.subTest(message=message, fields=list(value)):
                self.write(self.config, {**self.player, **value})
                self.assert_rejected(self.run_mr(), message)
        self.assertFalse(self.commands.exists())

    def test_invalid_alignment_structure_is_rejected_before_adb(self):
        for field, value in (('roomOrigin', {'x':14,'z':0}), ('withinTolerance', 'true'), ('markers', [])):
            with self.subTest(field=field):
                self.write(self.plan, {**self.alignment, field:value})
                self.assert_rejected(self.run_mr(), 'Use a checked room alignment JSON export')
        invalid = copy.deepcopy(self.alignment)
        invalid['markers'][1]['room']['z'] = 7
        self.write(self.plan, invalid)
        self.assert_rejected(self.run_mr(), 'Use the original A, B and C')
        self.assertFalse(self.commands.exists())

    def test_deploy_uses_exact_checked_alignment_bytes_before_launch(self):
        self.provision_apk()
        before = self.plan.read_bytes()
        digest = hashlib.sha256(before).hexdigest()
        result = self.run_mr(alter=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(b'{}', self.plan.read_bytes())
        self.assertEqual(before, (self.remote / f'vr-room-alignment-{digest}.json').read_bytes())
        configured = json.loads((self.remote / 'vr-connection.json').read_bytes())
        self.assertEqual({**self.player,'roomAlignmentSha256':digest,'questPassthrough':True,'requestMixedReality':True}, configured)
        commands = self.commands.read_text(encoding='utf-8').splitlines()
        self.assertEqual('devices', commands[0])
        self.assertIn('shell monkey', commands[-1])
        self.assertNotIn(self.player['joinTicket'], result.stdout + result.stderr + ''.join(commands))
        self.assertFalse(list(self.remote.glob('*.tmp')))

    def test_plain_vr_deploy_preserves_four_player_fields(self):
        self.provision_apk()
        result = self.run_script('-Serial','fixture')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(['vr-connection.json'], [path.name for path in self.remote.iterdir()])
        self.assertEqual(self.player, json.loads((self.remote / 'vr-connection.json').read_bytes()))

    def test_locked_mr_checks_exact_bytes_before_adb_and_infers_mr_for_deploy(self):
        self.provision_apk()
        original = self.plan.read_bytes()
        digest = hashlib.sha256(original).hexdigest()
        config = {**self.player, 'roomAlignmentSha256':digest}
        self.write(self.config, config)
        self.assert_rejected(self.run_script(), 'requires a checked room alignment')
        self.plan.write_bytes(original + b'\n')
        self.assert_rejected(self.run_script('-AlignmentFile',str(self.plan)), 'does not match the locked MR alignment for room 5')
        self.assertFalse(self.commands.exists())
        self.plan.write_bytes(original)
        checked = self.run_script('-CheckOnly','-AlignmentFile',str(self.plan))
        self.assertEqual(0, checked.returncode, checked.stderr)
        report = json.loads(checked.stdout)
        self.assertEqual(('MR',digest,True), (report['mode'],report['alignmentSha256'],report['alignmentPinsVerified']))
        self.assertFalse(self.commands.exists())
        result = self.run_script('-AlignmentFile',str(self.plan),alter=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(original, (self.remote / f'vr-room-alignment-{digest}.json').read_bytes())
        self.assertEqual({**config,'questPassthrough':True,'requestMixedReality':True},
                         json.loads((self.remote / 'vr-connection.json').read_bytes()))

    def test_invalid_locked_hash_is_rejected_before_adb(self):
        self.provision_apk()
        for value in (None, 'a' * 63, 'A' * 64):
            with self.subTest(value=value):
                self.write(self.config, {**self.player, 'roomAlignmentSha256':value})
                self.assert_rejected(self.run_script('-AlignmentFile',str(self.plan)), 'Use a valid locked MR alignment SHA-256')
        self.assertFalse(self.commands.exists())

    def test_failed_connection_activation_cleans_staging_and_keeps_existing_file(self):
        self.provision_apk()
        active = self.remote / 'vr-connection.json'
        active.write_bytes(b'previous configuration')
        self.assert_rejected(self.run_mr(failure='config-move'), 'Player connection file could not be activated')
        self.assertEqual(b'previous configuration', active.read_bytes())
        self.assertFalse(list(self.remote.glob('*.tmp')))
        commands = self.commands.read_text(encoding='utf-8')
        self.assertIn('shell rm -f', commands)
        self.assertNotIn('shell monkey', commands)

    def test_failed_or_wrong_device_identification_never_installs(self):
        self.provision_apk()
        for failure, message in (('getprop','Could not identify the selected Android device'), ('model','not a Meta Quest 3')):
            with self.subTest(failure=failure):
                self.assert_rejected(self.run_mr('-Serial','fixture',failure=failure), message)
        self.assertNotIn(' install ', self.commands.read_text(encoding='utf-8'))


class QuestVenueTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='vr-quest-venue-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / 'venue.json'
        self.expiry = int(time.time()) + 240
        self.session_ids = [uuid.uuid4() for _ in range(5)]
        self.players = [uuid.uuid4() for _ in range(25)]
        self.admissions = [uuid.uuid4() for _ in range(25)]

    def config(self, room, seat, session, port, **changes):
        index = (room - 1) * 5 + seat
        claims = {'session':session, 'player':self.players[index], 'admission':self.admissions[index],
                  'expiry':self.expiry}
        claims.update(changes)
        return {'role':'Client', 'address':'192.168.1.10', 'port':port,
                'joinTicket':make_ticket(room, seat, **claims)}

    def prepare(self, topology):
        manifest = {'version':1, 'topology':topology, 'rooms':[]}
        rooms = {}
        for room in range(1, 6):
            session, port = (self.session_ids[0], 7777) if topology == 'Linked' else (self.session_ids[room-1], 7776 + room)
            plan = self.root / f'calibration {room}.json'
            markers = [{'x':-2,'z':-2}, {'x':2,'z':-2}, {'x':0,'z':2}]
            plan.write_text(json.dumps({'version':1, 'profile':'room-floor-alignment-v1', 'roomId':room,
                'withinTolerance':True, 'roomOrigin':{'x':(room-3)*14,'z':0}, 'markers':[
                    {'name':name,'room':point,'tracking':point} for name, point in zip('ABC', markers)]}), encoding='utf-8')
            manifest['rooms'].append({'roomId':room, 'sessionId':str(session), 'ticketsZip':f'room {room}.zip',
                                      'alignmentFile':plan.name})
            rooms[room] = {f'room-{room:02}-seat-{seat+1:02}.json':self.config(room, seat, session, port) for seat in range(5)}
        return manifest, rooms

    def run_venue(self, manifest, rooms, *flags, environment=None):
        self.path.write_text(json.dumps(manifest), encoding='utf-8')
        for room, entries in rooms.items():
            with zipfile.ZipFile(self.root / f'room {room}.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in entries.items():
                    archive.writestr(name, data if isinstance(data, str) else json.dumps(data))
        return subprocess.run(['pwsh','-NoProfile','-NonInteractive','-File',str(ROOT / 'scripts/deploy-quest.ps1'),
                               '-VenueManifest',str(self.path),*flags], capture_output=True, encoding='utf-8', timeout=20, env=environment)

    def bundle(self, topology):
        manifest, seats = self.prepare(topology)
        files = {}
        for room in manifest['rooms']:
            room_id = room['roomId']
            original = b'\xef\xbb\xbf' + (self.root / room['alignmentFile']).read_bytes() + b'\r\n'
            room['alignmentFile'] = f'room-{room_id:02}-alignment.json'
            room['ticketsZip'] = f'room-{room_id:02}-connections.zip'
            files[room['alignmentFile']] = original
            tickets = io.BytesIO()
            with zipfile.ZipFile(tickets, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for name, config in seats[room_id].items():
                    config['roomAlignmentSha256'] = hashlib.sha256(original).hexdigest()
                    archive.writestr(name, json.dumps(config))
            files[room['ticketsZip']] = tickets.getvalue()
        files['venue.json'] = json.dumps(manifest).encode()
        return files, seats

    def vr_bundle(self, topology):
        manifest, seats = self.prepare(topology)
        manifest['mode'] = 'VR'
        files = {}
        for room in manifest['rooms']:
            room_id = room['roomId']
            room.pop('alignmentFile')
            room['ticketsZip'] = f'room-{room_id:02}-connections.zip'
            configs = seats[room_id]
            first = next(iter(configs.values()))
            room.update(address=first['address'], port=first['port'],
                        seats=[{'seat': seat, 'name': f'Player {room_id}/{seat}'} for seat in range(1, 6)])
            tickets = io.BytesIO()
            with zipfile.ZipFile(tickets, 'w') as archive:
                for name, config in configs.items():
                    archive.writestr(name, json.dumps(config))
            files[room['ticketsZip']] = tickets.getvalue()
        files['venue.json'] = json.dumps(manifest).encode()
        return files, seats

    def write_bundle(self, files):
        bundle = self.root / 'quest-mr-venue.zip'
        with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        return bundle

    def run_bundle(self, files, *flags, environment=None, script=ROOT / 'scripts/deploy-quest.ps1'):
        bundle = self.write_bundle(files)
        return subprocess.run(['pwsh','-NoProfile','-NonInteractive','-File',str(script),
                               '-VenueBundle',str(bundle),*flags], capture_output=True, encoding='utf-8', timeout=20, env=environment)

    def mixed_bundle(self):
        files, _ = self.vr_bundle('Independent')
        mr, _ = self.bundle('Independent')
        manifest = json.loads(files['venue.json'])
        manifest.update(version=2, mode='Mixed')
        for room in manifest['rooms']:
            room.pop('seats')
            room_id = room['roomId']
            room['mode'] = 'MR' if room_id in (2, 4) else 'VR'
            if room['mode'] == 'MR':
                room['alignmentFile'] = f'room-{room_id:02}-alignment.json'
                for name in (room['alignmentFile'], room['ticketsZip']):
                    files[name] = mr[name]
        files['venue.json'] = json.dumps(manifest)
        return files, manifest

    def test_mixed_bundle_requires_mode_specific_files_and_independent_rooms(self):
        files, manifest = self.mixed_bundle()
        preview = self.run_bundle(files)
        self.assertEqual(0, preview.returncode, preview.stderr)
        result = json.loads(preview.stdout)
        self.assertEqual(('Mixed', 'Independent', 25, True),
                         (result['mode'], result['topology'], result['seats'], result['alignmentPinsVerified']))
        self.assertEqual(['VR', 'MR', 'VR', 'MR', 'VR'], [room['mode'] for room in result['rooms']])
        self.assert_rejected(self.run_bundle(dict(files, **{'extra.json': '{}'})), 'exactly one alignment')
        changed = dict(files)
        changed['room-02-alignment.json'] += b'\r\n'
        self.assert_rejected(self.run_bundle(changed), 'alignment')
        manifest['topology'] = 'Linked'
        self.assert_rejected(self.run_bundle(dict(files, **{'venue.json': json.dumps(manifest)})), 'original topology')

    def device_map(self):
        path = self.root / 'device-map.json'
        document = {'version': 1, 'seats': [{'roomId': room, 'seat': seat, 'serial': f'fixture-{(room-1)*5+seat:02}'}
                                          for room in range(1, 6) for seat in range(1, 6)]}
        document['seats'].reverse()
        path.write_text(json.dumps(document), encoding='utf-8')
        return path, document

    def mock_capture_devices(self, rows, topology, *, held=False, wrong_seat=None):
        expected = {}
        for row in rows:
            room, seat, serial = row['roomId'], row['seat'], row['serial']
            index = (room - 1) * 5 + seat - 1
            session = self.session_ids[0] if topology == 'Linked' else self.session_ids[room - 1]
            port = 7777 if topology == 'Linked' else 7776 + room
            result = {'version': 1, 'roomId': room, 'sessionId': str(session), 'playerId': str(self.players[index]),
                      'admissionId': str(uuid.uuid4() if (room, seat) == wrong_seat else self.admissions[index])}
            def line(message):
                return f'11-09 14:30:00.000 7342 14325 I Unity   : {message}\r\n'.encode()
            startup = line(f'VR_NETWORK_STARTED role=Client started=True background=False port={port}')
            ending = line(f'VR_CLIENT_CONNECTED id={index+1}') + line('VR_CLIENT_DEBRIEF_FINAL ' + json.dumps(result)) + line('VR_CLIENT_DISCONNECTED')
            # Python's -s flag makes this relative filename stand in for the ADB serial.
            (self.root / serial).write_text(f'''import sys, time
from pathlib import Path
if sys.argv[1:] == ['shell', 'pidof', 'com.vrcommand.quest']:
    print(7342)
else:
    assert sys.argv[1:] == ['logcat', '-b', 'main', '--pid=7342', '-v', 'threadtime', '-s', 'Unity:I']
    sys.stdout.buffer.write({startup!r})
    sys.stdout.buffer.flush()
    until = time.monotonic() + 25
    while {held!r} and not Path('release').exists() and time.monotonic() < until:
        time.sleep(.05)
    sys.stdout.buffer.write({ending!r})
    sys.stdout.buffer.flush()
    time.sleep(60)
''', encoding='utf-8')
            expected[room, seat] = (str(session), port, startup + ending)
        return expected

    def capture_command(self, files, mapping, output, *flags):
        return [sys.executable, str(ROOT/'scripts/capture-quest-field-log.py'), '--adb', sys.executable,
                '--venue-bundle', str(self.write_bundle(files)), '--device-map', str(mapping),
                '--output-directory', str(output), '--seconds', '35', *flags]

    def test_venue_capture_starts_all_25_before_end_and_preserves_original_logs(self):
        self.expiry = int(time.time()) - 1
        files, configs = self.vr_bundle('Linked')
        mapping, document = self.device_map()
        expected = self.mock_capture_devices(document['seats'], 'Linked', held=True)
        output = self.root / 'capture all'
        command = self.capture_command(files, mapping, output)
        lines, ready = [], Event()
        with subprocess.Popen(command, cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8') as process:
            def collect():
                for line in process.stderr:
                    lines.append(line)
                    if 'venue-capture-ready' in line:
                        ready.set()
            collector = Thread(target=collect)
            collector.start()
            try:
                self.assertTrue(ready.wait(20), lines)
                self.assertFalse((output/'capture-report.json').exists())
                self.assertEqual(25, len(list(output.glob('*.partial'))))
                self.assertEqual(25, sum(json.loads(line)['stage']=='capture-ready' for line in lines))
            finally:
                (self.root/'release').touch()
                process.wait(timeout=25)
                collector.join(timeout=5)
            stdout = process.stdout.read()
            self.assertEqual(0, process.returncode, lines)
        report = json.loads((output/'capture-report.json').read_text(encoding='utf-8'))
        self.assertEqual((True, 'Linked', 25, 25), (report['complete'], report['topology'], report['expectedSeats'], report['capturedSeats']))
        self.assertEqual(sorted(expected), [(row['roomId'], row['seat']) for row in report['seats']])
        for row in report['seats']:
            session, port, original = expected[row['roomId'], row['seat']]
            self.assertEqual((session, port, 7342, len(original), hashlib.sha256(original).hexdigest()),
                             (row['sessionId'], row['port'], row['logcatPid'], row['bytes'], row['sha256']))
            self.assertEqual(original, (output/row['log']).read_bytes())
        self.assertFalse(list(output.glob('*.partial')))
        self.assertEqual(25, json.loads(stdout)['capturedSeats'])
        for private in (configs[1]['room-01-seat-01.json']['joinTicket'], 'fixture-01', str(self.root)):
            self.assertNotIn(private, stdout + ''.join(lines) + json.dumps(report))

    def test_partial_mixed_capture_keeps_success_and_rejects_wrong_admission(self):
        files, _ = self.mixed_bundle()
        mapping, document = self.device_map()
        document['seats'] = [row for row in document['seats'] if (row['roomId'], row['seat']) in {(2, 3), (5, 4)}]
        mapping.write_text(json.dumps(document), encoding='utf-8')
        self.mock_capture_devices(document['seats'], 'Independent', wrong_seat=(2, 3))
        output = self.root/'partial capture'
        command = self.capture_command(files, mapping, output)
        missing_flag = subprocess.run(command, cwd=self.root, capture_output=True, encoding='utf-8', timeout=15)
        self.assertEqual(1, missing_flag.returncode)
        self.assertFalse(output.exists())
        result = subprocess.run([*command, '--allow-partial-map'], cwd=self.root, capture_output=True, encoding='utf-8', timeout=20)
        self.assertEqual(1, result.returncode, result.stderr)
        report = json.loads((output/'capture-report.json').read_text(encoding='utf-8'))
        self.assertEqual((False, 'Independent', 2, 1), (report['complete'], report['topology'], report['expectedSeats'], report['capturedSeats']))
        failed, completed = report['seats']
        self.assertEqual((2, 3, False), (failed['roomId'], failed['seat'], failed['complete']))
        self.assertIn('differs from the original player admission', failed['reason'])
        self.assertTrue((output/failed['partial']).is_file())
        self.assertEqual((5, 4, True), (completed['roomId'], completed['seat'], completed['complete']))
        self.assertTrue((output/completed['log']).is_file())
        self.assertFalse((output/'room-02-seat-03-logcat.txt').exists())
        self.assertEqual(1, json.loads(result.stdout)['capturedSeats'])
        before = {path.name: path.read_bytes() for path in output.iterdir()}
        repeat = subprocess.run([*command, '--allow-partial-map'], cwd=self.root, capture_output=True, encoding='utf-8', timeout=20)
        self.assertEqual(1, repeat.returncode)
        self.assertNotIn('capture-ready', repeat.stderr)
        self.assertEqual(before, {path.name: path.read_bytes() for path in output.iterdir()})

    def run_fleet(self, files, mapping, *flags, faults=None, environment=None):
        env = {**os.environ, **(environment or {}), 'VR_QUEST_FLEET_FIXTURE': str(self.root), 'VR_QUEST_FLEET_FAULTS': json.dumps(faults or {})}
        return self.run_bundle(files, '-DeviceMap', str(mapping), '-ExpectedVersionCode', '61', '-AdbPath',
                               str(ROOT / 'tests/fixtures/mock-quest-fleet.ps1'), *flags, environment=env)

    def assert_rejected(self, result, message):
        self.assertNotEqual(0, result.returncode)
        self.assertIn(message, result.stderr)
        self.assertEqual('', result.stdout)
        self.assertNotIn('v2.', result.stderr)

    def test_tracked_readback_uses_original_admissions_and_one_snapshot_per_session(self):
        snapshots, seats, calls = {}, [], []
        topology = 'Independent'
        fixture_key = 'private-readiness-fixture-key'

        class Handler(BaseHTTPRequestHandler):
            def reply(self, payload, status=200):
                calls.append((self.command, self.path, self.headers.get('Authorization')))
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())

            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.reply({'topology': topology, 'allMatched': True, 'seats': seats})

            def do_GET(self):
                snapshot = snapshots[self.path.split('/')[3]]
                self.reply(snapshot, 503 if snapshot is None else 200)

            def log_message(self, *args):
                pass

        with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            args = ('-VerifyTrackedSeats', '-ManagementApi', f'http://127.0.0.1:{server.server_port}',
                    '-AdbPath', str(self.root / 'absent-adb.exe'))
            env = {**os.environ, 'VR_COMMAND_MASTER_KEY': fixture_key}
            try:
                for topology in ('Independent', 'Linked'):
                    with self.subTest(topology=topology):
                        files, _ = self.vr_bundle(topology)
                        calls.clear()
                        snapshots.clear()
                        seats.clear()
                        for room in range(1, 6):
                            session = str(self.session_ids[0 if topology == 'Linked' else room - 1])
                            snapshot = snapshots.setdefault(session, {'version': 1, 'sessionId': session,
                                'sourceState': 'Fresh', 'origin': 'Simulation', 'worldSequence': 32,
                                'sessionSequence': 12, 'observedSequence': 12, 'players': []})
                            for seat in range(5):
                                index = (room - 1) * 5 + seat
                                seats.append({'roomId': room, 'seat': seat, 'status': 'matched',
                                              'headset': 'ViveXr' if index == 1 else 'Quest3'})
                                snapshot['players'].append({'roomId': room, 'seat': seat,
                                    'playerId': str(self.players[index]), 'admissionId': str(self.admissions[index]),
                                    'state': 'Participating', 'canParticipate': True, 'rigKind': 'Tracked'})
                        result = self.run_bundle(files, *args, environment=env)
                        self.assertEqual(0, result.returncode, result.stderr)
                        report = json.loads(result.stdout)
                        self.assertEqual((topology, 'tracked-readiness', True, 24),
                                         (report['topology'], report['phase'], report['complete'], len(report['seats'])))
                        self.assertTrue(all(row['status'] == 'tracked-ready' for row in report['seats']))
                        self.assertNotIn((1, 2), [(row['roomId'], row['seat']) for row in report['seats']])
                        self.assertEqual([('POST', '/api/vr-deployment/venue-check', 'Bearer ' + fixture_key)] + [
                            ('GET', f'/api/sessions/{session}/readiness', 'Bearer ' + fixture_key) for session in snapshots], calls)

                sample = snapshots[str(self.session_ids[0])]
                sample['players'][0]['rigKind'] = 'Simulated'
                sample['players'][2]['admissionId'] = str(uuid.uuid4())
                sample['players'][3].update(state='PoseUnavailable', canParticipate=False)
                sample['players'][-1] = sample['players'][4]
                calls.clear()
                mapping, document = self.device_map()
                document['seats'] = [row for row in document['seats'] if row['roomId'] == 1]
                mapping.write_text(json.dumps(document), encoding='utf-8')
                result = self.run_bundle(files, *args, '-DeviceMap', str(mapping), '-AllowPartialMap', environment=env)
                self.assertEqual(1, result.returncode, result.stderr)
                self.assertEqual(['not-tracked', 'seat-headset-mismatch', 'admission-changed', 'awaiting-tracked-pose', 'readiness-invalid'],
                                 [row['status'] for row in json.loads(result.stdout)['seats']])
                self.assertEqual(2, len(calls))
                self.assertFalse((self.root / 'adb.log').exists())
                for value in (fixture_key, 'fixture-01', str(self.players[0]), str(self.admissions[0]), 'v2.'):
                    self.assertNotIn(value, result.stdout + result.stderr)

                for changes, status in (({'sourceState': 'Stale'}, 'source-not-fresh'),
                                        ({'observedSequence': 11}, 'source-revision-pending'),
                                        ({'sessionId': str(uuid.uuid4())}, 'readiness-invalid'),
                                        (None, 'readiness-unavailable')):
                    with self.subTest(status=status):
                        snapshots[str(self.session_ids[0])] = {**sample, **changes} if changes is not None else None
                        result = self.run_bundle(files, *args, '-DeviceMap', str(mapping), '-AllowPartialMap', environment=env)
                        self.assertEqual(1, result.returncode, result.stderr)
                        self.assertEqual(status, json.loads(result.stdout)['seats'][0]['status'])
                self.assert_rejected(self.run_bundle(files, *args, '-DeployMappedSeats', environment=env),
                                     'omit deployment and device-check')
            finally:
                server.shutdown()
                thread.join(timeout=5)

    def test_bundle_preflight_and_seat_selection_need_no_extraction_or_adb(self):
        for topology in ('Linked', 'Independent'):
            with self.subTest(topology=topology):
                files, _ = self.bundle(topology)
                result = self.run_bundle(files)
                self.assertEqual(0, result.returncode, result.stderr)
                venue = json.loads(result.stdout)
                self.assertEqual((topology, 25, True), (venue['topology'], venue['seats'], venue['alignmentPinsVerified']))
                result = self.run_bundle(files, '-RoomId', '5', '-Seat', '2', '-CheckOnly')
                self.assertEqual(0, result.returncode, result.stderr)
                seat = json.loads(result.stdout)
                self.assertEqual((5, 2, 'MR'), (seat['roomId'], seat['seat'], seat['mode']))
                self.assertEqual(hashlib.sha256(files['room-05-alignment.json']).hexdigest(), seat['alignmentSha256'])
                self.assertNotIn('v2.', result.stdout)
        self.assertEqual({'quest-mr-venue.zip', *(f'calibration {i}.json' for i in range(1, 6))}, {file.name for file in self.root.iterdir()})
        self.assert_rejected(self.run_bundle(files, '-RoomId', '5'), 'Specify both -RoomId and -Seat')
        self.assert_rejected(self.run_bundle(files, '-Serial', 'fixture'), 'Specify -RoomId and -Seat')
        self.assert_rejected(self.run_bundle(files, '-RoomId', '5', '-Seat', '2'), 'Specify -Serial')

    def test_vr_bundle_previews_both_topologies_and_requires_live_check_to_write(self):
        for topology in ('Linked', 'Independent'):
            with self.subTest(topology=topology):
                files, _ = self.vr_bundle(topology)
                result = self.run_bundle(files)
                self.assertEqual(0, result.returncode, result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual((topology, 'VR', 25), (report['topology'], report['mode'], report['seats']))
                self.assertNotIn('alignmentPinsVerified', report)
                selected = self.run_bundle(files, '-RoomId', '5', '-Seat', '2', '-CheckOnly')
                self.assertEqual(0, selected.returncode, selected.stderr)
                seat = json.loads(selected.stdout)
                self.assertEqual((5, 2, 'VR', None), (seat['roomId'], seat['seat'], seat['mode'], seat['alignmentSha256']))
                self.assertNotIn('v2.', result.stdout + selected.stdout)
                self.assert_rejected(self.run_bundle(files, '-RoomId', '5', '-Seat', '2', '-Serial', 'fixture-22'),
                                     'requires -ManagementApi')

    def test_vr_bundle_rejects_mismatched_manifest_and_mr_config(self):
        files, _ = self.vr_bundle('Independent')
        manifest = json.loads(files['venue.json'])
        manifest['rooms'][3]['port'] = 8888
        self.assert_rejected(self.run_bundle({**files, 'venue.json': json.dumps(manifest)}), 'VR manifest endpoint')
        with zipfile.ZipFile(io.BytesIO(files['room-04-connections.zip'])) as archive:
            entries = {name: json.loads(archive.read(name)) for name in archive.namelist()}
        entries['room-04-seat-02.json']['roomAlignmentSha256'] = 'f' * 64
        replacement = io.BytesIO()
        with zipfile.ZipFile(replacement, 'w') as archive:
            for name, config in entries.items():
                archive.writestr(name, json.dumps(config))
        self.assert_rejected(self.run_bundle({**files, 'room-04-connections.zip': replacement.getvalue()}), 'needs a VR connection file')

    def test_vr_fleet_validates_current_headsets_and_writes_only_original_configs(self):
        files, configs = self.vr_bundle('Linked')
        mapping, document = self.device_map()
        calls = []
        headset = ['ViveXr']
        stale = [False]

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                calls.append((self.path, self.headers['Authorization'], json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                payload = {'topology': 'Linked', 'allMatched': not stale[0], 'seats': [
                    {'roomId': room, 'seat': seat, 'status': 'admission-changed' if stale[0] and (room, seat) == (2, 1) else 'matched',
                     'headset': headset[0] if (room, seat) == (2, 1) else 'Quest3'}
                    for room in range(1, 6) for seat in range(5)]}
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())

            def log_message(self, *args):
                pass

        with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f'http://127.0.0.1:{server.server_port}'
                env = {'VR_COMMAND_MASTER_KEY': 'private-fixture-master'}
                rejected = self.run_fleet(files, mapping, '-DeployMappedSeats', '-ManagementApi', url, environment=env)
                self.assertEqual(1, rejected.returncode, rejected.stderr)
                report = json.loads(rejected.stdout)
                self.assertEqual('seat-headset-mismatch', report['devices'][6]['status'])
                self.assertFalse(any(self.root.glob('fixture-*')))
                selected = [row for row in document['seats'] if row['serial'] in {'fixture-01','fixture-13','fixture-24'}]
                mapping.write_text(json.dumps({'version': 1, 'seats': selected}), encoding='utf-8')
                stale[0] = True
                blocked = self.run_fleet(files, mapping, '-AllowPartialMap', '-DeployMappedSeats', '-ManagementApi', url, environment=env)
                self.assert_rejected(blocked, 'Room 2 seat 2: admission-changed')
                self.assertFalse(any(self.root.glob('fixture-*')))
                stale[0] = False
                (self.root / 'adb.log').unlink()
                partial = self.run_fleet(files, mapping, '-AllowPartialMap', '-DeployMappedSeats', '-ManagementApi', url,
                                         faults={'fixture-07': 'offline', 'fixture-25': 'wrong-model'}, environment=env)
                self.assertEqual(0, partial.returncode, partial.stderr)
                report = json.loads(partial.stdout)
                self.assertEqual((True, True, 3, 22), (report['complete'], report['managementVerified'], report['mappedSeats'], report['unmappedSeats']))
                self.assertEqual([(1, 1), (3, 3), (5, 4)], [(row['roomId'], row['seat']) for row in report['devices']])
                self.assertTrue(all(row['status'] == 'launch-requested' for row in report['devices']))
                self.assertEqual({'fixture-01','fixture-13','fixture-24'}, {file.name for file in self.root.glob('fixture-*')})
                for row in selected:
                    room, seat = row['roomId'], row['seat']
                    self.assertEqual(configs[room][f'room-{room:02}-seat-{seat:02}.json'],
                                     json.loads((self.root / row['serial'] / 'vr-connection.json').read_bytes()))
                commands = (self.root / 'adb.log').read_text(encoding='utf-8').splitlines()
                self.assertEqual({'fixture-01','fixture-13','fixture-24'}, {line.split()[1] for line in commands if line.startswith('-s ')})
                self.assertEqual(3, sum(' shell monkey ' in line for line in commands))
                self.assertNotIn('private-fixture-master', partial.stdout)
                self.assertNotIn('v2.', partial.stdout)
                mapping.write_text(json.dumps(document), encoding='utf-8')
                headset[0] = 'Quest3'
                applied = self.run_fleet(files, mapping, '-DeployMappedSeats', '-ManagementApi', url, environment=env)
                self.assertEqual(0, applied.returncode, applied.stderr)
                self.assertTrue(json.loads(applied.stdout)['complete'])
            finally:
                server.shutdown()
                thread.join()
        self.assertEqual(4, len(calls))
        for route, key, proof in calls:
            self.assertEqual(('/api/vr-deployment/venue-check', 'Bearer private-fixture-master'), (route, key))
            for room in proof['rooms']:
                self.assertEqual({'roomId', 'sessionId', 'connectionFiles'}, set(room))
                self.assertEqual(list(configs[room['roomId']].values()),
                                 [json.loads(base64.b64decode(raw)) for raw in room['connectionFiles']])
        for index in range(25):
            room, seat = index // 5 + 1, index % 5 + 1
            device = self.root / f'fixture-{index+1:02}'
            self.assertEqual({'vr-connection.json'}, {file.name for file in device.iterdir()})
            self.assertEqual(configs[room][f'room-{room:02}-seat-{seat:02}.json'],
                             json.loads((device / 'vr-connection.json').read_text(encoding='utf-8')))

    def test_device_map_rejects_missing_duplicate_or_unsafe_assignments_before_adb(self):
        files, _ = self.bundle('Linked')
        path, document = self.device_map()
        for edit, message in (
            (lambda rows: rows.pop(), 'exactly 25 seats'),
            (lambda rows: rows[0].update(roomId=rows[1]['roomId'], seat=rows[1]['seat']), 'mapped more than once'),
            (lambda rows: rows[0].update(serial=rows[1]['serial']), 'repeats an ADB serial'),
            (lambda rows: rows[0].update(serial='fixture-25;other'), 'exact ADB serial'),
        ):
            with self.subTest(message=message):
                invalid = copy.deepcopy(document)
                edit(invalid['seats'])
                path.write_text(json.dumps(invalid), encoding='utf-8')
                self.assert_rejected(self.run_fleet(files, path), message)
        self.assert_rejected(self.run_fleet(files, path, '-DeployMappedSeats'), 'requires -ManagementApi')
        self.assertFalse((self.root / 'adb.log').exists())

    def test_partial_map_requires_opt_in_and_rejects_invalid_counts_and_duplicates(self):
        files, _ = self.bundle('Independent')
        path, document = self.device_map()
        self.assert_rejected(self.run_bundle(files, '-AllowPartialMap'), 'Specify -DeviceMap')
        for seats, message in [
            ([], '1 to 25 seats'),
            ([*document['seats'], document['seats'][0]], '1 to 25 seats'),
            ([document['seats'][0]] * 2, 'mapped more than once'),
            ([document['seats'][0], {**document['seats'][1], 'serial': document['seats'][0]['serial']}], 'repeats an ADB serial'),
        ]:
            with self.subTest(message=message):
                path.write_text(json.dumps({'version': 1, 'seats': seats}), encoding='utf-8')
                self.assert_rejected(self.run_fleet(files, path, '-AllowPartialMap', '-CheckOnly'), message)
        path.write_text(json.dumps({'version': 1, 'seats': document['seats'][:1]}), encoding='utf-8')
        self.assert_rejected(self.run_fleet(files, path, '-CheckOnly'), 'exactly 25 seats')
        self.assert_rejected(self.run_fleet(files, path, '-AllowPartialMap', '-DeployMappedSeats'), 'requires -ManagementApi')
        self.assertFalse((self.root / 'adb.log').exists())
        result = self.run_fleet(files, path, '-AllowPartialMap', '-CheckOnly')
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(('Independent', 'preflight', True, True, 1, 24),
                         (report['topology'], report['phase'], report['complete'], report['alignmentPinsVerified'],
                          report['mappedSeats'], report['unmappedSeats']))
        self.assertNotIn('managementVerified', report)
        self.assertEqual([{'roomId': 5, 'seat': 5, 'status': 'ready', 'versionCode': 61}], report['devices'])
        self.assertFalse(any(self.root.glob('fixture-*')))

    def test_partial_mr_deployment_preserves_original_pins_on_selected_devices(self):
        files, configs = self.bundle('Linked')
        mapping, document = self.device_map()
        selected = [row for row in document['seats'] if row['serial'] in {'fixture-03','fixture-22'}]
        mapping.write_text(json.dumps({'version': 1, 'seats': selected}), encoding='utf-8')
        session = str(self.session_ids[0])
        calls = []
        readiness = {'version': 1, 'sessionId': session, 'sessionSequence': 27, 'observedSequence': 27,
                     'worldSequence': 14, 'sourceState': 'Fresh', 'origin': 'GameServer', 'mrStartState': 'WaitingPlayers',
                     'players': [{'roomId': row['roomId'], 'seat': row['seat'] - 1, 'state': 'Participating',
                                  'rigKind': 'Tracked', 'canParticipate': True,
                                  'playerId': str(self.players[(row['roomId'] - 1) * 5 + row['seat'] - 1]),
                                  'admissionId': str(self.admissions[(row['roomId'] - 1) * 5 + row['seat'] - 1])}
                                 for row in selected]}

        class Handler(BaseHTTPRequestHandler):
            def respond(self, payload):
                calls.append(self.path)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())

            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.respond({'topology': 'Linked', 'allMatched': True, 'seats': [
                    {'roomId': room, 'seat': seat, 'status': 'matched'} for room in range(1, 6) for seat in range(5)]})

            def do_GET(self):
                if self.path == f'/api/sessions/{session}/readiness':
                    self.respond(readiness)
                else:
                    self.respond({'version': 1, 'sessionId': session, 'sessionEnded': False, 'address': '192.168.1.10', 'port': 7777})

            def log_message(self, *args):
                pass

        with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                result = self.run_fleet(files, mapping, '-AllowPartialMap', '-DeployMappedSeats',
                    '-ManagementApi', f'http://127.0.0.1:{server.server_port}', environment={'VR_COMMAND_MASTER_KEY': 'private-fixture-master'})
                deploy_calls = calls.copy()
                before = (self.root / 'adb.log').read_bytes()
                flags = ('-VerifyTrackedSeats', '-DeviceMap', str(mapping), '-AllowPartialMap',
                         '-ManagementApi', f'http://127.0.0.1:{server.server_port}')
                env = {**os.environ, 'VR_COMMAND_MASTER_KEY': 'private-fixture-master'}
                ready = self.run_bundle(files, *flags, environment=env)
                self.assertEqual(0, ready.returncode, ready.stderr)
                self.assertEqual(['tracked-ready'] * 2, [row['status'] for row in json.loads(ready.stdout)['seats']])
                for changes in ({'mrStartState': 'WaitingProfile'}, {'mrStartState': 'Ready', 'origin': 'Simulation'}):
                    readiness.update(changes)
                    pending = self.run_bundle(files, *flags, environment=env)
                    self.assertEqual(1, pending.returncode, pending.stderr)
                    self.assertEqual(['mr-profile-pending'] * 2, [row['status'] for row in json.loads(pending.stdout)['seats']])
                self.assertEqual(before, (self.root / 'adb.log').read_bytes())
                self.assertEqual(deploy_calls + (deploy_calls + [f'/api/sessions/{session}/readiness']) * 3, calls)
            finally:
                server.shutdown()
                thread.join(timeout=5)
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual((True, True, True, 2, 23), (report['complete'], report['managementVerified'],
                         report['alignmentPinsVerified'], report['mappedSeats'], report['unmappedSeats']))
        self.assertEqual(['/api/mr-deployment/venue-check', f'/api/sessions/{session}/connection-endpoint'], deploy_calls)
        self.assertEqual({'fixture-03','fixture-22'}, {path.name for path in self.root.glob('fixture-*')})
        for row in selected:
            room, seat = row['roomId'], row['seat']
            directory = self.root / row['serial']
            config = configs[room][f'room-{room:02}-seat-{seat:02}.json']
            original = files[f'room-{room:02}-alignment.json']
            alignment = f"vr-room-alignment-{config['roomAlignmentSha256']}.json"
            self.assertEqual(original, (directory / alignment).read_bytes())
            self.assertEqual(dict(config, questPassthrough=True, requestMixedReality=True),
                             json.loads((directory / 'vr-connection.json').read_bytes()))
            self.assertEqual({alignment, 'vr-connection.json'}, {file.name for file in directory.iterdir()})
        self.assertNotIn('v2.', result.stdout)

    def test_device_map_reads_all_25_and_reports_faults_without_device_writes(self):
        files, _ = self.bundle('Independent')
        path, _ = self.device_map()
        faults = {'fixture-03': 'missing', 'fixture-07': 'unauthorized', 'fixture-11': 'offline',
                  'fixture-16': 'wrong-model', 'fixture-22': 'package-missing', 'fixture-25': 'version-mismatch'}
        result = self.run_fleet(files, path, '-DeployMappedSeats', '-ManagementApi', 'http://127.0.0.1:1', faults=faults)
        self.assertEqual(1, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(('preflight', False), (report['phase'], report['complete']))
        self.assertEqual([(r, s) for r in range(1, 6) for s in range(1, 6)], [(row['roomId'], row['seat']) for row in report['devices']])
        self.assertEqual({2:'missing', 6:'unauthorized', 10:'offline', 15:'wrong-model', 21:'package-unavailable', 24:'version-mismatch'},
                         {i:row['status'] for i,row in enumerate(report['devices']) if row['status'] != 'ready'})
        self.assertEqual(60, report['devices'][-1]['versionCode'])
        result = self.run_fleet(files, path, '-CheckOnly')
        self.assertEqual(0, result.returncode, result.stderr)
        ready = json.loads(result.stdout)
        self.assertTrue(ready['complete'] and all(row['status'] == 'ready' and row['versionCode'] == 61 for row in ready['devices']))
        commands = (self.root / 'adb.log').read_text(encoding='utf-8').splitlines()
        self.assertTrue(all(line == 'devices' or ' shell getprop ' in line or ' shell pm list packages ' in line for line in commands))
        self.assertNotIn('unmapped-device', '\n'.join(commands))
        self.assertNotIn('fixture-', result.stdout)

    def test_mapped_deployment_stops_after_failure_and_keeps_prior_results(self):
        files, seats = self.bundle('Linked')
        path, _ = self.device_map()
        session = str(self.session_ids[0])
        calls = []

        class Handler(BaseHTTPRequestHandler):
            def respond(self, data):
                calls.append(self.path)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())

            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.respond({'topology': 'Linked', 'allMatched': True, 'seats': [
                    {'roomId': room, 'seat': seat, 'status': 'matched'} for room in range(1, 6) for seat in range(5)]})

            def do_GET(self):
                self.respond({'version': 1, 'sessionId': session, 'sessionEnded': False, 'address': '192.168.1.10', 'port': 7777})

            def log_message(self, *args):
                pass

        before = self.root / 'fixture-04'
        before.mkdir()
        (before / 'vr-connection.json').write_bytes(b'previous connection')
        with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                result = self.run_fleet(files, path, '-DeployMappedSeats', '-ManagementApi', f'http://127.0.0.1:{server.server_port}',
                                        faults={'fixture-04': 'config-move'}, environment={'VR_COMMAND_MASTER_KEY': 'PRIVATE_MASTER_CANARY'})
            finally:
                server.shutdown()
                thread.join(timeout=5)
        self.assertEqual(1, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(('deployment', False, True), (report['phase'], report['complete'], report['managementVerified']))
        self.assertEqual(['launch-requested'] * 3 + ['deployment-failed'] + ['not-attempted'] * 21,
                         [row['status'] for row in report['devices']])
        self.assertEqual(['/api/mr-deployment/venue-check', f'/api/sessions/{session}/connection-endpoint'], calls)
        self.assertEqual(b'previous connection', (before / 'vr-connection.json').read_bytes())
        self.assertFalse(list(before.glob('*.tmp')))
        self.assertEqual(['fixture-01','fixture-02','fixture-03','fixture-04'], sorted(folder.name for folder in self.root.glob('fixture-*')))
        for seat in range(1, 4):
            actual = json.loads((self.root / f'fixture-{seat:02}' / 'vr-connection.json').read_bytes())
            self.assertEqual(seats[1][f'room-01-seat-{seat:02}.json']['joinTicket'], actual['joinTicket'])
        commands = (self.root / 'adb.log').read_text(encoding='utf-8').splitlines()
        first_write = next(index for index, line in enumerate(commands) if 'shell am force-stop' in line)
        self.assertEqual(51, first_write)
        self.assertEqual(3, sum(' shell monkey ' in line for line in commands))
        self.assertNotIn('v2.', result.stdout + result.stderr)
        self.assertNotIn('PRIVATE_MASTER_CANARY', result.stdout + result.stderr)

    def test_bundle_rejects_mismatched_files_before_a_selected_deployment(self):
        files, _ = self.bundle('Linked')
        flags = ('-RoomId', '5', '-Seat', '2', '-Serial', 'fixture')
        self.assert_rejected(self.run_bundle({**files, 'unrelated.txt': b'extra'}, *flags), 'exactly one manifest and ten room files')
        manifest = json.loads(files['venue.json'])
        manifest['rooms'][1]['alignmentFile'] = '../room-02-alignment.json'
        self.assert_rejected(self.run_bundle({**files, 'venue.json': json.dumps(manifest)}, *flags), 'Room 2 must use the original room filenames')
        self.assert_rejected(self.run_bundle({**files, 'room-02-alignment.json': files['room-02-alignment.json'] + b'\n'}, *flags),
                             'Room 2 seat 1 does not match the locked MR alignment file')
        self.assert_rejected(self.run_bundle({**files, 'room-02-connections.zip': b'x' * 65537}, *flags), 'Room 2 connection ZIP has an invalid size or length')

    def test_bundle_deploys_only_the_requested_seat_and_pins_the_original_bytes(self):
        files, seats = self.bundle('Independent')
        scripts = self.root / 'scripts'
        scripts.mkdir()
        script = scripts / 'deploy-quest.ps1'
        shutil.copyfile(ROOT / 'scripts' / script.name, script)
        adb = scripts / 'mock-adb.ps1'
        adb.write_text(ADB_FIXTURE, encoding='utf-8')
        apk = self.root / 'artifacts/quest/VrCommand.apk'
        apk.parent.mkdir(parents=True)
        apk.write_bytes(b'mock APK')
        remote = self.root / 'remote'
        remote.mkdir()
        environment = {**os.environ, 'QUEST_TEST_ROOT':str(self.root),
                       'QUEST_TEST_ALTER_ALIGNMENT':str(self.root / 'quest-mr-venue.zip')}
        result = self.run_bundle(files, '-RoomId', '4', '-Seat', '3', '-Serial', 'fixture', '-AdbPath', str(adb),
                                 environment=environment, script=script)
        self.assertEqual(0, result.returncode, result.stderr)
        config = {**seats[4]['room-04-seat-03.json'], 'questPassthrough': True, 'requestMixedReality': True}
        self.assertEqual(config, json.loads((remote / 'vr-connection.json').read_bytes()))
        name = f'vr-room-alignment-{config["roomAlignmentSha256"]}.json'
        self.assertEqual(files['room-04-alignment.json'], (remote / name).read_bytes())
        self.assertEqual({'vr-connection.json', name}, {file.name for file in remote.iterdir()})
        commands = (self.root / 'adb.log').read_text(encoding='utf-8').splitlines()
        self.assertTrue(all(command.startswith('-s fixture ') for command in commands))
        self.assertEqual(2, sum(' push ' in command for command in commands))
        self.assertIn('shell monkey', commands[-1])
        self.assertNotIn(config['joinTicket'], result.stdout + result.stderr + ''.join(commands))

    def test_live_bundle_checks_the_published_endpoint_before_deployment(self):
        files, _ = self.bundle('Linked')
        session = str(self.session_ids[0])
        calls = []

        class Handler(BaseHTTPRequestHandler):
            def respond(self, data):
                calls.append((self.command, self.path, self.headers.get('Authorization')))
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())

            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.respond({'topology': 'Linked', 'allMatched': True, 'seats': [
                    {'roomId': room, 'seat': seat, 'status': 'matched'} for room in range(1, 6) for seat in range(5)]})

            def do_GET(self):
                self.respond({'version': 1, 'sessionId': session, 'sessionEnded': False, 'address': '192.168.1.10',
                              'port': 7777 if len(calls) == 1 else 17777})

            def log_message(self, *args):
                pass

        environment = {**os.environ, 'VR_COMMAND_MASTER_KEY': 'PRIVATE_MASTER_CANARY'}
        with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                flags = ('-RoomId', '3', '-Seat', '4', '-ManagementApi', f'http://127.0.0.1:{server.server_port}')
                accepted = self.run_bundle(files, *flags, '-CheckOnly', environment=environment)
                self.assertEqual(0, accepted.returncode, accepted.stderr)
                self.assertTrue(json.loads(accepted.stdout)['managementVerified'])
                denied = self.run_bundle(files, *flags, '-Serial', 'fixture', environment=environment)
                self.assert_rejected(denied, 'does not match the current published game endpoint')
                self.assertNotIn('PRIVATE_MASTER_CANARY', accepted.stdout + accepted.stderr + denied.stderr)
                self.assertEqual([('POST', '/api/mr-deployment/venue-check', 'Bearer PRIVATE_MASTER_CANARY'),
                                  ('GET', f'/api/sessions/{session}/connection-endpoint', 'Bearer PRIVATE_MASTER_CANARY')] * 2, calls)
            finally:
                server.shutdown()
                thread.join(timeout=5)

    def test_both_topologies_check_all_twenty_five_seats_without_printing_tickets(self):
        for topology, endpoint_count in (('Linked',1), ('Independent',5)):
            with self.subTest(topology=topology):
                manifest, rooms = self.prepare(topology)
                manifest['rooms'].reverse()
                rooms[5]['room-05-seat-05.json'] = self.config(5, 4, uuid.UUID(manifest['rooms'][0]['sessionId']),
                                                              7777 if endpoint_count == 1 else 7781, expiry=self.expiry-30)
                result = self.run_venue(manifest, rooms)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertNotIn('v2.', result.stdout)
                self.assertNotIn(str(self.players[0]), result.stdout)
                self.assertNotIn(str(self.session_ids[0]), result.stdout)
                self.assertNotIn(str(self.admissions[0]), result.stdout)
                report = json.loads(result.stdout)
                self.assertEqual((topology,25), (report['topology'],report['seats']))
                self.assertEqual(5, len(report['rooms']))
                self.assertEqual(endpoint_count, len({room['endpoint'] for room in report['rooms']}))
                self.assertEqual(time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(self.expiry-30)), report['earliestExpiryUtc'][:19])
                for index, room in enumerate(report['rooms'], 1):
                    self.assertEqual({'roomId','seats','endpoint','alignmentSha256'}, set(room))
                    self.assertEqual((index,5), (room['roomId'],room['seats']))
                    self.assertEqual(hashlib.sha256((self.root / f'calibration {index}.json').read_bytes()).hexdigest(), room['alignmentSha256'])

    def test_wrong_session_wrong_seat_and_expiry_are_located(self):
        manifest, rooms = self.prepare('Linked')
        name = 'room-02-seat-04.json'
        for config, message in (
                (self.config(2, 3, self.session_ids[1], 7777), 'does not match the expected session or seat'),
                (self.config(2, 2, self.session_ids[0], 7777), 'does not match the expected session or seat'),
                (self.config(2, 3, self.session_ids[0], 7777, expiry=self.expiry-300), 'Player ticket has expired')):
            with self.subTest(message=message):
                rooms[2][name] = config
                self.assert_rejected(self.run_venue(manifest, rooms), 'Room 2 seat 4: ' + message if 'expired' in message else 'Room 2 seat 4 ticket ' + message)

    def test_distinct_player_and_admission_are_required_across_rooms(self):
        manifest, rooms = self.prepare('Independent')
        for claim, value in (('player', self.players[0]), ('admission', self.admissions[0])):
            with self.subTest(claim=claim):
                rooms[4]['room-04-seat-01.json'] = self.config(4, 0, self.session_ids[3], 7780, **{claim:value})
                self.assert_rejected(self.run_venue(manifest, rooms), 'Room 4 seat 1 repeats a player or admission')

    def test_topology_checks_session_and_endpoint_counts(self):
        manifest, rooms = self.prepare('Linked')
        manifest['topology'] = 'Independent'
        self.assert_rejected(self.run_venue(manifest, rooms), 'Independent requires 5 distinct session(s)')
        manifest, rooms = self.prepare('Linked')
        for config in rooms[5].values():
            config['port'] = 7778
        self.assert_rejected(self.run_venue(manifest, rooms), 'Linked requires 1 distinct session(s) and 1 distinct game-server endpoint(s)')
        manifest, rooms = self.prepare('Independent')
        for config in rooms[5].values():
            config['port'] = 7777
        self.assert_rejected(self.run_venue(manifest, rooms), 'Independent requires 5 distinct session(s) and 5 distinct game-server endpoint(s)')

    def test_endpoint_must_be_canonical_and_consistent_in_a_room(self):
        manifest, rooms = self.prepare('Linked')
        config = rooms[3]['room-03-seat-01.json']
        config['address'] = '127.1'
        self.assert_rejected(self.run_venue(manifest, rooms), 'Room 3 seat 1 needs a canonical unicast IPv4 address')
        config.update(address='192.168.1.10', port=7778)
        self.assert_rejected(self.run_venue(manifest, rooms), 'Room 3 contains different game-server endpoints')

    def test_room_manifest_and_archive_reject_mixed_alignment_and_unexpected_files(self):
        manifest, rooms = self.prepare('Linked')
        manifest['rooms'][3]['alignmentFile'] = manifest['rooms'][1]['alignmentFile']
        self.assert_rejected(self.run_venue(manifest, rooms), 'ticket is for room 4; the alignment export is for room 2')
        manifest, rooms = self.prepare('Linked')
        rooms[2]['../room-02-seat-05.json'] = rooms[2].pop('room-02-seat-05.json')
        self.assert_rejected(self.run_venue(manifest, rooms), 'Room 2 is missing the expected seat 5 connection file')
        manifest, rooms = self.prepare('Linked')
        rooms[2].pop('room-02-seat-05.json')
        self.assert_rejected(self.run_venue(manifest, rooms), 'Room 2 must contain exactly five seat connection files')
        manifest, rooms = self.prepare('Linked')
        rooms[2]['room-02-seat-05.json'] = '{"joinTicket":"PRIVATE_CANARY"}' + ' '*4096
        rejected = self.run_venue(manifest, rooms)
        self.assert_rejected(rejected, 'Room 2 seat 5 contains an invalid connection JSON file')
        self.assertNotIn('PRIVATE_CANARY', rejected.stderr)

    def test_venue_parameters_cannot_invoke_adb(self):
        manifest, rooms = self.prepare('Linked')
        self.assert_rejected(self.run_venue(manifest, rooms, '-Serial', 'device'), 'Parameter set cannot be resolved')

    def test_venue_checks_pinned_files_for_both_topologies_and_rejects_a_changed_room(self):
        for topology in ('Linked','Independent'):
            with self.subTest(topology=topology):
                manifest, rooms = self.prepare(topology)
                for room, entries in rooms.items():
                    plan = self.root / manifest['rooms'][room-1]['alignmentFile']
                    digest = hashlib.sha256(plan.read_bytes()).hexdigest()
                    for config in entries.values():
                        config['roomAlignmentSha256'] = digest
                result = self.run_venue(manifest, rooms)
                self.assertEqual(0, result.returncode, result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual((topology,25,True), (report['topology'],report['seats'],report['alignmentPinsVerified']))
                wrong_plan = self.root / manifest['rooms'][3]['alignmentFile']
                wrong_plan.write_bytes(wrong_plan.read_bytes() + b'\n')
                self.assert_rejected(self.run_venue(manifest, rooms), 'Room 4 seat 1 does not match the locked MR alignment file')
                wrong_plan.write_bytes(wrong_plan.read_bytes()[:-1])
                rooms[4]['room-04-seat-05.json'].pop('roomAlignmentSha256')
                self.assert_rejected(self.run_venue(manifest, rooms), 'Do not mix locked MR and legacy connection files')

    def test_live_venue_sends_original_bytes_once_and_fails_closed(self):
        manifest, rooms = self.prepare('Linked')
        for room, entries in rooms.items():
            plan = self.root / manifest['rooms'][room-1]['alignmentFile']
            plan.write_bytes(b'\xef\xbb\xbf'+plan.read_bytes()+b'\r\n')
            for config in entries.values():
                config['roomAlignmentSha256'] = hashlib.sha256(plan.read_bytes()).hexdigest()
        name = 'room-01-seat-01.json'
        original = '\ufeff'+json.dumps(rooms[1][name], indent=2)+'\r\n'
        rooms[1][name] = original
        requests = []
        seats = [{'roomId':room,'seat':seat,'status':'matched'} for room in range(1,6) for seat in range(5)]
        receipt = {'topology':'Linked','allMatched':True,'seats':seats}
        responses = [(200,receipt), (200,{**receipt,'allMatched':False,'seats':[dict(s,status='admission-changed') if i==11 else s for i,s in enumerate(seats)]}),
                     (200,{**receipt,'seats':seats[:-1]}), (403,{'error':'PRIVATE_RESPONSE_CANARY'})]

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append((self.path,self.headers.get('Authorization'),json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                status, result = responses[len(requests)-1]
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())

            def log_message(self, *args):
                pass

        environment = {**os.environ, 'VR_COMMAND_MASTER_KEY':'PRIVATE_MASTER_CANARY'}
        with ThreadingHTTPServer(('127.0.0.1',0), Handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                args = ('-ManagementApi',f'http://127.0.0.1:{server.server_port}')
                result = self.run_venue(manifest, rooms, *args, environment=environment)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertTrue(json.loads(result.stdout)['managementVerified'])
                self.assertNotIn('PRIVATE_MASTER_CANARY',result.stdout+result.stderr)
                self.assertEqual(1,len(requests))
                path, bearer, body = requests[0]
                self.assertEqual(('/api/mr-deployment/venue-check','Bearer PRIVATE_MASTER_CANARY'),(path,bearer))
                self.assertEqual([5]*5,[len(room['connectionFiles']) for room in body['rooms']])
                self.assertEqual(original.encode(),base64.b64decode(body['rooms'][0]['connectionFiles'][0]))
                self.assertEqual((self.root / manifest['rooms'][0]['alignmentFile']).read_bytes(),base64.b64decode(body['rooms'][0]['alignmentFile']))
                for message in ('Room 3 seat 2: admission-changed','invalid venue check receipt','current Master key'):
                    result = self.run_venue(manifest, rooms, *args, environment=environment)
                    self.assert_rejected(result,message)
                    self.assertNotIn('PRIVATE_',result.stdout+result.stderr)
                self.assertEqual(4,len(requests))
                offline = self.run_venue(manifest, rooms, environment=environment)
                self.assertEqual(0,offline.returncode,offline.stderr)
                self.assertNotIn('managementVerified',json.loads(offline.stdout))
                self.assertEqual(4,len(requests))
            finally:
                server.shutdown()
                thread.join(timeout=5)

    def test_live_venue_requires_pins_and_does_not_send_to_cleartext_lan(self):
        manifest, rooms = self.prepare('Independent')
        self.assert_rejected(self.run_venue(manifest, rooms, '-ManagementApi','http://127.0.0.1:5081'), 'all 25 connection files')
        for room, entries in rooms.items():
            digest = hashlib.sha256((self.root / manifest['rooms'][room-1]['alignmentFile']).read_bytes()).hexdigest()
            for config in entries.values():
                config['roomAlignmentSha256'] = digest
        environment = {**os.environ, 'VR_COMMAND_MASTER_KEY':'PRIVATE_MASTER_CANARY'}
        result = self.run_venue(manifest, rooms, '-ManagementApi','http://192.0.2.10:5081', environment=environment)
        self.assert_rejected(result,'an HTTPS origin or a local loopback HTTP origin')
        self.assertNotIn('PRIVATE_MASTER_CANARY',result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
