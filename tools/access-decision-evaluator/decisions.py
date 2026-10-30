"""Evaluate bounded fictional request declarations with default deny and deny precedence."""
import toolkit as t
import decision_core as c
import access_core as r

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','policy','requests'});t.require(v['format']=='outlands-access-decisions-v1','FORMAT_INVALID');counts={};issues=[];context=r.policy(v['policy'],'policy',counts,issues);requests=r.requests(v['requests'],context,'requests',counts,issues);qualified=not issues;assessment=None
    if qualified:
        rows=[]
        for key,(position,row) in sorted(requests.items()):
            result=r.decide(context,row)
            if result['expectation_met'] is False:c.issue(issues,'requests',position,'EXPECTED_DECISION_MISMATCH')
            rows.append(dict(id=key,**result))
        assessment=dict(requests=rows,default_decision='deny',deny_precedence=True,request_completeness_verified=False)
    return r.output(raw,'outlands-access-decisions-report-v1',counts,issues,qualified,assessment,dict(policy_sha256=c.pin(context['value']),requests_sha256=c.cohort_pin(requests)))

def main(argv=None):return c.cli('Evaluate explicit access declarations; no real access decision or enforcement.',check,argv)
if __name__=='__main__':raise SystemExit(main())
