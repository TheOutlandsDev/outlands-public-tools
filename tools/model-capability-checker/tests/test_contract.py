import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import models as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment'])
        for key in ['models_sha256']:self.assertIsNone(r[key])
        return r
    def test_positive_and_authority_boundaries(self):
        r=self.run_value();self.assertEqual(r['status'],'PASS')
        for key in ('capabilities_independently_verified','artifact_bytes_verified','input_units_measured','output_units_measured','inference_performed','inference_occurrence_verified','provider_contacted','output_content_verified','dispatch_authorized','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(r[key],False)
    def test_outer_format_unknown_fields_and_duplicate_keys_refuse(self):
        for v in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(v)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_row_order_does_not_change_normalized_scope_pins(self):
        before=self.run_value()
        for path in [['models']]:
            selected=self.value
            for key in path:selected=selected[key]
            selected.reverse()
        after=self.run_value()
        for key in ['models_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_identity_snapshots_count_once(self):
        for path in [['models']]:
            value=copy.deepcopy(self.value);selected=value
            for key in path:selected=selected[key]
            if not selected:continue
            selected.append(copy.deepcopy(selected[0]));r=self.run_value(value);self.assertEqual(r['status'],'PASS')
            counts=r['counts'][path[-1]];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_rejected_rows_withhold_and_omit_values(self):
        for path in [['models']]:
            value=copy.deepcopy(self.value);selected=value
            for key in path:selected=selected[key]
            selected.append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(value)
            self.assertEqual(r['counts'][path[-1]]['rejected_rows'],1);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_nonlist_and_excess_rows_are_fixed_refusals(self):
        for path in [['models']]:
            for rows in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);selected=value
                for key in path[:-1]:selected=selected[key]
                selected[path[-1]]=rows
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_conflicting_model_revision_withholds_every_member(self):
        self.value['models'].append(dict(self.value['models'][0],revision=2));r=self.withheld();self.assertEqual(r['counts']['models']['conflict_rows'],2)
    def test_model_types_and_bounds_reject_rows(self):
        for change in ({'revision':True},{'max_input_units':0},{'max_output_units':1000000001},{'context_units':'700'},{'tasks':[]},{'input_types':['text','text']},{'output_types':[{}]},{'extra':0}):
            value=copy.deepcopy(self.value);value['models'][0].update(change);self.withheld(value)
    def test_empty_model_catalog_withholds(self):
        self.value['models']=[];self.withheld()

    def test_collection_and_per_model_pins_match_independent_bytes(self):
        r=self.run_value();self.assertEqual(r['models_sha256'],pin(self.value['models']));self.assertEqual(r['assessment']['consistent_models'],2)
        self.assertEqual(r['assessment']['models'][0]['model_sha256'],pin(self.value['models'][0]))
    def test_independent_limit_exceeding_context_retains_assessment_and_pins(self):
        self.value['models'][0]['max_input_units']=701;self.value['models'][0]['max_output_units']=702;r=self.review()
        self.assertEqual(r['assessment']['models'][0]['failed_criteria'],['MODEL_INPUT_EXCEEDS_CONTEXT','MODEL_OUTPUT_EXCEEDS_CONTEXT']);self.assertIsNotNone(r['models_sha256'])
    def test_maximum_input_plus_output_need_not_fit_simultaneously(self):
        self.value['models'][0]['max_output_units']=200;self.assertEqual(self.run_value()['status'],'PASS')
    def test_capability_sets_normalize_order_but_not_revisions(self):
        self.value['models'][0]['tasks']=['classify-ticket','npc-intent'];before=self.run_value()['models_sha256']
        self.value['models'][0]['tasks'].reverse();self.assertEqual(self.run_value()['models_sha256'],before)
        self.value['models'][0]['revision']=2;self.assertNotEqual(self.run_value()['models_sha256'],before)
    def test_duplicate_normalized_capability_sets_are_one_snapshot(self):
        a=self.value['models'][0];a['tasks']=['npc-intent','classify-ticket'];self.value['models'].append(dict(a,tasks=['classify-ticket','npc-intent']))
        r=self.run_value();self.assertEqual(r['status'],'PASS');self.assertEqual(r['counts']['models']['duplicate_rows'],1)
    def test_one_structurally_bad_model_withholds_good_model_assessment(self):
        self.value['models'].append({'id':'bad-model'});self.withheld()
    def test_limits_equal_to_context_are_consistent(self):
        self.value['models'][0].update(max_input_units=700,max_output_units=700);self.assertEqual(self.run_value()['status'],'PASS')
