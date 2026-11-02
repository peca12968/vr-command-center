"""Windows-only execution of the real Framework review class, not a GUI test."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]

class PlayerConfigReviewTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Actual Windows Framework compiler required')
    def test_actual_review_rejects_stale_replaced_missing_and_invalid_inputs(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/check-player-config-review.py')],
                                cwd=ROOT, capture_output=True, text=True, timeout=90)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report['complete'])
        self.assertEqual(24, report['checks'])

if __name__ == '__main__': unittest.main()
