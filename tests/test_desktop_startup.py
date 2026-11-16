import importlib.util
import os
from pathlib import Path
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
    @unittest.skipUnless(os.name == 'nt', 'Windows Firewall preflight uses PowerShell and Windows executable paths')
    def test_firewall_preflight_defaults_to_unattended(self):
        checker = ROOT / 'scripts/check-windows-firewall-notifications.ps1'
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'VrCommand.exe'
            image.touch()
            fixture = image.with_suffix('.ps1')
            fixture.write_text('''
param($Checker, $Image, [int]$Enabled, [int]$Notifying, [int]$RuleProfiles)
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
    $policy | Add-Member ScriptMethod FirewallEnabled { param($mask) ($this.Enabled -band $mask) -ne 0 }
    $policy | Add-Member ScriptMethod NotificationsDisabled { param($mask) ($this.Notifying -band $mask) -eq 0 }
    $policy
}
& $Checker -Executable $Image
exit $LASTEXITCODE
''', encoding='utf-8')
            power_shell = shutil.which('pwsh') or 'powershell.exe'
            cmd = [power_shell, '-NoProfile', '-NonInteractive', '-File', str(fixture), str(checker), str(image)]
            environment = os.environ.copy()
            environment.pop('VR_COMMAND_UNATTENDED', None)
            cases = [
                (None, '7', '4', '0', 2),
                ('1', '7', '4', '0', 2),
                ('unexpected', '7', '4', '0', 2),
                (None, '7', '4', '7', 2),
                (None, '7', '0', '0', 0),
                (None, '3', '4', '0', 0),
                ('0', '7', '4', '0', 0),
                ('0', '7', '2', '0', 2),
                ('0', '7', '2', '2', 0),
            ]
            for mode, enabled, notifying, rules, expected in cases:
                with self.subTest(mode=mode, enabled=enabled, notifying=notifying, rules=rules):
                    env = environment.copy()
                    if mode is not None:
                        env['VR_COMMAND_UNATTENDED'] = mode
                    result = subprocess.run([*cmd, enabled, notifying, rules],
                                            env=env,
                                            capture_output=True, text=True, timeout=15,
                                            creationflags=subprocess.CREATE_NO_WINDOW)
                    self.assertEqual(result.returncode, expected, result.stderr)
                    if expected == 2:
                        message = ('may prompt on the Private profile.' if mode == '0'
                                   else 'notifications are enabled on: Public.')
                        self.assertIn(message, result.stderr)

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
