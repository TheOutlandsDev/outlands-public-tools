"""Durable job boundaries, advisory retention and reviewed private metadata reports."""
from contextlib import closing
import json
import re
import sqlite3
import uuid
from . import contracts as c,filesystem as fs,journal as j,runtime as r

def _code(error):
    return str(error) if isinstance(error,r.WorkbenchError) and re.fullmatch('[A-Z][A-Z0-9_]{0,79}',str(error)) else 'FILESYSTEM_REFUSED' if isinstance(error,OSError) else 'OPERATION_REFUSED'

def _check_head(state,pin):
    c.pin(pin)
    if state['head']!=pin:c.fail('JOURNAL_HEAD_CONFLICT')

def _run(raw,kind):
    value=r.decode(raw);c.envelope(value,('request',));c.request(kind,value['request'])
    with r.DATABASE_LOCK:
        state,_=j.read();_check_head(state,value['expected_head']);identifier=uuid.uuid4().hex;event=dict(operation='job_started',actor=value['actor'],reason=value['reason'],data=dict(job_id=identifier,kind=kind,request=value['request']));state=j.append(event,state['head'])
        try:
            if kind=='snapshot':result=fs.snapshot(identifier,value['request'])
            elif kind=='restore_imported':result=fs.restore_imported(identifier,value['request'])
            else:
                selected=state['snapshots'][value['request']['snapshot_id']]['result'];snapshot_id=selected['snapshot_id'];pin=selected['manifest_sha256']
                if kind=='restore':result=fs.restore(identifier,snapshot_id,pin)
                else:
                    _,verified=fs.verify_snapshot(snapshot_id,pin);result=dict(snapshot_id=snapshot_id,manifest_sha256=pin,**verified)
        except Exception as error:
            code=_code(error)
            try:j.append(dict(operation='job_failed',actor=value['actor'],reason=value['reason'],data=dict(job_id=identifier,code=code)),state['head'])
            except Exception:c.fail('JOURNAL_FINALIZATION_FAILED')
            c.fail(code)
        try:state=j.append(dict(operation='job_completed',actor=value['actor'],reason=value['reason'],data=dict(job_id=identifier,result=result)),state['head'])
        except Exception:c.fail('JOURNAL_FINALIZATION_FAILED')
    return dict(head=state['head'],job=state['jobs'][identifier])

def snapshot(raw):return _run(raw,'snapshot')
def restore(raw):return _run(raw,'restore')
def restore_imported(raw):return _run(raw,'restore_imported')
def verify(raw):return _run(raw,'verify')

def overview():
    state,_=j.read()
    return dict(head=state['head'],sequence=state['sequence'],jobs=list(state['jobs'].values()),snapshots=sorted(state['snapshots'].values(),key=lambda row:row['completed_sequence']),unfinished_jobs=sum(row['status']=='started' for row in state['jobs'].values()),deletion_implemented=False)

def job(identifier):
    c.identifier(identifier);state,_=j.read()
    if identifier not in state['jobs']:c.fail('JOB_NOT_FOUND')
    return dict(head=state['head'],job=state['jobs'][identifier])

def inspect_snapshot(identifier):
    c.identifier(identifier);state,_=j.read();selected=state['snapshots'].get(identifier)
    if selected is None:c.fail('SNAPSHOT_NOT_REGISTERED')
    # Viewing the stored manifest does not claim that the current payload is verified.
    raw=r.read_bytes(r.local_path('snapshots/'+identifier+'/manifest.json'));manifest=fs.manifest(raw,identifier)
    if r.digest(raw)!=selected['result']['manifest_sha256']:c.fail('SNAPSHOT_MANIFEST_HASH_MISMATCH')
    return dict(head=state['head'],snapshot=selected,manifest=manifest,payload_reverified=False)

def hold(raw):
    value=r.decode(raw);c.envelope(value,('snapshot_id','hold'));c.identifier(value['snapshot_id'])
    with r.DATABASE_LOCK:state=j.append(dict(operation='hold_changed',actor=value['actor'],reason=value['reason'],data=dict(snapshot_id=value['snapshot_id'],hold=value['hold'])),value['expected_head'])
    return dict(head=state['head'],snapshot=state['snapshots'][value['snapshot_id']])

def recover(raw):
    value=r.decode(raw);c.fields(value,('actor','reason'));c.text(value['actor'],160);c.text(value['reason']);recovered=[]
    with r.DATABASE_LOCK:
        state,_=j.read()
        for row in list(state['jobs'].values()):
            if row['status']=='started':
                state=j.append(dict(operation='job_interrupted',actor=value['actor'],reason=value['reason'],data=dict(job_id=row['job_id'],code='INTERRUPTED_NO_AUTOREPLAY')),state['head']);recovered.append(row['job_id'])
    return dict(head=state['head'],interrupted_jobs=recovered,partial_outputs_retained=True,automatically_replayed=False,source_files_changed=False)

