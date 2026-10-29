"""Compile managed player adapters against real Unity/package APIs; never run Unity."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile
import urllib.request
from datetime import datetime, timezone
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'artifacts/unity-sdk-check'
# Official Unity registry tarball SHA-1 values. These are a diagnostic SDK graph,
# not a replacement for the project's eventual UPM packages-lock.json.
PINS = {
    'com.unity.netcode.gameobjects': ('2.7.0', 'bd2a018756edad4b0a685634ffde855b1207c37e'),
    'com.unity.inputsystem': ('1.17.0', '02433b2481abc5c0063956fdc211f3d8c777447f'),
    'com.unity.transport': ('2.6.0', '6e74a0e6481d0f4d298b271a4172b7d880d164e1'),
    'com.unity.burst': ('1.8.24', 'f7a407abf4d5abf19ce630824dcde261e02ed97e'),
    'com.unity.collections': ('2.4.3', 'eba9b2ae55c09c3548eaeac72a96dda87b0640cf'),
    'com.unity.mathematics': ('1.3.2', '8017b507cc74bf0a1dd14b18aa860569f807314d'),
}
SOURCE_FOLDERS = {'Runtime', 'InputSystem', 'Unity.Collections', 'Unity.Mathematics'}
SUPPORT_DLLS = {'package/Unity.Burst.Unsafe.dll',
                'package/Unity.Collections.LowLevel.ILSupport/Unity.Collections.LowLevel.ILSupport.dll'}
LIMITATION = ('Managed API binding only. No Unity Editor import, ProjectBuilder compilation, '
              'UPM resolution, NGO/Burst/Collections IL postprocessing, native execution, '
              'shader/audio import, NUnit execution, IL2CPP, APK or headset validation.')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected(path):
    parts = PurePosixPath(path).parts
    if len(parts) < 2 or parts[0] != 'package' or any(p.endswith('~') or p.startswith('.') or p == '..' for p in parts):
        return False
    if path in SUPPORT_DLLS or path == 'package/package.json':
        return True
    if len(parts) == 2 and ('license' in parts[-1].lower() or 'notices' in parts[-1].lower()):
        return True
    return len(parts) > 2 and parts[1] in SOURCE_FOLDERS and PurePosixPath(path).suffix in {'.cs', '.asmdef'}


def receipt(folder, name):
    version, archive_hash = PINS[name]
    return {'name': name, 'version': version, 'archiveSha1': archive_hash,
            'tarball': f'https://download.packages.unity.com/{name}/-/{name}-{version}.tgz',
            'files': {p.relative_to(folder).as_posix(): digest(p) for p in sorted(folder.rglob('*'))
                      if p.is_file() and selected(p.relative_to(folder).as_posix())}}


def package(name, offline):
    version, archive_hash = PINS[name]
    target = WORK / 'sources' / name / version
    record = target / 'source-receipt.json'
    if record.exists():
        if json.loads(record.read_text(encoding='utf-8')) != receipt(target, name):
            raise RuntimeError(f'Cached SDK source changed: {target}')
    else:
        if target.exists():
            raise RuntimeError(f'Unverified SDK cache already exists: {target}')
        if offline:
            raise RuntimeError(f'Missing verified SDK cache for {name} {version}; run once without --offline')
        target.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix='sdk-extract-', dir=WORK))
        with tempfile.NamedTemporaryFile(prefix='sdk-download-', suffix='.tgz', dir=WORK, delete=False) as output:
            archive_path = Path(output.name)
            checksum = hashlib.sha1()
            url = f'https://download.packages.unity.com/{name}/-/{name}-{version}.tgz'
            with urllib.request.urlopen(url, timeout=60) as response:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                    checksum.update(chunk)
        if checksum.hexdigest() != archive_hash:
            raise RuntimeError(f'Official SDK tarball checksum mismatch: {name}')
        with tarfile.open(archive_path, 'r:gz') as archive:
            for member in archive:
                if member.isfile() and selected(member.name):
                    archive.extract(member, stage, filter='data')
        manifest = json.loads((stage / 'package/package.json').read_text(encoding='utf-8-sig'))
        if (manifest['name'], manifest['version']) != (name, version):
            raise RuntimeError(f'SDK manifest mismatch: {name}')
        (stage / record.name).write_text(json.dumps(receipt(stage, name), indent=2) + '\n', encoding='utf-8')
        stage.rename(target)
        archive_path.unlink()
        print(f'Verified official source: {name} {version}', flush=True)
    return target / 'package'


def source_files(source):
    files = []
    for file in sorted(source.rglob('*.cs')):
        if any(part.endswith('~') or part.startswith('.') for part in file.relative_to(source).parts):
            continue
        owner = file.parent
        while owner != source and not list(owner.glob('*.asmdef')):
            owner = owner.parent
        if owner == source:
            files.append(file)
    if not files:
        raise RuntimeError(f'No managed sources in {source}')
    return files


def preflight(editor):
    expected = next(line.split(':', 1)[1].strip() for line in (ROOT / 'clients/unity/ProjectSettings/ProjectVersion.txt').read_text().splitlines() if line.startswith('m_EditorVersion:'))
    environment = dict(os.environ, VR_COMMAND_SDK_EDITOR_BINARY=str(editor / 'Unity.exe'))
    version = subprocess.check_output(['powershell', '-NoProfile', '-Command',
        '[Diagnostics.FileVersionInfo]::GetVersionInfo($env:VR_COMMAND_SDK_EDITOR_BINARY).ProductVersion'], env=environment, text=True).strip()
    if version.split('_')[0] != expected:
        raise RuntimeError(f'Editor version mismatch: expected {expected}, actual {version}')
    builtin = editor / 'Data/Resources/PackageManager/BuiltInPackages'
    dependencies = json.loads((ROOT / 'clients/unity/Packages/manifest.json').read_text())['dependencies']
    for name, requested in dependencies.items():
        manifest = builtin / name / 'package.json'
        if manifest.exists():
            actual = json.loads(manifest.read_text(encoding='utf-8-sig'))['version']
            if requested != actual:
                raise RuntimeError(f'Built-in package version mismatch: {name} project={requested} Editor={actual}')
    for name in ['com.unity.inputsystem', 'com.unity.netcode.gameobjects']:
        if dependencies[name] != PINS[name][0]:
            raise RuntimeError(f'Diagnostic SDK pin does not match project: {name}')
    core = json.loads((builtin / 'com.unity.render-pipelines.core/package.json').read_text())['dependencies']
    if core['com.unity.collections'] != PINS['com.unity.collections'][0]:
        raise RuntimeError('Diagnostic Collections pin does not match the installed SRP Core dependency')
    return version, builtin


def generate(editor, builtin, packages, profile):
    projects = WORK / 'projects' / profile
    projects.mkdir(parents=True, exist_ok=True)
    engine = sorted((editor / 'Data/Managed/UnityEngine').glob('*.dll'))
    if not engine:
        raise RuntimeError('Actual Unity engine reference DLLs are missing')
    engine.append(packages['com.unity.collections'] / 'Unity.Collections.LowLevel.ILSupport/Unity.Collections.LowLevel.ILSupport.dll')
    defines = [f'UNITY_{year}_{minor}_OR_NEWER' for year in range(2017, 2024) for minor in range(1, 5 if year < 2020 else 4)]
    defines += [f'UNITY_6000_{minor}_OR_NEWER' for minor in range(4)]
    defines += [f'UNITY_5_{minor}_OR_NEWER' for minor in range(3, 7)]
    defines += ['UNITY_6000', 'UNITY_6000_3', 'UNITY_64', 'DEVELOPMENT_BUILD', 'ENABLE_INPUT_SYSTEM', 'ENABLE_UNITY_COLLECTIONS_CHECKS', 'UNITY_ASSERTIONS']
    defines += ['UNITY_ANDROID', 'ENABLE_IL2CPP'] if profile == 'android' else ['UNITY_STANDALONE', 'UNITY_STANDALONE_WIN', 'ENABLE_MONO']
    specs = {
        'Unity.Burst': (packages['com.unity.burst'] / 'Runtime', [], [], [packages['com.unity.burst'] / 'Unity.Burst.Unsafe.dll']),
        'Unity.Mathematics': (packages['com.unity.mathematics'] / 'Unity.Mathematics', [], [], []),
        'Unity.Collections': (packages['com.unity.collections'] / 'Unity.Collections', ['Unity.Burst', 'Unity.Mathematics'], ['UNITY_2022_2_14F1_OR_NEWER', 'UNITY_2022_2_16F1_OR_NEWER'], []),
        'Unity.Networking.Transport': (packages['com.unity.transport'] / 'Runtime', ['Unity.Burst', 'Unity.Mathematics', 'Unity.Collections'], ['HOSTNAME_RESOLUTION_AVAILABLE', 'DONT_FRAGMENT_BIT_AVAILABLE'], []),
        'Unity.Netcode.Runtime': (packages['com.unity.netcode.gameobjects'] / 'Runtime', ['Unity.Burst', 'Unity.Mathematics', 'Unity.Collections', 'Unity.Networking.Transport'], ['UNITY_DEDICATED_SERVER_ARGUMENTS_PRESENT', 'COM_UNITY_MODULES_PHYSICS', 'HOSTNAME_RESOLUTION_AVAILABLE', 'UNITY_6000_3_0A6_OR_HIGHER', 'SCENE_MANAGEMENT_SCENE_HANDLE_AVAILABLE'], []),
        'UnityEngine.UI': (builtin / 'com.unity.ugui/Runtime/UGUI', [], ['PACKAGE_PHYSICS', 'PACKAGE_INPUTSYSTEM'], []),
        'Unity.InputSystem': (packages['com.unity.inputsystem'] / 'InputSystem', ['UnityEngine.UI'], ['UNITY_INPUT_SYSTEM_ENABLE_XR', 'UNITY_INPUT_SYSTEM_ENABLE_PHYSICS', 'UNITY_INPUT_SYSTEM_ENABLE_UI', 'UNITY_INPUT_SYSTEM_PLATFORM_SCROLL_DELTA', 'UNITY_INPUT_SYSTEM_INPUT_MODULE_SCROLL_DELTA', 'UNITY_INPUT_SYSTEM_INPUT_MODULE_NAVIGATION_DEVICE_TYPE', 'UNITY_INPUT_SYSTEM_SENDPOINTERHOVERTOPARENT', 'UNITY_INPUT_SYSTEM_PLATFORM_POLLING_FREQUENCY'], []),
        'VrCommand.Runtime': (ROOT / 'clients/unity/Assets/VrCommand/Runtime', ['Unity.Netcode.Runtime', 'Unity.Networking.Transport', 'Unity.InputSystem', 'Unity.Collections', 'UnityEngine.UI'], [], []),
        'VrCommand.Tests': (ROOT / 'clients/unity/Assets/VrCommand/Tests/Editor', ['VrCommand.Runtime', 'Unity.Netcode.Runtime', 'Unity.Collections'], [], [builtin / 'com.unity.ext.nunit/net40/unity-custom/nunit.framework.dll']),
    }
    inventory = {}
    for name, (source, references, extra, libraries) in specs.items():
        files = source_files(source)
        xml = ['<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>netstandard2.1</TargetFramework><LangVersion>9.0</LangVersion><Nullable>disable</Nullable><ImplicitUsings>disable</ImplicitUsings><EnableDefaultCompileItems>false</EnableDefaultCompileItems><RestorePackagesWithLockFile>false</RestorePackagesWithLockFile><AllowUnsafeBlocks>true</AllowUnsafeBlocks><TreatWarningsAsErrors>false</TreatWarningsAsErrors><GenerateAssemblyInfo>false</GenerateAssemblyInfo>',
               f'<AssemblyName>{name}</AssemblyName><DefineConstants>{";".join(defines + extra)}</DefineConstants></PropertyGroup><ItemGroup>']
        xml += [f'<Compile Include="{escape(str(file))}" />' for file in files]
        for library in engine + libraries:
            if not library.is_file():
                raise RuntimeError(f'Actual SDK DLL is missing: {library}')
            xml.append(f'<Reference Include="{library.stem}"><HintPath>{escape(str(library))}</HintPath><Private>false</Private></Reference>')
        xml += [f'<ProjectReference Include="{reference}.csproj" />' for reference in references]
        if name in {'VrCommand.Runtime', 'VrCommand.Tests'}:
            xml.append(f'<ProjectReference Include="{escape(str(ROOT / "src/VrCommand.Simulation/VrCommand.Simulation.csproj"))}" />')
        xml.append('</ItemGroup></Project>')
        (projects / (name + '.csproj')).write_text('\n'.join(xml), encoding='utf-8')
        inventory[name] = {'sources': {str(file): digest(file) for file in files}, 'defines': defines + extra,
                           'libraries': {str(file): digest(file) for file in engine + libraries}}
    return projects, inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--editor-directory', type=Path, default=Path('F:/Tools/UnityEditors/6000.3.27f1/Editor'))
    parser.add_argument('--profile', choices=['android', 'windows', 'both'], default='both')
    parser.add_argument('--offline', action='store_true', help='Refuse SDK downloads; validate existing source receipts')
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    report = {'startedAtUtc': datetime.now(timezone.utc).isoformat(), 'checkerSha256': digest(Path(__file__)),
              'scope': LIMITATION, 'pins': PINS, 'profiles': {}, 'complete': False}
    (WORK / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    version, builtin = preflight(args.editor_directory)
    report['editorVersion'] = version
    packages = {name: package(name, args.offline) for name in PINS}
    for profile in ['android', 'windows'] if args.profile == 'both' else [args.profile]:
        projects, inventory = generate(args.editor_directory, builtin, packages, profile)
        log = WORK / (profile + '.log')
        with log.open('w', encoding='utf-8') as output:
            result = subprocess.run(['dotnet', 'build', str(projects / 'VrCommand.Tests.csproj'), '--configuration', 'Release',
                                     '--artifacts-path', str(WORK / ('build-' + profile))], stdout=output, stderr=subprocess.STDOUT)
        report['profiles'][profile] = {'exitCode': result.returncode, 'log': str(log), 'assemblies': inventory}
        (WORK / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        if result.returncode:
            raise RuntimeError(f'Managed SDK binding failed for {profile}; see {log}')
        runtime_count = len(inventory['VrCommand.Runtime']['sources'])
        test_count = len(inventory['VrCommand.Tests']['sources'])
        print(f'{profile}: {runtime_count} player adapter sources and {test_count} NUnit source files bind to real Unity/NGO/Input/Transport APIs. Log: {log}', flush=True)
    report['complete'] = True
    report['finishedAtUtc'] = datetime.now(timezone.utc).isoformat()
    (WORK / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(LIMITATION)


if __name__ == '__main__':
    main()
