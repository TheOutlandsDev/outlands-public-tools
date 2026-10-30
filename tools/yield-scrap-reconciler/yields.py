"""Reconcile explicit per-specimen dispositions with exact cohort-denominator fractions."""
from collections import Counter
import toolkit as t
import quality_core as c

KINDS=('first_pass_good','reworked_good','scrap','pending')
def disposition(row):
    key,out=c.record(row,{'id','specimen_id','disposition'},('id','specimen_id'))
    t.require(row['disposition'] in KINDS,'DISPOSITION_INVALID');return key,out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','cohort','dispositions'})
    t.require(value['format']=='outlands-yield-scrap-v1','FORMAT_INVALID')
    cohort,cc,issues=c.rows(value['cohort'],c.entity,'cohort')
    dispositions,dc,other=c.rows(value['dispositions'],disposition,'dispositions');issues+=other
    if not cohort:c.issue(issues,'cohort',0,'EMPTY_COHORT')
    c.unique_pairs(dispositions,('specimen_id',),'dispositions',issues,'MULTIPLE_DISPOSITIONS')
    seen=set()
    for index,row in dispositions.values():
        seen.add(row['specimen_id'])
        if row['specimen_id'] not in cohort:c.issue(issues,'dispositions',index,'SPECIMEN_MISSING')
    for key,(index,_) in cohort.items():
        if key not in seen:c.issue(issues,'cohort',index,'DISPOSITION_MISSING')
    summary=fractions=None
    if not issues:
        counts=Counter(r['disposition'] for _,r in dispositions.values());n=len(cohort)
        summary={kind:counts[kind] for kind in KINDS};summary.update(cohort=n,good=counts['first_pass_good']+counts['reworked_good'],closed_cohort=counts['pending']==0)
        t.require(sum(summary[k] for k in KINDS)==n,'DISPOSITION_ACCOUNTING_FAILED')
        fractions={name:c.ratio(number,n) for name,number in [('first_pass_yield',counts['first_pass_good']),('eventual_yield',summary['good']),('scrap_fraction',counts['scrap']),('pending_fraction',counts['pending'])]}
        if counts['pending']:c.issue(issues,'cohort',0,'COHORT_NOT_CLOSED')
    result=c.base(raw,'outlands-yield-scrap-review-v1',dict(cohort=cc,dispositions=dc),issues)
    result.update(summary=summary,fractions=fractions,quality_target_evaluated=False,inspection_coverage_verified=False,
                  physical_cohort_completeness_verified=False,dispositions_changed=False)
    return result

def main(argv=None):return c.cli('Reconcile supplied specimen dispositions; no quality target or production approval.',check,argv)
if __name__=='__main__':raise SystemExit(main())
