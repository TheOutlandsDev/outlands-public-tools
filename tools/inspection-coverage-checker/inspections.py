"""Account for selected specimen/check records, separately from their declared outcomes."""
import toolkit as t
import quality_core as c

def required_check(row):return c.record(row,{'id','rule_id','rule_revision'},('id','rule_id'),(('rule_revision',1,10**6),))
def inspection(row):
    key,out=c.record(row,{'id','specimen_id','check_id','rule_id','rule_revision','source_sha256','outcome'},('id','specimen_id','check_id','rule_id'),(('rule_revision',1,10**6),))
    t.sha(row['source_sha256']);t.require(row['outcome'] in ('within_limits','outside_limits','not_evaluated'),'OUTCOME_INVALID');return key,out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','specimens','checks','records'})
    t.require(value['format']=='outlands-inspection-coverage-v1','FORMAT_INVALID')
    specimens,sc,issues=c.rows(value['specimens'],c.entity,'specimens')
    checks,cc,other=c.rows(value['checks'],required_check,'checks');issues+=other
    records,rc,other=c.rows(value['records'],inspection,'records');issues+=other
    if not specimens:c.issue(issues,'specimens',0,'EMPTY_SPECIMEN_COHORT')
    if not checks:c.issue(issues,'checks',0,'EMPTY_CHECK_COHORT')
    t.require(len(specimens)*len(checks)<=10000,'EXPECTED_PAIR_LIMIT')
    c.unique_pairs(records,('specimen_id','check_id'),'records',issues,'MULTIPLE_RECORDS_FOR_CHECK')
    for index,row in records.values():
        if row['specimen_id'] not in specimens:c.issue(issues,'records',index,'SPECIMEN_MISSING')
        if row['check_id'] not in checks:c.issue(issues,'records',index,'CHECK_MISSING')
        else:
            expected=checks[row['check_id']][1]
            if (row['rule_id'],row['rule_revision'])!=(expected['rule_id'],expected['rule_revision']):c.issue(issues,'records',index,'RULE_SELECTION_MISMATCH')
    coverage=summary=None
    if not issues:
        selected={(r['specimen_id'],r['check_id']):(i,r) for i,r in records.values()};coverage=[]
        summary=dict(expected_pairs=len(specimens)*len(checks),recorded_pairs=0,missing_pairs=0,within_limits=0,outside_limits=0,not_evaluated=0)
        for specimen in sorted(specimens):
            for check_id in sorted(checks):
                entry=selected.get((specimen,check_id));outcome=None
                if entry is None:summary['missing_pairs']+=1;c.issue(issues,'coverage',0,'INSPECTION_RECORD_MISSING')
                else:
                    index,row=entry;outcome=row['outcome'];summary['recorded_pairs']+=1;summary[outcome]+=1
                    if outcome!='within_limits':c.issue(issues,'records',index,'INSPECTION_OUTCOME_REQUIRES_REVIEW')
                coverage.append(dict(specimen_id=specimen,check_id=check_id,record_id=entry[1]['id'] if entry else None,
                                     record_present=entry is not None,outcome=outcome))
        summary.update(records_complete=summary['missing_pairs']==0,all_records_within_limits=summary['within_limits']==summary['expected_pairs'])
        t.require(summary['recorded_pairs']+summary['missing_pairs']==summary['expected_pairs'],'COVERAGE_ACCOUNTING_FAILED')
    result=c.base(raw,'outlands-inspection-coverage-review-v1',dict(specimens=sc,checks=cc,records=rc),issues)
    result.update(coverage=coverage,summary=summary,source_bytes_verified=False,measurement_results_recomputed=False,inspections_performed=False)
    return result

def main(argv=None):return c.cli('Check declared inspection coverage; no physical inspection or acceptance authority.',check,argv)
if __name__=='__main__':raise SystemExit(main())
