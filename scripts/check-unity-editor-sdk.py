"""Bind ProjectBuilder to real Editor/OpenXR APIs; never execute Editor code."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('vr_sdk', ROOT / 'scripts/check-unity-sdk.py')
sdk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdk)
XR_PINS = {
    'com.unity.xr.openxr': ('1.19.0', '55edf9b26dd2bdec9d513fbcb0b9e4a9e5d790e9'),
    'com.unity.xr.management': ('4.6.1', 'df145a5bc89e37453667848cc4c11a49a7246aa3'),
    'com.unity.xr.core-utils': ('2.3.0', 'f4116c6290594e2609ede158fccdad4a54a17081'),
    'com.unity.xr.legacyinputhelpers': ('2.1.11', 'a3936666e06871a5fd0461a69a4d99efb31a21c1'),
}
META = 'Unity.XR.OpenXR.Features.MetaQuestSupport'
LIMITATION = ('ProjectBuilder managed API binding only. No Editor execution, asset/scene generation, '
              'UPM resolution, URP rendering validation, full Unity compilation, ILPP, NUnit execution, '
              'native plugin execution, IL2CPP, APK or headset validation. '
              'URP-specific validation branches are outside this diagnostic graph.')


def save_report(report):
    (sdk.WORK / 'editor-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


def generate(editor, builtin, packages, player_report):
    projects = sdk.WORK / 'projects/editor'
    projects.mkdir(parents=True, exist_ok=True)
    player = player_report['profiles']['windows']['assemblies']
    defines = player['VrCommand.Runtime']['defines'] + ['UNITY_EDITOR', 'UNITY_EDITOR_WIN']
    ui = builtin / 'com.unity.ugui'
    def source(package, folder):
        return packages[package] / folder
    asmdef = ROOT / 'clients/unity/Assets/VrCommand/Editor/VrCommand.Editor.asmdef'
    declared = json.loads(asmdef.read_text(encoding='utf-8'))['references']
    specs = {
        'Unity.InternalAPIEngineBridge.004': (ui / 'Runtime/InternalBridge', [], []),
        'UnityEngine.UI': (ui / 'Runtime/UGUI', ['Unity.InternalAPIEngineBridge.004'], ['PACKAGE_PHYSICS', 'PACKAGE_INPUTSYSTEM']),
        'UnityEditor.UI': (ui / 'Editor/UGUI', ['UnityEngine.UI'], ['PACKAGE_PHYSICS']),
        'Unity.InputSystem': (sdk.WORK / 'sources/com.unity.inputsystem/1.17.0/package/InputSystem', ['UnityEngine.UI', 'UnityEditor.UI'],
                              [d for d in player['Unity.InputSystem']['defines'] if d not in player['VrCommand.Runtime']['defines']]),
        'UnityEngine.SpatialTracking': (source('com.unity.xr.legacyinputhelpers', 'Runtime/TrackedPoseDriver'), [], []),
        'Unity.XR.CoreUtils': (source('com.unity.xr.core-utils', 'Runtime'), ['Unity.InputSystem', 'UnityEngine.SpatialTracking', 'UnityEngine.UI'],
                              ['INCLUDE_PHYSICS_MODULE', 'INCLUDE_UGUI', 'INCLUDE_INPUT_SYSTEM', 'INCLUDE_LEGACY_INPUT_HELPERS', 'HAS_SET_LOCAL_POSITION_AND_ROTATION', 'HAS_GET_POSITION_AND_ROTATION']),
        'Unity.XR.CoreUtils.Editor': (source('com.unity.xr.core-utils', 'Editor'), ['Unity.XR.CoreUtils', 'Unity.InputSystem'], ['INCLUDE_INPUT_SYSTEM', 'INPUT_SYSTEM_1_1_OR_NEWER']),
        'Unity.XR.Management': (source('com.unity.xr.management', 'Runtime'), [], []),
        'Unity.XR.Management.Editor': (source('com.unity.xr.management', 'Editor'), ['Unity.XR.Management', 'Unity.XR.CoreUtils.Editor', 'Unity.InputSystem'], ['INPUT_SYSTEM_1_4_OR_NEWER', 'UNITY_XR_VISIONOS_SUPPORTED']),
        'Unity.XR.OpenXR': (source('com.unity.xr.openxr', 'Runtime'), ['Unity.XR.Management', 'Unity.XR.Management.Editor', 'Unity.InputSystem', 'Unity.XR.CoreUtils', 'UnityEngine.SpatialTracking'], ['INPUT_SYSTEM_POSE_VALID', 'INPUT_SYSTEM_BINDING_VALIDATOR', 'SPACEWARP_RIGHT_HAND_NDC_SUPPORTED']),
        'Unity.XR.OpenXR.Editor': (source('com.unity.xr.openxr', 'Editor'), ['Unity.XR.Management', 'Unity.XR.Management.Editor', 'Unity.XR.OpenXR', 'Unity.InputSystem', 'Unity.XR.CoreUtils.Editor'], ['XR_MGMT_3_2_0_OR_NEWER', 'XR_MGMT_4_4_0_OR_NEWER']),
        META: (source('com.unity.xr.openxr', 'Runtime/MetaQuest'), ['Unity.XR.OpenXR', 'Unity.InputSystem'], []),
        'VrCommand.Editor': (ROOT / 'clients/unity/Assets/VrCommand/Editor', declared, []),
    }
    engine = sorted((editor / 'Data/Managed/UnityEngine').glob('*.dll'))
    engine += [editor / 'Data/PlaybackEngines/AndroidPlayer' / name for name in
               ['UnityEditor.Android.Extensions.dll', 'Unity.Android.Gradle.dll', 'Unity.Android.Types.dll']]
    engine += [editor / 'Data/NetStandard/EditorExtensions/Microsoft.Win32.Registry.dll']
    existing = {p.stem: p for p in (sdk.WORK / 'build-windows/bin').glob('*/release/*.dll') if p.stem == p.parent.parent.name}
    inventory = {}
    for name, (folder, references, extra) in specs.items():
        files = sdk.source_files(folder)
        xml = ['<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>netstandard2.1</TargetFramework><LangVersion>9.0</LangVersion><Nullable>disable</Nullable><ImplicitUsings>disable</ImplicitUsings><EnableDefaultCompileItems>false</EnableDefaultCompileItems><RestorePackagesWithLockFile>false</RestorePackagesWithLockFile><AllowUnsafeBlocks>true</AllowUnsafeBlocks><TreatWarningsAsErrors>false</TreatWarningsAsErrors><GenerateAssemblyInfo>false</GenerateAssemblyInfo><DisableTransitiveProjectReferences>true</DisableTransitiveProjectReferences>',
               f'<AssemblyName>{name}</AssemblyName><DefineConstants>{";".join(defines + extra)}</DefineConstants></PropertyGroup><ItemGroup>']
        xml += [f'<Compile Include="{escape(str(file))}" />' for file in files]
        libraries = engine[:]
        for reference in references:
            if reference in specs:
                xml.append(f'<ProjectReference Include="{reference}.csproj" />')
            else:
                if reference not in existing:
                    raise RuntimeError(f'Unresolved declared SDK reference: {reference}')
                libraries.append(existing[reference])
        for library in libraries:
            if not library.is_file():
                raise RuntimeError(f'Actual Editor SDK DLL is missing: {library}')
            xml.append(f'<Reference Include="{library.stem}"><HintPath>{escape(str(library))}</HintPath><Private>false</Private></Reference>')
        xml.append('</ItemGroup></Project>')
        (projects / (name + '.csproj')).write_text('\n'.join(xml), encoding='utf-8')
        inventory[name] = {'sources': {str(file): sdk.digest(file) for file in files}, 'defines': defines + extra,
                           'references': references, 'libraries': {str(file): sdk.digest(file) for file in libraries}}
    return projects, inventory, asmdef


def build(project, log):
    with log.open('w', encoding='utf-8') as output:
        return subprocess.run(['dotnet', 'build', str(project), '--configuration', 'Release',
                               '--artifacts-path', str(sdk.WORK / 'build-editor')], stdout=output, stderr=subprocess.STDOUT).returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--editor-directory', type=Path, default=Path('F:/Tools/UnityEditors/6000.3.27f1/Editor'))
    parser.add_argument('--offline', action='store_true', help='Refuse SDK downloads')
    parser.add_argument('--verify-missing-reference', action='store_true', help='Also prove that removing the Meta Quest direct reference fails compilation')
    args = parser.parse_args()
    sdk.WORK.mkdir(parents=True, exist_ok=True)
    report = {'startedAtUtc': datetime.now(timezone.utc).isoformat(), 'checkerSha256': sdk.digest(Path(__file__)),
              'scope': LIMITATION, 'complete': False, 'excludedPackageDefines': ['UNITY_RENDER_PIPELINES_UNIVERSAL', 'ENABLE_RENDER_GRAPH_COMPATIBILITY_MODE_SUPPORTED']}
    save_report(report)
    version, builtin = sdk.preflight(args.editor_directory)
    manifest = json.loads((ROOT / 'clients/unity/Packages/manifest.json').read_text())['dependencies']
    for name in ['com.unity.xr.openxr', 'com.unity.xr.management']:
        if manifest[name] != XR_PINS[name][0]:
            raise RuntimeError(f'Diagnostic XR pin does not match project: {name}')
    command = [sys.executable, str(ROOT / 'scripts/check-unity-sdk.py'), '--profile', 'windows', '--editor-directory', str(args.editor_directory)]
    if args.offline:
        command.append('--offline')
    baseline_log = sdk.WORK / 'editor-player-baseline.log'
    with baseline_log.open('w', encoding='utf-8') as output:
        result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'Windows player SDK baseline failed; see {baseline_log}')
    player_snapshot = sdk.WORK / 'editor-player-report.json'
    player_snapshot.write_bytes((sdk.WORK / 'report.json').read_bytes())
    player_report = json.loads(player_snapshot.read_text(encoding='utf-8'))
    if not player_report['complete'] or player_report['profiles']['windows']['exitCode'] != 0:
        raise RuntimeError('Missing successful player SDK report')
    sdk.PINS.update(XR_PINS)
    sdk.SOURCE_FOLDERS.add('Editor')
    packages = {name: sdk.package(name, args.offline) for name in XR_PINS}
    projects, inventory, asmdef = generate(args.editor_directory, builtin, packages, player_report)
    log = sdk.WORK / 'editor.log'
    code = build(projects / 'VrCommand.Editor.csproj', log)
    report.update(editorVersion=version, playerReportSha256=sdk.digest(player_snapshot), xrPins=XR_PINS,
                  asmdefSha256=sdk.digest(asmdef), assemblies=inventory, exitCode=code, log=str(log))
    save_report(report)
    if code:
        raise RuntimeError(f'ProjectBuilder SDK binding failed; see {log}')
    if args.verify_missing_reference:
        project_text = (projects / 'VrCommand.Editor.csproj').read_text(encoding='utf-8')
        reference = f'<ProjectReference Include="{META}.csproj" />'
        if project_text.count(reference) != 1:
            raise RuntimeError('The direct Meta Quest reference is not declared exactly once')
        probe = projects / 'VrCommand.Editor.MissingReference.csproj'
        probe.write_text(project_text.replace(reference, ''), encoding='utf-8')
        probe_log = sdk.WORK / 'editor-missing-reference.log'
        probe_code = build(probe, probe_log)
        diagnostics = probe_log.read_text(encoding='utf-8')
        expected = probe_code != 0 and 'error CS0234' in diagnostics and 'MetaQuestSupport' in diagnostics and 'ProjectBuilder.cs' in diagnostics
        report['missingReferenceProbe'] = {'exitCode': probe_code, 'expectedRejection': expected, 'log': str(probe_log)}
        save_report(report)
        if not expected:
            raise RuntimeError(f'Missing-reference regression probe did not fail as expected; see {probe_log}')
    report.update(complete=True, finishedAtUtc=datetime.now(timezone.utc).isoformat())
    save_report(report)
    count = sum(len(assembly['sources']) for assembly in inventory.values())
    print(f'ProjectBuilder binds to actual Editor/OpenXR APIs: {count} managed sources, {len(inventory)} assemblies. Log: {log}')
    print(LIMITATION)


if __name__ == '__main__':
    main()
