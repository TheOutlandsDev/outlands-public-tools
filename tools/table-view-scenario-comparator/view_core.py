"""Strict typed scalar filters, total ordering and pinned pagination; no SQL or UI."""
from collections import Counter
from functools import cmp_to_key
import toolkit as t
import decision_core as c

def column(row):
    key,out=c.record(row,{'id','type','nullable'},('id',));t.require(row['type'] in ('string','integer','boolean'),'COLUMN_TYPE_INVALID');t.require(type(row['nullable']) is bool,'NULLABLE_FLAG_INVALID');return key,out

def nested(value,parser,maximum,minimum=1):
    t.require(type(value) is list and minimum<=len(value)<=maximum,'NESTED_LIMIT');out={}
    for row in value:
        key,normalized=parser(row);t.require(key not in out,'NESTED_ID_DUPLICATE');out[key]=normalized
    return [out[k] for k in sorted(out)]

def scalar(value,col,nullable=True):
    if value is None:t.require(nullable and col['nullable'],'NULL_VALUE_INVALID');return
    t.require(type(value) is {'string':str,'integer':int,'boolean':bool}[col['type']],'SCALAR_TYPE_INVALID')
    if col['type']=='integer':t.integer(value,10**12,-10**12)
    if col['type']=='string':t.require(len(value)<=256,'STRING_LIMIT')

def view(row):
    key,out=c.record(row,{'id','revision','columns','predicates','sort','id_order'},('id',),('revision',));out['columns']=nested(row['columns'],column,32);cols={v['id']:v for v in out['columns']}
    t.require(row['id_order'] in ('asc','desc'),'ID_ORDER_INVALID')
    def predicate(v):
        k,p=c.record(v,{'id','field','op','value'},('id','field'));t.require(v['field'] in cols,'FIELD_UNKNOWN');t.require(v['op'] in ('eq','ne','lt','le','gt','ge','is_null','is_not_null'),'PREDICATE_OPERATOR_INVALID');col=cols[v['field']]
        if v['op'] in ('is_null','is_not_null'):t.require(v['value'] is None,'NULL_PREDICATE_VALUE_INVALID')
        else:
            scalar(v['value'],col,False)
            if col['type']=='boolean':t.require(v['op'] in ('eq','ne'),'BOOLEAN_ORDER_PREDICATE_INVALID')
        return k,p
    out['predicates']=nested(row['predicates'],predicate,16,0);t.require(type(row['sort']) is list and len(row['sort'])<=8,'SORT_LIMIT');out['sort']=[];seen=set()
    for v in row['sort']:
        t.fields(v,{'field','direction','nulls'});t.identifier(v['field']);t.require(v['field'] in cols,'FIELD_UNKNOWN');t.require(v['field'] not in seen,'SORT_FIELD_DUPLICATE');seen.add(v['field']);t.require(v['direction'] in ('asc','desc'),'SORT_DIRECTION_INVALID');t.require(v['nulls'] in ('first','last'),'NULL_ORDER_INVALID');out['sort'].append(dict(v))
    return key,out

def snapshot(row):
    key,out=c.record(row,{'id','revision','columns','rows'},('id',),('revision',));out['columns']=nested(row['columns'],column,32);cols={v['id']:v for v in out['columns']}
    def record(v):
        k,normalized=c.record(v,{'id','values'},('id',));t.fields(v['values'],set(cols))
        for field,col in cols.items():scalar(v['values'][field],col)
        return k,normalized
    out['rows']=nested(row['rows'],record,512,0);return key,out

def ordered_ids(value,maximum):
    t.require(type(value) is list and len(value)<=maximum,'ROW_ID_LIST_LIMIT')
    for v in value:t.identifier(v)
    return list(value)

def projection(row):
    key,out=c.record(row,{'id','revision','view','view_revision','view_sha256','snapshot','snapshot_revision','snapshot_sha256','row_ids'},('id','view','snapshot'),('revision','view_revision','snapshot_revision'))
    for k in ('view_sha256','snapshot_sha256'):t.sha(row[k])
    out['row_ids']=ordered_ids(row['row_ids'],512);return key,out

def plan(row):
    key,out=c.record(row,{'id','revision','projection','projection_revision','projection_sha256','page_size'},('id','projection'),('revision','projection_revision'));t.sha(row['projection_sha256']);t.integer(row['page_size'],128,1);return key,out

def page(row):
    key,out=c.record(row,{'id','revision','plan','plan_revision','plan_sha256','index','row_ids'},('id','plan'),('revision','plan_revision'));t.sha(row['plan_sha256']);t.integer(row['index'],511);out['row_ids']=ordered_ids(row['row_ids'],128);return key,out

