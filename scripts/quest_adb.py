"""Resolve authorized ADB aliases to their current transport IDs."""

from collections import Counter
import re
import subprocess


class AdbTransportError(ValueError):
    """An ADB transport could not be selected from the device inventory."""


def android_user_id(output):
    match = re.fullmatch(rb'(0|[1-9][0-9]{0,9})(?:\r?\n)?', output)
    if match is None or int(match[1]) > 2**31 - 1:
        raise ValueError('Could not identify the foreground Android user on the selected Quest.')
    return match[1].decode('ascii')


def read_adb_transports(adb, timeout):
    if timeout <= 0:
        raise AdbTransportError('Deadline elapsed before reading Quest ADB transports')
    try:
        result = subprocess.run([*adb, 'devices', '-l'], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, timeout=min(5, timeout),
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except subprocess.TimeoutExpired:
        raise AdbTransportError('Quest ADB transport inventory timed out') from None
    if result.returncode != 0 or len(result.stdout) > 65536:
        raise AdbTransportError('Could not read Quest ADB transports')
    rows = result.stdout.decode('utf-8').splitlines()
    if not rows or rows[0] != 'List of devices attached':
        raise AdbTransportError('Invalid Quest ADB transport inventory')
    aliases, ids = Counter(), Counter()
    candidates = {}
    for line in rows[1:]:
        if not line.strip():
            continue
        row = re.fullmatch(r'(\(no serial number\)|\S+)[ \t]+(\S+)(?:[ \t]+(.*))?', line)
        if row is None:
            raise AdbTransportError('Invalid Quest ADB transport inventory row')
        serial, state, metadata = row.groups()
        aliases[serial] += 1
        transport_fields = [token for token in (metadata or '').split() if token.startswith('transport_id:')]
        valid_ids = [int(token.removeprefix('transport_id:')) for token in transport_fields
                     if re.fullmatch(r'transport_id:[1-9][0-9]{0,18}', token)]
        ids.update(valid_ids)
        if (state == 'device' and len(transport_fields) == len(valid_ids) == 1
                and valid_ids[0] <= 2**63 - 1):
            candidates[serial] = valid_ids[0]
    return {serial: str(transport) for serial, transport in candidates.items()
            if aliases[serial] == 1 and ids[transport] == 1}


def select_adb_transport(adb, transports, serial):
    transport = transports.get(serial)
    if transport is None:
        raise AdbTransportError('Expected one authorized Quest ADB transport for this seat')
    return [*adb, '-t', transport]
