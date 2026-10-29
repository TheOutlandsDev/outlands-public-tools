import copy
from pathlib import Path
import unittest
import publication
import toolkit as t

EXAMPLES=Path(__file__).absolute().parents[1]/'examples'


class Publication(unittest.TestCase):
    def setUp(self):
        self.plan=t.decode((EXAMPLES/'plan.json').read_bytes())
        self.manifest=(EXAMPLES/'manifest.json').read_bytes(); self.review=(EXAMPLES/'review.json').read_bytes()
        self.inputs={r['id']:(EXAMPLES/(r['id']+'.json')).read_bytes() for r in self.plan['items']}

    def call(self): return publication.check(t.encode(self.plan),self.manifest,self.review,self.inputs)
    def codes(self): return {r['code'] for r in self.call()['issues']}
    def update_review(self,change):
        value=t.decode(self.review); change(value); self.review=t.encode(value); self.plan['review_sha256']=t.digest(self.review)

    def test_complete_review_is_consistency_only(self):
        result=self.call(); self.assertEqual(result['status'],'PASS')
        for field in ('publication_authorized','privacy_independently_verified','rights_independently_verified','target_changes_performed'):
            self.assertFalse(result[field])
        self.assertEqual(result['interpretation'],'DECLARED_PLAN_CONSISTENCY_ONLY')

    def test_unselected_artifact_bytes_are_not_required(self):
        self.assertEqual(set(self.inputs),{'reconciliation','result'})
        self.assertEqual(self.call()['status'],'PASS')

    def test_extra_unselected_input_refused(self):
        self.inputs['source']=b'invented'
        with self.assertRaisesRegex(t.Rejected,'BINDING_COVERAGE_INVALID'): self.call()

    def test_selected_byte_tampering_detected(self):
        self.inputs['result']+=b'changed'; self.assertIn('ARTIFACT_HASH_MISMATCH',self.codes())
        self.assertIn('ARTIFACT_SIZE_MISMATCH',self.codes())

    def test_stale_manifest_pin_in_plan_or_review(self):
        self.plan['manifest_sha256']='0'*64; self.assertIn('MANIFEST_PIN_MISMATCH',self.codes())
        self.plan['manifest_sha256']=t.digest(self.manifest)
        self.update_review(lambda value:value.update(manifest_sha256='0'*64))
        self.assertIn('MANIFEST_PIN_MISMATCH',self.codes())

    def test_stale_review_pin(self):
        self.plan['review_sha256']='0'*64; self.assertIn('REVIEW_PIN_MISMATCH',self.codes())

    def test_run_identity_binding(self):
        self.plan['run_id']='other-run'; self.assertIn('RUN_ID_MISMATCH',self.codes())

    def test_hold_cannot_be_cleared_by_true_assertions(self):
        self.update_review(lambda value:value['items'][0].update(decision='hold'))
        self.assertIn('REVIEW_HELD',self.codes()); self.assertEqual(self.call()['status'],'REVIEW_REQUIRED')

    def test_each_assertion_required(self):
        for key in ('rights_reviewed','privacy_reviewed','context_reviewed'):
            original=self.review
            self.update_review(lambda value:value['items'][0].update({key:False}))
            self.assertIn('REVIEW_ASSERTIONS_INCOMPLETE',self.codes()); self.review=original
            self.plan['review_sha256']=t.digest(original)

    def test_assertions_do_not_coerce_booleans(self):
        self.update_review(lambda value:value['items'][0].update(privacy_reviewed=1))
        with self.assertRaises(t.Rejected): self.call()

    def test_renamed_output_requires_new_matching_review(self):
        self.plan['items'][0]['public_name']='renamed.json'; self.assertIn('REVIEW_ITEM_MISMATCH',self.codes())

    def test_plan_content_pin_must_agree_with_manifest_and_review(self):
        self.plan['items'][0]['sha256']='0'*64
        self.assertIn('PLAN_ARTIFACT_PIN_MISMATCH',self.codes()); self.assertIn('REVIEW_ITEM_MISMATCH',self.codes())

    def test_missing_and_extra_review_entries(self):
        self.update_review(lambda value:value['items'].pop())
        self.assertIn('REVIEW_SELECTION_COVERAGE_MISMATCH',self.codes())

    def test_unknown_artifact_is_reported_without_opening_other_inputs(self):
        self.plan['items'][0]['id']='missing'; self.inputs['missing']=self.inputs.pop('reconciliation')
        self.update_review(lambda value:value['items'][0].update(id='missing'))
        self.assertIn('UNKNOWN_ARTIFACT_REFERENCE',self.codes())

    def test_name_traversal_devices_and_streams_refused(self):
        for name in ('../a.json','a/b.json','CON','a:stream','a.txt.'):
            self.plan['items'][0]['public_name']=name
            with self.assertRaises(t.Rejected): self.call()

    def test_case_insensitive_public_name_collision(self):
        self.plan['items'][0]['public_name']='Sample.json'; self.plan['items'][1]['public_name']='sample.JSON'
        with self.assertRaisesRegex(t.Rejected,'PUBLIC_NAME_COLLISION'): self.call()

    def test_duplicate_selection_ids_refused(self):
        self.plan['items'].append(copy.deepcopy(self.plan['items'][0]))
        with self.assertRaises(t.Rejected): self.call()

    def test_no_body_values_or_private_original_names_in_summary(self):
        result=self.call(); encoded=t.encode(result)
        self.assertNotIn(b'sample-alpha',encoded); self.assertNotIn(b'fictional-example',encoded)
        self.assertEqual({r['public_name'] for r in result['selected']},{'sample-result.json','sample-reconciliation.json'})

    def test_unknown_metadata_and_empty_selection_refused(self):
        self.plan['destination']='invented'
        with self.assertRaises(t.Rejected): self.call()
        del self.plan['destination']; self.plan['items']=[]
        with self.assertRaises(t.Rejected): self.call()

    def test_immutable_inputs_and_deterministic_output(self):
        before=copy.deepcopy((self.plan,self.inputs)); self.assertEqual(self.call(),self.call())
        self.assertEqual(before,(self.plan,self.inputs))
