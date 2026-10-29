from evidence import check as OP
WITHHELD='evidence'

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

    def test_exact_quote_pin_and_answer_pin(self):
        value=sample(); result=run(value); row=result['evidence'][0]
        self.assertEqual(row['answer_sha256'],t.digest(value['answers'][0]['text'].encode()))
        self.assertEqual(row['checked_citations'][0]['quote_sha256'],t.digest(b'Fictional gardens'))
        self.assertFalse(result['claim_support_verified']); self.assertFalse(result['factual_truth_verified'])

    def test_quote_not_present_in_answer_still_only_structural(self):
        value=sample(); value['answers'][0]['text']='An unrelated invented statement.'
        result=run(value); self.assertEqual(result['status'],'PASS'); self.assertFalse(result['claim_support_verified'])

    def test_missing_citations_withholds(self):
        value=sample(); value['answers'][0]['citations']=[]
        self.assertIsNone(run(value)['evidence'])

    def test_empty_answers_review(self):
        value=sample(); value['answers']=[]; self.assertIsNone(run(value)['evidence'])

    def test_bounds_and_empty_span(self):
        for changes in ({'start':-1},{'start':True},{'start':2,'end':2},{'end':4097},{'end':200}):
            value=sample(); value['answers'][0]['citations'][0].update(changes)
            self.assertIsNone(run(value)['evidence'])

    def test_unicode_codepoint_offsets(self):
        d=doc(body='A\U0001f331e\u0301B'); value=sample(); value['documents']=[d]
        value['answers'][0]['citations']=[dict(source=ref(d),start=1,end=4,quote='\U0001f331e\u0301')]
        self.assertEqual(run(value)['status'],'PASS')
        value['answers'][0]['citations'][0]['quote']='\U0001f331\u00e9'; self.assertIsNone(run(value)['evidence'])

    def test_wrong_reference_and_pin(self):
        for changes in ({'id':'missing'},{'revision':2},{'sha256':'0'*64}):
            value=sample(); value['answers'][0]['citations'][0]['source'].update(changes)
            self.assertIsNone(run(value)['evidence'])

    def test_duplicate_citation_refused(self):
        value=sample(); value['answers'][0]['citations']*=2
        self.assertEqual(run(value)['counts']['answers']['rejected_rows'],1)

    def test_one_bad_answer_withholds_good_answer(self):
        value=sample(); bad=copy.deepcopy(value['answers'][0]); bad['id']='answer-b'; bad['citations'][0]['quote']='Wrong invented quote'
        value['answers'].append(bad); self.assertIsNone(run(value)['evidence'])

    def test_answer_duplicates_and_conflicts(self):
        value=sample(); value['answers']*=2; self.assertEqual(run(value)['counts']['answers']['duplicate_rows'],1)
        value['answers'].append(dict(value['answers'][0],text='Changed invented answer.'))
        result=run(value); self.assertEqual(result['counts']['answers']['conflict_rows'],3); self.assertIsNone(result['evidence'])

    def test_reports_omit_answers_and_quotes(self):
        value=sample(); raw=t.encode(run(value)).decode()
        self.assertNotIn(value['answers'][0]['text'],raw); self.assertNotIn(value['answers'][0]['citations'][0]['quote'],raw)
