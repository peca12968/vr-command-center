"""Match the live source age to the packet delivered by SSE."""

from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from live_world_frame import read_live_frame


def sse(*events):
    return io.BytesIO(''.join(f'event: {name}\ndata: {json.dumps(data)}\n\n' for name, data in events).encode())


class LiveWorldFrameTests(unittest.TestCase):
    def setUp(self):
        self.header = {'acceptedSequence': 11, 'capturedAtUtc': '2026-11-16T00:00:01+00:00',
                       'header': {'sessionId': 'current', 'captureStartedAtUtc': '2026-11-16T00:00:00.0000000+00:00'}}
        self.frame = {'packet': {'sequence': 12, 'elapsedMilliseconds': 1200}}

    def test_age_uses_the_delivered_packet_when_it_is_newer_than_the_header(self):
        received = datetime(2026, 11, 16, 0, 0, 2, tzinfo=timezone.utc)
        with patch('live_world_frame.datetime', wraps=datetime) as clock:
            clock.now.return_value = received
            frame, observation = read_live_frame(sse(('header', self.header), ('status', {}), ('frame', self.frame)), 'current')
        self.assertEqual(self.frame, frame)
        self.assertEqual(11, observation['watchHeaderSequence'])
        self.assertEqual(12, observation['worldSequence'])
        self.assertEqual('2026-11-16T00:00:01.200000+00:00', observation['capturedAtUtc'])
        self.assertEqual(0.8, observation['sourceAgeSeconds'])

    def test_rejects_out_of_order_or_unrelated_recording(self):
        with self.assertRaisesRegex(RuntimeError, 'different session'):
            read_live_frame(sse(('header', self.header), ('frame', self.frame)), 'other')
        with self.assertRaisesRegex(RuntimeError, 'without its recording header'):
            read_live_frame(sse(('frame', self.frame)), 'current')
        self.frame['packet']['sequence'] = 10
        with self.assertRaisesRegex(RuntimeError, 'predates'):
            read_live_frame(sse(('header', self.header), ('frame', self.frame)), 'current')

    def test_legacy_header_can_be_read_without_a_fabricated_age(self):
        self.header['header'].pop('captureStartedAtUtc')
        frame, observation = read_live_frame(sse(('header', self.header), ('frame', self.frame)), 'current')
        self.assertEqual(self.frame, frame)
        self.assertIsNone(observation['sourceAgeSeconds'])


if __name__ == '__main__':
    unittest.main()
