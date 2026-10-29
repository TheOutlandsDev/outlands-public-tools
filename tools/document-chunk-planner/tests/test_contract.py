from chunks import plan as OP
WITHHELD='chunks'

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

    def test_known_windows_and_hashes(self):
        result=run(sample()); chunks=result['chunks']
        self.assertEqual([(r['start'],r['end']) for r in chunks],[(0,5),(3,8),(6,11)])
        for row,body in zip(chunks,['ABCDE','DEFGH','GHIJK']):
            self.assertEqual(row['sha256'],t.digest(body.encode()))
        self.assertEqual(result['chunk_count'],3)

    def test_exact_boundary_and_short_document(self):
        for body in ('A','ABCDE','ABCDEF'):
            value=sample(); value['documents']=[doc(body=body)]; result=run(value)
            self.assertEqual(result['chunk_count'],1 if len(body)<=5 else 2)

    def test_zero_overlap_complete_coverage(self):
        value=sample(); value['policy']['overlap_chars']=0; chunks=run(value)['chunks']
        self.assertEqual([(r['start'],r['end']) for r in chunks],[(0,5),(5,10),(10,11)])

    def test_unicode_codepoints_not_utf8_offsets(self):
        value=sample(); value['documents']=[doc(body='A\U0001f331e\u0301B')]; value['policy']=dict(max_chars=2,overlap_chars=0)
        chunks=run(value)['chunks']
        self.assertEqual([(r['start'],r['end'],r['utf8_bytes']) for r in chunks],[(0,2,5),(2,4,3),(4,5,1)])

    def test_invalid_policy(self):
        for policy in (dict(max_chars=0,overlap_chars=0),dict(max_chars=4,overlap_chars=4),
                       dict(max_chars=True,overlap_chars=0),dict(max_chars=5,overlap_chars=-1),
                       dict(max_chars=4097,overlap_chars=0),{}):
            value=sample(); value['policy']=policy
            with self.assertRaises(t.Rejected): run(value)

    def test_global_chunk_budget_no_partial_plan(self):
        value=sample(); value['documents']=[doc('a','x'*4096),doc('b','y'*4096)]
        value['policy']=dict(max_chars=1,overlap_chars=0)
        result=run(value); self.assertIsNone(result['chunks']); self.assertIn('CHUNK_LIMIT',[i['code'] for i in result['issues']])

    def test_exact_chunk_budget(self):
        value=sample(); value['documents']=[doc(body='x'*4096)]; value['policy']=dict(max_chars=1,overlap_chars=0)
        result=run(value); self.assertEqual(result['chunk_count'],4096); self.assertEqual(result['status'],'PASS')

    def test_overlap_progress(self):
        value=sample(); value['documents']=[doc(body='x'*4096)]; value['policy']=dict(max_chars=4096,overlap_chars=4095)
        self.assertEqual(run(value)['chunk_count'],1)
        value['policy']['max_chars']=4095; value['policy']['overlap_chars']=4094
        self.assertEqual(run(value)['chunk_count'],2)

    def test_policy_pin_and_document_order(self):
        value=sample(); value['documents'].append(doc('another')); before=run(value); value['documents'].reverse()
        after=run(value); self.assertEqual(before['chunks'],after['chunks'])
        self.assertEqual(after['policy_sha256'],t.digest(t.encode(value['policy'])))
