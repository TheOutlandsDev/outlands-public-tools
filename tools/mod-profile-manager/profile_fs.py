"""Original MIT bounded plain-file storage primitives for managed profile trees."""
from __future__ import annotations
from contextlib import contextmanager
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid
from inspection_support import (TextError, canonical_directory, identity, linked,
                                local_path, no_links, strict_json)

MAX_FILES = 1024
MAX_DIRECTORIES = 2048
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_PATH = 512
MAX_JSON = 1024 * 1024
COMPONENT = re.compile(r'[A-Za-z0-9_. +@()\-]{1,120}')
RESERVED = re.compile(r'(?i)(?:CON|CONIN\$|CONOUT\$|PRN|AUX|NUL|COM[0-9¹²³]|LPT[0-9¹²³])(?:\..*)?')


class ProfileError(Exception):
    """Controlled fixed code; never contain an input path or payload."""


def require(condition, code):
    if not condition: raise ProfileError(code)


def safe_path(value):
    require(isinstance(value,(str,Path)),'LOCAL_ABSOLUTE_PATH_REQUIRED')
    try: path = local_path(value)
    except TextError as error: raise ProfileError(str(error)) from None
    if os.name == 'nt':
        require(all(part == part.rstrip(' .') and not RESERVED.fullmatch(part)
                    for part in path.parts[1:]), 'WINDOWS_PATH_UNSUPPORTED')
    return path


def checked_directory(value):
    path = safe_path(value)
    try: return canonical_directory(path)
    except TextError as error: raise ProfileError(str(error)) from None


def guard_links(path):
    try: no_links(path)
    except TextError as error: raise ProfileError(str(error)) from None


def relative_name(value):
    require(type(value) is str and 0 < len(value) <= MAX_PATH, 'RELATIVE_PATH_UNSUPPORTED')
    parts = value.split('/')
    require(all(part not in ('', '.', '..') and COMPONENT.fullmatch(part)
                and part == part.strip(' ') and part == part.rstrip('.')
                and not RESERVED.fullmatch(part) for part in parts), 'RELATIVE_PATH_UNSUPPORTED')
    return value


def _stream_check(path):
    """Reject Windows named data streams; never copy or expose stream contents."""
    if os.name != 'nt': return
    from ctypes import wintypes
    class StreamData(ctypes.Structure):
        _fields_ = [('size', ctypes.c_longlong), ('name', wintypes.WCHAR * 296)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    first = kernel.FindFirstStreamW
    first.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(StreamData), wintypes.DWORD]
    first.restype = wintypes.HANDLE
    nxt = kernel.FindNextStreamW
    nxt.argtypes = [wintypes.HANDLE, ctypes.POINTER(StreamData)]; nxt.restype = wintypes.BOOL
    close = kernel.FindClose; close.argtypes = [wintypes.HANDLE]; close.restype = wintypes.BOOL
    data = StreamData(); handle = first(str(path), 0, ctypes.byref(data), 0)
    if handle == ctypes.c_void_p(-1).value:
        require(ctypes.get_last_error() == 38, 'STREAM_CHECK_UNAVAILABLE'); return
    try:
        while True:
            require(data.name in ('', '::$DATA'), 'NAMED_STREAM_UNSUPPORTED')
            if not nxt(handle, ctypes.byref(data)):
                require(ctypes.get_last_error() == 38, 'STREAM_CHECK_UNAVAILABLE'); break
    finally: close(handle)


def regular_info(path):
    guard_links(path); info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and not linked(info), 'REGULAR_FILE_REQUIRED')
    require(info.st_nlink == 1, 'HARDLINK_UNSUPPORTED')
    _stream_check(path)
    return info


def read_regular(value, maximum=MAX_FILE_BYTES):
    require(type(maximum) is int and 0<maximum<=max(MAX_FILE_BYTES,MAX_JSON),'READ_LIMIT_INVALID')
    path = safe_path(value); before = regular_info(path)
    require(before.st_size <= maximum, 'FILE_BYTE_LIMIT')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
                 | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0))
    try:
        opened = os.fstat(fd)
        require(stat.S_ISREG(opened.st_mode) and opened.st_nlink == 1
                and identity(before) == identity(opened), 'INPUT_CHANGED')
        data = bytearray()
        while True:
            block = os.read(fd, min(65536, maximum + 1-len(data)))
            if not block: break
            data.extend(block); require(len(data) <= maximum, 'FILE_BYTE_LIMIT')
        after = os.fstat(fd); path_info = regular_info(path)
        require(after.st_nlink == path_info.st_nlink == 1
                and len(data) == opened.st_size and identity(opened) == identity(after) == identity(path_info)
                and opened.st_ctime_ns == after.st_ctime_ns, 'INPUT_CHANGED')
        return bytes(data)
    finally: os.close(fd)


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)+'\n').encode('utf-8')


