"""Check response observations, including explicitly declared error variants for invalid requests."""
import toolkit as t
import decision_core as c
import api_core as r
def check(raw):
    v=t.decode(raw);t.fields(v,{'format','operations','requests','responses'});t.require(v['format']=='outlands-api-responses-v1','FORMAT_INVALID');counts={};issues=[];scope=r.exchange_context(v['operations'],v['requests'],v['responses'],'',counts,issues);qualified=not issues;assessment=None
    if qualified:
        coverage=[]
        for key,(position,row) in sorted(scope['requests'].items()):
            if scope['request_results'][key]['expectation_met'] is False:c.issue(issues,'requests',position,'EXPECTED_VALIDITY_MISMATCH')
            response_id=scope['by_request'].get(key)
            if response_id is None:c.issue(issues,'coverage',0,'RESPONSE_MISSING')
            coverage.append(dict(request=key,response_id=response_id))
        for key,(position,row) in sorted(scope['responses'].items()):
            result=scope['response_results'][key]
            if not result['valid']:c.issue(issues,'responses',position,'RESPONSE_CONTRACT_VIOLATION')
            if result['expectation_met'] is False:c.issue(issues,'responses',position,'EXPECTED_VALIDITY_MISMATCH')
        assessment=dict(requests=list(scope['request_results'].values()),responses=list(scope['response_results'].values()),coverage=coverage,invalid_requests_can_have_declared_error_responses=True)
    return r.output(raw,'outlands-api-responses-report-v1',counts,issues,qualified,assessment,{key+'_sha256':c.cohort_pin(scope[key]) for key in ('operations','requests','responses')})
def main(argv=None):return c.cli('Check supplied API response observations; no service calls or proof of real responses.',check,argv)
if __name__=='__main__':raise SystemExit(main())
