"""Bounded portable selectors and typed journal request contracts."""
import re
from . import runtime as r

MAX_FILES=256
MAX_DIRS=128
MAX_ENTRIES=1024
MAX_FILE=4*1024*1024
MAX_TOTAL=32*1024*1024
MAX_JOBS=64
MAX_EVENTS=256
ZERO='0'*64
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
def identifier(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{32}',value):fail('IDENTIFIER_INVALID')
    return value
def pin(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}',value):fail('HASH_INVALID')
    return value
def relative(value):
    if type(value) is not str or not 1<=len(value)<=240:fail('RELATIVE_PATH_INVALID')
    parts=value.split('/')
    if not 1<=len(parts)<=8:fail('PATH_DEPTH_LIMIT')
    for part in parts:
        if not re.fullmatch('[A-Za-z0-9_. -]{1,64}',part) or part in ('.','..') or part.endswith(('.',' ')) or part.split('.')[0].casefold() in RESERVED:fail('RELATIVE_PATH_INVALID')
    return value
def selector(value):
    relative(value)
    if not value.startswith('inbox/') or len(value.split('/'))<2:fail('SOURCE_MUST_BE_SELECTED_INBOX_TREE')
    return value
def exclusions(value):
    if type(value) is not list or len(value)>16:fail('EXCLUSIONS_INVALID')
    for name in value:relative(name)
    if len({name.casefold() for name in value})!=len(value):fail('EXCLUSIONS_DUPLICATE')
    return sorted(value)
def envelope(value,extra):
    fields(value,('expected_head','actor','reason',*extra));pin(value['expected_head']);text(value['actor'],160);text(value['reason']);return value
def request(kind,value):
    if kind=='snapshot':
        fields(value,('source','exclusions','quiescent'));selector(value['source']);exclusions(value['exclusions'])
        if type(value['quiescent']) is not bool or not value['quiescent']:fail('QUIESCENT_SOURCE_ASSERTION_REQUIRED')
    elif kind=='restore_imported':
        fields(value,('source','manifest_sha256'));selector(value['source']);pin(value['manifest_sha256'])
    elif kind in ('restore','verify'):
        fields(value,('snapshot_id',));identifier(value['snapshot_id'])
    else:fail('JOB_KIND_INVALID')
    return value
def policy(value):
    fields(value,('keep_last','protect_untested'));integer(value['keep_last'],1,16)
    if type(value['protect_untested']) is not bool:fail('POLICY_INVALID')
    return value
