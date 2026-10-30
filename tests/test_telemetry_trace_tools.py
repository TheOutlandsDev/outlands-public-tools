"""Actual independent CLI and connected fictional HVAC telemetry/trace acceptance."""
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
TOOLS={'metric-definition-contract-checker':'definitions.py','metric-snapshot-reconciler':'snapshots.py',
       'trace-structure-checker':'traces.py','metric-trace-correlation-checker':'correlations.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-telemetry-trace-'); self.addCleanup(self.temp.cleanup)
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
            if name=='metric-definition-contract-checker':self.assertIsNone(out['assessment']);self.assertIsNone(out['definitions_sha256'])
            else:self.assertIsNotNone(out['assessment'])

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_hvac_report_telemetry_review(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        definitions=self.run_value('metric-definition-contract-checker',example('metric-definition-contract-checker'));snapshots=self.run_value('metric-snapshot-reconciler',example('metric-snapshot-reconciler'));traces=self.run_value('trace-structure-checker',example('trace-structure-checker'));correlations=self.run_value('metric-trace-correlation-checker',example('metric-trace-correlation-checker'))
        for key in ('definitions_sha256','series_sha256'):self.assertEqual({v[key] for v in (definitions,snapshots,correlations)},{definitions[key]})
        self.assertEqual({v['runs_sha256'] for v in (snapshots,traces,correlations)},{traces['runs_sha256']});self.assertEqual(snapshots['points_sha256'],correlations['points_sha256']);self.assertEqual(traces['traces_sha256'],correlations['traces_sha256']);self.assertEqual(traces['spans_sha256'],correlations['spans_sha256'])
        self.assertTrue(all(v['state']=='valid' for v in snapshots['assessment']['coverage']));self.assertTrue(correlations['assessment']['requirements'][0]['covered'])
        for report in (definitions,snapshots,traces,correlations):
            for key in ('telemetry_collected','services_contacted','clocks_read','instrumentation_executed','artifact_bytes_verified','metrics_emitted','causation_inferred','records_changed','target_changes_performed'):self.assertFalse(report[key])

    def test_missing_metric_and_partial_trace_withhold_correlation_without_trusting_reports(self):
        name='metric-trace-correlation-checker';value=json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'));value['points'].pop(0);out=self.run_value(name,value,1);self.assertIsNone(out['assessment']);self.assertIsNone(out['qualified_scope_sha256']);self.assertTrue(any(row['code']=='REQUIRED_POINT_MISSING' for row in out['issues']))
        value=json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'));value['traces'][0]['complete']=False
        for row in value['spans']:row['trace_sha256']=sha(encode(value['traces'][0]))
        value['links'][0]['span_sha256']=sha(encode(value['spans'][1]));out=self.run_value(name,value,1);self.assertIsNone(out['assessment']);self.assertTrue(any(row['code']=='TRACE_DECLARED_PARTIAL' for row in out['issues']))
        value['status']='PASS';out=self.run_value(name,value,2);self.assertEqual(out['status'],'ERROR')

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])

    def test_fictional_game_and_ai_software_cli_examples(self):
        for name,file in [('metric-definition-contract-checker','game-metrics.json'),('trace-structure-checker','ai-software-trace.json')]:
            code,out=self.cli(name,file=ROOT/'tools'/name/'examples'/file);self.assertEqual(code,0);self.assertEqual(out['status'],'PASS');self.assertFalse(out['telemetry_collected']);self.assertFalse(out['services_contacted'])




    def test_existing_duration_analyzer_reviews_explicit_fictional_span_adapter(self):
        selected=json.loads((ROOT/'tools/trace-structure-checker/examples/input.json').read_text(encoding='utf-8'))['spans'][1]
        # Explicit teaching adapter, never an inference of actual execution or hold-free work.
        run=dict(id=selected['id'],start=selected['start'],end=selected['end']);events=[dict(id='declared-start',run_id=run['id'],at=run['start'],kind='start'),dict(id='declared-finish',run_id=run['id'],at=run['end'],kind='finish')];value=dict(format='outlands-process-event-durations-v1',runs=[run],events=events);file=self.root/'fictional-duration-adapter.json';file.write_bytes(encode(value));script=ROOT/'tools/process-event-duration-analyzer/durations.py'
        code,out=self.invoke(script,['--input',file]);self.assertEqual(code,0);self.assertEqual(out['durations'][0]['elapsed_ticks'],6);self.assertEqual(out['durations'][0]['active_ticks'],6);self.assertFalse(out['target_changes_performed'])
        value['events'].pop();file.write_bytes(encode(value));code,out=self.invoke(script,['--input',file]);self.assertEqual(code,1);self.assertIsNone(out['durations']);self.assertIsNone(out['totals'])

    def test_invalid_extra_link_does_not_erase_existing_required_coverage(self):
        name='metric-trace-correlation-checker';value=json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'));value['links'].append(dict(value['links'][0],id='link-outside',span='span-input',span_sha256=sha(encode(value['spans'][0]))));out=self.run_value(name,value,1);self.assertTrue(out['assessment']['requirements'][0]['covered']);self.assertFalse(out['assessment']['links'][0]['consistent']);self.assertIsNone(out['qualified_scope_sha256']);self.assertFalse(out['causation_inferred'])
