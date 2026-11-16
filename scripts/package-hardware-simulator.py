"""Package the tested offline simulator and live loopback mock rehearsal."""
import argparse,hashlib,json,shutil,uuid,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=['VrCommand.HardwareSimulator.dll','VrCommand.HardwareSimulator.deps.json','VrCommand.HardwareSimulator.runtimeconfig.json','VrCommand.Core.dll','VrCommand.Simulation.dll']
VERSION='0.2.22'
MOCK_FIREWALL_FILES=('windows_firewall.py','check-windows-firewall-notifications.ps1')
LIVE_VERSIONS={*(f'0.2.{minor}' for minor in range(15)), '0.2.19', '0.2.20', '0.2.21', VERSION}
README=f'''VR Command 硬體回饋模擬器 {VERSION}

需要 .NET 10 runtime，本機使用10.0.14驗證。這不是Unity玩家程式或廠商SDK。
在解壓目錄執行（請把輸出放在包外的新檔案）：
dotnet VrCommand.HardwareSimulator.dll --input example.json --output <新的包外report.json>

即時模式使用 Windows 管理包 0.31.27 以上與同房房控憑證。Python 3.12 可啟動本機模擬設備：
python mock-device.py --room 1 --port 19101
Windows 預設採用無人值守查核。任一啟用中的防火牆設定檔仍會顯示入站通知時，模擬設備會在終端機記錄原因並略過啟動。
在另一個終端設定 VR_COMMAND_ROOM_KEY，再執行：
dotnet VrCommand.HardwareSimulator.dll --live <包外room-config.json> --output <新的包外report.json>
加上 --status 可在終端查看逐行 JSON 狀態，例如暫停、握手、等待 ACK 及模擬設備失聯。每行只包含房號、狀態和累計數字，stopped 表示報告已寫出並關閉。
同一台電腦的同一帳戶，每個原場次及房間只能有一個即時閘道。GatewayLeaseUnavailable 表示無法取得本機鎖定，請確認原閘道已退出及應用程式資料夾可寫入。
同一帳戶的運作中閘道也須使用不同模擬 TCP 埠及設備 ID。MockPortLeaseUnavailable 與 DeviceLeaseUnavailable 分別表示指定資源無法取得，請核對各房設定。
即時模式可加上 --stop-file <尚不存在的本機標記檔>。每個程序使用獨立路徑。建立空白標記檔後，該程序關閉模擬連線，待確認的批次記為 cancelled，報告終止原因為 operator-stop。
搭配管理包 0.31.61 以上，可從座位／設備清單建立即時設定：
dotnet VrCommand.HardwareSimulator.dll --bind-room <包外seat-map.json> --output <新的包外room-config.json>
此命令使用本房房控金鑰讀取當前名冊。版本 2 即時設定在握手前及排演中核對原入場。名冊不符時以 binding-mismatch 結束，請核對座位後重新產生設定。
HTTPS 排演可在單房或五房清單指定原管理憑證的 managementCertificateSha256。輸出的房間設定會保留此指紋。
搭配管理包 0.31.94，可用 VR_COMMAND_MASTER_KEY 一次核對五房並輸出各房設定：
dotnet VrCommand.HardwareSimulator.dll --bind-venue <包外venue-map.json> --output <新的包外資料夾>
整批核對五房原場次、現行名冊與互不重複的模擬埠及設備 ID。正式排演仍各用房控金鑰。
各房 --live 加上 --status-directory <同一個已建立的本機狀態目錄> 後，主控可讀取五房狀態：
dotnet VrCommand.HardwareSimulator.dll --venue-status <包外venue-bindings.json> --status-directory <本機狀態目錄>
此查詢不需金鑰。未啟動顯示 waiting，超過三秒未更新的執行中房間顯示 stale。重啟使用新的 runId 與計數。
設定 VR_COMMAND_ROOM_1_KEY 至 VR_COMMAND_ROOM_5_KEY 後，可用同一份五房綁定啟動五個模擬閘道：
dotnet VrCommand.HardwareSimulator.dll --live-venue <包外venue-bindings.json> --output <新的包外資料夾> --stop-file <尚不存在的本機標記檔>
先核對五房憑證、入場與本機互斥資源。建立標記檔會停止本次所有仍運作的閘道，已取消的批次不計入模擬確認。
在本次輸出資料夾建立 room-01.stop 到 room-05.stop，可單獨停止指定房間。該房報告終止原因為 operator-room-stop，其他房繼續排演。
五房結果見輸出目錄的 venue-report.json 與各房報告。某房入場失效時，其他房可繼續排演，總結果會列出各房退出碼。
原綁定清單與整個輸出目錄可搬到另一台電腦後離線核對：
dotnet VrCommand.HardwareSimulator.dll --verify-venue-report <原venue-bindings.json> --report-directory <原五房輸出目錄>
版本 3 另需原綁定清單旁的 room-01.json 至 room-05.json。核對原設定及每筆設備與入場對應，列出逐席模擬確認、取消與失敗數。版本 2 報告仍可讀取各房總數。
verified 代表檔案一致性，排演結果見 rehearsalComplete。
可將通過核對的原檔打包成一份交接 ZIP，再直接核對：
dotnet VrCommand.HardwareSimulator.dll --pack-venue-report <原venue-bindings.json> --report-directory <原五房輸出目錄> --output <新ZIP>
dotnet VrCommand.HardwareSimulator.dll --verify-venue-zip <交接ZIP>
排演中若管理服務拒絕本房讀取或回覆無效，本房關閉模擬連線並寫出終止報告。原因分別為 management-refused 及 management-invalid-response。待確認批次取消，先前已確認的模擬回饋保留。
每次附掛都核對戰鬥串流與來源。已附掛的串流若回報不同來源，該房以 management-invalid-response 結束。短暫的管理連線故障則關閉原連線，恢復後用新連線及當前游標。
同一輪房間排演會保留最近已核對的管理序號與檢查時間。任一值倒退時取消待確認批次，以 management-invalid-response 結束該房。
同一管理回覆中的重複 eventId 或 reportId，以及新批次沿用本輪已嘗試送出的識別，均會在送出前以 management-invalid-response 結束該房。
management-unavailable 可從 fault 區分 management-service-unavailable、management-timeout 與 management-transport。恢復正常時會清除故障碼。
配置範例、模擬協議和操作方式見專案 docs/HARDWARE.md。操作金鑰放在程序環境，設定與報告放在包外。
即時模式以唯讀 HTTP 或 HTTPS 取事件，模擬連線僅使用 127.0.0.1 TCP。回覆只確認模擬批次，physicalDeliveryConfirmed 固定為 false。
閘道等待確認時會繼續檢查管理狀態。已暫停、結束或失效的批次會中止，模擬設備可用 --manual 的 observe-close 觀察該連線關閉。
閘道只在場次執行且有戰鬥來源時握手。暫停也會關閉閒置連線，繼續後使用新連線和目前游標。

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
    version, mode=manifest.get('toolVersion'),manifest.get('mode')
    valid_version=(version=='0.1.0' and mode=='OfflineSimulationOnly') or (
        isinstance(version,str) and version in LIVE_VERSIONS and mode=='OfflineAndLiveSimulation')
    if manifest.get('schemaVersion')!=1 or not valid_version:raise ValueError('Unsupported simulator package')
    expected=set(FILES)|{'example.json','README.txt'}
    if mode=='OfflineAndLiveSimulation':expected.add('mock-device.py')
    if version in {'0.2.20', '0.2.21', VERSION}:expected.update(MOCK_FIREWALL_FILES)
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
    if not witness.get('complete') or witness.get('checks',0)<35 or read(live/'cleanup.json')!={'allStopped':True,'apiExitCode':0}:
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
    for name in MOCK_FIREWALL_FILES:
        shutil.copyfile(ROOT/'scripts'/name,folder/name)
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
