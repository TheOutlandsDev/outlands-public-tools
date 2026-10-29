"""Explicit private instances, bounded I/O and an opt-in loopback model client."""
import argparse
from contextlib import contextmanager
import gzip
from functools import lru_cache
import io
import json
import math
import os
from pathlib import Path
import sqlite3
import sys
import threading
from urllib.error import HTTPError,URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler,ProxyHandler,Request,build_opener

from .vendor import store_io as guarded

SOURCE = Path(__file__).resolve().parent.parent
PROTECTED = next((p for p in SOURCE.parents if (p/".git").exists()), SOURCE)
guarded.PACKAGE = PROTECTED
MAX_INPUT = 16*1024*1024
MAX_RECORD = 1024*1024
MAX_ROWS = 10000
FORMAT = "outlands-corpus-model-workbench-v1"
_root = None
_lock_identity = None
_client = None
_sqlite = threading.local()
_database_lock = threading.RLock()
DEFAULT_SETTINGS = dict(ollama_url=None,ollama_timeout_seconds=60,
    comparison_options=dict(num_ctx=8192,num_predict=1024,temperature=0),
    max_response_characters=32000,minimum_scored_cases_for_routing=3)


class WorkbenchError(ValueError):
    """Fixed diagnostic codes; no native exception, endpoint or path text."""


class Parser(argparse.ArgumentParser):
    def error(self,message):raise WorkbenchError("ARGUMENTS_INVALID")


@contextmanager
def io_errors():
    try:yield
    except WorkbenchError:raise
    except (OSError,guarded.ReviewError):raise WorkbenchError("FILESYSTEM_REFUSED") from None


def read_bytes(path,maximum=MAX_INPUT):
    with io_errors():
        selected=guarded.selected_path(guarded._io_path(path))
        if os.name=="nt":return guarded._windows().read_bounded(selected,maximum,guarded.ReviewError,single_link=True)
        return guarded._read_posix(selected,maximum,single_link=True)


def write_new(path,raw):
    with io_errors():guarded._write_export(guarded._export_path(path),raw)


def _mkdir(path):
    with io_errors(),guarded._store_parent(path):
        path.mkdir(mode=0o700)
        guarded.selected_path(path,private_output=True)


def decode(raw):
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:raise WorkbenchError("JSON_DUPLICATE_KEY")
            value[key]=item
        return value
    def constant(value):raise WorkbenchError("JSON_NUMBER_INVALID")
    def finite(value,depth=0):
        if depth>64:raise WorkbenchError("JSON_DEPTH_LIMIT")
        if type(value) is float and not math.isfinite(value):raise WorkbenchError("JSON_NUMBER_INVALID")
        if type(value) is dict:
            for item in value.values():finite(item,depth+1)
        if type(value) is list:
            for item in value:finite(item,depth+1)
    try:
        value=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=pairs,parse_constant=constant)
        finite(value)
        return value
    except WorkbenchError:raise
    except (ValueError,UnicodeError,RecursionError):raise WorkbenchError("JSON_INVALID") from None


def configure(value,*,create=False,confirm_stopped=False):
    global _root,_lock_identity
    if _root is not None:raise WorkbenchError("INSTANCE_ALREADY_SELECTED")
    with io_errors():root=guarded._export_path(value)
    if root.is_relative_to(SOURCE):raise WorkbenchError("PRIVATE_STATE_INSIDE_SOURCE")
    if create:
        _mkdir(root)
        for name in ('config','database','inbox','sources','exports','backups','benchmarks','reports'):_mkdir(root/name)
        write_new(root/'workspace.json',json.dumps(dict(format=FORMAT)).encode())
        write_new(root/'config/settings.json',json.dumps(DEFAULT_SETTINGS,indent=2).encode())
        for name in ('sample-corpus.jsonl','coding_devops_v1.jsonl'):
            destination=root/('inbox' if name.startswith('sample') else 'benchmarks')/name
            write_new(destination,read_bytes(SOURCE/'examples'/name))
    if decode(read_bytes(root/'workspace.json',65536))!={'format':FORMAT}:raise WorkbenchError("WORKSPACE_FORMAT_INVALID")
    lock=root/'.session-lock'
    if lock.exists() or lock.is_symlink():
        if confirm_stopped is not True:raise WorkbenchError("INSTANCE_BUSY_OR_STALE")
        with io_errors():
            guarded.selected_path(lock)
            if not lock.is_dir() or list(lock.iterdir()):raise WorkbenchError("LOCK_REFUSED")
            lock.rmdir()
    _mkdir(lock)
    info=lock.lstat();_lock_identity=(info.st_dev,info.st_ino);_root=root
    from . import corpus
    corpus.ROOT=root;corpus.DB=root/'database/corpus.sqlite3'
    existing=sys.modules.get(__package__+'.models')
    if existing is not None:existing.ROOT=root
    settings()


