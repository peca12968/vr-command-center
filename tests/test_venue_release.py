"""Offline verification boundaries, independent of native or headset acceptance."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile


spec = importlib.util.spec_from_file_location('venue_release', Path(__file__).resolve().parents[1] / 'scripts/verify-venue-release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class VenueReleaseTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name).resolve()
        self.control, self.server, self.player = (self.root / name for name in ('control', 'server', 'player'))
        self.source = {'schemaVersion': 1, 'target': 'StandaloneWindows64', 'sourceFingerprint': 'a' * 64,
                       'unityVersion': '6000.3.27f1', 'sceneNetworkId': 'GlobalObjectId_V1-2-scene',
                       'playerPrefabId': 'GlobalObjectId_V1-1-player'}
        publication = {'target': 'win-x64', 'apiVersion': '0.31.0', 'consoleVersion': '0.31.83',
                       'runtimeFrameworks': {'Microsoft.NETCore.App': '10.0.14'}}
        for name in ('Start-Control.exe', 'Runtime/VrCommand.Api.exe', 'Runtime/VrCommand.Api.dll'):
            self.write(self.control, name, 'fixture binary')
        self.write(self.control, 'Runtime/wwwroot/console/index.html', '控制台 v0.31.83 ·')
        self.write(self.control, 'publish-receipt.json', dict(publication, schemaVersion=1, baseCommit='b' * 40))
        self.manifest(self.control, 'control-package.json', dict(publication, schemaVersion=1))
        for name in ('VrCommand.exe', 'UnityPlayer.dll', 'VrCommand_Data/globalgamemanagers', 'build-receipt.json'):
            body = self.source if name.endswith('.json') else 'fixture game'
            self.write(self.player, name, body)
            self.write(self.server, 'Runtime/' + name, body)
        self.write(self.player, 'Launch-Player.exe', 'fixture launcher')
        self.write(self.server, 'Launch-Server.exe', 'fixture launcher')
        self.manifest(self.server, 'server-package.json', {'schemaVersion': 1, 'target': 'win-x64', 'build': self.source})
        self.manifest(self.player, 'player-package.json', {'version': 1, 'platform': 'Windows-x64', 'build': self.source})

    def write(self, folder, name, body):
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(body) if isinstance(body, dict) else body, encoding='utf-8')

    def manifest(self, folder, name, fields):
        rows = [{'path': file.relative_to(folder).as_posix(), 'bytes': file.stat().st_size, 'sha256': release.digest(file)}
                for file in sorted(folder.rglob('*')) if file.is_file() and file.name != name]
        self.write(folder, name, dict(fields, files=rows))

    def test_same_windows_game_runtime_and_management_publication(self):
        identity, summary = release.verify_windows(self.control, self.server, self.player)
        self.assertEqual(identity, {key: self.source[key] for key in release.IDENTITY})
        self.assertEqual(summary['pairedGameFiles'], 4)
        self.assertEqual(summary['consoleVersion'], '0.31.83')
        server_manifest = self.server / 'server-package.json'
        server_bytes = server_manifest.read_bytes()
        self.assertEqual(summary['serverManifestSha256'], hashlib.sha256(server_bytes).hexdigest())
        server_manifest.write_bytes(server_bytes + b'\n')
        _, server_repacked = release.verify_windows(self.control, self.server, self.player)
        self.assertEqual(server_repacked['playerManifestSha256'], summary['playerManifestSha256'])
        self.assertNotEqual(server_repacked['serverManifestSha256'], summary['serverManifestSha256'])
        manifest = self.player / 'player-package.json'
        original = manifest.read_bytes()
        self.assertEqual(summary['playerManifestSha256'], hashlib.sha256(original).hexdigest())
        manifest.write_bytes(original + b'\n')
        _, repackaged = release.verify_windows(self.control, self.server, self.player)
        self.assertEqual(repackaged['pairedGameFiles'], summary['pairedGameFiles'])
        self.assertNotEqual(repackaged['playerManifestSha256'], summary['playerManifestSha256'])

    def test_individually_valid_player_with_replaced_runtime_is_not_a_pair(self):
        self.write(self.player, 'VrCommand.exe', 'different but manifest-consistent game')
        self.manifest(self.player, 'player-package.json', {'version': 1, 'platform': 'Windows-x64', 'build': self.source})
        with self.assertRaisesRegex(ValueError, r'runtime files differ \(1\): VrCommand\.exe'):
            release.verify_windows(self.control, self.server, self.player)

    def test_windows_build_mismatch_lists_only_changed_identity_fields(self):
        different = dict(self.source, sourceFingerprint='c' * 64, playerPrefabId='GlobalObjectId_V1-1-other')
        self.write(self.player, 'build-receipt.json', different)
        self.manifest(self.player, 'player-package.json', {'version': 1, 'platform': 'Windows-x64', 'build': different})
        with self.assertRaisesRegex(ValueError, r'differs: sourceFingerprint, playerPrefabId$'):
            release.verify_windows(self.control, self.server, self.player)

    def test_player_with_unlisted_files_is_rejected(self):
        self.write(self.player, 'unlisted.json', {})
        with self.assertRaisesRegex(ValueError, 'unlisted files'):
            release.verify_windows(self.control, self.server, self.player)

    def test_player_manifest_replacement_during_verification_is_rejected(self):
        verify = release.player_package.verify

        def replace_after_verifying(folder, *, manifest_bytes):
            checked = verify(folder, manifest_bytes=manifest_bytes)
            (folder / 'player-package.json').write_bytes(manifest_bytes + b'\n')
            return checked

        with patch.object(release.player_package, 'verify', side_effect=replace_after_verifying):
            with self.assertRaisesRegex(ValueError, 'manifest changed during verification'):
                release.verify_windows(self.control, self.server, self.player)

    def test_server_manifest_replacement_during_verification_is_rejected(self):
        verify = release.server_package.verify

        def replace_after_verifying(folder, *, manifest_bytes):
            checked = verify(folder, manifest_bytes=manifest_bytes)
            (folder / 'server-package.json').write_bytes(manifest_bytes + b'\n')
            return checked

        with patch.object(release.server_package, 'verify', side_effect=replace_after_verifying):
            with self.assertRaisesRegex(ValueError, 'server manifest changed during verification'):
                release.verify_windows(self.control, self.server, self.player)

    def test_quest_uses_original_receipt_bytes_and_build_identity(self):
        apk = self.root / 'game.apk'
        with zipfile.ZipFile(apk, 'w') as archive:
            for name in ('libil2cpp.so', 'libUnityOpenXR.so', 'libopenxr_loader.so'):
                archive.writestr('lib/arm64-v8a/' + name, b'fixture')
        receipt = {'artifact': apk.name, 'bytes': apk.stat().st_size, 'sha256': release.digest(apk),
                   'version': '0.49.0', 'versionCode': 63, 'architecture': 'arm64-v8a',
                   'source': dict(self.source, target='Android')}
        self.write(self.root, 'game.receipt.json', receipt)
        game = release.identity(self.source, 'StandaloneWindows64')
        with self.assertRaisesRegex(ValueError, r'build source or network identity differs: sourceFingerprint$'):
            release.verify_quest(apk, self.root, self.root, dict(game, sourceFingerprint='b' * 64))
        apk.write_bytes(b'wrong APK')
        with self.assertRaisesRegex(ValueError, 'original release receipt'):
            release.verify_quest(apk, self.root, self.root, game)

    def test_verified_quest_metadata_must_match_fields_in_original_receipt(self):
        apk = self.root / 'game.apk'
        with zipfile.ZipFile(apk, 'w') as archive:
            for name in ('libil2cpp.so', 'libUnityOpenXR.so', 'libopenxr_loader.so'):
                archive.writestr('lib/arm64-v8a/' + name, b'fixture')
        for name in ('build-tools/36.0.0/aapt2', 'build-tools/36.0.0/aapt2.exe', 'build-tools/36.0.0/lib/apksigner.jar', 'bin/java', 'bin/java.exe'):
            self.write(self.root, name, 'fixture')
        meta = {'applicationId': release.QUEST_APP, 'version': '0.49.0', 'versionCode': 63, 'architecture': 'arm64-v8a',
                'minSdk': 32, 'targetSdk': 35, 'signatureV2': True, 'signerSha256': 'e' * 64}
        receipt = {'artifact': apk.name, 'bytes': apk.stat().st_size, 'sha256': release.digest(apk),
                   'source': dict(self.source, target='Android'), 'version': meta['version'],
                   'versionCode': meta['versionCode'], 'architecture': meta['architecture']}
        game = release.identity(self.source, 'StandaloneWindows64')
        with (patch.object(release.subprocess, 'run', **{'return_value.stdout': b''}),
              patch.object(release, 'quest_metadata', return_value=meta),
              patch.object(release, 'quest_manifest_metadata', return_value={'immersiveLauncher': True})):
            for accepted in (receipt, dict(receipt, **meta)):
                self.write(self.root, 'game.receipt.json', accepted)
                result = release.verify_quest(apk, self.root, self.root, game)
                self.assertEqual(result['signerSha256'], 'e' * 64)
                self.assertTrue(result['androidManifest']['immersiveLauncher'])
            for field, value in [('signerSha256', 'f' * 64), ('signatureV2', 1), ('minSdk', 31),
                                 ('targetSdk', 34), ('applicationId', 'com.example.other')]:
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, f'Quest APK {field} differs'):
                    self.write(self.root, 'game.receipt.json', {**receipt, **meta, field: value})
                    release.verify_quest(apk, self.root, self.root, game)

            def replace_apk(_badging, _manifest):
                apk.write_bytes(b'replaced after the manifest was read')
                return {'immersiveLauncher': True}

            self.write(self.root, 'game.receipt.json', receipt)
            with patch.object(release, 'quest_manifest_metadata', side_effect=replace_apk), \
                    self.assertRaisesRegex(ValueError, 'changed during verification'):
                release.verify_quest(apk, self.root, self.root, game)

    def test_quest_metadata_accepts_arm64_and_verified_v2_only(self):
        badging = ("package: name='com.vrcommand.quest' versionCode='63' versionName='0.49.0'\n"
                   "minSdkVersion:'32'\ntargetSdkVersion:'35'\napplication-debuggable\nnative-code: 'arm64-v8a'\n")
        signing = ('Verified using v2 scheme (APK Signature Scheme v2): true\n'
                   f"Signer #1 certificate SHA-256 digest: {'e' * 64}\n")
        result = release.quest_metadata(badging, signing)
        self.assertEqual((result['versionCode'], result['signerSha256']), (63, 'e' * 64))
        for altered in (badging.replace('arm64-v8a', 'x86'), badging.replace('32', '31'),
                        badging.replace('com.vrcommand.quest', 'com.vrcommand.udpprobe'),
                        badging.replace('application-debuggable', '')):
            with self.subTest(badging=altered), self.assertRaises(ValueError):
                release.quest_metadata(altered, signing)
        with self.assertRaisesRegex(ValueError, 'v2 signature'):
            release.quest_metadata(badging, signing.replace('true', 'false'))

    def test_compiled_quest_manifest_requires_the_same_vr_launcher_and_mr_declarations(self):
        badging = "launchable-activity: name='com.vrcommand.quest.PlayerActivity'  label='' icon=''\n"
        tree = '''N: android=http://schemas.android.com/apk/res/android (line=1)
  E: manifest (line=1)
    E: uses-feature (line=3)
      A: android:name="android.hardware.vr.headtracking"
      A: android:required=true
      A: android:version=1
    E: uses-feature (line=6)
      A: android:name="com.oculus.feature.PASSTHROUGH"
    E: uses-permission (line=8)
      A: android:name="android.permission.INTERNET"
    E: application (line=10)
      E: meta-data (line=11)
        A: android:name="com.oculus.supportedDevices"
        A: android:value="quest2|eureka|quest3s" (Raw: "quest2|eureka|quest3s")
      E: activity (line=14)
        A: http://schemas.android.com/apk/res/android:name(0x01010003)=".PlayerActivity" (Raw: ".PlayerActivity")
        A: android:exported=true
        E: intent-filter (line=16)
          E: category (line=17)
            A: android:name="android.intent.category.LAUNCHER"
          E: action (line=19)
            A: android:name="android.intent.action.MAIN"
          E: category (line=21)
            A: android:name="com.oculus.intent.category.VR"
'''
        summary = release.quest_manifest_metadata(badging, tree)
        self.assertEqual(summary['launchActivity'], 'com.vrcommand.quest.PlayerActivity')
        self.assertEqual(summary['quest3DeviceIdentifier'], 'eureka')
        self.assertEqual(release.quest_manifest_metadata(badging, tree.replace('eureka', 'quest3'))['quest3DeviceIdentifier'], 'quest3')
        split_vr_filter = tree.replace('          E: category (line=21)', '        E: intent-filter (line=21)\n          E: category (line=22)')
        for candidate, error in (
            (split_vr_filter, 'single MAIN filter'),
            (tree.replace('com.oculus.intent.category.VR', 'com.oculus.intent.category.2D'), 'Meta VR categories'),
            (tree.replace('android:exported=true', 'android:exported=false'), 'enabled and exported'),
            (tree.replace('android:required=true', 'android:required=false'), 'version 1 head tracking'),
            (tree.replace('quest2|eureka|quest3s', 'quest2|quest3s'), 'declare Quest 3 support'),
            (tree.replace('com.oculus.feature.PASSTHROUGH', 'com.oculus.feature.OTHER'), 'passthrough feature declaration'),
            (tree.replace('android.permission.INTERNET', 'android.permission.ACCESS_NETWORK_STATE'), 'Internet permission'),
        ):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                release.quest_manifest_metadata(badging, candidate)
