"""Observer metadata provenance and clock counterexamples, not native evidence."""
import copy
from datetime import datetime,timedelta,timezone
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('observer_active',ROOT/'scripts/check-desktop-active.py')
active=importlib.util.module_from_spec(spec);spec.loader.exec_module(active)
observer=active.observer

class ObserverTests(unittest.TestCase):
    def fixture(self):
        start=datetime(2026,11,1,tzinfo=timezone.utc);rows=[]
        for index,(epoch,mode) in enumerate(observer.PLAN,1):
            begin=index*1000;end=begin+50
            rows.append({'index':index,'epoch':epoch,'mode':mode,'windowId':123,'fromMilliseconds':begin,'toMilliseconds':end,
                'fromUtc':(start+timedelta(milliseconds=begin)).isoformat(),'toUtc':(start+timedelta(milliseconds=end)).isoformat(),
                'screenshots':0 if mode=='Accessibility' else 1,'apiReturned':True})
        return {'version':1,'sessionId':'session','playerId':'player','visiblePid':42,'platform':'win32','clockHostSha256':'a'*64,'operations':rows}

    def validate(self,value):return observer.validate_records(value,'session','player',42,'a'*64)

    def test_exact_order_and_same_clock_host_are_required_for_join(self):
        value=self.fixture();result=self.validate(value)
        self.assertTrue(result['clockJoinValid']);self.assertEqual(result['operations'],12)
        for fields in ({'sessionId':'old'},{'playerId':'old'},{'visiblePid':1},{'version':2},{'image':'not permitted'}):
            with self.assertRaises(ValueError):self.validate({**value,**fields})

    def test_missing_extra_reordered_or_wrong_window_operations_are_rejected(self):
        value=self.fixture()
        for change in (lambda v:v['operations'].pop(),lambda v:v['operations'].append(v['operations'][0]),
            lambda v:v['operations'].reverse(),lambda v:v['operations'][4].__setitem__('windowId',124),
            lambda v:v['operations'][0].__setitem__('index',2)):
            candidate=copy.deepcopy(value);change(candidate)
            with self.assertRaises(ValueError):self.validate(candidate)

    def test_image_mode_does_not_silently_fall_back_or_accept_payload(self):
        value=self.fixture()
        for change in (lambda r:r.__setitem__('screenshots',1),lambda r:r.__setitem__('apiReturned',False),
            lambda r:r.__setitem__('mode','Screenshot'),lambda r:r.__setitem__('image','payload')):
            candidate=copy.deepcopy(value);change(candidate['operations'][0])
            with self.assertRaises(ValueError):self.validate(candidate)
        value['operations'][3]['screenshots']=0
        with self.assertRaises(ValueError):self.validate(value)

    def test_invalid_monotonic_and_naive_utc_are_rejected(self):
        value=self.fixture()
        for change in (lambda r:r.__setitem__('fromMilliseconds',float('nan')),lambda r:r.__setitem__('toMilliseconds',-1),
            lambda r:r.__setitem__('fromUtc','2026-11-01T00:00:00'),lambda r:r.__setitem__('toMilliseconds',0)):
            candidate=copy.deepcopy(value);change(candidate['operations'][0])
            with self.assertRaises(ValueError):self.validate(candidate)
        value['operations'][1]['fromMilliseconds']=1049
        with self.assertRaises(ValueError):self.validate(value)

    def test_clock_step_or_different_host_withholds_join_without_rewriting_raw(self):
        value=self.fixture();value['operations'][0]['toUtc']='2026-11-01T00:00:01.110000+00:00'
        before=copy.deepcopy(value);self.assertFalse(self.validate(value)['clockJoinValid']);self.assertEqual(value,before)
        for fields in ({'platform':'linux'},{'clockHostSha256':'b'*64}):
            result=self.validate({**self.fixture(),**fields});self.assertFalse(result['clockJoinValid']);self.assertFalse(result['clockHostMatched'])

    def test_failed_timer_report_cannot_skip_native_cleanup_or_become_success(self):
        v=object.__new__(active.ActiveVenue);child=SimpleNamespace(poll=lambda:0,pid=7)
        v.observer_heartbeat=SimpleNamespace(child=child);v.pose_programs=[];v.pose_finished=False
        v.processes={'observer-independent-timer':child};v.finish_observer_timer=Mock(side_effect=OSError('report failed'))
        v.stop=lambda name:v.processes.pop(name);v.save=Mock()
        with patch.object(active.capacity.ReplicationVenue,'cleanup',return_value=True) as cleanup:
            self.assertFalse(v.cleanup());cleanup.assert_called_once_with()
        self.assertEqual(v.processes,{});self.assertEqual(v.save.call_args.args[1]['errors'],['OSError'])

    def test_zero_ammo_does_not_hide_motion_aim_reload_or_rifle_changes(self):
        player={'id':'p','head':{'x':0,'y':1.65,'z':-3},'muzzle':{'x':0,'y':1.4,'z':-2.8},'forward':{'x':0,'y':0,'z':1},
            'magazine':30,'reserve':90,'reloading':False,'fireSequence':0,'connected':True,'rig':{'kind':'Simulated'}}
        baseline={'players':[player]};self.assertEqual(observer.stationary_faults(copy.deepcopy(baseline),baseline),[])
        for key,value in [('head',{'x':.05,'y':1.65,'z':-3}),('forward',{'x':1,'y':0,'z':0}),('reloading',True),('magazine',29),('fireSequence',1)]:
            candidate=copy.deepcopy(baseline);candidate['players'][0][key]=value
            self.assertTrue(observer.stationary_faults(candidate,baseline))
        candidate=copy.deepcopy(baseline);candidate['players'][0]['connected']=False;candidate['players'][0]['rig']['kind']='None'
        self.assertEqual(observer.stationary_faults(candidate,baseline),[]) # Report participation failure separately, never call it input.

    def test_stationary_roster_cannot_drop_or_alias_an_original_player(self):
        baseline={'players':[{'id':'p'}]}
        self.assertTrue(observer.stationary_faults({'players':[]},baseline))
        self.assertTrue(observer.stationary_faults({'players':[{'id':'other'}]},baseline))

    def test_replay_keeps_a_transient_move_failed_after_it_recovers(self):
        player={'id':'p','head':{'x':0,'y':1.65,'z':0},'muzzle':{'x':0,'y':1.4,'z':1},'forward':{'x':0,'y':0,'z':1},
            'magazine':30,'reserve':90,'reloading':False,'fireSequence':0}
        frames=[{'packet':{'sequence':i,'frame':{'players':[copy.deepcopy(player)],'phase':'Ended' if i==3 else 'Running'}},'statistics':{}} for i in range(1,4)]
        frames[1]['packet']['frame']['players'][0]['head']['x']=.05
        entry={'id':'session','players':[player],'sealed':{'world':{'durationMilliseconds':100,'acceptedSequence':3}}}
        v=SimpleNamespace(args=SimpleNamespace(observer_sequence=True),base='http://127.0.0.1:5099',tokens={'Master':'fixture'})
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        with patch.object(active.urllib.request,'urlopen',return_value=response),patch.object(active.capacity,'sse_frames',return_value=iter(frames)),patch.object(active,'world_continuity_fault',return_value=None):
            result=active.replay(v,entry,{1:frames[0],3:frames[2]})
        self.assertFalse(result['stationary']['passed']);self.assertEqual(result['stationary']['faultFrameCount'],1)
        self.assertEqual(result['stationary']['examples'][0]['sequence'],2)

if __name__=='__main__':unittest.main()
