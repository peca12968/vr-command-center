import importlib.util
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('startup', ROOT / 'scripts/check-desktop-startup.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import windows_firewall


class StartupWitnessTests(unittest.TestCase):
    def packet(self, observed=7, phase='Running', tick=1, suspended=False):
        return {'sequence': 119, 'observedSequence': observed, 'elapsedMilliseconds': 17261, 'suspended': suspended, 'frame': {'phase': phase, 'tick': tick}}

    def test_preparing_tick_zero_cannot_be_confused_with_accepted_begin(self):
        self.assertFalse(m.applied(self.packet(6, 'Preparing', 0), 7))
        self.assertFalse(m.applied(self.packet(7, 'Preparing', 0), 7))

    def test_old_running_policy_is_not_the_current_command_ack(self):
        self.assertFalse(m.applied(self.packet(6), 7))
        self.assertTrue(m.applied(self.packet(7), 7))

    def test_suspension_zero_tick_or_wrong_phase_prevents_application(self):
        for packet in [self.packet(suspended=True), self.packet(tick=0), self.packet(phase='Paused'), self.packet(phase='Ended')]:
            self.assertFalse(m.applied(packet, 7))

    def test_witness_has_no_actors_ticket_or_raw_payload(self):
        packet = self.packet(); packet['joinTicket'] = 'private'; packet['frame']['players'] = [{'id': 'private'}]
        self.assertEqual({'sequence', 'observedSequence', 'elapsedMilliseconds', 'suspended', 'phase', 'tick'}, set(m.witness(packet)))


class NativeLaunchTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Windows player entry uses Windows process options')
    def test_windows_player_checks_policy_before_starting_a_child_with_exact_arguments(self):
        compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
        if not compiler.is_file():
            self.skipTest('Windows .NET Framework compiler is unavailable')
        powershell = shutil.which('pwsh') or 'powershell.exe'
        with tempfile.TemporaryDirectory(prefix='player startup 測試 ') as directory:
            root = Path(directory)
            image, config, witness = (root / name for name in ('VrCommand.exe', '連線 設定.json', 'child.txt'))
            config.touch()
            for name in ('start-windows-vr.ps1', 'windows-process.ps1'):
                shutil.copyfile(ROOT / 'scripts' / name, root / name)
            (root / 'check-windows-firewall-notifications.ps1').write_text('''
param([string]$Executable, [switch]$Unattended)
if ($Executable -cne $env:FIXTURE_IMAGE -or -not $Unattended -or $env:VR_COMMAND_UNATTENDED -ne '1') { exit 9 }
$previous = Test-Path -LiteralPath 'checked.txt'
Add-Content -LiteralPath 'checked.txt' -Value $Executable
if ($previous) { exit ([int]$env:FIXTURE_FINAL_EXIT) }
exit ([int]$env:FIXTURE_FIREWALL_EXIT)
''', encoding='utf-8')
            source = root / 'Fixture.cs'
            source.write_text('''
using System;
using System.IO;
class Fixture {
    static int Main(string[] args) {
        File.WriteAllLines("child.txt", new[] { Environment.GetEnvironmentVariable("VR_COMMAND_UNATTENDED") });
        File.AppendAllLines("child.txt", args);
        return 17;
    }
}
''', encoding='utf-8')
            subprocess.run([str(compiler), '/nologo', '/out:' + str(image), str(source)], check=True,
                           capture_output=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
            metrics = str(root / '量測 資料.json')
            command = [powershell, '-NoProfile', '-NonInteractive', '-File', str(root / 'start-windows-vr.ps1'),
                       '-Executable', str(image), '-Config', str(config), '-LinkMetrics', metrics]
            env = {**os.environ, 'VR_COMMAND_UNATTENDED': '0', 'FIXTURE_IMAGE': str(image)}
            for initial, final, expected in ((2, 0, 2), (0, 2, 2), (0, 0, 17)):
                checks = root / 'checked.txt'
                checks.unlink(missing_ok=True)
                result = subprocess.run(command, cwd=root, env={**env, 'FIXTURE_FIREWALL_EXIT': str(initial),
                                                               'FIXTURE_FINAL_EXIT': str(final)},
                                        capture_output=True, text=True, errors='replace', timeout=15,
                                        creationflags=subprocess.CREATE_NO_WINDOW)
                self.assertEqual(expected, result.returncode, result.stderr)
                self.assertEqual(1 if initial else 2, len(checks.read_bytes().splitlines()))
                if expected == 2:
                    self.assertFalse(witness.exists())
            self.assertEqual(['1', '--vr-config', str(config), '--vr-link-metrics', metrics],
                             witness.read_text(encoding='utf-8').splitlines())

    def test_desktop_venue_rejects_python_before_creating_a_port_probe(self):
        refusal = windows_firewall.WindowsFirewallLaunchError('Python firewall preflight refused.')
        with patch.object(windows_firewall, 'require_silent_windows_launch', side_effect=refusal) as guard, \
                patch.object(m.vm.socket, 'socket') as socket:
            with self.assertRaisesRegex(windows_firewall.WindowsFirewallLaunchError, 'Python firewall preflight refused'):
                m.vm.Venue(SimpleNamespace())

        guard.assert_called_once_with(sys.executable)
        socket.assert_not_called()

    def test_tcp_smoke_scripts_reject_python_before_creating_a_port_probe(self):
        refusal = windows_firewall.WindowsFirewallLaunchError('Python firewall preflight refused.')
        for script in ('smoke_api.py', 'smoke_world.py'):
            with self.subTest(script=script), patch.dict(os.environ, {'VR_COMMAND_WORLD_TEST_WINDOWS_IPC': '0'}), \
                    patch.object(windows_firewall, 'require_silent_windows_launch', side_effect=refusal) as guard, \
                    patch.object(m.vm.socket, 'socket') as socket:
                with self.assertRaisesRegex(SystemExit, 'Python firewall preflight refused'):
                    runpy.run_path(str(ROOT / 'scripts' / script))

            guard.assert_called_once_with(sys.executable)
            socket.assert_not_called()

    @unittest.skipUnless(os.name == 'nt', 'Control GUI validation uses Windows')
    def test_control_gui_exits_before_opening_port_when_python_preflight_refuses(self):
        spec = importlib.util.spec_from_file_location('control_gui', ROOT / 'scripts/check-control-gui.py')
        gui = importlib.util.module_from_spec(spec); spec.loader.exec_module(gui)
        refusal = windows_firewall.WindowsFirewallLaunchError('Python firewall preflight refused.')
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(sys, 'argv', ['check-control-gui.py', directory, '--runtime-root', directory]), \
                patch.object(gui.checks.package, 'verify'), \
                patch.object(windows_firewall, 'require_silent_windows_launch', side_effect=refusal) as guard, \
                patch.object(gui.socket, 'socket') as socket, patch.object(gui.subprocess, 'Popen') as launch, \
                patch('sys.stderr'):
            with self.assertRaises(SystemExit) as exit_status:
                gui.main()

        self.assertEqual(exit_status.exception.code, 2)
        guard.assert_called_once_with(sys.executable)
        socket.assert_not_called()
        launch.assert_not_called()

    def test_https_native_checks_the_game_again_before_contacting_management(self):
        spec = importlib.util.spec_from_file_location('control_https', ROOT / 'scripts/check-control-https.py')
        https = importlib.util.module_from_spec(spec); spec.loader.exec_module(https)
        refusal = windows_firewall.WindowsFirewallLaunchError('Game firewall policy changed.')
        request = Mock()
        folder = ROOT / 'server-package-fixture'
        with patch.object(windows_firewall, 'require_silent_windows_launch', side_effect=refusal) as guard, \
                patch.object(https.socket, 'socket') as socket, patch.object(https.subprocess, 'Popen') as launch:
            with self.assertRaisesRegex(windows_firewall.WindowsFirewallLaunchError, 'Game firewall policy changed'):
                https.verify_native(folder, None, None, {}, None, request, None, None, None)

        guard.assert_called_once_with(folder / 'Runtime/VrCommand.exe')
        request.assert_not_called()
        socket.assert_not_called()
        launch.assert_not_called()

    @unittest.skipUnless(os.name == 'nt', 'Windows Firewall preflight uses PowerShell and Windows executable paths')
    def test_firewall_preflight_cannot_be_overridden_by_inherited_manual_mode(self):
        checker = ROOT / 'scripts/check-windows-firewall-notifications.ps1'
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'VrCommand.exe'
            image.touch()
            fixture = image.with_suffix('.ps1')
            fixture.write_text('''
param($Checker, $Image, [int]$Enabled, [int]$Notifying, [int]$RuleProfiles, [int]$ForceUnattended)
function New-Object {
    param([string]$ComObject)
    if ($ComObject -ne 'HNetCfg.FwPolicy2') { throw 'Unexpected COM request' }
    $rules = @()
    if ($RuleProfiles) {
        $rules += [pscustomobject]@{
            Enabled = $true; Direction = 1; ApplicationName = $Image; Protocol = 256
            Profiles = $RuleProfiles; LocalAddresses = '*'; RemoteAddresses = '*'; InterfaceTypes = 'All'
        }
    }
    $policy = [pscustomobject]@{ CurrentProfileTypes = 2; Enabled = $Enabled; Notifying = $Notifying; Rules = $rules }
    $policy | Add-Member ScriptMethod FirewallEnabled {
        param($mask)
        if ($this.Enabled -eq 8 -and $mask -eq 4) { return $null }
        ($this.Enabled -band $mask) -ne 0
    }
    $policy | Add-Member ScriptMethod NotificationsDisabled {
        param($mask)
        if ($this.Notifying -eq 8 -and $mask -eq 4) { return 'unknown' }
        ($this.Notifying -band $mask) -eq 0
    }
    $policy
}
& $Checker -Executable $Image -Unattended:([bool]$ForceUnattended)
exit $LASTEXITCODE
''', encoding='utf-8')
            power_shell = shutil.which('pwsh') or 'powershell.exe'
            cmd = [power_shell, '-NoProfile', '-NonInteractive', '-File', str(fixture), str(checker), str(image)]
            environment = os.environ.copy()
            environment.pop('VR_COMMAND_UNATTENDED', None)
            cases = [
                ('1', '8', '0', '0', '1', 1),
                ('1', '7', '8', '0', '1', 1),
                (None, '7', '4', '0', '0', 2),
                ('1', '7', '4', '0', '0', 2),
                ('unexpected', '7', '4', '0', '0', 2),
                (None, '7', '4', '7', '0', 2),
                (None, '7', '0', '0', '0', 0),
                (None, '3', '4', '0', '0', 0),
                ('0', '7', '4', '0', '0', 2),
                ('0', '7', '2', '0', '0', 2),
                ('0', '7', '2', '2', '0', 2),
                ('0', '7', '4', '7', '0', 2),
                ('0', '7', '0', '0', '0', 0),
                ('0', '7', '4', '7', '1', 2),
                ('0', '7', '0', '0', '1', 0),
            ]
            for mode, enabled, notifying, rules, force, expected in cases:
                with self.subTest(mode=mode, enabled=enabled, notifying=notifying, rules=rules, force=force):
                    env = environment.copy()
                    if mode is not None:
                        env['VR_COMMAND_UNATTENDED'] = mode
                    result = subprocess.run([*cmd, enabled, notifying, rules, force],
                                            env=env,
                                            capture_output=True, text=True, timeout=15,
                                            creationflags=subprocess.CREATE_NO_WINDOW)
                    self.assertEqual(result.returncode, expected, result.stderr)
                    if expected == 1:
                        self.assertIn('Could not read the Windows Firewall state for Public', result.stderr)
                    if expected == 2:
                        profile = 'Private' if notifying == '2' else 'Public'
                        message = f'notifications are enabled on: {profile}.'
                        self.assertIn(message, result.stderr)

    def test_packaged_result_race_rechecks_the_game_before_calling_the_launcher(self):
        spec = importlib.util.spec_from_file_location('end_race', ROOT / 'scripts/check-desktop-end-race.py')
        race = importlib.util.module_from_spec(spec); spec.loader.exec_module(race)
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory).resolve()
            venue = SimpleNamespace(args=SimpleNamespace(player_package=package), directory=package,
                                    save=Mock(), processes={}, packaged={})
            refusal = windows_firewall.WindowsFirewallLaunchError('Firewall profile changed.')
            with patch.object(race, 'require_silent_windows_launch', side_effect=refusal) as check, \
                    patch.object(race, 'start_checked_windows_process') as launch:
                with self.assertRaises(windows_firewall.WindowsFirewallLaunchError):
                    race.PackagedRaceVenue.launch(venue, 'end-race-late', {})

            check.assert_called_once_with(package / 'VrCommand.exe')
            launch.assert_not_called()
            self.assertEqual(venue.processes, {})

    def test_venue_rechecks_before_each_child_and_stops_on_policy_change(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory).resolve() / 'VrCommand.exe'
            image.touch()
            venue = SimpleNamespace(args=SimpleNamespace(player_exe=image, job_workers=2),
                                    directory=image.parent, save=Mock(), processes={})
            error = windows_firewall.WindowsFirewallLaunchError('Firewall profile changed.')
            with patch.object(m.vm.subprocess, 'CREATE_NO_WINDOW', 0, create=True), \
                    patch.object(windows_firewall, 'require_silent_windows_launch', side_effect=[None, error]) as check, \
                    patch.object(windows_firewall.subprocess, 'Popen') as launch:
                m.vm.Venue.launch(venue, 'server', {})
                with self.assertRaisesRegex(windows_firewall.WindowsFirewallLaunchError, 'Firewall profile changed'):
                    m.vm.Venue.launch(venue, 'client', {})

            self.assertEqual(check.call_args_list, [call(image), call(image)])
            launch.assert_called_once()
            self.assertEqual(launch.call_args.args[0][0], str(image))
            self.assertEqual(launch.call_args.kwargs['executable'], str(image))
            self.assertEqual(venue.processes, {'server': launch.return_value})

    @unittest.skipUnless(os.name == 'nt', 'Windows Firewall preflight uses Windows process options')
    def test_automated_launch_overrides_inherited_interactive_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory).resolve() / 'VrCommand.exe'
            image.touch()
            child_env = {'VR_COMMAND_UNATTENDED': '0', 'SET_BY_CALLER': 'value'}
            with patch.dict(os.environ, {'VR_COMMAND_UNATTENDED': '0'}), \
                    patch.object(windows_firewall.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as check, \
                    patch.object(windows_firewall.subprocess, 'Popen') as launch:
                windows_firewall.start_checked_windows_process([image], env=child_env)

            self.assertEqual(check.call_args.kwargs['env']['VR_COMMAND_UNATTENDED'], '1')
            self.assertEqual(launch.call_args.kwargs['env'], {'VR_COMMAND_UNATTENDED': '1', 'SET_BY_CALLER': 'value'})
            self.assertEqual(child_env['VR_COMMAND_UNATTENDED'], '0')


if __name__ == '__main__': unittest.main()