def read_json(path):
    try: return strict_json(read_regular(path, MAX_JSON), MAX_JSON, 40000, 8192)
    except TextError as error: raise ProfileError(str(error)) from None


def fresh_directory(path):
    path = safe_path(path); checked_directory(path.parent)
    require(not path.exists() and not path.is_symlink(), 'DESTINATION_EXISTS')
    path.mkdir(mode=0o700, exist_ok=False); guard_links(path)
    return path


def write_new(path, data, maximum=MAX_FILE_BYTES):
    path = safe_path(path); checked_directory(path.parent)
    require(type(maximum) is int and 0<maximum<=max(MAX_FILE_BYTES,MAX_JSON),'WRITE_LIMIT_INVALID')
    require(type(data) is bytes and len(data) <= maximum, 'FILE_BYTE_LIMIT')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
                 | getattr(os, 'O_BINARY', 0), 0o600)
    try:
        opened = os.fstat(fd)
        require(stat.S_ISREG(opened.st_mode) and opened.st_nlink == 1, 'REGULAR_FILE_REQUIRED')
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(data); stream.flush(); os.fsync(fd)
    finally: os.close(fd)
    require(read_regular(path, max(1, len(data))) == data, 'WRITE_VERIFICATION_FAILED')


def save_json(path, value):
    """Replace only a checked manager metadata file; retain failed fresh temps."""
    path = safe_path(path); checked_directory(path.parent)
    previous = None
    if path.exists(): previous = regular_info(path)
    else: require(not path.is_symlink(), 'LINKED_PATH_REJECTED')
    data = json_bytes(value); require(len(data) <= MAX_JSON, 'METADATA_BYTE_LIMIT')
    temp = path.parent/('.tmp-'+uuid.uuid4().hex)
    write_new(temp, data, MAX_JSON)
    guard_links(path.parent)
    if previous is not None:
        current = regular_info(path)
        require(identity(previous) == identity(current) and previous.st_ctime_ns == current.st_ctime_ns,
                'METADATA_CHANGED')
        os.replace(temp, path)
    else: rename_no_replace(temp, path)
    require(read_regular(path, MAX_JSON) == data, 'WRITE_VERIFICATION_FAILED')


def rename_no_replace(source, destination):
    source = safe_path(source); destination = safe_path(destination)
    guard_links(source); checked_directory(source.parent); checked_directory(destination.parent)
    require(not destination.exists() and not destination.is_symlink(), 'DESTINATION_EXISTS')
    if os.name == 'nt':
        os.rename(source, destination)  # Windows rejects any existing destination.
    elif sys.platform.startswith('linux'):
        library = ctypes.CDLL(None, use_errno=True); function = getattr(library, 'renameat2', None)
        require(function is not None, 'NOREPLACE_UNAVAILABLE')
        function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        if function(-100, os.fsencode(source), -100, os.fsencode(destination), 1):
            error = ctypes.get_errno()
            if error == errno.EEXIST: raise ProfileError('DESTINATION_EXISTS')
            if error in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP}:
                raise ProfileError('NOREPLACE_UNAVAILABLE')
            raise OSError(error, 'Rename failed')
    else: raise ProfileError('PLATFORM_UNSUPPORTED')
    guard_links(destination)


