import hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('control_package_checks',ROOT/'scripts/package-control-server.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ControlPackageBoundaryTests(unittest.TestCase):
    def temporary(self):
        temp=tempfile.TemporaryDirectory(prefix='vr-control-package-check-');self.addCleanup(temp.cleanup);return Path(temp.name)
    def manifest(self,folder,name,content):
        path=folder/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
        value={'schemaVersion':1,'target':'win-x64','apiVersion':'0.31.0','files':[{'path':name,'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()}]}
        (folder/'control-package.json').write_text(json.dumps(value),encoding='utf-8');return value
    def test_tampered_payload_does_not_verify(self):
        folder=self.temporary();self.manifest(folder,'README.txt',b'original');(folder/'README.txt').write_bytes(b'modified')
        with self.assertRaises(ValueError):m.verify(folder)
    def test_even_hash_matching_nested_credentials_cannot_be_shipped(self):
        for key in ('OperatorKeys','joinTicket','ControlPipeToken','GameServerKey'):
            with self.subTest(key=key):
                folder=self.temporary();self.manifest(folder,'settings.json',json.dumps({'nested':[{'unknown':{key:'sensitive'}}]}).encode())
                with self.assertRaises(ValueError):m.verify(folder)
    def test_additional_instance_files_cannot_hitchhike_on_a_valid_package(self):
        folder=self.temporary();self.manifest(folder,'README.txt',b'original');(folder/'operator-keys.json').write_text('{}',encoding='utf-8')
        with self.assertRaises(ValueError):m.verify(folder)
    def test_matching_hash_does_not_authorize_database_or_ticket_key_paths(self):
        for name in ('Runtime/missions/missions.db','Runtime/sessions/worlds.db-wal','Runtime/player-ticket-signing.key','Runtime/old.worldlog'):
            with self.subTest(name=name):
                folder=self.temporary();self.manifest(folder,name,b'not-for-distribution')
                with self.assertRaises(ValueError):m.verify(folder)
    def test_windows_alias_or_traversal_cannot_escape_the_package(self):
        for name in ('../outside','Runtime/../outside','/outside','C:/outside','Runtime\\outside','Runtime//outside'):
            with self.subTest(name=name),self.assertRaises(ValueError):m.relative(name)
    def test_case_aliased_duplicate_cannot_replace_an_entry(self):
        folder=self.temporary();manifest=self.manifest(folder,'README.txt',b'original');manifest['files'].append(dict(manifest['files'][0],path='readme.TXT'));(folder/'control-package.json').write_text(json.dumps(manifest),encoding='utf-8')
        with self.assertRaises(ValueError):m.verify(folder)
    def test_license_references_retain_the_exact_upstream_blob_bytes(self):
        root=ROOT/'tools/WindowsControlLauncher/Notices';upstream=json.loads((root/'UPSTREAM.json').read_text(encoding='utf-8'))
        for row in upstream['files']:
            content=(root/row['path']).read_bytes();self.assertEqual(row['githubBlobSha'],hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest())
if __name__=='__main__':unittest.main()
