"""Package the existing Windows Unity build with a standalone Framework server launcher."""
import argparse,importlib.util,json,os,shutil,subprocess,uuid,zipfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('server_player_package',ROOT/'scripts/package-windows-player.py');player=importlib.util.module_from_spec(spec);spec.loader.exec_module(player)
digest=player.digest;plain=player.plain
TOP='VRCommand-GameServer'
README='''VR Command Windows 遊戲伺服器啟動器 1.1／Windows 遊戲程式

完整解壓後開啟Launch-Server.exe。先啟動獨立的管理服務，在網頁控制台建立Preparing VR場次。
按「選擇檔案」選control-instance.json，或在路徑欄直接貼上完整檔案路徑，再按「載入／更新」。只使用既有GameServer角色金鑰。
清單顯示房間、獨立／五房模式及任務名稱；明確選取後可核對完整場次與任務版本ID，再填IPv4與UDP埠、按啟動。預設127.0.0.1只供同機。
更新只保留同一路徑／實例／API／GameServer金鑰中仍可啟動的原選取；消失或載入失敗不改選其他房間。路徑編輯後必須重新載入。
獨立房間各開一個啟動器、各選場次與不同UDP埠；五房Linked場次只開一個。
有新場次時按載入／更新。已綁定來源／Running／MR場次不由此工具接管；啟動前仍重新向原API核對，不拿清單當保留或就緒。
伺服器就緒後，從控制台下載各玩家自己的連線檔，交給玩家包；再由控制台開始任務。
操作員由控制台End後，等戰鬥與世界雙封存，再保留36秒供玩家戰績傳送，啟動器才終止自己的Unity程序。
「中止」會保留本次journal但不算正常完成；不自動End、不重新開舊戰場、不修復或重送舊journal。
此停止方式為封存後的OS程序終止，不宣稱Unity正常退出／本地最後回條落盤或玩家全部收到戰績。
啟動器關閉時，已加入私人Windows Job的子程序會被停止；這不是斷電恢復機制。

管理服務與此啟動器在同機時，可直接選既有實例。遠端管理服務可用CLI七欄JSON：
role="Server",managementApiUrl="http://IPv4:埠",gameServerKey="既有GameServer金鑰",
sessionId="Preparing場次UUID",address="玩家看到的IPv4",listenAddress="本機IPv4或0.0.0.0",port=7777。
不要把此私人JSON、管理實例或日誌資料加回共用ZIP。Unity只收到GameServer金鑰，沒有Master金鑰。
CLI：Launch-Server.exe --run 私人JSON --work 全新資料夾 --seconds 3600 --ready-report 新就緒檔 --report 新結果檔
唯讀列出待開場次：Launch-Server.exe --catalog control-instance.json完整路徑 --report 新結果檔；報告不含金鑰，輸出須在程式包與實例外。
seconds為60..86400，期限結束仍未完成封存與36秒保留則失敗；結果與就緒檔必須在程式包與work外且不能重複。
離線核對：Launch-Server.exe --verify package --report 新結果檔。

本機記錄：%LOCALAPPDATA%/VrCommand/GameServers（含私人金鑰）與GameServerReports。
Windows x64與.NET Framework4.8；操作人員不需Python、Unity Editor或.NET SDK。
使用隨包Unity Windows遊戲程式、原規則與Simulation來源；來源識別見Runtime/build-receipt.json。沒有在本包新增頭盔、MR或廠商硬體整合。
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
    manifest={'schemaVersion':1,'target':'win-x64','launcherVersion':'1.1.0','createdAtUtc':datetime.now(timezone.utc).isoformat(),'build':receipt,'launcherSourceSha256':source_hash,'scope':'Standalone server launcher, unchanged Unity Windows runtime; no keys, tickets or databases; manifest is not a signature.',
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
