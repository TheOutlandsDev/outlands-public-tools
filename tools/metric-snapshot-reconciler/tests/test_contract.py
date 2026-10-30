import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import snapshots as app
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
        for key in ['definitions_sha256', 'series_sha256', 'runs_sha256', 'points_sha256']:self.assertIsNone(out[key])
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
        for path in [['definitions'], ['series'], ['runs'], ['points']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['definitions_sha256', 'series_sha256', 'runs_sha256', 'points_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['definitions'], ['series'], ['runs'], ['points']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['definitions'], ['series'], ['runs'], ['points']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['definitions'], ['series'], ['runs'], ['points']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['definitions'], ['series'], ['runs'], ['points']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['definitions'], ['series'], ['runs'], ['points']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['definitions'], ['series'], ['runs'], ['points']][0]).clear();self.withheld(value)

    def test_known_exact_scalar_values_and_disjoint_bucket_count(self):
        out=self.run_value();rows={v['id']:v for v in out['assessment']['points']};self.assertEqual(rows['point-depth']['value'],'4');self.assertEqual((rows['point-latency']['count'],rows['point-latency']['sum'],rows['point-latency']['buckets']),(2,'12',[1,1,0]));self.assertTrue(all(v['state']=='valid' for v in out['assessment']['coverage']));self.assertFalse(out['assessment']['underlying_observations_verified'])
    def test_missing_required_point_is_not_zero_and_optional_absence_is_explicit(self):
        self.value['points'].pop(0);out=self.review();self.assertEqual(out['assessment']['coverage'][0]['state'],'required_missing');self.assertIsNone(out['assessment']['coverage'][0]['point_id']);self.value['series'][0]['required']=False;self.assertEqual(self.run_value()['assessment']['coverage'][0]['state'],'optional_absent')
    def test_alias_snapshot_slot_is_not_latest_selection_or_time_series(self):
        self.value['points'].append(dict(self.value['points'][0],id='later',at=16));self.withheld()
    def test_counter_and_gauge_limits_remain_visible_findings(self):
        for index,value in ((0,'-1'),(1,'21'),(1,'-0.25')):
            data=copy.deepcopy(self.value);data['points'][index]['value']=value;out=self.review(data);self.assertFalse(out['assessment']['points'][index]['consistent']);self.assertIn('invalid',[v['state'] for v in out['assessment']['coverage']])
    def test_empty_histogram_requires_zero_sum_and_never_invents_observations(self):
        row=self.value['points'][2];row.update(count=0,sum='0',buckets=[0,0,0]);self.assertEqual(self.run_value()['status'],'PASS');row['sum']='1';self.assertIn('EMPTY_HISTOGRAM_SUM_NONZERO',self.review()['assessment']['points'][2]['failed_criteria'])
    def test_bucket_counts_are_disjoint_and_must_total_declared_count(self):
        self.value['points'][2]['buckets']=[1,2,0];out=self.review();self.assertIn('HISTOGRAM_COUNT_MISMATCH',out['assessment']['points'][2]['failed_criteria']);self.assertEqual(out['assessment']['points'][2]['buckets'],[1,2,0])
    def test_metric_kind_payload_and_bucket_shape_are_structural(self):
        value=copy.deepcopy(self.value);value['points'][2]['buckets']=[1,1];self.withheld(value);self.value['points'][0]['sum']='0';self.withheld()
    def test_run_bounds_are_inclusive_and_outside_times_are_not_hidden(self):
        for at in (10,30):
            value=copy.deepcopy(self.value);value['points'][0]['at']=at;self.assertEqual(self.run_value(value)['status'],'PASS')
        self.value['points'][0]['at']=31;self.assertIn('POINT_TIME_OUTSIDE_RUN',self.review()['assessment']['points'][0]['failed_criteria'])
    def test_exact_series_run_revisions_and_source_pins_withhold(self):
        for change in ({'series':'other'},{'series_sha256':'0'*64},{'run_revision':2},{'run_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['points'][0].update(change);self.withheld(value)
    def test_exact_decimal_normalization_and_strict_numeric_shapes(self):
        self.value['points'][0]['value']='-0.0000';self.assertEqual(self.run_value()['assessment']['points'][0]['value'],'0')
        for change in ({'value':True},{'at':True},{'count':True},{'buckets':[True]}):
            value=copy.deepcopy(self.value);value['points'][0].update(change);self.withheld(value)
    def test_expected_series_run_product_is_bounded_before_expansion(self):
        self.value['series']=[dict(self.value['series'][0],id='series-'+str(i),labels={'stage':'stage-'+str(i)}) for i in range(21)];self.value['runs']=[dict(self.value['runs'][0],id='run-'+str(i)) for i in range(1000)];self.value['points']=[]
        with self.assertRaisesRegex(t.Rejected,'METRIC_COVERAGE_LIMIT'):self.run_value()
    def test_all_optional_empty_points_remain_explicit_absence_not_health_proof(self):
        self.value['points']=[]
        for row in self.value['series']:row['required']=False
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertTrue(all(row['state']=='optional_absent' for row in out['assessment']['coverage']));self.assertFalse(out['telemetry_collected'])
