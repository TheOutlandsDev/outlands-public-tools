"""Inspect the preserved kit, prepare an exercise, or check reviewed fixtures."""
import argparse
import ast
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent
TASKS=['eval_001_pathlib_json_loader','eval_002_secure_subprocess','eval_003_typed_validation','eval_004_mutable_default','eval_005_csv_summary']
def sha(raw):return hashlib.sha256(raw).hexdigest()

def ordinary(value,exists=True):
    p=Path(os.path.abspath(value))
    for part in (p,*p.parents):
        try:s=part.lstat()
        except FileNotFoundError:
            if part==p and not exists:continue
            raise ValueError('PATH_UNAVAILABLE') from None
        if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('LINK_PATH_REFUSED')
    return p

def verify_original():
    b=json.loads((ROOT/'BASELINE.json').read_bytes())
    if b['original_files']!=63 or len(b['original_source_sha256'])!=63:raise ValueError('ORIGINAL_INVENTORY_CHANGED')
    for name,pin in b['original_source_sha256'].items():
        p=ordinary(ROOT/name)
        if not p.is_file() or sha(p.read_bytes())!=pin:raise ValueError('ORIGINAL_BYTES_CHANGED')
    return b

def inspect():
    b=verify_original();manifest=json.loads((ROOT/'original/02_source_catalog/source_manifest.json').read_bytes())
    return dict(status='SOURCE_MATCH',original_files=b['original_files'],example_tests=8,evaluation_test_definitions=18,tasks=TASKS,source_links=len(manifest),runtime_dependencies=0,model_or_agent_included=False,third_party_content_bundled=False)

def child_environment():
    env={k:v for k,v in os.environ.items() if not k.upper().startswith(('PYTHON','PIP_','LD_','DYLD_'))}
    env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_COLORS='0',NO_COLOR='1')
    return env

def observe(mode,task=None):
    verify_original()
    if mode not in ('examples','starter','reference') or mode!='examples' and task not in TASKS:raise ValueError('UNKNOWN_EVALUATION')
    cmd=[sys.executable,'-I','-B',str(ROOT/'probe.py'),'--mode',mode]
    if task is not None:cmd+=['--task',task]
    with tempfile.TemporaryDirectory(prefix='seed-observe-') as temp:
        r=subprocess.run(cmd,cwd=temp,env=child_environment(),capture_output=True,text=True,timeout=60)
    if r.returncode:raise ValueError('FIXTURE_PROBE_FAILED')
    v=json.loads(r.stdout)
    if v['skipped'] or v['warnings'] or v['unreviewed_runtime_attempts'] or v['audit_canaries_refused']!=3:raise ValueError('UNEXPECTED_FIXTURE_SIDE_EFFECT')
    return v

def starter_matches(value):
    expected=json.loads((ROOT/'STARTER-CONTRACT.json').read_bytes())[value['task']]
    keys=('declared_methods','framework_entries','framework_started','actual_methods_started','passed','failures','errors','import_failures','skipped','started_ids','passed_ids','failure_ids','error_types')
    return {k:value[k] for k in keys}==expected

def prepare(task,out):
    verify_original()
    if task not in TASKS:raise ValueError('UNKNOWN_EVALUATION')
    out=ordinary(out,False)
    if os.path.lexists(out):raise ValueError('OUTPUT_EXISTS')
    if out.is_relative_to(ROOT):raise ValueError('OUTPUT_MUST_BE_OUTSIDE_PACKAGE')
    base=ROOT/'original/05_evals'/task
    source_files=[p for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    if len(source_files)!=5:raise ValueError('EXERCISE_INVENTORY_CHANGED')
    payloads={p.relative_to(base).as_posix():p.read_bytes() for p in source_files}
    out.mkdir()
    rows=[]
    for name,raw in sorted(payloads.items()):
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(raw)
        rows.append(dict(path=name,bytes=len(raw),sha256=sha(raw)))
    with (out/'COPY-MANIFEST.json').open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(dict(schema=1,task=task,files=rows,originals_changed=False),indent=2)+'\n')
    return dict(status='EXERCISE_PREPARED',task=task,files=5,executed_code=False,originals_changed=False)

