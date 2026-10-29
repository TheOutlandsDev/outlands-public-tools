"""Selected unchanged first-party MIT guarded I/O helpers."""
from contextlib import contextmanager
import importlib.util
import os
from pathlib import Path
import stat
PACKAGE=Path(__file__).resolve().parents[2]
MAX_IMPORT=16*1024*1024
MAX_EXPORT=16*1024*1024
_WINDOWS_BACKEND=None
class ReviewError(ValueError):pass


def _export_path(value):
    path=selected_path(_io_path(value),private_output=True)
    if os.name=='nt':
        with _windows().export_scope(path,PACKAGE,ReviewError):pass
    return path

def _io_path(value):
    if os.name=='nt':return _windows().selected_path(value,_windows()._core(ReviewError))
    raw=os.fspath(value)
    if not isinstance(raw,str) or not raw or '..' in Path(raw).parts:raise ReviewError('IO_PATH_INVALID')
    return Path(os.path.abspath(raw))

def _quiet_sidecars(path):
    for suffix in ('-journal','-wal','-shm'):
        try:Path(str(path)+suffix).lstat()
        except FileNotFoundError:continue
        raise ReviewError('STORE_SIDECAR_PRESENT')

def _read_import(value):
    path=selected_path(_io_path(value))
    if not path.is_file() or path.stat().st_size>MAX_IMPORT:raise ReviewError('IMPORT_LIMIT')
    if os.name=='nt':return _windows().read_bounded(path,MAX_IMPORT,ReviewError)
    return _read_posix(path,MAX_IMPORT)

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

def _safe_posix(path):
    for part in [*reversed(path.parents),path]:
        info=part.lstat()
        if stat.S_ISLNK(info.st_mode):raise ReviewError('LINK_FORBIDDEN')
        if part!=path and not stat.S_ISDIR(info.st_mode):raise ReviewError('PARENT_NOT_DIRECTORY')

@contextmanager
def _store_parent(path):
    if os.name=='nt':
        with _windows().export_scope(path,PACKAGE,ReviewError):yield
    else:
        _safe_posix(path.parent)
        yield
        _safe_posix(path.parent)

@contextmanager
def _store_scope(value,*,initial=False,created=None):
    from contextlib import ExitStack
    path=_export_path(value)
    _quiet_sidecars(path)
    with ExitStack() as owned:
        owned.enter_context(_store_parent(path))
        if os.name=='nt':fd=owned.enter_context(_windows().store_file(path,ReviewError))
        else:
            _safe_posix(path)
            info=path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:raise ReviewError('STORE_UNAVAILABLE')
            fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
            owned.callback(os.close,fd)
            os.set_inheritable(fd,False)
            opened=os.fstat(fd)
            if (info.st_dev,info.st_ino)!=(opened.st_dev,opened.st_ino):raise ReviewError('STORE_CHANGED')
        before=os.fstat(fd)
        identity=lambda info:(info.st_dev,info.st_ino,info.st_nlink)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>64*1024*1024
                or created is not None and created!=(before.st_dev,before.st_ino)):raise ReviewError('STORE_UNAVAILABLE')
        if initial:
            if before.st_size!=0:raise ReviewError('STORE_CHANGED')
        else:
            header=b''
            while len(header)<100:
                block=os.read(fd,100-len(header))
                if not block:break
                header+=block
            after=os.fstat(fd)
            if (len(header)!=100 or not header.startswith(b'SQLite format 3\x00')
                    or identity(after)!=identity(before) or after.st_size!=before.st_size
                    or after.st_mtime_ns!=before.st_mtime_ns):raise ReviewError('STORE_HEADER_INVALID')
            if header[18:20]!=b'\x01\x01':raise ReviewError('STORE_JOURNAL_MODE_UNSUPPORTED')
        _quiet_sidecars(path)
        yield path
        _quiet_sidecars(path)
        final=path.lstat()
        if not stat.S_ISREG(final.st_mode) or identity(final)!=identity(before) or identity(os.fstat(fd))!=identity(before):
            raise ReviewError('STORE_CHANGED')
        if os.name!='nt':_safe_posix(path)

def _windows():
    global _WINDOWS_BACKEND
    if _WINDOWS_BACKEND is None:
        spec=importlib.util.spec_from_file_location('outlands_review_io_windows',Path(__file__).with_name('review_io_windows.py'))
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _WINDOWS_BACKEND=module
    return _WINDOWS_BACKEND

def _write_export(path,data):
    if type(data) is not bytes or len(data)>MAX_EXPORT:raise ReviewError('EXPORT_LIMIT')
    if os.name=='nt':
        backend=_windows()
        with backend.export_scope(path,PACKAGE,ReviewError) as output:
            backend.exclusive_write(output,data,ReviewError)
            if backend.read_bounded(output,len(data),ReviewError,single_link=True)!=data:raise ReviewError('EXPORT_VERIFY_FAILED')
    else:_write_posix(path,data)

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

def selected_path(value, *, private_output=False):
    path=Path(os.path.abspath(value))
    for part in [*reversed(path.parents),path]:
        if part.exists() or part.is_symlink():
            info=part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:raise ReviewError('LINK_FORBIDDEN')
    if private_output and path.is_relative_to(PACKAGE):raise ReviewError('PRIVATE_STATE_INSIDE_REPOSITORY')
    if not path.parent.is_dir():raise ReviewError('PARENT_REQUIRED')
    return path
