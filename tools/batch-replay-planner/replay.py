"""Describe explicit batch replay decisions without retries or side effects."""
import toolkit as t
import control_core as c


def plan(raw):
    value=t.decode(raw); t.fields(value,{'format','stream','expected','receipts'})
    t.require(value['format']=='outlands-batch-replay-v1','FORMAT_INVALID')
    expected,receipts,counts,issues=c.prepare(value)
    if not expected: c.problem(issues,'expected',0,'EMPTY_BATCH_COHORT')
    decisions=[]
    for key,(index,row) in receipts.items():
        # Uncertainty in supplied history is never treated as retry permission.
        if row['status']!='committed': c.problem(issues,'receipts',index,'HISTORY_'+row['status'].upper())
        if not c.clean(row['batch']): c.problem(issues,'receipts',index,'RECEIPT_COUNTS_REQUIRE_REVIEW')
    for key,(index,row) in expected.items():
        if key in receipts:
            ri,receipt=receipts[key]
            if not c.equal_batch(row,receipt['batch']): c.problem(issues,'receipts',ri,'BATCH_METADATA_MISMATCH')
            action='SKIP_ALREADY_COMMITTED'
        else: action='MANUAL_REVIEW_NEW_BATCH'
        decisions.append(dict(id=key,sequence=row['sequence'],decision=action,execution_authorized=False))
    result=c.report(raw,'outlands-batch-replay-plan-v1',counts,issues)
    result.update(plan=sorted(decisions,key=lambda row:(row['sequence'],row['id'])) if not issues else None,
                  plan_only=True,retry_performed=False,execution_authorized=False)
    return result


def main(argv=None): return c.cli('Plan explicit batch review/skip decisions; never retry uncertain outcomes.',plan,argv)
if __name__=='__main__': raise SystemExit(main())
