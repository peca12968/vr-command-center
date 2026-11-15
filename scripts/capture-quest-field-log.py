"""Preserve original Quest logcat for one player or the mapped venue seats."""

import argparse
import asyncio
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid


spec = importlib.util.spec_from_file_location('field_results', Path(__file__).with_name('verify-field-results.py'))
field = importlib.util.module_from_spec(spec)
spec.loader.exec_module(field)
PID_CHECK_SECONDS = 5
STARTUP_SECONDS = 30


def read_connection(path):
    with path.open('rb') as file:
        data = file.read(4097)
    field.require(len(data) <= 4096, 'Player connection file is too large')
    config = field.read_json(data.decode('utf-8-sig'))
    field.require(type(config) is dict and config.get('role') == 'Client', 'Use the original player connection file')
    port = field.integer(config.get('port'), 1024, 65535)
    ticket = config.get('joinTicket')
    claims = re.fullmatch(r'v2\.([A-Za-z0-9_-]{100})\.[A-Za-z0-9_-]{43}', ticket) if isinstance(ticket, str) else None
    field.require(claims is not None, 'Use a v2 player connection file')
    payload = base64.urlsafe_b64decode(claims[1])
    field.require(payload[0] == 2 and 1 <= payload[49] <= 5 and payload[50] <= 4, 'Invalid player ticket claims')
    expected = {key: field.identity(str(uuid.UUID(bytes_le=payload[offset:offset + 16])))
                for key, offset in (('sessionId', 1), ('playerId', 17), ('admissionId', 33))}
    return port, dict(expected, roomId=payload[49])


