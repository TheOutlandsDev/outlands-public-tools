"""Actual independent CLI and connected fictional HVAC health/incident acceptance."""
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
TOOLS={'component-health-snapshot-checker':'health.py','incident-timeline-checker':'incidents.py',
       'alert-correlation-planner':'alerts.py','recovery-readiness-planner':'recovery.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-health-incident-'); self.addCleanup(self.temp.cleanup)
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

    def test_review_examples_withhold_qualified_scope_and_invalid_alert_plan(self):
        for name in TOOLS:
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json');self.assertEqual(code,1);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['issues']);self.assertIsNone(result['qualified_scope_sha256']);self.assertEqual(result['assessment'] is None,name=='alert-correlation-planner')

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_hvac_health_incident_and_recovery_review(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        health=self.run_value('component-health-snapshot-checker',example('component-health-snapshot-checker'));self.assertTrue(health['assessment']['all_declared_healthy_and_fresh'])
        timeline=self.run_value('incident-timeline-checker',example('incident-timeline-checker'));self.assertTrue(timeline['assessment']['incidents'][0]['resolved_as_of'])
        alerts=self.run_value('alert-correlation-planner',example('alert-correlation-planner'));self.assertEqual(alerts['assessment']['grouped_alerts'],3);self.assertEqual(len(alerts['assessment']['groups']),2);self.assertEqual(alerts['assessment']['suppressed_alerts'],0)
        recovery_input=example('recovery-readiness-planner');by_role={row['role']:row for row in recovery_input['checks']};by_check={row['check']:row for row in recovery_input['evidence']}
        # Explicit fictional operator adapter; the planner does not authenticate report bytes.
        for role,report,passed in [('component-health',health,health['assessment']['all_declared_healthy_and_fresh']),('incident-resolution',timeline,timeline['assessment']['incidents'][0]['resolved_as_of'])]:
            by_check[by_role[role]['id']].update(outcome='pass' if passed else 'fail',observed_at=recovery_input['as_of'],artifact_sha256=sha(encode(report)))
        recovery=self.run_value('recovery-readiness-planner',recovery_input);self.assertTrue(recovery['assessment']['incidents'][0]['ready_for_manual_recovery_review']);self.assertEqual(recovery['incidents_sha256'],timeline['incidents_sha256'])
        for report in (health,timeline,alerts,recovery):
            self.assertEqual(report['components_sha256'],health['components_sha256'])
            for key in ('observations_independently_verified','artifact_bytes_verified','actual_health_verified','notifications_sent','alerts_suppressed','recovery_authorized','recovery_performed','target_changes_performed'):self.assertFalse(report[key])

    def test_stale_health_reopened_incident_and_old_drill_block_recovery_readiness(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        health_input=example('component-health-snapshot-checker');health_input['as_of']=31;health=self.run_value('component-health-snapshot-checker',health_input,1)
        timeline_input=example('incident-timeline-checker');timeline_input['as_of']=31;timeline_input['events'].append(dict(timeline_input['events'][0],id='event-reopened',ordinal=4,at=25,action='reopen'));timeline=self.run_value('incident-timeline-checker',timeline_input);self.assertFalse(timeline['assessment']['incidents'][0]['resolved_as_of'])
        recovery_input=example('recovery-readiness-planner');recovery_input['as_of']=31;roles={row['id']:row['role'] for row in recovery_input['checks']}
        for evidence in recovery_input['evidence']:
            role=roles[evidence['check']]
            if role in ('component-health','incident-resolution'):evidence.update(outcome='fail',observed_at=31,artifact_sha256=sha(encode(health if role=='component-health' else timeline)))
        recovery=self.run_value('recovery-readiness-planner',recovery_input,1);row=recovery['assessment']['incidents'][0];self.assertFalse(row['ready_for_manual_recovery_review']);self.assertIsNone(recovery['qualified_scope_sha256']);self.assertTrue(any('EVIDENCE_STALE' in check['failed_criteria'] for check in row['checks']))

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])

    def test_fictional_game_health_cli(self):
        name='component-health-snapshot-checker';code,out=self.cli(name,file=ROOT/'tools'/name/'examples/game-health.json');self.assertEqual(code,0);self.assertTrue(out['assessment']['all_declared_healthy_and_fresh']);self.assertFalse(out['actual_health_verified'])
