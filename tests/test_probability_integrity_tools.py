"""Actual independent CLI and connected fictional HVAC probability acceptance."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
TOOLS={'probability-vector-checker':'vectors.py','binary-probability-error-calculator':'errors.py',
       'reliability-bin-reporter':'bins.py','calibration-map-checker':'maps.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-probability-contracts-'); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def invoke(self,script,args):
        q=subprocess.run([sys.executable,'-B',str(script),*map(str,args)],capture_output=True,
                         env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(q.stderr,b''); return q.returncode,json.loads(q.stdout)

    def cli(self,name,file=None,extra=(),folder=None):
        folder=folder or ROOT/'tools'/name
        return self.invoke(folder/TOOLS[name],['--input',file or folder/'examples/input.json',*extra])

    def run_value(self,name,value,code=0):
        file=self.root/(name+'.json'); file.write_bytes(encode(value)); actual,result=self.cli(name,file=file)
        self.assertEqual(actual,code); return result

    def test_valid_examples(self):
        for name in TOOLS:
            code,result=self.cli(name); self.assertEqual(code,0); self.assertEqual(result['status'],'PASS')

    def test_independent_source_copies(self):
        for name in TOOLS:
            folder=self.root/name; shutil.copytree(ROOT/'tools'/name,folder,ignore=shutil.ignore_patterns('__pycache__'))
            code,result=self.invoke(folder/'source_check.py',[]); self.assertEqual(code,0); self.assertEqual(result['status'],'SOURCE_MATCH')
            self.assertEqual(self.cli(name,folder=folder)[0],0)

    def test_new_reports_and_overwrite_prevention(self):
        for name in TOOLS:
            out=self.root/(name+'.json'); code,result=self.cli(name,extra=('--out',out))
            self.assertEqual(code,0); self.assertEqual(result,dict(status='PASS',report_written=True))
            raw=out.read_bytes(); self.assertEqual(json.loads(raw),self.cli(name)[1])
            self.assertEqual(self.cli(name,extra=('--out',out))[0],2); self.assertEqual(out.read_bytes(),raw)

    def test_source_tree_output_refusal(self):
        for name in TOOLS:
            out=ROOT/'tools'/name/'fictional-never-created.json'
            self.assertEqual(self.cli(name,extra=('--out',out))[0],2); self.assertFalse(out.exists())

    def test_fixed_argument_and_path_errors(self):
        for name in TOOLS:
            code,result=self.cli(name,extra=('--SYNTHETIC_SENTINEL',)); self.assertEqual(code,2)
            self.assertEqual(result,dict(status='ERROR',code='ARGUMENTS_INVALID'))
            code,result=self.cli(name,file=self.root/'SYNTHETIC_SENTINEL.json')
            self.assertEqual(code,2); self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(result))

    def test_review_examples_retain_complete_qualified_findings(self):
        for name in TOOLS:
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json')
            self.assertEqual(code,1);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['issues']);self.assertIsNotNone(result['assessment'])

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_hvac_probability_and_map_review(self):
        def example(name,file='input.json'):return json.loads((ROOT/'tools'/name/'examples'/file).read_text(encoding='utf-8'))
        vector_input=example('probability-vector-checker');vectors=self.run_value('probability-vector-checker',vector_input)
        self.assertTrue(vectors['assessment']['all_vectors_valid']);self.assertEqual(vectors['assessment']['valid_cases'],4)
        error_input=example('binary-probability-error-calculator')
        # Explicit fictional operator adapter: select the contract's positive class, never infer label direction.
        contract=error_input['contract'];by_case={r['id']:r for r in vector_input['cases']}
        for row in error_input['predictions']:
            source=by_case[row['case']];self.assertEqual(source['model'],contract['model']);self.assertEqual(source['model_revision'],contract['model_revision'])
            row['probability']=next(p['value'] for p in source['probabilities'] if p['label']==contract['positive_label'])
        errors=self.run_value('binary-probability-error-calculator',error_input)
        self.assertEqual(errors['metrics']['total_squared_error']['exact_fraction'],'3/8');self.assertEqual(errors['metrics']['mean_squared_error']['exact_fraction'],'3/32')
        bin_input=example('reliability-bin-reporter')
        for key in ('contract','cohort','predictions','outcomes'):bin_input[key]=error_input[key]
        bins=self.run_value('reliability-bin-reporter',bin_input)
        for key in ('contract_sha256','cohort_sha256','predictions_sha256','outcomes_sha256'):self.assertEqual(bins[key],errors[key])
        self.assertEqual(bins['metrics']['weighted_absolute_bin_gap']['exact_fraction'],'1/4');self.assertEqual(sum(b['cases'] for b in bins['metrics']['bins']),4)
        mapping_input=example('calibration-map-checker','needs-review.json')
        for side in ('before','after'):
            for key in ('model','model_revision','positive_label','negative_label'):self.assertEqual(mapping_input[side][key],contract[key])
        mapping=self.run_value('calibration-map-checker',mapping_input,1)
        self.assertEqual(mapping['assessment']['points_changed'],['point-middle']);self.assertTrue(mapping['map_assessments']['after']['nondecreasing'])
        self.assertNotEqual(mapping['before_sha256'],mapping['after_sha256']);self.assertFalse(mapping['mapping_applied'])
        # No map is applied and the explicitly supplied predictions remain the evaluation source.
        self.assertEqual(error_input['predictions'],bin_input['predictions'])
        for result in (vectors,errors,bins,mapping):
            for key in ('calibration_established','cohort_independence_verified','label_truth_verified','model_fitted','model_updated','inference_performed','target_changes_performed'):self.assertFalse(result[key])

    def test_missing_outcome_withholds_both_full_cohort_metric_reports(self):
        error_input=json.loads((ROOT/'tools/binary-probability-error-calculator/examples/input.json').read_text(encoding='utf-8'));error_input['outcomes'].pop()
        errors=self.run_value('binary-probability-error-calculator',error_input,1);self.assertIsNone(errors['metrics']);self.assertEqual(errors['assessment']['missing_outcomes'],['case-delta'])
        bin_input=json.loads((ROOT/'tools/reliability-bin-reporter/examples/input.json').read_text(encoding='utf-8'))
        for key in ('contract','cohort','predictions','outcomes'):bin_input[key]=error_input[key]
        bins=self.run_value('reliability-bin-reporter',bin_input,1);self.assertIsNone(bins['metrics']);self.assertTrue(bins['bin_assessment']['valid_partition']);self.assertIsNone(bins['report_sha256'])

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])

    def test_fictional_game_vector_cli(self):
        name='probability-vector-checker';code,r=self.cli(name,file=ROOT/'tools'/name/'examples/game-vectors.json')
        self.assertEqual(code,0);self.assertEqual(r['assessment']['cases'][0]['probability_sum']['exact_fraction'],'1/1');self.assertFalse(r['calibration_established'])