@contextmanager
def lock_workspace(value):
    root = checked_directory(value); path = root/'.lock'; before = regular_info(path)
    require(before.st_size == 1, 'LOCK_FILE_INVALID')
    fd = os.open(path, os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0))
    locked = False
    try:
        opened = os.fstat(fd)
        require(identity(opened) == identity(before) and opened.st_nlink == 1, 'LOCK_FILE_INVALID')
        try:
            if os.name == 'nt':
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET); msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            elif sys.platform.startswith('linux'):
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            else: raise ProfileError('PLATFORM_UNSUPPORTED')
            locked = True
        except OSError as error:
            if error.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}: raise ProfileError('WORKSPACE_BUSY') from None
            raise
        yield root
    finally:
        if locked:
            if os.name == 'nt':
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET); msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def scan_tree(value):
    root = checked_directory(value); base = root.lstat(); directories=[]; files=[]; total=0; seen=set()
    pending=[(root, '')]
    while pending:
        folder, relative = pending.pop(); before=folder.lstat(); guard_links(folder)
        require(stat.S_ISDIR(before.st_mode) and before.st_dev == base.st_dev, 'TREE_DIRECTORY_UNSUPPORTED')
        _stream_check(folder)
        entries=[]
        with os.scandir(folder) as iterator:
            for entry in iterator:
                require(len(entries)<MAX_FILES+MAX_DIRECTORIES,'TREE_ENTRY_LIMIT')
                entries.append(entry)
        entries.sort(key=lambda item:item.name)
        for entry in entries:
            name = relative_name((relative+'/' if relative else '')+entry.name)
            key=name.casefold(); require(key not in seen, 'CASE_COLLISION'); seen.add(key)
            path=folder/entry.name; info=path.lstat()
            require(not linked(info) and info.st_dev == base.st_dev, 'TREE_ENTRY_UNSUPPORTED')
            if stat.S_ISDIR(info.st_mode):
                directories.append(name); require(len(directories) <= MAX_DIRECTORIES, 'DIRECTORY_COUNT_LIMIT')
                pending.append((path,name))
            elif stat.S_ISREG(info.st_mode):
                require(len(files) < MAX_FILES, 'FILE_COUNT_LIMIT')
                require(info.st_size<=MAX_FILE_BYTES,'FILE_BYTE_LIMIT')
                require(total+info.st_size<=MAX_TOTAL_BYTES,'TREE_BYTE_LIMIT')
                data=read_regular(path,MAX_FILE_BYTES);total+=len(data);require(total <= MAX_TOTAL_BYTES, 'TREE_BYTE_LIMIT')
                files.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
            else: raise ProfileError('TREE_ENTRY_UNSUPPORTED')
        after=folder.lstat()
        require(identity(before) == identity(after) and before.st_ctime_ns == after.st_ctime_ns,'INPUT_CHANGED')
    body={'schema_version':1,'directories':sorted(directories),'files':sorted(files,key=lambda row:row['path']),'total_bytes':total}
    return dict(body,digest=hashlib.sha256(json_bytes(body)).hexdigest())


def validate_manifest(value):
    require(type(value) is dict and set(value)=={'schema_version','directories','files','total_bytes','digest'},'MANIFEST_INVALID')
    require(type(value['schema_version']) is int and value['schema_version']==1,'MANIFEST_INVALID')
    directories=value['directories'];files=value['files']
    require(type(directories) is list and len(directories)<=MAX_DIRECTORIES
            and all(type(name) is str for name in directories),'MANIFEST_INVALID')
    require(directories==sorted(directories),'MANIFEST_INVALID')
    require(type(files) is list and 1<=len(files)<=MAX_FILES,'MANIFEST_INVALID')
    paths=[];total=0
    for name in directories: relative_name(name);paths.append(name)
    for row in files:
        require(type(row) is dict and set(row)=={'path','bytes','sha256'},'MANIFEST_INVALID')
        relative_name(row['path']);paths.append(row['path'])
        require(type(row['bytes']) is int and 0<=row['bytes']<=MAX_FILE_BYTES,'MANIFEST_INVALID')
        require(type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}',row['sha256']),'MANIFEST_INVALID')
        total+=row['bytes']
    require(files==sorted(files,key=lambda row:row['path']) and len({p.casefold() for p in paths})==len(paths),'MANIFEST_INVALID')
    directory_set=set(directories)
    for name in paths:
        parents=name.split('/')[:-1]
        require(all('/'.join(parents[:index]) in directory_set for index in range(1,len(parents)+1)),'MANIFEST_INVALID')
    require(type(value['total_bytes']) is int and value['total_bytes']==total<=MAX_TOTAL_BYTES,'MANIFEST_INVALID')
    body={key:value[key] for key in ['schema_version','directories','files','total_bytes']}
    require(type(value['digest']) is str and value['digest']==hashlib.sha256(json_bytes(body)).hexdigest(),'MANIFEST_INVALID')
    return value


def verify_tree(path, manifest):
    require(scan_tree(path)==validate_manifest(manifest), 'TREE_MISMATCH')


def copy_tree(source, destination, manifest):
    verify_tree(source,manifest);fresh_directory(destination)
    for name in sorted(manifest['directories'], key=lambda value:(value.count('/'),value)):
        fresh_directory(destination/name)
    for row in manifest['files']:
        data=read_regular(source/row['path'],MAX_FILE_BYTES)
        require(len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],'INPUT_CHANGED')
        write_new(destination/row['path'],data,MAX_FILE_BYTES)
    verify_tree(source,manifest);verify_tree(destination,manifest)
