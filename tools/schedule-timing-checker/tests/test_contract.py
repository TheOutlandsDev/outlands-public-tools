import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import timing as app
import schedule_core as r

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()
def at(value,path):
    for key in path:value=value[key]
    return value

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        out=self.run_value(value);self.assertEqual(out['status'],'REVIEW_REQUIRED');self.assertTrue(out['issues']);self.assertIsNone(out['qualified_scope_sha256']);return out
    def withheld(self,value=None):
        out=self.review(value);self.assertIsNone(out['assessment'])
        for key in ['tasks_sha256', 'dependencies_sha256', 'calendars_sha256', 'placements_sha256', 'plan_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('actual_availability_verified','actual_task_durations_verified','capacity_checked','optimality_proven','calendar_updated','schedule_executed','dispatch_authorized','records_changed','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['tasks'], ['dependencies'], ['calendars'], ['placements']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['tasks_sha256', 'dependencies_sha256', 'calendars_sha256', 'placements_sha256', 'plan_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['tasks'], ['dependencies'], ['calendars'], ['placements']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['tasks'], ['dependencies'], ['calendars'], ['placements']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['tasks'], ['dependencies'], ['calendars'], ['placements']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['tasks'], ['dependencies'], ['calendars'], ['placements']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['tasks'], ['dependencies'], ['calendars'], ['placements']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['tasks'], ['dependencies'], ['calendars'], ['placements']][0]).clear();self.withheld(value)

    def rebind(self,b=None):
        b=self.value if b is None else b;tasks={row['id']:row for row in b['tasks']};calendars={row['id']:r.calendar(row)[1] for row in b['calendars']}
        for edge in b['dependencies']:
            for field in ('predecessor','successor'):
                if edge[field] in tasks:edge[field+'_sha256']=pin(tasks[edge[field]]);edge[field+'_revision']=tasks[edge[field]]['revision']
        header=b['plan'];header.update(tasks_sha256=pin(sorted(tasks.values(),key=lambda row:row['id'])),dependencies_sha256=pin(sorted(b['dependencies'],key=lambda row:row['id'])),calendars_sha256=pin(sorted(calendars.values(),key=lambda row:row['id'])))
        for row in b['placements']:
            row.update(plan=header['id'],plan_revision=header['revision'],plan_sha256=pin(header))
            if row['task'] in tasks:row.update(task_revision=tasks[row['task']]['revision'],task_sha256=pin(tasks[row['task']]))
            if row['calendar'] in calendars:row.update(calendar_revision=calendars[row['calendar']]['revision'],calendar_sha256=pin(calendars[row['calendar']]))

    def test_known_placements_and_derived_finishes(self):
        out=self.run_value();self.assertTrue(out['assessment']['all_declared_timing_feasible']);self.assertEqual({row['id']:row['finish'] for row in out['assessment']['tasks']},{'hvac-panel-assembly':6,'hvac-flow-inspection':11,'hvac-service-packaging':18});self.assertFalse(out['capacity_checked'])
    def test_half_open_window_end_is_accepted_but_gap_crossing_is_not(self):
        self.value['placements'][1]['start']=8;self.assertEqual(self.run_value()['status'],'PASS');self.value['placements'][1]['start']=9;out=self.review();row=next(row for row in out['assessment']['tasks'] if row['id']=='hvac-flow-inspection');self.assertIn('OUTSIDE_WORKING_WINDOW',row['failed_criteria'])
    def test_minimum_lag_violation_is_not_calendar_capacity(self):
        self.value['placements'][1]['start']=6;row=next(row for row in self.review()['assessment']['tasks'] if row['id']=='hvac-flow-inspection');self.assertEqual(row['failed_criteria'],['PRECEDENCE_LAG_VIOLATION'])
    def test_missing_placement_and_missing_predecessor_stay_visible(self):
        self.value['placements'].pop(1);out=self.review();rows={row['id']:row for row in out['assessment']['tasks']};self.assertIsNone(rows['hvac-flow-inspection']['finish']);self.assertIn('PREDECESSOR_PLACEMENT_MISSING',rows['hvac-service-packaging']['failed_criteria'])
    def test_release_due_and_calendar_violations_retain_all_criteria(self):
        self.value['tasks'][0]['release']=1;self.rebind();out=self.review();self.assertIn('START_BEFORE_RELEASE',next(row for row in out['assessment']['tasks'] if row['id']=='hvac-panel-assembly')['failed_criteria'])
        self.value['placements'][2]['start']=29;row=next(row for row in self.review()['assessment']['tasks'] if row['id']=='hvac-service-packaging');self.assertEqual(row['lateness'],2);self.assertIn('FINISH_AFTER_DUE',row['failed_criteria']);self.assertIn('OUTSIDE_WORKING_WINDOW',row['failed_criteria'])
    def test_multiple_placements_do_not_select_best_or_latest(self):
        self.value['placements'].append(dict(self.value['placements'][0],id='alias',start=1));self.withheld()
    def test_plan_cohort_and_full_snapshot_bindings_are_exact(self):
        for update in ({'plan':'other'},{'plan_revision':2},{'plan_sha256':'0'*64},{'task':'other'},{'calendar':'other'},{'task_sha256':'0'*64},{'calendar_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['placements'][0].update(update);self.withheld(value)
        self.value['plan']['tasks_sha256']='0'*64;self.withheld()
    def test_invalid_graph_or_empty_required_calendar_withholds(self):
        value=copy.deepcopy(self.value);value['calendars']=[];self.withheld(value)
        self.value['dependencies'][0]['successor']=self.value['dependencies'][0]['predecessor'];self.rebind();self.withheld()
    def test_no_placements_reports_all_tasks_missing(self):
        self.value['placements']=[];out=self.review();self.assertEqual(len(out['assessment']['tasks']),3);self.assertTrue(all(row['failed_criteria']==['PLACEMENT_MISSING'] for row in out['assessment']['tasks']))
