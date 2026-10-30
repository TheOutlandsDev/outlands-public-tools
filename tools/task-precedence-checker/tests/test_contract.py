import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import precedence as app
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
        for key in ['tasks_sha256', 'dependencies_sha256']:self.assertIsNone(out[key])
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
        for path in [['tasks'], ['dependencies']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['tasks_sha256', 'dependencies_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['tasks'], ['dependencies']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['tasks'], ['dependencies']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['tasks'], ['dependencies']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['tasks'], ['dependencies']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['tasks'], ['dependencies']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['tasks'], ['dependencies']][0]).clear();self.withheld(value)

    def edge(self,before,after,id='extra-edge'):
        tasks={row['id']:row for row in self.value['tasks']};return dict(id=id,predecessor=before,predecessor_revision=tasks[before]['revision'],predecessor_sha256=pin(tasks[before]),successor=after,successor_revision=tasks[after]['revision'],successor_sha256=pin(tasks[after]),minimum_lag=0)
    def test_known_precedence_lower_bounds_include_declared_lag(self):
        out=self.run_value();rows={row['id']:row for row in out['assessment']['tasks']};self.assertEqual((rows['hvac-panel-assembly']['earliest_finish'],rows['hvac-flow-inspection']['earliest_start'],rows['hvac-service-packaging']['earliest_finish']),(6,7,14));self.assertFalse(out['assessment']['calendar_and_capacity_constraints_applied'])
    def test_release_can_dominate_predecessor_bound(self):
        row=self.value['tasks'][1];row['release']=10
        for edge in self.value['dependencies']:
            for field in ('predecessor','successor'):
                if edge[field]==row['id']:edge[field+'_sha256']=pin(row)
        result=next(row for row in self.run_value()['assessment']['tasks'] if row['id']=='hvac-flow-inspection');self.assertEqual(result['earliest_start'],10)
    def test_impossible_due_retains_exact_lower_bound_and_lateness(self):
        self.value['tasks'][2]['due']=10
        for edge in self.value['dependencies']:
            if edge['successor']==self.value['tasks'][2]['id']:edge['successor_sha256']=pin(self.value['tasks'][2])
        result=next(row for row in self.review()['assessment']['tasks'] if row['id']=='hvac-service-packaging');self.assertEqual(result['unavoidable_lateness'],4)
    def test_self_cycle_and_disconnected_cycle_withhold_all(self):
        self.value['dependencies'].append(self.edge('hvac-service-packaging','hvac-panel-assembly'));self.withheld()
        self.value['dependencies'].pop();task=dict(id='independent',revision=1,duration=1,release=0,due=10);self.value['tasks'].append(task);self.value['dependencies'].append(self.edge(task['id'],task['id']));self.withheld()
    def test_duplicate_endpoint_pairs_are_ambiguous(self):
        self.value['dependencies'].append(dict(self.value['dependencies'][0],id='alias'));self.withheld()
    def test_unknown_or_stale_task_reference_withholds(self):
        for update in ({'predecessor':'other'},{'successor_revision':2},{'predecessor_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['dependencies'][0].update(update);self.withheld(value)
    def test_positive_duration_and_nonnegative_lag_are_strict(self):
        for update in ({'duration':0},{'duration':True},{'release':11,'due':10}):
            value=copy.deepcopy(self.value);value['tasks'][0].update(update);self.withheld(value)
        self.value['dependencies'][0]['minimum_lag']=-1;self.withheld()
    def test_independent_tasks_and_long_chain_are_iterative(self):
        self.value['tasks']=[dict(id='task-'+str(n),revision=1,duration=1,release=0,due=10**9) for n in range(700)];self.value['dependencies']=[self.edge('task-'+str(n),'task-'+str(n+1),'edge-'+str(n)) for n in range(699)]
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertEqual(next(row for row in out['assessment']['tasks'] if row['id']=='task-699')['earliest_finish'],700)
