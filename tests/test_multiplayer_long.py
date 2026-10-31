"""All-player continuity and evidence boundaries; no simulated native results."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('multiplayer_long', ROOT / 'scripts/check-desktop-multiplayer-long.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class MultiplayerContinuityTests(unittest.TestCase):
    def setUp(self):
        self.players = [{'id': str(i), 'admissionId': 'epoch-' + str(i), 'roomId': i // 5 + 1, 'seat': i % 5} for i in range(25)]
        self.health = {p['id']: (80 if p['seat'] == 0 else 100) for p in self.players}

    def row(self, sequence=1, tick=1, elapsed=100):
        return {'packet': {'sequence': sequence, 'observedSequence': 31, 'elapsedMilliseconds': elapsed,
            'frame': {'phase': 'Running', 'tick': tick, 'players': [{'id': p['id'], 'roomId': p['roomId'], 'health': self.health[p['id']],
                'connected': True, 'rig': {'kind': 'Simulated'}} for p in self.players]}}}

    def test_every_player_is_checked_including_last_not_only_first(self):
        row = self.row(); self.assertEqual([], m.roster_faults(row, self.players, 31, self.health))
        row['packet']['frame']['players'][-1]['connected'] = False
        faults = m.roster_faults(row, self.players, 31, self.health)
        self.assertEqual([{'playerId': '24', 'reason': 'inactiveBody'}], faults)

    def test_original_room_health_and_rig_each_have_a_fence(self):
        for key, value, reason in [('roomId', 1, 'wrongRoom'), ('health', 80, 'changedHealth'), ('rig', {'kind': 'None'}, 'inactiveBody')]:
            row = self.row(); row['packet']['frame']['players'][-1][key] = value
            self.assertEqual(reason, m.roster_faults(row, self.players, 31, self.health)[0]['reason'])

    def test_missing_foreign_and_duplicate_rosters_fail(self):
        for action in ['missing', 'foreign', 'duplicate']:
            row = self.row(); actual = row['packet']['frame']['players']
            if action == 'missing': actual.pop()
            if action == 'foreign': actual[-1]['id'] = 'foreign'
            if action == 'duplicate': actual.append(copy.deepcopy(actual[0]))
            self.assertIn('rosterMismatch', [f['reason'] for f in m.roster_faults(row, self.players, 31, self.health)])

    def test_health_before_policy_and_normal_ended_disconnect_are_not_false_faults(self):
        row = self.row(); row['packet']['observedSequence'] = 30; row['packet']['frame']['players'][0]['health'] = 100
        self.assertEqual([], m.roster_faults(row, self.players, 31, self.health))
        row['packet']['frame']['phase'] = 'Ended'; row['packet']['frame']['players'][0]['connected'] = False
        self.assertEqual([], m.roster_faults(row, self.players, 31, self.health))

    def test_unplanned_pause_counts_as_fault_even_without_running_phase(self):
        audit = m.Continuity(self.players, 31, self.health); row = self.row(); row['packet']['frame']['phase'] = 'Paused'; audit.observe(row)
        self.assertEqual(1, audit.result()['badFrames']); self.assertEqual({'unexpectedSuspension': 1}, audit.result()['reasonCounts'])

    def test_live_skips_are_counted_and_full_replay_cannot_skip(self):
        live = m.Continuity(self.players, 31, self.health); live.observe(self.row()); live.observe(self.row(3, 3, 300))
        self.assertEqual(1, live.result()['skippedLiveSequences'])
        replay = m.Continuity(self.players, 31, self.health, replay=True); replay.observe(self.row())
        with self.assertRaises(ValueError): replay.observe(self.row(3, 3, 300))

    def test_every_saved_gap_uses_original_1500ms_boundary(self):
        for gap, passed in [(1499, True), (1500, False)]:
            audit = m.Continuity(self.players, 31, self.health, replay=True); audit.observe(self.row()); audit.observe(self.row(2, 2, 100 + gap))
            self.assertEqual(passed, audit.result()['passed'])

    def test_sample_bound_never_discards_bad_frame_or_player_counts(self):
        audit = m.Continuity(self.players, 31, self.health)
        for index in range(1, 251):
            row = self.row(index, index, index * 100); row['packet']['frame']['players'][-1]['connected'] = False; audit.observe(row)
        result = audit.result(); self.assertEqual(200, len(result['faultSamples'])); self.assertEqual(250, result['badFrames'])
        self.assertEqual({'24': 250}, result['perPlayerBadFrames']); self.assertEqual(6250, result['expectedParticipantObservations']); self.assertFalse(result['passed'])

    def test_admissions_are_an_exact_roster_not_a_subset_or_classification(self):
        self.assertTrue(m.same_admissions(list(reversed(self.players)), self.players))
        for field, value in [('admissionId', 'new-epoch'), ('seat', 99), ('roomId', 99)]:
            changed = copy.deepcopy(self.players); changed[-1][field] = value
            self.assertFalse(m.same_admissions(changed, self.players))
        self.assertFalse(m.same_admissions(self.players[:-1], self.players))

    def test_clock_or_sequence_rewind_and_deadline_overrun_are_rejected(self):
        for sequence, tick, elapsed in [(1, 2, 200), (2, 0, 200), (2, 18001, 200), (2, 2, 0)]:
            audit = m.Continuity(self.players, 31, self.health); audit.observe(self.row())
            with self.assertRaises(ValueError): audit.observe(self.row(sequence, tick, elapsed))

    def test_recovery_and_subthreshold_capture_gap_cannot_hide_31_inactive_player_rows(self):
        # Native counterexample shape: a 497ms capture gap, two bad frames
        # (13 / 18 bodies), then full recovery. The first player stays healthy.
        audit = m.Continuity(self.players, 31, self.health, replay=True)
        for sequence, tick, elapsed, inactive in [(1, 1, 100, 0), (2, 2, 597, 0), (3, 8, 700, 13), (4, 10, 800, 18), (5, 13, 906, 0)]:
            row = self.row(sequence, tick, elapsed)
            if inactive:
                for player in row['packet']['frame']['players'][-inactive:]: player['connected'] = False
            audit.observe(row)
        result = audit.result()
        self.assertEqual(0, result['captureGapsAtLeast1500ms']); self.assertEqual(497, result['maximumCaptureGapMilliseconds'])
        self.assertEqual(2, result['badFrames']); self.assertEqual({'inactiveBody': 31}, result['reasonCounts'])
        self.assertFalse(result['passed']); self.assertTrue(audit.last['packet']['frame']['players'][-1]['connected'])


if __name__ == '__main__': unittest.main()
