from keys import check as OP

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

    def test_known_foreign_coverage_and_null_skip(self):
        result=run(sample()); entries=next(row for row in result['summary'] if row['table']=='entries')
        self.assertEqual(entries['foreign_keys'],[dict(name='item_ref',resolved_rows=2,skipped_null_rows=1)])

    def test_all_primary_key_duplicates_flagged(self):
        value=sample(); value['dataset']['tables'][0]['rows'] += [['a','Invented amber'],['a','Other invented label']]
        result=run(value); self.assertIsNone(result['summary'])
        self.assertEqual(len([i for i in result['issues'] if i['code']=='DUPLICATE_PRIMARY_KEY']),3)
        self.assertEqual(result['counts']['items']['accepted_rows'],4); self.assertFalse(result['duplicate_rows_discarded'])

    def test_missing_reference_and_rejected_row_withhold_all(self):
        for row in ([4,'missing'],[False,'a']):
            value=sample(); value['dataset']['tables'][1]['rows'].append(row); self.assertIsNone(run(value)['summary'])

    def test_reject_null_foreign_key(self):
        value=sample(); value['dataset']['schema']['tables'][1]['foreign_keys'][0]['null_policy']='reject'
        self.assertIn('FOREIGN_KEY_NULL',[i['code'] for i in run(value)['issues']])

    def test_composite_partial_null_skip_and_exact_decimal(self):
        parent=table('parents',[col('a','decimal'),col('b','integer')],['a','b'])
        child=table('children',[col('a','decimal',True),col('b','integer',True)],[],[fk(columns=['a','b'],target='parents',references=['a','b'])])
        value=dict(format='outlands-key-reference-check-v1',dataset=dict(schema=dict(tables=[parent,child]),tables=[
            dict(name='parents',rows=[['1.00',2]]),dict(name='children',rows=[['1',2],[None,2]])]))
        result=run(value); self.assertEqual(result['status'],'PASS')
        row=next(s for s in result['summary'] if s['table']=='children')
        self.assertEqual(row['foreign_keys'][0]['skipped_null_rows'],1)

    def test_empty_tables_are_vacuous_scope_only(self):
        value=sample()
        for row in value['dataset']['tables']: row['rows']=[]
        result=run(value); self.assertEqual(result['status'],'PASS'); self.assertFalse(result['database_contents_verified'])

    def test_no_key_constraints_requires_review(self):
        value=dict(format='outlands-key-reference-check-v1',dataset=dict(schema=dict(tables=[table(pk=[])]),tables=[dict(name='items',rows=[['a']])]))
        self.assertIn('NO_KEY_CONSTRAINTS',[i['code'] for i in run(value)['issues']])

    def test_self_reference(self):
        spec=table(cols=[col(),col('parent',nullable=True)],fks=[fk(columns=['parent'])])
        value=dict(format='outlands-key-reference-check-v1',dataset=dict(schema=dict(tables=[spec]),tables=[dict(name='items',rows=[['root',None],['child','root']])]))
        self.assertEqual(run(value)['status'],'PASS')

    def test_report_omits_values(self):
        value=sample(); value['dataset']['tables'][1]['rows'][0][1]='SYNTHETIC_SENTINEL'
        self.assertNotIn('SYNTHETIC_SENTINEL',t.encode(run(value)).decode())

    def test_input_order_does_not_change_valid_summary(self):
        value=sample(); before=run(value); value['dataset']['tables'].reverse()
        self.assertEqual(run(value)['summary'],before['summary'])