def case(row):
    key,out=c.record(row,{'id','revision','baseline_view','baseline_view_revision','baseline_view_sha256','candidate_view','candidate_view_revision','candidate_view_sha256','snapshot','snapshot_revision','snapshot_sha256','page_size'},('id','baseline_view','candidate_view','snapshot'),('revision','baseline_view_revision','candidate_view_revision','snapshot_revision'))
    for k in ('baseline_view_sha256','candidate_view_sha256','snapshot_sha256'):t.sha(row[k])
    t.integer(row['page_size'],128,1);return key,out

def collect(value,parser,side,counts,issues,required=True,maximum=32):
    t.require(type(value) is list and len(value)<=maximum,'COHORT_LIMIT');rows,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not rows:c.issue(issues,side,0,'COHORT_EMPTY')
    return rows

def reference(row,name,records,side,position,issues):
    target=records.get(row[name])
    if target is None:c.issue(issues,side,position,'REFERENCE_UNKNOWN');return None
    selected=target[1]
    if row[name+'_revision']!=selected['revision'] or row[name+'_sha256']!=c.pin(selected):c.issue(issues,side,position,'SNAPSHOT_MISMATCH')
    return selected

def compatible(v,s,side,position,issues):
    if v['columns']!=s['columns']:c.issue(issues,side,position,'COLUMN_CONTRACT_MISMATCH')

def matches(value,predicate):
    op=predicate['op'];wanted=predicate['value']
    if op=='is_null':return value is None
    if op=='is_not_null':return value is not None
    if value is None:return False
    if op=='eq':return value==wanted
    if op=='ne':return value!=wanted
    if op=='lt':return value<wanted
    if op=='le':return value<=wanted
    if op=='gt':return value>wanted
    return value>=wanted

def evaluate(view,snapshot):
    records=[row for row in snapshot['rows'] if all(matches(row['values'][p['field']],p) for p in view['predicates'])]
    def compare(a,b):
        for rule in view['sort']:
            x,y=a['values'][rule['field']],b['values'][rule['field']]
            if x is None and y is None:continue
            if x is None:return -1 if rule['nulls']=='first' else 1
            if y is None:return 1 if rule['nulls']=='first' else -1
            difference=(x>y)-(x<y)
            if difference:return difference if rule['direction']=='asc' else -difference
        difference=(a['id']>b['id'])-(a['id']<b['id']);return difference if view['id_order']=='asc' else -difference
    return [row['id'] for row in sorted(records,key=cmp_to_key(compare))]

def sequence_check(actual,expected):
    counts=Counter(actual);wanted=set(expected);seen=set(actual)
    return dict(valid=actual==expected,missing_count=len(wanted-seen),unexpected_count=len(seen-wanted),duplicate_count=sum(v-1 for v in counts.values()),order_matches=actual==expected)

def windows(ids,size):return [ids[i:i+size] for i in range(0,len(ids),size)] or [[]]

def projection_context(value,counts,issues):
    views=collect(value['views'],view,'views',counts,issues);snapshots=collect(value['snapshots'],snapshot,'snapshots',counts,issues);projections=collect(value['projections'],projection,'projections',counts,issues,True,128)
    for _,(position,row) in sorted(projections.items()):
        v=reference(row,'view',views,'projections',position,issues);s=reference(row,'snapshot',snapshots,'projections',position,issues)
        if v is not None and s is not None:compatible(v,s,'projections',position,issues)
    return dict(views=views,snapshots=snapshots,projections=projections)

def projection_results(scope,issues):
    results={}
    for key,(position,row) in sorted(scope['projections'].items()):
        expected=evaluate(scope['views'][row['view']][1],scope['snapshots'][row['snapshot']][1]);result=sequence_check(row['row_ids'],expected);result.update(id=key,expected_row_ids=expected);results[key]=result
        if not result['valid']:c.issue(issues,'projections',position,'PROJECTION_MISMATCH')
    return results

def pagination(row,projection,records):
    expected=windows(projection['expected_row_ids'],row['page_size']);slots={}
    for record in records:slots.setdefault(record['index'],[]).append(record)
    wanted=set(range(len(expected)));actual=set(slots);missing=sorted(wanted-actual);unexpected=sorted(actual-wanted);duplicates=sorted(k for k,v in slots.items() if len(v)>1);complete=not (missing or unexpected or duplicates);pages=[]
    for index in sorted(wanted&actual):
        if len(slots[index])==1:pages.append(dict(index=index,expected_row_ids=expected[index],**sequence_check(slots[index][0]['row_ids'],expected[index])))
    coverage=sequence_check([v for i in range(len(expected)) for v in slots[i][0]['row_ids']],projection['expected_row_ids']) if complete else None
    return dict(id=row['id'],complete=complete,valid=complete and all(p['valid'] for p in pages) and coverage['valid'],expected_page_count=len(expected),missing_indices=missing,unexpected_indices=unexpected,duplicate_indices=duplicates,pages=pages,coverage=coverage)

