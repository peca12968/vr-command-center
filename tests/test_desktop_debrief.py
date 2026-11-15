import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('desktop_debrief', ROOT / 'scripts/check-desktop-debrief.py')
debrief = importlib.util.module_from_spec(spec); spec.loader.exec_module(debrief)


class DebriefEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.entry = {'id': 'session'}; self.player = {'id': 'player', 'admissionId': 'admission', 'roomId': 3}
        self.metrics = {'ammoUsed': 3, 'shotsHit': 1, 'kills': 1, 'hitsReceived': 2, 'damageTaken': 20, 'health': 80, 'accuracyPercent': 33.33}
        self.sealed = {'world': {'complete': True, 'acceptedSequence': 27, 'header': {'streamId': 'stream'}},
            'statistics': {'throughSequence': 42, 'pendingTelemetry': False, 'players': [{'playerId': 'player', **self.metrics}]}}
        self.result = {'version': 1, 'sessionId': 'session', 'playerId': 'player', 'admissionId': 'admission', 'roomId': 3,
            'origin': 'Simulation', 'streamId': 'stream', 'worldSequence': 27, 'throughSequence': 42, **self.metrics}
    def test_exact_sealed_native_result_is_accepted(self):
        self.assertEqual(self.result, debrief.validate_result(self.result, self.entry, self.player, self.sealed))
    def test_game_server_result_requires_the_explicit_source(self):
        result = {**self.result, 'origin': 'GameServer'}
        self.assertEqual(result, debrief.validate_result(result, self.entry, self.player, self.sealed, expected_origin='GameServer'))
        with self.assertRaises(ValueError):
            debrief.validate_result(result, self.entry, self.player, self.sealed)
        with self.assertRaises(ValueError):
            debrief.validate_result(self.result, self.entry, self.player, self.sealed, expected_origin='GameServer')
    def test_old_or_foreign_admission_is_rejected(self):
        for field in ['sessionId', 'playerId', 'admissionId']:
            with self.subTest(field=field):
                bad = {**self.result, field: 'foreign'}
                with self.assertRaises(ValueError): debrief.validate_result(bad, self.entry, self.player, self.sealed)
    def test_each_displayed_metric_must_match_sealed_ledger(self):
        for field in self.metrics:
            with self.subTest(field=field):
                bad = {**self.result, field: self.result[field] + 1}
                with self.assertRaises(ValueError): debrief.validate_result(bad, self.entry, self.player, self.sealed)
    def test_world_stream_and_both_sequences_must_match(self):
        for field in ['streamId', 'worldSequence', 'throughSequence']:
            with self.subTest(field=field):
                bad = {**self.result, field: 'foreign' if field == 'streamId' else self.result[field] + 1}
                with self.assertRaises(ValueError): debrief.validate_result(bad, self.entry, self.player, self.sealed)
    def test_pending_or_unsealed_evidence_cannot_be_final(self):
        for incomplete_world in [True, False]:
            bad = copy.deepcopy(self.sealed)
            if incomplete_world: bad['world']['complete'] = False
            else: bad['statistics']['pendingTelemetry'] = True
            with self.assertRaises(ValueError): debrief.validate_result(self.result, self.entry, self.player, bad)


class ResultLifecycleTests(unittest.TestCase):
    def test_pending_received_and_acknowledged_are_distinct(self):
        phase = debrief.venue_module.player_result_phase
        text = 'VR_CLIENT_CONNECTED id=1\nVR_CLIENT_DEBRIEF_PENDING s\n'
        self.assertEqual('pending', phase(text))
        text += 'VR_CLIENT_DEBRIEF_FINAL {}\n'; self.assertEqual('received', phase(text))
        text += 'VR_CLIENT_DISCONNECTED\n'; self.assertEqual('acknowledged', phase(text))
    def test_old_result_cannot_satisfy_new_connection(self):
        phase = debrief.venue_module.player_result_phase
        text = 'VR_CLIENT_CONNECTED id=1\nVR_CLIENT_DEBRIEF_FINAL {}\nVR_CLIENT_DISCONNECTED\nVR_CLIENT_CONNECTED id=2\n'
        self.assertEqual('connected', phase(text))
    def test_disconnect_and_never_connected_do_not_imply_result(self):
        phase = debrief.venue_module.player_result_phase
        self.assertEqual('notConnected', phase('VR_CLIENT_ADMISSION_REJECTED\n'))
        self.assertEqual('disconnected', phase('VR_CLIENT_CONNECTED id=1\nVR_CLIENT_DISCONNECTED\n'))
    def test_seal_wait_allows_closed_player_but_not_failed_authority(self):
        class Process:
            def __init__(self, closed): self.closed = closed
            def poll(self): return 0 if self.closed else None
        v = debrief.venue_module.Venue.__new__(debrief.venue_module.Venue)
        v.processes = {'api': Process(False), 'round-server': Process(False), 'round-client': Process(True)}
        self.assertTrue(v.wait(lambda: True, 1, 'seal', required={'api', 'round-server'}))
        with self.assertRaises(RuntimeError): v.wait(lambda: True, 1, 'normal')
        v.processes['round-server'].closed = True
        with self.assertRaises(RuntimeError): v.wait(lambda: True, 1, 'seal', required={'api', 'round-server'})
    def test_missing_result_times_out_without_claiming_delivery(self):
        class Process:
            def poll(self): return None
        with tempfile.TemporaryDirectory(prefix='vr-debrief-') as directory:
            v = debrief.venue_module.Venue.__new__(debrief.venue_module.Venue)
            v.directory = Path(directory); v.processes = {'round-client': Process()}
            (v.directory / 'round-client.log').write_text('VR_CLIENT_CONNECTED id=1\n')
            with patch.object(v, 'save'), patch.object(debrief.venue_module.time, 'monotonic', side_effect=[0, 37]):
                result = v.wait_for_player_results({'name': 'round', 'sealed': True})
            self.assertFalse(result['allAcknowledged']); self.assertEqual(['round-client'], result['timedOut'])
    def test_empty_recipient_set_is_not_a_delivery_pass(self):
        with tempfile.TemporaryDirectory(prefix='vr-debrief-') as directory:
            v = debrief.venue_module.Venue.__new__(debrief.venue_module.Venue)
            v.directory = Path(directory); v.processes = {}
            result = v.wait_for_player_results({'name': 'round', 'sealed': True})
            self.assertFalse(result['allAcknowledged']); self.assertEqual({}, result['phases'])
    def test_retention_cleanup_cannot_overwrite_a_completed_delivery_with_empty_set(self):
        class Process:
            def poll(self): return None
        with tempfile.TemporaryDirectory(prefix='vr-debrief-') as directory:
            v = debrief.venue_module.Venue.__new__(debrief.venue_module.Venue)
            v.directory = Path(directory); v.processes = {'round-client': Process()}
            (v.directory / 'round-client.log').write_text('VR_CLIENT_CONNECTED id=1\nVR_CLIENT_DEBRIEF_FINAL {}\nVR_CLIENT_DISCONNECTED\n')
            entry = {'name': 'round', 'sealed': True}; first = v.wait_for_player_results(entry)
            saved = (v.directory / 'round-player-results.json').read_bytes(); v.processes = {}
            self.assertTrue(first['allAcknowledged']); self.assertIs(first, v.wait_for_player_results(entry))
            self.assertEqual(saved, (v.directory / 'round-player-results.json').read_bytes())


if __name__ == '__main__': unittest.main()
