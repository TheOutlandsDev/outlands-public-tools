"""Review declared recovery-check evidence against exact incident snapshots; never recover."""
import toolkit as t
import decision_core as c
import health_core as r

def policy(value):
    _,out=c.record(value,{'id','revision','required_roles','maximum_evidence_age'},('id',),('revision',));out['required_roles']=c.tags(value['required_roles'],1);t.integer(value['maximum_evidence_age'],10**9);return out

def check_record(row,roles):
    key,out=c.record(row,{'id','revision','incident','incident_revision','incident_sha256','role'},('id','incident','role'),('revision','incident_revision'))
    t.sha(row['incident_sha256']);t.require(row['role'] in roles,'ROLE_UNKNOWN');return key,out

def evidence(row):
    key,out=c.record(row,{'id','check','check_revision','check_sha256','policy_sha256','outcome','observed_at','artifact_sha256'},('id','check'),('check_revision',))
    for field in ('check_sha256','policy_sha256','artifact_sha256'):t.sha(row[field])
    t.integer(row['observed_at']);t.require(row['outcome'] in ('pass','fail','unknown'),'OUTCOME_INVALID');return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','components','incidents','policy','checks','evidence','as_of'});t.require(v['format']=='outlands-recovery-readiness-v1','FORMAT_INVALID');t.integer(v['as_of'])
    rule=policy(v['policy']);counts={};issues=[];components=r.collect(v['components'],r.component,'components',counts,issues)
    incidents=r.collect(v['incidents'],r.incident,'incidents',counts,issues)
    checks=r.collect(v['checks'],lambda row:check_record(row,rule['required_roles']),'checks',counts,issues,False)
    evidence_rows=r.collect(v['evidence'],evidence,'evidence',counts,issues,False)
    r.slots(checks,lambda row:(row['incident'],row['role']),'checks',issues);r.slots(evidence_rows,lambda row:row['check'],'evidence',issues)
    for position,row in incidents.values():r.reference(row,'component',components,'incidents',position,issues)
    for position,row in checks.values():r.reference(row,'incident',incidents,'checks',position,issues)
    for position,row in evidence_rows.values():
        r.reference(row,'check',checks,'evidence',position,issues)
        if row['policy_sha256']!=c.pin(rule):c.issue(issues,'evidence',position,'POLICY_PIN_MISMATCH')
    qualified=not issues;assessment=None
    if qualified:
        selected={(row['incident'],row['role']):row for _,row in checks.values()};receipts={row['check']:row for _,row in evidence_rows.values()};out=[]
        for key,(position,incident) in sorted(incidents.items()):
            missing=[];details=[]
            for role in rule['required_roles']:
                task=selected.get((key,role));receipt=receipts.get(task['id']) if task else None;codes=[];age=dict(age=None,future=False,fresh=False)
                if task is None:missing.append(role);codes.append('CHECK_ROLE_MISSING')
                elif receipt is None:codes.append('CHECK_EVIDENCE_MISSING')
                else:
                    age=r.freshness(receipt['observed_at'],v['as_of'],rule['maximum_evidence_age'])
                    if age['future']:codes.append('EVIDENCE_FUTURE')
                    elif not age['fresh']:codes.append('EVIDENCE_STALE')
                    if receipt['outcome']!='pass':codes.append('CHECK_NOT_DECLARED_PASSED')
                for code in codes:c.issue(issues,'incidents',position,code)
                details.append(dict(role=role,check_id=task['id'] if task else None,evidence_id=receipt['id'] if receipt else None,declared_outcome=receipt['outcome'] if receipt else None,**age,failed_criteria=codes))
            out.append(dict(id=key,missing_roles=missing,checks=details,ready_for_manual_recovery_review=all(not row['failed_criteria'] for row in details)))
        assessment=dict(incidents=out,all_required_check_declarations_ready=not issues)
    return r.output(raw,'outlands-recovery-readiness-report-v1',counts,issues,qualified,assessment,dict(components=components,incidents=incidents,checks=checks,evidence=evidence_rows),rule,dict(as_of=v['as_of']))

def main(argv=None):return c.cli('Plan declared recovery readiness; no restarts, restores or recovery authorization.',check,argv)
if __name__=='__main__':raise SystemExit(main())
