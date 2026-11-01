import copy,importlib.util,math,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('ai_targeting',Path(__file__).resolve().parents[1]/'scripts/check-desktop-ai-targeting.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class TargetingEvidenceTests(unittest.TestCase):
    def setUp(self):
        length=math.sqrt(3**2+.25**2+2.75**2)
        self.events=[{'kind':'EnemyShot','enemyId':'front','playerId':'close','sequence':1,'tick':1},
            {'kind':'PlayerDamaged','enemyId':'front','playerId':'close','sequence':2,'tick':1,'damage':20},
            {'kind':'EnemyShot','enemyId':'rear','playerId':'far','targetId':'far','hit':'Friendly','sequence':3,'tick':1,'origin':{'x':-3,'y':1.4,'z':-.25},'direction':{'x':3/length,'y':.25/length,'z':-2.75/length}},
            {'kind':'PlayerDamaged','enemyId':'rear','playerId':'far','sequence':4,'tick':1,'damage':20}]
    def errors(self):return m.targeting_errors(self.events,'rear','far','front','close')
    def test_exact_first_tick_shot_and_damage_pair(self):self.assertEqual([],self.errors())
    def test_missing_rear_shot_is_not_success_when_front_fired(self):self.events=self.events[:2];self.assertTrue(self.errors())
    def test_late_or_wrong_target_cannot_substitute_first_tick(self):
        for change in ({'tick':21},{'playerId':'close'},{'targetId':'middle'},{'hit':'Enemy'}):
            original=copy.deepcopy(self.events);self.events[2].update(change);self.assertTrue(self.errors());self.events=original
    def test_saved_ray_must_use_actual_rear_muzzle_and_far_player(self):
        for field in ('origin','direction'):
            original=copy.deepcopy(self.events);self.events[2][field]['x']+=.01;self.assertTrue(self.errors());self.events=original
    def test_dead_closest_player_does_not_prove_visible_target_selection(self):self.events[1]['damage']=100;self.assertTrue(self.errors())
    def test_damage_requires_same_enemy_tick_player_and_amount(self):
        for change in ({'damage':40},{'playerId':'close'},{'enemyId':'front'},{'tick':2},{'sequence':5}):
            original=copy.deepcopy(self.events);self.events[3].update(change);self.assertTrue(self.errors());self.events=original
    def test_nonfinite_bool_and_missing_positions_are_rejected(self):
        for x in (True,float('nan'),float('inf'),'0'):
            self.assertFalse(m.near({'x':x,'y':0,'z':0},{'x':0,'y':0,'z':0}))
        self.assertFalse(m.near({}, {'x':0,'y':0,'z':0}))
if __name__=='__main__':unittest.main()
