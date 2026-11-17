"""Preserve original Quest logcat for one player or the mapped venue seats."""

import argparse
import asyncio
import base64
from collections import Counter
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

from quest_adb import AdbTransportError, read_adb_transports, select_adb_transport

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
    return port, dict(expected, roomId=payload[49]), payload[50] + 1, config.get('address')


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


def report_capture_status(pid, *, stage='capture-ready', **seat):
    print(json.dumps({'stage': stage, 'logcatPid': pid, **seat}), file=sys.stderr, flush=True)


async def read_capture(child, adb, pid, port, admission, log, deadline, on_ready, openxr=None, *,
                       on_final=None, on_disconnected=None, device_identity=None, venue_device=None):
    async def confirm_source(verify_device=True):
        if verify_device and device_identity is not None:
            await asyncio.to_thread(check_device_identity, adb, device_identity, deadline - time.monotonic(), venue_device)
        remaining = deadline - time.monotonic()
        field.require(remaining > 0, 'Capture timed out before the original process could be checked')
        current = await asyncio.to_thread(quest_pid, adb, min(5, remaining))
        field.require(current == pid, 'The original Quest process changed')

    startup_deadline = min(deadline, time.monotonic() + STARTUP_SECONDS)
    next_pid_check = time.monotonic() + PID_CHECK_SECONDS
    started = ready = final_seen = False
    xr_ready = openxr is None
    connection = None
    connection_ids = set()
    size = 0
    while True:
        now = time.monotonic()
        field.require(now < deadline, 'Capture timed out before the final disconnect')
        field.require(started or now < startup_deadline, 'Original Quest startup is unavailable')
        field.require(xr_ready or now < startup_deadline, 'Original Quest OpenXR launch marker is unavailable')
        if now >= next_pid_check:
            await confirm_source()
            next_pid_check = time.monotonic() + PID_CHECK_SECONDS
            continue
        read_deadline = min(deadline, next_pid_check, deadline if started and xr_ready else startup_deadline)
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
        elif message.startswith(field.PLAYER_MARKERS) or message == 'VR_CLIENT_ADMISSION_REJECTED':
            field.require(process == str(pid) and started, 'Player marker is outside the original Quest startup or process')
            if message.startswith('VR_CLIENT_CONNECTED'):
                match = field.CONNECT.fullmatch(message)
                field.require(match is not None and connection is None and not final_seen, 'Unexpected player connection marker')
                connection = match.group(1)
                field.require(connection not in connection_ids, 'Player connection number reused')
                connection_ids.add(connection)
            elif message in ('VR_CLIENT_DISCONNECTED', 'VR_CLIENT_ADMISSION_REJECTED'):
                connection = None
                if ready and not final_seen:
                    ready = False
                    if on_disconnected is not None:
                        on_disconnected(pid)
            elif message.startswith('VR_CLIENT_DEBRIEF_FINAL '):
                field.require(xr_ready, 'Original Quest OpenXR launch marker is unavailable')
                field.require(connection is not None and not final_seen, 'Player final result lacks a unique live connection')
                if on_final is not None:
                    on_final()
                final_seen = True
            if final_seen and message == 'VR_CLIENT_DISCONNECTED':
                log.seek(0)
                captured = field.limited_read(log)
                _, result = field.quest_client_result(captured.decode('utf-8'), pid, port)
                field.require(type(result) is dict and type(result.get('version')) is int and result['version'] == 1
                              and type(result.get('roomId')) is int
                              and all(result.get(key) == value for key, value in admission.items()),
                              'Final result differs from the original player admission')
                await confirm_source(verify_device=False)
                return {'version': 1, 'complete': True, 'logcatPid': pid, 'port': port, 'roomId': admission['roomId'], 'bytes': size,
                        'sha256': hashlib.sha256(captured).hexdigest(), 'scope': 'quest-logcat-only'}
        if started and xr_ready and connection is not None and not ready and not final_seen:
            if device_identity is not None:
                await confirm_source()
                next_pid_check = time.monotonic() + PID_CHECK_SECONDS
            ready = True
            on_ready(pid)


