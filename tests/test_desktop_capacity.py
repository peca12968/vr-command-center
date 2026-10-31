"""Capacity evidence invariants; actual native processes are separate checks."""
import copy
import importlib.util
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('capacity',ROOT/'scripts/check-desktop-capacity.py')
capacity=importlib.util.module_from_spec(spec);spec.loader.exec_module(capacity)


class CapacityTests(unittest.TestCase):
    def test_long_native_names_use_short_unique_probe_directories_with_saved_mapping(self):
        with tempfile.TemporaryDirectory(prefix='vr-replica-path-') as temporary:
            root=Path(temporary).resolve();self.assertEqual(root.parent,Path(tempfile.gettempdir()).resolve())
            self.assertTrue(root.name.startswith('vr-replica-path-'))
            v=object.__new__(capacity.ReplicationVenue);v.args=SimpleNamespace(replication_probe=True);v.runtime_directory=root;v.directory=root;v.probes={}
            names=['capacity-independent-5-client-'+str(i)*36 for i in range(2)]
            with patch.object(capacity.venue_module.Venue,'launch'):
                for name in names:v.launch(name,{'role':'Client'})
            self.assertEqual([p.name for p in v.probes.values()],['p001','p002'])
            self.assertEqual(capacity.venue_module.read_json(root/'replication-probes.json'),{n:str(p) for n,p in v.probes.items()})

    def replica(self):
        players,value=self.fixture();frame=value['packet']['frame'];frame['tick']=100;frame['enemies']=[]
        native=[];actors=[];avatars=[]
        for number,p in enumerate(frame['players'],1):
            p.update(magazine=30,reserve=90,reloading=False);p['head']['y']=1.65
            native.append({'playerId':p['id'],'nativeConnectionId':number})
            actors.append({'id':p['id'],'room':p['roomId'],'health':100,'magazine':30,'reserve':90,'connected':True,'reloading':False,
                'enemy':False,'presentationTick':100,'position':dict(p['head'])})
            avatars.append({'playerId':p['id'],'connection':number,'owner':number==1,'source':1,'accepted':True,'head':dict(p['head'])})
        return {'listening':True,'ready':True,'phase':'Running','packetQueueCapacity':128,'actorListSerializedBytes':3527,
            'presentation':{'phase':1,'tick':100,'rooms':31,'weather':0,'night':False,'lightning':False},'localConnection':1,'actors':actors,'avatars':avatars},frame,native

    def test_replica_enemy_roster_position_and_fire_sequence_are_authoritative(self):
        snapshot,frame,native=self.replica();position={'x':-32.5,'y':0,'z':-1}
        frame['enemies']=[{'id':'enemy-1','roomId':1,'health':100,'fireSequence':7,'feet':position}]
        actor={'id':'enemy-1','room':1,'health':100,'enemy':True,'fireSequence':7,'position':dict(position),'presentationTick':100}
        snapshot['actors'].append(actor);capacity.validate_replica(snapshot,frame,native)
        actor['fireSequence']=6
        with self.assertRaises(ValueError):capacity.validate_replica(snapshot,frame,native)
        snapshot['actors'].pop()
        with self.assertRaises(ValueError):capacity.validate_replica(snapshot,frame,native)

    def test_full_local_client_replica_and_distinct_server_ownership(self):
        snapshot,frame,native=self.replica();capacity.validate_replica(snapshot,frame,native)
        for avatar in snapshot['avatars']:avatar['owner']=False
        snapshot['packetQueueCapacity']=1024
        capacity.validate_replica(snapshot,frame,native,server=True)
        snapshot['packetQueueCapacity']=128
        with self.assertRaises(ValueError):capacity.validate_replica(snapshot,frame,native)

    def test_replica_rejects_wrong_owner_connection_stale_tick_and_nonfinite_pose(self):
        snapshot,frame,native=self.replica()
        for change in (lambda s:s.__setitem__('localConnection',25),lambda s:s['avatars'][3].__setitem__('connection',1),
            lambda s:s.__setitem__('packetQueueCapacity',64),lambda s:s.__setitem__('actorListSerializedBytes',0),
            lambda s:s['presentation'].__setitem__('tick',99),lambda s:s['avatars'][2]['head'].__setitem__('x',float('nan')),
            lambda s:s['actors'][2]['position'].__setitem__('x',float('inf'))):
            candidate=copy.deepcopy(snapshot);change(candidate)
            with self.assertRaises(ValueError):capacity.validate_replica(candidate,frame,native)

    def test_replica_rejects_missing_avatar_old_health_and_incoherent_actor_tick(self):
        snapshot,frame,native=self.replica()
        for change in (lambda s:s['avatars'].pop(),lambda s:s['actors'][0].__setitem__('health',80),
            lambda s:s['actors'][1].__setitem__('presentationTick',99),lambda s:s.__setitem__('phase','Paused')):
            candidate=copy.deepcopy(snapshot);change(candidate)
            with self.assertRaises(ValueError):capacity.validate_replica(candidate,frame,native)

    def fixture(self):
        players=[{'id':f'player-{room}-{seat}','admissionId':f'admission-{room}-{seat}','roomId':room,'seat':seat}
            for room in range(1,6) for seat in range(5)]
        frame={'packet':{'frame':{'phase':'Running','players':[{'id':p['id'],'roomId':p['roomId'],'health':100,'connected':True,
            'rig':{'kind':'Simulated'},'head':{'x':(p['roomId']-3)*14+(p['seat']-2)*1.5,'z':-3}} for p in players]},'suspended':False}}
        return players,frame

    def test_full_five_by_five_roster_and_frame_are_supported(self):
        players,frame=self.fixture();capacity.validate_roster(players,[1,2,3,4,5],5)
        self.assertEqual(len(capacity.validate_frame(frame,players)['players']),25)

    def test_alias_admission_slot_or_wrong_room_cannot_claim_capacity(self):
        players,_=self.fixture()
        for key in ('id','admissionId','seat','roomId'):
            candidate=copy.deepcopy(players);candidate[1][key]=candidate[0][key] if key!='roomId' else 5
            with self.assertRaises(ValueError):capacity.validate_roster(candidate,[1,2,3,4,5],5)

    def test_foreign_duplicate_stale_tracked_or_wrong_spawn_is_rejected(self):
        players,frame=self.fixture()
        for change in (lambda f:f['packet']['frame']['players'][0].__setitem__('id','foreign'),
            lambda f:f['packet']['frame']['players'][0].__setitem__('id',players[1]['id']),
            lambda f:f['packet']['frame']['players'][0].__setitem__('connected',False),
            lambda f:f['packet']['frame']['players'][0]['rig'].__setitem__('kind','Tracked'),
            lambda f:f['packet']['frame']['players'][0]['head'].__setitem__('x',0),
            lambda f:f['packet'].__setitem__('suspended',True)):
            candidate=copy.deepcopy(frame);change(candidate)
            with self.assertRaises(ValueError):capacity.validate_frame(candidate,players)

    def test_low_memory_refuses_new_launches_without_a_lowered_floor(self):
        capacity.require_memory({'totalPhysicalBytes':32*1024**3,'availablePhysicalBytes':3*1024**3})
        with self.assertRaises(RuntimeError):capacity.require_memory({'totalPhysicalBytes':32*1024**3,'availablePhysicalBytes':1024**3})
        with self.assertRaises(ValueError):capacity.require_memory({'totalPhysicalBytes':1,'availablePhysicalBytes':2})

    def test_replay_requires_complete_event_and_does_not_silently_accept_eof(self):
        good=io.BytesIO(b'event: frame\ndata: {"packet":1}\n\nevent: complete\ndata: {"complete":true}\n\n')
        self.assertEqual(list(capacity.sse_frames(good)),[{'packet':1}])
        with self.assertRaises(RuntimeError):list(capacity.sse_frames(io.BytesIO(b'event: frame\ndata: {"packet":1}\n\n')))

    def test_report_filename_escape_is_rejected_before_api_access(self):
        for name in ('../report.csv','F:/other.csv','folder\\report.csv'):
            with self.assertRaises(ValueError):capacity.practice.save_report(None,None,None,filename=name)


if __name__=='__main__':unittest.main()
