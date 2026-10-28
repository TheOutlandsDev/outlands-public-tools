"""Exact request schemas, portable selectors and bounded scalar normalization."""
import re
from . import runtime as r

ZERO='0'*64
MAX_ROWS=1000
MAX_SOURCES=8
MAX_FIELDS=16
MAX_JOBS=64
MAX_EVENTS=256
MAX_SOURCE=1024*1024
MAX_PLAN=3*1024*1024
MAX_OUTPUT_STORE=8*1024*1024
RESERVED={'con','prn','aux','nul',*{p+str(i) for p in ('com','lpt') for i in range(1,10)}}

def fail(code):raise r.WorkbenchError(code)
def fields(value,names):
    if type(value) is not dict or set(value)!=set(names):fail('FIELDS_INVALID')
def integer(value,low,high):
    if type(value) is not int or not low<=value<=high:fail('INTEGER_INVALID')
    return value
def text(value,maximum=400,empty=False):
    if type(value) is not str or (not empty and not value.strip()) or len(value)>maximum:fail('TEXT_INVALID')
    if any(ord(ch)<32 and ch not in '\n\r\t' for ch in value):fail('TEXT_CONTROL_REFUSED')
    try:raw=value.encode('utf-8')
    except UnicodeError:fail('TEXT_ENCODING_INVALID')
    if len(raw)>maximum:fail('TEXT_SIZE_LIMIT')
    return value
def choice(value,values):
    if type(value) is not str or value not in values:fail('CHOICE_INVALID')
    return value
def pin(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}',value):fail('HASH_INVALID')
    return value
def identifier(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{32}',value):fail('IDENTIFIER_INVALID')
    return value
def field_name(value):
    if type(value) is not str or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,31}',value):fail('FIELD_NAME_INVALID')
    return value
def selector(value):
    if type(value) is not str or not 1<=len(value)<=240:fail('SELECTOR_INVALID')
    parts=value.split('/')
    if not 2<=len(parts)<=8 or parts[0]!='inbox':fail('SELECTOR_INVALID')
    for part in parts:
        if not re.fullmatch('[A-Za-z0-9_. -]{1,64}',part) or part in ('.','..') or part.endswith(('.',' ')) or part.split('.')[0].casefold() in RESERVED:fail('SELECTOR_INVALID')
    return value
def checks(value):
    fields(value,('quality','privacy','rights','context'))
    if any(type(v) is not bool or not v for v in value.values()):fail('REVIEW_REQUIRED')
    return value
def contract(value):
    fields(value,('format','key','unknown_fields','trim_strings','empty_as_null','fields'))
    if value['format']!='outlands-import-contract-v1':fail('CONTRACT_FORMAT_INVALID')
    field_name(value['key']);choice(value['unknown_fields'],('reject','ignore'))
    if any(type(value[k]) is not bool for k in ('trim_strings','empty_as_null')):fail('CONTRACT_BOOLEAN_INVALID')
    if type(value['fields']) is not list or not 1<=len(value['fields'])<=MAX_FIELDS:fail('CONTRACT_FIELDS_LIMIT')
    sources=set();targets=set();key=None
    for row in value['fields']:
        fields(row,('source','target','type','nullable'));field_name(row['source']);field_name(row['target']);choice(row['type'],('text','integer','decimal','boolean'))
        if type(row['nullable']) is not bool:fail('CONTRACT_BOOLEAN_INVALID')
        if row['source'].casefold() in sources or row['target'].casefold() in targets:fail('CONTRACT_MAPPING_DUPLICATE')
        sources.add(row['source'].casefold());targets.add(row['target'].casefold())
        if row['target']==value['key']:key=row
    if key is None or key['nullable'] or key['type'] not in ('text','integer'):fail('CONTRACT_KEY_INVALID')
    return value
def request(kind,value):
    if kind=='plan':
        fields(value,('sources','contract'));contract(value['contract'])
        if type(value['sources']) is not list or not 1<=len(value['sources'])<=MAX_SOURCES:fail('SOURCE_COUNT_LIMIT')
        for item in value['sources']:
            fields(item,('path','format'));selector(item['path']);choice(item['format'],('csv','jsonl'))
        if len({item['path'].casefold() for item in value['sources']})!=len(value['sources']):fail('SOURCE_SELECTION_DUPLICATE')
    elif kind=='import':
        fields(value,('plan_id','plan_sha256','accept_rejections','checks'));identifier(value['plan_id']);pin(value['plan_sha256']);checks(value['checks'])
        if type(value['accept_rejections']) is not bool:fail('REJECTIONS_CHOICE_REQUIRED')
    else:fail('JOB_KIND_INVALID')
    return value
def envelope(value,extra):
    fields(value,('expected_head','actor','reason',*extra));pin(value['expected_head']);text(value['actor'],160);text(value['reason']);return value

def normalize(row,rule):
    if type(row) is not dict or len(row)>32 or any(type(k) is not str for k in row):fail('ROW_OBJECT_REQUIRED')
    allowed={v['source'] for v in rule['fields']};unknown=sorted(set(row)-allowed)
    if unknown and rule['unknown_fields']=='reject':fail('UNKNOWN_FIELDS')
    for name in row:text(name,128)
    result={}
    for item in rule['fields']:
        value=row.get(item['source'])
        if type(value) is str:
            if rule['trim_strings']:value=value.strip()
            if rule['empty_as_null'] and value=='':value=None
        if value is None:
            if not item['nullable']:fail('REQUIRED_VALUE_MISSING')
            result[item['target']]=None;continue
        kind=item['type']
        if kind=='text':
            text(value,256,empty=item['nullable']);out=value
        elif kind=='integer':
            if type(value) is str:
                if not re.fullmatch('-?(0|[1-9][0-9]{0,17})',value):fail('INTEGER_VALUE_INVALID')
                value=int(value)
            out=integer(value,-999999999999999999,999999999999999999)
        elif kind=='boolean':
            if type(value) is str and value in ('true','false'):value=value=='true'
            if type(value) is not bool:fail('BOOLEAN_VALUE_INVALID')
            out=value
        else:
            if type(value) is int:value=str(value)
            if type(value) is not str or not re.fullmatch(r'-?(0|[1-9][0-9]{0,17})(\.[0-9]{1,6})?',value):fail('DECIMAL_VALUE_INVALID')
            out=value.rstrip('0').rstrip('.') if '.' in value else value
            if out=='-0':out='0'
        result[item['target']]=out
    return result,unknown
