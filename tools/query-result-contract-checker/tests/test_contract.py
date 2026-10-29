from results import check as OP

import copy
import json
from pathlib import Path
import unittest
import toolkit as t
from test_relational_core import col,table,fk,dataset

def sample(): return json.loads((Path(__file__).parent.parent/'examples/input.json').read_text(encoding='utf-8'))
def run(value): return OP(t.encode(value))

class Contracts(unittest.TestCase):
    def test_example_passes(self): self.assertEqual(run(sample())['status'],'PASS')

    def test_review_example(self):
        value=json.loads((Path(__file__).parent.parent/'examples/needs-review.json').read_text(encoding='utf-8'))
        self.assertEqual(run(value)['status'],'REVIEW_REQUIRED')

    def test_wrong_format_and_unknown_field(self):
        for changes in ({'format':'unsupported'},{'unexpected':'invented'}):
            with self.assertRaises(t.Rejected): run(dict(sample(),**changes))

    def test_ambiguous_json_and_malformed_outer_shapes(self):
        for raw in (b'{"format":1,"format":2}',b'NaN',b'1.0',b'"\\ud800"',b'null',b'[]',b'{}'):
            with self.assertRaises(t.Rejected): OP(raw)

    def test_raw_input_pin_and_no_mutation(self):
        value=sample(); before=copy.deepcopy(value); raw=t.encode(value); result=OP(raw)
        self.assertEqual(value,before); self.assertEqual(result['input_sha256'],t.digest(raw)); self.assertFalse(result['sql_executed'])
        self.assertFalse(result['target_changes_performed'])

    def test_json_round_trip(self):
        result=run(sample()); self.assertEqual(t.decode(t.encode(result)),result)

    def test_known_pins_and_summary(self):
        value=sample(); result=run(value)
        self.assertEqual(result['summary'],dict(returned_rows=1,declared_complete=True))
        self.assertEqual(result['recomputed_pins']['query_sha256'],t.digest(value['query'].encode()))

    def test_every_pin_checked_against_actual_embedded_input(self):
        for side in ('contract','result'):
            for field in ('query_sha256','dataset_sha256','bindings_sha256'):
                value=sample(); value[side][field]='0'*64; self.assertIsNone(run(value)['summary'])

    def test_matching_false_pins_cannot_pass(self):
        value=sample(); value['contract']['query_sha256']=value['result']['query_sha256']='0'*64
        self.assertEqual(len([i for i in run(value)['issues'] if i['code']=='QUERY_SHA256_MISMATCH']),2)

    def test_ordered_columns_and_row_types(self):
        value=sample(); value['result']['columns'].reverse(); self.assertIsNone(run(value)['summary'])
        value=sample(); value['result']['rows']=[[1,'Invented amber']]; self.assertIsNone(run(value)['summary'])

    def test_required_complete_and_explicit_partial_policy(self):
        value=sample(); value['result']['truncated']=True; self.assertIsNone(run(value)['summary'])
        value['contract']['require_complete']=False; result=run(value)
        self.assertEqual(result['status'],'PASS'); self.assertFalse(result['summary']['declared_complete']); self.assertFalse(result['completeness_authority_verified'])

    def test_result_row_range(self):
        value=sample(); value['result']['rows']=[]; self.assertIsNone(run(value)['summary'])
        value['contract']['min_rows']=0; self.assertEqual(run(value)['status'],'PASS')

    def test_contract_range_and_boolean_flags_refused(self):
        for changes in ({'min_rows':True},{'max_rows':0},{'require_complete':1},{'max_rows':1001}):
            value=sample(); value['contract'].update(changes)
            with self.assertRaises(t.Rejected): run(value)
        value=sample(); value['result']['truncated']=0
        with self.assertRaises(t.Rejected): run(value)

    def test_changed_binding_and_dataset_pin(self):
        for field in ('bindings','dataset'):
            value=sample()
            if field=='bindings': value['bindings']['selected']='b'
            else: value['dataset']['tables'][0]['rows'][0][1]='Changed invented label'
            self.assertIsNone(run(value)['summary'])

    def test_invalid_dataset_row_withholds_result(self):
        value=sample(); value['dataset']['schema']['tables'][1]['name']='result'; value['dataset']['tables'][1]['name']='result'
        value['dataset']['tables'][1]['rows']=[[False,'a']]; value['result']['rows']=[[False,'Invented label']]
        result=run(value); self.assertIsNone(result['summary'])
        self.assertTrue({'dataset:result','result'}<=set(row['table'] for row in result['issues']))

    def test_no_query_execution_or_semantic_binding_claim(self):
        value=sample(); value['query']='An invented string that is not SQL.'
        value['contract']['query_sha256']=value['result']['query_sha256']=t.digest(value['query'].encode())
        result=run(value); self.assertEqual(result['status'],'PASS'); self.assertFalse(result['sql_executed']); self.assertFalse(result['placeholder_bindings_verified'])

    def test_bindings_are_bounded_scalars(self):
        for item in ([],{},'x'*257):
            value=sample(); value['bindings']['selected']=item
            with self.assertRaises(t.Rejected): run(value)

    def test_report_omits_query_bindings_and_results(self):
        value=sample(); raw=t.encode(run(value)).decode()
        self.assertNotIn(value['query'],raw); self.assertNotIn(value['result']['rows'][0][1],raw)
        self.assertFalse(run(value)['result_values_verified_against_query'])
