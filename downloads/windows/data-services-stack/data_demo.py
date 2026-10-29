"""Invented CLI exercise with independent numerical and preservation checks."""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent

def tree(root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

def exercise(workspace,application=None):
    development_source=application is not None
    application=Path(application) if application else ROOT/'application'
    if not workspace.is_absolute() or workspace.exists() or not workspace.parent.is_dir():raise ValueError('NEW_PRIVATE_EXERCISE_REQUIRED')
    sys.path.insert(0,str(application));from data_services import files
    workspace=files.selected(workspace,output=True);files.mkdir(workspace)
    inputs=workspace/'inputs';exports=workspace/'exports';files.mkdir(inputs);files.mkdir(exports);journal=workspace/'journal';calls=[]
    config=dict(version=1,jobs=[dict(id='sample',input_format='jsonl',method='mean',horizon=3,window=3,season=1,min_history=3,route='sample_route',max_attempts=3)])
    raw=b'\n'.join(json.dumps(dict(series='sample',period=i,value=2*(i+1)),sort_keys=True,separators=(',',':')).encode() for i in range(6))
    files.write_new(inputs/'jobs.json',json.dumps(config).encode());files.write_new(inputs/'sample.jsonl',raw);files.write_new(inputs/'invalid.jsonl',b'null')
    original_inputs=tree(inputs)
    def command(*args,expected=0):
        entry=[str(application/'stack.py')]
        if development_source:
            # System Python's isolated mode omits the script directory. The
            # shipped embedded runtime instead pins application in its _pth.
            entry=['-c','import sys;sys.path.insert(0,sys.argv.pop(1));from data_services.cli import main;raise SystemExit(main())',str(application)]
        p=subprocess.run([sys.executable,'-I','-B','-X','utf8',*entry,'--workspace',str(journal),*map(str,args)],capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=60)
        calls.append(args[0])
        if p.returncode!=expected:
            files.write_new(workspace/'failed-command.log',p.stdout+p.stderr)
            raise AssertionError('Original CLI failed; private log retained in the exercise.')
        return json.loads(p.stdout)
    source=command('source-check');assert source['status']=='PASS'
    command('init');command('configure','--config',inputs/'jobs.json')
    assert command('run','--job','sample','--key','sample_run','--input',inputs/'sample.jsonl')['state']=='COMPLETED'
    assert command('run','--job','sample','--key','rejected_run','--input',inputs/'invalid.jsonl',expected=2)['state']=='REJECTED'
    retry=command('dispatch-fake','--now',0,'--outcomes','retry');assert retry==[dict(key='sample_run',state='PENDING',code='RETRY_SCHEDULED',attempts=1,next_attempt=1)]
    saved=command('status');assert saved['queue']==retry
    assert command('dispatch-fake','--now',0)==[]
    accepted=command('dispatch-fake','--now',1);assert accepted==[dict(key='sample_run',state='ACCEPTED',code='ADAPTER_ACCEPTED',attempts=2,next_attempt=None)]
    command('report-delivery','--key','sample_run','--receipt','fake_receipt')
    command('run','--job','sample','--key','uncertain_run','--input',inputs/'sample.jsonl')
    unknown=command('dispatch-fake','--now',2,'--outcomes','accepted_then_unknown');assert unknown==[dict(key='uncertain_run',state='REVIEW_REQUIRED',code='DELIVERY_UNCERTAIN',attempts=1,next_attempt=None)]
    reopened=command('status');assert next(x for x in reopened['queue'] if x['key']=='uncertain_run')==unknown[0]
    assert command('dispatch-fake','--now',100)==[]
    result=command('result','--key','sample_run');other=command('result','--key','uncertain_run')
    numbers=[2*(i+1) for i in range(6)];prediction=sum(numbers[-3:])/3
    errors=[numbers[i]-sum(numbers[i-3:i])/3 for i in range(3,6)]
    expected_score=dict(count=len(errors),mae=sum(abs(x) for x in errors)/len(errors),rmse=math.sqrt(sum(x*x for x in errors)/len(errors)))
    for run in (result,other):
        assert run['result']['accepted']==6 and run['result']['duplicates']==0 and run['result']['score']==expected_score
        assert run['result']['forecast']==[dict(series='sample',period=i,value=prediction) for i in (6,7,8)]
    command('export','--key','sample_run','--output',exports/'sample-result.json')
    assert json.loads((exports/'sample-result.json').read_bytes())==result
    before=tree(workspace)
    refusal=command('report-delivery','--key','uncertain_run','--receipt','fake_receipt',expected=2);assert refusal==dict(status='ERROR',code='DELIVERY_REPORT_REFUSED') and tree(workspace)==before
    current=command('status');head=current['head_sha256']
    command('run','--job','sample','--key','sample_run','--input',inputs/'sample.jsonl')
    assert tree(workspace)==before
    assert command('demo',expected=2)['status']=='ERROR' and tree(workspace)==before
    final=command('status');assert final['head_sha256']==head and not final['recovery_required'] and final['orphan_generations']==0
    assert tree(inputs)==original_inputs
    return dict(status='PASS',command_checks=len(calls),input_records=6,duplicate_records=0,predictions=[prediction]*3,holdout_predictions=3,mae=expected_score['mae'],rmse=expected_score['rmse'],retry_attempts=1,retry_due_tick=1,not_due_attempts=0,accepted_attempts=2,unknown_attempts=1,unknown_state='REVIEW_REQUIRED',future_replay_calls=0,invalid_input_refused=True,uncertain_delivery_assertion_refused=True,idempotent_run_preserves_journal=True,existing_demo_refused_without_writes=True,input_bytes_unchanged=True,result_export_independently_read=True,saved_results_reopened=True,real_delivery_verified=False,real_forecast_usefulness_measured=False,automatic_dispatch=False)
