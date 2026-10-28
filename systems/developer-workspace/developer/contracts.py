"""Neutral text-only projects with portable names and bounded private contents."""
import re
from . import runtime as r

SUFFIXES={'.py','.pyw','.json','.xml','.rdl','.sql','.md','.txt','.js','.mjs','.cjs','.html','.css'}
MAX_FILES=200
MAX_FILE=65536
MAX_TOTAL=1024*1024


def fields(value,names):
    if type(value) is not dict or set(value)!=set(names):raise r.WorkbenchError('FIELDS_INVALID')


def text(value,maximum,empty=False):
    if type(value) is not str or not empty and not value.strip() or len(value)>maximum:raise r.WorkbenchError('TEXT_INVALID')
    if any(ord(ch)<32 and ch not in '\n\r\t' for ch in value):raise r.WorkbenchError('TEXT_CONTROL_REFUSED')
    try:raw=value.encode('utf-8')
    except UnicodeError:raise r.WorkbenchError('TEXT_ENCODING_INVALID') from None
    if len(raw)>maximum:raise r.WorkbenchError('TEXT_SIZE_LIMIT')
    return value


def token(value):
    if type(value) is not str or not re.fullmatch('[a-z][a-z0-9-]{0,47}',value):raise r.WorkbenchError('IDENTIFIER_INVALID')
    return value


def hash_value(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}',value):raise r.WorkbenchError('HASH_INVALID')
    return value


def integer(value,low,high):
    if type(value) is not int or not low<=value<=high:raise r.WorkbenchError('INTEGER_INVALID')
    return value


def path(value):
    if type(value) is not str or len(value)>240:raise r.WorkbenchError('SOURCE_PATH_INVALID')
    parts=value.split('/')
    if not 1<=len(parts)<=8:raise r.WorkbenchError('SOURCE_PATH_INVALID')
    for part in parts:
        if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,63}',part) or part.endswith('.') or part.split('.')[0].casefold() in {'con','prn','aux','nul',*{'com'+str(i) for i in range(1,10)},*{'lpt'+str(i) for i in range(1,10)}}:raise r.WorkbenchError('SOURCE_PATH_INVALID')
        if part.casefold() in {'node_modules','__pycache__','runtime','private','outputs'} and part!=parts[-1]:raise r.WorkbenchError('SOURCE_DIRECTORY_REFUSED')
    suffix='.'+parts[-1].rsplit('.',1)[-1].lower() if '.' in parts[-1] else ''
    if suffix not in SUFFIXES:raise r.WorkbenchError('SOURCE_TYPE_REFUSED')
    return value


def files(values):
    if type(values) is not list or not 1<=len(values)<=MAX_FILES:raise r.WorkbenchError('FILE_COUNT_LIMIT')
    seen=set();result=[];total=0
    for value in values:
        fields(value,('path','content'));name=path(value['path']);content=text(value['content'],MAX_FILE,empty=True)
        key=name.casefold()
        if key in seen:raise r.WorkbenchError('SOURCE_PATH_COLLISION')
        if any(key.startswith(old+'/') or old.startswith(key+'/') for old in seen):raise r.WorkbenchError('SOURCE_PATH_COLLISION')
        seen.add(key);total+=len(content.encode('utf-8'));result.append(dict(path=name,content=content))
    if total>MAX_TOTAL:raise r.WorkbenchError('PROJECT_SIZE_LIMIT')
    return sorted(result,key=lambda item:item['path'])


def project(raw):
    value=r.decode(raw);fields(value,('format','project_id','title','files'))
    if value['format']!='outlands-developer-project-v1':raise r.WorkbenchError('PROJECT_FORMAT_INVALID')
    return dict(format=value['format'],project_id=token(value['project_id']),title=text(value['title'],120),files=files(value['files']))
