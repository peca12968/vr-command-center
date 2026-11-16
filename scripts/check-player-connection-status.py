"""Compile and run the actual Windows launcher status class against bounded log fixtures.

This is not native admission or GUI evidence; check-external-native.cjs --launcher-status
separately uses real downloaded tickets, native clients and authoritative sealed results.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path, default=Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe')
    args = parser.parse_args()
    if os.name != 'nt' or not args.compiler.is_file(): parser.error('Requires Windows and the installed .NET Framework compiler')
    directory = ROOT / 'artifacts/launcher-status-checks' / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]); directory.mkdir(parents=True, exist_ok=False)
    sources = [ROOT / 'tools/WindowsPlayerLauncher' / name for name in ['PlayerLauncher.cs', 'ConnectionStatusChecks.cs']]
    sources.append(ROOT / 'tools/WindowsFirewallPreflight.cs')
    executable = directory / 'checks.exe'
    result = subprocess.run([str(args.compiler), '/nologo', '/target:exe', '/platform:x64', '/optimize+', '/warnaserror+', '/main:LauncherStateChecks',
        '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll', '/reference:System.Web.Extensions.dll',
        '/reference:System.IO.Compression.dll', '/out:' + str(executable), *map(str, sources)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
    (directory / 'compile.log').write_bytes(result.stdout)
    if result.returncode: raise RuntimeError('Actual launcher monitor compilation failed; preserve the compile log')
    run = subprocess.run([str(executable), str(directory / 'fixtures')], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    (directory / 'run.log').write_bytes(run.stdout)
    if run.returncode: raise RuntimeError('Actual launcher monitor checks failed; preserve the run log')
    report = json.loads(run.stdout.decode('utf-8')); assert report['complete'] and report['checks'] == 46
    report['sourceHashes'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    (directory / 'checks.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'complete': True, 'checks': report['checks'], 'directory': str(directory), 'sourceHashes': report['sourceHashes']}))


if __name__ == '__main__': main()
