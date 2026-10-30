"""Validate supplied request declarations against exact selected operation snapshots."""
import toolkit as t
import decision_core as c
import api_core as r
def check(raw):
    v=t.decode(raw);t.fields(v,{'format','operations','requests'});t.require(v['format']=='outlands-api-requests-v1','FORMAT_INVALID');counts={};issues=[];operations=r.operation_scope(v['operations'],'operations',counts,issues);requests,budget=r.request_scope(v['requests'],operations,'requests',counts,issues);qualified=not issues;assessment=None
    if qualified:
        rows=[]
        for key,(position,row) in sorted(requests.items()):
            result=r.assess_request(row,operations[row['operation']][1]);rows.append(result)
            if not result['valid']:c.issue(issues,'requests',position,'REQUEST_CONTRACT_VIOLATION')
            if result['expectation_met'] is False:c.issue(issues,'requests',position,'EXPECTED_VALIDITY_MISMATCH')
        assessment=dict(requests=rows,defaults_inserted=False)
    return r.output(raw,'outlands-api-requests-report-v1',counts,issues,qualified,assessment,dict(operations_sha256=c.cohort_pin(operations),requests_sha256=c.cohort_pin(requests)))
def main(argv=None):return c.cli('Check supplied API requests; no network calls, coercion or authentication.',check,argv)
if __name__=='__main__':raise SystemExit(main())
