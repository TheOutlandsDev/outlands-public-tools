"""Bounded declared work items, half-open lease intervals and exact record references."""
import toolkit as t
import decision_core as c

def collect(value,parser,side,counts,issues,required=True):
    selected,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not selected:c.issue(issues,side,0,'COHORT_EMPTY')
    return selected

def item(row):
    key,out=c.record(row,{'id','revision','kind','handler','handler_revision','handler_sha256','input_sha256','input_contract_sha256','result_contract_sha256','metadata'},('id','kind','handler'),('revision','handler_revision'))
    for field in ('handler_sha256','input_sha256','input_contract_sha256','result_contract_sha256'):t.sha(row[field])
    out['metadata']=c.tags(row['metadata']);return key,out

def lease(row):
    key,out=c.record(row,{'id','item','item_revision','item_sha256','ordinal','at','action','worker','token','until'},('id','item','worker'),('item_revision',))
    t.sha(row['item_sha256']);t.integer(row['ordinal'],1000,1);t.integer(row['at'],10**12);t.integer(row['token'],10**12,1)
    t.require(row['action'] in ('acquire','renew','release'),'LEASE_ACTION_INVALID')
    if row['action']=='release':t.require(row['until'] is None,'RELEASE_UNTIL_INVALID')
    else:t.integer(row['until'],10**12);t.require(row['until']>row['at'],'UNTIL_NOT_AFTER_EVENT')
    return key,out

def delivery(row):
    key,out=c.record(row,{'id','item','item_revision','item_sha256','ordinal','at','worker','token'},('id','item','worker'),('item_revision',))
    t.sha(row['item_sha256']);t.integer(row['ordinal'],1000,1);t.integer(row['at'],10**12);t.integer(row['token'],10**12,1);return key,out

def reference(row,field,records,side,position,issues,revision=True):
    selected=records.get(row[field])
    if selected is None:c.issue(issues,side,position,'REFERENCE_UNKNOWN');return None
    target=selected[1]
    if row[field+'_sha256']!=c.pin(target) or (revision and row[field+'_revision']!=target['revision']):c.issue(issues,side,position,'SNAPSHOT_MISMATCH')
    return target

def slots(rows,slot,side,issues):
    seen=set()
    for position,row in rows.values():
        key=slot(row)
        if key in seen:c.issue(issues,side,position,'SLOT_AMBIGUOUS')
        seen.add(key)

def timeline(rows,side,issues):
    slots(rows,lambda row:(row['item'],row['ordinal']),side,issues);groups={}
    for value in rows.values():groups.setdefault(value[1]['item'],[]).append(value)
    for group in groups.values():
        previous=-1
        for expected,(position,row) in enumerate(sorted(group,key=lambda pair:pair[1]['ordinal']),1):
            if row['ordinal']!=expected:c.issue(issues,side,position,'ORDINAL_GAP')
            if row['at']<previous:c.issue(issues,side,position,'TIME_REVERSED')
            previous=row['at']

def lease_scope(items_value,events_value,as_of,counts,issues):
    items=collect(items_value,item,'items',counts,issues);events=collect(events_value,lease,'lease_events',counts,issues,False)
    for position,row in events.values():reference(row,'item',items,'lease_events',position,issues)
    timeline(events,'lease_events',issues);qualified=not issues;assessment=None;windows=[]
    if qualified:
        summaries=[]
        for key,(item_position,_) in sorted(items.items()):
            group=sorted((pair for pair in events.values() if pair[1]['item']==key),key=lambda pair:pair[1]['ordinal']);current=None;highest=0;history=[]
            if not group:c.issue(issues,'items',item_position,'LEASE_HISTORY_MISSING')
            for position,row in group:
                failed=[]
                if row['at']>as_of:failed.append('EVENT_AFTER_AS_OF')
                else:
                    if current is not None and row['at']>=current['end']:current=None
                    if row['action']=='acquire':
                        if current is not None:failed.append('LEASE_OVERLAP')
                        if row['token']<=highest:failed.append('TOKEN_NOT_INCREASING')
                        highest=max(highest,row['token'])
                        if not failed:
                            current=dict(item=key,worker=row['worker'],token=row['token'],start=row['at'],end=row['until'],acquire_event=row['id']);windows.append(current)
                    else:
                        if current is None:failed.append('LEASE_NOT_ACTIVE')
                        elif (row['worker'],row['token'])!=(current['worker'],current['token']):failed.append('LEASE_OWNER_MISMATCH')
                        elif row['action']=='renew' and row['until']<=current['end']:failed.append('RENEWAL_NOT_EXTENDED')
                        if not failed:
                            if row['action']=='renew':current['end']=row['until']
                            else:current['end']=row['at'];current=None
                for code in failed:c.issue(issues,'lease_events',position,code)
                history.append(dict(id=row['id'],action=row['action'],at=row['at'],applied=not failed,failed_criteria=failed))
            owner=None if current is None or as_of>=current['end'] else dict(worker=current['worker'],token=current['token'],until=current['end'],acquire_event=current['acquire_event'])
            summaries.append(dict(id=key,current_owner=owner,highest_declared_acquire_token=highest,history=history))
        assessment=dict(items=summaries,ownership_windows=windows)
    return items,events,assessment,windows,qualified

def owns(windows,item_id,worker,token,at):
    return sum(row['item']==item_id and row['worker']==worker and row['token']==token and row['start']<=at<row['end'] for row in windows)==1

def delivery_scope(value,items,counts,issues):
    rows=collect(value,delivery,'deliveries',counts,issues,False)
    for position,row in rows.values():reference(row,'item',items,'deliveries',position,issues)
    timeline(rows,'deliveries',issues);return rows

def delivery_failures(row,windows,as_of):
    out=[]
    if row['at']>as_of:out.append('DELIVERY_AFTER_AS_OF')
    if not owns(windows,row['item'],row['worker'],row['token'],row['at']):out.append('DELIVERY_OWNER_NOT_ACTIVE')
    return out

def output(raw,fmt,counts,issues,qualified,assessment,pins,**extra):
    report=c.base(raw,fmt,counts,issues)
    report.update(assessment=assessment,qualified_scope_sha256=c.pin(dict(format=fmt,**pins)) if qualified and not issues else None,
        payloads_opened=False,handler_executed=False,artifact_bytes_verified=False,worker_contacted=False,
        ownership_enforced=False,jobs_executed=False,queue_changed=False,records_changed=False,results_committed=False,**extra)
    report.update({key:value if qualified else None for key,value in pins.items()});return report
