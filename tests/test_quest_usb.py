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
    elseif ($KeyName -eq 'DEVPKEY_Device_Parent') { [pscustomobject]@{ Data = $node.parent } }
    else { throw 'Unexpected device property request.' }
}
'''


def node(instance, descriptors, *, kind='USB', problem=0, parent=None):
    return dict(InstanceId=instance, Class=kind, descriptors=descriptors, problem=problem, parent=parent)


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

    def test_only_a_unique_usable_transport_counts_as_connected(self):
        nodes = [node(USB_ROOT, [ADB_DESCRIPTOR])]
        for fields, other, state in [
                ('', '', 'transport-unavailable'),
                ('transport_id:9223372036854775808', '', 'transport-unavailable'),
                ('transport_id:4 transport_id:5', '', 'transport-unavailable'),
                ('transport_id:4', '(no serial number) no permissions transport_id:4', 'transport-ambiguous'),
                ('transport_id:4', 'unassigned offline transport_id:4 transport_id:7', 'transport-ambiguous'),
                ('transport_id:9223372036854775807', 'unassigned device transport_id:7', 'device')]:
            with self.subTest(fields=fields, other=other):
                report = self.diagnose(nodes, adb_reply(f'fixture-serial device {fields}\n{other}\n'))
                self.assertEqual(report['status'], 'adb-usb-' + state)
                self.assertEqual(report['adb']['matchingMetaUsb']['device'], int(state == 'device'))


@unittest.skipUnless(shutil.which('pwsh'), 'PowerShell is required')
class QuestUsbGroupTests(unittest.TestCase):
    def snapshot(self, roots, entries, expected, *, server='reachable', unobservable=False, seats=None, nodes=None):
        if nodes is None:
            nodes = [node(root, [ADB_DESCRIPTOR]) for root in roots] + [node(USB_PORTABLE, ['USB\\MS_COMP_MTP'])]
        fixture = dict(nodes=nodes, pnpUnavailable=unobservable, expected=expected,
                       inventory=dict(Status=server, Entries=entries, Unidentified=0), seats=seats)
        command = PNP_FIXTURE + '''
