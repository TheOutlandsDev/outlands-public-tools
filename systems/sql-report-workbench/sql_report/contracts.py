"""Portable neutral dataset/query contracts; no operating schema or connection input."""
import math
import re
from . import preflight,runtime as r


def fields(value,names):
    if type(value) is not dict or set(value)!=set(names):raise r.WorkbenchError('FIELDS_INVALID')


def token(value):
    if type(value) is not str or not re.fullmatch(r'[A-Za-z][A-Za-z0-9._-]{0,63}',value):raise r.WorkbenchError('IDENTITY_INVALID')
    reserved={'con','prn','aux','nul'}|{'com'+str(i) for i in range(1,10)}|{'lpt'+str(i) for i in range(1,10)}
    if value.endswith('.') or value.split('.',1)[0].casefold() in reserved:raise r.WorkbenchError('IDENTITY_NOT_PORTABLE')
    return value


def identifier(value):
    if type(value) is not str or not re.fullmatch('[a-z][a-z0-9_]{0,47}',value) or value.startswith('sqlite_'):raise r.WorkbenchError('SQL_IDENTIFIER_INVALID')
    return value


def integer(value,low,high):
    if type(value) is not int or not low<=value<=high:raise r.WorkbenchError('INTEGER_INVALID')
    return value


def text(value,maximum,empty=False,multiline=False):
    if type(value) is not str or len(value)>maximum or not empty and not value.strip() or any(ord(ch)<32 and (not multiline or ch not in '\r\n\t') for ch in value):raise r.WorkbenchError('TEXT_INVALID')
    try:value.encode('utf-8')
    except UnicodeError:raise r.WorkbenchError('TEXT_INVALID') from None
    return value


def hash_value(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}',value):raise r.WorkbenchError('HASH_INVALID')
    return value


def scalar(value,kind,nullable=True):
    if value is None:
        if not nullable:raise r.WorkbenchError('NULL_REFUSED')
        return None
    if kind=='integer':return integer(value,-10**12,10**12)
    if kind=='real':
        if type(value) not in (int,float) or not -10**12<=value<=10**12 or not math.isfinite(value):raise r.WorkbenchError('NUMBER_INVALID')
        return float(value)
    if kind=='text':return text(value,1000,empty=True,multiline=True)
    raise r.WorkbenchError('TYPE_INVALID')


def dataset(raw):
    value=r.decode(raw);fields(value,('format','dataset_id','title','tables'))
    if value['format']!='outlands-sql-dataset-v1':raise r.WorkbenchError('DATASET_FORMAT_INVALID')
    token(value['dataset_id']);text(value['title'],120);tables=value['tables']
    if type(tables) is not list or not 1<=len(tables)<=8:raise r.WorkbenchError('TABLE_LIMIT')
    seen=set();total=0
    for table in tables:
        fields(table,('name','columns','rows'));name=identifier(table['name'])
        if name in seen:raise r.WorkbenchError('TABLE_DUPLICATE')
        seen.add(name);columns=table['columns'];rows=table['rows']
        if type(columns) is not list or not 1<=len(columns)<=16 or type(rows) is not list or len(rows)>1000:raise r.WorkbenchError('TABLE_SHAPE_LIMIT')
        names=set()
        for column in columns:
            fields(column,('name','type','nullable'));identifier(column['name'])
            if column['name'] in names or column['type'] not in ('integer','real','text') or type(column['nullable']) is not bool:raise r.WorkbenchError('COLUMN_INVALID')
            names.add(column['name'])
        for row in rows:
            if type(row) is not list or len(row)!=len(columns):raise r.WorkbenchError('ROW_SHAPE_INVALID')
            for i,column in enumerate(columns):row[i]=scalar(row[i],column['type'],column['nullable'])
            if len(r.encode(row))>8192:raise r.WorkbenchError('ROW_SIZE_LIMIT')
        total+=len(rows)
    if total>5000:raise r.WorkbenchError('TOTAL_ROW_LIMIT')
    value['tables']=sorted(tables,key=lambda item:item['name']);return value


def sql(value):
    text(value,16384,multiline=True)
    if len(value.encode())>16384:raise r.WorkbenchError('SQL_SIZE_LIMIT')
    try:preflight._check_query(value)
    except ValueError:raise r.WorkbenchError('SQL_PREFLIGHT_REFUSED') from None
    masked=preflight._masked_sql(value)
    if any(marker in masked for marker in ('?','@','$')):raise r.WorkbenchError('NAMED_COLON_PARAMETERS_REQUIRED')
    return set(re.findall(r':([A-Za-z][A-Za-z0-9_]*)',masked))


def query(raw):
    value=r.decode(raw);fields(value,('format','query_id','title','sql','parameters'))
    if value['format']!='outlands-sql-query-v1':raise r.WorkbenchError('QUERY_FORMAT_INVALID')
    token(value['query_id']);text(value['title'],120);names=sql(value['sql']);definitions=value['parameters']
    if type(definitions) is not dict or len(definitions)>32 or set(definitions)!=names:raise r.WorkbenchError('PARAMETER_MAPPING_INVALID')
    for name,kind in definitions.items():
        identifier(name)
        if kind not in ('integer','real','text'):raise r.WorkbenchError('PARAMETER_TYPE_INVALID')
    return value


def bindings(value,definitions):
    if type(value) is not dict or set(value)!=set(definitions):raise r.WorkbenchError('BINDINGS_INVALID')
    return {name:scalar(value[name],kind) for name,kind in definitions.items()}
