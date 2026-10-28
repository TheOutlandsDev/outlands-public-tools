"""Exact schemas and bounded literal template substitution; no expressions."""
import re
from . import runtime as r

ZERO='0'*64
MAX_JOBS=64
MAX_EVENTS=256
MAX_TEMPLATE=65536
MAX_VALUES=131072
MAX_PREVIEW=262144
MAX_DOCX=2*1024*1024
RESERVED={'con','prn','aux','nul',*{p+str(i) for p in ('com','lpt') for i in range(1,10)}}

def fail(code):raise r.WorkbenchError(code)
def fields(value,names):
    if type(value) is not dict or set(value)!=set(names):fail('FIELDS_INVALID')
def integer(value,low,high):
    if type(value) is not int or not low<=value<=high:fail('INTEGER_INVALID')
    return value
def text(value,maximum=400,empty=False):
    if type(value) is not str or (not empty and not value.strip()) or len(value)>maximum:fail('TEXT_INVALID')
    if any((ord(ch)<32 and ch not in '\n\r\t') or ord(ch) in (0xfffe,0xffff) for ch in value):fail('TEXT_CONTROL_REFUSED')
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
def name(value):
    if type(value) is not str or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,31}',value):fail('NAME_INVALID')
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
def envelope(value,extra):
    fields(value,('expected_head','actor','reason',*extra));pin(value['expected_head']);text(value['actor'],160);text(value['reason']);return value
def sequence(value,low,high):
    if type(value) is not list or not low<=len(value)<=high:fail('LIST_LIMIT')
def unique(names):
    if len({v.casefold() for v in names})!=len(names):fail('NAME_DUPLICATE')

def placeholders(value,scalars):
    text(value,1200);parts=re.findall(r'\{\{([A-Za-z][A-Za-z0-9_]{0,31})\}\}',value)
    stripped=re.sub(r'\{\{([A-Za-z][A-Za-z0-9_]{0,31})\}\}','',value)
    if '{{' in stripped or '}}' in stripped or any(n not in scalars for n in parts):fail('PLACEHOLDER_INVALID')
def template(value):
    fields(value,('format','label','title','fields','sections'))
    if value['format']!='outlands-document-template-v1':fail('TEMPLATE_FORMAT_INVALID')
    text(value['label'],120);text(value['title'],160);sequence(value['fields'],1,16);declared={};scalars=set()
    for item in value['fields']:
        if type(item) is not dict:fail('FIELD_INVALID')
        kind=choice(item.get('kind'),('text','quantity','rows'));fields(item,('name','label','kind','columns') if kind=='rows' else ('name','label','kind'));name(item['name']);text(item['label'],80);declared[item['name']]=item
        if kind=='rows':
            sequence(item['columns'],1,8)
            for col in item['columns']:fields(col,('name','label','kind'));name(col['name']);text(col['label'],80);choice(col['kind'],('text','quantity'))
            unique([col['name'] for col in item['columns']])
        else:scalars.add(item['name'])
    unique([item['name'] for item in value['fields']]);placeholders(value['title'],scalars);sequence(value['sections'],1,16);blocks=0
    for section in value['sections']:
        fields(section,('id','title','optional','blocks'));name(section['id']);text(section['title'],100)
        if type(section['optional']) is not bool:fail('OPTIONAL_BOOLEAN_INVALID')
        sequence(section['blocks'],1,16);blocks+=len(section['blocks'])
        for block in section['blocks']:
            if type(block) is not dict:fail('BLOCK_INVALID')
            kind=choice(block.get('kind'),('paragraph','bullet','table'))
            if kind!='table':fields(block,('kind','text'));placeholders(block['text'],scalars);continue
            fields(block,('kind','source','columns','totals'));source=declared.get(block['source'])
            if source is None or source['kind']!='rows':fail('TABLE_SOURCE_INVALID')
            cols={col['name']:col for col in source['columns']};sequence(block['columns'],1,8)
            for col in block['columns']:
                fields(col,('field','width'));name(col['field']);integer(col['width'],1,100)
                if col['field'] not in cols:fail('TABLE_FIELD_INVALID')
            selected=[col['field'] for col in block['columns']];unique(selected)
            if sum(col['width'] for col in block['columns'])!=100:fail('TABLE_WIDTHS_INVALID')
            sequence(block['totals'],0,8);unique(block['totals'])
            if any(n not in selected or cols[n]['kind']!='quantity' for n in block['totals']):fail('TABLE_TOTAL_INVALID')
    unique([section['id'] for section in value['sections']])
    if blocks>64 or len(r.encode(value))>MAX_TEMPLATE:fail('TEMPLATE_LIMIT')
    return value

def values(template_value,value):
    declared={item['name']:item for item in template_value['fields']};fields(value,declared)
    if len(r.encode(value))>MAX_VALUES:fail('VALUES_LIMIT')
    for key,item in declared.items():
        selected=value[key]
        if item['kind']=='text':text(selected,800)
        elif item['kind']=='quantity':integer(selected,0,999999999)
        else:
            sequence(selected,0,100)
            for row in selected:
                fields(row,[col['name'] for col in item['columns']])
                for col in item['columns']:
                    if col['kind']=='text':text(row[col['name']],240)
                    else:integer(row[col['name']],0,999999999)
    return value
def selection(template_value,selected):
    sequence(selected,0,16)
    for item in selected:name(item)
    unique(selected);available={s['id']:s for s in template_value['sections']}
    if any(n not in available for n in selected) or any(s['id'] not in selected for s in available.values() if not s['optional']):fail('SECTION_SELECTION_INVALID')
    if not selected:fail('SECTION_SELECTION_EMPTY')
    return selected

def request(kind,value):
    if kind=='template':
        fields(value,('parent_id','template'));template(value['template'])
        if value['parent_id'] is not None:identifier(value['parent_id'])
    elif kind=='preview':
        fields(value,('template_id','template_sha256','values','sections'));identifier(value['template_id']);pin(value['template_sha256'])
        if type(value['values']) is not dict or len(r.encode(value['values']))>MAX_VALUES:fail('VALUES_LIMIT')
        sequence(value['sections'],0,16)
    elif kind=='build':fields(value,('preview_id','preview_sha256','checks'));identifier(value['preview_id']);pin(value['preview_sha256']);checks(value['checks'])
    else:fail('JOB_KIND_INVALID')
    return value
