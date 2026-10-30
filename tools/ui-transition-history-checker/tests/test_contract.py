import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import histories as app
import form_core as r

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()
def at(value,path):
    for key in path:value=value[key]
    return value

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        out=self.run_value(value);self.assertEqual(out['status'],'REVIEW_REQUIRED');self.assertTrue(out['issues']);self.assertIsNone(out['qualified_scope_sha256']);return out
    def withheld(self,value=None):
        out=self.review(value);self.assertIsNone(out['assessment'])
        for key in ['forms_sha256', 'flows_sha256', 'submissions_sha256', 'histories_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('browser_started','dom_inspected','scripts_executed','network_requests_performed','authentication_performed','records_changed','raw_values_emitted','content_privacy_verified','execution_authorized','target_changes_performed','accessibility_verified','whole_ui_compatibility_verified'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['forms'], ['flows'], ['submissions'], ['histories']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['forms_sha256', 'flows_sha256', 'submissions_sha256', 'histories_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['forms'], ['flows'], ['submissions'], ['histories']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['forms'], ['flows'], ['submissions'], ['histories']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['forms'], ['flows'], ['submissions'], ['histories']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['forms'], ['flows'], ['submissions'], ['histories']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['forms'], ['flows'], ['submissions'], ['histories']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['forms'], ['flows'], ['submissions'], ['histories']][0]).clear();self.withheld(value)


    def repin(self,value=None,prefix=''):
        value=self.value if value is None else value
        def name(key):return prefix+'_'+key if prefix else key
        forms={v['id']:r.form(v)[1] for v in value[name('forms')]};flows={v['id']:v for v in value.get(name('flows'),[])};subs={v['id']:v for v in value.get(name('submissions'),[])}
        for row in [*flows.values(),*subs.values()]:
            if row['form'] in forms:row.update(form_revision=forms[row['form']]['revision'],form_sha256=pin(forms[row['form']]))
        for row in value.get(name('histories'),[]):
            if row['flow'] in flows:row.update(flow_revision=flows[row['flow']]['revision'],flow_sha256=pin(r.flow(flows[row['flow']])[1]))
            for item in row['events']:
                if item['submission'] in subs:item.update(submission_revision=subs[item['submission']]['revision'],submission_sha256=pin(subs[item['submission']]))

    def test_known_review_history_reaches_only_declared_terminal(self):
        row=self.run_value()['assessment']['histories'][0];self.assertTrue(row['valid']);self.assertTrue(row['terminal_reached']);self.assertEqual(row['last_confirmed_state'],'reviewed');self.assertEqual(len(row['steps']),2)
    def test_bad_sequence_blocks_later_steps_without_recovery(self):
        self.value['histories'][0]['events'][0]['sequence']=2;row=self.review()['assessment']['histories'][0];self.assertEqual(row['last_confirmed_state'],'draft');self.assertEqual(row['steps'][1]['failed_criteria'],['UNASSESSED_AFTER_INVALID_STEP'])
    def test_wrong_source_state_is_not_used_to_choose_another_transition(self):
        self.value['histories'][0]['events'][0]['from']='review';row=self.review()['assessment']['histories'][0];self.assertIn('SOURCE_STATE_MISMATCH',row['steps'][0]['failed_criteria']);self.assertFalse(row['terminal_reached'])
    def test_wrong_target_and_unknown_action_do_not_advance(self):
        for change in ({'to':'reviewed'},{'action':'other-action'}):
            value=copy.deepcopy(self.value);value['histories'][0]['events'][0].update(change);self.assertEqual(self.review(value)['assessment']['histories'][0]['last_confirmed_state'],'draft')
    def test_unknown_or_stale_observation_reference_withholds_whole_history_scope(self):
        for change in ({'submission':'missing'},{'submission_revision':2},{'submission_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['histories'][0]['events'][0].update(change);self.withheld(value)
    def test_submission_must_bind_the_same_form_snapshot_as_flow(self):
        other=copy.deepcopy(self.value['forms'][0]);other['id']='other-form';self.value['forms'].append(other);self.value['submissions'][0].update(form='other-form',form_sha256=pin(other));self.repin();self.withheld()
    def test_no_submission_transition_rejects_attached_values_reference(self):
        self.value['histories'][0]['events'][1].update({key:self.value['histories'][0]['events'][0][key] for key in ('submission','submission_revision','submission_sha256')});self.assertIn('SUBMISSION_NOT_ALLOWED',self.review()['assessment']['histories'][0]['steps'][1]['failed_criteria'])
    def test_valid_submission_guard_requires_actual_validity(self):
        self.value['submissions'][0]['values']['priority']=6;self.value['submissions'][0]['expected_valid']=False;self.repin();self.assertIn('SUBMISSION_VALIDITY_MISMATCH',self.review()['assessment']['histories'][0]['steps'][0]['failed_criteria'])
    def test_explicit_invalid_submission_branch_can_be_a_valid_history(self):
        self.value['flows'][0]['transitions'][0]['submission_requirement']='invalid';self.value['submissions'][0]['values']['priority']=6;self.value['submissions'][0]['expected_valid']=False;self.repin();out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertFalse(out['assessment']['submissions'][0]['valid']);self.assertTrue(out['assessment']['histories'][0]['valid'])
    def test_missing_guarded_submission_is_a_logical_history_finding(self):
        self.value['histories'][0]['events'][0].update(submission=None,submission_revision=None,submission_sha256=None);self.assertIn('SUBMISSION_REQUIRED',self.review()['assessment']['histories'][0]['steps'][0]['failed_criteria'])
    def test_empty_or_partial_history_does_not_invent_terminal_coverage(self):
        for size in (0,1):
            value=copy.deepcopy(self.value);value['histories'][0]['events']=value['histories'][0]['events'][:size];self.assertFalse(self.review(value)['assessment']['histories'][0]['terminal_reached'])
    def test_terminal_state_cannot_have_outgoing_transition(self):
        self.value['flows'][0]['transitions'][0]['from']='reviewed';self.withheld()
    def test_ambiguous_action_slot_and_duplicate_transition_id_refuse(self):
        for alias in (dict(self.value['flows'][0]['transitions'][0],id='alias'),copy.deepcopy(self.value['flows'][0]['transitions'][0])):
            value=copy.deepcopy(self.value);value['flows'][0]['transitions'].append(alias);self.withheld(value)
    def test_unreachable_or_nonterminating_states_are_structural_findings(self):
        self.value['flows'][0]['states'].append('unreachable');self.withheld()
    def test_exact_flow_and_flow_form_pins_are_not_report_authority(self):
        value=copy.deepcopy(self.value);value['histories'][0]['flow_sha256']='0'*64;self.withheld(value);self.value['flows'][0]['form_sha256']='0'*64;self.withheld()
    def test_event_and_history_caps_are_not_truncated(self):
        value=copy.deepcopy(self.value);value['histories'][0]['events']*=65;self.withheld(value);self.value['histories']=[dict(self.value['histories'][0],id='history-'+str(i)) for i in range(257)]
        with self.assertRaisesRegex(t.Rejected,'COHORT_LIMIT'):self.run_value()
