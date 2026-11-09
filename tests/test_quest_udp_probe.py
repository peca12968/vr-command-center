import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('quest_udp', ROOT / 'scripts/probe-quest-udp.py')
quest_udp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(quest_udp)
SERVER = '127.0.0.1'
PEER = '127.0.0.2'
POWERSHELL = shutil.which('powershell.exe' if os.name == 'nt' else 'pwsh')
EDITOR_JDK = Path('F:/Tools/UnityEditors/6000.3.27f1/Editor/Data/PlaybackEngines/AndroidPlayer/OpenJDK')


def java_tool(name):
    suffix = '.exe' if os.name == 'nt' else ''
    for root in (os.environ.get('VR_COMMAND_JDK'), os.environ.get('JAVA_HOME'), EDITOR_JDK if os.name == 'nt' else None):
        if root:
            candidate = Path(root) / 'bin' / (name + suffix)
            if candidate.is_file():
                return str(candidate)
    return shutil.which(name)


@unittest.skipUnless(java_tool('javac') and java_tool('java'), 'A JDK is required for the Quest probe protocol checks')
class QuestUdpProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = tempfile.TemporaryDirectory(prefix='quest-udp-test-')
        cls.addClassCleanup(work.cleanup)
        cls.classes = Path(work.name)
        subprocess.run([java_tool('javac'), '--release', '8', '-d', str(cls.classes),
                        str(ROOT / 'tools/QuestUdpProbe/Probe.java')], check=True, capture_output=True, timeout=20)
        cls.java = [java_tool('java'), '-cp', str(cls.classes), 'com.vrcommand.udpprobe.Probe']

    def setUp(self):
        work = tempfile.TemporaryDirectory(prefix='quest-udp-session-')
        self.addCleanup(work.cleanup)
        self.work = Path(work.name)
        self.secret = bytes(range(32))
        self.key = self.work / 'probe.key'
        self.key.write_bytes(base64.b64encode(self.secret))

    def command(self, port, count, timeout, peer=SERVER):
        return [*self.java, str(self.key), PEER, peer, str(port), str(count), str(timeout)]

    @unittest.skipUnless(POWERSHELL, 'PowerShell is required for Windows listener interoperability')
    def test_java_probe_pairs_with_original_windows_listener(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserve:
            reserve.bind((SERVER, 0))
            port = reserve.getsockname()[1]
        shell = [POWERSHELL, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'RemoteSigned',
                 '-File', str(ROOT / 'scripts/check-lan-udp.ps1')]
        listener_report = self.work / 'listener.ndjson'
        with listener_report.open('xb') as stream, subprocess.Popen(
            [*shell, '-Mode', 'Listen', '-KeyFile', str(self.key), '-LocalAddress', SERVER, '-PeerAddress', PEER,
             '-Port', str(port), '-Count', '3', '-Seconds', '10'], stdout=stream, stderr=subprocess.STDOUT,
        ) as listener:
            try:
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    if b'\n' in listener_report.read_bytes():
                        self.assertEqual('listening', json.loads(listener_report.read_bytes().splitlines()[0])['stage'])
                        break
                    self.assertIsNone(listener.poll())
                    time.sleep(.04)
                else:
                    self.fail('Windows listener did not bind')
                probe = subprocess.run(self.command(port, 3, 900), capture_output=True, check=True, timeout=8)
                self.assertEqual(0, listener.wait(timeout=5))
            finally:
                if listener.poll() is None:
                    listener.kill()
        listener_final = json.loads(listener_report.read_bytes().splitlines()[-1])
        probe_final = json.loads(probe.stdout)
        self.assertEqual(3, probe_final['matched'])
        self.assertEqual(listener_final['exchangeSha256'], probe_final['exchangeSha256'])
        self.assertEqual([1, 2, 3], [sample['sample'] for sample in probe_final['samples']])
        probe_report = self.work / 'quest-probe.json'
        probe_report.write_bytes(probe.stdout)
        bind = (datetime.now(timezone.utc) + timedelta(seconds=2)).isoformat()
        paired = subprocess.run([*shell, '-ListenerReport', str(listener_report), '-ProbeReport', str(probe_report),
                                '-ExpectedServerAddress', SERVER, '-ExpectedGamePort', str(port),
                                '-ExpectedPeerAddresses', f'{SERVER},{PEER}', '-BindingObservedAtUtc', bind],
                               capture_output=True, check=True, timeout=8)
        self.assertEqual(1, json.loads(paired.stdout)['verifiedPeerIndex'])
        self.assertNotIn(PEER.encode(), paired.stdout)

    def test_rejects_wrong_port_bad_tag_and_oversized_reply(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as other:
            server.bind((SERVER, 0))
            other.bind((SERVER, 0))
            server.settimeout(5)
            with subprocess.Popen(self.command(server.getsockname()[1], 1, 600),
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE) as probe:
                try:
                    request, source = server.recvfrom(256)
                    self.assertEqual(PEER, source[0])
                    nonce = request.split(b':')[1]
                    prefix = b'VRLAN1R:' + nonce
                    reply = prefix + b':' + hmac.new(self.secret, prefix, hashlib.sha256).hexdigest().encode()
                    other.sendto(reply, source)
                    server.sendto(prefix + b':' + b'0' * 64, source)
                    server.sendto(reply + b'X', source)
                    output, _ = probe.communicate(timeout=5)
                finally:
                    if probe.poll() is None:
                        probe.kill()
        self.assertEqual(1, probe.returncode)
        report = json.loads(output)
        self.assertFalse(report['complete'])
        self.assertEqual(0, report['matched'])
        self.assertEqual([{'sample': 1, 'roundTripMs': None}], report['samples'])
        self.assertIsNone(report['exchangeSha256'])

    def test_key_and_address_failures_do_not_echo_inputs(self):
        invalid_address = subprocess.run(self.command(7777, 1, 200, '8.8.8.8'), capture_output=True, timeout=8)
        self.assertEqual(1, invalid_address.returncode)
        self.assertEqual('address', json.loads(invalid_address.stdout)['step'])
        self.assertNotIn(b'8.8.8.8', invalid_address.stdout + invalid_address.stderr)
        self.key.write_bytes(b'secret-invalid-key')
        invalid_key = subprocess.run(self.command(7777, 1, 200), capture_output=True, timeout=8)
        self.assertEqual(1, invalid_key.returncode)
        self.assertEqual('key', json.loads(invalid_key.stdout)['step'])
        self.assertNotIn(b'secret-invalid-key', invalid_key.stdout + invalid_key.stderr)


class QuestUdpAdbTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory(prefix='quest-udp-adb-test-')
        self.addCleanup(work.cleanup)
        root = Path(work.name)
        adb, key = root / 'adb.exe', root / 'probe.key'
        adb.touch()
        self.key = base64.b64encode(bytes(range(32)))
        key.write_bytes(self.key)
        self.args = SimpleNamespace(adb=adb, key_file=key, serial='probe-device', local_address=PEER, peer_address=SERVER,
                                    port=7777, count=1, timeout_ms=900)
        self.report = {'version': 1, 'stage': 'finished', 'mode': 'probe', 'localAddress': PEER, 'peerAddress': SERVER,
                       'port': 7777, 'requested': 1, 'matched': 1, 'samples': [{'sample': 1, 'roundTripMs': 2.3}],
                       'exchangeSha256': 'a' * 64, 'complete': True, 'scope': 'authenticated-udp-only',
                       'completedAtUtc': '2026-11-10T00:00:00Z'}

    @staticmethod
    def result(text=b''):
        return subprocess.CompletedProcess([], 0, text, b'')

    def output(self):
        return (quest_udp.PREFIX + json.dumps(self.report) + '\r\nINSTRUMENTATION_CODE: -1\r\n').encode()

    def test_adb_key_is_sent_only_on_private_stdin_and_cleaned(self):
        with patch.object(quest_udp.subprocess, 'run', side_effect=[self.result(), self.result(self.output()), self.result()]) as calls:
            self.assertEqual(self.report, quest_udp.run_probe(self.args))
        transfer, probe, cleanup = calls.call_args_list
        self.assertEqual(self.key, transfer.kwargs['input'])
        self.assertIsNone(probe.kwargs['input'])
        self.assertIsNone(cleanup.kwargs['input'])
        self.assertNotIn(self.key.decode(), repr([call.args for call in calls.call_args_list]))
        for call in (transfer, probe, cleanup):
            self.assertEqual(['-s', 'probe-device'], call.args[0][1:3])
        key_path = cleanup.args[0][-1]
        self.assertRegex(key_path, r'\Afiles/udp-[0-9a-f]{32}\.key\Z')
        self.assertIn(key_path, transfer.args[0][-1])
        self.assertIn(Path(key_path).name, probe.args[0])

    def test_bad_report_is_rejected_and_private_file_is_cleaned(self):
        self.report['peerAddress'] = '127.0.0.3'
        with patch.object(quest_udp.subprocess, 'run', side_effect=[self.result(), self.result(self.output()), self.result()]) as calls:
            with self.assertRaisesRegex(ValueError, 'requested probe'):
                quest_udp.run_probe(self.args)
        self.assertEqual(3, calls.call_count)
        self.assertIn('rm', calls.call_args.args[0])
        self.report['peerAddress'] = SERVER
        self.report.update(matched=0, complete=False, exchangeSha256=None, samples=[{'sample': 1, 'roundTripMs': None}])
        self.assertFalse(quest_udp.android_report(self.output(), self.args)['complete'])
