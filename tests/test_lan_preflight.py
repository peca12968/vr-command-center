import base64
from contextlib import contextmanager
from datetime import datetime, timedelta
import hashlib
import hmac
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
SHELL = shutil.which(os.environ.get('VR_COMMAND_POWERSHELL', 'powershell.exe' if os.name == 'nt' else 'pwsh'))
LOOPBACK = '127.0.0.1'


def packet(key, kind, nonce):
    prefix = f'VRLAN1{kind}:{nonce}'.encode('ascii')
    return prefix + b':' + hmac.new(key, prefix, hashlib.sha256).hexdigest().encode('ascii')


@unittest.skipUnless(SHELL, 'PowerShell is required for native UDP preflight checks')
class LanPreflightTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix='lan-preflight-')
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.key = self.root / 'probe.key'
        self.shell = [SHELL, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'RemoteSigned',
                      '-File', str(ROOT / 'scripts/check-lan-udp.ps1')]
        result = self.run_script('-NewKey', '-KeyFile', self.key)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'version': 1, 'stage': 'key-created'})

    def run_script(self, *args):
        return subprocess.run([*self.shell, *map(str, args)], capture_output=True, text=True, timeout=15)

    def options(self, port, count, *, key=None, peer=LOOPBACK, local=LOOPBACK):
        return ['-LocalAddress', local, '-PeerAddress', peer, '-Port', str(port), '-Count', str(count),
                '-KeyFile', str(key or self.key)]

    @contextmanager
    def listener(self, port, count, *, peer=LOOPBACK, seconds=10, filename='listener.ndjson'):
        path = self.root / filename
        with path.open('xb') as output:
            with subprocess.Popen(self.shell + ['-Mode', 'Listen', '-Seconds', str(seconds), *self.options(port, count, peer=peer)],
                                  stdout=output, stderr=subprocess.STDOUT) as process:
                try:
                    end = time.monotonic() + 8
                    while time.monotonic() < end:
                        log = path.read_text(encoding='utf-8')
                        if '\n' in log:
                            ready = json.loads(log.splitlines()[0])
                            self.assertEqual(ready, {'version': 1, 'stage': 'listening', 'localAddress': LOOPBACK,
                                                     'peerAddress': peer, 'port': port})
                            break
                        if process.poll() is not None:
                            self.fail(log)
                        time.sleep(.04)
                    else:
                        self.fail('Listener did not report its bound socket')
                    yield process, path
                finally:
                    if process.poll() is None:
                        process.kill()

    def test_key_is_created_once_and_errors_hide_private_values(self):
        original = self.key.read_bytes()
        self.assertEqual(len(base64.b64decode(original, validate=True)), 32)
        duplicate = self.run_script('-NewKey', '-KeyFile', self.key)
        self.assertEqual(duplicate.returncode, 1)
        self.assertEqual(json.loads(duplicate.stdout)['step'], 'key')
        self.assertEqual(self.key.read_bytes(), original)
        self.assertNotIn(original.decode('ascii'), duplicate.stdout)
        self.assertNotIn(str(self.key), duplicate.stdout)
        invalid = self.run_script('-Mode', 'Probe', *self.options(7777, 1, peer='192.168.050.2'))
        self.assertEqual(invalid.returncode, 1)
        self.assertEqual(json.loads(invalid.stdout)['step'], 'address')

    def test_both_processes_finish_and_the_port_can_be_reused(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserved:
            reserved.bind((LOOPBACK, 0))
            port = reserved.getsockname()[1]
        probe_address = '127.0.0.2'
        with self.listener(port, 3, peer=probe_address) as (listener, path):
            occupied = self.run_script('-Mode', 'Listen', *self.options(port, 1))
            self.assertEqual(occupied.returncode, 1)
            self.assertEqual(json.loads(occupied.stdout)['step'], 'bind')
            result = self.run_script('-Mode', 'Probe', *self.options(port, 3, local=probe_address))
            self.assertEqual(result.returncode, 0, result.stderr)
            probe = json.loads(result.stdout)
            self.assertTrue(probe['complete'])
            self.assertEqual(probe['scope'], 'authenticated-udp-only')
            self.assertEqual([item['sample'] for item in probe['samples']], [1, 2, 3])
            self.assertTrue(all(0 <= item['roundTripMs'] <= 900 for item in probe['samples']))
            self.assertEqual(listener.wait(timeout=5), 0)
            final = json.loads(path.read_text(encoding='utf-8').splitlines()[-1])
            self.assertEqual(final['matched'], 3)
            self.assertRegex(probe['exchangeSha256'], r'\A[0-9a-f]{64}\Z')
            self.assertEqual(probe['exchangeSha256'], final['exchangeSha256'])
        report = self.root / 'probe.json'
        report.write_text(result.stdout, encoding='utf-8-sig')
        listener_report = self.root / 'listener-tee.ndjson'
        listener_report.write_text(path.read_text(encoding='utf-8'), encoding='utf-16')
        paired = self.run_script('-ListenerReport', listener_report, '-ProbeReport', report)
        self.assertEqual(paired.returncode, 0, paired.stderr or paired.stdout)
        self.assertEqual(json.loads(paired.stdout), {'version': 1, 'stage': 'pair-verified', 'complete': True,
            'port': port, 'matched': 3, 'scope': 'authenticated-udp-only', 'exchangeSha256': probe['exchangeSha256']})
        finished = datetime.fromisoformat(final['completedAtUtc'])
        bind = (finished + timedelta(seconds=2)).isoformat()
        expected = ['-ExpectedServerAddress', LOOPBACK, '-ExpectedGamePort', str(port),
                    '-ExpectedPeerAddresses', f'{LOOPBACK},{probe_address}', '-BindingObservedAtUtc', bind]
        options = ['-ListenerReport', listener_report, '-ProbeReport', report]
        matched = self.run_script(*options, *expected)
        self.assertEqual(matched.returncode, 0, matched.stdout or matched.stderr)
        self.assertIs(json.loads(matched.stdout)['endpointVerified'], True)
        for index, wrong in ((1, '127.0.0.3'), (3, str(port-1)), (5, LOOPBACK),
                             (7, (finished - timedelta(seconds=1)).isoformat()),
                             (7, (finished + timedelta(minutes=31)).isoformat())):
            with self.subTest(index=index):
                mismatch = expected.copy(); mismatch[index] = wrong
                rejected = self.run_script(*options, *mismatch)
                self.assertEqual(rejected.returncode, 1, rejected.stdout or rejected.stderr)
                self.assertEqual(json.loads(rejected.stdout)['step'], 'binding')
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as next_owner:
            next_owner.bind((LOOPBACK, port))

    def test_wrong_authentication_and_replay_are_not_echoed(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.bind((LOOPBACK, 0))
            sender.settimeout(.35)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserved:
                reserved.bind((LOOPBACK, 0))
                port = reserved.getsockname()[1]
            key = base64.b64decode(self.key.read_bytes())
            with self.listener(port, 2) as (listener, path):
                target = (LOOPBACK, port)
                nonce = 'b' * 32
                sender.sendto(packet(bytes(byte ^ 255 for byte in key), 'Q', nonce), target)
                with self.assertRaises(socket.timeout):
                    sender.recvfrom(256)
                original = packet(key, 'Q', nonce)
                sender.sendto(original, target)
                self.assertEqual(sender.recvfrom(256), (packet(key, 'R', nonce), target))
                sender.sendto(original, target)
                with self.assertRaises(socket.timeout):
                    sender.recvfrom(256)
                fresh = 'a' * 32
                sender.sendto(packet(key, 'Q', fresh), target)
                self.assertEqual(sender.recvfrom(256), (packet(key, 'R', fresh), target))
                self.assertEqual(listener.wait(timeout=5), 0)
            final = json.loads(path.read_text(encoding='utf-8').splitlines()[-1])
            self.assertEqual(final['matched'], 2)
            text = f'VRLAN1\n{LOOPBACK}\n{LOOPBACK}\n{port}\n{fresh}\n{nonce}'
            self.assertEqual(final['exchangeSha256'], hashlib.sha256(text.encode('ascii')).hexdigest())

    def test_pair_rejects_reports_from_different_exchanges_on_the_same_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserved:
            reserved.bind((LOOPBACK, 0))
            port = reserved.getsockname()[1]
        reports = []
        for index in range(2):
            with self.listener(port, 2, filename=f'listener-{index}.ndjson') as (listener, path):
                completed = self.run_script('-Mode', 'Probe', *self.options(port, 2))
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(listener.wait(timeout=5), 0)
                reports.append((path, json.loads(completed.stdout)))
        path, first = reports[0]
        second = reports[1][1]
        self.assertNotEqual(first['exchangeSha256'], second['exchangeSha256'])
        self.assertEqual((first['port'], first['matched']), (second['port'], second['matched']))
        report = self.root / 'probe.json'
        for changed in (second, {**first, 'localAddress': '127.0.0.2'}, {**first, 'complete': False},
                        {**first, 'samples': []}, {**first, 'exchangeSha256': None}):
            with self.subTest(changed=changed):
                report.write_text(json.dumps(changed), encoding='utf-16')
                paired = self.run_script('-ListenerReport', path, '-ProbeReport', report)
                self.assertEqual(paired.returncode, 1, paired.stderr)
                self.assertEqual(json.loads(paired.stdout), {'version': 1, 'stage': 'failed', 'step': 'reports', 'complete': False})

    def test_probe_rejects_a_signed_reply_from_another_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as other:
            server.bind((LOOPBACK, 0))
            other.bind((LOOPBACK, 0))
            server.settimeout(6)
            options = self.options(server.getsockname()[1], 1)
            with subprocess.Popen(self.shell + ['-Mode', 'Probe', '-TimeoutMs', '600', *options],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as probe:
                try:
                    incoming, source = server.recvfrom(256)
                    nonce = incoming.decode('ascii').split(':')[1]
                    key = base64.b64decode(self.key.read_bytes())
                    other.sendto(packet(key, 'R', nonce), source)
                    stdout, stderr = probe.communicate(timeout=5)
                    self.assertEqual(probe.returncode, 1, stderr)
                    result = json.loads(stdout)
                    self.assertEqual(result['matched'], 0)
                    self.assertEqual(result['samples'], [{'sample': 1, 'roundTripMs': None}])
                finally:
                    if probe.poll() is None:
                        probe.kill()

    def test_listener_expires_with_no_packets_from_the_expected_peer(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.bind((LOOPBACK, 0))
            sender.settimeout(.4)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserved:
                reserved.bind((LOOPBACK, 0))
                port = reserved.getsockname()[1]
            with self.listener(port, 1, peer='127.0.0.2', seconds=5) as (listener, path):
                key = base64.b64decode(self.key.read_bytes())
                sender.sendto(packet(key, 'Q', 'c' * 32), (LOOPBACK, port))
                with self.assertRaises(socket.timeout):
                    sender.recvfrom(256)
                self.assertEqual(listener.wait(timeout=8), 1)
                result = json.loads(path.read_text(encoding='utf-8').splitlines()[-1])
                self.assertEqual(result['matched'], 0)
                self.assertFalse(result['complete'])


if __name__ == '__main__':
    unittest.main()
