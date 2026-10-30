import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import correlations as app
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
        for key in ['definitions_sha256', 'series_sha256', 'runs_sha256', 'points_sha256', 'traces_sha256', 'spans_sha256', 'requirements_sha256', 'links_sha256']:self.assertIsNone(out[key])
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
        for path in [['definitions'], ['series'], ['runs'], ['points'], ['traces'], ['spans'], ['requirements'], ['links']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['definitions_sha256', 'series_sha256', 'runs_sha256', 'points_sha256', 'traces_sha256', 'spans_sha256', 'requirements_sha256', 'links_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['definitions'], ['series'], ['runs'], ['points'], ['traces'], ['spans'], ['requirements'], ['links']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['definitions'], ['series'], ['runs'], ['points'], ['traces'], ['spans'], ['requirements'], ['links']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['definitions'], ['series'], ['runs'], ['points'], ['traces'], ['spans'], ['requirements'], ['links']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['definitions'], ['series'], ['runs'], ['points'], ['traces'], ['spans'], ['requirements'], ['links']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['definitions'], ['series'], ['runs'], ['points'], ['traces'], ['spans'], ['requirements'], ['links']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['definitions'], ['series'], ['runs'], ['points'], ['traces'], ['spans'], ['requirements'], ['links']][0]).clear();self.withheld(value)

    def repin_point(self):
        for row in self.value['requirements']:
            row['point_sha256']=pin(next(v for v in self.value['points'] if v['id']==row['point']))
        for row in self.value['links']:
            row['point_sha256']=pin(next(v for v in self.value['points'] if v['id']==row['point']))
    def test_known_exact_link_and_required_coverage_with_no_causation_claim(self):
        out=self.run_value();self.assertEqual(out['assessment']['requirements'][0]['consistent_link_ids'],['link-preview']);self.assertTrue(out['assessment']['requirements'][0]['covered']);self.assertFalse(out['assessment']['semantic_relationship_verified']);self.assertFalse(out['assessment']['clock_synchronization_verified']);self.assertFalse(out['causation_inferred'])
    def test_missing_links_never_prove_correlation(self):
        self.value['links']=[];row=self.review()['assessment']['requirements'][0];self.assertFalse(row['covered']);self.assertEqual(row['consistent_link_ids'],[])
    def test_no_required_selection_never_passes_vacuously(self):
        self.value['requirements']=[];self.value['links']=[];self.withheld()
    def test_requirement_and_point_span_link_aliases_are_ambiguous(self):
        for field in ('requirements','links'):
            value=copy.deepcopy(self.value);value[field].append(dict(value[field][0],id='alias'));self.withheld(value)
    def test_unknown_stale_point_and_span_references_withhold(self):
        for change in ({'point':'other'},{'point_sha256':'0'*64},{'span':'other'},{'span_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['links'][0].update(change);self.withheld(value)
    def test_invalid_source_metric_or_partial_trace_withholds_whole_correlation(self):
        value=copy.deepcopy(self.value);value['points'][1]['value']='100';self.withheld(value)
        self.value['traces'][0]['complete']=False
        for row in self.value['spans']:row['trace_sha256']=pin(self.value['traces'][0])
        self.value['links'][0]['span_sha256']=pin(self.value['spans'][1]);out=self.withheld();self.assertTrue(any(row['code']=='TRACE_DECLARED_PARTIAL' for row in out['issues']))
    def test_link_window_includes_start_excludes_end_and_zero_duration(self):
        point=self.value['points'][2];point['at']=12;self.repin_point();self.value['links'][0]['at']=12;self.assertEqual(self.run_value()['status'],'PASS');point['at']=18;self.repin_point();self.value['links'][0]['at']=18;self.assertIn('LINK_TIME_OUTSIDE_SPAN',self.review()['assessment']['links'][0]['failed_criteria'])
        point['at']=12;self.repin_point();self.value['links'][0]['at']=12;self.value['spans'][1]['end']=12;self.value['links'][0]['span_sha256']=pin(self.value['spans'][1]);self.assertEqual(self.review()['assessment']['links'][0]['failed_criteria'],['LINK_TIME_OUTSIDE_SPAN'])
    def test_link_time_cannot_drift_from_selected_point_time(self):
        self.value['links'][0]['at']=14;row=self.review()['assessment']['links'][0];self.assertEqual(row['failed_criteria'],['LINK_POINT_TIME_MISMATCH'])
    def test_same_clock_label_does_not_allow_cross_run_correlation(self):
        run=dict(self.value['runs'][0],id='other-run');self.value['runs'].append(run)
        self.value['points'].extend([dict(row,id='other-'+row['id'],run=run['id'],run_sha256=pin(run)) for row in list(self.value['points'])]);trace=self.value['traces'][0];trace.update(run=run['id'],run_sha256=pin(run))
        for row in self.value['spans']:row['trace_sha256']=pin(trace)
        self.value['links'][0]['span_sha256']=pin(self.value['spans'][1]);self.assertEqual(self.review()['assessment']['links'][0]['failed_criteria'],['LINK_RUN_MISMATCH'])
    def test_unselected_existing_point_is_not_silently_added_to_scope(self):
        point=self.value['points'][0];self.value['links'][0].update(point=point['id'],point_sha256=pin(point));self.withheld()
    def test_multiple_distinct_span_links_are_accounted_explicitly(self):
        self.value['links'].append(dict(self.value['links'][0],id='link-root',span='span-root',span_sha256=pin(self.value['spans'][2])));out=self.run_value();self.assertEqual(out['assessment']['requirements'][0]['consistent_link_ids'],['link-preview','link-root'])
    def test_one_consistent_link_does_not_erase_invalid_extra_link(self):
        self.value['links'].append(dict(self.value['links'][0],id='link-outside',span='span-input',span_sha256=pin(self.value['spans'][0])));out=self.review();self.assertTrue(out['assessment']['requirements'][0]['covered']);self.assertFalse(out['assessment']['links'][0]['consistent']);self.assertIsNone(out['qualified_scope_sha256'])