def read_device_serial(adb, timeout):
    field.require(timeout > 0, 'Capture timed out before the Quest device identity could be checked')
    try:
        result = subprocess.run([*adb, 'shell', 'getprop', 'ro.serialno'], capture_output=True, timeout=min(5, timeout))
    except subprocess.TimeoutExpired:
        raise field.EvidenceError('Quest device identity could not be read') from None
    serial = re.fullmatch(rb'([A-Za-z0-9][A-Za-z0-9._-]{0,127})\r?\n?', result.stdout)
    field.require(result.returncode == 0 and serial is not None and not re.fullmatch(rb'unknown|0+', serial[1], re.I),
                  'Quest device identity could not be read')
    return serial[1].decode('ascii').upper()


def check_device_identity(adb, expected, timeout, venue_device=None):
    require_device_identity(read_device_serial(adb, timeout), expected, venue_device)


def require_device_identity(reported, expected, venue_device=None):
    if isinstance(expected, str):
        field.require(reported == expected, 'Quest device identity changed during capture')
    else:
        salt, digest = expected
        field.require(field.quest_deployment_fingerprint(salt, reported) == digest,
                      'Quest device identity differs from the original deployment')
    if venue_device is not None:
        scope, digest = venue_device
        field.require(field.quest_deployment_fingerprint(scope, reported) == digest,
                      'Quest device identity differs from the original venue device proof')


def publish_capture_file(staged, output):
    """Expose a closed capture file atomically and preserve an existing destination."""
    try:
        if os.name == 'nt':
            staged.rename(output)  # Windows rename refuses an existing destination.
            return
        os.link(staged, output)
    except FileExistsError:
        raise field.EvidenceError('Capture output already exists; the staged file was preserved') from None
    staged.unlink()


