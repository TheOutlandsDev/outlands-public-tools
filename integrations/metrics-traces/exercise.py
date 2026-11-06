"""Installed fictional metrics-to-trace exercise; no instrumentation or collection."""
import copy
import hashlib
import json
from importlib.resources import files
from outlands_metric_definition_contract_checker.definitions import check as definitions
from outlands_metric_snapshot_reconciler.snapshots import check as snapshots
from outlands_trace_structure_checker.traces import check as traces
from outlands_metric_trace_correlation_checker.correlations import check as correlations

def raw(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')

def pin(value):
    return hashlib.sha256(raw(value)).hexdigest()

def select(scope,fmt,keys):
    return dict(format=fmt,**{key:copy.deepcopy(scope[key]) for key in keys})

def move_point(scope,at):
    value=copy.deepcopy(scope)
    point=next(row for row in value['points'] if row['id']=='point-latency')
    point['at']=at
    for row in value['requirements']+value['links']:
        if row['point']==point['id']:row['point_sha256']=pin(point)
    for row in value['links']:row['at']=at
    return value

def main():
    scope=json.loads(files('outlands_metric_trace_correlation_checker').joinpath('examples','input.json').read_bytes())
    d=select(scope,'outlands-metric-definitions-v1',('definitions','series'))
    m=select(scope,'outlands-metric-snapshots-v1',('definitions','series','runs','points'))
    t=select(scope,'outlands-trace-structure-v1',('runs','traces','spans'))
    dr=definitions(raw(d));mr=snapshots(raw(m));tr=traces(raw(t));cr=correlations(raw(scope))
    assert dr['status']==mr['status']==tr['status']==cr['status']=='PASS'
    for key in ('definitions_sha256','series_sha256'):assert dr[key]==mr[key]==cr[key]
    assert mr['runs_sha256']==tr['runs_sha256']==cr['runs_sha256']
    assert mr['points_sha256']==cr['points_sha256'] and tr['spans_sha256']==cr['spans_sha256']
    assert all(row['state']=='valid' for row in mr['assessment']['coverage'])
    assert cr['assessment']['requirements'][0]['covered'] is True
    span=next(row for row in scope['spans'] if row['id']=='span-preview')
    assert (span['start'],span['end'])==(12,18)
    start=correlations(raw(move_point(scope,12)));assert start['status']=='PASS'
    end=correlations(raw(move_point(scope,18)))
    assert end['status']=='REVIEW_REQUIRED' and end['assessment'] is not None and end['qualified_scope_sha256'] is None
    assert any(row['code']=='LINK_TIME_OUTSIDE_SPAN' for row in end['issues'])
    missing=copy.deepcopy(scope);missing['points']=[row for row in missing['points'] if row['id']!='point-completed']
    missing_report=correlations(raw(missing));assert missing_report['status']=='REVIEW_REQUIRED' and missing_report['assessment'] is None
    missing_trace=copy.deepcopy(t);missing_trace['spans']=[row for row in missing_trace['spans'] if row['id']!='span-input']
    partial=traces(raw(missing_trace));assert partial['status']=='REVIEW_REQUIRED' and partial['assessment'] is not None
    bad_histogram=copy.deepcopy(m);hist=next(row for row in bad_histogram['points'] if row['id']=='point-latency')
    assert hist['buckets']==[1,1,0] and hist['count']==2
    hist['count']=3;bad=snapshots(raw(bad_histogram));assert bad['status']=='REVIEW_REQUIRED' and bad['assessment'] is not None
    stale=copy.deepcopy(scope);stale['links'][0]['span_sha256']='0'*64
    withheld=correlations(raw(stale));assert withheld['status']=='REVIEW_REQUIRED' and withheld['assessment'] is None
    for report in (dr,mr,tr,cr,start,end,missing_report,partial,bad,withheld):
        for key in ('telemetry_collected','services_contacted','clocks_read','instrumentation_executed','artifact_bytes_verified','metrics_emitted','causation_inferred','records_changed','target_changes_performed'):assert report[key] is False
    assert cr['assessment']['semantic_relationship_verified'] is False and cr['assessment']['clock_synchronization_verified'] is False
    print(json.dumps(dict(status='PASS',metric_points=3,spans=3,required_links=1,link_start='included',link_end='excluded',missing_metric='correlation withheld',missing_span='REVIEW_REQUIRED',bucket_count_mismatch='REVIEW_REQUIRED',stale_pin='assessment withheld',causation_inferred=False),sort_keys=True))

if __name__=='__main__':
    main()
