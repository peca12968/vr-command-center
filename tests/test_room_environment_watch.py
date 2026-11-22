import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/watch-room-environment.ps1'


@unittest.skipUnless(shutil.which('pwsh'), 'PowerShell 7 required')
class EnvironmentWatchTests(unittest.TestCase):
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
