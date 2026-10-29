"""Compatible private instances, content pins, bounded views and new-only outputs."""
from contextlib import closing
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import threading
import uuid
import review_store as core

SOURCE=Path(__file__).resolve().parents[1]
MAX_BODY=4*1024*1024
MAX_STORE=64*1024*1024
LIMITS={'groups':2000,'aliases':4000,'records':2000,'provenance':20000,'reviews':5000}
TABLES={'groups':('id','split'),'aliases':('id','target'),'records':('id','group_id','body','status','checks'),'provenance':('source_sha256','source_row','record_id'),'reviews':('record_id','decision','actor','note','checks','created_utc')}
FORMAT='outlands-dataset-workbench-v1'

class Refused(ValueError):pass

def encode(value):return json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode('utf-8')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def decode(raw):
    if type(raw) is not bytes or len(raw)>MAX_BODY:raise Refused('BODY_LIMIT')
    def pairs(items):
        value={}
        for k,v in items:
            if k in value:raise Refused('JSON_DUPLICATE_KEY')
            value[k]=v
        return value
    def invalid(value):raise Refused('JSON_NUMBER_INVALID')
    def bounded(value,depth=0):
        if depth>64:raise Refused('JSON_DEPTH_LIMIT')
        if type(value) is float and not math.isfinite(value):raise Refused('JSON_NUMBER_INVALID')
        if type(value) is dict:
            for v in value.values():bounded(v,depth+1)
        if type(value) is list:
            for v in value:bounded(v,depth+1)
    value=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=pairs,parse_constant=invalid);bounded(value);return value
def fields(value,required):
    if type(value) is not dict or set(value)!=set(required):raise Refused('FIELDS_INVALID')
def text(value,maximum):
    if type(value) is not str or len(value)>maximum or not value.strip():raise Refused('TEXT_INVALID')
    return value
def hash_value(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}',value) is None:raise Refused('PIN_INVALID')
    return value
def read(path,maximum=MAX_BODY):
    path=core.selected_path(core._io_path(path))
    if os.name=='nt':return core._windows().read_bounded(path,maximum,core.ReviewError,single_link=True)
    return core._read_posix(path,maximum,single_link=True)
def mkdir(path):
    path=core._export_path(path)
    with core._store_parent(path):path.mkdir(mode=0o700);core.selected_path(path,private_output=True)
def snapshot(con):
    # Explicit columns are trusted constants. A single SQLite transaction holds this view.
    result={}
    for table,columns in TABLES.items():
        rows=con.execute('SELECT '+','.join(columns)+' FROM '+table+' ORDER BY '+','.join(columns)+' LIMIT ?', (LIMITS[table]+1,)).fetchall()
        if len(rows)>LIMITS[table]:raise Refused('WORKBENCH_VIEW_LIMIT')
        result[table]=[dict(zip(columns,tuple(row))) for row in rows]
    groups={row['id']:row['split'] for row in result['groups']}
    for row in result['groups']:
        if type(row['id']) is not str or not re.fullmatch('[a-zA-Z0-9_-]{1,80}',row['id']) or row['split'] not in core.SPLITS:raise Refused('RECORD_CONTENT_INVALID')
    for row in result['records']:
        hash_value(row['id']);body=decode(row['body'].encode('utf-8'));fields(body,{'text'})
        if type(body['text']) is not str or not body['text'].strip() or len(row['body'].encode())>core.MAX_RECORD or core.canonical(body)!=row['body'] or digest(row['body'].encode('utf-8'))!=row['id'] or row['status'] not in {'pending','approved','rejected'}:raise Refused('RECORD_CONTENT_INVALID')
        checks=decode(row['checks'].encode('utf-8'))
        if type(checks) is not dict or set(checks)-core.CHECKS or any(type(v) is not bool for v in checks.values()):raise Refused('RECORD_CONTENT_INVALID')
        if row['group_id'] not in groups:raise Refused('RECORD_CONTENT_INVALID')
    for row in result['reviews']:
        if row['decision'] not in {'pending','approved','rejected'} or type(row['actor']) is not str or type(row['note']) is not str or len(row['actor'])>128 or len(row['note'])>4096:raise Refused('RECORD_CONTENT_INVALID')
    return result,digest(encode(result))

