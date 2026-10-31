import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('continuity_comparison', ROOT / 'scripts/compare-desktop-continuity.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class ContinuityComparisonTests(unittest.TestCase):
    def fixture(self):
        stats = [{'playerId': str(i), 'ammoUsed': 0, 'shotsHit': 0, 'kills': 0, 'hitsReceived': 0, 'damageTaken': 0, 'health': 100, 'accuracyPercent': 0} for i in range(25)]
        results = [{**p, 'streamId': 'stream', 'worldSequence': 100, 'throughSequence': 38, 'finalStreamSequence': 5, 'origin': 'Simulation'} for p in stats]
        return {'executionFinished': True, 'complete': True, 'acceptancePassed': True, 'participants': 25, 'headsets': 0, 'hosts': 1, 'networkCapacityAccepted': False,
            'durationSeconds': 900, 'playerBuildReceipt': {'sourceFingerprint': 'a' * 64}, 'clientResults': results,
            'originalConnectionsAfterExpiry': {'allOriginalAdmissions': True, 'participants': 25},
            'sealed': {'world': {'complete': True, 'acceptedSequence': 100, 'header': {'origin': 'Simulation', 'streamId': 'stream', 'roomIds': [1, 2, 3, 4, 5], 'rulesVersion': '0.8.0', 'assetSet': 'player-body-v1'}},
                'statistics': {'pendingTelemetry': False, 'throughSequence': 38, 'players': stats}},
            'replay': {'frames': 100, 'finalTick': 18000, 'runningFrames': 90, 'expectedParticipantObservations': 2250, 'badFrames': 0, 'perPlayerBadFrames': {},
                'finalPacketAndStatisticsMatch': True, 'captureGapsAtLeast1500ms': 0, 'maximumCaptureGapMilliseconds': 114},
            'live': {'runningFrames': 89, 'frames': 90, 'badFrames': 0}, 'sourceAge': {'badSamples': 0, 'maximumSourceAgeSeconds': .2}, 'nativeLogFindings': []}

    def summary(self, report, manifest=False):
        return m.summarize(report, {'errors': [], 'remainingTrackedChildren': []}, manifest)

    def test_absent_legacy_mode_is_unknown_and_explicit_null_is_disabled(self):
        report = self.fixture(); self.assertEqual('NotRecorded', self.summary(report)['diagnosticMode'])
        report['poseContinuity'] = None; self.assertEqual('DisabledByTool', self.summary(report)['diagnosticMode'])
        with self.assertRaises(ValueError): self.summary(report, True)

    def test_sparse_requires_complete_collection_and_expected_program_count(self):
        report = self.fixture(); report['poseContinuity'] = {'complete': True, 'programs': [{} for _ in range(26)]}
        self.assertEqual('Sparse', self.summary(report, True)['diagnosticMode'])
        with self.assertRaises(ValueError): self.summary(report, False)
        report['poseContinuity']['programs'].pop()
        with self.assertRaises(ValueError): self.summary(report, True)

    def test_31_body_failures_cannot_be_hidden_by_matching_final_results(self):
        report = self.fixture(); report.update(complete=False, acceptancePassed=False)
        counts = {str(i): 2 if i < 13 else 1 for i in range(18)}
        report['replay'].update(badFrames=2, perPlayerBadFrames=counts); report['live']['badFrames'] = 2
        row = self.summary(report); self.assertFalse(row['acceptancePassed']); self.assertEqual(31, row['badParticipantRows'])
        report.update(complete=True, acceptancePassed=True)
        with self.assertRaises(ValueError): self.summary(report)

    def test_clock_gap_queue_or_bad_source_age_prevents_a_green_acceptance(self):
        for field in ['capture', 'age', 'queue']:
            report = self.fixture()
            if field == 'capture': report['replay']['captureGapsAtLeast1500ms'] = 1
            elif field == 'age': report['sourceAge']['badSamples'] = 1
            else: report['nativeLogFindings'] = [{'sendQueueFull': 1}]
            with self.subTest(field=field), self.assertRaises(ValueError): self.summary(report)

    def test_unfinished_partial_or_controlled_runs_cannot_join_natural_comparison(self):
        for change in [{'executionFinished': False}, {'fixtureKind': 'ControlledUpstreamLossCalibration'}]:
            report = self.fixture(); report.update(change)
            with self.assertRaises(ValueError): self.summary(report)
        with self.assertRaises(ValueError): m.summarize(self.fixture(), {'errors': ['failure'], 'remainingTrackedChildren': []}, False)

    def test_final_private_results_must_match_ledger_and_world_not_just_count(self):
        for field, value in [('health', 80), ('worldSequence', 99), ('throughSequence', 37), ('streamId', 'foreign')]:
            report = self.fixture(); report['clientResults'][-1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.summary(report)
        report = self.fixture(); report['clientResults'][-1]['playerId'] = '0'
        with self.assertRaises(ValueError): self.summary(report)
        report = self.fixture(); report['clientResults'][-1]['finalStreamSequence'] = 6
        with self.assertRaises(ValueError): self.summary(report)

    def test_same_fingerprint_different_mode_is_not_claimed_as_a_causal_control(self):
        a = self.summary(self.fixture()); a['run'] = 'run-a'; b = copy.deepcopy(a); b.update(run='run-b', diagnosticMode='Sparse')
        report = m.comparison([a, b]); self.assertIn('diagnosticMode', report['recordedConditionDifferences'])
        self.assertFalse(report['causalRootProven']); self.assertFalse(report['networkCapacityAccepted'])
        self.assertIn('NotRecorded', m.markdown(report))

    def test_version_difference_and_duplicate_runs_are_explicit(self):
        a = self.summary(self.fixture()); a['run'] = 'run-a'; b = copy.deepcopy(a); b.update(run='run-b', sourceFingerprint='b' * 64)
        self.assertIn('sourceFingerprint', m.comparison([a, b])['recordedConditionDifferences'])
        with self.assertRaises(ValueError): m.comparison([a, a])


if __name__ == '__main__': unittest.main()
