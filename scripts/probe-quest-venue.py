"""Collect original Quest UDP preflight pairs before starting a five-room venue."""
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('quest_udp', ROOT / 'probe-quest-udp.py')
quest_udp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(quest_udp)
CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
ROOMS = tuple(range(1, 6))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(raw):
    def unique_fields(pairs):
        result = dict(pairs)
        require(len(result) == len(pairs), 'Duplicate JSON field.')
        return result

    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique_fields)


def read_plan_file(path):
    with path.open('rb') as source:
        raw = source.read(32769)
    require(len(raw) <= 32768, 'Network plan or device map is too large.')
    value = read_json(raw)
    require(type(value) is dict and type(value.get('version')) is int and value['version'] == 1, 'Expected a version 1 JSON file.')
    return value


def seat_rows(rows, field):
    require(type(rows) is list and 1 <= len(rows) <= 25, 'Expected 1 to 25 mapped Quest seats.')
    seats = {}
    for row in rows:
        require(type(row) is dict and row.keys() == {'roomId', 'seat', field}, 'Unexpected seat mapping fields.')
        room, seat, value = row['roomId'], row['seat'], row[field]
        require(type(room) is int and room in ROOMS and type(seat) is int and seat in ROOMS and type(value) is str,
                'Invalid Quest seat mapping.')
        require((room, seat) not in seats, 'Quest seat is listed more than once.')
        seats[room, seat] = value
    return seats


def load_plan(device_map_path, network_plan_path):
    device_map = read_plan_file(device_map_path)
    network = read_plan_file(network_plan_path)
    require(device_map.keys() == {'version', 'seats'} and network.keys() == {'version', 'mode', 'endpoints', 'sources'},
            'Unexpected device map or network plan fields.')
    serials = seat_rows(device_map['seats'], 'serial')
    sources = seat_rows(network['sources'], 'address')
    require(serials.keys() == sources.keys(), 'Network sources must match the mapped Quest seats exactly.')
    require(len(set(serials.values())) == len(serials) and all(re.fullmatch(r'[A-Za-z0-9\[][A-Za-z0-9._:%\[\]-]{0,127}', value)
            for value in serials.values()), 'Use distinct explicit ADB serials.')
    require(len({quest_udp.address(value) for value in sources.values()}) == len(sources), 'Use a distinct IPv4 for each mapped Quest.')
    mode = network['mode']
    require(mode in ('Independent', 'Linked'), 'Expected Independent or Linked venue mode.')
    expected = {ROOMS} if mode == 'Linked' else {(room,) for room in ROOMS}
    endpoints = network['endpoints']
    require(type(endpoints) is list and len(endpoints) == len(expected), 'Provide every game endpoint for the venue mode.')
    groups, used_bindings = {}, set()
    for row in endpoints:
        require(type(row) is dict and row.keys() == {'roomIds', 'address', 'port'}, 'Unexpected game endpoint fields.')
        rooms, address, port = row['roomIds'], row['address'], row['port']
        require(type(rooms) is list and all(type(room) is int for room in rooms) and tuple(rooms) in expected
                and tuple(rooms) not in groups and type(address) is str and type(port) is int and 1024 <= port <= 65535,
                'Invalid or repeated game endpoint.')
        binding = quest_udp.address(address), port
        require(binding not in used_bindings, 'A game binding is used by more than one endpoint.')
        used_bindings.add(binding)
        devices = [{'roomId': room, 'seat': seat, 'serial': serials[room, seat], 'address': sources[room, seat]}
                   for room, seat in sorted(serials) if room in rooms]
        groups[tuple(rooms)] = {'roomIds': rooms, 'address': address, 'port': port, 'devices': devices}
    return mode, [groups[rooms] for rooms in sorted(groups) if groups[rooms]['devices']]


def device_ready(adb, serial):
    result = subprocess.run([str(adb), '-s', serial, 'get-state'], capture_output=True, timeout=8, creationflags=CREATE_NO_WINDOW)
    return result.returncode == 0 and result.stdout.strip() == b'device'


def wait_for_listener(process, path, expected):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        require(process.poll() is None, 'UDP listener exited before binding.')
        with path.open('rb') as source:
            line = source.readline(4097)
        require(len(line) <= 4096, 'Invalid UDP listener response.')
        if line.endswith(b'\n'):
            require(read_json(line) == expected, 'UDP listener did not bind the requested endpoint.')
            return
        time.sleep(.05)
    raise ValueError('UDP listener did not report its binding.')


