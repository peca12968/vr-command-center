"""Compile the real Windows player config review against replacement/edit fixtures."""
import argparse, hashlib, json, os, subprocess, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    compiler = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    if os.name != 'nt' or not compiler.is_file(): parser.error('Requires Windows and the installed Framework compiler')
    directory = ROOT / 'artifacts/player-review-checks' / ('run-' + uuid.uuid4().hex)
    directory.mkdir(parents=True, exist_ok=False)
    sources = [ROOT / 'tools/WindowsPlayerLauncher' / n for n in ['PlayerLauncher.cs', 'ConfigReviewChecks.cs']]
    exe = directory / 'checks.exe'
    done = subprocess.run([str(compiler), '/nologo', '/target:exe', '/platform:x64', '/warnaserror+', '/main:PlayerReviewChecks',
        '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll', '/reference:System.Web.Extensions.dll', '/reference:System.IO.Compression.dll',
        '/out:' + str(exe), *map(str, sources)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
    (directory / 'compile.log').write_bytes(done.stdout)
    if done.returncode: raise RuntimeError('ConfigReview compilation failed; preserve log')
    run = subprocess.run([str(exe), str(directory / 'fixtures')], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    (directory / 'run.log').write_bytes(run.stdout)
    if run.returncode: raise RuntimeError('ConfigReview checks failed; preserve log')
    report = json.loads(run.stdout.decode('utf-8'))
    assert report['complete'] and report['checks'] == 36
    report['sourceHashes'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    (directory / 'checks.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'complete': True, 'checks': report['checks'], 'directory': str(directory)}))

if __name__ == '__main__': main()
