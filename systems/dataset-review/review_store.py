#!/usr/bin/env python3
"""Single-operator private dataset review store. No network or model execution."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
from datetime import datetime,timezone
from contextlib import contextmanager

PACKAGE=Path(__file__).resolve().parents[2]
SPLITS={'train':0,'validation':1,'test':2}
CHECKS={'quality','privacy','rights','context'}
MAX_IMPORT=4*1024*1024
MAX_RECORD=64*1024
MAX_EXPORT=16*1024*1024
SECRET=re.compile(r'-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|sk-(?:proj-)?[A-Za-z0-9_-]{32,}')
SCHEMA='''
PRAGMA foreign_keys=ON;
CREATE TABLE groups (id TEXT PRIMARY KEY, split TEXT NOT NULL);
CREATE TABLE aliases (id TEXT PRIMARY KEY,target TEXT NOT NULL REFERENCES groups(id));
CREATE TABLE records (id TEXT PRIMARY KEY, group_id TEXT NOT NULL REFERENCES groups(id),
 body TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', checks TEXT NOT NULL DEFAULT '{}');
CREATE TABLE provenance (source_sha256 TEXT NOT NULL, source_row INTEGER NOT NULL,
 record_id TEXT NOT NULL REFERENCES records(id), PRIMARY KEY(source_sha256,source_row));
CREATE TABLE reviews (record_id TEXT NOT NULL REFERENCES records(id), decision TEXT NOT NULL,
 actor TEXT NOT NULL,note TEXT NOT NULL,checks TEXT NOT NULL,created_utc TEXT NOT NULL);
'''

class ReviewError(ValueError):pass

def selected_path(value, *, private_output=False):
    path=Path(os.path.abspath(value))
    for part in [*reversed(path.parents),path]:
        if part.exists() or part.is_symlink():
            info=part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:raise ReviewError('LINK_FORBIDDEN')
    if private_output and path.is_relative_to(PACKAGE):raise ReviewError('PRIVATE_STATE_INSIDE_REPOSITORY')
    if not path.parent.is_dir():raise ReviewError('PARENT_REQUIRED')
    return path

@contextmanager
def connect(store):
    path=selected_path(store,private_output=True)
    if not path.is_file() or path.stat().st_size>64*1024*1024:raise ReviewError('STORE_UNAVAILABLE')
    con=sqlite3.connect(path.as_uri()+'?mode=rw',uri=True)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        with con:yield con
    finally:con.close()

def initialize(store):
    path=selected_path(store,private_output=True)
    with path.open('xb'):pass
    with connect(path) as con:con.executescript(SCHEMA)
    return dict(status='INITIALIZED')

def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)

def import_records(store,source):
    data=_read_import(source)
    sha=hashlib.sha256(data).hexdigest()
    prepared=[]
    for number,line in enumerate(data.decode('utf-8-sig').splitlines(),1):
        if not line.strip():continue
        row=json.loads(line)
        if not isinstance(row,dict) or not isinstance(row.get('text'),str) or not row['text'].strip():raise ReviewError('TEXT_REQUIRED')
        group=row.get('group');split=row.get('split','train')
        if not isinstance(group,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',group) or split not in SPLITS:raise ReviewError('GROUP_OR_SPLIT_INVALID')
        body=canonical(dict(text=row['text'].replace('\r\n','\n').strip()))
        if len(body.encode('utf-8'))>MAX_RECORD:raise ReviewError('RECORD_LIMIT')
        prepared.append((number,group,split,body,hashlib.sha256(body.encode('utf-8')).hexdigest()))
    added=0
    with connect(store) as con:
        for number,group,split,body,identifier in prepared:
            alias=con.execute('SELECT target FROM aliases WHERE id=?',(group,)).fetchone()
            if alias:group=alias['target']
            old=con.execute('SELECT split FROM groups WHERE id=?',(group,)).fetchone()
            split=max([split,old['split']] if old else [split],key=SPLITS.get)
            con.execute('INSERT INTO groups VALUES(?,?) ON CONFLICT(id) DO UPDATE SET split=excluded.split',(group,split))
            existing=con.execute('SELECT group_id FROM records WHERE id=?',(identifier,)).fetchone()
            if existing and existing['group_id']!=group:
                previous=existing['group_id']
                previous_split=con.execute('SELECT split FROM groups WHERE id=?',(previous,)).fetchone()['split']
                winner=min(previous,group);loser=max(previous,group)
                strongest=max(split,previous_split,key=SPLITS.get)
                con.execute('UPDATE groups SET split=? WHERE id=?',(strongest,winner))
                con.execute('UPDATE records SET group_id=? WHERE group_id=?',(winner,loser))
                con.execute('UPDATE aliases SET target=? WHERE target=?',(winner,loser))
                con.execute('INSERT OR REPLACE INTO aliases VALUES(?,?)',(loser,winner))
                con.execute('DELETE FROM groups WHERE id=?',(loser,))
                group=winner
            cursor=con.execute('INSERT OR IGNORE INTO records(id,group_id,body) VALUES(?,?,?)',(identifier,group,body))
            added+=cursor.rowcount
            con.execute('INSERT OR IGNORE INTO provenance VALUES(?,?,?)',(sha,number,identifier))
    return dict(status='IMPORTED_PENDING',added=added,rows=len(prepared),source_sha256=sha)

def review(store,identifier,decision,actor,note,checks):
    if decision not in {'pending','approved','rejected'} or not actor.strip() or not note.strip() or len(actor)>128 or len(note)>4096:raise ReviewError('REVIEW_REQUIRED')
    if decision=='approved' and not all(checks.get(key) is True for key in CHECKS):raise ReviewError('FOUR_CHECKS_REQUIRED')
    with connect(store) as con:
        row=con.execute('SELECT body FROM records WHERE id=?',(identifier,)).fetchone()
        if not row:raise ReviewError('UNKNOWN_RECORD')
        if decision=='approved' and SECRET.search(row['body']):raise ReviewError('CREDENTIAL_PATTERN_REQUIRES_NEW_REDACTED_RECORD')
        encoded=canonical({key:checks.get(key) is True for key in sorted(CHECKS)})
        con.execute('UPDATE records SET status=?,checks=? WHERE id=?',(decision,encoded,identifier))
        con.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?)',(identifier,decision,actor,note,encoded,datetime.now(timezone.utc).isoformat()))
    return dict(status=decision.upper(),id=identifier)

def records(store):
    with connect(store) as con:
        return [dict(row) for row in con.execute('SELECT records.id,group_id,status,split FROM records JOIN groups ON groups.id=records.group_id ORDER BY records.id')]

def export_records(store,destination):
    destination=_export_path(destination)
    lines=[];total=0
    with connect(store) as con:
        for row in con.execute("SELECT records.id,body,checks,split FROM records JOIN groups ON groups.id=records.group_id WHERE status='approved' ORDER BY records.id"):
            if not all(json.loads(row['checks']).get(key) is True for key in CHECKS):continue
            line=canonical(dict(id=row['id'],text=json.loads(row['body'])['text'],split=row['split']))+'\n'
            total+=len(line.encode('utf-8'))
            if total>MAX_EXPORT:raise ReviewError('EXPORT_LIMIT')
            lines.append(line)
    _write_export(destination,''.join(lines).encode('utf-8'))
    return dict(status='PRIVATE_EXPORT_WRITTEN',records=len(lines),sha256=hashlib.sha256(''.join(lines).encode('utf-8')).hexdigest())

_WINDOWS_BACKEND=None


def _windows():
    global _WINDOWS_BACKEND
    if _WINDOWS_BACKEND is None:
        spec=importlib.util.spec_from_file_location('outlands_review_io_windows',Path(__file__).with_name('review_io_windows.py'))
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _WINDOWS_BACKEND=module
    return _WINDOWS_BACKEND


def _io_path(value):
    if os.name=='nt':return _windows().selected_path(value,_windows()._core(ReviewError))
    raw=os.fspath(value)
    if not isinstance(raw,str) or not raw or '..' in Path(raw).parts:raise ReviewError('IO_PATH_INVALID')
    return Path(os.path.abspath(raw))


def _safe_posix(path):
    for part in [*reversed(path.parents),path]:
        info=part.lstat()
        if stat.S_ISLNK(info.st_mode):raise ReviewError('LINK_FORBIDDEN')
        if part!=path and not stat.S_ISDIR(info.st_mode):raise ReviewError('PARENT_NOT_DIRECTORY')


def _read_posix(value,maximum,*,single_link=False):
    path=_io_path(value)
    _safe_posix(path)
    expected=path.lstat()
    if not stat.S_ISREG(expected.st_mode):raise ReviewError('INPUT_NOT_REGULAR')
    if expected.st_size>maximum:raise ReviewError('INPUT_TOO_LARGE')
    if single_link and expected.st_nlink!=1:raise ReviewError('OUTPUT_LINK_COUNT')
    flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0)
    fd=os.open(path,flags)
    try:
        os.set_inheritable(fd,False)
        before=os.fstat(fd)
        identity=lambda info:(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_nlink)
        if not stat.S_ISREG(before.st_mode) or identity(before)!=identity(expected):raise ReviewError('INPUT_CHANGED')
        chunks=[];size=0
        while True:
            block=os.read(fd,min(65536,maximum+1-size))
            if not block:break
            size+=len(block)
            if size>maximum:raise ReviewError('INPUT_TOO_LARGE')
            chunks.append(block)
        after=os.fstat(fd)
        if (size!=before.st_size or identity(before)!=identity(after)
                or identity(path.lstat())!=identity(after)):raise ReviewError('INPUT_CHANGED')
        _safe_posix(path)
        return b''.join(chunks)
    finally:os.close(fd)


def _read_import(value):
    path=selected_path(_io_path(value))
    if not path.is_file() or path.stat().st_size>MAX_IMPORT:raise ReviewError('IMPORT_LIMIT')
    if os.name=='nt':return _windows().read_bounded(path,MAX_IMPORT,ReviewError)
    return _read_posix(path,MAX_IMPORT)


def _export_path(value):
    path=selected_path(_io_path(value),private_output=True)
    if os.name=='nt':
        with _windows().export_scope(path,PACKAGE,ReviewError):pass
    return path


def _write_posix(path,data):
    path=_export_path(path)
    _safe_posix(path.parent)
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0)
    fd=os.open(path,flags,0o600)
    try:
        os.set_inheritable(fd,False)
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size!=0 or before.st_nlink!=1:raise ReviewError('OUTPUT_CHANGED')
        position=0
        while position<len(data):
            block=data[position:position+65536]
            written=os.write(fd,block)
            if not 0<written<=len(block):raise ReviewError('OUTPUT_IO_ERROR')
            position+=written
        os.fsync(fd)
        written=os.fstat(fd)
        identity=lambda info:(info.st_dev,info.st_ino,info.st_mode,info.st_nlink)
        if identity(before)!=identity(written) or written.st_size!=len(data):raise ReviewError('OUTPUT_CHANGED')
        if _read_posix(path,len(data),single_link=True)!=data:raise ReviewError('EXPORT_VERIFY_FAILED')
        after=os.fstat(fd)
        final=path.lstat()
        stable=lambda info:(*identity(info),info.st_size,info.st_mtime_ns,info.st_ctime_ns)
        if stable(written)!=stable(after) or stable(after)!=stable(final):raise ReviewError('OUTPUT_CHANGED')
        _safe_posix(path)
    finally:os.close(fd)


def _write_export(path,data):
    if type(data) is not bytes or len(data)>MAX_EXPORT:raise ReviewError('EXPORT_LIMIT')
    if os.name=='nt':
        backend=_windows()
        with backend.export_scope(path,PACKAGE,ReviewError) as output:
            backend.exclusive_write(output,data,ReviewError)
            if backend.read_bounded(output,len(data),ReviewError,single_link=True)!=data:raise ReviewError('EXPORT_VERIFY_FAILED')
    else:_write_posix(path,data)


class Parser(argparse.ArgumentParser):
    def error(self,message):raise ReviewError('INVALID_ARGUMENTS')

def main(argv=None):
    parser=Parser(description=__doc__,prog='review_store.py' if os.name=='nt' else None);parser.add_argument('--store',required=True)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init');sub.add_parser('list')
    imp=sub.add_parser('import');imp.add_argument('--input',required=True)
    rev=sub.add_parser('review');rev.add_argument('--id',required=True);rev.add_argument('--decision',required=True,choices=['pending','approved','rejected']);rev.add_argument('--actor',required=True);rev.add_argument('--note',required=True)
    for check in sorted(CHECKS):rev.add_argument('--'+check,action='store_true')
    exp=sub.add_parser('export');exp.add_argument('--output',required=True)
    try:
        args=parser.parse_args(argv)
        if args.command=='init':result=initialize(args.store)
        elif args.command=='import':result=import_records(args.store,args.input)
        elif args.command=='list':result=records(args.store)
        elif args.command=='review':result=review(args.store,args.id,args.decision,args.actor,args.note,{key:getattr(args,key) for key in CHECKS})
        else:result=export_records(args.store,args.output)
        print(canonical(result));return 0
    except KeyboardInterrupt:
        if os.name!='nt':raise
        print(canonical(dict(status='ERROR',code='REVIEW_OPERATION_INTERRUPTED')));return 130
    except (OSError,ValueError,UnicodeError,sqlite3.Error,TypeError,RecursionError):
        print(canonical(dict(status='ERROR',code='REVIEW_OPERATION_FAILED')));return 2

if __name__=='__main__':sys.exit(main())
