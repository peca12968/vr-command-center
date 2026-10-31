import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('external_control', ROOT / 'scripts/start-desktop-control.py')
control = importlib.util.module_from_spec(spec); spec.loader.exec_module(control)

class ExternalControlTests(unittest.TestCase):
    def args(self, **changes):
        return SimpleNamespace(**({'client_mode': 'local', 'advertise_address': None, 'listen_address': None, 'visible_room': 1, 'results_seconds': 0} | changes))
    def test_local_mode_binds_loopback_by_default(self):
        args = self.args(); control.configure_network(args)
        self.assertEqual(('127.0.0.1', '127.0.0.1', 1), (args.advertise_address, args.listen_address, args.visible_room))
    def test_external_requires_an_explicit_advertised_address(self):
        with self.assertRaises(ValueError): control.configure_network(self.args(client_mode='external'))
        args = self.args(client_mode='external', advertise_address='192.168.1.100'); control.configure_network(args)
        self.assertEqual(('0.0.0.0', 0), (args.listen_address, args.visible_room))
    def test_declared_addresses_reject_ambiguous_multicast_or_wildcard_destination(self):
        for address in ['0.0.0.0', '224.0.0.1', '255.255.255.255', '127.1', '127.0.0.01', 'localhost', '::1', ' 127.0.0.1']:
            with self.subTest(address=address), self.assertRaises(ValueError): control.configure_network(self.args(client_mode='external', advertise_address=address))
    def test_specific_binding_must_agree_with_the_destination(self):
        with self.assertRaises(ValueError): control.configure_network(self.args(client_mode='external', advertise_address='192.168.1.100', listen_address='127.0.0.1'))
        args = self.args(client_mode='external', advertise_address='127.0.0.1', listen_address='127.0.0.1'); control.configure_network(args)
        self.assertEqual('127.0.0.1', args.listen_address)
    def test_local_mode_does_not_advertise_a_different_network(self):
        with self.assertRaises(ValueError): control.configure_network(self.args(advertise_address='192.168.1.100'))
    def test_external_results_are_unknown_and_server_grace_is_not_reset(self):
        class Venue:
            args = SimpleNamespace(client_mode='external', results_seconds=0)
            def save(self, name, value): self.saved = value
        venue = Venue(); entry = {'name': 'session'}
        with patch.object(control.time, 'monotonic', return_value=100): self.assertEqual(136, control.retain_results(venue, entry))
        with patch.object(control.time, 'monotonic', return_value=120): self.assertEqual(136, control.retain_results(venue, entry))
        self.assertIsNone(venue.saved['allAcknowledged']); self.assertEqual({}, venue.saved['phases']); self.assertEqual(36, venue.saved['serverRetentionSeconds'])

if __name__ == '__main__': unittest.main()
