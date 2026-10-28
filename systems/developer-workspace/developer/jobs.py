"""Single active owned job; bounded child execution, explicit cancellation and shutdown."""
import subprocess
import sys
import threading
import time
import uuid
from . import runtime as r

LOCK=threading.RLock()
JOBS={}


class Control:
    def __init__(self):self.cancelled=threading.Event();self.process=None;self.children=[]
    def execute(self,request):
        if self.cancelled.is_set():return dict(status='cancelled',worker_executed=False)
        with LOCK:
            if self.cancelled.is_set():return dict(status='cancelled',worker_executed=False)
            child=subprocess.Popen([sys.executable,'-I','-S','-B',str(r.SOURCE/'validation_worker.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=r.SOURCE);self.process=child;self.children.append(child)
        try:
            try:out,_=child.communicate(r.encode(request),timeout=4)
            except subprocess.TimeoutExpired:child.kill();child.communicate(timeout=5);return dict(status='budget_exceeded',reason='PARENT_WALL_BUDGET',worker_executed=True)
            if self.cancelled.is_set():return dict(status='cancelled',worker_executed=True)
            if child.returncode or len(out)>1024*1024:return dict(status='refused',reason='WORKER_FAILED',worker_executed=True)
            value=r.decode(out)
            if type(value) is not dict or value.get('status') not in ('completed','refused','budget_exceeded','cancelled'):raise r.WorkbenchError('WORKER_PROTOCOL_REFUSED')
            return value
        finally:
            if child.poll() is None:child.kill();child.communicate(timeout=5)
            with LOCK:self.process=None
    def cancel(self):
        self.cancelled.set()
        with LOCK:
            if self.process and self.process.poll() is None:
                try:self.process.terminate()
                except OSError:pass


def start(kind,task,finish):
    with LOCK:
        if any(job['state']=='running' for job in JOBS.values()):raise r.WorkbenchError('JOB_ALREADY_RUNNING')
        while len(JOBS)>=20:del JOBS[next(iter(JOBS))]
        identifier=uuid.uuid4().hex;control=Control();job=dict(job_id=identifier,kind=kind,state='running',control=control,result=None);JOBS[identifier]=job
        def run():
            try:
                value=task(control)
                if control.cancelled.is_set():value=dict(status='cancelled',worker_executed=bool(control.children))
                result=finish(value)
            except Exception:result=dict(status='refused',reason='JOB_REFUSED',saved=False)
            finally:
                with LOCK:job['result']=locals().get('result',dict(status='refused',reason='JOB_REFUSED',saved=False));job['state']='finished'
        thread=threading.Thread(target=run,daemon=False);job['thread']=thread;thread.start()
    return dict(job_id=identifier,kind=kind,state='running')


def status(identifier):
    with LOCK:
        if identifier not in JOBS:raise r.WorkbenchError('JOB_NOT_FOUND')
        job=JOBS[identifier];return {key:job[key] for key in ('job_id','kind','state','result')}


def cancel(identifier):
    with LOCK:
        if identifier not in JOBS:raise r.WorkbenchError('JOB_NOT_FOUND')
        job=JOBS[identifier]
        if job['state']=='finished':return dict(cancel_requested=False,**status(identifier))
        job['control'].cancel();return dict(cancel_requested=True,job_id=identifier)


def wait(identifier,timeout=40):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        value=status(identifier)
        if value['state']=='finished':return value['result']
        time.sleep(.01)
    cancel(identifier);raise r.WorkbenchError('JOB_WAIT_LIMIT')


def close():
    with LOCK:
        active=list(JOBS.values())
        for job in active:
            if job['state']=='running':job['control'].cancel()
    for job in active:job['thread'].join(timeout=10)
    with LOCK:
        if any(job['thread'].is_alive() for job in active):raise r.WorkbenchError('WORKER_SHUTDOWN_REFUSED')
        JOBS.clear()
