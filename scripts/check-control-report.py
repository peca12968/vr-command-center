"""Regress atomic publication using the actual compiled launcher's SaveNew and a controlled serializer."""
import argparse,hashlib,importlib.util,json,os,subprocess,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path);p.add_argument('--before',type=Path);p.add_argument('--before-source',type=Path);args=p.parse_args()
    if os.name!='nt':p.error('Requires the actual Windows Framework compiler / launcher')
    spec=importlib.util.spec_from_file_location('control_report_package',ROOT/'scripts/package-control-server.py');package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)
    after=package.verify(args.package);source=ROOT/'tools/WindowsControlLauncher/ControlLauncher.cs';assert after['launcherSourceSha256']==sha(source)
    out=ROOT/'artifacts/control-report-checks'/('run-'+uuid.uuid4().hex);out.mkdir(parents=True,exist_ok=False)
    proof=ROOT/'tools/WindowsControlLauncher/Tests/ReportPublicationProof.cs';exe=out/'ReportProof.exe';compiler=Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    with (out/'compile.log').open('xb') as log:subprocess.run([str(compiler),'/nologo','/codepage:65001','/platform:x64','/r:System.Web.Extensions.dll','/out:'+str(exe),str(proof)],stdout=log,stderr=subprocess.STDOUT,check=True)
    rows=[]
    for label,folder,expected in ([('before',args.before,1)] if args.before else [])+[('after',args.package,0)]:
        manifest=package.verify(folder)
        if label=='before':assert args.before_source and sha(args.before_source)==manifest['launcherSourceSha256']
        target=out/(label+'-publication.json');report=out/(label+'-proof.json');result=subprocess.run([str(exe),str(folder/'Start-Control.exe'),str(target),str(report)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
        value=json.loads(report.read_text(encoding='utf-8'));assert result.returncode==expected and value['passed']==(label=='after') and json.loads(value['finalContent'])=={'status':'ready'}
        if label=='before':assert value['serializerBlockedFinalVisible'] and value['finalBytesWhileBlocked']==0
        else:assert not value['serializerBlockedFinalVisible'] and value['finalBytesWhileBlocked'] is None
        rows.append({'case':label,'exitCode':result.returncode,'result':value,'package':str(folder),'launcherSha256':sha(folder/'Start-Control.exe'),'launcherSourceSha256':manifest['launcherSourceSha256']})
    result={'complete':True,'cases':rows,'proofSourceSha256':sha(proof),'scope':'Actual compiled method regression; no original OS scheduling, whole GUI, API or gameplay root-cause claim'}
    (out/'checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');(ROOT/'artifacts/control-report-checks-latest-path.txt').write_text(str(out),encoding='utf-8');print(json.dumps({'complete':True,'cases':len(rows),'directory':str(out)}))
if __name__=='__main__':main()
