"""Check half-open capacity reservations without scheduling or resource actions."""
from collections import defaultdict
import toolkit as t
import resource_core as c


def reservation(row):
    t.fields(row,{'id','resource_id','start','end','units'})
    t.identifier(row['id']); t.identifier(row['resource_id']); c.interval(row['start'],row['end'])
    t.integer(row['units'],10**6,1); return row['id'],dict(row)


def check(raw):
    value=t.decode(raw); t.fields(value,{'format','resources','reservations'})
    t.require(value['format']=='outlands-resource-reservations-v1','FORMAT_INVALID')
    resources,rc,issues=c.rows(value['resources'],c.resource,'resources'); resource_issues=bool(issues)
    reservations,bc,other=c.rows(value['reservations'],reservation,'reservations'); issues+=other
    if not resources: c.problem(issues,'resources',0,'EMPTY_RESOURCE_COHORT')
    grouped=defaultdict(list)
    for key,(index,row) in reservations.items():
        if row['resource_id'] not in resources:
            c.problem(issues,'reservations',index,'RESOURCE_MISSING'); continue
        resource=resources[row['resource_id']][1]
        if not c.covered(resource,row['start'],row['end']): c.problem(issues,'reservations',index,'RESERVATION_OUTSIDE_AVAILABILITY')
        grouped[row['resource_id']].append(row)
    summary=None
    if not issues:
        summary=[]
        for key,(_,resource) in sorted(resources.items()):
            changes=defaultdict(int)
            for row in grouped[key]: changes[row['start']]+=row['units']; changes[row['end']]-=row['units']
            times=sorted(changes); used=peak=0; over=[]
            for start,end in zip(times,times[1:]):
                # Aggregate simultaneous ends/starts before the following span.
                used+=changes[start]; peak=max(peak,used)
                if used>resource['capacity']:
                    over.append(dict(start=start,end=end,units=used))
                    c.problem(issues,'reservations',0,'CAPACITY_EXCEEDED',resource_id=key,start=start,end=end)
            summary.append(dict(id=key,capacity=resource['capacity'],reservation_count=len(grouped[key]),peak_units=peak,over_capacity_spans=over))
    result=c.base(raw,'outlands-resource-reservation-review-v1',dict(resources=rc,reservations=bc),issues)
    result.update(summary=summary,resource_contract_sha256=c.resource_pin(resources) if not resource_issues else None,
                  interval_end_exclusive=True,reservations_changed=False,schedule_optimized=False)
    return result


def main(argv=None): return c.cli('Check explicit reservation capacity and availability; no scheduling.',check,argv)
if __name__=='__main__': raise SystemExit(main())
