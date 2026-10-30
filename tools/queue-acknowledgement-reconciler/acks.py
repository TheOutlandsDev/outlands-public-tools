"""Reconcile exact deliveries and acknowledgements against a recomputed supplied lease history."""
import toolkit as t
import decision_core as c
import worker_core as r

def acknowledgement(row):
    key,out=c.record(row,{'id','delivery','delivery_sha256','at','worker','token','state'},('id','delivery','worker'))
    t.sha(row['delivery_sha256']);t.integer(row['at'],10**12);t.integer(row['token'],10**12,1);t.require(row['state'] in ('acknowledged','requeued','dead_lettered'),'ACK_STATE_INVALID');return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','items','lease_events','deliveries','acknowledgements','as_of'});t.require(v['format']=='outlands-queue-acknowledgements-v1','FORMAT_INVALID');t.integer(v['as_of'],10**12)
    counts={};issues=[];items,events,lease_assessment,windows,_=r.lease_scope(v['items'],v['lease_events'],v['as_of'],counts,issues)
    deliveries=r.delivery_scope(v['deliveries'],items,counts,issues);acks=r.collect(v['acknowledgements'],acknowledgement,'acknowledgements',counts,issues,False)
    r.slots(acks,lambda row:row['delivery'],'acknowledgements',issues)
    for position,row in acks.values():
        target=r.reference(row,'delivery',deliveries,'acknowledgements',position,issues,False)
        if target is not None and row['at']<target['at']:c.issue(issues,'acknowledgements',position,'ACK_BEFORE_DELIVERY')
    qualified=not issues;assessment=None
    if qualified:
        ack_index={row['delivery']:(position,row) for position,row in acks.values()};out=[];summaries=[]
        for key,(item_position,_) in sorted(items.items()):
            group=sorted((pair for pair in deliveries.values() if pair[1]['item']==key),key=lambda pair:pair[1]['ordinal']);previous=None;successes=[];all_accounted=True
            if not group:c.issue(issues,'items',item_position,'DELIVERY_MISSING');all_accounted=False
            for position,row in group:
                failed=r.delivery_failures(row,windows,v['as_of']);ack_pair=ack_index.get(row['id']);ack=ack_pair[1] if ack_pair else None;ack_failed=[]
                if previous is not None:
                    old,old_ack,old_valid=previous
                    terminal=old_ack is not None and old_valid and old_ack['at']<=row['at']
                    if terminal and old_ack['state'] in ('acknowledged','dead_lettered'):failed.append('DELIVERY_AFTER_TERMINAL_OUTCOME')
                    elif not (terminal and old_ack['state']=='requeued'):
                        expired=not r.owns(windows,old['item'],old['worker'],old['token'],row['at']) and row['token']>old['token']
                        if not expired:failed.append('PRIOR_DELIVERY_UNRESOLVED')
                if ack is None:ack_failed.append('ACK_MISSING')
                else:
                    if ack['at']>v['as_of']:ack_failed.append('ACK_AFTER_AS_OF')
                    if (ack['worker'],ack['token'])!=(row['worker'],row['token']):ack_failed.append('ACK_DELIVERY_OWNER_MISMATCH')
                    if not r.owns(windows,row['item'],ack['worker'],ack['token'],ack['at']):ack_failed.append('ACK_OWNER_NOT_ACTIVE')
                ack_valid=ack is not None and not failed and not ack_failed
                if ack_valid and ack['state']=='acknowledged':successes.append(row['id'])
                if failed or ack_failed:all_accounted=False
                for code in failed:c.issue(issues,'deliveries',position,code)
                for code in ack_failed:c.issue(issues,'acknowledgements',ack_pair[0] if ack_pair else 0,code)
                out.append(dict(id=row['id'],item=key,delivery_consistent=not failed,acknowledgement_id=ack['id'] if ack else None,declared_state=ack['state'] if ack else None,acknowledgement_consistent=ack_valid,failed_criteria=failed+ack_failed))
                previous=(row,ack,ack_valid)
            if len(successes)>1:c.issue(issues,'items',item_position,'MULTIPLE_SUCCESSFUL_DELIVERIES')
            if not successes:c.issue(issues,'items',item_position,'ITEM_NOT_ACKNOWLEDGED')
            summaries.append(dict(id=key,delivery_count=len(group),all_deliveries_accounted=all_accounted,single_consistent_acknowledged_delivery=successes[0] if len(successes)==1 else None))
        assessment=dict(items=summaries,deliveries=out,broker_delivery_verified=False)
    return r.output(raw,'outlands-queue-acknowledgements-report-v1',counts,issues,qualified,assessment,dict(items_sha256=c.cohort_pin(items),lease_events_sha256=c.cohort_pin(events),deliveries_sha256=c.cohort_pin(deliveries),acknowledgements_sha256=c.cohort_pin(acks),as_of_sha256=c.pin(v['as_of'])),as_of=v['as_of'])

def main(argv=None):return c.cli('Reconcile declared queue acknowledgements; no broker access or acknowledgements sent.',check,argv)
if __name__=='__main__':raise SystemExit(main())
