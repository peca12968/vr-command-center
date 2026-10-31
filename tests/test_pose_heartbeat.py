"""Synthetic clock / coverage joins plus one real timer process; no Unity claim."""
import copy
from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('heartbeat_analysis', ROOT / 'scripts/analyze-pose-input.py')
analysis = importlib.util.module_from_spec(spec); spec.loader.exec_module(analysis)


class HeartbeatTests(unittest.TestCase):
    def fixture(self):
        epoch = 1_793_491_200_000_000_000
        report = {'schemaVersion':1, 'source':'IndependentPythonWakeTiming', 'complete':True, 'truncated':False,
            'sampleSeconds':.01, 'maximumGapRows':4096, 'startedCounterNs':0, 'endedCounterNs':3_000_000_000,
            'durationNs':3_000_000_000, 'wakes':200, 'maximumGapNs':600_000_000, 'maximumClockStepNs':1000,
            'gaps':[{'fromCounterNs':950_000_000, 'toCounterNs':1_550_000_000,
                     'fromUnixNs':epoch+950_000_000, 'toUnixNs':epoch+1_550_000_000, 'durationNs':600_000_000, 'processCpuNs':1000}],
            'anchors':[{'counterNs':index*1_000_000_000, 'unixNs':epoch+index*1_000_000_000} for index in range(4)]}
        base = analysis.UNIX_TICKS + epoch // 100
        shared = [{'fromUtcTicks':base+9_000_000, 'toUtcTicks':base+15_000_000}]
        return report, shared, {'observation':(base,base+30_000_000)}

    def test_known_gap_intersection_preserves_common_time_and_coverage(self):
        report, shared, periods = self.fixture(); value = analysis.heartbeat_analysis(report,shared,periods,True)
        self.assertAlmostEqual(value['nativeTripleGapIntersections'][0]['seconds'], .55)
        self.assertEqual(value['fullyCoveredNativeTripleGaps'],1); self.assertEqual(value['phaseLongGaps']['observation'],1)

    def test_clean_timer_does_not_manufacture_a_shared_pause(self):
        report, shared, periods = self.fixture(); report.update(gaps=[], maximumGapNs=15_000_000)
        value = analysis.heartbeat_analysis(report,shared,periods,True)
        self.assertEqual(value['nativeTripleGapIntersections'],[]); self.assertEqual(value['fullyCoveredNativeTripleGaps'],1)
        self.assertAlmostEqual(value['maximumWakeGapSeconds'], .015)

    def test_missing_timer_coverage_is_explicit(self):
        report, shared, periods = self.fixture()
        report.update(startedUnixNs=report['anchors'][2]['unixNs'], endedUnixNs=report['anchors'][-1]['unixNs'],
                      startedCounterNs=2_000_000_000, durationNs=1_000_000_000, anchors=report['anchors'][2:], gaps=[], maximumGapNs=15_000_000)
        value = analysis.heartbeat_analysis(report,shared,periods,True)
        self.assertEqual(value['fullyCoveredNativeTripleGaps'],0); self.assertEqual(value['uncoveredNativeTripleGaps'],1)

    def test_bad_heartbeat_clock_or_native_clock_withholds_join(self):
        report, shared, periods = self.fixture()
        for native_valid in (False, True):
            candidate=copy.deepcopy(report)
            if native_valid: candidate['maximumClockStepNs']=100_000_000
            value=analysis.heartbeat_analysis(candidate,shared,periods,native_valid)
            self.assertFalse(value['clockJoinValid']); self.assertIsNone(value['nativeTripleGapIntersections']); self.assertIsNone(value['fullyCoveredNativeTripleGaps'])

    def test_clock_anchor_discontinuity_cannot_be_hidden_by_summary(self):
        report, shared, periods = self.fixture(); report['anchors'][2]['unixNs'] += 200_000_000
        self.assertFalse(analysis.heartbeat_analysis(report,shared,periods,True)['clockJoinValid'])
        report, shared, periods = self.fixture()
        report.update(startedUnixNs=report['anchors'][0]['unixNs']+100_000_000, endedUnixNs=report['anchors'][-1]['unixNs'])
        self.assertFalse(analysis.heartbeat_analysis(report,shared,periods,True)['clockJoinValid'])

    def test_incomplete_or_inconsistent_gap_is_rejected(self):
        report, shared, periods = self.fixture()
        candidate=copy.deepcopy(report);candidate['complete']=False
        with self.assertRaises(ValueError): analysis.heartbeat_analysis(candidate,shared,periods,True)
        report['gaps'][0]['durationNs'] += 1
        with self.assertRaises(ValueError): analysis.heartbeat_analysis(report,shared,periods,True)

    def test_real_process_writes_only_after_explicit_finish(self):
        with tempfile.TemporaryDirectory(prefix='vr-heartbeat-') as temporary:
            root=Path(temporary).resolve();self.assertEqual(root.parent,Path(tempfile.gettempdir()).resolve())
            self.assertTrue(root.name.startswith('vr-heartbeat-'))
            path=root/'probe'; child=subprocess.Popen([sys.executable,str(ROOT/'scripts/pose-heartbeat.py'),'--directory',str(path)])
            try:
                deadline=time.monotonic()+10
                while not path.exists() and child.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue(path.exists());time.sleep(.15);self.assertFalse((path/'report.json').exists())
                (path/'finish.request').write_text('finish');self.assertEqual(child.wait(timeout=10),0)
                report=json.loads((path/'report.json').read_text());self.assertTrue(report['complete']);self.assertGreater(report['wakes'],0)
                self.assertLessEqual(report['startedUnixNs'],report['endedUnixNs'])
            finally:
                if child.poll() is None:child.terminate();child.wait(timeout=10)


if __name__=='__main__':unittest.main()
