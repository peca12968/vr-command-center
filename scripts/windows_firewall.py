"""Check the exact executable before starting Windows network fixtures."""

import os
from pathlib import Path
import shutil
import subprocess


class WindowsFirewallLaunchError(RuntimeError):
    """The executable could not be cleared for unattended startup."""


def require_silent_windows_launch(executable):
    if os.name != 'nt':
        return

    executable = Path(executable).resolve(strict=True)
    checker = Path(__file__).with_name('check-windows-firewall-notifications.ps1')
    powershell = shutil.which('pwsh') or 'powershell.exe'
    try:
        result = subprocess.run(
            [powershell, '-NoLogo', '-NoProfile', '-NonInteractive', '-File', str(checker),
             '-Executable', str(executable)],
            env={**os.environ, 'VR_COMMAND_UNATTENDED': '1'},
            creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True, text=True, errors='replace', timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise WindowsFirewallLaunchError(
            f'Startup skipped for {executable.name}. Could not complete the Windows Firewall check.'
        ) from error
    if result.returncode:
        detail = result.stderr.strip() or f'Firewall check exited with code {result.returncode}.'
        raise WindowsFirewallLaunchError(f'Startup skipped for {executable.name}. {detail}')


def start_checked_windows_process(command, **options):
    """Recheck the exact image at each native launch."""
    executable = Path(command[0]).resolve(strict=True)
    require_silent_windows_launch(executable)
    if os.name == 'nt':
        environment = options.get('env')
        options['env'] = {**(os.environ if environment is None else environment), 'VR_COMMAND_UNATTENDED': '1'}
    return subprocess.Popen([str(executable), *command[1:]], executable=str(executable), **options)
