"""Installed four-tool fictional declaration exercise; no test execution or artifact I/O."""
import copy
import hashlib
import json
from outlands_test_case_manifest_checker.cases import check as cases
from outlands_test_run_coverage_checker.runs import check as coverage
from outlands_regression_comparison_reporter.regressions import check as compare
from outlands_evidence_completeness_checker.evidence import check as evidence

def raw(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):
    return hashlib.sha256(raw(value)).hexdigest()
def bundle(identifier, mismatch=False, revision=1):
    expected=dict(exit_code=0,stdout_sha256=pin({'fictional_flow':'acceptable'}),stderr_sha256=hashlib.sha256(b'').hexdigest())
    case=dict(id='fictional-flow',revision=revision,definition_sha256=pin({'check':'fictional flow declaration'}),input_sha256=pin({'flow':12}),expectation_sha256=pin(expected))
    expectation=dict(id='expect-flow',case=case['id'],case_revision=revision,case_sha256=pin(case),expected_exit=expected['exit_code'],stdout_sha256=expected['stdout_sha256'],stderr_sha256=expected['stderr_sha256'])
    run=dict(id=identifier,revision=1,subject_sha256=pin({'subject':identifier}),cases_sha256=pin([case]),expectations_sha256=pin([expectation]))
    result=dict(id='result-flow',run=identifier,run_revision=1,run_sha256=pin(run),case=case['id'],case_revision=revision,case_sha256=pin(case),state='completed',observed_exit=0,stdout_sha256=pin({'fictional_flow':'low'}) if mismatch else expected['stdout_sha256'],stderr_sha256=expected['stderr_sha256'],output_complete=True)
    return dict(cases=[case],expectations=[expectation],run=run,results=[result])

def main():
    baseline=bundle('fictional-baseline');candidate=bundle('fictional-candidate',True)
    manifest=cases(raw(dict(format='outlands-test-case-manifest-v1',cases=baseline['cases'],expectations=baseline['expectations'])))
    assert manifest['status']=='PASS'
    passing=coverage(raw(dict(format='outlands-test-run-coverage-v1',**baseline)))
    failing=coverage(raw(dict(format='outlands-test-run-coverage-v1',**candidate)))
    assert passing['assessment']['matched_cases']==1
    assert failing['status']=='REVIEW_REQUIRED' and failing['assessment']['matched_cases']==0
    comparison=compare(raw(dict(format='outlands-regression-comparison-v1',baseline=baseline,candidate=candidate)))
    assert comparison['assessment']['classification_counts']['regression']==1
    rule=dict(id='fictional-evidence-policy',revision=1,required_roles=['capture'])
    result=candidate['results'][0];case=candidate['cases'][0];run=candidate['run']
    artifact=dict(id='fictional-capture',run=run['id'],run_revision=1,run_sha256=pin(run),case=case['id'],case_revision=case['revision'],case_sha256=pin(case),result=result['id'],result_sha256=pin(result),policy_sha256=pin(rule),role='capture',content_sha256=pin({'fictional':'failure evidence'}),complete=True)
    scope=dict(format='outlands-evidence-completeness-v1',**candidate,policy=rule,artifacts=[artifact])
    complete=evidence(raw(scope))
    assert complete['status']=='PASS' and complete['assessment']['cases'][0]['observation']['matched'] is False
    assert complete['assessment']['test_outcomes_upgraded'] is False
    missing=copy.deepcopy(scope);missing['artifacts']=[]
    missing_report=evidence(raw(missing))
    assert missing_report['status']=='REVIEW_REQUIRED' and missing_report['assessment']['cases'][0]['missing_roles']==['capture']
    changed=compare(raw(dict(format='outlands-regression-comparison-v1',baseline=baseline,candidate=bundle('fictional-revised',False,2))))
    assert changed['assessment']['classification_counts']['incomparable_contract']==1
    stale=copy.deepcopy(candidate);stale['results'][0]['run_sha256']='0'*64
    withheld=coverage(raw(dict(format='outlands-test-run-coverage-v1',**stale)))
    assert withheld['status']=='REVIEW_REQUIRED' and withheld['assessment'] is None
    print(json.dumps(dict(status='PASS',manifest=manifest['status'],baseline=passing['status'],candidate=failing['status'],regressions=1,complete_failure_evidence=complete['status'],missing_evidence=missing_report['status'],changed_contract='incomparable_contract',stale_binding='assessment withheld'),sort_keys=True))

if __name__=='__main__':
    main()
