"""Check a bounded proposed checkpoint window against committed receipt declarations."""
import toolkit as t
import control_core as c


def check(raw):
    value=t.decode(raw); t.fields(value,{'format','stream','previous','proposed','expected','receipts'})
    t.require(value['format']=='outlands-checkpoint-progression-v1','FORMAT_INVALID')
    previous=t.integer(value['previous'],10**9); proposed=t.integer(value['proposed'],10**9)
    t.require(previous<=proposed and proposed-previous<=1000,'CHECKPOINT_WINDOW_INVALID')
    expected,receipts,counts,issues=c.prepare(value)
    positions={row['sequence'] for _,row in expected.values()}
    for sequence in range(previous+1,proposed+1):
        if sequence not in positions: c.problem(issues,'expected',0,'CHECKPOINT_GAP')
    for index,row in expected.values():
        if not previous<row['sequence']<=proposed: c.problem(issues,'expected',index,'BATCH_OUTSIDE_CHECKPOINT_WINDOW')
    matched,missing,orphan=c.reconcile(expected,receipts,issues)
    counts.update(resolved_committed_batches=len(matched),missing_receipts=missing,unexpected_receipts=orphan)
    result=c.report(raw,'outlands-checkpoint-progression-review-v1',counts,issues)
    result.update(previous=previous,proposed=proposed,suggested_checkpoint=proposed if not issues else None,
                  advancement_eligible_for_explicit_review=not issues and proposed>previous,
                  previous_checkpoint_authority_verified=False,checkpoint_written=False,plan_only=True)
    return result


def main(argv=None): return c.cli('Check contiguous declared committed coverage before manual checkpoint review.',check,argv)
if __name__=='__main__': raise SystemExit(main())
