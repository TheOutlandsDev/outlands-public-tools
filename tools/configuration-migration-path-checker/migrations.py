"""Check one exact supplied migration chain; never open adapters or execute checks."""
import toolkit as t
import decision_core as c
import config_core as r

def selector(value):
    t.fields(value,{'id','revision','sha256'});t.identifier(value['id']);t.integer(value['revision'],10**6,1);t.sha(value['sha256']);return dict(value)

def step(row):
    key,out=c.record(row,{'id','ordinal','from_contract','from_contract_revision','from_contract_sha256','to_contract','to_contract_revision','to_contract_sha256','adapter_sha256','required_checks'},('id','from_contract','to_contract'),('from_contract_revision','to_contract_revision'))
    t.integer(row['ordinal'],1000,1)
    for field in ('from_contract_sha256','to_contract_sha256','adapter_sha256'):t.sha(row[field])
    out['required_checks']=c.tags(row['required_checks']);return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','contracts','source','target','steps'});t.require(v['format']=='outlands-config-migration-path-v1','FORMAT_INVALID')
    source=selector(v['source']);target=selector(v['target']);counts={};issues=[]
    contracts=r.collect(v['contracts'],r.contract_record,'contracts',counts,issues);steps=r.collect(v['steps'],step,'steps',counts,issues,False)
    t.require(sum(len(row['fields']) for _,row in contracts.values())<=4096,'CONTRACT_FIELD_SCOPE_LIMIT')
    t.require(sum(len(row['required_checks']) for _,row in steps.values())<=4096,'CHECK_REFERENCE_SCOPE_LIMIT')
    r.slots(steps,lambda row:row['ordinal'],'steps',issues)
    for side,selection in [('source',source),('target',target)]:
        record=contracts.get(selection['id'])
        if record is None:c.issue(issues,side,0,'CONTRACT_UNKNOWN')
        elif selection['revision']!=record[1]['revision'] or selection['sha256']!=c.pin(record[1]):c.issue(issues,side,0,'CONTRACT_SNAPSHOT_MISMATCH')
    current=source['id'];visited={current};path=[current];ordered=sorted(steps.values(),key=lambda pair:pair[1]['ordinal'])
    for expected,(position,row) in enumerate(ordered,1):
        for field in ('from_contract','to_contract'):r.reference(row,field,contracts,'steps',position,issues)
        if row['ordinal']!=expected:c.issue(issues,'steps',position,'STEP_ORDINAL_GAP')
        if row['from_contract']!=current:c.issue(issues,'steps',position,'PATH_DISCONTINUITY')
        if row['to_contract'] in visited:c.issue(issues,'steps',position,'PATH_CYCLE')
        current=row['to_contract'];visited.add(current);path.append(current)
    qualified=not issues;assessment=None
    if qualified:
        if current!=target['id']:c.issue(issues,'path',0,'PATH_TARGET_NOT_REACHED')
        assessment=dict(contract_ids=path,step_ids=[row['id'] for _,row in ordered],required_check_ids=sorted({tag for _,row in ordered for tag in row['required_checks']}),
            target_reached=current==target['id'],checks_executed=False,adapters_opened=False)
    return r.output(raw,'outlands-config-migration-path-report-v1',counts,issues,qualified,assessment,dict(contracts_sha256=c.cohort_pin(contracts),steps_sha256=c.cohort_pin(steps),source_sha256=c.pin(source),target_sha256=c.pin(target)))

def main(argv=None):return c.cli('Check a declared migration path; no adapters or checks executed.',check,argv)
if __name__=='__main__':raise SystemExit(main())
