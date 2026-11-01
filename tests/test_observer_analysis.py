"""Synthetic counterexamples for closed observation interval comparisons."""
from datetime import datetime,timedelta,timezone
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('observer_analysis',ROOT/'scripts/analyze-observer-sequence.py')
analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)

class ObserverAnalysisTests(unittest.TestCase):
    def fixture(self):
        start=datetime(2026,11,1,tzinfo=timezone.utc)
        def utc(seconds):return (start+timedelta(seconds=seconds)).isoformat()
        def tick(seconds):return analysis.sparse.legacy.common.ticks(utc(seconds))
        operation={'fromUtc':utc(1),'toUtc':utc(2)}
        streams=[{'point':point,'connection':25,'source':1,'firstUtcTicks':tick(0),'lastUtcTicks':tick(3)} for point in ('PoseReceive','PoseAccepted')]
        report={'role':'Server','streams':streams,'gaps':[]}
        validation={'clockJoinValid':True,'mainThreadWindows':[],'playerLoop':None}
        return operation,report,validation,tick

    def join(self,operation,report,validation,valid=True):return analysis.join_operation(operation,report,validation,25,valid)

    def test_same_point_clips_and_unions_without_adding_other_points(self):
        op,report,validation,tick=self.fixture()
        report['gaps']=[{'point':point,'connection':25,'source':1,'fromUtcTicks':tick(a),'toUtcTicks':tick(b)}
            for point,a,b in [('PoseReceive',.5,1.6),('PoseReceive',1.4,2.5),('PoseAccepted',.5,2.5)]]
        result=self.join(op,report,validation)
        self.assertEqual(result['points']['PoseReceive']['overlappingGapCount'],2)
        self.assertEqual(result['points']['PoseReceive']['overlapUnionSeconds'],1)
        self.assertEqual(result['points']['PoseAccepted']['overlapUnionSeconds'],1)
        self.assertTrue(result['complete'])

    def test_interleaved_other_player_or_source_does_not_become_our_gap(self):
        op,report,validation,tick=self.fixture()
        report['gaps']=[{'point':'PoseReceive','connection':identity,'source':source,'fromUtcTicks':tick(0),'toUtcTicks':tick(3)} for identity,source in [(24,1),(25,2)]]
        result=self.join(op,report,validation)
        self.assertEqual(result['points']['PoseReceive']['overlappingGapCount'],0)
        self.assertEqual(result['points']['PoseReceive']['overlapUnionSeconds'],0)

    def test_missing_point_coverage_is_unknown_not_a_zero_gap(self):
        op,report,validation,tick=self.fixture();report['streams'][0]['firstUtcTicks']=tick(1.1)
        result=self.join(op,report,validation)
        self.assertFalse(result['complete']);self.assertIsNone(result['points']['PoseReceive']['overlappingGapCount'])
        self.assertIsNone(result['points']['PoseReceive']['overlapUnionSeconds'])

    def test_caller_or_native_clock_failure_withholds_all_joins(self):
        op,report,validation,_=self.fixture()
        for caller,native in [(False,True),(True,False)]:
            validation['clockJoinValid']=native;result=self.join(op,report,validation,caller)
            self.assertFalse(result['complete']);self.assertIsNone(result['mainThreadWindowCount']);self.assertIsNone(result['playerLoopOverlapCount'])
            self.assertIsNone(result['points']['PoseReceive']['overlappingGapCount'])

    def test_cpu_is_retained_for_the_whole_sample_not_scaled_to_the_call(self):
        op,report,validation,tick=self.fixture()
        window={'fromUtcTicks':tick(.5),'toUtcTicks':tick(2.5),'wallSecondsIncludingQueries':2,'mainThreadCpuSeconds':.8,'mainThreadCycleDelta':100}
        validation['mainThreadWindows']=[window];result=self.join(op,report,validation)
        self.assertEqual(result['mainThreadWindowExamples'],[window]);self.assertEqual(result['mainThreadWindowExamples'][0]['mainThreadCpuSeconds'],.8)

    def test_adjacent_outside_intervals_do_not_overlap_or_inflate_the_union(self):
        op,report,validation,tick=self.fixture()
        report['gaps']=[{'point':'PoseReceive','connection':25,'source':1,'fromUtcTicks':tick(a),'toUtcTicks':tick(b)} for a,b in [(0,1),(2,3)]]
        self.assertEqual(self.join(op,report,validation)['points']['PoseReceive']['overlappingGapCount'],0)
        self.assertEqual(analysis.union_seconds([(tick(1),tick(1.5)),(tick(1.5),tick(2))]),1)

if __name__=='__main__':unittest.main()
