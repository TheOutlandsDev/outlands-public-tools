"""Strict offline grouping and exact aggregate checks over supplied fictional rows."""
from collections import defaultdict
from decimal import Decimal
import re
import toolkit as t
import decision_core as c

def decimal(value):
    t.require(type(value) is str and re.fullmatch(r'-?(?:0|[1-9][0-9]{0,12})(?:\.[0-9]{1,6})?',value),'DECIMAL_INVALID')
    return Decimal(value)

def column(row):
    key,out=c.record(row,{'id','type','nullable'},('id',))
    t.require(row['type'] in ('string','integer','decimal','boolean'),'COLUMN_TYPE_INVALID')
    t.require(type(row['nullable']) is bool,'NULLABLE_INVALID')
    return key,out

def unique(value,parser,maximum,minimum=1):
    t.require(type(value) is list and minimum<=len(value)<=maximum,'COHORT_LIMIT')
    out={}
    for row in value:
        key,item=parser(row);t.require(key not in out,'NESTED_ID_DUPLICATE');out[key]=item
    return [out[k] for k in sorted(out)]

def scalar(value,col):
    if value is None:t.require(col['nullable'],'NULL_INVALID');return None
    kind=col['type']
    if kind=='integer':t.integer(value,10**12,-10**12);return value
    if kind=='decimal':return decimal(value)
    if kind=='boolean':t.require(type(value) is bool,'BOOLEAN_INVALID');return value
    t.require(type(value) is str and len(value)<=256,'STRING_INVALID');return value

def definition(row):
    key,out=c.record(row,{'id','revision','columns','group_by','measures'},('id',),('revision',))
    out['columns']=unique(row['columns'],column,32);cols={x['id']:x for x in out['columns']}
    t.require(type(row['group_by']) is list and 1<=len(row['group_by'])<=4,'GROUP_BY_INVALID')
    for field in row['group_by']:
        t.identifier(field);t.require(field in cols and cols[field]['type']!='decimal','GROUP_FIELD_INVALID')
    t.require(len(set(row['group_by']))==len(row['group_by']),'GROUP_FIELD_DUPLICATE')
    def measure(v):
        k,m=c.record(v,{'id','field','op'},('id',))
        t.require(v['op'] in ('count_rows','count_values','sum','min','max'),'MEASURE_OP_INVALID')
        t.require(v['field'] is None if v['op']=='count_rows' else v['field'] in cols,'MEASURE_FIELD_INVALID')
        if v['op'] in ('sum','min','max'):t.require(cols[v['field']]['type'] in ('integer','decimal'),'MEASURE_TYPE_INVALID')
        return k,m
    out['measures']=unique(row['measures'],measure,16)
    return key,out

def snapshot(row):
    key,out=c.record(row,{'id','revision','columns','rows'},('id',),('revision',))
    out['columns']=unique(row['columns'],column,32);cols={x['id']:x for x in out['columns']}
    def item(v):
        k,r=c.record(v,{'id','values'},('id',));t.fields(v['values'],set(cols))
        for field,col in cols.items():scalar(v['values'][field],col)
        return k,r
    out['rows']=unique(row['rows'],item,512,0)
    return key,out

def claim(row):
    key,out=c.record(row,{'id','revision','definition','definition_revision','definition_sha256','snapshot','snapshot_revision','snapshot_sha256','groups'},('id','definition','snapshot'),('revision','definition_revision','snapshot_revision'))
    for name in ('definition_sha256','snapshot_sha256'):t.sha(row[name])
    def group(v):
        k,g=c.record(v,{'id','key','row_ids','values'},('id',))
        t.require(type(v['key']) is list and len(v['key'])<=4,'GROUP_KEY_INVALID')
        t.require(type(v['row_ids']) is list and len(v['row_ids'])<=512,'ROW_IDS_INVALID')
        for rid in v['row_ids']:t.identifier(rid)
        t.require(type(v['values']) is dict,'VALUES_INVALID')
        return k,g
    out['groups']=unique(row['groups'],group,512,0)
    return key,out

def scenario(row):
    key,out=c.record(row,{'id','revision','baseline','baseline_revision','baseline_sha256','candidate','candidate_revision','candidate_sha256','snapshot','snapshot_revision','snapshot_sha256'},('id','baseline','candidate','snapshot'),('revision','baseline_revision','candidate_revision','snapshot_revision'))
    for name in ('baseline_sha256','candidate_sha256','snapshot_sha256'):t.sha(row[name])
    return key,out

def collect(value,parser,name,counts,issues,minimum=1,maximum=32):
    t.require(type(value) is list and minimum<=len(value)<=maximum,'COHORT_LIMIT')
    records,counts[name],found=c.rows(value,parser,name);issues.extend(found)
    if minimum and not records:c.issue(issues,name,0,'COHORT_EMPTY')
    return records

def reference(row,name,records,side,position,issues):
    selected=records.get(row[name])
    if selected is None:c.issue(issues,side,position,'REFERENCE_UNKNOWN');return None
    item=selected[1]
    if row[name+'_revision']!=item['revision'] or row[name+'_sha256']!=c.pin(item):c.issue(issues,side,position,'SNAPSHOT_MISMATCH')
    return item

