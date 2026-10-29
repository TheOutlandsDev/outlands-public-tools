"""Original CLI practice with independent arithmetic, report and revision checks."""
import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
def tree(root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
def totals(plan):
    return [sum(p[key] for p in plan['products']) for key in ('remaining_demand','dock_allocated_quantity')]+[sum(p['allocation']['conservation'][key] for p in plan['products']) for key in ('covered','uncovered')]+[sum(p['lot_proposal']['recommended_lot_count'] for p in plan['products'])]
def report(workspace,value):
    folder=workspace/value['directory'];manifest=value['manifest']
    assert set(tree(folder))==set(manifest['files'])|{'manifest.json'}
    assert json.loads((folder/'manifest.json').read_bytes())==manifest
    for name,row in manifest['files'].items():
        raw=(folder/name).read_bytes();assert row==dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    return json.loads((folder/'plan.json').read_bytes())

def exercise(workspace,application=None):
    development_source=application is not None
    application=Path(application) if application else ROOT/'application'
    if not workspace.is_absolute() or workspace.exists() or not workspace.parent.is_dir():raise ValueError('NEW_PRIVATE_EXERCISE_REQUIRED')
    calls=[]
    def command(*args,expected=0):
        entry=[str(application/'workbench.py')]
        if development_source:
            entry=['-c',"import sys,runpy;sys.path.insert(0,sys.argv.pop(1));sys.argv.pop(0);runpy.run_path(sys.argv[0],run_name='__main__')",str(application),str(application/'workbench.py')]
        p=subprocess.run([sys.executable,'-I','-B','-X','utf8',*entry,'--workspace',str(workspace),*map(str,args)],capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=60)
        calls.append(args[0])
        if p.returncode!=expected:
            if workspace.is_dir():(workspace/'failed-command.log').write_bytes(p.stdout+p.stderr)
            raise AssertionError('Original CLI failed; private log retained.')
        return json.loads(p.stdout)
    command('init');command('import','--file','inbox/sample-project.json')
    inputs=tree(workspace/'inbox');initial=command('plan','--project','sample-workshop');assert totals(initial)==[160,25,85,50,3]
    # Independent conservation: original orders 70+50+40, assigned dock 15+10,
    # WIP 40+20+25; stage-7 stock cannot also count as production WIP.
    assert 70+50+40==(15+10)+(40+20+25)+50
    first_report=command('export','--project','sample-workshop');assert report(workspace,first_report)==initial
    first_bytes=tree(workspace/first_report['directory'])
    action=dict(project_id='sample-workshop',revision_sha256=initial['revision_sha256'],action_id=initial['actions'][0]['action_id'],actor='sample_reviewer',change=dict(command='ACKNOWLEDGE',expected_version=0))
    action_file=workspace/'inbox/sample-action.json';action_file.write_text(json.dumps(action),encoding='utf-8')
    assert command('action','--file','inbox/sample-action.json')['state']['status']=='ACKNOWLEDGED'
    before=tree(workspace);assert command('action','--file','inbox/sample-action.json',expected=2)==dict(error='ACTION_VERSION_CONFLICT') and tree(workspace)==before
    revised=command('revise-order','--project','sample-workshop','--file','inbox/sample-order-revision.json','--expected',initial['revision_sha256']);assert revised['sequence']==2
    final=command('plan','--project','sample-workshop');assert totals(final)==[170,25,85,60,4] and all(a['workflow']['status']=='OPEN' for a in final['actions'])
    before=tree(workspace)
    assert command('revise-order','--project','sample-workshop','--file','inbox/sample-order-revision.json','--expected',initial['revision_sha256'],expected=2)==dict(error='REVISION_CONFLICT') and tree(workspace)==before
    second_report=command('export','--project','sample-workshop');assert report(workspace,second_report)==final and second_report['directory']!=first_report['directory']
    history=command('history','--project','sample-workshop')['revisions'];assert len(history)==2 and history[1]['parent_sha256']==initial['revision_sha256'] and history[0]['revision_sha256']==initial['revision_sha256']
    backup=command('backup');raw=(workspace/backup['file']).read_bytes();assert backup['sha256']==hashlib.sha256(raw).hexdigest() and backup['bytes']==len(raw)
    with closing(sqlite3.connect((workspace/backup['file']).as_uri()+'?mode=ro',uri=True)) as db:assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)] and db.execute('SELECT COUNT(*) FROM revisions').fetchone()[0]==2
    before=tree(workspace);assert command('init',expected=2)['error'] and tree(workspace)==before
    assert command('show','--project','sample-workshop')['revision_sha256']==final['revision_sha256'] and tree(workspace)==before
    assert tree(workspace/first_report['directory'])==first_bytes
    assert all(tree(workspace/'inbox')[n]==v for n,v in inputs.items())
    return dict(status='PASS',command_checks=len(calls),initial_totals=[160,25,85,50,3],final_totals=[170,25,85,60,4],revisions=2,private_report_files=5,report_hashes_independently_verified=True,original_inputs_unchanged=True,old_report_unchanged=True,stale_action_refused=True,stale_revision_refused=True,new_revision_does_not_inherit_review=True,backup_integrity_checked=True,saved_revision_reopened=True,existing_initialization_refused_without_writes=True,external_system_writes=False,lot_ids_reserved=False,shipment_execution_authorized=False)
