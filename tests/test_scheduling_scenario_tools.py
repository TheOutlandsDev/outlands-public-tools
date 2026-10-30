"""Actual independent CLI and connected fictional HVAC scheduling/scenario acceptance."""
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
TOOLS={'availability-exception-planner':'availability.py','task-precedence-checker':'precedence.py',
       'schedule-timing-checker':'timing.py','schedule-scenario-comparator':'scenarios.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-scheduling-scenario-'); self.addCleanup(self.temp.cleanup)
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

    def test_connected_four_tool_hvac_working_window_and_plan_review(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        availability=self.run_value('availability-exception-planner',example('availability-exception-planner'));self.assertEqual(availability['assessment']['calendars'][0]['remaining_units'],27)
        precedence=self.run_value('task-precedence-checker',example('task-precedence-checker'));self.assertEqual(next(row for row in precedence['assessment']['tasks'] if row['id']=='hvac-service-packaging')['earliest_finish'],14)
        timing_input=example('schedule-timing-checker')
        # Explicit fictional operator adapter: a proposed new calendar revision, never a calendar update.
        timing_input['calendars'][0]['windows']=availability['assessment']['calendars'][0]['available_windows']
        self.assertEqual(sha(encode(timing_input['calendars'])),timing_input['plan']['calendars_sha256'])
        timing=self.run_value('schedule-timing-checker',timing_input);self.assertEqual(timing['tasks_sha256'],precedence['tasks_sha256']);self.assertTrue(timing['assessment']['all_declared_timing_feasible'])
        comparison_input=example('schedule-scenario-comparator');self.assertEqual(comparison_input['baseline']['plan'],timing_input['plan'])
        comparison=self.run_value('schedule-scenario-comparator',comparison_input);flow=next(row for row in comparison['assessment']['tasks'] if row['id']=='hvac-flow-inspection');self.assertEqual(flow['delta'],dict(start=1,finish=1,lateness=0));self.assertEqual(comparison['assessment']['totals']['delta'],dict(latest_finish=0,total_lateness=0));self.assertIsNone(comparison['assessment']['preferred_plan'])
        for report in (availability,precedence,timing,comparison):
            for key in ('actual_availability_verified','actual_task_durations_verified','capacity_checked','optimality_proven','calendar_updated','schedule_executed','dispatch_authorized','target_changes_performed'):self.assertFalse(report[key])

    def test_missing_proposed_task_never_improves_aggregate_comparison(self):
        source=json.loads((ROOT/'tools/schedule-scenario-comparator/examples/needs-review.json').read_text(encoding='utf-8'))
        timing=self.run_value('schedule-timing-checker',dict(format='outlands-schedule-timing-v1',**source['candidate']),1);self.assertIsNone(next(row for row in timing['assessment']['tasks'] if row['id']=='hvac-service-packaging')['finish'])
        comparison=self.run_value('schedule-scenario-comparator',source,1);self.assertIsNone(comparison['assessment']['totals']);self.assertFalse(comparison['assessment']['all_tasks_comparable']);self.assertIsNone(comparison['qualified_scope_sha256'])

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])

    def test_fictional_game_availability_cli(self):
        name='availability-exception-planner';code,out=self.cli(name,file=ROOT/'tools'/name/'examples/game-availability.json');self.assertEqual(code,0);self.assertEqual(out['assessment']['calendars'][0]['remaining_units'],27);self.assertFalse(out['calendar_updated'])


    def test_existing_public_reservation_checker_handles_capacity_separately(self):
        source=json.loads((ROOT/'tools/schedule-timing-checker/examples/input.json').read_text(encoding='utf-8'))
        timing=self.run_value('schedule-timing-checker',source)
        value=dict(format='outlands-resource-reservations-v1',resources=[dict(id='hvac-workcell',capacity=1,capabilities=[],availability=source['calendars'][0]['windows'])],reservations=[dict(id='reservation-'+row['id'],resource_id='hvac-workcell',start=row['start'],end=row['finish'],units=1) for row in timing['assessment']['tasks']])
        file=self.root/'declared-capacity.json';file.write_bytes(encode(value));script=ROOT/'tools/resource-reservation-checker/reservations.py'
        code,out=self.invoke(script,['--input',file]);self.assertEqual(code,0);self.assertEqual(out['summary'][0]['peak_units'],1);self.assertFalse(out['reservations_changed'])
        row=next(row for row in value['reservations'] if row['id']=='reservation-hvac-flow-inspection');row.update(start=3,end=7);file.write_bytes(encode(value))
        code,out=self.invoke(script,['--input',file]);self.assertEqual(code,1);self.assertEqual(out['summary'][0]['over_capacity_spans'],[dict(start=3,end=6,units=2)]);self.assertFalse(out['schedule_optimized'])
