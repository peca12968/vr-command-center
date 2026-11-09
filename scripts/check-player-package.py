"""Run the actual compiled Windows launcher's offline rejection checks.

Uses only freshly created fixture configs; does not connect to a game server.
Actual downloaded-ticket admission is checked separately by check-external-native.cjs.
"""
import argparse
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('player_package', ROOT / 'scripts/package-windows-player.py')
package = importlib.util.module_from_spec(spec); spec.loader.exec_module(package)


def check_openxr_unavailable(folder, directory, base):
    config = directory / 'openxr-fixture.json'
    log = directory / 'openxr-unavailable.log'
    report = directory / 'openxr-process.json'
    status = directory / 'openxr-status.json'
    env = {**os.environ, 'XR_RUNTIME_JSON': str(directory / 'missing-openxr-runtime.json')}
    command = [str(folder / 'Launch-Player.exe'), '--config', str(config), '--launch', '--openxr', '--wait',
               '--log', str(log), '--report', str(report), '--status-report', str(status)]
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as isolated:
        isolated.bind(('127.0.0.1', 0))
        config.write_text(json.dumps(dict(base, port=isolated.getsockname()[1])), encoding='utf-8')
        with subprocess.Popen(command, cwd=directory, env=env, creationflags=subprocess.CREATE_NO_WINDOW) as process:
            try:
                code = process.wait(timeout=45)
            except subprocess.TimeoutExpired:
                if process.poll() is None:
                    subprocess.run([str(Path(os.environ['WINDIR']) / 'System32/taskkill.exe'), '/PID', str(process.pid), '/T', '/F'],
                                   capture_output=True, timeout=10, check=True)
                raise
    messages = log.read_text(encoding='utf-8', errors='replace').splitlines()
    launch = json.loads(report.read_text(encoding='utf-8'))
    connection = json.loads(status.read_text(encoding='utf-8'))
    if (code != 2 or launch['status'] != 'exited' or launch['exitCode'] != 2
            or connection['state'] != 'OpenXRUnavailable' or connection['exited'] is not True
            or connection['processId'] != launch['processId']
            or [line for line in messages if line.startswith('VR_OPENXR_STARTUP ')]
            != ['VR_OPENXR_STARTUP status=requested', 'VR_OPENXR_STARTUP status=unavailable']
            or any(line.startswith('VR_NETWORK_STARTED ') for line in messages)):
        raise AssertionError('Unavailable Windows OpenXR must exit before network admission')


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('package_directory', type=Path)
    parser.add_argument('--check-openxr-unavailable', action='store_true', help='Run a graphical player with a missing OpenXR runtime for that process')
    args = parser.parse_args(); folder = package.plain(args.package_directory)
    if os.name != 'nt' or folder.name != package.TOP: parser.error('Use an extracted Windows package')
    manifest = package.verify(folder)
    if manifest['launcherSourceSha256'] != package.digest(ROOT / 'tools/WindowsPlayerLauncher/PlayerLauncher.cs'):
        parser.error('Repackage the current launcher source before testing')
    directory = ROOT / 'artifacts/player-package-checks' / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    directory.mkdir(parents=True, exist_ok=False); findings = []

    def check(label, options, success=False, executable=None):
        report = directory / ('report-' + str(len(findings)) + '.json')
        result = subprocess.run([str(executable or folder / 'Launch-Player.exe'), *options, '--report', str(report)],
                                cwd=directory, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        value = json.loads(report.read_text(encoding='utf-8'))
        expected = 'verified' if success else 'rejected'
        if result.returncode != (0 if success else 1) or value.get('status') != expected or 'processId' in value:
            raise AssertionError('Actual launcher result differed: ' + label)
        findings.append(label); print('PASS:', label, flush=True)

    check('Actual launcher verifies the full extracted runtime', ['--verify'], success=True)
    base = {'role': 'Client', 'address': '127.0.0.1', 'port': 7777, 'joinTicket': 'fixture-not-a-ticket'}
    cases = [('server identity', dict(base, role='Server')), ('host identity', dict(base, role='Host')),
             ('management key', dict(base, gameServerKey='fixture-secret')), ('missing ticket', {k: v for k, v in base.items() if k != 'joinTicket'}),
             ('empty ticket', dict(base, joinTicket='')), ('URL destination', dict(base, address='http://127.0.0.1')),
             ('ambiguous IPv4', dict(base, address='127.1')), ('wildcard destination', dict(base, address='0.0.0.0')),
             ('multicast destination', dict(base, address='224.0.0.1')), ('boolean port', dict(base, port=True)),
             ('out-of-range port', dict(base, port=65536))]
    for index, (label, config) in enumerate(cases):
        file = directory / ('invalid ' + str(index) + ' 玩家 &.json'); file.write_text(json.dumps(config), encoding='utf-8')
        check('Rejects ' + label + ' before spawning a player', ['--config', str(file), '--launch', '--headless'])
    oversized = directory / 'oversized.json'; oversized.write_text('x' * 32769, encoding='utf-8')
    check('Rejects oversized input without logging its contents', ['--config', str(oversized), '--launch', '--headless'])
    valid = directory / 'status-input.json'; valid.write_text(json.dumps(base), encoding='utf-8')
    check('Rejects OpenXR without a direct graphical launch', ['--openxr', '--config', str(valid)])
    check('Rejects OpenXR combined with headless launch', ['--openxr', '--launch', '--headless', '--config', str(valid)])
    check('Rejects OpenXR combined with verify-only mode', ['--openxr', '--launch', '--verify', '--config', str(valid)])
    check('Rejects status output without an owned waited launch', ['--status-report', str(directory / 'not-started.json')])
    common = ['--config', str(valid), '--launch', '--headless', '--wait']
    future_log = directory / 'new-log.txt'
    check('Rejects case-aliased status and game log paths before launch', [*common, '--log', str(future_log), '--status-report', str(future_log).upper()])
    check('Rejects status output inside the delivered package', [*common, '--log', str(future_log), '--status-report', str(folder / 'new-status.json')])
    existing = directory / 'existing-status.json'; existing.write_text('preserve owned fixture', encoding='utf-8')
    check('Rejects existing status output without overwriting it', [*common, '--log', str(future_log), '--status-report', str(existing)])
    assert existing.read_text(encoding='utf-8') == 'preserve owned fixture' and not future_log.exists() and not (folder / 'new-status.json').exists()
    if args.check_openxr_unavailable:
        check_openxr_unavailable(folder, directory, base)
        findings.append('Graphical OpenXR launch with a missing runtime exits before admission')
        print('PASS:', findings[-1], flush=True)
    # A fresh minimal copy is intentionally incomplete. Never alter the delivered package.
    broken = directory / 'broken-package'; broken.mkdir(); shutil.copyfile(folder / 'Launch-Player.exe', broken / 'Launch-Player.exe')
    shutil.copyfile(folder / 'player-package.json', broken / 'player-package.json')
    check('Rejects missing runtime files', ['--verify'], executable=broken / 'Launch-Player.exe')
    bad = json.loads(json.dumps(manifest)); bad['files'][0]['path'] = '../outside'
    (broken / 'player-package.json').write_text(json.dumps(bad), encoding='utf-8')
    check('Rejects a manifest path outside the package', ['--verify'], executable=broken / 'Launch-Player.exe')
    for report in directory.glob('report-*.json'):
        if 'fixture-secret' in report.read_text(encoding='utf-8') or 'fixture-not-a-ticket' in report.read_text(encoding='utf-8'):
            raise AssertionError('Diagnostic report leaked fixture credentials')
    result = {'complete': True, 'checks': len(findings), 'findings': findings, 'packageDirectory': str(folder),
              'launcherSourceSha256': manifest['launcherSourceSha256'],
              'scope': 'Actual Windows launcher preflight and selected startup rejection; no game admission, GUI input or headset verification'}
    (directory / 'checks.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'complete': True, 'checks': len(findings), 'directory': str(directory)}))


if __name__ == '__main__': main()
