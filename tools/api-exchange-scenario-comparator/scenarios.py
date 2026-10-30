"""Compare exact fictional exchange cohorts under two independently compiled operation contracts."""
import toolkit as t
import decision_core as c
import api_core as r
def request_case(row):return {key:value for key,value in row.items() if key not in ('operation_revision','operation_sha256')}
def response_case(row):return {key:value for key,value in row.items() if key!='request_sha256'}
def check(raw):
    v=t.decode(raw);t.fields(v,{'format','baseline_operations','candidate_operations','baseline_requests','candidate_requests','baseline_responses','candidate_responses'});t.require(v['format']=='outlands-api-exchange-scenarios-v1','FORMAT_INVALID');counts={};issues=[]
    baseline=r.exchange_context(v['baseline_operations'],v['baseline_requests'],v['baseline_responses'],'baseline',counts,issues);candidate=r.exchange_context(v['candidate_operations'],v['candidate_requests'],v['candidate_responses'],'candidate',counts,issues,False)
    for key in set(baseline['operations'])&set(candidate['operations']):
        left=baseline['operations'][key][1];right=candidate['operations'][key][1]
        if left['revision']==right['revision'] and left!=right:c.issue(issues,'operations',0,'OPERATION_IDENTITY_CONFLICT')
    qualified=not issues;assessment=None
    if qualified:
        rows=[]
        for key in sorted(set(baseline['requests'])|set(candidate['requests'])):
            left=baseline['requests'].get(key);right=candidate['requests'].get(key);a=b=None
            left_response=baseline['by_request'].get(key);right_response=candidate['by_request'].get(key)
            if left is None:state='candidate_only'
            elif right is None:state='candidate_missing'
            elif request_case(left[1])!=request_case(right[1]):state='request_scope_changed'
            elif left_response is None or right_response is None:state='response_coverage_missing'
            elif response_case(baseline['responses'][left_response][1])!=response_case(candidate['responses'][right_response][1]):state='response_scope_changed'
            else:
                a=r.summary(baseline,key);b=r.summary(candidate,key);state='unchanged' if (a['request_valid'],a['response_valid'])==(b['request_valid'],b['response_valid']) else 'validation_changed'
                if any(out[field] is False for out in (a,b) for field in ('request_expectation_met','response_expectation_met')):c.issue(issues,'scenarios',0,'EXPECTED_VALIDITY_MISMATCH')
            if state!='unchanged':c.issue(issues,'scenarios',0,state.upper())
            rows.append(dict(id=key,state=state,baseline=a,candidate=b))
        assessment=dict(scenarios=rows,all_declared_outcomes_equal=not issues,whole_api_compatibility_verified=False)
    pins={side+'_'+key+'_sha256':c.cohort_pin(scope[key]) for side,scope in [('baseline',baseline),('candidate',candidate)] for key in ('operations','requests','responses')}
    return r.output(raw,'outlands-api-exchange-scenarios-report-v1',counts,issues,qualified,assessment,pins)
def main(argv=None):return c.cli('Compare declared API exchange scenarios; no requests, servers or compatibility certification.',check,argv)
if __name__=='__main__':raise SystemExit(main())
