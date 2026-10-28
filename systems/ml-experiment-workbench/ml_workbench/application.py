"""Immutable datasets, reproducible preparation, separate holdouts, review and exports."""
from collections import Counter
import html
import sqlite3
import uuid
from . import contracts as c,fixtures,learner,metrics,runtime as r


def _dataset(con,identifier):
    c.token(identifier);row=con.execute('SELECT dataset_sha256,dataset_json FROM datasets WHERE dataset_id=?',(identifier,)).fetchone()
    if row is None:raise r.WorkbenchError('DATASET_NOT_FOUND')
    value=c.dataset(row[1].encode())
    if value['dataset_id']!=identifier or r.digest(r.encode(value))!=row[0]:raise r.WorkbenchError('DATASET_HASH_MISMATCH')
    return value,row[0]


def _experiment(con,identifier):
    c.token(identifier);row=con.execute('SELECT config_sha256,config_json,result_sha256,result_json FROM experiments WHERE experiment_id=?',(identifier,)).fetchone()
    if row is None:raise r.WorkbenchError('EXPERIMENT_NOT_FOUND')
    config=c.experiment(row[1].encode());result=r.decode(row[3].encode())
    if config['experiment_id']!=identifier or r.digest(r.encode(config))!=row[0] or r.digest(r.encode(result))!=row[2] or result['config_sha256']!=row[0] or result['dataset_sha256']!=config['dataset_sha256']:raise r.WorkbenchError('EXPERIMENT_HASH_MISMATCH')
    return dict(config=config,config_sha256=row[0],prepared=result,prepared_sha256=row[2])


def _evaluation(con,identifier):
    row=con.execute('SELECT evaluation_sha256,evaluation_json FROM evaluations WHERE experiment_id=?',(identifier,)).fetchone()
    if row is None:return None
    value=r.decode(row[1].encode())
    if r.digest(r.encode(value))!=row[0] or value['experiment_id']!=identifier:raise r.WorkbenchError('EVALUATION_HASH_MISMATCH')
    return dict(sha256=row[0],result=value)


def _review(con,artifact):
    row=con.execute('SELECT payload_json FROM reviews WHERE artifact_sha256=? ORDER BY row_version DESC LIMIT 1',(artifact,)).fetchone()
    return r.decode(row[0].encode()) if row else dict(status='pending',row_version=0)


def import_dataset(raw):
    value=c.dataset(raw);encoded=r.encode(value);sha=r.digest(encoded)
    with r.connect() as con:
        row=con.execute('SELECT dataset_sha256 FROM datasets WHERE dataset_id=?',(value['dataset_id'],)).fetchone()
        if row:
            if row[0]!=sha:raise r.WorkbenchError('DATASET_IMMUTABLE')
            return dict(dataset_id=value['dataset_id'],dataset_sha256=sha,created=False)
        if con.execute('SELECT COUNT(*) FROM datasets').fetchone()[0]>=50:raise r.WorkbenchError('DATASET_LIMIT')
        con.execute('INSERT INTO datasets VALUES(?,?,?)',(value['dataset_id'],sha,encoded.decode()))
    return dict(dataset_id=value['dataset_id'],dataset_sha256=sha,created=True)


def datasets():
    with r.connect() as con:rows=con.execute('SELECT dataset_id,dataset_sha256 FROM datasets ORDER BY dataset_id LIMIT 51').fetchall()
    if len(rows)>50:raise r.WorkbenchError('DATASET_LIMIT')
    return dict(datasets=[dict(dataset_id=row[0],dataset_sha256=row[1]) for row in rows])


def dataset(identifier):
    with r.connect() as con:value,sha=_dataset(con,identifier)
    return dict(dataset=value,dataset_sha256=sha)


def example(identifier):
    with r.connect() as con:value,sha=_dataset(con,identifier)
    config=r.decode(r.read_bytes(r.SOURCE/'examples/sample-experiment.json'));config['dataset_id']=identifier;config['dataset_sha256']=sha;return config


def example_file(identifier):
    config=example(identifier);name='inbox/'+uuid.uuid4().hex+'-experiment.json';r.write_new(r.local_path(name,False),r.encode(config));return dict(file=name,configuration=config)


def _choose(labels,scores,grid):
    candidates=[metrics.calculate(labels,scores,t) for t in grid]
    best=max(candidates,key=lambda m:(m['f1'] if m['f1'] is not None else -1,-abs(m['threshold']-.5),-m['threshold']))
    return best,[{key:m[key] for key in ('threshold','f1','accuracy')} for m in candidates]


