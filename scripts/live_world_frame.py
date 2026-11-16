"""Read a live SSE frame and measure that packet's capture age."""

from datetime import datetime, timedelta, timezone
import json


def read_live_frame(response, session_id):
    header = None
    kind = ''
    for _ in range(60):
        line = response.readline()
        if not line:
            break
        line = line.decode('utf-8').strip()
        if line.startswith('event: '):
            kind = line[7:]
        elif line.startswith('data: ') and kind == 'header':
            header = json.loads(line[6:])
            if header['header']['sessionId'] != session_id:
                raise RuntimeError('Live world belongs to a different session')
        elif line.startswith('data: ') and kind == 'frame':
            received = datetime.now(timezone.utc)
            value = json.loads(line[6:])
            if header is None:
                raise RuntimeError('Live world frame arrived without its recording header')
            packet = value['packet']
            if packet['sequence'] < header['acceptedSequence']:
                raise RuntimeError('Live world frame predates its recording header')
            start = header['header'].get('captureStartedAtUtc')
            captured = datetime.fromisoformat(start) if start else None
            if captured is not None:
                if captured.utcoffset() is None:
                    raise ValueError('Live world capture has no UTC offset')
                captured += timedelta(milliseconds=packet['elapsedMilliseconds'])
            return value, {
                'worldSequence': packet['sequence'],
                'watchHeaderSequence': header['acceptedSequence'],
                'elapsedMilliseconds': packet['elapsedMilliseconds'],
                'capturedAtUtc': captured.isoformat() if captured is not None else None,
                'receivedAtUtc': received.isoformat(),
                'sourceAgeSeconds': (received - captured).total_seconds() if captured is not None else None,
            }
