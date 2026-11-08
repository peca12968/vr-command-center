import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
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

    def run_venue(self, manifest, rooms, *flags):
        self.path.write_text(json.dumps(manifest), encoding='utf-8')
        for room, entries in rooms.items():
            with zipfile.ZipFile(self.root / f'room {room}.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in entries.items():
                    archive.writestr(name, data if isinstance(data, str) else json.dumps(data))
        return subprocess.run(['pwsh','-NoProfile','-NonInteractive','-File',str(ROOT / 'scripts/deploy-quest.ps1'),
                               '-VenueManifest',str(self.path),*flags], capture_output=True, encoding='utf-8', timeout=20)

    def assert_rejected(self, result, message):
        self.assertNotEqual(0, result.returncode)
        self.assertIn(message, result.stderr)
        self.assertEqual('', result.stdout)
        self.assertNotIn('v2.', result.stderr)

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


if __name__ == '__main__':
    unittest.main()
