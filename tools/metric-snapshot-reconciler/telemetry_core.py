"""Bounded exact metric snapshots, selected span graphs and declared reference consistency."""
from collections import deque
from fractions import Fraction
import re
import toolkit as t
import decision_core as c

def number(value):
    t.require(type(value) is str and re.fullmatch(r'-?(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,6})?',value),'NUMBER_INVALID')
    exact=Fraction(value);text=value.rstrip('0').rstrip('.') if '.' in value else value
    return exact,'0' if exact==0 else text
def collect(value,parser,side,counts,issues,required=True):
    selected,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not selected:c.issue(issues,side,0,'COHORT_EMPTY')
    return selected
def slots(rows,slot,side,issues):
    seen=set()
    for position,row in rows.values():
        key=slot(row)
        if key in seen:c.issue(issues,side,position,'SLOT_AMBIGUOUS')
        seen.add(key)
def reference(row,field,records,side,position,issues,revision=True):
    selected=records.get(row[field])
    if selected is None:c.issue(issues,side,position,'REFERENCE_UNKNOWN');return None
    target=selected[1]
    if row[field+'_sha256']!=c.pin(target) or (revision and row[field+'_revision']!=target['revision']):c.issue(issues,side,position,'SNAPSHOT_MISMATCH')
    return target
def labels(value):
    t.require(type(value) is dict and len(value)<=8,'LABEL_LIMIT')
    for key,item in value.items():t.identifier(key);t.identifier(item)
    return dict(value)
def definition(row):
    key,out=c.record(row,{'id','revision','kind','unit','label_keys','bounds','minimum','maximum'},('id','unit'),('revision',))
    t.require(row['kind'] in ('counter','gauge','histogram'),'METRIC_KIND_INVALID');out['label_keys']=c.tags(row['label_keys']);t.require(len(out['label_keys'])<=8,'LABEL_LIMIT')
    t.require(type(row['bounds']) is list and len(row['bounds'])<=16,'BUCKET_LIMIT');out['bounds']=[number(v)[1] for v in row['bounds']];bounds=[number(v)[0] for v in out['bounds']]
    t.require(all(a<b for a,b in zip(bounds,bounds[1:])),'BUCKET_ORDER_INVALID')
    for field in ('minimum','maximum'):
        if row[field] is not None:out[field]=number(row[field])[1]
    if row['kind']=='histogram':t.require(row['minimum'] is None and row['maximum'] is None,'HISTOGRAM_SCALAR_LIMIT_INVALID')
    else:
        t.require(not bounds,'SCALAR_BUCKETS_INVALID')
        if out['minimum'] is not None and out['maximum'] is not None:t.require(number(out['minimum'])[0]<=number(out['maximum'])[0],'VALUE_LIMIT_ORDER_INVALID')
        if row['kind']=='counter':t.require(out['minimum']=='0' and (out['maximum'] is None or number(out['maximum'])[0]>=0),'COUNTER_LIMIT_INVALID')
    return key,out
def series(row):
    key,out=c.record(row,{'id','metric','metric_revision','metric_sha256','labels','required'},('id','metric'),('metric_revision',));t.sha(row['metric_sha256']);out['labels']=labels(row['labels']);t.require(type(row['required']) is bool,'REQUIRED_FLAG_INVALID');return key,out
def metric_contract(value,counts,issues):
    definitions=collect(value['definitions'],definition,'definitions',counts,issues);series_rows=collect(value['series'],series,'series',counts,issues)
    slots(series_rows,lambda row:(row['metric'],tuple(sorted(row['labels'].items()))),'series',issues)
    for position,row in series_rows.values():
        target=reference(row,'metric',definitions,'series',position,issues)
        if target is not None and set(row['labels'])!=set(target['label_keys']):c.issue(issues,'series',position,'LABEL_KEYS_MISMATCH')
    return definitions,series_rows
def run(row):
    key,out=c.record(row,{'id','revision','clock','minimum_at','maximum_at'},('id','clock'),('revision',));t.integer(row['minimum_at'],10**12);t.integer(row['maximum_at'],10**12);t.require(row['minimum_at']<=row['maximum_at'],'RUN_INTERVAL_INVALID');return key,out
