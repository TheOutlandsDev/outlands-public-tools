"""Bounded declared schemas, typed supplied rows and exact key identity."""
from decimal import Decimal
import re
import toolkit as t

TYPES=('integer','decimal','text','boolean')


def names(value,maximum=4,empty=False):
    t.require(type(value) is list and (0 if empty else 1)<=len(value)<=maximum,'NAME_LIST_INVALID')
    for name in value: t.identifier(name)
    t.require(len(set(value))==len(value),'DUPLICATE_NAME')
    return list(value)


def columns(value):
    t.require(type(value) is list and 1<=len(value)<=16,'COLUMN_LIMIT')
    result=[]
    for col in value:
        t.fields(col,{'name','type','nullable'}); t.identifier(col['name'])
        t.require(col['type'] in TYPES and type(col['nullable']) is bool,'COLUMN_INVALID')
        result.append(dict(col))
    t.require(len({col['name'] for col in result})==len(result),'DUPLICATE_COLUMN')
    return result


def schema(value):
    t.fields(value,{'tables'})
    t.require(type(value['tables']) is list and 1<=len(value['tables'])<=8,'TABLE_LIMIT')
    tables={}
    for row in value['tables']:
        t.fields(row,{'name','columns','primary_key','foreign_keys'}); name=t.identifier(row['name'])
        t.require(name not in tables,'DUPLICATE_TABLE')
        cols=columns(row['columns']); by_name={col['name']:col for col in cols}
        pk=names(row['primary_key'],empty=True)
        t.require(set(pk)<=set(by_name) and all(not by_name[k]['nullable'] for k in pk),'PRIMARY_KEY_INVALID')
        fks=row['foreign_keys']; t.require(type(fks) is list and len(fks)<=16,'FOREIGN_KEY_LIMIT')
        selected=[]; seen=set()
        for fk in fks:
            t.fields(fk,{'name','columns','table','references','null_policy'})
            t.identifier(fk['name']); t.identifier(fk['table'])
            t.require(fk['name'] not in seen,'DUPLICATE_CONSTRAINT'); seen.add(fk['name'])
            source=names(fk['columns']); target=names(fk['references'])
            t.require(set(source)<=set(by_name) and len(source)==len(target),'FOREIGN_KEY_INVALID')
            t.require(fk['null_policy'] in ('skip_any','reject'),'NULL_POLICY_INVALID')
            selected.append(dict(name=fk['name'],columns=source,table=fk['table'],references=target,null_policy=fk['null_policy']))
        tables[name]=dict(name=name,columns=cols,primary_key=pk,foreign_keys=selected)
    for table in tables.values():
        source={col['name']:col for col in table['columns']}
        for fk in table['foreign_keys']:
            t.require(fk['table'] in tables,'REFERENCE_TABLE_MISSING')
            target=tables[fk['table']]; target_cols={col['name']:col for col in target['columns']}
            t.require(fk['references']==target['primary_key'],'REFERENCE_MUST_MATCH_PRIMARY_KEY')
            t.require(all(source[a]['type']==target_cols[b]['type'] for a,b in zip(fk['columns'],fk['references'])),'REFERENCE_TYPE_MISMATCH')
    return dict(tables=list(tables.values()))


def text(value,maximum=256,empty=True):
    t.require(type(value) is str and (0 if empty else 1)<=len(value)<=maximum,'TEXT_INVALID')
    t.require(all((ord(c)>=32 or c in '\n\r\t') and not 0x7f<=ord(c)<=0x9f for c in value),'TEXT_CONTROL_INVALID')
    return value


def scalar(value,col):
    if value is None:
        t.require(col['nullable'],'NULL_NOT_ALLOWED'); return None
    kind=col['type']
    if kind=='integer': return t.integer(value,10**12,-10**12)
    if kind=='boolean':
        t.require(type(value) is bool,'BOOLEAN_INVALID'); return value
    if kind=='text': return text(value)
    t.require(type(value) is str and re.fullmatch(r'-?(?:0|[1-9][0-9]{0,12})(?:\.[0-9]{1,6})?',value),'DECIMAL_INVALID')
    number=Decimal(value); t.require(number.copy_abs()<=10**12,'DECIMAL_LIMIT')
    out=format(number,'f')
    if '.' in out: out=out.rstrip('0').rstrip('.')
    return '0' if number==0 else out


def issue(issues,table,row,code,constraint=None):
    issues.append(dict(table=table,row=row,code=code,constraint=constraint))


def rows(raw,cols,table):
    t.require(type(raw) is list and len(raw)<=1000,'ROW_LIMIT')
    accepted=[]; issues=[]
    for index,row in enumerate(raw,1):
        try:
            t.require(type(row) is list and len(row)==len(cols),'ROW_SHAPE_INVALID')
            accepted.append((index,[scalar(value,col) for value,col in zip(row,cols)]))
        except t.Rejected as error: issue(issues,table,index,str(error))
    return accepted,dict(input_rows=len(raw),accepted_rows=len(accepted),rejected_rows=len(raw)-len(accepted)),issues


def dataset(value):
    t.fields(value,{'schema','tables'}); declared=schema(value['schema'])
    specs={row['name']:row for row in declared['tables']}
    t.require(type(value['tables']) is list and len(value['tables'])==len(specs),'DATA_TABLE_COVERAGE_INVALID')
    selected={}; counts={}; issues=[]; total=0
    for table in value['tables']:
        t.fields(table,{'name','rows'}); name=t.identifier(table['name'])
        t.require(name in specs and name not in selected,'DATA_TABLE_COVERAGE_INVALID')
        values,accounting,other=rows(table['rows'],specs[name]['columns'],name)
        total+=accounting['input_rows']; t.require(total<=1000,'TOTAL_ROW_LIMIT')
        selected[name]=values; counts[name]=accounting; issues+=other
    return declared,selected,counts,issues


def indices(spec,selected):
    cols={col['name']:i for i,col in enumerate(spec['columns'])}
    t.require(set(selected)<=set(cols),'KEY_COLUMN_MISSING')
    return [cols[name] for name in selected]


def key(row,positions): return t.encode([row[i] for i in positions])


def base(raw,fmt,counts,issues):
    return dict(format=fmt,status='REVIEW_REQUIRED' if issues else 'PASS',input_sha256=t.digest(raw),
                counts=counts,issues=sorted(issues,key=lambda row:(row['table'],row['row'],row['code'],row['constraint'] or '')),
                source_authority_verified=False,content_privacy_verified=False,sql_executed=False,target_changes_performed=False)


def cli(description,operation,argv=None):
    p=t.Parser(description=description); p.add_argument('--input',required=True); p.add_argument('--out')
    return t.run(p,lambda a:operation(t.read(a.input)),argv)
