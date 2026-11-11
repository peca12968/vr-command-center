"""Package the self-contained management API and a Windows Framework launcher. No live data or credentials."""
import argparse,hashlib,importlib.util,json,os,re,shutil,subprocess,uuid,zipfile
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1];TOP='VRCommand-ControlServer'
SECRET_KEYS={'operatorkeys','operatorkeyfile','gameserverkey','jointicket','playerticketsigningkey','controlpipetoken','vr_command_control_pfx_password'}
FORBIDDEN_PARTS={'data','missions','sessions','telemetry','journals'}
README='''VR Command Windows 管理服務包 API 0.31.0／控制台 0.31.130

完整解壓後開啟 Start-Control.exe。
1. 首次選擇監聽IPv4與埠號（預設127.0.0.1:5081），按「新增資料實例」。
2. 按「啟動管理服務」，等候「服務已就緒」，再按「開啟控制台」。
3. 選擇Master或對應Room1–Room5角色，按「複製登入金鑰」，貼到控制台登入。
4. 需要重開時，用「選取資料實例」選回原資料夾的control-instance.json，再啟動；請保留整個資料夾。
5. 結束時按「停止管理服務」，等待正常停止後才關閉視窗。

新實例資料預設在使用者的LocalAppData/VrCommand/ControlServers下，與本包分開。
每實例有自己的七角色金鑰、玩家票券簽章金鑰及SQLite資料；不要交付或公開這些資料。
本包本身沒有登入金鑰、票券、任務資料庫、遊戲伺服器設定或Unity遊戲。
GameServer角色供遊戲伺服器使用，不能拿到玩家端；玩家使用控制台下載的短票券。
主控與各房可在「Quest 3 MR 席位部署核對」選擇同一席的連線檔與房間原始校正檔。
五房房卡可核對各場公布的 UDP 端點，並標示同機位址與合併場的共用端點。
若全館啟動結果未確認，主控可選擇原結果 JSON，唯讀核對管理端的原場次、來源與端點。
五房獨立場若同時有 VR 與 MR，可用混合五房配票下載同一份 ZIP。只有 MR 房需要原始校正檔。
主控也可用專案的 deploy-quest.ps1 五房線上預檢核對全部 25 席的部署檔與現行名冊。
建立場次前，可展開保存版本的場地平面圖核對掩體、出生位和通路。
戰鬥及世界雙封存後，可從任務統計選擇玩家並開啟個人事件回放。
回放暫停後，可依房間及戰鬥事件種類搜尋已保存快照，並直接停在結果所在格。
房控可讀取本房的即時戰鬥回饋介面，作為廠商轉接器的遊戲事件來源。
五房空閒時，主控可用同一版本或逐房指定保存版本，一次建立五個獨立準備場次。
五房備妥 Quest 3 名冊、校正檔與伺服器端點後，可下載完整 MR 部署包供預檢。
房間總覽以最近接受的有效快照顯示活動時間或自動結束倒數。
場次面板以同一序號顯示場次狀態、玩家戰績和最近事件。
主控可一次暫停執行中場次，再繼續仍停在全館暫停階段的場次。
房卡顯示全館命令是否已由遊戲端套用，批次繼續須等所有目標確認暫停。
全館開始可選擇要求五房各有五席有效追蹤，管理服務會在受理前再核對原遊戲快照。
停止管理API不會假造任務End、世界seal或玩家結果；遊戲伺服器與任務收尾分開處理。

執行環境：Windows x64及.NET Framework 4.8。API已自含.NET/ASP.NET Core，不需安裝Python或.NET SDK。
場館可在127.0.0.1管理實例加入control-https.json與control-https.pfx，另開指定IPv4的HTTPS房控入口。
PFX密碼由啟動程序的VR_COMMAND_CONTROL_PFX_PASSWORD提供，詳細操作見專案docs/WINDOWS_CONTROL_PACKAGE.md。
正式開場前可在 HTTPS 控制台的「主控與五房控連線核對」收集回條，再由主控核對六台的來源位址。需要逐次核對葉憑證指紋時使用 check-venue-operator.py。
啟動器不修改防火牆、DNS或NAT；實際跨機與頭盔仍待驗證。
控制台可管理任務、五房名冊與觀戰資料；Unity GameServer與玩家包仍須另外啟動。
主控可在已完成雙封存的場次「任務收尾」下載場館驗收資料ZIP。ZIP含名冊、統計與公告端點，請與原始遊戲日誌私下保管。
主控可在「全館收尾」一次下載選定批次的驗收 ZIP，含原批次明細與每場的驗收資料。
主控可在「VR 五房配票」核對原名冊及公告端點後，一次下載 25 份短效連線檔。
VR 五房連線 ZIP 可供 Quest 部署工具直接預檢及線上核對原票券、席位裝置與公告端點。
單席、整房及五房配票在存檔前重新核對原場次與入場名冊。
VR 場次的「VR 席位連線檔核對」可核對原票券、現行入場、公告端點及近期原遊戲畫格。
合併場的已封存回放可依指定房間匯出玩家檔，保留原畫格與時間。
場地通路預覽可在原格點找不到路徑時，使用較細格點核對偏移缺口。

control-package.json是檔案SHA256與建置紀錄，不是數位簽章或可信發行者證明。
Notices/保留實際執行環境與NuGet metadata、授權及上游參考NOTICE；參考NOTICE可能提及未隨包附帶的元件。
只在全體writer停止後備份完整資料實例（含WAL），不要用舊版本開啟新資料或替換部分資料檔。
'''
def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def plain(path):
    path=Path(os.path.abspath(path))
    for p in (path,*path.parents):
        if p.is_symlink() or hasattr(p,'is_junction') and p.is_junction():raise ValueError('Package paths must not use links / junctions')
    return path