def retention(raw):
    value=r.decode(raw);c.fields(value,('expected_head','policy'));c.policy(value['policy'])
    with r.DATABASE_LOCK:
        state,_=j.read();_check_head(state,value['expected_head']);snapshots=sorted(state['snapshots'].values(),key=lambda row:row['completed_sequence'],reverse=True);recent={row['snapshot_id'] for row in snapshots[:value['policy']['keep_last']]};pending=any(row['status']=='started' for row in state['jobs'].values());rows=[]
        for selected in snapshots:
            identifier=selected['snapshot_id'];reasons=[];verified=False;drill=False;error=None
            if identifier in recent:reasons.append('KEEP_LAST')
            if selected['hold']:reasons.append('MANUAL_HOLD')
            if pending:reasons.append('UNFINISHED_JOB')
            try:
                manifest,_=fs.verify_snapshot(identifier,selected['result']['manifest_sha256']);verified=True
                for candidate in reversed(list(state['jobs'].values())):
                    if candidate['kind']=='restore' and candidate['status']=='completed' and candidate['result']['snapshot_id']==identifier:
                        try:fs.verify_restore(candidate['job_id'],candidate['result'],manifest);drill=True;break
                        except (r.WorkbenchError,OSError):continue
            except (r.WorkbenchError,OSError) as refused:error=_code(refused);reasons.append('VERIFICATION_FAILED')
            if value['policy']['protect_untested'] and not drill:reasons.append('RESTORE_DRILL_NOT_CURRENTLY_VERIFIED')
            rows.append(dict(snapshot_id=identifier,status='protected' if reasons else 'candidate',reasons=reasons,payload_verified=verified,restore_drill_verified=drill,error=error))
    return dict(head=state['head'],policy=value['policy'],snapshots=rows,candidates=sum(row['status']=='candidate' for row in rows),protected=sum(row['status']=='protected' for row in rows),advisory_only=True,deletion_implemented=False,storage_reclaimed=False)

def history():
    state,events=j.read();return dict(head=state['head'],events=events)

def export(raw):
    value=r.decode(raw);c.envelope(value,('policy','checks'));c.fields(value['checks'],('quality','privacy','rights','context'));c.policy(value['policy'])
    if any(type(item) is not bool or not item for item in value['checks'].values()):c.fail('EXPORT_REVIEW_REQUIRED')
    with r.DATABASE_LOCK:
        state,_=j.read();_check_head(state,value['expected_head']);plan=retention(r.encode(dict(expected_head=state['head'],policy=value['policy'])));data={'overview.json':r.encode(overview()),'journal.json':r.encode(history()),'retention.json':r.encode(plan),'review.json':r.encode(value)}
        for row in plan['snapshots']:
            identifier=row['snapshot_id']
            try:content=dict(snapshot_id=identifier,manifest=inspect_snapshot(identifier)['manifest'],payload_verified_during_review=row['payload_verified'],error=row['error'])
            except (r.WorkbenchError,OSError) as error:content=dict(snapshot_id=identifier,manifest=None,payload_verified_during_review=False,error=_code(error))
            data['manifests/'+identifier+'.json']=r.encode(content)
        manifest=dict(format='outlands-private-recovery-report-v1',journal_head=state['head'],includes_snapshot_bytes=False,public_release_authorized=False,files={name:dict(bytes=len(raw),sha256=r.digest(raw)) for name,raw in sorted(data.items())});directory=r.local_path('reports/'+uuid.uuid4().hex,False);r.mkdir(directory)
        if state['snapshots']:r.mkdir(directory/'manifests')
        for name,content in sorted(data.items()):r.write_new(directory/name,content)
        r.write_new(directory/'manifest.json',r.encode(manifest))
    return dict(directory=directory.relative_to(r.ROOT).as_posix(),manifest=manifest)

def backup_index():
    target=r.local_path('index-backups/'+uuid.uuid4().hex+'.sqlite3',False);r.write_new(target,b'')
    with r.connect() as source,r.io_errors(),r.guarded._store_scope(target,initial=True):
        with closing(sqlite3.connect(target)) as destination:source.backup(destination);r.validate_schema(destination);j.load(destination)
    raw=r.read_bytes(target,r.MAX_STORE);return dict(file=target.relative_to(r.ROOT).as_posix(),bytes=len(raw),sha256=r.digest(raw),includes_snapshot_bytes=False,private_index_backup=True)

def demo():
    actor='sample_operator';reason='Fictional recovery workflow'
    def run(fn,request):return fn(r.encode(dict(expected_head=overview()['head'],actor=actor,reason=reason,request=request)))
    first=run(snapshot,dict(source='inbox/sample-files-v1',exclusions=['cache'],quiescent=True))['job']['result'];restored=run(restore,dict(snapshot_id=first['snapshot_id']));run(verify,dict(snapshot_id=first['snapshot_id']));second=run(snapshot,dict(source='inbox/sample-files-v2',exclusions=['cache'],quiescent=True))['job']['result']
    for held in (True,False):hold(r.encode(dict(expected_head=overview()['head'],actor=actor,reason=reason,snapshot_id=first['snapshot_id'],hold=held)))
    policy=dict(keep_last=1,protect_untested=True);plan=retention(r.encode(dict(expected_head=overview()['head'],policy=policy)));report=export(r.encode(dict(expected_head=overview()['head'],actor=actor,reason=reason,policy=policy,checks=dict(quality=True,privacy=True,rights=True,context=True))));index=backup_index();state=overview()
    return dict(mode='FICTIONAL_BACKUP_RECOVERY_DEMO',snapshots=len(state['snapshots']),completed_jobs=sum(row['status']=='completed' for row in state['jobs']),journal_events=state['sequence'],files_per_snapshot=first['file_count'],excluded_per_snapshot=first['excluded_count'],snapshot_bytes=first['total_bytes'],restored_bytes=restored['job']['result']['total_bytes'],retention_candidates=plan['candidates'],retention_protected=plan['protected'],private_report_files=len(report['manifest']['files'])+1,index_backup_verified=index['bytes']>0,index_includes_snapshot_bytes=False,source_files_changed=False,deletion_performed=False,external_services_used=False)
