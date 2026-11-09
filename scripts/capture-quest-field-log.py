"""Preserve one Quest game's original logcat from startup to its final disconnect."""

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


async def read_capture(child, adb, pid, port, admission, log, deadline):
    startup_deadline = min(deadline, time.monotonic() + STARTUP_SECONDS)
    next_pid_check = time.monotonic() + PID_CHECK_SECONDS
    started = final_seen = False
    size = 0
    while True:
        now = time.monotonic()
        field.require(now < deadline, 'Capture timed out before the final disconnect')
        field.require(started or now < startup_deadline, 'Original Quest startup is unavailable')
        if now >= next_pid_check:
            current = await asyncio.to_thread(quest_pid, adb, min(5, deadline - now))
            field.require(current == pid, 'The original Quest process changed')
            next_pid_check = time.monotonic() + PID_CHECK_SECONDS
            continue
        read_deadline = min(deadline, next_pid_check, deadline if started else startup_deadline)
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
        if message.startswith('VR_NETWORK_STARTED '):
            field.require(process == str(pid) and not started and field.quest_startup_on_port(message, port),
                          'Quest startup differs from the original process or game port')
            started = True
            print(json.dumps({'stage': 'capture-ready', 'logcatPid': pid}), file=sys.stderr, flush=True)
        elif message.startswith(field.PLAYER_MARKERS):
            field.require(process == str(pid) and started, 'Player marker is outside the original Quest startup or process')
            if message.startswith('VR_CLIENT_DEBRIEF_FINAL '):
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


async def capture(adb, port, admission, output, seconds):
    partial = output.with_name(output.name + '.partial')
    field.require(not os.path.lexists(output) and not os.path.lexists(partial), 'Choose a new capture output path')
    deadline = time.monotonic() + seconds
    pid = await asyncio.to_thread(quest_pid, adb, min(5, seconds))
    with partial.open('x+b') as log:
        child = await asyncio.create_subprocess_exec(*adb, 'logcat', '-b', 'main', f'--pid={pid}',
                                                    '-v', 'threadtime', '-s', 'Unity:I',
                                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        try:
            report = await read_capture(child, adb, pid, port, admission, log, deadline)
        finally:
            if child.returncode is None:
                try:
                    child.kill()
                except ProcessLookupError:
                    pass
            await asyncio.wait_for(child.communicate(), 5)
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', required=True, type=Path, help='Path to the installed ADB executable')
    parser.add_argument('--serial', required=True, help='ADB serial of the already launched Quest')
    parser.add_argument('--connection-file', required=True, type=Path, help='Original player connection JSON for this admission')
    parser.add_argument('--output', required=True, type=Path, help='New output log path in a private directory')
    parser.add_argument('--seconds', type=int, default=1800, help='Total capture deadline, 1 through 7200 seconds')
    args = parser.parse_args()
    try:
        field.integer(args.seconds, 1, 7200)
        field.require(re.fullmatch(r'[A-Za-z0-9\[][A-Za-z0-9._:%\[\]-]{0,127}', args.serial), 'Use a valid explicit ADB serial')
        field.require(args.adb.is_file(), 'Provide the installed ADB executable')
        port, admission = read_connection(args.connection_file)
        report = asyncio.run(capture([str(args.adb.resolve()), '-s', args.serial], port, admission, args.output, args.seconds))
    except field.EvidenceError as error:
        parser.exit(1, f'Quest capture incomplete. {error}.\n')
    except (OSError, UnicodeError, ValueError, TimeoutError, RecursionError, KeyboardInterrupt):
        parser.exit(1, 'Quest capture incomplete. Check ADB and use a new output path.\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
