"""Check explicitly requested symmetric component pairs against a pinned declared matrix."""
import toolkit as t
import decision_core as c
import config_core as r

def component(row):
    key,out=c.record(row,{'id','revision','version','contract_sha256'},('id','version'),('revision',));t.sha(row['contract_sha256']);return key,out

def pair(row,rule):
    fields={'id','left','left_revision','left_sha256','right','right_revision','right_sha256'}|({'allowed'} if rule else set())
    key,out=c.record(row,fields,('id','left','right'),('left_revision','right_revision'));t.sha(row['left_sha256']);t.sha(row['right_sha256']);t.require(row['left']!=row['right'],'PAIR_SELF_REFERENCE')
    if rule:t.require(type(row['allowed']) is bool,'ALLOWED_FLAG_INVALID')
    if row['right']<row['left']:
        for suffix in ('','_revision','_sha256'):out['left'+suffix],out['right'+suffix]=row['right'+suffix],row['left'+suffix]
    return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','components','rules','requirements'});t.require(v['format']=='outlands-compatibility-matrix-v1','FORMAT_INVALID')
    counts={};issues=[];components=r.collect(v['components'],component,'components',counts,issues)
    rules=r.collect(v['rules'],lambda row:pair(row,True),'rules',counts,issues,False);requirements=r.collect(v['requirements'],lambda row:pair(row,False),'requirements',counts,issues)
    for side,rows in [('rules',rules),('requirements',requirements)]:
        r.slots(rows,lambda row:(row['left'],row['right']),side,issues)
        for position,row in rows.values():
            for field in ('left','right'):r.reference(row,field,components,side,position,issues)
    qualified=not issues;assessment=None
    if qualified:
        selected={(row['left'],row['right']):row for _,row in rules.values()};out=[]
        for key,(position,row) in sorted(requirements.items()):
            rule=selected.get((row['left'],row['right']));state='unlisted' if rule is None else 'supported' if rule['allowed'] else 'unsupported'
            if state!='supported':c.issue(issues,'requirements',position,'PAIR_'+state.upper())
            out.append(dict(id=key,left=row['left'],right=row['right'],rule_id=rule['id'] if rule else None,state=state))
        assessment=dict(requirements=out,all_requested_pairs_declared_supported=not issues,unrequested_pairs_checked=False)
    return r.output(raw,'outlands-compatibility-matrix-report-v1',counts,issues,qualified,assessment,dict(components_sha256=c.cohort_pin(components),rules_sha256=c.cohort_pin(rules),requirements_sha256=c.cohort_pin(requirements)))

def main(argv=None):return c.cli('Check declared compatibility pairs; no runtime or version inference.',check,argv)
if __name__=='__main__':raise SystemExit(main())