def probe_seat(shell, adb, directory, group, device, count, timeout_ms):
    room, seat = device['roomId'], device['seat']
    label = f'room-{room:02}-seat-{seat:02}'
    listener_path = directory / (label + '-listener.ndjson')
    probe_path = directory / (label + '-probe.json')
    stage = 'device'
    result = {'roomId': room, 'seat': seat, 'complete': False}
    try:
        require(device_ready(adb, device['serial']), 'ADB device is not ready.')
        stage = 'key'
        with tempfile.TemporaryDirectory(prefix='quest-venue-udp-') as work:
            key = Path(work) / 'probe.key'
            subprocess.run([*shell, '-NewKey', '-KeyFile', str(key)], capture_output=True, check=True, timeout=10,
                           creationflags=CREATE_NO_WINDOW)
            stage = 'listener'
            address, port, peer = group['address'], group['port'], device['address']
            seconds = math.ceil(count * timeout_ms / 1000) + 32
            command = [*shell, '-Mode', 'Listen', '-KeyFile', str(key), '-LocalAddress', address,
                       '-PeerAddress', peer, '-Port', str(port), '-Count', str(count), '-Seconds', str(seconds)]
            with listener_path.open('xb') as stream, subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                                                      creationflags=CREATE_NO_WINDOW) as listener:
                try:
                    wait_for_listener(listener, listener_path, {'version': 1, 'stage': 'listening', 'localAddress': address,
                                                               'peerAddress': peer, 'port': port})
                    stage = 'probe'
                    report = quest_udp.run_probe(argparse.Namespace(adb=adb, serial=device['serial'], key_file=key,
                        local_address=peer, peer_address=address, port=port, count=count, timeout_ms=timeout_ms))
                    with probe_path.open('x', encoding='utf-8', newline='\n') as destination:
                        json.dump(report, destination, separators=(',', ':'))
                        destination.write('\n')
                    require(report['complete'] is True, 'Quest probe did not complete.')
                    stage = 'pair'
                    require(listener.wait(timeout=8) == 0, 'UDP listener did not finish.')
                finally:
                    if listener.poll() is None:
                        listener.kill()
                        listener.wait(timeout=5)
            checked = subprocess.run([*shell, '-ListenerReport', str(listener_path), '-ProbeReport', str(probe_path)],
                                     capture_output=True, check=True, timeout=10, creationflags=CREATE_NO_WINDOW)
            pair = read_json(checked.stdout)
            require(pair.get('complete') is True and pair.get('stage') == 'pair-verified' and pair.get('port') == port
                    and pair.get('matched') == count and pair.get('exchangeSha256') == report.get('exchangeSha256')
                    and re.fullmatch(r'[0-9a-f]{64}', pair.get('exchangeSha256', '')), 'UDP report pair did not verify.')
        result.update(complete=True, stage='verified', exchangeSha256=pair['exchangeSha256'])
    except (OSError, ValueError, TypeError, AttributeError, KeyError, RecursionError, subprocess.SubprocessError):
        result['stage'] = stage
    if listener_path.is_file():
        result['listener'] = listener_path.name
    if probe_path.is_file():
        result['probe'] = probe_path.name
    return result


def probe_venue(shell, adb, mode, groups, directory, count, timeout_ms):
    directory.mkdir()
    deadline = time.monotonic() + 20 * 60
    results, exchanges = [], set()
    for group in groups:
        seats = []
        for device in group['devices']:
            seat = (probe_seat(shell, adb, directory, group, device, count, timeout_ms) if time.monotonic() < deadline
                    else {'roomId': device['roomId'], 'seat': device['seat'], 'complete': False, 'stage': 'budget'})
            if seat['complete']:
                exchange = seat['exchangeSha256']
                if exchange in exchanges:
                    seat.update(complete=False, stage='duplicate')
                exchanges.add(exchange)
            seats.append(seat)
            print(json.dumps({key: seat[key] for key in ('roomId', 'seat', 'complete', 'stage')}), file=sys.stderr, flush=True)
        complete = all(seat['complete'] for seat in seats)
        summary = {'roomIds': group['roomIds'], 'complete': complete, 'seats': seats}
        if complete:
            summary['udpSourcePreflights'] = [{key: seat[key] for key in ('listener', 'probe')} for seat in seats]
        results.append(summary)
    seats = [seat for group in results for seat in group['seats']]
    report = {'version': 1, 'scope': 'quest-udp-preflight-only', 'mode': mode, 'complete': all(seat['complete'] for seat in seats),
              'expectedSeats': len(seats), 'verifiedSeats': sum(seat['complete'] for seat in seats), 'groups': results}
    with (directory / 'preflight-report.json').open('x', encoding='utf-8', newline='\n') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', required=True, type=Path)
    parser.add_argument('--device-map', required=True, type=Path)
    parser.add_argument('--network-plan', required=True, type=Path)
    parser.add_argument('--output-directory', required=True, type=Path)
    parser.add_argument('--count', type=int, default=5)
    parser.add_argument('--timeout-ms', type=int, default=900)
    args = parser.parse_args()
    if not (1 <= args.count <= 20 and 200 <= args.timeout_ms <= 3000):
        parser.error('Use valid probe sample and timeout bounds.')
    try:
        mode, groups = load_plan(args.device_map, args.network_plan)
        adb = args.adb.resolve(strict=True)
        powershell = (shutil.which('powershell.exe') if os.name == 'nt' else None) or shutil.which('pwsh')
        require(adb.is_file() and powershell is not None, 'ADB or PowerShell is missing.')
        shell = [powershell, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'RemoteSigned',
                 '-File', str(ROOT / 'check-lan-udp.ps1')]
        report = probe_venue(shell, adb, mode, groups, args.output_directory, args.count, args.timeout_ms)
    except (OSError, ValueError, argparse.ArgumentTypeError, RecursionError):
        parser.exit(1, 'Quest venue preflight could not start or save its report. Check the maps, tools and new output directory.\n')
    print(json.dumps({key: report[key] for key in ('complete', 'expectedSeats', 'verifiedSeats')}))
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
