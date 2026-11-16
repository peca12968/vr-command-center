"""Publish and verify the self-contained Windows recording recovery tool."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = 'tools/VrCommand.WorldRelay/VrCommand.WorldRelay.csproj'
INPUTS = ('global.json', 'Directory.Build.props', 'tools/VrCommand.WorldRelay',
          'src/VrCommand.Core', 'src/VrCommand.Simulation', 'clients/unity/Packages/com.vrcommand.simulation/Runtime')
VERSION = '0.1.1'
RUNTIME = '10.0.14'
TOP = 'VRCommand-RecordingRecovery'
NOTICE_FILES = ('LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT')
FILES = {'Recover-Recording.exe', 'README.txt', *NOTICE_FILES}
README = r"""VR Command Windows 場次錄製補送 0.1.1

在原遊戲伺服器已退出後，由操作員結束原管理場次。保留原工作資料夾的 server-config.json 與 telemetry 裡的兩份原始日誌。
請以原設定檔執行，另指定尚不存在的工作資料夾。上層資料夾須先存在。

  .\Recover-Recording.exe --recover-server 'C:\private\server-work\server-config.json' --work 'C:\private\recovered-room1'

工具以唯讀獨占方式開啟原日誌，在工作副本確認原伺服器、場次、來源及已接受邊界，再補送已落盤的紀錄。
HTTPS 管理實例使用原設定中的 managementCertificateSha256，補送戰鬥及世界回放均須符合原站台憑證。
成功後讀取工作資料夾的 recovery.json。worldSealed 與 combatSealed 各自表示該來源是否已封存。
若原日誌未保存結尾，可在主控台播放補送後的保存片段。出現錯誤時保留原件，依狀況修正後用新的工作資料夾重試。
遊戲程序不會由此工具啟動。原設定檔含 GameServer 金鑰，請與兩份日誌及補送資料私下保管。
本包自含 Windows x64 .NET 執行環境。操作說明見專案 docs/WINDOWS_SERVER_PACKAGE.md。
"""


def sha(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify(folder):
    manifest = read(folder / 'recovery-package.json')
    if ((manifest.get('schemaVersion'), manifest.get('target'), manifest.get('runtime')) != (1, 'win-x64', RUNTIME)
            or manifest.get('version') not in ('0.1.0', VERSION)):
        raise ValueError('Unexpected Windows recovery package')
    if set(manifest['files']) != FILES or {path.name for path in folder.iterdir()} != FILES | {'recovery-package.json'}:
        raise ValueError('Unexpected recovery package payload')
    for name, expected in manifest['files'].items():
        path = folder / name
        if path.is_symlink() or not path.is_file() or expected != {'bytes': path.stat().st_size, 'sha256': sha(path)}:
            raise ValueError('Recovery package integrity mismatch: ' + name)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage-root', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        print(json.dumps({'complete': True, 'files': len(verify(args.verify)['files'])}))
        return
    if os.name != 'nt' or not args.stage_root or not args.output or args.output.suffix.lower() != '.zip':
        parser.error('Build on Windows with --stage-root and a new --output ZIP')
    output = args.output.resolve()
    if output.exists() or output.with_suffix('.receipt.json').exists():
        parser.error('Use new output paths')

    stage = args.stage_root.resolve() / ('recovery-' + uuid.uuid4().hex)
    stage.mkdir(parents=True, exist_ok=False)
    source = stage / 'source'
    inputs = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '--', *INPUTS],
                                     cwd=ROOT, text=True, encoding='utf-8').splitlines()
    source_hashes = {}
    for name in sorted(set(inputs)):
        path = ROOT / name
        if path.is_symlink() or {'bin', 'obj', 'data'} & set(Path(name).parts):
            raise ValueError('Unexpected recovery source')
        destination = source / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        source_hashes[name] = sha(destination)
    locks = {name: read(source / name)['dependencies'] for name in source_hashes if name.endswith('packages.lock.json')}
    packages = stage / 'packages'
    project = source / PROJECT
    common = ['--artifacts-path', str(stage / 'build'), '-r', 'win-x64', '-p:SelfContained=true',
              '-p:PublishSingleFile=true', '-p:IncludeNativeLibrariesForSelfExtract=true', '-p:RuntimeFrameworkVersion=' + RUNTIME,
              '-p:RestorePackagesPath=' + str(packages)]
    publication = stage / 'publish'
    with (stage / 'build.log').open('xb') as log:
        for command in (['restore', str(project), '--force-evaluate', *common],
                        ['publish', str(project), '-c', 'Release', '--no-restore', '-o', str(publication), *common]):
            subprocess.run(['dotnet', *command], cwd=source, stdout=log, stderr=subprocess.STDOUT, check=True)
    for name, original in locks.items():
        after = read(source / name)['dependencies']
        for group, expected in original.items():
            entries = after.get(group, {}).copy()
            if 'Microsoft.NET.ILLink.Tasks' not in expected and 'Microsoft.NET.ILLink.Tasks' in entries:
                if entries.pop('Microsoft.NET.ILLink.Tasks').get('resolved') != RUNTIME:
                    raise ValueError('Unexpected single-file analyzer version')
            if entries != expected:
                raise ValueError('An original NuGet pin changed')
    if any(sha(ROOT / name) != digest for name, digest in source_hashes.items()):
        raise ValueError('Recovery source changed during publication')

    folder = stage / TOP
    folder.mkdir()
    shutil.copyfile(publication / 'VrCommand.WorldRelay.exe', folder / 'Recover-Recording.exe')
    (folder / 'README.txt').write_text(README, encoding='utf-8')
    for name in NOTICE_FILES:
        shutil.copyfile(packages / 'microsoft.netcore.app.runtime.win-x64' / RUNTIME / name, folder / name)
    manifest = {'schemaVersion': 1, 'version': VERSION, 'target': 'win-x64', 'runtime': RUNTIME, 'sourceFiles': source_hashes,
                'files': {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(folder.iterdir())}}
    (folder / 'recovery-package.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    verify(folder)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(folder.iterdir()):
            archive.write(path, TOP + '/' + path.name)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError('Recovery package ZIP CRC failed')
    receipt = {'complete': True, 'directory': str(folder), 'zip': str(output), 'bytes': output.stat().st_size,
               'sha256': sha(output), 'files': len(FILES), 'sourceFiles': len(source_hashes)}
    with output.with_suffix('.receipt.json').open('x', encoding='utf-8') as report:
        json.dump(receipt, report, indent=2)
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
