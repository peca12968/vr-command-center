import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publication_timing', ROOT / 'scripts/analyze-publication-timing.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class PublicationTimingTests(unittest.TestCase):
    def row(self, seconds, duration=0, point='WorldJournal'):
        return {'seconds': seconds, 'durationSeconds': duration, 'point': point,
            'utcTicks': m.ticks('2026-10-31T12:00:00+00:00') + round(seconds * m.SCALE), 'connection': 'private'}

    def fixtures(self):
        trace = {'schemaVersion': 1, 'source': 'NativeWindowsMonotonicTiming', 'role': 'Server', 'complete': True,
            'truncated': False, 'error': '', 'maximumSeconds': 240, 'capacity': 32768, 'endedSeconds': 3.,
            'rows': [self.row(.1, .01), self.row(1.2, .3), self.row(1.2, .4, 'WorldCapture'), self.row(2.1, .2), self.row(3, 0, 'Stop')]}
        witness = {'version': 1, 'acceptedSequence': 7, 'applicationObserved': False, 'truncated': False, 'totalSamples': 1,
            'responseObservedAtUtc': '2026-10-31T12:00:01+00:00',
            'samples': [{'receivedAtUtc': '2026-10-31T12:00:02+00:00', 'secondsAfterResponse': 1.}]}
        return trace, witness

    def test_nested_groups_stay_separate_and_spans_are_clipped_to_receiver_window(self):
        t, w = self.fixtures(); r = m.correlate(t, w)
        self.assertTrue(r['utcCorrelationUsable']); self.assertAlmostEqual(.3, r['points']['WorldJournal']['windowUnionSeconds'])
        self.assertEqual(2, r['points']['WorldJournal']['windowSamples']); self.assertEqual(3, r['points']['WorldJournal']['totalSamples'])
        self.assertAlmostEqual(.2, r['points']['WorldCapture']['windowUnionSeconds']); self.assertFalse(r['causalRootProven'])
        self.assertNotIn('private', str(r)); self.assertEqual(3, len(r['unmeasured']))

    def test_union_does_not_double_count_overlapping_or_duplicate_utc_intervals(self):
        self.assertEqual(1., m.union_seconds([(0, m.SCALE), (0, m.SCALE), (m.SCALE // 2, m.SCALE), (2, 2)]))

    def test_clock_jump_keeps_native_totals_but_does_not_invent_correlated_durations(self):
        t, w = self.fixtures(); t['rows'][2]['utcTicks'] += m.SCALE
        r = m.correlate(t, w); self.assertFalse(r['utcCorrelationUsable'])
        self.assertIsNone(r['points']['WorldJournal']['windowUnionSeconds']); self.assertEqual(3, r['points']['WorldJournal']['totalSamples'])

    def test_incomplete_window_coverage_is_unknown_not_zero_cost(self):
        t, w = self.fixtures(); t['rows'] = t['rows'][:3]
        r = m.correlate(t, w); self.assertFalse(r['windowCovered']); self.assertIsNone(r['points']['WorldJournal']['windowSamples'])

    def test_bad_role_overflow_lifetime_and_incomplete_trace_fail(self):
        for key, value in [('role', 'Client'), ('complete', False), ('truncated', True), ('capacity', 1), ('endedSeconds', 241), ('error', 'failed')]:
            t, w = self.fixtures(); t[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): m.correlate(t, w)

    def test_truncated_or_empty_receiver_window_and_wrong_boundary_fail(self):
        for key, value in [('truncated', True), ('totalSamples', 2), ('samples', []), ('acceptedSequence', True)]:
            t, w = self.fixtures(); w[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): m.correlate(t, w)

    def test_negative_nan_duration_and_monotonic_rewind_fail(self):
        for key, value in [('durationSeconds', -.1), ('durationSeconds', float('nan')), ('durationSeconds', 5), ('seconds', -.1), ('utcTicks', 0)]:
            t, w = self.fixtures(); t['rows'][1][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): m.correlate(t, w)

    def test_no_world_journal_or_naive_utc_does_not_pass(self):
        t, w = self.fixtures(); t['rows'] = [r for r in t['rows'] if r['point'] != 'WorldJournal']
        with self.assertRaises(ValueError): m.correlate(t, w)
        with self.assertRaises(ValueError): m.ticks('2026-10-31T12:00:00')

    def test_outlier_rows_are_bounded_and_count_keeps_all_observations(self):
        t, w = self.fixtures()
        t['rows'] = [self.row(.01, 0, 'Start')] + [self.row(1 + i / 1000, .1) for i in range(100)] + [self.row(3, 0, 'Stop')]
        r = m.correlate(t, w)['points']['WorldJournal']
        self.assertEqual(100, r['slowWindowCount']); self.assertEqual(64, len(r['earliestSlowWindow'])); self.assertTrue(r['slowWindowTruncated'])


if __name__ == '__main__': unittest.main()
