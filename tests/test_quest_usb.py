import json
import os
from pathlib import Path
import select
import shutil
import socket
import subprocess
import sys
import tempfile
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
'''


def node(instance, descriptors, *, kind='USB', problem=0):
    return dict(InstanceId=instance, Class=kind, descriptors=descriptors, problem=problem)


def adb_reply(text):
    payload = text.encode('ascii')
    return f'OKAY{len(payload):04x}'.encode('ascii') + payload


@unittest.skipUnless(shutil.which('pwsh'), 'PowerShell is required')
class QuestUsbTests(unittest.TestCase):
    def diagnose(self, nodes, reply, *, unobservable=False):
        from windows_firewall import WindowsFirewallLaunchError, require_silent_windows_launch

        requests = []
        local_socket = os.name == 'nt' and os.environ.get('VR_COMMAND_UNATTENDED') == '1'
        if os.name == 'nt' and not local_socket:
            try:
                require_silent_windows_launch(sys.executable)
            except WindowsFirewallLaunchError:
                local_socket = True
        family = 1 if local_socket else socket.AF_INET
        with tempfile.TemporaryDirectory() as directory, socket.socket(family, socket.SOCK_STREAM) as server:
            options = {}
            if local_socket:
                from windows_ipc_api import accept_unix, bind_unix, unix_address
                address = Path(directory).resolve() / 'adb.sock'
                bind_unix(server, unix_address(address))
                options['VR_QUEST_USB_SOCKET'] = str(address)
            else:
                server.bind(('127.0.0.1', 0))
                options['VR_QUEST_USB_PORT'] = str(server.getsockname()[1])
            if reply is not None:
                server.listen(1)
                server.settimeout(8)

                def serve():
                    if not select.select([server], [], [], 8)[0]:
                        return
                    connection = accept_unix(server) if local_socket else server.accept()[0]
                    with connection as client, client.makefile('rb') as stream:
                        client.settimeout(3)
                        size = stream.read(4)
                        requests.append(size + stream.read(int(size, 16)))
                        for start in range(0, len(reply), 3):
                            client.sendall(reply[start:start + 3])

                worker = Thread(target=serve, daemon=True)
                worker.start()
            command = PNP_FIXTURE + '\n& $env:VR_QUEST_USB_SCRIPT -AdbServerPort ([int]$env:VR_QUEST_USB_PORT)'
            if local_socket:
                command = PNP_FIXTURE + '''
. $env:VR_QUEST_USB_SCRIPT
$socket = [Net.Sockets.Socket]::new('Unix', 'Stream', 'Unspecified')
try {
    try {
        $socket.Connect([Net.Sockets.UnixDomainSocketEndPoint]::new($env:VR_QUEST_USB_SOCKET))
        $stream = [Net.Sockets.NetworkStream]::new($socket)
        try { $inventory = Read-AdbInventoryStream $stream } finally { $stream.Dispose() }
    } catch [Net.Sockets.SocketException] { $inventory = @{ Status = 'unreachable'; Entries = @{}; Unidentified = 0 } }
    Write-QuestUsbReport (Get-QuestUsbReport $inventory 0)
} finally { $socket.Dispose() }
'''
            result = subprocess.run(['pwsh', '-NoProfile', '-NonInteractive', '-Command', command],
                                    env={**os.environ, **options, 'VR_QUEST_USB_SCRIPT': str(SCRIPT),
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


@unittest.skipUnless(shutil.which('pwsh'), 'PowerShell is required')
class QuestUsbGroupTests(unittest.TestCase):
    def snapshot(self, roots, entries, expected, *, server='reachable', unobservable=False):
        nodes = [node(root, [ADB_DESCRIPTOR]) for root in roots] + [node(USB_PORTABLE, ['USB\\MS_COMP_MTP'])]
        fixture = dict(nodes=nodes, pnpUnavailable=unobservable, expected=expected,
                       inventory=dict(Status=server, Entries=entries, Unidentified=0))
        command = PNP_FIXTURE + '''
. $env:VR_QUEST_USB_SCRIPT
$inventory = ($env:VR_QUEST_USB_FIXTURE | ConvertFrom-Json -AsHashtable).inventory
$report = Get-QuestUsbReport $inventory $fixture.expected
Write-QuestUsbReport $report
Write-QuestUsbReport $report -Summary
'''
        result = subprocess.run(['pwsh', '-NoProfile', '-NonInteractive', '-Command', command],
                                env={**os.environ, 'VR_QUEST_USB_SCRIPT': str(SCRIPT), 'VR_QUEST_USB_FIXTURE': json.dumps(fixture)},
                                capture_output=True, encoding='utf-8', timeout=15, check=True)
        self.assertNotIn('fixture-serial', result.stdout.lower())
        self.assertNotIn('generated&', result.stdout)
        snapshot, summary = result.stdout.split('\n', 1)
        return json.loads(snapshot), summary

    def test_partial_inventory_including_wireless_and_ambiguous_devices(self):
        five = [USB_ROOT + str(i) for i in range(5)]
        one, _ = self.snapshot(five, {'fixture-serial0': 'device'}, 5)
        self.assertEqual(one['status'], 'adb-usb-partial-inventory')
        self.assertEqual(one['group']['unmatchedUsbRoots'], 4)
        self.assertFalse(one['group']['allExpectedInDeviceState'])
        roots = [USB_ROOT + str(i) for i in range(3)]
        # Two further physical roots share a serial and cannot establish a unique USB match.
        roots.extend([USB_ROOT, USB_ROOT.replace('5011', '5346')])
        report, summary = self.snapshot(roots, {'FIXTURE-SERIAL0': 'device', 'fixture-serial1': 'unauthorized',
                                                'fixture-serial': 'device', '172.16.1.87:5555': 'device'}, 5)
        self.assertEqual(report['status'], 'adb-usb-partial-inventory')
        self.assertEqual(report['group'], dict(expected=5, metaUsbRoots=5, matchedRoots=2, unmatchedUsbRoots=3,
                                               allExpectedInDeviceState=False))
        self.assertEqual(report['adb']['unmatchedEntries'], 2)
        self.assertIn('已連線 1、待授權 1', summary)
        self.assertIn('3 台無法對應', summary)

    def test_full_group_must_match_the_requested_size_and_state(self):
        roots = [USB_ROOT + str(i) for i in range(25)]
        entries = {'fixture-serial' + str(i): 'device' for i in range(25)}
        for expected, state, ready in [(25, 'device', True), (24, 'device', False), (25, 'offline', False)]:
            with self.subTest(expected=expected, state=state):
                report, summary = self.snapshot(roots, {**entries, 'fixture-serial0': state}, expected)
                self.assertEqual(report['group']['matchedRoots'], 25)
                self.assertEqual(report['group']['allExpectedInDeviceState'], ready)
                self.assertEqual('已核對預期台數及 USB 偵錯連線' in summary, ready)

    def test_unknown_inventories(self):
        for server, missing_windows in [('unreachable', False), ('invalid-response', False), ('reachable', True)]:
            with self.subTest(server=server, missing_windows=missing_windows):
                report, summary = self.snapshot([USB_ROOT], {}, 1, server=server, unobservable=missing_windows)
                self.assertEqual(report['group']['metaUsbRoots'], None if missing_windows else 1)
                self.assertIsNone(report['group']['matchedRoots'])
                self.assertIsNone(report['group']['unmatchedUsbRoots'])
                self.assertIsNone(report['group']['allExpectedInDeviceState'])
                self.assertIn('無法比對', summary)
