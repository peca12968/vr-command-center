"""Read-only journal evidence must reject corruption and keep application / ack apart."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('journal_analysis', ROOT / 'scripts/analyze-world-journal.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class JournalAnalysisTests(unittest.TestCase):
    def record(self, tag, data):
        payload = bytes([tag]) + (struct.pack('<q', data) if tag in (2, 3, 4) else json.dumps(data).encode())
        return struct.pack('<i', len(payload)) + payload + hashlib.sha256(payload).digest()

    def header(self, timestamp='2026-10-31T12:00:00+00:00'):
        return b'VRWORLD1' + self.record(0, {'captureStartedAtUtc': timestamp, 'sessionId': 'private'})

    def frame(self, sequence, observed=7, phase='Running', tick=1, suspended=False):
        return self.record(1, {'sequence': sequence, 'observedSequence': observed, 'elapsedMilliseconds': sequence * 100,
            'suspended': suspended, 'frame': {'phase': phase, 'tick': tick, 'players': [{'id': 'private'}]}})

    def analyze(self, data, **options):
        with tempfile.TemporaryDirectory(prefix='vr-journal-read-') as temporary:
            path = Path(temporary) / 'source.worldlog'; path.write_bytes(data)
            try: return m.analyze(path, 7, **options)
            finally: self.assertEqual(data, path.read_bytes(), 'Reader changed source bytes')

    def test_source_application_can_be_ahead_of_durable_ack(self):
        data = self.header() + self.frame(1, 6, 'Preparing', 0) + self.record(2, 1) + self.frame(2, tick=0) + self.frame(3)
        r = self.analyze(data, response_utc='2026-10-31T12:00:00.250+00:00')
        self.assertEqual(3, r['firstApplied']['worldSequence']); self.assertEqual(1, r['acknowledgedSequence'])
        self.assertEqual(2, r['unacknowledgedFrames']); self.assertFalse(r['complete']); self.assertFalse(r['sealed'])
        self.assertAlmostEqual(.05, r['firstAppliedCaptureSecondsAfterResponse']); self.assertEqual(hashlib.sha256(data).hexdigest(), r['sha256'])
        self.assertNotIn('private', json.dumps(r))

    def test_old_running_and_suspended_current_are_not_application(self):
        r = self.analyze(self.header() + self.frame(1, 6) + self.frame(2, suspended=True))
        self.assertIsNone(r['firstApplied'])

    def test_legacy_missing_capture_is_not_invented(self):
        r = self.analyze(self.header('') + self.frame(1), response_utc='2026-10-31T12:00:00+00:00')
        self.assertIsNone(r['firstApplied']['capturedAtUtc']); self.assertIsNone(r['firstAppliedCaptureSecondsAfterResponse'])

    def test_torn_length_payload_digest_and_bit_corruption_fail_without_repair(self):
        good = self.header() + self.frame(1)
        for data in [good + b'\x01', good[:-35], good[:-1], good[:-1] + bytes([good[-1] ^ 1])]:
            with self.subTest(bytes=len(data)), self.assertRaises(ValueError): self.analyze(data)

    def test_unknown_tag_missing_or_duplicate_header_and_bad_length_fail(self):
        for data in [b'BADMAGIC', b'VRWORLD1' + self.frame(1), self.header() + self.record(0, {}),
                     self.header() + self.record(9, {}), self.header() + struct.pack('<i', 1048576)]:
            with self.subTest(bytes=len(data)), self.assertRaises(ValueError): self.analyze(data)

    def test_frame_gaps_and_observation_rewinds_fail(self):
        for frames in [self.frame(2), self.frame(1) + self.frame(3), self.frame(1, 7) + self.frame(2, 6)]:
            with self.assertRaises(ValueError): self.analyze(self.header() + frames)

    def test_receipt_gap_ack_ahead_and_early_completion_or_seal_fail(self):
        for tag, sequence in [(2, 2), (3, 1), (4, 1)]:
            with self.assertRaises(ValueError): self.analyze(self.header() + self.frame(1) + self.record(tag, sequence))

    def test_complete_seal_and_terminal_frame_boundary(self):
        good = self.header() + self.frame(1, phase='Ended') + self.record(2, 1) + self.record(3, 1) + self.record(4, 1)
        r = self.analyze(good); self.assertTrue(r['complete']); self.assertTrue(r['sealed']); self.assertEqual(0, r['unacknowledgedFrames'])
        with self.assertRaises(ValueError): self.analyze(good + self.frame(2))

    def test_transitions_are_bounded_while_counts_and_last_frame_continue(self):
        r = self.analyze(self.header() + b''.join(self.frame(i, i) for i in range(1, 301)))
        self.assertEqual(256, len(r['transitions'])); self.assertEqual(300, r['transitionCount']); self.assertTrue(r['transitionsTruncated'])
        self.assertEqual(300, r['lastFrame']['worldSequence'])

    def test_naive_timestamp_is_rejected_rather_than_using_local_timezone(self):
        with self.assertRaises(ValueError): self.analyze(self.header('2026-10-31T12:00:00'))

    def test_expected_session_must_match_before_correlating_other_run_evidence(self):
        with self.assertRaises(ValueError): self.analyze(self.header() + self.frame(1), expected_session='different')
        self.assertEqual(1, self.analyze(self.header() + self.frame(1), expected_session='private')['firstApplied']['worldSequence'])


if __name__ == '__main__': unittest.main()
