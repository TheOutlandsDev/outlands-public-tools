"""Actual standalone CLIs and public-baseline interoperability on invented observations."""
from fractions import Fraction
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
TOOLS={'forecast-error-analyzer':'forecast_errors.py','prediction-interval-checker':'intervals.py',
       'distribution-comparison-reporter':'distributions.py','recommendation-feedback-reconciler':'feedback.py'}


def enc(value): return (json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'))+'\n').encode('ascii')
def fraction(value): return Fraction(int(value['numerator']),int(value['denominator']))


class Walkthrough(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='fictional-forecast-feedback-')
        self.addCleanup(temp.cleanup); self.private=Path(temp.name)

    def call(self,root,script,args,code=0):
        result=subprocess.run([sys.executable,'-B',str(root/script),*map(str,args)],cwd=self.private,
                              capture_output=True,timeout=30)
        self.assertEqual(result.returncode,code,result.stdout.decode('utf-8',errors='replace'))
        self.assertEqual(result.stderr,b''); return json.loads(result.stdout)

    def run_value(self,name,value,code=0):
        selected=self.private/(name+'.json'); selected.write_bytes(enc(value))
        return self.call(ROOT/'tools'/name,TOOLS[name],['--input',selected],code)

    def test_all_fictional_cli_examples(self):
        for name,script in TOOLS.items():
            root=ROOT/'tools'/name
            with self.subTest(tool=name): self.assertEqual(self.call(root,script,['--input',root/'examples/input.json'])['status'],'PASS')

    def test_actual_standalone_copied_sources_and_manifest_pins(self):
        for name,script in TOOLS.items():
            root=self.private/name; shutil.copytree(ROOT/'tools'/name,root,ignore=shutil.ignore_patterns('__pycache__'))
            with self.subTest(tool=name):
                self.call(root,script,['--input',root/'examples/input.json'])
                self.assertEqual(self.call(root,'source_check.py',[])['status'],'SOURCE_MATCH')

    def test_private_new_reports_and_overwrite_refusal(self):
        for name,script in TOOLS.items():
            root=ROOT/'tools'/name; target=self.private/(name+'.json'); args=['--input',root/'examples/input.json','--out',target]
            self.assertTrue(self.call(root,script,args)['report_written']); before=target.read_bytes()
            self.call(root,script,args,2); self.assertEqual(target.read_bytes(),before)

    def test_source_tree_output_refused_without_creation(self):
        for name,script in TOOLS.items():
            root=ROOT/'tools'/name; target=root/'FICTIONAL-MUST-NOT-BE-WRITTEN.json'
            self.assertFalse(target.exists()); self.call(root,script,['--input',root/'examples/input.json','--out',target],2)
            self.assertFalse(target.exists())

    def test_fixed_argument_errors_omit_values(self):
        for name,script in TOOLS.items():
            self.assertEqual(self.call(ROOT/'tools'/name,script,['--unknown','FICTIONAL_SENTINEL'],2),dict(status='ERROR',code='ARGUMENTS_INVALID'))

    def test_review_examples_have_no_partial_derived_metrics(self):
        for name,script in TOOLS.items():
            root=ROOT/'tools'/name; result=self.call(root,script,['--input',root/'examples/needs-review.json'],1)
            if 'metrics' in result: self.assertIsNone(result['metrics'])
            if 'comparisons' in result: self.assertEqual(result['comparisons'],[])
            if 'states' in result: self.assertEqual(result['states'],[])

    def test_valid_pending_feedback_is_not_reported_complete(self):
        root=ROOT/'tools/recommendation-feedback-reconciler'
        result=self.call(root,'feedback.py',['--input',root/'examples/pending.json'])
        self.assertFalse(result['all_acceptances_have_observed_outcomes'])

    def test_public_baseline_actual_predictions_and_four_tool_cohort(self):
        # Execute only the existing public educational baseline on invented numbers.
        program="""
import json,sys
sys.path.insert(0,sys.argv[1])
from ingestion import ingest_csv
from evaluator import forecast,rolling_score
values=[2,4,2,4,2,4]
forecasts=[]
for target in range(2,6):
    batch=ingest_csv('series,period,value\\n'+''.join(f'sample,{i},{v}\\n' for i,v in enumerate(values[:target])))
    point=forecast(batch,method='last',horizon=1)[0]
    forecasts.append(dict(id='sample-'+str(target),revision=1,series='sample',origin=target-1,target=target,predicted=str(point.value)))
batch=ingest_csv('series,period,value\\n'+''.join(f'sample,{i},{v}\\n' for i,v in enumerate(values)))
score=rolling_score(batch,min_history=2,method='last')
print(json.dumps(dict(forecasts=forecasts,outcomes=[dict(series='sample',period=i,value=str(values[i])) for i in range(2,6)],mae=score.mae,rmse=score.rmse)))
"""
        result=subprocess.run([sys.executable,'-B','-c',program,str(ROOT/'tools/forecast-baseline-evaluator')],
                              cwd=self.private,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr.decode()); baseline=json.loads(result.stdout)
        errors=self.run_value('forecast-error-analyzer',dict(format='outlands-forecast-errors-v1',forecasts=baseline['forecasts'],outcomes=baseline['outcomes']))
        self.assertEqual(fraction(errors['metrics']['mae']),2); self.assertEqual(baseline['mae'],2)
        self.assertEqual(errors['metrics']['rmse_approx'],'2.000000000000'); self.assertEqual(baseline['rmse'],2)
        intervals=[]
        for row in baseline['forecasts']:
            item={k:v for k,v in row.items() if k!='predicted'}; center=Fraction(row['predicted'])
            item.update(lower=str(int(center-2)),upper=str(int(center+2))); intervals.append(item)
        coverage=self.run_value('prediction-interval-checker',dict(format='outlands-interval-coverage-v1',nominal_coverage='0.8',intervals=intervals,outcomes=baseline['outcomes']))
        self.assertEqual(fraction(coverage['metrics']['coverage']),1); self.assertFalse(coverage['calibration_verified'])
        distribution=self.run_value('distribution-comparison-reporter',dict(format='outlands-distribution-comparison-v1',fields=[dict(name='value',kind='numeric',boundaries=['0','3','6'])],
            reference=[dict(id=row['id'],values=dict(value=row['predicted'])) for row in baseline['forecasts']],
            current=[dict(id='sample-'+str(row['period']),values=dict(value=row['value'])) for row in baseline['outcomes']]))
        self.assertEqual(fraction(distribution['comparisons'][0]['total_variation_distance']),0)
        feedback=self.run_value('recommendation-feedback-reconciler',dict(format='outlands-recommendation-feedback-v1',
            recommendations=[dict(recommendation_id=row['id'],revision=1,action='inspect') for row in baseline['forecasts']],
            decisions=[dict(recommendation_id=row['id'],revision=1,decision='accept') for row in baseline['forecasts']],
            outcomes=[dict(recommendation_id='sample-'+str(row['period']),revision=1,status='observed',observed=row['value']) for row in baseline['outcomes']]))
        self.assertEqual(feedback['state_counts'],{'OUTCOME_RECORDED':4})
        self.assertFalse(feedback['causal_effect_estimated']); self.assertFalse(feedback['model_or_policy_updated'])

    def test_raw_input_pins_match_selected_fixture_bytes(self):
        import hashlib
        for name,script in TOOLS.items():
            root=ROOT/'tools'/name; selected=root/'examples/input.json'
            self.assertEqual(self.call(root,script,['--input',selected])['input_sha256'],hashlib.sha256(selected.read_bytes()).hexdigest())

    def test_no_input_mutation_or_action_artifacts(self):
        import hashlib
        for name,script in TOOLS.items():
            root=ROOT/'tools'/name; selected=self.private/(name+'.json'); selected.write_bytes((root/'examples/input.json').read_bytes())
            before=hashlib.sha256(selected.read_bytes()).hexdigest(); names=set(self.private.iterdir())
            result=self.call(root,script,['--input',selected]); self.assertFalse(result['target_changes_performed'])
            self.assertEqual(hashlib.sha256(selected.read_bytes()).hexdigest(),before); self.assertEqual(set(self.private.iterdir()),names)
