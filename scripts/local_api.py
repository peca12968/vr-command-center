"""Resolve the exact management API process used by local integration tests."""

import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def add_api_arguments(parser):
    api = parser.add_mutually_exclusive_group()
    api.add_argument('--api-dll', type=Path, help='Managed API assembly to run with the installed dotnet host')
    api.add_argument('--api-exe', type=Path, help='VrCommand.Api.exe in an extracted Windows management package')


def api_command(args):
    executable = getattr(args, 'api_exe', None)
    if executable is not None:
        executable = executable.resolve(strict=True)
        assembly = executable.with_suffix('.dll')
        if executable.name.lower() != 'vrcommand.api.exe' or not executable.is_file() or not assembly.is_file():
            raise ValueError('Use VrCommand.Api.exe alongside VrCommand.Api.dll from the Windows management package')
        return [str(executable)], executable.parent, assembly

    assembly = getattr(args, 'api_dll', None) or Path(os.environ.get('VR_COMMAND_API_DLL',
        ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll'))
    dotnet = shutil.which('dotnet')
    if not dotnet or not assembly.is_file():
        raise RuntimeError('Build the API and install dotnet, or specify --api-exe')
    assembly = assembly.resolve(strict=True)
    return [str(Path(dotnet).resolve(strict=True)), str(assembly)], ROOT, assembly


def checked_api_command(args):
    from windows_firewall import require_silent_windows_launch

    command, cwd, assembly = api_command(args)
    require_silent_windows_launch(command[0])
    return command, cwd, assembly
