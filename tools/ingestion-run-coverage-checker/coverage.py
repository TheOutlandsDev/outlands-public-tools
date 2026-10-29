"""Reconcile a declared batch cohort and row totals without importing records."""
import toolkit as t
import control_core as c


def check(raw):
    value=t.decode(raw); t.fields(value,{'format','stream','expected','receipts'})
    t.require(value['format']=='outlands-ingestion-run-coverage-v1','FORMAT_INVALID')
    expected,receipts,counts,issues=c.prepare(value)
    if not expected: c.problem(issues,'expected',0,'EMPTY_BATCH_COHORT')
    matched,missing,orphan=c.reconcile(expected,receipts,issues)
    counts.update(resolved_committed_batches=len(matched),missing_receipts=missing,unexpected_receipts=orphan)
    totals={key:sum(row['counts'][key] for row in matched) for key in sorted(c.COUNT_FIELDS)} if not issues else None
    result=c.report(raw,'outlands-ingestion-run-coverage-review-v1',counts,issues)
    result.update(declared_totals=totals,cohort_complete=not issues,actual_store_contents_verified=False)
    return result


def main(argv=None): return c.cli('Reconcile expected batch declarations with exact selected committed receipts.',check,argv)
if __name__=='__main__': raise SystemExit(main())
