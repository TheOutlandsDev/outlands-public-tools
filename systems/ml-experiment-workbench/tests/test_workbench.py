"""Fictional timing/group, independent numerical, application, HTTP and native tests."""
from contextlib import closing
import copy
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from ml_workbench import application as app,contracts as c,fixtures,learner,metrics,runtime as r,web


def config():return json.loads((APP/'examples/sample-experiment.json').read_text(encoding='utf-8'))
def validated():return c.dataset(r.encode(fixtures.dataset()))
def parts():return c.partition(validated(),c.experiment(r.encode(config())))


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close)
        self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize()
    def load(self):return app.import_dataset(r.encode(fixtures.dataset()))
    def prepare(self,identifier='sample-baseline',changes=None):
        self.load();value=app.example('sample-ml');value['experiment_id']=identifier
        if changes:value['learner'].update(changes)
        return app.prepare(r.encode(value))
    def evaluate(self,identifier='sample-baseline'):
        self.prepare(identifier);record=app.show(identifier);return app.evaluate(r.encode(dict(experiment_id=identifier,expected_sha256=record['prepared_sha256'])))
    def approve(self,identifier='sample-baseline',**changes):
        record=app.show(identifier);value=dict(experiment_id=identifier,artifact_sha256=record['artifact_sha256'],expected_version=record['review']['row_version'],status='approved',actor='sample_reviewer',note='',checks=dict(quality=True,privacy=True,rights=True,context=True));value.update(changes);return app.review(r.encode(value))


class Numerical(unittest.TestCase):
    def test_confusion_known_metrics(self):
        result=metrics.calculate([0,0,1,1],[.1,.8,.7,.9],.75);self.assertEqual(result['confusion'],dict(tp=1,fp=1,tn=1,fn=1));self.assertEqual(result['f1'],.5);self.assertEqual(result['accuracy'],.5);self.assertAlmostEqual(result['brier'],(.01+.64+.09+.01)/4)
    def test_auc_independent_pairwise_oracle(self):
        rng=random.Random(43)
        for _ in range(50):
            labels=[0,1]+[rng.randrange(2) for _ in range(18)];scores=[rng.choice([.1,.2,.5,.7,.9]) for _ in labels];positive=[s for s,y in zip(scores,labels) if y];negative=[s for s,y in zip(scores,labels) if not y];expected=sum(1 if a>b else .5 if a==b else 0 for a in positive for b in negative)/(len(positive)*len(negative));self.assertAlmostEqual(metrics.calculate(labels,scores,.5)['roc_auc'],expected)
    def test_average_precision_grouped_tie_oracle(self):
        labels=[1,0,1,0,1];scores=[.9,.9,.7,.5,.5];expected=(1/3)*(1/2)+(1/3)*(2/3)+(1/3)*(3/5);self.assertAlmostEqual(metrics.calculate(labels,scores,.5)['average_precision'],expected)
    def test_tied_pair_auc_and_ap(self):
        result=metrics.calculate([0,1],[.5,.5],.5);self.assertEqual(result['roc_auc'],.5);self.assertEqual(result['average_precision'],.5)
    def test_single_class_and_zero_denominators(self):
        result=metrics.calculate([0,0],[.1,.2],.5);self.assertIsNone(result['roc_auc']);self.assertIsNone(result['average_precision']);self.assertIsNone(result['precision']);self.assertIsNone(result['recall']);self.assertIsNone(result['f1'])
    def test_reliability_bins_and_empty_unknown(self):
        result=metrics.calculate([0,1,1],[0.,.4,1.],.5);bins=result['reliability_bins'];self.assertEqual([row['count'] for row in bins],[1,0,1,0,1]);self.assertIsNone(bins[1]['mean_score']);self.assertEqual(bins[4]['positive_fraction'],1);self.assertFalse(result['scores_calibrated'])
    def test_log_loss_endpoints_finite(self):self.assertTrue(math.isfinite(metrics.calculate([0,1],[1.,0.],.5)['log_loss']))
    def test_metric_rejections(self):
        for labels,scores in (([],[]),([1],[.1,.2]),([True],[.5]),([1],[float('nan')]),([1],[-.1]),([1],[1.1])):
            with self.assertRaises(r.WorkbenchError):metrics.calculate(labels,scores,.5)
    def test_stable_sigmoid_extremes(self):self.assertEqual(learner.sigmoid(-10000),0);self.assertEqual(learner.sigmoid(10000),1);self.assertEqual(learner.sigmoid(0),.5)
    def test_observed_training_mean_population_scale(self):
        rows=[dict(features=dict(x=x)) for x in (2.,None,4.)];p=learner.preprocessing(rows,['x']);self.assertEqual(p['means'],[3.]);self.assertEqual(p['scales'],[1.]);self.assertEqual(p['training_missing_counts'],[1]);self.assertEqual(learner.transform(rows,p),[[-1.],[0.],[1.]])
    def test_constant_and_all_missing_features(self):
        p=learner.preprocessing([dict(features=dict(x=4))]*3,['x']);self.assertEqual(p['scales'],[1.]);self.assertEqual(p['constant_or_tiny_scale'],[True])
        with self.assertRaisesRegex(r.WorkbenchError,'NO_TRAINING_FEATURE_VALUES'):learner.preprocessing([dict(features=dict(x=None))]*3,['x'])
    def test_one_step_gradient_oracle(self):
        rows=[dict(features=dict(x=0),outcome=0),dict(features=dict(x=2),outcome=1)];model=learner.fit(rows,['x'],dict(iterations=1,learning_rate=.2,l2=.1));self.assertEqual(model['weights'],[.1]);self.assertEqual(model['intercept'],0);self.assertAlmostEqual(learner.scores(model,rows)[1],1/(1+math.exp(-.1)))
    def test_repeated_training_deterministic(self):
        selected=parts()['train'];self.assertEqual(learner.fit(selected,['signal','load','ready'],config()['learner']),learner.fit(selected,['signal','load','ready'],config()['learner']))
    def test_brier_and_logloss_independent_arithmetic(self):
        labels=[0,1,0];scores=[.2,.7,.4];m=metrics.calculate(labels,scores,.5);self.assertAlmostEqual(m['brier'],(.04+.09+.16)/3);self.assertAlmostEqual(m['log_loss'],-(math.log(.8)+math.log(.7)+math.log(.6))/3)
    def test_threshold_selection_tie_rule(self):
        best,_=app._choose([0,1],[.1,.9],[.3,.5,.7]);self.assertEqual(best['threshold'],.5)


