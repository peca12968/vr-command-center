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

if __name__=='__main__':unittest.main()
