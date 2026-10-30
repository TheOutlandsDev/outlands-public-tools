"""Check declared case identities and derived expectation contracts without running tests."""
import toolkit as t
import decision_core as c
import test_core as r

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','cases','expectations'});t.require(v['format']=='outlands-test-case-manifest-v1','FORMAT_INVALID')
    counts={};issues=[];cases,expectations=r.select(v,counts,issues);qualified=not issues;assessment=None
    if qualified:
        expected={row['case']:row for _,row in expectations.values()};out=[]
        for key,(position,row) in sorted(cases.items()):
            exp=expected.get(key)
            if exp is None:c.issue(issues,'cases',position,'EXPECTATION_MISSING')
            out.append(dict(id=key,expectation_id=exp['id'] if exp else None,expectation_contract_present=exp is not None))
        assessment=dict(cases=out,all_expectation_contracts_present=not issues)
    return r.output(raw,'outlands-test-case-manifest-report-v1',counts,issues,qualified,assessment,dict(cases_sha256=c.cohort_pin(cases),expectations_sha256=c.cohort_pin(expectations)))

def main(argv=None):return c.cli('Check declared test case contracts; never execute tests.',check,argv)
if __name__=='__main__':raise SystemExit(main())
