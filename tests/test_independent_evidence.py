"""Closed independent evidence must not hide identity / tail / acceptance errors."""
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('independent_evidence', ROOT / 'scripts/verify-independent-evidence.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class IndependentEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='vr-independent-evidence-')
        self.root = Path(self.temporary.name); self.directory = self.root / 'artifacts/desktop-long/20261101-000000-1234abcd'
        self.directory.mkdir(parents=True); self.root_patch = patch.object(m, 'ROOT', self.root); self.root_patch.start()
        self.addCleanup(self.root_patch.stop); self.addCleanup(self.temporary.cleanup)
        self.make_fixture()

    def save(self, name, value): (self.directory / name).write_text(json.dumps(value), encoding='utf-8')
    def read(self, name): return json.loads((self.directory / name).read_text())
    def mutate(self, name, change):
        value = self.read(name); change(value); self.save(name, value)

    def make_fixture(self):
        owners = []; headers = []; rooms = []
        pause = {'tick': 2400, 'pauseSequence': 13, 'resumeSequence': 14, 'secondsObserved': 3.1,
            'otherRooms': [{'roomId': i, 'beforeTick': 2400, 'afterTick': 2460} for i in range(2, 6)]}
        for room in range(1, 6):
            prefix = 'independent-long-' + str(room); player, admission, session, stream = ['p' + str(room), 'a' + str(room), 's' + str(room), 'w' + str(room)]
            owner = {'name': prefix + '-client-' + admission, 'playerId': player, 'admissionId': admission, 'sessionId': session, 'roomId': room, 'seat': 0, 'processId': 100 + room}; owners.append(owner)
            header = {'sessionId': session, 'streamId': stream, 'roomIds': [room], 'origin': 'Simulation', 'rulesVersion': '0.8.0', 'missionDurationSeconds': 900, 'props': [{'roomId': room}]}; headers.append(header)
            stats = dict(zip(m.METRICS, [0, 0, 0, 1, 20, 80, 0.0])); ledger = {'playerId': player, 'name': player, 'roomId': room, **stats}
            sealed = {'world': {'header': header, 'acceptedSequence': 10, 'durationMilliseconds': 900100, 'complete': True},
                'statistics': {'sessionId': session, 'origin': 'Simulation', 'throughSequence': 17, 'players': [ledger], 'pendingTelemetry': False}}
            result = {'version': 1, 'sessionId': session, 'playerId': player, 'admissionId': admission, 'roomId': room, 'origin': 'Simulation', 'streamId': stream,
                'worldSequence': 10, 'throughSequence': 17, 'finalStreamSequence': 1, **stats}
            csv_name = prefix + '-report.csv'; csv_row = {'reportVersion': '1', 'rowType': 'Player', 'sessionMode': 'Independent', 'sessionId': session,
                'roomIds': str(room), 'playerRoomId': str(room), 'origin': 'Simulation', 'plannedDurationSeconds': '900',
                **{k: result[k] for k in ['playerId', 'streamId', 'throughSequence', 'finalStreamSequence', *m.METRICS]}}
            with (self.directory / csv_name).open('w', encoding='utf-8-sig', newline='') as target:
                writer = csv.DictWriter(target, fieldnames=csv_row); writer.writeheader(); writer.writerow(csv_row)
            def counters(replay):
                running = 8 if replay else 7
                return {'frames': 10 if replay else 9, 'runningFrames': running, 'expectedParticipantObservations': running, 'finalSequence': 10, 'finalTick': 18000,
                    'skippedLiveSequences': 0 if replay else 1, 'badFrames': 0, 'perPlayerBadFrames': {}, 'pausedFrames': 1 if room == 1 else 0,
                    'captureGapsAtLeast1500ms': 0, 'badPausedFrames': 0, 'badEnvironmentFrames': 0, 'passed': True, 'finalPacketAndStatisticsMatch': True}
            rooms.append({'roomIds': [room], 'sessionId': session, 'sealed': sealed, 'clientResults': [result],
                'originalConnectionsAfterExpiry': {'tick': 6000, 'allOriginalAdmissions': True},
                'automaticEnd': {'sessionId': session, 'kind': 'ControlApplied', 'sequence': 16, 'payload': {'clockExpiration': {'streamId': stream, 'observedSequence': 15, 'tick': 18000}}},
                'finalReportCsv': {'path': str(self.directory / csv_name), 'sha256': hashlib.sha256((self.directory / csv_name).read_bytes()).hexdigest(), 'players': 1, 'verified': True},
                'live': counters(False), 'replay': counters(True), 'sourceAge': {'frames': 9, 'heartbeats': 1, 'maximumSeconds': .1, 'badSamples': 0}})
            self.save(prefix + '-sealed.json', sealed)
            self.save(prefix + '-latest-frame.json', {'packet': {'sequence': 10, 'observedSequence': 16, 'throughCombatSequence': 1, 'elapsedMilliseconds': 900100, 'frame': {'phase': 'Ended', 'tick': 18000}}, 'statistics': [ledger]})
            self.save(prefix + '-player-results.json', {'allAcknowledged': True, 'timedOut': [], 'phases': {owner['name']: 'acknowledged'}})
        self.save('independent-checks.json', {'version': 1, 'fixtureKind': 'IndependentFiveRoomLong', 'executionFinished': True, 'acceptancePassed': True, 'complete': True,
            'headsets': 0, 'hosts': 1, 'networkCapacityAccepted': False, 'durationSecondsPerRoom': 900, 'participants': 5, 'poseContinuity': None,
            'playerBuildReceipt': {'target': 'StandaloneWindows64', 'sourceFingerprint': 'a' * 64}, 'rooms': rooms, 'pauseIsolation': pause, 'nativeLogFindings': []})
        self.save('independent-native-clients.json', owners); self.save('independent-world-headers.json', headers)
        self.save('independent-pause-isolation.json', pause); self.save('cleanup.json', {'errors': [], 'remainingTrackedChildren': []})
        (self.directory / 'preserved.db').write_bytes(b'opaque SQLite / never open')

    def test_consistent_readback_preserves_every_byte_and_original_scope(self):
        before = {p.name: p.read_bytes() for p in self.directory.iterdir()}
        result = m.verify(self.directory)
        self.assertTrue(result['acceptancePassed']); self.assertEqual(5, result['participants']); self.assertEqual(50, sum(r['worldFrames'] for r in result['rooms']))
        self.assertNotIn('preserved.db', result['evidenceHashes'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.directory.iterdir()})

    def test_unfinished_cleanup_and_linked_format_are_rejected(self):
        for name, change in [('cleanup.json', lambda r: r['remainingTrackedChildren'].append(123)),
            ('independent-checks.json', lambda r: r.update(executionFinished=False)),
            ('independent-checks.json', lambda r: r.update(fixtureKind='Linked'))]:
            with self.subTest(name=name, change=change):
                self.make_fixture(); self.mutate(name, change)
                with self.assertRaises(ValueError): m.verify(self.directory)

    def test_unknown_cleanup_log_or_timeout_state_is_not_a_clean_empty_list(self):
        for name, change in [('cleanup.json', lambda r: r.update(errors=None)),
            ('cleanup.json', lambda r: r.update(remainingTrackedChildren=None)),
            ('independent-checks.json', lambda r: r.update(nativeLogFindings=None)),
            ('independent-long-1-player-results.json', lambda r: r.update(timedOut=None))]:
            with self.subTest(name=name):
                self.make_fixture(); self.mutate(name, change)
                with self.assertRaises(ValueError): m.verify(self.directory)

    def test_result_cannot_bind_the_frame_before_the_real_world_seal(self):
        self.mutate('independent-checks.json', lambda r: r['rooms'][0]['clientResults'][0].update(worldSequence=9))
        with self.assertRaisesRegex(ValueError, 'boundary'): m.verify(self.directory)

    def test_unchanged_player_id_cannot_replace_its_original_admission(self):
        self.mutate('independent-checks.json', lambda r: r['rooms'][0]['clientResults'][0].update(admissionId='replacement'))
        with self.assertRaisesRegex(ValueError, 'admission'): m.verify(self.directory)

    def test_success_flags_cannot_hide_a_failed_saved_frame(self):
        self.mutate('independent-checks.json', lambda r: r['rooms'][0]['replay'].update(badFrames=1, perPlayerBadFrames={'p1': 1}))
        with self.assertRaisesRegex(ValueError, 'pass flag'): m.verify(self.directory)

    def test_closed_counterexample_remains_failed_even_with_exact_results_and_csv(self):
        def change(r):
            r.update(acceptancePassed=False, complete=False)
            r['rooms'][0]['replay'].update(badFrames=1, perPlayerBadFrames={'p1': 1}, passed=False)
        self.mutate('independent-checks.json', change)
        self.assertFalse(m.verify(self.directory)['acceptancePassed'])

    def test_live_capture_gap_flag_keeps_the_original_replay_only_policy(self):
        def change(r):
            r.update(acceptancePassed=False, complete=False)
            r['rooms'][0]['live'].update(captureGapsAtLeast1500ms=1)
            r['rooms'][0]['replay'].update(captureGapsAtLeast1500ms=1, passed=False)
        self.mutate('independent-checks.json', change)
        self.assertFalse(m.verify(self.directory)['acceptancePassed'])

    def test_live_coalescing_does_not_replace_the_full_replay_terminal_check(self):
        self.mutate('independent-checks.json', lambda r: r['rooms'][0]['live'].update(finalSequence=9, finalTick=17998))
        self.assertTrue(m.verify(self.directory)['acceptancePassed'])

    def test_independent_seal_copy_cannot_differ_from_embedded_report(self):
        self.mutate('independent-long-1-sealed.json', lambda r: r['world'].update(acceptedSequence=9))
        with self.assertRaisesRegex(ValueError, 'seal artifact'): m.verify(self.directory)

    def test_acknowledged_flag_cannot_cover_another_connection(self):
        self.mutate('independent-long-1-player-results.json', lambda r: r.update(phases={'other-client': 'acknowledged'}))
        with self.assertRaisesRegex(ValueError, 'acknowledgment'): m.verify(self.directory)

    def test_csv_changed_with_an_updated_hash_still_needs_exact_statistics(self):
        path = self.directory / 'independent-long-1-report.csv'
        rows = list(csv.DictReader(io.StringIO(path.read_text(encoding='utf-8-sig')))); rows[0]['health'] = '20'
        with path.open('w', encoding='utf-8-sig', newline='') as target:
            writer = csv.DictWriter(target, fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
        self.mutate('independent-checks.json', lambda r: r['rooms'][0]['finalReportCsv'].update(sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        with self.assertRaisesRegex(ValueError, 'CSV statistics'): m.verify(self.directory)

    def test_csv_cannot_relabel_the_same_player_as_another_room(self):
        path = self.directory / 'independent-long-1-report.csv'
        rows = list(csv.DictReader(io.StringIO(path.read_text(encoding='utf-8-sig')))); rows[0]['playerRoomId'] = '2'
        with path.open('w', encoding='utf-8-sig', newline='') as target:
            writer = csv.DictWriter(target, fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
        self.mutate('independent-checks.json', lambda r: r['rooms'][0]['finalReportCsv'].update(sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        with self.assertRaisesRegex(ValueError, 'CSV session / room'): m.verify(self.directory)

    def test_other_rooms_must_really_advance_during_accepted_pause(self):
        def change(r): r['otherRooms'][0]['afterTick'] = r['otherRooms'][0]['beforeTick']
        self.mutate('independent-pause-isolation.json', change)
        self.mutate('independent-checks.json', lambda r: change(r['pauseIsolation']))
        with self.assertRaisesRegex(ValueError, 'did not advance'): m.verify(self.directory)

    def test_full_replay_cannot_skip_a_saved_frame(self):
        self.mutate('independent-checks.json', lambda r: r['rooms'][0]['replay'].update(frames=9))
        with self.assertRaisesRegex(ValueError, 'full replay'): m.verify(self.directory)

    def test_original_expiry_witness_and_per_player_accounting_are_required(self):
        self.mutate('independent-checks.json', lambda r: r['rooms'][0]['originalConnectionsAfterExpiry'].update(allOriginalAdmissions=False))
        with self.assertRaisesRegex(ValueError, 'admission witness'): m.verify(self.directory)

    def test_output_cannot_add_files_inside_the_preserved_input(self):
        output = self.directory / 'new-report.json'
        with patch('sys.argv', ['verify-independent-evidence', str(self.directory), '--output', str(output)]):
            with self.assertRaisesRegex(ValueError, 'preserved input'): m.main()
        self.assertFalse(output.exists())

    def test_exercise_pause_uses_saved_utc_interval_and_the_original_room(self):
        capture = datetime(2026, 11, 10, tzinfo=timezone.utc)
        pause = {'pausedTick': 40, 'accepted': 10, 'resumed': 11}
        paused, peer_ticks = [], []
        room1 = m.exercise_room_observer(1, capture, {'p1'}, pause, paused, [])
        room2 = m.exercise_room_observer(2, capture, {'p2'}, pause, paused, peer_ticks)

        def packet(room, time, tick, phase='Running', observed=10):
            return {'sequence': time, 'suspended': False, 'elapsedMilliseconds': time, 'observedSequence': observed,
                    'frame': {'phase': phase, 'tick': tick, 'players': [
                        {'id': f'p{room}', 'roomId': room, 'connected': True, 'rig': {'kind': 'Simulated'}, 'health': 100}]}}

        room1(packet(1, 100, 40, 'Paused'))
        room1(packet(1, 300, 40, 'Paused'))
        for time, tick in [(99, 39), (100, 40), (200, 42), (300, 44), (301, 45)]:
            room2(packet(2, time, tick))
        self.assertEqual([40, 42, 44], peer_ticks)
        for observe, bad in [(room2, packet(2, 200, 40, 'Paused')),
                             (room1, packet(1, 200, 41, 'Paused')),
                             (room1, packet(1, 200, 40, 'Paused', observed=11))]:
            with self.assertRaisesRegex(ValueError, 'Pause crossed'):
                observe(bad)
        with self.assertRaisesRegex(ValueError, 'original room roster'):
            room2(packet(1, 200, 42))


if __name__ == '__main__': unittest.main()
