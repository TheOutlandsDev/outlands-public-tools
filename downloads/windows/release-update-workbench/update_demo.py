"""Invented update planning through the original CLI; no target execution."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
APP=ROOT/'application'
CHECKS=dict(quality=True,privacy=True,rights=True,context=True)

def require(value,code):
    if not value:raise ValueError(code)

def digest(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return json.dumps(value,ensure_ascii=True,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
def read(path):return json.loads(path.read_bytes())

class Exercise:
    def __init__(self,name,workspace):
        self.source=APP;self.workspace=workspace;self.calls=0;self.requests=0;self.call('init')
    def call(self,*args,error=None):
        self.calls+=1
        result=subprocess.run([sys.executable,'-B',str(self.source/'workbench.py'),'--workspace',str(self.workspace),*map(str,args)],cwd=self.source,capture_output=True,timeout=90)
        if result.returncode!=(2 if error else 0):
            (self.workspace/'exercise-command-failure.log').write_bytes(result.stdout+result.stderr)
            raise ValueError('EXERCISE_COMMAND_FAILED_PRIVATE_LOG_RETAINED')
        value=json.loads(result.stdout)
        if error:require(value==dict(error=error),'EXPECTED_REFUSAL_MISSING')
        return value
    def request(self,command,body,error=None):
        self.requests+=1;head=self.call('overview')['head'];name='inbox/lifecycle-request-'+str(self.requests)+'.json'
        value=dict(expected_head=head,actor='sample_operator',reason='Fictional Windows update exercise',**body)
        with (self.workspace/name).open('x',encoding='utf-8') as stream:json.dump(value,stream)
        return self.call(command,'--file',name,error=error)
    def mutate(self,command,request,error=None):
        value=self.request(command,dict(request=request),error)
        return value if error else value['job']['result']
    def artifact(self,result,kind):
        raw=(self.workspace/result['target']/(kind+'.json')).read_bytes()
        require(digest(raw)==result[kind+'_sha256'],'ARTIFACT_HASH_ORACLE_FAILED')
        return json.loads(raw)

def verify_report(workspace,result,count):
    folder=workspace/result['directory'];manifest=read(folder/'manifest.json')
    require(manifest==result['manifest'] and len(manifest['files'])==count,'HANDOFF_MANIFEST_ORACLE_FAILED')
    require(not manifest['public_release_authorized'] and not manifest['execution_authorized'],'HANDOFF_SCOPE_ORACLE_FAILED')
    require({p.name for p in folder.iterdir()}==set(manifest['files'])|{'manifest.json'},'HANDOFF_INVENTORY_ORACLE_FAILED')
    for name,row in manifest['files'].items():
        raw=(folder/name).read_bytes();require(row==dict(bytes=len(raw),sha256=digest(raw)),'HANDOFF_HASH_ORACLE_FAILED')
    return manifest

def updates(workspace):
    e=Exercise('release-update-workbench',workspace)
    sentinel=workspace/'inbox/fictional-target.txt';sentinel.write_bytes(b'Invented target sentinel; no target update authorized.\n');target_pin=digest(sentinel.read_bytes())
    fixtures={n:read(workspace/'inbox'/('capture-'+n+'.json'))['request'] for n in ('v1','v2')}
    selected={request['source']+'/'+row['path'] for request in fixtures.values() for row in request['manifest']['inventory']}
    before={n:(workspace/n).read_bytes() for n in selected}
    baseline=e.mutate('capture',fixtures['v1']);candidate=e.mutate('capture',dict(fixtures['v2'],parent_id=baseline['candidate_id']))
    snapshots={}
    for result in (baseline,candidate):
        value=e.artifact(result,'candidate');e.call('inspect','--kind','candidate','--id',result['candidate_id'])
        folder=workspace/result['target']/'payload';expected={row['path']:dict(size=row['size'],sha256=row['sha256']) for row in value['inventory']}
        actual={p.relative_to(folder).as_posix():dict(size=p.stat().st_size,sha256=digest(p.read_bytes())) for p in folder.rglob('*') if p.is_file()}
        require(expected==actual and len(actual)==4,'SNAPSHOT_COPY_ORACLE_FAILED');snapshots[result['candidate_id']]=(folder,actual)
    policy={key:False for key in ('backup_confirmed','target_stopped_confirmed','readiness_confirmed','allow_removals','dependency_reviewed')}
    request=dict(baseline_id=baseline['candidate_id'],baseline_sha256=baseline['candidate_sha256'],candidate_id=candidate['candidate_id'],candidate_sha256=candidate['candidate_sha256'],policy=policy)
    blocked=e.mutate('compare',request);blocked_plan=e.mutate('make-plan',dict(comparison_id=blocked['comparison_id'],comparison_sha256=blocked['comparison_sha256']))
    e.request('review',dict(plan_id=blocked_plan['plan_id'],plan_sha256=blocked_plan['plan_sha256'],approve=True,checks=CHECKS),error='BLOCKED_PLAN_CANNOT_BE_APPROVED')
    ready=e.mutate('compare',dict(request,policy={key:True for key in policy}));comparison=e.artifact(ready,'comparison')
    expected_counts=dict(ADD=1,REMOVE=1,REPLACE=2,UNCHANGED=1)
    require(comparison['counts']==expected_counts and blocked['blocker_count']==5 and ready['blocker_count']==0,'UPDATE_COMPARISON_ORACLE_FAILED')
    require(comparison['dependency_lock']['counts']['version_text_changed']==1,'LOCK_TEXT_ORACLE_FAILED')
    planned=e.mutate('make-plan',dict(comparison_id=ready['comparison_id'],comparison_sha256=ready['comparison_sha256']));plan=e.artifact(planned,'plan')
    require(plan['plan_only'] and not plan['execution_authorized'] and not plan['runtime_verified'] and all(row['status']=='NOT_PERFORMED' for row in plan['steps']),'UPDATE_MANUAL_SCOPE_ORACLE_FAILED')
    require(not plan['rollback']['backup_independently_verified'] and not plan['rollback']['restore_performed'],'ROLLBACK_SCOPE_ORACLE_FAILED')
    export_request=dict(plan_id=planned['plan_id'],checks=CHECKS)
    e.request('export',export_request,error='CURRENT_PLAN_APPROVAL_REQUIRED')
    review=dict(plan_id=planned['plan_id'],plan_sha256=planned['plan_sha256'],approve=True,checks=CHECKS)
    e.request('review',review);exported=e.request('export',export_request);manifest=verify_report(workspace,exported,7)
    require(not manifest['payload_files_included'] and manifest['target_updates_plan_only'],'UPDATE_HANDOFF_SCOPE_ORACLE_FAILED')
    another=e.mutate('make-plan',dict(comparison_id=ready['comparison_id'],comparison_sha256=ready['comparison_sha256']))
    e.request('export',dict(export_request,plan_id=another['plan_id']),error='CURRENT_PLAN_APPROVAL_REQUIRED')
    e.request('review',dict(review,approve=False));e.request('export',export_request,error='CURRENT_PLAN_APPROVAL_REQUIRED')
    e.call('inspect','--kind','plan','--id',planned['plan_id']);history=e.call('history');state=e.call('overview')
    require(state['reviews'][planned['plan_id']]['status']=='REVOKED' and len(state['candidates'])==2 and len(state['plans'])==3 and state['unfinished_jobs']==0,'UPDATE_REOPEN_ORACLE_FAILED')
    require(all((workspace/n).read_bytes()==raw for n,raw in before.items()),'PACKAGE_INPUT_CHANGED')
    for folder,original in snapshots.values():
        current={p.relative_to(folder).as_posix():dict(size=p.stat().st_size,sha256=digest(p.read_bytes())) for p in folder.rglob('*') if p.is_file()};require(current==original,'COPIED_SNAPSHOT_CHANGED')
    require(all(row['status']=='NOT_PERFORMED' for row in plan['steps']) and len(history['events'])==16,'UPDATE_HISTORY_ORACLE_FAILED')
    require(digest(sentinel.read_bytes())==target_pin,'FICTIONAL_TARGET_CHANGED')
    return dict(fictional_target_unchanged=True,manual_checkpoints='NOT_PERFORMED',rollback_restore_performed=False,status='PASS',snapshots=2,files_per_snapshot=4,file_counts=expected_counts,blockers_before=5,blockers_after=0,lock_version_text_changes=1,blocked_approval_refused=True,unapproved_export_refused=True,new_plan_inherits_approval=False,revoked_export_refused=True,private_handoff_files=8,input_bytes_unchanged=True,copied_snapshots_unchanged=True,target_updates_performed=False,programs_executed=False,network_probed=False,command_checks=e.calls)


def exercise(workspace):
    if not workspace.is_absolute() or '..' in workspace.parts or workspace.exists() or not workspace.parent.is_dir():
        raise ValueError('EXERCISE_REQUIRES_NEW_ABSOLUTE_INSTANCE')
    if workspace.resolve().is_relative_to(ROOT):raise ValueError('EXTERNAL_INSTANCE_REQUIRED')
    return dict(mode='FICTIONAL_UPDATE_EXERCISE',**updates(workspace))
