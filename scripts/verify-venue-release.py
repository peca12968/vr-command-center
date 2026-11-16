"""Verify the matching Windows packages and the signed Quest development APK before distribution."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile


def local_module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


server_package = local_module('package-windows-server')
player_package = server_package.player
control_package = local_module('package-control-server')
digest = player_package.digest
IDENTITY = ('unityVersion', 'sourceFingerprint', 'sceneNetworkId', 'playerPrefabId')
HASH = r'[0-9a-f]{64}'
ABI = 'arm64-v8a'
QUEST_APP = 'com.vrcommand.quest'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def identity(receipt, target):
    require(receipt.get('schemaVersion') == 1 and receipt.get('target') == target,
            f'Invalid {target} build receipt')
    values = {key: receipt.get(key) for key in IDENTITY}
    require(all(isinstance(value, str) and value for value in values.values())
            and re.fullmatch(HASH, values['sourceFingerprint'])
            and all(values[key].startswith('GlobalObjectId_V1-') for key in ('sceneNetworkId', 'playerPrefabId')),
            f'Missing {target} source or network identity')
    return values


def require_matching_identity(expected, actual, message):
    different = [field for field in IDENTITY if expected[field] != actual[field]]
    require(not different, f'{message}: {", ".join(different)}')


def verify_windows(control, server, player):
    control_manifest = control_package.verify(control)
    server_manifest_path = player_package.plain(server / 'server-package.json')
    server_manifest_bytes = server_manifest_path.read_bytes()
    server_manifest_hash = hashlib.sha256(server_manifest_bytes).hexdigest()
    server_manifest = server_package.verify(server, manifest_bytes=server_manifest_bytes)
    manifest_path = player_package.plain(player / 'player-package.json')
    manifest_bytes = manifest_path.read_bytes()
    player_manifest = player_package.verify(player, manifest_bytes=manifest_bytes)
    player_manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    published = read(control / 'publish-receipt.json')
    console = control_manifest.get('consoleVersion')
    require(published.get('schemaVersion') == 1 and published.get('target') == 'win-x64'
            and isinstance(console, str) and re.fullmatch(r'\d+\.\d+\.\d+', console)
            and all(published.get(key) == control_manifest.get(key) for key in ('apiVersion', 'consoleVersion', 'runtimeFrameworks'))
            and re.fullmatch(r'[0-9a-f]{40}', published.get('baseCommit', '')) is not None,
            'Management publication and package identities differ')
    required = {'Start-Control.exe', 'Runtime/VrCommand.Api.exe', 'Runtime/VrCommand.Api.dll',
                'Runtime/wwwroot/console/index.html', 'publish-receipt.json'}
    require(required <= {row['path'] for row in control_manifest['files']}
            and f'v{console} ' in (control / 'Runtime/wwwroot/console/index.html').read_text(encoding='utf-8'),
            'Management package is missing its expected runtime or console')

    server_build = read(server / 'Runtime/build-receipt.json')
    player_build = read(player / 'build-receipt.json')
    require(server_build == server_manifest.get('build'), 'Windows server manifest and original build receipt differ')
    require(player_build == player_manifest.get('build'), 'Windows player manifest and original build receipt differ')
    game = identity(server_build, 'StandaloneWindows64')
    require_matching_identity(game, identity(player_build, 'StandaloneWindows64'),
                              'Windows server and player build source or network identity differs')
    require(server_build == player_build, 'Windows server and player do not share their original build receipt')
    runtime = {row['path'].removeprefix('Runtime/'): (row['bytes'], row['sha256']) for row in server_manifest['files']
               if row['path'].startswith('Runtime/')}
    names = set(player_package.RUNTIME) | {'build-receipt.json'}
    paired = {row['path']: (row['bytes'], row['sha256']) for row in player_manifest['files']
              if row['path'].split('/', 1)[0] in names}
    if runtime != paired:
        different = sorted(name for name in runtime.keys() | paired.keys() if runtime.get(name) != paired.get(name))
        preview = ', '.join(different[:3])
        raise ValueError(f'Windows server and player runtime files differ ({len(different)}): {preview}')
    require({f.relative_to(player).as_posix() for f in player.rglob('*') if f.is_file()}
            == {row['path'] for row in player_manifest['files']} | {'player-package.json'},
            'Windows player package contains unlisted files')
    require(digest(manifest_path) == player_manifest_hash, 'Windows player manifest changed during verification')
    require(digest(server_manifest_path) == server_manifest_hash, 'Windows server manifest changed during verification')
    return game, {'apiVersion': control_manifest['apiVersion'], 'consoleVersion': console, 'buildCommit': published['baseCommit'],
                  'controlFiles': len(control_manifest['files']), 'pairedGameFiles': len(runtime),
                  'serverFiles': len(server_manifest['files']), 'playerFiles': len(player_manifest['files']),
                  'playerManifestSha256': player_manifest_hash, 'serverManifestSha256': server_manifest_hash}


def quest_metadata(badging, signing):
    package = re.search(r"^package: name='([^']+)' versionCode='([0-9]+)' versionName='([^']+)'", badging, re.M)
    require(package is not None and package[1] == QUEST_APP, 'Wrong Quest application identifier')
    require(re.search(r"^(?:minSdkVersion|sdkVersion):'32'$", badging, re.M)
            and re.search(r"^targetSdkVersion:'35'$", badging, re.M), 'Unexpected Quest SDK levels')
    native = re.search(r'^native-code:\s*([^\r\n]+)$', badging, re.M)
    require(native is not None and re.findall(r"'([^']+)'", native[1]) == [ABI], 'Quest game APK must contain only ARM64 native code')
    require(re.search(r'^application-debuggable$', badging, re.M), 'Expected a Quest development APK')
    require(re.search(r'^Verified using v2 scheme \(APK Signature Scheme v2\): true$', signing, re.M),
            'Quest APK v2 signature was not verified')
    signers = re.findall(r'^Signer #[0-9]+ certificate SHA-256 digest: ([0-9a-f]{64})$', signing, re.M)
    require(len(signers) == 1, 'Expected one verified Quest signer')
    return {'applicationId': package[1], 'version': package[3], 'versionCode': int(package[2]),
            'architecture': ABI, 'minSdk': 32, 'targetSdk': 35, 'signatureV2': True, 'signerSha256': signers[0]}


def verify_quest(apk, sdk, jdk, game):
    require(apk.is_file() and apk.suffix.lower() == '.apk', 'Choose the original Quest APK')
    receipt = read(apk.with_suffix('.receipt.json'))
    require(receipt.get('artifact') == apk.name and type(receipt.get('bytes')) is int
            and apk.stat().st_size == receipt['bytes'] and digest(apk) == receipt.get('sha256'),
            'Quest APK differs from its original release receipt')
    require_matching_identity(game, identity(receipt['source'], 'Android'),
                              'Quest APK differs from the matching Windows pair; build source or network identity differs')
    suffix = '.exe' if os.name == 'nt' else ''
    tools = sdk / 'build-tools' / '36.0.0'
    aapt, java, signer = tools / ('aapt2' + suffix), jdk / 'bin' / ('java' + suffix), tools / 'lib/apksigner.jar'
    require(all(file.is_file() for file in (aapt, java, signer)), 'Android SDK or JDK is missing the verification tools')

    def run(*args):
        return subprocess.run([str(arg) for arg in args], check=True, capture_output=True,
                              encoding='utf-8', timeout=45).stdout

    meta = quest_metadata(run(aapt, 'dump', 'badging', apk), run(java, '-jar', signer, 'verify', '--verbose', '--print-certs', apk))
    require(meta['version'] == receipt.get('version') and meta['versionCode'] == receipt.get('versionCode')
            and meta['architecture'] == receipt.get('architecture'), 'Quest APK version or architecture differs from the release receipt')
    for field in ('applicationId', 'minSdk', 'targetSdk', 'signatureV2', 'signerSha256'):
        if field in receipt:
            require(type(receipt[field]) is type(meta[field]) and receipt[field] == meta[field],
                    f'Quest APK {field} differs from the release receipt')
    with zipfile.ZipFile(apk) as archive:
        natives = {f'lib/{ABI}/{name}' for name in ('libil2cpp.so', 'libUnityOpenXR.so', 'libopenxr_loader.so')}
        require(natives <= set(archive.namelist()), 'Quest APK is missing the required OpenXR or game libraries')
    return {**meta, 'bytes': receipt['bytes'], 'sha256': receipt['sha256']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('control', 'server', 'player', 'quest-apk', 'sdk', 'jdk'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        game, windows = verify_windows(args.control.absolute(), args.server.absolute(), args.player.absolute())
        quest = verify_quest(args.quest_apk.absolute(), args.sdk.absolute(), args.jdk.absolute(), game)
    except subprocess.SubprocessError as error:
        parser.exit(1, f'Venue release rejected: Android verification tool failed ({type(error).__name__}).\n')
    except (ValueError, OSError, KeyError, TypeError, AttributeError, zipfile.BadZipFile) as error:
        parser.exit(1, f'Venue release rejected: {error}\n')
    print(json.dumps({'verified': True, 'scope': 'offline-package-consistency', 'game': game, 'windows': windows, 'quest': quest}))


if __name__ == '__main__':
    main()
