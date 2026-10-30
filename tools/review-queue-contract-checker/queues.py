"""Review declared queue coverage against one explicitly selected snapshot per item."""
import toolkit as t
import decision_core as c
import review_core as r

def entry(row,roles):
    key,out=c.record(row,{'id','item','item_revision','item_sha256','stage','covered_roles','blockers'},('id','item','stage'),('item_revision',))
    t.sha(row['item_sha256']);out['covered_roles']=c.tags(row['covered_roles']);out['blockers']=c.tags(row['blockers'])
    t.require(set(out['covered_roles'])<=set(roles),'ROLE_UNKNOWN');return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','policy','items','entries'});t.require(v['format']=='outlands-review-queue-v1','FORMAT_INVALID')
    policy=r.roles(v['policy']);counts={};issues=[]
    items=r.collect(v['items'],r.snapshot,'items',counts,issues)
    entries=r.collect(v['entries'],lambda row:entry(row,policy['required_roles']),'entries',counts,issues,False)
    r.slots(entries,lambda row:row['item'],'entries',issues)
    for position,row in entries.values():r.reference(row,'item',items,'entries',position,issues)
    qualified=not issues;assessment=None
    if qualified:
        selected={row['item']:row for _,row in entries.values()};out=[]
        for key,(position,item) in sorted(items.items()):
            row=selected.get(key);missing=sorted(set(policy['required_roles'])-set(row['covered_roles'] if row else []));codes=[]
            if row is None:codes.append('QUEUE_ENTRY_MISSING')
            if missing:codes.append('REVIEW_COVERAGE_MISSING')
            if row and row['blockers']:codes.append('DECLARED_BLOCKERS_PRESENT')
            for code in codes:c.issue(issues,'items',position,code)
            out.append(dict(id=key,entry_id=row['id'] if row else None,stage=row['stage'] if row else None,
                missing_roles=missing,blockers=row['blockers'] if row else [],ready_for_manual_review=not codes))
        assessment=dict(items=out,all_covered_and_unblocked=not issues)
    return r.output(raw,'outlands-review-queue-report-v1',counts,issues,qualified,assessment,dict(items=items,entries=entries),policy)

def main(argv=None):return c.cli('Check declared queue coverage; no review or changes performed.',check,argv)
if __name__=='__main__':raise SystemExit(main())
