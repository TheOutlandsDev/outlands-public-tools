"""Bounded, exact-field contracts; no coercion of quantities or decisions."""
from datetime import datetime,timezone
from decimal import Decimal
import math
import re
from .runtime import WorkbenchError,decode,encode


def fields(value,required,optional=()):
    if type(value) is not dict or set(value)-set(required)-set(optional) or not set(required)<=set(value):raise WorkbenchError('FIELDS_INVALID')
    return value


def text(value,maximum=120):
    if type(value) is not str or not 1<=len(value)<=maximum or not value.strip() or any(ord(c)<32 for c in value):raise WorkbenchError('TEXT_INVALID')
    return value.strip()


def token(value):
    if type(value) is not str or not re.fullmatch(r'[A-Za-z][A-Za-z0-9._-]{0,63}',value):raise WorkbenchError('IDENTITY_INVALID')
    return value


def integer(value,minimum=0,maximum=1000000000):
    if type(value) is not int or not minimum<=value<=maximum:raise WorkbenchError('INTEGER_INVALID')
    return value


def number(value,minimum=0,maximum=1000000000):
    if type(value) not in (int,float):raise WorkbenchError('NUMBER_INVALID')
    try:
        if not math.isfinite(value) or not minimum<=value<=maximum:raise WorkbenchError('NUMBER_INVALID')
        result=Decimal(str(value))
        if result.as_tuple().exponent<-6:raise WorkbenchError('NUMBER_PRECISION_LIMIT')
        return result
    except (OverflowError,ValueError):raise WorkbenchError('NUMBER_INVALID') from None


def boolean(value):
    if type(value) is not bool:raise WorkbenchError('BOOLEAN_INVALID')
    return value


def instant(value):
    text(value,48)
    try:
        stamp=datetime.fromisoformat(value)
        if stamp.tzinfo is None or stamp.utcoffset() is None:raise ValueError()
        return stamp.astimezone(timezone.utc)
    except (ValueError,OverflowError):raise WorkbenchError('TIME_INVALID') from None


def utc(value):return instant(value).isoformat(timespec='microseconds')


def rows(value,maximum=500):
    if type(value) is not list or len(value)>maximum:raise WorkbenchError('COLLECTION_LIMIT')
    return value


def keyed(value,maximum=500):
    selected=rows(value,maximum);seen=set()
    for row in selected:
        if type(row) is not dict:raise WorkbenchError('FIELDS_INVALID')
        key=token(row.get('id'))
        if key in seen:raise WorkbenchError('DUPLICATE_IDENTITY')
        seen.add(key)
    return sorted(selected,key=lambda r:r['id'])


def finite(value):
    if isinstance(value,Decimal):return float(value)
    if type(value) is dict:return {k:finite(v) for k,v in value.items()}
    if type(value) in (tuple,list):return [finite(v) for v in value]
    return value


def scenario(raw):
    value=decode(raw)
    fields(value,('format','project_id','title','snapshot_utc','window','capacity','process','inventory','dispatch','active_lots','completions'),('planning_reference',))
    if value['format']!='outlands-operations-scenario-v1':raise WorkbenchError('SCENARIO_FORMAT_INVALID')
    token(value['project_id']);text(value['title']);value['snapshot_utc']=utc(value['snapshot_utc'])
    fields(value['window'],('start','end'))
    value['window']={k:utc(v) for k,v in value['window'].items()}
    if not instant(value['window']['start'])<instant(value['window']['end'])<=instant(value['snapshot_utc']):raise WorkbenchError('WINDOW_INVALID')
    for key in ('capacity','process','inventory','active_lots'):value[key]=keyed(value[key])
    fields(value['dispatch'],('policy','candidates'));value['dispatch']['candidates']=keyed(value['dispatch']['candidates'])
    rows(value['completions'],2000)
    from .engines.events import event
    value['completions']=sorted([event(v) for v in value['completions']],key=lambda r:(r['source'],r['event_id']))
    seen=set()
    for row in value['completions']:
        key=(row['source'],row['event_id'])
        if key in seen:raise WorkbenchError('DUPLICATE_EVENT')
        seen.add(key)
    if 'planning_reference' in value:
        from .planning_report import reference
        reference(value['planning_reference'])
    return value