class Contracts(unittest.TestCase):
    def test_known_chronology_counts(self):
        p=parts();self.assertEqual([len(p[k]) for k in ('train','validation','test','excluded')],[118,48,48,26]);self.assertEqual(len({row['group_id'] for row in p['train']}),59)
    def test_feature_availability_future_refused(self):
        data=fixtures.dataset();data['rows'][1]['feature_available_day']['signal']=2
        with self.assertRaisesRegex(r.WorkbenchError,'FEATURE_NOT_AVAILABLE_AT_DECISION'):c.dataset(r.encode(data))
    def test_missing_feature_requires_missing_time(self):
        data=fixtures.dataset();data['rows'][0]['feature_available_day']['load']=0
        with self.assertRaises(r.WorkbenchError):c.dataset(r.encode(data))
    def test_label_before_decision_refused(self):
        data=fixtures.dataset();data['rows'][1]['label_available_day']=0
        with self.assertRaises(r.WorkbenchError):c.dataset(r.encode(data))
    def test_label_cutoff_is_strict_for_training_validation(self):
        data=validated();data['rows'][0]['label_available_day']=130;data['rows'][130]['label_available_day']=190;p=c.partition(data,c.experiment(r.encode(config())));self.assertNotIn('sample-row-0',[row['row_id'] for row in p['train']]);self.assertNotIn('sample-row-130',[row['row_id'] for row in p['validation']])
    def test_test_label_asof_is_inclusive(self):
        data=validated();data['rows'][190]['label_available_day']=250;p=c.partition(data,c.experiment(r.encode(config())));self.assertIn('sample-row-190',[row['row_id'] for row in p['test']])
    def test_group_crossing_refused_even_when_label_purged(self):
        data=validated();data['rows'][190]['group_id']=data['rows'][118]['group_id']
        with self.assertRaisesRegex(r.WorkbenchError,'GROUP_CROSSES_PARTITIONS'):c.partition(data,c.experiment(r.encode(config())))
    def test_duplicate_rows_and_case_aliases_refused(self):
        for kind in ('row_id','group_id'):
            data=fixtures.dataset();data['rows'][2][kind]=data['rows'][0][kind].upper()
            with self.assertRaises(r.WorkbenchError):c.dataset(r.encode(data))
    def test_unknown_fields_and_boolean_numbers_refused(self):
        for key,value in (('extra','fictional'),('decision_day',True),('outcome',1.0)):
            data=fixtures.dataset();data['rows'][0][key]=value
            with self.assertRaises(r.WorkbenchError):c.dataset(r.encode(data))
    def test_empty_and_single_class_partitions_refused(self):
        data=validated()
        for row in data['rows']:
            if row['decision_day']<120:row['outcome']=0
        with self.assertRaises(r.WorkbenchError):c.partition(data,c.experiment(r.encode(config())))
    def test_hyperparameter_and_split_limits(self):
        for change in ('iterations','learning_rate','l2','chronology','thresholds'):
            value=config()
            if change=='chronology':value['split']['train_end_day']=130
            elif change=='thresholds':value['thresholds']=[.5,.5]
            else:value['learner'][change]={'iterations':601,'learning_rate':0,'l2':2}[change]
            with self.assertRaises(r.WorkbenchError):c.experiment(r.encode(value))
    def test_dataset_row_feature_limits(self):
        for change in ('rows','features'):
            data=fixtures.dataset()
            if change=='rows':data['rows']*=6
            else:data['feature_names']*=9
            with self.assertRaises(r.WorkbenchError):c.dataset(r.encode(data))
    def test_reserved_identifiers(self):
        for value in ('CON','aux.json','COM1','sample.'):
            with self.assertRaises(r.WorkbenchError):c.token(value)
    def test_json_duplicate_nonfinite_depth_size_utf8(self):
        for raw in (b'{"a":1,"a":2}',b'NaN',b'1e999',b'['*66+b'0'+b']'*66,b'x'*(r.MAX_INPUT+1),b'\xff'):
            with self.assertRaises(r.WorkbenchError):r.decode(raw)


