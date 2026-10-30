from labels import check as OP

import copy
import json
from pathlib import Path
import unittest
import toolkit as t
import decision_core as c

def sample():return json.loads((Path(__file__).parent.parent/'examples/input.json').read_text(encoding='utf-8'))
def run(value):return OP(t.encode(value))

class Contracts(unittest.TestCase):
    def test_fictional_example_passes(self):self.assertEqual(run(sample())['status'],'PASS')

    def test_review_example(self):
        value=json.loads((Path(__file__).parent.parent/'examples/needs-review.json').read_text(encoding='utf-8'))
        self.assertEqual(run(value)['status'],'REVIEW_REQUIRED')

    def test_wrong_format_and_unknown_fields(self):
        for change in ({'format':'unsupported'},{'extra':0}):
            with self.assertRaises(t.Rejected):run(dict(sample(),**change))

    def test_strict_json_and_outer_shapes(self):
        for raw in (b'null',b'[]',b'{}',b'NaN',b'1.0',b'"\\ud800"',b'{"format":1,"format":2}'):
            with self.assertRaises(t.Rejected):OP(raw)

    def test_raw_input_pin_no_mutation_or_authorization(self):
        value=sample();before=copy.deepcopy(value);raw=t.encode(value);result=OP(raw)
        self.assertEqual(value,before);self.assertEqual(result['input_sha256'],t.digest(raw));self.assertFalse(result['execution_authorized']);self.assertFalse(result['target_changes_performed'])

    def test_report_round_trip(self):
        result=run(sample());self.assertEqual(t.decode(t.encode(result)),result)

    def test_known_explicit_rename_and_pin(self):
        result=run(sample());self.assertFalse(result['assessment']['record_level_rule_required']);self.assertEqual(result['after_sha256'],c.pin(c.taxonomy(sample()['after'])))

    def test_split_and_merge_require_record_level_review(self):
        value=sample();value['mappings'][1]['targets'].append('noise-check');result=run(value)
        self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['assessment']['record_level_rule_required']);self.assertEqual(result['assessment']['merges'],[dict(target='noise-check',sources=['needs-review','noise-check'])])

    def test_explicit_retirement_and_introduction_do_not_modify_records(self):
        value=sample();value['mappings'][0]['targets']=[];result=run(value)
        self.assertEqual(result['status'],'PASS');self.assertEqual(result['assessment']['introduced_labels'],['filter-check']);self.assertFalse(result['records_relabelled']);self.assertFalse(result['retirement_authorized'])

    def test_missing_mapping_is_not_implicit_identity(self):
        value=sample();value['mappings'].pop();self.assertIsNone(run(value)['assessment'])

    def test_missing_labels_or_duplicate_source_mappings_withhold(self):
        for change in ({'source':'missing'},{'targets':['missing']}):
            value=sample();value['mappings'][0].update(change);self.assertIsNone(run(value)['assessment'])
        value=sample();value['mappings'].append(dict(value['mappings'][0],id='another'));self.assertIsNone(run(value)['assessment'])

    def test_mapping_change_requires_new_revision_even_without_label_changes(self):
        value=sample();value['before']=copy.deepcopy(value['after']);value['mappings'][0]['source']='filter-check';value['mappings'][0]['targets']=['needs-review']
        self.assertIsNone(run(value)['assessment'])

    def test_taxonomy_identity_or_version_regression_withholds(self):
        for change in ({'id':'other'},{'revision':1}):
            value=sample();value['after'].update(change);self.assertIsNone(run(value)['assessment'])

    def test_normalized_duplicate_snapshots_count_once(self):
        value=sample();before=run(value);value['mappings']*=2;self.assertEqual(run(value)['assessment'],before['assessment'])

    def test_conflicting_mapping_group_withholds_every_member(self):
        value=sample();value['mappings']+=[copy.deepcopy(value['mappings'][0]),dict(value['mappings'][0],targets=[])]
        result=run(value);self.assertIsNone(result['assessment']);self.assertEqual(result['counts']['mappings']['conflict_rows'],3)

    def test_input_order_does_not_change_assessment(self):
        value=sample();before=run(value);value['mappings'].reverse();value['after']['labels'].reverse();self.assertEqual(run(value)['assessment'],before['assessment'])
