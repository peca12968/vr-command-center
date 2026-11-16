"""Check the exact executable before starting Windows network fixtures."""

import os
from pathlib import Path
import shutil
import subprocess


def require_silent_windows_launch(executable):
    if os.name != 'nt':
        return

    executable = Path(executable).resolve(strict=True)
    checker = Path(__file__).with_name('check-windows-firewall-notifications.ps1')
    powershell = shutil.which('pwsh') or 'powershell.exe'
    result = subprocess.run(
        [powershell, '-NoLogo', '-NoProfile', '-NonInteractive', '-File', str(checker),
         '-Executable', str(executable)],
        creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True, text=True, errors='replace', timeout=15,
    )
    if result.returncode:
        detail = result.stderr.strip() or f'Firewall check exited with code {result.returncode}.'
        raise RuntimeError(f'Startup skipped for {executable.name}. {detail}')
