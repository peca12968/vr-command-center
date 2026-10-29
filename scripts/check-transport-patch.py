"""Materialize / verify the narrowly patched official Unity Transport source.

The embedded package replaces UPM's registry copy, never Library/PackageCache.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'clients/unity/Packages/com.unity.transport'
URL = 'https://download.packages.unity.com/com.unity.transport/-/com.unity.transport-2.7.4.tgz'
SHA1 = '98ef8bfec34d7eea791603fc1e45ce86c3484180'
RECEIPT_SHA256 = 'd179e4697e00e838b8634979091ae06a45d8d0052dbdf53f39e35c5f3470ea77'
PATCH_FILE = 'Runtime/UDPNetworkInterface.cs'
BEFORE = b'''                        if (results[i].status == Binding.Baselib_RegisteredNetwork_CompletionStatus.Failed)
                        {
                            failedCount++;
                            continue;
                        }'''
AFTER = BEFORE.replace(b'                            failedCount++;', b'                            ReceiveQueue.ReleaseBuffer(bufferIndex);\n                            failedCount++;')


def digest(value): return hashlib.sha256(value).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--materialize', action='store_true', help='Create the embedded package once from the pinned official archive')
    args = parser.parse_args()
    if args.materialize:
        if PACKAGE.exists(): raise RuntimeError('Embedded package already exists; refusing to overwrite local work')
        archive = ROOT / 'artifacts/unity-transport-2.7.4.tgz'
        if not archive.exists():
            archive.parent.mkdir(parents=True, exist_ok=True)
            archive.write_bytes(urllib.request.urlopen(URL, timeout=60).read())
        data = archive.read_bytes()
        if hashlib.sha1(data).hexdigest() != SHA1: raise RuntimeError('Official transport archive hash mismatch')
        source, final = {}, {}
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            for member in tar.getmembers():
                parts = PurePosixPath(member.name).parts
                if not parts or parts[0] != 'package' or '..' in parts or member.issym() or member.islnk(): raise RuntimeError('Unsafe package archive path')
                if not member.isfile(): continue
                relative = PurePosixPath(*parts[1:]).as_posix()
                if relative in ['.signature', '.attestation.p7m']: continue
                content = tar.extractfile(member).read(); source[relative] = digest(content)
                if relative == PATCH_FILE:
                    # Preserve the original line endings, replacing exactly this receive branch.
                    lf = content.replace(b'\r\n', b'\n')
                    if lf.count(BEFORE) != 1: raise RuntimeError('Expected upstream failure branch was not found exactly once')
                    patched = lf.replace(BEFORE, AFTER)
                    content = patched.replace(b'\n', b'\r\n') if b'\r\n' in content else patched
                destination = (PACKAGE / relative).resolve()
                if not destination.is_relative_to(PACKAGE.resolve()): raise RuntimeError('Archive destination escaped the embedded package')
                destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(content)
                final[relative] = digest(content)
        receipt = {'schemaVersion': 1, 'upstreamVersion': '2.7.4', 'archiveUrl': URL, 'archiveSha1': SHA1, 'archiveSha256': digest(data),
                   'patch': {'file': PATCH_FILE, 'purpose': 'Return failed receive-completion buffers to the receive pool before continuing',
                             'reference': 'https://discussions.unity.com/t/unity-transport-6-6-0-udp-host-stops-receiving-after-abrupt-client-disconnect-on-windows/1736023'},
                   'omitted': ['.signature', '.attestation.p7m'], 'originalFilesSha256': source, 'embeddedFilesSha256': final}
        (PACKAGE / 'UPSTREAM.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8', newline='\r\n')
    receipt_bytes = (PACKAGE / 'UPSTREAM.json').read_bytes()
    if digest(receipt_bytes) != RECEIPT_SHA256: raise RuntimeError('Pinned official-source / exact-patch receipt changed')
    receipt = json.loads(receipt_bytes)
    expected = receipt['embeddedFilesSha256']
    paths = {path.relative_to(PACKAGE).as_posix(): path for path in PACKAGE.rglob('*')
             if path.is_file() and path.relative_to(PACKAGE).as_posix() not in ['UPSTREAM.json', 'UPSTREAM.json.meta']}
    if paths.keys() != expected.keys(): raise RuntimeError('Embedded source inventory changed')
    for name, path in paths.items():
        if digest(path.read_bytes()) != expected[name]: raise RuntimeError('Embedded source hash changed: ' + name)
    changed = [name for name in expected if expected[name] != receipt['originalFilesSha256'][name]]
    if changed != [PATCH_FILE]: raise RuntimeError('Transport fork must change only the approved receive failure branch')
    print(f'Verified {len(expected)} official embedded files; exactly one scoped source patch; license and notices retained.')


if __name__ == '__main__': main()
