"""Package an actually built Windows player plus an offline config-picker launcher.

No tickets, server configs, journals or API binaries are included. This does not
sign the package or attest to headset, LAN or hardware compatibility.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOP = 'VRCommand-Player'
RUNTIME = ('VrCommand.exe', 'UnityPlayer.dll', 'UnityCrashHandler64.exe', 'WinPixEventRuntime.dll',
           'D3D12', 'MonoBleedingEdge', 'VrCommand_Data')
META_SUBSYSTEM_JSON = 'VrCommand_Data/UnitySubsystems/libUnityARFoundationMeta/UnitySubsystemsManifest.json'
# Byte-for-byte copy emitted by Unity from com.unity.xr.meta-openxr 2.3.2.
META_SUBSYSTEM_SHA256 = '1b948c6cf83c2b90b1e8f217d83ed17d8f4761702f6204e75dbeca698572aed2'
RUNTIME_JSON = {'build-receipt.json', 'VrCommand_Data/RuntimeInitializeOnLoads.json', 'VrCommand_Data/ScriptingAssemblies.json',
                'VrCommand_Data/UnitySubsystems/UnityOpenXR/UnitySubsystemsManifest.json', META_SUBSYSTEM_JSON}
NOTICES = {
    'clients/unity/Packages/com.unity.transport/LICENSE.md': 'Notices/Unity-Transport-LICENSE.md',
    'clients/unity/Packages/com.unity.transport/UPSTREAM.json': 'Notices/Unity-Transport-UPSTREAM.json',
    'clients/unity/ThirdPartyNotices/UnityUrpTemplate-LICENSE.md': 'Notices/Unity-URP-Template-LICENSE.md',
    'clients/unity/Assets/VrCommand/Resources/VrCommand/Fonts/OFL.txt': 'Notices/Font-OFL.txt',
    'clients/unity/Assets/VrCommand/Resources/VrCommand/Fonts/NOTICE.txt': 'Notices/Font-NOTICE.txt',
}
README = '''VR Command Windows 玩家包

1. 完整解壓 ZIP 至本機資料夾，不要只取出 EXE，也不要直接在 ZIP 中執行。
2. 開啟 Launch-Player.exe，選擇控制人員從控制台下載的玩家連線檔（JSON），或貼上完整路徑後按 Enter 載入。
3. 核對地址與席位，選擇桌面模式（Alt+D）或 Windows OpenXR（Alt+O），再按「開始遊戲」（Alt+S）。
4. 票券為短效；過期、移除或入場被拒時，向控制人員重新取得連線檔。
路徑編輯或載入失敗會解除舊選取；開始前若檔案已變更，須重新載入並核對地址。遊戲已啟動後，原路徑更新與Reconnect仍使用原驗票流程。
啟動前的票券倒數依本機時間顯示，入場由遊戲伺服器驗證。

WASD移動；方向鍵或按住右鍵拖曳瞄準；Space／左鍵射擊；R換彈；B任務簡報；Escape關閉簡報。
任務由控制人員開始、暫停與結束。啟動器顯示「正在等待最終戰績」時，請保留遊戲視窗。等待期間若中斷，可請控制人員從原場次確認戰績。
同次入場斷線可在遊戲的Reconnect按鈕重新讀取原路徑的最新票券。
啟動器 1.18 可用 --refresh-player-ticket "原連線.json" "新連線.json" --report "新更新報告.json" 更新同一入場的原檔。三個參數使用本機完整路徑。更新確認後，在原遊戲內重新連線。

Windows 開發版自 0.46.0 起支援連線量測。指定新 JSON 絕對路徑，上層目錄須已存在。結果含往返時間、逾時與 Unity 更新次數。
啟動器 1.5 可在 --launch --wait --log 新日誌 --report 新程序報告 加上 --link-metrics 新量測.json。程序結束時會在程序報告保存原日誌與量測檔的 SHA-256，供封存驗收核對。請保留三個原檔。
啟動器 1.6 可在 --verify 或 --launch 加上 --release-report 原發行報告.json，逐檔核對場館交付的 Windows 玩家套件。
啟動器 1.9 可在視窗選擇或貼上場館發行報告，核對後再開始遊戲。遊戲關閉後按「開啟本次紀錄資料夾」，保留同一次的 player.log 與 launch-report.json。
啟動器 1.11 會核對等待場次、完整最終戰績及結束斷線。已核對發行並正常退出後才建立 player-evidence.zip，包含原日誌及退出報告。命令列可搭配 --launch --wait --release-report --log --report 指定 --evidence-zip 新檔案.zip。
啟動器 1.12 同時指定 --link-metrics 和 --evidence-zip 時，會將同次原始量測一併封入 ZIP。主控可從收件資料夾逐席核對原量測。
啟動器 1.14.1 可在視窗核對場館發行報告後勾選「記錄本次連線量測」。量測結案時，視窗會顯示回覆、逾時和中斷數。收到最終戰績並關閉遊戲後，從本次紀錄資料夾取出驗收 ZIP。
啟動器 1.7 在發行核對搭配 --wait --log 新日誌 --report 新程序報告 時，另在終止報告保存原玩家日誌的 SHA-256，供五房封存驗收。

環境：Windows x64、適用的圖形驅動及 .NET Framework 4.8；不需要Unity Editor、Python或.NET 10 SDK。
來源、場景與伺服器須同版。平常使用桌面合成頭手，實際Simulation／GameServer來源以場次為準。
接到支援的 Windows OpenXR 執行環境時，可使用 Launch-Player.exe --config "玩家連線檔" --launch --openxr --wait 進入 VR。頭盔及控制器相容性需現場驗收。
啟動器 1.15 可在入場前用 Launch-Player.exe --check-openxr --report "包外新報告.json" 檢查 Windows OpenXR 清單與 x64 DLL 標頭。報告上層目錄須已存在。退出碼 0 表示找到檔案，1 表示請查看報告的狀態，2 表示命令或報告路徑有誤。
啟動器 1.16 可直接在視窗按「檢查 OpenXR」（Alt+X），查看本機檔案檢查結果。連線檔可在檢查後再載入。
127.*只供同機連線，其他玩家必須能連到伺服器公告的IPv4與UDP埠。
本包不修改防火牆、不安裝驅動、不提供NAT或中繼，也沒有驗證你的網路。

連線檔包含短效票券，請個別交付；不要放進共用玩家包或重新分享。
玩家包沒有主控台或GameServer金鑰。離線核對只檢查格式／完整性；票券與入場由伺服器驗證。
player-package.json為SHA256檔案清單與建置來源紀錄，並非數位簽章或可信發行者證明。
build-receipt.json為原Unity成功建置紀錄，不代表實機／跨機／25台測試成功。
Notices/保留相關素材與套件授權；遊戲資源內亦保留原字型授權頁。
'''


def digest(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def plain(path):
    """Do not follow symbolic links or Windows junctions while collecting files."""
    path = Path(os.path.abspath(path))
    for entry in (path, *path.parents):
        if entry.is_symlink() or (hasattr(entry, 'is_junction') and entry.is_junction()):
            raise ValueError('Package paths must not use symbolic links or junctions')
    return path


def source_fingerprint():
    spec = importlib.util.spec_from_file_location('package_source_check', ROOT / 'scripts/check-unity-admission.py')
    checker = importlib.util.module_from_spec(spec); spec.loader.exec_module(checker)
    return checker.source_fingerprint()


def collect(player):
    player = plain(player)
    receipt = json.loads((player / 'build-receipt.json').read_text(encoding='utf-8'))
    if receipt.get('schemaVersion') != 1 or receipt.get('target') != 'StandaloneWindows64' or receipt.get('sourceFingerprint') != source_fingerprint():
        raise ValueError('Build Desktop from the current source before packaging')
    if Path(receipt.get('outputPath', '')).resolve() != (player / 'VrCommand.exe').resolve():
        raise ValueError('Receipt must describe this actual Windows player output')
    files = []
    for name in (*RUNTIME, 'build-receipt.json'):
        entry = plain(player / name)
        if not entry.exists(): raise FileNotFoundError('Required player output is missing: ' + name)
        entries = [entry] if entry.is_file() else sorted(entry.rglob('*'))
        for file in entries:
            plain(file)
            if file.is_file():
                relative = file.relative_to(player).as_posix()
                # Build-time debug directories are outside the runtime allowlist.
                # Unexpected credentials / runtime state inside a runtime tree fail closed.
                if file.suffix.lower() in ('.key', '.journal', '.worldlog', '.db', '.sqlite', '.log') or (file.suffix.lower() == '.json' and relative not in RUNTIME_JSON):
                    raise ValueError('Runtime input contains private state; rebuild a clean player')
                if relative == META_SUBSYSTEM_JSON and (file.stat().st_size != 181 or digest(file) != META_SUBSYSTEM_SHA256):
                    raise ValueError('Unexpected Unity Meta subsystem manifest')
                files.append((file, relative))
    return receipt, files


def relative_file(folder, name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name or any(part in ('', '.', '..') for part in name.split('/')) or PurePosixPath(name).is_absolute():
        raise ValueError('Invalid package path')
    return plain(folder / name)


def verify(folder, *, manifest_bytes=None):
    folder = plain(folder)
    if manifest_bytes is None:
        manifest_bytes = plain(folder / 'player-package.json').read_bytes()
    manifest = json.loads(manifest_bytes.decode('utf-8'))
    if manifest.get('version') != 1 or manifest.get('platform') != 'Windows-x64' or not isinstance(manifest.get('files'), list):
        raise ValueError('Unsupported player package')
    seen = set()
    for row in manifest['files']:
        file = relative_file(folder, row['path']); name = row['path'].lower()
        if name in seen or not isinstance(row['bytes'], int) or row['bytes'] < 0 or not re.fullmatch('[a-f0-9]{64}', row['sha256']): raise ValueError('Invalid package file entry')
        seen.add(name)
        if file.stat().st_size != row['bytes'] or digest(file) != row['sha256']: raise ValueError('Package content differs: ' + row['path'])
    if not {'vrcommand.exe', 'unityplayer.dll', 'launch-player.exe', 'vrcommand_data/globalgamemanagers', 'build-receipt.json'} <= seen:
        raise ValueError('Required package files missing')
    return manifest


def package(player, output, compiler):
    receipt, files = collect(player)
    output = plain(output)
    if output.exists(): raise FileExistsError('Never overwrite an existing package')
    output.parent.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'tools/WindowsPlayerLauncher/PlayerLauncher.cs'
    # All transient copies belong to one new workspace folder; no existing build is edited.
    with tempfile.TemporaryDirectory(prefix='player-package-', dir=ROOT / 'artifacts') as temporary:
        folder = Path(temporary) / TOP; folder.mkdir()
        for file, relative in files:
            target = folder / relative; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(file, target)
            if digest(file) != digest(target): raise ValueError('Player changed while copying')
        for original, relative in NOTICES.items():
            target = folder / relative; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT / original, target)
        (folder / '開始使用.txt').write_text(README, encoding='utf-8-sig')
        subprocess.run([str(compiler), '/nologo', '/target:winexe', '/platform:x64', '/optimize+', '/warnaserror+',
                        '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll', '/reference:System.Web.Extensions.dll',
                        '/reference:System.IO.Compression.dll',
                        '/resource:' + str(ROOT / 'scripts/check-windows-firewall-notifications.ps1') + ',FirewallPreflight.ps1',
                        '/out:' + str(folder / 'Launch-Player.exe'), str(source),
                        str(ROOT / 'tools/WindowsFirewallPreflight.cs')], check=True)
        manifest = {'version': 1, 'platform': 'Windows-x64', 'launcherVersion': '1.18', 'createdAtUtc': datetime.now(timezone.utc).isoformat(),
                    'build': receipt, 'launcherSourceSha256': digest(source), 'scope': 'Offline portable PC player; no tickets; not a signature or network/device verification',
                    'files': [{'path': file.relative_to(folder).as_posix(), 'bytes': file.stat().st_size, 'sha256': digest(file)}
                              for file in sorted(folder.rglob('*')) if file.is_file()]}
        (folder / 'player-package.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        verify(folder)
        # Exclusive creation preserves any prior package, including on failure.
        with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for file in sorted(folder.rglob('*')):
                if file.is_file(): archive.write(file, TOP + '/' + file.relative_to(folder).as_posix())
        with zipfile.ZipFile(output) as archive:
            if archive.testzip() is not None: raise ValueError('ZIP checksum failed')
        return {'complete': True, 'zip': str(output), 'sha256': digest(output), 'bytes': output.stat().st_size,
                'files': len(manifest['files']), 'sourceFingerprint': receipt['sourceFingerprint'], 'launcherSourceSha256': digest(source)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--player-directory', type=Path, default=ROOT / 'artifacts/desktop')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--compiler', type=Path, default=Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe')
    parser.add_argument('--verify', type=Path, help='Verify an extracted package, without compiling or running it')
    args = parser.parse_args()
    if args.verify:
        result = verify(args.verify); print(json.dumps({'complete': True, 'files': len(result['files'])})); return
    if os.name != 'nt' or not args.compiler.is_file(): parser.error('Use Windows with the installed .NET Framework compiler')
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
    output = args.output or ROOT / 'artifacts/player-packages' / ('windows-' + stamp + '.zip')
    result = package(args.player_directory, output, args.compiler)
    with output.with_suffix('.receipt.json').open('x', encoding='utf-8') as file: file.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__': main()
