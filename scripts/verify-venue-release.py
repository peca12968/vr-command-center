"""Verify the matching Windows packages and the signed Quest development APK before distribution."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
from xml.etree.ElementTree import Element
import zipfile


def local_module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


server_package = local_module('package-windows-server')
player_package = server_package.player
control_package = local_module('package-control-server')
hardware_package = local_module('package-hardware-simulator')
digest = player_package.digest
IDENTITY = ('unityVersion', 'sourceFingerprint', 'sceneNetworkId', 'playerPrefabId')
HASH = r'[0-9a-f]{64}'
ABI = 'arm64-v8a'
QUEST_LIBRARIES = ('libmain.so', 'libunity.so', 'libil2cpp.so', 'libopenxr_loader.so',
                   'libUnityOpenXR.so', 'libUnityARFoundationMeta.so')
ELF64_HEADER = struct.Struct('<16sHHIQQQIHHHHHH')
ELF64_PROGRAM_HEADER = struct.Struct('<IIQQQQQQ')
ELF64_LITTLE_ENDIAN = b'\x7fELF\x02\x01\x01'
ELF_SHARED_OBJECT = 3
ELF_AARCH64 = 183
ELF_LOAD = 1
ELF_DYNAMIC = 2
ZIP_LOCAL_HEADER = struct.Struct('<4s5H3I2H')
NATIVE_PAGE_BYTES = 4096
QUEST_APP = 'com.vrcommand.quest'
QUEST_VR_CATEGORY = 'com.oculus.intent.category.VR'


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


def windows_openxr(player, paired):
    data = 'VrCommand_Data/'
    def checked_bytes(relative):
        name = data + relative
        require(name in paired, 'Missing Windows OpenXR package file: ' + name)
        raw = (player / name).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == paired[name][1], 'Windows OpenXR file changed: ' + name)
        return raw

    manifest = json.loads(checked_bytes('UnitySubsystems/UnityOpenXR/UnitySubsystemsManifest.json'))
    require(isinstance(manifest, dict) and manifest.get('libraryName') == 'UnityOpenXR',
            'Unexpected Windows OpenXR subsystem library')
    for kind, identifier in [('displays', 'OpenXR Display'), ('inputs', 'OpenXR Input')]:
        rows = manifest.get(kind)
        require(isinstance(rows, list) and sum(isinstance(row, dict) and row.get('id') == identifier for row in rows) == 1,
                f'Missing or duplicate Windows subsystem: {identifier}')
    assemblies = json.loads(checked_bytes('ScriptingAssemblies.json'))
    names = assemblies.get('names') if isinstance(assemblies, dict) else None
    required_assemblies = ['Unity.XR.Management.dll', 'Unity.XR.OpenXR.dll', 'VrCommand.Runtime.dll']
    for name in required_assemblies:
        require(isinstance(names, list) and names.count(name) == 1
                and paired.get(data + 'Managed/' + name, (0,))[0] > 0,
                'Missing Windows XR scripting assembly or registration: ' + name)

    libraries = ['UnityOpenXR.dll', 'openxr_loader.dll']
    for name in libraries:
        raw = checked_bytes('Plugins/x86_64/' + name)
        error = 'Expected a Windows x64 OpenXR DLL: ' + name
        require(len(raw) >= 64 and raw[:2] == b'MZ', error)
        offset, = struct.unpack_from('<I', raw, 60)
        require(64 <= offset <= len(raw) - 26 and raw[offset:offset + 4] == b'PE\0\0', error)
        machine, = struct.unpack_from('<H', raw, offset + 4)
        size, flags, magic = struct.unpack_from('<HHH', raw, offset + 20)
        require(machine == 0x8664 and flags & 0x2000 and magic == 0x20b and 112 <= size <= len(raw) - offset - 24, error)
    return {'libraryName': 'UnityOpenXR', 'displayId': 'OpenXR Display', 'inputId': 'OpenXR Input',
            'nativeX64Libraries': libraries, 'registeredAssemblies': required_assemblies}


def verify_windows(control, server, player):
    control_path = control_package.plain(control / 'control-package.json')
    control_bytes = control_path.read_bytes()
    control_hash = hashlib.sha256(control_bytes).hexdigest()
    control_manifest = control_package.verify(control, manifest_bytes=control_bytes)
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
    openxr = windows_openxr(player, paired)
    require(digest(manifest_path) == player_manifest_hash, 'Windows player manifest changed during verification')
    require(digest(server_manifest_path) == server_manifest_hash, 'Windows server manifest changed during verification')
    require(digest(control_path) == control_hash, 'Windows control manifest changed during verification')
    return game, {'apiVersion': control_manifest['apiVersion'], 'consoleVersion': console, 'buildCommit': published['baseCommit'],
                  'controlFiles': len(control_manifest['files']), 'pairedGameFiles': len(runtime),
                  'serverFiles': len(server_manifest['files']), 'playerFiles': len(player_manifest['files']),
                  'playerManifestSha256': player_manifest_hash, 'serverManifestSha256': server_manifest_hash,
                  'controlManifestSha256': control_hash, 'openXR': openxr}


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


def quest_manifest_tree(dump):
    root = None
    stack = []
    for line in dump.splitlines():
        item = re.fullmatch(r'( *)([EN]): (\S+)(?: \(line=\d+\))?', line)
        if item:
            depth = len(item[1])
            while stack and stack[-1][0] >= depth:
                stack.pop()
            if item[2] == 'N':
                continue
            element = Element(item[3])
            if stack:
                stack[-1][1].append(element)
            else:
                require(root is None and element.tag == 'manifest', 'Invalid compiled Quest manifest tree')
                root = element
            stack.append((depth, element))
            continue
        attribute = re.fullmatch(r' *A: (?:http://schemas\.android\.com/apk/res/android:|android:)(\w+)(?:\(0x[0-9a-fA-F]+\))?=(.*)', line)
        if attribute and stack:
            value = re.match(r'"([^"]*)"', attribute[2])
            stack[-1][1].set(attribute[1], value[1] if value else attribute[2])
    require(root is not None, 'Missing compiled Quest manifest tree')
    return root


def quest_manifest_metadata(badging, dump):
    manifest = quest_manifest_tree(dump)
    launchers = re.findall(r"^launchable-activity: name='([^']+)'", badging, re.M)
    applications = manifest.findall('application')
    require(len(launchers) == len(applications) == 1, 'Quest APK needs one launchable activity and application')
    launcher, = launchers
    application, = applications
    extract_native_libs = application.get('extractNativeLibs', 'true')
    require(extract_native_libs in ('true', 'false'), 'Quest APK must declare a readable extractNativeLibs setting')
    names = {launcher}
    if launcher.startswith(QUEST_APP + '.'):
        relative = launcher[len(QUEST_APP):]
        names.add(relative)
        if '.' not in relative[1:]:
            names.add(relative[1:])
    activities = [activity for activity in application.findall('activity') if activity.get('name') in names]
    require(len(activities) == 1 and application.get('enabled', 'true') == 'true',
            'Quest APK launcher activity is missing or disabled')
    activity, = activities
    require(activity.get('enabled', 'true') == 'true' and activity.get('exported') == 'true',
            'Quest APK launcher activity must be enabled and exported')
    require(any('android.intent.action.MAIN' in {action.get('name') for action in intent.findall('action')}
                and {'android.intent.category.LAUNCHER', QUEST_VR_CATEGORY} <= {node.get('name') for node in intent.findall('category')}
                for intent in activity.findall('intent-filter')),
            'Quest APK launcher lacks a single MAIN filter with Android launcher and Meta VR categories')
    supported = application.findall("meta-data[@name='com.oculus.supportedDevices']")
    devices = supported[0].get('value', '').split('|') if len(supported) == 1 else []
    # The project's pinned Unity OpenXR settings emit eureka for Quest 3 development builds.
    quest3 = 'quest3' if 'quest3' in devices else 'eureka' if 'eureka' in devices else None
    require(quest3 is not None, 'Quest APK does not declare Quest 3 support')
    tracking = manifest.findall("uses-feature[@name='android.hardware.vr.headtracking']")
    require(len(tracking) == 1 and tracking[0].get('required', 'true') == 'true' and tracking[0].get('version') == '1',
            'Quest APK must require version 1 head tracking')
    require(len(manifest.findall("uses-feature[@name='com.oculus.feature.PASSTHROUGH']")) == 1,
            'Quest APK is missing the MR passthrough feature declaration')
    require(manifest.find("uses-permission[@name='android.permission.INTERNET']") is not None,
            'Quest APK lacks the Android Internet permission for multiplayer')
    return {'launchActivity': launcher, 'immersiveLauncher': True, 'quest3DeviceIdentifier': quest3,
            'headTrackingVersion': 1, 'passthroughDeclared': True, 'internetPermission': True,
            'extractNativeLibs': extract_native_libs == 'true'}


def verify_quest_library(file, size, name):
    header = file.read(ELF64_HEADER.size)
    error = f'Quest APK native library {name}: expected a little-endian ARM64 ELF shared object'
    require(len(header) == ELF64_HEADER.size and header.startswith(ELF64_LITTLE_ENDIAN), error)
    (_, kind, machine, version, _, table_offset, _, _, header_size, entry_size, entry_count,
     _, _, _) = ELF64_HEADER.unpack(header)
    require((kind, machine, version) == (ELF_SHARED_OBJECT, ELF_AARCH64, 1), error)
    error = f'Quest APK native library {name}: invalid ELF program headers'
    table_size = entry_size * entry_count
    require(header_size == ELF64_HEADER.size and table_offset >= header_size
            and entry_size == ELF64_PROGRAM_HEADER.size and 0 < entry_count < 0xffff
            and table_offset + table_size <= size, error)
    file.seek(table_offset)
    table = file.read(table_size)
    require(len(table) == table_size, error)
    file_backed = set()
    for kind, _, offset, _, _, file_size, memory_size, _ in ELF64_PROGRAM_HEADER.iter_unpack(table):
        if kind in (ELF_LOAD, ELF_DYNAMIC):
            require(file_size <= memory_size and offset + file_size <= size, error)
            if file_size:
                file_backed.add(kind)
    require({ELF_LOAD, ELF_DYNAMIC} <= file_backed, error)


def verify_direct_library(apk, info):
    require(info.compress_type == zipfile.ZIP_STORED,
            f'Quest APK directly loaded native library is compressed: {info.filename}')
    apk.seek(info.header_offset)
    header = apk.read(ZIP_LOCAL_HEADER.size)
    error = f'Quest APK native library has an invalid local ZIP header: {info.filename}'
    require(len(header) == ZIP_LOCAL_HEADER.size, error)
    signature, _, flags, method, _, _, _, _, _, name_bytes, extra_bytes = ZIP_LOCAL_HEADER.unpack(header)
    require(signature == b'PK\x03\x04' and method == zipfile.ZIP_STORED and not (flags | info.flag_bits) & 1
            and info.file_size == info.compress_size, error)
    data_offset = info.header_offset + ZIP_LOCAL_HEADER.size + name_bytes + extra_bytes
    require(data_offset % NATIVE_PAGE_BYTES == 0,
            f'Quest APK directly loaded native library is not aligned to 4 KiB: {info.filename}')


def quest_native_libraries(apk, *, extract_native_libs):
    with apk.open('rb') as raw, zipfile.ZipFile(raw) as archive:
        libraries = {}
        for info in archive.infolist():
            path = info.filename
            if not (path.startswith('lib/') and path.endswith('.so')):
                continue
            require(path.startswith(f'lib/{ABI}/') and path.count('/') == 2,
                    f'Quest APK has a native library outside its ARM64 ABI directory: {path}')
            name = path.rsplit('/', 1)[1]
            require(name not in libraries, f'Quest APK contains a duplicate native library: {name}')
            libraries[name] = info
        missing = [name for name in QUEST_LIBRARIES if name not in libraries]
        require(not missing, f'Quest APK is missing required native libraries: {", ".join(missing)}')
        for name, info in libraries.items():
            if not extract_native_libs:
                verify_direct_library(raw, info)
            with archive.open(info) as file:
                verify_quest_library(file, info.file_size, name)
    summary = {'arm64ElfLibrariesVerified': len(libraries), 'requiredLibraries': list(QUEST_LIBRARIES)}
    if not extract_native_libs:
        summary['directLoadAlignmentBytes'] = NATIVE_PAGE_BYTES
    return summary


def verify_quest(apk, sdk, jdk, game):
    require(apk.is_file() and apk.suffix.lower() == '.apk', 'Choose the original Quest APK')
    receipt_bytes = apk.with_suffix('.receipt.json').read_bytes()
    receipt = json.loads(receipt_bytes)
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
                              timeout=45).stdout.decode('utf-8').replace('\r\n', '\n')

    badging = run(aapt, 'dump', 'badging', apk)
    meta = quest_metadata(badging, run(java, '-jar', signer, 'verify', '--verbose', '--print-certs', apk))
    require(meta['version'] == receipt.get('version') and meta['versionCode'] == receipt.get('versionCode')
            and meta['architecture'] == receipt.get('architecture'), 'Quest APK version or architecture differs from the release receipt')
    for field in ('applicationId', 'minSdk', 'targetSdk', 'signatureV2', 'signerSha256'):
        if field in receipt:
            require(type(receipt[field]) is type(meta[field]) and receipt[field] == meta[field],
                    f'Quest APK {field} differs from the release receipt')
    android_manifest = quest_manifest_metadata(badging, run(aapt, 'dump', 'xmltree', apk, '--file', 'AndroidManifest.xml'))
    native_libraries = quest_native_libraries(apk, extract_native_libs=android_manifest['extractNativeLibs'])
    require(digest(apk) == receipt['sha256'], 'Quest APK changed during verification')
    return {**meta, 'bytes': receipt['bytes'], 'sha256': receipt['sha256'], 'androidManifest': android_manifest,
            'nativeLibraries': native_libraries, 'receiptSha256': hashlib.sha256(receipt_bytes).hexdigest()}


def verify_hardware(folder):
    manifest_path = control_package.plain(folder / 'hardware-package.json')
    raw = manifest_path.read_bytes()
    manifest = hardware_package.verify(folder, manifest_bytes=raw)
    files = manifest['files']
    require({*hardware_package.MOCK_FIREWALL_FILES, hardware_package.MOCK_IPC_FILE} <= files.keys(),
            'The field kit requires a simulator with guarded Windows and local socket support')
    for name in hardware_package.MOCK_FIREWALL_FILES:
        require(files[name]['sha256'] == digest(Path(__file__).with_name(name)),
                f'The simulator uses a different Windows firewall check: {name}')
    require(files['mock-device.py']['sha256'] == digest(Path(__file__).with_name('hardware-mock-peer.py')),
            'The simulator uses a different mock device entry point')
    return {'toolVersion': manifest['toolVersion'], 'mode': manifest['mode'], 'files': len(files),
            'manifestSha256': hashlib.sha256(raw).hexdigest()}


def write_field_kit(destination, control, server, player, apk, report, hardware=None):
    destination = control_package.plain(destination)
    require(destination.suffix.lower() == '.zip' and not destination.exists(), 'Choose a new field kit ZIP path')
    for folder in (control, server, player, hardware):
        if folder is not None:
            require(not destination.is_relative_to(folder.resolve()), 'Save the field kit outside its input packages')

    def copy_verified(archive, path, name, expected):
        checksum = hashlib.sha256()
        with control_package.plain(path).open('rb') as source, archive.open(name, 'w') as target:
            while chunk := source.read(1024 * 1024):
                checksum.update(chunk)
                target.write(chunk)
        require(checksum.hexdigest() == expected, f'File changed before field kit publication: {name}')

    with tempfile.TemporaryDirectory(prefix='.field-kit-', dir=destination.parent) as work:
        pending = Path(work) / 'kit.zip'
        with zipfile.ZipFile(pending, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
            for folder, top, role in ((control, 'VRCommand-ControlServer', 'control'),
                                      (server, 'VRCommand-GameServer', 'server'), (player, 'VRCommand-Player', 'player')):
                filename = role + '-package.json'
                raw = control_package.plain(folder / filename).read_bytes()
                require(hashlib.sha256(raw).hexdigest() == report['windows'][role + 'ManifestSha256'],
                        f'{role} manifest changed before field kit publication')
                archive.writestr(top + '/' + filename, raw)
                for row in json.loads(raw)['files']:
                    relative = control_package.relative(row['path'])
                    copy_verified(archive, folder / relative, top + '/' + relative.as_posix(), row['sha256'])
            if hardware:
                raw = control_package.plain(hardware / 'hardware-package.json').read_bytes()
                require(hashlib.sha256(raw).hexdigest() == report['hardwareSimulator']['manifestSha256'],
                        'Hardware simulator manifest changed before field kit publication')
                top = 'VRCommand-HardwareSimulator/'
                archive.writestr(top + 'hardware-package.json', raw)
                for name, row in json.loads(raw)['files'].items():
                    copy_verified(archive, hardware / control_package.relative(name), top + name, row['sha256'])
            for path, key in ((apk, 'sha256'), (apk.with_suffix('.receipt.json'), 'receiptSha256')):
                copy_verified(archive, path, 'Quest/' + path.name, report['quest'][key])
            scripts = Path(__file__).resolve().parent
            for name in ('deploy-quest.ps1', 'quest-adb-process.ps1', 'check-quest-usb.ps1',
                         'check-windows-firewall-notifications.ps1', 'check-field-install.ps1'):
                archive.write(scripts / name, 'scripts/' + name)
            archive.write(scripts.parent / 'docs/VENUE_FIELD_KIT.md', 'README.md')
            archive.writestr('venue-release.json', json.dumps(report, indent=2) + '\n')
        with zipfile.ZipFile(pending) as archive:
            require(archive.testzip() is None, 'Field kit ZIP readback failed')
        # Publish only a complete archive and never replace a concurrent delivery.
        if os.name == 'nt':
            pending.rename(destination)
        else:
            os.link(pending, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('control', 'server', 'player', 'quest-apk', 'sdk', 'jdk'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--field-kit', type=Path, help='Publish a new ZIP containing all verified packages and the release report')
    parser.add_argument('--hardware-simulator', type=Path, help='Verify an extracted hardware rehearsal package and include it when publishing a field kit')
    args = parser.parse_args()
    try:
        game, windows = verify_windows(args.control.absolute(), args.server.absolute(), args.player.absolute())
        quest = verify_quest(args.quest_apk.absolute(), args.sdk.absolute(), args.jdk.absolute(), game)
        report = {'verified': True, 'scope': 'offline-package-consistency', 'game': game, 'windows': windows, 'quest': quest}
        if args.hardware_simulator:
            report['hardwareSimulator'] = verify_hardware(args.hardware_simulator)
        if args.field_kit:
            write_field_kit(args.field_kit, args.control, args.server, args.player, args.quest_apk, report, args.hardware_simulator)
    except subprocess.SubprocessError as error:
        parser.exit(1, f'Venue release rejected: Android verification tool failed ({type(error).__name__}).\n')
    except (ValueError, OSError, KeyError, TypeError, AttributeError, zipfile.BadZipFile) as error:
        parser.exit(1, f'Venue release rejected: {error}\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
