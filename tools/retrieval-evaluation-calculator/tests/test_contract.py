from retrieval import calculate as OP
WITHHELD='metrics'

import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
from test_knowledge_core import doc,ref

def sample(): return json.loads((Path(__file__).parent.parent/'examples/input.json').read_text(encoding='utf-8'))
def run(value): return OP(t.encode(value))

class Contracts(unittest.TestCase):
    def test_example_passes(self):
        self.assertEqual(run(sample())['status'],'PASS')

    def test_review_example_withholds(self):
        value=json.loads((Path(__file__).parent.parent/'examples/needs-review.json').read_text(encoding='utf-8'))
        result=run(value); self.assertEqual(result['status'],'REVIEW_REQUIRED')
        self.assertIsNone(result[WITHHELD])

    def test_wrong_format(self):
        value=sample(); value['format']='fictional-unsupported'
        with self.assertRaises(t.Rejected): run(value)

    def test_unknown_top_level_field(self):
        value=sample(); value['unexpected']='invented'
        with self.assertRaises(t.Rejected): run(value)

    def test_input_pin_and_no_mutation(self):
        value=sample(); before=copy.deepcopy(value); raw=t.encode(value)
        result=OP(raw)
        self.assertEqual(result['input_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(value,before)
        self.assertFalse(result['target_changes_performed'])

    def test_invalid_document_withholds_all(self):
        value=sample(); value['documents'].append(dict(doc('extra'),revision=True))
        result=run(value); self.assertEqual(result['status'],'REVIEW_REQUIRED'); self.assertIsNone(result[WITHHELD])

    def test_empty_documents_review(self):
        value=sample(); value['documents']=[]
        result=run(value); self.assertEqual(result['status'],'REVIEW_REQUIRED'); self.assertIsNone(result[WITHHELD])

    def test_conflicting_documents_withhold_all(self):
        value=sample(); value['documents'].append(dict(value['documents'][0],revision=2))
        result=run(value); self.assertEqual(result['status'],'REVIEW_REQUIRED'); self.assertIsNone(result[WITHHELD])
        self.assertEqual(result['counts']['documents']['conflict_rows'],2)

    def test_duplicate_documents_do_not_change_derived_result(self):
        value=sample(); before=run(value); value['documents']+=copy.deepcopy(value['documents'])
        result=run(value); self.assertEqual(result['status'],'PASS'); self.assertEqual(result[WITHHELD],before[WITHHELD])

    def test_report_round_trip_and_no_bodies(self):
        value=sample(); result=run(value); raw=t.encode(result)
        self.assertEqual(t.decode(raw),result)
        for d in value['documents']: self.assertNotIn(d['text'],raw.decode())

    def test_ambiguous_json_refused(self):
        for raw in (b'{"format":1,"format":2}',b'NaN',b'1.0',b'"\\ud800"'):
            with self.assertRaises(t.Rejected): OP(raw)

    def test_malformed_outer_shapes_refused(self):
        for value in (None,False,1,'invented',[],{}):
            with self.assertRaises(t.Rejected): run(value)

    def test_known_macro_metrics(self):
        result=run(sample()); self.assertEqual(result['metrics'],dict(macro_precision_at_k=dict(numerator='1',denominator='2'),
            macro_recall_at_k=dict(numerator='3',denominator='4'),mean_reciprocal_rank_at_k=dict(numerator='3',denominator='4')))
        self.assertEqual(result['per_query'][0]['reciprocal_rank_at_k'],dict(numerator='1',denominator='2'))

    def test_empty_ranking_is_zero_not_unknown(self):
        value=sample(); value['queries']=value['queries'][:1]; value['queries'][0]['ranked']=[]
        result=run(value); self.assertEqual(result['status'],'PASS')
        self.assertTrue(all(v==dict(numerator='0',denominator='1') for v in result['metrics'].values()))

    def test_no_queries_review(self):
        value=sample(); value['queries']=[]; self.assertIsNone(run(value)['metrics'])

    def test_unjudged_query_withholds_entire_cohort(self):
        value=sample(); value['queries'][1]['relevant']=[]
        result=run(value); self.assertIsNone(result['metrics']); self.assertIsNone(result['per_query'])

    def test_duplicate_ranks_and_judgments_refused(self):
        for field in ('ranked','relevant'):
            value=sample(); value['queries'][0][field]*=2
            self.assertEqual(run(value)['counts']['queries']['rejected_rows'],1)

    def test_wrong_revision_outside_top_k_still_review(self):
        value=sample(); value['k']=1; value['queries'][0]['ranked'][1]['revision']=2
        self.assertIsNone(run(value)['metrics'])

    def test_duplicate_query_does_not_weight_metrics(self):
        value=sample(); before=run(value); value['queries'].append(copy.deepcopy(value['queries'][0]))
        after=run(value); self.assertEqual(after['metrics'],before['metrics']); self.assertEqual(after['counts']['queries']['duplicate_rows'],1)

    def test_changed_ranking_same_query_conflicts(self):
        value=sample(); changed=copy.deepcopy(value['queries'][0]); changed['ranked'].reverse(); value['queries'].append(changed)
        self.assertEqual(run(value)['counts']['queries']['conflict_rows'],2)

    def test_k_limits(self):
        for k in (0,101,True,'2'):
            value=sample(); value['k']=k
            with self.assertRaises(t.Rejected): run(value)

    def test_precision_uses_k_even_when_short(self):
        value=sample(); value['queries']=value['queries'][1:]; value['k']=3
        result=run(value); self.assertEqual(result['metrics']['macro_precision_at_k'],dict(numerator='1',denominator='3'))

    def test_order_invariance_and_order_sensitivity(self):
        value=sample(); before=run(value); value['documents'].reverse(); value['queries'].reverse()
        self.assertEqual(run(value)['metrics'],before['metrics'])
        value['queries'][1]['ranked'].reverse()
        self.assertNotEqual(run(value)['metrics']['mean_reciprocal_rank_at_k'],before['metrics']['mean_reciprocal_rank_at_k'])
