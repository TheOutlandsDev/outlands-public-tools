"""Create a bounded CSV content-hash inventory of an explicitly selected folder."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import secrets
import stat
import unicodedata


EXCLUDED_DIRECTORIES = frozenset({
    '.git', '.hg', '.svn', '.ssh', '.aws', '.azure', '.gnupg', '.kube',
    '.venv', 'venv', 'env', '__pycache__', '.pytest_cache', '.ruff_cache',
    '.cache', 'node_modules', 'vendor', 'third_party', 'third-party',
    'build', 'dist', 'target', 'inventory', 'snapshots', 'backups',
    'logs', 'data', 'databases', 'models', 'datasets',
})
EXCLUDED_SUFFIXES = frozenset({
    '.pem', '.key', '.p12', '.pfx', '.db', '.sqlite', '.sqlite3',
    '.log', '.zip', '.7z', '.tar', '.gz', '.zst', '.pyc', '.pyo',
})
MAX_ENTRIES = 10000
MAX_TREE_BYTES = 1024 * 1024
DEFAULT_TREE_DEPTH = 16


class InventoryError(Exception):
    """A stable code; never an upstream error containing source paths or data."""


_WINDOWS_BACKEND = None


def _windows():
    global _WINDOWS_BACKEND
    if _WINDOWS_BACKEND is None:
        spec = importlib.util.spec_from_file_location(
            'outlands_inventory_windows', Path(__file__).with_name('inventory_windows.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _WINDOWS_BACKEND = module
    return _WINDOWS_BACKEND


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise InventoryError(code)


def _is_link(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, 'st_file_attributes', 0)
        & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))


def _no_links(path: Path) -> None:
    for component in reversed((path, *path.parents)):
        _require(not _is_link(component.lstat()), 'LINKED_PATH')


def _directory(value: Path) -> Path:
    if os.name == 'nt':
        return _windows().checked_directory(value, InventoryError)
    path = Path(value).absolute()
    _require('..' not in path.parts, 'INVALID_PATH')
    _no_links(path)
    _require(stat.S_ISDIR(path.lstat().st_mode), 'DIRECTORY_REQUIRED')
    return path


def _identity(info: os.stat_result) -> tuple[int, ...]:
    # Python 3.12+ Windows path/fd stat results can differ in deprecated ctime
    # semantics. Birth time is comparable across both; POSIX keeps change time.
    comparable_time = info.st_birthtime_ns if os.name == 'nt' else info.st_ctime_ns
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, comparable_time)


def _descriptor_identity(info: os.stat_result) -> tuple[int, ...]:
    # Retain the fd's own change-time check before/after reading on every OS.
    return (*_identity(info), info.st_ctime_ns)


def _sha256(path: Path, expected: os.stat_result, limit: int) -> str:
    if os.name == 'nt':
        return _windows().hash_file(path, expected, limit, InventoryError, _identity, _descriptor_identity)
    _no_links(path)
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    flags |= getattr(os, 'O_BINARY', 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        _require(stat.S_ISREG(before.st_mode) and not _is_link(before), 'NONREGULAR_INPUT')
        _require(_identity(before) == _identity(expected), 'SOURCE_CHANGED')
        digest, actual = hashlib.sha256(), 0
        while True:
            block = os.read(fd, min(65536, limit + 1 - actual))
            if not block:
                break
            actual += len(block)
            _require(actual <= limit, 'FILE_BYTE_LIMIT')
            digest.update(block)
        after = os.fstat(fd)
        _require(actual == before.st_size and _descriptor_identity(before) == _descriptor_identity(after),
                 'SOURCE_CHANGED')
        _require(_identity(path.lstat()) == _identity(after), 'SOURCE_CHANGED')
        return digest.hexdigest().upper()
    finally:
        os.close(fd)


def _excluded_file(name: str) -> bool:
    lowered = name.casefold()
    return (lowered.startswith('.env') or lowered.startswith('credentials')
            or lowered in {'id_rsa', 'id_ed25519'}
            or Path(lowered).suffix in EXCLUDED_SUFFIXES
            or lowered.endswith(('.sqlite-wal', '.sqlite-shm', '.sqlite3-wal', '.sqlite3-shm')))


def _collect(root: Path, max_files: int, max_file_bytes: int,
             max_total_bytes: int, *, observed_directories: list[tuple[str, ...]] | None = None,
             extra_excluded_directories: frozenset[str] = frozenset()
             ) -> tuple[list[tuple[Path, os.stat_result]], dict[str, int]]:
    selected: list[tuple[Path, os.stat_result]] = []
    skipped = {'directories': 0, 'files': 0, 'links': 0, 'nonregular': 0}
    entries, total = 0, 0

    def failed_walk(_error: OSError) -> None:
        raise InventoryError('SOURCE_SCAN_FAILED')

    walker = os.walk
    if os.name == 'nt':
        def walker(*args, **kwargs):
            return _windows().walk(*args, **kwargs, error=InventoryError)
    for current, directories, files in walker(root, topdown=True, followlinks=False,
                                              onerror=failed_walk):
        here = Path(current)
        _no_links(here)
        if observed_directories is not None and here != root:
            observed_directories.append(here.relative_to(root).parts)
        entries += len(directories) + len(files)
        _require(entries <= MAX_ENTRIES, 'ENTRY_LIMIT')
        keep = []
        for name in sorted(directories, key=lambda value: (value.casefold(), value)):
            info = (here / name).lstat()
            if _is_link(info):
                skipped['links'] += 1
            elif name.casefold() in EXCLUDED_DIRECTORIES | extra_excluded_directories:
                skipped['directories'] += 1
            else:
                _require(stat.S_ISDIR(info.st_mode), 'SOURCE_CHANGED')
                keep.append(name)
        directories[:] = keep
        for name in sorted(files, key=lambda value: (value.casefold(), value)):
            path = here / name
            info = path.lstat()
            if _is_link(info):
                skipped['links'] += 1
                continue
            if not stat.S_ISREG(info.st_mode):
                skipped['nonregular'] += 1
                continue
            if _excluded_file(name):
                skipped['files'] += 1
                continue
            _require(info.st_size <= max_file_bytes, 'FILE_BYTE_LIMIT')
            total += info.st_size
            _require(total <= max_total_bytes, 'TOTAL_BYTE_LIMIT')
            selected.append((path, info))
            _require(len(selected) <= max_files, 'FILE_COUNT_LIMIT')
    selected.sort(key=lambda item: (item[0].relative_to(root).as_posix().casefold(),
                                    item[0].relative_to(root).as_posix()))
    return selected, skipped


def _tree_name(value: str) -> str:
    """Quote names and escape invisible/control characters without losing Unicode."""
    quoted = json.dumps(value, ensure_ascii=False)
    return ''.join(json.dumps(char, ensure_ascii=True)[1:-1]
                   if unicodedata.category(char).startswith('C') or char in '\u2028\u2029'
                   else char for char in quoted)


def _render_tree(files: list[tuple[str, ...]], directories: list[tuple[str, ...]],
                 max_depth: int) -> tuple[bytes, dict]:
    """Render only the already collected scope, without reopening or walking inputs."""
    nodes = {parts: 'directory' for parts in directories}
    nodes.update({parts: 'file' for parts in files})
    children: dict[tuple[str, ...], list[tuple[str, ...]]] = {}
    for parts in nodes:
        children.setdefault(parts[:-1], []).append(parts)
    for values in children.values():
        values.sort(key=lambda parts: (nodes[parts] != 'directory', parts[-1].casefold(), parts[-1]))
    lines: list[str] = []
    byte_count = 0

    def append_line(value: str) -> None:
        nonlocal byte_count
        try:
            byte_count += len(value.encode('utf-8')) + 1
        except UnicodeError:
            raise InventoryError('SOURCE_NAME_UNSUPPORTED') from None
        _require(byte_count <= MAX_TREE_BYTES, 'TREE_BYTE_LIMIT')
        lines.append(value)

    append_line('OUTLANDS selected source tree')
    append_line('.')
    rendered = 0
    # Stack keeps rendering bounded by collected entries, not Python's recursion limit.
    roots = children.get((), [])
    stack = [(parts, '', index == len(roots) - 1) for index, parts in reversed(list(enumerate(roots)))]
    while stack:
        parts, prefix, last = stack.pop()
        directory = nodes[parts] == 'directory'
        append_line(prefix + ('`-- ' if last else '|-- ') + _tree_name(parts[-1] + ('/' if directory else '')))
        rendered += 1
        below = children.get(parts, [])
        next_prefix = prefix + ('    ' if last else '|   ')
        if below and len(parts) >= max_depth:
            append_line(next_prefix + '`-- [subtree omitted at display depth limit]')
        else:
            stack.extend((child, next_prefix, index == len(below) - 1)
                         for index, child in reversed(list(enumerate(below))))
    try:
        data = ('\n'.join(lines) + '\n').encode('utf-8')
    except UnicodeError:
        raise InventoryError('SOURCE_NAME_UNSUPPORTED') from None
    _require(len(data) <= MAX_TREE_BYTES, 'TREE_BYTE_LIMIT')
    return data, {'format': 'outlands.quoted_tree.v1', 'path': 'tree.txt',
                  'scope': 'selected_regular_files_and_observed_nonexcluded_directories',
                  'directory_count': len(directories), 'entry_count': len(nodes),
                  'displayed_entries': rendered, 'hidden_by_depth': len(nodes) - rendered,
                  'display_complete': rendered == len(nodes), 'max_display_depth': max_depth,
                  'max_bytes': MAX_TREE_BYTES,
                  'tree_txt_sha256': hashlib.sha256(data).hexdigest().upper()}


def _additional_exclusions(values: tuple[str, ...] | list[str]) -> frozenset[str]:
    _require(isinstance(values, (tuple, list)) and len(values) <= 64, 'INVALID_EXCLUSIONS')
    for value in values:
        _require(isinstance(value, str) and 0 < len(value) <= 255 and value not in ('.', '..')
                 and not any(char in value for char in '/\\')
                 and not any(unicodedata.category(char).startswith('C') for char in value),
                 'INVALID_EXCLUSIONS')
        try:
            value.encode('utf-8')
        except UnicodeError:
            raise InventoryError('INVALID_EXCLUSIONS') from None
    return frozenset(value.casefold() for value in values)


def _csv_path(value: str) -> tuple[str, str]:
    # Quoting CSV alone does not stop spreadsheet formula evaluation.
    stripped = value.lstrip()
    unsafe = value.startswith(("'", '\t', '\r', '\n')) or stripped.startswith(('=', '+', '-', '@'))
    return ("'" + value, 'true') if unsafe else (value, 'false')


def _exclusive_write(path: Path, data: bytes) -> None:
    if os.name == 'nt':
        return _windows().exclusive_write(path, data, InventoryError)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(data)


def snapshot(root: Path, output: Path, label: str, *, max_files: int = 1000,
             max_file_bytes: int = 8 * 1024 * 1024,
             max_total_bytes: int = 64 * 1024 * 1024,
             when: datetime | None = None, tree: bool = False,
             tree_depth: int = DEFAULT_TREE_DEPTH,
             exclude_directories: tuple[str, ...] | list[str] = ()) -> tuple[Path, dict]:
    options = dict(max_files=max_files, max_file_bytes=max_file_bytes,
                   max_total_bytes=max_total_bytes, when=when, tree=tree,
                   tree_depth=tree_depth, exclude_directories=exclude_directories)
    if os.name == 'nt':
        with _windows().boundaries(root, output, InventoryError) as (root, output):
            return _snapshot_impl(root, output, label, **options)
    return _snapshot_impl(root, output, label, **options)


def _snapshot_impl(root: Path, output: Path, label: str, *, max_files: int = 1000,
                   max_file_bytes: int = 8 * 1024 * 1024,
                   max_total_bytes: int = 64 * 1024 * 1024,
                   when: datetime | None = None, tree: bool = False,
                   tree_depth: int = DEFAULT_TREE_DEPTH,
                   exclude_directories: tuple[str, ...] | list[str] = ()) -> tuple[Path, dict]:
    _require(type(label) is str and re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,47}', label) is not None,
             'INVALID_LABEL')
    for value, ceiling in ((max_files, 10000), (max_file_bytes, 64 * 1024 * 1024),
                           (max_total_bytes, 256 * 1024 * 1024)):
        _require(type(value) is int and 0 < value <= ceiling, 'INVALID_LIMIT')
    _require(type(tree) is bool and type(tree_depth) is int and 1 <= tree_depth <= 64,
             'INVALID_TREE_OPTIONS')
    _require(tree or tree_depth == DEFAULT_TREE_DEPTH, 'TREE_REQUIRED')
    extra_exclusions = _additional_exclusions(exclude_directories)
    root, output = _directory(root), _directory(output)
    _require(root.parent != root, 'FILESYSTEM_ROOT_REJECTED')
    _require(not output.is_relative_to(root), 'OUTPUT_INSIDE_INPUT')
    directories: list[tuple[str, ...]] = []
    if tree or extra_exclusions:
        selected, skipped = _collect(root, max_files, max_file_bytes, max_total_bytes,
                                     observed_directories=directories if tree else None,
                                     extra_excluded_directories=extra_exclusions)
    else:
        selected, skipped = _collect(root, max_files, max_file_bytes, max_total_bytes)
    rows, top_levels, actual_total = [], {}, 0
    for path, info in selected:
        relative = path.relative_to(root).as_posix()
        digest = _sha256(path, info, max_file_bytes)
        actual_total += info.st_size
        _require(actual_total <= max_total_bytes, 'TOTAL_BYTE_LIMIT')
        encoded_path, escaped = _csv_path(relative)
        rows.append({'path': encoded_path, 'path_escaped': escaped, 'bytes': info.st_size,
                     'modified_utc': datetime.fromtimestamp(info.st_mtime, timezone.utc).isoformat(),
                     'sha256': digest, 'status': 'ok'})
        top = relative.split('/', 1)[0]
        top_levels[top] = top_levels.get(top, 0) + 1
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=(
        'path', 'path_escaped', 'bytes', 'modified_utc', 'sha256', 'status'))
    writer.writeheader()
    writer.writerows(rows)
    try:
        csv_bytes = buffer.getvalue().encode('utf-8')
    except UnicodeError:
        raise InventoryError('SOURCE_NAME_UNSUPPORTED') from None
    when = when or datetime.now(timezone.utc)
    summary = {'schema_version': 'outlands.source_inventory.v1', 'label': label,
               'created_at_utc': when.isoformat(), 'coverage': 'selected_regular_files_only',
               'file_count': len(rows), 'hashed_file_count': len(rows),
               'total_bytes': actual_total, 'top_level_counts': top_levels,
               'skipped': skipped, 'files_csv_sha256': hashlib.sha256(csv_bytes).hexdigest().upper(),
               'path_encoding': 'Remove one leading apostrophe only when path_escaped is true.',
               'limits': {'max_files': max_files, 'max_file_bytes': max_file_bytes,
                          'max_total_bytes': max_total_bytes, 'max_entries': MAX_ENTRIES},
               'default_excluded_directories': sorted(EXCLUDED_DIRECTORIES),
               'default_excluded_suffixes': sorted(EXCLUDED_SUFFIXES)}
    if extra_exclusions:
        summary['additional_excluded_directories'] = sorted(extra_exclusions)
    tree_bytes = None
    if tree:
        tree_bytes, tree_summary = _render_tree(
            [path.relative_to(root).parts for path, _ in selected], directories, tree_depth)
        summary['tree'] = tree_summary
    summary_bytes = (json.dumps(summary, indent=2, sort_keys=True) + '\n').encode('utf-8')
    _no_links(output)
    run = output / (when.strftime('%Y%m%dT%H%M%SZ') + '_' + label + '_' + secrets.token_hex(3))
    if os.name == 'nt':
        with _windows().new_directory(run, InventoryError):
            _exclusive_write(run / 'files.csv', csv_bytes)
            if tree_bytes is not None:
                _exclusive_write(run / 'tree.txt', tree_bytes)
            _exclusive_write(run / 'summary.json', summary_bytes)
        return run, summary
    try:
        run.mkdir(mode=0o700, exist_ok=False)
    except FileExistsError:
        raise InventoryError('OUTPUT_EXISTS') from None
    # A failure can leave this new partial run directory; it is never reported as success.
    _exclusive_write(run / 'files.csv', csv_bytes)
    if tree_bytes is not None:
        _exclusive_write(run / 'tree.txt', tree_bytes)
    _exclusive_write(run / 'summary.json', summary_bytes)
    return run, summary


class _Parser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise InventoryError('ARGUMENTS_INVALID')


def _argument_path(value: str):
    # Keep Windows spelling until the native backend validates it.
    return value if os.name == 'nt' else Path(value)


def main(argv: list[str] | None = None) -> int:
    try:
        parser = _Parser(description=__doc__, prog='source_inventory.py' if os.name == 'nt' else None)
        parser.add_argument('--root', type=_argument_path, required=True)
        parser.add_argument('--output-dir', type=_argument_path, required=True)
        parser.add_argument('--label', required=True)
        parser.add_argument('--max-files', type=int, default=1000)
        parser.add_argument('--max-file-bytes', type=int, default=8 * 1024 * 1024)
        parser.add_argument('--max-total-bytes', type=int, default=64 * 1024 * 1024)
        parser.add_argument('--tree', action='store_true', help='Also write a quoted relative tree.txt of the selected scope.')
        parser.add_argument('--tree-depth', type=int, default=None,
                            help='Display depth from 1 to 64; requires --tree (default: 16).')
        parser.add_argument('--exclude-dir', action='append', default=[],
                            help='Additional excluded directory basename; repeat up to 64 times.')
        args = parser.parse_args(argv)
        _require(args.tree or args.tree_depth is None, 'TREE_REQUIRED')
        run, summary = snapshot(args.root, args.output_dir, args.label,
                                max_files=args.max_files, max_file_bytes=args.max_file_bytes,
                                max_total_bytes=args.max_total_bytes, tree=args.tree,
                                tree_depth=DEFAULT_TREE_DEPTH if args.tree_depth is None else args.tree_depth,
                                exclude_directories=args.exclude_dir)
        print(json.dumps({'result': 'COMPLETE_WITH_EXCLUSIONS', 'snapshot': run.name,
                          'file_count': summary['file_count'], 'skipped': summary['skipped']}, sort_keys=True))
        return 0
    except KeyboardInterrupt:
        if os.name != 'nt':
            raise
        print(json.dumps({'result': 'INCOMPLETE', 'error': 'INTERRUPTED'}, sort_keys=True))
        return 130
    except InventoryError as error:
        print(json.dumps({'result': 'INCOMPLETE', 'error': str(error)}, sort_keys=True))
        return 2
    except (OSError, ValueError):
        print(json.dumps({'result': 'INCOMPLETE', 'error': 'IO_OR_METADATA_ERROR'}, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
