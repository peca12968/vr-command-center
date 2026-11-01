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


class OperatorControlsTests(unittest.TestCase):
    def fixture(self):
        environment={'mode':'VR','weather':'Storm','timeOfDay':'Night','lightning':True}
        value={'packet':{'observedSequence':20,'suspended':False,'weather':'Storm','lightning':True,
            'frame':{'phase':'Running','tick':100,'visibility':'Storm','night':True,'behavior':'Hold','autoAttack':False}}}
        return value,environment

    def test_source_must_observe_the_real_command_fence_and_active_tick(self):
        value,environment=self.fixture();active.validate_operator_packet(value,environment,'Hold',20,100)
        for change in (lambda v:v['packet'].__setitem__('observedSequence',19),lambda v:v['packet'].__setitem__('suspended',True),
            lambda v:v['packet']['frame'].__setitem__('phase','Paused'),lambda v:v['packet']['frame'].__setitem__('tick',99)):
            candidate=copy.deepcopy(value);change(candidate)
            with self.assertRaises(ValueError):active.validate_operator_packet(candidate,environment,'Hold',20,100)

    def test_same_fence_does_not_hide_wrong_environment_ai_or_auto_attack(self):
        value,environment=self.fixture()
        for change in (lambda v:v['packet'].__setitem__('weather','Clear'),lambda v:v['packet'].__setitem__('lightning',False),
            lambda v:v['packet']['frame'].__setitem__('night',False),lambda v:v['packet']['frame'].__setitem__('visibility','Clear'),
            lambda v:v['packet']['frame'].__setitem__('behavior','Advance'),lambda v:v['packet']['frame'].__setitem__('autoAttack',True)):
            candidate=copy.deepcopy(value);change(candidate)
            with self.assertRaises(ValueError):active.validate_operator_packet(candidate,environment,'Hold',20,100)

    def enemies(self):
        return {'enemies':[{'id':'alive','health':100,'roomId':1,'feet':{'x':0,'y':0,'z':0}},
            {'id':'dead','health':0,'roomId':3,'feet':{'x':1,'y':0,'z':0}}]}

    def test_actual_live_enemy_motion_is_distinct_from_dead_or_stationary_actor(self):
        before=self.enemies();after=copy.deepcopy(before)
        after['enemies'][1]['feet']['x']+=1
        with self.assertRaises(ValueError):active.validate_enemy_motion(before,after)
        after['enemies'][0]['feet']['z']+=.1
        self.assertEqual(active.validate_enemy_motion(before,after),{'alive':.1})

    def test_movement_cannot_hide_respawn_roster_health_or_room_change(self):
        before=self.enemies();after=copy.deepcopy(before);after['enemies'][0]['feet']['x']+=.1
        for change in (lambda v:v['enemies'][0].__setitem__('id','replacement'),lambda v:v['enemies'][1].__setitem__('health',100),
            lambda v:v['enemies'][0].__setitem__('roomId',2),lambda v:v['enemies'].append(copy.deepcopy(v['enemies'][0])),
            lambda v:v['enemies'][0]['feet'].__setitem__('x',float('nan'))):
            candidate=copy.deepcopy(after);change(candidate)
            with self.assertRaises(ValueError):active.validate_enemy_motion(before,candidate)


class FinalResultsTests(unittest.TestCase):
    def fixture(self):
        frame,statistics,_,_=ActiveTests().fixture()
        players=[{'id':p['id'],'admissionId':'a-'+p['id'],'roomId':p['roomId']} for p in frame['players']]
        native=[{'name':'client-'+p['id'],'playerId':p['id'],'admissionId':p['admissionId'],'roomId':p['roomId'],'nativeConnectionId':index+1} for index,p in enumerate(players)]
        entry={'id':'session','players':players}
        ledger=[{**p,'roomId':next(v['roomId'] for v in players if v['id']==p['playerId']),'health':100} for p in statistics['players']]
        sealed={'world':{'complete':True,'acceptedSequence':20,'header':{'streamId':'stream'}},
            'statistics':{'pendingTelemetry':False,'throughSequence':30,'players':ledger}}
        results=[{'version':1,'sessionId':'session','playerId':p['id'],'admissionId':p['admissionId'],'roomId':p['roomId'],
            'origin':'Simulation','streamId':'stream','worldSequence':20,'throughSequence':30,'finalStreamSequence':2,
            **{k:next(s[k] for s in ledger if s['playerId']==p['id']) for k in
                ('ammoUsed','shotsHit','kills','hitsReceived','damageTaken','health','accuracyPercent')}} for p in players]
        delivery={'allAcknowledged':True,'timedOut':[],'phases':{p['name']:'acknowledged' for p in native}}
        return entry,native,sealed,delivery,results

    def validate(self,values,server_log=None):
        if server_log is None:server_log='\n'.join('VR_SERVER_DEBRIEF_ACK id='+str(p['nativeConnectionId']) for p in values[1])
        return active.validate_final_results(*values,combat_sequence=2,server_log=server_log)

    def test_all_original_results_need_exact_seals_and_leave_evidence_unchanged(self):
        values=self.fixture();original=copy.deepcopy(values);results=self.validate(values)
        self.assertEqual(25,len(results));self.assertEqual(values,original)

    def test_empty_closed_or_unknown_delivery_cannot_be_acknowledged(self):
        for change in (lambda d:d.update(phases={}),lambda d:d.update(timedOut=None),
            lambda d:d['phases'].__setitem__('client-p1-0','closed')):
            values=self.fixture();change(values[3])
            with self.assertRaises(ValueError):self.validate(values)

    def test_missing_or_duplicated_player_final_is_rejected(self):
        for change in (lambda r:r.pop(),lambda r:r.__setitem__(0,None),lambda r:r.__setitem__(0,copy.deepcopy(r[1]))):
            values=self.fixture();change(values[4])
            with self.assertRaises(ValueError):self.validate(values)

    def test_old_admission_in_result_or_native_owner_is_rejected(self):
        for index in (1,4):
            values=self.fixture();values[index][0]['admissionId']='previous-admission'
            with self.assertRaises(ValueError):self.validate(values)

    def test_previous_world_frame_cannot_be_a_final_result(self):
        values=self.fixture();values[4][0]['worldSequence']=19
        with self.assertRaisesRegex(ValueError,'world seal'):self.validate(values)

    def test_combat_tail_must_match_actual_sealed_session_stream(self):
        values=self.fixture();values[4][0]['finalStreamSequence']=1
        with self.assertRaisesRegex(ValueError,'combat boundary'):self.validate(values)

    def test_same_player_cannot_receive_another_rooms_statistics(self):
        values=self.fixture();values[4][0]['roomId']=2
        with self.assertRaisesRegex(ValueError,'room'):self.validate(values)

    def test_final_health_cannot_differ_from_sealed_ledger(self):
        values=self.fixture();values[4][0]['health']=99
        with self.assertRaisesRegex(ValueError,'statistics'):self.validate(values)

    def test_client_final_and_disconnect_cannot_substitute_for_server_ack(self):
        values=self.fixture();correct='\n'.join('VR_SERVER_DEBRIEF_ACK id='+str(i) for i in range(1,26))
        for text in ('',correct.replace('id=25','id=24'),correct.replace('id=25','id=99'),correct+'\nVR_SERVER_DEBRIEF_TIMEOUT id=25'):
            with self.subTest(text=text):
                with self.assertRaisesRegex(ValueError,'Server did not acknowledge'):self.validate(values,text)


if __name__=='__main__':unittest.main()
