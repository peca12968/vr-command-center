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


def install(adb, serial, apk):
    from quest_adb import read_adb_transports, select_adb_transport
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
        return result.stdout.decode('utf-8').strip()

    if invoke('shell', 'getprop', 'ro.product.model') != 'Quest 3':
        raise ValueError('The selected device must be a Meta Quest 3.')
    packages = invoke('shell', 'pm', 'list', 'packages', PACKAGE).splitlines()
    installed = 'package:' + PACKAGE in packages
    if not installed:
        with tempfile.TemporaryDirectory(prefix='vr-quest-probe-') as directory:
            staged = Path(directory) / APK_NAME
            staged.write_bytes(data)
            invoke('install', str(staged), timeout=90)
    path = re.fullmatch(r'package:((?:/[A-Za-z0-9._=+~-]+)+/base\.apk)', invoke('shell', 'pm', 'path', PACKAGE))
    if path is None or invoke('shell', 'sha256sum', path[1]).split()[:1] != [APK_SHA256]:
        raise ValueError('The diagnostic installed on the Quest differs from the venue release.')
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
