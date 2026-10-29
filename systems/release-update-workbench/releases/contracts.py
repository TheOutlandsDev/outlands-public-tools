"""Exact bounded release declarations; no target actions."""
import re
from . import runtime as r

ZERO='0'*64
MAX_JOBS=64
MAX_EVENTS=256
MAX_FILE=65536
MAX_TOTAL=2*1024*1024
MAX_FILES=64
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
    from .vendor import preflight,lock_diff
    try:return fn(*args)
    except (preflight.PreflightError,lock_diff.DiffError):fail('PACKAGE_DECLARATION_INVALID')

def inventory(value):
    from .vendor import preflight
    rows=vendor_call(preflight.manifest_rows,value);sequence(rows,1,MAX_FILES)
    for row in rows:portable(row['path']);integer(row['size'],0,MAX_FILE)
    if sum(row['size'] for row in rows)>MAX_TOTAL:fail('PACKAGE_TOTAL_LIMIT')
    return rows

def launcher(value,rows):
    fields(value,('schema_version','executable','working_directory','arguments'));integer(value['schema_version'],1,1);portable(value['executable']);names={row['path'] for row in rows}
    if value['executable'] not in names:fail('LAUNCHER_ENTRY_NOT_LISTED')
    working=value['working_directory']
    if working!='.':
        portable(working)
        if not any(path.startswith(working+'/') for path in names):fail('LAUNCHER_DIRECTORY_NOT_LISTED')
    sequence(value['arguments'],0,16)
    for arg in value['arguments']:
        text(arg,240,empty=True)
        if any(ord(ch)<32 or ord(ch)==127 for ch in arg):fail('ARGUMENT_CONTROL_REFUSED')
    return value

def policy(value):
    fields(value,('backup_confirmed','target_stopped_confirmed','readiness_confirmed','allow_removals','dependency_reviewed'))
    if any(type(item) is not bool for item in value.values()):fail('POLICY_BOOLEAN_INVALID')
    return value

def assertions(value,required=True):
    fields(value,('quality','privacy','rights','context'))
    if any(type(v) is not bool or (required and not v) for v in value.values()):fail('REVIEW_REQUIRED')
    return value

def request(kind,value):
    if kind=='candidate':
        fields(value,('parent_id','label','source','manifest','manifest_sha256','dependency_lock','launcher'));text(value['label'],120);selector(value['source']);pin(value['manifest_sha256']);rows=inventory(value['manifest'])
        if value['parent_id'] is not None:identifier(value['parent_id'])
        if r.digest(r.encode(value['manifest']))!=value['manifest_sha256']:fail('TRUSTED_MANIFEST_PIN_MISMATCH')
        launcher(value['launcher'],rows)
        if value['dependency_lock'] is not None:
            from .vendor import lock_diff
            lock=value['dependency_lock'];fields(lock,('path','text'));portable(lock['path']);text(lock['text'],MAX_FILE);vendor_call(lock_diff.parse_lock,lock['text'].encode('utf-8'));row=next((row for row in rows if row['path']==lock['path']),None)
            if row is None or row['size']!=len(lock['text'].encode()) or row['sha256']!=r.digest(lock['text'].encode()):fail('LOCK_MANIFEST_MISMATCH')
    elif kind=='comparison':
        fields(value,('baseline_id','baseline_sha256','candidate_id','candidate_sha256','policy'))
        for key in ('baseline_id','candidate_id'):identifier(value[key])
        for key in ('baseline_sha256','candidate_sha256'):pin(value[key])
        policy(value['policy'])
    elif kind=='plan':fields(value,('comparison_id','comparison_sha256'));identifier(value['comparison_id']);pin(value['comparison_sha256'])
    else:fail('JOB_KIND_INVALID')
    return value
