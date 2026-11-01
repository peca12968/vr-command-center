import copy,importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('desktop_exercise_checks',Path(__file__).resolve().parents[1]/'scripts/check-desktop-exercise.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ExerciseEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.players=[{'id':'alpha','admissionId':'epoch-a','roomId':3,'seat':0}]
        self.value={'packet':{'suspended':False,'observedSequence':10,'frame':{'phase':'Running','players':[{'id':'alpha','roomId':3,'connected':True,'health':100,'head':{'x':-3,'y':1.65,'z':-2.5},'rig':{'kind':'Simulated'}}]}}}
    def test_moving_body_is_not_rejected_as_static_spawn(self):
        self.assertEqual(m.validate_frame(self.value,self.players)['phase'],'Running')
    def test_running_frame_must_reach_its_original_begin_receipt(self):
        with self.assertRaises(ValueError):m.validate_frame(self.value,self.players,begin_sequence=11)
        m.validate_frame(self.value,self.players,begin_sequence=10)
    def test_recovered_body_does_not_erase_earlier_invalid_frame(self):
        bad=copy.deepcopy(self.value);bad['packet']['frame']['players'][0]['connected']=False
        with self.assertRaises(ValueError):m.validate_frame(bad,self.players)
        m.validate_frame(self.value,self.players)
    def test_original_admission_and_seat_are_mandatory(self):
        for field,value in [('admissionId','other'),('seat',1),('roomId',2)]:
            bad={'players':copy.deepcopy(self.players)};bad['players'][0][field]=value
            with self.assertRaises(ValueError):m.validate_roster(bad,self.players)
    def test_unexpected_pause_is_not_a_continuity_exemption(self):
        value=copy.deepcopy(self.value);value['packet']['frame']['phase']='Paused'
        with self.assertRaises(ValueError):m.validate_frame(value,self.players)
        m.validate_frame(value,self.players,{'accepted':10,'resumed':11})
        with self.assertRaises(ValueError):m.validate_frame(value,self.players,{'accepted':10,'resumed':10})
    def test_foreign_rig_health_and_lane_fail(self):
        for field,value in [('roomId',4),('health',99),('rig',{'kind':'Tracked'}),('head',{'x':0,'y':1.65,'z':-2.5})]:
            bad=copy.deepcopy(self.value);bad['packet']['frame']['players'][0][field]=value
            with self.assertRaises(ValueError):m.validate_frame(bad,self.players)
    def test_explicit_original_process_and_input_report_required(self):
        owner={'pid':100,'playerId':'alpha','roomId':3,'nativeConnectionId':1}
        report={'version':1,'mode':'AutomatedSimulation','role':'Client','physicalInput':False,'headsets':0,'complete':True,'truncated':False,'reason':'Requested','fault':'','pid':100,'playerId':'alpha','room':3,'connection':1,'fireSubmissions':2,'reloadSubmissions':1,'movementFrames':1,'activeFrames':2,'firstTick':1,'lastTick':200}
        m.validate_report(report,owner)
        for field,value in [('pid',101),('connection',2),('mode','Physical'),('headsets',False),('reason','Timeout'),('complete',False),('reloadSubmissions',0)]:
            with self.assertRaises(ValueError):m.validate_report({**report,field:value},owner)

class EnduranceEvidenceTests(unittest.TestCase):
    def samples(self):return {i:{'min':-3,'max':-2.3,'reload':True,'ammoMax':2*(i+1),'frames':190,'walkingFrames':180} for i in range(3)}
    def test_every_cycle_needs_its_own_accepted_movement_reload_and_shots(self):
        samples=self.samples();m.validate_endurance_cycles(samples,3)
        for field,value in [('max',-3),('reload',False),('ammoMax',2),('frames',0),('walkingFrames',0),('min',float('nan'))]:
            bad=self.samples();bad[1][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):m.validate_endurance_cycles(bad,3)
        self.assertEqual(samples,self.samples())
    def test_later_recovery_or_extra_cycles_do_not_replace_a_missing_cycle(self):
        for action in [lambda d:d.pop(1),lambda d:d.update({3:d[2]}),lambda d:d.__setitem__(1,{**d[1],'ammoMax':6})]:
            bad=self.samples();action(bad)
            with self.assertRaises(ValueError):m.validate_endurance_cycles(bad,3)
    def test_endurance_report_requires_its_own_bound_and_actual_tick_coverage(self):
        owner={'pid':100,'playerId':'alpha','roomId':3,'nativeConnectionId':1}
        report={'version':1,'mode':'AutomatedSimulation','role':'Client','physicalInput':False,'headsets':0,'complete':True,'truncated':False,'reason':'Requested','fault':'','pid':100,'playerId':'alpha','room':3,'connection':1,'fireSubmissions':90,'reloadSubmissions':45,'movementFrames':100,'activeFrames':100,'firstTick':1,'lastTick':17999,'profile':'Endurance','maximumActiveTicks':19000,'maximumCollectionSeconds':1200}
        m.validate_report(report,owner,90,45,17900,True)
        for field,value in [('profile','Short'),('maximumActiveTicks',1200),('maximumCollectionSeconds',240),('lastTick',17000),('fireSubmissions',88),('reloadSubmissions',44)]:
            with self.subTest(field=field),self.assertRaises(ValueError):m.validate_report({**report,field:value},owner,90,45,17900,True)

class OperatorCombinationTests(unittest.TestCase):
    def receipts(self):
        return [{'commandId':identity,'appliedAtSequence':sequence,'duplicate':False,'session':{'id':'round'}} for identity,sequence in [('environment',11),('ai',13)]]
    def test_accepted_intents_must_preserve_exact_identity_session_and_order(self):
        original=self.receipts();self.assertEqual(m.validate_control_receipts(original,'round',['environment','ai'],10),13)
        for field,value in [('commandId','other'),('session',{'id':'another'}),('duplicate',True),('appliedAtSequence',10),('appliedAtSequence',True)]:
            bad=self.receipts();bad[1][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):m.validate_control_receipts(bad,'round',['environment','ai'],10)
        self.assertEqual(original,self.receipts())
    def test_missing_duplicate_or_reversed_operator_intents_are_rejected(self):
        for responses,identities in [(self.receipts()[:1],['environment','ai']),(self.receipts(),['environment','environment']),(list(reversed(self.receipts())),['ai','environment'])]:
            with self.assertRaises(ValueError):m.validate_control_receipts(responses,'round',identities,10)
    def test_exact_saved_source_and_statistics_must_both_reappear_in_replay(self):
        reference={'packet':{'sequence':20,'observedSequence':13,'frame':{'behavior':'Patrol'}},'statistics':[{'playerId':'a','ammoUsed':2}]};matched=set();before=copy.deepcopy(reference)
        m.match_control_reference(copy.deepcopy(reference),{20:reference},matched)
        self.assertEqual(matched,{20});self.assertEqual(reference,before)
        for change in [lambda v:v['packet']['frame'].update(behavior='Hold'),lambda v:v['statistics'][0].update(ammoUsed=1),lambda v:v['packet'].update(observedSequence=12)]:
            bad=copy.deepcopy(reference);change(bad);seen=set()
            with self.assertRaises(ValueError):m.match_control_reference(bad,{20:reference},seen)
            self.assertEqual(seen,set())
    def test_other_sequence_cannot_satisfy_a_missing_operator_checkpoint(self):
        reference={'packet':{'sequence':20},'statistics':[]};seen=set()
        m.match_control_reference({'packet':{'sequence':21},'statistics':[]},{20:reference},seen)
        self.assertEqual(seen,set())

if __name__=='__main__':unittest.main()