def quest_pid(adb, timeout):
    try:
        result = subprocess.run([*adb, 'shell', 'pidof', 'com.vrcommand.quest'],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise field.EvidenceError('Quest process lookup timed out') from None
    pid = result.stdout.strip()
    field.require(result.returncode == 0 and re.fullmatch(rb'[1-9][0-9]{0,9}', pid)
                  and int(pid) <= 2**31 - 1, 'Expected one running Quest game process')
    return int(pid)


def report_ready(pid, **seat):
    print(json.dumps({'stage': 'capture-ready', 'logcatPid': pid, **seat}), file=sys.stderr, flush=True)


async def read_capture(child, adb, pid, port, admission, log, deadline, on_ready, openxr=None):
    startup_deadline = min(deadline, time.monotonic() + STARTUP_SECONDS)
    next_pid_check = time.monotonic() + PID_CHECK_SECONDS
    started = ready = final_seen = False
    xr_ready = openxr is None
    size = 0
    while True:
        now = time.monotonic()
        field.require(now < deadline, 'Capture timed out before the final disconnect')
        field.require(started or now < startup_deadline, 'Original Quest startup is unavailable')
        field.require(xr_ready or now < startup_deadline, 'Original Quest OpenXR launch marker is unavailable')
        if now >= next_pid_check:
            current = await asyncio.to_thread(quest_pid, adb, min(5, deadline - now))
            field.require(current == pid, 'The original Quest process changed')
            next_pid_check = time.monotonic() + PID_CHECK_SECONDS
            continue
        read_deadline = min(deadline, next_pid_check, deadline if ready else startup_deadline)
        try:
            line = await asyncio.wait_for(child.stdout.readline(), read_deadline - now)
        except TimeoutError:
            continue
        field.require(bool(line) and line.endswith(b'\n'), 'ADB logcat ended before the final disconnect')
        size += len(line)
        field.require(size <= field.MAX_FILE_BYTES, 'Quest logcat reached the capture size limit')
        log.write(line)
        entry = field.LOGCAT_UNITY.fullmatch(line.decode('utf-8').rstrip('\r\n'))
        if entry is None:
            continue
        process, message = entry.groups()
        if openxr is not None and field.quest_openxr_marker(process, message, openxr):
            field.require(not xr_ready, 'Original Quest OpenXR launch marker is repeated')
            xr_ready = True
        if message.startswith('VR_NETWORK_STARTED '):
            field.require(process == str(pid) and not started and field.client_startup_on_port(message, port),
                          'Quest startup differs from the original process or game port')
            started = True
        elif message.startswith(field.PLAYER_MARKERS):
            field.require(process == str(pid) and started, 'Player marker is outside the original Quest startup or process')
            if message.startswith('VR_CLIENT_DEBRIEF_FINAL '):
                field.require(ready, 'Original Quest OpenXR launch marker is unavailable')
                final_seen = True
            if final_seen and message == 'VR_CLIENT_DISCONNECTED':
                log.seek(0)
                captured = field.limited_read(log)
                _, result = field.quest_client_result(captured.decode('utf-8'), pid, port)
                field.require(type(result) is dict and type(result.get('version')) is int and result['version'] == 1
                              and type(result.get('roomId')) is int
                              and all(result.get(key) == value for key, value in admission.items()),
                              'Final result differs from the original player admission')
                remaining = deadline - time.monotonic()
                field.require(remaining > 0, 'Capture timed out before the original process could be checked')
                current = await asyncio.to_thread(quest_pid, adb, min(5, remaining))
                field.require(current == pid, 'The original Quest process changed')
                return {'version': 1, 'complete': True, 'logcatPid': pid, 'port': port, 'roomId': admission['roomId'], 'bytes': size,
                        'sha256': hashlib.sha256(captured).hexdigest(), 'scope': 'quest-logcat-only'}
        if started and xr_ready and not ready:
            ready = True
            on_ready(pid)


def check_device_identity(adb, expected, timeout):
    field.require(timeout > 0, 'Capture timed out before the Quest device identity could be checked')
    try:
        result = subprocess.run([*adb, 'shell', 'getprop', 'ro.serialno'], capture_output=True, timeout=min(5, timeout))
    except subprocess.TimeoutExpired:
        raise field.EvidenceError('Quest device identity could not be read') from None
    serial = re.fullmatch(rb'([A-Za-z0-9][A-Za-z0-9._-]{0,127})\r?\n?', result.stdout)
    field.require(result.returncode == 0 and serial is not None and not re.fullmatch(rb'unknown|0+', serial[1], re.I),
                  'Quest device identity could not be read')
    salt, digest = expected
    field.require(field.quest_deployment_fingerprint(salt, serial[1].decode('ascii').upper()) == digest,
                  'Quest device identity differs from the original deployment')


async def capture(adb, port, admission, output, seconds, on_ready=report_ready, *, device_identity=None, openxr=None):
    partial = output.with_name(output.name + '.partial')
    field.require(not os.path.lexists(output) and not os.path.lexists(partial), 'Choose a new capture output path')
    deadline = time.monotonic() + seconds
    if device_identity is not None:
        await asyncio.to_thread(check_device_identity, adb, device_identity, deadline - time.monotonic())
    remaining = deadline - time.monotonic() if device_identity is not None else seconds
    field.require(remaining > 0, 'Capture timed out before checking the Quest process')
    pid = await asyncio.to_thread(quest_pid, adb, min(5, remaining))
    field.require(openxr is None or pid == openxr[0], 'Quest process differs from the original OpenXR launch')
    with partial.open('x+b') as log:
        child = await asyncio.create_subprocess_exec(*adb, 'logcat', '-b', 'main', f'--pid={pid}',
                                                    '-v', 'threadtime', '-s', 'Unity:I',
                                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        try:
            report = await read_capture(child, adb, pid, port, admission, log, deadline, on_ready, openxr)
        finally:
            if child.returncode is None:
                try:
                    child.kill()
                except ProcessLookupError:
                    pass
            await asyncio.wait_for(child.communicate(), 5)
        if device_identity is not None:
            await asyncio.to_thread(check_device_identity, adb, device_identity, deadline - time.monotonic())
        log.seek(0)
        with output.open('xb') as ready:
            try:
                shutil.copyfileobj(log, ready)
                ready.flush()
            except OSError:
                ready.close()
                output.unlink()
                raise
    partial.unlink()
    return report


def venue_plan(bundle, device_map, partial):
    pwsh = shutil.which('pwsh')
    field.require(pwsh is not None, 'Install PowerShell 7 to read the original deployment ZIP')
    command = [pwsh, '-NoProfile', '-NonInteractive', '-File', str(Path(__file__).with_name('deploy-quest.ps1')),
               '-ReadCapturePlan', '-VenueBundle', str(bundle.resolve()), '-DeviceMap', str(device_map.resolve())]
    if partial:
        command.append('-AllowPartialMap')
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20)
    except subprocess.TimeoutExpired:
        raise field.EvidenceError('Deployment ZIP and device map validation timed out') from None
    field.require(result.returncode == 0, 'Check the original deployment ZIP and version 1 device map')
    return field.read_json(result.stdout.decode('utf-8-sig'))


def retry_capture_plan(plan, report_path):
    report = field.read_quest_capture_report(report_path, plan['topology'])
    field.require(report.get('deploymentSha256') == plan.get('deploymentSha256'),
                  'Retry with the same original Quest deployment report as the first capture')
    seats = {(row['roomId'], row['seat']): row for row in plan['seats']}
    retry = []
    for row in report['seats']:
        original = seats.get((row['roomId'], row['seat']))
        field.require(original is not None and row['sessionId'] == original['sessionId'] and row['port'] == original['port'],
                      'Prior Quest capture report does not match the original deployment seats')
        if not row['complete']:
            retry.append(original)
    field.require(retry, 'Prior Quest capture report has no incomplete seats')
    return {**plan, 'seats': retry}


def bind_deployment(plan, path):
    report, raw = field.read_quest_document(path)
    seats = plan['seats']
    devices = report.get('devices')
    field.require(report.get('phase') == 'deployment' and report.get('topology') == plan['topology']
                  and report.get('complete') is report.get('managementVerified') is True
                  and field.integer(report.get('apkVerificationVersion'), 1, 1)
                  and type(devices) is list and len(devices) == len(seats),
                  'Provide the completed Quest deployment report for the original mapped seats')
    version_code = field.integer(report.get('expectedVersionCode'), 1, 2**31 - 1)
    require_openxr = report.get('requireOpenXR', False)
    field.require(type(require_openxr) is bool and (not require_openxr or version_code >= 74),
                  'Invalid Quest OpenXR deployment option for the original release')
    apk_digest = report.get('expectedApkSha256')
    field.require(type(apk_digest) is str and re.fullmatch(r'[0-9a-f]{64}', apk_digest), 'Quest deployment report lacks a verified release APK')
    proof, _ = field.quest_deployment_retry_proof(report, len(seats))
    field.require(proof is not None and proof['venueSha256'] == plan['venueSha256'],
                  'Quest deployment report does not match the original venue ZIP')
    device_map = {(row['roomId'], row['seat']): row['serial'] for row in seats}
    field.require(field.quest_deployment_map_fingerprint(proof['salt'], device_map) == proof['mapSha256'],
                  'Quest deployment report does not match the original device map')
    bound_seats = []
    for seat, device, fingerprint in zip(seats, devices, proof['devices'], strict=True):
        field.require(type(device) is dict and device.get('status') == 'launch-requested'
                      and device.get('apkVerified') is device.get('filesVerified') is True
                      and field.integer(device.get('versionCode'), 1) == version_code
                      and all(type(device.get(key)) is type(seat[key]) and device[key] == seat[key]
                              for key in ('roomId', 'seat', 'port', 'sessionId', 'playerId', 'admissionId')),
                      'Quest deployment report differs from an original admitted seat')
        opening = field.quest_openxr_proof(device, require_openxr)
        bound_seats.append({**seat, 'deviceIdentity': (proof['salt'], fingerprint), 'openXR': opening})
    field.require(not require_openxr or len({row['openXR'][1] for row in bound_seats}) == len(bound_seats),
                  'Quest OpenXR launch nonce was reused between seats')
    return {**plan, 'deploymentSha256': hashlib.sha256(raw).hexdigest(),
            'seats': bound_seats}


async def capture_venue(adb, plan, directory, seconds):
    directory.mkdir()
    ready = 0
    failed = False

    async def capture_seat(row):
        nonlocal ready, failed
        seat = {'roomId': row['roomId'], 'seat': row['seat']}
        source = dict(seat, sessionId=row['sessionId'], port=row['port'])
        admission = {key: row[key] for key in ('sessionId', 'playerId', 'admissionId', 'roomId')}
        log = directory / f"room-{seat['roomId']:02}-seat-{seat['seat']:02}-logcat.txt"

        def on_ready(pid):
            nonlocal ready
            report_ready(pid, **seat)
            ready += 1
            if ready == len(plan['seats']) and not failed:
                print(json.dumps({'stage': 'venue-capture-ready', 'seats': ready}), file=sys.stderr, flush=True)

        try:
            report = await capture([*adb, '-s', row['serial']], source['port'], admission, log, seconds, on_ready,
                                   device_identity=row.get('deviceIdentity'), openxr=row.get('openXR'))
        except (field.EvidenceError, OSError, UnicodeError, ValueError, TimeoutError, RecursionError) as error:
            failed = True
            reason = str(error) if isinstance(error, field.EvidenceError) else 'Check ADB and the capture directory'
            print(json.dumps({'stage': 'capture-failed', **seat, 'reason': reason}), file=sys.stderr, flush=True)
            partial = log.with_name(log.name + '.partial')
            return {**source, 'complete': False, 'reason': reason, **({'partial': partial.name} if partial.is_file() else {})}
        return {**source, 'complete': True, 'log': log.name, 'logcatPid': report['logcatPid'],
                'bytes': report['bytes'], 'sha256': report['sha256']}

    seats = await asyncio.gather(*(capture_seat(row) for row in plan['seats']))
    captured = sum(row['complete'] for row in seats)
    summary = {'version': 1, 'complete': captured == len(seats), 'topology': plan['topology'],
               'expectedSeats': len(seats), 'capturedSeats': captured, 'scope': 'quest-logcat-only'}
    if 'deploymentSha256' in plan:
        summary['deploymentSha256'] = plan['deploymentSha256']
    with (directory / 'capture-report.json').open('x', encoding='utf-8') as report:
        json.dump(dict(summary, seats=seats), report, indent=2)
        report.write('\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', required=True, type=Path, help='Path to the installed ADB executable')
    parser.add_argument('--serial', help='ADB serial of the already launched Quest')
    parser.add_argument('--connection-file', type=Path, help='Original player connection JSON for this admission')
    parser.add_argument('--output', type=Path, help='New output log path in a private directory')
    parser.add_argument('--venue-bundle', type=Path, help='Original five-room deployment ZIP for concurrent capture')
    parser.add_argument('--device-map', type=Path, help='Version 1 Quest device map used for deployment')
    parser.add_argument('--deployment-report', type=Path, help='Original completed deployment report for these exact mapped seats')
    parser.add_argument('--allow-partial-map', action='store_true', help='Capture only the explicitly mapped Quest seats')
    parser.add_argument('--retry-incomplete', type=Path, help='Read only the failed seats from this original venue capture report')
    parser.add_argument('--output-directory', type=Path, help='New private directory for venue captures and the report')
    parser.add_argument('--seconds', type=int, default=1800, help='Total capture deadline, 1 through 7200 seconds')
    args = parser.parse_args()
    try:
        field.integer(args.seconds, 1, 7200)
        field.require(args.adb.is_file(), 'Provide the installed ADB executable')
        adb = [str(args.adb.resolve())]
        single = (args.serial, args.connection_file, args.output)
        venue = (args.venue_bundle, args.device_map, args.output_directory)
        if any(venue) or args.allow_partial_map or args.retry_incomplete or args.deployment_report:
            field.require(all(venue) and not any(single), 'Use a venue ZIP, device map and output directory together')
            plan = venue_plan(args.venue_bundle, args.device_map, args.allow_partial_map)
            if args.deployment_report:
                plan = bind_deployment(plan, args.deployment_report)
            if args.retry_incomplete:
                plan = retry_capture_plan(plan, args.retry_incomplete)
            report = asyncio.run(capture_venue(adb, plan, args.output_directory, args.seconds))
        else:
            field.require(all(single), 'Use a serial, connection file and output log together')
            field.require(re.fullmatch(r'[A-Za-z0-9\[][A-Za-z0-9._:%\[\]-]{0,127}', args.serial), 'Use a valid explicit ADB serial')
            port, admission = read_connection(args.connection_file)
            report = asyncio.run(capture([*adb, '-s', args.serial], port, admission, args.output, args.seconds))
    except field.EvidenceError as error:
        parser.exit(1, f'Quest capture incomplete. {error}.\n')
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, TimeoutError, RecursionError, KeyboardInterrupt):
        parser.exit(1, 'Quest capture incomplete. Check ADB and use a new output path.\n')
    print(json.dumps(report))
    if not report['complete']:
        sys.exit(1)


if __name__ == '__main__':
    main()
