"""Strict, bounded contracts for explicitly supplied observation recordings."""
import copy
from datetime import datetime,timezone
import re
from . import runtime as r

MAX_DOCUMENT=512*1024
MAX_SNAPSHOTS=128
MAX_REVISIONS=64

def fail(code):
    raise r.WorkbenchError(code)

def fields(value,names):
    if type(value) is not dict or set(value)!=set(names):fail('FIELDS_INVALID')

def text(value,maximum=400,empty=False):
    if type(value) is not str or (not empty and not value.strip()) or len(value)>maximum:fail('TEXT_INVALID')
    if any(ord(ch)<32 and ch not in '\n\r\t' for ch in value):fail('TEXT_CONTROL_REFUSED')
    try:raw=value.encode('utf-8')
    except UnicodeError:fail('TEXT_ENCODING_INVALID')
    if len(raw)>maximum:fail('TEXT_SIZE_LIMIT')
    return value

def token(value):
    if type(value) is not str or not re.fullmatch('[a-z][a-z0-9_-]{0,39}',value):fail('IDENTIFIER_INVALID')
    if value in {'con','prn','aux','nul',*{prefix+str(i) for prefix in ('com','lpt') for i in range(1,10)}}:fail('IDENTIFIER_RESERVED')
    return value

def integer(value,low,high):
    if type(value) is not int or not low<=value<=high:fail('INTEGER_INVALID')
    return value

def hash_value(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}',value):fail('HASH_INVALID')
    return value

def choice(value,values):
    if type(value) is not str or value not in values:fail('CHOICE_INVALID')
    return value

def timestamp(value):
    if type(value) is not str or not re.fullmatch(r'20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z',value):fail('TIMESTAMP_INVALID')
    try:return datetime.fromisoformat(value[:-1]+'+00:00')
    except ValueError:fail('TIMESTAMP_INVALID')

def stamp(value):
    return value.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')

def sequence(value,low,high):
    if type(value) is not list or not low<=len(value)<=high:fail('COLLECTION_LIMIT')
    return value

def create(value):
    fields(value,('case_id','title','policy','services','maintenance'))
    token(value['case_id']);text(value['title'],160)
    policy=value['policy'];fields(policy,('maximum_age_seconds','maximum_gap_seconds','clean_samples'))
    integer(policy['maximum_age_seconds'],1,3600);integer(policy['maximum_gap_seconds'],1,86400);integer(policy['clean_samples'],1,10)
    seen=set();services=[]
    for row in sequence(value['services'],1,8):
        fields(row,('id','label','expected_state','signals'));token(row['id']);text(row['label'],160);choice(row['expected_state'],('online','planned_off'))
        if row['id'] in seen:fail('SERVICE_DUPLICATE')
        seen.add(row['id']);signals=sequence(row['signals'],1,4)
        for signal in signals:token(signal)
        if len(set(signals))!=len(signals):fail('SIGNAL_DUPLICATE')
        services.append(copy.deepcopy(row))
    windows=[];window_ids=set()
    for window in sequence(value['maintenance'],0,8):
        fields(window,('id','service_id','start','end','reason'));token(window['id']);text(window['reason']);token(window['service_id'])
        if window['id'] in window_ids or window['service_id'] not in seen:fail('MAINTENANCE_REFERENCE_INVALID')
        window_ids.add(window['id']);start=timestamp(window['start']);end=timestamp(window['end'])
        if not 0<(end-start).total_seconds()<=86400:fail('MAINTENANCE_BOUND_INVALID')
        if any(old['service_id']==window['service_id'] and start<timestamp(old['end']) and timestamp(old['start'])<end for old in windows):fail('MAINTENANCE_OVERLAP')
        windows.append(copy.deepcopy(window))
    return dict(format='outlands-reliability-case-v1',case_id=value['case_id'],title=value['title'],policy=copy.deepcopy(policy),services=services,maintenance=windows,snapshots=[],acknowledgements=[])

def append(document,values):
    sequence(values,1,MAX_SNAPSHOTS)
    if len(document['snapshots'])+len(values)>MAX_SNAPSHOTS:fail('SNAPSHOT_LIMIT')
    doc=copy.deepcopy(document);registry={row['id']:row for row in doc['services']};ids={s['id'] for s in doc['snapshots']};last=None;facts={}
    for snapshot in doc['snapshots']:
        last=timestamp(snapshot['at'])
        for row in snapshot['services']:
            for signal in row['signals']:facts[row['service_id'],signal['id']]=signal
    for snapshot in values:
        fields(snapshot,('id','at','services'));token(snapshot['id']);at=timestamp(snapshot['at'])
        if snapshot['id'] in ids:fail('SNAPSHOT_DUPLICATE')
        if last is not None and at<=last:fail('SNAPSHOT_ORDER_INVALID')
        if doc['snapshots'] and (at-timestamp(doc['snapshots'][0]['at'])).total_seconds()>31*86400:fail('RECORDING_SPAN_LIMIT')
        ids.add(snapshot['id']);last=at;seen=set()
        for row in sequence(snapshot['services'],0,8):
            fields(row,('service_id','signals'));service=token(row['service_id'])
            if service not in registry or service in seen:fail('SNAPSHOT_SERVICE_INVALID')
            seen.add(service);signals=set()
            for signal in sequence(row['signals'],0,4):
                fields(signal,('id','state','observed_at','note'));identifier=token(signal['id']);choice(signal['state'],('healthy','degraded','down','unknown'));text(signal['note'],400,empty=True);observed=timestamp(signal['observed_at'])
                if identifier not in registry[service]['signals'] or identifier in signals:fail('SNAPSHOT_SIGNAL_INVALID')
                if observed>at:fail('OBSERVATION_FUTURE')
                signals.add(identifier);key=(service,identifier);old=facts.get(key)
                if old is not None:
                    old_at=timestamp(old['observed_at'])
                    if observed<old_at:fail('OBSERVATION_ORDER_INVALID')
                    if observed==old_at and signal!=old:fail('OBSERVATION_CONFLICT')
                facts[key]=signal
        doc['snapshots'].append(copy.deepcopy(snapshot))
    bounded(doc)
    return doc

def bounded(document):
    if len(r.encode(document))>MAX_DOCUMENT:fail('DOCUMENT_LIMIT')

def acknowledgement(value):
    fields(value,('incident_id','expected_episode','expected_escalations','actor','reason'));hash_value(value['incident_id']);integer(value['expected_episode'],1,MAX_SNAPSHOTS);integer(value['expected_escalations'],0,MAX_SNAPSHOTS);text(value['actor'],160);text(value['reason'])
    return copy.deepcopy(value)
