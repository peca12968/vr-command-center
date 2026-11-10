import hashlib
import importlib.util
import io
import json
from pathlib import Path
import ssl
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location('venue_operator', Path(__file__).resolve().parents[1]
                                             / 'scripts/check-venue-operator.py')
operator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(operator)
FINGERPRINT = hashlib.sha256(b'certificate fixture').hexdigest()
KEY = 'test-operator-key'


class Response(io.BytesIO):
    def __init__(self, status, body=b'', **headers):
        super().__init__(body)
        self.status = status
        self.headers = headers
        self.length = None

    def getheader(self, name, default=''):
        return self.headers.get(name, default)


def responses(role='RoomController', room=2, visible=(2,)):
    return [Response(200, b'<form id="login-form">', **{'Content-Type': 'text/html'}),
            Response(401, **{'WWW-Authenticate': 'Bearer'}),
            Response(401, **{'WWW-Authenticate': 'Bearer'}),
            Response(200, json.dumps({'role': role, 'roomId': room, 'id': 'private-operator-id'}).encode(),
                     **{'Content-Type': 'application/json'}),
            Response(200, json.dumps([{'id': value, 'capacity': 5, 'sessionId': 'private-session'}
                                      for value in visible]).encode(), **{'Content-Type': 'application/json'})]


class VenueOperatorTests(unittest.TestCase):
    def run_check(self, replies, role='room2', certificates=None, handshake_error=None):
        with patch.object(operator.http.client, 'HTTPSConnection') as https, patch.object(operator, 'operator_key', return_value=KEY) as key:
            connection = https.return_value
            connection.sock.getpeercert.return_value = b'certificate fixture'
            connection.sock.getpeercert.side_effect = certificates
            connection.getresponse.side_effect = replies
            connection.connect.side_effect = handshake_error
            report = operator.check('venue.example', 443, object(), FINGERPRINT, role)
        return report, connection.request.call_args_list, key.call_count

    def test_https_origin_only(self):
        self.assertEqual(('venue.example', 443), operator.endpoint('https://Venue.Example/'))
        self.assertEqual(('192.168.1.4', 8443), operator.endpoint('https://192.168.1.4:8443'))
        for origin in ('http://venue.example', 'https://x@venue.example', 'https://venue.example/#',
                       'https://venue.example/path', 'https://venue.example:0', 'https://venue.example\n'):
            with self.subTest(origin=origin), self.assertRaises(operator.CheckFailed):
                operator.endpoint(origin)

    def test_all_scopes_and_only_read_requests(self):
        for role, room in operator.ROLES.items():
            expected = [1, 2, 3, 4, 5] if room is None else [room]
            identity = 'Master' if room is None else 'RoomController'
            with self.subTest(role=role):
                report, calls, prompts = self.run_check(responses(identity, room, expected), role)
                self.assertTrue(report['complete'], report)
                self.assertEqual(expected, report['roomIds'])
                self.assertEqual(1, prompts)
                self.assertEqual([('GET', path) for path in ('/console/', '/api/me', '/api/rooms', '/api/me', '/api/rooms')],
                                 [call.args for call in calls])
                self.assertEqual([None, None, None, f'Bearer {KEY}', f'Bearer {KEY}'],
                                 [call.kwargs['headers'].get('Authorization') for call in calls])
                for private in (KEY, 'private-operator-id', 'private-session'):
                    self.assertNotIn(private, json.dumps(report))

    def test_certificate_changes_before_authenticated_request(self):
        report, calls, _ = self.run_check(responses(), certificates=[b'certificate fixture'] * 3 + [b'other'])
        self.assertEqual('certificate-fingerprint-mismatch', report['error'])
        self.assertEqual('operator-identity', report['failedCheck'])
        self.assertEqual(3, len(calls))
        self.assertTrue(all('Authorization' not in call.kwargs['headers'] for call in calls))

    def test_invalid_tls_never_reaches_http_or_key_prompt(self):
        report, calls, prompts = self.run_check([], handshake_error=ssl.SSLCertVerificationError())
        self.assertEqual('certificate-trust-or-hostname-failed', report['error'])
        self.assertEqual([], calls)
        self.assertEqual(0, prompts)

    def test_redirect_is_not_followed(self):
        replies = responses()
        replies[3] = Response(302, Location='https://elsewhere.example/' + KEY)
        report, calls, _ = self.run_check(replies)
        self.assertEqual('unexpected-http-302', report['error'])
        self.assertEqual(4, len(calls))
        self.assertNotIn(KEY, json.dumps(report))

    def test_anonymous_access_stops_before_key_prompt(self):
        replies = responses()
        replies[2] = Response(200, b'should not be accessible')
        report, calls, prompts = self.run_check(replies)
        self.assertEqual('anonymous-rooms', report['failedCheck'])
        self.assertEqual(0, prompts)
        self.assertEqual(3, len(calls))

    def test_wrong_role_and_scope(self):
        for role, replies, error in (('room2', responses('Master', None), 'operator-role-or-room-mismatch'),
                                     ('room2', responses(room=1), 'operator-role-or-room-mismatch'),
                                     ('room2', responses(visible=(1, 2)), 'visible-rooms-or-capacity-mismatch'),
                                     ('master', responses('Master', None, (1, 2, 3, 4, 4)), 'visible-rooms-or-capacity-mismatch')):
            with self.subTest(role=role, error=error):
                report, _, _ = self.run_check(replies, role)
                self.assertFalse(report['complete'])
                self.assertEqual(error, report['error'])

    def test_body_size_is_bounded(self):
        report, calls, prompts = self.run_check([Response(200, b'x' * (operator.BODY_LIMIT + 1),
                                                          **{'Content-Type': 'text/html'})])
        self.assertEqual('invalid-response-length', report['error'])
        self.assertEqual(1, len(calls))
        self.assertEqual(0, prompts)


if __name__ == '__main__':
    unittest.main()