def _predictions(rows,scores):return [dict(row_id=row['row_id'],group_id=row['group_id'],decision_day=row['decision_day'],outcome=row['outcome'],score=score) for row,score in zip(rows,scores)]


def _split_summary(parts):
    result={part:dict(rows=len(parts[part]),groups=len({row['group_id'] for row in parts[part]}),row_ids=[row['row_id'] for row in parts[part]],cohort_sha256=r.digest(r.encode(parts[part]))) for part in ('train','validation','test')}
    result['excluded']=parts['excluded'];result['excluded_by_reason']=dict(Counter(row['reason'] for row in parts['excluded']));return result


def prepare(raw):
    config=c.experiment(raw);encoded=r.encode(config);config_sha=r.digest(encoded)
    with r.connect() as con:
        existing=con.execute('SELECT config_sha256 FROM experiments WHERE experiment_id=?',(config['experiment_id'],)).fetchone()
        if existing:
            if existing[0]!=config_sha:raise r.WorkbenchError('EXPERIMENT_IMMUTABLE')
            return dict(experiment_id=config['experiment_id'],prepared_sha256=_experiment(con,config['experiment_id'])['prepared_sha256'],created=False)
        if con.execute('SELECT COUNT(*) FROM experiments').fetchone()[0]>=100:raise r.WorkbenchError('EXPERIMENT_LIMIT')
        data,data_sha=_dataset(con,config['dataset_id'])
        if data_sha!=config['dataset_sha256']:raise r.WorkbenchError('DATASET_PIN_MISMATCH')
        parts=c.partition(data,config);model=learner.fit(parts['train'],data['feature_names'],config['learner']);scores=learner.scores(model,parts['validation']);labels=[row['outcome'] for row in parts['validation']]
        validation,grid=_choose(labels,scores,config['thresholds']);baseline_scores=[model['training_prevalence']]*len(labels);baseline,baseline_grid=_choose(labels,baseline_scores,config['thresholds'])
        result=dict(format='outlands-ml-prepared-v1',implementation_version='0.1.0',dataset_sha256=data_sha,config_sha256=config_sha,model=model,model_sha256=r.digest(r.encode(model)),threshold=validation['threshold'],baseline_threshold=baseline['threshold'],training=metrics.calculate([row['outcome'] for row in parts['train']],learner.scores(model,parts['train']),validation['threshold']),validation=validation,baseline_validation=baseline,validation_grid=grid,baseline_validation_grid=baseline_grid,validation_predictions=_predictions(parts['validation'],scores),split=_split_summary(parts),threshold_source='validation_f1_then_nearest_half_then_lower',preprocessing_source='training_rows_only',test_evaluated=False)
        result_raw=r.encode(result);result_sha=r.digest(result_raw)
        if len(result_raw)>r.MAX_INPUT:raise r.WorkbenchError('RESULT_LIMIT')
        con.execute('INSERT INTO experiments VALUES(?,?,?,?,?,?)',(config['experiment_id'],config['dataset_id'],config_sha,encoded.decode(),result_sha,result_raw.decode()))
    return dict(experiment_id=config['experiment_id'],prepared_sha256=result_sha,created=True)


def experiments():
    with r.connect() as con:rows=con.execute('SELECT experiment_id,dataset_id,result_sha256 FROM experiments ORDER BY experiment_id LIMIT 101').fetchall()
    if len(rows)>100:raise r.WorkbenchError('EXPERIMENT_LIMIT')
    return dict(experiments=[dict(experiment_id=row[0],dataset_id=row[1],prepared_sha256=row[2]) for row in rows])


def show(identifier):
    with r.connect() as con:
        result=_experiment(con,identifier);evaluation=_evaluation(con,identifier)
        if evaluation and evaluation['result']['prepared_sha256']!=result['prepared_sha256']:raise r.WorkbenchError('EVALUATION_PARENT_MISMATCH')
        artifact=evaluation['sha256'] if evaluation else result['prepared_sha256'];review=_review(con,artifact)
    return dict(experiment_id=identifier,**result,evaluation=evaluation,artifact_sha256=artifact,review=review)


