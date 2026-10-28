"""Explicit private instances and reviewed Windows/POSIX file/store boundaries."""
from contextlib import contextmanager
import argparse
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import threading

from .vendor import store_io as guarded

SOURCE=Path(__file__).resolve().parent.parent
PROTECTED=next((p for p in SOURCE.parents if (p/'.git').exists()),SOURCE)
guarded.PACKAGE=PROTECTED
MAX_INPUT=4*1024*1024
MAX_STORE=64*1024*1024
FORMAT='outlands-backup-recovery-workbench-v1'
ROOT=None
_identity=None
DATABASE_LOCK=threading.RLock()


class WorkbenchError(ValueError):pass


class Parser(argparse.ArgumentParser):
    def error(self,message):raise WorkbenchError('ARGUMENTS_INVALID')


@contextmanager
def io_errors():
    try:yield
    except WorkbenchError:raise
    except (OSError,guarded.ReviewError):raise WorkbenchError('FILESYSTEM_REFUSED') from None


def read_bytes(path,maximum=MAX_INPUT):
    with io_errors():
        selected=guarded.selected_path(guarded._io_path(path))
        if os.name=='nt':return guarded._windows().read_bounded(selected,maximum,guarded.ReviewError,single_link=True)
        return guarded._read_posix(selected,maximum,single_link=True)


def write_new(path,raw):
    if len(raw)>MAX_INPUT:raise WorkbenchError('OUTPUT_LIMIT')
    with io_errors():guarded._write_export(guarded._export_path(path),raw)


def mkdir(path):
    with io_errors(),guarded._store_parent(path):
        path.mkdir(mode=0o700);guarded.selected_path(path,private_output=True)


def decode(raw):
    if len(raw)>MAX_INPUT:raise WorkbenchError('INPUT_LIMIT')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise WorkbenchError('JSON_DUPLICATE_KEY')
            result[key]=value
        return result
    def constant(value):raise WorkbenchError('JSON_NUMBER_INVALID')
    def check(value,depth=0):
        if depth>64:raise WorkbenchError('JSON_DEPTH_LIMIT')
        if type(value) is float and not math.isfinite(value):raise WorkbenchError('JSON_NUMBER_INVALID')
        if type(value) is dict:
            for item in value.values():check(item,depth+1)
        if type(value) is list:
            for item in value:check(item,depth+1)
    try:
        value=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=pairs,parse_constant=constant);check(value);return value
    except WorkbenchError:raise
    except (ValueError,UnicodeError,RecursionError):raise WorkbenchError('JSON_INVALID') from None


def encode(value):return json.dumps(value,ensure_ascii=True,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
def digest(raw):return hashlib.sha256(raw).hexdigest()


def local_path(value,must_exist=True):
    if ROOT is None:raise WorkbenchError('WORKSPACE_REQUIRED')
    raw=Path(value);selected=raw if raw.is_absolute() else ROOT/raw
    with io_errors():selected=guarded.selected_path(guarded._io_path(selected))
    if not selected.is_relative_to(ROOT):raise WorkbenchError('PATH_OUTSIDE_WORKSPACE')
    if must_exist and not selected.exists():raise WorkbenchError('PATH_NOT_FOUND')
    return selected


def configure(value,*,create=False,confirm_stopped=False):
    global ROOT,_identity
    if ROOT is not None:raise WorkbenchError('INSTANCE_ALREADY_SELECTED')
    with io_errors():root=guarded._export_path(value)
    if root.is_relative_to(SOURCE):raise WorkbenchError('PRIVATE_STATE_INSIDE_SOURCE')
    if create:
        mkdir(root)
        for name in ('inbox','reports','index-backups','database','snapshots','restores'):mkdir(root/name)
        write_new(root/'workspace.json',encode(dict(format=FORMAT)))
        from .filesystem import seed_fictional
        seed_fictional(root)
    if decode(read_bytes(root/'workspace.json'))!={'format':FORMAT}:raise WorkbenchError('WORKSPACE_FORMAT_INVALID')
    lock=root/'.session-lock'
    if lock.exists() or lock.is_symlink():
        if confirm_stopped is not True:raise WorkbenchError('INSTANCE_BUSY_OR_STALE')
        with io_errors():
            guarded.selected_path(lock)
            if not lock.is_dir() or list(lock.iterdir()):raise WorkbenchError('LOCK_REFUSED')
            lock.rmdir()
    mkdir(lock);info=lock.lstat();_identity=(info.st_dev,info.st_ino);ROOT=root


def close():
    global ROOT,_identity
    if ROOT is None:return
    try:
        lock=ROOT/'.session-lock'
        with io_errors():
            guarded.selected_path(lock);info=lock.lstat()
            if (info.st_dev,info.st_ino)!=_identity or not lock.is_dir() or list(lock.iterdir()):raise WorkbenchError('LOCK_CHANGED')
            lock.rmdir()
    finally:ROOT=None;_identity=None


@lru_cache(maxsize=1)
def expected_schema():
    con=sqlite3.connect(':memory:')
    try:
        con.executescript((SOURCE/'recovery/schema.sql').read_text(encoding='utf-8'))
        return tuple(con.execute('SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name'))
    finally:con.close()


def validate_schema(con):
    rows=con.execute('SELECT type,substr(name,1,257),substr(tbl_name,1,257),substr(sql,1,16385) FROM sqlite_schema ORDER BY type,name LIMIT 129').fetchall()
    if len(rows)>128 or tuple(tuple(r) for r in rows)!=expected_schema():raise WorkbenchError('STORE_SCHEMA_REFUSED')
    if con.execute('PRAGMA user_version').fetchone()[0]!=0:raise WorkbenchError('STORE_VERSION_REFUSED')
    if con.execute('SELECT value FROM meta WHERE key=?',('format',)).fetchone()!=('1',):raise WorkbenchError('STORE_VERSION_REFUSED')


def _connection(path):
    con=sqlite3.connect(path.as_uri()+'?mode=rw',uri=True,timeout=5)
    con.execute('PRAGMA foreign_keys=ON')
    if hasattr(con,'enable_load_extension'):con.enable_load_extension(False)
    return con


def initialize():
    path=local_path('database/workbench.sqlite3',False);write_new(path,b'')
    with DATABASE_LOCK,io_errors(),guarded._store_scope(path,initial=True):
        con=_connection(path)
        try:
            con.executescript('BEGIN IMMEDIATE;\n'+(SOURCE/'recovery/schema.sql').read_text(encoding='utf-8'))
            con.execute('INSERT INTO meta VALUES(?,?)',('format','1'));validate_schema(con);con.commit()
        except BaseException:con.rollback();raise
        finally:con.close()


@contextmanager
def connect():
    path=local_path('database/workbench.sqlite3')
    with DATABASE_LOCK,io_errors(),guarded._store_scope(path):
        con=_connection(path)
        try:
            validate_schema(con)
            with con:
                yield con
                if con.execute('PRAGMA page_count').fetchone()[0]*con.execute('PRAGMA page_size').fetchone()[0]>MAX_STORE:raise WorkbenchError('STORE_LIMIT')
        finally:con.close()