def output(raw,mode,counts,issues,assessment,pins):
    out=c.base(raw,'outlands-table-view-'+mode+'-report-v1',counts,issues);qualified=assessment is not None
    out.update(assessment=assessment,cohort_sha256=pins if qualified else None,qualified_scope_sha256=c.pin(pins) if qualified and not issues else None,browser_started=False,dom_inspected=False,sql_executed=False,network_requests_performed=False,records_changed=False,raw_scalar_values_emitted=False,whole_view_compatibility_verified=False)
    return out

def check(raw,mode):
    value=t.decode(raw);fields={'views':{'views'},'projections':{'views','snapshots','projections'},'pages':{'views','snapshots','projections','plans','pages'},'scenarios':{'baseline_views','candidate_views','snapshots','cases'}}[mode]
    t.fields(value,fields|{'format'});t.require(value['format']=='outlands-table-view-'+mode+'-v1','FORMAT_INVALID');counts={};issues=[];assessment=None;pins={}
    if mode=='views':
        views=collect(value['views'],view,'views',counts,issues);pins['views']=c.cohort_pin(views)
        if not issues:assessment=dict(views=[dict(id=k,revision=v['revision'],sha256=c.pin(v),column_count=len(v['columns']),predicate_count=len(v['predicates']),sort_fields=[r['field'] for r in v['sort']],id_order=v['id_order']) for k,(_,v) in sorted(views.items())])
    elif mode in ('projections','pages'):
        scope=projection_context(value,counts,issues)
        if mode=='pages':
            scope['plans']=collect(value['plans'],plan,'plans',counts,issues);scope['pages']=collect(value['pages'],page,'pages',counts,issues,False,512)
            for _,(position,row) in sorted(scope['plans'].items()):reference(row,'projection',scope['projections'],'plans',position,issues)
            for _,(position,row) in sorted(scope['pages'].items()):reference(row,'plan',scope['plans'],'pages',position,issues)
        pins={k:c.cohort_pin(rows) for k,rows in scope.items()}
        if not issues:
            projections=projection_results(scope,issues);assessment=dict(projections=list(projections.values()))
            if mode=='pages':
                results=[]
                for key,(position,row) in sorted(scope['plans'].items()):
                    result=projections[row['projection']]
                    if not result['valid']:result=dict(id=key,complete=False,valid=False,expected_page_count=None,missing_indices=None,unexpected_indices=None,duplicate_indices=None,pages=None,coverage=None);c.issue(issues,'plans',position,'PAGINATION_WITHHELD_INVALID_PROJECTION')
                    else:
                        selected=[v for _,v in scope['pages'].values() if v['plan']==key];result=pagination(row,result,selected)
                        if not result['valid']:c.issue(issues,'plans',position,'PAGE_COVERAGE_MISMATCH')
                    results.append(result)
                assessment['plans']=results
    else:
        left=collect(value['baseline_views'],view,'baseline_views',counts,issues);right=collect(value['candidate_views'],view,'candidate_views',counts,issues);snapshots=collect(value['snapshots'],snapshot,'snapshots',counts,issues);cases=collect(value['cases'],case,'cases',counts,issues)
        scope=dict(baseline_views=left,candidate_views=right,snapshots=snapshots,cases=cases);pins={k:c.cohort_pin(rows) for k,rows in scope.items()}
        for k in left.keys()&right.keys():
            a=left[k][1];b=right[k][1]
            if a['revision']==b['revision'] and c.pin(a)!=c.pin(b):c.issue(issues,'candidate_views',right[k][0],'SAME_REVISION_DEFINITION_CONFLICT')
        for _,(position,row) in sorted(cases.items()):
            a=reference(row,'baseline_view',left,'cases',position,issues);b=reference(row,'candidate_view',right,'cases',position,issues);s=reference(row,'snapshot',snapshots,'cases',position,issues)
            if s is not None:
                for v in (a,b):
                    if v is not None:compatible(v,s,'cases',position,issues)
        if not issues:
            results=[]
            for k,(position,row) in sorted(cases.items()):
                s=snapshots[row['snapshot']][1];a=evaluate(left[row['baseline_view']][1],s);b=evaluate(right[row['candidate_view']][1],s);equal=a==b;results.append(dict(id=k,equal=equal,baseline_row_ids=a,candidate_row_ids=b,baseline_pages=windows(a,row['page_size']),candidate_pages=windows(b,row['page_size'])))
                if not equal:c.issue(issues,'cases',position,'VIEW_OUTCOME_CHANGED')
            assessment=dict(cases=results,all_selected_outcomes_equal=all(v['equal'] for v in results))
    return output(raw,mode,counts,issues,assessment,pins)
