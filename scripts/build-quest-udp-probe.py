"""Build and verify the Quest UDP diagnostic APK with an installed Android SDK and JDK."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile


SOURCE = Path(__file__).resolve().parents[1] / 'tools' / 'QuestUdpProbe'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', required=True, type=Path)
    parser.add_argument('--jdk', required=True, type=Path)
    parser.add_argument('--keystore', required=True, type=Path, help='Dedicated diagnostic debug keystore with alias androiddebugkey')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir() or output.suffix != '.apk':
        parser.error('Choose a new .apk in an existing output directory.')
    tools = args.sdk / 'build-tools' / '36.0.0'
    platform = args.sdk / 'platforms' / 'android-35' / 'android.jar'
    suffix = '.exe' if os.name == 'nt' else ''
    java = args.jdk / 'bin' / ('java' + suffix)
    javac = args.jdk / 'bin' / ('javac' + suffix)
    aapt = tools / ('aapt2' + suffix)
    zipalign = tools / ('zipalign' + suffix)
    d8 = tools / 'lib' / 'd8.jar'
    signer = tools / 'lib' / 'apksigner.jar'
    for path in (java, javac, aapt, zipalign, d8, signer, platform, args.keystore):
        if not path.is_file():
            parser.error('The SDK, JDK or diagnostic keystore is missing a required file.')

    def run(*command):
        return subprocess.run(list(map(str, command)), check=True, capture_output=True, text=True, timeout=90).stdout

    with tempfile.TemporaryDirectory(prefix='quest-udp-probe-') as directory:
        work = Path(directory)
        classes = work / 'classes'
        dex = work / 'dex'
        classes.mkdir()
        dex.mkdir()
        run(javac, '--release', '8', '-classpath', platform, '-d', classes,
            SOURCE / 'Probe.java', SOURCE / 'ProbeInstrumentation.java')
        run(java, '-cp', d8, 'com.android.tools.r8.D8', '--min-api', '32', '--lib', platform,
            '--output', dex, *sorted(classes.rglob('*.class')))
        unsigned = work / 'unsigned.apk'
        aligned = work / 'aligned.apk'
        signed = work / 'signed.apk'
        run(aapt, 'link', '--manifest', SOURCE / 'AndroidManifest.xml', '-I', platform, '-o', unsigned)
        with zipfile.ZipFile(unsigned, 'a', compression=zipfile.ZIP_STORED) as archive:
            archive.write(dex / 'classes.dex', 'classes.dex')
        run(zipalign, '-f', '4', unsigned, aligned)
        run(java, '-jar', signer, 'sign', '--ks', args.keystore, '--ks-key-alias', 'androiddebugkey',
            '--ks-pass', 'pass:android', '--key-pass', 'pass:android', '--v1-signing-enabled', 'false',
            '--v2-signing-enabled', 'true', '--v3-signing-enabled', 'false', '--v4-signing-enabled', 'false', '--out', signed, aligned)
        run(zipalign, '-c', '4', signed)
        signing = run(java, '-jar', signer, 'verify', '--verbose', '--print-certs', signed)
        manifest = run(aapt, 'dump', 'badging', signed)
        if ("name='com.vrcommand.udpprobe'" not in manifest or "minSdkVersion:'32'" not in manifest
                or "targetSdkVersion:'35'" not in manifest):
            raise RuntimeError('Unexpected APK identity or SDK levels.')
        if 'v2 scheme (APK Signature Scheme v2): true' not in signing:
            raise RuntimeError('The APK v2 signature could not be verified.\n' + signing)
        with signed.open('rb') as source, output.open('xb') as destination:
            shutil.copyfileobj(source, destination)
    print(json.dumps({'apk': str(output), 'bytes': output.stat().st_size,
                      'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'signing': 'APK Signature Scheme v2 verified'}))


if __name__ == '__main__':
    main()
