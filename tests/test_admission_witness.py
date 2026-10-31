import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('admission_window', ROOT / 'scripts/admission_witness.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class AdmissionWitnessTests(unittest.TestCase):
    def packet(self, observed=7, phase='Running', tick=1, suspended=False):
        return {'sequence': 119, 'observedSequence': observed, 'elapsedMilliseconds': 17261, 'suspended': suspended,
            'frame': {'phase': phase, 'tick': tick, 'players': [{'id': 'private'}]}, 'joinTicket': 'private'}

    def test_preparing_tick_zero_is_not_application_even_at_current_sequence(self):
        w = m.BeginWitness(7); w.observe(self.packet(7, 'Preparing', 0)); self.assertFalse(w.applied)
        self.assertEqual({'Preparing': 1}, w.snapshot()['phaseCounts'])

    def test_older_running_suspended_and_zero_tick_do_not_close_window(self):
        for packet in [self.packet(6), self.packet(tick=0), self.packet(suspended=True), self.packet(phase='Paused')]:
            w = m.BeginWitness(7); w.observe(packet); self.assertFalse(w.applied)

    def test_first_applied_is_retained_and_later_snapshots_do_not_replace_it(self):
        w = m.BeginWitness(7); w.observe(self.packet(6)); w.observe(self.packet()); w.observe(self.packet(observed=8, tick=50))
        r = w.snapshot(); self.assertTrue(r['applicationObserved']); self.assertEqual(2, r['totalSamples']); self.assertEqual(1, r['firstApplied']['tick'])

    def test_unknown_capture_time_is_unknown_not_zero_age(self):
        for missing in [None, '']:
            w = m.BeginWitness(7); w.observe(self.packet(), missing); self.assertIsNone(w.snapshot()['firstApplied']['sourceAgeSeconds'])

    def test_capture_timestamp_uses_header_plus_elapsed_not_receive_time(self):
        w = m.BeginWitness(7); w.observe(self.packet(), '2026-10-31T12:00:00+00:00')
        self.assertEqual('2026-10-31T12:00:17.261000+00:00', w.snapshot()['firstApplied']['capturedAtUtc'])

    def test_sample_limit_retains_earliest_rows_and_all_counts_and_first_application(self):
        w = m.BeginWitness(7, limit=2)
        for _ in range(3): w.observe(self.packet(6, 'Preparing', 0))
        w.observe(self.packet()); r = w.snapshot()
        self.assertTrue(r['truncated']); self.assertEqual(2, len(r['samples'])); self.assertEqual(4, r['totalSamples']); self.assertEqual({'Preparing': 3, 'Running': 1}, r['phaseCounts'])
        self.assertIsNotNone(r['firstApplied'])

    def test_metadata_does_not_contain_actors_credentials_or_raw_frame(self):
        w = m.BeginWitness(7); w.observe(self.packet()); row = w.snapshot()['firstApplied']
        self.assertFalse({'frame', 'players', 'joinTicket'} & set(row)); self.assertNotIn('private', str(w.snapshot()))

    def test_invalid_boundaries_fail_instead_of_creating_empty_evidence(self):
        for sequence in [0, -1, True, '7']:
            with self.assertRaises(ValueError): m.BeginWitness(sequence)
        for limit in [0, 257, True]:
            with self.assertRaises(ValueError): m.BeginWitness(7, limit=limit)


if __name__ == '__main__': unittest.main()
