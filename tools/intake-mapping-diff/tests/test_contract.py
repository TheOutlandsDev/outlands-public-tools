from mapping_diff import compare as OP
DERIVED='changes'

import copy
import json
from pathlib import Path
import unittest
import toolkit as t
from test_control_core import batch,receipt

def sample(): return json.loads((Path(__file__).parent.parent/'examples/input.json').read_text(encoding='utf-8'))
def run(value): return OP(t.encode(value))

class Contracts(unittest.TestCase):
    def test_example_passes(self): self.assertEqual(run(sample())['status'],'PASS')

    def test_review_example(self):
        value=json.loads((Path(__file__).parent.parent/'examples/needs-review.json').read_text(encoding='utf-8'))
        self.assertEqual(run(value)['status'],'REVIEW_REQUIRED')

    def test_unknown_top_level_field(self):
        value=sample(); value['unknown']='fictional'
        with self.assertRaises(t.Rejected): run(value)

    def test_wrong_format(self):
        value=sample(); value['format']='fictional-unsupported'
        with self.assertRaises(t.Rejected): run(value)

    def test_ambiguous_json_and_outer_shapes(self):
        for raw in (b'{"format":1,"format":2}',b'NaN',b'1.0',b'"\\ud800"',b'null',b'[]',b'{}'):
            with self.assertRaises(t.Rejected): OP(raw)

    def test_raw_input_pin_and_no_mutation(self):
        value=sample(); before=copy.deepcopy(value); raw=t.encode(value); result=OP(raw)
        self.assertEqual(value,before); self.assertEqual(result['input_sha256'],t.digest(raw)); self.assertFalse(result['target_changes_performed'])

    def test_json_round_trip(self):
        result=run(sample()); self.assertEqual(t.decode(t.encode(result)),result)

    def test_identical_map_no_changes(self):
        result=run(sample()); self.assertEqual(result['changes'],[])
        self.assertEqual(result['before_mapping_sha256'],result['after_mapping_sha256'])

    def test_known_field_change_codes(self):
        value=sample(); value['after']['fields'][1].update(source='Quantity',type='decimal',required=False)
        changes=run(value)['changes']; self.assertEqual([r['code'] for r in changes],['SOURCE_HEADER_CHANGED','TYPE_CHANGED','REQUIRED_CHANGED'])
        self.assertTrue(all(r['target']=='units' for r in changes))

    def test_no_rename_inference(self):
        value=sample(); value['after']['fields'][1]['target']='quantity'; result=run(value)
        self.assertEqual({r['code'] for r in result['changes']},{'FIELD_ADDED','FIELD_REMOVED','FIELD_ORDER_OR_MEMBERS_CHANGED'})
        self.assertFalse(result['rename_inferred'])

    def test_identity_order_changes_reported(self):
        value=sample(); value['before']['identity']=['record_id','units']; value['after']['identity']=['units','record_id']
        self.assertEqual(run(value)['changes'],[dict(target=None,code='IDENTITY_ORDER_OR_MEMBERS_CHANGED')])

    def test_field_order_and_unknown_policy(self):
        value=sample(); value['after']['fields'].reverse(); value['after']['unknown_columns']='ignore'
        self.assertEqual({r['code'] for r in run(value)['changes']},{'FIELD_ORDER_OR_MEMBERS_CHANGED','UNKNOWN_COLUMN_POLICY_CHANGED'})

    def test_invalid_map_refused(self):
        for mutate in ('identity','duplicate','required','type'):
            value=sample()
            if mutate=='identity': value['after']['identity']=['missing']
            elif mutate=='duplicate': value['after']['fields']*=2
            elif mutate=='required': value['after']['fields'][0]['required']=1
            else: value['after']['fields'][0]['type']='script'
            with self.assertRaises(t.Rejected): run(value)

    def test_canonical_mapping_pin_ignores_object_key_order(self):
        value=sample(); before=run(value); value['after']={key:value['after'][key] for key in reversed(value['after'])}
        self.assertEqual(run(value)['after_mapping_sha256'],before['after_mapping_sha256'])

    def test_private_source_headers_not_echoed(self):
        value=sample(); value['after']['fields'][1]['source']='SYNTHETIC_SENTINEL'
        self.assertNotIn('SYNTHETIC_SENTINEL',t.encode(run(value)).decode())

    def test_mapping_format_bounds(self):
        for change in ({'format':'unsupported'},{'fields':[]},{'identity':[]},{'unknown_columns':False}):
            value=sample(); value['after'].update(change)
            with self.assertRaises(t.Rejected): run(value)
