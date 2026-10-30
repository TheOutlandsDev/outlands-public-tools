import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import corrections as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment'])
        for key in ['review_scope_sha256', 'snapshots_sha256', 'corrections_sha256']:self.assertIsNone(r[key])
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
        for key in ['snapshots', 'corrections']:self.value[key].reverse()
        after=self.run_value()
        for key in ['review_scope_sha256', 'snapshots_sha256', 'corrections_sha256']:self.assertEqual(before[key],after[key])
    def test_identical_identity_snapshots_count_once(self):
        for key in ['snapshots', 'corrections']:
            if not self.value[key]:continue
            value=copy.deepcopy(self.value);value[key].append(copy.deepcopy(value[key][0]));r=self.run_value(value)
            self.assertEqual(r['status'],'PASS');counts=r['counts'][key];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_bad_rows_withhold_and_omit_supplied_values(self):
        for key in ['snapshots', 'corrections']:
            value=copy.deepcopy(self.value);value[key].append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_list_bounds_and_nonlist_are_fixed_refusals(self):
        for key in ['snapshots', 'corrections']:
            for rows in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);value[key]=rows
                with self.assertRaises(t.Rejected):self.run_value(value)

    def test_conflicting_identity_groups_exclude_every_member(self):
        for side in ['snapshots', 'corrections']:
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
        self.value[['snapshots', 'corrections'][0]]=[];self.withheld()
    def test_unknown_fields_and_nonobjects_are_rejected_rows(self):
        for side in ['snapshots', 'corrections']:
            value=copy.deepcopy(self.value);value[side].append(None);self.withheld(value)
            if value[side][:-1]:
                value=copy.deepcopy(self.value);value[side][0]['extra']=0;self.withheld(value)

    def repin(self):
        by_id={row['id']:row for row in self.value['snapshots']}
        for row in self.value['corrections']:
            for field in ('before','after'):
                if row[field] in by_id:row[field+'_sha256']=pin(by_id[row[field]]);row[field+'_revision']=by_id[row[field]]['revision']
    def test_known_complete_history(self):
        r=self.run_value();self.assertEqual(r['assessment']['records'],[dict(record='hvac-service-spec',snapshot_ids=['service-v1','service-v2'],correction_ids=['correction-one'],complete_declared_history=True,failed_criteria=[])])
    def test_missing_parent_retains_diagnostics_without_qualification(self):
        self.value['corrections']=[];r=self.review();self.assertEqual(r['assessment']['records'][0]['failed_criteria'],['PARENT_CORRECTION_MISSING']);self.assertIsNone(r['review_scope_sha256'])
    def test_revision_gap_and_incomplete_root(self):
        self.value['snapshots']=self.value['snapshots'][1:];self.value['corrections']=[];r=self.review();self.assertEqual(r['assessment']['records'][0]['failed_criteria'],['PARENT_CORRECTION_MISSING','REVISION_GAP'])
    def test_same_record_revision_alias_is_ambiguous(self):
        self.value['snapshots'].append(dict(self.value['snapshots'][0],id='alias'));self.withheld()
    def test_cross_record_and_unchanged_artifact_refuse(self):
        for change in ({'record':'other'},{'artifact_sha256':self.value['snapshots'][0]['artifact_sha256']}):
            original=copy.deepcopy(self.value);self.value['snapshots'][1].update(change);self.repin();self.withheld();self.value=original
    def test_non_successor_and_reverse_links_withhold(self):
        self.value['snapshots'][1]['revision']=3;self.repin();self.withheld()
    def test_full_snapshot_pin_includes_identity_record_revision_and_artifact(self):
        self.value['snapshots'][0]['artifact_sha256']='1'*64;self.withheld()
    def test_fork_or_duplicate_parent_claim_is_not_selected_latest(self):
        self.value['corrections'].append(dict(self.value['corrections'][0],id='second-change'));self.withheld()
    def test_self_reference_never_counts_as_lineage(self):
        row=self.value['corrections'][0];row.update(after=row['before'],after_revision=row['before_revision'],after_sha256=row['before_sha256']);self.withheld()
    def test_unknown_parent_withholds(self):
        self.value['corrections'][0]['before']='missing';self.withheld()
    def test_independent_revision_one_needs_no_correction(self):
        self.value['snapshots']=self.value['snapshots'][:1];self.value['corrections']=[];self.assertEqual(self.run_value()['status'],'PASS')
    def test_two_complete_records_are_not_joined(self):
        self.value['snapshots'].append(dict(id='other-v1',record='hvac-other',revision=1,artifact_sha256='2'*64));r=self.run_value();self.assertEqual(r['status'],'PASS');self.assertEqual(len(r['assessment']['records']),2)
    def test_explicit_successor_can_revert_an_older_artifact(self):
        third=dict(self.value['snapshots'][0],id='service-v3',revision=3);self.value['snapshots'].append(third)
        edge=self.value['corrections'][0];self.value['corrections'].append(dict(id='reversion',before=edge['after'],before_revision=2,before_sha256=edge['after_sha256'],after=third['id'],after_revision=3,after_sha256=pin(third)))
        self.assertEqual(self.run_value()['status'],'PASS')
