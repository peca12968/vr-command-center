import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('startup', ROOT / 'scripts/check-desktop-startup.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


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


if __name__ == '__main__': unittest.main()
