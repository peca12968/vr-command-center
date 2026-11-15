"""Package the existing Windows Unity build with a standalone Framework server launcher."""
import argparse,importlib.util,json,os,shutil,subprocess,uuid,zipfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('server_player_package',ROOT/'scripts/package-windows-player.py');player=importlib.util.module_from_spec(spec);spec.loader.exec_module(player)
digest=player.digest;plain=player.plain
TOP='VRCommand-GameServer'
README='''VR Command Windows 遊戲伺服器啟動器 1.24／Windows 遊戲程式

完整解壓後開啟 Launch-Server.exe。先啟動配套的管理服務，在網頁控制台建立 Preparing VR 或 MR 場次。
按「選擇檔案」選control-instance.json，或在路徑欄直接貼上完整檔案路徑，按 Enter 或「載入／更新」。只使用既有GameServer角色金鑰。
清單載入後，按 Alt+R 到場次清單，用方向鍵選房。Alt+P 到 UDP 埠，Alt+S 啟動已選場次。
清單顯示房間、獨立／五房模式及任務名稱；明確選取後可核對完整場次與任務版本ID，再填IPv4與UDP埠、按啟動。預設127.0.0.1只供同機。
更新只保留同一路徑、實例、API、GameServer 金鑰與 HTTPS 指紋中仍在清單內的原選取。場次或設定改變時須重新載入及選擇。
讀取場次期間仍可移動或關閉視窗。等讀取完成後再選房及啟動。若讀取失敗，重新載入前舊場次不能用於啟動。
獨立房間各開一個啟動器、各選場次與不同UDP埠；五房Linked場次只開一個。
使用控制台下載的五房計畫時，按 Alt+V 開啟「五房批次啟動」，貼上 JSON 完整路徑後按 Enter 核對。確認清單後按 Alt+S 啟動全館。
確認各房已登記席號、任務、場次與 UDP 埠後按「啟動全館」。合併模式五房共用同一場次和埠。第一版計畫的席位會顯示「計畫未提供」。所有遊戲程序準備好後，第四版計畫會一次核對並登記全部來源。若設定已變更，請回主控台重新下載。
全館批次請使用控制台 0.31.100 或以上的管理包。所有原遊戲程序與 UDP 綁定均確認後，管理服務一次公告整批端點。
來源登記或整批端點公告遇到暫時性連線故障時，最多重送一次原請求。仍需核對原回條和 Windows UDP 綁定後才會產生就緒檔。
有新場次時按載入／更新。清單只列尚未綁定來源的 Preparing 場次。啟動前會向原管理服務重新核對場次與來源。
MR 場次如缺少校正鎖定，清單會標示待鎖定，選取後顯示房號並停用啟動。由主控鎖定後按載入／更新。
CLI 啟動同樣在建立遊戲程序前檢查鎖定。唯讀清單報告含 canStart 及 missingAlignmentRoomIds，供操作員辨識缺少鎖定的房間。
啟動器在公告前會核對 Windows 的 UDP 綁定，確認本次遊戲程序已綁定所設定的本機位址與埠。就緒檔的 udpBinding 是啟動時的觀察，遠端能否加入仍需實測。
伺服器就緒後，從控制台下載各玩家自己的連線檔。VR 使用玩家包或頭盔部署流程。MR 使用 Quest 3 校正及 MR 部署流程，等全名冊追蹤就緒再從控制台開始。
操作員由控制台End後，等戰鬥與世界雙封存，再保留36秒供玩家戰績傳送，啟動器才終止自己的Unity程序。
就緒後遇到暫時性管理讀取失敗時，啟動器保留原遊戲程序並等待最多15秒，再核對同一場次與來源。請恢復原管理實例。結果檔會記錄中斷及恢復次數。
「中止」會保留本次journal但不算正常完成；不自動End、不重新開舊戰場、不修復或重送舊journal。
此停止方式為封存後的OS程序終止，不宣稱Unity正常退出／本地最後回條落盤或玩家全部收到戰績。
啟動器關閉時，已加入私人Windows Job的子程序會被停止；這不是斷電恢復機制。

管理服務與此啟動器在同機時，可直接選既有實例。CLI七欄JSON：
role="Server",managementApiUrl="http://IPv4:埠",gameServerKey="既有GameServer金鑰",
sessionId="Preparing場次UUID",address="玩家看到的IPv4",listenAddress="本機IPv4或0.0.0.0",port=7777。
分機部署請將 managementApiUrl 設為管理站台 HTTPS 原點，並加上第八欄 managementCertificateSha256（管理員提供的葉憑證 SHA-256，小寫）。
遠端 HTTPS 亦可用私人 control-instance.json 連線設定，供待開清單、圖形介面與五房批次啟動。設定見專案 docs/WINDOWS_SERVER_PACKAGE.md。
不要把此私人JSON、管理實例或日誌資料加回共用ZIP。Unity只收到GameServer金鑰，沒有Master金鑰。
CLI：Launch-Server.exe --run 私人JSON --work 全新資料夾 --seconds 3600 --ready-report 新就緒檔 --report 新結果檔
五房批次：Launch-Server.exe --venue-run 私人計畫JSON --work 全新資料夾 --seconds 3600 --ready-report 新就緒檔 --report 新結果檔
唯讀核對五房計畫：Launch-Server.exe --venue-check 計畫JSON完整路徑 --report 新結果檔
直接開啟五房視窗並填入路徑：Launch-Server.exe --venue-window 計畫JSON完整路徑
計畫欄位：version=4、controlInstance（管理實例完整路徑）、topology（Independent 或 Linked）、address、listenAddress、servers。
每個 servers 項目含 sessionId、sessionSequence、missionId、roomIds 及 port。獨立列五筆及不同 UDP 埠，合併列一筆且 roomIds 含五房。原場次須為未綁來源的 Preparing。
版本 4 需搭配管理包 0.31.114 及遊戲伺服器 0.50.4 以上。既有版本 2、3 沿用逐場登記核對，版本 1 沿用原房間及 UDP 核對。
從啟動器 1.21 起，版本 2 至 4 的唯讀預覽附上原場次已登記的房號及席號。UDP 預檢可核對席位清單是否完整相符。
等全館就緒檔出現，再由原控制台操作配票與場次。個別原子程序、UDP 綁定、雙封存與終止結果會逐場記錄。設定及結果須留在包外。
就緒或結果報告已寫出後，可在批次視窗複製原報告路徑，回主控台選取報告核對。修改計畫路徑或重新核對計畫會清除按鈕上的本輪報告。
場館驗收可在圖形介面勾選「記錄本次玩家連線來源（場館驗收）」，或在上述CLI另加 --peer-diagnostics on。
每場須明確開啟。結果的 peerDiagnosticsEnabled 記錄啟動時是否開啟，原連線編號與來源位址及埠可在 workDirectory 下的 server.log 核對。
請將server.log留在私人資料夾，勿放入公開結果。
唯讀列出待開場次：Launch-Server.exe --catalog control-instance.json完整路徑 --report 新結果檔；報告不含金鑰，輸出須在程式包與實例外。
seconds為60..86400，期限結束仍未完成封存與36秒保留則失敗；結果與就緒檔必須在程式包與work外且不能重複。
離線核對：Launch-Server.exe --verify package --report 新結果檔。

本機記錄：%LOCALAPPDATA%/VrCommand/GameServers（含私人金鑰）與GameServerReports。
Windows x64與.NET Framework4.8；操作人員不需Python、Unity Editor或.NET SDK。
VR 預設使用 Simulation 來源。頭盔測試請勾選「VR 房間只接受追蹤姿態」，或在單場／五房 CLI 啟動加 --tracked-vr on。遊戲伺服器 0.50.8 起使用 GameServer 來源並只接受追蹤姿態。MR 使用 GameServer 來源。遊戲建置來源見 Runtime/build-receipt.json。
Windows 玩家包與 Quest APK 須使用與伺服器相同的遊戲版本。升級時先結束既有場次，再一併更新伺服器及玩家端。
未修改防火牆、未提供NAT/中繼；跨機網路與25位同時操作須另外驗收。
server-package.json是SHA256完整性清單，不是數位簽章。Runtime/build-receipt.json保留原實際Unity建置紀錄。
Notices保留玩家包相同的素材／Transport授權。Microsoft Job文件：https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
'''