def grouped(definition,snapshot):
    cols={x['id']:x for x in definition['columns']}
    t.require(definition['columns']==snapshot['columns'],'COLUMN_MISMATCH')
    members=defaultdict(list)
    for row in snapshot['rows']:
        key=tuple(row['values'][f] for f in definition['group_by'])
        members[key].append(row)
    results=[]
    for key,rows in members.items():
        vals={}
        for m in definition['measures']:
            op=m['op'];field=m['field']
            nonnull=[scalar(r['values'][field],cols[field]) for r in rows if field is not None and r['values'][field] is not None]
            if op=='count_rows':answer=len(rows)
            elif op=='count_values':answer=len(nonnull)
            elif op=='sum':answer=sum(nonnull) if nonnull else None
            elif op=='min':answer=min(nonnull) if nonnull else None
            else:answer=max(nonnull) if nonnull else None
            vals[m['id']]=str(answer) if isinstance(answer,Decimal) else answer
        results.append(dict(key=list(key),row_ids=sorted(r['id'] for r in rows),values=vals))
    return sorted(results,key=lambda x:t.encode(x['key']))

def compare_groups(actual,expected,mode):
    findings=[];selected=[]
    for g in actual:
        matches=[e for e in expected if e['key']==g['key']]
        if len(matches)!=1:findings.append('UNKNOWN_GROUP_KEY');continue
        e=matches[0];selected.append(t.encode(g['key']))
        if len(g['row_ids'])!=len(set(g['row_ids'])):findings.append('DUPLICATE_CONTRIBUTOR')
        if sorted(g['row_ids'])!=e['row_ids']:findings.append('MEMBERSHIP_MISMATCH')
        if mode=='aggregates':
            if set(g['values'])!=set(e['values']):findings.append('MEASURE_SET_MISMATCH')
            elif g['values']!=e['values']:findings.append('AGGREGATE_MISMATCH')
    if len(selected)!=len(expected) or len(set(selected))!=len(selected):findings.append('GROUP_COVERAGE_MISMATCH')
    return sorted(set(findings))

def check(raw,mode):
    value=t.decode(raw);required={'contracts':{'definitions'},'membership':{'definitions','snapshots','claims'},'aggregates':{'definitions','snapshots','claims'},'scenarios':{'baseline_definitions','candidate_definitions','snapshots','scenarios'}}[mode]
    t.fields(value,required|{'format'});t.require(value['format']=='outlands-grouped-report-'+mode+'-v1','FORMAT_INVALID')
    counts={};issues=[];assessment=None
    if mode=='scenarios':
        left=collect(value['baseline_definitions'],definition,'baseline_definitions',counts,issues)
        right=collect(value['candidate_definitions'],definition,'candidate_definitions',counts,issues)
        snaps=collect(value['snapshots'],snapshot,'snapshots',counts,issues)
        cases=collect(value['scenarios'],scenario,'scenarios',counts,issues)
        for _,(pos,item) in sorted(cases.items()):
            a=reference(item,'baseline',left,'scenarios',pos,issues);b=reference(item,'candidate',right,'scenarios',pos,issues);s=reference(item,'snapshot',snaps,'scenarios',pos,issues)
            if a is not None and s is not None and a['columns']!=s['columns']:c.issue(issues,'scenarios',pos,'COLUMN_MISMATCH')
            if b is not None and s is not None and b['columns']!=s['columns']:c.issue(issues,'scenarios',pos,'COLUMN_MISMATCH')
        if not issues:
            assessment=[]
            for k,(pos,item) in sorted(cases.items()):
                s=snaps[item['snapshot']][1];a=grouped(left[item['baseline']][1],s);b=grouped(right[item['candidate']][1],s)
                equal=a==b;assessment.append(dict(id=k,equal=equal,baseline=a,candidate=b))
                if not equal:c.issue(issues,'scenarios',pos,'GROUPED_OUTCOME_CHANGED')
        cohorts={'baseline_definitions':left,'candidate_definitions':right,'snapshots':snaps,'scenarios':cases}
    else:
        defs=collect(value['definitions'],definition,'definitions',counts,issues)
        cohorts={'definitions':defs}
        if mode=='contracts':
            if not issues:assessment=[dict(id=k,revision=d['revision'],sha256=c.pin(d),groups=d['group_by'],measures=[m['id'] for m in d['measures']]) for k,(_,d) in sorted(defs.items())]
        else:
            snaps=collect(value['snapshots'],snapshot,'snapshots',counts,issues);claims=collect(value['claims'],claim,'claims',counts,issues);cohorts.update(snapshots=snaps,claims=claims)
            for _,(pos,item) in sorted(claims.items()):
                d=reference(item,'definition',defs,'claims',pos,issues);s=reference(item,'snapshot',snaps,'claims',pos,issues)
                if d is not None and s is not None and d['columns']!=s['columns']:c.issue(issues,'claims',pos,'COLUMN_MISMATCH')
            if not issues:
                assessment=[]
                for k,(pos,item) in sorted(claims.items()):
                    expected=grouped(defs[item['definition']][1],snaps[item['snapshot']][1]);findings=compare_groups(item['groups'],expected,mode)
                    assessment.append(dict(id=k,expected=expected,findings=findings))
                    for code in findings:c.issue(issues,'claims',pos,code)
    out=c.base(raw,'outlands-grouped-report-'+mode+'-report-v1',counts,issues)
    pins={name:c.cohort_pin(records) for name,records in cohorts.items()}
    out.update(assessment=assessment,cohort_sha256=pins if assessment is not None else None,qualified_scope_sha256=c.pin(pins) if assessment is not None and not issues else None,sql_executed=False,database_opened=False,network_requests_performed=False,source_completeness_verified=False,target_changes_performed=False)
    return out
