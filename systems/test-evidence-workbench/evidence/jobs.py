"""One explicit suite at a time; no restart replay or external process IDs."""
import threading
import time
import uuid
from . import runtime as r
from .runner import Control

LOCK=threading.RLock();JOBS={}


def start(task,finish):
    with LOCK:
        if any(job['state']=='running' for job in JOBS.values()):raise r.WorkbenchError('JOB_ALREADY_RUNNING')
        while len(JOBS)>=20:del JOBS[next(iter(JOBS))]
        identifier=uuid.uuid4().hex;control=Control();job=dict(job_id=identifier,state='running',control=control,result=None);JOBS[identifier]=job
        def run():
            try:result=finish(task(control))
            except Exception:result=dict(status='refused',reason='JOB_REFUSED',saved=False)
            finally:
                with LOCK:job['result']=locals().get('result',dict(status='refused',reason='JOB_REFUSED',saved=False));job['state']='finished'
        thread=threading.Thread(target=run,daemon=False);job['thread']=thread;thread.start()
    return dict(job_id=identifier,state='running')


def status(identifier):
    with LOCK:
        if identifier not in JOBS:raise r.WorkbenchError('JOB_NOT_FOUND')
        return {key:JOBS[identifier][key] for key in ('job_id','state','result')}


def cancel(identifier):
    with LOCK:
        if identifier not in JOBS:raise r.WorkbenchError('JOB_NOT_FOUND')
        if JOBS[identifier]['state']=='finished':return dict(cancel_requested=False,**status(identifier))
        JOBS[identifier]['control'].cancel();return dict(job_id=identifier,cancel_requested=True)


def wait(identifier,timeout=80):
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
