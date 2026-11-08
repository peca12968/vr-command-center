"""Portable-package invariants; fake bytes here do not claim Unity execution."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('windows_package', ROOT / 'scripts/package-windows-player.py')
package = importlib.util.module_from_spec(spec); spec.loader.exec_module(package)


class PlayerPackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name).resolve()

    def fixture(self):
        for name in package.RUNTIME:
            file = self.folder / name
            if '.' in name: file.write_bytes(b'fixture only')
            else: file.mkdir()
        (self.folder / 'VrCommand_Data/globalgamemanagers').write_bytes(b'fixture only')
        receipt = {'schemaVersion': 1, 'target': 'StandaloneWindows64', 'sourceFingerprint': 'a' * 64,
                   'outputPath': str(self.folder / 'VrCommand.exe')}
        (self.folder / 'build-receipt.json').write_text(json.dumps(receipt), encoding='utf-8')
        return receipt

    def manifest(self):
        self.fixture(); (self.folder / 'Launch-Player.exe').write_bytes(b'fixture launcher')
        result = {'version': 1, 'platform': 'Windows-x64', 'files': [
            {'path': file.relative_to(self.folder).as_posix(), 'bytes': file.stat().st_size, 'sha256': package.digest(file)}
            for file in sorted(self.folder.rglob('*')) if file.is_file()]}
        self.save(result); return result

    def save(self, manifest):
        (self.folder / 'player-package.json').write_text(json.dumps(manifest), encoding='utf-8')

    def test_collect_uses_current_successful_receipt_and_excludes_do_not_ship_and_root_configs(self):
        receipt = self.fixture(); (self.folder / 'server.json').write_text('{"gameServerKey":"fixture-secret"}')
        (self.folder / 'Example_BurstDebugInformation_DoNotShip').mkdir()
        with patch.object(package, 'source_fingerprint', return_value='a' * 64):
            actual, files = package.collect(self.folder)
        self.assertEqual(receipt, actual); names = {name for _, name in files}
        self.assertNotIn('server.json', names); self.assertFalse(any('DoNotShip' in name for name in names))

    def test_collect_rejects_wrong_source_or_different_output(self):
        self.fixture()
        with patch.object(package, 'source_fingerprint', return_value='b' * 64), self.assertRaises(ValueError): package.collect(self.folder)
        receipt = json.loads((self.folder / 'build-receipt.json').read_text()); receipt['outputPath'] = str(self.folder / 'other.exe')
        (self.folder / 'build-receipt.json').write_text(json.dumps(receipt))
        with patch.object(package, 'source_fingerprint', return_value='a' * 64), self.assertRaises(ValueError): package.collect(self.folder)

    def test_private_state_inside_runtime_tree_rejects_instead_of_packaging(self):
        self.fixture()
        for name in ['server.json', 'keys.json', 'world.db', 'state.journal']:
            file = self.folder / 'VrCommand_Data' / name; file.write_bytes(b'fixture')
            with patch.object(package, 'source_fingerprint', return_value='a' * 64), self.assertRaises(ValueError): package.collect(self.folder)
            file.unlink()

    def test_collect_checks_exact_meta_subsystem_manifest(self):
        self.fixture()
        manifest = self.folder / package.META_SUBSYSTEM_JSON
        manifest.parent.mkdir(parents=True)
        meta = b'''{
    "name": "libUnityARFoundationMeta",
    "version": "1.0.0",
    "libraryName": "libUnityARFoundationMeta",
    "meshings": [
    {
        "id": "MetaOpenXR-Meshing"
    }]
}
'''
        with patch.object(package, 'source_fingerprint', return_value='a' * 64):
            manifest.write_bytes(meta)
            self.assertIn((manifest, package.META_SUBSYSTEM_JSON), package.collect(self.folder)[1])
            manifest.write_bytes(meta.replace(b'MetaOpenXR-Meshing', b'fixture-privatekey'))
            with self.assertRaisesRegex(ValueError, 'Unexpected Unity Meta subsystem manifest'):
                package.collect(self.folder)

    def test_hash_and_size_check_detect_changed_or_missing_runtime_files(self):
        self.manifest(); package.verify(self.folder)
        (self.folder / 'UnityPlayer.dll').write_bytes(b'changed')
        with self.assertRaises(ValueError): package.verify(self.folder)
        (self.folder / 'UnityPlayer.dll').unlink()
        with self.assertRaises(FileNotFoundError): package.verify(self.folder)

    def test_manifest_paths_cannot_escape_or_use_windows_aliases(self):
        manifest = self.manifest()
        for name in ['../outside', '/outside', 'C:/outside', 'a\\b', 'a//b', 'a/./b', 'file:stream']:
            manifest['files'][0]['path'] = name; self.save(manifest)
            with self.subTest(name=name), self.assertRaises(ValueError): package.verify(self.folder)

    def test_case_collisions_and_missing_essentials_are_rejected(self):
        manifest = self.manifest(); duplicate = dict(manifest['files'][0]); duplicate['path'] = duplicate['path'].upper()
        manifest['files'].append(duplicate); self.save(manifest)
        with self.assertRaises((ValueError, FileNotFoundError)): package.verify(self.folder)
        manifest['files'] = [row for row in manifest['files'] if row['path'] != 'VrCommand.exe' and row is not duplicate]; self.save(manifest)
        with self.assertRaises(ValueError): package.verify(self.folder)

    def test_symlink_is_not_followed(self):
        target = self.folder / 'original'; target.write_bytes(b'fixture')
        link = self.folder / 'link'
        try: link.symlink_to(target)
        except OSError: self.skipTest('Symlink creation requires an unavailable Windows privilege')
        with self.assertRaises(ValueError): package.plain(link)


if __name__ == '__main__': unittest.main()
