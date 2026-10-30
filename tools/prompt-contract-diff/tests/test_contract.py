from prompts import check as OP

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

    def test_matching_contract_and_version_only_change(self):
        value=sample();result=run(value);self.assertFalse(result['changes']['messages_changed'])
        value['after']['revision']=2;result=run(value);self.assertEqual(result['status'],'PASS');self.assertTrue(result['changes']['version_only']);self.assertNotEqual(result['before_sha256'],result['after_sha256'])

    def test_message_role_text_and_order_changes_are_explicit(self):
        for change in ('role','text','order'):
            value=sample();value['after']['revision']=2
            if change=='role':value['after']['messages'][0]['role']='assistant'
            elif change=='text':value['after']['messages'][0]['template']='Invented replacement instruction.'
            else:value['after']['messages'].reverse()
            result=run(value);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['changes']['messages_changed'])

    def test_fields_and_variable_changes_are_structural(self):
        value=sample();value['after']['revision']=2;value['after']['messages'][1]['template']='{{new_request}}';value['after']['variables']=['new_request'];value['after']['output_contract']['fields'].append(dict(id='needs_review',type='boolean',required=True))
        result=run(value);self.assertEqual(result['changes']['variables_added'],['new_request']);self.assertEqual(result['changes']['variables_removed'],['request_text']);self.assertEqual(result['changes']['fields_added'],['needs_review'])

    def test_changed_prompt_requires_new_revision(self):
        value=sample();value['after']['messages'][0]['template']='Changed fictional instruction.';self.assertIsNone(run(value)['changes'])

    def test_taxonomy_change_requires_its_own_revision(self):
        value=sample();value['after']['revision']=2;value['after']['output_contract']['taxonomy']['labels'].append('other')
        self.assertIsNone(run(value)['changes'])

    def test_ids_and_revision_regressions_withhold_comparison(self):
        value=sample();value['after']['id']='another';self.assertIsNone(run(value)['changes'])
        value=sample();value['before']['revision']=2;self.assertIsNone(run(value)['changes'])
        value=sample();value['after']['output_contract']['taxonomy']['id']='another';self.assertIsNone(run(value)['changes'])

    def test_malformed_undeclared_or_unused_placeholders_refuse(self):
        for template in ('{{missing}}','{{request_text','{{UPPER}}','{{request_text}} }}'):
            value=sample();value['after']['messages'][1]['template']=template
            with self.assertRaises(t.Rejected):run(value)
        value=sample();value['after']['variables'].append('unused')
        with self.assertRaises(t.Rejected):run(value)

    def test_exact_role_and_output_schema_subset(self):
        for change in ('tool-role','duplicate-message','optional-label','duplicate-field','unknown-field-type'):
            value=sample();after=value['after']
            if change=='tool-role':after['messages'][0]['role']='tool'
            elif change=='duplicate-message':after['messages'].append(dict(after['messages'][0]))
            elif change=='optional-label':after['output_contract']['fields'][0]['required']=False
            elif change=='duplicate-field':after['output_contract']['fields'].append(dict(after['output_contract']['fields'][0]))
            else:after['output_contract']['fields'][1]['type']='object'
            with self.assertRaises(t.Rejected):run(value)

    def test_field_and_variable_order_normalization_keeps_pin(self):
        value=sample();value['after']['output_contract']['fields'].reverse();value['after']['output_contract']['taxonomy']['labels'].reverse()
        result=run(value);self.assertEqual(result['status'],'PASS');self.assertEqual(result['before_sha256'],result['after_sha256'])

    def test_no_rendering_or_literal_prompt_echo(self):
        value=sample();value['before']['messages'][0]['template']='SYNTHETIC_SENTINEL';value['after']=copy.deepcopy(value['before']);result=run(value)
        self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(result));self.assertFalse(result['prompt_rendered']);self.assertFalse(result['model_behavior_evaluated'])
