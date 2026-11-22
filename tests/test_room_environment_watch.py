import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/watch-room-environment.ps1'


@unittest.skipUnless(shutil.which('pwsh'), 'PowerShell 7 required')
class EnvironmentWatchTests(unittest.TestCase):
    def test_venue_publishes_five_rooms_together_and_recovers_from_bad_snapshots(self):
        command = r"""
$script:sample = 0
function Start-Sleep {}
function Invoke-RestMethod {
    param($Uri,$Headers)
    if ($Uri.AbsolutePath -cne '/api/venue/hardware-environment' -or $Headers.Authorization -cne 'Bearer venue-test') {
        throw 'Unexpected request'
    }
    $script:sample++
    if ($script:sample -eq 4) { throw 'connection dropped' }
    $rows = @(foreach ($room in 1..5) {
        $id = if ($script:sample -ge 7) { "12345678-0000-4444-8888-00000000000$room" } else { '12345678-0000-4444-8888-000000000009' }
        $s = [pscustomobject]@{ version=1;roomId=$room;sessionId=$id;throughSequence=8;phaseSinceSequence=4;environmentSinceSequence=6
            state='Running';environment=[pscustomobject]@{mode='VR';weather='Storm';timeOfDay='Night';lightning=$true} }
        switch ($script:sample) {
            2 { if ($room -eq 5) { $s.roomId = 1 } else { $s.throughSequence=99 } }
            3 { $s.throughSequence=9; $s.state='Paused'; $s.phaseSinceSequence=9; $s.environment=$null }
            5 { $s.throughSequence=8 }
            6 { $s.throughSequence=12; $s.phaseSinceSequence=10; if ($room -eq 5) { $s.environment.weather='Fog' } }
            { $_ -ge 7 } { $s.throughSequence=1; $s.phaseSinceSequence=1; $s.environmentSinceSequence=1
                $s.state='Preparing'; $s.environment=$null; if($room -eq 5) { $s=$null } }
        }
        [pscustomobject]@{version=1;roomId=$room;session=$s}
    })
    $time = if ($script:sample -eq 7) { [datetime]::new(2026,11,22) } else { '2026-11-22T01:00:00.1234567Z' }
    [pscustomobject]@{version=1;checkedAtUtc=$time;rooms=$rows}
}
& $env:VRC_WATCH_TEST -ManagementApi 'http://127.0.0.1' -AllRooms -Samples 8
"""
        result = subprocess.run(['pwsh', '-NoProfile', '-NonInteractive', '-Command', command],
                                capture_output=True, text=True, timeout=15, env={**os.environ, 'VRC_WATCH_TEST': str(SCRIPT),
                                'VR_COMMAND_ROOM_KEY': 'wrong-role-test', 'VR_COMMAND_MASTER_KEY': 'venue-test'})
        self.assertEqual(0, result.returncode, result.stderr)
        pages = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([None, 'invalid-snapshot', None, 'management-unreachable', 'invalid-snapshot',
                          'invalid-snapshot', 'invalid-snapshot', None], [p['reason'] for p in pages])
        for page in pages:
            self.assertEqual(list(range(1, 6)), [r['roomId'] for r in page['rooms']])
            if page['reason']:
                self.assertEqual('Unavailable', page['status'])
                self.assertIsNone(page['checkedAtUtc'])
                self.assertTrue(all(r['status'] == 'Unavailable' and r['session'] is None for r in page['rooms']))
            else:
                self.assertEqual('Available', page['status'])
                self.assertEqual('2026-11-22T01:00:00.1234567+00:00', page['checkedAtUtc'])
        self.assertTrue(all(r['session']['environment']['lightning'] is True for r in pages[0]['rooms']))
        self.assertTrue(all(r['status'] == 'Paused' and r['session']['environment'] is None for r in pages[2]['rooms']))
        self.assertEqual(['Preparing'] * 4 + ['Idle'], [r['status'] for r in pages[-1]['rooms']])
        self.assertNotIn('venue-test', result.stdout + result.stderr)

    def test_bad_samples_clear_state_and_a_new_session_can_restart_at_sequence_one(self):
        command = r"""
$script:sample = 0
function Start-Sleep {}
function Invoke-RestMethod {
    $script:sample++
    $climate = [pscustomobject]@{ mode='VR'; weather='Storm'; timeOfDay='Night'; lightning=$true }
    $session = [pscustomobject]@{ version=1; roomId=4; sessionId='12345678-0000-4444-8888-000000000001'
        state='Running'; throughSequence=18; phaseSinceSequence=5; environmentSinceSequence=7; environment=$climate }
    switch ($script:sample) {
        2 { $session.roomId = 1 }
        3 { $climate.lightning = 'false' }
        4 { $session.phaseSinceSequence = 19 }
        5 { $session.state = 'Paused' }
        6 { throw 'private diagnostic data' }
        7 { $session.sessionId = '12345678-0000-4444-8888-000000000002'; $session.state='Preparing'
            $session.throughSequence=1; $session.phaseSinceSequence=1; $session.environmentSinceSequence=1; $session.environment=$null }
        8 { $session = $null }
    }
    return [pscustomobject]@{version=1; roomId=4; session=$session}
}
& $env:VRC_WATCH_TEST -ManagementApi 'http://127.0.0.1' -RoomId 4 -Samples 8
"""
        result = subprocess.run(['pwsh', '-NoProfile', '-NonInteractive', '-Command', command],
                                capture_output=True, text=True, timeout=15,
                                env={**os.environ, 'VRC_WATCH_TEST': str(SCRIPT), 'VR_COMMAND_ROOM_KEY': 'test-room-key'})
        self.assertEqual(0, result.returncode, result.stderr)
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(['Running', *(['Unavailable'] * 5), 'Preparing', 'Idle'], [row['status'] for row in rows])
        self.assertEqual([None] * 5, [row['session'] for row in rows[1:6]])
        self.assertEqual(1, rows[6]['session']['throughSequence'])
        self.assertIsNone(rows[7]['session'])
        self.assertNotIn('private diagnostic data', result.stdout + result.stderr)
