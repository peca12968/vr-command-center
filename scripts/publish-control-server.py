"""Publish the Windows management API in a fresh source snapshot, without changing repository locks."""
import argparse,hashlib,json,os,shutil,subprocess,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INPUTS=['global.json','Directory.Build.props','src/VrCommand.Api','src/VrCommand.Core','src/VrCommand.Persistence','src/VrCommand.Simulation',
        'clients/unity/Packages/com.vrcommand.simulation/Runtime','clients/unity/Assets/VrCommand/Audio',
        'scripts/package-player-replay.mjs','tests/browser/package.json','tests/browser/pnpm-lock.yaml','tests/browser/pnpm-workspace.yaml']
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def runtime_config(folder):
    options=read(folder/'VrCommand.Api.runtimeconfig.json')['runtimeOptions']
    if 'framework' in options or 'frameworks' in options or options.get('tfm')!='net10.0':raise ValueError('Expected a self-contained .NET 10 publication')
    frameworks={v['name']:v['version'] for v in options.get('includedFrameworks',[])}
    if set(frameworks)!={'Microsoft.NETCore.App','Microsoft.AspNetCore.App'}:raise ValueError('Missing bundled management runtime')
    for name in ['VrCommand.Api.exe','VrCommand.Api.dll','coreclr.dll','hostfxr.dll','hostpolicy.dll','e_sqlite3.dll',
                 'wwwroot/console/index.html','wwwroot/console/player-replay-offline.html']:
        if not (folder/name).is_file():raise ValueError('Missing publication file: '+name)
    return frameworks
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build-root',type=Path,required=True);p.add_argument('--runtime-version',default='10.0.14');args=p.parse_args()
    if os.name!='nt':p.error('Publish and verify the actual Windows runtime on Windows')
    if not args.runtime_version.startswith('10.0.') or not args.runtime_version.removeprefix('10.0.').isdigit():p.error('Use an explicit .NET 10 patch version')
    root=args.build_root.resolve()/('control-server-'+uuid.uuid4().hex);root.mkdir(parents=True,exist_ok=False);source=root/'source';source.mkdir()
    names=sorted(set(subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','--',*INPUTS],cwd=ROOT,text=True,encoding='utf-8').splitlines()))
    hashes={}
    for name in names:
        file=ROOT/name
        if file.is_symlink() or any(part in ('bin','obj','data') for part in Path(name).parts):raise ValueError('Unexpected build input: '+name)
        out=source/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,out);hashes[name]=digest(file)
    locks={name:read(source/name) for name in names if name.endswith('packages.lock.json')}
    project=source/'src/VrCommand.Api/VrCommand.Api.csproj';work=root/'work';publication=root/'publication'
    common=['--artifacts-path',str(work),'-r','win-x64','-p:SelfContained=true','-p:RuntimeFrameworkVersion='+args.runtime_version]
    with (root/'restore.log').open('xb') as log:subprocess.run(['dotnet','restore',str(project),'--force-evaluate',*common],cwd=source,stdout=log,stderr=subprocess.STDOUT,check=True)
    # RID-specific lock groups are isolated here. Original dependency groups and
    # all their package pins must remain byte-equivalent as parsed JSON.
    for name,before in locks.items():
        after=read(source/name)
        for group,entries in before['dependencies'].items():
            if after['dependencies'].get(group)!=entries:raise ValueError('Original dependency pins changed: '+name+' '+group)
    with (root/'publish.log').open('xb') as log:subprocess.run(['dotnet','publish',str(project),'--configuration','Release','--no-restore','--self-contained','true','-o',str(publication),*common],cwd=source,stdout=log,stderr=subprocess.STDOUT,check=True)
    with (root/'replay-bundle.log').open('xb') as log:
        subprocess.run(['node',str(ROOT/'scripts/package-player-replay.mjs'),
                        str(publication/'wwwroot/console/player-replay-offline.html'),
                        str(source/'src/VrCommand.Api/wwwroot/console')],stdout=log,stderr=subprocess.STDOUT,check=True)
    frameworks=runtime_config(publication)
    if 'v0.31.301' not in (publication/'wwwroot/console/index.html').read_text(encoding='utf-8'):raise ValueError('Expected console 0.31.301 in the actual publication')
    if set(frameworks.values())!={args.runtime_version}:raise ValueError('Published runtime differs from the requested patch')
    for name,value in hashes.items():
        if digest(ROOT/name)!=value:raise ValueError('Repository source changed during publication: '+name)
    receipt={'schemaVersion':1,'target':'win-x64','apiVersion':'0.31.0','consoleVersion':'0.31.301','completedAtUtc':datetime.now(timezone.utc).isoformat(),'runtimeFrameworks':frameworks,
        'baseCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'sourceFiles':hashes,
        'isolatedLocks':{name:{'originalSha256':hashes[name],'publishedSha256':digest(source/name)} for name in locks},
        'files':{v.relative_to(publication).as_posix():digest(v) for v in sorted(publication.rglob('*')) if v.is_file()},
        'scope':'Actual self-contained API publication; dependency pins retained in an isolated RID lock; not a signature / LAN / Unity / headset acceptance'}
    (root/'publish-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    (ROOT/'artifacts/control-server-publish-path.txt').write_text(str(root),encoding='utf-8');print(json.dumps({'complete':True,'directory':str(root),'frameworks':frameworks,'files':len(receipt['files'])}))
if __name__=='__main__':main()
