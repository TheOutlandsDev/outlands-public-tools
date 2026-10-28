"""Strict identities, class/split contracts and bounded JSON fields."""
import re
from .runtime import WorkbenchError,decode,encode,digest


def fields(value,required,optional=()):
    if type(value) is not dict or set(value)-set(required)-set(optional) or not set(required)<=set(value):raise WorkbenchError('FIELDS_INVALID')
    return value


def token(value):
    if type(value) is not str or not re.fullmatch(r'[A-Za-z][A-Za-z0-9._-]{0,63}',value):raise WorkbenchError('IDENTITY_INVALID')
    return value


def integer(value,low,high):
    if type(value) is not int or not low<=value<=high:raise WorkbenchError('INTEGER_INVALID')
    return value


def text(value,maximum):
    if type(value) is not str or not 1<=len(value)<=maximum or not value.strip() or any(ord(x)<32 for x in value):raise WorkbenchError('TEXT_INVALID')
    return value.strip()


def hash_value(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}',value):raise WorkbenchError('HASH_INVALID')
    return value


def dataset(raw):
    value=decode(raw);fields(value,('format','dataset_id','title','classes','split'))
    if value['format']!='outlands-visual-dataset-v1':raise WorkbenchError('DATASET_FORMAT_INVALID')
    token(value['dataset_id']);text(value['title'],120)
    if type(value['classes']) is not list or not 1<=len(value['classes'])<=8:raise WorkbenchError('CLASS_LIMIT')
    ids=set();labels=set()
    for row in value['classes']:
        fields(row,('id','label'));integer(row['id'],1,255);token(row['label'])
        if row['id'] in ids or row['label'].casefold() in labels:raise WorkbenchError('CLASS_IDENTITY_CONFLICT')
        ids.add(row['id']);labels.add(row['label'].casefold())
    value['classes']=sorted(value['classes'],key=lambda r:r['id'])
    split=value['split'];fields(split,('seed','train_per_mille','validation_per_mille','test_per_mille'));token(split['seed'])
    for key in ('train_per_mille','validation_per_mille','test_per_mille'):integer(split[key],1,998)
    if sum(split[k] for k in ('train_per_mille','validation_per_mille','test_per_mille'))!=1000:raise WorkbenchError('SPLIT_INVALID')
    return value


def partition(config,specimen_id):
    token(specimen_id);bucket=int(digest((config['split']['seed']+'\0'+specimen_id).encode())[:8],16)%1000
    if bucket<config['split']['train_per_mille']:return 'train'
    if bucket<config['split']['train_per_mille']+config['split']['validation_per_mille']:return 'validation'
    return 'test'