async def capture(adb, port, admission, output, seconds, on_ready=report_capture_status, *,
                  device_identity=None, venue_device=None, openxr=None, on_final=None, on_disconnected=None):
    partial = output.with_name(output.name + '.partial')
    field.require(not os.path.lexists(output) and not os.path.lexists(partial), 'Choose a new capture output path')
    deadline = time.monotonic() + seconds
    if device_identity is None:
        # Use the first physical serial only for this capture. Keep it out of reports and status output.
        device_identity = await asyncio.to_thread(read_device_serial, adb, deadline - time.monotonic())
    else:
        await asyncio.to_thread(check_device_identity, adb, device_identity, deadline - time.monotonic(), venue_device)
    remaining = deadline - time.monotonic()
    field.require(remaining > 0, 'Capture timed out before checking the Quest process')
    pid = await asyncio.to_thread(quest_pid, adb, min(5, remaining))
    field.require(openxr is None or pid == openxr[0], 'Quest process differs from the original OpenXR launch')
    with partial.open('x+b') as log:
        child = await asyncio.create_subprocess_exec(*adb, 'logcat', '-b', 'main', f'--pid={pid}',
                                                    '-v', 'threadtime', '-s', 'Unity:I',
                                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        try:
            report = await read_capture(child, adb, pid, port, admission, log, deadline, on_ready, openxr,
                                        on_final=on_final, on_disconnected=on_disconnected,
                                        device_identity=device_identity, venue_device=venue_device)
        finally:
            if child.returncode is None:
                try:
                    child.kill()
                except ProcessLookupError:
                    pass
            await asyncio.wait_for(child.communicate(), 5)
        await asyncio.to_thread(check_device_identity, adb, device_identity, deadline - time.monotonic(), venue_device)
    publish_capture_file(partial, output)
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


def capture_binding(plan, salt):
    device_map = {(row['roomId'], row['seat']): row['serial'] for row in plan['seats']}
    return {'venueSha256': plan['venueSha256'], 'salt': salt,
            'mapSha256': field.quest_deployment_map_fingerprint(salt, device_map)}


def retry_capture_plan(plan, report_path):
    report = field.read_quest_capture_report(report_path, plan['topology'])
    field.require(report.get('deploymentSha256') == plan.get('deploymentSha256'),
                  'Retry with the same original Quest deployment report as the first capture')
    field.require(report.get('partialDeployment') == plan.get('partialDeployment'),
                  'Retry with the same deployed-seat capture option as the first capture')
    binding = report.get('captureBinding')
    if binding is None:
        field.require('deploymentSha256' in report,
                      'The prior Quest capture lacks an original ZIP and device map binding; start a new capture')
        binding = capture_binding(plan, uuid.uuid4().hex)
    else:
        field.require(binding == capture_binding(plan, binding['salt']),
                      'Retry with the original venue ZIP and Quest device map for the first capture')
    seats = {(row['roomId'], row['seat']): row for row in plan['seats']}
    completed_devices = field.quest_capture_device_fingerprints(report)
    field.require(completed_devices.keys() <= seats.keys(), 'Prior Quest capture names an unplanned completed headset seat')
    retry = []
    for row in report['seats']:
        original = seats.get((row['roomId'], row['seat']))
        field.require(original is not None and row['sessionId'] == original['sessionId'] and row['port'] == original['port'],
                      'Prior Quest capture report does not match the original deployment seats')
        if not row['complete']:
            retry.append(original)
    field.require(retry, 'Prior Quest capture report has no incomplete seats')
    return {**plan, 'seats': retry, 'captureBinding': binding, 'completedDevices': completed_devices}


def bind_deployment(plan, path, *, completed_only=False, after=None):
    report, raw = field.read_quest_document(path)
    seats = plan['seats']
    devices = report.get('devices')
    field.require(report.get('phase') == 'deployment' and report.get('topology') == plan['topology']
                  and report.get('managementVerified') is True and field.integer(report.get('apkVerificationVersion'), 1, 1)
                  and type(devices) is list and len(devices) == len(seats),
                  'Provide the original Quest deployment report for the original mapped seats')
    devices, launched = field.quest_deployment_rows(report)
    field.require(report['complete'] is not completed_only, 'Use --capture-deployed-seats only with an incomplete Quest deployment report'
                  if completed_only else 'Use --capture-deployed-seats to capture from an incomplete Quest deployment report')
    field.require(launched, 'The original Quest deployment has no successfully launched seats')
    version_code = field.integer(report.get('expectedVersionCode'), 1, 2**31 - 1)
    require_openxr = report.get('requireOpenXR', False)
    field.require(type(require_openxr) is bool and (not require_openxr or version_code >= 74),
                  'Invalid Quest OpenXR deployment option for the original release')
    apk_digest = report.get('expectedApkSha256')
    field.require(type(apk_digest) is str and re.fullmatch(r'[0-9a-f]{64}', apk_digest), 'Quest deployment report lacks a verified release APK')
    proof, predecessor = field.quest_deployment_retry_proof(report, len(seats))
    field.require(proof is not None and proof['venueSha256'] == plan['venueSha256'],
                  'Quest deployment report does not match the original venue ZIP')
    device_map = {(row['roomId'], row['seat']): row['serial'] for row in seats}
    field.require(field.quest_deployment_map_fingerprint(proof['salt'], device_map) == proof['mapSha256'],
                  'Quest deployment report does not match the original device map')
    skip = 0
    if after is not None:
        prior, prior_raw = field.read_quest_document(after)
        field.require(predecessor == hashlib.sha256(prior_raw).hexdigest(),
                      'Use the exact preceding Quest deployment report')
        prior_devices, prior_launched = field.quest_deployment_rows(prior)
        prior_proof, _ = field.quest_deployment_retry_proof(prior, len(prior_devices))
        fields = ('phase', 'topology', 'managementVerified', 'apkVerificationVersion', 'expectedVersionCode', 'expectedApkSha256')
        field.require(prior['complete'] is False and len(prior_devices) == len(seats)
                      and field.quest_deployment_proof_matches_parent(proof, prior_proof, report.get('previousVenueSha256'))
                      and prior.get('requireOpenXR', False) is require_openxr
                      and all(type(prior.get(key)) is type(report.get(key)) and prior[key] == report[key] for key in fields)
                      and launched[:len(prior_launched)] == prior_launched,
                      'Quest deployment retry changes its original proof or completed prefix')
        skip = len(prior_launched)
        field.require(len(launched) > skip, 'No seats have launched since the preceding Quest deployment report')
    bound_seats = []
    scoped = proof.get('venueDevices')
    for index, (seat, device, fingerprint) in enumerate(zip(seats, devices, proof['devices'], strict=True)):
        field.require(all(type(device.get(key)) is int and device[key] == seat[key] for key in ('roomId', 'seat')),
                      'Quest deployment report does not match the original mapped seat order')
        if device['status'] != 'launch-requested':
            continue
        field.require(device.get('apkVerified') is device.get('filesVerified') is True
                      and field.integer(device.get('versionCode'), 1) == version_code
                      and all(type(device.get(key)) is type(seat[key]) and device[key] == seat[key]
                              for key in ('port', 'sessionId', 'playerId', 'admissionId')),
                      'Quest deployment report differs from an original admitted seat')
        opening = field.quest_openxr_proof(device, require_openxr)
        venue_device = (scoped['scopeSha256'], scoped['devices'][index]) if scoped is not None else None
        bound_seats.append({**seat, 'deviceIdentity': (proof['salt'], fingerprint), 'venueDevice': venue_device, 'openXR': opening})
    field.require(not require_openxr or len({row['openXR'][1] for row in bound_seats}) == len(bound_seats),
                  'Quest OpenXR launch nonce was reused between seats')
    return {**plan, 'deploymentSha256': hashlib.sha256(raw).hexdigest(),
            **({'partialDeployment': True} if completed_only else {}),
            'seats': bound_seats[skip:]}


async def capture_venue(adb, plan, directory, seconds):
    binding = plan.get('captureBinding')
    if binding is None:
        binding = capture_binding(plan, uuid.uuid4().hex)
    field.require(not os.path.lexists(directory), 'Choose a new capture output path')
    deadline = time.monotonic() + seconds
    transports = await asyncio.to_thread(read_adb_transports, adb, seconds)
    directory.mkdir()

    def identify_seat(row):
        target = select_adb_transport(adb, transports, row['serial'])
        return target, read_device_serial(target, deadline - time.monotonic())

    # Distinct ADB aliases can name the same headset over different transports.
    identities = await asyncio.gather(*(asyncio.to_thread(identify_seat, row) for row in plan['seats']),
                                      return_exceptions=True)
    device_counts = Counter(identity[1] for identity in identities if isinstance(identity, tuple))
    completed_devices = dict(plan.get('completedDevices', {}))
    retained_devices = set(completed_devices.values())
    ready_seats = set()
    can_announce_ready = True
    partial_deployment = {'partialDeployment': True} if plan.get('partialDeployment') else {}

    def close_readiness():
        nonlocal can_announce_ready
        can_announce_ready = False

    async def capture_seat(row, identity):
        seat = {'roomId': row['roomId'], 'seat': row['seat']}
        source = dict(seat, sessionId=row['sessionId'], port=row['port'])
        admission = {key: row[key] for key in ('sessionId', 'playerId', 'admissionId', 'roomId')}
        log = directory / f"room-{seat['roomId']:02}-seat-{seat['seat']:02}-logcat.txt"
        seat_key = (seat['roomId'], seat['seat'])

        def on_ready(pid):
            report_capture_status(pid, **seat)
            ready_seats.add(seat_key)
            if len(ready_seats) == len(plan['seats']) and can_announce_ready:
                print(json.dumps({'stage': 'venue-capture-ready', 'seats': len(ready_seats), **partial_deployment}),
                      file=sys.stderr, flush=True)

        def on_disconnected(pid):
            ready_seats.discard(seat_key)
            report_capture_status(pid, stage='capture-disconnected', **seat)

        try:
            if isinstance(identity, BaseException):
                raise identity
            target, serial = identity
            field.require(device_counts[serial] == 1, 'The same Quest headset is assigned to multiple capture seats')
            fingerprint = field.quest_deployment_fingerprint(binding['salt'], 'quest-capture-device-v1:' + serial)
            field.require(fingerprint not in retained_devices, 'This Quest headset already completed another capture seat')
            if 'deviceIdentity' in row:
                require_device_identity(serial, row['deviceIdentity'], row.get('venueDevice'))
            remaining = deadline - time.monotonic()
            field.require(remaining > 0, 'Capture timed out before checking the Quest process')
            report = await capture(target, source['port'], admission, log, remaining, on_ready,
                                   device_identity=serial,
                                   openxr=row.get('openXR'),
                                   on_final=close_readiness, on_disconnected=on_disconnected)
        except (field.EvidenceError, OSError, UnicodeError, ValueError, TimeoutError, RecursionError) as error:
            close_readiness()
            reason = str(error) if isinstance(error, (field.EvidenceError, AdbTransportError)) else 'Check ADB and the capture directory'
            print(json.dumps({'stage': 'capture-failed', **seat, 'reason': reason}), file=sys.stderr, flush=True)
            partial = log.with_name(log.name + '.partial')
            return {**source, 'complete': False, 'reason': reason, **({'partial': partial.name} if partial.is_file() else {})}
        completed_devices[seat_key] = fingerprint
        return {**source, 'complete': True, 'log': log.name, 'logcatPid': report['logcatPid'],
                'bytes': report['bytes'], 'sha256': report['sha256']}

    seats = await asyncio.gather(*(capture_seat(row, identity) for row, identity in zip(plan['seats'], identities, strict=True)))
    captured = sum(row['complete'] for row in seats)
    summary = {'version': 1, 'complete': captured == len(seats), 'topology': plan['topology'],
               'expectedSeats': len(seats), 'capturedSeats': captured, 'scope': 'quest-logcat-only', **partial_deployment}
    summary['captureBinding'] = binding
    if 'deploymentSha256' in plan:
        summary['deploymentSha256'] = plan['deploymentSha256']
    report_path = directory / 'capture-report.json'
    staged_report = report_path.with_suffix('.json.partial')
    device_fingerprints = [{'roomId': room, 'seat': seat, 'sha256': digest}
                           for (room, seat), digest in sorted(completed_devices.items())]
    with staged_report.open('x', encoding='utf-8') as report:
        json.dump(dict(summary, seats=seats, completedDeviceFingerprints=device_fingerprints), report, indent=2)
        report.write('\n')
    publish_capture_file(staged_report, report_path)
    return summary


def main():
    from windows_firewall import require_silent_windows_launch

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', required=True, type=Path, help='Path to the installed ADB executable')
    parser.add_argument('--serial', help='ADB serial of the already launched Quest')
    parser.add_argument('--connection-file', type=Path, help='Original player connection JSON for this admission')
    parser.add_argument('--output', type=Path, help='New output log path in a private directory')
    parser.add_argument('--quest-launch-report', type=Path, help='Original single-seat -RequireOpenXR deployment report')
    parser.add_argument('--quest-launch-release', type=Path, help='Exact original release report used to launch that seat')
    parser.add_argument('--venue-bundle', type=Path, help='Original five-room deployment ZIP for concurrent capture')
    parser.add_argument('--device-map', type=Path, help='Version 1 Quest device map used for deployment')
    parser.add_argument('--deployment-report', type=Path, help='Original deployment report for these exact mapped seats')
    parser.add_argument('--capture-deployed-seats', action='store_true',
                        help='Capture only the successfully launched seats in the original incomplete deployment report')
    parser.add_argument('--after-deployment-report', type=Path, help='Capture only seats launched since this preceding deployment report')
    parser.add_argument('--allow-partial-map', action='store_true', help='Capture only the explicitly mapped Quest seats')
    parser.add_argument('--retry-incomplete', type=Path, help='Read only the failed seats from this original venue capture report')
    parser.add_argument('--output-directory', type=Path, help='New private directory for venue captures and the report')
    parser.add_argument('--seconds', type=int, default=1800, help='Total capture deadline, 1 through 7200 seconds')
    args = parser.parse_args()

    def check_adb_startup():
        try:
            require_silent_windows_launch(args.adb)
        except RuntimeError as error:
            raise field.EvidenceError('ADB startup skipped by the Windows Firewall check') from error

    try:
        field.integer(args.seconds, 1, 7200)
        field.require(args.adb.is_file(), 'Provide the installed ADB executable')
        adb = [str(args.adb.resolve())]
        single = (args.serial, args.connection_file, args.output)
        venue = (args.venue_bundle, args.device_map, args.output_directory)
        field.require(not args.capture_deployed_seats or args.deployment_report,
                      'Use --capture-deployed-seats with the original incomplete --deployment-report')
        field.require(not args.after_deployment_report or args.deployment_report,
                      'Use --after-deployment-report with --deployment-report')
        field.require(bool(args.quest_launch_report) == bool(args.quest_launch_release),
                      'Provide both --quest-launch-report and --quest-launch-release for single-seat capture')
        if any(venue) or args.allow_partial_map or args.retry_incomplete or args.deployment_report:
            field.require(all(venue) and not any(single) and args.quest_launch_report is None,
                          'Use a venue ZIP, device map and output directory together without single-seat options')
            plan = venue_plan(args.venue_bundle, args.device_map, args.allow_partial_map)
            if args.deployment_report:
                plan = bind_deployment(plan, args.deployment_report, completed_only=args.capture_deployed_seats,
                                       after=args.after_deployment_report)
            if args.retry_incomplete:
                plan = retry_capture_plan(plan, args.retry_incomplete)
            check_adb_startup()
            report = asyncio.run(capture_venue(adb, plan, args.output_directory, args.seconds))
        else:
            field.require(all(single), 'Use a serial, connection file and output log together')
            field.require(re.fullmatch(r'[A-Za-z0-9\[][A-Za-z0-9._:%\[\]-]{0,127}', args.serial), 'Use a valid explicit ADB serial')
            port, admission, seat, address = read_connection(args.connection_file)
            openxr = None
            device_identity = None
            if args.quest_launch_report is not None:
                launch, raw = field.read_quest_document(args.quest_launch_report)
                deployments, launches, server_addresses, devices = field.single_session_quest_launches([launch], args.quest_launch_release)
                location = (admission['roomId'], seat)
                original = (admission['sessionId'], admission['playerId'], admission['admissionId'], port)
                field.require(deployments.get(location) == original,
                              'Quest launch report differs from the original connection seat, admission or endpoint')
                if location in server_addresses:
                    field.require(server_addresses[location] == field.quest_server_address_sha256(address),
                                  'Quest launch server address differs from the original connection')
                openxr = launches[location]
                device_identity = devices.get(location)
            check_adb_startup()
            deadline = time.monotonic() + args.seconds
            target = select_adb_transport(adb, read_adb_transports(adb, args.seconds), args.serial)
            remaining = deadline - time.monotonic()
            field.require(remaining > 0, 'Capture timed out before checking the Quest process')
            report = asyncio.run(capture(target, port, admission, args.output, remaining, openxr=openxr, device_identity=device_identity,
                                         on_disconnected=lambda pid: report_capture_status(pid, stage='capture-disconnected')))
            if openxr is not None:
                report.update(openXRVerified=True, questLaunchReportSha256=hashlib.sha256(raw).hexdigest())
            if device_identity is not None:
                report['deviceIdentityVerified'] = True
    except (field.EvidenceError, AdbTransportError) as error:
        parser.exit(1, f'Quest capture incomplete. {error}.\n')
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, TimeoutError, RecursionError, KeyboardInterrupt):
        parser.exit(1, 'Quest capture incomplete. Check ADB and use a new output path.\n')
    print(json.dumps(report))
    if not report['complete']:
        sys.exit(1)


if __name__ == '__main__':
    main()