def original_cli_checks():
    verify_original()
    with tempfile.TemporaryDirectory(prefix='seed-original-cli-') as temp:
        work=Path(temp)/'kit';shutil.copytree(ROOT/'original',work,ignore=shutil.ignore_patterns('__pycache__'))
        def run(script,*args):
            r=subprocess.run([sys.executable,'-B',str(work/'scripts'/script),*args],cwd=temp,env=child_environment(),capture_output=True,text=True,timeout=90)
            if r.returncode:raise ValueError('ORIGINAL_CLI_CHECK_FAILED')
            return r
        integrity=run('check_pack_integrity.py')
        if '39 source records' not in integrity.stdout:raise ValueError('SOURCE_RECORD_COUNT_CHANGED')
        examples=run('run_example_tests.py')
        if 'Ran 8 tests' not in examples.stderr or 'OK' not in examples.stderr:raise ValueError('EXAMPLE_CLI_DISCOVERY_CHANGED')
        run('catalog_to_markdown.py')
        index=(work/'02_source_catalog/source_manifest_index.md').read_text(encoding='utf-8')
        if index.count('\n## ')!=39:raise ValueError('CATALOG_REGENERATION_CHANGED')
        # Exercise the unchanged legacy template only with a known reference
        # in a disposable copy. The shipped original starter is never changed.
        task=TASKS[3]
        shutil.copyfile(ROOT/'references'/task/'starter/tagger.py',work/'05_evals'/task/'starter/tagger.py')
        example=run('eval_runner_template.py','05_evals/'+task)
        if 'Ran 2 tests' not in example.stderr or 'OK' not in example.stderr:raise ValueError('LEGACY_EVAL_TEMPLATE_CHANGED')
    verify_original()
    return dict(integrity=True,example_runner=True,catalog_regeneration_in_disposable_copy=True,legacy_template_with_separate_reference=True,original_drive_or_package_modified=False)

def check():
    source=inspect();examples=observe('examples')
    if not examples['success'] or examples['passed']!=8 or examples['actual_methods_started']!=8:raise ValueError('EXAMPLE_REGRESSION')
    references=[observe('reference',t) for t in TASKS]
    if sum(v['passed'] for v in references)!=18 or any(not v['success'] or v['actual_methods_started']!=v['declared_methods'] for v in references):raise ValueError('REFERENCE_REGRESSION')
    starters=[observe('starter',t) for t in TASKS]
    if not all(starter_matches(v) for v in starters):raise ValueError('STARTER_BASELINE_CHANGED')
    cli=original_cli_checks()
    return dict(schema=1,status='PASS',source=source,examples=examples,references=references,starters=starters,
                positive_example_and_reference_methods=26,positive_passed=26,starter_declared_methods=18,
                starter_actual_methods=sum(v['actual_methods_started'] for v in starters),starter_framework_entries=sum(v['framework_started'] for v in starters),
                starter_passed=sum(v['passed'] for v in starters),starter_failures=sum(v['failures'] for v in starters),starter_errors=sum(v['errors'] for v in starters),
                starter_import_failures=sum(v['import_failures'] for v in starters),starter_outcomes_match=True,original_cli=cli,
                intentionally_bad_examples_executed=False,model_training_or_inference_performed=False,external_sources_fetched=False)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    s.add_parser('inspect')
    e=s.add_parser('evaluate');e.add_argument('--mode',required=True,choices=('starter','reference'));e.add_argument('--task',required=True,choices=TASKS)
    c=s.add_parser('check');c.add_argument('--report',type=Path)
    use=s.add_parser('prepare');use.add_argument('--task',required=True,choices=TASKS);use.add_argument('--out',required=True,type=Path)
    a=p.parse_args(argv)
    try:
        report=None
        if a.command=='check' and a.report:
            report=ordinary(a.report,False)
            if os.path.lexists(report):raise ValueError('OUTPUT_EXISTS')
            if report.is_relative_to(ROOT):raise ValueError('OUTPUT_MUST_BE_OUTSIDE_PACKAGE')
        if a.command=='inspect':value=inspect()
        elif a.command=='prepare':value=prepare(a.task,a.out)
        elif a.command=='evaluate':
            value=observe(a.mode,a.task);value['classification']='EXPECTED_STARTER_BASELINE' if a.mode=='starter' and starter_matches(value) else 'REFERENCE_PASS' if a.mode=='reference' and value['success'] else 'UNEXPECTED_OUTCOME'
            if value['classification']=='UNEXPECTED_OUTCOME':raise ValueError('EVALUATION_REGRESSION')
        else:value=check()
        if report:
            with report.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,indent=2)+'\n')
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as error:
        code=str(error) if isinstance(error,ValueError) and str(error).replace('_','').isupper() and ' ' not in str(error) else 'KIT_OPERATION_FAILED'
        print(json.dumps(dict(status='ERROR',code=code)));return 2
    print(json.dumps(value));return 0

if __name__=='__main__':raise SystemExit(main())
