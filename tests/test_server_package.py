"""Package integrity boundaries with fake bytes, not native Unity/GUI evidence."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('test_server_package',ROOT/'scripts/package-windows-server.py');package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)
class ServerPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name).resolve()
        for name in ['Launch-Server.exe','Runtime/VrCommand.exe','Runtime/UnityPlayer.dll','Runtime/build-receipt.json']:
            f=self.folder/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b'fixture, not a built player')
        self.manifest={'schemaVersion':1,'target':'win-x64','files':[{'path':f.relative_to(self.folder).as_posix(),'bytes':f.stat().st_size,'sha256':package.digest(f)} for f in sorted(self.folder.rglob('*')) if f.is_file()]};self.save()
    def save(self):(self.folder/'server-package.json').write_text(json.dumps(self.manifest),encoding='utf-8')
    def test_changed_runtime_or_missing_file_is_rejected(self):
        package.verify(self.folder);file=self.folder/'Runtime/UnityPlayer.dll';file.write_bytes(b'changed')
        with self.assertRaises(ValueError):package.verify(self.folder)
        file.unlink()
        with self.assertRaises(FileNotFoundError):package.verify(self.folder)
    def test_extra_private_configuration_is_rejected(self):
        (self.folder/'server-config.json').write_text('{"gameServerKey":"fixture"}')
        with self.assertRaises(ValueError):package.verify(self.folder)
    def test_manifest_cannot_escape_or_use_windows_stream_alias(self):
        for name in ['../other','C:/other','/other','Runtime\\other','a//b','a/./b','name:stream']:
            self.manifest['files'][0]['path']=name;self.save()
            with self.subTest(name=name),self.assertRaises(ValueError):package.verify(self.folder)
    def test_case_duplicate_and_missing_required_launcher_reject(self):
        row=dict(self.manifest['files'][0]);self.manifest['files'].append(dict(row,path=row['path'].upper()));self.save()
        with self.assertRaises((ValueError,FileNotFoundError)):package.verify(self.folder)
        self.manifest['files']=[x for x in self.manifest['files'] if x['path'].lower()!='launch-server.exe'];(self.folder/'Launch-Server.exe').unlink();self.save()
        with self.assertRaises(ValueError):package.verify(self.folder)
if __name__=='__main__':unittest.main()
