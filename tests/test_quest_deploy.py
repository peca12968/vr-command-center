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


def make_ticket(room, seat, expiry):
    payload = bytearray(75)
    payload[0], payload[49], payload[50] = 2, room, seat
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


if __name__ == '__main__':
    unittest.main()
