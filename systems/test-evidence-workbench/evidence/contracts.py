"""Exact neutral check, trust and suite contracts; no executable/argument discovery."""
import re
from . import runtime as r


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


def object_value(value,maximum):
    if type(value) is not dict:raise r.WorkbenchError('OBJECT_REQUIRED')
    def normalize(item,depth=0):
        if depth>32:raise r.WorkbenchError('OBJECT_DEPTH_LIMIT')
        if type(item) in (int,float):
            if not -1e12<=item<=1e12:raise r.WorkbenchError('OBJECT_NUMBER_LIMIT')
            return int(item) if type(item) is float and item.is_integer() else item
        if type(item) is dict:return {key:normalize(child,depth+1) for key,child in item.items()}
        if type(item) is list:return [normalize(child,depth+1) for child in item]
        return item
    result=normalize(value)
    if len(r.encode(result))>maximum:raise r.WorkbenchError('OBJECT_SIZE_LIMIT')
    return result


def definition(value):
    fields(value,('format','case_id','title','script','input','expected','timeout_ms'))
    if value['format']!='outlands-trusted-check-v1':raise r.WorkbenchError('CASE_FORMAT_INVALID')
    token(value['case_id']);text(value['title'],120);text(value['script'],32768);integer(value['timeout_ms'],100,5000)
    inputs=object_value(value['input'],16384)
    expected=value['expected'];fields(expected,('exit_code','stdout','stderr'));integer(expected['exit_code'],0,255);text(expected['stderr'],2048,empty=True)
    stdout=object_value(expected['stdout'],8192)
    if len(r.encode(value))>131072:raise r.WorkbenchError('CASE_SIZE_LIMIT')
    return {**value,'input':inputs,'expected':{**expected,'stdout':stdout}}


def bundle(raw):
    value=r.decode(raw);fields(value,('format','cases'))
    if value['format']!='outlands-check-bundle-v1' or type(value['cases']) is not list or not 1<=len(value['cases'])<=20:raise r.WorkbenchError('BUNDLE_INVALID')
    cases=[definition(v) for v in value['cases']]
    if len({v['case_id'] for v in cases})!=len(cases):raise r.WorkbenchError('CASE_DUPLICATE')
    return cases


def suite(raw):
    value=r.decode(raw);fields(value,('cases',))
    if type(value['cases']) is not list or not 1<=len(value['cases'])<=8:raise r.WorkbenchError('SUITE_LIMIT')
    seen=set()
    for item in value['cases']:
        fields(item,('case_id','expected_sha256','trust_version'));token(item['case_id']);hash_value(item['expected_sha256']);integer(item['trust_version'],1,1000)
        if item['case_id'] in seen:raise r.WorkbenchError('CASE_DUPLICATE')
        seen.add(item['case_id'])
    return value
