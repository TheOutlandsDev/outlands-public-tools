import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import definitions as app
import telemetry_core as r

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
        for key in ['definitions_sha256', 'series_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('telemetry_collected','services_contacted','clocks_read','instrumentation_executed','artifact_bytes_verified','metrics_emitted','causation_inferred','records_changed','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['definitions'], ['series']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['definitions_sha256', 'series_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['definitions'], ['series']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['definitions'], ['series']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['definitions'], ['series']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['definitions'], ['series']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['definitions'], ['series']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['definitions'], ['series']][0]).clear();self.withheld(value)

    def test_known_metric_kinds_units_and_declared_series(self):
        out=self.run_value();self.assertEqual([v['kind'] for v in out['assessment']['definitions']],['counter','histogram','gauge']);self.assertTrue(all(v['declared_series_count']==v['required_series_count']==1 for v in out['assessment']['definitions']));self.assertFalse(out['assessment']['unit_semantics_verified'])
    def test_unknown_stale_metric_and_label_keys_withhold(self):
        for change in ({'metric':'other'},{'metric_revision':2},{'metric_sha256':'0'*64},{'labels':{'undeclared':'preview'}}):
            value=copy.deepcopy(self.value);value['series'][0].update(change);self.withheld(value)
    def test_series_aliases_are_ambiguous_even_when_required_flags_match(self):
        self.value['series'].append(dict(self.value['series'][0],id='alias'));self.withheld()
    def test_number_normalization_keeps_exact_definition_pin(self):
        before=self.run_value();self.value['definitions'][0]['minimum']='-0.000';out=self.run_value();self.assertEqual(before['definitions_sha256'],out['definitions_sha256']);self.assertEqual(r.number('-3.2500'),(r.Fraction(-13,4),'-3.25'))
    def test_nonincreasing_and_duplicate_bucket_bounds_are_rejected_rows(self):
        for bounds in (['10','5'],['5','5.0']):
            value=copy.deepcopy(self.value);value['definitions'][1]['bounds']=bounds;self.withheld(value)
    def test_counter_requires_zero_lower_limit_and_nonnegative_upper(self):
        for change in ({'minimum':None},{'minimum':'-1'},{'maximum':'-1'}):
            value=copy.deepcopy(self.value);value['definitions'][0].update(change);self.withheld(value)
    def test_gauge_bounds_and_scalar_bucket_payload_are_strict(self):
        for change in ({'minimum':'21'},{'bounds':['1']},{'maximum':True}):
            value=copy.deepcopy(self.value);value['definitions'][2].update(change);self.withheld(value)
    def test_histogram_has_no_implicit_scalar_limits_and_can_have_one_overflow_bucket(self):
        value=copy.deepcopy(self.value);value['definitions'][1]['minimum']='0';self.withheld(value);metric=self.value['definitions'][1];metric['bounds']=[];self.value['series'][2]['metric_sha256']=pin(metric);self.assertEqual(self.run_value()['status'],'PASS')
    def test_label_limits_duplicate_keys_and_symbolic_values_are_strict(self):
        for labels in ({'stage':'INVALID_SENTINEL'},{str(i):'value' for i in range(9)},[],{'stage':'../private'}):
            value=copy.deepcopy(self.value);value['series'][0]['labels']=labels;self.withheld(value)
        self.value['definitions'][0]['label_keys']=['stage','stage'];self.withheld()
    def test_empty_required_definition_or_series_cohort_never_passes(self):
        for field in ('definitions','series'):
            value=copy.deepcopy(self.value);value[field]=[];self.withheld(value)
    def test_opaque_unit_labels_do_not_trigger_conversion_or_instrumentation(self):
        metric=self.value['definitions'][0];metric['unit']='invented-jobs';self.value['series'][0]['metric_sha256']=pin(metric);out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertFalse(out['instrumentation_executed'])
    def test_decimal_exponents_precision_and_bucket_limits_are_refused(self):
        for bad in ('1e3','1.0000001','1000000000000','+1'):
            value=copy.deepcopy(self.value);value['definitions'][2]['maximum']=bad;self.withheld(value)
        self.value['definitions'][1]['bounds']=[str(i) for i in range(17)];self.withheld()
