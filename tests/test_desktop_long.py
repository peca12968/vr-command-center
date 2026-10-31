import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('desktop_long', Path(__file__).resolve().parents[1] / 'scripts/check-desktop-long.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class LongContinuityTests(unittest.TestCase):
    def row(self):
        return {'packet': {'observedSequence': 9, 'frame': {'phase': 'Running', 'players': [{'id': 'own', 'connected': True, 'health': 80, 'rig': {'kind': 'Simulated'}}]}}}
    def test_alive_original_body_and_stable_damage_are_required(self):
        row = self.row(); self.assertIsNone(m.active_fault(row, 'own', 9, 80))
        for field, value in [('connected', False), ('health', 100)]:
            broken = copy.deepcopy(row); broken['packet']['frame']['players'][0][field] = value
            self.assertIsNotNone(m.active_fault(broken, 'own', 9, 80))
        row['packet']['frame']['players'][0]['rig']['kind'] = 'None'; self.assertEqual('inactiveBody', m.active_fault(row, 'own', 9, 80))
    def test_prior_damage_and_ended_disconnect_are_not_false_running_failures(self):
        row = self.row(); row['packet']['observedSequence'] = 8; row['packet']['frame']['players'][0]['health'] = 100
        self.assertIsNone(m.active_fault(row, 'own', 9, 80))
        row['packet']['frame']['phase'] = 'Ended'; row['packet']['frame']['players'][0]['connected'] = False
        self.assertIsNone(m.active_fault(row, 'own', 9, 80))
    def test_unplanned_pause_or_missing_original_player_fails_continuity(self):
        row = self.row(); row['packet']['frame']['phase'] = 'Paused'; self.assertEqual('unexpectedSuspension', m.active_fault(row, 'own', 9, 80))
        row = self.row(); row['packet']['frame']['players'][0]['id'] = 'other'; self.assertEqual('inactiveBody', m.active_fault(row, 'own', 9, 80))


if __name__ == '__main__': unittest.main()
