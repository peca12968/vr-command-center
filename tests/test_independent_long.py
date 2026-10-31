import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('independent_long', ROOT / 'scripts/check-desktop-independent-long.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class IndependentLongTests(unittest.TestCase):
    def entry(self, room=1):
        return {'id': 'session-' + str(room), 'port': 7000 + room, 'roomIds': [room], 'stableSequence': 10,
            'mission': {'definition': {'environment': {'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False}}},
            'players': [{'id': str(i), 'roomId': room} for i in range(5)], 'health': {str(i): 80 if i == 0 else 100 for i in range(5)}}

    def row(self, room=1, sequence=1, tick=2400, phase='Running', observed=10):
        entry = self.entry(room)
        return {'packet': {'sequence': sequence, 'elapsedMilliseconds': sequence * 100, 'observedSequence': observed, 'suspended': False,
            'weather': 'Clear', 'lightning': False, 'frame': {'phase': phase, 'tick': tick, 'night': False, 'enemies': [{'roomId': room}],
            'players': [{'id': p['id'], 'roomId': room, 'health': entry['health'][p['id']], 'connected': True, 'rig': {'kind': 'Simulated'}} for p in entry['players']]}}}

    def pause(self): return {'tick': 2400, 'pauseSequence': 11, 'resumeSequence': 12}

    def test_planned_pause_checks_every_sequence_without_counting_activity(self):
        audit = m.RoomAudit(self.entry(), replay=True)
        for row in [self.row(), self.row(sequence=2, phase='Paused', observed=11), self.row(sequence=3, tick=2401, observed=12)]: audit.observe(row)
        result = audit.finish(self.pause()); self.assertTrue(result['passed']); self.assertEqual(3, result['frames'])
        self.assertEqual(2, result['runningFrames']); self.assertEqual(10, result['expectedParticipantObservations']); self.assertEqual(1, result['pausedFrames'])

    def test_only_accepted_pause_epoch_and_frozen_tick_are_allowed(self):
        for tick, sequence in [(2401, 11), (2400, 10), (2400, 12)]:
            audit = m.RoomAudit(self.entry()); audit.observe(self.row()); audit.observe(self.row(sequence=2, tick=tick, phase='Paused', observed=sequence))
            with self.subTest(tick=tick, sequence=sequence), self.assertRaises(ValueError): audit.finish(self.pause())

    def test_planned_pause_must_really_be_observed(self):
        audit = m.RoomAudit(self.entry()); audit.observe(self.row())
        with self.assertRaises(ValueError): audit.finish(self.pause())

    def test_other_room_pause_remains_a_continuity_failure(self):
        audit = m.RoomAudit(self.entry(2)); audit.observe(self.row(2)); audit.observe(self.row(2, sequence=2, phase='Paused', observed=11))
        result = audit.finish(self.pause()); self.assertFalse(result['passed']); self.assertEqual(1, result['badFrames'])

    def test_pause_does_not_hide_last_players_body_loss(self):
        audit = m.RoomAudit(self.entry()); audit.observe(self.row()); row = self.row(sequence=2, phase='Paused', observed=11)
        row['packet']['frame']['players'][-1]['connected'] = False; audit.observe(row)
        result = audit.finish(self.pause()); self.assertFalse(result['passed']); self.assertEqual(1, result['badPausedFrames'])

    def test_suspension_weather_night_lightning_and_enemy_room_leaks_fail(self):
        for field in ['suspended', 'weather', 'night', 'lightning', 'enemy']:
            row = self.row(2)
            if field == 'suspended': row['packet']['suspended'] = True
            elif field == 'weather': row['packet']['weather'] = 'Storm'
            elif field == 'night': row['packet']['frame']['night'] = True
            elif field == 'lightning': row['packet']['lightning'] = True
            else: row['packet']['frame']['enemies'][0]['roomId'] = 1
            audit = m.RoomAudit(self.entry(2)); audit.observe(row)
            with self.subTest(field=field): self.assertFalse(audit.finish(None)['passed'])

    def test_running_recovery_cannot_erase_an_earlier_inactive_player(self):
        audit = m.RoomAudit(self.entry(2), replay=True); bad = self.row(2); bad['packet']['frame']['players'][-1]['connected'] = False
        audit.observe(bad); audit.observe(self.row(2, sequence=2, tick=2401))
        result = audit.finish(None); self.assertFalse(result['passed']); self.assertEqual({'4': 1}, result['perPlayerBadFrames'])

    def test_planned_pause_preserves_saved_frame_gap_boundary(self):
        audit = m.RoomAudit(self.entry(), replay=True); audit.observe(self.row())
        row = self.row(sequence=2, phase='Paused', observed=11); row['packet']['elapsedMilliseconds'] = 1600; audit.observe(row)
        result = audit.finish(self.pause()); self.assertFalse(result['passed']); self.assertEqual(1, result['captureGapsAtLeast1500ms'])

    def test_pause_observation_bound_fails_instead_of_dropping_earlier_evidence(self):
        audit = m.RoomAudit(self.entry())
        for i in range(1, 513): audit.observe(self.row(sequence=i, phase='Paused', observed=11))
        with self.assertRaises(ValueError): audit.observe(self.row(sequence=513, phase='Paused', observed=11))

    def test_distinct_world_session_room_stream_port_and_geometry_are_required(self):
        entries = [self.entry(i) for i in range(1, 6)]
        headers = [{'sessionId': e['id'], 'roomIds': e['roomIds'], 'streamId': 'stream-' + e['id'], 'origin': 'Simulation', 'missionDurationSeconds': 900,
            'props': [{'roomId': e['roomIds'][0]}]} for e in entries]
        m.verify_worlds(entries, headers)
        for field in ['sessionId', 'roomIds', 'streamId', 'origin', 'missionDurationSeconds', 'props']:
            changed = copy.deepcopy(headers); changed[-1][field] = copy.deepcopy(headers[0][field]) if field not in ('origin', 'missionDurationSeconds') else ('GameServer' if field == 'origin' else 901)
            with self.subTest(field=field), self.assertRaises(ValueError): m.verify_worlds(entries, changed)
        entries[-1]['port'] = entries[0]['port']
        with self.assertRaises(ValueError): m.verify_worlds(entries, headers)


if __name__ == '__main__': unittest.main()