def relative(name):
    if not isinstance(name,str) or not name or '\\' in name or ':' in name or name.startswith('/') or any(v in ('','.','..') for v in name.split('/')):raise ValueError('Unsafe package path')
    return PurePosixPath(name)
def payload(name,content=None):
    path=relative(name);parts={part.lower() for part in path.parts}
    if parts&FORBIDDEN_PARTS or path.suffix.lower() in {'.db','.sqlite','.sqlite3','.journal','.worldlog','.combat','.key','.pfx','.p12'} or path.name.lower() in {'operator-keys.json','control-instance.json','control-https.json','keys.json'} or path.name.lower().endswith(('-wal','-shm')):raise ValueError('Live data / credentials cannot be packaged: '+name)
    if path.suffix.lower()=='.json' and content is not None:
        def visit(value):
            if isinstance(value,dict):
                for key,item in value.items():
                    if key.lower() in SECRET_KEYS:raise ValueError('Credential configuration cannot be packaged')
                    visit(item)
            elif isinstance(value,list):
                for item in value:visit(item)
        visit(json.loads(content))
def publication(build):
    build=plain(build);receipt=read(build/'publish-receipt.json');folder=plain(build/'publication')
    if receipt.get('schemaVersion')!=1 or receipt.get('target')!='win-x64' or receipt.get('apiVersion')!='0.31.0':raise ValueError('Use an actual supported Windows publication')
    if receipt.get('consoleVersion')!='0.31.130':raise ValueError('Publish the current console 0.31.130 before packaging')
    expected=receipt['files'];actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    if actual!=set(expected):raise ValueError('Publication contains missing or additional files')
    for name,value in expected.items():
        file=plain(folder/relative(name));payload(name,file.read_bytes() if file.suffix.lower()=='.json' else None)
        if digest(file)!=value:raise ValueError('Publication file changed: '+name)
    spec=importlib.util.spec_from_file_location('control_publish',ROOT/'scripts/publish-control-server.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    if module.runtime_config(folder)!=receipt['runtimeFrameworks']:raise ValueError('Runtime framework mismatch')
    for name,value in receipt['sourceFiles'].items():
        if digest(ROOT/name)!=value:raise ValueError('Current API sources differ from publication: '+name)
    return folder,receipt
def notices(build,output):
    assets=read(build/'work/obj/VrCommand.Api/project.assets.json');cache=[Path(v) for v in assets['packageFolders']]
    receipt=read(build/'publish-receipt.json');packages=[name.lower() for name,value in assets['libraries'].items() if value['type']=='package']
    packages += [name.lower()+'.runtime.win-x64/'+version for name,version in receipt['runtimeFrameworks'].items()]
    sources=[]
    for index,name in enumerate(sorted(set(packages)),1):
        folder=next((p/name for p in cache if (p/name).is_dir()),None)
        if folder is None:raise FileNotFoundError('Restore the actual NuGet / runtime package first: '+name)
        selected=[p for p in folder.iterdir() if p.is_file() and (p.suffix=='.nuspec' or re.match(r'^(license|notice|third.party.notices|copying)',p.name,re.I))]
        if not any(p.suffix=='.nuspec' for p in selected):raise ValueError('Package provenance missing')
        for file in selected:
            plain(file);target=output/'NuGet'/('p'+str(index))/('metadata.nuspec' if file.suffix=='.nuspec' else file.name);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target);sources.append({'package':name,'originalFileName':file.name,'path':target.relative_to(output).as_posix(),'sha256':digest(target)})
    for file in sorted((ROOT/'tools/WindowsControlLauncher/Notices').iterdir()):
        plain(file);shutil.copyfile(file,output/file.name)
    (output/'bundled-packages.json').write_text(json.dumps({'packages':sources,'scope':'Original restored package licenses / metadata plus separately attributed upstream references'},indent=2)+'\n',encoding='utf-8')
    return sources
