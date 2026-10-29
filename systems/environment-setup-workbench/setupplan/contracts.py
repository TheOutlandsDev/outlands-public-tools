"""Exact bounded supplied-profile schemas; no executable commands or discovery."""
import re
from . import runtime as r

ZERO='0'*64
MAX_JOBS=64
MAX_EVENTS=256
MAX_PROFILE=65536
MAX_OBSERVATIONS=131072
MAX_REPORT=262144
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

def portable(value):
    text(value,240)
    parts=value.split('/')
    if len(parts)>8:fail('RELATIVE_PATH_INVALID')
    for part in parts:
        if not re.fullmatch('[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}',part) or part.endswith('.') or part.split('.')[0].casefold() in RESERVED:fail('RELATIVE_PATH_INVALID')
    return value

def vendor_call(fn,*args):
    from .vendor import configuration,connections
    try:return fn(*args)
    except (configuration.ContractError,connections.PlanError):fail('DECLARATION_CONTRACT_INVALID')

def profile(value):
    from .vendor import configuration,connections
    fields(value,('format','label','prerequisites','configuration','layout','connections','steps'))
    if value['format']!='outlands-setup-profile-v1':fail('PROFILE_FORMAT_INVALID')
    text(value['label'],120);sequence(value['prerequisites'],0,32);sequence(value['layout'],0,32);sequence(value['steps'],1,32)
    refs=set()
    for row in value['prerequisites']:
        fields(row,('id','kind','required'));name(row['id']);choice(row['kind'],('file','program','manual'))
        if type(row['required']) is not bool:fail('REQUIRED_BOOLEAN_INVALID')
        refs.add('prerequisite:'+row['id'])
    unique([row['id'] for row in value['prerequisites']])
    vendor_call(configuration.parse_contract,value['configuration'])
    refs.update('configuration:'+row['id'] for row in value['configuration']['fields']+value['configuration']['rules'])
    for row in value['layout']:fields(row,('id','path'));name(row['id']);portable(row['path']);refs.add('layout:'+row['id'])
    unique([row['id'] for row in value['layout']]);unique([row['path'] for row in value['layout']])
    vendor_call(connections.parse_plan,value['connections']);refs.update('connection:'+row['id'] for row in value['connections']['bindings'])
    ids=[]
    for row in value['steps']:
        fields(row,('id','label','depends_on','checks','verification'));ids.append(name(row['id']));text(row['label'],120);text(row['verification'],400)
        sequence(row['depends_on'],0,32);sequence(row['checks'],1,128)
        for item in row['depends_on']:name(item)
        for item in row['checks']:
            if type(item) is not str or item not in refs:fail('CHECK_REFERENCE_INVALID')
        unique(row['depends_on']);unique(row['checks'])
    unique(ids);known=set(ids)
    if any(d not in known or d==row['id'] for row in value['steps'] for d in row['depends_on']):fail('STEP_DEPENDENCY_INVALID')
    # Stable topological order, never recursion or command construction.
    remaining=list(value['steps']);seen=set()
    while remaining:
        ready=[row for row in remaining if set(row['depends_on'])<=seen]
        if not ready:fail('STEP_CYCLE_REFUSED')
        seen.update(row['id'] for row in ready);remaining=[row for row in remaining if row not in ready]
    if len(r.encode(value))>MAX_PROFILE:fail('PROFILE_LIMIT')
    return value

def observations(value):
    from .vendor import configuration
    fields(value,('prerequisites','settings','files'))
    if type(value['prerequisites']) is not dict or len(value['prerequisites'])>32:fail('OBSERVATION_LIMIT')
    for key,status in value['prerequisites'].items():name(key);choice(status,('PRESENT','MISSING','UNKNOWN','UNSAFE'))
    vendor_call(configuration._settings,value['settings']);sequence(value['files'],0,128)
    for path in value['files']:portable(path)
    unique(value['files'])
    if len(r.encode(value))>MAX_OBSERVATIONS:fail('OBSERVATION_LIMIT')
    return value

def request(kind,value):
    if kind=='profile':
        fields(value,('parent_id','profile'));profile(value['profile'])
        if value['parent_id'] is not None:identifier(value['parent_id'])
    elif kind=='evaluation':
        fields(value,('profile_id','profile_sha256','observations'));identifier(value['profile_id']);pin(value['profile_sha256']);observations(value['observations'])
    elif kind=='plan':
        fields(value,('evaluation_id','evaluation_sha256','checks'));identifier(value['evaluation_id']);pin(value['evaluation_sha256']);checks(value['checks'])
    else:fail('JOB_KIND_INVALID')
    return value
