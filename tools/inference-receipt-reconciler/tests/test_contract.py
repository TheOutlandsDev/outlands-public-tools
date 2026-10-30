import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import receipts as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment'])
        for key in ['attempts_sha256']:self.assertIsNone(r[key])
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
        for path in [['models'], ['chain', 'steps'], ['attempts']]:
            selected=self.value
            for key in path:selected=selected[key]
            selected.reverse()
        after=self.run_value()
        for key in ['models_sha256', 'request_sha256', 'policy_sha256', 'chain_sha256', 'plan_sha256', 'attempts_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_identity_snapshots_count_once(self):
        for path in [['models'], ['chain', 'steps'], ['attempts']]:
            value=copy.deepcopy(self.value);selected=value
            for key in path:selected=selected[key]
            if not selected:continue
            selected.append(copy.deepcopy(selected[0]));r=self.run_value(value);self.assertEqual(r['status'],'PASS')
            counts=r['counts'][path[-1]];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_rejected_rows_withhold_and_omit_values(self):
        for path in [['models'], ['chain', 'steps'], ['attempts']]:
            value=copy.deepcopy(self.value);selected=value
            for key in path:selected=selected[key]
            selected.append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(value)
            self.assertEqual(r['counts'][path[-1]]['rejected_rows'],1);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_nonlist_and_excess_rows_are_fixed_refusals(self):
        for path in [['models'], ['chain', 'steps'], ['attempts']]:
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
        models={m['id']:m for m in self.value['models']};chain=self.value['chain'];rule=self.value['policy']
        for field in ('allowed_models','allowed_tasks','allowed_input_types','allowed_output_types'):rule[field].sort()
        for step in chain['steps']:
            step['on_failures'].sort()
            if step['model'] in models:step.update(model_revision=models[step['model']]['revision'],model_sha256=pin(models[step['model']]))
        chain.update(request_sha256=pin(self.value['request']),policy_sha256=pin(rule))
        normalized=dict(chain,steps=sorted(chain['steps'],key=lambda r:r['id']))
        binding=dict(models_sha256=pin(sorted(self.value['models'],key=lambda r:r['id'])),request_sha256=pin(self.value['request']),policy_sha256=pin(rule),chain_sha256=pin(normalized))
        steps={s['id']:s for s in chain['steps']}
        for a in self.value['attempts']:
            a.update(request_sha256=binding['request_sha256'],plan_sha256=pin(binding))
            if a['step'] in steps:
                for field in ('model','model_revision','model_sha256'):a[field]=steps[a['step']][field]
    def terminal(self,status,rows):
        self.value['attempts']=rows;last=rows[-1] if rows else None
        self.value['result']=dict(status=status,attempts=len(rows),final_attempt=last['id'] if last else None,output_sha256=last['output_sha256'] if status=='succeeded' else None)
    def test_successful_fallback_has_exact_attempt_order_and_output_pin(self):
        r=self.run_value();a=r['assessment'];self.assertEqual(a['ordered_attempt_ids'],['attempt-one','attempt-two']);self.assertEqual(a['observed_terminal_status'],'succeeded')
        self.assertEqual(a['output_sha256'],self.value['result']['output_sha256']);self.assertTrue(a['eligible_for_manual_receipt_review']);self.assertFalse(r['inference_occurrence_verified'])
    def test_early_success_needs_no_fallback_receipt(self):
        a=self.value['attempts'][0];a.update(status='succeeded',failure_class=None,output_sha256='1'*64,output_units=1);self.terminal('succeeded',[a]);self.assertEqual(self.run_value()['status'],'PASS')
    def test_terminal_failed_outcome_can_pass_consistency_without_success_claim(self):
        a=self.value['attempts'][0];a['failure_class']='invalid-output';self.terminal('failed',[a]);r=self.run_value();self.assertEqual(r['status'],'PASS');self.assertEqual(r['assessment']['observed_terminal_status'],'failed')
    def test_failed_last_step_never_becomes_success(self):
        self.value['attempts'][1].update(status='failed',failure_class='rate-limited',output_sha256=None,output_units=None);self.terminal('failed',self.value['attempts']);self.assertEqual(self.run_value()['status'],'PASS')
    def test_missing_permitted_fallback_is_unknown_with_retained_summary(self):
        self.terminal('unknown',self.value['attempts'][:1]);a=self.review()['assessment'];self.assertEqual(a['observed_terminal_status'],'unknown');self.assertIn('FALLBACK_RECEIPT_MISSING',a['failed_criteria'])
    def test_unknown_receipt_never_passes_or_authorizes_retry(self):
        a=self.value['attempts'][0];a.update(status='unknown',failure_class=None);self.terminal('unknown',[a]);r=self.review();self.assertIsNotNone(r['assessment']);self.assertIn('TERMINAL_OUTCOME_UNKNOWN',r['assessment']['failed_criteria'])
    def test_no_attempts_is_explicit_uncertainty_not_inference(self):
        self.terminal('unknown',[]);a=self.review()['assessment'];self.assertEqual(a['attempts'],0);self.assertEqual(a['failed_criteria'],['ATTEMPTS_MISSING','TERMINAL_OUTCOME_UNKNOWN'])
    def test_attempt_after_success_or_unknown_withholds_summary(self):
        for change in ({'status':'succeeded','failure_class':None,'output_sha256':'1'*64,'output_units':1},{'status':'unknown','failure_class':None}):
            v=copy.deepcopy(self.value);v['attempts'][0].update(change);self.withheld(v)
    def test_transition_failure_class_must_be_explicitly_permitted(self):
        self.value['chain']['steps'][0]['on_failures']=['unavailable'];self.rebind();self.withheld()
    def test_ordinal_gap_and_wrong_start_withhold_summary(self):
        v=copy.deepcopy(self.value);v['attempts'][1]['ordinal']=3;self.withheld(v)
        a=self.value['attempts'][1];a['ordinal']=1;self.terminal('succeeded',[a]);self.withheld()
    def test_distinct_attempt_ids_for_same_ordinal_are_ambiguous(self):
        self.value['attempts'].append(dict(self.value['attempts'][0],id='attempt-extra'));r=self.withheld();self.assertTrue(any(x['code']=='SLOT_AMBIGUOUS' for x in r['issues']))
    def test_exact_model_request_plan_and_step_binding_is_required(self):
        for change in ({'step':'missing'},{'model':'hvac-reserve'},{'model_revision':2},{'model_sha256':'0'*64},{'request_sha256':'0'*64},{'plan_sha256':'0'*64}):
            v=copy.deepcopy(self.value);v['attempts'][0].update(change);self.withheld(v)
    def test_ineligible_chain_withholds_receipts_but_retains_plan_findings(self):
        self.value['chain']['maximum_attempts']=1;self.rebind();r=self.withheld();self.assertIsNone(r['plan_sha256']);self.assertIn('CHAIN_EXCEEDS_ATTEMPT_CAP',r['plan_assessment']['failed_criteria'])
    def test_declared_result_mismatches_retain_computed_observations(self):
        self.value['result'].update(status='failed',attempts=1,final_attempt='attempt-one',output_sha256=None);a=self.review()['assessment']
        self.assertEqual(a['observed_terminal_status'],'succeeded');self.assertEqual(a['failed_criteria'],['FINAL_ATTEMPT_MISMATCH','RESULT_ATTEMPT_COUNT_MISMATCH','RESULT_OUTPUT_PIN_MISMATCH','RESULT_STATUS_MISMATCH'])
    def test_output_budget_excess_is_review_not_silent_acceptance(self):
        self.value['attempts'][1]['output_units']=41;a=self.review()['assessment'];self.assertIn('OUTPUT_BUDGET_EXCEEDED',a['failed_criteria']);self.assertEqual(a['observed_terminal_status'],'succeeded')
    def test_malformed_conditional_receipts_and_ordinal_types_reject_rows(self):
        for change in ({'status':'other'},{'ordinal':True},{'ordinal':33},{'failure_class':None},{'output_sha256':'1'*64},{'output_units':0}):
            v=copy.deepcopy(self.value);v['attempts'][0].update(change);self.withheld(v)
        for change in ({'failure_class':'timeout'},{'output_sha256':None},{'output_units':True}):
            v=copy.deepcopy(self.value);v['attempts'][1].update(change);self.withheld(v)
    def test_result_schema_is_fixed_refusal(self):
        for change in ({'attempts':True},{'attempts':33},{'status':'other'},{'final_attempt':None},{'output_sha256':None},{'extra':0}):
            v=copy.deepcopy(self.value);v['result'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(v)
    def test_changed_prompt_revision_cannot_reuse_existing_chain(self):
        self.value['request']['prompt_sha256']='0'*64;self.withheld()