class Workbench:
    def __init__(self,root):
        self.root=core._export_path(root);self.lock=threading.RLock();self.uncertain=False;self.closed=False;self.marker=self.root/'.session-lock';self.identity=None
        if decode(read(self.root/'workspace.json'))!={'format':FORMAT}:raise Refused('WORKSPACE_FORMAT_INVALID')
        mkdir(self.marker);info=self.marker.lstat();self.identity=(info.st_dev,info.st_ino)
        self.store=self.local('database/review.sqlite3')
        try:self.state()
        except BaseException:self.close();raise
    @staticmethod
    def initialize(root,source=None):
        root=core._export_path(root);mkdir(root)
        for name in ('inbox','database','exports','backups'):mkdir(root/name)
        core._write_export(root/'workspace.json',encode({'format':FORMAT}));core._write_export(root/'inbox/sample-records.jsonl',read(SOURCE/'examples/sample-records.jsonl'))
        target=root/'database/review.sqlite3'
        if source is None:core.initialize(target)
        else:
            source=core._export_path(source)
            # The caller must stop the selected legacy instance first. Never open it for writes.
            with core._store_scope(source):
                with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as con:
                    core._store_checker().configure(con,readonly=True);core._validate_store(con)
                    with con:
                        con.execute('BEGIN');snapshot(con);core.initialize(target)
                        with core._store_scope(target),closing(sqlite3.connect(target.as_uri()+'?mode=rw',uri=True)) as dest:
                            core._store_checker().configure(dest);con.backup(dest);core._validate_store(dest)
        return {'status':'INITIALIZED','copied_existing_store':source is not None}
    def local(self,value,exists=True):
        if type(value) is not str:raise Refused('PATH_INVALID')
        raw=Path(value);path=core.selected_path(core._io_path(raw if raw.is_absolute() else self.root/raw))
        if not path.is_relative_to(self.root) or path==self.root:raise Refused('PATH_OUTSIDE_WORKSPACE')
        if exists and not path.exists():raise Refused('PATH_NOT_FOUND')
        return path
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def close(self):
        with self.lock:
            if self.closed:return
            if self.identity is not None:
                core.selected_path(self.marker);info=self.marker.lstat()
                if self.identity!=(info.st_dev,info.st_ino) or list(self.marker.iterdir()):raise Refused('SESSION_LOCK_CHANGED')
                self.marker.rmdir()
            self.closed=True
    def _active(self):
        if self.closed:raise Refused('WORKBENCH_CLOSED')
        core.selected_path(self.marker);info=self.marker.lstat()
        if self.identity!=(info.st_dev,info.st_ino) or list(self.marker.iterdir()):raise Refused('SESSION_LOCK_CHANGED')
    def _snapshot(self):
        self._active()
        with core.connect(self.store) as con:con.execute('BEGIN');return snapshot(con)
    def _guard(self,expected):
        hash_value(expected)
        def before(con):
            con.execute('BEGIN IMMEDIATE');_,head=snapshot(con)
            if head!=expected:raise Refused('STALE_STATE_REFRESH_REQUIRED')
        return before
    def state(self,query='',status='',split='',offset=0,limit=100,refresh=False):
        with self.lock:
            if type(query) is not str or len(query)>200 or status not in {'','pending','approved','rejected'} or split not in {'','train','validation','test'} or type(offset) is not int or not 0<=offset<=2000 or type(limit) is not int or not 1<=limit<=250:raise Refused('FILTER_INVALID')
            data,head=self._snapshot();groups={r['id']:r['split'] for r in data['groups']};rows=[]
            for r in data['records']:
                body=decode(r['body'].encode())['text'];row=dict(id=r['id'],group=r['group_id'],split=groups[r['group_id']],status=r['status'],preview=body[:180])
                if (not status or row['status']==status) and (not split or row['split']==split) and query.casefold() in body.casefold():rows.append(row)
            if refresh:self.uncertain=False
            return dict(head=head,records=rows[offset:offset+limit],matched=len(rows),total=len(data['records']),offset=offset,limit=limit,counts={s:sum(r['status']==s for r in data['records']) for s in ('pending','approved','rejected')},refresh_required=self.uncertain,public_release_authorized=False)
    def detail(self,identifier):
        with self.lock:
            hash_value(identifier);data,head=self._snapshot();row=next((r for r in data['records'] if r['id']==identifier),None)
            if row is None:raise Refused('RECORD_NOT_FOUND')
            group=next(r for r in data['groups'] if r['id']==row['group_id']);return dict(head=head,id=identifier,text=decode(row['body'].encode())['text'],status=row['status'],checks=decode(row['checks'].encode()),group=group['id'],split=group['split'],aliases=[r['id'] for r in data['aliases'] if r['target']==group['id']],linked_records=sum(r['group_id']==group['id'] for r in data['records']),provenance=[r for r in data['provenance'] if r['record_id']==identifier],reviews=[r for r in data['reviews'] if r['record_id']==identifier],credential_pattern=bool(core.SECRET.search(row['body'])))
    def mutate(self,operation,body):
        with self.lock:
            self._active()
            if self.uncertain:raise Refused('OPERATION_UNCERTAIN_REFRESH_REQUIRED')
            shapes={'import':{'expected','file'},'review':{'expected','id','decision','actor','note','checks'},'export':{'expected'},'backup':{'expected'}}
            if operation not in shapes:raise Refused('OPERATION_INVALID')
            fields(body,shapes[operation]);expected=hash_value(body['expected']);_,head=self._snapshot()
            if head!=expected:raise Refused('STALE_STATE_REFRESH_REQUIRED')
            if operation=='review':
                hash_value(body['id']);text(body['actor'],128);text(body['note'],4096);fields(body['checks'],core.CHECKS)
                if body['decision'] not in {'pending','approved','rejected'} or any(type(v) is not bool for v in body['checks'].values()):raise Refused('REVIEW_INVALID')
                if body['decision']=='approved' and not all(body['checks'].values()):raise Refused('FOUR_CHECKS_REQUIRED')
                if self.detail(body['id'])['credential_pattern'] and body['decision']=='approved':raise Refused('NEW_REDACTED_RECORD_REQUIRED')
            if operation=='import':source=self.local(body['file']);read(source)
            try:
                if operation=='import':result=core.import_records(self.store,source,_guard=self._guard(expected),_after=snapshot)
                elif operation=='review':result=core.review(self.store,body['id'],body['decision'],body['actor'],body['note'],body['checks'],_guard=self._guard(expected),_after=snapshot)
                elif operation=='export':result=self._export(expected)
                else:result=self._backup(expected)
                return dict(result=result,head=self.state()['head'])
            except Refused:raise
            except BaseException:
                self.uncertain=True;raise Refused('OPERATION_UNCERTAIN_REFRESH_REQUIRED') from None
    def _export(self,expected):
        folder=self.local('exports/'+uuid.uuid4().hex,False);mkdir(folder);target=folder/'approved.jsonl';result=core.export_records(self.store,target,_guard=self._guard(expected));raw=read(target,core.MAX_EXPORT)
        if digest(raw)!=result['sha256']:raise Refused('EXPORT_READBACK_CHANGED')
        manifest=dict(format='outlands-dataset-export-v1',store_head=expected,records=result['records'],files={'approved.jsonl':dict(bytes=len(raw),sha256=digest(raw))},public_release_authorized=False)
        core._write_export(folder/'manifest.json',encode(manifest));return dict(directory=folder.relative_to(self.root).as_posix(),manifest=manifest)
    def _backup(self,expected):
        destination=self.local('backups/'+uuid.uuid4().hex+'.sqlite3',False);core.initialize(destination)
        with core.connect(self.store) as source:
            self._guard(expected)(source)
            # SQLite backup needs a read transaction rather than a pending write transaction.
            source.rollback();source.execute('BEGIN');_,head=snapshot(source)
            if head!=expected:raise Refused('STALE_STATE_REFRESH_REQUIRED')
            with core._store_scope(destination),closing(sqlite3.connect(destination.as_uri()+'?mode=rw',uri=True)) as dest:
                core._store_checker().configure(dest);source.backup(dest);core._validate_store(dest);_,copied=snapshot(dest)
                if copied!=expected:raise Refused('BACKUP_CONTENT_CHANGED')
        raw=read(destination,MAX_STORE);return dict(file=destination.relative_to(self.root).as_posix(),bytes=len(raw),sha256=digest(raw),store_head=expected,database_only=True)

def recover(root,confirmed):
    if confirmed is not True:raise Refused('STOPPED_ASSERTION_REQUIRED')
    root=core._export_path(root);marker=core.selected_path(root/'.session-lock')
    if not marker.is_dir() or list(marker.iterdir()):raise Refused('SESSION_LOCK_REFUSED')
    marker.rmdir()
    with Workbench(root):pass

