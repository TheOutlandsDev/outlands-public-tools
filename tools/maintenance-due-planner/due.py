"""Advisory service due states from explicit ordinals and declared cumulative usage."""
import toolkit as t
import service_core as c

def snapshot(row):
    key,out=c.record(row,{'id','unit','usage_origin','observed_at','total_usage','source_sha256'},('id','unit','usage_origin'),(('observed_at',0,10**9),('total_usage',0,10**15)))
    t.sha(row['source_sha256']);return key,out
def plan(row):
    key,out=c.record(row,{'id','asset_id','last_service_at','time_interval','meter_id','meter_unit','usage_origin','last_service_usage','usage_interval'},('id','asset_id'),(('last_service_at',0,10**9),))
    if row['time_interval'] is not None:t.integer(row['time_interval'],10**9,1)
    if row['usage_interval'] is not None:
        t.integer(row['usage_interval'],10**12,1);t.integer(row['last_service_usage'],10**15)
        for field in ('meter_id','meter_unit','usage_origin'):t.identifier(row[field])
    else:t.require(all(row[k] is None for k in ('meter_id','meter_unit','usage_origin','last_service_usage')),'UNUSED_METER_FIELDS')
    t.require(row['time_interval'] is not None or row['usage_interval'] is not None,'INTERVAL_REQUIRED')
    return key,out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','as_of','maximum_meter_age','meters','plans'})
    t.require(value['format']=='outlands-maintenance-due-v1','FORMAT_INVALID')
    t.integer(value['as_of'],10**9);t.integer(value['maximum_meter_age'],10**9)
    meters,mc,issues=c.rows(value['meters'],snapshot,'meters');plans,pc,other=c.rows(value['plans'],plan,'plans');issues+=other
    if not plans:c.issue(issues,'plans',0,'EMPTY_PLAN_COHORT')
    for index,row in meters.values():
        if row['observed_at']>value['as_of']:c.issue(issues,'meters',index,'METER_FROM_FUTURE')
    for index,row in plans.values():
        if row['last_service_at']>value['as_of']:c.issue(issues,'plans',index,'SERVICE_BASELINE_FROM_FUTURE')
        if row['usage_interval'] is not None:
            if row['meter_id'] not in meters:c.issue(issues,'plans',index,'METER_MISSING')
            else:
                meter=meters[row['meter_id']][1]
                if (row['meter_unit'],row['usage_origin'])!=(meter['unit'],meter['usage_origin']):c.issue(issues,'plans',index,'METER_UNIT_OR_ORIGIN_MISMATCH')
                if meter['observed_at']<row['last_service_at']:c.issue(issues,'plans',index,'METER_PREDATES_SERVICE_BASELINE')
                if meter['total_usage']<row['last_service_usage']:c.issue(issues,'plans',index,'USAGE_BASELINE_AHEAD_OF_SNAPSHOT')
    assessments=None
    if not issues:
        assessments=[]
        for key,(index,row) in sorted(plans.items()):
            next_at=row['last_service_at']+row['time_interval'] if row['time_interval'] is not None else None
            time_due=value['as_of']>=next_at if next_at is not None else None
            meter_due=due_usage=fresh=age=remaining_usage=None
            if row['usage_interval'] is not None:
                meter=meters[row['meter_id']][1];age=value['as_of']-meter['observed_at'];fresh=age<=value['maximum_meter_age']
                due_usage=row['last_service_usage']+row['usage_interval'];remaining_usage=due_usage-meter['total_usage']
                meter_due=meter['total_usage']>=due_usage if fresh else None
                if not fresh:c.issue(issues,'plans',index,'METER_STALE')
            state='due' if time_due is True or meter_due is True else 'unknown' if fresh is False else 'not_due'
            if state=='due':c.issue(issues,'plans',index,'MAINTENANCE_DUE')
            assessments.append(dict(id=key,asset_id=row['asset_id'],due_state=state,due_by_time=time_due,due_by_usage=meter_due,
                next_due_at=next_at,due_usage=due_usage,meter_fresh=fresh,meter_age=age,remaining_usage=remaining_usage,
                remaining_time=next_at-value['as_of'] if next_at is not None else None))
    result=c.base(raw,'outlands-maintenance-due-review-v1',dict(meters=mc,plans=pc),issues)
    result.update(as_of=value['as_of'],assessments=assessments,meter_sources_verified=False,interval_suitability_verified=False,
                  schedule_created=False,service_performed=False,live_clock_used=False)
    return result

def main(argv=None):return c.cli('Plan supplied service due states; no clock, scheduling or equipment control.',check,argv)
if __name__=='__main__':raise SystemExit(main())
