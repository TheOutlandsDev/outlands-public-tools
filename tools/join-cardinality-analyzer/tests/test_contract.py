from joins import analyze as OP

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

    def test_known_many_to_many_counts(self):
        s=run(sample())['summary']; self.assertEqual((s['inner_rows'],s['left_outer_rows'],s['right_outer_rows'],s['full_outer_rows']),(6,8,8,10))
        self.assertEqual((s['unmatched_left_rows'],s['unmatched_right_rows']),(2,2))
        self.assertEqual(s['key_group_shapes']['many_to_many'],1)

    def test_explicit_null_matching_changes_counts(self):
        value=sample(); value['join']['null_policy']='match'; s=run(value)['summary']
        self.assertEqual((s['inner_rows'],s['full_outer_rows']),(7,9)); self.assertEqual(s['key_group_shapes']['one_to_one'],1)

    def test_independent_materialized_oracle_on_fictional_rows(self):
        value=sample(); left=value['dataset']['tables'][0]['rows']; right=value['dataset']['tables'][1]['rows']
        pairs=[(a,b) for a in left for b in right if a[0] is not None and b[0] is not None and a[0]==b[0]]
        self.assertEqual(run(value)['summary']['inner_rows'],len(pairs))

    def test_empty_and_unmatched_inputs(self):
        value=sample(); value['dataset']['tables'][1]['rows']=[]; s=run(value)['summary']
        self.assertEqual((s['inner_rows'],s['left_outer_rows'],s['full_outer_rows']),(0,4,4))

    def test_invalid_row_withholds_all(self):
        value=sample(); value['dataset']['tables'][0]['rows'].append([True]); self.assertIsNone(run(value)['summary'])

    def test_invalid_join_contract(self):
        for changes in ({'left_table':'missing'},{'left_columns':['missing']},{'right_columns':[]},{'null_policy':'guess'}):
            value=sample(); value['join'].update(changes)
            with self.assertRaises(t.Rejected): run(value)

    def test_type_mismatch_refused(self):
        value=sample(); value['dataset']['schema']['tables'][1]['columns'][0]['type']='integer'; value['dataset']['tables'][1]['rows']=[[1]]
        with self.assertRaisesRegex(t.Rejected,'JOIN_TYPE_MISMATCH'): run(value)

    def test_physical_duplicates_preserved(self):
        value=sample(); value['dataset']['tables'][0]['rows']=[['a']]*2; value['dataset']['tables'][1]['rows']=[['a']]*3
        self.assertEqual(run(value)['summary']['inner_rows'],6)

    def test_self_join(self):
        value=sample(); value['join']['right_table']='left_rows'; self.assertEqual(run(value)['summary']['inner_rows'],5)

    def test_order_invariance_and_fanout(self):
        value=sample(); before=run(value)['summary']
        for table in value['dataset']['tables']: table['rows'].reverse()
        self.assertEqual(run(value)['summary'],before)
        self.assertEqual((before['max_matches_per_left_row'],before['max_matches_per_right_row']),(3,2))

    def test_composite_key_avoids_concatenation_collision(self):
        spec=dict(tables=[table(name,[col('a'),col('b')],[]) for name in ('left_rows','right_rows')])
        value=sample(); value['dataset']=dict(schema=spec,tables=[dict(name='left_rows',rows=[['ab','c']]),dict(name='right_rows',rows=[['a','bc']])])
        value['join'].update(left_columns=['a','b'],right_columns=['a','b'])
        self.assertEqual(run(value)['summary']['inner_rows'],0)

    def test_report_omits_key_values_and_no_integrity_claim(self):
        value=sample(); value['dataset']['tables'][0]['rows'][0][0]='SYNTHETIC_SENTINEL'; result=run(value)
        self.assertNotIn('SYNTHETIC_SENTINEL',t.encode(result).decode()); self.assertFalse(result['key_constraints_evaluated']); self.assertFalse(result['join_materialized'])