def verify(folder):
    folder=plain(folder);manifest=json.loads((folder/'server-package.json').read_text(encoding='utf-8'))
    if manifest.get('schemaVersion')!=1 or manifest.get('target')!='win-x64':raise ValueError('Unsupported server package')
    seen=set()
    for row in manifest['files']:
        name=row['path'];key=name.lower();file=player.relative_file(folder,name)
        if key in seen:raise ValueError('Case-aliased package path')
        seen.add(key)
        if file.stat().st_size!=row['bytes'] or digest(file)!=row['sha256']:raise ValueError('Changed package content: '+name)
    actual={p.relative_to(folder).as_posix().lower() for p in folder.rglob('*') if p.is_file()}
    if actual!=seen|{'server-package.json'}:raise ValueError('Additional or missing package files')
    if not {'launch-server.exe','runtime/vrcommand.exe','runtime/unityplayer.dll','runtime/build-receipt.json'}<=seen:raise ValueError('Required server files missing')
    return manifest

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--player-directory',type=Path,default=ROOT/'artifacts/desktop');p.add_argument('--stage-root',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify',type=Path);args=p.parse_args()
    if args.verify:print(json.dumps({'complete':True,'files':len(verify(args.verify)['files'])}));return
    if os.name!='nt' or not args.stage_root or not args.output:p.error('Use Windows with new --stage-root and --output')
    receipt,files=player.collect(args.player_directory);stage=plain(args.stage_root)/('server-'+uuid.uuid4().hex);stage.mkdir(parents=True,exist_ok=False);folder=stage/TOP;folder.mkdir()
    for source,name in files:
        target=folder/'Runtime'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        if digest(source)!=digest(target):raise ValueError('Unity changed during copy')
    for source,name in player.NOTICES.items():
        target=folder/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/source,target)
    source=ROOT/'tools/WindowsServerLauncher/ServerLauncher.cs';compiler=Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    frozen=stage/'ServerLauncher.input.cs';shutil.copyfile(source,frozen);source_hash=digest(frozen)
    with (stage/'compile.log').open('xb') as log:subprocess.run([str(compiler),'/nologo','/warnaserror','/codepage:65001','/target:winexe','/platform:x64','/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Web.Extensions.dll','/out:'+str(folder/'Launch-Server.exe'),str(frozen)],stdout=log,stderr=subprocess.STDOUT,check=True)
    if digest(source)!=source_hash:raise ValueError('Launcher source changed during compilation')
    (folder/'README.txt').write_text(README,encoding='utf-8')
    manifest={'schemaVersion':1,'target':'win-x64','launcherVersion':'1.24.0','createdAtUtc':datetime.now(timezone.utc).isoformat(),'build':receipt,'launcherSourceSha256':source_hash,'scope':'Standalone server launcher; no keys, tickets or databases; manifest is not a signature.',
        'files':[{'path':p.relative_to(folder).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(folder.rglob('*')) if p.is_file()]}
    (folder/'server-package.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');verify(folder)
    output=plain(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in sorted(folder.rglob('*')):
            if file.is_file():z.write(file,TOP+'/'+file.relative_to(folder).as_posix())
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None:raise ValueError('ZIP CRC failed')
    result={'complete':True,'directory':str(folder),'zip':str(output),'bytes':output.stat().st_size,'sha256':digest(output),'sourceFingerprint':receipt['sourceFingerprint'],'launcherSourceSha256':digest(source),'files':len(manifest['files'])}
    with output.with_suffix('.receipt.json').open('x',encoding='utf-8') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
