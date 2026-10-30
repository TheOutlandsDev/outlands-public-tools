"""Compare exact declared request scenarios without silently treating lost coverage as improvement."""
import toolkit as t
import decision_core as c
import access_core as r

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','baseline','candidate','baseline_requests','candidate_requests'});t.require(v['format']=='outlands-access-policy-scenarios-v1','FORMAT_INVALID');counts={};issues=[]
    baseline=r.policy(v['baseline'],'baseline',counts,issues);candidate=r.policy(v['candidate'],'candidate',counts,issues)
    before=r.requests(v['baseline_requests'],baseline,'baseline_requests',counts,issues);after=r.requests(v['candidate_requests'],candidate,'candidate_requests',counts,issues,False)
    if (baseline['value']['id'],baseline['value']['revision'])==(candidate['value']['id'],candidate['value']['revision']) and c.pin(baseline['value'])!=c.pin(candidate['value']):c.issue(issues,'policies',0,'POLICY_IDENTITY_CONFLICT')
    qualified=not issues;assessment=None
    if qualified:
        out=[]
        for key in sorted(set(before)|set(after)):
            left=before.get(key);right=after.get(key);a=b=None
            if left is None:state='candidate_only'
            elif right is None:state='candidate_missing'
            elif left[1]!=right[1]:state='request_scope_changed'
            else:
                a=r.decide(baseline,left[1]);b=r.decide(candidate,right[1]);state='unchanged' if a['decision']==b['decision'] else 'decision_changed'
                if a['expectation_met'] is False:c.issue(issues,'baseline_requests',left[0],'EXPECTED_DECISION_MISMATCH')
                if b['expectation_met'] is False:c.issue(issues,'candidate_requests',right[0],'EXPECTED_DECISION_MISMATCH')
            if state!='unchanged':c.issue(issues,'requests',0,state.upper())
            out.append(dict(id=key,state=state,baseline=a,candidate=b))
        assessment=dict(requests=out,all_declared_scenarios_equal=not issues,security_improvement_inferred=False)
    return r.output(raw,'outlands-access-policy-scenarios-report-v1',counts,issues,qualified,assessment,dict(baseline_sha256=c.pin(baseline['value']),candidate_sha256=c.pin(candidate['value']),baseline_requests_sha256=c.cohort_pin(before),candidate_requests_sha256=c.cohort_pin(after)))

def main(argv=None):return c.cli('Compare explicit access policy scenarios; no live policy probing or deployment.',check,argv)
if __name__=='__main__':raise SystemExit(main())
