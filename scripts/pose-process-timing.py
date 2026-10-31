"""Bounded read-only CPU accounting for explicitly owned Windows processes.

No threads, memory, commands, UI, input, network, privileges or process mutation.
Handles retain process identity; all output except one ready marker is deferred.
"""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import time

ROLES=('Visible','Peer','Server')


class ProcessQuery:
    def __init__(self,pid,*,executable=None,created=None,process_handle=None):
        if os.name!='nt':raise OSError('Windows process timing is unavailable')
        if type(pid) is not int or not 0<pid<2**32:raise ValueError('Invalid PID')
        self.api=ctypes.WinDLL('kernel32',use_last_error=True)
        self.api.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];self.api.OpenProcess.restype=wintypes.HANDLE
        self.api.CloseHandle.argtypes=[wintypes.HANDLE];self.api.CloseHandle.restype=wintypes.BOOL
        self.api.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];self.api.WaitForSingleObject.restype=wintypes.DWORD
        self.api.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
        self.api.QueryFullProcessImageNameW.restype=wintypes.BOOL
        self.api.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
        self.api.GetProcessTimes.restype=wintypes.BOOL
        self.api.QueryProcessCycleTime.argtypes=[wintypes.HANDLE,ctypes.POINTER(ctypes.c_ulonglong)]
        self.api.QueryProcessCycleTime.restype=wintypes.BOOL
        # Query identity / times + zero-time liveness wait; no write / VM / suspend rights.
        self.owns_handle=process_handle is None
        self.handle=self.api.OpenProcess(0x1000|0x100000,False,pid) if self.owns_handle else wintypes.HANDLE(int(process_handle))
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())
        try:
            buffer=ctypes.create_unicode_buffer(32768);length=wintypes.DWORD(len(buffer))
            if not self.api.QueryFullProcessImageNameW(self.handle,0,buffer,ctypes.byref(length)):raise ctypes.WinError(ctypes.get_last_error())
            self.image=buffer.value;self.pid=pid
            birth,_,_=self.times();self.created=birth
            if executable is not None and os.path.normcase(str(Path(executable).resolve()))!=os.path.normcase(str(Path(self.image).resolve())):
                raise ValueError('Owned process executable mismatch')
            if created is not None and birth!=created:raise ValueError('Owned process creation time mismatch')
        except BaseException:self.close();raise

    def times(self):
        if self.api.WaitForSingleObject(self.handle,0)!=258:raise RuntimeError('Owned process is not live')
        values=[wintypes.FILETIME() for _ in range(4)]
        if not self.api.GetProcessTimes(self.handle,*[ctypes.byref(v) for v in values]):raise ctypes.WinError(ctypes.get_last_error())
        numbers=[v.dwLowDateTime+(v.dwHighDateTime<<32) for v in values]
        return numbers[0],numbers[2],numbers[3]

    def close(self):
        if self.handle:
            handle=self.handle;self.handle=None
            if self.owns_handle and not self.api.CloseHandle(handle):raise ctypes.WinError(ctypes.get_last_error())

    def cpu_cycles(self):
        value=ctypes.c_ulonglong()
        if not self.api.QueryProcessCycleTime(self.handle,ctypes.byref(value)):raise ctypes.WinError(ctypes.get_last_error())
        return value.value

    def identity(self,role):
        return {'role':role,'pid':self.pid,'createdFileTime':self.created,'executable':self.image}


def validate_targets(targets):
    if not isinstance(targets,list) or not 1<=len(targets)<=3:raise ValueError('Invalid target count')
    if len({t['role'] for t in targets})!=len(targets) or len({t['pid'] for t in targets})!=len(targets):raise ValueError('Duplicate process identity')
    for target in targets:
        if target['role'] not in ROLES or type(target['pid']) is not int or not 0<target['pid']<2**32 \
            or type(target['createdFileTime']) is not int or target['createdFileTime']<=0 or not Path(target['executable']).is_absolute():
            raise ValueError('Invalid owned process identity')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--manifest',type=Path,required=True)
    args=parser.parse_args()
    if not args.directory.is_absolute() or not args.manifest.is_absolute():parser.error('Use fresh absolute paths')
    directory=args.directory.resolve();manifest=args.manifest.resolve()
    if manifest.parent!=directory.parent or manifest.name!='pose-process-targets.json':parser.error('Use the adjacent owned-target manifest')
    metadata=json.loads(manifest.read_text())
    if metadata['schemaVersion']!=1 or metadata['source']!='OwnedProcessTimingTargets':raise ValueError('Unsupported target manifest')
    targets=metadata['targets'];validate_targets(targets);directory.mkdir(parents=True,exist_ok=False)
    handles=[];rows=[];cycles=0;explicit=False;truncated=False;error='';closed=0
    started=time.perf_counter_ns();next_check=started
    try:
        for target in targets:handles.append(ProcessQuery(target['pid'],executable=target['executable'],created=target['createdFileTime']))
        while True:
            if cycles==5000:truncated=True;break
            for target,handle in zip(targets,handles):
                a=time.perf_counter_ns();ua=time.time_ns();birth,kernel,user=handle.times();cpu_cycles=handle.cpu_cycles();ub=time.time_ns();b=time.perf_counter_ns()
                if birth!=target['createdFileTime']:raise RuntimeError('Process identity changed')
                rows.append({'role':target['role'],'fromCounterNs':a,'toCounterNs':b,'fromUnixNs':ua,'toUnixNs':ub,
                    'kernel100ns':kernel,'user100ns':user,'cpuCycles':cpu_cycles})
            cycles+=1
            if cycles==1:(directory/'ready.json').write_text(json.dumps({'schemaVersion':1,'targetCount':len(targets)}),encoding='utf-8')
            now=time.perf_counter_ns()
            if now-started>=240_000_000_000:break
            if now>=next_check:
                next_check=now+250_000_000
                if (directory/'finish.request').exists():explicit=True;break
            time.sleep(.05)
    except Exception as failure:error=type(failure).__name__
    finally:
        for handle in handles:
            try:handle.close();closed+=1
            except Exception as failure:error=error or type(failure).__name__
    report={'schemaVersion':1,'source':'OwnedWindowsProcessCpuTiming','complete':explicit and not truncated and not error,
        'truncated':truncated,'error':error,'sampleSeconds':.05,'maximumSeconds':240,'maximumSamples':5000,
        'cycles':cycles,'cycleCounterVersion':1,'closedHandleCount':closed,'targets':targets,'rows':rows}
    (directory/'report.json').write_text(json.dumps(report),encoding='utf-8')
    if not report['complete']:raise SystemExit('Owned process timing incomplete: '+(error or 'limit reached'))


if __name__=='__main__':main()
