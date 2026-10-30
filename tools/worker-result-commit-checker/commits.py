"""Check exact result/commit claims and declared lease ownership, without database writes."""
import toolkit as t
import decision_core as c
import worker_core as r

def result(row):
    key,out=c.record(row,{'id','item','item_revision','item_sha256','delivery','delivery_sha256','worker','token','at','input_sha256','handler_sha256','result_contract_sha256','artifact_sha256'},('id','item','delivery','worker'),('item_revision',))
    for field in ('item_sha256','delivery_sha256','input_sha256','handler_sha256','result_contract_sha256','artifact_sha256'):t.sha(row[field])
    t.integer(row['at'],10**12);t.integer(row['token'],10**12,1);return key,out

def commit(row):
    key,out=c.record(row,{'id','item','item_revision','item_sha256','result','result_sha256','worker','token','at'},('id','item','result','worker'),('item_revision',))
    t.sha(row['item_sha256']);t.sha(row['result_sha256']);t.integer(row['at'],10**12);t.integer(row['token'],10**12,1);return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','items','lease_events','deliveries','results','commits','as_of'});t.require(v['format']=='outlands-worker-result-commits-v1','FORMAT_INVALID');t.integer(v['as_of'],10**12)
    counts={};issues=[];items,events,lease_assessment,windows,_=r.lease_scope(v['items'],v['lease_events'],v['as_of'],counts,issues)
    deliveries=r.delivery_scope(v['deliveries'],items,counts,issues);results=r.collect(v['results'],result,'results',counts,issues,False);commits=r.collect(v['commits'],commit,'commits',counts,issues,False)
    r.slots(results,lambda row:row['delivery'],'results',issues)
    for position,row in results.values():
        job=r.reference(row,'item',items,'results',position,issues);sent=r.reference(row,'delivery',deliveries,'results',position,issues,False)
        if sent is not None and row['item']!=sent['item']:c.issue(issues,'results',position,'DELIVERY_ITEM_MISMATCH')
        if job is not None and any(row[field]!=job[field] for field in ('input_sha256','handler_sha256','result_contract_sha256')):c.issue(issues,'results',position,'RESULT_CONTRACT_MISMATCH')
        if sent is not None and row['at']<sent['at']:c.issue(issues,'results',position,'RESULT_BEFORE_DELIVERY')
    for position,row in commits.values():
        r.reference(row,'item',items,'commits',position,issues);selected=r.reference(row,'result',results,'commits',position,issues,False)
        if selected is not None and row['item']!=selected['item']:c.issue(issues,'commits',position,'RESULT_ITEM_MISMATCH')
        if selected is not None and row['at']<selected['at']:c.issue(issues,'commits',position,'COMMIT_BEFORE_RESULT')
    qualified=not issues;assessment=None
    if qualified:
        delivery_valid={};result_valid={};delivery_out=[];result_out=[];commit_out=[];summaries=[]
        for key,(position,row) in sorted(deliveries.items()):
            failed=r.delivery_failures(row,windows,v['as_of']);delivery_valid[key]=not failed
            for code in failed:c.issue(issues,'deliveries',position,code)
            delivery_out.append(dict(id=key,consistent=not failed,failed_criteria=failed))
        for key,(position,row) in sorted(results.items()):
            sent=deliveries[row['delivery']][1];failed=[]
            if not delivery_valid[row['delivery']]:failed.append('RESULT_DELIVERY_INVALID')
            if row['at']>v['as_of']:failed.append('RESULT_AFTER_AS_OF')
            if (row['worker'],row['token'])!=(sent['worker'],sent['token']):failed.append('RESULT_DELIVERY_OWNER_MISMATCH')
            if not r.owns(windows,row['item'],row['worker'],row['token'],row['at']):failed.append('RESULT_OWNER_NOT_ACTIVE')
            result_valid[key]=not failed
            for code in failed:c.issue(issues,'results',position,code)
            result_out.append(dict(id=key,consistent=not failed,failed_criteria=failed))
        for key,(item_position,_) in sorted(items.items()):
            group=sorted((pair for pair in commits.values() if pair[1]['item']==key),key=lambda pair:pair[1]['id']);valid=[]
            if not group:c.issue(issues,'items',item_position,'COMMIT_MISSING')
            for position,row in group:
                selected=results[row['result']][1];failed=[]
                if len(group)>1:failed.append('COMMIT_SLOT_AMBIGUOUS')
                if not result_valid[row['result']]:failed.append('COMMIT_RESULT_INVALID')
                if row['at']>v['as_of']:failed.append('COMMIT_AFTER_AS_OF')
                if (row['worker'],row['token'])!=(selected['worker'],selected['token']):failed.append('COMMIT_RESULT_OWNER_MISMATCH')
                if not r.owns(windows,key,row['worker'],row['token'],row['at']):failed.append('COMMIT_OWNER_NOT_ACTIVE')
                if not failed:valid.append(row['id'])
                for code in failed:c.issue(issues,'commits',position,code)
                commit_out.append(dict(id=row['id'],consistent=not failed,failed_criteria=failed))
            summaries.append(dict(id=key,commit_count=len(group),consistent_commit_id=valid[0] if len(valid)==1 else None))
        assessment=dict(items=summaries,deliveries=delivery_out,results=result_out,commits=commit_out,commit_verified=False)
    return r.output(raw,'outlands-worker-result-commits-report-v1',counts,issues,qualified,assessment,dict(items_sha256=c.cohort_pin(items),lease_events_sha256=c.cohort_pin(events),deliveries_sha256=c.cohort_pin(deliveries),results_sha256=c.cohort_pin(results),commits_sha256=c.cohort_pin(commits),as_of_sha256=c.pin(v['as_of'])),as_of=v['as_of'])

def main(argv=None):return c.cli('Check declared worker result commits; no artifact reads, jobs or database writes.',check,argv)
if __name__=='__main__':raise SystemExit(main())