. $env:VR_QUEST_USB_SCRIPT
$inventory = ($env:VR_QUEST_USB_FIXTURE | ConvertFrom-Json -AsHashtable).inventory
$report = Get-QuestUsbReport $inventory $fixture.expected $fixture.seats
Write-QuestUsbReport $report
Write-QuestUsbReport $report -Summary
'''
        result = subprocess.run(['pwsh', '-NoProfile', '-NonInteractive', '-Command', command],
                                env={**os.environ, 'VR_QUEST_USB_SCRIPT': str(SCRIPT), 'VR_QUEST_USB_FIXTURE': json.dumps(fixture)},
                                capture_output=True, encoding='utf-8', timeout=15, check=True)
        self.assertNotIn('fixture-serial', result.stdout.lower())
        self.assertNotIn('generated&', result.stdout)
        self.assertNotIn('172.16.1.87', result.stdout)
        snapshot, summary = result.stdout.split('\n', 1)
        return json.loads(snapshot), summary

    def test_mapped_seats_report_only_their_own_usb_connection(self):
        seats = [dict(roomId=room, seat=seat, serial=f'fixture-serial{room}{seat}')
                 for room in range(1, 6) for seat in range(1, 6)]
        roots = [USB_ROOT + row['serial'][-2:] for row in seats]
        entries = {row['serial']: 'device' for row in seats}
        full, _ = self.snapshot(roots, entries, 0, seats=seats)
        self.assertEqual(full['mapped']['connected'], 25)
        self.assertIs(full['mapped']['allInDeviceState'], True)
        self.assertEqual(full['mapped']['seats'], [dict(roomId=s['roomId'], seat=s['seat'], state='device') for s in seats])
        entries.update({'fixture-serial11': 'unauthorized', 'fixture-serial12': 'offline', 'fixture-serial13': 'other'})
        del entries['fixture-serial14']
        # The unassigned, connected fifth-room device cannot fill a different missing seat.
        roots.pop(4)
        mapped, summary = self.snapshot(roots, entries, 0, seats=seats[:5])
        self.assertEqual([s['state'] for s in mapped['mapped']['seats']],
                         ['unauthorized', 'offline', 'other', 'adb-not-listed', 'usb-not-found'])
        self.assertEqual(mapped['mapped']['connected'], 0)
        self.assertIs(mapped['mapped']['allInDeviceState'], False)
        self.assertIn('第 1 房第 1 席：待頭盔授權', summary)

    def test_missing_transports_show_only_interfaces_observed_for_that_seat(self):
        seats = [dict(roomId=room, seat=1, serial=f'fixture-serial{room}') for room in range(1, 6)]
        roots = [USB_ROOT + str(room) for room in range(1, 6)]
        # Common product and interface IDs; only the Windows parent identifies each physical device.
        nodes = [node(USB_ADB, [ADB_DESCRIPTOR], parent=roots[1].lower(), problem=28),
                 node(USB_PORTABLE, [r'USB\MS_COMP_MTP'], parent=roots[0]),
                 node(USB_ADB + 'x', [ADB_DESCRIPTOR], parent=roots[2], problem=None),
                 node(USB_ADB + 'y', [ADB_DESCRIPTOR], parent=roots[3].replace('5011', '5346'), problem=28),
                 node(USB_ADB + 'z', [ADB_DESCRIPTOR], parent=None, problem=28),
                 *(node(root, [r'USB\COMPOSITE']) for root in roots[:4]), node(roots[4], [ADB_DESCRIPTOR])]
        for server, state in [('reachable', 'adb-not-listed'), ('unreachable', 'adb-inventory-unavailable')]:
            report, summary = self.snapshot([], {}, 0, nodes=nodes, seats=seats, server=server)
            rows = report['mapped']['seats']
            self.assertEqual([row['state'] for row in rows], [state] * 5)
            self.assertEqual([row.get('windowsEvidence') for row in rows], [
                ['portable-media'], ['adb-interface', 'adb-driver-problem'],
                ['adb-interface', 'adb-driver-state-unknown'], None, ['adb-interface']])
            self.assertIn('檔案傳輸介面', next(line for line in summary.splitlines() if '第 1 房第 1 席' in line))
            self.assertIn('驅動程式有問題', next(line for line in summary.splitlines() if '第 2 房第 1 席' in line))
            self.assertFalse(report['mapped']['allInDeviceState'])

    def test_transport_problems_identify_the_two_affected_seats_in_a_full_venue(self):
        seats = [dict(roomId=room, seat=seat, serial=f'fixture-serial{room}{seat}')
                 for room in range(1, 6) for seat in range(1, 6)]
        entries = {row['serial']: 'device' for row in seats}
        entries.update({'fixture-serial31': 'transport-unavailable', 'fixture-serial55': 'transport-ambiguous'})
        roots = [USB_ROOT + row['serial'][-2:] for row in seats]
        report, summary = self.snapshot(roots, entries, 25, seats=seats)
        self.assertEqual(report['mapped']['connected'], 23)
        self.assertFalse(report['mapped']['allInDeviceState'])
        self.assertFalse(report['group']['allExpectedInDeviceState'])
        self.assertIn('第 3 房第 1 席：缺少可用的 ADB 連線編號', summary)
        self.assertIn('第 5 房第 5 席：ADB 連線編號重複', summary)

    def test_ambiguous_missing_and_wireless_seats(self):
        serials = ['fixture-serial1', 'FIXTURE-SERIAL1', 'fixture-serial', '172.16.1.87:5555', 'fixture-serial2']
        seats = [dict(roomId=1, seat=i, serial=s) for i, s in enumerate(serials, 1)]
        roots = [USB_ROOT, USB_ROOT.replace('5011', '5346'), USB_ROOT + '1', USB_ROOT + '2']
        for server, missing, last in [('unreachable', False, 'adb-inventory-unavailable'),
                                      ('reachable', True, 'usb-inventory-unavailable')]:
            report, _ = self.snapshot(roots, {}, 0, server=server, unobservable=missing, seats=seats)
            states = [s['state'] for s in report['mapped']['seats']]
            self.assertEqual(states, ['ambiguous-map', 'ambiguous-map', 'usb-inventory-unavailable' if missing else
                                      'ambiguous-usb', 'not-usb-serial', last])
            self.assertFalse(report['mapped']['allInDeviceState'])

    def test_deployment_entry_reads_existing_map_and_returns_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'devices.json'
            rows = [dict(roomId=5, seat=2, serial='fixture-serial'), dict(roomId=1, seat=3, serial='fixture-serial3')]
            path.write_text(json.dumps(dict(version=1, seats=rows)), encoding='utf-8')
            cmd = PNP_FIXTURE + '\n& $env:VR_DEPLOY_SCRIPT -CheckSeatUsb -DeviceMap $env:VR_TEST_MAP\nexit $LASTEXITCODE'
            env = {**os.environ, 'VR_DEPLOY_SCRIPT': str(SCRIPT.with_name('deploy-quest.ps1')),
                   'VR_TEST_MAP': str(path), 'VR_QUEST_USB_FIXTURE': json.dumps(dict(nodes=[]))}
            result = subprocess.run(['pwsh', '-NonInteractive', '-NoProfile', '-Command', cmd], env=env,
                                    capture_output=True, encoding='utf-8', timeout=15)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertNotIn('fixture-serial', result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)['mapped']['seats'], [
                dict(roomId=1, seat=3, state='usb-not-found'), dict(roomId=5, seat=2, state='usb-not-found')])

            env['VR_QUEST_USB_FIXTURE'] = json.dumps(dict(nodes=[
                node(USB_ROOT, [r'USB\COMPOSITE']), node(USB_ADB, [ADB_DESCRIPTOR], parent=USB_ROOT, problem=28)]))
            diagnosed = subprocess.run(['pwsh', '-NonInteractive', '-NoProfile', '-Command', cmd], env=env,
                                       capture_output=True, encoding='utf-8', timeout=15)
            self.assertEqual(diagnosed.returncode, 1, diagnosed.stderr)
            missing, detected = json.loads(diagnosed.stdout)['mapped']['seats']
            self.assertNotIn('windowsEvidence', missing)
            self.assertEqual((detected['roomId'], detected['seat']), (5, 2))
            self.assertEqual(detected['windowsEvidence'], ['adb-interface', 'adb-driver-problem'])
            self.assertNotIn('fixture-serial', diagnosed.stdout + diagnosed.stderr)

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
