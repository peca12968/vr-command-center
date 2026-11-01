"""Package the exact tested offline simulator DLL graph; no runtime, vendor SDK, devices or credentials."""
import argparse,hashlib,json,shutil,uuid,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=['VrCommand.HardwareSimulator.dll','VrCommand.HardwareSimulator.deps.json','VrCommand.HardwareSimulator.runtimeconfig.json','VrCommand.Core.dll','VrCommand.Simulation.dll']
README='''VR Command 硬體回饋離線模擬器 0.1.0

需要 .NET 10 runtime，本機使用10.0.14驗證。這不是Unity玩家程式或廠商SDK。
在解壓目錄執行（請把輸出放在包外的新檔案）：
dotnet VrCommand.HardwareSimulator.dll --input example.json --output <新的包外report.json>

example.json是隔離API／ArenaSession產生的模擬資料，不含操作憑證。
只接受一場Ended且戰鬥已精確seal的schema6/7事件；會依既有規則重建。
輸入檔不是簽章，工具不能證明任意檔案曾被特定API接受。
Step時間為離線虛擬毫秒，不用原UTC判斷現場新鮮度；不得當成現場設備控制。
最多4096事件、128綁定、4096步、虛擬10分鐘；每設備最多32項含in-flight。
模擬有效期2秒，不更動遊戲0.5／1.5秒政策。只有Receive後匹配連線／delivery的ACK才算SimulatedAcknowledged。
斷線、換綁、停止與最後清理會取消未完成回饋，不能當成實體設備已停止。
不連USB／Serial／TCP／BLE，不發任何實體命令；不把damage映射成震動／力道。
complete只表示離線腳本處理完畢，physicalDeliveryConfirmed永遠false。
原始任務／場次／API不受模擬改動；廠商協議與真正設備須取得資料後另整合驗收。
manifest只是完整性清單，不是數位簽章。詳細契約見專案docs/HARDWARE_SIMULATOR.md。
'''
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def verify(folder):
    folder=folder.resolve();manifest=read(folder/'hardware-package.json')
    if manifest.get('schemaVersion')!=1 or manifest.get('toolVersion')!='0.1.0' or manifest.get('mode')!='OfflineSimulationOnly':raise ValueError('Unsupported simulator package')
    if set(manifest['files'])!=set(FILES)|{'example.json','README.txt'}:raise ValueError('Unexpected simulator package payload')
    actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    if actual!=set(manifest['files'])|{'hardware-package.json'}:raise ValueError('Missing or additional package file')
    for name,row in manifest['files'].items():
        path=Path(name)
        if '\\' in name or ':' in name or path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe package path')
        file=folder/path
        if file.is_symlink() or file.stat().st_size!=row['bytes'] or sha(file)!=row['sha256']:raise ValueError('Package integrity mismatch')
    return manifest
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path);p.add_argument('--stage-root',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify',type=Path);args=p.parse_args()
    if args.verify:print(json.dumps({'complete':True,'files':len(verify(args.verify)['files'])}));return
    if not all([args.evidence,args.stage_root,args.output]):p.error('Use --evidence, --stage-root and a new ZIP --output')
    evidence=args.evidence.resolve();checks=read(evidence/'checks.json');cleanup=read(evidence/'cleanup.json')
    if not checks.get('complete') or checks.get('checks',0)<38 or cleanup!={'errors':[],'apiRemaining':False}:raise ValueError('Require completed simulator / API proof and original cleanup')
    if checks['helperSha256']!=sha(ROOT/'scripts/check-hardware-simulator.py'):raise ValueError('Proof helper changed')
    binary=Path(checks['binaries']['simulator']).parent
    stage=args.stage_root.resolve()/('hardware-simulator-'+uuid.uuid4().hex);stage.mkdir(parents=True,exist_ok=False);folder=stage/'VRCommand-HardwareSimulator';folder.mkdir()
    for name in FILES:
        if sha(binary/name)!=checks['binaryFiles']['simulator'][name]:raise ValueError('Tested simulator output changed')
        shutil.copyfile(binary/name,folder/name)
    sample=evidence/'simulation-input.json';expected=read(evidence/'simulation-report.json')
    if not expected['simulatedHardwareOnly'] or expected['physicalDeliveryConfirmed']:raise ValueError('Not an offline simulation report')
    shutil.copyfile(sample,folder/'example.json');(folder/'README.txt').write_text(README,encoding='utf-8')
    manifest={'schemaVersion':1,'toolVersion':'0.1.0','mode':'OfflineSimulationOnly','requires':'.NET 10 runtime','testEvidence':str(evidence),'inputSteps':expected['inputSteps'],
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
    receipt={'complete':True,'directory':str(folder),'zip':str(output),'bytes':output.stat().st_size,'sha256':sha(output),'files':len(manifest['files']),'scope':'Tested DLLs plus synthetic fixture; framework-dependent offline simulator only'}
    with output.with_suffix('.receipt.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
    (ROOT/'artifacts/hardware-simulator-package-path.txt').write_text(str(folder),encoding='utf-8');print(json.dumps(receipt))
if __name__=='__main__':main()
