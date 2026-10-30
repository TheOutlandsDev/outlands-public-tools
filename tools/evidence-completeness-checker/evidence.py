"""Check full declared evidence bindings, independently of a test's matching verdict."""
import toolkit as t
import decision_core as c
import test_core as r

def policy(value):
    _,out=c.record(value,{'id','revision','required_roles'},('id',),('revision',));out['required_roles']=c.tags(value['required_roles'],1);return out

def artifact(row,roles):
    key,out=c.record(row,{'id','run','run_revision','run_sha256','case','case_revision','case_sha256','result','result_sha256','policy_sha256','role','content_sha256','complete'},('id','run','case','result','role'),('run_revision','case_revision'))
    for field in ('run_sha256','case_sha256','result_sha256','policy_sha256','content_sha256'):t.sha(row[field])
    t.require(row['role'] in roles,'ROLE_UNKNOWN');t.require(type(row['complete']) is bool,'COMPLETENESS_INVALID');return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','cases','expectations','run','results','policy','artifacts'});t.require(v['format']=='outlands-evidence-completeness-v1','FORMAT_INVALID')
    counts={};issues=[];b=r.bundle({k:v[k] for k in ('cases','expectations','run','results')},counts,issues);rule=policy(v['policy'])
    artifacts=r.collect(v['artifacts'],lambda row:artifact(row,rule['required_roles']),'artifacts',counts,issues,False)
    r.slots(artifacts,lambda row:(row['case'],row['role']),'artifacts',issues)
    for position,row in artifacts.values():
        r.reference(row,'case',b['cases'],'artifacts',position,issues)
        if row['run']!=b['run']['id'] or row['run_revision']!=b['run']['revision'] or row['run_sha256']!=c.pin(b['run']):c.issue(issues,'artifacts',position,'RUN_SNAPSHOT_MISMATCH')
        if row['policy_sha256']!=c.pin(rule):c.issue(issues,'artifacts',position,'POLICY_PIN_MISMATCH')
        result=b['results'].get(row['result'])
        if result is None:c.issue(issues,'artifacts',position,'RESULT_UNKNOWN')
        elif row['result_sha256']!=c.pin(result[1]) or row['case']!=result[1]['case']:c.issue(issues,'artifacts',position,'RESULT_BINDING_MISMATCH')
    qualified=not issues;assessment=None
    if qualified:
        selected={(row['case'],row['role']):row for _,row in artifacts.values()};out=[]
        for observation in r.evaluate(b):
            key=observation['id'];position=b['cases'][key][0];missing=[];incomplete=[];codes=[]
            for role in rule['required_roles']:
                row=selected.get((key,role))
                if row is None:missing.append(role)
                elif not row['complete']:incomplete.append(role)
            if missing:codes.append('EVIDENCE_ROLE_MISSING')
            if incomplete:codes.append('EVIDENCE_ARTIFACT_INCOMPLETE')
            # Complete failure evidence is eligible for manual review; it never makes a test pass.
            if observation['matched'] is None:codes.append('OBSERVATION_INCOMPLETE')
            for code in codes:c.issue(issues,'cases',position,code)
            out.append(dict(id=key,missing_roles=missing,incomplete_roles=incomplete,observation=observation,
                artifact_ids=sorted(row['id'] for _,row in artifacts.values() if row['case']==key),ready_for_manual_evidence_review=not codes))
        assessment=dict(cases=out,all_evidence_contracts_complete=not issues,test_outcomes_upgraded=False)
    return r.output(raw,'outlands-evidence-completeness-report-v1',counts,issues,qualified,assessment,dict(**r.bundle_pins(b),policy_sha256=c.pin(rule),artifacts_sha256=c.cohort_pin(artifacts)))

def main(argv=None):return c.cli('Check declared evidence completeness; never open artifacts or upgrade test outcomes.',check,argv)
if __name__=='__main__':raise SystemExit(main())
