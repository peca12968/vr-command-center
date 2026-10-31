import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('journal_stages', ROOT / 'scripts/analyze-journal-stages.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class JournalStageTests(unittest.TestCase):
    def row(self, stage, operation, thread, start, end, succeeded=True):
        base = m.publication.ticks('2026-10-31T12:00:00+00:00')
        return {'stage': stage, 'operation': operation, 'managedThreadId': thread, 'sequence': 0, 'succeeded': succeeded,
            'startedTimestamp': 1000000 + round(start * 1000000), 'endedTimestamp': 1000000 + round(end * 1000000),
            'startedUtcTicks': base + round(start * m.publication.SCALE), 'endedUtcTicks': base + round(end * m.publication.SCALE)}

    def fixtures(self):
        base = m.publication.ticks('2026-10-31T12:00:00+00:00')
        report = {'version': 1, 'source': 'NativeWindowsWorldJournalStages', 'role': 'Server', 'complete': True, 'truncated': False,
            'inFlight': 0, 'error': '', 'maximumSeconds': 90, 'capacity': 32768, 'frequency': 1000000, 'mainManagedThreadId': 1,
            'startedTimestamp': 1000000, 'stoppedTimestamp': 4000000, 'startedUtcTicks': base, 'stoppedUtcTicks': base + 3 * m.publication.SCALE,
            'rows': [self.row(0, 6, 1, 1.2, 1.8), self.row(2, 2, 2, 1.2, 1.7), self.row(2, 1, 1, 1.8, 2.2)]}
        parent = {'windowStartUtc': '2026-10-31T12:00:01+00:00', 'windowEndUtc': '2026-10-31T12:00:02+00:00', 'utcCorrelationUsable': True}
        return report, parent

    def test_state_read_wait_and_background_ack_flush_intersect_but_are_not_added(self):
        r, p = self.fixtures(); a = m.correlate(r, p)
        self.assertAlmostEqual(.6, a['mainGateEnterWindowSeconds']); self.assertAlmostEqual(.5, a['backgroundAckFlushWindowSeconds'])
        self.assertAlmostEqual(.5, a['mainWaitOverlapsBackgroundAckFlushSeconds']); self.assertAlmostEqual(.2, a['mainFrameFlushWindowSeconds'])
        self.assertFalse(a['causalRootProven']); self.assertNotIn('rows', str(a['groups']))

    def test_managed_thread_identity_is_used_not_the_operation_name(self):
        r, p = self.fixtures(); r['rows'][1]['managedThreadId'] = 1
        a = m.correlate(r, p); self.assertEqual(0, a['backgroundAckFlushWindowSeconds']); self.assertEqual(0, a['mainWaitOverlapsBackgroundAckFlushSeconds'])

    def test_completion_order_does_not_need_to_be_timestamp_order(self):
        r, p = self.fixtures(); a = m.correlate(r, p); r['rows'].reverse()
        self.assertEqual(a, m.correlate(r, p))

    def test_utc_jump_disables_window_values_while_preserving_native_counts(self):
        r, p = self.fixtures(); r['rows'][0]['endedUtcTicks'] += m.publication.SCALE
        a = m.correlate(r, p); self.assertFalse(a['utcCorrelationUsable']); self.assertIsNone(a['mainGateEnterWindowSeconds'])
        self.assertEqual(1, a['groups']['Main/LastSequence/GateEnter']['count'])

    def test_parent_unknown_and_lack_of_coverage_do_not_become_zero_cost(self):
        r, p = self.fixtures(); p['utcCorrelationUsable'] = False
        self.assertIsNone(m.correlate(r, p)['mainFrameFlushWindowSeconds'])
        r, p = self.fixtures(); p['windowEndUtc'] = '2026-10-31T12:00:04+00:00'
        self.assertFalse(m.correlate(r, p)['windowCovered'])

    def test_inflight_truncation_wrong_capacity_and_incomplete_reports_fail(self):
        for key, value in [('inFlight', 1), ('truncated', True), ('capacity', 1), ('complete', False), ('role', 'Client'), ('frequency', 0)]:
            r, p = self.fixtures(); r[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): m.correlate(r, p)

    def test_bad_integer_operation_duration_and_outside_anchor_fail(self):
        for key, value in [('managedThreadId', True), ('operation', 12), ('stage', 3), ('sequence', -1), ('startedTimestamp', 0), ('endedTimestamp', 1)]:
            r, p = self.fixtures(); r['rows'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): m.correlate(r, p)

    def test_failed_write_does_not_invent_a_flush_or_game_success(self):
        r, p = self.fixtures(); r['rows'] = [self.row(1, 1, 1, 1.2, 1.3, False)]
        a = m.correlate(r, p); self.assertEqual(1, a['failedOperations']); self.assertEqual(0, a['mainFrameFlushWindowSeconds'])
        self.assertEqual(1, a['groups']['Main/Frame/Write']['failed'])

    def test_overlap_uses_union_and_handles_disjoint_or_duplicate_intervals(self):
        scale = m.publication.SCALE
        self.assertEqual(.5, m.intersection_seconds([(0, scale), (0, scale)], [(scale // 2, scale)]))
        self.assertEqual(0, m.intersection_seconds([(0, 1)], [(2, 3)]))

    def test_quantized_utc_pair_does_not_erase_a_stopwatch_measured_call(self):
        r, p = self.fixtures(); row = self.row(1, 1, 1, 1.5, 1.5003); row['startedUtcTicks'] = row['endedUtcTicks']
        r['rows'] = [row]; a = m.correlate(r, p)['groups']['Main/Frame/Write']
        self.assertEqual(1, a['windowSamples']); self.assertAlmostEqual(.0003, a['windowUnionSeconds'])


if __name__ == '__main__': unittest.main()
