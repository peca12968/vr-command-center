"""CPU accounting joins, ownership guards and one real Windows sampler process."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
analysis=module('cpu_analysis','scripts/analyze-process-timing.py')
producer=module('cpu_producer','scripts/pose-process-timing.py')


class ProcessTimingTests(unittest.TestCase):
    def fixture(self):
        base=1_793_491_200_000_000_000
        targets=[{'role':role,'pid':index+101,'createdFileTime':123+index,'executable':str(Path(sys.executable).resolve())}
            for index,role in enumerate(('Visible','Peer','Server'))]
        rows=[]
        for cycle in range(5):
            for index,target in enumerate(targets):
                start=cycle*100_000_000+index*1_000_000+1
                rows.append({'role':target['role'],'fromCounterNs':start,'toCounterNs':start+1000,
                    'fromUnixNs':base+start,'toUnixNs':base+start+1000,
                    'kernel100ns':cycle*100_000 if index!=1 else 0,'user100ns':cycle*200_000 if index!=1 else 5})
        report={'schemaVersion':1,'source':'OwnedWindowsProcessCpuTiming','complete':True,'truncated':False,'error':'',
            'sampleSeconds':.05,'maximumSeconds':240,'maximumSamples':5000,'cycles':5,'closedHandleCount':3,'targets':copy.deepcopy(targets),'rows':rows}
        interval={'kind':'syntheticNativeGap','fromUtcTicks':analysis.UNIX_TICKS+(base+50_000_000)//100,
            'toUtcTicks':analysis.UNIX_TICKS+(base+350_000_000)//100}
        return report,targets,[interval],True

    def test_only_interior_queries_establish_counter_advance_and_zero_is_not_suspension(self):
        value=analysis.analyze(*self.fixture());roles=value['intervals'][0]['processes']
        self.assertEqual(roles['Visible']['interiorSamples'],3);self.assertAlmostEqual(roles['Visible']['accountedCpuSeconds'],.06)
        self.assertEqual(roles['Visible']['activity'],'accountedCpuAdvanced');self.assertTrue(roles['Visible']['bracketedBySamples'])
        self.assertEqual(roles['Peer']['activity'],'noAccountedAdvanceObserved')

    def test_cpu_accrued_before_interval_is_not_interpolated_into_it(self):
        args=list(self.fixture())
        for index,row in enumerate(args[0]['rows']):row.update(kernel100ns=0,user100ns=0 if index<3 else 1_000_000)
        for r in analysis.analyze(*args)['intervals'][0]['processes'].values():self.assertEqual(r['accountedCpuSeconds'],0)

    def test_too_few_interior_queries_are_unknown_not_zero(self):
        args=list(self.fixture());args[2][0]['toUtcTicks']=args[2][0]['fromUtcTicks']+700_000
        r=analysis.analyze(*args)['intervals'][0]['processes']['Visible']
        self.assertEqual(r['activity'],'insufficientInteriorSamples');self.assertIsNone(r['accountedCpuSeconds'])

    def test_upper_query_bracket_is_rounded_outward_before_containment(self):
        args=list(self.fixture());row=args[0]['rows'][9];args[2][0]['toUtcTicks']=analysis.UNIX_TICKS+row['toUnixNs']//100
        self.assertEqual(analysis.analyze(*args)['intervals'][0]['processes']['Visible']['interiorSamples'],2)

    def test_clock_steps_or_bad_native_clocks_withhold_joins(self):
        args=list(self.fixture());args[0]['rows'][5]['fromUnixNs']+=200_000_000
        self.assertIsNone(analysis.analyze(*args)['intervals'])
        args=list(self.fixture());args[-1]=False;self.assertFalse(analysis.analyze(*args)['clockJoinValid'])

    def test_incomplete_identity_reused_pid_and_unclosed_handles_cannot_pass(self):
        for field,value in [('complete',False),('truncated',True),('closedHandleCount',2)]:
            args=list(self.fixture());args[0][field]=value
            with self.assertRaises(ValueError):analysis.analyze(*args)
        args=list(self.fixture());args[1][0]['createdFileTime']+=1
        with self.assertRaises(ValueError):analysis.analyze(*args)
        targets=self.fixture()[1];targets[1]['pid']=targets[0]['pid']
        with self.assertRaises(ValueError):producer.validate_targets(targets)

    def test_partial_cycles_role_changes_or_cpu_counter_reversal_are_rejected(self):
        for change in (lambda r:r['rows'].pop(),lambda r:r['rows'][2].__setitem__('role','Visible'),
                       lambda r:r['rows'][9].__setitem__('user100ns',0)):
            args=list(self.fixture());change(args[0])
            with self.assertRaises(ValueError):analysis.analyze(*args)

    def test_cycle_advance_with_zero_time_accounting_and_legacy_without_cycles(self):
        args=list(self.fixture());args[0]['cycleCounterVersion']=1
        for index,row in enumerate(args[0]['rows']):row.update(kernel100ns=0,user100ns=0,cpuCycles=index//3*1000)
        value=analysis.analyze(*args)['intervals'][0]['processes']['Visible']
        self.assertEqual(value['accountedCpuSeconds'],0);self.assertEqual(value['cpuCycleDelta'],2000)
        self.assertEqual(value['cpuCycleAdvancingPairs'],2)
        self.assertEqual(value['cycleActivity'],'cycleCounterAdvanced')
        args[0]['rows'][9]['cpuCycles']=0
        with self.assertRaises(ValueError):analysis.analyze(*args)
        legacy=analysis.analyze(*self.fixture())['intervals'][0]['processes']['Visible']
        self.assertIsNone(legacy['cpuCycleDelta']);self.assertEqual(legacy['cycleActivity'],'unavailable')

    @unittest.skipUnless(os.name=='nt','Windows API producer is not a Linux test')
    def test_real_owned_sampler_checks_birth_keeps_borrowed_handle_and_defers_output(self):
        with tempfile.TemporaryDirectory(prefix='vr-cpu-timing-') as temporary:
            root=Path(temporary).resolve();self.assertEqual(root.parent,Path(tempfile.gettempdir()).resolve());self.assertTrue(root.name.startswith('vr-cpu-timing-'))
            worker=subprocess.Popen([sys.executable,'-c','import time\nend=time.monotonic()+15\nwhile time.monotonic()<end: sum(range(1000))'])
            sampler=None
            try:
                query=producer.ProcessQuery(worker.pid,process_handle=worker._handle)
                identity=query.identity('Visible');query.close();self.assertIsNone(worker.poll())
                with self.assertRaises(ValueError):producer.ProcessQuery(worker.pid,created=identity['createdFileTime']+1)
                manifest=root/'pose-process-targets.json';manifest.write_text(json.dumps({'schemaVersion':1,'source':'OwnedProcessTimingTargets','targets':[identity]}))
                directory=root/'probe';sampler=subprocess.Popen([sys.executable,str(ROOT/'scripts/pose-process-timing.py'),'--directory',str(directory),'--manifest',str(manifest)])
                deadline=time.monotonic()+10
                while not (directory/'ready.json').exists() and sampler.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue((directory/'ready.json').exists());time.sleep(.25);self.assertFalse((directory/'report.json').exists())
                (directory/'finish.request').write_text('finish');self.assertEqual(sampler.wait(timeout=10),0)
                report=json.loads((directory/'report.json').read_text());value=analysis.analyze(report,[identity],[],True)
                self.assertTrue(value['clockJoinValid']);self.assertEqual(report['closedHandleCount'],1)
                self.assertGreater(report['rows'][-1]['user100ns']-report['rows'][0]['user100ns'],0)
                self.assertGreater(report['rows'][-1]['cpuCycles']-report['rows'][0]['cpuCycles'],0)
            finally:
                for child in (sampler,worker):
                    if child is not None and child.poll() is None:child.terminate();child.wait(timeout=10)


if __name__=='__main__':unittest.main()
