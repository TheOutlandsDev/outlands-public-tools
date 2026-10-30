"""Reconcile one selected declared result per planned case; never execute tests."""
import toolkit as t
import decision_core as c
import test_core as r

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','cases','expectations','run','results'});t.require(v['format']=='outlands-test-run-coverage-v1','FORMAT_INVALID')
    counts={};issues=[];b=r.bundle({k:value for k,value in v.items() if k!='format'},counts,issues);qualified=not issues;assessment=None
    if qualified:
        outcomes=r.evaluate(b)
        for row in outcomes:
            for code in row['failed_criteria']:c.issue(issues,'cases',b['cases'][row['id']][0],code)
        assessment=dict(cases=outcomes,planned_cases=len(outcomes),completed_cases=sum(row['state']=='completed' for row in outcomes),
            matched_cases=sum(row['matched'] is True for row in outcomes),all_cases_complete_and_matched=not issues)
    return r.output(raw,'outlands-test-run-coverage-report-v1',counts,issues,qualified,assessment,r.bundle_pins(b))

def main(argv=None):return c.cli('Check declared run coverage and exact expected results; never execute tests.',check,argv)
if __name__=='__main__':raise SystemExit(main())
