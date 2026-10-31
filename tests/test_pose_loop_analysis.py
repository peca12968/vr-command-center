"""Synthetic boundary evidence / clock / completeness counterexamples."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('loop_analysis',ROOT/'scripts/analyze-pose-input.py')
analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)


class LoopAnalysisTests(unittest.TestCase):
    def fixture(self):
        base=639290000000000001
        report={'version':1,'source':'NativeWindowsPlayerLoopBoundaries','complete':True,'truncated':False,'detached':True,
            'maximumNodes':512,'capacity':4096,'callbacks':4,'firstSeconds':1.,'lastSeconds':3.,'firstUtcTicks':base,
            'lastUtcTicks':base+20_000_000,'maximumClockStepSeconds':.00001,
            'boundaries':[{'path':'/0','system':'EngineWait','side':'before','calls':2,'maximumIncomingGapSeconds':.7},
                          {'path':'/0','system':'EngineWait','side':'after','calls':2,'maximumIncomingGapSeconds':.8}],
            'gaps':[{'fromBoundary':0,'toBoundary':1,'fromFrame':1,'toFrame':1,'fromSeconds':1.,'toSeconds':1.8,
                     'fromUtcTicks':base,'toUtcTicks':base+8_000_000},
                    {'fromBoundary':1,'toBoundary':0,'fromFrame':1,'toFrame':2,'fromSeconds':1.8,'toSeconds':2.5,
                     'fromUtcTicks':base+8_000_000,'toUtcTicks':base+15_000_000}]}
        shared=[{'fromUtcTicks':base+2_000_000,'toUtcTicks':base+6_000_000}]
        periods={'observation':(base,base+20_000_000),'boundary':(base+7_000_000,base+9_000_000)}
        return report,{'endedSeconds':3.1},periods,shared,True

    def test_native_bounding_and_cross_frame_gaps_are_distinct(self):
        value=analysis.loop_analysis(*self.fixture())
        self.assertEqual(value['gaps'][0]['location'],'inside observed system')
        self.assertEqual(value['gaps'][1]['location'],'between observers')
        self.assertEqual(len(value['phaseGaps']['boundary']),2)
        self.assertAlmostEqual(value['nativeTripleIntersections'][0]['seconds'],.4)
        self.assertEqual(value['fullyCoveredNativeTripleGaps'],1)

    def test_incomplete_truncated_attached_or_invalid_indices_are_rejected(self):
        for field,value in [('complete',False),('truncated',True),('detached',False)]:
            args=list(self.fixture());args[0][field]=value
            with self.assertRaises(ValueError):analysis.loop_analysis(*args)
        args=list(self.fixture());args[0]['gaps'][0]['toBoundary']=999
        with self.assertRaises(ValueError):analysis.loop_analysis(*args)

    def test_inconsistent_boundary_counters_and_gap_duration_are_rejected(self):
        args=list(self.fixture());args[0]['callbacks']=5
        with self.assertRaises(ValueError):analysis.loop_analysis(*args)
        args=list(self.fixture());args[0]['boundaries'][1]['maximumIncomingGapSeconds']=.1
        with self.assertRaises(ValueError):analysis.loop_analysis(*args)

    def test_clock_steps_withhold_joins_even_when_summary_claims_clean(self):
        args=list(self.fixture());args[0]['gaps'][1]['fromUtcTicks']+=2_000_000
        value=analysis.loop_analysis(*args);self.assertFalse(value['clockJoinValid']);self.assertIsNone(value['phaseGaps'])
        args=list(self.fixture());args[-1]=False
        self.assertIsNone(analysis.loop_analysis(*args)['nativeTripleIntersections'])

    def test_native_interval_outside_loop_coverage_is_not_claimed_covered(self):
        args=list(self.fixture());args[3][0]['fromUtcTicks']-=10_000_000
        value=analysis.loop_analysis(*args);self.assertEqual(value['fullyCoveredNativeTripleGaps'],0)
        self.assertEqual(value['uncoveredNativeTripleGaps'],1)

    def test_clean_gap_list_does_not_claim_zero_callback_delta(self):
        args=list(self.fixture());args[0]['gaps']=[]
        for b in args[0]['boundaries']:b['maximumIncomingGapSeconds']=.03
        value=analysis.loop_analysis(*args);self.assertEqual(value['nativeTripleIntersections'],[])
        self.assertAlmostEqual(value['maximumAdjacentBoundaryGapSeconds'],.03)

    def test_missing_sparse_evidence_or_duplicate_boundary_cannot_look_complete(self):
        args=list(self.fixture());args[0]['gaps']=[]
        with self.assertRaises(ValueError):analysis.loop_analysis(*args)
        args=list(self.fixture());args[0]['boundaries'][1]['side']='before'
        with self.assertRaises(ValueError):analysis.loop_analysis(*args)
        args=list(self.fixture());args[0]['boundaries'][1]['system']='Changed'
        with self.assertRaises(ValueError):analysis.loop_analysis(*args)

    def test_early_removed_markers_cannot_claim_the_whole_observation(self):
        args=list(self.fixture());args[2]['observation']=(args[0]['firstUtcTicks'],args[0]['lastUtcTicks']+1_000_000)
        self.assertFalse(analysis.loop_analysis(*args)['observationFullyCovered'])


if __name__=='__main__':unittest.main()
