#!/usr/bin/env python3
"""Check a bounded set of local Markdown links and JSON syntax, offline."""
import argparse
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import unquote, urlsplit

MAX_FILES=10000
MAX_BYTES=2*1024*1024

class DocsError(ValueError):pass

_WINDOWS_BACKEND=None


def _windows():
    global _WINDOWS_BACKEND
    if _WINDOWS_BACKEND is None:
        spec=importlib.util.spec_from_file_location('outlands_docs_windows',Path(__file__).with_name('docs_windows.py'))
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _WINDOWS_BACKEND=module
    return _WINDOWS_BACKEND


def safe_path(path):
    if os.name=='nt':
        _windows().checked_path(path,DocsError)
        return
    for p in [*reversed(path.parents),path]:
        if p.exists() or p.is_symlink():
            info=p.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:raise DocsError('LINKED_PATH')

def check(root):
    if os.name=='nt':
        with _windows().root_scope(root,DocsError) as selected:
            return _check_impl(selected)
    return _check_impl(root)


def _check_impl(root):
    root=Path(os.path.abspath(root));safe_path(root)
    if not root.is_dir():raise DocsError('ROOT_NOT_DIRECTORY')
    results=[];count=0;stack=[root];file_count=0
    while stack:
        folder=stack.pop()
        with _directory_entries(folder,MAX_FILES-file_count) as entries:
            for entry in entries:
                file_count+=1
                if file_count>MAX_FILES:raise DocsError('ENTRY_LIMIT')
                path=Path(entry.path);relative=path.relative_to(root).as_posix()
                info=path.lstat()
                if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
                    results.append(dict(path=relative,rule='LINK_OR_REPARSE'));continue
                if entry.name=='.git' and folder==root:continue
                if entry.is_dir(follow_symlinks=False):
                    if entry.name.startswith('.') or entry.name in {'node_modules','runtime','private','__pycache__'}:continue
                    stack.append(path);continue
                if path.suffix.lower() not in {'.md','.json'}:continue
                if not stat.S_ISREG(info.st_mode) or info.st_size>MAX_BYTES:
                    results.append(dict(path=relative,rule='SIZE_OR_TYPE'));continue
                try:text=_read_text(path,info)
                except (OSError,UnicodeError,DocsError):results.append(dict(path=relative,rule='READ_ERROR'));continue
                count+=1
                if path.suffix.lower()=='.json':
                    try:json.loads(text,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
                    except (ValueError,RecursionError):results.append(dict(path=relative,rule='INVALID_JSON'))
                    continue
                fence=None
                for number,line in enumerate(text.splitlines(),1):
                    marker=re.match(r'^\s*(`{3,}|~{3,})',line)
                    if marker:
                        if fence is None:fence=marker.group(1)[0]
                        elif marker.group(1)[0]==fence:fence=None
                        continue
                    if fence:continue
                    line=re.sub(r'`[^`]*`','',line)
                    links=re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',line)
                    ref=re.match(r'^\s*\[[^\]]+\]:\s*(.+)$',line)
                    if ref:links.append(ref.group(1))
                    for target in links:
                        target=target.strip()
                        target=target[1:target.index('>')] if target.startswith('<') and '>' in target else target.split()[0] if target else ''
                        if not target or target.startswith('#'):continue
                        try:parts=urlsplit(target)
                        except ValueError:results.append(dict(path=relative,line=number,rule='INVALID_LINK'));continue
                        if parts.scheme in {'http','https','mailto'}:continue
                        if parts.scheme or parts.netloc:
                            results.append(dict(path=relative,line=number,rule='UNSUPPORTED_LINK_SCHEME'));continue
                        decoded=unquote(parts.path)
                        destination=Path(os.path.abspath(path.parent/decoded))
                        if not destination.is_relative_to(root):
                            results.append(dict(path=relative,line=number,rule='LINK_ESCAPES_ROOT'));continue
                        try:
                            _check_target(destination,root)
                        except (OSError,DocsError):results.append(dict(path=relative,line=number,rule='MISSING_OR_LINKED_TARGET'))
    return dict(status='FAIL' if results else 'PASS',checked_documents=count,findings=results,
                limits='Common Markdown links only; no anchor validation, external fetch, or source execution')

@contextmanager
def _directory_entries(folder,remaining):
    if os.name=='nt':
        with _windows().directory_entries(folder,remaining,DocsError) as entries:
            yield entries
        return
    safe_path(folder)
    before=folder.lstat()
    if not stat.S_ISDIR(before.st_mode):raise DocsError('DIRECTORY_REQUIRED')
    entries=[]
    with os.scandir(folder) as iterator:
        for entry in iterator:
            entries.append(entry)
            if len(entries)>remaining:raise DocsError('ENTRY_LIMIT')
    yield sorted(entries,key=lambda entry:entry.name)
    after=folder.lstat()
    identity=lambda info:(info.st_dev,info.st_ino,info.st_mode,info.st_mtime_ns,info.st_ctime_ns)
    if identity(before)!=identity(after):raise DocsError('DIRECTORY_CHANGED')
    safe_path(folder)


def _read_text(path,expected):
    if os.name=='nt':
        data=_windows().read_bounded(path,MAX_BYTES,DocsError,expected=expected)
    else:
        data=_read_posix(path,expected)
    # Match read_text's UTF-8 BOM handling and universal newline conversion.
    return data.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')


def _read_posix(path,expected):
    safe_path(path)
    flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0)
    fd=os.open(path,flags)
    try:
        os.set_inheritable(fd,False)
        before=os.fstat(fd)
        identity=lambda info:(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
        if (not stat.S_ISREG(before.st_mode) or before.st_size>MAX_BYTES
                or identity(before)!=identity(expected)):raise DocsError('INPUT_CHANGED')
        chunks=[];size=0
        while True:
            block=os.read(fd,min(65536,MAX_BYTES+1-size))
            if not block:break
            size+=len(block)
            if size>MAX_BYTES:raise DocsError('INPUT_SIZE_LIMIT')
            chunks.append(block)
        after=os.fstat(fd)
        if (size!=before.st_size or identity(before)!=identity(after)
                or identity(path.lstat())!=identity(after)):raise DocsError('INPUT_CHANGED')
        safe_path(path)
        return b''.join(chunks)
    finally:
        os.close(fd)


def _check_target(destination,root):
    if os.name=='nt':
        _windows().check_target(destination,root,DocsError)
        return
    safe_path(destination)
    if not destination.exists():raise DocsError('MISSING')


class Parser(argparse.ArgumentParser):
    def error(self,message):raise DocsError('INVALID_ARGUMENTS')

def main(argv=None):
    parser=Parser(description=__doc__,prog='docs_check.py' if os.name=='nt' else None);parser.add_argument('--root',required=True)
    try:
        args=parser.parse_args(argv);result=check(args.root)
        # Relative filenames and line numbers are private operational output.
        print(json.dumps(result,sort_keys=True));return int(result['status']!='PASS')
    except KeyboardInterrupt:
        if os.name!='nt':raise
        print(json.dumps(dict(status='ERROR',code='DOCUMENTATION_CHECK_INTERRUPTED')));return 130
    except (OSError,UnicodeError,ValueError,RecursionError):
        print(json.dumps(dict(status='ERROR',code='DOCUMENTATION_CHECK_FAILED')));return 2

if __name__=='__main__':sys.exit(main())
