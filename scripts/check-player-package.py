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
import struct
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('player_package', ROOT / 'scripts/package-windows-player.py')
package = importlib.util.module_from_spec(spec); spec.loader.exec_module(package)


def check_openxr_preflight(folder, directory, mock_manifest):
    launcher = str(folder / 'Launch-Player.exe')
    fixture = directory / 'OpenXR fixture 玩家'
    fixture.mkdir()
    manifest = fixture / 'runtime.json'

    def run(output, override, options=()):
        env = {key: value for key, value in os.environ.items() if key.upper() != 'XR_RUNTIME_JSON'}
        if override is not None:
            env['XR_RUNTIME_JSON'] = str(override)
        return subprocess.run([launcher, '--check-openxr', '--report', str(output), *options],
                              cwd=fixture, env=env, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW).returncode

    def inspect(name, override, status):
        output = fixture / (name + '.json')
        code = run(output, override)
        body = output.read_bytes()
        value = json.loads(body)
        if status is None:
            status = value['status']
            assert status in {'runtime-not-configured', 'registry-unreadable', 'manifest-path-invalid', 'manifest-missing',
                              'manifest-invalid', 'library-search-required', 'library-path-invalid', 'library-missing',
                              'library-unreadable', 'library-not-x64-dll', 'x64-runtime-files-found'}
        complete = status == 'x64-runtime-files-found'
        assert code == (0 if complete else 1), (name, code)
        assert value == {'version': 1, 'scope': 'windows-openxr-runtime-files', 'complete': complete,
                         'source': 'environment' if override is not None else 'registry64', 'status': status}, (name, value)
        return output

    def write_manifest(library):
        manifest.write_text(json.dumps({'file_format_version': '1.0.0', 'runtime': {'library_path': library}}), encoding='utf-8-sig')

    inspect('registry', None, None)
    inspect('missing', manifest, 'manifest-missing')
    inspect('unc', r'\\unreachable\openxr\runtime.json', 'manifest-path-invalid')
    manifest.write_bytes(b' ' * 65537)
    inspect('oversized', manifest, 'manifest-invalid')
    manifest.write_bytes(b'{"\xff":0}')
    inspect('bad-encoding', manifest, 'manifest-invalid')
    write_manifest('runtime.dll')
    inspect('bare-name', manifest, 'library-search-required')
    write_manifest(r'\\unreachable\openxr\runtime.dll')
    inspect('remote-library', manifest, 'library-path-invalid')
    write_manifest('./runtime.dll')
    inspect('missing-library', manifest, 'library-missing')
    library = fixture / 'runtime.dll'
    header = bytearray(256)
    struct.pack_into('<H', header, 0, 0x5A4D)
    struct.pack_into('<I', header, 60, 64)
    struct.pack_into('<IH', header, 64, 0x4550, 0x14C)
    struct.pack_into('<HHH', header, 84, 112, 0x2000, 0x20B)
    library.write_bytes(header)
    inspect('x86', manifest, 'library-not-x64-dll')
    struct.pack_into('<H', header, 68, 0x8664)
    library.write_bytes(header)
    success = inspect('x64', manifest, 'x64-runtime-files-found')
    original = success.read_bytes()
    disallowed = folder / 'preflight-inside.json'
    conflicting = fixture / 'preflight-launch.json'
    assert run(success, manifest) == 2 and success.read_bytes() == original
    assert run(disallowed, manifest) == 2 and not disallowed.exists()
    assert run(conflicting, manifest, ['--launch']) == 2 and not conflicting.exists()
    if mock_manifest is not None:
        inspect('unity-mock', mock_manifest.resolve(strict=True), 'x64-runtime-files-found')
    return mock_manifest.resolve(strict=True) if mock_manifest is not None else manifest


def check_openxr_unavailable(folder, directory, base, release=None, manifest_hash=None):
    config = directory / 'openxr-fixture.json'
    log = directory / 'openxr-unavailable.log'
    report = directory / 'openxr-process.json'
    status = directory / 'openxr-status.json'
    evidence = directory / 'openxr-player-evidence.zip'
    env = {**os.environ, 'XR_RUNTIME_JSON': str(directory / 'missing-openxr-runtime.json')}
    command = [str(folder / 'Launch-Player.exe'), '--config', str(config), '--launch', '--openxr', '--wait',
               '--log', str(log), '--report', str(report), '--status-report', str(status)]
    if release is not None:
        command += ['--release-report', str(release), '--evidence-zip', str(evidence)]
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
    if (code != 2 or evidence.exists() or launch['status'] != 'exited' or launch['exitCode'] != 2
            or connection['state'] != 'OpenXRUnavailable' or connection['exited'] is not True
            or connection['processId'] != launch['processId']
            or launch.get('playerManifestSha256') != manifest_hash
            or launch.get('venueReleaseReportSha256') != (package.digest(release) if release is not None else None)
            or (manifest_hash is not None and launch.get('playerLogSha256') != package.digest(log))
            or [line for line in messages if line.startswith('VR_OPENXR_STARTUP ')]
            != ['VR_OPENXR_STARTUP status=requested', 'VR_OPENXR_STARTUP status=unavailable']
            or any(line.startswith('VR_NETWORK_STARTED ') for line in messages)):
        raise AssertionError('Unavailable Windows OpenXR must exit before network admission')


