import copy
import json
from pathlib import Path
import unittest
import delivery
import toolkit as t


class Evidence(unittest.TestCase):
    def setUp(self):
        self.value=json.loads((Path(__file__).absolute().parents[1]/'examples/evidence.json').read_text(encoding='utf-8'))
        self.item=self.value['messages'][0]

    def call(self): return delivery.reconcile(t.encode(self.value))
    def row(self): return self.call()['messages'][0]
    def refused(self,code=None):
        with self.assertRaises(t.Rejected) as caught: self.call()
        if code: self.assertEqual(str(caught.exception),code)

    def test_matching_report_is_only_caller_assertion(self):
        result=self.call(); self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['messages'][0]['state'],'DELIVERY_REPORTED')
        self.assertFalse(result['real_delivery_verified']); self.assertFalse(result['target_changes_performed'])
        self.assertFalse(result['messages'][0]['retry_permitted'])

    def test_acceptance_alone_is_not_delivery(self):
        self.item['reports']=[]; self.assertEqual(self.row()['state'],'ACCEPTED_PENDING_EVIDENCE')

    def test_uncertain_never_eligible(self):
        self.item.update(attempts=[dict(number=1,tick=0,outcome='uncertain',receipt=None)],reports=[])
        self.assertEqual(self.row()['state'],'REVIEW_REQUIRED'); self.assertFalse(self.row()['retry_permitted'])

    def test_acceptance_after_uncertainty_cannot_clear_review(self):
        self.item['attempts'][0]['outcome']='uncertain'
        row=self.row(); self.assertEqual(row['state'],'REVIEW_REQUIRED')
        self.assertIn('REPLAY_AFTER_TERMINAL_OR_UNCERTAIN',row['issues'])

    def test_replay_after_acceptance_or_permanent_failure(self):
        for outcome,receipt in (('accepted','first_receipt'),('permanent_not_accepted',None)):
            self.item['attempts'][0].update(outcome=outcome,receipt=receipt)
            self.assertIn('REPLAY_AFTER_TERMINAL_OR_UNCERTAIN',self.row()['issues'])

    def test_definite_non_acceptance_records_no_executable_permission(self):
        self.item['attempts']=self.item['attempts'][:1]; self.item['reports']=[]
        row=self.row(); self.assertEqual(row['state'],'DEFINITE_NON_ACCEPTANCE_RECORDED')
        self.assertFalse(row['retry_permitted'])

    def test_no_attempts_pending(self):
        self.item.update(attempts=[],reports=[]); self.assertEqual(self.row()['state'],'PENDING')

    def test_final_retry_exhausted(self):
        self.value['max_attempts']=1; self.item['attempts']=self.item['attempts'][:1]; self.item['reports']=[]
        self.assertEqual(self.row()['state'],'FAILED')

    def test_replay_exceeding_declared_maximum(self):
        self.value['max_attempts']=1
        self.assertIn('ATTEMPT_LIMIT_EXCEEDED',self.row()['issues'])

    def test_backoff_too_early(self):
        self.item['attempts'][1]['tick']=0
        self.assertIn('RETRY_BEFORE_DECLARED_BACKOFF',self.row()['issues'])

    def test_second_retry_delay_is_two_ticks(self):
        self.item['reports']=[]
        self.item['attempts'][1].update(outcome='retryable_not_accepted',receipt=None)
        self.item['attempts'].append(dict(number=3,tick=2,outcome='accepted',receipt='last_receipt'))
        self.assertIn('RETRY_BEFORE_DECLARED_BACKOFF',self.row()['issues'])
        self.item['attempts'][2]['tick']=3; self.assertEqual(self.row()['issues'],[])

    def test_tick_overflow_requires_review(self):
        self.item['attempts']=self.item['attempts'][:1]; self.item['reports']=[]
        self.item['attempts'][0]['tick']=10**12
        self.assertIn('RETRY_TICK_OVERFLOW',self.row()['issues'])

    def test_mismatched_receipt_or_attempt_requires_review(self):
        for key,value in (('receipt','wrong_receipt'),('attempt',1)):
            original=copy.deepcopy(self.item['reports'])
            self.item['reports'][0][key]=value
            self.assertIn('REPORT_NOT_MATCHED_TO_ACCEPTANCE',self.row()['issues'])
            self.item['reports']=original

    def test_orphan_report_requires_review(self):
        self.item['attempts']=[]; self.assertEqual(self.row()['state'],'REVIEW_REQUIRED')

    def test_conflicting_reports_never_promoted(self):
        self.item['reports'].append(dict(self.item['reports'][0],outcome='bounced'))
        self.assertIn('CONFLICTING_REPORTS',self.row()['issues'])
        self.assertEqual(self.row()['state'],'REVIEW_REQUIRED')

    def test_identical_reports_counted_once_without_conflict(self):
        self.item['reports']*=2; row=self.row()
        self.assertEqual(row['duplicate_reports'],1); self.assertEqual(row['state'],'DELIVERY_REPORTED')

    def test_bounce_is_not_delivery(self):
        self.item['reports'][0]['outcome']='bounced'; self.assertEqual(self.row()['state'],'BOUNCE_REPORTED')

    def test_unknown_outcomes_and_unexpected_receipts(self):
        self.item['attempts'][0]['outcome']='timeout'; self.refused('OUTCOME_INVALID')
        self.item['attempts'][0].update(outcome='retryable_not_accepted',receipt='unexpected'); self.refused('UNEXPECTED_RECEIPT')

    def test_nonsequential_number_and_backwards_ticks_refused(self):
        self.item['attempts'][1]['number']=3; self.refused('ATTEMPT_SEQUENCE_INVALID')
        self.item['attempts'][1]['number']=2; self.item['attempts'][0]['tick']=2; self.refused('TICK_ORDER_INVALID')

    def test_boolean_ticks_and_limits_refused(self):
        self.value['max_attempts']=True; self.refused('INTEGER_INVALID')
        self.value['max_attempts']=3; self.item['attempts'][0]['tick']=True; self.refused('INTEGER_INVALID')

    def test_duplicate_message_and_invalid_content_pin(self):
        self.value['messages'].append(copy.deepcopy(self.item)); self.refused('DUPLICATE_MESSAGE')
        self.value['messages'].pop(); self.item['content_sha256']='x'*64; self.refused('HASH_INVALID')

    def test_message_attempt_report_limits(self):
        original=copy.deepcopy(self.value)
        self.value['messages']=[]; self.refused('MESSAGE_LIMIT')
        self.value=copy.deepcopy(original); self.value['messages']*=65; self.refused('MESSAGE_LIMIT')
        self.value=copy.deepcopy(original); self.value['messages'][0]['attempts']*=3; self.refused('EVIDENCE_LIMIT')
        self.value=copy.deepcopy(original); self.value['messages'][0]['reports']*=9; self.refused('EVIDENCE_LIMIT')

    def test_receipts_omitted_from_report(self):
        self.assertNotIn('fake_receipt',json.dumps(self.call()))

    def test_unknown_metadata_refused(self):
        self.item['source_path']='invented'; self.refused('FIELDS_INVALID')

    def test_deterministic_immutable_and_exact_pin(self):
        original=copy.deepcopy(self.value); result=self.call()
        self.assertEqual(result,self.call()); self.assertEqual(original,self.value)
        self.assertEqual(result['input_sha256'],t.digest(t.encode(self.value)))
