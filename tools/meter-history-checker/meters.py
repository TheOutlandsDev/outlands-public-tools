"""Check explicit counter readings and reset boundaries without reading a device."""
from collections import defaultdict
import toolkit as t
import service_core as c

def meter(row):return c.record(row,{'id','unit','usage_origin','initial_at','initial_reading'},('id','unit','usage_origin'),(('initial_at',0,10**9),('initial_reading',0,10**12)))
def event(row):
    key,out=c.record(row,{'id','meter_id','at','kind','reading','previous_reading'},('id','meter_id'),(('at',0,10**9),('reading',0,10**12)))
    t.require(row['kind'] in ('sample','reset'),'METER_EVENT_KIND_INVALID')
    if row['kind']=='sample':t.require(row['previous_reading'] is None,'SAMPLE_PREVIOUS_READING_FORBIDDEN')
    else:t.integer(row['previous_reading'],10**12)
    return key,out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','meters','events'})
    t.require(value['format']=='outlands-meter-history-v1','FORMAT_INVALID')
    meters,mc,issues=c.rows(value['meters'],meter,'meters');events,ec,other=c.rows(value['events'],event,'events');issues+=other
    if not meters:c.issue(issues,'meters',0,'EMPTY_METER_COHORT')
    grouped=defaultdict(list)
    for index,row in events.values():
        if row['meter_id'] not in meters:c.issue(issues,'events',index,'METER_MISSING')
        else:grouped[row['meter_id']].append((index,row))
    snapshots=[]
    for key,(index,initial) in sorted(meters.items()):
        ordered=sorted(grouped[key],key=lambda p:(p[1]['at'],p[1]['id']));seen=set()
        previous=initial['initial_reading'];last=initial['initial_at'];usage=resets=samples=0
        for ei,row in ordered:
            if row['at'] in seen:c.issue(issues,'events',ei,'METER_TIME_TIE')
            seen.add(row['at'])
            if row['at']<=last:c.issue(issues,'events',ei,'METER_TIME_NOT_AFTER_PREVIOUS')
            before=row['reading'] if row['kind']=='sample' else row['previous_reading']
            if before<previous:c.issue(issues,'events',ei,'COUNTER_DECREASE_WITHOUT_VALID_RESET')
            else:usage+=before-previous
            if row['kind']=='reset':resets+=1
            else:samples+=1
            previous=row['reading'];last=row['at']
        snapshots.append(dict(id=key,unit=initial['unit'],usage_origin=initial['usage_origin'],observed_at=last,total_usage=usage,
                              display_reading=previous,reset_count=resets,sample_count=samples))
    result=c.base(raw,'outlands-meter-history-review-v1',dict(meters=mc,events=ec),issues)
    result.update(snapshots=snapshots if not issues else None,physical_counter_verified=False,counters_changed=False,live_reading_collected=False)
    return result

def main(argv=None):return c.cli('Review supplied counter histories; no device reading or reset.',check,argv)
if __name__=='__main__':raise SystemExit(main())