def check_local_profiler(folder, directory):
    log = directory / 'local-profiler.log'
    command = [str(folder / 'VrCommand.exe'), '-batchmode', '-nographics', '-job-worker-count', '2',
               '-logFile', str(log), '--vr-config', str(directory / 'absent-player-config.json')]
    powershell = Path(os.environ['WINDIR']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    with subprocess.Popen(command, cwd=directory, creationflags=subprocess.CREATE_NO_WINDOW) as process:
        try:
            deadline = time.monotonic() + 30
            while process.poll() is None and time.monotonic() < deadline:
                messages = log.read_text(encoding='utf-8', errors='replace') if log.exists() else ''
                if 'XRGeneral Settings awakening...' in messages:
                    break
                time.sleep(.2)
            else:
                raise AssertionError('Packaged development player did not reach startup')
            script = ("@{tcp=@(Get-NetTCPConnection -State Listen -OwningProcess " + str(process.pid)
                      + " -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort);"
                      + "udp=@(Get-NetUDPEndpoint -OwningProcess " + str(process.pid)
                      + " -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort)} | ConvertTo-Json -Depth 3 -Compress")
            query = subprocess.run([str(powershell), '-NoProfile', '-NonInteractive', '-Command', script],
                                   capture_output=True, encoding='utf-8', timeout=10, check=True,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
            sockets = json.loads(query.stdout)
            messages = log.read_text(encoding='utf-8', errors='replace')
            result = {'processId': process.pid, **sockets, 'alive': process.poll() is None,
                      'gameNetworkStarted': 'VR_NETWORK_STARTED ' in messages,
                      'discoveryBroadcastStarted': 'Started UDP target info broadcast' in messages}
            (directory / 'local-profiler.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
            if (not result['alive'] or result['gameNetworkStarted'] or result['discoveryBroadcastStarted']
                    or len(sockets['tcp']) != 1 or sockets['tcp'][0]['LocalAddress'] != '127.0.0.1' or sockets['udp']):
                raise AssertionError('Unity PlayerConnection did not stay on loopback without discovery broadcast')
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)


def main():
    from windows_firewall import require_silent_windows_launch

    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('package_directory', type=Path)
    parser.add_argument('--check-openxr-unavailable', action='store_true', help='Run a graphical player with a missing OpenXR runtime for that process')
    parser.add_argument('--openxr-mock-manifest', type=Path, help='Also run the file preflight against this existing Unity mock manifest')
    parser.add_argument('--check-local-profiler', action='store_true', help='Check the actual owned Unity PlayerConnection sockets without a player config')
    parser.add_argument('--check-release-form', action='store_true', help='Exercise the shipped WinForms handlers with an actual owned OpenXR child')
    parser.add_argument('--release-report', type=Path, help='Original offline release report for this package')
    parser.add_argument('--other-release-report', type=Path, help='Original offline report for a different package')
    args = parser.parse_args(); folder = package.plain(args.package_directory)
    if os.name != 'nt' or folder.name != package.TOP: parser.error('Use an extracted Windows package')
    manifest = package.verify(folder)
    if manifest['launcherSourceSha256'] != package.digest(ROOT / 'tools/WindowsPlayerLauncher/PlayerLauncher.cs'):
        parser.error('Repackage the current launcher source before testing')
    if args.check_openxr_unavailable:
        require_silent_windows_launch(sys.executable)
    if args.check_openxr_unavailable or args.check_local_profiler or args.check_release_form:
        require_silent_windows_launch(folder / 'VrCommand.exe')
    directory = ROOT / 'artifacts/player-package-checks' / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    directory.mkdir(parents=True, exist_ok=False); findings = []

    def check(label, options, success=False, executable=None, manifest_hash=None):
        report = directory / ('report-' + str(len(findings)) + '.json')
        result = subprocess.run([str(executable or folder / 'Launch-Player.exe'), *options, '--report', str(report)],
                                cwd=directory, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        value = json.loads(report.read_text(encoding='utf-8'))
        expected = 'verified' if success else 'rejected'
        release_hash = package.digest(Path(options[options.index('--release-report') + 1])) if manifest_hash is not None else None
        if (result.returncode != (0 if success else 1) or value.get('status') != expected or 'processId' in value
                or value.get('playerManifestSha256') != manifest_hash or value.get('venueReleaseReportSha256') != release_hash):
            raise AssertionError('Actual launcher result differed: ' + label)
        findings.append(label); print('PASS:', label, flush=True)

    check('Actual launcher verifies the full extracted runtime', ['--verify'], success=True)
    rejected = subprocess.run([str(folder / 'Launch-Player.exe'), '--launch', '--headless'], cwd=directory,
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
    if rejected.returncode != 1 or b'Unable to start.' not in rejected.stderr:
        raise AssertionError('Invalid headless launch must exit without a dialog and report the error')
    findings.append('Invalid headless launch without a report exits with a terminal diagnostic')
    print('PASS:', findings[-1], flush=True)
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
    metrics = directory / 'original-link.json'
    check('Rejects link metrics without a waited launch and original log', ['--link-metrics', str(metrics)])
    with_log = [*common, '--log', str(future_log)]
    check('Rejects link metrics inside the delivered package', [*with_log, '--link-metrics', str(folder / 'link.json')])
    check('Rejects a link report with no parent directory', [*with_log, '--link-metrics', str(directory / 'missing' / 'link.json')])
    check('Rejects case-aliased link metrics and status output', [*with_log, '--link-metrics', str(metrics), '--status-report', str(metrics).upper()])
    check('Rejects duplicate link metrics options', [*with_log, '--link-metrics', str(metrics), '--link-metrics', str(directory / 'duplicate.json')])
    metrics.write_text('preserve original metrics', encoding='utf-8')
    check('Rejects existing link metrics without overwriting them', [*with_log, '--link-metrics', str(metrics)])
    assert metrics.read_text(encoding='utf-8') == 'preserve original metrics' and not future_log.exists() and not (folder / 'link.json').exists()
    manifest_hash = package.digest(folder / 'player-package.json')
    release = args.release_report.resolve(strict=True) if args.release_report else directory / 'venue-release.json'
    release_shape = {'verified': True, 'scope': 'offline-package-consistency', 'windows': {'playerManifestSha256': manifest_hash}}
    if not args.release_report:
        release.write_text(json.dumps(release_shape), encoding='utf-8-sig')
    original_release = release.read_bytes()
    check('Matches the original release and verifies every local package file', ['--verify', '--release-report', str(release)],
          success=True, manifest_hash=manifest_hash)
    same_manifest = directory / 'same-package-different-release-bytes.json'
    same_manifest.write_bytes(original_release + b'\n')
    check('Records distinct release report bytes for the same player package', ['--verify', '--release-report', str(same_manifest)],
          success=True, manifest_hash=manifest_hash)
    other_release = args.other_release_report.resolve(strict=True) if args.other_release_report else directory / 'different-release.json'
    if not args.other_release_report:
        other_release.write_text(json.dumps({**release_shape, 'windows': {'playerManifestSha256': '0' * 64}}), encoding='utf-8')
    other_bytes = other_release.read_bytes()
    assert json.loads(other_bytes.decode('utf-8-sig'))['windows']['playerManifestSha256'] != manifest_hash
    check('Refuses a different release before spawning any player', [*with_log, '--release-report', str(other_release)])
    for label, value in [('a legacy release without the player manifest', {**release_shape, 'windows': {}}),
                         ('an unverified release', {**release_shape, 'verified': False}),
                         ('a malformed manifest hash', {**release_shape, 'windows': {'playerManifestSha256': manifest_hash + '\n'}})]:
        invalid = directory / 'invalid-release.json'
        invalid.write_text(json.dumps(value), encoding='utf-8')
        check('Refuses ' + label, ['--verify', '--release-report', str(invalid)])
    check('Refuses duplicate release arguments without showing a modal', ['--verify', '--release-report', str(release), '--release-report', str(other_release)])
    check('Refuses a release report without verify or launch', ['--release-report', str(release)])
    evidence = directory / 'player-evidence.zip'
    with_release = [*with_log, '--release-report', str(release)]
    check('Rejects player evidence ZIP without an original release', [*with_log, '--evidence-zip', str(evidence)])
    check('Rejects player evidence ZIP inside the delivered package', [*with_release, '--evidence-zip', str(folder / evidence.name)])
    check('Rejects duplicate player evidence ZIP arguments', [*with_release, '--evidence-zip', str(evidence),
                                                            '--evidence-zip', str(directory / 'another.zip')])
    evidence.write_bytes(b'original evidence fixture')
    check('Preserves an existing player evidence ZIP', [*with_release, '--evidence-zip', str(evidence)])
    assert evidence.read_bytes() == b'original evidence fixture'
    assert not future_log.exists() and release.read_bytes() == original_release and other_release.read_bytes() == other_bytes
    preflight_manifest = check_openxr_preflight(folder, directory, args.openxr_mock_manifest)
    findings.append('Packaged OpenXR preflight reports registry, explicit manifests, PE architecture and output rejections')
    print('PASS:', findings[-1], flush=True)
    if args.check_local_profiler:
        check_local_profiler(folder, directory)
        findings.append('Actual Unity PlayerConnection listens only on loopback with no discovery broadcast')
        print('PASS:', findings[-1], flush=True)
    if args.check_openxr_unavailable:
        check_openxr_unavailable(folder, directory, base, release, manifest_hash)
        findings.append('Graphical OpenXR launch with a missing runtime exits before admission')
        print('PASS:', findings[-1], flush=True)
    if args.check_release_form:
        compiler = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
        runner = directory / 'release-form-checks.exe'
        subprocess.run([str(compiler), '/nologo', '/target:exe', '/platform:x64', '/warnaserror+',
                        '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll', '/reference:System.Web.Extensions.dll',
                        '/out:' + str(runner), str(ROOT / 'tools/WindowsPlayerLauncher/ReleaseFormChecks.cs')],
                       check=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        result = subprocess.run([str(runner), str(folder), str(directory), str(valid), str(release), str(other_release), str(preflight_manifest)],
                                capture_output=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
        (directory / 'release-form-run.log').write_bytes(result.stdout + result.stderr)
        result.check_returncode()
        reviewed = json.loads((directory / 'release-form-checks.json').read_bytes())
        assert reviewed['complete'] and reviewed['checks'] == 26
        findings.append('Shipped WinForms release selection rejects stale reports and publishes the owned child log digest')
        print('PASS:', findings[-1], flush=True)
    # A fresh minimal copy is intentionally incomplete. Never alter the delivered package.
    broken = directory / 'broken-package'; broken.mkdir(); shutil.copyfile(folder / 'Launch-Player.exe', broken / 'Launch-Player.exe')
    shutil.copyfile(folder / 'player-package.json', broken / 'player-package.json')
    check('Rejects missing runtime files', ['--verify'], executable=broken / 'Launch-Player.exe')
    check('Matching release alone cannot authorize an incomplete player package', ['--verify', '--release-report', str(release)],
          executable=broken / 'Launch-Player.exe')
    bad = json.loads(json.dumps(manifest)); bad['files'][0]['path'] = '../outside'
    (broken / 'player-package.json').write_text(json.dumps(bad), encoding='utf-8')
    check('Rejects a manifest path outside the package', ['--verify'], executable=broken / 'Launch-Player.exe')
    local = directory / 'minimal release fixture'
    local.mkdir()
    launcher = local / 'Launch-Player.exe'
    shutil.copyfile(folder / launcher.name, launcher)
    entries = [launcher]
    for name in ('VrCommand.exe', 'UnityPlayer.dll', 'VrCommand_Data/globalgamemanagers', 'build-receipt.json'):
        file = local / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b'fixture')
        entries.append(file)
    local_manifest = local / 'player-package.json'
    local_manifest.write_text(json.dumps({'version': 1, 'platform': 'Windows-x64', 'files': [
        {'path': file.relative_to(local).as_posix(), 'sha256': package.digest(file), 'bytes': file.stat().st_size}
        for file in entries]}), encoding='utf-8')
    local_release = directory / 'minimal-release.json'
    local_hash = package.digest(local_manifest)
    local_release.write_text(json.dumps({**release_shape, 'windows': {'playerManifestSha256': local_hash}}), encoding='utf-8')
    check('Release verification accepts a fixture with exactly its original manifest files',
          ['--verify', '--release-report', str(local_release)], success=True, executable=launcher, manifest_hash=local_hash)
    (local / 'VrCommand_Data' / 'unexpected.dll').write_bytes(b'unlisted fixture')
    check('Release verification rejects an unlisted file inside the runtime even when every listed file matches',
          ['--verify', '--release-report', str(local_release)], executable=launcher)
    for report in directory.glob('report-*.json'):
        if 'fixture-secret' in report.read_text(encoding='utf-8') or 'fixture-not-a-ticket' in report.read_text(encoding='utf-8'):
            raise AssertionError('Diagnostic report leaked fixture credentials')
    result = {'complete': True, 'checks': len(findings), 'findings': findings, 'packageDirectory': str(folder),
              'launcherSourceSha256': manifest['launcherSourceSha256'],
              'scope': 'Actual Windows launcher preflight and selected startup rejection; no game admission, GUI input or headset verification'}
    (directory / 'checks.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'complete': True, 'checks': len(findings), 'directory': str(directory)}))


if __name__ == '__main__': main()
