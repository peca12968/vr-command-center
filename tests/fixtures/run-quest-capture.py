"""Run the capture CLI with a fixture in place of the ADB executable."""

import asyncio
import json
from pathlib import Path
import runpy
import subprocess
import sys


def fake_adb(args):
    transports = json.loads(Path('adb-transports.json').read_bytes())
    with Path('adb-calls.jsonl').open('a', encoding='utf-8') as log:
        log.write(json.dumps(args) + '\n')
    if args == ['devices', '-l']:
        print('List of devices attached')
        for serial, transport in transports.items():
            print(f'{serial} device transport_id:{transport}')
        return
    if args[0] == '-t':
        serials = [serial for serial, transport in transports.items() if str(transport) == args[1]]
        if len(serials) != 1:
            sys.exit(1)
        serial, = serials
    else:
        assert args[0] == '-s'
        serial = args[1]
    sys.argv = [serial, *args[2:]]
    runpy.run_path(serial, run_name='__main__')


if sys.argv[1:2] == ['--fake-adb']:
    fake_adb(sys.argv[2:])
else:
    fixture = Path(__file__).resolve()
    command = str(Path(sys.executable).resolve())
    capture = fixture.parents[2] / 'scripts' / 'capture-quest-field-log.py'
    run = subprocess.run
    start = asyncio.create_subprocess_exec

    def route(args):
        if str(args[0]) == command:
            return [command, str(fixture), '--fake-adb', *args[1:]]
        return args

    def run_command(args, *positional, **keywords):
        return run(route(args), *positional, **keywords)

    async def start_command(*args, **keywords):
        return await start(*route(args), **keywords)

    subprocess.run = run_command
    asyncio.create_subprocess_exec = start_command
    sys.path.insert(0, str(capture.parent))
    sys.argv[0] = str(capture)
    runpy.run_path(str(capture), run_name='__main__')
