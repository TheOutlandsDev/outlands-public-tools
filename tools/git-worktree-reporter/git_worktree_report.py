"""Report supported local Git worktree observations without changing Git state."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import threading
import time
import unicodedata

MAX_OUTPUT = 8 * 1024 * 1024
MAX_CONFIG = 1024 * 1024
MAX_METADATA = 32 * 1024 * 1024
MAX_ENTRIES = 10000
MAX_PATH = 4096
COMMAND_SECONDS = 15
OID = re.compile(r'(?:[0-9a-f]{40}|[0-9a-f]{64})\Z')
MODE = re.compile(r'[0-7]{6}\Z')
XY = re.compile(r'[.MADRCUT]{2}\Z')
SUB = re.compile(r'(?:N\.\.\.|S[.C][.M][.U])\Z')


class ReportError(Exception):
    """Fixed public code, never Git's raw error or a source path."""


def require(value, code):
    if not value:
        raise ReportError(code)


def linked(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def local_path(value):
    path = Path(value)
    raw = str(value)
    require(path.is_absolute() and '..' not in path.parts and not raw.startswith(('\\\\', '//')),
            'LOCAL_ABSOLUTE_PATH_REQUIRED')
    require(not any(unicodedata.category(c).startswith('C') for c in raw), 'INVALID_LOCAL_PATH')
    require(os.name != 'nt' or ':' not in raw[2:], 'DEVICE_OR_STREAM_PATH_REJECTED')
    return path


def no_links(path):
    for part in reversed((path, *path.parents)):
        require(not linked(part.lstat()), 'LINKED_PATH_REJECTED')


def metadata_present(path):
    # Unlike Path.exists(), lstat does not follow a final symbolic link. Check
    # parents first as well, including Windows reparse points, before children.
    for part in reversed((path, *path.parents)):
        try: info = part.lstat()
        except FileNotFoundError: return False
        require(not linked(info), 'LINKED_PATH_REJECTED')
    return True


def canonical_directory(value):
    """Canonicalize an existing no-link directory, including Windows DOS aliases."""
    path = local_path(value)
    no_links(path)
    before = path.lstat()
    require(stat.S_ISDIR(before.st_mode), 'DIRECTORY_REQUIRED')
    # Resolving before link validation would hide unsupported symlink/reparse
    # components. After validation it expands ordinary 8.3/long-name aliases.
    canonical = local_path(path.resolve(strict=True))
    no_links(canonical)
    require(identity(before) == identity(canonical.lstat()), 'INPUT_CHANGED')
    return canonical


def identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def read_regular(path, maximum):
    no_links(path)
    expected = path.lstat()
    require(stat.S_ISREG(expected.st_mode) and expected.st_size <= maximum, 'METADATA_FILE_UNSUPPORTED')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and not linked(before) and identity(before) == identity(expected), 'INPUT_CHANGED')
        chunks, size = [], 0
        while True:
            chunk = os.read(fd, min(65536, maximum + 1 - size))
            if not chunk:
                break
            size += len(chunk); require(size <= maximum, 'METADATA_BYTE_LIMIT'); chunks.append(chunk)
        after = os.fstat(fd)
        require(size == before.st_size and identity(before) == identity(after)
                and before.st_ctime_ns == after.st_ctime_ns and identity(after) == identity(path.lstat()), 'INPUT_CHANGED')
        return b''.join(chunks)
    finally:
        os.close(fd)


def isolated_environment():
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith(('GIT_', 'GCM_', 'SSH_', 'GIT_SSH'))
           and key.upper() not in {'PAGER', 'GITPAGER', 'LD_PRELOAD', 'LD_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES', 'DYLD_LIBRARY_PATH'}}
    env.update({'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_SYSTEM': os.devnull,
                'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_OPTIONAL_LOCKS': '0',
                'GIT_TERMINAL_PROMPT': '0', 'GIT_NO_LAZY_FETCH': '1',
                'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_ALLOW_PROTOCOL': '',
                'GIT_ATTR_NOSYSTEM': '1', 'LC_ALL': 'C', 'LANG': 'C'})
    return env