def evaluate(raw):
    value=r.decode(raw);c.fields(value,('experiment_id','expected_sha256'));c.hash_value(value['expected_sha256'])
    with r.connect() as con:
        record=_experiment(con,value['experiment_id'])
        if record['prepared_sha256']!=value['expected_sha256']:raise r.WorkbenchError('PREPARED_CONFLICT')
        previous=_evaluation(con,value['experiment_id'])
        if previous:return dict(evaluation=previous,created=False)
        data,data_sha=_dataset(con,record['config']['dataset_id'])
        if data_sha!=record['config']['dataset_sha256']:raise r.WorkbenchError('DATASET_PIN_MISMATCH')
        parts=c.partition(data,record['config']);prepared=record['prepared'];rows=parts['test']
        if r.digest(r.encode(rows))!=prepared['split']['test']['cohort_sha256']:raise r.WorkbenchError('COHORT_HASH_MISMATCH')
        scores=learner.scores(prepared['model'],rows);labels=[row['outcome'] for row in rows]
        result=dict(format='outlands-ml-evaluation-v1',experiment_id=value['experiment_id'],prepared_sha256=record['prepared_sha256'],model_sha256=prepared['model_sha256'],threshold=prepared['threshold'],baseline_threshold=prepared['baseline_threshold'],test_cohort_sha256=prepared['split']['test']['cohort_sha256'],metrics=metrics.calculate(labels,scores,prepared['threshold']),baseline_metrics=metrics.calculate(labels,[prepared['model']['training_prevalence']]*len(rows),prepared['baseline_threshold']),predictions=_predictions(rows,scores),protocol='one_immutable_evaluation_per_experiment_not_access_control',real_world_accuracy_established=False)
        raw=r.encode(result);sha=r.digest(raw)
        if len(raw)>r.MAX_INPUT:raise r.WorkbenchError('RESULT_LIMIT')
        con.execute('INSERT INTO evaluations VALUES(?,?,?)',(value['experiment_id'],sha,raw.decode()))
    return dict(evaluation=dict(sha256=sha,result=result),created=True)


def review(raw):
    value=r.decode(raw);c.fields(value,('experiment_id','artifact_sha256','expected_version','status','actor','note','checks'));c.hash_value(value['artifact_sha256']);c.integer(value['expected_version'],0,1000);c.text(value['actor'],80);c.text(value['note'],1000,empty=True);c.fields(value['checks'],('quality','privacy','rights','context'))
    if value['status'] not in ('pending','approved','rejected') or any(type(flag) is not bool for flag in value['checks'].values()):raise r.WorkbenchError('REVIEW_INVALID')
    if value['status']=='approved' and not all(value['checks'].values()):raise r.WorkbenchError('REVIEW_CHECKS_REQUIRED')
    with r.connect() as con:
        prepared=_experiment(con,value['experiment_id']);evaluation=_evaluation(con,value['experiment_id']);artifact=evaluation['sha256'] if evaluation else prepared['prepared_sha256']
        if artifact!=value['artifact_sha256']:raise r.WorkbenchError('ARTIFACT_CONFLICT')
        old=_review(con,artifact)
        if old['row_version']!=value['expected_version']:raise r.WorkbenchError('REVIEW_VERSION_CONFLICT')
        if con.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]>=5000:raise r.WorkbenchError('REVIEW_LIMIT')
        result={k:v for k,v in value.items() if k!='expected_version'};result['row_version']=old['row_version']+1;con.execute('INSERT INTO reviews VALUES(?,?,?)',(artifact,result['row_version'],r.encode(result).decode()))
    return dict(review=result,operator_assertions_unverified=True)


def compare(left,right):
    with r.DATABASE_LOCK:
        a=show(left);b=show(right)
    common=a['prepared']['split']['test']['cohort_sha256']==b['prepared']['split']['test']['cohort_sha256'];evaluated=bool(a['evaluation'] and b['evaluation'])
    result=dict(left=left,right=right,same_test_cohort=common,both_evaluated=evaluated,validation_f1=dict(left=a['prepared']['validation']['f1'],right=b['prepared']['validation']['f1']),test_comparison_available=common and evaluated,warning='Repeated experiments can turn the holdout into development data; a matching cohort is not independent final validation.')
    if common and evaluated:
        am=a['evaluation']['result']['metrics'];bm=b['evaluation']['result']['metrics'];result['test']={key:dict(left=am[key],right=bm[key],delta_right_minus_left=bm[key]-am[key] if am[key] is not None and bm[key] is not None else None) for key in ('roc_auc','average_precision','brier','accuracy','f1')}
    return result


