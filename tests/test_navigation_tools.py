"""Actual independent CLI and connected fictional HVAC navigation acceptance."""
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
TOOLS={'navigation-route-contract-checker':'routes.py','navigation-target-checker':'targets.py',
       'navigation-reachability-reporter':'reachability.py','navigation-scenario-comparator':'scenarios.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-navigation-'); self.addCleanup(self.temp.cleanup)
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
            if name=='navigation-route-contract-checker':self.assertIsNone(out['assessment']);self.assertIsNone(out['cohort_sha256'])
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
    def test_connected_four_tool_hvac_navigation(self):
        names=list(TOOLS);reports=[self.run_value(name,self.example(name)) for name in names];scope=reports[0]['cohort_sha256']['manifests'];self.assertEqual(scope,reports[1]['cohort_sha256']['manifests']);self.assertEqual(scope,reports[2]['cohort_sha256']['manifests']);self.assertEqual(scope,reports[3]['cohort_sha256']['baseline_manifests']);self.assertEqual(reports[1]['cohort_sha256']['links'],reports[2]['cohort_sha256']['links']);self.assertEqual(reports[2]['assessment']['plans'][0]['graph']['reachable_pages'],['home-page','parts-page','service-page']);self.assertTrue(reports[3]['assessment']['all_selected_outcomes_equal'])
    def test_game_and_ai_software_cli_examples(self):
        for name,file in [('navigation-route-contract-checker','game.json'),('navigation-target-checker','ai-software.json')]:self.assertEqual(self.cli(name,file=ROOT/'tools'/name/'examples'/file)[0],0)
    def test_broken_target_withholds_reachability_and_same_negative_is_not_equality(self):
        value=self.example('navigation-reachability-reporter');value['links'][0]['target_path']='/missing';value['plans'][0]['links_sha256']=sha(encode(value['links']));out=self.run_value('navigation-reachability-reporter',value,1);self.assertIsNone(out['assessment']['plans'][0]['graph']);value=self.example('navigation-scenario-comparator')
        for key in ('baseline_links','candidate_links'):value[key][0]['target_path']='/missing'
        self.assertFalse(self.run_value('navigation-scenario-comparator',value,1)['assessment']['all_selected_outcomes_equal'])
    def test_full_manifest_and_link_pins_prevent_stale_handoff(self):
        v=self.example('navigation-target-checker');v['manifests'][0]['revision']=2;self.assertIsNone(self.run_value('navigation-target-checker',v,1)['assessment']);v=self.example('navigation-reachability-reporter');v['links'].pop();self.assertIsNone(self.run_value('navigation-reachability-reporter',v,1)['assessment'])
