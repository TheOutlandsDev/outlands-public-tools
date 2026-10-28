"""Bounded neutral datasets, immutable experiments and chronological/group boundaries."""
import math
import re
from . import runtime as r


def fields(value,required):
    if type(value) is not dict or set(value)!=set(required):raise r.WorkbenchError('FIELDS_INVALID')


def token(value):
    if type(value) is not str or not re.fullmatch(r'[A-Za-z][A-Za-z0-9._-]{0,63}',value):raise r.WorkbenchError('IDENTITY_INVALID')
    reserved={'con','prn','aux','nul'}|{'com'+str(i) for i in range(1,10)}|{'lpt'+str(i) for i in range(1,10)}
    if value.endswith('.') or value.split('.',1)[0].casefold() in reserved:raise r.WorkbenchError('IDENTITY_NOT_PORTABLE')
    return value


def integer(value,low,high):
    if type(value) is not int or not low<=value<=high:raise r.WorkbenchError('INTEGER_INVALID')
    return value


def number(value,low,high):
    if type(value) not in (int,float) or not low<=value<=high or not math.isfinite(value):raise r.WorkbenchError('NUMBER_INVALID')
    return float(value)


def text(value,maximum,empty=False):
    if type(value) is not str or len(value)>maximum or not empty and not value.strip() or any(ord(x)<32 for x in value):raise r.WorkbenchError('TEXT_INVALID')
    return value


def hash_value(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}',value):raise r.WorkbenchError('HASH_INVALID')
    return value


def dataset(raw):
    value=r.decode(raw);fields(value,('format','dataset_id','title','feature_names','rows'))
    if value['format']!='outlands-ml-dataset-v1':raise r.WorkbenchError('DATASET_FORMAT_INVALID')
    token(value['dataset_id']);text(value['title'],120);names=value['feature_names']
    if type(names) is not list or not 1<=len(names)<=8:raise r.WorkbenchError('FEATURE_LIMIT')
    for name in names:token(name)
    if len({name.casefold() for name in names})!=len(names):raise r.WorkbenchError('FEATURE_IDENTITY_CONFLICT')
    rows=value['rows']
    if type(rows) is not list or not 1<=len(rows)<=1200:raise r.WorkbenchError('ROW_LIMIT')
    ids=set();groups={}
    for row in rows:
        fields(row,('row_id','group_id','decision_day','label_available_day','features','feature_available_day','outcome'))
        token(row['row_id']);token(row['group_id']);key=row['row_id'].casefold();group=row['group_id'].casefold()
        if key in ids or group in groups and groups[group]!=row['group_id']:raise r.WorkbenchError('ROW_OR_GROUP_IDENTITY_CONFLICT')
        ids.add(key);groups[group]=row['group_id'];integer(row['decision_day'],0,1000000);integer(row['label_available_day'],row['decision_day'],1000000);integer(row['outcome'],0,1)
        fields(row['features'],names);fields(row['feature_available_day'],names)
        for name in names:
            feature=row['features'][name];available=row['feature_available_day'][name]
            if feature is None:
                if available is not None:raise r.WorkbenchError('MISSING_FEATURE_TIME_INVALID')
            else:
                number(feature,-1000000,1000000);integer(available,0,1000000)
                if available>row['decision_day']:raise r.WorkbenchError('FEATURE_NOT_AVAILABLE_AT_DECISION')
    value['rows']=sorted(rows,key=lambda row:(row['decision_day'],row['row_id']))
    return value


def experiment(raw):
    value=r.decode(raw);fields(value,('format','experiment_id','dataset_id','dataset_sha256','split','learner','thresholds'))
    if value['format']!='outlands-ml-experiment-v1':raise r.WorkbenchError('EXPERIMENT_FORMAT_INVALID')
    token(value['experiment_id']);token(value['dataset_id']);hash_value(value['dataset_sha256'])
    split=value['split'];names=('train_end_day','validation_start_day','validation_end_day','test_start_day','test_end_day','as_of_day');fields(split,names)
    for name in names:integer(split[name],1,1000000)
    if not (split['train_end_day']<split['validation_start_day']<split['validation_end_day']<split['test_start_day']<split['test_end_day']<=split['as_of_day']):raise r.WorkbenchError('CHRONOLOGY_INVALID')
    learner=value['learner'];fields(learner,('iterations','learning_rate','l2'));integer(learner['iterations'],1,600);number(learner['learning_rate'],.001,1);number(learner['l2'],0,1)
    thresholds=value['thresholds']
    if type(thresholds) is not list or not 1<=len(thresholds)<=19:raise r.WorkbenchError('THRESHOLD_LIMIT')
    for threshold in thresholds:number(threshold,.01,.99)
    if len(set(thresholds))!=len(thresholds):raise r.WorkbenchError('THRESHOLD_DUPLICATE')
    value['thresholds']=sorted(thresholds);return value


def partition(data,config):
    split=config['split'];result=dict(train=[],validation=[],test=[],excluded=[]);groups={}
    for row in data['rows']:
        day=row['decision_day'];part='train' if day<split['train_end_day'] else 'validation' if split['validation_start_day']<=day<split['validation_end_day'] else 'test' if split['test_start_day']<=day<split['test_end_day'] else None
        if part:
            old=groups.setdefault(row['group_id'],part)
            if old!=part:raise r.WorkbenchError('GROUP_CROSSES_PARTITIONS')
        reason='gap_or_outside_window' if part is None else 'training_label_not_available' if part=='train' and row['label_available_day']>=split['validation_start_day'] else 'validation_label_not_available' if part=='validation' and row['label_available_day']>=split['test_start_day'] else 'test_label_pending' if part=='test' and row['label_available_day']>split['as_of_day'] else None
        if reason:result['excluded'].append(dict(row_id=row['row_id'],reason=reason))
        else:result[part].append(row)
    if len(result['train'])<2 or len(result['validation'])<2 or not result['test']:raise r.WorkbenchError('PARTITION_EMPTY_OR_TOO_SMALL')
    for part in ('train','validation'):
        if {row['outcome'] for row in result[part]}!={0,1}:raise r.WorkbenchError('TRAINING_AND_VALIDATION_REQUIRE_BOTH_CLASSES')
    return result
