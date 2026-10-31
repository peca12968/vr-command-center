import copy
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('active',ROOT/'scripts/check-desktop-active.py')
active=importlib.util.module_from_spec(spec);spec.loader.exec_module(active)


class ActiveTests(unittest.TestCase):
    def row(self,seconds,phase=1):return {'seconds':seconds,'phase':phase,'ready':True,'coherent':True,'players':25,'connected':25,'health':2500}

    def test_continuity_rejects_transient_participation_loss_between_good_checkpoints(self):
        rows=[self.row(.1),self.row(.2),self.row(.3)];rows[1]['connected']=16
        result=active.analyze_continuity({'rows':rows},0)
        self.assertFalse(result['passed']);self.assertEqual(len(result['badRunningRows']),1)

    def test_deliberate_pause_is_not_a_running_tick_gap_and_startup_is_separate(self):
        rows=[self.row(.1),self.row(.2),self.row(.3,2),self.row(20,1),self.row(20.1)]
        rows[0]['players']=0;result=active.analyze_continuity({'rows':rows},.2)
        self.assertTrue(result['passed']);self.assertAlmostEqual(result['maximumAdjacentRunningTickGapSeconds'],.1)
        rows[-1]['seconds']=22
        self.assertFalse(active.analyze_continuity({'rows':rows},.2)['passed'])

    def test_world_replay_continuity_detects_stale_rig_not_just_hit_statistics(self):
        frame,_,_,_=self.fixture();frame['phase']='Running';frame['tick']=10;expected={p['id'] for p in frame['players']}
        self.assertIsNone(active.world_continuity_fault(frame,expected))
        frame['players'][0]['connected']=False
        self.assertIsNotNone(active.world_continuity_fault(frame,expected))
        frame['phase']='Ended';self.assertIsNone(active.world_continuity_fault(frame,expected))

    def fixture(self,stage='kill'):
        players=[{'id':f'p{r}-{s}','roomId':r,'head':{'x':(r-3)*14+(s-2)*1.5,'y':1.65,'z':-3},
            'health':100,'connected':True,'rig':{'kind':'Simulated'},'magazine':30,'reserve':90,'reloading':False,'fireSequence':0}
            for r in range(1,6) for s in range(5)]
        initial={'players':copy.deepcopy(players)};own='p3-0';player=next(p for p in players if p['id']==own);player['head']['z']+=.1
        shots={'move':0,'shot':1,'reload':1,'kill':2}[stage];player['fireSequence']=100*shots
        player['magazine'],player['reserve']={'move':(30,90),'shot':(29,90),'reload':(30,89),'kill':(29,89)}[stage]
        frame={'players':players,'enemies':[{'id':'target','roomId':3,'health':100-50*shots}]}
        metrics=[{'playerId':p['id'],'ammoUsed':shots if p['id']==own else 0,'shotsHit':shots if p['id']==own else 0,
            'kills':1 if p['id']==own and shots==2 else 0,'accuracyPercent':100 if p['id']==own and shots else 0,
            'damageTaken':0,'hitsReceived':0} for p in players]
        return frame,{'players':metrics},initial,own

    def test_all_four_input_stages_preserve_passive_players_and_exact_ammunition(self):
        for stage in ('move','shot','reload','kill'):
            frame,stats,initial,own=self.fixture(stage);result=active.validate_input(frame,stats,initial,own,stage)
            self.assertAlmostEqual(result['distanceMeters'],.1);self.assertEqual(result['enemyHealth'],frame['enemies'][0]['health'])

    def test_passive_pose_or_weapon_input_cannot_be_counted_as_single_operator(self):
        frame,stats,initial,own=self.fixture()
        for change in (lambda f:f['players'][0]['head'].__setitem__('x',10),lambda f:f['players'][0].__setitem__('fireSequence',1),
            lambda f:f['players'][0].__setitem__('magazine',29)):
            candidate=copy.deepcopy(frame);change(candidate)
            with self.assertRaises(ValueError):active.validate_input(candidate,stats,initial,own,'kill')

    def test_duplicate_roster_and_incomplete_statistics_are_rejected(self):
        frame,stats,initial,own=self.fixture();frame['players'][0]['id']=frame['players'][1]['id']
        with self.assertRaises(ValueError):active.validate_input(frame,stats,initial,own,'kill')
        frame,stats,initial,own=self.fixture();stats['players'].pop()
        with self.assertRaises(ValueError):active.validate_input(frame,stats,initial,own,'kill')

    def test_nonfinite_or_excessive_motion_and_incomplete_reload_are_rejected(self):
        frame,stats,initial,own=self.fixture('reload')
        for change in (lambda p:p['head'].__setitem__('x',float('nan')),lambda p:p['head'].__setitem__('y',float('nan')),
            lambda p:p['head'].__setitem__('z',0),lambda p:p.__setitem__('reloading',True),lambda p:p.__setitem__('reserve',90)):
            candidate=copy.deepcopy(frame);change(active.actor(candidate,own))
            with self.assertRaises(ValueError):active.validate_input(candidate,stats,initial,own,'reload')

    def test_fake_kill_or_missing_damage_or_passive_statistics_cannot_match(self):
        frame,stats,initial,own=self.fixture();frame['enemies'][0]['health']=50
        with self.assertRaises(ValueError):active.validate_input(frame,stats,initial,own,'kill')
        frame,stats,initial,own=self.fixture();stats['players'][0]['ammoUsed']=1
        with self.assertRaises(ValueError):active.validate_input(frame,stats,initial,own,'kill')


if __name__=='__main__':unittest.main()
