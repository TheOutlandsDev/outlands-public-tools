import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import alerts as app
import health_core as r

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
        for key in ['components_sha256', 'alerts_sha256', 'policy_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('observations_independently_verified','artifact_bytes_verified','actual_health_verified','notifications_sent','alerts_suppressed','recovery_authorized','recovery_performed','records_changed','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['components'], ['alerts']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['components_sha256', 'alerts_sha256', 'policy_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['components'], ['alerts']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['components'], ['alerts']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['components'], ['alerts']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['components'], ['alerts']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['components'], ['alerts']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['components'], ['alerts']][0]).clear();self.withheld(value)

    def test_known_anchored_groups_and_complete_accounting(self):
        out=self.run_value();rows=out['assessment']['groups'];self.assertEqual([row['alert_ids'] for row in rows],[['alert-1','alert-2'],['alert-3']]);self.assertEqual(rows[0]['highest_declared_severity'],'critical');self.assertEqual((out['assessment']['selected_alerts'],out['assessment']['grouped_alerts'],out['assessment']['suppressed_alerts']),(3,3,0))
    def test_inclusive_anchor_boundary_is_not_a_sliding_bridge(self):
        for row,at in zip(self.value['alerts'],[0,10,20]):row['at']=at
        rows=self.run_value()['assessment']['groups'];self.assertEqual([row['alert_ids'] for row in rows],[['alert-1','alert-2'],['alert-3']]);self.assertEqual(rows[0]['window_end'],10)
    def test_zero_window_groups_only_equal_ordinals(self):
        self.value['policy']['window']=0;self.value['alerts'][1]['at']=10;self.assertEqual([len(row['alert_ids']) for row in self.run_value()['assessment']['groups']],[2,1])
    def test_components_and_keys_are_independent_partitions(self):
        component=dict(self.value['components'][0],id='hvac-other');self.value['components'].append(component);self.value['alerts'][1].update(component=component['id'],component_sha256=pin(component));self.value['alerts'][2]['key']='other-key';self.assertEqual(len(self.run_value()['assessment']['groups']),3)
    def test_group_pins_and_order_are_stable_under_input_order(self):
        before=self.run_value();self.value['alerts'].reverse();self.assertEqual(self.run_value()['assessment'],before['assessment'])
    def test_severity_does_not_authorize_suppression_or_dispatch(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertFalse(out['alerts_suppressed']);self.assertFalse(out['notifications_sent']);self.assertEqual(out['assessment']['groups'][0]['highest_declared_severity'],'critical')
    def test_unknown_component_and_stale_snapshot_withhold(self):
        for change in ({'component':'unknown'},{'component_revision':2},{'component_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['alerts'][0].update(change);self.withheld(value)
    def test_invalid_severity_time_and_policy_bounds_refuse(self):
        for change in ({'severity':'urgent'},{'at':True},{'at':-1}):
            value=copy.deepcopy(self.value);value['alerts'][0].update(change);self.withheld(value)
        self.value['policy']['window']=-1
        with self.assertRaises(t.Rejected):self.run_value()
    def test_distinct_ids_with_equal_metadata_are_preserved_as_distinct_alerts(self):
        self.value['alerts'].append(dict(self.value['alerts'][0],id='separate-alert'));out=self.run_value();self.assertEqual(out['assessment']['grouped_alerts'],4);self.assertIn('separate-alert',out['assessment']['groups'][0]['alert_ids'])
    def test_empty_alerts_never_issues_a_noop_qualification(self):
        self.value['alerts']=[];self.withheld()
