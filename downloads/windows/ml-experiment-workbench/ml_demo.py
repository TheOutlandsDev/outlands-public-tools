"""Original CLI exercise with independent numerical, report and restart oracles."""
from contextlib import closing
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
def sha(data):return hashlib.sha256(data).hexdigest()
def encode(value):return (json.dumps(value,ensure_ascii=True,allow_nan=False,sort_keys=True,indent=2)+'\n').encode()
def tree(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
def seed_demo():
    from ml_workbench import application as app,runtime as r,fixtures
    raw=r.encode(fixtures.dataset());r.write_new(r.local_path('inbox/fictional-dataset.json',False),raw);app.import_dataset(raw)

def numerical(record,data):
    # Literal fixture cohorts and independently recomputed arithmetic; no learner/metrics imports.
    prepared=record['prepared'];rows={row['row_id']:row for row in data['rows']};parts={part:[rows['sample-row-'+str(i)] for i in days] for part,days in [('train',range(118)),('validation',range(130,178)),('test',range(190,238))]}
    assert len(data['rows'])==240 and len(prepared['split']['excluded'])==26
    for part,selected in parts.items():assert prepared['split'][part]['row_ids']==[row['row_id'] for row in selected]
    groups=[{row['group_id'] for row in parts[part]} for part in ('train','validation','test')];assert all(groups[i].isdisjoint(groups[j]) for i,j in ((0,1),(0,2),(1,2)))
    model=prepared['model'];p=model['preprocessing'];assert p['feature_names']==data['feature_names'] and not model['scores_calibrated'] and not model['executable_serialization']
    for i,name in enumerate(data['feature_names']):
        values=[row['features'][name] for row in parts['train'] if row['features'][name] is not None];mean=sum(values)/len(values);scale=(sum((x-mean)**2 for x in values)/len(values))**.5
        assert math.isclose(mean,p['means'][i],abs_tol=1e-12) and math.isclose(scale,p['scales'][i],abs_tol=1e-12)
    def scores(part):
        values=[]
        for row in parts[part]:
            z=model['intercept']+sum(w*((row['features'][name] if row['features'][name] is not None else mean)-mean)/scale for name,mean,scale,w in zip(p['feature_names'],p['means'],p['scales'],model['weights']));values.append(1/(1+math.exp(-z)))
        return values
    def metrics(part,values,threshold):
        labels=[row['outcome'] for row in parts[part]];positive=[s for y,s in zip(labels,values) if y];negative=[s for y,s in zip(labels,values) if not y]
        tp=sum(y==1 and s>=threshold for y,s in zip(labels,values));fp=sum(y==0 and s>=threshold for y,s in zip(labels,values));fn=sum(y==1 and s<threshold for y,s in zip(labels,values));tn=len(labels)-tp-fp-fn
        return dict(roc_auc=sum(1 if a>b else .5 if a==b else 0 for a in positive for b in negative)/(len(positive)*len(negative)),brier=sum((s-y)**2 for y,s in zip(labels,values))/len(labels),accuracy=(tp+tn)/len(labels),f1=2*tp/(2*tp+fp+fn),confusion=dict(tp=tp,fp=fp,tn=tn,fn=fn))
    validation=scores('validation');choices=[(metrics('validation',validation,t)['f1'],-abs(t-.5),-t,t) for t in record['config']['thresholds']];assert prepared['threshold']==max(choices)[3]==.4
    for saved,computed in zip(prepared['validation_predictions'],validation):assert math.isclose(saved['score'],computed,abs_tol=1e-12)
    if record['evaluation']:
        evaluation=record['evaluation']['result'];values=scores('test');expected=metrics('test',values,prepared['threshold'])
        assert evaluation['model_sha256']==prepared['model_sha256'] and evaluation['threshold']==prepared['threshold']
        for key in ('roc_auc','brier','accuracy','f1'):assert math.isclose(evaluation['metrics'][key],expected[key],abs_tol=1e-12)
        assert evaluation['metrics']['confusion']==expected['confusion']
        for saved,computed in zip(evaluation['predictions'],values):assert math.isclose(saved['score'],computed,abs_tol=1e-12)
        baseline=metrics('test',[model['training_prevalence']]*48,prepared['baseline_threshold'])
        for key in ('roc_auc','brier','accuracy','f1'):assert math.isclose(evaluation['baseline_metrics'][key],baseline[key],abs_tol=1e-12)
        assert math.isclose(expected['roc_auc'],.883478,abs_tol=1e-6) and math.isclose(expected['brier'],.167048,abs_tol=1e-6)
    else:assert prepared['test_evaluated'] is False and 'test_predictions' not in prepared and 'test_metrics' not in prepared

def verify_report(workspace,result,record,data):
    directory=workspace/result['directory'];manifest=json.loads((directory/'manifest.json').read_bytes());assert manifest==result['manifest']
    expected={'configuration.json','model.json','preparation.json','evaluation.json','review.json','summary.json','report.html'}
    assert set(manifest['files'])==expected and {p.name for p in directory.iterdir()}==expected|{'manifest.json'} and manifest['public_release_authorized'] is False
    for name,row in manifest['files'].items():
        raw=(directory/name).read_bytes();assert row==dict(bytes=len(raw),sha256=sha(raw))
    assert json.loads((directory/'model.json').read_bytes())==record['prepared']['model'] and manifest['artifact_sha256']==record['artifact_sha256']
    assert json.loads((directory/'evaluation.json').read_bytes())==record['evaluation']['result'];numerical(record,data)

def exercise(workspace,application=None):
    development=application is not None;app=Path(application) if development else ROOT/'application';workspace=Path(workspace)
    if not workspace.is_absolute() or workspace.exists() or not workspace.parent.is_dir():raise ValueError('NEW_PRIVATE_EXERCISE_REQUIRED')
    sys.path.insert(0,str(app));from ml_workbench import fixtures
    data=fixtures.dataset();count=0
    def cli(*args,expected=0):
        nonlocal count
        entry=[str(app/'workbench.py')]
        if development:entry=['-c',"import sys,runpy;sys.path.insert(0,sys.argv.pop(1));sys.argv.pop(0);runpy.run_path(sys.argv[0],run_name='__main__')",str(app),str(app/'workbench.py')]
        p=subprocess.run([sys.executable,'-I','-B','-X','utf8',*entry,'--workspace',str(workspace),*map(str,args)],capture_output=True,timeout=90,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        if p.returncode!=expected:
            if workspace.is_dir():(workspace/'failed-command.log').write_bytes(p.stdout+p.stderr)
            raise AssertionError('Original CLI exercise failed; preserve the workspace.')
        count+=1;return json.loads(p.stdout)
    def write(name,value):
        path=workspace/'inbox'/name;path.write_bytes(encode(value));return 'inbox/'+name
    def review(record,expected=0,checks=True):return dict(experiment_id='sample-baseline',artifact_sha256=record['artifact_sha256'],expected_version=expected,status='approved',actor='sample_reviewer',note='Fictional practice review',checks=dict.fromkeys(('quality','privacy','rights','context'),checks))
    cli('init');invalid=copy.deepcopy(data);invalid['rows'][1]['feature_available_day']['signal']=2;cli('import','--file',write('future.json',invalid),expected=2)
    path=write('fictional.json',data);first=cli('import','--file',path);assert first['created'];assert not cli('import','--file',path)['created'];original_inputs=tree(workspace/'inbox')
    config=cli('example','--dataset','sample-ml')['configuration'];invalid=copy.deepcopy(config);invalid['split']['train_end_day']=140;cli('prepare','--file',write('chronology.json',invalid),expected=2)
    configuration=write('experiment.json',config);prepared=cli('prepare','--file',configuration);assert prepared['created'];record=cli('show','--experiment','sample-baseline');assert record['evaluation'] is None;numerical(record,data)
    cli('export','--experiment','sample-baseline',expected=2);cli('review','--file',write('prepared-review.json',review(record)))
    cli('evaluate','--experiment','sample-baseline','--expected','0'*64,expected=2);evaluated=cli('evaluate','--experiment','sample-baseline','--expected',prepared['prepared_sha256']);assert evaluated['created']
    record=cli('show','--experiment','sample-baseline');assert record['review']==dict(status='pending',row_version=0);numerical(record,data)
    cli('export','--experiment','sample-baseline',expected=2);cli('review','--file',write('missing-review.json',review(record,checks=False)),expected=2)
    approved=write('review.json',review(record));cli('review','--file',approved);cli('review','--file',approved,expected=2)
    record['review']={k:v for k,v in review(record).items() if k!='expected_version'};record['review']['row_version']=1
    report=cli('export','--experiment','sample-baseline');verify_report(workspace,report,record,data);old_report=tree(workspace/report['directory'])
    assert not cli('prepare','--file',configuration)['created'];assert cli('show','--experiment','sample-baseline')==record;assert not cli('evaluate','--experiment','sample-baseline','--expected',prepared['prepared_sha256'])['created']
    second=copy.deepcopy(config);second['learner']['l2']=.2;cli('prepare','--file',write('immutable-conflict.json',second),expected=2);second['experiment_id']='sample-comparison';second_prepared=cli('prepare','--file',write('comparison.json',second));assert second_prepared['created']
    assert not cli('compare','--left','sample-baseline','--right','sample-comparison')['test_comparison_available'];cli('evaluate','--experiment','sample-comparison','--expected',second_prepared['prepared_sha256']);comparison=cli('compare','--left','sample-baseline','--right','sample-comparison');assert comparison['same_test_cohort'] and comparison['test_comparison_available']
    backup=cli('backup');raw=(workspace/backup['file']).read_bytes();assert sha(raw)==backup['sha256']
    with closing(sqlite3.connect((workspace/backup['file']).as_uri()+'?mode=ro',uri=True)) as con:assert con.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
    saved=tree(workspace);assert cli('show','--experiment','sample-baseline')==record and tree(workspace)==saved;cli('init',expected=2);assert tree(workspace)==saved and tree(workspace/report['directory'])==old_report
    for name,digest in original_inputs.items():assert sha((workspace/'inbox'/name).read_bytes())==digest
    assert count==29
    m=record['evaluation']['result']['metrics'];return dict(status='PASS',command_checks=count,rows=240,training_rows=118,validation_rows=48,test_rows=48,excluded_rows=26,experiments=2,threshold=.4,test_auc=m['roc_auc'],test_brier=m['brier'],private_report_files=8,train_only_preprocessing_independently_checked=True,model_predictions_independently_replayed=True,metrics_independently_recomputed=True,validation_threshold_independently_checked=True,prepared_without_test_metrics=True,evaluation_resets_review=True,missing_review_checks_refused=True,stale_review_refused=True,future_feature_refused=True,invalid_chronology_refused=True,immutable_conflict_refused=True,idempotent_replay=True,same_test_cohort=True,comparison_waits_for_evaluations=True,report_hashes_independently_verified=True,old_report_unchanged=True,original_inputs_unchanged=True,backup_integrity_checked=True,saved_experiment_reopened=True,existing_initialization_refused_without_writes=True,real_world_accuracy_established=False,scores_calibrated=False,pretrained_weights_included=False,complete_restore_performed=False)
