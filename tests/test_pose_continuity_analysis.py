import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sparse_analysis', ROOT / 'scripts/analyze-pose-continuity.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
BASE = 639290000000000000


class SparseAnalysisTests(unittest.TestCase):
    def fixture(self):
        before = {'threadId': 42, 'creationTime': 100, 'kernel100ns': 10, 'user100ns': 20, 'cycles': 9007199254740993,
            'fromSeconds': 1, 'toSeconds': 1.001, 'fromUtcTicks': BASE + 10000000, 'toUtcTicks': BASE + 10010000}
        after = {**before, 'kernel100ns': 100010, 'user100ns': 200020, 'cycles': before['cycles'] + 1234567,
            'fromSeconds': 1.7, 'toSeconds': 1.701, 'fromUtcTicks': BASE + 17000000, 'toUtcTicks': BASE + 17010000}
        return {'version': 1, 'source': 'NativeWindowsSparsePoseContinuity', 'role': 'Client', 'complete': True, 'truncated': False, 'error': '',
            'stopReason': 'Explicit local diagnostic stop', 'maximumSeconds': 1200, 'streamCapacity': 256, 'gapCapacity': 4096, 'endedSeconds': 3,
            'mainThreadSamples': 50, 'mainThreadId': 42, 'maximumClockStepSeconds': 0,
            'streams': [{'point': 'PoseSend', 'connection': 7, 'source': 1, 'count': 2, 'firstSeconds': 1, 'lastSeconds': 1.7,
                'firstUtcTicks': BASE + 10000000, 'lastUtcTicks': BASE + 17000000, 'maximumGapSeconds': .7, 'maximumDurationSeconds': 0}],
            'gaps': [{'point': 'PoseSend', 'connection': 7, 'source': 1, 'fromSeconds': 1, 'toSeconds': 1.7, 'fromFrame': 10, 'toFrame': 20,
                'fromUtcTicks': BASE + 10000000, 'toUtcTicks': BASE + 17000000, 'durationSeconds': 0}],
            'bodies': [], 'threadWindows': [{'before': before, 'after': after}], 'playerLoop': None}

    def test_thread_cpu_and_cycles_are_not_wall_time_or_whole_process_values(self):
        result = m.validate(self.fixture(), 'Client', False); window = result['mainThreadWindows'][0]
        self.assertTrue(result['clockJoinValid']); self.assertAlmostEqual(.03, window['mainThreadCpuSeconds'])
        self.assertAlmostEqual(.701, window['wallSecondsIncludingQueries']); self.assertEqual(1234567, window['mainThreadCycleDelta'])

    def test_partial_truncated_wrong_role_and_changed_bounds_are_rejected(self):
        for field, value in [('complete', False), ('truncated', True), ('role', 'Server'), ('maximumSeconds', 240), ('streamCapacity', 999), ('error', 'failure')]:
            report = self.fixture(); report[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): m.validate(report, 'Client', False)

    def test_clock_step_disables_join_without_inventing_a_cause(self):
        report = self.fixture(); report['maximumClockStepSeconds'] = .05
        self.assertFalse(m.validate(report, 'Client', False)['clockJoinValid'])

    def test_thread_identity_reuse_and_counter_rewind_are_rejected(self):
        for key, value in [('threadId', 43), ('creationTime', 101), ('cycles', 1), ('user100ns', 1)]:
            report = self.fixture(); report['threadWindows'][0]['after'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): m.validate(report, 'Client', False)

    def test_negative_query_duration_and_nonfinite_values_are_rejected(self):
        report = self.fixture(); report['threadWindows'][0]['after']['toSeconds'] = 1
        with self.assertRaises(ValueError): m.validate(report, 'Client', False)
        report = self.fixture(); report['streams'][0]['maximumGapSeconds'] = float('nan')
        with self.assertRaises(ValueError): m.validate(report, 'Client', False)

    def test_duplicate_stream_or_gap_outside_its_aggregate_is_rejected(self):
        report = self.fixture(); report['streams'].append(copy.deepcopy(report['streams'][0]))
        with self.assertRaises(ValueError): m.validate(report, 'Client', False)
        report = self.fixture(); report['gaps'][0]['toSeconds'] = 2
        with self.assertRaises(ValueError): m.validate(report, 'Client', False)

    def test_actual_jsonutility_empty_initialized_loop_is_only_absence_shape(self):
        report = self.fixture(); report['playerLoop'] = {'version': 1, 'capacity': 4096, 'maximumNodes': 512, 'source': 'NativeWindowsPlayerLoopBoundaries',
            'complete': False, 'truncated': False, 'detached': False, 'callbacks': 0, 'firstUtcTicks': 0, 'lastUtcTicks': 0,
            'firstSeconds': 0, 'lastSeconds': 0, 'maximumClockStepSeconds': 0, 'boundaries': [], 'gaps': []}
        self.assertTrue(m.validate(report, 'Client', False)['clockJoinValid'])
        report['playerLoop']['gaps'].append({'unobserved': True})
        with self.assertRaises(ValueError): m.validate(report, 'Client', False)

    def test_unknown_age_is_exactly_minus_one_and_boolean_ids_are_not_integers(self):
        report = self.fixture(); report['bodies'] = [{'connection': 7, 'frame': 11, 'utcTicks': BASE, 'seconds': 1, 'poseAgeSeconds': -.5, 'connected': False}]
        with self.assertRaises(ValueError): m.validate(report, 'Client', False)
        report = self.fixture(); report['streams'][0]['connection'] = True
        with self.assertRaises(ValueError): m.validate(report, 'Client', False)


if __name__ == '__main__': unittest.main()