def export(identifier):
    with r.DATABASE_LOCK:
        record=show(identifier)
        if record['evaluation'] is None:raise r.WorkbenchError('EVALUATION_REQUIRED_FOR_EXPORT')
        if record['review']['status']!='approved':raise r.WorkbenchError('APPROVAL_REQUIRED')
        prepared=record['prepared'];evaluation=record['evaluation']['result'];model=prepared['model']
        data={'configuration.json':r.encode(record['config']),'model.json':r.encode(model),'preparation.json':r.encode(prepared),'evaluation.json':r.encode(evaluation),'review.json':r.encode(record['review'])}
        summary=dict(experiment_id=identifier,dataset_id=record['config']['dataset_id'],dataset_sha256=prepared['dataset_sha256'],split=prepared['split'],selected_threshold=prepared['threshold'],validation=prepared['validation'],test=evaluation['metrics'],baseline_test=evaluation['baseline_metrics'],scope='Private local binary baseline; scores are not calibrated; synthetic results do not establish real-world accuracy.')
        data['summary.json']=r.encode(summary)
        page='<!doctype html><html lang="en"><meta charset="utf-8"><title>ML experiment report</title><style>body{max-width:1000px;margin:30px auto;font:16px system-ui;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Offline ML experiment</h1><p>Private report. Review before sharing. Scores are not calibrated.</p><pre>'+html.escape(r.encode(summary).decode())+'</pre></html>'
        data['report.html']=page.encode();manifest=dict(format='outlands-ml-report-v1',experiment_id=identifier,artifact_sha256=record['artifact_sha256'],review_version=record['review']['row_version'],dataset_sha256=prepared['dataset_sha256'],model_sha256=prepared['model_sha256'],implementation_version='0.1.0',files={name:dict(bytes=len(raw),sha256=r.digest(raw)) for name,raw in sorted(data.items())},public_release_authorized=False)
        directory=r.local_path('reports/'+uuid.uuid4().hex,False);r.mkdir(directory)
        for name,raw in sorted(data.items()):r.write_new(directory/name,raw)
        r.write_new(directory/'manifest.json',r.encode(manifest))
    return dict(directory=directory.relative_to(r.ROOT).as_posix(),manifest=manifest)


def backup():
    destination=r.local_path('backups/'+uuid.uuid4().hex+'.sqlite3',False);r.write_new(destination,b'')
    with r.connect() as source,r.io_errors(),r.guarded._store_scope(destination,initial=True):
        target=sqlite3.connect(destination.as_uri()+'?mode=rw',uri=True)
        try:source.backup(target);r.validate_schema(target)
        finally:target.close()
    raw=r.read_bytes(destination,r.MAX_STORE);return dict(file=destination.relative_to(r.ROOT).as_posix(),bytes=len(raw),sha256=r.digest(raw),scope='database_only_including_private_datasets_models_and_reviews')


def demo():
    data=fixtures.dataset();raw=r.encode(data);r.write_new(r.local_path('inbox/fictional-dataset.json',False),raw);import_dataset(raw);config=example('sample-ml');first=prepare(r.encode(config));before=show(config['experiment_id']);evaluation=evaluate(r.encode(dict(experiment_id=config['experiment_id'],expected_sha256=first['prepared_sha256'])));after=show(config['experiment_id'])
    review(r.encode(dict(experiment_id=config['experiment_id'],artifact_sha256=after['artifact_sha256'],expected_version=0,status='approved',actor='sample_reviewer',note='Fictional experiment review',checks=dict(quality=True,privacy=True,rights=True,context=True))))
    report=export(config['experiment_id']);config['experiment_id']='sample-comparison';config['learner']['l2']=.2;second=prepare(r.encode(config));evaluate(r.encode(dict(experiment_id=config['experiment_id'],expected_sha256=second['prepared_sha256'])));comparison=compare('sample-baseline','sample-comparison');saved=backup();parts=before['prepared']['split'];tested=evaluation['evaluation']['result']['metrics']
    return dict(mode='FICTIONAL_ML_EXPERIMENT_DEMO',rows=len(data['rows']),training_rows=parts['train']['rows'],validation_rows=parts['validation']['rows'],test_rows=parts['test']['rows'],excluded_rows=len(parts['excluded']),prepared_without_test_metrics=before['evaluation'] is None,threshold=before['prepared']['threshold'],test_auc=tested['roc_auc'],test_brier=tested['brier'],experiments=len(experiments()['experiments']),comparison_same_cohort=comparison['same_test_cohort'],private_report_files=len(report['manifest']['files'])+1,backup_validated=saved['bytes']>0,real_customer_data_or_pretrained_weights_included=False,scores_calibrated=False)
