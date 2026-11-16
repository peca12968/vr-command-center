"""Actual concurrent observation reads and Windows writer-lease copy fencing."""
import ctypes
from ctypes import wintypes
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import call, patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('artifact_venue',ROOT/'scripts/start-desktop-venue.py')
venue=importlib.util.module_from_spec(spec);spec.loader.exec_module(venue)


class ArtifactTests(unittest.TestCase):
    def directory(self):return tempfile.TemporaryDirectory(prefix='vr-artifacts-')
    def guard(self,path):
        self.assertEqual(path.parent,Path(tempfile.gettempdir()).resolve());self.assertTrue(path.name.startswith('vr-artifacts-'))

    def test_packaged_api_uses_the_approved_program_and_its_original_assembly(self):
        with self.directory() as temporary:
            root = Path(temporary).resolve()
            exe = root / 'VrCommand.Api.exe'
            dll = root / 'VrCommand.Api.dll'
            exe.touch()
            args = SimpleNamespace(api_exe=exe)
            with self.assertRaisesRegex(ValueError, 'alongside VrCommand.Api.dll'):
                venue.api_command(args)
            dll.touch()
            self.assertEqual(([str(exe)], root, dll), venue.api_command(args))

    @unittest.skipUnless(os.name == 'nt', 'Windows launch preflight')
    def test_blocked_relay_checks_the_actual_python_process_and_stops_validation(self):
        firewall_spec = importlib.util.spec_from_file_location('windows_firewall', ROOT / 'scripts/windows_firewall.py')
        windows_firewall = importlib.util.module_from_spec(firewall_spec)
        firewall_spec.loader.exec_module(windows_firewall)

        def check(program):
            if program == sys.executable:
                raise windows_firewall.WindowsFirewallLaunchError('Blocked relay')

        args = SimpleNamespace(player_exe=Path(sys.executable))
        with (patch.dict(sys.modules, windows_firewall=windows_firewall),
              patch.object(venue, 'api_command'), patch.object(venue.subprocess, 'run') as run,
              patch.object(windows_firewall, 'require_silent_windows_launch', side_effect=check) as verify):
            with self.assertRaisesRegex(windows_firewall.WindowsFirewallLaunchError, 'Blocked relay'):
                venue.verify_player(args, python_listener=True)
            self.assertEqual(verify.call_args_list, [call(args.player_exe), call(sys.executable)])
            run.assert_not_called()

    def test_concurrent_reader_sees_only_complete_json_and_no_temporary_files_remain(self):
        with self.directory() as temporary:
            root=Path(temporary).resolve();self.guard(root);path=root/'status.json';venue.atomic_json(path,{'sequence':0})
            stop=threading.Event();started=threading.Event();errors=[];seen=[]
            def reader():
                while not stop.is_set():
                    try:seen.append(venue.read_json(path)['sequence']);started.set()
                    except Exception as error:errors.append(type(error).__name__)
            child=threading.Thread(target=reader);child.start()
            try:
                self.assertTrue(started.wait(5))
                for sequence in range(1,31):venue.atomic_json(path,{'sequence':sequence,'padding':'x'*8192})
            finally:stop.set();child.join(timeout=5)
            self.assertFalse(child.is_alive());self.assertEqual(errors,[]);self.assertTrue(seen)
            self.assertEqual(json.loads(path.read_text())['sequence'],30);self.assertEqual([p.name for p in root.iterdir()],['status.json'])

    def test_snapshot_never_overwrites_existing_forensic_copy_or_recurses_into_source(self):
        with self.directory() as temporary:
            root=Path(temporary).resolve();self.guard(root);source=root/'source';source.mkdir();(source/'data.bin').write_bytes(b'original')
            destination=root/'snapshot';destination.mkdir();(destination/'witness').write_text('keep')
            with self.assertRaises(FileExistsError):venue.snapshot_runtime(source,destination)
            self.assertEqual((destination/'witness').read_text(),'keep')
            with self.assertRaises(ValueError):venue.snapshot_runtime(source,source/'nested')

    def test_persistently_malformed_json_is_not_hidden_by_sharing_retry(self):
        with self.directory() as temporary:
            root=Path(temporary).resolve();self.guard(root);path=root/'corrupt.json';path.write_text('{broken')
            with self.assertRaises(json.JSONDecodeError):venue.read_json(path)

    def test_venue_artifact_path_cannot_escape_its_owned_run_directory(self):
        with self.directory() as temporary:
            root=Path(temporary).resolve();self.guard(root);owner=object.__new__(venue.Venue);owner.directory=root
            with self.assertRaises(ValueError):owner.save('../outside.json',{'invalid':True})
            self.assertEqual(list(root.iterdir()),[])

    @unittest.skipUnless(os.name=='nt','Actual Windows exclusive file sharing test')
    def test_snapshot_waits_for_an_owned_exclusive_writer_lease_before_first_copy(self):
        with self.directory() as temporary:
            root=Path(temporary).resolve();self.guard(root);source=root/'source';(source/'missions').mkdir(parents=True)
            lease=source/'missions/.library-writer.lock';lease.write_bytes(b'');(source/'payload.bin').write_bytes(b'closed data')
            api=ctypes.WinDLL('kernel32',use_last_error=True)
            api.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
            api.CreateFileW.restype=wintypes.HANDLE;api.CloseHandle.argtypes=[wintypes.HANDLE];api.CloseHandle.restype=wintypes.BOOL
            handle=api.CreateFileW(str(lease),0x80000000,0,None,3,0,None)
            self.assertNotIn(handle,(None,ctypes.c_void_p(-1).value))
            def release():time.sleep(.2);api.CloseHandle(handle)
            writer=threading.Thread(target=release);writer.start();started=time.monotonic()
            try:venue.snapshot_runtime(source,root/'snapshot')
            finally:writer.join(timeout=5)
            self.assertGreaterEqual(time.monotonic()-started,.15)
            self.assertEqual((root/'snapshot/payload.bin').read_bytes(),b'closed data');self.assertTrue((root/'snapshot/missions/.library-writer.lock').exists())


if __name__=='__main__':unittest.main()
