"""Package the tested offline simulator and live loopback mock rehearsal."""
import argparse,hashlib,json,shutil,uuid,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=['VrCommand.HardwareSimulator.dll','VrCommand.HardwareSimulator.deps.json','VrCommand.HardwareSimulator.runtimeconfig.json','VrCommand.Core.dll','VrCommand.Simulation.dll']
VERSION='0.2.2'
README=f'''VR Command 硬體回饋模擬器 {VERSION}

需要 .NET 10 runtime，本機使用10.0.14驗證。這不是Unity玩家程式或廠商SDK。
在解壓目錄執行（請把輸出放在包外的新檔案）：
dotnet VrCommand.HardwareSimulator.dll --input example.json --output <新的包外report.json>

即時模式使用 Windows 管理包 0.31.27 以上與同房房控憑證。Python 3.12 可啟動本機模擬設備：
python mock-device.py --port 19101
在另一個終端設定 VR_COMMAND_ROOM_KEY，再執行：
dotnet VrCommand.HardwareSimulator.dll --live <包外room-config.json> --output <新的包外report.json>
即時模式可加上 --stop-file <尚不存在的本機標記檔>。每個程序使用獨立路徑。建立空白標記檔後，該程序關閉模擬連線，待確認的批次記為 cancelled，報告終止原因為 operator-stop。
配置範例、模擬協議和操作方式見專案 docs/HARDWARE.md。憑證放在程序環境，設定與報告放在包外。
即時模式以唯讀 HTTP 取事件，模擬連線僅使用 127.0.0.1 TCP。回覆只確認模擬批次，physicalDeliveryConfirmed 固定為 false。
閘道等待確認時會繼續檢查管理狀態。已暫停、結束或失效的批次會中止，模擬設備可用 --manual 的 observe-close 觀察該連線關閉。

example.json是隔離API／ArenaSession產生的模擬資料，不含操作憑證。
只接受一場Ended且戰鬥已精確seal的schema6/7事件；會依既有規則重建。
輸入檔不是簽章，工具不能證明任意檔案曾被特定API接受。
Step時間為離線虛擬毫秒，不用原UTC判斷現場新鮮度；不得當成現場設備控制。
最多4096事件、128綁定、4096步、虛擬10分鐘；每設備最多32項含in-flight。
模擬有效期2秒，不更動遊戲0.5／1.5秒政策。只有Receive後匹配連線／delivery的ACK才算SimulatedAcknowledged。
斷線、換綁、停止與最後清理會取消未完成回饋，不能當成實體設備已停止。
離線模式不連設備或網路。所有模式保留原遊戲損傷值，實體輸出映射依廠商協議另設計。
complete表示該輪離線模擬或即時排演完成。請另看每筆模擬確認狀態。
原始任務／場次／API不受模擬改動；廠商協議與真正設備須取得資料後另整合驗收。
manifest只是完整性清單，不是數位簽章。詳細契約見專案docs/HARDWARE_SIMULATOR.md。
'''
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def verify(folder):
    folder=folder.resolve();manifest=read(folder/'hardware-package.json')
    version=(manifest.get('toolVersion'),manifest.get('mode'))
    if manifest.get('schemaVersion')!=1 or version not in {('0.1.0','OfflineSimulationOnly'),('0.2.0','OfflineAndLiveSimulation'),('0.2.1','OfflineAndLiveSimulation'),(VERSION,'OfflineAndLiveSimulation')}:raise ValueError('Unsupported simulator package')
    expected=set(FILES)|{'example.json','README.txt'}
    if version[1]=='OfflineAndLiveSimulation':expected.add('mock-device.py')
    if set(manifest['files'])!=expected:raise ValueError('Unexpected simulator package payload')
    actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    if actual!=set(manifest['files'])|{'hardware-package.json'}:raise ValueError('Missing or additional package file')
    for name,row in manifest['files'].items():
        path=Path(name)
        if '\\' in name or ':' in name or path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe package path')
        file=folder/path
        if file.is_symlink() or file.stat().st_size!=row['bytes'] or sha(file)!=row['sha256']:raise ValueError('Package integrity mismatch')
    return manifest
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path);p.add_argument('--live-evidence',type=Path);p.add_argument('--stage-root',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify',type=Path);args=p.parse_args()
    if args.verify:print(json.dumps({'complete':True,'files':len(verify(args.verify)['files'])}));return
    if not all([args.evidence,args.live_evidence,args.stage_root,args.output]):p.error('Use --evidence, --live-evidence, --stage-root and a new ZIP --output')
    evidence=args.evidence.resolve();checks=read(evidence/'checks.json');cleanup=read(evidence/'cleanup.json')
    if not checks.get('complete') or checks.get('checks',0)<38 or cleanup!={'errors':[],'apiRemaining':False}:raise ValueError('Require completed simulator / API proof and original cleanup')
    if checks['helperSha256']!=sha(ROOT/'scripts/check-hardware-simulator.py'):raise ValueError('Proof helper changed')
    live=args.live_evidence.resolve();witness=read(live/'checks.json');peer=ROOT/'scripts/hardware-mock-peer.py'
    if not witness.get('complete') or witness.get('checks',0)<20 or read(live/'cleanup.json')!={'allStopped':True,'apiExitCode':0}:
        raise ValueError('Require the completed live rehearsal and process cleanup')
    if witness['helperSha256']!=sha(ROOT/'scripts/check-live-hardware-gateway.py') or witness['peerSha256']!=sha(peer):
        raise ValueError('Live proof helper or tested mock changed')
    binary=Path(checks['binaries']['simulator']).parent
    stage=args.stage_root.resolve()/('hardware-simulator-'+uuid.uuid4().hex);stage.mkdir(parents=True,exist_ok=False);folder=stage/'VRCommand-HardwareSimulator';folder.mkdir()
    for name in FILES:
        if sha(binary/name)!=checks['binaryFiles']['simulator'][name] or sha(binary/name)!=witness['binaryFiles'][name]:
            raise ValueError('Offline and live checks must use the same compiled simulator content')
        shutil.copyfile(binary/name,folder/name)
    sample=evidence/'simulation-input.json';expected=read(evidence/'simulation-report.json')
    if not expected['simulatedHardwareOnly'] or expected['physicalDeliveryConfirmed']:raise ValueError('Not an offline simulation report')
    shutil.copyfile(sample,folder/'example.json');shutil.copyfile(peer,folder/'mock-device.py');(folder/'README.txt').write_text(README,encoding='utf-8')
    manifest={'schemaVersion':1,'toolVersion':VERSION,'mode':'OfflineAndLiveSimulation','requires':'.NET 10 runtime; Python 3.12 for the optional mock device',
        'testEvidence':str(evidence),'liveTestEvidence':str(live),'inputSteps':expected['inputSteps'],
        'scope':'No physical device, vendor wire format, authentication attestation, Unity / headset / network capacity acceptance. File hashes are not signatures.',
        'files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(folder.iterdir()) if p.is_file()}}
    (folder/'hardware-package.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');verify(folder)
    output=args.output.resolve()
    if output.suffix.lower()!='.zip':raise ValueError('Use a new ZIP output')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in sorted(folder.iterdir()):z.write(file,'VRCommand-HardwareSimulator/'+file.name)
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None:raise ValueError('ZIP checksum failure')
    receipt={'complete':True,'directory':str(folder),'zip':str(output),'bytes':output.stat().st_size,'sha256':sha(output),'files':len(manifest['files']),'scope':'Tested DLLs, offline fixture and loopback mock peer'}
    with output.with_suffix('.receipt.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
    (ROOT/'artifacts/hardware-simulator-package-path.txt').write_text(str(folder),encoding='utf-8');print(json.dumps(receipt))
if __name__=='__main__':main()
