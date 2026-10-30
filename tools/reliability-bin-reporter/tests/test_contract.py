import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import bins as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['metrics']);return r
    def test_positive_and_truth_boundaries(self):
        r=self.run_value();self.assertEqual(r['status'],'PASS')
        for key in ('probability_interpretation_verified','label_truth_verified','cohort_independence_verified','calibration_established','model_fitted','model_updated','inference_performed','artifact_bytes_verified','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(r[key],False)
    def test_outer_format_unknown_fields_and_duplicate_keys_refuse(self):
        for v in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(v)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_row_order_preserves_normalized_pins(self):
        before=self.run_value()
        for path in [['cohort'], ['predictions'], ['outcomes'], ['bins']]:
            rows=self.value
            for key in path:rows=rows[key]
            rows.reverse()
        after=self.run_value()
        for key in ['cohort_sha256', 'contract_sha256', 'bins_sha256', 'report_sha256']:self.assertEqual(before[key],after[key])
    def test_identical_snapshots_count_once_with_complete_accounting(self):
        for path in [['cohort'], ['predictions'], ['outcomes'], ['bins']]:
            value=copy.deepcopy(self.value);rows=value
            for key in path:rows=rows[key]
            rows.append(copy.deepcopy(rows[0]));r=self.run_value(value);self.assertEqual(r['status'],'PASS')
            side=path[-1] if len(path)==1 else path[0]+'_points';counts=r['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_rejected_rows_withhold_qualified_result_and_omit_values(self):
        for path in [['cohort'], ['predictions'], ['outcomes'], ['bins']]:
            value=copy.deepcopy(self.value);rows=value
            for key in path:rows=rows[key]
            rows.append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_list_bounds_and_nonlist_refuse(self):
        for path in [['cohort'], ['predictions'], ['outcomes'], ['bins']]:
            for rows in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);selected=value
                for key in path[:-1]:selected=selected[key]
                selected[path[-1]]=rows
                with self.assertRaises(t.Rejected):self.run_value(value)

    def test_known_bin_memberships_means_rates_and_weighted_gap(self):
        r=self.run_value();a=r['metrics'];self.assertEqual([b['cases'] for b in a['bins']],[1,1,2])
        self.assertEqual([b['mean_probability']['exact_fraction'] for b in a['bins']],['1/4','1/2','7/8'])
        self.assertEqual([b['positive_fraction']['exact_fraction'] for b in a['bins']],['0/1','1/1','1/1'])
        self.assertEqual([b['signed_gap']['exact_fraction'] for b in a['bins']],['-1/4','1/2','1/8']);self.assertEqual(a['weighted_absolute_bin_gap']['exact_fraction'],'1/4')
        self.assertEqual([b['case_ids'] for b in a['bins']],[['case-alpha'],['case-charlie'],['case-bravo','case-delta']])
    def test_zero_and_one_and_internal_edges_have_exact_membership(self):
        self.value['predictions'][0]['probability']='0';r=self.run_value();self.assertEqual(r['metrics']['cohort_cases'],4);self.assertEqual(sum(x['cases'] for x in r['metrics']['bins']),4)
        self.assertIn('case-charlie',r['metrics']['bins'][1]['case_ids']);self.assertIn('case-bravo',r['metrics']['bins'][2]['case_ids']);self.assertIn('case-delta',r['metrics']['bins'][2]['case_ids'])
    def test_empty_bins_are_visible_without_zero_denominators_or_quality_claims(self):
        self.value['bins']=[dict(id='quarter-'+str(i),lower=a,upper=b) for i,(a,b) in enumerate(zip(['0','0.25','0.5','0.75'],['0.25','0.5','0.75','1']))]
        r=self.run_value();self.assertEqual(r['status'],'PASS');self.assertEqual(r['metrics']['empty_bins'],['quarter-0']);self.assertIsNone(r['metrics']['bins'][0]['mean_probability']);self.assertIsNone(r['metrics']['bins'][0]['positive_fraction']);self.assertFalse(r['calibration_established'])
    def test_gap_exposes_missing_domain_and_withholds_all_bin_metrics(self):
        self.value['bins'][1]['lower']='0.6';r=self.review();self.assertIsNone(r['metrics']);self.assertIsNone(r['report_sha256']);self.assertEqual(r['bin_assessment']['gaps'][0]['lower']['exact_fraction'],'1/2')
        self.assertTrue(r['assessment']['complete']);self.assertIsNotNone(r['bins_sha256'])
    def test_overlap_never_double_counts_assignments(self):
        self.value['bins'][1]['lower']='0.4';r=self.review();self.assertIsNone(r['metrics']);self.assertTrue(r['bin_assessment']['overlaps'])
    def test_nested_overlaps_do_not_create_false_union_gaps(self):
        self.value['bins']=[dict(id='wide',lower='0',upper='0.9'),dict(id='nested',lower='0.2',upper='0.3'),dict(id='tail',lower='0.4',upper='1')]
        a=self.review()['bin_assessment'];self.assertEqual(a['gaps'],[]);self.assertEqual(len(a['overlaps']),2)
    def test_nonpositive_width_withholds_assignment_and_retains_diagnostics(self):
        for lower,upper in [('0.5','0.5'),('0.8','0.7')]:
            self.value['bins'][1].update(lower=lower,upper=upper);r=self.review();self.assertIsNone(r['metrics']);self.assertFalse(r['bin_assessment']['valid_partition'])
    def test_single_bin_is_descriptive_and_depends_on_declared_partition(self):
        self.value['bins']=[dict(id='all',lower='0',upper='1')];r=self.run_value()
        self.assertEqual(r['metrics']['weighted_absolute_bin_gap']['exact_fraction'],'1/8');self.assertFalse(r['calibration_established'])
    def test_missing_or_unknown_evidence_never_produces_partial_bin_metrics(self):
        self.value['outcomes'][0]['label']=None;r=self.review();self.assertIsNone(r['metrics']);self.assertTrue(r['bin_assessment']['valid_partition']);self.assertFalse(r['assessment']['complete'])
    def test_distinct_ids_with_equal_bin_ranges_are_overlap_not_deduplicated(self):
        self.value['bins'].append(dict(self.value['bins'][0],id='duplicate-range'));r=self.review();self.assertEqual(r['counts']['bins']['accepted_records'],4);self.assertIsNone(r['metrics'])
    def test_bad_bin_decimals_reject_rows_and_bin_pin(self):
        for lower in ('-0.1','1.1','NaN',True):
            value=copy.deepcopy(self.value);value['bins'][0]['lower']=lower;r=self.withheld(value);self.assertIsNone(r['bins_sha256']);self.assertIsNone(r['bin_assessment'])
    def test_fraction_zero_and_one_boundaries_normalize(self):
        expected=self.run_value()['report_sha256'];self.value['bins'][0]['lower']='-0.000';self.value['bins'][2]['upper']='1.000000';self.assertEqual(self.run_value()['report_sha256'],expected)
    def test_empty_bins_and_raw_bin_limit_refuse_or_withhold(self):
        self.value['bins']=[];r=self.review();self.assertIsNone(r['metrics']);self.assertIsNone(r['bin_assessment'])
        self.value['bins']=[{}]*33
        with self.assertRaises(t.Rejected):self.run_value()
    def test_invalid_cohort_keeps_independent_bin_contract_but_no_metrics(self):
        self.value['predictions'][0]['case']='missing';r=self.review();self.assertIsNone(r['assessment']);self.assertIsNone(r['metrics']);self.assertTrue(r['bin_assessment']['valid_partition']);self.assertIsNone(r['cohort_sha256'])
