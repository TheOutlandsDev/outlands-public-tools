from schema_diff import compare as OP

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

    def test_identical_schema_no_changes(self):
        result=run(sample()); self.assertEqual(result['changes'],[]); self.assertEqual(result['before_schema_sha256'],result['after_schema_sha256'])

    def test_known_nullable_change(self):
        value=sample(); value['after']['tables'][0]['columns'][1]['nullable']=True
        self.assertEqual(run(value)['changes'],[dict(table='items',column='label',constraint=None,code='COLUMN_NULLABILITY_CHANGED')])

    def test_column_added_removed_and_type(self):
        value=sample(); value['after']['tables'][0]['columns'][1]=col('quantity','integer')
        self.assertEqual({r['code'] for r in run(value)['changes']},{'COLUMN_ADDED','COLUMN_REMOVED','COLUMN_ORDER_OR_MEMBERS_CHANGED'})
        value=sample(); value['after']['tables'][0]['columns'][1]['type']='integer'
        self.assertEqual(run(value)['changes'][0]['code'],'COLUMN_TYPE_CHANGED')

    def test_no_rename_inference_or_ddl(self):
        value=sample(); value['after']['tables'][1]['name']='renamed'; result=run(value)
        self.assertEqual({r['code'] for r in result['changes']},{'TABLE_ADDED','TABLE_REMOVED','TABLE_ORDER_OR_MEMBERS_CHANGED'})
        self.assertFalse(result['rename_inferred']); self.assertFalse(result['ddl_generated']); self.assertFalse(result['compatibility_verified'])

    def test_primary_key_order_change(self):
        value=sample(); value['before']['tables'][1]['primary_key']=['entry_id','item_id']
        value['before']['tables'][1]['columns'][1]['nullable']=False
        value['after']=copy.deepcopy(value['before']); value['after']['tables'][1]['primary_key'].reverse()
        self.assertEqual([r['code'] for r in run(value)['changes']],['PRIMARY_KEY_CHANGED'])

    def test_foreign_key_policy_and_removal(self):
        value=sample(); value['after']['tables'][1]['foreign_keys'][0]['null_policy']='reject'
        self.assertEqual(run(value)['changes'][0]['code'],'FOREIGN_KEY_CHANGED')
        value['after']['tables'][1]['foreign_keys']=[]
        self.assertEqual({r['code'] for r in run(value)['changes']},{'FOREIGN_KEY_REMOVED','FOREIGN_KEY_ORDER_OR_MEMBERS_CHANGED'})

    def test_table_and_column_order_are_explicit(self):
        value=sample(); value['after']['tables'].reverse(); value['after']['tables'][1]['columns'].reverse()
        self.assertEqual({r['code'] for r in run(value)['changes']},{'TABLE_ORDER_OR_MEMBERS_CHANGED','COLUMN_ORDER_OR_MEMBERS_CHANGED'})

    def test_invalid_referenced_schema_refused(self):
        value=sample(); value['after']['tables'].pop(0)
        with self.assertRaises(t.Rejected): run(value)

    def test_object_key_order_does_not_change_schema_pin(self):
        value=sample(); value['after']={key:value['after'][key] for key in reversed(value['after'])}
        result=run(value); self.assertEqual(result['before_schema_sha256'],result['after_schema_sha256'])
