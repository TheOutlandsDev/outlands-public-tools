#!/usr/bin/env python3
"""Offline text-export review. Findings omit matched content snippets."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import importlib.util
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from urllib.parse import urlsplit

MAX_FILE = 2 * 1024 * 1024
MAX_FILES = 20000
MAX_TOTAL = 64 * 1024 * 1024
MAX_JSON = 16 * 1024 * 1024
MAX_REPORT = 64 * 1024 * 1024
TEXT_SUFFIXES = {'.py','.ps1','.sh','.js','.mjs','.cjs','.ts','.cs','.php','.sql','.m',
                 '.md','.txt','.rst','.json','.toml','.yaml','.yml','.xml','.html','.css','.csv','.ini','.cfg'}
TEXT_NAMES = {'.gitignore','.gitattributes','license','copying','notice','dockerfile','makefile'}
BLOCK_DIRS = {'private','runtime','outputs','reports','logs','backups','credentials','secrets',
              'node_modules','__pycache__','.git','.codex','.aws','.agents'}
RULES = {
 'PRIVATE_KEY': re.compile(r'-----BEGIN (?:OPENSSH |RSA |EC |DSA |ENCRYPTED )?PRIVATE KEY-----'),
 'CREDENTIAL_SHAPE': re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|sk-(?:proj-)?[A-Za-z0-9_-]{32,})'),
 'CREDENTIAL_ASSIGNMENT': re.compile(r'''(?i)\b(?:password|api_key|access_token|secret_key)\s*[=:]\s*["'][^"'\s]{8,}["']'''),
 'EMAIL': re.compile(r'\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b'),
 'USER_HOME': re.compile(r'[A-Z]:[\\/](?:Users)[\\/]|/(?:home|Users)/[A-Za-z0-9._-]+/',re.I),
 'UNC_PATH': re.compile(r'\\\\[A-Za-z][A-Za-z0-9_.-]+\\[A-Za-z]'),
 'PRIVATE_IPV6': re.compile(r'\b(?:fd[0-9a-f]{2}|fc[0-9a-f]{2}|fe80):[0-9a-f:]+',re.I),
 'INTERNAL_HOSTNAME': re.compile(r'\b[A-Za-z0-9][A-Za-z0-9.-]*\.(?:local|internal|lan|home|ts\.net)\b',re.I),
 'ROOTED_WINDOWS_PATH': re.compile(r'\b[A-Z]:[\\/][A-Za-z]',re.I),
}
IPV4 = re.compile(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])')
IPV6 = re.compile(r'(?<![\w:])[0-9A-Fa-f:]*:[0-9A-Fa-f:]+(?![\w:])')
URL = re.compile(r'https?://[^\s<>\x22\x27)]+',re.I)
SAFE_EMAIL_DOMAINS={'example.com','example.org','example.net','example.invalid'}
BLOCK_NAME = re.compile(r'^\.env(?:$|\.)|^id_(?:rsa|ed25519)$|\.(?:pem|pfx|p12|key|kdbx|sqlite3?|db)$|ed25519$',re.I)

class AuditError(ValueError):
    pass


_WINDOWS_BACKEND = None


def _windows():
    global _WINDOWS_BACKEND
    if _WINDOWS_BACKEND is None:
        spec = importlib.util.spec_from_file_location(
            'outlands_audit_windows', Path(__file__).with_name('audit_windows.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _WINDOWS_BACKEND = module
    return _WINDOWS_BACKEND

def linked(path):
    info=path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info,'st_file_attributes',0)&0x400)

def explicit_path(path):
    if os.name == 'nt':
        return _windows().checked_path(path, AuditError)
    p=Path(os.path.abspath(path))
    for ancestor in [*reversed(p.parents),p]:
        if ancestor.exists() and linked(ancestor):raise AuditError('LINKED_PATH')
    return p

def inspect_text(text,denied=()):
    found=[]
    for number,line in enumerate(text.splitlines(),1):
        for rule,pattern in RULES.items():
            for match in pattern.finditer(line):
                if rule=='EMAIL' and match.group(1).lower() in SAFE_EMAIL_DOMAINS:continue
                found.append((rule,number))
                break
        for match in IPV4.finditer(line):
            try:ip=ipaddress.ip_address(match.group())
            except ValueError:continue
            # Loopback and documentation blocks are usable in fictional examples.
            if ip.is_loopback or any(ip in ipaddress.ip_network(n) for n in ('192.0.2.0/24','198.51.100.0/24','203.0.113.0/24')):continue
            found.append(('NETWORK_ADDRESS',number))
            break
        if any(value.casefold() in line.casefold() for value in denied):
            found.append(('PRIVATE_LITERAL',number))
        for match in IPV6.finditer(line):
            try:ip=ipaddress.ip_address(match.group())
            except ValueError:continue
            if ip.version==6 and not ip.is_loopback and ip not in ipaddress.ip_network('2001:db8::/32'):
                found.append(('NETWORK_ADDRESS_IPV6',number));break
        for match in URL.finditer(line):
            try:parts=urlsplit(match.group())
            except ValueError:found.append(('INVALID_URL_REVIEW',number));continue
            if parts.username is not None or parts.password is not None:found.append(('URL_CREDENTIALS',number))
            if parts.hostname and '.' not in parts.hostname and ':' not in parts.hostname and parts.hostname!='localhost':found.append(('SINGLE_LABEL_HOST',number))
    return found

def inspect(root, denied=()):
    if os.name == 'nt':
        with _windows().root_scope(root, AuditError) as selected:
            return _inspect_windows(selected, denied)
    return _inspect_posix(root, denied)


def _inspect_posix(root, denied=()):
    root=explicit_path(root)
    if not root.is_dir():raise AuditError('ROOT_NOT_DIRECTORY')
    findings=[];inventory=[];errors=[];excluded=[];total=0;entries_seen=0
    stack=[root]
    while stack:
        directory=stack.pop()
        try:
            with os.scandir(directory) as iterator:entries=sorted(iterator,key=lambda x:x.name.casefold())
        except OSError:
            errors.append('UNREADABLE_DIRECTORY');continue
        for entry in entries:
            entries_seen+=1
            if entries_seen>MAX_FILES:
                errors.append('ENTRY_LIMIT');stack=[];break
            path=Path(entry.path);relative=path.relative_to(root).as_posix()
            def flag(rule,line=None):findings.append(dict(path=relative,rule=rule,line=line))
            try:
                # DirEntry.stat omits file identity fields on Windows. lstat
                # obtains a complete identity for comparison with the open file.
                info=path.lstat()
                if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
                    flag('LINK_OR_REPARSE');continue
                if relative=='.git':
                    excluded.append('.git');continue
                for rule,_ in inspect_text(relative,denied):flag('PATH_'+rule)
                if entry.is_dir(follow_symlinks=False):
                    if entry.name.casefold() in BLOCK_DIRS or entry.name.lower().startswith('.venv'):
                        flag('PRIVATE_OR_RUNTIME_DIRECTORY')
                    else:stack.append(path)
                    continue
                if not stat.S_ISREG(info.st_mode):flag('NOT_REGULAR');continue
                if BLOCK_NAME.search(entry.name):flag('SENSITIVE_FILENAME');continue
                if path.suffix.lower() not in TEXT_SUFFIXES and entry.name.casefold() not in TEXT_NAMES:
                    flag('BINARY_OR_UNKNOWN_FORMAT_REVIEW');continue
                if info.st_size>MAX_FILE or total+info.st_size>MAX_TOTAL:
                    flag('SIZE_LIMIT');continue
                with path.open('rb') as handle:
                    opened=os.fstat(handle.fileno());data=handle.read(MAX_FILE+1);after=os.fstat(handle.fileno())
                identity=lambda x:(x.st_dev,x.st_ino,x.st_size,x.st_mtime_ns)
                if identity(info)!=identity(opened) or identity(opened)!=identity(after) or len(data)!=info.st_size:
                    flag('INPUT_CHANGED');continue
                total+=len(data)
                try:text=data.decode('utf-8-sig')
                except UnicodeError:flag('NON_UTF8_REVIEW');continue
                if '\x00' in text:flag('BINARY_CONTENT_REVIEW');continue
                inventory.append(dict(path=relative,size=len(data),sha256=hashlib.sha256(data).hexdigest()))
                for rule,line in inspect_text(text,denied):flag(rule,line)
            except OSError:errors.append('ENTRY_READ_FAILED')
    inventory.sort(key=lambda row:row['path'])
    findings.sort(key=lambda row:(row['path'],row['line'] or 0,row['rule']))
    return dict(schema_version=1,status='REVIEW_REQUIRED' if findings or errors else 'NO_PATTERN_FINDINGS',
                inventory=inventory,findings=findings,errors=errors,excluded=excluded,
                scope=dict(max_entries=MAX_FILES,max_file_bytes=MAX_FILE,max_total_bytes=MAX_TOTAL,
                           bytes_read=total,git_history_scanned=False,semantic_ip_review=False))


def _inspect_windows(root, denied=()):
    findings=[];inventory=[];errors=[];excluded=[];entries_seen=0
    budget=[MAX_TOTAL]
    stack=[root]
    while stack:
        directory=stack.pop()
        try:
            with _windows().directory_entries(directory, MAX_FILES-entries_seen, AuditError) as entries:
                for entry in entries:
                    entries_seen+=1
                    path=Path(entry.path);relative=path.relative_to(root).as_posix()
                    def flag(rule,line=None):findings.append(dict(path=relative,rule=rule,line=line))
                    try:
                        info=path.lstat()
                        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
                            flag('LINK_OR_REPARSE');continue
                        if relative=='.git':
                            excluded.append('.git');continue
                        for rule,_ in inspect_text(relative,denied):flag('PATH_'+rule)
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name.casefold() in BLOCK_DIRS or entry.name.lower().startswith('.venv'):
                                flag('PRIVATE_OR_RUNTIME_DIRECTORY')
                            else:stack.append(path)
                            continue
                        if not stat.S_ISREG(info.st_mode):flag('NOT_REGULAR');continue
                        if BLOCK_NAME.search(entry.name):flag('SENSITIVE_FILENAME');continue
                        if path.suffix.lower() not in TEXT_SUFFIXES and entry.name.casefold() not in TEXT_NAMES:
                            flag('BINARY_OR_UNKNOWN_FORMAT_REVIEW');continue
                        if info.st_size>MAX_FILE or info.st_size>max(0,budget[0]):
                            flag('SIZE_LIMIT');continue
                        try:
                            data=_windows().read_bounded(path, MAX_FILE, AuditError, expected=info, budget=budget)
                        except AuditError as error:
                            if str(error)=='TOTAL_BYTE_LIMIT':
                                flag('SIZE_LIMIT');errors.append('BYTE_LIMIT');stack.clear();break
                            flag('INPUT_CHANGED');continue
                        try:text=data.decode('utf-8-sig')
                        except UnicodeError:flag('NON_UTF8_REVIEW');continue
                        if '\x00' in text:flag('BINARY_CONTENT_REVIEW');continue
                        inventory.append(dict(path=relative,size=len(data),sha256=hashlib.sha256(data).hexdigest()))
                        for rule,line in inspect_text(text,denied):flag(rule,line)
                    except OSError:errors.append('ENTRY_READ_FAILED')
        except AuditError as error:
            if str(error)=='ENTRY_LIMIT':
                errors.append('ENTRY_LIMIT');stack.clear();break
            errors.append('UNREADABLE_DIRECTORY')
        except OSError:errors.append('UNREADABLE_DIRECTORY')
    inventory.sort(key=lambda row:row['path'])
    findings.sort(key=lambda row:(row['path'],row['line'] or 0,row['rule']))
    return dict(schema_version=1,status='REVIEW_REQUIRED' if findings or errors else 'NO_PATTERN_FINDINGS',
                inventory=inventory,findings=findings,errors=errors,excluded=excluded,
                scope=dict(max_entries=MAX_FILES,max_file_bytes=MAX_FILE,max_total_bytes=MAX_TOTAL,
                           bytes_read=MAX_TOTAL-budget[0],git_history_scanned=False,semantic_ip_review=False))

def validate_manifest(data):
    if not isinstance(data,dict) or data.get('schema_version')!=1 or not isinstance(data.get('inventory'),list):raise AuditError('INVALID_MANIFEST')
    paths=[]
    for row in data['inventory']:
        if not isinstance(row,dict):raise AuditError('INVALID_MANIFEST')
        path=row.get('path');p=PurePosixPath(path) if isinstance(path,str) else None
        if not p or p.is_absolute() or '\\' in path or ':' in path or any(part in ('.','..') for part in path.split('/')) or p.as_posix()!=path:raise AuditError('INVALID_MANIFEST_PATH')
        if not isinstance(row.get('size'),int) or isinstance(row['size'],bool) or row['size']<0 or not re.fullmatch('[a-f0-9]{64}',str(row.get('sha256',''))):raise AuditError('INVALID_MANIFEST')
        paths.append(path.casefold())
    if len(set(paths))!=len(paths):raise AuditError('DUPLICATE_MANIFEST_PATH')
    return sorted(data['inventory'],key=lambda row:row['path'])

def read_json(path):
    p=explicit_path(path)
    if os.name == 'nt':
        data=_windows().read_bounded(p, MAX_JSON, AuditError, single_link=True)
    else:
        data=_read_control_posix(p)
    return json.loads(data.decode('utf-8'))


def _read_control_posix(path):
    expected=path.lstat()
    if not stat.S_ISREG(expected.st_mode) or linked(path):raise AuditError('INPUT_NOT_REGULAR')
    if expected.st_size>MAX_JSON:raise AuditError('MANIFEST_TOO_LARGE')
    flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0)
    fd=os.open(path,flags)
    try:
        before=os.fstat(fd)
        identity=lambda info:(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
        if not stat.S_ISREG(before.st_mode) or identity(expected)!=identity(before):raise AuditError('INPUT_CHANGED')
        chunks=[];size=0
        while True:
            block=os.read(fd,min(65536,MAX_JSON+1-size))
            if not block:break
            size+=len(block)
            if size>MAX_JSON:raise AuditError('MANIFEST_TOO_LARGE')
            chunks.append(block)
        after=os.fstat(fd)
        if size!=before.st_size or identity(before)!=identity(after) or identity(path.lstat())!=identity(after):raise AuditError('INPUT_CHANGED')
        return b''.join(chunks)
    finally:
        os.close(fd)


def _report_bytes(data):
    chunks=[];size=0
    for text in json.JSONEncoder(indent=2).iterencode(data):
        block=text.encode('utf-8')
        size+=len(block)
        if size+1>MAX_REPORT:raise AuditError('REPORT_TOO_LARGE')
        chunks.append(block)
    return b''.join(chunks)+b'\n'

def write_new(path,data,root):
    if os.name == 'nt':
        return _windows().write_report(path, _report_bytes(data), root, AuditError)
    p=explicit_path(path)
    if p.is_relative_to(root):raise AuditError('REPORT_MUST_BE_OUTSIDE_ROOT')
    with p.open('x',encoding='utf-8',newline='\n') as handle:json.dump(data,handle,indent=2);handle.write('\n')

class Parser(argparse.ArgumentParser):
    def error(self,message):raise AuditError('INVALID_ARGUMENTS')

def main(argv=None):
    parser=Parser(description=__doc__,prog='release_audit.py' if os.name=='nt' else None)
    parser.add_argument('--root',required=True)
    parser.add_argument('--deny-file',help='Private JSON array of literal markers; never print its values')
    parser.add_argument('--manifest',help='Compare against an independently reviewed exact inventory')
    parser.add_argument('--report',help='New private JSON report outside root')
    parser.add_argument('--write-manifest',help='New inventory outside root; does not grant approval')
    try:
        args=parser.parse_args(argv);root=explicit_path(args.root)
        denied=read_json(args.deny_file) if args.deny_file else []
        if not isinstance(denied,list) or len(denied)>1000 or any(not isinstance(x,str) or len(x)<3 or len(x)>1024 for x in denied):raise AuditError('INVALID_DENY_FILE')
        result=inspect(root,denied)
        if args.manifest and validate_manifest(read_json(args.manifest))!=result['inventory']:
            result['errors'].append('MANIFEST_MISMATCH');result['status']='REVIEW_REQUIRED'
        if args.report:write_new(args.report,result,root)
        if args.write_manifest:
            if result['status']!='NO_PATTERN_FINDINGS':raise AuditError('MANIFEST_DENIED_FINDINGS')
            write_new(args.write_manifest,dict(schema_version=1,inventory=result['inventory']),root)
        summary=dict(status=result['status'],files=len(result['inventory']),findings=dict(Counter(x['rule'] for x in result['findings'])),errors=result['errors'])
        print(json.dumps(summary,sort_keys=True));return int(result['status']!='NO_PATTERN_FINDINGS')
    except KeyboardInterrupt:
        if os.name!='nt':raise
        print(json.dumps(dict(status='ERROR',code='AUDIT_INTERRUPTED')));return 130
    except (OSError,UnicodeError,ValueError,TypeError,RecursionError):
        print(json.dumps(dict(status='ERROR',code='AUDIT_INPUT_OR_OUTPUT_ERROR')));return 2

if __name__=='__main__':sys.exit(main())
