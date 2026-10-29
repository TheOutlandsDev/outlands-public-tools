from replay import plan as OP
DERIVED='plan'

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

    def test_duplicate_rows_count_once(self):
        value=sample(); before=run(value); value['expected']*=2; value['receipts']*=2
        after=run(value); self.assertEqual(after[DERIVED],before[DERIVED]); self.assertEqual(after['status'],'PASS')
        self.assertEqual(after['counts']['expected']['duplicate_rows'],len(sample()['expected']))

    def test_conflicting_batch_group_withholds_all(self):
        value=sample(); value['expected'].append(dict(value['expected'][0],sequence=99))
        result=run(value); self.assertIsNone(result[DERIVED]); self.assertEqual(result['counts']['expected']['conflict_rows'],2)

    def test_malformed_row_withholds_all(self):
        value=sample(); value['expected'].append(None); result=run(value)
        self.assertIsNone(result[DERIVED]); self.assertEqual(result['counts']['expected']['rejected_rows'],1)

    def test_conflicting_receipt_snapshots_withhold(self):
        value=sample(); value['receipts'].append(dict(value['receipts'][0],status='uncertain'))
        result=run(value); self.assertIsNone(result[DERIVED]); self.assertEqual(result['counts']['receipts']['conflict_rows'],2)

    def test_scope_mismatch_withholds(self):
        value=sample(); value['receipts'][0]['stream']='other-stream'; self.assertIsNone(run(value)[DERIVED])

    def test_metadata_mismatch_withholds(self):
        for field,changed in [('sequence',99),('source_sha256','0'*64),('mapping_sha256','0'*64),('preview_sha256','0'*64)]:
            value=sample(); value['receipts'][0]['batch'][field]=changed; self.assertIsNone(run(value)[DERIVED])

    def test_uncertain_and_failed_outcomes_block(self):
        for status in ('uncertain','failed'):
            value=sample(); value['receipts'][0]['status']=status; self.assertIsNone(run(value)[DERIVED])

    def test_rejected_or_conflicting_source_counts_block(self):
        for field in ('rejected_rows','conflict_rows'):
            value=sample(); value['expected'][0]['counts'].update(duplicate_rows=0,**{field:1})
            value['receipts'][0]['batch']=copy.deepcopy(value['expected'][0]); self.assertIsNone(run(value)[DERIVED])

    def test_row_counts_and_commit_authority_remain_unverified(self):
        result=run(sample()); self.assertFalse(result['row_counts_recomputed']); self.assertFalse(result['receipt_authority_verified'])
        self.assertFalse(result['exactly_once_verified'])

    def test_order_invariance(self):
        value=sample(); before=run(value); value['expected'].reverse(); value['receipts'].reverse()
        self.assertEqual(run(value)[DERIVED],before[DERIVED])

    def test_sequence_and_content_aliases_withhold(self):
        for field in ('sequence','content'):
            value=sample(); value['receipts']=[]
            if field=='sequence': value['expected'][1]['sequence']=value['expected'][0]['sequence']
            else:
                for key in ('source_sha256','mapping_sha256','preview_sha256'): value['expected'][1][key]=value['expected'][0][key]
            result=run(value); self.assertEqual(result['status'],'REVIEW_REQUIRED'); self.assertIsNone(result[DERIVED])

    def test_known_skip_and_new_decisions(self):
        result=run(sample()); self.assertEqual([r['decision'] for r in result['plan']],['SKIP_ALREADY_COMMITTED','MANUAL_REVIEW_NEW_BATCH'])
        self.assertTrue(result['plan_only']); self.assertFalse(result['retry_performed'])
        self.assertTrue(all(not row['execution_authorized'] for row in result['plan']))

    def test_no_receipts_all_require_manual_review(self):
        value=sample(); value['receipts']=[]
        self.assertTrue(all(r['decision']=='MANUAL_REVIEW_NEW_BATCH' for r in run(value)['plan']))

    def test_empty_candidate_cohort_review(self):
        value=sample(); value['expected']=[]; self.assertIsNone(run(value)['plan'])

    def test_unselected_committed_history_allowed(self):
        value=sample(); value['receipts'].append(receipt(batch('history',10)))
        self.assertEqual(run(value)['status'],'PASS')

    def test_unselected_uncertainty_blocks_all(self):
        value=sample(); value['receipts'].append(receipt(batch('history',10),'uncertain'))
        self.assertIsNone(run(value)['plan'])

    def test_reused_content_under_new_id_blocked(self):
        value=sample(); candidate=dict(value['expected'][0],id='renamed',sequence=3); value['expected']=[candidate]
        self.assertIn('CONTENT_ID_ALIAS',[i['code'] for i in run(value)['issues']])

    def test_changed_mapping_new_batch_is_manual_only(self):
        value=sample(); candidate=dict(value['expected'][0],id='changed',sequence=3,mapping_sha256='0'*64)
        value['expected']=[candidate]; result=run(value)
        self.assertEqual(result['status'],'PASS'); self.assertEqual(result['plan'][0]['decision'],'MANUAL_REVIEW_NEW_BATCH')
