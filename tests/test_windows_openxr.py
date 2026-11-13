import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which('pwsh')


@unittest.skipUnless(os.name == 'nt' and POWERSHELL, 'Requires Windows and PowerShell')
class WindowsOpenXrTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manifest = self.root / 'openxr.json'

    def inspect(self, manifest, status, *, source='environment'):
        result = subprocess.run([POWERSHELL, '-NoProfile', '-NonInteractive', '-File',
                                 str(ROOT/'scripts/check-windows-openxr.ps1')],
                                env={**os.environ, 'XR_RUNTIME_JSON': str(manifest)},
                                capture_output=True, encoding='utf-8', timeout=10)
        self.assertEqual('', result.stderr)
        complete = status == 'x64-runtime-files-found'
        self.assertEqual(0 if complete else 1, result.returncode)
        self.assertEqual({'version': 1, 'scope': 'windows-openxr-runtime-files', 'complete': complete,
                          'source': source, 'status': status}, json.loads(result.stdout))
        self.assertNotIn(str(self.root), result.stdout)

    def write_manifest(self, library):
        self.manifest.write_text(json.dumps({'file_format_version': '1.0.0', 'runtime': {'library_path': library}}), encoding='utf-8-sig')

    def test_selects_explicit_manifest_without_registry_fallback(self):
        self.inspect(self.manifest, 'manifest-missing')
        self.inspect('relative.json', 'manifest-path-invalid')
        self.inspect(r'\\unreachable\runtime\openxr.json', 'manifest-path-invalid')

    def test_reports_bad_manifest_and_unresolved_library(self):
        self.manifest.write_bytes(b'{')
        self.inspect(self.manifest, 'manifest-invalid')
        self.manifest.write_bytes(b' ' * 65537)
        self.inspect(self.manifest, 'manifest-invalid')
        for library, status in [('runtime.dll', 'library-search-required'), (r'.\missing.dll', 'library-missing'),
                                (r'\\unreachable\runtime\runtime.dll', 'library-path-invalid')]:
            self.write_manifest(library)
            self.inspect(self.manifest, status)

    def test_x64_dll_header_and_manifest_relative_path(self):
        runtime = self.root/'runtime files'
        runtime.mkdir()
        library = runtime/'runtime.dll'
        self.write_manifest(r'.\runtime files\runtime.dll')
        header = bytearray(256)
        struct.pack_into('<H', header, 0, 0x5A4D)
        struct.pack_into('<I', header, 60, 64)
        struct.pack_into('<IH', header, 64, 0x4550, 0x8664)
        struct.pack_into('<HHH', header, 84, 112, 0x2000, 0x20B)
        library.write_bytes(header)
        self.inspect(self.manifest, 'x64-runtime-files-found')
        self.write_manifest(str(library))
        self.inspect(self.manifest, 'x64-runtime-files-found')
        struct.pack_into('<H', header, 68, 0x14C)
        library.write_bytes(header)
        self.inspect(self.manifest, 'library-not-x64-dll')
        struct.pack_into('<H', header, 68, 0x8664)
        struct.pack_into('<H', header, 86, 0)
        library.write_bytes(header)
        self.inspect(self.manifest, 'library-not-x64-dll')
        library.write_bytes(header[:70])
        self.inspect(self.manifest, 'library-not-x64-dll')
