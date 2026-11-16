import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from threading import Thread
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check-quest-usb.ps1'
sys.path.insert(0, str(SCRIPT.parent))
USB_ROOT = r'USB\VID_2833&PID_5011\fixture-serial'
USB_PORTABLE = r'USB\VID_2833&PID_5011&MI_00\generated&0&0000'
USB_ADB = r'USB\VID_2833&PID_5011&MI_04\generated&0&0004'
ADB_DESCRIPTOR = r'USB\Class_ff&SubClass_42&Prot_01'

PNP_FIXTURE = r'''
$fixture = $env:VR_QUEST_USB_FIXTURE | ConvertFrom-Json
function Get-PnpDevice([switch]$PresentOnly, [string]$ErrorAction) {
    if (-not $PresentOnly -or $fixture.pnpUnavailable) { throw 'Unobservable PnP fixture.' }
    $fixture.nodes
}
function Get-PnpDeviceProperty([string]$InstanceId, [string]$KeyName, [string]$ErrorAction) {
    $node = $fixture.nodes | Where-Object InstanceId -EQ $InstanceId
    if ($KeyName -eq 'DEVPKEY_Device_CompatibleIds') { [pscustomobject]@{ Data = $node.descriptors } }
    elseif ($KeyName -eq 'DEVPKEY_Device_ProblemCode') { [pscustomobject]@{ Data = $node.problem } }
    else { throw 'Unexpected device property request.' }
}
& $env:VR_QUEST_USB_SCRIPT -AdbServerPort ([int]$env:VR_QUEST_USB_PORT)
'''


def node(instance, descriptors, *, kind='USB', problem=0):
    return dict(InstanceId=instance, Class=kind, descriptors=descriptors, problem=problem)


def adb_reply(text):
    payload = text.encode('ascii')
    return f'OKAY{len(payload):04x}'.encode('ascii') + payload


@unittest.skipUnless(shutil.which('pwsh'), 'PowerShell is required')
class QuestUsbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from windows_firewall import WindowsFirewallLaunchError, require_silent_windows_launch

        try:
            require_silent_windows_launch(sys.executable)
        except WindowsFirewallLaunchError as error:
            raise unittest.SkipTest(str(error)) from error

    def diagnose(self, nodes, reply, *, unobservable=False):
        requests = []
        with socket.socket() as server:
            server.bind(('127.0.0.1', 0))
            if reply is not None:
                server.listen(1)
                server.settimeout(8)

                def serve():
                    with server.accept()[0] as client, client.makefile('rb') as stream:
                        client.settimeout(3)
                        size = stream.read(4)
                        requests.append(size + stream.read(int(size, 16)))
                        for start in range(0, len(reply), 3):
                            client.sendall(reply[start:start + 3])

                worker = Thread(target=serve, daemon=True)
                worker.start()
            result = subprocess.run(['pwsh', '-NoProfile', '-NonInteractive', '-Command', PNP_FIXTURE],
                                    env={**os.environ, 'VR_QUEST_USB_SCRIPT': str(SCRIPT),
                                         'VR_QUEST_USB_PORT': str(server.getsockname()[1]),
                                         'VR_QUEST_USB_FIXTURE': json.dumps(dict(nodes=nodes, pnpUnavailable=unobservable))},
                                    capture_output=True, encoding='utf-8', timeout=12)
            if reply is not None:
                worker.join(timeout=4)
                self.assertFalse(worker.is_alive())
                self.assertEqual(requests, [b'000ehost:devices-l'])
        self.assertEqual(result.returncode, 0, result.stderr)
        for value in ('fixture-serial', 'generated&', '172.16.1.87', 'ADB INTERNAL MESSAGE'):
            self.assertNotIn(value, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_mtp_and_unrelated_adb_do_not_count_as_meta_debugging(self):
        root = node(USB_ROOT, [r'USB\COMPOSITE'])
        mtp = node(USB_PORTABLE, [r'USB\MS_COMP_MTP'], kind='WPD')
        other = node(r'USB\VID_1234&PID_5678\other', [ADB_DESCRIPTOR])
        reply = adb_reply('172.16.1.87:5555\tdevice product:other model:Other\n')
        result = self.diagnose([root, mtp, other], reply)
        self.assertEqual(result['status'], 'meta-usb-without-adb-interface')
        self.assertEqual(result['windows'], dict(observed=True, metaUsbNodes=2, portableMediaInterfaces=1, adbInterfaces=0,
                                                adbInterfacesWithProblems=0, unknownInterfaceDescriptors=0, unknownAdbDriverStates=0))
        self.assertEqual(result['adb']['unmatchedEntries'], 1)
        self.assertEqual(result['status'], self.diagnose([root, mtp], None)['status'])

    def test_correlates_usb_states_and_never_counts_duplicate_rows_as_ready(self):
        nodes = [node(USB_ROOT, [r'USB\COMPOSITE']), node(USB_ADB, [ADB_DESCRIPTOR])]
        for state in ('device', 'unauthorized', 'offline', 'bootloader'):
            with self.subTest(state=state):
                reply = adb_reply(f'{"FIXTURE-SERIAL":<22} {state} usb:2-3 transport_id:4\n172.16.1.87:5555\tdevice\n'
                                  f'{"(no serial number)":<22} no permissions transport_id:12\n')
                result = self.diagnose(nodes, reply)
                expected = state if state != 'bootloader' else 'other'
                self.assertEqual(result['status'], 'adb-usb-' + expected)
                self.assertEqual(result['adb']['matchingMetaUsb'][expected], 1)
                self.assertEqual(result['adb']['unmatchedEntries'], 2)
        duplicate = adb_reply('fixture-serial\tdevice\nFIXTURE-SERIAL\tdevice\n')
        self.assertEqual(self.diagnose(nodes, duplicate)['status'], 'adb-usb-other')
        second = node(r'USB\VID_2833&PID_5346\another', [ADB_DESCRIPTOR])
        mixed = adb_reply('fixture-serial device\nanother unauthorized\n')
        self.assertEqual(self.diagnose([*nodes, second], mixed)['status'], 'adb-usb-mixed-states')

    def test_distinguishes_driver_error_server_error_and_unknown_usb_evidence(self):
        root = node(USB_ROOT, [r'USB\COMPOSITE'])
        interface = node(USB_ADB, [r'USB\COMPAT_VID_2833&Class_ff&SubClass_42&Prot_01'], problem=None)
        ready = adb_reply('')
        unavailable = self.diagnose([root, interface], None)
        self.assertEqual(unavailable['status'], 'adb-server-inventory-unavailable')
        self.assertEqual(unavailable['adb']['server'], 'unreachable')
        self.assertEqual(unavailable['windows']['unknownAdbDriverStates'], 1)
        invalid = self.diagnose([root, interface], b'OKAYzzzzADB INTERNAL MESSAGE')
        self.assertEqual(invalid['adb']['server'], 'invalid-response')
        self.assertEqual(self.diagnose([root, interface], ready)['status'], 'adb-usb-transport-unmatched')
        self.assertEqual(self.diagnose([root, dict(interface, problem=28)], ready)['status'], 'adb-usb-driver-problem')
        self.assertEqual(self.diagnose([root, dict(interface, descriptors=[])], ready)['status'], 'meta-usb-interface-descriptors-incomplete')
        self.assertEqual(self.diagnose([], ready)['status'], 'meta-usb-not-enumerated')
        self.assertEqual(self.diagnose([], ready, unobservable=True)['status'], 'windows-usb-inventory-unavailable')
