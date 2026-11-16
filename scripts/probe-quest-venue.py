"""Collect original Quest UDP preflight pairs before starting a five-room venue."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
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
FIELD_SPEC = importlib.util.spec_from_file_location('field_results', ROOT / 'verify-field-results.py')
field = importlib.util.module_from_spec(FIELD_SPEC)
FIELD_SPEC.loader.exec_module(field)
CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
PREFLIGHT_WINDOW = timedelta(minutes=30)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(raw):
    def unique_fields(pairs):
        result = dict(pairs)
        require(len(result) == len(pairs), 'Duplicate JSON field.')
        return result

    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique_fields)


def load_plan(device_map_path, network_plan_path, *, launcher_preview=None):
    serials = field.read_quest_device_map(device_map_path)
    mode, endpoints, sources = field.read_quest_network_plan(network_plan_path)
    require(serials.keys() == sources.keys(), 'Network sources must match the mapped Quest seats exactly.')
    if launcher_preview is not None:
        checked = field.check_udp_launcher_endpoints(launcher_preview, mode, endpoints)
        field.require(checked['topologyMatches'], 'The Quest network plan uses a different venue mode from the Windows preview')
        for group in checked['groups']:
            field.require(not group['issues'], 'Quest network plan differs from the Windows endpoint for room(s) '
                          + ', '.join(map(str, group['roomIds'])) + ' (' + ', '.join(group['issues']) + ')')
    groups = []
    for rooms, (address, port) in sorted(endpoints.items()):
        devices = [{'roomId': room, 'seat': seat, 'serial': serials[room, seat], 'address': sources[room, seat]}
                   for room, seat in sorted(serials) if room in rooms]
        if devices:
            groups.append({'roomIds': list(rooms), 'address': address, 'port': port, 'devices': devices})
    return mode, groups


def path_reference(path, directory):
    try:
        return os.path.relpath(path, directory)
    except ValueError:  # The original report can be on another Windows drive.
        return str(path)


def launcher_proof(plan_path, preview_path, directory):
    plan_path, preview_path = plan_path.resolve(strict=True), preview_path.resolve(strict=True)
    plan = field.read_udp_launcher_document(plan_path, preview=False)
    preview = field.read_udp_launcher_document(preview_path, preview=True)
    checked = field.compare_udp_launch_documents(plan, preview)
    field.require(checked['complete'], 'Use matching original Windows launch plan and preview files')
    endpoints = {rooms: (row['address'], row['port']) for rooms, row in plan[2].items()}
    summary = field.check_udp_launcher_endpoints(preview, checked['mode'], endpoints)
    field.require(summary['complete'], 'The original Windows plan and preview must use concrete matching IPv4 addresses')
    return {'launchBinding': {'plan': path_reference(plan_path, directory),
                              'preview': path_reference(preview_path, directory), **checked},
            'launcherPreview': summary}, preview


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


def report_bytes(path, limit=32768):
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    require(0 < len(raw) <= limit, 'Invalid original UDP report size.')
    return raw


def pair_metadata(listener, probe):
    raw = report_bytes(listener)
    completed = read_json(raw.splitlines()[-1])['completedAtUtc']
    return {'completedAtUtc': completed, 'listenerSha256': hashlib.sha256(raw).hexdigest(),
            'probeSha256': hashlib.sha256(report_bytes(probe)).hexdigest()}


def fresh(stamp, now):
    completed = datetime.fromisoformat(stamp)
    return completed.utcoffset() == timedelta(0) and timedelta(0) < now - completed <= PREFLIGHT_WINDOW


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
        metadata = pair_metadata(listener_path, probe_path)
        require(fresh(metadata['completedAtUtc'], datetime.now(timezone.utc)), 'Invalid listener completion time.')
        result.update(complete=True, stage='verified', exchangeSha256=pair['exchangeSha256'], **metadata)
    except (OSError, ValueError, TypeError, AttributeError, KeyError, RecursionError, subprocess.SubprocessError):
        result['stage'] = stage
    if listener_path.is_file():
        result['listener'] = listener_path.name
    if probe_path.is_file():
        result['probe'] = probe_path.name
    return result


def read_retry(path, mode, groups, plan_hash, count, launcher):
    previous = read_json(report_bytes(path, limit=256 * 1024))
    require(type(previous) is dict and field.integer(previous.get('version'), 1, 1) == 1
            and previous.get('scope') == 'quest-udp-preflight-only' and previous.get('mode') == mode
            and previous.get('planSha256') == plan_hash and type(previous.get('sampleCount')) is int
            and previous['sampleCount'] == count, 'Retry must use the original Quest plan and sample count.')
    field.require(('launchBinding' in previous) == (launcher is not None),
                  'Retry must preserve the original Windows launch proof')
    if launcher is not None:
        checked, _ = field.read_udp_launch_binding(previous, path.parent, mode)
        field.require(all(checked[key] == launcher['launchBinding'][key] for key in ('planSha256', 'previewSha256')),
                      'Retry requires the original Windows launch plan and preview bytes')
    originals = previous['groups']
    require(type(originals) is list and len(originals) == len(groups), 'Retry room groups differ.')
    seats = {}
    for original, group in zip(originals, groups, strict=True):
        require(type(original) is dict and original['roomIds'] == group['roomIds'] and type(original['seats']) is list
                and len(original['seats']) == len(group['devices']), 'Retry room groups differ.')
        for row, device in zip(original['seats'], group['devices'], strict=True):
            require(type(row) is dict and type(row.get('complete')) is bool
                    and all(type(row[key]) is int and row[key] == device[key] for key in ('roomId', 'seat')),
                    'Retry seats differ.')
            if row['complete']:
                seats[device['roomId'], device['seat']] = row
    return seats


def reuse_seat(row, previous_directory, directory, group, device, count, exchanges):
    try:
        listener, probe = ((previous_directory / row[key]).resolve(strict=True) for key in ('listener', 'probe'))
        metadata = pair_metadata(listener, probe)
        now = datetime.now(timezone.utc)
        if (listener == probe or row['exchangeSha256'] in exchanges
                or any(row[key] != value for key, value in metadata.items()) or not fresh(metadata['completedAtUtc'], now)):
            return None
        summary, _ = field.verify_udp_preflight((listener, probe),
            {'address': group['address'], 'port': group['port'], 'observedAtUtc': now.isoformat()},
            {field.ipv4(device['address'])})
        if summary['samples'] != count or summary['exchangeSha256'] != row['exchangeSha256']:
            return None
    except (OSError, ValueError, TypeError, AttributeError, IndexError, KeyError, RecursionError):
        return None
    retained = {'roomId': device['roomId'], 'seat': device['seat'], 'complete': True, 'stage': 'reused',
                'exchangeSha256': summary['exchangeSha256'], **metadata}
    for key, path in (('listener', listener), ('probe', probe)):
        retained[key] = path_reference(path, directory)
    return retained


def probe_venue(shell, adb, mode, groups, directory, count, timeout_ms, retry_report=None, *, launcher=None):
    plan_hash = hashlib.sha256(json.dumps([mode, groups], sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
    previous = read_retry(retry_report, mode, groups, plan_hash, count, launcher) if retry_report else {}
    directory.mkdir()
    deadline = time.monotonic() + 20 * 60
    results, exchanges = [], set()
    interrupted = False
    for group in groups:
        seats = []
        for device in group['devices']:
            room, number = device['roomId'], device['seat']
            seat = {'roomId': room, 'seat': number, 'complete': False, 'stage': 'not-attempted' if interrupted else 'budget'}
            if not interrupted and time.monotonic() < deadline:
                try:
                    row = previous.get((room, number))
                    retained = reuse_seat(row, retry_report.parent, directory, group, device, count, exchanges) if row else None
                    if retained is not None:
                        seat = retained
                    elif time.monotonic() < deadline:
                        seat = probe_seat(shell, adb, directory, group, device, count, timeout_ms)
                except KeyboardInterrupt:
                    interrupted = True
                    seat['stage'] = 'interrupted'
            if seat['complete']:
                exchange = seat['exchangeSha256']
                if exchange in exchanges:
                    seat.update(complete=False, stage='duplicate')
                exchanges.add(exchange)
            seats.append(seat)
            print(json.dumps({key: seat[key] for key in ('roomId', 'seat', 'complete', 'stage')}), file=sys.stderr, flush=True)
        results.append({'roomIds': group['roomIds'], 'seats': seats})

    checked_at = datetime.now(timezone.utc)
    for group in results:
        for seat in group['seats']:
            if seat['complete'] and not fresh(seat['completedAtUtc'], checked_at):
                seat.update(complete=False, stage='expired')
                print(json.dumps({key: seat[key] for key in ('roomId', 'seat', 'complete', 'stage')}), file=sys.stderr, flush=True)
        group['complete'] = all(seat['complete'] for seat in group['seats'])
        if group['complete']:
            group['udpSourcePreflights'] = [{key: seat[key] for key in ('listener', 'probe')} for seat in group['seats']]
    seats = [seat for group in results for seat in group['seats']]
    report = {'version': 1, 'scope': 'quest-udp-preflight-only', 'mode': mode, 'complete': all(seat['complete'] for seat in seats),
              'planSha256': plan_hash, 'sampleCount': count, 'interrupted': interrupted,
              'expectedSeats': len(seats), 'verifiedSeats': sum(seat['complete'] for seat in seats),
              'reusedSeats': sum(seat['stage'] == 'reused' for seat in seats), 'groups': results, **(launcher or {})}
    with (directory / 'preflight-report.json').open('x', encoding='utf-8', newline='\n') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', required=True, type=Path)
    parser.add_argument('--device-map', required=True, type=Path)
    parser.add_argument('--network-plan', required=True, type=Path)
    parser.add_argument('--launch-plan', type=Path, help='Original revision-guarded Windows launch plan')
    parser.add_argument('--launcher-preview', type=Path, help='Original successful Windows launcher preview')
    parser.add_argument('--output-directory', required=True, type=Path)
    parser.add_argument('--retry-report', type=Path, help='Original batch report to retain fresh, verified seats from')
    parser.add_argument('--count', type=int, default=5)
    parser.add_argument('--timeout-ms', type=int, default=900)
    args = parser.parse_args()
    if not (1 <= args.count <= 20 and 200 <= args.timeout_ms <= 3000):
        parser.error('Use valid probe sample and timeout bounds.')
    if (args.launch_plan is None) != (args.launcher_preview is None):
        parser.error('--launch-plan and --launcher-preview must be supplied together.')
    from windows_firewall import WindowsFirewallLaunchError, require_silent_windows_launch

    try:
        directory = args.output_directory.resolve()
        launcher, preview = (launcher_proof(args.launch_plan, args.launcher_preview, directory)
                             if args.launch_plan is not None else (None, None))
        mode, groups = load_plan(args.device_map, args.network_plan, launcher_preview=preview)
        adb = args.adb.resolve(strict=True)
        powershell = (shutil.which('powershell.exe') if os.name == 'nt' else None) or shutil.which('pwsh')
        require(adb.is_file() and powershell is not None, 'ADB or PowerShell is missing.')
        require_silent_windows_launch(adb)
        require_silent_windows_launch(powershell)
        shell = [powershell, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'RemoteSigned',
                 '-File', str(ROOT / 'check-lan-udp.ps1')]
        report = probe_venue(shell, adb, mode, groups, directory, args.count, args.timeout_ms, args.retry_report, launcher=launcher)
    except (field.EvidenceError, WindowsFirewallLaunchError) as error:
        parser.exit(1, f'Quest venue preflight rejected. {error}.\n')
    except (OSError, ValueError, argparse.ArgumentTypeError, TypeError, KeyError, RecursionError):
        parser.exit(1, 'Quest venue preflight could not start or save its report. Check the maps, retry report, tools and new output directory.\n')
    print(json.dumps({key: report[key] for key in ('complete', 'expectedSeats', 'verifiedSeats', 'reusedSeats', 'interrupted')}))
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
