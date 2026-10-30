import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import scenarios as app
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
        for key in ['baseline_tasks_sha256', 'baseline_dependencies_sha256', 'baseline_calendars_sha256', 'baseline_placements_sha256', 'baseline_plan_sha256', 'candidate_tasks_sha256', 'candidate_dependencies_sha256', 'candidate_calendars_sha256', 'candidate_placements_sha256', 'candidate_plan_sha256']:self.assertIsNone(out[key])
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
        for path in [['baseline', 'tasks'], ['baseline', 'dependencies'], ['baseline', 'calendars'], ['baseline', 'placements'], ['candidate', 'tasks'], ['candidate', 'dependencies'], ['candidate', 'calendars'], ['candidate', 'placements']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['baseline_tasks_sha256', 'baseline_dependencies_sha256', 'baseline_calendars_sha256', 'baseline_placements_sha256', 'baseline_plan_sha256', 'candidate_tasks_sha256', 'candidate_dependencies_sha256', 'candidate_calendars_sha256', 'candidate_placements_sha256', 'candidate_plan_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['baseline', 'tasks'], ['baseline', 'dependencies'], ['baseline', 'calendars'], ['baseline', 'placements'], ['candidate', 'tasks'], ['candidate', 'dependencies'], ['candidate', 'calendars'], ['candidate', 'placements']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['baseline', 'tasks'], ['baseline', 'dependencies'], ['baseline', 'calendars'], ['baseline', 'placements'], ['candidate', 'tasks'], ['candidate', 'dependencies'], ['candidate', 'calendars'], ['candidate', 'placements']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['baseline', 'tasks'], ['baseline', 'dependencies'], ['baseline', 'calendars'], ['baseline', 'placements'], ['candidate', 'tasks'], ['candidate', 'dependencies'], ['candidate', 'calendars'], ['candidate', 'placements']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['baseline', 'tasks'], ['baseline', 'dependencies'], ['baseline', 'calendars'], ['baseline', 'placements'], ['candidate', 'tasks'], ['candidate', 'dependencies'], ['candidate', 'calendars'], ['candidate', 'placements']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['baseline', 'tasks'], ['baseline', 'dependencies'], ['baseline', 'calendars'], ['baseline', 'placements'], ['candidate', 'tasks'], ['candidate', 'dependencies'], ['candidate', 'calendars'], ['candidate', 'placements']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['baseline', 'tasks'], ['baseline', 'dependencies'], ['baseline', 'calendars'], ['baseline', 'placements'], ['candidate', 'tasks'], ['candidate', 'dependencies'], ['candidate', 'calendars'], ['candidate', 'placements']][0]).clear();self.withheld(value)

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

    def test_known_signed_per_task_and_complete_cohort_deltas(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');row=next(row for row in out['assessment']['tasks'] if row['id']=='hvac-flow-inspection');self.assertEqual(row['delta'],dict(start=1,finish=1,lateness=0));self.assertEqual(out['assessment']['totals']['delta'],dict(latest_finish=0,total_lateness=0));self.assertIsNone(out['assessment']['preferred_plan'])
    def test_missing_task_placement_never_improves_aggregate(self):
        self.value['candidate']['placements'].pop();out=self.review();self.assertIsNone(out['assessment']['totals']);self.assertEqual(next(row for row in out['assessment']['tasks'] if row['id']=='hvac-service-packaging')['state'],'incomplete')
    def test_added_and_removed_tasks_remain_visible_with_no_totals(self):
        b=self.value['candidate'];task=dict(id='independent-task',revision=1,duration=1,release=0,due=30);b['tasks'].append(task);b['placements'].append(dict(b['placements'][0],id='independent-placement',task=task['id'],start=0));self.rebind(b);out=self.review();self.assertEqual(next(row for row in out['assessment']['tasks'] if row['id']==task['id'])['state'],'added');self.assertIsNone(out['assessment']['totals'])
        self.value['baseline'],self.value['candidate']=self.value['candidate'],self.value['baseline'];out=self.review();self.assertEqual(next(row for row in out['assessment']['tasks'] if row['id']==task['id'])['state'],'removed')
    def test_changed_task_contract_is_incomparable(self):
        b=self.value['candidate'];b['tasks'][1]['duration']=3;self.rebind(b);out=self.review();self.assertEqual(next(row for row in out['assessment']['tasks'] if row['id']=='hvac-flow-inspection')['state'],'incomparable_task');self.assertIsNone(out['assessment']['totals'])
    def test_changed_unreferenced_context_is_conservatively_incomparable(self):
        b=self.value['candidate'];b['calendars'].append(dict(id='other-calendar',revision=1,windows=[]));self.rebind(b);out=self.review();self.assertTrue(all(row['state']=='incomparable_context' for row in out['assessment']['tasks']))
    def test_different_selected_calendar_prevents_per_task_delta(self):
        for side in ('baseline','candidate'):self.value[side]['calendars'].append(dict(self.value[side]['calendars'][0],id='alternate-calendar'));self.rebind(self.value[side])
        self.value['candidate']['placements'][0]['calendar']='alternate-calendar';self.rebind(self.value['candidate']);out=self.review();self.assertEqual(next(row for row in out['assessment']['tasks'] if row['id']=='hvac-panel-assembly')['state'],'incomparable_calendar');self.assertIsNone(out['assessment']['totals'])
    def test_feasible_later_plan_is_descriptive_without_automatic_ranking(self):
        self.value['candidate']['placements'][2]['start']=26;out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertEqual(out['assessment']['totals']['delta']['latest_finish'],11);self.assertIsNone(out['assessment']['preferred_plan'])
    def test_lateness_deltas_remain_visible_with_review_required(self):
        self.value['candidate']['placements'][2]['start']=29;out=self.review();self.assertTrue(out['assessment']['all_tasks_comparable']);self.assertEqual(out['assessment']['totals']['delta'],dict(latest_finish=14,total_lateness=2));self.assertIsNone(out['qualified_scope_sha256'])
    def test_same_plan_id_or_stale_binding_on_either_side_withholds(self):
        for side in ('baseline','candidate'):
            value=copy.deepcopy(self.value);value[side]['placements'][0]['task_sha256']='0'*64;self.withheld(value)
        self.value['candidate']['plan']['id']=self.value['baseline']['plan']['id'];self.rebind(self.value['candidate']);self.withheld()
    def test_nonobject_bundle_is_fixed_refusal(self):
        self.value['candidate']=[]
        with self.assertRaises(t.Rejected):self.run_value()
