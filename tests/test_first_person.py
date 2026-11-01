"""Counterexamples for private first-person evidence, not native game evidence."""
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('first_person',ROOT/'scripts/check-desktop-first-person.py');first=importlib.util.module_from_spec(spec);spec.loader.exec_module(first)

class FirstPersonTests(unittest.TestCase):
    def fixture(self):
        head={'x':0,'y':1.65,'z':-3};muzzle={'x':.18,'y':1.53,'z':-2.1};forward={'x':0,'y':0,'z':1}
        row={'id':'original','tick':12,'firstPerson':True,'visible':True,'arms':True,'simulated':True,'head':head,
            **{key:{'x':0,'y':0,'z':0} for key in ('feet','leftElbow','leftWrist','rightElbow')},'rightWrist':first.grip_world(muzzle,forward,(.06,-.15,-.595))}
        capture={'firstPerson':row,'players':[],'phase':'Paused'}
        frame={'tick':12,'phase':'Paused','players':[{'id':'original','connected':True,'rig':{'kind':'Simulated'},'head':copy.deepcopy(head),'muzzle':muzzle,'forward':forward}]}
        return capture,frame
    def test_private_owner_is_not_a_remote_or_tracked_body(self):
        c,f=self.fixture();self.assertEqual(first.validate_capture(c,'original',f),0)
        for changes in ({'id':'foreign'},{'firstPerson':False},{'simulated':False},{'arms':False},{'visible':False}):
            candidate=copy.deepcopy(c);candidate['firstPerson'].update(changes)
            with self.assertRaises(ValueError):first.validate_capture(candidate,'original',f)
        c['players']=[c['firstPerson']]
        with self.assertRaises(ValueError):first.validate_capture(c,'original',f)
    def test_stale_tick_phase_or_accepted_rig_cannot_back_a_settled_capture(self):
        c,f=self.fixture()
        for change in (lambda v:v.__setitem__('tick',13),lambda v:v.__setitem__('phase','Running'),
            lambda v:v['players'][0].__setitem__('connected',False),lambda v:v['players'][0]['rig'].__setitem__('kind','None')):
            candidate=copy.deepcopy(f);change(candidate)
            with self.assertRaises(ValueError):first.validate_capture(c,'original',candidate)
    def test_source_head_or_glove_endpoint_difference_does_not_pass_as_pause(self):
        c,f=self.fixture()
        for key in ('head','rightWrist'):
            candidate=copy.deepcopy(c);candidate['firstPerson'][key]['x']+=.000002
            with self.assertRaises(ValueError):first.validate_capture(candidate,'original',f)
    def test_nan_and_boolean_vectors_cannot_hide_a_failed_difference(self):
        c,f=self.fixture()
        for invalid in (float('nan'),float('inf'),True):
            candidate=copy.deepcopy(c);candidate['firstPerson']['head']['x']=invalid
            with self.assertRaises(ValueError):first.validate_capture(candidate,'original',f)
        with self.assertRaises(ValueError):first.grip_world({'x':0,'y':0,'z':0},{'x':0,'y':0,'z':0},(0,0,0))
    def test_body_clock_must_be_an_integer_and_a_known_game_phase(self):
        c,f=self.fixture()
        for tick in (-1,True,1.5):
            candidate=copy.deepcopy(c);candidate['firstPerson']['tick']=tick
            with self.assertRaises(ValueError):first.validate_capture(candidate,'original')
        c['phase']='Unknown'
        with self.assertRaises(ValueError):first.validate_capture(c,'original')
    def test_probe_finish_io_failure_still_runs_native_cleanup(self):
        v=object.__new__(first.FirstPersonVenue);v.probe_report=None;v.finish_probe=Mock(side_effect=OSError('finish failed'));v.save=Mock()
        with patch.object(first.venue_module.Venue,'cleanup',return_value=True) as cleanup:
            self.assertFalse(v.cleanup());cleanup.assert_called_once_with()
        self.assertEqual(v.save.call_args.args[1],{'errors':['OSError'],'finished':False})
    def test_solo_replay_keeps_a_transient_participation_failure_after_recovery(self):
        for fault in (False,True):
            frames=[{'packet':{'sequence':i,'suspended':False,'frame':{'phase':'Ended' if i==3 else 'Running',
                'players':[{'id':'original','connected':True,'health':100,'rig':{'kind':'Simulated'}}]}},'statistics':[]} for i in range(1,4)]
            if fault:frames[1]['packet']['frame']['players'][0]['connected']=False
            entry={'id':'fixture','players':[{'id':'original'}],'sealed':{'world':{'durationMilliseconds':100,'acceptedSequence':3}}}
            v=SimpleNamespace(base='http://127.0.0.1:5099',tokens={'Master':'fixture'})
            response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
            with patch.object(first.urllib.request,'urlopen',return_value=response),patch.object(first.capacity,'sse_frames',return_value=iter(frames)):
                result=first.replay(v,entry,{1:frames[0],3:frames[2]})
            self.assertEqual(result['complete'],not fault);self.assertEqual(result['frames'],3)
            if fault:self.assertEqual(result['worldContinuityFaults'][0]['sequence'],2)

if __name__=='__main__':unittest.main()
