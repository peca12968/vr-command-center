import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'prepare-vr-session.py'


class QuestProvisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'connections'
        self.keys = self.root / 'keys.json'
        self.keys.write_text(json.dumps({'OperatorKeys': {'Master': 'master', 'GameServer': 'server'}}))
        self.issued = 0
        self.ended = False

    def provision(self, address, fail_on=None):
        def handle(request, timeout):
            path = urlsplit(request.full_url).path
            self.assertFalse((self.output / 'session').exists())
            if path == '/api/rooms':
                body = [{'id': 1, 'sessionId': None}]
            elif path == '/api/missions':
                body = {'id': 'mission'}
            elif path == '/api/sessions':
                body = {'id': 'session'}
            elif path.endswith('/players'):
                player = json.loads(request.data)
                body = {'players': [{'id': player['playerId'], 'admissionId': 'admission'}]}
            elif path.endswith('/join-ticket'):
                self.assertEqual('admission', request.get_header('If-match-admission'))
                self.issued += 1
                if self.issued == fail_on:
                    raise OSError('Interrupted during ticket issuance')
                body = {'ticket': f'ticket-{self.issued}', 'expiresAtUtc': 'expiry'}
            elif path == '/api/sessions/session/commands':
                self.assertEqual('End', json.loads(request.data)['action'])
                self.ended = True
                body = {}
            else:
                self.fail(path)
            return io.BytesIO(json.dumps(body).encode())

        stdout = io.StringIO()
        with patch.object(sys, 'argv', [str(SCRIPT), '--server-address', address, '--players', '5',
                                        '--output', str(self.output), '--key-file', str(self.keys)]), redirect_stdout(stdout), \
                patch('urllib.request.urlopen', side_effect=handle):
            runpy.run_path(str(SCRIPT), run_name='__main__')
        return json.loads(stdout.getvalue())

    def test_invalid_address_stops_before_room_or_key_access(self):
        self.keys.unlink()
        for address in ('127.0.0.9', '0.0.0.0', '224.1.1.1', '255.255.255.255', 'localhost', '192.168.001.3'):
            with self.subTest(address=address), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                self.provision(address)
            self.assertEqual(2, error.exception.code)
            self.assertFalse(self.output.exists())

    def test_issue_all_five_then_publish(self):
        result = self.provision('192.0.2.10')
        self.assertEqual(5, len(result['players']))
        folder = Path(result['directory'])
        self.assertEqual([folder], list(self.output.iterdir()))
        server = json.loads((folder / 'server.json').read_text())
        self.assertEqual('0.0.0.0', server['listenAddress'])
        self.assertEqual('192.0.2.10', server['address'])
        for number, seat in enumerate(result['players'], 1):
            self.assertEqual({'role': 'Client', 'address': server['address'], 'port': server['port'],
                              'joinTicket': f'ticket-{number}'}, json.loads((folder / seat['file']).read_text()))
        self.assertFalse(self.ended)

    def test_interrupted_ticket_ends_own_session_and_leaves_no_delivery(self):
        with self.assertRaisesRegex(OSError, 'Interrupted'):
            self.provision('192.0.2.10', fail_on=3)
        self.assertEqual(3, self.issued)
        self.assertTrue(self.ended)
        self.assertEqual([], list(self.output.iterdir()))
