"""Actual independent CLI and connected fictional HVAC pricing acceptance."""
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
TOOLS={'price-book-contract-checker':'books.py','quote-line-pricing-checker':'lines.py',
       'quote-total-reconciler':'totals.py','quote-pricing-scenario-comparator':'scenarios.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-quote-pricing-'); self.addCleanup(self.temp.cleanup)
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

    def test_review_examples_retain_findings_without_qualified_scope(self):
        for name in TOOLS:
            code,out=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json');self.assertEqual(code,1);self.assertEqual(out['status'],'REVIEW_REQUIRED');self.assertTrue(out['issues']);self.assertIsNone(out['qualified_scope_sha256'])
            if name=='price-book-contract-checker':self.assertIsNone(out['assessment']);self.assertIsNone(out['cohort_sha256'])
            else:self.assertIsNotNone(out['assessment'])

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])


    def example(self,name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
    def test_connected_price_book_quote_lines_totals_and_scenario(self):
        names=list(TOOLS);book=self.run_value(names[0],self.example(names[0]));lines=self.run_value(names[1],self.example(names[1]));value=self.example(names[2]);price_out=lines['assessment']['quotes'][0]['lines'];claim=value['claims'][0];claim['line_totals']=[dict(line=v['id'],amount=v['rounded_extension']) for v in price_out];totals=self.run_value(names[2],value);scenario=self.run_value(names[3],self.example(names[3]));self.assertEqual(book['cohort_sha256']['price_books'],lines['cohort_sha256']['price_books']);self.assertEqual(book['cohort_sha256']['price_books'],scenario['cohort_sha256']['baseline_price_books']);self.assertEqual(totals['assessment']['claims'][0]['expected']['total'],'214.25');self.assertTrue(scenario['assessment']['baskets'][0]['equal'])
    def test_game_and_ai_software_cli_examples(self):
        for name,file in [('price-book-contract-checker','game.json'),('quote-line-pricing-checker','ai-software.json')]:self.assertEqual(self.cli(name,file=ROOT/'tools'/name/'examples'/file)[0],0)
    def test_stale_connected_book_and_quote_claim_pins(self):
        v=self.example('quote-line-pricing-checker');v['price_books'][0]['revision']=2;out=self.run_value('quote-line-pricing-checker',v,1);self.assertIsNone(out['assessment']);v=self.example('quote-total-reconciler');v['quotes'][0]['adjustments'].reverse();self.assertIsNone(self.run_value('quote-total-reconciler',v,1)['assessment'])
    def test_scenario_currency_refusal_and_price_change_review(self):
        v=self.example('quote-pricing-scenario-comparator');v['candidate_price_books'][0]['currency']='EUR';self.assertIsNone(self.run_value('quote-pricing-scenario-comparator',v,1)['assessment']);v=self.example('quote-pricing-scenario-comparator');v['candidate_price_books'][0]['items'][0]['tiers'][1]['unit_price']='11.5';self.assertFalse(self.run_value('quote-pricing-scenario-comparator',v,1)['assessment']['baskets'][0]['equal'])
