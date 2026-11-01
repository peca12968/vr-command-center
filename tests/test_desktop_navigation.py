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
    def stream(self,frames,age=0,goal=None):
        for i,q in enumerate(frames):q['packet'].update(sequence=i+1,elapsedMilliseconds=0,observedSequence=4);q['packet']['frame']['phase']='Running'
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        v=SimpleNamespace(base='http://127.0.0.1:5099',tokens={'Master':'fixture'},save=Mock())
        with patch.object(m.urllib.request,'urlopen',return_value=response),patch.object(m.capacity,'sse_frames',return_value=iter(frames)):
            return m.wait_endpoint(v,{'id':'fixture'},{'captureStartedAtUtc':(datetime.now(timezone.utc)-timedelta(seconds=age)).isoformat()},4,'enemy',goal)
    def test_continuous_source_keeps_transient_endpoint_before_patrol_returns(self):
        frames=[self.frame(149,x=4.5,z=4.7),self.frame(150,x=4.5,z=5),self.frame(160,x=3.5,z=5)]
        self.assertIs(self.stream(frames),frames[1])
    def test_continuous_source_cannot_use_an_old_endpoint_as_fresh_evidence(self):
        with self.assertRaises(RuntimeError):self.stream([self.frame(150,x=4.5,z=5)],age=2)
    def test_anchor_profiles_check_their_actual_geometry_and_generated_spawn(self):
        for case in ('blocked-start','non-grid-goal'):
            cx,cz,_,sx,_=m.CASES[case]
            self.assertEqual(m.inspect_frame(self.frame(x=sx),'original','enemy',case=case),[])
            self.assertTrue(m.inspect_frame(self.frame(x=cx,z=cz),'original','enemy',case=case))
    def test_non_grid_endpoint_is_not_replaced_by_the_old_fixed_target(self):
        frame=self.frame(150,x=3.75,z=5)
        self.assertIs(self.stream([frame],goal={'x':3.75,'y':0,'z':5}),frame)
    def probe(self):
        return {'schemaVersion':1,'source':'NativeAuthorityTick','sessionId':'session','streamId':'stream','maximumSeconds':180,'maximumRows':4096,'complete':True,'truncated':False,'reason':'Explicit diagnostic stop',
            'samples':3,'firstTick':1,'lastTick':3,'endedSeconds':.2,'rows':[{'tick':i+1,'observedSequence':4,'seconds':.05*(i+1),'id':'enemy','room':3,'health':100,'feet':{'x':4.5,'y':0,'z':z}} for i,z in enumerate((4.8,4.9,4.8))]}
    def validate_probe(self,report):return m.validate_authority_probe(report,'session','stream','enemy',4,{'x':4.5,'y':0,'z':5},'blocked-start')
    def test_authority_endpoint_is_an_actual_tick_without_a_fabricated_world_sequence(self):
        result=self.validate_probe(self.probe());self.assertEqual(result['row']['tick'],2);self.assertIsNone(result['worldSequence'])
    def test_authority_report_rejects_foreign_sources_missing_ticks_and_truncation(self):
        for key,value in [('streamId','foreign'),('source','Replica'),('complete',False),('truncated',True),('samples',0),('lastTick',4)]:
            q=self.probe();q[key]=value
            with self.assertRaises(ValueError):self.validate_probe(q)
        q=self.probe();q['rows'][1]['tick']=3
        with self.assertRaises(ValueError):self.validate_probe(q)
    def test_authority_endpoint_after_the_original_twenty_seconds_cannot_pass(self):
        q=self.probe();q['endedSeconds']=22;q['rows'][1]['seconds']=21.1;q['rows'][2]['seconds']=21.15
        with self.assertRaises(ValueError):self.validate_probe(q)
    def test_authority_finish_io_error_still_runs_native_cleanup(self):
        v=object.__new__(m.NavigationVenue);v.args=SimpleNamespace(tick_probe=True);v.probe_report=None;v.finish_probe=Mock(side_effect=OSError('finish failed'));v.save=Mock()
        with patch.object(m.venue.Venue,'cleanup',return_value=True) as cleanup:self.assertFalse(v.cleanup());cleanup.assert_called_once_with()
        self.assertEqual(v.save.call_args.args[1]['errors'],['OSError'])
if __name__=='__main__':unittest.main()
