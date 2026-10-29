"""Bounded symbolic artifact contracts. Paths and free-form metadata are absent."""
import re
import toolkit as t

ROLES=('input','mapping','schema','configuration','code','result','evidence')


def ids(value,minimum=0,maximum=16):
    t.require(type(value) is list and minimum <= len(value) <= maximum, 'REFERENCE_LIMIT')
    for item in value:
        t.identifier(item)
    t.require(len(set(value))==len(value), 'DUPLICATE_REFERENCE')
    return value


def items(value,fields,minimum=1):
    t.require(type(value) is list and minimum <= len(value) <= 16, 'ARTIFACT_LIMIT')
    for row in value:
        t.fields(row,fields); t.identifier(row['id'])
    t.require(len({row['id'] for row in value})==len(value), 'DUPLICATE_ARTIFACT')
    return {row['id']:row for row in value}


def manifest(raw):
    value=t.decode(raw)
    t.fields(value,{'format','run_id','artifacts'})
    t.require(value['format']=='outlands-run-artifact-manifest-v1','MANIFEST_FORMAT_INVALID')
    t.identifier(value['run_id'])
    rows=items(value['artifacts'],{'id','role','bytes','sha256'})
    total=0
    for row in rows.values():
        t.require(type(row['role']) is str and row['role'] in ROLES,'ROLE_INVALID')
        total+=t.integer(row['bytes'],t.MAX_INPUT)
        t.sha(row['sha256'])
    t.require(total<=16*1024*1024,'TOTAL_INPUT_LIMIT')
    return value,rows


def buffers(inputs,expected):
    t.require(type(inputs) is dict and set(inputs)==set(expected),'BINDING_COVERAGE_INVALID')
    t.require(all(type(v) is bytes and len(v)<=t.MAX_INPUT for v in inputs.values()) and
              sum(map(len,inputs.values()))<=16*1024*1024,'TOTAL_INPUT_LIMIT')


def observe(rows,inputs):
    buffers(inputs,rows)
    observed,issues=[],[]
    for key,row in sorted(rows.items()):
        raw=inputs[key]
        actual=dict(id=key,bytes=len(raw),sha256=t.digest(raw))
        observed.append(actual)
        for field,code in (('bytes','ARTIFACT_SIZE_MISMATCH'),('sha256','ARTIFACT_HASH_MISMATCH')):
            if actual[field]!=row[field]: issues.append(dict(code=code,item=key))
    return observed,issues


def public_name(value):
    t.require(type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}',value)
              and '..' not in value and not value.endswith('.') and
              value.split('.')[0].upper() not in {'CON','PRN','AUX','NUL',
                  *(f'COM{i}' for i in range(10)),*(f'LPT{i}' for i in range(10))},'PUBLIC_NAME_INVALID')
    return value


def selected_names(rows):
    seen=set()
    for row in rows.values():
        name=public_name(row['public_name'])
        t.require(name.casefold() not in seen,'PUBLIC_NAME_COLLISION')
        seen.add(name.casefold()); t.sha(row['sha256'])