def verify(folder):
    folder=plain(folder);manifest=read(folder/'control-package.json')
    if manifest.get('schemaVersion')!=1 or manifest.get('target')!='win-x64' or manifest.get('apiVersion')!='0.31.0':raise ValueError('Unsupported control package')
    seen=set()
    for row in manifest['files']:
        name=row['path'];key=name.lower()
        if key in seen:raise ValueError('Case-aliased duplicate package path')
        seen.add(key);file=plain(folder/relative(name));payload(name,file.read_bytes() if file.suffix.lower()=='.json' else None)
        if file.stat().st_size!=row['bytes'] or digest(file)!=row['sha256']:raise ValueError('Package integrity check failed: '+name)
    actual={p.relative_to(folder).as_posix().lower() for p in folder.rglob('*') if p.is_file()}
    if actual!=seen|{'control-package.json'}:raise ValueError('Additional or missing package files')
    return manifest
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--publication',type=Path);parser.add_argument('--stage-root',type=Path);parser.add_argument('--output',type=Path);parser.add_argument('--verify',type=Path);args=parser.parse_args()
    if args.verify:print(json.dumps({'complete':True,'files':len(verify(args.verify)['files'])}));return
    if os.name!='nt' or not all([args.publication,args.stage_root,args.output]):parser.error('Use Windows with --publication, --stage-root and a new --output ZIP')
    api,receipt=publication(args.publication);stage=plain(args.stage_root)/('control-server-'+uuid.uuid4().hex);stage.mkdir(parents=True,exist_ok=False);folder=stage/TOP;folder.mkdir();shutil.copytree(api,folder/'Runtime')
    license_folder=folder/'Notices';license_folder.mkdir();notice_sources=notices(args.publication,license_folder)
    source=ROOT/'tools/WindowsControlLauncher/ControlLauncher.cs';compiler=Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    with (stage/'compile.log').open('xb') as log:subprocess.run([str(compiler),'/nologo','/warnaserror','/codepage:65001','/target:winexe','/platform:x64','/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Web.Extensions.dll','/out:'+str(folder/'Start-Control.exe'),str(source)],stdout=log,stderr=subprocess.STDOUT,check=True)
    (folder/'README.txt').write_text(README,encoding='utf-8');(folder/'publish-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    manifest={'schemaVersion':1,'target':'win-x64','apiVersion':'0.31.0','consoleVersion':receipt['consoleVersion'],'createdAtUtc':datetime.now(timezone.utc).isoformat(),'launcherSourceSha256':digest(source),'runtimeFrameworks':receipt['runtimeFrameworks'],
        'scope':'Portable management API / private instance launcher; no Unity server, keys, tickets or databases. SHA manifest is not a signature.',
        'files':[{'path':p.relative_to(folder).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(folder.rglob('*')) if p.is_file()]}
    (folder/'control-package.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');verify(folder)
    output=plain(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
        for file in sorted(folder.rglob('*')):
            if file.is_file():bundle.write(file,TOP+'/'+file.relative_to(folder).as_posix())
    with zipfile.ZipFile(output) as bundle:
        if bundle.testzip() is not None:raise ValueError('ZIP checksum failed')
    result={'complete':True,'zip':str(output),'bytes':output.stat().st_size,'sha256':digest(output),'directory':str(folder),'files':len(manifest['files']),'launcherSourceSha256':digest(source),'notices':len(notice_sources)}
    with output.with_suffix('.receipt.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    (ROOT/'artifacts/control-server-package-path.txt').write_text(str(folder),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
