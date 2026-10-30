import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import routes as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment'])
        for key in ['models_sha256', 'requests_sha256', 'policy_sha256', 'proposals_sha256', 'route_plan_sha256']:self.assertIsNone(r[key])
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
        for path in [['models'], ['requests'], ['proposals']]:
            selected=self.value
            for key in path:selected=selected[key]
            selected.reverse()
        after=self.run_value()
        for key in ['models_sha256', 'requests_sha256', 'policy_sha256', 'proposals_sha256', 'route_plan_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_identity_snapshots_count_once(self):
        for path in [['models'], ['requests'], ['proposals']]:
            value=copy.deepcopy(self.value);selected=value
            for key in path:selected=selected[key]
            if not selected:continue
            selected.append(copy.deepcopy(selected[0]));r=self.run_value(value);self.assertEqual(r['status'],'PASS')
            counts=r['counts'][path[-1]];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_rejected_rows_withhold_and_omit_values(self):
        for path in [['models'], ['requests'], ['proposals']]:
            value=copy.deepcopy(self.value);selected=value
            for key in path:selected=selected[key]
            selected.append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(value)
            self.assertEqual(r['counts'][path[-1]]['rejected_rows'],1);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_nonlist_and_excess_rows_are_fixed_refusals(self):
        for path in [['models'], ['requests'], ['proposals']]:
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

    def repin(self):
        models={r['id']:r for r in self.value['models']};requests={r['id']:r for r in self.value['requests']};rule=copy.deepcopy(self.value['policy'])
        for k in ('allowed_models','allowed_tasks','allowed_input_types','allowed_output_types'):rule[k].sort()
        for p in self.value['proposals']:
            if p['request'] in requests:p.update(request_revision=requests[p['request']]['revision'],request_sha256=pin(requests[p['request']]))
            if p['model'] in models:
                m=copy.deepcopy(models[p['model']])
                for k in ('tasks','input_types','output_types'):m[k].sort()
                p.update(model_revision=m['revision'],model_sha256=pin(m))
            p['policy_sha256']=pin(rule)
    def test_plan_pin_binds_every_scope_and_never_dispatches(self):
        r=self.run_value();self.assertTrue(r['assessment']['eligible_for_manual_routing_review'])
        self.assertEqual(r['route_plan_sha256'],pin({k:r[k] for k in ('models_sha256','requests_sha256','policy_sha256','proposals_sha256')}));self.assertFalse(r['dispatch_authorized'])
    def test_exact_budget_boundaries_pass(self):
        self.value['models'][0].update(max_input_units=240,max_output_units=40,context_units=280)
        self.value['policy'].update(max_input_units=240,max_output_units=40,max_total_units=280);self.repin();self.assertEqual(self.run_value()['status'],'PASS')
    def test_input_limit_failure_retains_full_proposal_with_no_plan_pin(self):
        self.value['models'][0]['max_input_units']=239;self.repin();r=self.review();self.assertIn('MODEL_INPUT_BUDGET_EXCEEDED',r['assessment']['proposals'][0]['failed_criteria']);self.assertIsNone(r['route_plan_sha256'])
    def test_context_sum_is_checked_separately_from_individual_limits(self):
        self.value['models'][0].update(max_input_units=240,max_output_units=40,context_units=260);self.repin()
        self.assertIn('MODEL_CONTEXT_BUDGET_EXCEEDED',self.review()['assessment']['proposals'][0]['failed_criteria'])
    def test_output_and_policy_limits_report_all_failures(self):
        self.value['requests'][0]['output_budget']=81;self.value['policy']['max_total_units']=300;self.repin();r=self.review()
        self.assertEqual(r['assessment']['proposals'][0]['failed_criteria'],['MODEL_OUTPUT_BUDGET_EXCEEDED','POLICY_OUTPUT_BUDGET_EXCEEDED','POLICY_TOTAL_BUDGET_EXCEEDED'])
    def test_explicit_policy_and_capability_constraints_are_independent(self):
        changes=[('models','tasks',['other-task'],'MODEL_TASK_UNSUPPORTED'),('models','input_types',['other-input'],'MODEL_INPUT_TYPE_UNSUPPORTED'),('models','output_types',['other-output'],'MODEL_OUTPUT_TYPE_UNSUPPORTED'),('policy','allowed_models',['hvac-reserve'],'MODEL_NOT_ALLOWED'),('policy','allowed_tasks',['other-task'],'TASK_NOT_ALLOWED'),('policy','allowed_input_types',['other-input'],'INPUT_TYPE_NOT_ALLOWED'),('policy','allowed_output_types',['other-output'],'OUTPUT_TYPE_NOT_ALLOWED')]
        original=copy.deepcopy(self.value)
        for side,key,val,code in changes:
            self.value=copy.deepcopy(original);target=self.value[side][0] if side=='models' else self.value[side];target[key]=val;self.repin()
            self.assertIn(code,self.review()['assessment']['proposals'][0]['failed_criteria'])
    def test_zero_input_units_are_explicitly_supported(self):
        self.value['requests'][0]['input_units']=0;self.repin();self.assertEqual(self.run_value()['status'],'PASS')
    def test_unknown_and_stale_bindings_withhold_all_plan_results(self):
        for change in ({'model':'missing'},{'model_revision':2},{'model_sha256':'0'*64},{'request':'missing'},{'request_revision':2},{'request_sha256':'0'*64},{'policy_sha256':'0'*64}):
            v=copy.deepcopy(self.value);v['proposals'][0].update(change);self.withheld(v)
    def test_changed_request_prompt_hash_invalidates_existing_proposal(self):
        self.value['requests'][0]['prompt_sha256']='0'*64;self.withheld()
    def test_distinct_proposals_for_one_request_are_ambiguous_even_when_equal(self):
        self.value['proposals'].append(dict(self.value['proposals'][0],id='proposal-extra'));self.withheld()
    def test_missing_request_coverage_is_not_implicit_abstention(self):
        self.value['requests'].append(dict(self.value['requests'][0],id='request-other'));self.withheld()
    def test_unused_inconsistent_model_invalidates_catalog_scope(self):
        self.value['models'][1]['max_input_units']=501;self.withheld()
    def test_policy_unknown_model_withholds_and_bad_schema_refuses(self):
        self.value['policy']['allowed_models'].append('missing');self.repin();self.withheld()
        for change in ({'revision':True},{'max_total_units':0},{'allowed_models':[]},{'extra':0}):
            v=copy.deepcopy(self.value);v['policy'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(v)
    def test_bad_request_boolean_units_and_missing_hash_are_rejected_rows(self):
        for change in ({'input_units':True},{'input_units':-1},{'output_budget':0},{'prompt_sha256':None}):
            v=copy.deepcopy(self.value);v['requests'][0].update(change);self.withheld(v)
    def test_empty_requests_or_proposals_withhold(self):
        for key in ('requests','proposals'):
            v=copy.deepcopy(self.value);v[key]=[];self.withheld(v)
    def test_fictional_game_routing_example(self):
        v=json.loads((Path(__file__).resolve().parents[1]/'examples/game-routing.json').read_text(encoding='utf-8'))
        self.assertEqual(self.run_value(v)['assessment']['proposals'][0]['model'],'game-dialogue')
