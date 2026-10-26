"""Small JSON and structured redaction helpers. No arbitrary command runner."""
from __future__ import annotations
import importlib.util
import json
import os
import stat
from pathlib import Path

SENSITIVE_KEYS=frozenset({'password','api_key','authorization','secret','token',
                          'access_token','refresh_token','secret_key','private_key'})

class HelperError(ValueError):pass

_WINDOWS_BACKEND=None


def _windows():
    global _WINDOWS_BACKEND
    if _WINDOWS_BACKEND is None:
        spec=importlib.util.spec_from_file_location('outlands_helpers_windows',Path(__file__).with_name('helpers_windows.py'))
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _WINDOWS_BACKEND=module
    return _WINDOWS_BACKEND


def _read_bytes(value,maximum):
    if os.name=='nt':
        return _windows().read_bounded(value,maximum,HelperError)
    return _read_posix(value,maximum)


def _posix_path(value):
    raw=os.fspath(value)
    if not isinstance(raw,str) or not raw or '..' in Path(raw).parts:raise HelperError('INPUT_PATH_INVALID')
    return Path(os.path.abspath(raw))


def _safe_posix(path):
    for part in [*reversed(path.parents),path]:
        info=part.lstat()
        if stat.S_ISLNK(info.st_mode):raise HelperError('LINK_FORBIDDEN')
        if part!=path and not stat.S_ISDIR(info.st_mode):raise HelperError('PARENT_NOT_DIRECTORY')


def _read_posix(value,maximum):
    path=_posix_path(value)
    _safe_posix(path)
    expected=path.lstat()
    if not stat.S_ISREG(expected.st_mode):raise HelperError('INPUT_NOT_REGULAR')
    if expected.st_size>maximum:raise HelperError('INPUT_TOO_LARGE')
    flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0)
    fd=os.open(path,flags)
    try:
        os.set_inheritable(fd,False)
        before=os.fstat(fd)
        identity=lambda info:(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
        if not stat.S_ISREG(before.st_mode) or identity(before)!=identity(expected):raise HelperError('INPUT_CHANGED')
        chunks=[];size=0
        while True:
            block=os.read(fd,min(65536,maximum+1-size))
            if not block:break
            size+=len(block)
            if size>maximum:raise HelperError('INPUT_TOO_LARGE')
            chunks.append(block)
        after=os.fstat(fd)
        if (size!=before.st_size or identity(before)!=identity(after)
                or identity(path.lstat())!=identity(after)):raise HelperError('INPUT_CHANGED')
        _safe_posix(path)
        return b''.join(chunks)
    finally:
        os.close(fd)


def load_json_object(path, max_bytes=1024*1024):
    """Load one bounded UTF-8 JSON object. Error messages omit paths and values.

    The caller selects a trusted input. This is not a filesystem sandbox.
    """
    if type(max_bytes) is not int or not 0<max_bytes<=16*1024*1024:raise HelperError('INVALID_LIMIT')
    try:
        data=_read_bytes(path,max_bytes)
        if len(data)>max_bytes:raise HelperError('INPUT_TOO_LARGE')
        result=json.loads(data.decode('utf-8-sig'),parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
        if not isinstance(result,dict):raise HelperError('OBJECT_REQUIRED')
        return result
    except (OSError,UnicodeError,ValueError,RecursionError,TypeError):
        raise HelperError('JSON_OBJECT_LOAD_FAILED') from None

def redact_structure(value, *, max_depth=32):
    """Copy JSON-like data and redact values under selected sensitive keys.

    Case and dash/underscore variants are normalized. Text inside ordinary
    fields, unknown key names and identifying metadata are not anonymized.
    """
    if type(max_depth) is not int or not 1<=max_depth<=128:raise HelperError('INVALID_DEPTH')
    def visit(item,depth):
        if depth>max_depth:raise HelperError('DEPTH_LIMIT')
        if isinstance(item,dict):
            result={}
            for key,entry in item.items():
                if not isinstance(key,str):raise HelperError('STRING_KEYS_REQUIRED')
                result[key]='<redacted>' if key.casefold().replace('-','_') in SENSITIVE_KEYS else visit(entry,depth+1)
            return result
        if isinstance(item,list):return [visit(entry,depth+1) for entry in item]
        if item is None or type(item) in (str,int,float,bool):return item
        raise HelperError('JSON_TYPES_REQUIRED')
    return visit(value,0)
