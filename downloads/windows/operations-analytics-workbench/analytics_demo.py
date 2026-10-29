"""Invented original-CLI handoff, event identities and preservation exercise."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
NAMES={'plan.json','orders.csv','allocations.csv','readiness.csv','manifest.json'}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def tree(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
def report(workspace,value):
    folder=workspace/value['directory'];manifest=value['manifest'];assert not manifest['mail_sent']
    assert set(tree(folder))==set(manifest['files'])|{'manifest.json'} and len(manifest['files'])==7
    assert json.loads((folder/'manifest.json').read_bytes())==manifest
    for n,row in manifest['files'].items():
        raw=(folder/n).read_bytes();assert row==dict(bytes=len(raw),sha256=sha(raw))
    return json.loads((folder/'analytics.json').read_bytes())
def oracle(plan):
    assert plan['capacity'][0]['whole_unit_capacity']==201 and plan['capacity'][0]['minimum_people_under_assumptions']==3
    assert plan['process'][0]['oee_fraction']==.5625 and plan['process'][0]['p90_minutes_linear_interpolation']==7.1
    assert plan['inventory'][0]['proposed_order_units']==18 and len(plan['dispatch']['ranked'])==len(plan['dispatch']['blocked'])==2
    assert all(plan[k] is False for k in ('external_system_writes','production_execution_authorized','purchase_authorized'))
def reference(plan):
    ref=plan['planning_reference'];assert [ref[k] for k in ('remaining_demand','dock_allocated_quantity','covered_quantity','uncovered_quantity')]==[160,25,85,50] and not ref['independently_verified']
    return ref
def copy_fixture(workspace,fixture):
    if {p.name for p in fixture.iterdir()}!=NAMES:raise ValueError('FIXTURE_INVENTORY_REFUSED')
    target=workspace/'inbox/sample-planning-report';target.mkdir()
    for f in fixture.iterdir():(target/f.name).write_bytes(f.read_bytes())
    return target
def exercise(workspace,application=None,fixture=None):
    development=application is not None;application=Path(application) if development else ROOT/'application';fixture=Path(fixture) if fixture else ROOT/'examples/planning-report'
    if not workspace.is_absolute() or workspace.exists() or not workspace.parent.is_dir():raise ValueError('NEW_PRIVATE_EXERCISE_REQUIRED')
    calls=[]
    def command(*args,expected=0):
        entry=[str(application/'workbench.py')]
        if development:entry=['-c',"import sys,runpy;sys.path.insert(0,sys.argv.pop(1));sys.argv.pop(0);runpy.run_path(sys.argv[0],run_name='__main__')",str(application),str(application/'workbench.py')]
        p=subprocess.run([sys.executable,'-I','-B','-X','utf8',*entry,'--workspace',str(workspace),*map(str,args)],capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=60);calls.append(args[0])
        if p.returncode!=expected:
            if workspace.is_dir():(workspace/'failed-command.log').write_bytes(p.stdout+p.stderr)
            raise AssertionError('Original CLI failed; private log retained.')
        return json.loads(p.stdout)
    command('init');command('import','--file','inbox/sample-scenario.json');copied=copy_fixture(workspace,fixture);inputs=tree(workspace/'inbox')
    first=command('plan','--project','sample-operations');oracle(first);assert first['snapshot']['completed_units']==25 and first['planning_reference'] is None
    assert 3*336//5==201 and .75*(300/360)*.9==.5625 and 10+15==25
    exported=command('export','--project','sample-operations');assert report(workspace,exported)==first;old_report=tree(workspace/exported['directory'])
    attached=command('attach-planning','--project','sample-operations','--directory','inbox/sample-planning-report','--expected',first['revision_sha256']);assert attached['sequence']==2
    second=command('plan','--project','sample-operations');ref=reference(second);assert second['snapshot']==first['snapshot'] and second['dispatch']==first['dispatch']
    assert ref['manifest_sha256']==sha((copied/'manifest.json').read_bytes())
    ingested=command('ingest','--project','sample-operations','--file','inbox/sample-events.json','--expected',second['revision_sha256']);assert ingested['sequence']==3 and ingested['inserted_events']==1
    before=tree(workspace);replayed=command('ingest','--project','sample-operations','--file','inbox/sample-events.json','--expected',ingested['revision_sha256']);assert not replayed['created'] and replayed['inserted_events']==0 and tree(workspace)==before
    final=command('plan','--project','sample-operations');oracle(final);reference(final);assert final['snapshot']['completed_units']==10+15+8==33 and final['snapshot']['completion_events']==3
    assert command('plan','--project','sample-operations','--revision','1')==first
    comparison=command('compare','--project','sample-operations','--left','1','--right','3');assert comparison['completion_units_before']==25 and comparison['completion_units_after']==33
    history=command('history','--project','sample-operations')['revisions'];assert len(history)==3 and history[1]['parent_sha256']==first['revision_sha256'] and history[2]['parent_sha256']==second['revision_sha256']
    exported_final=command('export','--project','sample-operations');assert report(workspace,exported_final)==final
    backed=command('backup');body=(workspace/backed['file']).read_bytes();assert backed['sha256']==sha(body) and backed['bytes']==len(body)
    with closing(sqlite3.connect((workspace/backed['file']).as_uri()+'?mode=ro',uri=True)) as db:assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)] and db.execute('SELECT COUNT(*) FROM revisions').fetchone()[0]==3
    before=tree(workspace);assert command('attach-planning','--project','sample-operations','--directory','inbox/sample-planning-report','--expected',first['revision_sha256'],expected=2)==dict(error='REVISION_CONFLICT') and tree(workspace)==before
    batch=json.loads((workspace/'inbox/sample-events.json').read_bytes());batch[0]['units']+=1;(workspace/'inbox/conflict.json').write_text(json.dumps(batch),encoding='utf-8');before=tree(workspace)
    assert command('ingest','--project','sample-operations','--file','inbox/conflict.json','--expected',final['revision_sha256'],expected=2)==dict(error='EVENT_IDENTITY_CONFLICT') and tree(workspace)==before
    bad=workspace/'inbox/bad-report';bad.mkdir()
    for f in copied.iterdir():(bad/f.name).write_bytes(f.read_bytes())
    original=(bad/'orders.csv').read_bytes();(bad/'orders.csv').write_bytes(original+b'fictional tamper');before=tree(workspace)
    assert command('attach-planning','--project','sample-operations','--directory','inbox/bad-report','--expected',final['revision_sha256'],expected=2)==dict(error='PLANNING_REPORT_BYTES_CHANGED') and tree(workspace)==before
    (bad/'orders.csv').write_bytes(original);(bad/'extra.json').write_bytes(b'{}');before=tree(workspace)
    assert command('attach-planning','--project','sample-operations','--directory','inbox/bad-report','--expected',final['revision_sha256'],expected=2)==dict(error='PLANNING_REPORT_INVENTORY') and tree(workspace)==before
    assert command('init',expected=2)['error'] and tree(workspace)==before
    assert command('show','--project','sample-operations')['revision_sha256']==final['revision_sha256'] and tree(workspace)==before
    assert tree(workspace/exported['directory'])==old_report and all(tree(workspace/'inbox')[n]==v for n,v in inputs.items())
    return dict(status='PASS',command_checks=len(calls),planning_totals=[160,25,85,50],initial_completions=25,final_completions=33,completion_events=3,inserted_events=1,replay_inserted_events=0,replay_created_revision=False,revisions=3,private_report_files=8,capacity=201,oee=.5625,reorder_units=18,report_hashes_independently_verified=True,old_report_unchanged=True,original_inputs_unchanged=True,planning_does_not_map_eligibility_or_completions=True,stale_revision_refused=True,changed_event_identity_refused=True,tampered_report_refused=True,extra_report_file_refused=True,historical_result_unchanged=True,backup_integrity_checked=True,saved_revision_reopened=True,existing_initialization_refused_without_writes=True,external_system_writes=False,production_execution_authorized=False,purchase_authorized=False,mail_sent=False)