def close():
    global _root,_lock_identity,_client
    if _root is None:return
    lock=_root/'.session-lock'
    try:
        with io_errors():
            guarded.selected_path(lock)
            info=lock.lstat()
            if (info.st_dev,info.st_ino)!=_lock_identity or not lock.is_dir() or list(lock.iterdir()):raise WorkbenchError("LOCK_CHANGED")
            lock.rmdir()
    finally:
        _root=None;_lock_identity=None;_client=None
        from . import corpus
        corpus.ROOT=None;corpus.DB=None


def local_path(value,must_exist=True):
    if _root is None:raise WorkbenchError("WORKSPACE_REQUIRED")
    raw=Path(value);selected=raw if raw.is_absolute() else _root/raw
    with io_errors():selected=guarded.selected_path(guarded._io_path(selected))
    if not selected.is_relative_to(_root):raise WorkbenchError("PATH_OUTSIDE_WORKSPACE")
    if must_exist and not selected.exists():raise WorkbenchError("PATH_NOT_FOUND")
    return selected


def settings():
    if _root is None:raise WorkbenchError("WORKSPACE_REQUIRED")
    value=decode(read_bytes(_root/'config/settings.json',65536))
    if type(value) is not dict or set(value)!=set(DEFAULT_SETTINGS):raise WorkbenchError("SETTINGS_INVALID")
    for name,low,high in (('ollama_timeout_seconds',1,120),('max_response_characters',1,200000),('minimum_scored_cases_for_routing',1,100)):
        if type(value[name]) is not int or not low<=value[name]<=high:raise WorkbenchError("SETTINGS_INVALID")
    options=value['comparison_options']
    if type(options) is not dict or set(options)!={'num_ctx','num_predict','temperature'}:raise WorkbenchError("SETTINGS_INVALID")
    if type(options['num_ctx']) is not int or not 2048<=options['num_ctx']<=32768:raise WorkbenchError("SETTINGS_INVALID")
    if type(options['num_predict']) is not int or not 1<=options['num_predict']<=options['num_ctx']-1024:raise WorkbenchError("SETTINGS_INVALID")
    if type(options['temperature']) not in (int,float) or not 0<=options['temperature']<=2:raise WorkbenchError("SETTINGS_INVALID")
    if value['ollama_url'] is not None:validate_url(value['ollama_url'])
    return value


def jsonl(path):
    yield from jsonl_bytes(read_bytes(local_path(path)),compressed=str(path).endswith('.gz'))


def jsonl_bytes(raw,*,compressed=False):
    if compressed:
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:raw=stream.read(MAX_INPUT+1)
        except (OSError,EOFError):raise WorkbenchError("GZIP_INVALID") from None
        if len(raw)>MAX_INPUT:raise WorkbenchError("IMPORT_LIMIT")
    if len(raw)>MAX_INPUT:raise WorkbenchError("IMPORT_LIMIT")
    for number,line in enumerate(raw.splitlines(),1):
        if number>MAX_ROWS or len(line)>MAX_RECORD:raise WorkbenchError("IMPORT_LIMIT")
        if line.strip():yield number,decode(line)


@lru_cache(maxsize=1)
def expected_schema():
    from . import corpus
    con=sqlite3.connect(':memory:')
    try:
        con.executescript((corpus.APP/'schema.sql').read_text(encoding='utf-8'))
        return tuple(con.execute('SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name'))
    finally:con.close()


def validate_schema(con):
    rows=con.execute('SELECT type,substr(name,1,257),substr(tbl_name,1,257),substr(sql,1,16385) FROM sqlite_schema ORDER BY type,name LIMIT 129').fetchall()
    if len(rows)>128 or tuple(tuple(row) for row in rows)!=expected_schema():raise WorkbenchError("STORE_SCHEMA_REFUSED")
    if con.execute('PRAGMA user_version').fetchone()[0]!=0:raise WorkbenchError("STORE_VERSION_REFUSED")
    version=con.execute('SELECT value FROM meta WHERE key=?',('schema_version',)).fetchone()
    if version is None or version[0]!='1':raise WorkbenchError("STORE_VERSION_REFUSED")


def _connection(path):
    con=sqlite3.connect(path.as_uri()+'?mode=rw',uri=True,timeout=5)
    con.row_factory=sqlite3.Row
    if hasattr(con,'enable_load_extension'):con.enable_load_extension(False)
    con.execute('PRAGMA foreign_keys=ON')
    return con


def initialize_database():
    from . import corpus
    if _root is None:raise WorkbenchError("WORKSPACE_REQUIRED")
    path=corpus.DB
    write_new(path,b'')
    with io_errors(),guarded._store_scope(path,initial=True):
        con=_connection(path)
        try:
            con.executescript('BEGIN IMMEDIATE;\n'+(corpus.APP/'schema.sql').read_text(encoding='utf-8'))
            con.execute('INSERT INTO meta VALUES(?,?)',('schema_version','1'))
            con.execute('INSERT INTO meta VALUES(?,?)',('created_utc',corpus.now()))
            corpus.event(con,'initialized',dict(schema_version=1))
            validate_schema(con);con.commit()
        except BaseException:con.rollback();raise
        finally:con.close()


