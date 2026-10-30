import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import queues as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment'])
        for key in ['review_scope_sha256', 'items_sha256', 'entries_sha256', 'policy_sha256']:self.assertIsNone(r[key])
        return r
    def test_positive_and_authority_boundaries(self):
        r=self.run_value();self.assertEqual(r['status'],'PASS')
        for key in ('artifact_bytes_verified','reviewer_identity_verified','approval_authority_verified','records_changed','execution_performed','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(r[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_row_order_preserves_full_scope_pins(self):
        before=self.run_value()
        for key in ['items', 'entries']:self.value[key].reverse()
        after=self.run_value()
        for key in ['review_scope_sha256', 'items_sha256', 'entries_sha256', 'policy_sha256']:self.assertEqual(before[key],after[key])
    def test_identical_identity_snapshots_count_once(self):
        for key in ['items', 'entries']:
            if not self.value[key]:continue
            value=copy.deepcopy(self.value);value[key].append(copy.deepcopy(value[key][0]));r=self.run_value(value)
            self.assertEqual(r['status'],'PASS');counts=r['counts'][key];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_bad_rows_withhold_and_omit_supplied_values(self):
        for key in ['items', 'entries']:
            value=copy.deepcopy(self.value);value[key].append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_list_bounds_and_nonlist_are_fixed_refusals(self):
        for key in ['items', 'entries']:
            for rows in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);value[key]=rows
                with self.assertRaises(t.Rejected):self.run_value(value)

    def test_conflicting_identity_groups_exclude_every_member(self):
        for side in ['items', 'entries']:
            if not self.value[side]:continue
            value=copy.deepcopy(self.value);row=copy.deepcopy(value[side][0])
            field=next(k for k in row if k!='id' and isinstance(row[k],(str,int)) and row[k] is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            value[side].extend([row,copy.deepcopy(value[side][0])]);r=self.withheld(value)
            self.assertEqual(r['counts'][side]['conflict_rows'],3)
    def test_input_pin_is_raw_and_reports_are_deterministic(self):
        raw=encode(self.value);r=app.check(raw);self.assertEqual(r['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(r,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(r['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(r['review_scope_sha256'],app.check(spaced)['review_scope_sha256'])
    def test_required_cohort_is_not_vacuously_valid(self):
        self.value[['items', 'entries'][0]]=[];self.withheld()
    def test_unknown_fields_and_nonobjects_are_rejected_rows(self):
        for side in ['items', 'entries']:
            value=copy.deepcopy(self.value);value[side].append(None);self.withheld(value)
            if value[side][:-1]:
                value=copy.deepcopy(self.value);value[side][0]['extra']=0;self.withheld(value)

    def test_known_coverage_and_exact_snapshot_pin(self):
        r=self.run_value();self.assertEqual(r['assessment']['items'],[dict(id='hvac-service-spec',entry_id='queue-filter-service',stage='completion-review',missing_roles=[],blockers=[],ready_for_manual_review=True)])
        self.assertEqual(r['items_sha256'],pin(sorted(self.value['items'],key=lambda row:row['id'])))
    def test_missing_entry_retains_uncovered_item(self):
        self.value['entries']=[];r=self.review();self.assertEqual(r['assessment']['items'][0]['missing_roles'],['quality','service']);self.assertIsNone(r['review_scope_sha256']);self.assertIsNotNone(r['items_sha256'])
    def test_covered_but_blocked_never_ready(self):
        self.value['entries'][0]['blockers']=['fictional-pending'];r=self.review();self.assertFalse(r['assessment']['items'][0]['ready_for_manual_review']);self.assertEqual(r['assessment']['items'][0]['missing_roles'],[])
    def test_partial_coverage_reports_exact_missing_roles(self):
        self.value['entries'][0]['covered_roles']=['service'];self.assertEqual(self.review()['assessment']['items'][0]['missing_roles'],['quality'])
    def test_unknown_item_or_stale_revision_or_pin_withholds_all(self):
        for change in ({'item':'other'},{'item_revision':1},{'item_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['entries'][0].update(change);self.withheld(value)
    def test_two_ids_for_same_item_is_ambiguous(self):
        self.value['entries'].append(dict(self.value['entries'][0],id='other-entry'));self.withheld()
    def test_roles_blockers_normalize_sets(self):
        before=self.run_value();self.value['policy']['required_roles'].reverse();self.value['entries'][0]['covered_roles'].reverse();self.assertEqual(self.run_value()['review_scope_sha256'],before['review_scope_sha256'])
    def test_unknown_duplicate_and_oversized_roles_refuse(self):
        for roles in (['unknown'],['quality','quality'],['quality']*33):
            value=copy.deepcopy(self.value);value['entries'][0]['covered_roles']=roles;self.withheld(value)
        self.value['policy']['required_roles']=[]
        with self.assertRaises(t.Rejected):self.run_value()
    def test_item_revision_boolean_and_bad_hash_are_rejected(self):
        for update in ({'revision':True},{'artifact_sha256':'A'*64}):
            value=copy.deepcopy(self.value);value['items'][0].update(update);self.withheld(value)
    def test_new_item_requires_independent_coverage(self):
        self.value['items'].append(dict(self.value['items'][0],id='hvac-other'));r=self.review();self.assertEqual(len(r['assessment']['items']),2);self.assertFalse(r['assessment']['all_covered_and_unblocked'])
    def test_stage_is_a_declaration_not_a_completion_rule(self):
        self.value['entries'][0]['stage']='fictional-completed';self.value['entries'][0]['covered_roles']=[];self.assertFalse(self.review()['assessment']['items'][0]['ready_for_manual_review'])
