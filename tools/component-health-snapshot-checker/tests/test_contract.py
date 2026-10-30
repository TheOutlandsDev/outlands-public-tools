import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import health as app
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
        for key in ['components_sha256', 'observations_sha256']:self.assertIsNone(out[key])
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
        for path in [['components'], ['observations']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['components_sha256', 'observations_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['components'], ['observations']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['components'], ['observations']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['components'], ['observations']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['components'], ['observations']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['components'], ['observations']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['components'], ['observations']][0]).clear();self.withheld(value)

    def test_known_freshness_at_inclusive_deadline(self):
        self.value['as_of']=30;out=self.run_value();self.assertEqual(out['status'],'PASS');row=out['assessment']['components'][0];self.assertEqual(row['age'],10);self.assertTrue(row['fresh'])
        self.value['as_of']=31;row=self.review()['assessment']['components'][0];self.assertEqual(row['age'],11);self.assertFalse(row['fresh']);self.assertEqual(row['failed_criteria'],['OBSERVATION_STALE'])
    def test_future_observation_has_no_negative_age_or_fresh_claim(self):
        self.value['as_of']=19;row=self.review()['assessment']['components'][0];self.assertIsNone(row['age']);self.assertTrue(row['future']);self.assertFalse(row['fresh'])
    def test_missing_observation_remains_visible(self):
        self.value['observations']=[];row=self.review()['assessment']['components'][0];self.assertIsNone(row['declared_state']);self.assertEqual(row['failed_criteria'],['OBSERVATION_MISSING'])
    def test_every_nonhealthy_declared_state_requires_review(self):
        for state in ('degraded','down','unknown','maintenance'):
            value=copy.deepcopy(self.value);value['observations'][0]['state']=state;self.assertFalse(self.review(value)['assessment']['components'][0]['declared_healthy_and_fresh'])
    def test_two_observation_ids_do_not_select_latest(self):
        self.value['observations'].append(dict(self.value['observations'][0],id='newer',observed_at=25));self.withheld()
    def test_stale_or_unknown_component_binding_withholds(self):
        for change in ({'component':'other'},{'component_revision':2},{'component_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['observations'][0].update(change);self.withheld(value)
    def test_zero_age_policy_accepts_only_same_ordinal(self):
        row=self.value['components'][0];row['maximum_age']=0;self.value['observations'][0]['component_sha256']=pin(row);self.value['as_of']=20;self.assertEqual(self.run_value()['status'],'PASS');self.value['as_of']=21;self.review()
    def test_boolean_and_invalid_time_state_shapes_refuse(self):
        for change in ({'observed_at':True},{'observed_at':-1},{'state':'green'}):
            value=copy.deepcopy(self.value);value['observations'][0].update(change);self.withheld(value)
        self.value['as_of']=True
        with self.assertRaises(t.Rejected):self.run_value()
    def test_asof_changes_qualified_scope_even_while_fresh(self):
        before=self.run_value()['qualified_scope_sha256'];self.value['as_of']=26;self.assertNotEqual(self.run_value()['qualified_scope_sha256'],before)
