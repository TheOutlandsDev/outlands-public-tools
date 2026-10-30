import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import recovery as app
import health_core as r

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
        for key in ['components_sha256', 'incidents_sha256', 'checks_sha256', 'evidence_sha256', 'policy_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('observations_independently_verified','artifact_bytes_verified','actual_health_verified','notifications_sent','alerts_suppressed','recovery_authorized','recovery_performed','records_changed','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['components'], ['incidents'], ['checks'], ['evidence']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['components_sha256', 'incidents_sha256', 'checks_sha256', 'evidence_sha256', 'policy_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['components'], ['incidents'], ['checks'], ['evidence']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['components'], ['incidents'], ['checks'], ['evidence']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['components'], ['incidents'], ['checks'], ['evidence']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['components'], ['incidents'], ['checks'], ['evidence']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['components'], ['incidents'], ['checks'], ['evidence']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['components'], ['incidents'], ['checks'], ['evidence']][0]).clear();self.withheld(value)

    def test_known_all_role_checks_ready_without_recovery_authority(self):
        out=self.run_value();row=out['assessment']['incidents'][0];self.assertEqual(row['missing_roles'],[]);self.assertTrue(row['ready_for_manual_recovery_review']);self.assertEqual(len(row['checks']),3);self.assertFalse(out['recovery_authorized'])
    def test_missing_check_and_evidence_are_distinct_blockers(self):
        self.value['checks'].pop();self.value['evidence'].pop();self.value['evidence'].pop();row=self.review()['assessment']['incidents'][0];self.assertEqual(row['missing_roles'],['restore-drill']);self.assertIn('CHECK_EVIDENCE_MISSING',row['checks'][1]['failed_criteria'])
    def test_unknown_and_failed_evidence_never_pass_readiness(self):
        for outcome in ('fail','unknown'):
            value=copy.deepcopy(self.value);value['evidence'][0]['outcome']=outcome;self.assertFalse(self.review(value)['assessment']['incidents'][0]['ready_for_manual_recovery_review'])
    def test_inclusive_age_boundary_future_and_stale_evidence(self):
        self.value['as_of']=30;self.assertEqual(self.run_value()['status'],'PASS');self.value['as_of']=31;self.assertIn('EVIDENCE_STALE',self.review()['assessment']['incidents'][0]['checks'][0]['failed_criteria']);self.value['as_of']=19;row=self.review()['assessment']['incidents'][0]['checks'][0];self.assertIsNone(row['age']);self.assertIn('EVIDENCE_FUTURE',row['failed_criteria'])
    def test_no_latest_or_best_check_or_evidence_selection(self):
        for side in ('checks','evidence'):
            value=copy.deepcopy(self.value);value[side].append(dict(value[side][0],id='alias'));self.withheld(value)
    def test_stale_incident_check_and_policy_pins_withhold(self):
        for side,field in [('checks','incident_sha256'),('evidence','check_sha256'),('evidence','policy_sha256')]:
            value=copy.deepcopy(self.value);value[side][0][field]='0'*64;self.withheld(value)
    def test_unknown_check_reference_is_not_discovered(self):
        self.value['evidence'][0]['check']='unknown';self.withheld()
    def test_policy_role_set_normalization_preserves_scope(self):
        before=self.run_value()['qualified_scope_sha256'];self.value['policy']['required_roles'].reverse();self.assertEqual(self.run_value()['qualified_scope_sha256'],before)
    def test_policy_revision_change_requires_exact_evidence_rebinding(self):
        self.value['policy']['revision']=2;self.withheld()
    def test_empty_roles_and_boolean_asof_are_fixed_refusals(self):
        value=copy.deepcopy(self.value);value['policy']['required_roles']=[]
        with self.assertRaises(t.Rejected):self.run_value(value)
        self.value['as_of']=True
        with self.assertRaises(t.Rejected):self.run_value()
    def test_empty_checks_and_evidence_retain_all_required_roles(self):
        self.value['checks']=[];self.value['evidence']=[];row=self.review()['assessment']['incidents'][0];self.assertEqual(row['missing_roles'],['component-health','incident-resolution','restore-drill'])
    def test_unknown_roles_and_invalid_evidence_shapes_are_rejected(self):
        value=copy.deepcopy(self.value);value['checks'][0]['role']='unknown';self.withheld(value)
        for change in ({'observed_at':True},{'artifact_sha256':'A'*64},{'outcome':'verified'}):
            value=copy.deepcopy(self.value);value['evidence'][0].update(change);self.withheld(value)
    def test_role_expansion_boundary_keeps_reports_bounded_and_refuses_larger_scope(self):
        incident=self.value['incidents'][0];self.value['incidents']=[dict(incident,id='incident-'+str(n).zfill(4)) for n in range(128)];self.value['policy']['required_roles']=['role-'+str(n).zfill(2)+'-'+'x'*40 for n in range(32)];self.value['checks']=[];self.value['evidence']=[]
        out=self.review();self.assertEqual(len(out['assessment']['incidents']),128);self.assertLess(len(t.encode(out)),8*1024*1024)
        self.value['incidents'].append(dict(incident,id='incident-over-boundary'))
        with self.assertRaisesRegex(t.Rejected,'^RECOVERY_SCOPE_LIMIT$'):self.run_value()
