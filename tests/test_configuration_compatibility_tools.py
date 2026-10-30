"""Actual independent CLI and connected fictional HVAC configuration/compatibility acceptance."""
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
TOOLS={'configuration-overlay-planner':'overlays.py','configuration-contract-diff':'contracts.py',
       'compatibility-matrix-checker':'matrix.py','configuration-migration-path-checker':'migrations.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-configuration-compatibility-'); self.addCleanup(self.temp.cleanup)
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

    def test_review_examples_retain_diagnostics_without_qualified_scope(self):
        for name in TOOLS:
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json');self.assertEqual(code,1);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['issues']);self.assertIsNone(result['qualified_scope_sha256']);self.assertIsNotNone(result['assessment'])

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_hvac_metadata_review(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        overlay_input=example('configuration-overlay-planner');overlay=self.run_value('configuration-overlay-planner',overlay_input)
        self.assertIsNotNone(overlay['effective_configuration_sha256'])
        diff_input=example('configuration-contract-diff');self.assertEqual(overlay['contract_sha256'],sha(encode(diff_input['baseline'])));diff=self.run_value('configuration-contract-diff',diff_input);self.assertTrue(diff['assessment']['all_field_metadata_equal'])
        matrix_input=example('compatibility-matrix-checker');self.assertTrue(all(row['contract_sha256']==diff['candidate_sha256'] for row in matrix_input['components']));matrix=self.run_value('compatibility-matrix-checker',matrix_input);self.assertTrue(matrix['assessment']['all_requested_pairs_declared_supported'])
        migration_input=example('configuration-migration-path-checker');self.assertEqual(migration_input['source']['sha256'],diff['baseline_sha256']);self.assertEqual(migration_input['target']['sha256'],diff['candidate_sha256']);migration=self.run_value('configuration-migration-path-checker',migration_input);self.assertTrue(migration['assessment']['target_reached']);self.assertFalse(migration['assessment']['checks_executed'])
        for report in (overlay,diff,matrix,migration):
            for key in ('raw_setting_values_emitted','settings_values_validated','runtime_compatibility_verified','adapter_bytes_verified','migration_executed','configuration_changed','installation_performed','execution_performed','target_changes_performed'):self.assertFalse(report[key])

    def test_denied_override_changed_metadata_false_matrix_and_missing_path_remain_review(self):
        outputs={}
        for name in TOOLS:
            value=json.loads((ROOT/'tools'/name/'examples/needs-review.json').read_text(encoding='utf-8'));report=self.run_value(name,value,1);outputs[name]=report;self.assertIsNone(report['qualified_scope_sha256']);self.assertFalse(report['target_changes_performed'])
        self.assertIsNone(outputs['configuration-overlay-planner']['effective_configuration_sha256']);self.assertFalse(outputs['configuration-contract-diff']['assessment']['all_field_metadata_equal']);self.assertEqual(outputs['compatibility-matrix-checker']['assessment']['requirements'][0]['state'],'unsupported');self.assertFalse(outputs['configuration-migration-path-checker']['assessment']['target_reached'])

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])

    def test_fictional_game_overlay_cli(self):
        name='configuration-overlay-planner';code,out=self.cli(name,file=ROOT/'tools'/name/'examples/game-overlays.json');self.assertEqual(code,0);self.assertEqual(len(out['assessment']['effective_fields']),3);self.assertFalse(out['configuration_changed'])


    def test_existing_value_checker_validates_separately_supplied_fictional_settings(self):
        # Fingerprints are not decoded into values. The fictional operator supplies values explicitly.
        overlay=json.loads((ROOT/'tools/configuration-overlay-planner/examples/input.json').read_text(encoding='utf-8'));settings=dict(demo_enabled=True,queue_limit=8,display_mode='quiet')
        selected={}
        order={row['id']:row['ordinal'] for row in overlay['layers']}
        for row in sorted(overlay['changes'],key=lambda row:order[row['layer']]):selected[row['key']]=row['value_sha256']
        self.assertEqual(selected,{key:sha(encode(value)) for key,value in settings.items()})
        contract=dict(schema_version=1,fields=[dict(id='demo_enabled',key='demo_enabled',type='boolean',required=True),dict(id='queue_limit',key='queue_limit',type='integer',required=True,minimum=1,maximum=16),dict(id='display_mode',key='display_mode',type='string',required=False,min_length=5,max_length=6,choices=['active','quiet'])],rules=[])
        contract_file=self.root/'fictional-contract.json';contract_file.write_bytes(encode(contract));settings_file=self.root/'fictional-settings.json';settings_file.write_bytes(encode(settings));before=contract_file.read_bytes();script=ROOT/'tools/configuration-contract-checker/config_check.py'
        code,out=self.invoke(script,['--contract',contract_file,'--settings',settings_file]);self.assertEqual(code,0);self.assertEqual(out['status'],'NO_DECLARED_VIOLATIONS')
        settings['queue_limit']=17;settings_file.write_bytes(encode(settings));code,out=self.invoke(script,['--contract',contract_file,'--settings',settings_file]);self.assertEqual(code,1);self.assertEqual(out['status'],'REVIEW_REQUIRED');self.assertNotIn('17',json.dumps(out));self.assertEqual(contract_file.read_bytes(),before)