class WindowsJob:
    """Kill-on-close job for owned Git descendants, not a hostile-program sandbox."""
    def __init__(self):
        self.handle = None
        if os.name != 'nt':
            return
        from ctypes import wintypes as w
        class Basic(ctypes.Structure):
            _fields_ = [('a', ctypes.c_longlong), ('b', ctypes.c_longlong), ('flags', w.DWORD),
                        ('minimum', ctypes.c_size_t), ('maximum', ctypes.c_size_t), ('count', w.DWORD),
                        ('affinity', ctypes.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]
        class Counters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in ('a', 'b', 'c', 'd', 'e', 'f')]
        class Limits(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', Counters), ('a', ctypes.c_size_t), ('b', ctypes.c_size_t),
                        ('c', ctypes.c_size_t), ('d', ctypes.c_size_t)]
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        self.kernel.CreateJobObjectW.restype = w.HANDLE
        self.kernel.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        self.kernel.SetInformationJobObject.restype = w.BOOL
        self.kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.kernel.AssignProcessToJobObject.restype = w.BOOL
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.kernel.CloseHandle.restype = w.BOOL
        handle = self.kernel.CreateJobObjectW(None, None)
        require(bool(handle), 'OWNED_PROCESS_JOB_UNAVAILABLE')
        limits = Limits(); limits.basic.flags = 0x2000
        if not self.kernel.SetInformationJobObject(handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            self.kernel.CloseHandle(handle); raise ReportError('OWNED_PROCESS_JOB_UNAVAILABLE')
        self.handle = handle

    def assign(self, process):
        if self.handle is not None:
            require(bool(self.kernel.AssignProcessToJobObject(self.handle, int(process._handle))), 'OWNED_PROCESS_JOB_UNAVAILABLE')

    def close(self):
        if self.handle is not None:
            self.kernel.CloseHandle(self.handle); self.handle = None


def run_bounded(arguments, *, cwd=None, maximum=MAX_OUTPUT, seconds=COMMAND_SECONDS):
    require(type(maximum) is int and 0 < maximum <= MAX_OUTPUT and 0 < seconds <= 60, 'INVALID_COMMAND_LIMIT')
    job = WindowsJob(); process = None; workers = []; limited = threading.Event(); read_failed = threading.Event(); data = [bytearray(), bytearray()]
    def stop():
        if process is None:
            return
        if os.name == 'nt':
            job.close()
            if process.poll() is None:
                process.kill()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    def reader(pipe, index, limit):
        try:
            while True:
                block = pipe.read(65536)
                if not block:
                    break
                if len(data[index]) + len(block) > limit:
                    limited.set(); break
                data[index].extend(block)
        except (OSError, ValueError):
            read_failed.set()
        finally:
            try: pipe.close()
            except (OSError, ValueError): read_failed.set()
    try:
        process = subprocess.Popen(arguments, cwd=cwd, env=isolated_environment(), stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                                   start_new_session=os.name != 'nt',
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
        job.assign(process)
        workers = [threading.Thread(target=reader, args=(pipe, index, limit), daemon=True)
                   for index, (pipe, limit) in enumerate(((process.stdout, maximum), (process.stderr, 65536)))]
        for worker in workers: worker.start()
        deadline = time.monotonic() + seconds
        while process.poll() is None:
            if limited.is_set(): stop(); raise ReportError('GIT_OUTPUT_LIMIT')
            if time.monotonic() >= deadline: stop(); raise ReportError('GIT_TIMEOUT')
            time.sleep(.01)
        job.close()
        for worker in workers: worker.join(1)
        if any(worker.is_alive() for worker in workers): stop(); raise ReportError('GIT_PIPE_DRAIN_FAILED')
        require(not limited.is_set(), 'GIT_OUTPUT_LIMIT')
        require(not read_failed.is_set(), 'GIT_PIPE_READ_FAILED')
        require(process.returncode == 0, 'GIT_COMMAND_FAILED')
        return bytes(data[0])
    finally:
        if process is not None and process.poll() is None:
            stop()
            try: process.wait(timeout=2)
            except subprocess.TimeoutExpired: pass
        job.close()
        for worker in workers: worker.join(1)
        if process is not None and not workers:
            if process.stdout is not None: process.stdout.close()
            if process.stderr is not None: process.stderr.close()


def git_arguments(executable, repo, command):
    config = {'core.fsmonitor': 'false', 'core.untrackedCache': 'false', 'core.hooksPath': os.devnull,
              'core.attributesFile': os.devnull, 'core.excludesFile': os.devnull,
              'core.pager': 'cat', 'gc.auto': '0', 'maintenance.auto': 'false',
              'protocol.allow': 'never', 'submodule.recurse': 'false', 'status.submoduleSummary': 'false',
              'diff.external': '', 'diff.renames': 'true', 'diff.renameLimit': '1000',
              'status.aheadBehind': 'true', 'color.ui': 'false'}
    result = [str(executable), '--no-pager', '--no-optional-locks', '--no-lazy-fetch', '--no-replace-objects']
    for key, value in config.items(): result += ['-c', key + '=' + value]
    return result + ['-C', str(repo), *command]


def check_config(data):
    require(data.endswith(b'\0') and len(data) <= MAX_CONFIG, 'CONFIG_FORMAT_UNSUPPORTED')
    for raw in data[:-1].split(b'\0'):
        try: key = raw.decode('utf-8').casefold()
        except UnicodeError: raise ReportError('CONFIG_FORMAT_UNSUPPORTED') from None
        require(0 < len(key) <= 1024 and not any(ord(c) < 32 for c in key), 'CONFIG_FORMAT_UNSUPPORTED')
        require(not key.startswith(('filter.', 'include.', 'includeif.'))
                and key not in {'core.worktree', 'extensions.partialclone', 'extensions.objectformat.compatobjectformat',
                                'core.sparsecheckout', 'core.sparsecheckoutcone', 'index.sparse', 'core.alternaterefscommand'}
                and not (key.startswith('diff.') and key.endswith(('.command', '.textconv')))
                and not (key.startswith('remote.') and key.endswith(('.promisor', '.partialclonefilter'))),
                'CONFIGURED_HELPER_OR_LAYOUT_UNSUPPORTED')


def path_text(text):
    require(0 < len(text) <= MAX_PATH and not text.startswith(('/', '\\'))
            and re.match(r'^[A-Za-z]:', text) is None and '\0' not in text
            and all(part not in ('', '.', '..') for part in text.split('/')), 'STATUS_PATH_UNSUPPORTED')
    return text


def parse_status(data):
    require(type(data) is bytes and len(data) <= MAX_OUTPUT and data.endswith(b'\0'), 'STATUS_FORMAT_UNSUPPORTED')
    try: fields = data[:-1].decode('utf-8').split('\0')
    except UnicodeError: raise ReportError('STATUS_UTF8_REQUIRED') from None
    headers = {}; rows = []; seen = set(); ignored_headers = 0; index = 0
    while index < len(fields):
        text = fields[index]; index += 1
        require(len(text) <= MAX_PATH + 512, 'STATUS_RECORD_LIMIT')
        if text.startswith('# '):
            key, sep, value = text[2:].partition(' ')
            require(bool(sep) and len(value) <= MAX_PATH, 'STATUS_FORMAT_UNSUPPORTED')
            if key in ('branch.oid', 'branch.head', 'branch.upstream', 'branch.ab'):
                require(key not in headers, 'STATUS_DUPLICATE_HEADER'); headers[key] = value
            else: ignored_headers += 1
            continue
        require(len(rows) < MAX_ENTRIES, 'STATUS_ENTRY_LIMIT')
        kind = text[:1]; old_path = None
        if kind == '?':
            require(text.startswith('? '), 'STATUS_FORMAT_UNSUPPORTED')
            row = {'kind': 'untracked', 'path': path_text(text[2:]), 'index_status': '?', 'worktree_status': '?', 'submodule': None}
        elif kind in ('1', '2', 'u'):
            parts = text.split(' ', {'1': 8, '2': 9, 'u': 10}[kind])
            require(len(parts) == {'1': 9, '2': 10, 'u': 11}[kind] and parts[0] == kind,
                    'STATUS_FORMAT_UNSUPPORTED')
            status_code, sub = parts[1:3]
            require(bool(XY.fullmatch(status_code)) and bool(SUB.fullmatch(sub)), 'STATUS_FORMAT_UNSUPPORTED')
            modes, objects = (parts[3:7], parts[7:10]) if kind == 'u' else (parts[3:6], parts[6:8])
            require(all(MODE.fullmatch(mode) for mode in modes) and all(OID.fullmatch(oid) for oid in objects), 'STATUS_FORMAT_UNSUPPORTED')
            if kind == '2':
                require(re.fullmatch(r'[RC][0-9]{1,3}', parts[8]) is not None
                        and int(parts[8][1:]) <= 100 and index < len(fields), 'STATUS_FORMAT_UNSUPPORTED')
                old_path = path_text(fields[index]); index += 1
            row = {'kind': {'1': 'tracked', '2': 'renamed_or_copied', 'u': 'unmerged'}[kind],
                   'path': path_text(parts[-1]), 'index_status': status_code[0], 'worktree_status': status_code[1],
                   'submodule': sub if sub.startswith('S') else None}
            if old_path is not None: row['original_path'] = old_path; row['similarity'] = parts[8]
        else: raise ReportError('STATUS_RECORD_UNSUPPORTED')
        require(row['path'] not in seen, 'STATUS_DUPLICATE_PATH'); seen.add(row['path']); rows.append(row)
    require('branch.oid' in headers and 'branch.head' in headers, 'STATUS_BRANCH_HEADERS_REQUIRED')
    head, branch = headers['branch.oid'], headers['branch.head']
    require(head == '(initial)' or OID.fullmatch(head), 'STATUS_FORMAT_UNSUPPORTED')
    require(bool(branch) and not any(unicodedata.category(c).startswith('C') for c in branch), 'STATUS_BRANCH_UNSUPPORTED')
    upstream = headers.get('branch.upstream'); counts = headers.get('branch.ab'); ahead = behind = None
    if upstream is not None:
        require(bool(upstream) and not any(unicodedata.category(c).startswith('C') for c in upstream), 'STATUS_BRANCH_UNSUPPORTED')
    if counts is not None:
        require(upstream is not None and re.fullmatch(r'\+[0-9]{1,9} -[0-9]{1,9}', counts), 'STATUS_FORMAT_UNSUPPORTED')
        a, b = counts.split(' '); ahead, behind = int(a[1:]), int(b[1:])
    rows.sort(key=lambda row: row['path'])
    return {'schema_version': 1, 'tool': 'git-worktree-reporter',
            'head_oid': None if head == '(initial)' else head,
            'branch': None if branch == '(detached)' else branch,
            'head_state': 'unborn' if head == '(initial)' else 'detached' if branch == '(detached)' else 'branch',
            'upstream': {'name': upstream, 'ahead': ahead, 'behind': behind,
                         'basis': 'stored_local_refs_only_no_network_refresh',
                         'comparison': 'available' if counts is not None else 'unavailable'},
            'entry_count': len(rows), 'entries': rows,
            'counts': {'untracked': sum(r['kind'] == 'untracked' for r in rows),
                       'unmerged': sum(r['kind'] == 'unmerged' for r in rows),
                       'staged': sum(r['kind'] not in ('untracked', 'unmerged') and r['index_status'] != '.' for r in rows),
                       'unstaged': sum(r['kind'] not in ('untracked', 'unmerged') and r['worktree_status'] != '.' for r in rows)},
            'ignored_header_count': ignored_headers, 'status_sha256': hashlib.sha256(data).hexdigest(),
            'coverage': 'selected_worktree_status_excluding_ignored_and_submodule_contents',
            'interpretation': 'Git status observations under isolated configuration, not a backup, content inventory, secret scan, ownership or publication clearance.'}


def metadata_pointer(base, text):
    # Git's relative commondir pointers legitimately contain '..'. Validate raw
    # routing syntax before filesystem observation, then check unnormalized
    # components so lexical cleanup cannot erase an intermediate symbolic link.
    require(bool(text) and len(text) <= MAX_PATH and not text.startswith(('\\', '//'))
            and not any(unicodedata.category(c).startswith('C') for c in text), 'GIT_METADATA_POINTER_UNSUPPORTED')
    pointer = Path(text)
    if os.name == 'nt':
        require(':' not in text[2:] and (not pointer.drive or pointer.is_absolute())
                and (not pointer.anchor or pointer.is_absolute()), 'GIT_METADATA_POINTER_UNSUPPORTED')
    else:
        require(re.match(r'^[A-Za-z]:', text) is None and '\\' not in text, 'GIT_METADATA_POINTER_UNSUPPORTED')
    candidate = pointer if pointer.is_absolute() else base / pointer
    result = local_path(Path(os.path.abspath(candidate)))
    no_links(candidate)
    no_links(result)
    return result


def metadata_directories(repo):
    marker = repo / '.git'; no_links(marker)
    if marker.is_dir(): gitdir = marker
    else:
        text = read_regular(marker, 4096).decode('utf-8')
        require(text.startswith('gitdir: ') and '\n' not in text.rstrip('\n'), 'GIT_LAYOUT_UNSUPPORTED')
        gitdir = metadata_pointer(repo, text[8:].rstrip('\n'))
    no_links(gitdir); require(gitdir.is_dir(), 'GIT_LAYOUT_UNSUPPORTED')
    common_marker = gitdir / 'commondir'; common = gitdir
    if metadata_present(common_marker):
        text = read_regular(common_marker, 4096).decode('utf-8').rstrip('\n')
        require(bool(text) and '\n' not in text, 'GIT_LAYOUT_UNSUPPORTED')
        common = metadata_pointer(gitdir, text)
        no_links(common); require(common.is_dir(), 'GIT_LAYOUT_UNSUPPORTED')
    return gitdir, common


def metadata_receipt(gitdir, common):
    paths = {gitdir / 'HEAD', gitdir / 'index', gitdir / 'config.worktree',
             common / 'config', common / 'packed-refs', gitdir / 'commondir'}
    values = []
    for path in sorted(paths):
        if metadata_present(path):
            data = read_regular(path, MAX_METADATA); values.append((str(path), hashlib.sha256(data).hexdigest()))
        else: values.append((str(path), None))
    return values


def inspect(repo_value, executable_value):
    repo, executable = local_path(repo_value), local_path(executable_value)
    no_links(repo); no_links(executable)
    require(repo.is_dir() and repo.parent != repo, 'WORKTREE_DIRECTORY_REQUIRED')
    require(stat.S_ISREG(executable.lstat().st_mode) and (os.name != 'nt' or executable.suffix.lower() == '.exe'), 'TRUSTED_GIT_EXECUTABLE_REQUIRED')
    version_raw = run_bounded([str(executable), '--version'], maximum=4096)
    match = re.fullmatch(rb'git version ([0-9]+)\.([0-9]+)\.([0-9]+)(?:[^\r\n]*)\r?\n?', version_raw)
    require(match is not None and tuple(map(int, match.groups())) >= (2, 49, 0), 'GIT_2_49_OR_NEWER_REQUIRED')
    gitdir, common = metadata_directories(repo)
    for unsupported in (common / 'shallow', common / 'info/grafts', common / 'objects/info/alternates', common / 'objects/info/http-alternates'):
        require(not metadata_present(unsupported), 'SHALLOW_GRAFT_OR_ALTERNATE_UNSUPPORTED')
    marker_before = read_regular(repo / '.git', 4096) if (repo / '.git').is_file() else None
    before = metadata_receipt(gitdir, common)
    config = run_bounded(git_arguments(executable, repo, ['config', '--null', '--name-only', '--list', '--no-includes']), maximum=MAX_CONFIG)
    check_config(config)
    top = run_bounded(git_arguments(executable, repo, ['rev-parse', '--show-toplevel', '--is-inside-work-tree']), maximum=8192)
    lines = top.decode('utf-8').splitlines()
    require(len(lines) == 2 and lines[1] == 'true' and os.path.normcase(str(Path(lines[0]).resolve())) == os.path.normcase(str(repo.resolve())), 'EXACT_WORKTREE_ROOT_REQUIRED')
    status = run_bounded(git_arguments(executable, repo, ['status', '--porcelain=v2', '-z', '--branch', '--ahead-behind', '--untracked-files=all', '--ignored=no', '--ignore-submodules=all', '--renames']))
    report = parse_status(status)
    require(before == metadata_receipt(gitdir, common), 'REPOSITORY_METADATA_CHANGED')
    require(marker_before == (read_regular(repo / '.git', 4096) if (repo / '.git').is_file() else None), 'REPOSITORY_METADATA_CHANGED')
    report['git_version'] = '.'.join(str(int(x)) for x in match.groups())
    report['observed_control_files_unchanged'] = True
    report['configuration'] = 'global_system_disabled_local_includes_filters_partial_clones_refused'
    report['subprocess_limits'] = {'seconds_each': COMMAND_SECONDS, 'stdout_bytes': MAX_OUTPUT, 'stderr_bytes': 65536, 'max_entries': MAX_ENTRIES}
    return report


def write_report(report, output_value, repo_value):
    output, repo = local_path(output_value), local_path(repo_value)
    no_links(output.parent)
    require(output.parent.is_dir() and not output.exists() and not output.is_symlink(), 'FRESH_OUTPUT_REQUIRED')
    repo = canonical_directory(repo)
    output = canonical_directory(output.parent) / output.name
    require(not output.is_relative_to(repo), 'OUTPUT_INSIDE_WORKTREE')
    gitdir, common = metadata_directories(repo)
    gitdir, common = canonical_directory(gitdir), canonical_directory(common)
    require(not output.is_relative_to(gitdir) and not output.is_relative_to(common), 'OUTPUT_INSIDE_GIT_METADATA')
    payload = (json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + '\n').encode('utf-8')
    require(len(payload) <= MAX_OUTPUT, 'REPORT_BYTE_LIMIT')
    output.mkdir(mode=0o700)
    for name, data in [('report.json', payload), ('MANIFEST.json', (json.dumps({'schema_version': 1, 'files': [{'path': 'report.json', 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}]}, indent=2) + '\n').encode('utf-8'))]:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
        fd = os.open(output / name, flags, 0o600)
        with os.fdopen(fd, 'wb') as stream: stream.write(data)


class Parser(argparse.ArgumentParser):
    def error(self, _message): raise ReportError('ARGUMENTS_INVALID')


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('--repo', type=Path, required=True)
        parser.add_argument('--git-executable', type=Path, required=True)
        parser.add_argument('--output', type=Path, required=True)
        args = parser.parse_args(argv)
        report = inspect(args.repo, args.git_executable)
        write_report(report, args.output, args.repo)
        print(json.dumps({'status': 'LOCAL_STATUS_RECORDED', 'head_state': report['head_state'], 'entry_count': report['entry_count'], 'counts': report['counts']}, sort_keys=True))
        return 0
    except ReportError as error:
        print(json.dumps({'status': 'INCOMPLETE', 'error': str(error)}, sort_keys=True)); return 2
    except (OSError, ValueError, OverflowError, UnicodeError, subprocess.SubprocessError):
        print(json.dumps({'status': 'INCOMPLETE', 'error': 'IO_OR_GIT_INPUT_ERROR'}, sort_keys=True)); return 2


if __name__ == '__main__':
    raise SystemExit(main())
