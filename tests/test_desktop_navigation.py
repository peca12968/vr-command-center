"""Native observer counterexamples; not a replacement for Unity gameplay."""
import copy,importlib.util,math
from pathlib import Path
import unittest
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from unittest.mock import Mock,patch
s=importlib.util.spec_from_file_location('navigation',Path(__file__).resolve().parents[1]/'scripts/check-desktop-navigation.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class NavigationTests(unittest.TestCase):
    def frame(self,tick=2,x=-4.5,z=-1):
        return {'packet':{'suspended':False,'frame':{'tick':tick,'autoAttack':False,'players':[{'id':'original','connected':True,'health':100,'rig':{'kind':'Simulated'}}],
            'enemies':[{'id':'enemy','roomId':3,'health':100,'fireSequence':0,'feet':{'x':x,'y':0,'z':z}}]}}}
    def inspect(self,q,previous=None):return m.inspect_frame(q,'original','enemy',previous)
    def test_original_participant_failure_is_not_hidden_by_later_recovery(self):
        q=self.frame();bad=copy.deepcopy(q);bad['packet']['frame']['players'][0]['connected']=False
        self.assertTrue(self.inspect(bad));self.assertEqual(self.inspect(q),[])
        bad=self.frame();bad['packet']['frame']['enemies'][0]['id']='replacement';self.assertTrue(self.inspect(bad))
    def test_saved_position_inside_actual_rotated_clearance_or_outside_room_fails(self):
        self.assertTrue(self.inspect(self.frame(x=.25,z=-1.75)));self.assertTrue(self.inspect(self.frame(x=5.8)))
        self.assertEqual(self.inspect(self.frame(x=0,z=-1)),[]);self.assertEqual(self.inspect(self.frame(x=.5,z=-1)),[])
    def test_nan_and_boolean_positions_cannot_pass_comparisons(self):
        for x in (math.nan,math.inf,True):self.assertTrue(self.inspect(self.frame(x=x)))
    def test_tick_bound_rejects_teleport_and_movement_while_clock_is_frozen(self):
        previous=self.frame();self.assertTrue(self.inspect(self.frame(tick=3,x=-3),previous));self.assertTrue(self.inspect(self.frame(x=-4.4),previous))
        self.assertEqual(self.inspect(self.frame(),previous),[])
        for tick in (-1,True,1.5):self.assertTrue(self.inspect(self.frame(tick=tick)))
    def test_suspended_source_is_not_accepted_and_missing_ticks_are_not_interpolated(self):
        q=self.frame();q['packet']['suspended']=True;self.assertTrue(self.inspect(q))
        self.assertEqual(self.inspect(self.frame(tick=22,x=.5,z=-1),self.frame(tick=2,x=0,z=-1)),[])
    def stream(self,frames,age=0):
        for i,q in enumerate(frames):q['packet'].update(sequence=i+1,elapsedMilliseconds=0,observedSequence=4);q['packet']['frame']['phase']='Running'
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        v=SimpleNamespace(base='http://127.0.0.1:5099',tokens={'Master':'fixture'},save=Mock())
        with patch.object(m.urllib.request,'urlopen',return_value=response),patch.object(m.capacity,'sse_frames',return_value=iter(frames)):
            return m.wait_endpoint(v,{'id':'fixture'},{'captureStartedAtUtc':(datetime.now(timezone.utc)-timedelta(seconds=age)).isoformat()},4,'enemy')
    def test_continuous_source_keeps_transient_endpoint_before_patrol_returns(self):
        frames=[self.frame(149,x=4.5,z=4.7),self.frame(150,x=4.5,z=5),self.frame(160,x=3.5,z=5)]
        self.assertIs(self.stream(frames),frames[1])
    def test_continuous_source_cannot_use_an_old_endpoint_as_fresh_evidence(self):
        with self.assertRaises(RuntimeError):self.stream([self.frame(150,x=4.5,z=5)],age=2)
if __name__=='__main__':unittest.main()
