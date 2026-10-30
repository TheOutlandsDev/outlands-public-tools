import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import selection as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None,key='assessment'):
        result=self.run_value(value);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['issues']);return result
    def withheld(self,value=None):
        result=self.review(value);self.assertIsNone(result['assessment']);return result
    def test_fictional_positive_and_authority_boundaries(self):
        result=self.run_value();self.assertEqual(result['status'],'PASS')
        for key in ('artifact_bytes_verified','label_truth_verified','holdout_independence_verified','training_performed','dataset_export_performed','content_privacy_verified','execution_authorized','target_changes_performed'):
            self.assertIs(result[key],False)
    def test_outer_contract_format_unknown_fields_and_duplicate_keys(self):
        for v in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(v)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_order_changes_do_not_change_qualified_pins(self):
        expected=self.run_value()
        for key in ['records', 'approvals', 'exclusions', 'selections']:self.value[key].reverse()
        actual=self.run_value()
        for key in ['records_sha256', 'policy_sha256', 'selected_records_sha256']:self.assertEqual(actual[key],expected[key])
    def test_identical_snapshots_count_once(self):
        for key in ['records', 'approvals', 'exclusions', 'selections']:
            if not self.value[key]:continue
            v=copy.deepcopy(self.value);v[key].append(copy.deepcopy(v[key][0]));result=self.run_value(v)
            self.assertEqual(result['status'],'PASS');counts=result['counts'][key];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')),counts['input_rows'])
    def test_rejected_rows_withhold_assessment_and_omit_values(self):
        for key in ['records', 'approvals', 'exclusions', 'selections']:
            v=copy.deepcopy(self.value);v[key].append({'id':'SYNTHETIC_SENTINEL'});result=self.withheld(v)
            self.assertEqual(result['counts'][key]['rejected_rows'],1);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(result))
    def test_list_bounds_are_fixed_refusals(self):
        for key in ['records', 'approvals', 'exclusions', 'selections']:
            for rows in (None,{},[{}]*1001):
                v=copy.deepcopy(self.value);v[key]=rows
                with self.assertRaises(t.Rejected):self.run_value(v)
    def test_taxonomy_rejects_duplicate_unknown_and_boolean_revision(self):
        for change in ({'labels':['filter','filter']},{'labels':[]},{'revision':True},{'revision':0},{'extra':0}):
            v=copy.deepcopy(self.value);v['taxonomy'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(v)

    def repin(self):
        records={r['id']:r for r in self.value['records']};policy=copy.deepcopy(self.value['policy']);policy['allowed_labels'].sort();taxonomy=copy.deepcopy(self.value['taxonomy']);taxonomy['labels'].sort()
        for side in ('approvals','exclusions','selections'):
            for r in self.value[side]:
                if r['record'] in records:r.update(record_revision=records[r['record']]['revision'],record_sha256=pin(records[r['record']]))
                if side!='exclusions':r['policy_sha256']=pin(policy)
                if side=='approvals':r['taxonomy_sha256']=pin(taxonomy)
    def test_selected_snapshot_pin_known_bytes_and_no_export(self):
        r=self.run_value();self.assertTrue(r['assessment']['eligible_for_manual_export_review']);self.assertEqual(r['selected_records_sha256'],pin(self.value['records'][:2]));self.assertFalse(r['dataset_export_performed'])
    def test_missing_approval_retains_refused_selection(self):
        self.value['approvals'].pop();r=self.review();self.assertIn('APPROVAL_MISSING',r['assessment']['selections'][1]['failed_criteria']);self.assertIsNone(r['selected_records_sha256'])
    def test_explicit_rejection_blocks_selection(self):
        self.value['approvals'][0]['decision']='reject';r=self.review();self.assertEqual(r['assessment']['eligible_records'],1)
    def test_exclusion_wins_over_approval(self):
        r=self.value['selections'][0];self.value['exclusions']=[{k:v for k,v in dict(r,id='exclude-alpha',reason='fictional-hold').items() if k!='policy_sha256'}]
        a=self.review()['assessment'];self.assertIn('RECORD_EXCLUDED',a['selections'][0]['failed_criteria']);self.assertFalse(a['eligible_for_manual_export_review'])
    def test_held_out_and_validation_records_never_become_training(self):
        for partition in ('test','validation'):
            self.value['records'][0]['partition']=partition;self.repin();r=self.review();self.assertIn('NONTRAINING_PARTITION',r['assessment']['selections'][0]['failed_criteria'])
    def test_policy_label_exclusion_is_retained(self):
        self.value['policy']['allowed_labels']=['noise'];self.repin();a=self.review()['assessment'];self.assertIn('LABEL_NOT_ALLOWED',a['selections'][0]['failed_criteria'])
    def test_changing_full_snapshot_label_or_group_invalidates_existing_pins(self):
        for change in ({'label':'noise'},{'group':'unit-other'},{'partition':'test'},{'content_sha256':'0'*64},{'revision':2}):
            v=copy.deepcopy(self.value);v['records'][0].update(change);r=self.withheld(v);self.assertIsNone(r['records_sha256']);self.assertIsNone(r['policy_sha256'])
    def test_reference_hash_revision_and_policy_pins_all_must_match(self):
        for side,changes in [('selections',[{'record':'missing'},{'record_revision':2},{'record_sha256':'0'*64},{'policy_sha256':'0'*64}]),('approvals',[{'taxonomy_sha256':'0'*64},{'policy_sha256':'0'*64},{'record_revision':2}])]:
            for change in changes:
                v=copy.deepcopy(self.value);v[side][0].update(change);self.withheld(v)
    def test_policy_revision_change_invalidates_approval_and_selection(self):
        self.value['policy']['revision']=2;self.withheld()
    def test_new_taxonomy_revision_invalidates_approval(self):
        self.value['taxonomy']['revision']=2;self.withheld()
    def test_distinct_approval_ids_for_same_record_are_ambiguous(self):
        self.value['approvals'].append(dict(self.value['approvals'][0],id='second-approval'));self.withheld()
    def test_distinct_selection_ids_do_not_double_select(self):
        self.value['selections'].append(dict(self.value['selections'][0],id='second-selection'));self.withheld()
    def test_multiple_explicit_exclusion_reasons_are_allowed_but_still_block(self):
        link={k:v for k,v in self.value['selections'][0].items() if k!='policy_sha256'}
        self.value['exclusions']=[dict(link,id='exclude-one',reason='hold-one'),dict(link,id='exclude-two',reason='hold-two')]
        self.assertEqual(self.review()['assessment']['eligible_records'],1)
    def test_stale_unused_exclusion_is_not_silently_ignored(self):
        r=self.value['records'][3];self.value['exclusions']=[dict(id='exclude-heldout',record=r['id'],record_revision=2,record_sha256=pin(r),reason='fictional-hold')];self.withheld()
    def test_empty_records_or_selection_withholds(self):
        for key in ('records','selections'):
            v=copy.deepcopy(self.value);v[key]=[];self.withheld(v)
    def test_conflicting_source_revision_withholds_group(self):
        self.value['records'].append(dict(self.value['records'][0],revision=2));r=self.withheld();self.assertEqual(r['counts']['records']['conflict_rows'],2)
    def test_policy_schema_and_unknown_label_are_fixed_refusals(self):
        for change in ({'revision':True},{'allowed_labels':[]},{'allowed_labels':['unknown']},{'extra':0}):
            v=copy.deepcopy(self.value);v['policy'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(v)
    def test_malformed_links_decision_and_revision_are_rejected_rows(self):
        for change in ({'decision':None},{'decision':[]},{'record_revision':True},{'taxonomy_sha256':'bad'}):
            v=copy.deepcopy(self.value);v['approvals'][0].update(change);self.withheld(v)
