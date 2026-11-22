"""Install the venue kit's verified network diagnostic on one authorized Quest 3."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


PACKAGE = 'com.vrcommand.udpprobe'
APK_NAME = 'vr-command-quest-udp-probe-0.1.0.apk'
APK_BYTES = 16588
APK_SHA256 = '478bcd63b9d79aca638d49049388021241245a6f046f3221fd95b0ba6e2f4c1f'
APK_PATH = r'((?:/[A-Za-z0-9._=+~-]+)+/base\.apk)'


def install(adb, serial, apk):
    from quest_adb import android_user_id, read_adb_transports, select_adb_transport
    from windows_firewall import require_silent_windows_launch

    with apk.open('rb') as stream:
        data = stream.read(APK_BYTES + 1)
    if hashlib.sha256(data).hexdigest() != APK_SHA256:
        raise ValueError('The diagnostic APK differs from the supported venue release.')
    command = [str(adb.resolve(strict=True))]
    require_silent_windows_launch(command[0])
    target = select_adb_transport(command, read_adb_transports(command, 5), serial)

    def invoke(*args, timeout=10):
        require_silent_windows_launch(command[0])
        result = subprocess.run([*target, *args], stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise ValueError('The selected Quest did not complete the diagnostic installation check.')
        return result.stdout

    if invoke('shell', 'getprop', 'ro.product.model').strip() != b'Quest 3':
        raise ValueError('The selected device must be a Meta Quest 3.')
    user_query = ('shell', 'am', 'get-current-user')
    user = android_user_id(invoke(*user_query))

    def packages(*flags):
        lines = invoke('shell', 'pm', 'list', 'packages', *flags, '--user', user, PACKAGE).decode().splitlines()
        if any(not line.startswith('package:') for line in lines):
            raise ValueError('Could not check Android packages for the selected Quest user.')
        return lines

    def verify(path):
        if not re.fullmatch(APK_PATH, path):
            raise ValueError('Could not identify the installed Quest diagnostic APK.')
        if invoke('shell', 'sha256sum', path).decode().split() != [APK_SHA256, path]:
            raise ValueError('The diagnostic installed on the Quest differs from the venue release.')

    installed = 'package:' + PACKAGE in packages()
    if not installed:
        # Android shares the APK across users, while installation and private files are per user.
        existing = [line for line in packages('-f', '-u') if line.endswith('=' + PACKAGE)]
        if existing:
            if len(existing) != 1:
                raise ValueError('Could not identify one shared Quest diagnostic APK.')
            verify(existing[0][len('package:'):-(len(PACKAGE) + 1)])
            invoke('shell', 'pm', 'install-existing', '--user', user, PACKAGE)
        else:
            with tempfile.TemporaryDirectory(prefix='vr-quest-probe-') as directory:
                staged = Path(directory) / APK_NAME
                staged.write_bytes(data)
                invoke('install', '-R', '--user', user, '--pkg', PACKAGE, str(staged), timeout=90)
    if 'package:' + PACKAGE not in packages('-e'):
        raise ValueError('The Quest diagnostic is unavailable for the selected Android user.')
    path = re.fullmatch('package:' + APK_PATH, invoke('shell', 'pm', 'path', '--user', user, PACKAGE).decode().rstrip('\r\n'))
    if path is None:
        raise ValueError('Could not identify the installed Quest diagnostic APK.')
    verify(path[1])
    if android_user_id(invoke(*user_query)) != user:
        raise ValueError('The foreground Android user changed during diagnostic installation.')
    return {'status': 'already-installed' if installed else 'installed', 'sha256': APK_SHA256}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', required=True, type=Path)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--apk', type=Path, default=Path(__file__).resolve().parents[1] / 'Quest/Diagnostics' / APK_NAME)
    args = parser.parse_args()
    os.environ['VR_COMMAND_UNATTENDED'] = '1'
    from windows_firewall import WindowsFirewallLaunchError
    try:
        result = install(args.adb, args.serial, args.apk)
    except (ValueError, WindowsFirewallLaunchError) as error:
        parser.exit(1, str(error) + '\n')
    except (OSError, subprocess.SubprocessError):
        parser.exit(1, 'Could not read the diagnostic APK or reach the selected Quest.\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
