import importlib.util
from pathlib import Path
import socket
import time
import unittest

spec=importlib.util.spec_from_file_location('udp_gate',Path(__file__).resolve().parents[1]/'scripts/udp_gate.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class UdpGateTests(unittest.TestCase):
    def setUp(self):
        self.server=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);self.server.bind(('127.0.0.1',0));self.server.settimeout(2)
        self.client=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);self.client.bind(('127.0.0.1',0));self.client.settimeout(2)
        self.gate=None
    def tearDown(self):
        if self.gate is not None:
            self.gate.close();self.assertFalse(self.gate.thread.is_alive());self.assertIsNone(self.gate.error)
        self.server.close();self.client.close()
    def gate_for(self,predicate=lambda:False,**kwargs):
        self.gate=m.LoopbackGate(self.server.getsockname()[1],predicate,**kwargs).start()
        self.client.sendto(b'client hello',('127.0.0.1',self.gate.port))
        data,self.reply=self.server.recvfrom(65536);self.assertEqual(b'client hello',data)
        return self.gate
    def until(self,predicate):
        deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            if predicate():return
            time.sleep(.005)
        self.fail('Gate observation timed out')
    def test_transparent_flow_preserves_opaque_bytes_and_server_endpoint(self):
        g=self.gate_for();payload=bytes(range(256))*2
        self.server.sendto(payload,self.reply);data,sender=self.client.recvfrom(65536)
        self.assertEqual(payload,data);self.assertEqual(('127.0.0.1',g.port),sender)
        self.assertEqual(0,g.counts['held']);self.assertFalse(g.report()['payloadsRecorded'])
    def test_delayed_packets_release_in_original_order(self):
        g=self.gate_for(lambda:True)
        self.server.sendto(b'first',self.reply);self.server.sendto(b'second',self.reply)
        self.until(lambda:g.counts['held']==2);g.release()
        self.assertEqual(b'first',self.client.recvfrom(65536)[0]);self.assertEqual(b'second',self.client.recvfrom(65536)[0])
        self.until(lambda:g.release_reason=='requested' and g.counts['released']==2)
    def test_drop_is_downstream_only_and_does_not_buffer(self):
        g=self.gate_for(lambda:True,mode='drop')
        self.server.sendto(b'lost',self.reply);self.until(lambda:g.counts['dropped']==1)
        self.client.settimeout(.1)
        with self.assertRaises(socket.timeout):self.client.recvfrom(65536)
        self.client.sendto(b'upstream still works',('127.0.0.1',g.port));self.assertEqual(b'upstream still works',self.server.recvfrom(65536)[0])
        self.assertEqual(0,g.counts['peakBytes']);g.release();self.until(lambda:g.release_reason=='requested')
        self.server.sendto(b'new reply',self.reply);self.client.settimeout(2);self.assertEqual(b'new reply',self.client.recvfrom(65536)[0])
    def test_packet_limit_releases_original_bytes_in_order(self):
        g=self.gate_for(lambda:True,max_packets=1)
        self.server.sendto(b'one',self.reply);self.server.sendto(b'two',self.reply)
        self.assertEqual(b'one',self.client.recvfrom(65536)[0]);self.assertEqual(b'two',self.client.recvfrom(65536)[0])
        self.assertEqual('queueLimit',g.release_reason);self.assertEqual(1,g.counts['peakPackets'])
    def test_size_filter_passes_small_opaque_packets_but_drops_large_ones(self):
        g=self.gate_for(lambda:True,mode='drop',pass_small_bytes=64)
        self.server.sendto(b's'*64,self.reply);self.server.sendto(b'L'*65,self.reply)
        self.assertEqual(b's'*64,self.client.recvfrom(65536)[0]);self.until(lambda:g.counts['dropped']==1)
        self.assertEqual(1,g.counts['smallPassed']);self.assertEqual(0,g.counts['peakBytes'])
    def test_byte_limit_does_not_retain_oversized_packet(self):
        g=self.gate_for(lambda:True,max_bytes=2)
        self.server.sendto(b'oversized',self.reply);self.assertEqual(b'oversized',self.client.recvfrom(65536)[0])
        self.assertEqual('queueLimit',g.release_reason);self.assertEqual(0,g.counts['peakBytes'])
    def test_hold_deadline_releases_without_an_operator(self):
        g=self.gate_for(lambda:True,max_hold_seconds=.1)
        self.server.sendto(b'deadline',self.reply);self.assertEqual(b'deadline',self.client.recvfrom(65536)[0])
        self.assertEqual('holdLimit',g.release_reason);self.assertGreaterEqual(g.report()['holdSeconds'],.1)
        duration=g.report()['holdSeconds'];time.sleep(.025);self.assertEqual(duration,g.report()['holdSeconds'])
    def test_second_client_cannot_use_the_gate(self):
        g=self.gate_for()
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as foreign:foreign.sendto(b'foreign',('127.0.0.1',g.port))
        self.until(lambda:g.counts['foreignDropped']==1);self.server.settimeout(.1)
        with self.assertRaises(socket.timeout):self.server.recvfrom(65536)
    def test_invalid_bounds_are_rejected_before_opening_a_socket(self):
        for kwargs in [{'mode':'unknown'},{'pass_small_bytes':65},{'max_hold_seconds':41},{'max_hold_seconds':0},{'max_packets':1025},{'max_bytes':2097153}]:
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):m.LoopbackGate(self.server.getsockname()[1],lambda:False,**kwargs)


if __name__=='__main__':unittest.main()