@contextmanager
def connect():
    from . import corpus
    if _root is None:raise WorkbenchError("WORKSPACE_REQUIRED")
    active=getattr(_sqlite,'connection',None)
    if active is not None:yield active;return
    with _database_lock,io_errors(),guarded._store_scope(corpus.DB):
        con=_connection(corpus.DB)
        try:
            validate_schema(con)
            _sqlite.connection=con
            with con:yield con
        finally:_sqlite.connection=None;con.close()


def validate_url(value):
    if type(value) is not str or not 1<=len(value)<=512:raise WorkbenchError("MODEL_URL_REQUIRED")
    if any(ord(char)<=32 or ord(char)==127 for char in value):raise WorkbenchError("MODEL_URL_REFUSED")
    try:
        url=urlparse(value)
        if (url.scheme!='http' or url.hostname not in {'127.0.0.1','localhost','::1'} or url.username or url.password
                or url.path not in ('','/') or url.query or url.fragment or url.port is not None and not 1<=url.port<=65535):
            raise WorkbenchError("MODEL_URL_REFUSED")
    except ValueError:raise WorkbenchError("MODEL_URL_REFUSED") from None
    # Resolve the localhost spelling to a literal, avoiding DNS/proxy routing.
    host='[::1]' if url.hostname=='::1' else '127.0.0.1'
    return 'http://'+host+(':'+str(url.port) if url.port is not None else '')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise WorkbenchError("MODEL_REDIRECT_REFUSED")


def set_client(client):
    global _client
    _client=client


def model_request(endpoint,payload=None,url=None):
    if endpoint not in {'/api/tags','/api/chat','/api/embed'}:raise WorkbenchError("MODEL_OPERATION_REFUSED")
    config=settings()
    if _client is not None:result=_client.request(endpoint,payload)
    else:
        base=validate_url(url or config['ollama_url'])
        raw=json.dumps(payload,ensure_ascii=True,allow_nan=False).encode() if payload is not None else None
        if raw is not None and len(raw)>MAX_RECORD:raise WorkbenchError("MODEL_REQUEST_LIMIT")
        request=Request(base+endpoint,data=raw,headers={'Content-Type':'application/json'})
        try:
            with build_opener(ProxyHandler({}),NoRedirect()).open(request,timeout=config['ollama_timeout_seconds']) as response:raw=response.read(2*MAX_RECORD+1)
        except WorkbenchError:raise
        except (HTTPError,URLError,TimeoutError,OSError):raise WorkbenchError("MODEL_REQUEST_FAILED") from None
        if len(raw)>2*MAX_RECORD:raise WorkbenchError("MODEL_RESPONSE_LIMIT")
        result=decode(raw)
    if type(result) is not dict:raise WorkbenchError("MODEL_RESPONSE_INVALID")
    if endpoint=='/api/tags':
        if type(result.get('models')) is not list or len(result['models'])>64:raise WorkbenchError("MODEL_RESPONSE_INVALID")
        names=set()
        for row in result['models']:
            if type(row) is not dict:raise WorkbenchError("MODEL_RESPONSE_INVALID")
            name=row.get('name') or row.get('model');sha=row.get('digest')
            if (type(name) is not str or not 1<=len(name)<=256 or any(ord(c)<32 or ord(c)==127 for c in name)
                    or name in names or type(sha) is not str or not 1<=len(sha)<=256):raise WorkbenchError("MODEL_RESPONSE_INVALID")
            names.add(name)
            if type(row.get('details',{})) is not dict:raise WorkbenchError("MODEL_RESPONSE_INVALID")
    if endpoint=='/api/embed':
        vectors=result.get('embeddings')
        if (type(vectors) is not list or not 1<=len(vectors)<=64
                or any(type(v) is not list or not 1<=len(v)<=4096 or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>1e10 for x in v) for v in vectors)):
            raise WorkbenchError("MODEL_VECTOR_INVALID")
    return result


def recover():
    with connect() as con:
        runs=con.execute("UPDATE benchmark_runs SET status='interrupted',error='RESTART_REVIEW_REQUIRED' WHERE status='running'").rowcount
        discussions=con.execute("UPDATE discussions SET status='interrupted',error='RESTART_REVIEW_REQUIRED' WHERE status='running'").rowcount
    return dict(benchmark_runs_held=runs,discussions_held=discussions,automatically_replayed=False)


class BoundedText:
    def __init__(self):self.parts=[];self.size=0
    def write(self,value):
        raw=value.encode('utf-8');self.size+=len(raw)
        if self.size>MAX_INPUT:raise WorkbenchError("EXPORT_LIMIT")
        self.parts.append(raw)
    def bytes(self):return b''.join(self.parts)


def write_once(path,raw):
    if path.exists():
        if read_bytes(path)!=raw:raise WorkbenchError("EXISTING_OUTPUT_CONFLICT")
    else:write_new(path,raw)
