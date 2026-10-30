import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import fallbacks as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment'])
        for key in ['models_sha256', 'request_sha256', 'policy_sha256', 'chain_sha256', 'plan_sha256']:self.assertIsNone(r[key])
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
        for path in [['models'], ['chain', 'steps']]:
            selected=self.value
            for key in path:selected=selected[key]
            selected.reverse()
        after=self.run_value()
        for key in ['models_sha256', 'request_sha256', 'policy_sha256', 'chain_sha256', 'plan_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_identity_snapshots_count_once(self):
        for path in [['models'], ['chain', 'steps']]:
            value=copy.deepcopy(self.value);selected=value
            for key in path:selected=selected[key]
            if not selected:continue
            selected.append(copy.deepcopy(selected[0]));r=self.run_value(value);self.assertEqual(r['status'],'PASS')
            counts=r['counts'][path[-1]];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_rejected_rows_withhold_and_omit_values(self):
        for path in [['models'], ['chain', 'steps']]:
            value=copy.deepcopy(self.value);selected=value
            for key in path:selected=selected[key]
            selected.append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(value)
            self.assertEqual(r['counts'][path[-1]]['rejected_rows'],1);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_nonlist_and_excess_rows_are_fixed_refusals(self):
        for path in [['models'], ['chain', 'steps']]:
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

    def rebind(self):
        models={m['id']:m for m in self.value['models']}
        for step in self.value['chain']['steps']:
            if step['model'] in models:step.update(model_revision=models[step['model']]['revision'],model_sha256=pin(models[step['model']]))
        self.value['chain'].update(request_sha256=pin(self.value['request']),policy_sha256=pin(self.value['policy']))
    def test_complete_order_and_plan_pin_known_scope(self):
        r=self.run_value();self.assertEqual([s['step'] for s in r['assessment']['ordered_steps']],['primary-step','reserve-step'])
        self.assertEqual(r['plan_sha256'],pin({k:r[k] for k in ('models_sha256','request_sha256','policy_sha256','chain_sha256')}))
    def test_cap_failure_retains_entire_chain_without_truncation(self):
        self.value['chain']['maximum_attempts']=1;r=self.review();self.assertEqual(len(r['assessment']['ordered_steps']),2);self.assertIsNone(r['plan_sha256']);self.assertIsNotNone(r['chain_sha256'])
    def test_repeated_model_is_review_not_an_implicit_retry(self):
        self.value['chain']['steps'][1]['model']='hvac-primary';self.rebind();self.assertIn('MODEL_REPEATED_IN_CHAIN',self.review()['assessment']['failed_criteria'])
    def test_per_step_budget_failure_preserves_complete_diagnostics(self):
        self.value['request']['input_units']=450;self.rebind();a=self.review()['assessment'];self.assertTrue(a['ordered_steps'][0]['eligible']);self.assertFalse(a['ordered_steps'][1]['eligible'])
    def test_cycle_and_self_cycle_withhold_order_and_pins(self):
        v=copy.deepcopy(self.value);v['chain']['steps'][1].update(next_step='primary-step',on_failures=['timeout']);self.withheld(v)
        self.value['chain']['steps'][0]['next_step']='primary-step';self.withheld()
    def test_unreachable_step_is_not_pruned(self):
        self.value['chain']['steps'].append(dict(self.value['chain']['steps'][1],id='unused-step'));self.withheld()
    def test_unknown_start_next_and_model_bindings_withhold(self):
        v=copy.deepcopy(self.value);v['chain']['start']='missing';self.withheld(v)
        for change in ({'next_step':'missing'},{'model':'missing'},{'model_revision':2},{'model_sha256':'0'*64}):
            v=copy.deepcopy(self.value);v['chain']['steps'][0].update(change);self.withheld(v)
    def test_actual_request_and_policy_pins_are_required(self):
        for key in ('request_sha256','policy_sha256'):
            v=copy.deepcopy(self.value);v['chain'][key]='0'*64;self.withheld(v)
    def test_failure_conditions_and_terminal_shape_reject_invalid_steps(self):
        for index,change in [(0,{'on_failures':[]}),(0,{'on_failures':['other']}),(1,{'on_failures':['timeout']}),(0,{'next_step':True})]:
            v=copy.deepcopy(self.value);v['chain']['steps'][index].update(change);self.withheld(v)
    def test_failure_condition_order_normalizes_without_changing_plan_pin(self):
        expected=self.run_value()['plan_sha256'];self.value['chain']['steps'][0]['on_failures'].reverse();self.assertEqual(self.run_value()['plan_sha256'],expected)
    def test_conflicting_step_identity_never_selects_latest(self):
        self.value['chain']['steps'].append(dict(self.value['chain']['steps'][0],next_step='primary-step'));self.withheld()
    def test_step_count_and_cap_bounds_are_fixed_refusals(self):
        for maximum in (0,33,True):
            v=copy.deepcopy(self.value);v['chain']['maximum_attempts']=maximum
            with self.assertRaises(t.Rejected):self.run_value(v)
        self.value['chain']['steps']=[{}]*33
        with self.assertRaisesRegex(t.Rejected,'STEP_LIMIT'):self.run_value()
    def test_empty_step_list_withholds(self):
        self.value['chain']['steps']=[];self.withheld()
    def test_full_32_step_bound_is_supported_without_recursion(self):
        template=self.value['models'][0];models=[dict(template,id='fictional-model-'+str(i).zfill(2)) for i in range(32)]
        self.value['models']=models;self.value['policy']['allowed_models']=[m['id'] for m in models]
        self.value['chain'].update(start='step-00',maximum_attempts=32,steps=[dict(id='step-'+str(i).zfill(2),model=m['id'],model_revision=1,model_sha256=pin(m),next_step='step-'+str(i+1).zfill(2) if i<31 else None,on_failures=['timeout'] if i<31 else []) for i,m in enumerate(models)])
        self.rebind();r=self.run_value();self.assertEqual(r['status'],'PASS');self.assertEqual(r['assessment']['declared_steps'],32)
