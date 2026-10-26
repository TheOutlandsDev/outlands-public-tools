#!/usr/bin/env python3
"""Create a neutral private workspace. Default operation is a read-only plan."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

MAX_SOURCE = 16*1024*1024
FOLDERS = ('original','working','evidence/screenshots','evidence/test-output',
           'deliverables','logs','rollback')
RESERVED = {'con','prn','aux','nul',*(f'com{i}' for i in range(1,10)),*(f'lpt{i}' for i in range(1,10))}

class WorkspaceError(ValueError):pass

_WINDOWS_BACKEND = None
CONTROL_TEXT = '# Private project control record\n\nStatus: INTAKE\n\n- Preserve original input bytes. Work on a separate copy.\n- Record scope, acceptance criteria, dependencies, and unresolved decisions.\n- Record actual commands and results; distinguish static checks from runtime proof.\n- Keep credentials, personal data, operational records, and private evidence local.\n- Prepare a separately reviewed export for sharing.\n- Record rollback instructions and acceptance before closure.\n\n## Decisions\n\nPending.\n\n## Validation\n\nNot run.\n\n## Handoff\n\nPending.\n'


def _windows():
    global _WINDOWS_BACKEND
    if _WINDOWS_BACKEND is None:
        spec = importlib.util.spec_from_file_location(
            'outlands_workspace_windows', Path(__file__).with_name('workspace_windows.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _WINDOWS_BACKEND = module
    return _WINDOWS_BACKEND


def path_without_links(value):
    if os.name == 'nt':
        return _windows().checked_path(value, WorkspaceError)
    path=Path(os.path.abspath(value))
    for component in [*reversed(path.parents),path]:
        if component.exists() or component.is_symlink():
            info=component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:raise WorkspaceError('LINK_FORBIDDEN')
    return path

def source_bytes(source):
    if os.name == 'nt':
        path=path_without_links(source)
        info=path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size>MAX_SOURCE:raise WorkspaceError('SOURCE_NOT_BOUNDED_FILE')
        return _windows().read_bounded(path, MAX_SOURCE, WorkspaceError, expected=info)
    path=path_without_links(source)
    before=path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size>MAX_SOURCE:raise WorkspaceError('SOURCE_NOT_BOUNDED_FILE')
    with path.open('rb') as handle:
        data=handle.read(MAX_SOURCE+1);after=os.fstat(handle.fileno())
    if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) or len(data)!=before.st_size:raise WorkspaceError('SOURCE_CHANGED')
    return data

def create(root,name,source=None,commit=False):
    if os.name == 'nt':
        return _create_windows(root,name,source,commit)
    return _create_posix(root,name,source,commit)


def _create_posix(root,name,source=None,commit=False):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}',name) or name in RESERVED:raise WorkspaceError('INVALID_NAME')
    root=path_without_links(root)
    if not root.is_dir():raise WorkspaceError('ROOT_NOT_DIRECTORY')
    destination=root/name
    if destination.exists() or destination.is_symlink():raise WorkspaceError('DESTINATION_EXISTS')
    data=source_bytes(source) if source else None
    if not commit:return dict(status='PLAN_ONLY',folders=list(FOLDERS),source_selected=data is not None)
    destination.mkdir()
    # Partial work is retained on error; existing data is never removed or replaced.
    for folder in FOLDERS:(destination/folder).mkdir(parents=True,exist_ok=False)
    (destination/'.gitignore').write_text('*\n',encoding='utf-8')
    if data is not None:
        for folder in ('original','working'):
            with (destination/folder/'intake.bin').open('xb') as handle:handle.write(data)
        metadata=dict(sha256=hashlib.sha256(data).hexdigest(),size=len(data))
        if any(hashlib.sha256((destination/folder/'intake.bin').read_bytes()).hexdigest()!=metadata['sha256'] for folder in ('original','working')):raise WorkspaceError('COPY_VERIFY_FAILED')
        (destination/'original'/'SOURCE.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    (destination/'CONTROL.md').write_text('''# Private project control record

Status: INTAKE

- Preserve original input bytes. Work on a separate copy.
- Record scope, acceptance criteria, dependencies, and unresolved decisions.
- Record actual commands and results; distinguish static checks from runtime proof.
- Keep credentials, personal data, operational records, and private evidence local.
- Prepare a separately reviewed export for sharing.
- Record rollback instructions and acceptance before closure.

## Decisions

Pending.

## Validation

Not run.

## Handoff

Pending.
''',encoding='utf-8')
    return dict(status='WORKSPACE_CREATED',source_verified=data is not None)

def _create_windows(root,name,source=None,commit=False):
    from contextlib import ExitStack

    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}',name) or name in RESERVED:raise WorkspaceError('INVALID_NAME')
    backend=_windows()
    with backend.root_scope(root, WorkspaceError) as selected:
        destination=backend.selected_path(selected/name, backend._core(WorkspaceError))
        if os.path.lexists(destination):raise WorkspaceError('DESTINATION_EXISTS')
        data=source_bytes(source) if source else None
        if not commit:return dict(status='PLAN_ONLY',folders=list(FOLDERS),source_selected=data is not None)
        text_bytes=lambda value:value.replace('\n',os.linesep).encode('utf-8')
        with ExitStack() as owned:
            owned.enter_context(backend.fresh_directory(destination, WorkspaceError))
            # New output is private material; failures retain it without cleanup.
            files={destination/'.gitignore':text_bytes('*\n')}
            backend.exclusive_write(destination/'.gitignore',files[destination/'.gitignore'],WorkspaceError)
            created={destination}
            for folder in FOLDERS:
                parent=destination
                for part in folder.split('/'):
                    parent/=part
                    if parent not in created:
                        owned.enter_context(backend.fresh_directory(parent, WorkspaceError))
                        created.add(parent)
            if data is not None:
                metadata=dict(sha256=hashlib.sha256(data).hexdigest(),size=len(data))
                for folder in ('original','working'):
                    files[destination/folder/'intake.bin']=data
                files[destination/'original'/'SOURCE.json']=text_bytes(json.dumps(metadata,indent=2)+'\n')
            files[destination/'CONTROL.md']=text_bytes(CONTROL_TEXT)
            for output,payload in files.items():
                if output.name!='.gitignore':backend.exclusive_write(output,payload,WorkspaceError)
            for output,payload in files.items():
                observed=backend.read_bounded(output,max(MAX_SOURCE,len(payload)),WorkspaceError,single_link=True)
                if observed!=payload:raise WorkspaceError('COPY_VERIFY_FAILED')
    return dict(status='WORKSPACE_CREATED',source_verified=data is not None)


class Parser(argparse.ArgumentParser):
    def error(self,message):raise WorkspaceError('INVALID_ARGUMENTS')

def main(argv=None):
    parser=Parser(description=__doc__,prog='workspace.py' if os.name=='nt' else None)
    parser.add_argument('--root',required=True,help='Existing private parent directory')
    parser.add_argument('--name',required=True,help='Neutral lowercase identifier')
    parser.add_argument('--source',help='Optional bounded file to retain as opaque input bytes')
    parser.add_argument('--create',action='store_true',help='Perform creation; otherwise plan only')
    try:
        args=parser.parse_args(argv)
        print(json.dumps(create(args.root,args.name,args.source,args.create),sort_keys=True));return 0
    except KeyboardInterrupt:
        if os.name!='nt':raise
        print(json.dumps(dict(status='ERROR',code='WORKSPACE_INTERRUPTED')));return 130
    except (OSError,ValueError,UnicodeError):
        print(json.dumps(dict(status='ERROR',code='WORKSPACE_INPUT_OR_OUTPUT_ERROR')));return 2

if __name__=='__main__':sys.exit(main())
