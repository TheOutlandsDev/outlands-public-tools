"""Bounded capture/cancel for the owned Python child; trusted code, not a sandbox."""
import base64
from itertools import islice
import os
from pathlib import Path
import select
import subprocess
import sys
import threading
import time
import uuid
from . import contracts as c,runtime as r

CAPTURE_LIMIT=16384


def _available(pipe):
    if os.name!='nt':return None if select.select([pipe],[],[],.02)[0] else 0
    import ctypes
    from ctypes import wintypes
    import msvcrt
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);peek=kernel.PeekNamedPipe
    peek.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p];peek.restype=wintypes.BOOL
    available=wintypes.DWORD()
    if not peek(msvcrt.get_osfhandle(pipe.fileno()),None,0,None,ctypes.byref(available),None):
        if ctypes.get_last_error() in (109,233):return -1
        raise OSError('PIPE_READ_REFUSED')
    return available.value


def captured(raw,truncated):
    try:text=raw.decode('utf-8');valid=True
    except UnicodeError:text=raw.decode('utf-8',errors='replace');valid=False
    return dict(text=text,base64=base64.b64encode(raw).decode('ascii'),bytes=len(raw),sha256=r.digest(raw),utf8_valid=valid,truncated=truncated,hash_scope='captured_prefix' if truncated else 'captured_bytes')


class Control:
    def __init__(self):self.cancelled=threading.Event();self.lock=threading.RLock();self.process=None;self.children=[]
    def cancel(self):
        self.cancelled.set()
        with self.lock:
            if self.process and self.process.poll() is None:
                try:self.process.terminate()
                except OSError:pass
    def execute(self,case):
        if self.cancelled.is_set():return dict(status='not_run',reason='CANCEL_REQUESTED',owned_child_started=False)
        if len(list(islice(r.local_path('runs').iterdir(),1601)))>=1600:raise r.WorkbenchError('RUN_DIRECTORY_LIMIT')
        directory=r.local_path('runs/'+uuid.uuid4().hex,False);r.mkdir(directory);script=case['script'].encode('utf-8');inputs=r.encode(case['input']);r.write_new(directory/'check.py',script);r.write_new(directory/'input.json',inputs)
        if r.digest(r.read_bytes(directory/'check.py'))!=r.digest(script) or r.read_bytes(directory/'input.json')!=inputs:raise r.WorkbenchError('RUN_INPUT_CHANGED')
        env={name:os.environ[name] for name in ('SystemRoot','WINDIR') if name in os.environ};env.update(TEMP=str(directory),TMP=str(directory))
        output={'stdout':bytearray(),'stderr':bytearray()};truncated={'stdout':False,'stderr':False};limit=threading.Event();capture_error=threading.Event();stop=threading.Event();threads=[]
        with self.lock:
            if self.cancelled.is_set():return dict(status='not_run',reason='CANCEL_REQUESTED',owned_child_started=False)
            flags=getattr(subprocess,'CREATE_NO_WINDOW',0) if os.name=='nt' else 0
            child=subprocess.Popen([sys.executable,'-I','-S','-B','-X','utf8',str(directory/'check.py')],cwd=directory,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags,close_fds=True);self.process=child;self.children.append(child)
        started=time.monotonic();deadline=started+case['timeout_ms']/1000;timed_out=False
        def read(name,pipe):
            try:
                while not stop.is_set():
                    available=_available(pipe)
                    if available==-1:break
                    if available==0:
                        if child.poll() is not None:break
                        stop.wait(.01);continue
                    raw=os.read(pipe.fileno(),4096 if available is None else min(4096,available))
                    if not raw:break
                    remaining=CAPTURE_LIMIT-len(output[name]);output[name].extend(raw[:remaining])
                    if len(raw)>remaining:truncated[name]=True;limit.set();break
            except (OSError,ValueError):capture_error.set()
        try:
            for name in output:
                thread=threading.Thread(target=read,args=(name,getattr(child,name)),daemon=False);threads.append(thread);thread.start()
            while child.poll() is None:
                if self.cancelled.is_set() or limit.is_set() or capture_error.is_set():break
                if time.monotonic()>=deadline:timed_out=True;break
                stop.wait(.01)
            if child.poll() is None:
                child.terminate()
                try:child.wait(timeout=.2)
                except subprocess.TimeoutExpired:child.kill();child.wait(timeout=2)
            for thread in threads:thread.join(timeout=1)
            stop.set()
            for thread in threads:thread.join(timeout=1)
            if any(thread.is_alive() for thread in threads):raise r.WorkbenchError('CAPTURE_SHUTDOWN_REFUSED')
            streams={name:captured(bytes(raw),truncated[name]) for name,raw in output.items()};observed=None;json_valid=False
            try:
                if streams['stdout']['utf8_valid'] and not streams['stdout']['truncated']:observed=c.object_value(r.decode(bytes(output['stdout'])),16384);json_valid=True
            except r.WorkbenchError:pass
            status='cancelled' if self.cancelled.is_set() else 'output_limited' if limit.is_set() else 'refused' if capture_error.is_set() else 'timeout' if timed_out else 'completed'
            matches=dict(exit_code=child.returncode==case['expected']['exit_code'],stdout=json_valid and r.encode(observed)==r.encode(case['expected']['stdout']),stderr=streams['stderr']['utf8_valid'] and not streams['stderr']['truncated'] and streams['stderr']['text'].replace('\r\n','\n')==case['expected']['stderr'].replace('\r\n','\n'))
            return dict(status=status,passed=status=='completed' and all(matches.values()),owned_child_started=True,exit_code=child.returncode,expected=case['expected'],matches=matches,stdout_json=observed if json_valid else None,stdout_json_valid=json_valid,streams=streams,elapsed_ms=round((time.monotonic()-started)*1000),script_sha256=r.digest(script),input_sha256=r.digest(inputs),descendant_containment=False)
        finally:
            stop.set()
            if child.poll() is None:child.kill();child.wait(timeout=2)
            for thread in threads:thread.join(timeout=2)
            for pipe in (child.stdout,child.stderr):pipe.close()
            with self.lock:self.process=None
