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
CHALLENGE = '12345678-1234-5678-1234-567812345678'


def witness(room):
    return {'version': 1, 'challenge': CHALLENGE, 'workstation': room, 'source': f'10.31.0.{20 + room}',
            'listener': '10.31.0.1', 'port': 443, 'observedAtUnixSeconds': 1794320000, 'signature': 'e' * 64}


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
    def run_check(self, replies, role='room2', certificates=None, handshake_error=None, challenge=None):
        with patch.object(operator.http.client, 'HTTPSConnection') as https, patch.object(operator, 'operator_key', return_value=KEY) as key:
            connection = https.return_value
            connection.sock.getpeercert.return_value = b'certificate fixture'
            connection.sock.getpeercert.side_effect = certificates
            connection.getresponse.side_effect = replies
            connection.connect.side_effect = handshake_error
            report = operator.check('venue.example', 443, object(), FINGERPRINT, role, challenge)
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

    def test_optional_witness_uses_the_same_cert_and_room_identity(self):
        value = witness(2)
        for response, success in ((value, True), (dict(value, workstation=3), False),
                                  (dict(value, challenge='different'), False)):
            reply = Response(200, json.dumps(response).encode(), **{'Content-Type': 'application/json'})
            report, calls, _ = self.run_check([*responses(), reply], challenge=CHALLENGE)
            self.assertEqual(success, report['complete'])
            self.assertEqual(('GET', '/api/operator-network/witness?challenge=' + CHALLENGE), calls[-1].args)
            self.assertEqual(f'Bearer {KEY}', calls[-1].kwargs['headers']['Authorization'])
            if success:
                self.assertEqual(value, report['networkWitness'])
            else:
                self.assertEqual('workstation-witness', report['failedCheck'])

    def test_venue_verification_submits_exact_reports_and_never_echoes_signatures(self):
        roles = list(operator.ROLES)
        expected = [witness(index)['source'] for index in range(6)]
        inventory = {'masterAddress': expected[0], 'roomAddresses': expected[1:]}
        files = {role: {'complete': True, 'origin': 'https://venue.example:443', 'expectedCertificateSha256': FINGERPRINT,
                        'expectedRole': role, 'networkWitness': witness(index)} for index, role in enumerate(roles)}
        files['inventory'] = inventory
        files['room5'] = witness(5)  # Original browser receipt, without the CLI wrapper.
        result = {'challenge': CHALLENGE, 'workstationAddresses': expected, 'listener': '10.31.0.1', 'port': 443}
        with patch.object(operator, 'local_json', side_effect=files.__getitem__), patch.object(operator, 'operator_key', return_value=KEY):
            with patch.object(operator, 'read_route', side_effect=[None, result]) as route:
                report = operator.verify_workstations('venue.example', 443, object(), FINGERPRINT, CHALLENGE, 'inventory', roles[::-1])
                self.assertTrue(report['complete'])
                self.assertEqual(expected, report['workstationAddresses'])
                self.assertNotIn('e' * 64, json.dumps(report))
                self.assertEqual('/api/operator-network/verify', route.call_args.args[4])
                self.assertEqual([witness(index) for index in range(5, -1, -1)], route.call_args.kwargs['body']['witnesses'])
            with patch.object(operator, 'read_route') as route, patch.object(operator, 'operator_key') as key:
                report = operator.verify_workstations('venue.example', 443, object(), FINGERPRINT, CHALLENGE, 'inventory', [*roles[:4], 'room3'])
                self.assertFalse(report['complete'])
                self.assertEqual([{'workstation': 3, 'reason': 'duplicate-role'}, {'workstation': 4, 'reason': 'missing-role'},
                                  {'workstation': 5, 'reason': 'missing-role'}], report['issues'])
                route.assert_not_called()
                key.assert_not_called()

    def test_workstation_rejection_returns_only_known_role_and_reason(self):
        first = {'workstation': 1, 'reason': 'expired', 'signature': 'private-signature'}
        second = {'workstation': 3, 'reason': 'source-mismatch', 'source': 'private-address'}
        for rows, accepted in [([second, first], True), ([first, first], False),
                               ([dict(first, workstation=True)], False), ([dict(first, reason='private-address')], False)]:
            with self.subTest(rows=rows), patch.object(operator.http.client, 'HTTPSConnection') as https:
                connection = https.return_value
                connection.sock.getpeercert.return_value = b'certificate fixture'
                value = {'code': 'operator-network-witnesses-rejected', 'issues': rows, 'error': 'private-server-text'}
                connection.getresponse.return_value = Response(400, json.dumps(value).encode(), **{'Content-Type': 'application/json'})
                with self.assertRaises(operator.CheckFailed) as raised:
                    operator.read_route('venue.example', 443, object(), FINGERPRINT, '/api/operator-network/verify',
                                        200, 'application/json', KEY, body={}, workstation_diagnostics=True)
                if accepted:
                    self.assertIsInstance(raised.exception, operator.WorkstationsRejected)
                    output = operator.rejected_workstations(raised.exception.issues)
                    self.assertEqual([{'workstation': 1, 'reason': 'expired'}, {'workstation': 3, 'reason': 'source-mismatch'}], output['issues'])
                    self.assertNotIn('private-', json.dumps(output))
                else:
                    self.assertEqual('unexpected-http-400', str(raised.exception))

    def test_verify_post_cannot_send_bearer_until_certificate_matches(self):
        with patch.object(operator.http.client, 'HTTPSConnection') as https:
            https.return_value.sock.getpeercert.return_value = b'other certificate'
            with self.assertRaisesRegex(operator.CheckFailed, 'certificate-fingerprint-mismatch'):
                operator.read_route('venue.example', 443, object(), FINGERPRINT, '/api/operator-network/verify',
                                    200, 'application/json', KEY, body={'challenge': CHALLENGE})
            https.return_value.request.assert_not_called()


if __name__ == '__main__':
    unittest.main()
