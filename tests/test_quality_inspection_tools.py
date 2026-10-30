"""Actual independent CLI and connected fictional HVAC quality/inspection acceptance."""
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
TOOLS={'measurement-contract-checker':'measurements.py','inspection-coverage-checker':'inspections.py',
       'yield-scrap-reconciler':'yields.py','rework-history-checker':'rework.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-hvac-inspections-'); self.addCleanup(self.temp.cleanup)
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

    def test_review_examples_keep_valid_diagnostics_but_withhold_invalid_histories(self):
        for name,key in zip(TOOLS,['assessments','coverage','summary','histories']):
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json')
            self.assertEqual(code,1);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['issues'])
            if name=='rework-history-checker':self.assertIsNone(result[key])
            else:self.assertIsNotNone(result[key])

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_hvac_inspection_cohort(self):
        example=json.loads((ROOT/'tools/measurement-contract-checker/examples/input.json').read_text(encoding='utf-8'))
        units=[dict(id='air-handler-'+suffix) for suffix in ('alpha','bravo','charlie')]
        readings=[dict(id='initial-'+suffix,specimen_id=unit['id'],check_id='demo-check',rule_id='demo-flow-window',rule_revision=1,unit='demo-units',value=value)
                  for unit,suffix,value in zip(units,('alpha','bravo','charlie'),('12','9','25'))]
        initial=self.run_value('measurement-contract-checker',dict(format=example['format'],rules=example['rules'][:1],measurements=readings),1)
        revised=dict(readings[1],id='after-bravo',value='14')
        after=self.run_value('measurement-contract-checker',dict(format=example['format'],rules=example['rules'][:1],measurements=[revised]))
        first={r['specimen_id']:r for r in initial['assessments']};second=after['assessments'][0]
        selected=[(first[units[0]['id']],initial['input_sha256']),(second,after['input_sha256']),(first[units[2]['id']],initial['input_sha256'])]
        records=[dict(id=row['id'],specimen_id=row['specimen_id'],check_id=row['check_id'],rule_id=row['rule_id'],rule_revision=row['rule_revision'],source_sha256=pin,outcome='within_limits' if row['within_declared_limits'] else 'outside_limits') for row,pin in selected]
        coverage=self.run_value('inspection-coverage-checker',dict(format='outlands-inspection-coverage-v1',specimens=units,
            checks=[dict(id='demo-check',rule_id='demo-flow-window',rule_revision=1)],records=records),1)
        self.assertTrue(coverage['summary']['records_complete']);self.assertEqual(coverage['summary']['outside_limits'],1)
        self.assertFalse(coverage['source_bytes_verified'])
        events=[dict(id='inspect-'+str(i),specimen_id=unit['id'],at=0,attempt=1,kind='inspect_pass' if first[unit['id']]['within_declared_limits'] else 'inspect_fail') for i,unit in enumerate(units)]
        # The exercise explicitly supplies fictional repair and scrap decisions.
        events+=[dict(id='repair-bravo',specimen_id=units[1]['id'],at=1,attempt=1,kind='rework'),
                 dict(id='reinspect-bravo',specimen_id=units[1]['id'],at=2,attempt=2,kind='inspect_pass' if second['within_declared_limits'] else 'inspect_fail'),
                 dict(id='scrap-charlie',specimen_id=units[2]['id'],at=1,attempt=1,kind='scrap')]
        history=self.run_value('rework-history-checker',dict(format='outlands-rework-histories-v1',units=units,events=events))
        self.assertEqual(history['totals'],dict(inspection_attempts=4,rework_events=1))
        yield_result=self.run_value('yield-scrap-reconciler',dict(format='outlands-yield-scrap-v1',cohort=units,dispositions=history['dispositions']))
        self.assertEqual(yield_result['summary'],dict(cohort=3,first_pass_good=1,reworked_good=1,scrap=1,pending=0,good=2,closed_cohort=True))
        self.assertEqual(yield_result['fractions']['eventual_yield']['exact_fraction'],'2/3')
        self.assertEqual(yield_result['fractions']['first_pass_yield']['exact_fraction'],'1/3')
        self.assertFalse(yield_result['inspection_coverage_verified']);self.assertFalse(yield_result['quality_target_evaluated'])

    def test_reconciled_yield_does_not_prove_inspection_coverage(self):
        coverage_input=json.loads((ROOT/'tools/inspection-coverage-checker/examples/input.json').read_text(encoding='utf-8'))
        coverage_input['records']=[];coverage=self.run_value('inspection-coverage-checker',coverage_input,1)
        units=coverage_input['specimens'];yield_result=self.run_value('yield-scrap-reconciler',dict(format='outlands-yield-scrap-v1',cohort=units,
            dispositions=[dict(id=u['id'],specimen_id=u['id'],disposition='first_pass_good') for u in units]))
        self.assertEqual(coverage['summary']['missing_pairs'],4);self.assertEqual(yield_result['fractions']['first_pass_yield']['exact_fraction'],'1/1')
        self.assertFalse(yield_result['inspection_coverage_verified']);self.assertFalse(coverage['summary']['records_complete'])

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])
