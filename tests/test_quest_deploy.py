import asyncio
import base64
from contextlib import contextmanager, redirect_stderr
import copy
from datetime import datetime
import hashlib
import importlib.util
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
sys.path.insert(0, str(ROOT / 'scripts'))
from windows_firewall import WindowsFirewallLaunchError, require_silent_windows_launch

CAPTURE_FIXTURE = ROOT / 'tests/fixtures/run-quest-capture.py'


@contextmanager
def quest_management_server(handler):
    try:
        require_silent_windows_launch(sys.executable)
    except WindowsFirewallLaunchError as error:
        raise unittest.SkipTest(str(error)) from error
    with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
        yield server


def tracked_world_player(readiness):
    return {'id': readiness['playerId'], 'roomId': readiness['roomId'], 'connected': True,
            'health': 100, 'rig': {'kind': 'Tracked'}}


def posix_shell():
    shell = shutil.which('sh')
    if shell is None and os.name == 'nt':
        git = Path(shutil.which('git')).resolve()
        shell = str(git.parent.parent / 'bin/sh.exe')
    return shell


ADB_FIXTURE = r"""
$remote = Join-Path $env:QUEST_TEST_ROOT 'remote'
$installedApp = Join-Path $env:QUEST_TEST_ROOT 'installed-app'
$probeNonce = Join-Path $env:QUEST_TEST_ROOT 'openxr-probe'
$disconnected = Join-Path $env:QUEST_TEST_ROOT 'disconnected'
$replacedDevice = Join-Path $env:QUEST_TEST_ROOT 'replaced-device'
[IO.File]::AppendAllText((Join-Path $env:QUEST_TEST_ROOT 'adb.log'), (($args -join ' ') + "`n"))
if ($args[0] -eq 'devices') {
    "List of devices attached"
    if ($args[1] -ceq '-l') {
        'other   unauthorized transport_id:42'
        switch ($env:QUEST_TEST_FAIL) {
            'missing-transport' { 'fixture   device' }
            'duplicate-transport' { 'fixture   device transport_id:42' }
            'multiple-authorized' { 'fixture   device transport_id:41'; 'spare   device transport_id:43' }
            default { 'fixture   device product:quest3 model:Quest_3 transport_id:41' }
        }
    } else {
        "other`tunauthorized"
        "fixture`tdevice"
    }
    exit 0
}
if ($args[0] -ceq '-t' -and $args[1] -ceq '41') {
    if ([IO.File]::Exists($disconnected)) { exit 1 }
} elseif ($args[0] -ceq '-s' -and $args[1] -ceq 'fixture') {
    if ([IO.File]::Exists($disconnected)) {
        [IO.File]::AppendAllText((Join-Path $env:QUEST_TEST_ROOT 'replacement.log'), (($args -join ' ') + "`n"))
        exit 1
    }
} else { exit 99 }
switch ($args[2]) {
    'install' {
        if ($env:QUEST_TEST_RELEASE_HASH) {
            $installedHash = (Get-FileHash -LiteralPath $args[-1] -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($installedHash -cne $env:QUEST_TEST_RELEASE_HASH) { exit 95 }
        }
        if ($env:QUEST_TEST_ALTER_ALIGNMENT) {
            [IO.File]::WriteAllText($env:QUEST_TEST_ALTER_ALIGNMENT, '{}')
        }
        if ($args[3] -ceq '-R') {
            if ($env:QUEST_TEST_FAIL -eq 'install-rejected') { 'Failure [INSTALL_FAILED_ALREADY_EXISTS]'; exit 0 }
            [IO.File]::WriteAllText($installedApp, 'installed')
            'Success'
        }
        exit 0
    }
    'push' {
        $staging = Join-Path $remote ($args[4].Split('/')[-1])
        Copy-Item -LiteralPath $args[3] -Destination $staging
        if ($env:QUEST_TEST_FAIL -eq 'different-device-after-copy') { [IO.File]::WriteAllText($replacedDevice, 'replacement') }
        if ($env:QUEST_TEST_FAIL -eq 'refresh-source-changed') {
            [IO.File]::AppendAllText((Join-Path $remote 'vr-connection.json'), "`n")
        }
        if ($env:QUEST_TEST_FAIL -eq 'refresh-alignment-changed') {
            $originalConfig = Get-Content -Raw -LiteralPath (Join-Path $remote 'vr-connection.json') | ConvertFrom-Json
            [IO.File]::AppendAllText((Join-Path $remote "vr-room-alignment-$($originalConfig.roomAlignmentSha256).json"), "`n")
        }
        if ($env:QUEST_TEST_FAIL -eq 'refresh-stage-changed') { [IO.File]::AppendAllText($staging, "`n") }
        if (($env:QUEST_TEST_FAIL -eq 'config-stage-changed' -and $args[4].Contains('/vr-connection-')) -or
            ($env:QUEST_TEST_FAIL -eq 'alignment-stage-changed' -and $args[4].Contains('/vr-room-alignment-'))) {
            [IO.File]::AppendAllText($staging, "`n")
        }
        exit 0
    }
    'pull' {
        if ($args[3] -cnotmatch '\A/sdcard/Android/data/com\.vrcommand\.quest/files/(vr-connection\.json|vr-room-alignment-[0-9a-f]{64}\.json)\z') { exit 97 }
        $path = Join-Path $remote $Matches[1]
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { exit 1 }
        Copy-Item -LiteralPath $path -Destination $args[4]
        if ($env:QUEST_TEST_FAIL -eq 'disconnect-after-pull') { [IO.File]::WriteAllText($disconnected, 'original transport gone') }
        exit 0
    }
    'shell' {
        switch ($args[3]) {
            { $_.StartsWith('current=$(sha256sum ') -or $_.StartsWith('staged=$(sha256sum ') } {
                if ($args.Count -ne 4) { exit 96 }
                $isConnection = $args[3].EndsWith("/vr-connection.json'")
                if ($isConnection -and $env:QUEST_TEST_FAIL -eq 'config-move') { exit 1 }
                if ($isConnection -and $env:QUEST_TEST_FAIL -eq 'refresh-alignment-at-replace') {
                    $originalConfig = Get-Content -Raw -LiteralPath (Join-Path $remote 'vr-connection.json') | ConvertFrom-Json
                    [IO.File]::AppendAllText((Join-Path $remote "vr-room-alignment-$($originalConfig.roomAlignmentSha256).json"), "`n")
                }
                Push-Location -LiteralPath $env:QUEST_TEST_ROOT
                try { & $env:QUEST_TEST_SH -c $args[3].Replace('/sdcard/Android/data/com.vrcommand.quest/files/', 'remote/') }
                finally { Pop-Location }
                if ($LASTEXITCODE -eq 0 -and $isConnection -and $env:QUEST_TEST_FAIL -eq 'config-active-changed') {
                    [IO.File]::AppendAllText((Join-Path $remote 'vr-connection.json'), "`n")
                }
                if ($LASTEXITCODE -eq 0 -and $isConnection -and $env:QUEST_TEST_FAIL -eq 'alignment-changed-after-activation') {
                    $alignment = Get-ChildItem -LiteralPath $remote -Filter 'vr-room-alignment-*.json' -File
                    if (@($alignment).Count -ne 1) { exit 96 }
                    [IO.File]::AppendAllText($alignment.FullName, "`n")
                }
                exit $LASTEXITCODE
            }
            'getprop' {
                if ($env:QUEST_TEST_FAIL -eq 'getprop') { exit 1 }
                if ($args[4] -ceq 'ro.serialno') {
                    if ($env:QUEST_TEST_FAIL -eq 'missing-device-identity') { 'unknown' }
                    elseif ([IO.File]::Exists($replacedDevice)) { 'HEADSET-B' }
                    else { 'headset-a' }
                    exit 0
                }
                if ($env:QUEST_TEST_FAIL -eq 'model') { 'Quest 2' } else { 'Quest 3' }
                if ($env:QUEST_TEST_FAIL -eq 'disconnect-after-model') { [IO.File]::WriteAllText($disconnected, 'original transport gone') }
                exit 0
            }
            'pm' {
                if (($args[4..9] -join ' ') -ceq 'list packages -u --user current com.vrcommand.quest') {
                    if (Test-Path -LiteralPath $installedApp) { 'package:com.vrcommand.quest' }
                    if ($env:QUEST_TEST_FAIL -eq 'disconnect-after-inventory') { [IO.File]::WriteAllText($disconnected, 'original transport gone') }
                    exit 0
                }
                if (($args[4..13] -join ' ') -ceq 'resolve-activity --brief --user current -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p com.vrcommand.quest') {
                    if ($env:QUEST_TEST_FAIL -eq 'missing-activity') { 'No activity found'; exit 0 }
                    'priority=0 preferredOrder=0 match=0x108000 specificIndex=-1 isDefault=false'
                    if ($env:QUEST_TEST_FAIL -eq 'launch-short') { 'com.vrcommand.quest/com.vrcommand.quest.MainActivity'; exit 0 }
                    'com.vrcommand.quest/com.unity3d.player.UnityPlayerActivity'
                    exit 0
                }
                if ($env:QUEST_TEST_RELEASE_HASH -and ($args[4..7] -join ' ') -ceq 'path --user current com.vrcommand.quest') {
                    if ($env:QUEST_TEST_FAIL -eq 'installed-apk-missing') { exit 0 }
                    'package:/data/app/fixture/base.apk'; exit 0
                }
                exit 98
            }
            'sha256sum' {
                if ($args[4] -ceq '/data/app/fixture/base.apk' -and $env:QUEST_TEST_RELEASE_HASH) {
                    $hash = if ($env:QUEST_TEST_FAIL -eq 'installed-apk-mismatch') { 'f' * 64 } else { $env:QUEST_TEST_RELEASE_HASH }
                    "$hash  $($args[4])"; exit 0
                }
                $file = Join-Path $remote ($args[4].Split('/')[-1])
                if (-not [IO.File]::Exists($file)) { exit 1 }
                $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
                if ($env:QUEST_TEST_FAIL -ceq 'alignment-late-stage-changed' -and $args[4] -cmatch '/vr-room-alignment-[a-f0-9]+\.tmp$') {
                    [IO.File]::AppendAllText($file, "`n")
                }
                "$hash  $($args[4])"
                exit 0
            }
            'rm' {
                Remove-Item -LiteralPath (Join-Path $remote ($args[5].Split('/')[-1])) -ErrorAction SilentlyContinue
                exit 0
            }
            'test' {
                if (($args[4..6] -join ' ') -cne '! -e /sdcard/Android/data/com.vrcommand.quest/files/vr-connection.json') { exit 98 }
                if (Test-Path -LiteralPath (Join-Path $remote 'vr-connection.json')) { exit 1 }
                exit 0
            }
            'pidof' {
                if ($args[4] -cne 'com.vrcommand.quest') { exit 98 }
                if ($env:QUEST_TEST_FAIL -eq 'process-restarted' -and (Test-Path -LiteralPath (Join-Path $remote 'observed-process'))) { '4243' }
                else { '4242' }
                exit 0
            }
            'am' {
                if ($env:QUEST_TEST_FAIL -eq 'force-stop') { exit 1 }
                if ($args[4] -ceq 'force-stop' -and $env:QUEST_TEST_FAIL -ceq 'config-changed-at-stop') {
                    $staging = Get-ChildItem -LiteralPath $remote -Filter 'vr-connection-*.tmp' -File
                    if (@($staging).Count -ne 1) { exit 96 }
                    [IO.File]::AppendAllText($staging.FullName, "`n")
                }
                if ($args[4] -ceq 'force-stop' -and $env:QUEST_TEST_FAIL -ceq 'alignment-changed-at-stop') {
                    $alignment = Get-ChildItem -LiteralPath $remote -Filter 'vr-room-alignment-*.json' -File
                    if (@($alignment).Count -ne 1) { exit 96 }
                    [IO.File]::AppendAllText($alignment.FullName, "`n")
                }
                if ($args[4] -ceq 'start') {
                    $activity = if ($env:QUEST_TEST_FAIL -eq 'launch-short') { 'com.vrcommand.quest/com.vrcommand.quest.MainActivity' }
                        else { 'com.vrcommand.quest/com.unity3d.player.UnityPlayerActivity' }
                    $target = "--user current -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -n $activity"
                    $last = $args.Count - 1
                    if ($args[$last - 2] -ceq '--es') {
                        if ($args[$last - 1] -cne 'com.vrcommand.quest.OPENXR_PROBE' -or $args[$last] -cnotmatch '\A[a-f0-9]{32}\z') { exit 98 }
                        [IO.File]::WriteAllText($probeNonce, $args[$last])
                        $last -= 3
                    }
                    if (($args[5..$last] -join ' ') -cnotin @("-W $target", "-W -S $target")) { exit 98 }
                    if ($env:QUEST_TEST_FAIL -eq 'launch-empty') { exit 0 }
                    if ($env:QUEST_TEST_FAIL -eq 'launch-reused') { 'Warning: Activity not started, intent delivered to the top-most instance.' }
                    if ($env:QUEST_TEST_FAIL -eq 'launch-timeout') { 'Status: timeout' } else { 'Status: ok' }
                    if ($env:QUEST_TEST_FAIL -eq 'launch-conflicting') { 'Activity: com.vrcommand.quest/.UnexpectedActivity' }
                    if ($env:QUEST_TEST_FAIL -eq 'launch-short') { 'Activity: com.vrcommand.quest/.MainActivity' }
                    else { "Activity: $activity" }
                }
                exit 0
            }
            'monkey' {
                if ($env:QUEST_TEST_FAIL -eq 'launch-empty') { 'Events injected: 0' }
                exit 0
            }
            'mkdir' { exit 0 }
        }
    }
    'logcat' {
        if (($args[3..11] -join ' ') -cne '-d -t 1000 --pid=4242 -v brief -s Unity AndroidRuntime') { exit 98 }
        if ($env:QUEST_TEST_FAIL -eq 'adb-log-timeout') { throw [TimeoutException]::new('ADB logcat timed out.') }
        if ($env:QUEST_TEST_FAIL -eq 'log-unavailable') { exit 1 }
        if ($env:QUEST_TEST_FAIL -eq 'process-restarted') { [IO.File]::WriteAllText((Join-Path $remote 'observed-process'), '4242') }
        if ($env:QUEST_TEST_FAIL -eq 'different-device-after-launch') { [IO.File]::WriteAllText($replacedDevice, 'replacement') }
        if ($env:QUEST_TEST_FAIL -eq 'process-crashed') { 'E/AndroidRuntime( 4242): FATAL EXCEPTION: main' }
        'I/Unity   ( 4242): startup fixture log'
        if (Test-Path -LiteralPath $probeNonce) {
            $nonce = [IO.File]::ReadAllText($probeNonce)
            if ($env:QUEST_TEST_FAIL -eq 'xr-stale') {
                'I/Unity   ( 4242): VR_QUEST_OPENXR nonce=11111111111111111111111111111111 loader=1 display=1 input=1'
                "I/Unity   ( 4243): VR_QUEST_OPENXR nonce=$nonce loader=1 display=1 input=1"
            } else {
                $input = if ($env:QUEST_TEST_FAIL -eq 'xr-not-ready') { 0 } else { 1 }
                "I/Unity   ( 4242): VR_QUEST_OPENXR nonce=$nonce loader=1 display=1 input=$input"
                if ($env:QUEST_TEST_FAIL -eq 'xr-conflicting') {
                    "I/Unity   ( 4242): VR_QUEST_OPENXR nonce=$nonce loader=1 display=0 input=1"
                }
            }
        }
        exit 0
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


class QuestAdbProcessTests(unittest.TestCase):
    def invoke(self, shell, script, **values):
        if not shutil.which(shell):
            self.skipTest('PowerShell is unavailable')
        env = {**os.environ, 'VR_QUEST_PROCESS_HELPER': str(ROOT / 'scripts' / 'quest-adb-process.ps1'),
               'VR_QUEST_PROCESS_PYTHON': sys.executable, **values}
        return subprocess.run([shell, '-NoProfile', '-NonInteractive', '-Command',
                               "$ErrorActionPreference = 'Stop'; . $env:VR_QUEST_PROCESS_HELPER; " + script],
                              env=env, capture_output=True, encoding='utf-8', timeout=12)

    def test_argument_boundaries_and_both_output_streams(self):
        arguments = ['space and "quotes"', 'trailing' + chr(92), '', 'literal $() & ;']
        script = """
$program = 'import json, sys; sys.stderr.write("fixture stderr" * 20000); print(json.dumps(sys.argv[1:])); sys.exit(7)'
$arguments = @('-c', $program) + @(ConvertFrom-Json -InputObject $env:VR_QUEST_PROCESS_ARGUMENTS)
$result = Invoke-QuestAdbProcess $env:VR_QUEST_PROCESS_PYTHON $arguments 5000 'argument test'
$result | ConvertTo-Json -Compress
"""
        shells = ['pwsh', 'powershell.exe'] if os.name == 'nt' else ['pwsh']
        for shell in shells:
            with self.subTest(shell=shell):
                result = self.invoke(shell, script, VR_QUEST_PROCESS_ARGUMENTS=json.dumps(arguments))
                if shell == 'powershell.exe' and 'FullyQualifiedErrorId : UnauthorizedAccess' in result.stderr:
                    self.skipTest('Windows PowerShell script execution is unavailable under the current policy')
                self.assertEqual(result.returncode, 0, result.stderr)
                child = json.loads(result.stdout)
                self.assertEqual(child['ExitCode'], 7)
                self.assertEqual(json.loads(child['Lines'][0]), arguments)
                self.assertEqual(result.stderr, '')

    def test_deadline_stops_only_the_started_client_and_discards_partial_output(self):
        with tempfile.TemporaryDirectory(prefix='vr-quest-adb-timeout-') as temporary:
            script = """
$program = 'import os, pathlib, sys, time; pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); print("partial success", flush=True); time.sleep(30)'
try {
    Invoke-QuestAdbProcess $env:VR_QUEST_PROCESS_PYTHON @('-c', $program, $env:VR_QUEST_PROCESS_PID) 1500 'logcat'
    throw 'The stalled process unexpectedly completed.'
} catch [TimeoutException] {
    $pidValue = [int](Get-Content -LiteralPath $env:VR_QUEST_PROCESS_PID)
    $alive = $null -ne (Get-Process -Id $pidValue -ErrorAction SilentlyContinue)
    [pscustomobject]@{ message = $_.Exception.Message; clientAlive = $alive } | ConvertTo-Json -Compress
}
"""
            companion = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            try:
                result = self.invoke('pwsh', script, VR_QUEST_PROCESS_PID=str(Path(temporary) / 'client.pid'))
                self.assertIsNone(companion.poll())
            finally:
                if companion.poll() is None:
                    companion.terminate()
                companion.wait(timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {
                'message': 'ADB logcat timed out. Check the current device state before retrying.', 'clientAlive': False})
            self.assertNotIn('partial success', result.stdout)

    def test_deadline_includes_output_pipe_left_open_by_background_process(self):
        with tempfile.TemporaryDirectory(prefix='vr-quest-adb-pipe-') as temporary:
            script = """
