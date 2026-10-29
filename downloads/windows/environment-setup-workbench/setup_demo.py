"""Invented setup review through the original CLI; no target execution."""
import copy
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
        value=dict(expected_head=head,actor='sample_operator',reason='Fictional Windows setup exercise',**body)
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

def setup(workspace):
    e=Exercise('environment-setup-workbench',workspace)
    names=('profile.json','observations.json');before={n:(workspace/'inbox'/n).read_bytes() for n in names}
    profile=read(workspace/'inbox/profile.json');observations=read(workspace/'inbox/observations.json')
    saved=e.mutate('save-profile',dict(parent_id=None,profile=profile))
    changed=copy.deepcopy(observations);changed['prerequisites']['sample_runtime']='MISSING'
    first=e.mutate('evaluate',dict(profile_id=saved['profile_id'],profile_sha256=saved['profile_sha256'],observations=changed))
    bad=e.artifact(first,'evaluation');e.call('inspect','--kind','evaluation','--id',first['evaluation_id'])
    require(bad['status']=='REVIEW_REQUIRED' and bad['summary']['blocked_steps']==3 and bad['summary']['blocking_checks']==1,'SETUP_MISSING_PREREQUISITE_ORACLE_FAILED')
    second=e.mutate('evaluate',dict(profile_id=saved['profile_id'],profile_sha256=saved['profile_sha256'],observations=observations))
    good=e.artifact(second,'evaluation');e.call('inspect','--kind','evaluation','--id',second['evaluation_id'])
    require(good['status']=='DECLARATIONS_SATISFIED' and good['summary']['checks']==9 and good['summary']['blocked_steps']==0,'SETUP_DECLARATION_ORACLE_FAILED')
    require([r['id'] for r in good['steps']]==['prepare','review','handoff'] and all(r['verification_status']=='NOT_PERFORMED' for r in good['steps']),'SETUP_MANUAL_ORDER_ORACLE_FAILED')
    require(all(good[key] is False for key in ('runtime_verified','network_probed','programs_executed','host_inventory_collected','configuration_modified')),'SETUP_EXECUTION_SCOPE_ORACLE_FAILED')
    comparison=e.call('compare','--kind','evaluation','--first',first['evaluation_id'],'--second',second['evaluation_id'])
    require(comparison['changes']['checks']['changed']==['prerequisite:sample_runtime'],'SETUP_COMPARISON_ORACLE_FAILED')
    request=dict(evaluation_id=second['evaluation_id'],evaluation_sha256=second['evaluation_sha256'],checks=dict(CHECKS,quality=False))
    e.mutate('make-plan',request,error='REVIEW_REQUIRED')
    planned=e.mutate('make-plan',dict(request,checks=CHECKS));plan=e.artifact(planned,'plan')
    require(plan['plan_only'] and not plan['execution_authorized'] and not plan['runtime_verified'],'SETUP_PLAN_SCOPE_ORACLE_FAILED')
    e.call('inspect','--kind','plan','--id',planned['plan_id'])
    exported=e.request('export',dict(plan_id=planned['plan_id'],checks=CHECKS));verify_report(workspace,exported,5)
    history=e.call('history');state=e.call('overview')
    require([len(state[k]) for k in ('profiles','evaluations','plans')]==[1,2,1] and state['unfinished_jobs']==0 and len(history['events'])==8,'SETUP_REOPEN_ORACLE_FAILED')
    require(all((workspace/'inbox'/n).read_bytes()==raw for n,raw in before.items()),'SETUP_FIXTURE_CHANGED')
    return dict(status='PASS',checks=9,blocked_steps_before=3,blocked_steps_after=0,ordered_steps=['prepare','review','handoff'],manual_verifications='NOT_PERFORMED',review_refused=True,private_handoff_files=6,input_bytes_unchanged=True,runtime_verified=False,programs_executed=False,network_probed=False,command_checks=e.calls)


def exercise(workspace):
    if not workspace.is_absolute() or '..' in workspace.parts or workspace.exists() or not workspace.parent.is_dir():
        raise ValueError('EXERCISE_REQUIRES_NEW_ABSOLUTE_INSTANCE')
    if workspace.resolve().is_relative_to(ROOT):raise ValueError('EXTERNAL_INSTANCE_REQUIRED')
    return dict(mode='FICTIONAL_SETUP_EXERCISE',**setup(workspace))
