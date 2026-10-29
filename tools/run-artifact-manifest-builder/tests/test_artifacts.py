import copy
import json
from pathlib import Path
import unittest
import artifacts
import run_core as c
import toolkit as t

EXAMPLES=Path(__file__).absolute().parents[1]/'examples'


class Builder(unittest.TestCase):
    def setUp(self):
        self.selection=json.loads((EXAMPLES/'selection.json').read_text(encoding='utf-8'))
        self.inputs={row['id']:(EXAMPLES/(row['id']+('.txt' if row['id'] in ('source','code') else '.json'))).read_bytes()
                     for row in self.selection['artifacts']}

    def call(self): return artifacts.build(t.encode(self.selection),self.inputs)

    def test_all_exact_actual_byte_sizes_and_pins(self):
        result=self.call(); self.assertEqual(result['status'],'PASS')
        for row in result['manifest']['artifacts']:
            self.assertEqual(row['bytes'],len(self.inputs[row['id']]))
            self.assertEqual(row['sha256'],t.digest(self.inputs[row['id']]))

    def test_manifest_pin_is_exact_canonical_manifest_bytes(self):
        result=self.call(); self.assertEqual(result['manifest_sha256'],t.digest(t.encode(result['manifest'])))
        self.assertEqual(c.manifest(t.encode(result['manifest']))[0],result['manifest'])

    def test_order_independent_inputs_and_sorted_manifest(self):
        before=self.call(); self.inputs=dict(reversed(list(self.inputs.items())))
        self.assertEqual(before,self.call()); keys=[r['id'] for r in before['manifest']['artifacts']]
        self.assertEqual(keys,sorted(keys))

    def test_one_missing_or_extra_buffer_refused(self):
        saved=self.inputs.pop('source')
        with self.assertRaises(t.Rejected): self.call()
        self.inputs['source']=saved; self.inputs['extra']=b'sample'
        with self.assertRaises(t.Rejected): self.call()

    def test_no_file_body_or_source_metadata_in_report(self):
        report=t.encode(self.call())
        self.assertNotIn(b'sample-alpha',report); self.assertNotIn(b'fictional-example',report)
        self.assertFalse(self.call()['source_paths_recorded']); self.assertFalse(self.call()['content_privacy_verified'])

    def test_duplicate_ids_refused(self):
        self.selection['artifacts'].append(copy.deepcopy(self.selection['artifacts'][0]))
        with self.assertRaisesRegex(t.Rejected,'DUPLICATE_ARTIFACT'): self.call()

    def test_empty_artifact_bytes_are_observed_not_guessed(self):
        self.inputs['code']=b''; rows={r['id']:r for r in self.call()['manifest']['artifacts']}
        self.assertEqual(rows['code']['bytes'],0); self.assertEqual(rows['code']['sha256'],t.digest(b''))

    def test_identical_bytes_under_distinct_ids_are_allowed(self):
        self.inputs['code']=self.inputs['source']; result=self.call()
        self.assertEqual(len(result['manifest']['artifacts']),len(self.inputs))

    def test_code_artifacts_are_never_executed(self):
        self.inputs['code']=b'raise RuntimeError("FICTIONAL_MUST_NOT_EXECUTE")\n'
        self.assertEqual(self.call()['status'],'PASS')

    def test_wrong_format_unknown_fields_and_invalid_role(self):
        original=copy.deepcopy(self.selection)
        for update in (dict(format='other'),dict(private_path='invented')):
            self.selection=dict(original,**update)
            with self.assertRaises(t.Rejected): self.call()
        self.selection=original; self.selection['artifacts'][0]['role']='unknown'
        with self.assertRaises(t.Rejected): self.call()

    def test_input_size_limit(self):
        self.inputs['source']=b'x'*(t.MAX_INPUT+1)
        with self.assertRaises(t.Rejected): self.call()

    def test_immutable_inputs_and_no_target_changes(self):
        before=copy.deepcopy((self.selection,self.inputs)); self.assertFalse(self.call()['target_changes_performed'])
        self.assertEqual(before,(self.selection,self.inputs))
