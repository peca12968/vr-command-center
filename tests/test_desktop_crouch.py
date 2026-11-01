import copy,importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('crouch_checks',Path(__file__).resolve().parents[1]/'scripts/check-desktop-crouch.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class CrouchEvidenceTests(unittest.TestCase):
    def setUp(self):self.body={'head':{'x':-3,'y':1,'z':-3},'health':100,'magazine':30,'reserve':90,'connected':True,'rig':{'kind':'Simulated'}}
    def test_both_canonical_heights_keep_the_original_float_tolerance(self):
        self.assertTrue(m.height(self.body,1));self.body['head']['y']=1.65;self.assertTrue(m.height(self.body,1.65));self.assertFalse(m.height(self.body,1))
    def test_nonfinite_bool_missing_and_string_height_cannot_pass(self):
        for y in (True,float('nan'),float('inf'),'1',None):self.body['head']['y']=y;self.assertFalse(m.height(self.body,1))
    def test_original_health_and_ammunition_cannot_be_reset(self):
        for change in ({'health':80},{'magazine':29},{'reserve':0}):
            body=copy.deepcopy(self.body);body.update(change)
            with self.assertRaises(RuntimeError):m.validate_body(body,100)
    def test_running_participation_requires_actual_valid_simulated_rig(self):
        for change in ({'connected':False},{'rig':{'kind':'None'}},{'rig':{'kind':'Tracked'}}):
            body=copy.deepcopy(self.body);body.update(change)
            with self.assertRaises(RuntimeError):m.validate_body(body,100)
    def test_intentional_focus_pause_requires_exact_receipt_interval(self):
        receipts={'focus-pause':{'appliedAtSequence':9},'focus-resume':{'appliedAtSequence':10}}
        for seq,phase,expected in [(8,'Paused',False),(9,'Paused',True),(10,'Paused',False),(9,'Running',False),(9,'Ended',False),(True,'Paused',False)]:
            self.assertEqual(expected,m.intentional_focus_pause({'observedSequence':seq,'frame':{'phase':phase}},receipts))
    def test_missing_observation_does_not_authorize_focus_exclusion(self):
        self.assertFalse(m.intentional_focus_pause({'frame':{'phase':'Paused'}},{'focus-pause':{'appliedAtSequence':9},'focus-resume':{'appliedAtSequence':10}}))
if __name__=='__main__':unittest.main()
