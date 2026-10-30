"""Counterexamples for same-host timing attribution; all inputs are synthetic."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pose_trace_analysis',ROOT/'scripts/analyze-pose-trace.py');analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)

class PoseTraceAnalysisTests(unittest.TestCase):
    def fixture(self,root):
        epoch=analysis.ticks('2026-10-31T00:00:00+00:00')
        marks={'baseline-start':0,'baseline-end':.2,'loss-start':.3,'loss-recovered':1.6,'gpu-stage-start':1.7,'gpu-stage-end':2}
        from datetime import datetime,timedelta,timezone
        start=datetime(2026,10,31,tzinfo=timezone.utc)
        (root/'trace-stages.json').write_text(json.dumps([{'phase':p,'utc':(start+timedelta(seconds=s)).isoformat()}for p,s in marks.items()]),encoding='utf-8')
        def row(point,s,duration=0,connected=False):
            return {'point':point,'seconds':s,'engineSeconds':s+5,'durationSeconds':duration,'poseAgeSeconds':.55 if point=='BodyConnection'else -1,
                'utcTicks':epoch+round(s*10000000),'frame':int(s*90),'source':1,'connection':1,'connected':connected}
        for name,role in [('player','Client'),('server','Server')]:
            times=[i*.05 for i in range(41)if name=='player'or i<=5 or i>=30]
            rows=[row('PoseSend'if name=='player'else'PoseReceive',t)for t in times]
            if name=='server':rows += [row('PoseAccepted',t)for t in times]+[row('BodyConnection',.8)]
            else:rows+=[row('PlayerGpuReadback',1.8,.003),row('PlayerPngEncode',1.82,.01),row('PlayerPngWrite',1.83,.001)]
            path=root/'runtime-snapshot'/('pose-timing-'+name+'-trace/report.json');path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'schemaVersion':1,'source':'NativeWindowsMonotonicTiming','role':role,'complete':True,'truncated':False,
                'error':'','capacity':32768,'endedSeconds':2.1,'rows':sorted(rows,key=lambda r:r['seconds'])}),encoding='utf-8')
        return epoch
    def test_boundary_gap_is_preserved_and_controlled_loss_is_separate_from_gpu_spans(self):
        with tempfile.TemporaryDirectory()as temp:
            d=Path(temp);self.fixture(d);v=analysis.analyze(d);self.assertTrue(v['calibrated'])
            self.assertAlmostEqual(1.25,v['phases']['controlledLoss']['PoseReceive']['maximumGapSeconds'])
            self.assertFalse(v['phases']['naturalBaseline']['Server']['staleTransitions'])
            self.assertAlmostEqual(.01,v['phases']['gpuStage']['Client']['maximumSpans']['PlayerPngEncode'])
    def test_client_stall_confounds_control_even_when_server_expired(self):
        with tempfile.TemporaryDirectory()as temp:
            d=Path(temp);epoch=self.fixture(d);p=d/'runtime-snapshot/pose-timing-player-trace/report.json';r=json.loads(p.read_text())
            base=r['rows'][20].copy();base.update(point='MainThreadGap',durationSeconds=.6);r['rows'].append(base);r['rows'].sort(key=lambda row:row['seconds']);p.write_text(json.dumps(r),encoding='utf-8')
            self.assertFalse(analysis.analyze(d)['calibrated'])
    def test_wall_clock_step_cannot_be_called_a_network_delay(self):
        with tempfile.TemporaryDirectory()as temp:
            d=Path(temp);self.fixture(d);p=d/'runtime-snapshot/pose-timing-server-trace/report.json';r=json.loads(p.read_text());r['rows'][3]['utcTicks']+=2000000;p.write_text(json.dumps(r),encoding='utf-8')
            self.assertFalse(analysis.analyze(d)['calibrated'])

if __name__=='__main__':unittest.main()
