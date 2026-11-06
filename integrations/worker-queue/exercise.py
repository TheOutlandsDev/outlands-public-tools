"""Installed fictional worker/queue review; no worker, broker or artifact access."""
import copy
import hashlib
import json
from importlib.resources import files
from outlands_work_item_contract_checker.items import check as items
from outlands_worker_lease_history_checker.leases import check as leases
from outlands_queue_acknowledgement_reconciler.acks import check as acks
from outlands_worker_result_commit_checker.commits import check as commits

OPS=(items,leases,acks,commits)
PACKAGES=('outlands_work_item_contract_checker','outlands_worker_lease_history_checker',
          'outlands_queue_acknowledgement_reconciler','outlands_worker_result_commit_checker')

def raw(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')

def pin(value):return hashlib.sha256(raw(value)).hexdigest()
def run(index,value):return OPS[index](raw(value))
def codes(report):return {row['code'] for row in report['issues']}

def main():
    values=[json.loads(files(p).joinpath('examples','input.json').read_bytes()) for p in PACKAGES]
    reports=[run(i,v) for i,v in enumerate(values)];checked=list(reports)
    assert all(r['status']=='PASS' and r['qualified_scope_sha256'] for r in reports)
    assert len({r['items_sha256'] for r in reports})==1
    assert len({r['lease_events_sha256'] for r in reports[1:]})==1
    assert reports[2]['deliveries_sha256']==reports[3]['deliveries_sha256']
    assert reports[1]['assessment']['items'][0]['current_owner']['worker']=='worker-beta'
    assert reports[1]['assessment']['ownership_windows'][0]['end']==20
    assert reports[2]['assessment']['items'][0]['single_consistent_acknowledged_delivery']=='delivery-current'
    assert reports[3]['assessment']['items'][0]['consistent_commit_id']=='commit-current'
    # Identical declarations count once and preserve normalized cohort pins.
    for i,value in enumerate(values):
        duplicate=copy.deepcopy(value)
        for field,rows in duplicate.items():
            if isinstance(rows,list) and rows:rows.append(copy.deepcopy(rows[0]))
        report=run(i,duplicate);checked.append(report)
        assert report['status']=='PASS' and report['qualified_scope_sha256']==reports[i]['qualified_scope_sha256']
        assert all(count['duplicate_rows']==1 for count in report['counts'].values())
    # A stale structural reference withholds the entire assessment and pins.
    stale=copy.deepcopy(values[1]);stale['lease_events'][0]['item_sha256']='0'*64
    report=run(1,stale);checked.append(report)
    assert report['status']=='REVIEW_REQUIRED' and report['assessment'] is None and report['items_sha256'] is None
    assert 'SNAPSHOT_MISMATCH' in codes(report)
    # A rejected overlapping acquisition still raises the in-range declared token.
    overlap=copy.deepcopy(values[1]);extra=dict(overlap['lease_events'][-1],id='lease-overlap',ordinal=4,at=31,action='acquire',worker='worker-gamma',token=3,until=45)
    overlap['lease_events'].append(extra);report=run(1,overlap);checked.append(report)
    assert 'LEASE_OVERLAP' in codes(report) and report['assessment']['items'][0]['highest_declared_acquire_token']==3
    assert report['assessment']['items'][0]['current_owner']['worker']=='worker-beta' and report['items_sha256'] is not None
    invalid_consumer=copy.deepcopy(values[2]);invalid_consumer['lease_events']=overlap['lease_events']
    report=run(2,invalid_consumer);checked.append(report)
    assert report['assessment'] is None and report['items_sha256'] is None
    future=copy.deepcopy(values[1]);future['lease_events'].append(dict(extra,id='lease-future',at=60,token=999,until=70))
    report=run(1,future);checked.append(report)
    assert 'EVENT_AFTER_AS_OF' in codes(report) and report['assessment']['items'][0]['highest_declared_acquire_token']==2
    # Expiry is exclusive even if the result was produced earlier within the lease.
    expired=copy.deepcopy(values[3]);expired['as_of']=50;expired['commits'][0]['at']=50
    report=run(3,expired);checked.append(report)
    assert 'COMMIT_OWNER_NOT_ACTIVE' in codes(report) and report['assessment']['items'][0]['consistent_commit_id'] is None
    expired_ack=copy.deepcopy(values[2]);expired_ack['as_of']=50;expired_ack['acknowledgements'][0]['at']=50
    report=run(2,expired_ack);checked.append(report);assert 'ACK_OWNER_NOT_ACTIVE' in codes(report)
    alias=copy.deepcopy(values[3]);alias['commits'].append(dict(alias['commits'][0],id='commit-alias'))
    report=run(3,alias);checked.append(report)
    assert 'COMMIT_SLOT_AMBIGUOUS' in codes(report) and all(not row['consistent'] for row in report['assessment']['commits'])
    # A current consistent acknowledgement does not erase a late former owner.
    late=copy.deepcopy(values[2]);current=late['deliveries'][0];current['ordinal']=2
    late['acknowledgements'][0]['delivery_sha256']=pin(current)
    old=dict(current,id='delivery-old',ordinal=1,at=12,worker='worker-alpha',token=1);late['deliveries'].append(old)
    late['acknowledgements'].append(dict(id='ack-old',delivery=old['id'],delivery_sha256=pin(old),at=25,worker='worker-alpha',token=1,state='acknowledged'))
    report=run(2,late);checked.append(report)
    assert 'ACK_OWNER_NOT_ACTIVE' in codes(report) and report['assessment']['items'][0]['single_consistent_acknowledged_delivery']=='delivery-current'
    assert report['assessment']['items'][0]['all_deliveries_accounted'] is False
    # Other consumers do not repeat the handler/required-metadata check.
    missing=copy.deepcopy(values);item=copy.deepcopy(missing[0]['items'][0]);item['metadata'].remove('review-scope')
    for value in missing:
        value['items']=[copy.deepcopy(item)]
        for field in ('lease_events','deliveries','results','commits'):
            for row in value.get(field,[]):row['item_sha256']=pin(item)
        delivery={row['id']:row for row in value.get('deliveries',[])}
        for row in value.get('acknowledgements',[]):row['delivery_sha256']=pin(delivery[row['delivery']])
        for row in value.get('results',[]):row['delivery_sha256']=pin(delivery[row['delivery']])
        results={row['id']:row for row in value.get('results',[])}
        for row in value.get('commits',[]):row['result_sha256']=pin(results[row['result']])
    missing_reports=[run(i,v) for i,v in enumerate(missing)];checked.extend(missing_reports)
    assert 'ITEM_METADATA_MISSING' in codes(missing_reports[0]) and all(r['status']=='PASS' for r in missing_reports[1:])
    assert len({r['items_sha256'] for r in missing_reports})==1
    for report in checked:
        for field in ('payloads_opened','handler_executed','artifact_bytes_verified','worker_contacted','ownership_enforced','jobs_executed','queue_changed','records_changed','results_committed','target_changes_performed','execution_authorized','declarations_independently_verified'):
            assert report[field] is False
        if report['status']=='REVIEW_REQUIRED':assert report['qualified_scope_sha256'] is None
    assert reports[0]['assessment']['payload_values_validated'] is False
    assert reports[2]['assessment']['broker_delivery_verified'] is False
    assert reports[3]['assessment']['commit_verified'] is False
    print(json.dumps(dict(status='PASS',current_owner='worker-beta',shared_item_lease_delivery_pins='matched',duplicates='counted once',stale_reference='assessment withheld',overlap='diagnostic only; consumer withheld',future_token='not applied',expiry='acknowledgement and commit unqualified',commit_alias='all unqualified',late_old_owner='finding retained beside current claim',missing_metadata='requires separate contract check',execution_authorized=False,ownership_enforced=False,artifact_bytes_verified=False,results_committed=False),sort_keys=True))

if __name__=='__main__':main()
