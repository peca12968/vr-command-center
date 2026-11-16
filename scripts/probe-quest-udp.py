"""Run the private Quest Android UDP preflight APK through ADB."""
import argparse
import base64
from datetime import datetime
import ipaddress
import json
from pathlib import Path
import re
import subprocess
import uuid


PACKAGE = 'com.vrcommand.udpprobe'
PREFIX = 'INSTRUMENTATION_RESULT: probeReport='
LAN = tuple(map(ipaddress.IPv4Network, ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '127.0.0.0/8')))


def address(value):
    try:
        parsed = ipaddress.IPv4Address(value)
        if str(parsed) == value and any(parsed in network for network in LAN):
            return value
    except ValueError:
        pass
    raise argparse.ArgumentTypeError('Use a canonical private or loopback IPv4 address.')


def read_key(path):
    with path.open('rb') as source:
        raw = source.read(47)
    if not 44 <= len(raw) <= 46:
        raise ValueError('Invalid UDP probe key.')
    encoded = raw.strip()
    decoded = base64.b64decode(encoded, validate=True)
    if len(decoded) != 32 or base64.b64encode(decoded) != encoded:
        raise ValueError('Invalid UDP probe key.')
    return encoded


def android_report(output, args):
    if len(output) > 32768:
        raise ValueError('Invalid Android probe report.')
    lines = output.decode('utf-8').splitlines()
    reports = [line[len(PREFIX):] for line in lines if line.startswith(PREFIX)]
    if len(reports) != 1 or lines.count('INSTRUMENTATION_CODE: -1') != 1:
        raise ValueError('Android probe instrumentation did not finish.')
    def unique_fields(pairs):
        fields = dict(pairs)
        if len(fields) != len(pairs):
            raise ValueError('Duplicate Android probe report field.')
        return fields

    report = json.loads(reports[0], object_pairs_hook=unique_fields)
    if type(report) is not dict or type(report.get('version')) is not int or report['version'] != 1:
        raise ValueError('Invalid Android probe report.')
    if report.get('stage') == 'failed' and set(report) == {'version', 'stage', 'step', 'complete'}:
        if report.get('step') in ('arguments', 'key', 'address', 'bind', 'exchange') and report.get('complete') is False:
            return report
    expected = {'stage': 'finished', 'mode': 'probe', 'localAddress': args.local_address, 'peerAddress': args.peer_address,
                'port': args.port, 'requested': args.count, 'scope': 'authenticated-udp-only'}
    if any(type(report.get(key)) is not type(value) or report[key] != value for key, value in expected.items()):
        raise ValueError('Android report differs from the requested probe.')
    fields = {'version', 'matched', 'samples', 'exchangeSha256', 'complete', 'completedAtUtc'} | expected.keys()
    if report.keys() != fields or type(report['samples']) is not list or len(report['samples']) != args.count:
        raise ValueError('Invalid Android probe samples.')
    matched = 0
    for number, sample in enumerate(report['samples'], 1):
        if type(sample) is not dict or sample.keys() != {'sample', 'roundTripMs'} or type(sample['sample']) is not int or sample['sample'] != number:
            raise ValueError('Invalid Android probe samples.')
        rtt = sample['roundTripMs']
        if rtt is not None:
            if type(rtt) not in (int, float) or not 0 <= rtt <= args.timeout_ms:
                raise ValueError('Invalid Android probe RTT.')
            matched += 1
    digest = report['exchangeSha256']
    if (type(report['matched']) is not int or report['matched'] != matched or report['complete'] is not (matched == args.count)
            or (matched and (type(digest) is not str or not re.fullmatch(r'[0-9a-f]{64}', digest)))
            or (not matched and digest is not None)):
        raise ValueError('Invalid Android probe completion.')
    stamp = report['completedAtUtc']
    if type(stamp) is not str or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,7})?Z', stamp):
        raise ValueError('Invalid Android probe completion time.')
    datetime.fromisoformat(stamp[:-1] + '+00:00')
    return report


def run_probe(args):
    adb = [str(args.adb.resolve(strict=True)), '-s', args.serial]
    key_name = 'udp-' + uuid.uuid4().hex + '.key'
    private_key = 'files/' + key_name

    def invoke(command, timeout=12, data=None):
        result = subprocess.run(adb + command, input=data, capture_output=True, timeout=timeout,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise ValueError('ADB could not run the Quest probe. Check the selected device and installed probe APK.')
        return result.stdout

    key = read_key(args.key_file)
    try:
        invoke(['shell', '-T', f"run-as {PACKAGE} sh -c 'umask 077; mkdir -p files && set -C && cat > {private_key}'"], data=key)
        settings = {'keyName': key_name, 'localAddress': args.local_address, 'peerAddress': args.peer_address,
                    'port': args.port, 'count': args.count, 'timeoutMs': args.timeout_ms}
        command = ['shell', 'am', 'instrument', '-w', '-r']
        for name, value in settings.items():
            command += ['-e', name, str(value)]
        command += [PACKAGE + '/.ProbeInstrumentation']
        return android_report(invoke(command, timeout=15 + args.count * args.timeout_ms / 1000), args)
    finally:
        invoke(['shell', 'run-as', PACKAGE, 'rm', '-f', private_key])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', required=True, type=Path)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--key-file', required=True, type=Path)
    parser.add_argument('--local-address', required=True, type=address)
    parser.add_argument('--peer-address', required=True, type=address)
    parser.add_argument('--port', required=True, type=int)
    parser.add_argument('--count', type=int, default=5)
    parser.add_argument('--timeout-ms', type=int, default=900)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}', args.serial)
            or not (1024 <= args.port <= 65535 and 1 <= args.count <= 20 and 200 <= args.timeout_ms <= 3000)):
        parser.error('Use one explicit ADB serial and valid probe bounds.')
    if args.report.exists() or not args.report.parent.is_dir():
        parser.error('Choose a new report file in an existing directory.')
    from windows_firewall import WindowsFirewallLaunchError, require_silent_windows_launch

    try:
        require_silent_windows_launch(args.adb)
        report = run_probe(args)
        with args.report.open('x', encoding='utf-8', newline='\n') as destination:
            json.dump(report, destination, separators=(',', ':'))
            destination.write('\n')
    except WindowsFirewallLaunchError as error:
        parser.exit(1, f'{error}\n')
    except (OSError, ValueError, subprocess.SubprocessError, KeyboardInterrupt):
        parser.exit(1, 'Quest UDP probe could not save a valid report. Check the device, APK, probe key and output path.\n')
    print(json.dumps({'complete': report['complete'], 'matched': report.get('matched', 0)}))
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
