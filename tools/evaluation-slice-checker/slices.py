"""Check explicit evaluation slice coverage without selecting or scoring cases."""
from collections import defaultdict
import toolkit as t
import decision_core as c
import dataset_common as d

def case(row):return c.record(row,{'id','expected_label'},('id','expected_label'))

def slice_row(row):
    key,out=c.record(row,{'id','minimum_cases'},('id',));t.integer(row['minimum_cases'],1000);return key,out

def member(row):return c.record(row,{'id','case','slice'},('id','case','slice'))

def policy(value):
    t.fields(value,{'membership_mode','require_all_cases_assigned','minimum_covered_fraction'})
    t.require(value['membership_mode'] in ('exclusive','overlap'),'MEMBERSHIP_MODE_INVALID')
    t.require(type(value['require_all_cases_assigned']) is bool,'BOOLEAN_REQUIRED')
    _,minimum=c.decimal(value['minimum_covered_fraction']);return dict(value,minimum_covered_fraction=minimum)

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','taxonomy','cohort','slices','memberships','policy'})
    t.require(value['format']=='outlands-evaluation-slice-v1','FORMAT_INVALID')
    taxonomy=c.taxonomy(value['taxonomy']);rule=policy(value['policy']);counts={};issues=[]
    def parse_case(row):
        key,out=case(row);t.require(out['expected_label'] in taxonomy['labels'],'LABEL_UNKNOWN');return key,out
    cohort=d.collect(value['cohort'],parse_case,'cohort',counts,issues,True)
    slices=d.collect(value['slices'],slice_row,'slices',counts,issues,True)
    memberships=d.collect(value['memberships'],member,'memberships',counts,issues)
    for position,row in memberships.values():
        if row['case'] not in cohort:c.issue(issues,'memberships',position,'CASE_UNKNOWN')
        if row['slice'] not in slices:c.issue(issues,'memberships',position,'SLICE_UNKNOWN')
    qualified=not issues;coverage=None
    if qualified:
        pairs=defaultdict(list);by_case=defaultdict(set);by_slice=defaultdict(set)
        for key,(_,row) in sorted(memberships.items()):
            pairs[row['case'],row['slice']].append(key);by_case[row['case']].add(row['slice']);by_slice[row['slice']].add(row['case'])
        repeated=[dict(case=key[0],slice=key[1],membership_ids=ids) for key,ids in sorted(pairs.items()) if len(ids)>1]
        overlaps=[dict(case=key,slices=sorted(ids)) for key,ids in sorted(by_case.items()) if len(ids)>1]
        absent=sorted(set(cohort)-set(by_case));fraction=c.ratio(len(by_case),len(cohort));outcomes=[];failures=[]
        if repeated:failures.append('MEMBERSHIP_REPEATED')
        if overlaps and rule['membership_mode']=='exclusive':failures.append('EXCLUSIVE_MEMBERSHIP_OVERLAP')
        if absent and rule['require_all_cases_assigned']:failures.append('CASES_UNASSIGNED')
        if c.decimal(rule['minimum_covered_fraction'])[0]*len(cohort)>len(by_case):failures.append('MINIMUM_COVERAGE_NOT_MET')
        for key,(_,row) in sorted(slices.items()):
            selected=by_slice[key];labels={label:sum(cohort[i][1]['expected_label']==label for i in selected) for label in taxonomy['labels']}
            meets=len(selected)>=row['minimum_cases']
            if not meets:failures.append('SLICE_MINIMUM_NOT_MET')
            outcomes.append(dict(id=key,cases=len(selected),minimum_cases=row['minimum_cases'],label_counts=labels,meets_minimum=meets))
        for failure in sorted(set(failures)):c.issue(issues,'coverage',0,failure)
        coverage=dict(cohort_cases=len(cohort),covered_cases=len(by_case),covered_fraction=fraction,
            unique_memberships=len(pairs),repeated_memberships=repeated,overlapping_cases=overlaps,unassigned_cases=absent,
            slices=outcomes,failed_criteria=sorted(set(failures)),eligible_for_manual_comparison_review=not failures)
    return d.output(raw,'outlands-evaluation-slice-report-v1',counts,issues,coverage=coverage,
        cohort_sha256=c.cohort_pin(cohort) if qualified else None,taxonomy_sha256=c.pin(taxonomy) if qualified else None,
        policy_sha256=c.pin(rule) if qualified else None)

def main(argv=None):return c.cli('Check declared evaluation slice coverage; no model evaluation.',check,argv)
if __name__=='__main__':raise SystemExit(main())
