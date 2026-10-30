import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import traces as app
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
        for key in ['runs_sha256', 'traces_sha256', 'spans_sha256']:self.assertIsNone(out[key])
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
        for path in [['runs'], ['traces'], ['spans']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['runs_sha256', 'traces_sha256', 'spans_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['runs'], ['traces'], ['spans']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['runs'], ['traces'], ['spans']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['runs'], ['traces'], ['spans']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['runs'], ['traces'], ['spans']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['runs'], ['traces'], ['spans']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['runs'], ['traces'], ['spans']][0]).clear();self.withheld(value)

    def repin(self):
        trace=copy.deepcopy(self.value['traces'][0]);trace['expected_spans'].sort()
        for row in self.value['spans']:row['trace_sha256']=pin(trace)
    def test_known_root_coverage_and_individual_durations(self):
        out=self.run_value();row=out['assessment']['traces'][0];self.assertEqual(row['root_ids'],['span-root']);self.assertEqual(row['observed_span_count'],3);self.assertEqual({v['id']:v['declared_duration'] for v in out['assessment']['spans']},{'span-input':3,'span-preview':6,'span-root':15});self.assertFalse(out['assessment']['parent_containment_assumed'])
    def test_async_child_can_outlive_parent_without_assumed_serial_execution(self):
        self.value['spans'][0]['end']=28;out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertFalse(out['assessment']['causal_order_verified'])
    def test_zero_duration_is_valid_but_reversed_span_is_rejected(self):
        self.value['spans'][0]['end']=11;self.assertEqual(self.run_value()['status'],'PASS');self.value['spans'][0]['end']=10;self.withheld()
    def test_missing_span_coverage_is_not_repaired_or_declared_complete(self):
        self.value['spans']=[];row=self.review()['assessment']['traces'][0];self.assertEqual(row['missing_span_ids'],['span-input','span-preview','span-root']);self.assertEqual(row['root_ids'],[]);self.assertIsNone(row['observed_start'])
    def test_unexpected_span_is_visible_in_complete_selected_scope(self):
        self.value['spans'].append(dict(self.value['spans'][0],id='unexpected-span'));row=self.review()['assessment']['traces'][0];self.assertEqual(row['unexpected_span_ids'],['unexpected-span']);self.assertEqual(row['observed_span_count'],4)
    def test_partial_declaration_remains_review_even_with_all_selected_records(self):
        self.value['traces'][0]['complete']=False;self.repin();row=self.review()['assessment']['traces'][0];self.assertFalse(row['complete_declared']);self.assertEqual(row['missing_span_ids'],[])
    def test_multiple_roots_require_review(self):
        self.value['spans'][0]['parent']=None;self.assertEqual(self.review()['assessment']['traces'][0]['root_ids'],['span-input','span-root'])
    def test_unknown_parent_self_cycle_and_multi_span_cycles_withhold(self):
        for parent in ('other','span-input'):
            value=copy.deepcopy(self.value);value['spans'][0]['parent']=parent;self.withheld(value)
        self.value['spans'][2]['parent']='span-input';self.withheld()
    def test_parent_cannot_silently_cross_trace_scope(self):
        trace=dict(self.value['traces'][0],id='other-trace',expected_spans=['other-root']);self.value['traces'].append(trace);self.value['spans'].append(dict(self.value['spans'][2],id='other-root',trace=trace['id'],trace_sha256=pin(trace)));self.value['spans'][0]['parent']='other-root';self.withheld()
    def test_run_boundaries_and_exact_trace_run_pins_are_checked(self):
        value=copy.deepcopy(self.value);value['spans'][0]['start']=9;self.assertTrue(any(v['code']=='SPAN_TIME_OUTSIDE_RUN' for v in self.review(value)['issues']));self.value['traces'][0]['run_revision']=2;self.withheld()
    def test_expected_span_identity_ownership_is_unique_and_bounded(self):
        value=copy.deepcopy(self.value);value['traces'].append(dict(value['traces'][0],id='alias'));self.withheld(value)
        self.value['traces']=[dict(self.value['traces'][0],id='trace-'+str(i),expected_spans=['span-'+str(i)+'-'+str(j) for j in range(128)]) for i in range(33)];self.value['spans']=[]
        with self.assertRaisesRegex(t.Rejected,'TRACE_EXPECTATION_SCOPE_LIMIT'):self.run_value()
    def test_empty_runs_or_traces_never_pass_and_expected_ids_are_set_like(self):
        for field in ('runs','traces'):
            value=copy.deepcopy(self.value);value[field]=[];self.withheld(value)
        before=self.run_value();self.value['traces'][0]['expected_spans'].reverse();self.assertEqual(before['qualified_scope_sha256'],self.run_value()['qualified_scope_sha256'])
