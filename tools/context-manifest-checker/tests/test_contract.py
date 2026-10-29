from context_manifest import check as OP
WITHHELD='manifest'

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

    def test_dependency_order_known_result(self):
        result=run(sample())
        self.assertEqual(result['dependency_order'],['garden','meadow','orchard'])
        self.assertEqual(result['manifest_sha256'],t.digest(t.encode(result['manifest'])))

    def test_order_invariance(self):
        value=sample(); before=run(value); value['documents'].reverse(); value['relationships'].reverse()
        after=run(value)
        self.assertEqual(after['manifest'],before['manifest']); self.assertEqual(after['manifest_sha256'],before['manifest_sha256'])

    def test_cycle_withholds_plan(self):
        value=sample(); value['relationships'].append(dict(dependent=ref(value['documents'][0]),prerequisite=ref(value['documents'][1])))
        result=run(value); self.assertIsNone(result['dependency_order']); self.assertIsNone(result['manifest_sha256'])
        self.assertIn('DEPENDENCY_CYCLE',[i['code'] for i in result['issues']])

    def test_self_dependency_rejected_row(self):
        value=sample(); value['relationships']=[dict(dependent=ref(value['documents'][0]),prerequisite=ref(value['documents'][0]))]
        self.assertEqual(run(value)['counts']['relationships']['rejected_rows'],1)

    def test_duplicate_edges_count_once(self):
        value=sample(); value['relationships']*=3; result=run(value)
        self.assertEqual(result['status'],'PASS'); self.assertEqual(result['counts']['relationships']['duplicate_rows'],2)

    def test_conflicting_edge_pins(self):
        value=sample(); other=copy.deepcopy(value['relationships'][0]); other['prerequisite']['revision']=2
        value['relationships'] += [copy.deepcopy(value['relationships'][0]),other]
        result=run(value); self.assertEqual(result['counts']['relationships']['conflict_rows'],3); self.assertIsNone(result['manifest'])

    def test_missing_reference(self):
        value=sample(); value['relationships'][0]['prerequisite']['id']='missing'
        self.assertIn('REFERENCE_MISSING',[i['code'] for i in run(value)['issues']])

    def test_maximum_depth_nonrecursive(self):
        docs=[doc('d'+str(i)) for i in range(100)]
        value=dict(format='outlands-context-manifest-v1',documents=docs,
                   relationships=[dict(dependent=ref(docs[i]),prerequisite=ref(docs[i-1])) for i in range(1,100)])
        result=run(value); self.assertEqual(result['status'],'PASS'); self.assertEqual(len(result['dependency_order']),100)

    def test_no_relationships_allowed(self):
        value=sample(); value['relationships']=[]; self.assertEqual(run(value)['status'],'PASS')
