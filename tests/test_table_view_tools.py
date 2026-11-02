"""Actual independent CLI and connected fictional HVAC table-view acceptance."""
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
TOOLS={'table-view-contract-checker':'views.py','filter-sort-projection-checker':'projections.py',
       'pagination-coverage-reconciler':'pages.py','table-view-scenario-comparator':'scenarios.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-table-view-'); self.addCleanup(self.temp.cleanup)
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
            if name=='table-view-contract-checker':self.assertIsNone(out['assessment']);self.assertIsNone(out['cohort_sha256'])
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
    def test_connected_four_tool_hvac_view_projection_pages_and_comparison(self):
        names=list(TOOLS);reports=[self.run_value(n,self.example(n)) for n in names];self.assertEqual(reports[0]['cohort_sha256']['views'],reports[1]['cohort_sha256']['views']);self.assertEqual(reports[1]['cohort_sha256']['views'],reports[2]['cohort_sha256']['views']);self.assertEqual(reports[1]['cohort_sha256']['snapshots'],reports[2]['cohort_sha256']['snapshots']);self.assertEqual(reports[1]['cohort_sha256']['projections'],reports[2]['cohort_sha256']['projections']);self.assertTrue(reports[2]['assessment']['plans'][0]['valid']);self.assertTrue(reports[3]['assessment']['all_selected_outcomes_equal'])
    def test_game_and_ai_software_cli_examples(self):
        for name,file in [('table-view-contract-checker','game.json'),('filter-sort-projection-checker','ai-software.json')]:self.assertEqual(self.cli(name,file=ROOT/'tools'/name/'examples'/file)[0],0)
    def test_invalid_projection_withholds_pages_and_duplicate_page_slot_is_not_selected(self):
        v=self.example('pagination-coverage-reconciler');v['projections'][0]['row_ids'].reverse();v['plans'][0]['projection_sha256']=sha(encode(v['projections'][0]));plan_pin=sha(encode(v['plans'][0]))
        for page in v['pages']:page['plan_sha256']=plan_pin
        out=self.run_value('pagination-coverage-reconciler',v,1);self.assertIsNone(out['assessment']['plans'][0]['pages']);v=self.example('pagination-coverage-reconciler');v['pages'].append(dict(v['pages'][0],id='other'));self.assertEqual(self.run_value('pagination-coverage-reconciler',v,1)['assessment']['plans'][0]['duplicate_indices'],[0])
    def test_stale_snapshot_and_changed_view_scenarios_remain_findings(self):
        v=self.example('filter-sort-projection-checker');v['snapshots'][0]['revision']=2;self.assertIsNone(self.run_value('filter-sort-projection-checker',v,1)['assessment']);v=self.example('table-view-scenario-comparator');v['candidate_views'][0]['id_order']='desc';v['cases'][0]['candidate_view_sha256']=sha(encode(v['candidate_views'][0]));self.assertFalse(self.run_value('table-view-scenario-comparator',v,1)['assessment']['all_selected_outcomes_equal'])