def point(row):
    key,out=c.record(row,{'id','series','series_sha256','run','run_revision','run_sha256','at','value','count','sum','buckets'},('id','series','run'),('run_revision',));t.sha(row['series_sha256']);t.sha(row['run_sha256']);t.integer(row['at'],10**12)
    for field in ('value','sum'):
        if row[field] is not None:out[field]=number(row[field])[1]
    if row['count'] is not None:t.integer(row['count'],10**12)
    t.require(type(row['buckets']) is list and len(row['buckets'])<=17,'BUCKET_LIMIT')
    for value in row['buckets']:t.integer(value,10**12)
    return key,out
def metric_context(value,counts,issues):
    definitions,series_rows=metric_contract(value,counts,issues);runs=collect(value['runs'],run,'runs',counts,issues);points=collect(value['points'],point,'points',counts,issues,False)
    t.require(len(series_rows)*len(runs)<=20000,'METRIC_COVERAGE_LIMIT');slots(points,lambda row:(row['series'],row['run']),'points',issues)
    for position,row in points.values():
        chosen=reference(row,'series',series_rows,'points',position,issues,False);reference(row,'run',runs,'points',position,issues)
        metric=definitions.get(chosen['metric']) if chosen is not None else None
        if metric is not None:
            if metric[1]['kind']=='histogram':
                if not(row['value'] is None and row['count'] is not None and row['sum'] is not None and len(row['buckets'])==len(metric[1]['bounds'])+1):c.issue(issues,'points',position,'POINT_PAYLOAD_INVALID')
            elif not(row['value'] is not None and row['count'] is None and row['sum'] is None and row['buckets']==[]):c.issue(issues,'points',position,'POINT_PAYLOAD_INVALID')
    qualified=not issues;assessment=None
    if qualified:
        out=[];valid={};selected={}
        for key,(position,row) in sorted(points.items()):
            metric=definitions[series_rows[row['series']][1]['metric']][1];scope=runs[row['run']][1];failed=[]
            if not scope['minimum_at']<=row['at']<=scope['maximum_at']:failed.append('POINT_TIME_OUTSIDE_RUN')
            if metric['kind']=='histogram':
                if sum(row['buckets'])!=row['count']:failed.append('HISTOGRAM_COUNT_MISMATCH')
                if row['count']==0 and number(row['sum'])[0]!=0:failed.append('EMPTY_HISTOGRAM_SUM_NONZERO')
            else:
                exact=number(row['value'])[0]
                if metric['minimum'] is not None and exact<number(metric['minimum'])[0]:failed.append('VALUE_BELOW_MINIMUM')
                if metric['maximum'] is not None and exact>number(metric['maximum'])[0]:failed.append('VALUE_ABOVE_MAXIMUM')
            for code in failed:c.issue(issues,'points',position,code)
            valid[key]=not failed;selected[(row['series'],row['run'])]=key
            out.append(dict(id=key,series=row['series'],run=row['run'],kind=metric['kind'],consistent=not failed,failed_criteria=failed,value=row['value'],count=row['count'],sum=row['sum'],buckets=row['buckets']))
        coverage=[]
        for series_id,(_,selected_series) in sorted(series_rows.items()):
            for run_id in sorted(runs):
                key=selected.get((series_id,run_id));state='valid' if key is not None and valid[key] else 'invalid' if key is not None else 'required_missing' if selected_series['required'] else 'optional_absent'
                if state=='required_missing':c.issue(issues,'coverage',0,'REQUIRED_POINT_MISSING')
                coverage.append(dict(series=series_id,run=run_id,state=state,point_id=key))
        assessment=dict(points=out,coverage=coverage,underlying_observations_verified=False)
    return dict(definitions=definitions,series=series_rows,runs=runs,points=points,assessment=assessment,qualified=qualified)
def trace(row):
    key,out=c.record(row,{'id','revision','run','run_revision','run_sha256','complete','expected_spans'},('id','run'),('revision','run_revision'));t.sha(row['run_sha256']);t.require(type(row['complete']) is bool,'COMPLETE_FLAG_INVALID')
    t.require(type(row['expected_spans']) is list and 1<=len(row['expected_spans'])<=128,'EXPECTED_SPAN_LIMIT')
    for span in row['expected_spans']:t.identifier(span)
    t.require(len(set(row['expected_spans']))==len(row['expected_spans']),'EXPECTED_SPAN_DUPLICATE');out['expected_spans']=sorted(row['expected_spans']);return key,out