$program = 'import os, pathlib, subprocess, sys; child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(15)"], stdin=subprocess.DEVNULL, stdout=sys.stdout, stderr=sys.stderr, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)); pathlib.Path(sys.argv[1]).write_text(str(child.pid)); print("partial success")'
try {
    Invoke-QuestAdbProcess $env:VR_QUEST_PROCESS_PYTHON @('-c', $program, $env:VR_QUEST_PROCESS_PID) 1500 'devices'
    throw 'The open pipe unexpectedly completed.'
} catch [TimeoutException] {
    $child = Get-Process -Id ([int](Get-Content -LiteralPath $env:VR_QUEST_PROCESS_PID)) -ErrorAction SilentlyContinue
    [pscustomobject]@{ message = $_.Exception.Message; backgroundAlive = $null -ne $child } | ConvertTo-Json -Compress
} finally {
    if (Test-Path -LiteralPath $env:VR_QUEST_PROCESS_PID) {
        Stop-Process -Id ([int](Get-Content -LiteralPath $env:VR_QUEST_PROCESS_PID)) -ErrorAction SilentlyContinue
    }
}
"""
            result = self.invoke('pwsh', script, VR_QUEST_PROCESS_PID=str(Path(temporary) / 'background.pid'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {
                'message': 'ADB devices timed out. Check the current device state before retrying.', 'backgroundAlive': True})


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
        shutil.copyfile(ROOT / 'scripts/quest-adb-process.ps1', self.scripts / 'quest-adb-process.ps1')
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

    def run_script(self, *flags, failure='', alter=False, release_hash='', management_key=None):
        env = {**os.environ, 'QUEST_TEST_ROOT':str(self.root), 'QUEST_TEST_FAIL':failure,
               'QUEST_TEST_ALTER_ALIGNMENT':str(self.plan) if alter else '', 'QUEST_TEST_RELEASE_HASH':release_hash,
               'QUEST_TEST_SH': posix_shell()}
        if management_key is not None:
            env['VR_COMMAND_MASTER_KEY'] = management_key
        return subprocess.run(['pwsh','-NoProfile','-NonInteractive','-File',str(self.script),
                               '-ClientConfig',str(self.config),'-AdbPath',str(self.adb),*flags],
                              env=env, capture_output=True, encoding='utf-8', timeout=20)

    def run_mr(self, *flags, **kwargs):
        return self.run_script('-AlignmentFile', str(self.plan), '-MixedReality', *flags, **kwargs)

    def assert_rejected(self, result, message):
        self.assertNotEqual(0, result.returncode)
        self.assertIn(message, result.stderr)
        ticket = json.loads(self.config.read_text(encoding='utf-8-sig'))['joinTicket']
        if ticket.startswith('v2.'):
            self.assertNotIn(ticket, result.stdout + result.stderr)

    def provision_apk(self):
        apk = self.root / 'artifacts/quest/VrCommand.apk'
        apk.parent.mkdir(parents=True)
        apk.write_bytes(b'mock APK')

    def test_single_quest_operations_keep_the_original_transport_on_disconnect(self):
        self.provision_apk()
        run_cases = (
            ('deploy', lambda: self.run_script('-Serial', 'fixture', failure='disconnect-after-model'),
             'APK installation failed', ' install -r '),
            ('first-launch', lambda: self.run_smoke(failure='disconnect-after-inventory'),
             'installation did not return Success', ' install -R '),
            ('ticket-refresh', lambda: self.run_refresh('disconnect-after-pull'),
             'could not be copied', ' push '),
        )
        for operation, invoke, message, attempted in run_cases:
            with self.subTest(operation=operation):
                for name in ('adb.log', 'disconnected', 'replacement.log'):
                    (self.root / name).unlink(missing_ok=True)
                active = self.remote / 'vr-connection.json'
                if operation == 'ticket-refresh':
                    self.ticket_refresh(self.expiry - 300)
                original = active.read_bytes() if active.exists() else None
                result = invoke()
                self.assertNotEqual(0, result.returncode)
                replacement = self.root / 'replacement.log'
                self.assertEqual('', replacement.read_text(encoding='utf-8') if replacement.exists() else '',
                                 'An old serial must not deliver a command to a new transport')
                self.assert_rejected(result, message)
                commands = self.commands.read_text(encoding='utf-8').splitlines()
                self.assertEqual('devices -l', commands[0])
                self.assertTrue(all(line.startswith('-t 41 ') for line in commands[1:]))
                self.assertEqual(1, sum(attempted in line for line in commands))
                self.assertEqual(original, active.read_bytes() if active.exists() else None)

    def test_single_quest_selection_requires_one_usable_transport(self):
        self.provision_apk()
        for fault, message in (
            ('missing-transport', 'ADB state: transport-unavailable'),
            ('duplicate-transport', 'ADB state: transport-ambiguous'),
            ('multiple-authorized', 'specify -Serial explicitly'),
        ):
            with self.subTest(fault=fault):
                self.commands.unlink(missing_ok=True)
                self.assert_rejected(self.run_script(failure=fault), message)
                self.assertEqual(['devices -l'], self.commands.read_text(encoding='utf-8').splitlines())
        self.commands.unlink()
        chosen = self.run_script('-Serial', 'fixture', failure='multiple-authorized')
        self.assertEqual(0, chosen.returncode, chosen.stderr)
        commands = self.commands.read_text(encoding='utf-8').splitlines()
        self.assertEqual('devices -l', commands[0])
        self.assertTrue(all(line.startswith('-t 41 ') for line in commands[1:]))
        self.assertIn(' shell am start ', commands[-1])

    @contextmanager
    def live_quest_check(self, config):
        requests = []
        state = {'reject': None}
        key = 'test-master-single-seat'
        expires = datetime.fromtimestamp(self.expiry).astimezone().isoformat()

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append((self.path, self.headers.get('Authorization'), self.headers.get('If-Match-Admission'), payload))
                if state['reject'] == len(requests):
                    self.send_error(409)
                    return
                body = json.dumps({'status': 'matched', 'roomId': 5, 'seat': 1, 'expiresAtUtc': expires,
                                   'address': config['address'], 'port': config['port']}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        with quest_management_server(Handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                yield f'http://127.0.0.1:{server.server_port}', key, requests, state
            finally:
                server.shutdown()
                thread.join()

    def test_single_deploy_verifies_original_files_and_rechecks_before_activation(self):
        session, player, admission = (uuid.uuid4() for _ in range(3))
        ticket = make_ticket(5, 1, self.expiry, session, player, admission)
        config = dict(self.player, joinTicket=ticket)
        path = f'/api/sessions/{session}/rooms/5/players/{player}/quest-deployment-check'
        self.provision_apk()
        with self.live_quest_check(config) as (url, key, requests, state):
            flags = ('-ManagementApi', url, '-Serial', 'fixture')
            active = self.remote / 'vr-connection.json'
            for mode in ('VR', 'MR'):
                with self.subTest(mode=mode):
                    self.commands.unlink(missing_ok=True)
                    active.write_bytes(b'previous connection')
                    selected = dict(config)
                    options = ()
                    expected_body = {}
                    if mode == 'MR':
                        alignment = self.plan.read_bytes()
                        selected['roomAlignmentSha256'] = hashlib.sha256(alignment).hexdigest()
                        expected_body['alignmentFile'] = base64.b64encode(alignment).decode()
                        options = ('-MixedReality', '-AlignmentFile', str(self.plan))
                    original = b'\xef\xbb\xbf' + json.dumps(selected).encode() + b'\r\n'
                    self.config.write_bytes(original)
                    expected_body['connectionFile'] = base64.b64encode(original).decode()
                    original_request = (path, f'Bearer {key}', str(admission), expected_body)

                    requests.clear()
                    state['reject'] = None
                    checked = self.run_script(*flags, *options, '-CheckOnly', management_key=key)
                    self.assertEqual(0, checked.returncode, checked.stderr)
                    self.assertTrue(json.loads(checked.stdout)['managementVerified'])
                    self.assertEqual([original_request], requests)
                    self.assertFalse(self.commands.exists())

                    requests.clear()
                    state['reject'] = 1
                    denied = self.run_script(*flags, *options, management_key=key)
                    self.assert_rejected(denied, 'session or admission changed')
                    self.assertEqual([original_request], requests)
                    self.assertFalse(self.commands.exists())

                    requests.clear()
                    state['reject'] = 3
                    changed = self.run_script(*flags, *options, management_key=key)
                    self.assert_rejected(changed, 'session or admission changed')
                    self.assertEqual([original_request] * 3, requests)
                    commands = self.commands.read_text(encoding='utf-8')
                    self.assertIn(' install ', commands)
                    self.assertNotIn(' force-stop ', commands)
                    self.assertNotIn(' am start ', commands)
                    self.assertEqual(b'previous connection', active.read_bytes())
                    self.assertFalse(list(self.remote.glob('*.tmp')))

                    requests.clear()
                    state['reject'] = None
                    self.commands.unlink()
                    deployed = self.run_script(*flags, *options, management_key=key)
                    self.assertEqual(0, deployed.returncode, deployed.stderr)
                    self.assertEqual([original_request] * 3, requests)
                    commands = self.commands.read_text(encoding='utf-8')
                    self.assertIn(' force-stop ', commands)
                    self.assertIn(' am start ', commands)
                    saved = json.loads(active.read_bytes())
                    self.assertEqual(ticket, saved['joinTicket'])
                    self.assertEqual(mode == 'MR', saved.get('requestMixedReality', False))
                    for result in (checked, denied, changed, deployed):
                        self.assertNotIn(key, result.stdout + result.stderr)
                        self.assertNotIn(ticket, result.stdout + result.stderr)

    def test_single_seat_checks_local_release_and_installed_apk_before_activation(self):
        apk = self.root / 'selected release.apk'
        apk.write_bytes(b'mock APK')
        expected = hashlib.sha256(apk.read_bytes()).hexdigest()
        release = self.root / 'release.json'
        report = {'verified': True, 'scope': 'offline-package-consistency', 'quest': {
            'applicationId': 'com.vrcommand.quest', 'architecture': 'arm64-v8a', 'signatureV2': True,
            'versionCode': 72, 'sha256': expected}}
        self.write(release, report)
        flags = ('-ApkPath', str(apk), '-ReleaseReport', str(release))
        checked = self.run_script(*flags, '-CheckOnly')
        self.assertEqual(0, checked.returncode, checked.stderr)
        info = json.loads(checked.stdout)
        self.assertEqual((True, 72), (info['localApkVerified'], info['expectedVersionCode']))
        self.assertFalse(self.commands.exists())
        apk.write_bytes(b'wrong APK')
        self.assert_rejected(self.run_script(*flags), 'Local Quest APK SHA-256 differs')
        self.assertFalse(self.commands.exists())
        apk.write_bytes(b'mock APK')
        failed = self.run_script(*flags, '-Serial', 'fixture', failure='installed-apk-mismatch', release_hash=expected)
        self.assert_rejected(failed, 'Installed Quest APK could not be verified')
        commands = self.commands.read_text(encoding='utf-8').splitlines()
        self.assertEqual(5, len(commands))
        self.assertEqual('devices -l', commands[0])
        staged = commands[2].split(' install -r ', 1)[1]
        self.assertNotEqual(str(apk), staged)
        self.assertFalse(Path(staged).exists())
        self.assertTrue(commands[-1].endswith('sha256sum /data/app/fixture/base.apk'))
        self.assertEqual([], list(self.remote.iterdir()))
        self.commands.unlink()
        success = self.run_script(*flags, '-Serial', 'fixture', release_hash=expected)
        self.assertEqual(0, success.returncode, success.stderr)
        commands = self.commands.read_text(encoding='utf-8').splitlines()
        self.assertLess(next(i for i, command in enumerate(commands) if 'base.apk' in command),
                        next(i for i, command in enumerate(commands) if ' push ' in command))
        self.assertIn(' shell am start ', commands[-1])
        self.assertEqual(self.player, json.loads((self.remote/'vr-connection.json').read_bytes()))
        self.assertEqual(expected, hashlib.sha256(apk.read_bytes()).hexdigest())

    def test_single_seat_can_launch_the_verified_installed_apk_without_a_local_copy(self):
        session, player, admission = (uuid.uuid4() for _ in range(3))
        self.player['joinTicket'] = make_ticket(5, 1, self.expiry, session, player, admission)
        self.write(self.config, self.player)
        digest = hashlib.sha256(b'preinstalled APK').hexdigest()
        release = self.root / 'release.json'
        self.write(release, {'verified': True, 'scope': 'offline-package-consistency', 'quest': {
            'applicationId': 'com.vrcommand.quest', 'architecture': 'arm64-v8a', 'signatureV2': True,
            'versionCode': 77, 'sha256': digest}})
        flags = ('-UseInstalledApk', '-ReleaseReport', str(release), '-Serial', 'fixture')
        for options in (('-UseInstalledApk',), (*flags, '-ApkPath', 'unused.apk'), (*flags, '-CheckOnly')):
            self.assert_rejected(self.run_script(*options), 'Use -UseInstalledApk with -ReleaseReport')
        self.assertFalse(self.commands.exists())

        active = self.remote / 'vr-connection.json'
        original = b'previous connection'
        active.write_bytes(original)
        for fault in ('installed-apk-missing', 'installed-apk-mismatch'):
            with self.subTest(fault=fault):
                self.commands.unlink(missing_ok=True)
                result = self.run_script(*flags, '-RequireOpenXR', failure=fault, release_hash=digest)
                self.assert_rejected(result, 'Installed Quest APK could not be verified')
                commands = self.commands.read_text(encoding='utf-8').splitlines()
                self.assertEqual(['devices -l', '-t 41 shell getprop ro.product.model', '-t 41 shell getprop ro.serialno',
                                  '-t 41 shell pm path --user current com.vrcommand.quest'] +
                                 (['-t 41 shell sha256sum /data/app/fixture/base.apk'] if fault.endswith('mismatch') else []),
                                 commands)
                self.assertEqual(original, active.read_bytes())

        self.commands.unlink()
        result = self.run_script(*flags, '-RequireOpenXR', release_hash=digest)
        self.assertEqual(0, result.returncode, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(('openxr-ready', True, True), tuple(receipt[key] for key in ('status', 'apkVerified', 'filesVerified')))
        self.assertEqual((3, 5, 2, str(session), str(player), str(admission), self.player['port']), tuple(
            receipt[key] for key in ('evidenceVersion', 'roomId', 'seat', 'sessionId', 'playerId', 'admissionId', 'port')))
        self.assertEqual(hashlib.sha256(self.player['address'].encode()).hexdigest(), receipt['serverAddressSha256'])
        self.assertEqual(hashlib.sha256(release.read_bytes()).hexdigest(), receipt['venueReleaseReportSha256'])
        self.assertNotIn(self.player['joinTicket'], result.stdout)
        self.assertEqual(4242, receipt['openXR']['processId'])
        self.assertEqual(hashlib.sha256(f"{receipt['openXR']['nonce']}\nHEADSET-A".encode()).hexdigest(), receipt['deviceFingerprint'])
        self.assertNotIn('HEADSET-A', result.stdout.upper())
        commands = self.commands.read_text(encoding='utf-8')
        self.assertNotIn(' install ', commands)
        self.assertLess(commands.index('sha256sum /data/app/fixture/base.apk'), commands.index(' push '))
        self.assertLess(commands.index(' push '), commands.index(' am start -W '))
        self.assertEqual(self.player, json.loads(active.read_bytes()))

    def test_single_seat_stops_when_original_device_identity_disappears_on_the_same_transport(self):
        digest = hashlib.sha256(b'preinstalled APK').hexdigest()
        release = self.root / 'release.json'
        self.write(release, {'verified': True, 'scope': 'offline-package-consistency', 'quest': {
            'applicationId': 'com.vrcommand.quest', 'architecture': 'arm64-v8a', 'signatureV2': True,
            'versionCode': 77, 'sha256': digest}})
        flags = ('-UseInstalledApk', '-ReleaseReport', str(release), '-Serial', 'fixture', '-RequireOpenXR')
        active = self.remote / 'vr-connection.json'
        for fault in ('missing-device-identity', 'different-device-after-copy', 'different-device-after-launch'):
            with self.subTest(fault=fault):
                self.commands.unlink(missing_ok=True)
                (self.root / 'replaced-device').unlink(missing_ok=True)
                active.write_bytes(b'previous connection')
                result = self.run_script(*flags, failure=fault, release_hash=digest)
                self.assert_rejected(result, 'original Quest device identity')
                self.assertNotIn('openxr-ready', result.stdout)
                self.assertNotIn('HEADSET-B', (result.stdout + result.stderr).upper())
                commands = self.commands.read_text(encoding='utf-8').splitlines()
                self.assertTrue(all(line.startswith('-t 41 ') for line in commands[1:]))
                if fault == 'different-device-after-launch':
                    self.assertTrue(any(' shell am start ' in line for line in commands))
                else:
                    self.assertFalse(any(' force-stop ' in line or ' am start ' in line or ' shell rm ' in line for line in commands))
                    self.assertEqual(b'previous connection', active.read_bytes())
                self.assertTrue(commands[-1].endswith(' shell getprop ro.serialno'))

    def test_single_seat_quest_link_measurement_requires_current_package_and_writes_opt_in(self):
        apk = self.root / 'link build.apk'
        apk.write_bytes(b'quest link fixture APK')
        expected = hashlib.sha256(apk.read_bytes()).hexdigest()
        release = self.root / 'release.json'
        report = {'verified': True, 'scope': 'offline-package-consistency', 'quest': {
            'applicationId': 'com.vrcommand.quest', 'architecture': 'arm64-v8a', 'signatureV2': True,
            'versionCode': 74, 'sha256': expected}}
        self.write(release, report)
        self.assert_rejected(self.run_script('-RecordLinkMetrics'), 'Use -RecordLinkMetrics with -ReleaseReport')
        flags = ('-RecordLinkMetrics', '-ApkPath', str(apk), '-ReleaseReport', str(release), '-Serial', 'fixture')
        self.assert_rejected(self.run_script(*flags), 'version code 75 or later')
        self.assertFalse(self.commands.exists())
        report['quest']['versionCode'] = 75
        self.write(release, report)
        original = self.config.read_bytes()
        result = self.run_script(*flags, release_hash=expected)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(dict(self.player, recordQuestLinkMetrics=True), json.loads((self.remote/'vr-connection.json').read_bytes()))
        self.assertEqual(original, self.config.read_bytes())

    def test_player_deployment_observes_openxr_after_verifying_the_active_config(self):
        apk = self.root / 'openxr.apk'
        apk.write_bytes(b'XR player deployment APK')
        digest = hashlib.sha256(apk.read_bytes()).hexdigest()
        release = self.root / 'release.json'
        self.write(release, {'verified': True, 'scope': 'offline-package-consistency', 'quest': {
            'applicationId': 'com.vrcommand.quest', 'architecture': 'arm64-v8a', 'signatureV2': True,
            'versionCode': 76, 'sha256': digest}})
        self.assert_rejected(self.run_script('-RequireOpenXR'), 'Use -RequireOpenXR with -ReleaseReport')
        flags = ('-RequireOpenXR', '-ApkPath', str(apk), '-ReleaseReport', str(release), '-Serial', 'fixture')
        self.assert_rejected(self.run_script(*flags, '-CheckOnly'), 'Use -RequireOpenXR with -ReleaseReport')
        self.assertFalse(self.commands.exists())
        result = self.run_script(*flags, release_hash=digest)
        self.assertEqual(0, result.returncode, result.stderr)
        receipt = json.loads(result.stdout)
        nonce = (self.root / 'openxr-probe').read_text()
        self.assertEqual(('openxr-ready', True, True), tuple(receipt[key] for key in ('status', 'apkVerified', 'filesVerified')))
        self.assertEqual({'processId': 4242, 'nonce': nonce}, receipt['openXR'])
        commands = self.commands.read_text(encoding='utf-8')
        self.assertLess(commands.index(' resolve-activity '), commands.index(' force-stop '))
        self.assertLess(commands.rindex('shell sha256sum /sdcard/Android/data/com.vrcommand.quest/files/vr-connection.json'),
                        commands.index(' am start -W '))
        self.assertNotIn('shell monkey', commands)
        self.assertEqual(self.player, json.loads((self.remote / 'vr-connection.json').read_bytes()))

    def test_player_deployment_requires_android_launcher_confirmation(self):
        self.provision_apk()
        for failure in ('launch-empty', 'launch-reused', 'launch-conflicting'):
            with self.subTest(failure=failure):
                self.commands.unlink(missing_ok=True)
                result = self.run_script('-Serial', 'fixture', failure=failure)
                self.assert_rejected(result, 'did not confirm that the Quest launcher activity started')
                commands = self.commands.read_text(encoding='utf-8')
                self.assertIn(' am start -W ', commands)
                self.assertNotIn(' --es com.vrcommand.quest.OPENXR_PROBE ', commands)
                self.assertEqual(self.player, json.loads((self.remote / 'vr-connection.json').read_bytes()))
        result = self.run_script('-Serial', 'fixture', failure='launch-short')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('Quest client installed and launched.', result.stdout)

    def run_smoke(self, serial='fixture', failure='', *, resume=False, require_openxr=False, version_code=72):
        apk = self.root / 'sample.apk'
        apk.write_bytes(b'first-launch test APK')
        expected = hashlib.sha256(apk.read_bytes()).hexdigest()
        release = self.root / 'release.json'
        self.write(release, {'verified': True, 'scope': 'offline-package-consistency', 'quest': {
            'applicationId': 'com.vrcommand.quest', 'architecture': 'arm64-v8a', 'signatureV2': True,
            'versionCode': version_code, 'sha256': expected}})
        env = {**os.environ, 'QUEST_TEST_ROOT': str(self.root), 'QUEST_TEST_FAIL': failure,
               'QUEST_TEST_ALTER_ALIGNMENT': '', 'QUEST_TEST_RELEASE_HASH': expected}
        return subprocess.run(['pwsh','-NoProfile','-NonInteractive','-File',str(self.script), '-SmokeTest',
                               '-Serial', serial, '-AdbPath', str(self.adb), '-ApkPath', str(apk), '-ReleaseReport', str(release),
                               *(['-ResumeSmokeTest'] if resume else []), *(['-RequireOpenXR'] if require_openxr else [])],
                              env=env, capture_output=True, encoding='utf-8', timeout=35)

    def test_fresh_quest_launch_verifies_apk_and_observes_started_process(self):
        result = self.run_smoke()
        self.assertEqual(0, result.returncode, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(('quest-first-launch', 'process-observed', 'Quest 3', 72, True, 3, 1),
                         tuple(receipt[key] for key in ('phase', 'status', 'model', 'versionCode', 'apkVerified',
                                                        'processObservationSeconds', 'unityLogLines')))
        self.assertEqual(hashlib.sha256((self.root/'sample.apk').read_bytes()).hexdigest(), receipt['apkSha256'])
        self.assertIs(receipt['installedThisRun'], True)
        self.assertNotIn('startup fixture log', result.stdout)
        commands = self.commands.read_text(encoding='utf-8').splitlines()
        staged = commands[3].split(' --pkg com.vrcommand.quest ', 1)[1]
        self.assertIn(' install -R --user current ', commands[3])
        self.assertFalse(Path(staged).exists())
        self.assertIn('sha256sum /data/app/fixture/base.apk', commands[5])
        self.assertIn(' shell pm resolve-activity ', commands[7])
        self.assertIn(' shell am start -W ', commands[8])
        self.assertIn(' logcat -d ', commands[10])
        self.assertFalse(list(self.remote.iterdir()))
        self.assert_rejected(self.run_smoke(), 'requires a headset without an existing VR Command app')
        self.assertEqual(1, self.commands.read_text(encoding='utf-8').count(' install '))

    def test_resume_quest_smoke_checks_existing_apk_and_config_before_restart(self):
        self.assert_rejected(self.run_smoke(resume=True), 'No existing VR Command app to resume')
        self.assert_rejected(self.run_smoke(failure='log-unavailable'), 'Could not read the launched Quest process logs.')
        self.assertTrue((self.root/'installed-app').exists())
        self.commands.unlink()

        self.assert_rejected(self.run_smoke(failure='installed-apk-mismatch', resume=True),
                             'Installed Quest APK could not be verified')
        config = self.remote/'vr-connection.json'
        self.write(config, self.player)
        config_bytes = config.read_bytes()
        self.assert_rejected(self.run_smoke(resume=True), 'has no existing player configuration')
        self.assertEqual(config_bytes, config.read_bytes())
        self.assertNotIn(' am start ', self.commands.read_text(encoding='utf-8'))
        config.unlink()

        resumed = self.run_smoke(resume=True)
        self.assertEqual(0, resumed.returncode, resumed.stderr)
        receipt = json.loads(resumed.stdout)
        self.assertEqual('process-observed', receipt['status'])
        self.assertIs(receipt['installedThisRun'], False)
        self.assertIs(receipt['apkVerified'], True)
        commands = self.commands.read_text(encoding='utf-8')
        self.assertEqual(1, commands.count(' am start -W -S '))
        for operation in (' install ', ' uninstall ', ' pm clear ', ' push '):
            self.assertNotIn(operation, commands)

    def test_quest_openxr_smoke_observes_only_the_current_launch(self):
        self.assert_rejected(self.run_smoke(require_openxr=True), 'version code 74 or later')
        self.assertFalse(self.commands.exists())
        result = self.run_smoke(require_openxr=True, version_code=74)
        self.assertEqual(0, result.returncode, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual('openxr-ready', receipt['status'])
        self.assertEqual({'loader': 'OpenXR', 'displayRunning': True, 'inputRunning': True}, receipt['openXR'])
        self.assertGreaterEqual(receipt['processObservationSeconds'], 3)
        nonce = (self.root / 'openxr-probe').read_text()
        self.assertRegex(nonce, r'^[a-f0-9]{32}$')
        self.assertIn(f'--es com.vrcommand.quest.OPENXR_PROBE {nonce}', self.commands.read_text())
        self.assertNotIn(nonce, result.stdout + result.stderr)
        for failure, expected in (('xr-not-ready', 'loader=1, display=1, input=0'),
                                  ('xr-conflicting', 'conflicting or invalid OpenXR evidence'),
                                  ('xr-stale', 'No OpenXR evidence was observed')):
            with self.subTest(failure=failure):
                self.commands.unlink()
                blocked = self.run_smoke(failure=failure, require_openxr=True, version_code=74, resume=True)
                self.assert_rejected(blocked, expected)
                self.assertEqual('', blocked.stdout)
                self.assertNotIn(' install ', self.commands.read_text())
                self.assertNotEqual(nonce, (self.root / 'openxr-probe').read_text())

    def test_quest_first_launch_stops_for_missing_access_and_bad_startup(self):
        cases = (
            ('other', '', 'ADB state: unauthorized', False, False),
            ('missing', '', 'ADB state: missing', False, False),
            ('fixture', 'model', 'Select an authorized Meta Quest 3', False, False),
            ('fixture', 'install-rejected', 'installation did not return Success', True, False),
            ('fixture', 'installed-apk-mismatch', 'Installed Quest APK could not be verified', True, False),
            ('fixture', 'existing-config', 'has no existing player configuration', True, False),
            ('fixture', 'missing-activity', 'Could not resolve a launcher activity', True, False),
            ('fixture', 'launch-timeout', 'did not confirm that the Quest launcher activity started', True, True),
            ('fixture', 'adb-log-timeout', 'ADB logcat timed out', True, True),
            ('fixture', 'log-unavailable', 'Could not read the launched Quest process logs', True, True),
            ('fixture', 'process-restarted', 'process exited, restarted or reported a fatal error', True, True),
            ('fixture', 'process-crashed', 'process exited, restarted or reported a fatal error', True, True),
        )
        for serial, failure, message, install, launch in cases:
            with self.subTest(serial=serial, failure=failure):
                self.commands.unlink(missing_ok=True)
                (self.root/'installed-app').unlink(missing_ok=True)
                (self.remote/'observed-process').unlink(missing_ok=True)
                config = self.remote/'vr-connection.json'
                config.unlink(missing_ok=True)
                if failure == 'existing-config':
                    self.write(config, self.player)
                result = self.run_smoke(serial, failure)
                self.assert_rejected(result, message)
                self.assertEqual('', result.stdout)
                commands = self.commands.read_text(encoding='utf-8')
                if serial != 'fixture':
                    self.assertIn('scripts/check-quest-usb.ps1', result.stderr)
                    self.assertEqual(commands.splitlines(), ['devices -l'])
                self.assertEqual(install, ' install ' in commands)
                self.assertEqual(launch, ' am start ' in commands)
                self.assertNotIn(' push ', commands)
                self.assertNotIn(' force-stop ', commands)
                if failure == 'existing-config':
                    self.assertEqual(self.player, json.loads(config.read_bytes()))

    def ticket_refresh(self, installed_expiry, *, mode='MR'):
        identities = [uuid.uuid4() for _ in range(3)]
        pin = hashlib.sha256(self.plan.read_bytes()).hexdigest()
        installed = {**self.player, 'joinTicket': make_ticket(5, 1, installed_expiry, *identities),
                     'roomAlignmentSha256': pin, 'questPassthrough': True, 'requestMixedReality': mode=='MR'}
        current = self.remote/'vr-connection.json'
        self.write(current, installed)
        fresh = {**self.player, 'joinTicket': make_ticket(5, 1, self.expiry, *identities)}
        if mode == 'MR':
            fresh['roomAlignmentSha256'] = pin
        self.write(self.config, fresh)
        alignment = self.remote/f'vr-room-alignment-{pin}.json'
        alignment.write_bytes(self.plan.read_bytes())
        return current, installed, fresh, identities, alignment

    def run_refresh(self, failure='', *, management_api=None, management_key=None):
        env = {**os.environ, 'QUEST_TEST_ROOT': str(self.root), 'QUEST_TEST_FAIL': failure, 'QUEST_TEST_SH': posix_shell()}
        if management_api is not None:
            env['VR_COMMAND_MASTER_KEY'] = management_key
        management = ['-ManagementApi', management_api] if management_api is not None else []
        return subprocess.run(['pwsh', '-NoProfile', '-NonInteractive', '-File', str(self.script), '-RefreshPlayerTicket',
                               '-ClientConfig', str(self.config), '-AdbPath', str(self.adb), '-Serial', 'fixture', *management],
                              env=env, capture_output=True, encoding='utf-8', timeout=20)

    def test_ticket_refresh_updates_only_original_ticket_and_is_idempotent(self):
        for mode in ('MR', 'VR'):
            with self.subTest(mode=mode):
                current, installed, fresh, _, alignment = self.ticket_refresh(self.expiry-300, mode=mode)
                if mode == 'VR':
                    installed['recordQuestLinkMetrics'] = True
                    self.write(current, installed)
                self.commands.unlink(missing_ok=True)
                result = self.run_refresh()
                self.assertEqual(0, result.returncode, result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual((5, 2, 'ticket-file-refreshed'), (report['roomId'], report['seat'], report['status']))
                self.assertEqual(dict(installed, joinTicket=fresh['joinTicket']), json.loads(current.read_bytes()))
                self.assertEqual(self.plan.read_bytes(), alignment.read_bytes())
                commands = self.commands.read_text(encoding='utf-8').splitlines()
                self.assertEqual(7, len(commands))
                self.assertEqual('devices -l', commands[0])
                self.assertTrue(all(command.startswith('-t 41 ') for command in commands[1:]))
                for phrase in ('getprop', 'pull', 'push', 'sha256sum'):
                    self.assertTrue(any(phrase in command for command in commands), commands)
                self.assertTrue(commands[-2].endswith('shell sha256sum /sdcard/Android/data/com.vrcommand.quest/files/vr-connection.json'))
                self.assertTrue(commands[-1].endswith('shell sha256sum /sdcard/Android/data/com.vrcommand.quest/files/' + alignment.name))
                self.assertNotIn(fresh['joinTicket'], result.stdout + result.stderr + '\n'.join(commands))
                self.assertNotIn(installed['joinTicket'], result.stdout + result.stderr + '\n'.join(commands))
                raw = current.read_bytes()
                self.commands.unlink()
                repeat = self.run_refresh()
                self.assertEqual(0, repeat.returncode, repeat.stderr)
                self.assertEqual('ticket-file-current', json.loads(repeat.stdout)['status'])
                self.assertEqual(5, len(self.commands.read_text(encoding='utf-8').splitlines()))
                self.assertEqual(raw, current.read_bytes())
                self.assertFalse(list(self.remote.glob('*.tmp')))

    def test_ticket_refresh_rejects_changed_seat_endpoint_pin_or_older_ticket(self):
        current, _, fresh, identities, _ = self.ticket_refresh(self.expiry-100)
        original = current.read_bytes()
        for changes, message in (
                ({'joinTicket': make_ticket(5, 1, self.expiry, *identities[:2], uuid.uuid4())}, 'same original admission'),
                ({'joinTicket': make_ticket(5, 0, self.expiry, *identities)}, 'same original admission'),
                ({'port': 7778}, 'same original admission'),
                ({'roomAlignmentSha256': 'a'*64}, 'original locked MR alignment'),
                ({'joinTicket': make_ticket(5, 1, self.expiry-150, *identities)}, 'later expiry')):
            with self.subTest(changes=changes.keys(), message=message):
                self.write(self.config, {**fresh, **changes})
                self.commands.unlink(missing_ok=True)
                self.assert_rejected(self.run_refresh(), message)
                self.assertEqual(original, current.read_bytes())
                self.assertNotIn(' push ', self.commands.read_text(encoding='utf-8'))
        self.assert_rejected(self.run_refresh('model'), 'authorized Meta Quest 3')

    def test_ticket_refresh_of_plain_vr_only_reads_back_the_connection_file(self):
        current, installed, fresh, _, alignment = self.ticket_refresh(self.expiry-300, mode='VR')
        for key in ('roomAlignmentSha256', 'questPassthrough', 'requestMixedReality'):
            del installed[key]
        self.write(current, installed)
        alignment.unlink()
        result = self.run_refresh()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('ticket-file-refreshed', json.loads(result.stdout)['status'])
        self.assertEqual(dict(installed, joinTicket=fresh['joinTicket']), json.loads(current.read_bytes()))
        commands = self.commands.read_text(encoding='utf-8').splitlines()
        self.assertEqual(6, len(commands))
        self.assertTrue(commands[-1].endswith('/vr-connection.json'))
        self.assertFalse(any('vr-room-alignment-' in command for command in commands))

    def test_ticket_refresh_checks_remote_files_before_replacing_and_cleans_owned_staging(self):
        for fault in ('refresh-source-changed', 'refresh-stage-changed'):
            with self.subTest(fault=fault):
                current, _, _, _, _ = self.ticket_refresh(self.expiry-300)
                original = current.read_bytes()
                result = self.run_refresh(fault)
                self.assert_rejected(result, 'Could not confirm ticket replacement')
                self.assertEqual(original + (b'\n' if fault=='refresh-source-changed' else b''), current.read_bytes())
                self.assertFalse(list(self.remote.glob('*.tmp')))

    def test_ticket_refresh_requires_the_installed_alignment_at_replacement_and_for_current_ticket(self):
        current, _, _, _, _ = self.ticket_refresh(self.expiry-300)
        original = current.read_bytes()
        self.assert_rejected(self.run_refresh('refresh-alignment-at-replace'), 'Room alignment file could not be verified')
        self.assertEqual(original, current.read_bytes())
        self.assertFalse(list(self.remote.glob('*.tmp')))

        current, installed, fresh, _, alignment = self.ticket_refresh(self.expiry)
        self.write(self.config, dict(fresh, joinTicket=installed['joinTicket']))
        original = current.read_bytes()
        alignment.unlink()
        self.commands.unlink(missing_ok=True)
        self.assert_rejected(self.run_refresh(), 'Room alignment file could not be verified')
        self.assertEqual(original, current.read_bytes())
        self.assertNotIn(' push ', self.commands.read_text(encoding='utf-8'))

    def test_ticket_refresh_requires_readback_of_active_config_and_alignment(self):
        for fault, message in (('config-active-changed', 'Player ticket file could not be verified'),
                               ('alignment-changed-after-activation', 'Room alignment file could not be verified')):
            with self.subTest(fault=fault):
                current, installed, fresh, _, _ = self.ticket_refresh(self.expiry-300)
                self.commands.unlink(missing_ok=True)
                result = self.run_refresh(fault)
                self.assert_rejected(result, message)
                self.assertEqual('', result.stdout)
                self.assertEqual(dict(installed, joinTicket=fresh['joinTicket']), json.loads(current.read_bytes()))
                self.assertFalse(list(self.remote.glob('*.tmp')))
                commands = self.commands.read_text(encoding='utf-8')
                for operation in (' install ', ' force-stop ', ' am start '):
                    self.assertNotIn(operation, commands)

    def test_ticket_refresh_live_verifies_original_bytes_through_publish(self):
        with self.live_quest_check(self.player) as (url, key, requests, state):
            options = {'management_api': url, 'management_key': key}
            for mode in ('VR', 'MR'):
                with self.subTest(mode=mode):
                    current, installed, fresh, identities, alignment = self.ticket_refresh(self.expiry-300, mode=mode)
                    original = current.read_bytes()
                    alignment_bytes = alignment.read_bytes()
                    session, player, admission = identities
                    path = f'/api/sessions/{session}/rooms/5/players/{player}/quest-deployment-check'
                    original_file = b'\xef\xbb\xbf' + json.dumps(fresh).encode() + b'\r\n'
                    self.config.write_bytes(original_file)
                    body = {'connectionFile': base64.b64encode(original_file).decode()}
                    if mode == 'MR':
                        body['alignmentFile'] = base64.b64encode(alignment_bytes).decode()
                    expected = (path, f'Bearer {key}', str(admission), body)

                    requests.clear()
                    state['reject'] = 2
                    self.commands.unlink(missing_ok=True)
                    rejected = self.run_refresh(**options)
                    self.assert_rejected(rejected, 'session or admission changed')
                    self.assertEqual([expected] * 2, requests)
                    self.assertEqual(original, current.read_bytes())
                    commands = self.commands.read_text(encoding='utf-8')
                    self.assertIn(' push ', commands)
                    self.assertNotIn('current=$(sha256sum', commands)
                    self.assertFalse(list(self.remote.glob('*.tmp')))

                    state['reject'] = None
                    if mode == 'MR':
                        requests.clear()
                        changed = self.run_refresh('refresh-alignment-changed', **options)
                        self.assert_rejected(changed, 'Room alignment file could not be verified')
                        self.assertEqual([expected] * 2, requests)
                        self.assertEqual(original, current.read_bytes())
                        self.assertFalse(list(self.remote.glob('*.tmp')))
                        alignment.write_bytes(alignment_bytes)

                    requests.clear()
                    self.commands.unlink()
                    refreshed = self.run_refresh(**options)
                    self.assertEqual(0, refreshed.returncode, refreshed.stderr)
                    report = json.loads(refreshed.stdout)
                    self.assertEqual('ticket-file-refreshed', report['status'])
                    self.assertIs(report['managementVerified'], True)
                    self.assertEqual([expected] * 2, requests)
                    self.assertEqual(dict(installed, joinTicket=fresh['joinTicket']), json.loads(current.read_bytes()))
                    self.assertEqual(alignment_bytes, alignment.read_bytes())
                    commands = self.commands.read_text(encoding='utf-8')
                    self.assertEqual(mode == 'MR', f' pull /sdcard/Android/data/com.vrcommand.quest/files/{alignment.name}' in commands)
                    for operation in (' install ', ' force-stop ', ' am start '):
                        self.assertNotIn(operation, commands)
                    for private in (key, fresh['joinTicket'], installed['joinTicket']):
                        self.assertNotIn(private, refreshed.stdout + refreshed.stderr + commands)

                    requests.clear()
                    self.commands.unlink()
                    repeated = self.run_refresh(**options)
                    self.assertEqual(0, repeated.returncode, repeated.stderr)
                    self.assertEqual('ticket-file-current', json.loads(repeated.stdout)['status'])
                    self.assertEqual([expected], requests)
                    self.assertNotIn(' push ', self.commands.read_text(encoding='utf-8'))

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
        self.assertEqual('devices -l', commands[0])
        alignment_readback = next(i for i, line in enumerate(commands) if 'shell sha256sum' in line and line.endswith(f'/vr-room-alignment-{digest}.json'))
        staged_config = next(i for i, line in enumerate(commands) if 'shell sha256sum' in line and '/vr-connection-' in line and line.endswith('.tmp'))
        stop = next(i for i, line in enumerate(commands) if 'shell am force-stop' in line)
        activate = next(i for i, line in enumerate(commands) if 'shell staged=$(sha256sum ' in line and line.endswith("/vr-connection.json'"))
        verified = next(i for i, line in enumerate(commands) if 'shell sha256sum' in line and line.endswith('/vr-connection.json'))
        self.assertEqual(sorted({alignment_readback, staged_config, stop, activate, verified}),
                         [alignment_readback, staged_config, stop, activate, verified])
        self.assertIn('shell am start', commands[-1])
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
        for fault, message in (('config-move', 'Player connection file could not be activated'),
                               ('force-stop', 'Quest app could not be stopped before activating configuration')):
            with self.subTest(fault=fault):
                self.commands.unlink(missing_ok=True)
                active.write_bytes(b'previous configuration')
                self.assert_rejected(self.run_mr(failure=fault), message)
                self.assertEqual(b'previous configuration', active.read_bytes())
                self.assertFalse(list(self.remote.glob('*.tmp')))
                commands = self.commands.read_text(encoding='utf-8').splitlines()
                self.assertTrue(any('shell rm -f' in line for line in commands))
                self.assertFalse(any('shell am start' in line for line in commands))
                if fault == 'force-stop':
                    self.assertTrue(any('shell sha256sum' in line and '/vr-connection-' in line for line in commands))
                    self.assertFalse(any('shell staged=$(sha256sum ' in line and line.endswith("/vr-connection.json'") for line in commands))

    def test_failed_or_wrong_device_identification_never_installs(self):
        self.provision_apk()
        for failure, message in (('getprop','Could not identify the selected Android device'), ('model','not a Meta Quest 3')):
            with self.subTest(failure=failure):
                self.assert_rejected(self.run_mr('-Serial','fixture',failure=failure), message)
        self.assertNotIn(' install ', self.commands.read_text(encoding='utf-8'))

    def test_deployment_refuses_altered_staged_or_active_files_before_launch(self):
        self.provision_apk()
        active = self.remote / 'vr-connection.json'
        original_alignment = self.plan.read_bytes()
        alignment = self.remote / f'vr-room-alignment-{hashlib.sha256(original_alignment).hexdigest()}.json'
        alignment.write_bytes(original_alignment)
        for fault, description in (('alignment-stage-changed', 'Room alignment file'),
                                   ('alignment-late-stage-changed', 'Room alignment file'),
                                   ('config-stage-changed', 'Player connection file'),
                                   ('config-active-changed', 'Player connection file')):
            with self.subTest(fault=fault):
                self.commands.unlink(missing_ok=True)
                active.write_bytes(b'previous configuration')
                result = self.run_mr('-Serial', 'fixture', failure=fault)
                self.assert_rejected(result, f'{description} could not be verified')
                commands = self.commands.read_text(encoding='utf-8')
                if fault.endswith('stage-changed'):
                    self.assertEqual(b'previous configuration', active.read_bytes())
                    self.assertNotIn('shell am force-stop', commands)
                self.assertEqual(original_alignment, alignment.read_bytes())
                self.assertFalse(list(self.remote.glob('*.tmp')))
                self.assertNotIn('shell am start', commands)

    def test_connection_changed_after_staged_verification_preserves_active_file(self):
        self.provision_apk()
        for run in (self.run_script, self.run_mr):
            with self.subTest(mode=run.__name__):
                self.commands.unlink(missing_ok=True)
                active = self.remote / 'vr-connection.json'
                original = b'{"role":"Client","address":"192.168.1.11","port":7777,"joinTicket":"previous"}'
                active.write_bytes(original)
                result = run('-Serial', 'fixture', failure='config-changed-at-stop')
                self.assert_rejected(result, 'Player connection file could not be verified')
                self.assertTrue(active.read_bytes() == original, 'Late mutation replaced the original connection file')
                self.assertFalse(list(self.remote.glob('*.tmp')))
                commands = self.commands.read_text(encoding='utf-8')
                self.assertIn('-t 41 shell am force-stop com.vrcommand.quest', commands)
                self.assertNotIn('shell am start', commands)

    def test_mr_alignment_stays_locked_through_connection_activation(self):
        self.provision_apk()
        active = self.remote / 'vr-connection.json'
        original = b'previous configuration'
        for fault, preserve in (('alignment-changed-at-stop', True), ('alignment-changed-after-activation', False)):
            with self.subTest(fault=fault):
                self.commands.unlink(missing_ok=True)
                active.write_bytes(original)
                result = self.run_mr('-Serial', 'fixture', failure=fault)
                self.assert_rejected(result, 'Room alignment file could not be verified')
                if preserve:
                    self.assertEqual(original, active.read_bytes())
                else:
                    installed = json.loads(active.read_bytes())
                    self.assertEqual(self.player['joinTicket'], installed['joinTicket'])
                    self.assertEqual(hashlib.sha256(self.plan.read_bytes()).hexdigest(), installed['roomAlignmentSha256'])
                self.assertFalse(list(self.remote.glob('*.tmp')))
                commands = self.commands.read_text(encoding='utf-8')
                self.assertIn('-t 41 shell am force-stop com.vrcommand.quest', commands)
                self.assertNotIn('shell am start', commands)


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

    def test_single_player_tracking_reads_the_original_preparing_seat(self):
        session = self.session_ids[3]
        player, admission = str(self.players[17]), str(self.admissions[17])
        config = self.config(4, 2, session, 7777)
        path = self.root / 'connection.json'
        path.write_text(json.dumps(config), encoding='utf-8')
        readiness_url = f'/api/sessions/{session}/readiness'
        frame_url = f'/api/sessions/{session}/world/frames/23'
        original = {'version': 1, 'sessionId': str(session), 'sessionSequence': 7, 'observedSequence': 7,
                    'sampledAtUtc': '2026-11-16T01:00:00.100Z', 'capturedAtUtc': '2026-11-16T01:00:00Z',
                    'sourceState': 'Fresh', 'sourceAgeMilliseconds': 100, 'origin': 'GameServer', 'worldSequence': 23,
                    'players': [{'roomId': 4, 'seat': 2, 'playerId': player, 'admissionId': admission,
                                 'state': 'Participating', 'rigKind': 'Tracked', 'canParticipate': True}]}
        body = tracked_world_player(original['players'][0])
        preparing = {'phase': 'Preparing', 'tick': 0, 'players': [body]}
        original_frame = {'packet': {'sequence': 23, 'observedSequence': 7, 'suspended': False, 'frame': preparing}}
        state = {'readiness': original, 'frame': original_frame}
        requests = []
        key = 'test-operator'

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append((self.path, self.headers.get('Authorization')))
                if self.headers.get('Authorization') != 'Bearer ' + key:
                    self.send_error(403)
                    return
                response = {readiness_url: state['readiness'], frame_url: state['frame']}.get(self.path)
                if response is None:
                    self.send_error(404)
                    return
                payload = json.dumps(response).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        with quest_management_server(Handler) as server:
            worker = Thread(target=server.serve_forever, daemon=True)
            worker.start()
            command = ['pwsh', '-NoProfile', '-NonInteractive', '-File', str(ROOT / 'scripts/deploy-quest.ps1'),
                       '-ClientConfig', str(path), '-VerifyPlayerTracking', '-ManagementApi', f'http://127.0.0.1:{server.server_port}']
            cases = (
                (original, original_frame, 'tracked-ready', True),
                (dict(original, players=[dict(original['players'][0], admissionId=str(uuid.uuid4()))]),
                 original_frame, 'admission-changed', False),
                (dict(original, origin='Simulation'), original_frame, 'source-capture-unverified', False),
                (dict(original, sessionId=str(uuid.uuid4())), original_frame, 'readiness-invalid', False),
                (original, None, 'source-frame-unverified', True),
                (original, {'packet': dict(original_frame['packet'], frame={'phase': 'Running', 'tick': 1})},
                 'source-outside-preparing', True),
                (original, {'packet': dict(original_frame['packet'], frame={'phase': 'Preparing', 'tick': 0})},
                 'source-frame-unverified', True),
            )
            invalid_actors = ([], [dict(body, id=str(uuid.uuid4()))], [dict(body, roomId=3)], [body, body],
                              [dict(body, connected=False)], [dict(body, connected='true')],
                              [dict(body, health=0)], [dict(body, rig={'kind': 'Simulated'})],
                              [dict(body, rig={'kind': ['Tracked']})])
            cases += tuple((original, {'packet': dict(original_frame['packet'], frame=dict(preparing, players=players))},
                            'source-seat-unverified', True) for players in invalid_actors)
            try:
                for snapshot, frame, expected, reads_frame in cases:
                    with self.subTest(expected=expected, body=(frame or {}).get('packet', {}).get('frame', {}).get('players')):
                        state.update(readiness=snapshot, frame=frame)
                        requests.clear()
                        result = subprocess.run(command, env={**os.environ, 'VR_COMMAND_MASTER_KEY': key},
                                                capture_output=True, encoding='utf-8', timeout=15)
                        ready = expected == 'tracked-ready'
                        self.assertEqual(0 if ready else 1, result.returncode, result.stderr)
                        report = json.loads(result.stdout)
                        self.assertEqual(('player', ready), (report['scope'], report['complete']))
                        seat, = report['seats']
                        self.assertEqual((str(session), 4, 3, expected),
                                         (seat['sessionId'], seat['roomId'], seat['seat'], seat['status']))
                        if ready:
                            self.assertEqual((23, 7), (seat['worldSequence'], seat['observedSequence']))
                            self.assertEqual(1, report['evidenceVersion'])
                            identity_bytes = f'quest-player-readiness-v1/{session}/{player}/{admission}'.encode('ascii')
                            self.assertEqual(hashlib.sha256(identity_bytes).hexdigest(), seat['admissionSha256'])
                        else:
                            self.assertNotIn('admissionSha256', seat)
                            self.assertNotIn('evidenceVersion', report)
                        for secret in (key, config['joinTicket'], player, admission):
                            self.assertNotIn(secret, result.stdout + result.stderr)
                        urls = [readiness_url, frame_url] if reads_frame else [readiness_url]
                        self.assertEqual([(url, 'Bearer ' + key) for url in urls], requests)
            finally:
                server.shutdown()
                worker.join()

    def test_quest_tracking_keeps_original_freshness_deadline_through_frame_readback(self):
        runner = self.root / 'readiness-freshness.ps1'
        runner.write_text(r'''
param($Source, $Mode)
$ErrorActionPreference = 'Stop'
$functions = @('Test-JsonInteger', 'Test-TrackedReadinessSnapshot', 'Get-TrackedSeatStatus', 'New-TrackedSeatReport',
               'New-PlayerTrackedSeatReport', 'Confirm-PlayerTrackedSeat', 'Read-TrackedSeatReport', 'Get-QuestSha256',
               'Confirm-ReadbackFreshness')
$ast = [Management.Automation.Language.Parser]::ParseFile($Source, [ref]$null, [ref]$null)
foreach ($definition in $ast.FindAll({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and
                                      $node.Name -cin $functions }, $false)) {
    . ([scriptblock]::Create($definition.Extent.Text))
}
$session = '91bdc053-1490-468f-bd0a-7fd851570977'
$player = 'a95a4a2c-583c-4750-a16a-983c30d1a4f4'
$admission = '8bb407fd-9dc4-4c2d-b467-7fe971dab013'
$second = 'c609db2c-4b64-4680-9a6a-7d752804fee0'
$sampled = [DateTimeOffset]::UtcNow
$ticket = @{ SessionId = [Guid]$session; PlayerId = [Guid]$player; AdmissionId = [Guid]$admission;
             RoomId = 1; Seat = 0; ExpiresAtUtc = $sampled.AddMinutes(1) }
$row = @{roomId=1; seat=0; playerId=$player; admissionId=$admission; canParticipate=$true; state='Participating'; rigKind='Tracked'}
$snapshot = [pscustomobject]@{ version=1; sessionId=$session; sourceState='Fresh'; origin='GameServer'; worldSequence=30;
    sessionSequence=18; observedSequence=18; sourceAgeMilliseconds=950; sampledAtUtc=$sampled; capturedAtUtc=$sampled.AddMilliseconds(-950);
    players=@([pscustomobject]$row) }
$other = $snapshot.PSObject.Copy()
$other.sessionId = $second
$other.sourceAgeMilliseconds = 0
$other.capturedAtUtc = $sampled
$other.players = @([pscustomobject]($row.Clone()))
$other.players[0].roomId = 2
$secondTicket = $ticket.Clone()
$secondTicket.SessionId = [Guid]$second; $secondTicket.RoomId = 2
$script:reads = 0
function Read-ManagementJson { return @{ Document=$snapshot; Elapsed=5 } }
function Read-VenueTrackedReadiness {
    $snapshots = @{ $session = $snapshot }
    if (-not $Mode.StartsWith('linked-')) { $snapshots[$second] = $other }
    return @{ Sessions=$snapshots; MaxAge=1500; SampledAtUtc=$sampled; Elapsed=5 }
}
function Confirm-PreparingReadinessFrames {
    $script:reads++
    if ($Mode.EndsWith('-late')) { Start-Sleep -Milliseconds 700 }
}
$target = @{ Origin = [Uri]'http://127.0.0.1:1' }
if ($Mode.StartsWith('single-')) { $report = Confirm-PlayerTrackedSeat $target $ticket }
else {
    $DeploymentReport = 'original'
    $topology = if ($Mode.StartsWith('linked-')) { 'Linked' } else { 'Independent' }
    if ($topology -ceq 'Linked') {
        $snapshot.players += $other.players
        $secondTicket.SessionId = $ticket.SessionId
    }
    $map = @(@{roomId=1; seat=1}, @{roomId=2; seat=1})
    $venue = @{ Report=@{ topology=$topology; mode='VR' }; SeatHeadsets=@{'1/1'='Quest3'; '2/1'='Quest3'};
                Connections=@{'1/1'=@{Ticket=$ticket}; '2/1'=@{Ticket=$secondTicket}} }
    $report = Read-TrackedSeatReport $target $venue $map 10000
}
@{ report=$report; readbacks=$script:reads } | ConvertTo-Json -Depth 8 -Compress
''', encoding='utf-8')
        command = ['pwsh', '-NoProfile', '-NonInteractive', '-File', str(runner), str(ROOT / 'scripts/deploy-quest.ps1')]
        for mode, expected in (
            ('single-fresh', ['tracked-ready']), ('single-late', ['source-expired-in-transit']),
            ('venue-fresh', ['tracked-ready'] * 2), ('venue-late', ['source-expired-in-transit', 'tracked-ready']),
            ('linked-fresh', ['tracked-ready'] * 2), ('linked-late', ['source-expired-in-transit'] * 2),
        ):
            with self.subTest(mode=mode):
                response = subprocess.run([*command, mode], capture_output=True, text=True, encoding='utf-8', timeout=10)
                self.assertEqual(0, response.returncode, response.stderr)
                result = json.loads(response.stdout)
                self.assertEqual(1, result['readbacks'])
                report = result['report']
                self.assertEqual(expected, [seat['status'] for seat in report['seats']])
                self.assertIs(report['complete'], mode.endswith('-fresh'))
                if mode.startswith('single-'):
                    self.assertEqual(mode.endswith('-fresh'), 'evidenceVersion' in report)
                    self.assertEqual(mode.endswith('-fresh'), 'admissionSha256' in report['seats'][0])

    def test_single_quest_wait_uses_a_fresh_complete_sample_and_stops_at_original_boundaries(self):
        session, player, admission = self.session_ids[0], self.players[0], self.admissions[0]
        snapshot = {'version': 1, 'sessionId': str(session), 'sessionSequence': 7, 'observedSequence': 7,
                    'sampledAtUtc': '2026-11-17T00:00:00.010Z', 'capturedAtUtc': '2026-11-17T00:00:00Z',
                    'sourceState': 'Fresh', 'sourceAgeMilliseconds': 10, 'origin': 'GameServer', 'worldSequence': 23,
                    'players': [{'roomId': 1, 'seat': 0, 'playerId': str(player), 'admissionId': str(admission),
                                 'state': 'Participating', 'rigKind': 'Tracked', 'canParticipate': True}]}
        fixture = self.root / 'snapshot.json'
        fixture.write_text(json.dumps(snapshot), encoding='utf-8')
        original = ROOT / 'scripts/deploy-quest.ps1'
        script = self.root / original.name
        shutil.copyfile(original.with_name('quest-adb-process.ps1'), self.root / 'quest-adb-process.ps1')
        script.write_text(original.read_text(encoding='utf-8').replace("if ($PSCmdlet.ParameterSetName -eq 'Venue') {", r'''
$script:sampleCount = 0
function Read-ManagementJson($Target, $Url, [int]$RequestMilliseconds) {
    $script:sampleCount++
    [IO.File]::AppendAllText($env:QUEST_READINESS_AUDIT, "$($Url.AbsolutePath) $RequestMilliseconds`n")
    $document = Get-Content -LiteralPath $env:QUEST_READINESS_FIXTURE -Raw | ConvertFrom-Json
    switch ($env:QUEST_READINESS_CASE) {
        'recover' { if ($script:sampleCount -eq 1) { $document.players[0].rigKind = 'Simulated' } }
        'changed' { $document.players[0].admissionId = [Guid]::NewGuid().ToString('D') }
        'ended' { $document.sourceState = 'Ended' }
        'slow' { Start-Sleep -Milliseconds ($RequestMilliseconds + 75) }
        'pending' { $document.sourceState = 'WaitingFrame' }
        'denied' { return @{ Status = 'readiness-access-denied' } }
    }
    return @{ Document = $document; Elapsed = 5 }
}
function Confirm-PreparingReadinessFrames($Target, $Report, $PlayersBySeat, [int]$RequestMilliseconds) {
    [IO.File]::AppendAllText($env:QUEST_READINESS_AUDIT, "frame:$($Report.seats[0].worldSequence) $RequestMilliseconds`n")
}
function Confirm-VenueReadback($Venue) {
    foreach ($key in $Venue.Connections.Keys) { $Venue.SeatHeadsets[$key] = 'Quest3' }
}
function Read-VenueTrackedReadiness($Target, $Venue, [int]$RequestMilliseconds) {
    $script:sampleCount++
    [IO.File]::AppendAllText($env:QUEST_READINESS_AUDIT, "venue $RequestMilliseconds`n")
    $sampled = [DateTimeOffset]::UtcNow
    $sessions = @{}
    foreach ($entry in $Venue.Connections.Values) {
        $ticket = $entry.Ticket
        $id = $ticket.SessionId.ToString('D')
        if (-not $sessions.ContainsKey($id)) {
            $sessions[$id] = @{ sessionId=$id; sampledAtUtc=$sampled; sourceState='Fresh'; origin='GameServer'; worldSequence=23;
                                sessionSequence=7; observedSequence=7; sourceAgeMilliseconds=10; players=@() }
        }
        $rig = if ($script:sampleCount -eq 1 -and $ticket.RoomId -eq 1) { 'Simulated' } else { 'Tracked' }
        $sessions[$id].players += @{ roomId=$ticket.RoomId; seat=$ticket.Seat; playerId=$ticket.PlayerId.ToString('D');
            admissionId=$ticket.AdmissionId.ToString('D'); state='Participating'; rigKind=$rig; canParticipate=$true }
    }
    return @{ Sessions=$sessions; SampledAtUtc=$sampled; MaxAge=1500; Elapsed=5 }
}
if ($PSCmdlet.ParameterSetName -eq 'Venue') {''', 1), encoding='utf-8')
        audit = self.root / 'readiness-audit.log'
        connection = self.root / 'original.json'
        command = ['pwsh', '-NoProfile', '-NonInteractive', '-File', str(script), '-ClientConfig', str(connection),
                   '-ManagementApi', 'http://127.0.0.1:1', '-VerifyPlayerTracking']
        key = 'private-wait-operator-fixture'

        def invoke(mode, seconds, expiry_seconds=30):
            audit.unlink(missing_ok=True)
            ticket = make_ticket(1, 0, int(time.time()) + expiry_seconds, session, player, admission)
            connection.write_text(json.dumps({'role': 'Client', 'address': '192.168.1.10', 'port': 7777,
                                             'joinTicket': ticket}), encoding='utf-8')
            flags = ['-WaitForTrackedSeconds', str(seconds)] if seconds is not None else []
            response = subprocess.run(command + flags, capture_output=True, text=True, encoding='utf-8', timeout=15,
                                      env={**os.environ, 'VR_COMMAND_MASTER_KEY': key, 'QUEST_READINESS_FIXTURE': str(fixture),
                                           'QUEST_READINESS_AUDIT': str(audit), 'QUEST_READINESS_CASE': mode})
            self.assertEqual('', response.stderr)
            for secret in (key, ticket, str(admission), str(player)):
                self.assertNotIn(secret, response.stdout)
            report = json.loads(response.stdout)
            self.assertEqual(0 if report['complete'] else 1, response.returncode)
            calls = [line.split() for line in audit.read_text(encoding='utf-8').splitlines()]
            readiness = [int(ms) for route, ms in calls if route == f'/api/sessions/{session}/readiness']
            if seconds is not None:
                self.assertEqual(len(readiness), report['wait']['samples'])
                self.assertTrue(all(0 < ms <= seconds * 1000 for ms in readiness))
            return report, calls

        original_report, calls = invoke('recover', None)
        self.assertNotIn('wait', original_report)
        self.assertEqual('not-tracked', original_report['seats'][0]['status'])
        self.assertEqual(1, len(calls))
        ready, calls = invoke('recover', 5)
        self.assertEqual({'maximumSeconds': 5, 'samples': 2, 'outcome': 'ready'}, ready['wait'])
        self.assertEqual((1, 23), (ready['evidenceVersion'], ready['seats'][0]['worldSequence']))
        self.assertIn('frame:23', [route for route, _ in calls])
        for mode, outcome in (('changed', 'admission-changed'), ('ended', 'source-outside-preparing'),
                              ('denied', 'readiness-access-denied'), ('slow', 'timed-out')):
            with self.subTest(mode=mode):
                stopped, _ = invoke(mode, 1 if mode == 'slow' else 5)
                self.assertEqual(outcome, stopped['wait']['outcome'])
                self.assertEqual(1, stopped['wait']['samples'])
                self.assertNotIn('evidenceVersion', stopped)
        expired, _ = invoke('pending', 6, expiry_seconds=3)
        self.assertEqual('ticket-expired', expired['wait']['outcome'])
        self.assertEqual('ticket-expired', expired['seats'][0]['status'])
        self.assertNotIn('evidenceVersion', expired)

        for topology in ('Independent', 'Linked'):
            with self.subTest(topology=topology):
                audit.unlink()
                files, _ = self.vr_bundle(topology, players_per_room=1)
                result = self.run_bundle(files, '-ManagementApi', 'http://127.0.0.1:1', '-VerifyTrackedSeats', '-AllHeadsets',
                                         '-WaitForTrackedSeconds', '5', script=script, environment={**os.environ,
                                            'VR_COMMAND_MASTER_KEY': key, 'QUEST_READINESS_AUDIT': str(audit)})
                self.assertEqual(0, result.returncode, result.stderr)
                venue = json.loads(result.stdout)
                self.assertEqual({'maximumSeconds': 5, 'samples': 2, 'outcome': 'ready'}, venue['wait'])
                self.assertEqual(['tracked-ready'] * 5, [seat['status'] for seat in venue['seats']])
                self.assertEqual(['venue'] * 2, [line.split()[0] for line in audit.read_text().splitlines()])

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

    def vr_bundle(self, topology, players_per_room=5):
        manifest, seats = self.prepare(topology)
        manifest['mode'] = 'VR'
        if players_per_room != 5:
            manifest['playersPerRoom'] = players_per_room
        files = {}
        for room in manifest['rooms']:
            room_id = room['roomId']
            room.pop('alignmentFile')
            room['ticketsZip'] = f'room-{room_id:02}-connections.zip'
            configs = dict(list(seats[room_id].items())[:players_per_room])
            seats[room_id] = configs
            first = next(iter(configs.values()))
            room.update(address=first['address'], port=first['port'],
                        seats=[{'seat': seat, 'name': f'Player {room_id}/{seat}'} for seat in range(1, players_per_room + 1)])
            tickets = io.BytesIO()
            with zipfile.ZipFile(tickets, 'w') as archive:
                for name, config in configs.items():
                    archive.writestr(name, json.dumps(config))
            files[room['ticketsZip']] = tickets.getvalue()
        files['venue.json'] = json.dumps(manifest).encode()
        return files, seats

    def write_bundle(self, files, name='quest-mr-venue.zip'):
        bundle = self.root / name
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

    def test_mr_and_mixed_bundle_pilot_requires_exact_seats_and_preserves_alignment(self):
        for mode, count in [('MR', 1), ('Mixed', 2)]:
            with self.subTest(mode=mode, count=count):
                files, _ = self.bundle('Linked') if mode == 'MR' else self.mixed_bundle()
                manifest = json.loads(files['venue.json'])
                manifest['playersPerRoom'] = count
                files['venue.json'] = json.dumps(manifest)
                self.assertNotEqual(0, self.run_bundle(files).returncode)
                for room in manifest['rooms']:
                    name = room['ticketsZip']
                    reduced = io.BytesIO()
                    with zipfile.ZipFile(io.BytesIO(files[name])) as original, zipfile.ZipFile(reduced, 'w') as pilot:
                        for seat in range(1, count + 1):
                            config = f"room-{room['roomId']:02}-seat-{seat:02}.json"
                            pilot.writestr(config, original.read(config))
                    files[name] = reduced.getvalue()

                result = self.run_bundle(files)
                self.assertEqual(0, result.returncode, result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual((manifest['topology'], 5 * count, True),
                                 (report['topology'], report['seats'], report['alignmentPinsVerified']))
                if mode == 'Mixed':
                    self.assertEqual(mode, report['mode'])
                changed = dict(files)
                changed['room-02-alignment.json'] += b'\r\n'
                self.assert_rejected(self.run_bundle(changed), 'alignment')

                if mode == 'MR':
                    for name, data in files.items():
                        content = data.encode() if isinstance(data, str) else data
                        (self.root / name).write_bytes(content)
                    extracted = subprocess.run(['pwsh', '-NoProfile', '-NonInteractive', '-File',
                                                str(ROOT / 'scripts/deploy-quest.ps1'), '-VenueManifest',
                                                str(self.root / 'venue.json')], capture_output=True, encoding='utf-8', timeout=20)
                    self.assertEqual(0, extracted.returncode, extracted.stderr)
                    self.assertEqual(5 * count, json.loads(extracted.stdout)['seats'])

    def device_map(self):
        path = self.root / 'device-map.json'
        document = {'version': 1, 'seats': [{'roomId': room, 'seat': seat, 'serial': f'fixture-{(room-1)*5+seat:02}'}
                                          for room in range(1, 6) for seat in range(1, 6)]}
        document['seats'].reverse()
        path.write_text(json.dumps(document), encoding='utf-8')
        return path, document

    def test_windows_staging_copies_only_live_verified_original_vr_seats(self):
        requests = []
        state = {'topology': 'Linked', 'quest': None, 'admission_changed': False, 'source_stale': False,
                 'reject_after_staging': False, 'staged_files': []}
        root = self.root
        key = 'PRIVATE_WINDOWS_TEST_MASTER'

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append((self.path, self.headers.get('Authorization'), body))
                strict = body.get('requireLiveSource') is True
                if state['reject_after_staging']:
                    state['staged_files'] = sorted(path.name for path in root.glob('.vr-windows-*/*.json'))
                stale = strict and (state['source_stale'] or bool(state['staged_files']))
                rows = [{'roomId': room, 'seat': seat, 'headset': 'Quest3' if (room, seat) == state['quest'] else 'ViveXr',
                         'status': ('source-stale' if stale and room == 5 else
                                    'admission-changed' if state['admission_changed'] and (room, seat) == (5, 4) else 'matched')}
                        for room in range(1, 6) for seat in range(5)]
                matched = all(row['status'] == 'matched' for row in rows)
                receipt = {'topology': state['topology'], 'allMatched': matched, 'seats': rows}
                if strict:
                    receipt['liveSourceVerified'] = matched
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(receipt).encode())

            def log_message(self, *args):
                pass

        with quest_management_server(Handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                mapping = self.root / 'Windows seat map.json'
                env = {**os.environ, 'VR_COMMAND_MASTER_KEY': key}

                def stage(files, rows, output):
                    mapping.write_text(json.dumps({'version': 1, 'seats': rows}), encoding='utf-8')
                    return self.run_bundle(files, '-WindowsSeatMap', str(mapping), '-WindowsOutputDirectory', str(output),
                                           '-ManagementApi', f'http://127.0.0.1:{server.server_port}', environment=env)

                files, _ = self.vr_bundle('Linked')
                all_seats = [{'roomId': room, 'seat': seat, 'station': f'R{room}-S{seat}'}
                             for room in range(1, 6) for seat in range(1, 6)]
                blocked = self.root / 'Unavailable Windows delivery'
                state['source_stale'] = True
                self.assert_rejected(stage(files, all_seats, blocked), 'Room 5 seat 1: source-stale')
                self.assertFalse(blocked.exists())
                self.assertEqual([], list(self.root.glob('.vr-windows-*')))
                state['source_stale'] = False
                state['reject_after_staging'] = True
                self.assert_rejected(stage(files, all_seats, blocked), 'Room 5 seat 1: source-stale')
                self.assertFalse(blocked.exists())
                self.assertEqual(25, len(state['staged_files']))
                self.assertEqual([], list(self.root.glob('.vr-windows-*')))
                state.update(reject_after_staging=False, staged_files=[])
                output = self.root / 'Windows delivery'
                result = stage(files, all_seats[::-1], output)
                self.assertEqual(0, result.returncode, result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(('Linked', True, 25), (report['topology'], report['managementVerified'], len(report['seats'])))
                self.assertIs(report['liveSourceVerified'], True)
                self.assertEqual(all_seats, [{key: row[key] for key in ('roomId', 'seat', 'station')} for row in report['seats']])
                self.assertEqual(5, len(requests))
                self.assertEqual(requests[-2], requests[-1])
                path, auth, body = requests[-1]
                self.assertEqual(('/api/vr-deployment/venue-check', f'Bearer {key}'), (path, auth))
                self.assertIs(body['requireLiveSource'], True)
                self.assertIs(body['allowLoopback'], True)
                before = {p.name: p.read_bytes() for p in output.iterdir()}
                self.assertEqual(25, len(before))
                for row in report['seats']:
                    room, seat = row['roomId'], row['seat']
                    with zipfile.ZipFile(io.BytesIO(files[f'room-{room:02}-connections.zip'])) as original:
                        raw = original.read(f'room-{room:02}-seat-{seat:02}.json')
                    self.assertEqual(raw, before[row['file']])
                    self.assertEqual(raw, base64.b64decode(body['rooms'][room-1]['connectionFiles'][seat-1]))
                self.assertNotIn(key, result.stdout + result.stderr)
                self.assertNotIn('joinTicket', result.stdout)
                self.assert_rejected(stage(files, all_seats, output), 'new Windows output directory')
                self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

                fresh = self.root / 'Rejected'
                one = all_seats[0]
                self.assert_rejected(stage(files, [one, {**all_seats[1], 'station': 'r1-s1'}], fresh), 'only once')
                self.assert_rejected(stage(files, [{**one, 'station': '../outside'}], fresh), 'station label')
                self.assertEqual(5, len(requests))
                state['quest'] = (1, 0)
                self.assert_rejected(stage(files, [one], fresh), 'not assigned to VIVE XR')
                state['admission_changed'] = True
                self.assert_rejected(stage(files, [all_seats[1]], fresh), 'Room 5 seat 5: admission-changed')
                self.assertFalse(fresh.exists())

                mixed, _ = self.mixed_bundle()
                state.update(topology='Independent', quest=None, admission_changed=False)
                self.assert_rejected(stage(mixed, [all_seats[5]], fresh), 'belongs to an MR room')
                self.assertEqual(7, len(requests))
                result = stage(mixed, [one], fresh)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual('/api/mixed-deployment/venue-check', requests[-1][0])
                self.assertEqual(requests[-2], requests[-1])
                self.assertIs(requests[-1][2]['requireLiveSource'], True)
                self.assertNotIn('allowLoopback', requests[-1][2])
                self.assertEqual(1, len(list(fresh.iterdir())))
                self.assertEqual([], list(self.root.glob('.vr-windows-*')))
            finally:
                server.shutdown()
                thread.join(timeout=5)

    def mock_capture_devices(self, rows, topology, *, held=False, wrong_seat=None, startup_gates=None,
                             reconnect_gates=None, rebind_seat=None, transport_base=0):
        expected = {}
        transports = {serial: transport_base + index
                      for index, serial in enumerate(sorted(row['serial'] for row in rows), 1)}
        self.root.joinpath('adb-transports.json').write_text(json.dumps(transports), encoding='utf-8')
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
            connected = line(f'VR_CLIENT_CONNECTED id={index+1}')
            ending = line('VR_CLIENT_DEBRIEF_FINAL ' + json.dumps(result)) + line('VR_CLIENT_DISCONNECTED')
            gate = (startup_gates or {}).get((room, seat))
            reconnect_gate = (reconnect_gates or {}).get((room, seat))
            outage = line('VR_CLIENT_DISCONNECTED') if reconnect_gate else b''
            restored = line(f'VR_CLIENT_CONNECTED id={index+101}') if reconnect_gate else b''
            (self.root / serial).write_text(f'''import json, sys, time
from pathlib import Path
if sys.argv[1:] == ['shell', 'pidof', 'com.vrcommand.quest']:
    print(7342)
else:
    assert sys.argv[1:] == ['logcat', '-b', 'main', '--pid=7342', '-v', 'threadtime', '-s', 'Unity:I']
    if {gate is not None!r}:
        gate = Path({str(gate)!r})
        until = time.monotonic() + 15
        while not gate.is_file() and time.monotonic() < until:
            time.sleep(.05)
        assert gate.is_file()
    sys.stdout.buffer.write({startup!r})
    sys.stdout.buffer.flush()
    if {(room, seat) == rebind_seat!r}:
        inventory = Path('adb-transports.json')
        current = json.loads(inventory.read_bytes())
        current[{serial!r}] += 100
        update = inventory.with_suffix('.tmp')
        update.write_text(json.dumps(current), encoding='utf-8')
        update.replace(inventory)
    sys.stdout.buffer.write({connected + outage!r})
    sys.stdout.buffer.flush()
    if {reconnect_gate is not None!r}:
        gate = Path({str(reconnect_gate)!r})
        until = time.monotonic() + 25
        while not gate.is_file() and time.monotonic() < until:
            time.sleep(.05)
        assert gate.is_file()
        sys.stdout.buffer.write({restored!r})
        sys.stdout.buffer.flush()
    until = time.monotonic() + 25
    while {held!r} and not Path('release').exists() and time.monotonic() < until:
        time.sleep(.05)
    sys.stdout.buffer.write({ending!r})
    sys.stdout.buffer.flush()
    time.sleep(60)
''', encoding='utf-8')
            expected[room, seat] = (str(session), port, startup + connected + outage + restored + ending)
        return expected

    def capture_command(self, files, mapping, output, *flags):
        return [sys.executable, str(CAPTURE_FIXTURE), '--adb', sys.executable,
                '--venue-bundle', str(self.write_bundle(files)), '--device-map', str(mapping),
                '--output-directory', str(output), '--seconds', '35', *flags]

    def test_capture_rejects_rebound_transport_with_equal_process_id_and_retries_only_failed_seat(self):
        files, _ = self.vr_bundle('Linked')
        mapping, document = self.device_map()
        rows = [row for row in document['seats'] if row['roomId'] == 1 and row['seat'] in (1, 2)]
        mapping.write_text(json.dumps(dict(document, seats=rows)), encoding='utf-8')
        expected = self.mock_capture_devices(rows, 'Linked', rebind_seat=(1, 1))
        first = self.root / 'first capture'
        command = self.capture_command(files, mapping, first, '--allow-partial-map')
        result = subprocess.run(command, cwd=self.root, capture_output=True, encoding='utf-8', timeout=20)
        self.assertEqual(1, result.returncode, result.stderr + result.stdout)
        report_path = first / 'capture-report.json'
        report = json.loads(report_path.read_bytes())
        self.assertEqual((False, 1), (report['complete'], report['capturedSeats']))
        failed, healthy = report['seats']
        self.assertFalse(failed['complete'])
        self.assertIn('Expected one running Quest game process', failed['reason'])
        self.assertEqual(expected[1, 1][2], (first / failed['partial']).read_bytes())
        self.assertFalse((first / 'room-01-seat-01-logcat.txt').exists())
        self.assertEqual(expected[1, 2][2], (first / healthy['log']).read_bytes())
        before = {path.name: path.read_bytes() for path in first.iterdir()}
        calls = [json.loads(line) for line in (self.root / 'adb-calls.jsonl').read_text().splitlines()]
        self.assertEqual(['devices', '-l'], calls[0])
        self.assertTrue(all(call[0] == '-t' and call[1] in ('1', '2') for call in calls[1:]))

        (self.root / 'adb-calls.jsonl').unlink()
        self.mock_capture_devices(rows, 'Linked', transport_base=200)
        second = self.root / 'recovered capture'
        command[command.index('--output-directory') + 1] = str(second)
        recovered = subprocess.run([*command, '--retry-incomplete', str(report_path)], cwd=self.root,
                                   capture_output=True, encoding='utf-8', timeout=20)
        self.assertEqual(0, recovered.returncode, recovered.stderr)
        self.assertEqual(expected[1, 1][2], (second / 'room-01-seat-01-logcat.txt').read_bytes())
        self.assertEqual(before, {path.name: path.read_bytes() for path in first.iterdir()})
        calls = [json.loads(line) for line in (self.root / 'adb-calls.jsonl').read_text().splitlines()]
        self.assertEqual(['devices', '-l'], calls[0])
        self.assertTrue(all(call[:2] == ['-t', '201'] for call in calls[1:]))
        self.assertTrue(any(call[2] == 'logcat' for call in calls[1:]))

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

    def test_venue_capture_only_announces_ready_when_disconnected_seat_rejoins(self):
        files, _ = self.vr_bundle('Linked')
        mapping, document = self.device_map()
        rows = [row for row in document['seats'] if row['roomId'] == 1 and row['seat'] in (1, 2)]
        mapping.write_text(json.dumps(dict(document, seats=rows)), encoding='utf-8')
        output = self.root / 'reconnect capture'
        start_second = self.root / 'start-second'
        reconnect_first = self.root / 'reconnect-first'
        expected = self.mock_capture_devices(rows, 'Linked', held=True, startup_gates={(1, 2): start_second},
                                             reconnect_gates={(1, 1): reconnect_first})
        disconnected, second_ready, venue_ready = Event(), Event(), Event()
        stages = []
        with subprocess.Popen(self.capture_command(files, mapping, output, '--allow-partial-map'), cwd=self.root,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8') as process:
            def collect():
                for line in process.stderr:
                    row = json.loads(line)
                    status = (row['stage'], row.get('seat'))
                    stages.append(status)
                    if status == ('capture-disconnected', 1):
                        disconnected.set()
                    elif status == ('capture-ready', 2):
                        second_ready.set()
                    elif status == ('venue-capture-ready', None):
                        venue_ready.set()

            collector = Thread(target=collect)
            collector.start()
            try:
                self.assertTrue(disconnected.wait(15), stages)
                start_second.touch()
                self.assertTrue(second_ready.wait(10), stages)
                reconnect_first.touch()
                self.assertTrue(venue_ready.wait(10), stages)
            finally:
                start_second.touch()
                reconnect_first.touch()
                (self.root / 'release').touch()
                process.wait(timeout=20)
                collector.join(timeout=5)
            self.assertEqual(0, process.returncode, stages)
        self.assertEqual([('capture-ready', 1), ('capture-disconnected', 1), ('capture-ready', 2),
                          ('capture-ready', 1), ('venue-capture-ready', None)], stages)
        for seat in (1, 2):
            self.assertEqual(expected[1, seat][2], (output / f'room-01-seat-{seat:02}-logcat.txt').read_bytes())

    def test_venue_capture_does_not_announce_ready_after_a_seat_already_finished(self):
        files, _ = self.vr_bundle('Linked')
        mapping, document = self.device_map()
        output = self.root / 'nonoverlapping capture'
        first_log = output / 'room-01-seat-01-logcat.txt'
        expected = self.mock_capture_devices(document['seats'], 'Linked', startup_gates={(5, 5): first_log})

        result = subprocess.run(self.capture_command(files, mapping, output), cwd=self.root,
                                capture_output=True, encoding='utf-8', timeout=25)

        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads((output / 'capture-report.json').read_bytes())
        self.assertEqual((True, 25, 25), (report['complete'], report['expectedSeats'], report['capturedSeats']))
        for row in report['seats']:
            _, _, original = expected[row['roomId'], row['seat']]
            self.assertEqual(original, (output / row['log']).read_bytes())
            self.assertEqual(hashlib.sha256(original).hexdigest(), row['sha256'])
        stages = [json.loads(line) for line in result.stderr.splitlines()]
        self.assertEqual(25, sum(row['stage'] == 'capture-ready' for row in stages))
        self.assertNotIn('venue-capture-ready', [row['stage'] for row in stages])

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

        expected = self.mock_capture_devices(document['seats'], 'Independent')
        retry_output = self.root / 'retried capture'
        retry = list(command)
        retry[retry.index('--output-directory') + 1] = str(retry_output)
        retry += ['--allow-partial-map', '--retry-incomplete', str(output / 'capture-report.json')]
        document['seats'].reverse()
        mapping.write_text(json.dumps(document), encoding='utf-8')
        finished = subprocess.run(retry, cwd=self.root, capture_output=True, encoding='utf-8', timeout=20)
        self.assertEqual(0, finished.returncode, finished.stderr)
        recovered = json.loads((retry_output / 'capture-report.json').read_bytes())
        self.assertEqual((True, 1, 1), (recovered['complete'], recovered['expectedSeats'], recovered['capturedSeats']))
        self.assertEqual(report['captureBinding'], recovered['captureBinding'])
        bundle = Path(command[command.index('--venue-bundle') + 1])
        self.assertEqual(hashlib.sha256(bundle.read_bytes()).hexdigest(), report['captureBinding']['venueSha256'])
        seat, = recovered['seats']
        self.assertEqual((2, 3), (seat['roomId'], seat['seat']))
        self.assertEqual(expected[2, 3][2], (retry_output / seat['log']).read_bytes())
        self.assertEqual(before, {path.name: path.read_bytes() for path in output.iterdir()})
        self.assertEqual(1, sum(json.loads(line)['stage'] == 'capture-ready' for line in finished.stderr.splitlines()))

        wrong_prior = self.root / 'wrong-prior.json'
        failed['port'] += 1
        wrong_prior.write_text(json.dumps(report), encoding='utf-8')
        unstarted = self.root / 'unstarted capture'
        retry[retry.index('--output-directory') + 1] = str(unstarted)
        retry[-1] = str(wrong_prior)
        rejected = subprocess.run(retry, cwd=self.root, capture_output=True, encoding='utf-8', timeout=20)
        self.assertEqual(1, rejected.returncode, rejected.stderr)
        self.assertIn('does not match the original deployment seats', rejected.stderr)
        self.assertFalse(unstarted.exists())

    def test_capture_retry_rejects_changed_zip_or_device_assignment_before_adb(self):
        files, _ = self.mixed_bundle()
        mapping, document = self.device_map()
        document['seats'] = [row for row in document['seats'] if (row['roomId'], row['seat']) in {(2, 3), (5, 4)}]
        mapping.write_text(json.dumps(document), encoding='utf-8')
        self.mock_capture_devices(document['seats'], 'Independent', wrong_seat=(2, 3))
        output = self.root / 'capture first'
        command = self.capture_command(files, mapping, output) + ['--allow-partial-map']
        original = subprocess.run(command, cwd=self.root, capture_output=True, encoding='utf-8', timeout=20)
        self.assertEqual(1, original.returncode, original.stderr)
        report_path = output / 'capture-report.json'
        report = json.loads(report_path.read_bytes())
        self.assertEqual(1, report['capturedSeats'])
        originals = {path.name: path.read_bytes() for path in output.iterdir()}

        for change in ('venue-bundle', 'device-map'):
            with self.subTest(change=change):
                if change == 'venue-bundle':
                    admission = self.admissions[7]
                    self.admissions[7] = uuid.uuid4()
                    revised, _ = self.mixed_bundle()
                    replacement = self.write_bundle(revised, 'reissued-venue.zip')
                    self.mock_capture_devices(document['seats'], 'Independent')
                    self.admissions[7] = admission
                else:
                    rows = [{**row, 'serial': 'replacement-headset'} if (row['roomId'], row['seat']) == (2, 3)
                            else row for row in document['seats']]
                    replacement = self.root / 'reassigned-device-map.json'
                    replacement.write_text(json.dumps({**document, 'seats': rows}), encoding='utf-8')
                    self.mock_capture_devices(rows, 'Independent')
                retry_output = self.root / f'retry changed {change}'
                retry = [*command, '--retry-incomplete', str(report_path)]
                retry[retry.index(f'--{change}') + 1] = str(replacement)
                retry[retry.index('--output-directory') + 1] = str(retry_output)
                result = subprocess.run(retry, cwd=self.root, capture_output=True, encoding='utf-8', timeout=20)
                self.assertEqual(1, result.returncode, result.stderr)
                self.assertIn('original venue ZIP and Quest device map', result.stderr)
                self.assertFalse(retry_output.exists())

        legacy_path = self.root / 'legacy-capture.json'
        del report['captureBinding']
        legacy_path.write_text(json.dumps(report), encoding='utf-8')
        retry_output = self.root / 'unbound legacy retry'
        retry = [*command, '--retry-incomplete', str(legacy_path)]
        retry[retry.index('--output-directory') + 1] = str(retry_output)
        result = subprocess.run(retry, cwd=self.root, capture_output=True, encoding='utf-8', timeout=20)
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertIn('prior Quest capture lacks an original ZIP and device map binding', result.stderr)
        self.assertFalse(retry_output.exists())
        self.assertEqual(originals, {path.name: path.read_bytes() for path in output.iterdir()})

    def run_fleet(self, files, mapping, *flags, faults=None, environment=None, fleet_root=None, release=None):
        env = {**os.environ, **(environment or {}), 'VR_QUEST_FLEET_FIXTURE': str(fleet_root or self.root),
               'VR_QUEST_FLEET_FAULTS': json.dumps(faults or {})}
        version = ('-ExpectedVersionCode', '61') if release is None else ('-ReleaseReport', str(release))
        return self.run_bundle(files, '-DeviceMap', str(mapping), *version, '-AdbPath',
                               str(ROOT / 'tests/fixtures/mock-quest-fleet.ps1'), *flags, environment=env)

    def release_report(self, version_code=64):
        apk = self.root / 'original-development.apk'
        apk.write_bytes(b'installed APK byte fixture')
        document = {'verified': True, 'scope': 'offline-package-consistency',
                    'quest': {'applicationId': 'com.vrcommand.quest', 'architecture': 'arm64-v8a', 'signatureV2': True,
                              'versionCode': version_code, 'sha256': hashlib.sha256(apk.read_bytes()).hexdigest()}}
        report = self.root / 'release.json'
        report.write_text(json.dumps(document), encoding='utf-8')
        return report, document, {'VR_QUEST_FLEET_APK': str(apk), 'VR_QUEST_FLEET_VERSION_CODE': str(version_code)}

    def assert_rejected(self, result, message):
        self.assertNotEqual(0, result.returncode)
        self.assertIn(message, result.stderr)
        self.assertEqual('', result.stdout)
        self.assertNotIn('v2.', result.stderr)

    def test_tracked_readback_uses_original_admissions_and_one_venue_sample(self):
        snapshots, seats, calls, requests = {}, [], [], []
        topology = 'Independent'
        fixture_key = 'private-readiness-fixture-key'
        sampled = '2026-11-10T00:00:00Z'
        delay, status_code = 0, 200

        class Handler(BaseHTTPRequestHandler):
            def reply(self, payload, status=200):
                calls.append((self.command, self.path, self.headers.get('Authorization')))
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path == '/api/venue/tracked-readiness':
                    requests.append(body)
                    time.sleep(delay)
                    self.reply({'version': 1, 'topology': topology, 'sampledAtUtc': sampled, 'maxSourceAgeMilliseconds': 1500,
                                'sessions': list(snapshots.values())}, status_code)
                    return
                self.reply({'topology': topology, 'allMatched': True, 'seats': seats})

            def log_message(self, *args):
                pass

        with quest_management_server(Handler) as server:
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
                                'sessionSequence': 12, 'observedSequence': 12, 'players': [],
                                'sampledAtUtc': sampled, 'sourceAgeMilliseconds': 50})
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
                        self.assertEqual([('POST', route, 'Bearer ' + fixture_key) for route in (
                            '/api/vr-deployment/venue-check', '/api/venue/tracked-readiness')], calls)
                        self.assertEqual({'topology': topology, 'rooms': [
                            {'roomId': room, 'sessionId': str(self.session_ids[0 if topology == 'Linked' else room - 1])}
                            for room in range(1, 6)]}, requests[-1])
                        expected_calls = calls.copy()
                        calls.clear()
                        combined = self.run_bundle(files, *args, '-AllHeadsets', environment=env)
                        self.assertEqual(0, combined.returncode, combined.stderr)
                        report = json.loads(combined.stdout)
                        self.assertEqual(('venue', True, True), (report['scope'], report['complete'], report['managementVerified']))
                        self.assertEqual([(seat['roomId'], seat['seat'] + 1, seat['headset'], 'tracked-ready') for seat in seats],
                            [(row['roomId'], row['seat'], row['registeredHeadset'], row['status']) for row in report['seats']])
                        self.assertEqual(expected_calls, calls)

                        if topology == 'Independent':
                            first = snapshots[str(self.session_ids[0])]
                            first['sourceAgeMilliseconds'] = 1490
                            delay = .15
                            expired = self.run_bundle(files, *args, '-AllHeadsets', environment=env)
                            self.assertEqual(1, expired.returncode, expired.stderr)
                            self.assertEqual(['source-expired-in-transit'] * 5 + ['tracked-ready'] * 20,
                                             [row['status'] for row in json.loads(expired.stdout)['seats']])
                            delay = 0
                            first['sourceAgeMilliseconds'] = 50
                            first['sampledAtUtc'] = '2026-11-10T00:00:01Z'
                            mixed_sample = self.run_bundle(files, *args, '-AllHeadsets', environment=env)
                            self.assertEqual(1, mixed_sample.returncode, mixed_sample.stderr)
                            self.assertEqual({'readiness-invalid'}, {row['status'] for row in json.loads(mixed_sample.stdout)['seats']})
                            first['sampledAtUtc'] = sampled

                        snapshots[str(self.session_ids[0])]['players'][1]['rigKind'] = 'Simulated'
                        calls.clear()
                        incomplete = self.run_bundle(files, *args, '-AllHeadsets', environment=env)
                        self.assertEqual(1, incomplete.returncode, incomplete.stderr)
                        report = json.loads(incomplete.stdout)
                        self.assertFalse(report['complete'])
                        self.assertEqual([(1, 2, 'ViveXr', 'not-tracked')],
                            [(row['roomId'], row['seat'], row['registeredHeadset'], row['status'])
                             for row in report['seats'] if row['status'] != 'tracked-ready'])
                        self.assertEqual(expected_calls, calls)
                        for value in (fixture_key, str(self.players[1]), str(self.admissions[1]), 'v2.'):
                            self.assertNotIn(value, combined.stdout + combined.stderr)

                sample = snapshots[str(self.session_ids[0])]
                sample['players'][0]['rigKind'] = 'Simulated'
                sample['players'][2]['admissionId'] = str(uuid.uuid4())
                sample['players'][3].update(state='PoseUnavailable', canParticipate=False)
                sample['players'][-1] = sample['players'][4]
                calls.clear()
                mapping, document = self.device_map()
                document['seats'] = [row for row in document['seats'] if row['roomId'] == 1]
                mapping.write_text(json.dumps(document), encoding='utf-8')
                self.assert_rejected(self.run_bundle(files, *args, '-AllHeadsets', '-DeviceMap', str(mapping),
                    '-AllowPartialMap', environment=env), 'without a device map or partial selection')
                self.assert_rejected(self.run_bundle(files, '-AllHeadsets', '-CheckOnly', environment=env),
                    'only with -VerifyTrackedSeats')
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
                                        ({'sourceAgeMilliseconds': True}, 'readiness-invalid'),
                                        (409, 'venue-changed'),
                                        (None, 'readiness-unavailable')):
                    with self.subTest(status=status):
                        status_code = changes if isinstance(changes, int) else 503 if changes is None else 200
                        snapshots[str(self.session_ids[0])] = {**sample, **changes} if isinstance(changes, dict) else sample
                        result = self.run_bundle(files, *args, '-DeviceMap', str(mapping), '-AllowPartialMap', environment=env)
                        self.assertEqual(1, result.returncode, result.stderr)
                        self.assertEqual(status, json.loads(result.stdout)['seats'][0]['status'])
                self.assert_rejected(self.run_bundle(files, *args, '-DeployMappedSeats', environment=env),
                                     'omit deployment and device-check')
            finally:
                server.shutdown()
                thread.join(timeout=5)

    def test_tracked_wait_requires_one_complete_sample_and_stops_at_original_venue_boundaries(self):
        topology = 'Independent'
        key = 'private-tracked-wait-fixture'
        calls, samples = [], []
        mode = 'recover'
        delayed = Event()

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                calls.append((self.path, self.headers.get('Authorization'), body))
                if self.path == '/api/vr-deployment/venue-check':
                    self.reply(200, {'topology': topology, 'allMatched': True, 'seats': [
                        {'roomId': room, 'seat': seat, 'status': 'matched', 'headset': 'ViveXr' if seat == 4 else 'Quest3'}
                        for room in range(1, 6) for seat in range(5)]})
                    return
                if self.path != '/api/venue/tracked-readiness':
                    self.reply(404, {})
                    return
                sample = len(samples) + 1
                samples.append(body)
                if mode in ('changed-venue', 'access-denied') and sample == 2:
                    self.reply(409 if mode == 'changed-venue' else 403, {})
                    return
                when = f'2026-11-11T00:00:{sample:02}Z'
                expected = (1, 0) if sample % 2 else (5, 4)
                reports = {}
                for room in range(1, 6):
                    session = str(self.suite.session_ids[0 if topology == 'Linked' else room - 1])
                    report = reports.setdefault(session, dict(version=1, sessionId=session, sourceState='Fresh', origin='Simulation',
                        worldSequence=100+sample, sessionSequence=12, observedSequence=12, sampledAtUtc=when,
                        sourceAgeMilliseconds=25, players=[]))
                    for seat in range(5):
                        index = (room-1)*5+seat
                        pending = (room, seat) == expected and (mode in ('alternating', 'ticket-expiry') or (mode == 'recover' and sample < 3)
                            or mode in ('changed-venue', 'changed-admission', 'access-denied'))
                        admission = uuid.uuid4() if mode == 'changed-admission' and sample == 2 and (room,seat)==(5,4) else self.suite.admissions[index]
                        report['players'].append(dict(roomId=room, seat=seat, playerId=str(self.suite.players[index]),
                            admissionId=str(admission), state='Participating', canParticipate=True, rigKind='Simulated' if pending else 'Tracked'))
                if mode == 'slow':
                    delayed.set()
                    time.sleep(1.8)
                self.reply(200, dict(version=1, topology=topology, sampledAtUtc=when, maxSourceAgeMilliseconds=1500,
                    sessions=list(reports.values())))

            def reply(self, code, value):
                data = json.dumps(value).encode()
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

            def log_message(self, *args):
                pass

        Handler.suite = self
        with quest_management_server(Handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            env = {**os.environ, 'VR_COMMAND_MASTER_KEY': key}
            args = ('-VerifyTrackedSeats', '-AllHeadsets', '-ManagementApi', f'http://127.0.0.1:{server.server_port}',
                    '-AdbPath', str(self.root/'absent-adb.exe'))

            def wait(files, seconds, success=False):
                calls.clear()
                samples.clear()
                result = self.run_bundle(files, *args, '-WaitForTrackedSeconds', str(seconds), environment=env)
                self.assertEqual(0 if success else 1, result.returncode, result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(success, report['complete'])
                self.assertEqual(len(samples), report['wait']['samples'])
                self.assertEqual([('/api/vr-deployment/venue-check', 'Bearer '+key)] + [('/api/venue/tracked-readiness', 'Bearer '+key)]*len(samples),
                                 [(route, auth) for route, auth, _ in calls])
                self.assertTrue(all(sample == samples[0] for sample in samples))
                self.assertFalse((self.root/'adb.log').exists())
                self.assertNotIn(key, result.stdout+result.stderr)
                return report

            try:
                for topology in ('Independent', 'Linked'):
                    with self.subTest(topology=topology):
                        files, _ = self.vr_bundle(topology)
                        ready = wait(files, 5, success=True)
                        self.assertEqual(dict(maximumSeconds=5, samples=3, outcome='ready'), ready['wait'])
                        self.assertEqual({103}, {seat['worldSequence'] for seat in ready['seats']})
                        self.assertEqual(25, sum(seat['status']=='tracked-ready' for seat in ready['seats']))

                mode = 'alternating'
                partial = wait(files, 3)
                self.assertEqual('timed-out', partial['wait']['outcome'])
                self.assertGreaterEqual(partial['wait']['samples'], 2)
                self.assertEqual(24, sum(row['status']=='tracked-ready' for row in partial['seats']))
                self.assertEqual(1, len({row['worldSequence'] for row in partial['seats']}))
                for mode, status in (('changed-venue','venue-changed'), ('changed-admission','admission-changed'),
                                     ('access-denied','readiness-access-denied')):
                    report = wait(files, 8)
                    self.assertEqual((2, status), (report['wait']['samples'], report['wait']['outcome']))
                    self.assertIn(status, {seat['status'] for seat in report['seats']})
                mode = 'slow'
                slow = wait(files, 1)
                self.assertTrue(delayed.is_set())
                self.assertEqual((1, 'timed-out'), (slow['wait']['samples'], slow['wait']['outcome']))
                self.assertTrue(all(seat['status']=='readiness-unavailable' for seat in slow['seats']))
                mode = 'ticket-expiry'
                self.expiry = int(time.time()) + 5
                expired_files, _ = self.vr_bundle(topology)
                expired = wait(expired_files, 10)
                self.assertEqual('ticket-expired', expired['wait']['outcome'])
                self.assertEqual({'ticket-expired'}, {seat['status'] for seat in expired['seats']})
                self.assert_rejected(self.run_bundle(files, '-WaitForTrackedSeconds', '3', '-CheckOnly'), 'only with -VerifyTrackedSeats')
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

    def test_single_bundle_seat_checks_local_release_without_adb(self):
        files, _ = self.vr_bundle('Linked')
        apk = self.root / 'game.apk'
        apk.write_bytes(b'mock release')
        release, report, _ = self.release_report()
        report['quest']['sha256'] = hashlib.sha256(apk.read_bytes()).hexdigest()
        release.write_text(json.dumps(report), encoding='utf-8')
        flags = ('-ReleaseReport', str(release), '-ApkPath', str(apk), '-AdbPath', str(self.root/'absent-adb.exe'), '-CheckOnly')
        result = self.run_bundle(files, '-RoomId', '5', '-Seat', '2', *flags)
        self.assertEqual(0, result.returncode, result.stderr)
        info = json.loads(result.stdout)
        self.assertEqual((5, 2, 'VR', True), (info['roomId'], info['seat'], info['mode'], info['localApkVerified']))
        self.assertNotIn('v2.', result.stdout)
        self.assert_rejected(self.run_bundle(files, *flags), 'check an APK for a single bundle seat')
        mapping, _ = self.device_map()
        self.assert_rejected(self.run_bundle(files, '-DeviceMap', str(mapping), *flags), 'Use -ApkPath only for a single-seat install')

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

    def test_vr_bundle_pilot_seats_preserve_original_capture_assignments(self):
        for topology in ('Independent', 'Linked'):
            for count in (1, 2):
                with self.subTest(topology=topology, count=count):
                    files, _ = self.vr_bundle(topology, count)
                    inspected = self.run_bundle(files)
                    self.assertEqual(0, inspected.returncode, inspected.stderr)
                    report = json.loads(inspected.stdout)
                    self.assertEqual((topology, count, 5 * count), (report['topology'], report['playersPerRoom'], report['seats']))
                    mapping, document = self.device_map()
                    document['seats'] = [row for row in document['seats'] if row['seat'] <= count]
                    mapping.write_text(json.dumps(document), encoding='utf-8')
                    capture = self.run_bundle(files, '-DeviceMap', str(mapping), '-ReadCapturePlan')
                    self.assertEqual(0, capture.returncode, capture.stderr)
                    seats = json.loads(capture.stdout)['seats']
                    self.assertEqual([(room, seat) for room in range(1, 6) for seat in range(1, count + 1)],
                                     [(row['roomId'], row['seat']) for row in seats])
                    self.assert_rejected(self.run_bundle(files, '-RoomId', '5', '-Seat', str(count + 1), '-CheckOnly'),
                                         'outside the original venue bundle')
                    document['seats'][-1]['seat'] = count + 1
                    mapping.write_text(json.dumps(document), encoding='utf-8')
                    self.assert_rejected(self.run_bundle(files, '-DeviceMap', str(mapping), '-ReadCapturePlan'),
                                         'outside the original venue bundle')
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
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                calls.append((self.path, self.headers['Authorization'], body))
                payload = {'topology': 'Linked', 'allMatched': not stale[0], 'seats': [
                    {'roomId': room, 'seat': seat, 'status': 'admission-changed' if stale[0] and (room, seat) == (2, 1) else 'matched',
                     'headset': headset[0] if (room, seat) == (2, 1) else 'Quest3'}
                    for room in range(1, 6) for seat in range(5)]}
                if body.get('requireLiveSource') is True:
                    payload['liveSourceVerified'] = payload['allMatched']
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())

            def log_message(self, *args):
                pass

        with quest_management_server(Handler) as server:
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
                self.assertEqual(3, sum(' shell am start ' in line for line in commands))
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
        self.assertEqual(4, sum('requireLiveSource' not in proof for _, _, proof in calls))
        self.assertEqual(56, sum(proof.get('requireLiveSource') is True for _, _, proof in calls))
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

    def test_combined_quest_tracking_binds_recovered_deployments_to_one_sample(self):
        calls = []
        sample_time = '2026-11-10T00:00:00Z'
        capture_time = '2026-11-09T23:59:59.950Z'
        topology = 'Independent'
        snapshots = {}
        running_frame = None
        simulated_body = None

        class Handler(BaseHTTPRequestHandler):
            def reply(self, body):
                calls.append((self.command, self.path))
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(body).encode())

            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                if self.path == '/api/venue/tracked-readiness':
                    self.reply({'version': 1, 'topology': topology, 'sampledAtUtc': sample_time,
                                'maxSourceAgeMilliseconds': 1500, 'sessions': list(snapshots.values())})
                else:
                    self.reply({'topology': topology, 'allMatched': True, 'seats': [
                        {'roomId': room, 'seat': seat, 'status': 'matched', 'headset': 'Quest3'}
                        for room in range(1, 6) for seat in range(5)]})

            def do_GET(self):
                session = self.path.split('/')[3]
                snapshot = snapshots[session]
                players = [tracked_world_player(row) for row in snapshot['players']]
                for player in players:
                    if player['id'] == simulated_body:
                        player['rig']['kind'] = 'Simulated'
                frame = {'phase': 'Running', 'tick': 1} if session == running_frame else {
                    'phase': 'Preparing', 'tick': 0, 'players': players}
                self.reply({'packet': {'sequence': snapshot['worldSequence'], 'observedSequence': snapshot['observedSequence'],
                                       'suspended': False, 'frame': frame}})

            def log_message(self, *args):
                pass

        mapping, document = self.device_map()
        mapped = sorted(document['seats'], key=lambda row: (row['roomId'], row['seat']))
        report_list = self.root / 'deployment reports.json'
        early_path = self.root / 'early deployment.json'
        later_path = self.root / 'later deployment.json'
        first_names = [early_path.name, later_path.name]

        with quest_management_server(Handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for topology in ('Independent', 'Linked'):
                    with self.subTest(topology=topology):
                        files, _ = self.vr_bundle(topology)
                        bundle = self.write_bundle(files)
                        venue_digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
                        snapshots.clear()
                        devices = []
                        for index, row in enumerate(mapped):
                            room, seat = row['roomId'], row['seat']
                            session = str(self.session_ids[room-1 if topology == 'Independent' else 0])
                            port = 7776 + room if topology == 'Independent' else 7777
                            owner = {'roomId': room, 'seat': seat, 'sessionId': session,
                                     'playerId': str(self.players[index]), 'admissionId': str(self.admissions[index])}
                            snapshot = snapshots.setdefault(session, {'version': 1, 'sessionId': session, 'worldSequence': 20 + room,
                                'sessionSequence': 12, 'observedSequence': 12, 'sourceState': 'Fresh', 'origin': 'GameServer',
                                'sampledAtUtc': sample_time, 'capturedAtUtc': capture_time, 'sourceAgeMilliseconds': 50, 'players': []})
                            snapshot['players'].append(dict(owner, seat=seat-1, canParticipate=True, state='Participating', rigKind='Tracked'))
                            devices.append(dict(owner, status='launch-requested', versionCode=76, port=port,
                                                filesVerified=True, apkVerified=True))

                        def deployment(seats, rows, number, complete):
                            salt = f'{number:032x}'
                            assignments = '\n'.join(f"{row['roomId']}/{row['seat']}={row['serial']}" for row in seats)
                            def fingerprint(value):
                                return hashlib.sha256(f'{salt}\n{value}'.encode()).hexdigest()
                            return {'phase': 'deployment', 'topology': topology, 'managementVerified': True,
                                    'expectedVersionCode': 76, 'expectedApkSha256': 'a' * 64, 'apkVerificationVersion': 1,
                                    'complete': complete, 'devices': rows, 'retry': {'version': 1, 'salt': salt,
                                    'venueSha256': venue_digest, 'mapSha256': fingerprint(assignments),
                                    'devices': [fingerprint(row['serial'].upper()) for row in seats]}}

                        pending = [dict(roomId=row['roomId'], seat=row['seat'], status='not-attempted', versionCode=76)
                                   for row in devices[12:]]
                        early = deployment(mapped, devices[:12] + pending, 1, False)
                        later = deployment(mapped[12:], devices[12:], 2, True)
                        early['venueReleaseReportSha256'] = later['venueReleaseReportSha256'] = 'c' * 64
                        early_path.write_text(json.dumps(early), encoding='utf-8')
                        later_path.write_text(json.dumps(later), encoding='utf-8')
                        report_list.write_text(json.dumps({'version': 1, 'reports': first_names}), encoding='utf-8')
                        command = ['pwsh', '-NoProfile', '-NonInteractive', '-File', str(ROOT/'scripts/deploy-quest.ps1'),
                                   '-VenueBundle', str(bundle), '-DeviceMap', str(mapping), '-VerifyTrackedSeats',
                                   '-DeploymentReportsFile', str(report_list), '-ManagementApi', f'http://127.0.0.1:{server.server_port}',
                                   '-AdbPath', str(self.root/'absent-adb.exe')]

                        def sample():
                            calls.clear()
                            return subprocess.run(command, capture_output=True, encoding='utf-8', timeout=20,
                                                  env={**os.environ, 'VR_COMMAND_MASTER_KEY': 'mock-combined-tracking-key'})

                        observed = sample()
                        self.assertEqual(0, observed.returncode, observed.stderr)
                        report = json.loads(observed.stdout)
                        self.assertEqual((2, True, 25, venue_digest), (report['evidenceVersion'], report['complete'],
                                         len(report['seats']), report['venueSha256']))
                        self.assertNotIn('deploymentSha256', report)
                        expected = [hashlib.sha256(path.read_bytes()).hexdigest() for path in (early_path, later_path)]
                        self.assertEqual([expected[0]]*12 + [expected[1]]*13, [row['deploymentSha256'] for row in report['seats']])
                        self.assertEqual(['tracked-ready']*25, [row['status'] for row in report['seats']])
                        self.assertEqual([('POST','/api/vr-deployment/venue-check'), ('POST','/api/venue/tracked-readiness')], calls[:2])
                        self.assertCountEqual([('GET', f"/api/sessions/{session}/world/frames/{snapshot['worldSequence']}")
                                               for session, snapshot in snapshots.items()], calls[2:])
                        self.assertEqual(datetime.fromisoformat(sample_time), datetime.fromisoformat(report['sampledAtUtc']))

                        ids = '\n'.join(sorted(snapshots))
                        scope = hashlib.sha256(f'vrcommand-quest-venue-devices-v1\n{topology}\n{ids}'.encode()).hexdigest()
                        fingerprints = [hashlib.sha256(f'{scope}\nHEADSET-{index}'.encode()).hexdigest() for index in range(25)]
                        early['retry']['venueDevices'] = {'scopeSha256': scope, 'devices': fingerprints}
                        later['retry']['venueDevices'] = {'scopeSha256': scope, 'devices': fingerprints[12:]}
                        early_path.write_text(json.dumps(early), encoding='utf-8')
                        later_path.write_text(json.dumps(later), encoding='utf-8')
                        self.assertEqual(0, sample().returncode)
                        later['retry']['venueDevices']['devices'][0] = fingerprints[0]
                        later_path.write_text(json.dumps(later), encoding='utf-8')
                        self.assert_rejected(sample(), 'same device for room/seat 1/1 and 3/3')
                        self.assertEqual([], calls)
                        later['retry']['venueDevices']['devices'][0] = fingerprints[12]
                        later_path.write_text(json.dumps(later), encoding='utf-8')

                        if topology == 'Independent':
                            running_frame = devices[12]['sessionId']
                            late = sample()
                            self.assertEqual(1, late.returncode, late.stderr)
                            self.assertEqual(['tracked-ready']*10 + ['source-outside-preparing']*5 + ['tracked-ready']*10,
                                             [row['status'] for row in json.loads(late.stdout)['seats']])
                            self.assertEqual(7, len(calls))
                            running_frame = None

                        simulated_body = devices[12]['playerId']
                        conflicting_frame = sample()
                        self.assertEqual(1, conflicting_frame.returncode, conflicting_frame.stderr)
                        rejected = json.loads(conflicting_frame.stdout)
                        self.assertFalse(rejected['complete'])
                        self.assertEqual(['tracked-ready']*12 + ['source-seat-unverified'] + ['tracked-ready']*12,
                                         [row['status'] for row in rejected['seats']])
                        self.assertEqual(2 + len(snapshots), len(calls))
                        self.assertNotIn(simulated_body, conflicting_frame.stdout)
                        simulated_body = None

                        broken = snapshots[devices[12]['sessionId']]
                        player = next(row for row in broken['players'] if row['playerId'] == devices[12]['playerId'])
                        player['rigKind'] = 'Simulated'
                        waiting = sample()
                        self.assertEqual(1, waiting.returncode, waiting.stderr)
                        self.assertEqual('not-tracked', json.loads(waiting.stdout)['seats'][12]['status'])
                        self.assertEqual(2, len(calls))
                        player['rigKind'] = 'Tracked'

                        for changed, expected_error in (
                            (deployment(mapped[13:], devices[13:], 2, True), 'cover every selected seat'),
                            (deployment(mapped[11:], devices[11:], 2, True), 'repeat a successfully launched seat'),
                            (dict(later, expectedApkSha256='b'*64), 'same verified APK'),
                            (dict(later, venueReleaseReportSha256='d'*64), 'same original venue release report'),
                        ):
                            later_path.write_text(json.dumps(changed), encoding='utf-8')
                            self.assert_rejected(sample(), expected_error)
                            self.assertFalse(calls)
            finally:
                server.shutdown()
                thread.join(timeout=5)

    def test_partial_mr_deployment_preserves_original_pins_on_selected_devices(self):
        files, configs = self.bundle('Linked')
        mapping, document = self.device_map()
        selected = [row for row in document['seats'] if row['serial'] in {'fixture-03','fixture-22'}]
        mapping.write_text(json.dumps({'version': 1, 'seats': selected}), encoding='utf-8')
        session = str(self.session_ids[0])
        calls = []
        frame_route = f'/api/sessions/{session}/world/frames/14'
        original_frame = {'sequence': 14, 'observedSequence': 27, 'suspended': False,
                          'frame': {'phase': 'Preparing', 'tick': 0}}
        saved_frame = original_frame
        readiness = {'version': 1, 'sessionId': session, 'sessionSequence': 27, 'observedSequence': 27,
                     'worldSequence': 14, 'sourceState': 'Fresh', 'origin': 'GameServer', 'mrStartState': 'WaitingPlayers',
                     'sampledAtUtc': '2026-11-10T00:00:00Z', 'capturedAtUtc': '2026-11-09T23:59:59.950Z', 'sourceAgeMilliseconds': 50,
                     'players': [{'roomId': row['roomId'], 'seat': row['seat'] - 1, 'state': 'Participating',
                                  'rigKind': 'Tracked', 'canParticipate': True,
                                  'playerId': str(self.players[(row['roomId'] - 1) * 5 + row['seat'] - 1]),
                                  'admissionId': str(self.admissions[(row['roomId'] - 1) * 5 + row['seat'] - 1])}
                                 for row in selected]}
        original_frame['frame']['players'] = [tracked_world_player(row) for row in readiness['players']]

        class Handler(BaseHTTPRequestHandler):
            def respond(self, payload):
                calls.append(self.path)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path == '/api/venue/tracked-readiness':
                    self.respond({'version': 1, 'topology': 'Linked', 'sampledAtUtc': readiness['sampledAtUtc'],
                                  'maxSourceAgeMilliseconds': 1500, 'sessions': [readiness]})
                    return
                receipt = {'topology': 'Linked', 'allMatched': True, 'seats': [
                    {'roomId': room, 'seat': seat, 'status': 'matched'} for room in range(1, 6) for seat in range(5)]}
                if body.get('requireLiveSource') is True:
                    receipt['liveSourceVerified'] = True
                self.respond(receipt)

            def do_GET(self):
                if self.path == frame_route:
                    if self.headers.get('Authorization') != 'Bearer private-fixture-master':
                        self.send_error(401)
                        return
                    if saved_frame is None:
                        calls.append(self.path)
                        self.send_error(404)
                        return
                    self.respond({'packet': saved_frame})
                    return
                self.respond({'version': 1, 'sessionId': session, 'sessionEnded': False, 'address': '192.168.1.10', 'port': 7777})

            def log_message(self, *args):
                pass

        with quest_management_server(Handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                release, _, release_env = self.release_report()
                api = f'http://127.0.0.1:{server.server_port}'
                auth = {'VR_COMMAND_MASTER_KEY': 'private-fixture-master'}
                result = self.run_fleet(files, mapping, '-AllowPartialMap', '-DeployMappedSeats',
                    '-ManagementApi', api, release=release, environment={**release_env, **auth})
                self.assertEqual(0, result.returncode, result.stderr)
                deploy_calls = calls.copy()
                before = (self.root / 'adb.log').read_bytes()
                bundle = self.root / 'quest-mr-venue.zip'
                original_bundle = bundle.read_bytes()
                original_map = mapping.read_bytes()
                deployment = self.root / 'deployment.json'
                deployment.write_bytes(result.stdout.encode('utf-8'))
                deployment_hash = hashlib.sha256(deployment.read_bytes()).hexdigest()
                bound = ('-DeploymentReport', str(deployment))
                flags = ('-VerifyTrackedSeats', '-DeviceMap', str(mapping), '-AllowPartialMap',
                         '-ManagementApi', api)

                def readback(*options):
                    return subprocess.run(['pwsh', '-NoProfile', '-NonInteractive', '-File',
                                           str(ROOT / 'scripts/deploy-quest.ps1'), '-VenueBundle', str(bundle),
                                           '-AdbPath', str(ROOT / 'tests/fixtures/mock-quest-fleet.ps1'), *options],
                                          capture_output=True, encoding='utf-8', timeout=20,
                                          env={**os.environ, **release_env, **auth, 'VR_QUEST_FLEET_FIXTURE': str(self.root)})

                legacy = readback(*flags)
                self.assertEqual(0, legacy.returncode, legacy.stderr)
                self.assertNotIn('deploymentSha256', json.loads(legacy.stdout))
                ready = readback(*flags, *bound, '-WaitForTrackedSeconds', '5')
                self.assertEqual(0, ready.returncode, ready.stderr)
                ready_report = json.loads(ready.stdout)
                probe_calls = deploy_calls[:2] + ['/api/venue/tracked-readiness']
                self.assertEqual(deploy_calls + probe_calls * 2 + [frame_route], calls)
                self.assertEqual(['tracked-ready'] * 2, [row['status'] for row in ready_report['seats']])
                self.assertEqual(deployment_hash, ready_report['deploymentSha256'])
                self.assertEqual((1, hashlib.sha256(original_bundle).hexdigest()),
                                 (ready_report['evidenceVersion'], ready_report['venueSha256']))
                for row in ready_report['seats']:
                    self.assertEqual((session, 14, 27), (row['sessionId'], row['worldSequence'], row['observedSequence']))
                    self.assertEqual(datetime.fromisoformat(readiness['capturedAtUtc']), datetime.fromisoformat(row['capturedAtUtc']))
                self.assertEqual({'maximumSeconds': 5, 'samples': 1, 'outcome': 'ready'}, ready_report['wait'])
                for canary in ('fixture-03', 'HARDWARE-SERIAL-', 'v2.', 'private-fixture-master'):
                    self.assertNotIn(canary, ready.stdout + ready.stderr)
                for changes in ({'mrStartState': 'WaitingProfile'}, {'mrStartState': 'Ready', 'origin': 'Simulation'}):
                    readiness.update(changes)
                    pending = readback(*flags, *bound)
                    self.assertEqual(1, pending.returncode, pending.stderr)
                    pending_report = json.loads(pending.stdout)
                    self.assertEqual(deployment_hash, pending_report['deploymentSha256'])
                    self.assertEqual(['mr-profile-pending'] * 2, [row['status'] for row in pending_report['seats']])
                readiness.update(origin='GameServer', capturedAtUtc=None)
                missing_capture = readback(*flags, *bound, '-WaitForTrackedSeconds', '5')
                self.assertEqual(1, missing_capture.returncode, missing_capture.stderr)
                missing_report = json.loads(missing_capture.stdout)
                self.assertEqual({'maximumSeconds': 5, 'samples': 1, 'outcome': 'source-capture-unverified'}, missing_report['wait'])

                readiness.update(capturedAtUtc='2026-11-09T23:59:59.950Z', mrStartState=None, mrTrackingState='Ready')
                saved_frame = dict(original_frame, frame={'phase': 'Running', 'tick': 23})
                late = readback(*flags, *bound, '-WaitForTrackedSeconds', '5')
                self.assertEqual(1, late.returncode, late.stderr)
                late_report = json.loads(late.stdout)
                self.assertFalse(late_report['complete'])
                self.assertEqual(['source-outside-preparing'] * 2, [row['status'] for row in late_report['seats']])
                self.assertEqual({'maximumSeconds': 5, 'samples': 1, 'outcome': 'source-outside-preparing'}, late_report['wait'])
                live = readback(*flags)
                self.assertEqual(0, live.returncode, live.stderr)
                self.assertNotIn('deploymentSha256', json.loads(live.stdout))
                invalid_frames = (
                    None,
                    dict(original_frame, observedSequence=26),
                    dict(original_frame, sequence=15),
                    dict(original_frame, frame={'phase': ['Preparing'], 'tick': 0}),
                    dict(original_frame, frame={'phase': 'Preparing', 'tick': 1}),
                )
                for saved_frame in invalid_frames:
                    incomplete = readback(*flags, *bound)
                    self.assertEqual(1, incomplete.returncode, incomplete.stderr)
                    invalid_report = json.loads(incomplete.stdout)
                    self.assertFalse(invalid_report['complete'])
                    self.assertEqual(['source-frame-unverified'] * 2, [row['status'] for row in invalid_report['seats']])

                header_error = 'complete release-verified deployment report for this original ZIP and device map'
                seat_error = 'does not match the original completed seat admissions'
                modified = self.root / 'modified-deployment.json'
                for changes, seat, error in (
                    ({'complete': False}, False, header_error),
                    ({'expectedApkSha256': None}, False, header_error),
                    ({'admissionId': str(self.admissions[0])}, True, seat_error),
                    ({'port': '7777'}, True, seat_error),
                    ({'apkVerified': False}, True, seat_error),
                    ({'filesVerified': False}, True, seat_error),
                ):
                    with self.subTest(changes=changes):
                        changed = json.loads(deployment.read_bytes())
                        (changed['devices'][0] if seat else changed).update(changes)
                        modified.write_text(json.dumps(changed), encoding='utf-8')
                        self.assert_rejected(readback(*flags, '-DeploymentReport', str(modified)), error)
                changed_map = json.loads(original_map)
                changed_map['seats'][0]['serial'] = 'fixture-04'
                mapping.write_text(json.dumps(changed_map), encoding='utf-8')
                self.assert_rejected(readback(*flags, *bound), header_error)
                mapping.write_bytes(original_map)
                bundle.write_bytes(original_bundle + b'ignored ZIP suffix')
                self.assert_rejected(readback(*flags, *bound), header_error)
                bundle.write_bytes(original_bundle)
                self.assert_rejected(readback('-VerifyTrackedSeats', '-ManagementApi', api, *bound), 'original -DeviceMap')
                self.assert_rejected(readback('-DeviceMap', str(mapping), *bound), 'only with -VerifyTrackedSeats')
                self.assertEqual(deployment_hash, hashlib.sha256(deployment.read_bytes()).hexdigest())
                self.assertEqual(before, (self.root / 'adb.log').read_bytes())
                self.assertEqual(deploy_calls + probe_calls * 2 + [frame_route] + probe_calls * 3
                                 + probe_calls + [frame_route] + probe_calls
                                 + (probe_calls + [frame_route]) * len(invalid_frames), calls)
            finally:
                server.shutdown()
                thread.join(timeout=5)
        report = json.loads(result.stdout)
        self.assertEqual((True, True, True, 2, 23), (report['complete'], report['managementVerified'],
                         report['alignmentPinsVerified'], report['mappedSeats'], report['unmappedSeats']))
        self.assertEqual(['/api/mr-deployment/venue-check', f'/api/sessions/{session}/connection-endpoint']
                         + ['/api/mr-deployment/venue-check'] * 4, deploy_calls)
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

    def test_prepare_quest_apks_before_tickets_and_without_launching(self):
        mapping, assignments = self.device_map()
        release, document, release_env = self.release_report()
        apk = Path(release_env['VR_QUEST_FLEET_APK'])
        command = ['pwsh', '-NoProfile', '-NonInteractive', '-File', str(ROOT / 'scripts/deploy-quest.ps1'),
                   '-PrepareQuestApks', '-DeviceMap', str(mapping), '-ReleaseReport', str(release), '-ApkPath', str(apk),
                   '-AdbPath', str(ROOT / 'tests/fixtures/mock-quest-fleet.ps1')]
        fresh = ('fixture-01', 'fixture-11', 'fixture-25')

        def run(fleet, *options, faults=None):
            fleet.mkdir(exist_ok=True)
            return subprocess.run([*command, *options], capture_output=True, encoding='utf-8', timeout=35,
                env={**os.environ, **release_env, 'VR_COMMAND_MASTER_KEY': '', 'VR_QUEST_FLEET_FIXTURE': str(fleet),
                     'VR_QUEST_FLEET_FRESH': ','.join(fresh), 'VR_QUEST_FLEET_FAULTS': json.dumps(faults or {})})

        check = self.root / 'preview'
        original_apk = apk.read_bytes()
        apk.write_bytes(b'other APK')
        self.assert_rejected(run(check, '-CheckOnly'), 'APK SHA-256 differs')
        self.assertFalse((check / 'transport.log').exists())
        apk.write_bytes(original_apk)
        preview = run(check, '-CheckOnly')
        self.assertEqual(0, preview.returncode, preview.stderr)
        planned = json.loads(preview.stdout)
        self.assertEqual('apk-preflight', planned['phase'])
        self.assertTrue(planned['complete'])
        self.assertEqual(['install-required' if index in (0, 10, 24) else 'ready' for index in range(25)],
                         [row['status'] for row in planned['devices']])
        self.assertFalse(list(check.glob('fixture-*')))

        blocked = self.root / 'blocked'
        failed = run(blocked, faults={'fixture-02': 'identity-first-device', 'fixture-24': 'version-mismatch'})
        self.assertEqual(1, failed.returncode, failed.stderr)
        invalid = json.loads(failed.stdout)
        self.assertEqual('apk-preflight', invalid['phase'])
        self.assertEqual(['duplicate-device', 'duplicate-device'], [row['status'] for row in invalid['devices'][:2]])
        self.assertEqual('version-mismatch', invalid['devices'][23]['status'])
        self.assertFalse(list(blocked.glob('fixture-*')))

        changed = self.root / 'changed'
        swapped = run(changed, faults={'fixture-01': 'identity-changed'})
        self.assertEqual(1, swapped.returncode, swapped.stderr)
        self.assertEqual('device-identity-changed', json.loads(swapped.stdout)['devices'][0]['status'])
        self.assertFalse(list(changed.glob('fixture-*')))

        fleet = self.root / 'fleet'
        interrupted = run(fleet, faults={'fixture-11': 'install-failed'})
        self.assertEqual(1, interrupted.returncode, interrupted.stderr)
        partial = json.loads(interrupted.stdout)
        self.assertFalse(partial['complete'])
        self.assertTrue(partial['devices'][0]['installedApk'] and partial['devices'][0]['apkVerified'])
        self.assertEqual('install-apk', partial['devices'][10]['failedStep'])
        self.assertEqual('not-attempted', partial['devices'][24]['status'])
        first_apk = fleet / 'fixture-01' / 'installed.apk'
        self.assertEqual(original_apk, first_apk.read_bytes())
        log = fleet / 'adb.log'
        log.unlink()
        resumed = run(fleet)
        self.assertEqual(0, resumed.returncode, resumed.stderr)
        ready = json.loads(resumed.stdout)
        self.assertEqual(('apk-preparation', True), (ready['phase'], ready['complete']))
        self.assertEqual(document['quest']['sha256'], ready['expectedApkSha256'])
        self.assertEqual(hashlib.sha256(release.read_bytes()).hexdigest(), ready['venueReleaseReportSha256'])
        self.assertTrue(all(row['status'] == 'ready' and row['apkVerified'] for row in ready['devices']))
        self.assertEqual(['fixture-11', 'fixture-25'], [line.split()[1] for line in log.read_text().splitlines() if ' install ' in line])
        for serial in fresh:
            self.assertEqual(original_apk, (fleet / serial / 'installed.apk').read_bytes())
        for directory in (check, blocked, changed, fleet):
            calls = (directory / 'transport.log').read_text()
            self.assertNotIn(' push ', calls)
            self.assertNotIn(' shell am ', calls)
        self.assertNotRegex(resumed.stdout, 'fixture-\\d+|HARDWARE-SERIAL|joinTicket')

        assignments['seats'] = [row for row in assignments['seats'] if row['serial'] == 'fixture-25']
        mapping.write_text(json.dumps(assignments), encoding='utf-8')
        one_seat = run(fleet, '-CheckOnly')
        self.assertEqual(0, one_seat.returncode, one_seat.stderr)
        self.assertEqual([(5, 5)], [(row['roomId'], row['seat']) for row in json.loads(one_seat.stdout)['devices']])

    def test_install_missing_quest_apks_during_mapped_deployment_and_retry(self):
        files, configs = self.vr_bundle('Independent')
        bundle = self.write_bundle(files)
        mapping, document = self.device_map()
        release, _, release_env = self.release_report()
        apk = Path(release_env['VR_QUEST_FLEET_APK'])
        command = ['pwsh', '-NoProfile', '-NonInteractive', '-File', str(ROOT / 'tests/fixtures/mock-quest-management.ps1'),
                   str(ROOT / 'scripts/deploy-quest.ps1'), '-VenueBundle', str(bundle),
                   '-DeviceMap', str(mapping), '-ReleaseReport', str(release),
                   '-AdbPath', str(ROOT / 'tests/fixtures/mock-quest-fleet.ps1'),
                   '-DeployMappedSeats', '-ManagementApi', 'http://127.0.0.1:1']

        def invoke(fleet, *options, faults=None, stale=False, allow_install=True):
            fleet.mkdir(exist_ok=True)
            flags = ['-InstallMissing', '-ApkPath', str(apk)] if allow_install else []
            return subprocess.run([*command, *flags, *options], capture_output=True, encoding='utf-8', timeout=90,
                env={**os.environ, **release_env, 'VR_COMMAND_MASTER_KEY': 'fixture-master',
                     'VR_QUEST_FLEET_FIXTURE': str(fleet), 'VR_QUEST_FLEET_FRESH': 'fixture-01,fixture-11,fixture-25',
                     'VR_QUEST_FLEET_FAULTS': json.dumps(faults or {}), 'VR_QUEST_TEST_SOURCE_STALE': '1' if stale else ''})

        bad_local = self.root / 'bad-local'
        original_bytes = apk.read_bytes()
        apk.write_bytes(b'edited APK')
        self.assert_rejected(invoke(bad_local), 'APK SHA-256 differs')
        self.assertFalse((bad_local / 'transport.log').exists())
        apk.write_bytes(original_bytes)

        blocked = self.root / 'blocked'
        wrong_package = invoke(blocked, faults={'fixture-25': 'package-disabled'})
        self.assertEqual(1, wrong_package.returncode, wrong_package.stderr)
        report = json.loads(wrong_package.stdout)
        self.assertEqual('preflight', report['phase'])
        self.assertEqual('package-unavailable', report['devices'][-1]['status'])
        self.assertFalse(list(blocked.glob('fixture-*')))
        self.assertNotIn(' install ', (blocked / 'transport.log').read_text())

        for name, fault, stale, step in (
            ('bad-readback', {'fixture-01': 'installed-apk-mismatch'}, False, 'verify-installed-apk'),
            ('changed-source', {}, True, 'verify-live-venue-after-install'),
        ):
            with self.subTest(step=step):
                fleet = self.root / name
                result = invoke(fleet, faults=fault, stale=stale)
                self.assertEqual(1, result.returncode, result.stderr)
                row = json.loads(result.stdout)['devices'][0]
                self.assertEqual(step, row['failedStep'])
                self.assertTrue(row['installedApk'])
                commands = (fleet / 'adb.log').read_text()
                self.assertNotIn(' push ', commands)
                self.assertNotIn(' shell am ', commands)

        fleet = self.root / 'resume'
        first = invoke(fleet, faults={'fixture-11': 'install-failed'})
        self.assertEqual(1, first.returncode, first.stderr)
        before = json.loads(first.stdout)
        self.assertEqual(['launch-requested'] * 10 + ['deployment-failed'] + ['not-attempted'] * 14,
                         [row['status'] for row in before['devices']])
        self.assertEqual('install-apk', before['devices'][10]['failedStep'])
        prior = self.root / 'original-deployment.json'
        prior.write_bytes(first.stdout.encode())
        log_file = fleet / 'adb.log'
        original_log = log_file.read_text()
        self.assert_rejected(invoke(fleet, '-RetryIncomplete', str(prior), allow_install=False), 'original APK installation option')
        self.assertEqual(original_log, log_file.read_text())
        log_file.unlink()
        resumed = invoke(fleet, '-RetryIncomplete', str(prior))
        self.assertEqual(0, resumed.returncode, resumed.stderr)
        complete = json.loads(resumed.stdout)
        self.assertTrue(complete['complete'])
        self.assertEqual(before['devices'][:10], complete['devices'][:10])
        self.assertEqual(hashlib.sha256(prior.read_bytes()).hexdigest(), complete['previousDeploymentSha256'])
        self.assertEqual(['fixture-11', 'fixture-25'], [line.split()[1] for line in log_file.read_text().splitlines() if ' install ' in line])
        self.assertTrue(all(row['apkVerified'] and row['filesVerified'] and row['status'] == 'launch-requested' for row in complete['devices']))
        self.assertEqual(3, sum(row.get('installedApk', False) for row in complete['devices']))
        for row in document['seats']:
            room, seat = row['roomId'], row['seat']
            readback = json.loads((fleet / row['serial'] / 'vr-connection.json').read_bytes())
            self.assertEqual(configs[room][f'room-{room:02}-seat-{seat:02}.json'], readback)

    def test_retry_mapped_quest_deployment_after_original_tickets_expire(self):
        mapping, document = self.device_map()
        document['seats'] = [row for row in document['seats'] if row['serial'] in ('fixture-01', 'fixture-02', 'fixture-03')]
        mapping.write_text(json.dumps(document), encoding='utf-8')
        release, _, release_env = self.release_report()
        command = ['pwsh', '-NoProfile', '-NonInteractive', '-File', str(ROOT / 'tests/fixtures/mock-quest-management.ps1'),
                   str(ROOT / 'scripts/deploy-quest.ps1'), '-DeviceMap', str(mapping), '-AllowPartialMap', '-ReleaseReport', str(release),
                   '-AdbPath', str(ROOT / 'tests/fixtures/mock-quest-fleet.ps1'),
                   '-DeployMappedSeats', '-ManagementApi', 'http://127.0.0.1:1']

        def run(bundle, *options, faults=None):
            return subprocess.run([*command, '-VenueBundle', str(bundle), *options], capture_output=True, encoding='utf-8', timeout=30,
                env={**os.environ, **release_env, 'VR_COMMAND_MASTER_KEY': 'fixture-master', 'VR_QUEST_FLEET_FIXTURE': str(self.root),
                     'VR_QUEST_FLEET_FRESH': '', 'VR_QUEST_TEST_SOURCE_STALE': '', 'VR_QUEST_FLEET_FAULTS': json.dumps(faults or {})})

        self.expiry = int(time.time()) + 18
        old_files, old_configs = self.vr_bundle('Independent')
        original = self.write_bundle(old_files, 'original.zip')
        first_report = self.root / 'interrupted-deployment.json'
        initial = run(original, '-SaveDeploymentReport', str(first_report), faults={'fixture-02': 'config-stage-changed'})
        self.assertEqual(1, initial.returncode, initial.stderr)
        previous_bytes = first_report.read_bytes()
        previous = json.loads(previous_bytes)
        self.assertEqual(['launch-requested', 'file-verification-failed', 'not-attempted'], [row['status'] for row in previous['devices']])
        transport_log = self.root / 'transport.log'
        before = transport_log.read_bytes()
        original_first_config = self.root / 'fixture-01/vr-connection.json'
        self.assertEqual(old_configs[1]['room-01-seat-01.json'], json.loads(original_first_config.read_bytes()))

        time.sleep(max(0, self.expiry + .1 - time.time()))
        retry = ('-RetryIncomplete', str(first_report))
        self.assert_rejected(run(original, *retry), 'Player ticket has expired')
        self.expiry = int(time.time()) + 240
        new_files, new_configs = self.vr_bundle('Independent')
        fresh = self.write_bundle(new_files, 'fresh.zip')
        self.assert_rejected(run(fresh, *retry), 'original ZIP, device map and APK requirement')

        original_admission = self.admissions[-1]
        self.admissions[-1] = uuid.uuid4()
        altered_files, _ = self.vr_bundle('Independent')
        altered = self.write_bundle(altered_files, 'changed-admission.zip')
        self.admissions[-1] = original_admission
        replace = (*retry, '-OriginalVenueBundle', str(original))
        self.assert_rejected(run(altered, *replace), 'Refreshed seat 5/5 must use the original session, player and admission')
        self.assertEqual(before, transport_log.read_bytes())

        final_report = self.root / 'resumed-deployment.json'
        resumed = run(fresh, *replace, '-SaveDeploymentReport', str(final_report))
        self.assertEqual(0, resumed.returncode, resumed.stderr)
        final = json.loads(final_report.read_bytes())
        self.assertTrue(final['complete'])
        self.assertEqual(previous_bytes, first_report.read_bytes())
        previous_hash = previous['retry']['venueSha256']
        self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), previous_hash)
        self.assertEqual(previous_hash, final['previousVenueSha256'])
        self.assertEqual(hashlib.sha256(previous_bytes).hexdigest(), final['previousDeploymentSha256'])
        self.assertEqual(dict(previous['retry'], venueSha256=hashlib.sha256(fresh.read_bytes()).hexdigest()), final['retry'])
        self.assertEqual(previous['devices'][0], final['devices'][0])
        self.assertEqual(old_configs[1]['room-01-seat-01.json'], json.loads(original_first_config.read_bytes()))
        for index in (2, 3):
            active = self.root / f'fixture-{index:02}/vr-connection.json'
            self.assertEqual(new_configs[1][f'room-01-seat-{index:02}.json'], json.loads(active.read_bytes()))
        calls = transport_log.read_bytes()[len(before):].decode().splitlines()
        self.assertNotIn('-t 101', '\n'.join(calls))
        self.assertEqual(['102', '103'], [line.split()[1] for line in calls if ' shell am start ' in line])

        spec = importlib.util.spec_from_file_location('quest_capture', ROOT / 'scripts/capture-quest-field-log.py')
        capture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(capture)
        original_bound = capture.bind_deployment(capture.venue_plan(original, mapping, True), first_report, completed_only=True)
        self.assertEqual([1], [row['seat'] for row in original_bound['seats']])
        fresh_plan = capture.venue_plan(fresh, mapping, True)
        incremental = capture.bind_deployment(fresh_plan, final_report, after=first_report)
        self.assertEqual([2, 3], [row['seat'] for row in incremental['seats']])
        broken_report = self.root / 'broken-lineage.json'
        broken_report.write_text(json.dumps(dict(final, previousVenueSha256='e' * 64)), encoding='utf-8')
        with self.assertRaisesRegex(capture.field.EvidenceError, 'changes its original proof'):
            capture.bind_deployment(fresh_plan, broken_report, after=first_report)

    def test_save_mapped_quest_deployment_report_recovers_after_process_exit(self):
        files, _ = self.vr_bundle('Independent')
        bundle = self.write_bundle(files)
        mapping, document = self.device_map()
        document['seats'] = [row for row in document['seats'] if row['serial'] in ('fixture-01', 'fixture-02', 'fixture-03')]
        mapping.write_text(json.dumps(document), encoding='utf-8')
        release, _, release_env = self.release_report(version_code=77)
        command = ['pwsh', '-NoProfile', '-NonInteractive', '-File', str(ROOT / 'tests/fixtures/mock-quest-management.ps1'),
                   str(ROOT / 'scripts/deploy-quest.ps1'), '-VenueBundle', str(bundle),
                   '-DeviceMap', str(mapping), '-AllowPartialMap', '-ReleaseReport', str(release),
                   '-AdbPath', str(ROOT / 'tests/fixtures/mock-quest-fleet.ps1'),
                   '-DeployMappedSeats', '-RequireOpenXR', '-ManagementApi', 'http://127.0.0.1:1']

        def options(fleet, gate=None, faults=None):
            return dict(cwd=fleet, encoding='utf-8', env={**os.environ, **release_env, 'VR_COMMAND_MASTER_KEY': 'fixture-master',
                'VR_QUEST_FLEET_FIXTURE': str(fleet), 'VR_QUEST_FLEET_FAULTS': json.dumps(faults or {}), 'VR_QUEST_FLEET_FRESH': '',
                'VR_QUEST_TEST_SOURCE_STALE': '',
                'VR_QUEST_FLEET_HOLD_AFTER_STAGE': 'fixture-02' if gate == 'stage' else '',
                'VR_QUEST_FLEET_HOLD_AFTER_LAUNCH': 'fixture-02' if gate == 'launch' else ''})

        for stage, signal in (('stage', 'connection-staged.request'), ('launch', 'first-launch.request')):
            with self.subTest(stage=stage):
                fleet = self.root / stage
                fleet.mkdir()
                report = fleet / 'original deployment.json'
                report.write_bytes(b'original report')
                output = ['-SaveDeploymentReport', report.name]
                collision = subprocess.run([*command, *output], capture_output=True, timeout=20, **options(fleet))
                self.assert_rejected(collision, 'Choose a new deployment report file')
                self.assertEqual(b'original report', report.read_bytes())
                self.assertFalse((fleet / 'transport.log').exists())
                report.unlink()

                with subprocess.Popen([*command, *output], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      **options(fleet, stage)) as process:
                    try:
                        deadline = time.monotonic() + 15
                        marker = fleet / signal
                        while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
                            time.sleep(.05)
                        if process.poll() is not None:
                            stdout, stderr = process.communicate()
                            self.fail(f'Deployment exited before {stage}: {stdout}\n{stderr}')
                        self.assertTrue(marker.exists(), f'Deployment did not reach {stage}')
                        original = report.read_bytes()
                        checkpoint = json.loads(original)
                        self.assertEqual(('deployment', False), (checkpoint['phase'], checkpoint['complete']))
                        second_status = 'not-attempted' if stage == 'stage' else 'deployment-failed'
                        self.assertEqual(['launch-requested', second_status, 'not-attempted'],
                                         [row['status'] for row in checkpoint['devices']])
                        if stage == 'launch':
                            self.assertEqual('launch-game', checkpoint['devices'][1]['failedStep'])
                        self.assertNotRegex(original.decode(), r'fixture-\d+|HARDWARE-SERIAL|joinTicket')
                    finally:
                        if process.poll() is None:
                            process.kill()
                        process.communicate(timeout=10)

                self.assertEqual(original, report.read_bytes())
                self.assertFalse(list(fleet.glob('.quest-deploy-*.tmp')))
                transport = fleet / 'transport.log'
                old_calls = transport.read_bytes()
                result = subprocess.run([*command, '-RetryIncomplete', str(report), '-SaveDeploymentReport', 'resumed.json'],
                                        capture_output=True, timeout=25, **options(fleet))
                self.assertEqual(original, report.read_bytes())
                if stage == 'launch':
                    self.assert_rejected(result, 'Confirm the previous launch outcome')
                    self.assertEqual(old_calls, transport.read_bytes())
                    self.assertFalse((fleet / 'resumed.json').exists())
                    original_config = fleet / 'fixture-02/vr-connection.json'
                    config_bytes = original_config.read_bytes()
                    nonce = (fleet / 'fixture-02/openxr-probe').read_text()
                    self.assertEqual({'nonce': nonce, 'configSha256': hashlib.sha256(config_bytes).hexdigest()},
                                     checkpoint['devices'][1]['pendingOpenXR'])
                    retry = ('-RetryIncomplete', str(report), '-RecoverOpenXRLaunch', '-SaveDeploymentReport', 'resumed.json')

                    legacy_report = fleet / 'legacy.json'
                    legacy = json.loads(original)
                    del legacy['devices'][1]['pendingOpenXR']
                    legacy_report.write_text(json.dumps(legacy), encoding='utf-8')
                    missing_proof = subprocess.run([*command, '-RetryIncomplete', str(legacy_report), '-RecoverOpenXRLaunch'],
                                                   capture_output=True, timeout=20, **options(fleet))
                    self.assert_rejected(missing_proof, 'lacks the saved OpenXR launch and configuration proof')
                    self.assertEqual(old_calls, transport.read_bytes())

                    original_config.write_bytes(config_bytes + b'\n')
                    changed_config = subprocess.run([*command, *retry], capture_output=True, timeout=20, **options(fleet))
                    self.assert_rejected(changed_config, 'Saved Quest launch file could not be verified')
                    original_config.write_bytes(config_bytes)
                    missing_xr = subprocess.run([*command, *retry], capture_output=True, timeout=20,
                                                **options(fleet, faults={'fixture-02': 'xr-not-ready'}))
                    self.assert_rejected(missing_xr, 'Quest OpenXR did not become ready')
                    blocked_calls = transport.read_bytes()
                    self.assertNotRegex(blocked_calls[len(old_calls):].decode(), r' (push|shell am) ')
                    self.assertFalse((fleet / 'resumed.json').exists())

                    recovered = subprocess.run([*command, *retry], capture_output=True, timeout=25, **options(fleet))
                    self.assertEqual(0, recovered.returncode, recovered.stderr)
                    latest = json.loads((fleet / 'resumed.json').read_bytes())
                    self.assertEqual(json.loads(recovered.stdout), latest)
                    self.assertTrue(latest['complete'])
                    self.assertEqual(checkpoint['devices'][0], latest['devices'][0])
                    self.assertEqual({'processId': 4302, 'nonce': nonce}, latest['devices'][1]['openXR'])
                    self.assertNotIn('pendingOpenXR', latest['devices'][1])
                    self.assertEqual(hashlib.sha256(original).hexdigest(), latest['previousDeploymentSha256'])
                    self.assertEqual(original, report.read_bytes())
                    self.assertEqual(config_bytes, original_config.read_bytes())
                    recovery_calls = transport.read_bytes()[len(blocked_calls):].decode().splitlines()
                    self.assertFalse(any(line.startswith('-t 102 ') and (' push ' in line or ' shell am ' in line)
                                         for line in recovery_calls))
                    self.assertEqual(['103'], [line.split()[1] for line in recovery_calls if ' shell am start ' in line])
                    continue
                self.assertEqual(0, result.returncode, result.stderr)
                resumed = json.loads((fleet / 'resumed.json').read_bytes())
                self.assertEqual(json.loads(result.stdout), resumed)
                self.assertTrue(resumed['complete'])
                self.assertEqual(hashlib.sha256(original).hexdigest(), resumed['previousDeploymentSha256'])
                self.assertEqual(checkpoint['devices'][0], resumed['devices'][0])
                new_calls = transport.read_bytes()[len(old_calls):].decode().splitlines()
                self.assertNotIn('-t 101', '\n'.join(new_calls))
                self.assertEqual(['102', '103'], [line.split()[1] for line in new_calls if ' shell am start ' in line])

    def test_device_map_reads_all_25_and_reports_faults_without_device_writes(self):
        files, _ = self.bundle('Independent')
        path, _ = self.device_map()
        faults = {'fixture-03': 'missing', 'fixture-07': 'unauthorized', 'fixture-11': 'offline',
                  'fixture-12': 'model-timeout', 'fixture-16': 'wrong-model', 'fixture-18': 'identity-timeout',
                  'fixture-22': 'package-missing', 'fixture-25': 'version-mismatch'}
        result = self.run_fleet(files, path, '-DeployMappedSeats', '-ManagementApi', 'http://127.0.0.1:1', faults=faults)
        self.assertEqual(1, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(('preflight', False), (report['phase'], report['complete']))
        self.assertEqual([(r, s) for r in range(1, 6) for s in range(1, 6)], [(row['roomId'], row['seat']) for row in report['devices']])
        self.assertEqual({2:'missing', 6:'unauthorized', 10:'offline', 11:'adb-timeout', 15:'wrong-model',
                          17:'adb-timeout', 21:'package-unavailable', 24:'version-mismatch'},
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

    def test_device_map_rejects_shared_and_unavailable_device_identities(self):
        files, _ = self.bundle('Independent')
        path, _ = self.device_map()
        faults = {'fixture-01': 'identity-duplicate', 'fixture-07': 'identity-duplicate',
                  'fixture-22': 'identity-invalid', 'fixture-25': 'identity-missing'}
        result = self.run_fleet(files, path, '-CheckOnly', faults=faults)
        self.assertEqual(1, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(('preflight', False), (report['phase'], report['complete']))
        self.assertEqual({0: 'duplicate-device', 6: 'duplicate-device', 21: 'device-identity-unavailable',
                          24: 'device-identity-unavailable'},
                         {i: row['status'] for i, row in enumerate(report['devices']) if row['status'] != 'ready'})
        commands = (self.root / 'adb.log').read_text(encoding='utf-8').splitlines()
        self.assertEqual(25, sum(line.endswith(' shell getprop ro.serialno') for line in commands))
        self.assertTrue(all(line == 'devices' or ' shell getprop ' in line or ' shell pm list packages ' in line for line in commands))
        self.assertNotIn('HARDWARE-SERIAL-', result.stdout + result.stderr)

    def test_mapped_deployment_stops_after_file_failure_and_keeps_prior_results(self):
        self.assert_mapped_deployment_stops('config-stage-changed', 'file-verification-failed', 'stage-connection')

    def test_mapped_deployment_stops_before_writing_to_changed_device(self):
        self.assert_mapped_deployment_stops('identity-changed', 'device-identity-changed', None)

    def test_mapped_deployment_does_not_retarget_after_transport_disconnect(self):
        self.assert_mapped_deployment_stops('disconnect-after-staging', 'deployment-failed', 'stop-game', partial=True)

    def test_mapped_quest_requires_an_unambiguous_transport(self):
        files, _ = self.bundle('Independent')
        path, _ = self.device_map()
        faults = {'fixture-03': 'transport-duplicate', 'fixture-08': 'transport-missing'}
        result = self.run_fleet(files, path, '-CheckOnly', faults=faults)
        self.assertEqual(1, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report['complete'])
        self.assertEqual({0: 'transport-ambiguous', 2: 'transport-ambiguous', 7: 'transport-unavailable'},
                         {i: row['status'] for i, row in enumerate(report['devices']) if row['status'] != 'ready'})
        commands = (self.root / 'transport.log').read_text(encoding='utf-8').splitlines()
        self.assertEqual('devices -l', commands[0])
        self.assertTrue(all(line.startswith('-t ') for line in commands[1:]))
        self.assertFalse(any(line.startswith(('-t 101 ', '-t 103 ', '-t 108 ')) for line in commands[1:]))

    def test_mapped_deployment_requires_a_current_source_receipt_before_each_seat(self):
        for reason in ('source-stale', 'missing-receipt'):
            with self.subTest(reason=reason):
                self.assert_mapped_deployment_stops(reason, 'venue-check-failed', 'verify-live-venue', partial=True)

    def test_mapped_deployment_checks_the_original_source_after_staging(self):
        self.assert_mapped_deployment_stops('source-stale-after-staging', 'venue-check-failed',
                                            'verify-live-venue-before-stop', partial=True)

    def test_release_report_requires_verified_quest_identity_before_adb(self):
        files, _ = self.bundle('Linked')
        mapping, _ = self.device_map()
        release, original, env = self.release_report()
        for target, field, value in [('report', 'verified', 'true'), ('report', 'scope', 'device'),
                                     ('quest', 'applicationId', 'com.other'), ('quest', 'applicationId', ['com.vrcommand.quest']),
                                     ('quest', 'signatureV2', False),
                                     ('quest', 'versionCode', '61'), ('quest', 'sha256', 'z' * 64)]:
            with self.subTest(field=field):
                document = copy.deepcopy(original)
                (document if target == 'report' else document['quest'])[field] = value
                release.write_text(json.dumps(document), encoding='utf-8')
                result = self.run_fleet(files, mapping, '-CheckOnly', release=release, environment=env)
                self.assert_rejected(result, 'successful offline venue release report')
        self.assert_rejected(self.run_fleet(files, mapping, '-CheckOnly', '-ExpectedVersionCode', '64',
                                           release=release, environment=env), 'either -ExpectedVersionCode or -ReleaseReport')
        self.assertFalse((self.root / 'adb.log').exists())

    def test_release_apk_check_fences_all_25_seats_before_any_deployment(self):
        files, _ = self.bundle('Independent')
        mapping, _ = self.device_map()
        release, original, env = self.release_report()
        faults = {'fixture-02': 'apk-hash-mismatch', 'fixture-04': 'apk-path-malformed', 'fixture-08': 'apk-split',
                  'fixture-09': 'apk-unreadable', 'fixture-10': 'apk-hash-wrong-path', 'fixture-25': 'version-mismatch'}
        result = self.run_fleet(files, mapping, '-DeployMappedSeats', '-ManagementApi', 'http://127.0.0.1:1',
                                faults=faults, release=release, environment=env)
        self.assertEqual(1, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(('preflight', False, 64, original['quest']['sha256']),
                         (report['phase'], report['complete'], report['expectedVersionCode'], report['expectedApkSha256']))
        self.assertEqual(hashlib.sha256(release.read_bytes()).hexdigest(), report['venueReleaseReportSha256'])
        self.assertEqual(25, len(report['devices']))
        self.assertEqual({2: 'apk-hash-mismatch', 4: 'apk-unverified', 8: 'apk-unverified', 9: 'apk-unverified',
                          10: 'apk-unverified', 25: 'version-mismatch'},
                         {i: row['status'] for i, row in enumerate(report['devices'], 1) if row['status'] != 'ready'})
        self.assertEqual(19, sum(row.get('apkVerified', False) for row in report['devices']))
        commands = (self.root / 'adb.log').read_text(encoding='utf-8').splitlines()
        self.assertEqual(24, sum(' shell pm path ' in line for line in commands))
        self.assertEqual(22, sum(' shell sha256sum ' in line for line in commands))
        self.assertTrue(all(line == 'devices' or any(' shell ' + op in line for op in ('pm ', 'getprop ', 'sha256sum ')) for line in commands))
        self.assertFalse(any(self.root.glob('fixture-*')))
        for canary in ('fixture-', '/data/app/', 'UNEXPECTED-COMMAND', 'v2.'):
            self.assertNotIn(canary, result.stdout + result.stderr)
        ready = self.run_fleet(files, mapping, '-CheckOnly', release=release, environment=env)
        self.assertEqual(0, ready.returncode, ready.stderr)
        self.assertTrue(all(row['apkVerified'] and row['status'] == 'ready' for row in json.loads(ready.stdout)['devices']))

    def test_release_apk_changed_after_preflight_stops_before_the_affected_seat(self):
        self.assert_mapped_deployment_stops('apk-changed', 'apk-hash-mismatch', None, partial=True, check_release=True)

    def test_mapped_deployment_reports_exact_failure_boundary(self):
        cases = (
            ('directory', 'deployment-failed', 'prepare-device'),
            ('alignment-stage-changed', 'file-verification-failed', 'stage-alignment'),
            ('force-stop', 'deployment-failed', 'stop-game'),
            ('config-move', 'deployment-failed', 'activate-connection'),
            ('config-changed-at-stop', 'file-verification-failed', 'activate-connection'),
            ('alignment-changed-at-stop', 'file-verification-failed', 'activate-connection'),
            ('config-active-changed', 'file-verification-failed', 'verify-active-connection'),
            ('alignment-changed-after-activation', 'file-verification-failed', 'verify-active-connection'),
            ('launch', 'deployment-failed', 'launch-game'),
        )
        for fault, status, step in cases:
            with self.subTest(fault=fault):
                self.assert_mapped_deployment_stops(fault, status, step, partial=True)

    def test_mapped_deployment_keeps_openxr_proof_on_retry_and_stops_at_failed_subsystem(self):
        files, _ = self.bundle('Linked')
        bundle = self.write_bundle(files)
        mapping, document = self.device_map()
        document['seats'] = [row for row in document['seats'] if row['seat'] == 1 and row['roomId'] in (1, 3, 5)]
        mapping.write_text(json.dumps(document), encoding='utf-8')
        release, _, release_env = self.release_report(76)
        session = str(self.session_ids[0])

        class Handler(BaseHTTPRequestHandler):
            def reply(self, body):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(body).encode())

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                response = {'topology': 'Linked', 'allMatched': True, 'seats': [
                    {'roomId': room, 'seat': seat, 'status': 'matched'} for room in range(1, 6) for seat in range(5)]}
                if payload.get('requireLiveSource'):
                    response['liveSourceVerified'] = True
                self.reply(response)

            def do_GET(self):
                self.reply({'version': 1, 'sessionId': session, 'sessionEnded': False, 'address': '192.168.1.10', 'port': 7777})

            def log_message(self, *args):
                pass

        with quest_management_server(Handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                command = ['pwsh', '-NoProfile', '-NonInteractive', '-File', str(ROOT / 'scripts/deploy-quest.ps1'),
                           '-VenueBundle', str(bundle), '-DeviceMap', str(mapping), '-AllowPartialMap',
                           '-AdbPath', str(ROOT / 'tests/fixtures/mock-quest-fleet.ps1'), '-ReleaseReport', str(release),
                           '-DeployMappedSeats', '-ManagementApi', f'http://127.0.0.1:{server.server_port}']

                def invoke(*flags, fault=None):
                    environment = {**os.environ, **release_env, 'VR_QUEST_FLEET_FIXTURE': str(self.root),
                                   'VR_COMMAND_MASTER_KEY': 'PRIVATE_MASTER_CANARY',
                                   'VR_QUEST_FLEET_FAULTS': json.dumps({'fixture-11': fault})}
                    return subprocess.run([*command, *flags], capture_output=True, encoding='utf-8', timeout=30, env=environment)

                first = invoke('-RequireOpenXR', fault='config-stage-changed')
                self.assertEqual(1, first.returncode, first.stderr)
                initial = json.loads(first.stdout)
                self.assertIs(initial['requireOpenXR'], True)
                release_bytes = release.read_bytes()
                release_hash = hashlib.sha256(release_bytes).hexdigest()
                self.assertEqual(release_hash, initial['venueReleaseReportSha256'])
                self.assertEqual(['launch-requested', 'file-verification-failed', 'not-attempted'],
                                 [row['status'] for row in initial['devices']])
                nonce = (self.root / 'fixture-01/openxr-probe').read_text()
                self.assertEqual({'processId': 4301, 'nonce': nonce}, initial['devices'][0]['openXR'])
                previous = self.root / 'first-openxr.json'
                previous.write_text(first.stdout, encoding='utf-8')
                adb_log = self.root / 'adb.log'
                adb_log.unlink()
                release.write_bytes(release_bytes + b'\n')
                self.assert_rejected(invoke('-RequireOpenXR', '-RetryIncomplete', str(previous)),
                                     'exact original Quest venue release report')
                self.assertFalse(adb_log.exists())
                release.write_bytes(release_bytes)
                self.assert_rejected(invoke('-RetryIncomplete', str(previous)), 'original OpenXR requirement')
                self.assertFalse(adb_log.exists())

                failed = invoke('-RequireOpenXR', '-RetryIncomplete', str(previous), fault='xr-not-ready')
                self.assertEqual(1, failed.returncode, failed.stderr)
                result = json.loads(failed.stdout)
                self.assertEqual(release_hash, result['venueReleaseReportSha256'])
                self.assertEqual(initial['devices'][0], result['devices'][0])
                affected = result['devices'][1]
                self.assertEqual(('deployment-failed', 'observe-openxr', True),
                                 (affected['status'], affected['failedStep'], affected['filesVerified']))
                self.assertIn('loader=1, display=1, input=0', affected['openXRFailure'])
                self.assertNotIn('openXR', affected)
                self.assertEqual('not-attempted', result['devices'][2]['status'])
                calls = adb_log.read_text(encoding='utf-8')
                self.assertNotIn('fixture-01 shell', calls)
                self.assertNotIn('fixture-21 shell am', calls)
                self.assertEqual(1, calls.count(' am start -W '))
                failed_report = self.root / 'failed-openxr.json'
                failed_report.write_text(failed.stdout, encoding='utf-8')
                adb_log.unlink()
                self.assert_rejected(invoke('-RequireOpenXR', '-RetryIncomplete', str(failed_report)),
                                     'Confirm the previous launch outcome')
                self.assertFalse(adb_log.exists())

                captured = self.root / 'capture-deployed-seats'
                active_path = self.root / 'fixture-01/vr-connection.json'
                active = active_path.read_bytes()
                scripts = self.root / 'capture-adb'
                scripts.mkdir()
                launch = initial['devices'][0]
                outcome = {key: launch[key] for key in ('roomId', 'sessionId', 'playerId', 'admissionId')}
                messages = (
                    f'VR_QUEST_OPENXR nonce={nonce} loader=1 display=1 input=1',
                    'VR_NETWORK_STARTED role=Client started=True background=False port=7777',
                    'VR_CLIENT_CONNECTED id=1', 'VR_CLIENT_DEBRIEF_FINAL ' + json.dumps(dict(outcome, version=1)),
                    'VR_CLIENT_DISCONNECTED',
                )
                raw = ''.join(f'11-09 14:30:00.000 4301 14325 I Unity : {message}\r\n' for message in messages).encode()
                (scripts / 'fixture-01').write_text(f'''import sys
from pathlib import Path
args = sys.argv[1:]
with Path("commands").open("a") as audit:
    audit.write(" ".join(args) + "\\n")
if args == ["shell", "getprop", "ro.serialno"]:
    print("HARDWARE-SERIAL-fixture-01")
elif args == ["shell", "pidof", "com.vrcommand.quest"]:
    print(4301)
else:
    assert args == ["logcat", "-b", "main", "--pid=4301", "-v", "threadtime", "-s", "Unity:I"]
    sys.stdout.buffer.write({raw!r})
''', encoding='utf-8')
                (scripts / 'adb-transports.json').write_text(json.dumps({'fixture-01': 41}), encoding='utf-8')
                capture_command = [sys.executable, str(CAPTURE_FIXTURE), '--adb', sys.executable,
                                   '--venue-bundle', str(bundle), '--device-map', str(mapping), '--allow-partial-map',
                                   '--deployment-report', str(failed_report), '--output-directory', str(captured), '--seconds', '8']
                skipped = subprocess.run(capture_command, cwd=scripts, capture_output=True, encoding='utf-8', timeout=12)
                self.assert_rejected(skipped, 'Use --capture-deployed-seats')
                mapped = mapping.read_bytes()
                changed = json.loads(mapped)
                next(row for row in changed['seats'] if row['roomId'] == 5)['serial'] = 'fixture-22'
                mapping.write_text(json.dumps(changed), encoding='utf-8')
                rejected = subprocess.run([*capture_command, '--capture-deployed-seats'], cwd=scripts,
                                          capture_output=True, encoding='utf-8', timeout=12)
                self.assert_rejected(rejected, 'original device map')
                mapping.write_bytes(mapped)
                self.assertFalse(captured.exists())
                self.assertFalse((scripts / 'commands').exists())
                unchanged = subprocess.run([*capture_command, '--capture-deployed-seats', '--after-deployment-report', str(previous)],
                                           cwd=scripts, capture_output=True, encoding='utf-8', timeout=12)
                self.assert_rejected(unchanged, 'No seats have launched since')
                self.assertFalse(captured.exists())
                observed = subprocess.run([*capture_command, '--capture-deployed-seats'], cwd=scripts,
                                          capture_output=True, encoding='utf-8', timeout=15)
                self.assertEqual(0, observed.returncode, observed.stderr)
                summary = json.loads(observed.stdout)
                self.assertEqual((True, True, 1, 1), tuple(summary[key] for key in
                                 ('partialDeployment', 'complete', 'expectedSeats', 'capturedSeats')))
                self.assertEqual(hashlib.sha256(failed_report.read_bytes()).hexdigest(), summary['deploymentSha256'])
                self.assertIn({'stage': 'venue-capture-ready', 'seats': 1, 'partialDeployment': True},
                              [json.loads(line) for line in observed.stderr.splitlines()])
                self.assertEqual(raw, (captured / 'room-01-seat-01-logcat.txt').read_bytes())
                self.assertEqual(active, active_path.read_bytes())
                self.assertEqual(['shell getprop ro.serialno', 'shell pidof com.vrcommand.quest',
                                  'logcat -b main --pid=4301 -v threadtime -s Unity:I',
                                  'shell getprop ro.serialno', 'shell pidof com.vrcommand.quest',
                                  'shell pidof com.vrcommand.quest', 'shell getprop ro.serialno'],
                                 (scripts / 'commands').read_text().splitlines())
            finally:
                server.shutdown()
                thread.join(timeout=5)

    def test_mapped_deployment_retries_only_original_unfinished_seats(self):
        files, _ = self.bundle('Independent')
        original = self.write_bundle(files)
        original_bytes = original.read_bytes()
        mapping, _ = self.device_map()
        rows = json.loads(mapping.read_bytes())
        rows['seats'] = [row for row in rows['seats'] if row['roomId'] == 1 and row['seat'] <= 3]
        mapping.write_text(json.dumps(rows), encoding='utf-8')
        release, _, release_env = self.release_report()
        sessions = {str(session): 7777 + index for index, session in enumerate(self.session_ids)}
        calls = []

        class Handler(BaseHTTPRequestHandler):
            def respond(self, body):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(body).encode())

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                calls.append(body)
                response = {'topology': 'Independent', 'allMatched': True, 'seats': [
                    {'roomId': room, 'seat': seat, 'status': 'matched'} for room in range(1, 6) for seat in range(5)]}
                if body.get('requireLiveSource'):
                    response['liveSourceVerified'] = True
                self.respond(response)

            def do_GET(self):
                session = self.path.split('/')[3]
                self.respond({'version': 1, 'sessionId': session, 'sessionEnded': False, 'address': '192.168.1.10', 'port': sessions[session]})

            def log_message(self, *args):
                pass

        with quest_management_server(Handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                command = ['pwsh', '-NoProfile', '-NonInteractive', '-File', str(ROOT/'scripts/deploy-quest.ps1'),
                           '-VenueBundle', str(original), '-DeviceMap', str(mapping), '-AllowPartialMap',
                           '-ReleaseReport', str(release), '-AdbPath', str(ROOT/'tests/fixtures/mock-quest-fleet.ps1'),
                           '-DeployMappedSeats', '-ManagementApi', f'http://127.0.0.1:{server.server_port}']
                log = self.root/'adb.log'
                first_report = self.root/'first.json'

                def invoke(*extra, faults=None, transport_base=100):
                    return subprocess.run([*command, *extra], capture_output=True, encoding='utf-8', timeout=20,
                        env={**os.environ, **release_env, 'VR_QUEST_FLEET_FIXTURE': str(self.root),
                             'VR_COMMAND_MASTER_KEY': 'PRIVATE_MASTER_CANARY', 'VR_QUEST_FLEET_FAULTS': json.dumps(faults or {}),
                             'VR_QUEST_FLEET_TRANSPORT_BASE': str(transport_base)})

                previous = self.root / 'fixture-02' / 'vr-connection.json'
                previous.parent.mkdir()
                original_connection = b'{"fixture":"previous connection"}'
                previous.write_bytes(original_connection)
                first = invoke(faults={'fixture-02': 'config-changed-at-stop'})
                self.assertEqual(1, first.returncode, first.stderr)
                interrupted = json.loads(first.stdout)
                self.assertEqual(['launch-requested','file-verification-failed','not-attempted'],
                                 [row['status'] for row in interrupted['devices']])
                self.assertEqual('activate-connection', interrupted['devices'][1]['failedStep'])
                self.assertEqual(original_connection, previous.read_bytes())
                self.assertEqual(hashlib.sha256(original_bytes).hexdigest(), interrupted['retry']['venueSha256'])
                first_report.write_text(first.stdout, encoding='utf-8')
                done_config = self.root/'fixture-01/vr-connection.json'
                done_bytes = done_config.read_bytes()
                log.unlink()
                retry = ('-RetryIncomplete', str(first_report))

                original.write_bytes(original_bytes + b'ignored ZIP suffix')
                self.assert_rejected(invoke(*retry), 'original ZIP, device map and APK requirement')
                original.write_bytes(original_bytes)
                changed = copy.deepcopy(rows)
                changed['seats'][0]['serial'] = 'fixture-04'
                mapping.write_text(json.dumps(changed), encoding='utf-8')
                self.assert_rejected(invoke(*retry), 'original ZIP, device map and APK requirement')
                mapping.write_text(json.dumps(rows), encoding='utf-8')
                changed = copy.deepcopy(interrupted)
                changed['devices'][1].update(status='deployment-failed', failedStep='launch-game')
                uncertain = self.root/'uncertain.json'
                uncertain.write_text(json.dumps(changed), encoding='utf-8')
                self.assert_rejected(invoke('-RetryIncomplete', str(uncertain)), 'Confirm the previous launch outcome')
                self.assertFalse(log.exists())

                alias = invoke(*retry, faults={'fixture-02': 'identity-first-device'})
                self.assertEqual(1, alias.returncode, alias.stderr)
                rejected = json.loads(alias.stdout)
                self.assertEqual('preflight', rejected['phase'])
                self.assertEqual(['device-identity-changed', 'ready'], [row['status'] for row in rejected['devices']])
                commands = log.read_text(encoding='utf-8')
                self.assertNotIn('-s fixture-01 ', commands)
                self.assertNotIn('force-stop', commands)
                self.assertNotIn(' push ', commands)
                log.unlink()

                retry_again = invoke(*retry, faults={'fixture-03': 'config-stage-changed'})
                self.assertEqual(1, retry_again.returncode, retry_again.stderr)
                retried = json.loads(retry_again.stdout)
                self.assertEqual(interrupted['devices'][0], retried['devices'][0])
                self.assertEqual(['launch-requested','launch-requested','file-verification-failed'],
                                 [row['status'] for row in retried['devices']])
                self.assertEqual(interrupted['retry'], retried['retry'])
                self.assertEqual(hashlib.sha256(first_report.read_bytes()).hexdigest(), retried['previousDeploymentSha256'])
                self.assertNotIn('-s fixture-01 ', log.read_text(encoding='utf-8'))
                report = self.root/'retry.json'
                report.write_text(retry_again.stdout, encoding='utf-8')
                log.unlink()

                transport_log = self.root / 'transport.log'
                transport_log.unlink()
                resumed = invoke('-RetryIncomplete', str(report), transport_base=200)
                self.assertEqual(0, resumed.returncode, resumed.stderr)
                transport_commands = transport_log.read_text(encoding='utf-8').splitlines()
                self.assertEqual('devices -l', transport_commands[0])
                self.assertTrue(all(line.startswith('-t 203 ') for line in transport_commands[1:]))
                self.assertTrue(any(line.startswith('-t 203 shell am start ') for line in transport_commands))
                final = json.loads(resumed.stdout)
                self.assertEqual((True, 3, 22), (final['complete'], final['mappedSeats'], final['unmappedSeats']))
                self.assertEqual(hashlib.sha256(report.read_bytes()).hexdigest(), final['previousDeploymentSha256'])
                self.assertEqual(retried['devices'][:2], final['devices'][:2])
                self.assertTrue(all(row['status'] == 'launch-requested' and row['apkVerified'] for row in final['devices']))
                final_report = self.root / 'final-deployment.json'
                final_report.write_text(resumed.stdout, encoding='utf-8')
                spec = importlib.util.spec_from_file_location('capture_quest', ROOT / 'scripts/capture-quest-field-log.py')
                capture = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(capture)
                capture_plan = capture.venue_plan(original, mapping, True)
                self.assertEqual(interrupted['retry']['venueSha256'], capture_plan['venueSha256'])
                bound = capture.bind_deployment(capture_plan, final_report)
                self.assertEqual(hashlib.sha256(final_report.read_bytes()).hexdigest(), bound['deploymentSha256'])
                self.assertEqual(final['retry']['devices'], [seat['deviceIdentity'][1] for seat in bound['seats']])
                with self.assertRaisesRegex(capture.field.EvidenceError, 'exact preceding Quest deployment report'):
                    capture.bind_deployment(capture_plan, final_report, after=first_report)
                incremental = capture.bind_deployment(capture_plan, final_report, after=report)
                self.assertEqual(bound['seats'][2:], incremental['seats'])
                changed_map = copy.deepcopy(capture_plan)
                changed_map['seats'][0]['serial'] = 'fixture-04'
                with self.assertRaisesRegex(capture.field.EvidenceError, 'original device map'):
                    capture.bind_deployment(changed_map, final_report)
                with self.assertRaisesRegex(capture.field.EvidenceError, 'original venue ZIP'):
                    capture.bind_deployment(dict(capture_plan, venueSha256='f' * 64), final_report)
                adb_capture = self.root / 'capture-adb.py'
                adb_capture.write_text('''from pathlib import Path
import sys
root = Path(__file__).parent
transports = {str(index): path.stem for index, path in enumerate(sorted(root.glob('fixture-*.logcat')), 1)}
if sys.argv[1:] == ['devices', '-l']:
    print('List of devices attached')
    for transport, serial in transports.items():
        print(f'{serial} device transport_id:{transport}')
    sys.exit(0)
assert sys.argv[1] == '-t'
serial, command = transports[sys.argv[2]], sys.argv[3:]
if command == ['shell', 'getprop', 'ro.serialno']:
    print('HARDWARE-SERIAL-' + serial)
elif command == ['shell', 'pidof', 'com.vrcommand.quest']:
    print(7342)
else:
    assert command == ['logcat', '-b', 'main', '--pid=7342', '-v', 'threadtime', '-s', 'Unity:I']
    sys.stdout.buffer.write(Path(__file__).with_name(serial + '.logcat').read_bytes())
''', encoding='utf-8')
                original_logs = {}
                for seat in bound['seats']:
                    result = {'version': 1, **{key: seat[key] for key in ('roomId', 'sessionId', 'playerId', 'admissionId')}}
                    messages = (f"VR_NETWORK_STARTED role=Client started=True background=False port={seat['port']}",
                                'VR_CLIENT_CONNECTED id=1', 'VR_CLIENT_DEBRIEF_FINAL ' + json.dumps(result),
                                'VR_CLIENT_DISCONNECTED')
                    raw = ''.join(f'11-09 00:00:00.000 7342 7343 I Unity : {message}\n' for message in messages).encode()
                    (self.root / (seat['serial'] + '.logcat')).write_bytes(raw)
                    original_logs[seat['roomId'], seat['seat']] = raw
                captured = self.root / 'capture-after-deploy'
                with redirect_stderr(io.StringIO()):
                    capture_result = asyncio.run(capture.capture_venue([sys.executable, str(adb_capture)], bound, captured, 10))
                self.assertTrue(capture_result['complete'])
                self.assertEqual(bound['deploymentSha256'], capture_result['deploymentSha256'])
                capture_report = capture.field.read_quest_capture_report(captured / 'capture-report.json', 'Independent')
                for seat in capture_report['seats']:
                    self.assertEqual(original_logs[seat['roomId'], seat['seat']], (captured / seat['log']).read_bytes())
                captured_delta = self.root / 'capture-newly-deployed'
                with redirect_stderr(io.StringIO()):
                    delta_result = asyncio.run(capture.capture_venue([sys.executable, str(adb_capture)], incremental, captured_delta, 10))
                self.assertEqual((1, 1), (delta_result['expectedSeats'], delta_result['capturedSeats']))
                self.assertEqual(original_logs[1, 3], (captured_delta / 'room-01-seat-03-logcat.txt').read_bytes())
                self.assertEqual({'capture-report.json', 'room-01-seat-03-logcat.txt'}, {file.name for file in captured_delta.iterdir()})
                self.assertNotIn('HARDWARE-SERIAL-', json.dumps(capture_report))
                self.assertEqual(done_bytes, done_config.read_bytes())
                commands = log.read_text(encoding='utf-8').splitlines()
                self.assertEqual({'fixture-03'}, {line.split()[1] for line in commands if line.startswith('-s ')})
                self.assertEqual(1, sum(' shell am start ' in line for line in commands))
                self.assertTrue(all(len(call['rooms']) == 5 for call in calls))
                for text in (first.stdout, retry_again.stdout, resumed.stdout):
                    for secret in ('PRIVATE_MASTER_CANARY', 'HARDWARE-SERIAL-', 'fixture-01', 'v2.'):
                        self.assertNotIn(secret, text)
            finally:
                server.shutdown()
                thread.join(timeout=5)

    def assert_mapped_deployment_stops(self, fault, expected_status, failed_step, *, partial=False, check_release=False):
        files, seats = self.bundle('Linked')
        path, _ = self.device_map()
        count = 5 if partial else 25
        if partial:
            mapping = json.loads(path.read_bytes())
            mapping['seats'] = [row for row in mapping['seats'] if row['roomId'] == 1]
            path.write_text(json.dumps(mapping), encoding='utf-8')
        session = str(self.session_ids[0])
        calls = []
        write_checks = []

        class Handler(BaseHTTPRequestHandler):
            def respond(self, data):
                calls.append(self.path)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                receipt = {'topology': 'Linked', 'allMatched': True, 'seats': [
                    {'roomId': room, 'seat': seat, 'status': 'matched'} for room in range(1, 6) for seat in range(5)]}
                if body.get('requireLiveSource') is True:
                    write_checks.append(body)
                    receipt['liveSourceVerified'] = True
                    commands = (fleet / 'adb.log').read_text(encoding='utf-8').splitlines()
                    staged = any(line.startswith('-s fixture-04 shell sha256sum ') and '/vr-connection-' in line for line in commands)
                    if (len(write_checks) == 7 and fault == 'source-stale') or (staged and fault == 'source-stale-after-staging'):
                        receipt.update(allMatched=False, liveSourceVerified=False)
                        for row in receipt['seats'][-5:]:
                            row['status'] = 'source-stale'
                    if len(write_checks) == 7 and fault == 'missing-receipt':
                        del receipt['liveSourceVerified']
                self.respond(receipt)

            def do_GET(self):
                self.respond({'version': 1, 'sessionId': session, 'sessionEnded': False, 'address': '192.168.1.10', 'port': 7777})

            def log_message(self, *args):
                pass

        fleet = self.root / fault
        before = fleet / 'fixture-04'
        before.mkdir(parents=True)
        (before / 'vr-connection.json').write_bytes(b'previous connection')
        release, release_env = None, {}
        if check_release:
            release, _, release_env = self.release_report()
        with quest_management_server(Handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                flags = ('-AllowPartialMap',) if partial else ()
                result = self.run_fleet(files, path, *flags, '-DeployMappedSeats', '-ManagementApi', f'http://127.0.0.1:{server.server_port}',
                                        faults={'fixture-04': fault}, environment={**release_env, 'VR_COMMAND_MASTER_KEY': 'PRIVATE_MASTER_CANARY'},
                                        fleet_root=fleet, release=release)
            finally:
                server.shutdown()
                thread.join(timeout=5)
        self.assertEqual(1, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        if fault == 'disconnect-after-staging':
            self.assertFalse((fleet / 'replacement-device.log').exists(), 'No commands may be sent to a replacement ADB transport')
            transport_commands = (fleet / 'transport.log').read_text(encoding='utf-8').splitlines()
            self.assertIn('-t 104 shell am force-stop com.vrcommand.quest', transport_commands)
            self.assertFalse(any(line.startswith('-t 104 shell am start ') for line in transport_commands))
        self.assertEqual(('deployment', False, True), (report['phase'], report['complete'], report['managementVerified']))
        self.assertEqual(['launch-requested'] * 3 + [expected_status] + ['not-attempted'] * (count - 4),
                         [row['status'] for row in report['devices']])
        self.assertEqual([True] * 3 + [None] * (count - 3), [row.get('filesVerified') for row in report['devices']])
        self.assertEqual([None] * 3 + [failed_step] + [None] * (count - 4), [row.get('failedStep') for row in report['devices']])
        expected_write_checks = 6 if fault in ('identity-changed', 'apk-changed') else 7
        after_stop = ('force-stop', 'config-move', 'config-changed-at-stop', 'config-active-changed',
                      'alignment-changed-at-stop', 'alignment-changed-after-activation', 'launch')
        if fault in (*after_stop, 'source-stale-after-staging', 'disconnect-after-staging'):
            expected_write_checks += 1
        self.assertEqual(['/api/mr-deployment/venue-check', f'/api/sessions/{session}/connection-endpoint']
                         + ['/api/mr-deployment/venue-check'] * expected_write_checks, calls)
        self.assertEqual(expected_write_checks, len(write_checks))
        self.assertTrue(all(proof == write_checks[0] for proof in write_checks))
        active = (before / 'vr-connection.json').read_bytes()
        if fault in ('config-active-changed', 'alignment-changed-after-activation', 'launch'):
            self.assertEqual(seats[1]['room-01-seat-04.json']['joinTicket'], json.loads(active)['joinTicket'])
            self.assertEqual(fault == 'config-active-changed', active.endswith(b'\n'))
        else:
            self.assertEqual(b'previous connection', active)
        self.assertEqual(1 if fault == 'disconnect-after-staging' else 0, len(list(before.glob('*.tmp'))))
        self.assertEqual(['fixture-01','fixture-02','fixture-03','fixture-04'], sorted(folder.name for folder in fleet.glob('fixture-*')))
        for seat in range(1, 4):
            actual = json.loads((fleet / f'fixture-{seat:02}' / 'vr-connection.json').read_bytes())
            self.assertEqual(seats[1][f'room-01-seat-{seat:02}.json']['joinTicket'], actual['joinTicket'])
        commands = (fleet / 'adb.log').read_text(encoding='utf-8').splitlines()
        first_write = next(index for index, line in enumerate(commands) if 'shell mkdir -p' in line)
        self.assertEqual(3 * count + 3 + (2 * count + 2 if check_release else 0), first_write)
        self.assertEqual(count + 4, sum(line.endswith(' shell getprop ro.serialno') for line in commands))
        if check_release:
            self.assertEqual([True] * 3 + [None] * (count - 3), [row.get('apkVerified') for row in report['devices']])
            self.assertEqual(1, report['apkVerificationVersion'])
            for index, row in enumerate(report['devices'][:3]):
                self.assertEqual((session, str(self.players[index]), str(self.admissions[index]), 7777),
                                 (row['sessionId'], row['playerId'], row['admissionId'], row['port']))
            self.assertTrue(all('admissionId' not in row for row in report['devices'][3:]))
            self.assertEqual(2, sum(line.startswith('-s fixture-04 shell pm path ') for line in commands))
            self.assertFalse(any(line.startswith('-s fixture-04 shell mkdir ') for line in commands))
        self.assertEqual(fault in after_stop,
                         any(line.startswith('-s fixture-04 shell am force-stop ') for line in commands))
        if fault == 'source-stale-after-staging':
            self.assertTrue(any(line.startswith('-s fixture-04 shell sha256sum ') and '/vr-connection-' in line for line in commands))
            self.assertTrue(any(line.startswith('-s fixture-04 shell rm -f ') and '/vr-connection-' in line for line in commands))
            self.assertFalse(any(line.startswith('-s fixture-04 shell staged=$(sha256sum ') and line.endswith("/vr-connection.json'") for line in commands))
        if fault == 'identity-changed':
            self.assertEqual(['-s fixture-04 shell pm list packages -e --show-versioncode --user current com.vrcommand.quest',
                              '-s fixture-04 shell getprop ro.serialno',
                              '-s fixture-04 shell getprop ro.serialno'],
                             [line for line in commands if line.startswith('-s fixture-04 ') and not line.endswith('ro.product.model')])
        self.assertEqual(4 if fault == 'launch' else 3, sum(' shell am start ' in line for line in commands))
        self.assertNotIn('v2.', result.stdout + result.stderr)
        self.assertNotIn('HARDWARE-SERIAL-', result.stdout + result.stderr)
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
        shutil.copyfile(ROOT / 'scripts/quest-adb-process.ps1', scripts / 'quest-adb-process.ps1')
        adb = scripts / 'mock-adb.ps1'
        adb.write_text(ADB_FIXTURE, encoding='utf-8')
        apk = self.root / 'artifacts/quest/VrCommand.apk'
        apk.parent.mkdir(parents=True)
        apk.write_bytes(b'mock APK')
        remote = self.root / 'remote'
        remote.mkdir()
        environment = {**os.environ, 'QUEST_TEST_ROOT':str(self.root), 'QUEST_TEST_SH': posix_shell(),
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
        self.assertEqual('devices -l', commands[0])
        self.assertTrue(all(command.startswith('-t 41 ') for command in commands[1:]))
        self.assertEqual(2, sum(' push ' in command for command in commands))
        self.assertIn('shell am start', commands[-1])
        self.assertNotIn(config['joinTicket'], result.stdout + result.stderr + ''.join(commands))

        release, release_data, _ = self.release_report()
        apk.unlink()
        (self.root / 'adb.log').unlink()
        result = self.run_bundle(files, '-RoomId', '4', '-Seat', '3', '-Serial', 'fixture', '-AdbPath', str(adb),
                                 '-UseInstalledApk', '-ReleaseReport', str(release), script=script,
                                 environment={**environment, 'QUEST_TEST_RELEASE_HASH': release_data['quest']['sha256']})
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(config, json.loads((remote / 'vr-connection.json').read_bytes()))
        self.assertEqual(files['room-04-alignment.json'], (remote / name).read_bytes())
        commands = (self.root / 'adb.log').read_text(encoding='utf-8')
        self.assertNotIn(' install ', commands)
        self.assertLess(commands.index('sha256sum /data/app/fixture/base.apk'), commands.index(' push '))

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
        with quest_management_server(Handler) as server:
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

    def test_single_online_seat_rechecks_the_source_after_apk_install(self):
        self.assert_single_online_seat_rechecks_source(after_staging=False)

    def test_single_online_seat_rechecks_the_source_after_staging(self):
        self.assert_single_online_seat_rechecks_source(after_staging=True)

    def assert_single_online_seat_rechecks_source(self, *, after_staging):
        files, _ = self.bundle('Linked')
        scripts = self.root / 'scripts'
        scripts.mkdir()
        script = scripts / 'deploy-quest.ps1'
        shutil.copyfile(ROOT / 'scripts' / script.name, script)
        shutil.copyfile(ROOT / 'scripts/quest-adb-process.ps1', scripts / 'quest-adb-process.ps1')
        adb = scripts / 'mock-adb.ps1'
        adb.write_text(ADB_FIXTURE, encoding='utf-8')
        apk = self.root / 'artifacts/quest/VrCommand.apk'
        apk.parent.mkdir(parents=True)
        apk.write_bytes(b'mock APK')
        remote = self.root / 'remote'
        remote.mkdir()
        if after_staging:
            (remote / 'vr-connection.json').write_bytes(b'previous connection')
        log = self.root / 'adb.log'
        reads = []

        class Handler(BaseHTTPRequestHandler):
            def respond(self, data):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                strict = body.get('requireLiveSource') is True
                commands = log.read_text(encoding='utf-8').splitlines() if log.is_file() else []
                installed = any(' install ' in line for line in commands)
                staged = any(' shell sha256sum ' in line and '/vr-connection-' in line for line in commands)
                reads.append((strict, installed, staged))
                live = not (staged if after_staging else installed)
                receipt = {'topology': 'Linked', 'allMatched': live, 'seats': [
                    {'roomId': room, 'seat': seat, 'status': 'matched' if live else 'source-stale'}
                    for room in range(1, 6) for seat in range(5)]}
                if strict:
                    receipt['liveSourceVerified'] = live
                self.respond(receipt)

            def do_GET(self):
                self.respond({'version': 1, 'sessionId': str(self.server.session), 'sessionEnded': False, 'address': '192.168.1.10', 'port': 7777})

            def log_message(self, *args):
                pass

        with quest_management_server(Handler) as server:
            server.session = self.session_ids[0]
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                result = self.run_bundle(files, '-RoomId', '4', '-Seat', '3', '-Serial', 'fixture', '-AdbPath', str(adb),
                    '-ManagementApi', f'http://127.0.0.1:{server.server_port}', script=script,
                    environment={**os.environ, 'QUEST_TEST_ROOT': str(self.root), 'QUEST_TEST_SH': posix_shell(),
                                 'VR_COMMAND_MASTER_KEY': 'PRIVATE_MASTER_CANARY'})
            finally:
                server.shutdown()
                thread.join(timeout=5)
        self.assert_rejected(result, 'source-stale')
        expected = [(False, False, False), (True, False, False), (True, True, False)]
        commands = log.read_text(encoding='utf-8').splitlines()
        if after_staging:
            expected.append((True, True, True))
            self.assertTrue(any(' shell rm -f ' in line and '/vr-connection-' in line for line in commands))
            self.assertFalse(any(' force-stop ' in line or ' am start ' in line for line in commands))
            self.assertFalse(list(remote.glob('*.tmp')))
            self.assertEqual(b'previous connection', (remote / 'vr-connection.json').read_bytes())
        else:
            self.assertEqual(3, len(commands))
            self.assertFalse(list(remote.iterdir()))
        self.assertEqual(expected, reads)

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
        with quest_management_server(Handler) as server:
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
