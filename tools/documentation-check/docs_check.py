#!/usr/bin/env python3
"""Check a bounded set of local Markdown links and JSON syntax, offline."""
import argparse
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

def safe_path(path):
    for p in [*reversed(path.parents),path]:
        if p.exists() or p.is_symlink():
            info=p.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:raise DocsError('LINKED_PATH')

def check(root):
    root=Path(os.path.abspath(root));safe_path(root)
    if not root.is_dir():raise DocsError('ROOT_NOT_DIRECTORY')
    results=[];count=0;stack=[root];file_count=0
    while stack:
        folder=stack.pop()
        with os.scandir(folder) as iterator:entries=sorted(iterator,key=lambda x:x.name)
        for entry in entries:
            file_count+=1
            if file_count>MAX_FILES:raise DocsError('ENTRY_LIMIT')
            path=Path(entry.path);relative=path.relative_to(root).as_posix()
            info=entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
                results.append(dict(path=relative,rule='LINK_OR_REPARSE'));continue
            if entry.name=='.git' and folder==root:continue
            if entry.is_dir(follow_symlinks=False):
                if entry.name.startswith('.') or entry.name in {'node_modules','runtime','private','__pycache__'}:continue
                stack.append(path);continue
            if path.suffix.lower() not in {'.md','.json'}:continue
            if not stat.S_ISREG(info.st_mode) or info.st_size>MAX_BYTES:
                results.append(dict(path=relative,rule='SIZE_OR_TYPE'));continue
            try:text=path.read_text(encoding='utf-8-sig')
            except (OSError,UnicodeError):results.append(dict(path=relative,rule='READ_ERROR'));continue
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
                        safe_path(destination)
                        if not destination.exists():raise DocsError('MISSING')
                    except (OSError,DocsError):results.append(dict(path=relative,line=number,rule='MISSING_OR_LINKED_TARGET'))
    return dict(status='FAIL' if results else 'PASS',checked_documents=count,findings=results,
                limits='Common Markdown links only; no anchor validation, external fetch, or source execution')

class Parser(argparse.ArgumentParser):
    def error(self,message):raise DocsError('INVALID_ARGUMENTS')

def main(argv=None):
    parser=Parser(description=__doc__);parser.add_argument('--root',required=True)
    try:
        args=parser.parse_args(argv);result=check(args.root)
        # Relative filenames and line numbers are private operational output.
        print(json.dumps(result,sort_keys=True));return int(result['status']!='PASS')
    except (OSError,UnicodeError,ValueError,RecursionError):
        print(json.dumps(dict(status='ERROR',code='DOCUMENTATION_CHECK_FAILED')));return 2

if __name__=='__main__':sys.exit(main())