class Application(Fixture):
    def test_complete_demo(self):
        result=app.demo();self.assertEqual([result[k] for k in ('rows','training_rows','validation_rows','test_rows','excluded_rows')],[240,118,48,48,26]);self.assertEqual(result['threshold'],.4);self.assertAlmostEqual(result['test_auc'],.8834782608695653);self.assertAlmostEqual(result['test_brier'],.16704756742375967);self.assertTrue(result['backup_validated']);self.assertTrue(result['comparison_same_cohort']);self.assertFalse(result['scores_calibrated'])
    def test_demo_no_external_network(self):
        with patch('socket.socket',side_effect=AssertionError('Unexpected network request')):self.assertFalse(app.demo()['real_customer_data_or_pretrained_weights_included'])
    def test_immutable_dataset_and_experiment(self):
        first=self.load();self.assertFalse(self.load()['created']);data=fixtures.dataset();data['title']='Other fictional title'
        with self.assertRaisesRegex(r.WorkbenchError,'DATASET_IMMUTABLE'):app.import_dataset(r.encode(data))
        first=self.prepare();self.assertFalse(self.prepare()['created'])
        with self.assertRaisesRegex(r.WorkbenchError,'EXPERIMENT_IMMUTABLE'):self.prepare(changes=dict(l2=.2))
    def test_dataset_pin_refused_atomically(self):
        self.load();value=config()
        with self.assertRaisesRegex(r.WorkbenchError,'DATASET_PIN_MISMATCH'):app.prepare(r.encode(value))
        self.assertEqual(app.experiments(),dict(experiments=[]))
    def test_test_changes_do_not_change_fit_or_threshold(self):
        self.prepare();a=app.show('sample-baseline')['prepared'];data=fixtures.dataset();data['dataset_id']='sample-changed'
        for row in data['rows']:
            if row['decision_day']>=190:row['features']['signal']=1000;row['outcome']=1-row['outcome']
        app.import_dataset(r.encode(data));value=app.example('sample-changed');value['experiment_id']='sample-altered';app.prepare(r.encode(value));b=app.show('sample-altered')['prepared'];self.assertEqual(a['model'],b['model']);self.assertEqual(a['threshold'],b['threshold']);self.assertEqual(a['validation_grid'],b['validation_grid']);self.assertNotEqual(a['split']['test']['cohort_sha256'],b['split']['test']['cohort_sha256'])
    def test_validation_changes_do_not_change_preprocessing_or_fit(self):
        self.prepare();a=app.show('sample-baseline')['prepared'];data=fixtures.dataset();data['dataset_id']='sample-validation'
        for row in data['rows']:
            if 130<=row['decision_day']<180:row['features']['signal']=100
        app.import_dataset(r.encode(data));value=app.example('sample-validation');value['experiment_id']='sample-altered';app.prepare(r.encode(value));b=app.show('sample-altered')['prepared'];self.assertEqual(a['model'],b['model'])
    def test_prepare_has_no_test_metrics(self):
        self.prepare();record=app.show('sample-baseline');self.assertIsNone(record['evaluation']);self.assertFalse(record['prepared']['test_evaluated']);self.assertNotIn('test_predictions',record['prepared'])
    def test_holdout_immutable_idempotent_and_conflict(self):
        first=self.evaluate();record=app.show('sample-baseline');second=app.evaluate(r.encode(dict(experiment_id='sample-baseline',expected_sha256=record['prepared_sha256'])));self.assertFalse(second['created']);self.assertEqual(first['evaluation'],second['evaluation'])
        with self.assertRaisesRegex(r.WorkbenchError,'PREPARED_CONFLICT'):app.evaluate(r.encode(dict(experiment_id='sample-baseline',expected_sha256='0'*64)))
    def test_review_resets_on_evaluation(self):
        self.prepare();self.approve();old=app.show('sample-baseline');self.evaluate();new=app.show('sample-baseline');self.assertEqual(old['review']['status'],'approved');self.assertEqual(new['review'],dict(status='pending',row_version=0));self.assertNotEqual(old['artifact_sha256'],new['artifact_sha256'])
    def test_review_checks_and_stale_versions(self):
        self.evaluate()
        with self.assertRaisesRegex(r.WorkbenchError,'REVIEW_CHECKS_REQUIRED'):self.approve(checks=dict(quality=True,privacy=False,rights=True,context=True))
        self.approve()
        with self.assertRaisesRegex(r.WorkbenchError,'REVIEW_VERSION_CONFLICT'):self.approve(expected_version=0)
        with self.assertRaises(r.WorkbenchError):self.approve(checks=dict(quality=1,privacy=True,rights=True,context=True))
    def test_stale_artifact_review_refused(self):
        self.prepare();old=app.show('sample-baseline');self.evaluate()
        with self.assertRaisesRegex(r.WorkbenchError,'ARTIFACT_CONFLICT'):self.approve(artifact_sha256=old['artifact_sha256'])
    def test_export_requires_evaluation_and_approval(self):
        self.prepare();self.approve()
        with self.assertRaisesRegex(r.WorkbenchError,'EVALUATION_REQUIRED_FOR_EXPORT'):app.export('sample-baseline')
        self.evaluate()
        with self.assertRaisesRegex(r.WorkbenchError,'APPROVAL_REQUIRED'):app.export('sample-baseline')
    def test_export_exact_hashes_and_safe_model_json(self):
        self.evaluate();self.approve();result=app.export('sample-baseline');directory=self.root/result['directory'];manifest=result['manifest'];self.assertEqual(len(manifest['files']),7);self.assertFalse(manifest['public_release_authorized']);self.assertEqual({p.name for p in directory.iterdir()},set(manifest['files'])|{'manifest.json'})
        for name,item in manifest['files'].items():
            raw=(directory/name).read_bytes();self.assertEqual(item,dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        model=json.loads((directory/'model.json').read_text(encoding='utf-8'));self.assertFalse(model['executable_serialization']);self.assertEqual(r.digest(r.encode(model)),manifest['model_sha256']);record=app.show('sample-baseline');data=validated();rows=c.partition(data,record['config'])['test'];actual=learner.scores(model,rows);expected=[row['score'] for row in record['evaluation']['result']['predictions']];self.assertEqual(actual,expected)
    def test_compare_same_and_different_cohorts(self):
        self.evaluate();self.prepare('sample-second',dict(l2=.2));self.assertFalse(app.compare('sample-baseline','sample-second')['test_comparison_available']);record=app.show('sample-second');app.evaluate(r.encode(dict(experiment_id='sample-second',expected_sha256=record['prepared_sha256'])));self.assertTrue(app.compare('sample-baseline','sample-second')['test_comparison_available'])
        data=fixtures.dataset();data['dataset_id']='sample-other';data['rows'][190]['features']['signal']=100;app.import_dataset(r.encode(data));value=app.example('sample-other');value['experiment_id']='sample-other';app.prepare(r.encode(value));record=app.show('sample-other');app.evaluate(r.encode(dict(experiment_id='sample-other',expected_sha256=record['prepared_sha256'])));result=app.compare('sample-baseline','sample-other');self.assertFalse(result['same_test_cohort']);self.assertNotIn('test',result)
    def test_store_budget_failure_rolls_back(self):
        with patch.object(r,'MAX_STORE',1),self.assertRaisesRegex(r.WorkbenchError,'STORE_LIMIT'):self.load()
        self.assertEqual(app.datasets(),dict(datasets=[]))
    def test_append_only_and_schema_version_checks(self):
        self.evaluate();self.approve()
        for table in ('datasets','experiments','evaluations','reviews'):
            with self.assertRaises(sqlite3.IntegrityError),r.connect() as con:con.execute('DELETE FROM '+table)
        path=self.root/'database/ml.sqlite3'
        with closing(sqlite3.connect(path)) as con:con.execute('PRAGMA user_version=2');con.commit()
        with self.assertRaisesRegex(r.WorkbenchError,'STORE_VERSION_REFUSED'):app.datasets()
        with closing(sqlite3.connect(path)) as con:con.execute('PRAGMA user_version=0');con.execute('CREATE TABLE unexpected(x)');con.commit()
        with self.assertRaisesRegex(r.WorkbenchError,'STORE_SCHEMA_REFUSED'):app.datasets()
    def test_database_backup_and_pinned_example_file(self):
        self.prepare();backup=app.backup();raw=(self.root/backup['file']).read_bytes();self.assertEqual(r.digest(raw),backup['sha256'])
        with closing(sqlite3.connect(self.root/backup['file'])) as con:r.validate_schema(con);self.assertEqual(con.execute('SELECT COUNT(*) FROM experiments').fetchone()[0],1)
        example=app.example_file('sample-ml');self.assertEqual(c.experiment(r.read_bytes(self.root/example['file']))['dataset_sha256'],app.dataset('sample-ml')['dataset_sha256'])
    def test_single_class_test_keeps_undefined_auc(self):
        data=fixtures.dataset()
        for row in data['rows']:
            if row['decision_day']>=190:row['outcome']=0
        app.import_dataset(r.encode(data));value=app.example('sample-ml');prepared=app.prepare(r.encode(value));result=app.evaluate(r.encode(dict(experiment_id='sample-baseline',expected_sha256=prepared['prepared_sha256'])))['evaluation']['result']['metrics'];self.assertIsNone(result['roc_auc']);self.assertIsNone(result['average_precision']);self.assertEqual(result['rows'],48)
    def test_all_missing_training_feature_refuses_atomic_prepare(self):
        data=fixtures.dataset()
        for row in data['rows']:
            if row['decision_day']<120:row['features']['load']=None;row['feature_available_day']['load']=None
        app.import_dataset(r.encode(data))
        with self.assertRaisesRegex(r.WorkbenchError,'NO_TRAINING_FEATURE_VALUES'):app.prepare(r.encode(app.example('sample-ml')))
        self.assertEqual(app.experiments(),dict(experiments=[]))


class Filesystem(Fixture):
    def test_source_cannot_be_instance(self):
        r.close()
        with self.assertRaises(r.WorkbenchError):r.configure(APP,create=True)
    def test_parent_escape_refused(self):
        with self.assertRaises(r.WorkbenchError):r.local_path('../outside',False)
    def test_existing_output_never_replaced(self):
        path=self.root/'inbox/existing.json';r.write_new(path,b'original')
        with self.assertRaises(r.WorkbenchError):r.write_new(path,b'replacement')
        self.assertEqual(path.read_bytes(),b'original')
    def make_link(self,action):
        try:action()
        except OSError:
            if os.environ.get('WORKBENCH_REQUIRE_LINKS')=='1':self.fail('Native link fixture required')
            self.skipTest('Native link fixture unavailable on this filesystem')
    def test_native_hardlink_input_refused(self):
        target=self.root/'inbox/alias';self.make_link(lambda:os.link(self.root/'inbox/sample-dataset.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_database_hardlink_refused(self):
        self.make_link(lambda:os.link(self.root/'database/ml.sqlite3',self.root/'database/alias.sqlite3'))
        with self.assertRaises(r.WorkbenchError):app.datasets()
    def test_native_symlink_input_refused(self):
        target=self.root/'inbox/alias';self.make_link(lambda:os.symlink(self.root/'inbox/sample-dataset.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_symlink_parent_refused(self):
        target=self.root/'alias';self.make_link(lambda:os.symlink(self.root/'inbox',target,target_is_directory=True))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target/'sample-dataset.json')
    @unittest.skipIf(os.name=='nt','POSIX-only FIFO')
    def test_posix_fifo_refused_without_blocking(self):
        target=self.root/'inbox/sample-fifo';os.mkfifo(target)
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    @unittest.skipUnless(os.name=='nt','Windows-only stream names')
    def test_windows_stream_refused(self):
        with self.assertRaises(r.WorkbenchError):r.local_path('inbox/sample-dataset.json:stream')
    def test_stale_lock_requires_assertion(self):
        r.close();(self.root/'.session-lock').mkdir()
        with self.assertRaises(r.WorkbenchError):r.configure(self.root)
        r.configure(self.root,confirm_stopped=True);self.assertEqual(app.datasets(),dict(datasets=[]))
    def test_nonempty_stale_lock_refused(self):
        r.close();(self.root/'.session-lock').mkdir();(self.root/'.session-lock/owned').write_bytes(b'fictional')
        with self.assertRaises(r.WorkbenchError):r.configure(self.root,confirm_stopped=True)
    def test_actual_child_termination_and_restart(self):
        self.prepare();r.close();process=subprocess.Popen([sys.executable,'-B',str(APP/'workbench.py'),'--workspace',str(self.root),'serve','--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:self.assertEqual(json.loads(process.stdout.readline())['mode'],'LOOPBACK_ML_UI');process.kill();process.communicate(timeout=10)
        finally:
            if process.poll() is None:process.kill();process.communicate(timeout=10)
        with self.assertRaises(r.WorkbenchError):r.configure(self.root)
        r.configure(self.root,confirm_stopped=True);self.assertEqual(app.show('sample-baseline')['prepared']['split']['train']['rows'],118)


class BrowserApi(Fixture):
    def setUp(self):
        super().setUp();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def request(self,path='/',method='GET',value=None,headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:
            connection.request(method,path,body=r.encode(value) if value is not None else None,headers=headers or {});response=connection.getresponse();return response.status,response.read(),dict(response.getheaders())
        finally:connection.close()
    def test_html_and_no_cache(self):
        status,raw,headers=self.request();self.assertEqual(status,200);self.assertIn(web.TOKEN.encode(),raw);self.assertNotIn(b'__SESSION_TOKEN__',raw);self.assertEqual(headers['Cache-Control'],'no-store')
    def test_api_token_required(self):self.assertEqual(self.request('/api/datasets')[0],403)
    def test_host_and_origin_refused(self):
        self.assertEqual(self.request(headers={'Host':'example.invalid'})[0],403);self.assertEqual(self.request('/api/backup','POST',{},dict(Origin='https://example.invalid',**{'X-Outlands-Token':web.TOKEN}))[0],403)
    def test_write_token_required(self):self.assertEqual(self.request('/api/backup','POST',{})[0],403)
    def test_fixed_error_no_private_path(self):
        status,raw,_=self.request('/api/experiment?experiment=missing',headers={'X-Outlands-Token':web.TOKEN});self.assertEqual(status,400);self.assertEqual(json.loads(raw),dict(error='EXPERIMENT_NOT_FOUND'))
    def test_unknown_fields_and_duplicate_query_refused(self):
        headers={'X-Outlands-Token':web.TOKEN};self.assertEqual(self.request('/api/backup','POST',{'extra':'fictional'},headers)[0],400);self.assertEqual(self.request('/api/dataset?dataset=a&dataset=b',headers=headers)[0],400)
    def test_real_import_prepare_and_evaluate_http(self):
        headers={'X-Outlands-Token':web.TOKEN};self.assertEqual(self.request('/api/import','POST',fixtures.dataset(),headers)[0],200);value=app.example('sample-ml');status,raw,_=self.request('/api/prepare','POST',value,headers);self.assertEqual(status,200);prepared=json.loads(raw);status,raw,_=self.request('/api/evaluate','POST',dict(experiment_id='sample-baseline',expected_sha256=prepared['prepared_sha256']),headers);self.assertEqual(status,200);self.assertEqual(json.loads(raw)['evaluation']['result']['metrics']['rows'],48)


if __name__=='__main__':unittest.main()