def span(row):
    key,out=c.record(row,{'id','trace','trace_revision','trace_sha256','parent','start','end'},('id','trace'),('trace_revision',));t.sha(row['trace_sha256'])
    if row['parent'] is not None:t.identifier(row['parent'])
    t.integer(row['start'],10**12);t.integer(row['end'],10**12);t.require(row['end']>=row['start'],'SPAN_INTERVAL_INVALID');return key,out
def trace_context(value,counts,issues,runs=None):
    local=[]
    if runs is None:runs=collect(value['runs'],run,'runs',counts,local)
    traces=collect(value['traces'],trace,'traces',counts,local);spans=collect(value['spans'],span,'spans',counts,local,False)
    t.require(sum(len(row['expected_spans']) for _,row in traces.values())<=4096,'TRACE_EXPECTATION_SCOPE_LIMIT');expected_owners={}
    for position,row in traces.values():
        reference(row,'run',runs,'traces',position,local)
        for key in row['expected_spans']:
            if key in expected_owners:c.issue(local,'traces',position,'EXPECTED_SPAN_OWNERSHIP_AMBIGUOUS')
            expected_owners[key]=row['id']
    for position,row in spans.values():
        reference(row,'trace',traces,'spans',position,local)
        if row['parent'] is not None:
            parent=spans.get(row['parent'])
            if parent is None:c.issue(local,'spans',position,'PARENT_UNKNOWN')
            elif parent[1]['trace']!=row['trace']:c.issue(local,'spans',position,'PARENT_TRACE_MISMATCH')
    if not local:
        waiting={key:0 if row['parent'] is None else 1 for key,(_,row) in spans.items()};children={key:[] for key in spans}
        for key,(_,row) in spans.items():
            if row['parent'] is not None:children[row['parent']].append(key)
        pending=deque(sorted(key for key,n in waiting.items() if n==0));visited=0
        while pending:
            key=pending.popleft();visited+=1
            for child in sorted(children[key]):
                waiting[child]-=1
                if waiting[child]==0:pending.append(child)
        if visited!=len(spans):c.issue(local,'spans',0,'SPAN_CYCLE')
    qualified=not local;assessment=None
    if qualified:
        rows=[];durations=[]
        for key,(position,row) in sorted(traces.items()):
            selected=[(p,span) for p,span in spans.values() if span['trace']==key];actual={span['id'] for _,span in selected};roots=sorted(span['id'] for _,span in selected if span['parent'] is None);missing=sorted(set(row['expected_spans'])-actual);extra=sorted(actual-set(row['expected_spans']))
            if not row['complete']:c.issue(local,'traces',position,'TRACE_DECLARED_PARTIAL')
            if missing:c.issue(local,'traces',position,'SPAN_COVERAGE_MISSING')
            if extra:c.issue(local,'traces',position,'SPAN_NOT_EXPECTED')
            if len(roots)!=1:c.issue(local,'traces',position,'TRACE_ROOT_COUNT_INVALID')
            scope=runs[row['run']][1]
            for span_position,item in selected:
                if not(scope['minimum_at']<=item['start']<=item['end']<=scope['maximum_at']):c.issue(local,'spans',span_position,'SPAN_TIME_OUTSIDE_RUN')
                durations.append(dict(id=item['id'],declared_duration=item['end']-item['start']))
            rows.append(dict(id=key,root_ids=roots,observed_span_count=len(selected),missing_span_ids=missing,unexpected_span_ids=extra,complete_declared=row['complete'],observed_start=min((span['start'] for _,span in selected),default=None),observed_end=max((span['end'] for _,span in selected),default=None)))
        assessment=dict(traces=rows,spans=sorted(durations,key=lambda row:row['id']),parent_containment_assumed=False,causal_order_verified=False)
    issues.extend(local);return dict(runs=runs,traces=traces,spans=spans,assessment=assessment,qualified=qualified)
def output(raw,fmt,counts,issues,qualified,assessment,pins):
    report=c.base(raw,fmt,counts,issues);report.update(assessment=assessment,qualified_scope_sha256=c.pin(dict(format=fmt,**pins)) if qualified and not issues else None,
        telemetry_collected=False,services_contacted=False,clocks_read=False,instrumentation_executed=False,artifact_bytes_verified=False,metrics_emitted=False,causation_inferred=False,records_changed=False)
    report.update({key:value if qualified else None for key,value in pins.items()});return report
