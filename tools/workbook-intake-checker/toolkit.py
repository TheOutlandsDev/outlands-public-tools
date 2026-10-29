"""Bounded buffer parsing and checked, explicit Windows/POSIX file operations."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import xml.etree.ElementTree as ET

MAX_INPUT = 4 * 1024 * 1024
MAX_OUTPUT = 8 * 1024 * 1024


class Rejected(ValueError):
    """Fixed diagnostic codes; never retain supplied values in error messages."""


def require(condition, code):
    if not condition:
        raise Rejected(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    try:
        raw = json.dumps(value, ensure_ascii=True, allow_nan=False,
                         sort_keys=True, separators=(',', ':')).encode('ascii')
    except (ValueError, TypeError, RecursionError):
        raise Rejected('OUTPUT_INVALID') from None
    require(len(raw) + 1 <= MAX_OUTPUT, 'OUTPUT_LIMIT')
    return raw + b'\n'


def decode(raw):
    require(type(raw) is bytes and len(raw) <= MAX_INPUT, 'INPUT_LIMIT')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'JSON_DUPLICATE_KEY')
            result[key] = value
        return result
    def number(_value):
        raise Rejected('JSON_INTEGER_OR_STRING_REQUIRED')
    try:
        value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs,
                           parse_float=number, parse_constant=number)
        pending = [(value, 0)]
        nodes = 0
        while pending:
            item, depth = pending.pop()
            nodes += 1
            require(depth <= 32 and nodes <= 100000, 'JSON_STRUCTURE_LIMIT')
            if type(item) is dict:
                pending.extend((key, depth + 1) for key in item)
                pending.extend((v, depth + 1) for v in item.values())
            elif type(item) is list:
                pending.extend((v, depth + 1) for v in item)
            elif type(item) is str:
                require(len(item) <= 4096, 'JSON_TEXT_LIMIT')
                item.encode('utf-8')
            elif type(item) is int:
                require(abs(item) <= 10**18, 'JSON_INTEGER_LIMIT')
        return value
    except Rejected:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise Rejected('JSON_INVALID') from None


def fields(value, names):
    require(type(value) is dict and set(value) == set(names), 'FIELDS_INVALID')


def identifier(value):
    require(type(value) is str and re.fullmatch(r'[a-z][a-z0-9_-]{0,47}', value),
            'IDENTIFIER_INVALID')
    return value


def sha(value):
    require(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value), 'HASH_INVALID')
    return value


def integer(value, maximum=10**12, minimum=0):
    require(type(value) is int and minimum <= value <= maximum, 'INTEGER_INVALID')
    return value


class XMLBuilder(ET.TreeBuilder):
    def __init__(self):
        super().__init__()
        self.depth = self.nodes = self.chars = 0

    def start(self, tag, attrs):
        self.depth += 1
        self.nodes += 1
        require(self.depth <= 32 and self.nodes <= 50000, 'XML_STRUCTURE_LIMIT')
        require(len(tag) <= 256 and len(attrs) <= 32, 'XML_STRUCTURE_LIMIT')
        for key, value in attrs.items():
            self.chars += len(key) + len(value)
        require(self.chars <= 2 * 1024 * 1024, 'XML_TEXT_LIMIT')
        return super().start(tag, attrs)

    def end(self, tag):
        self.depth -= 1
        return super().end(tag)

    def data(self, data):
        self.chars += len(data)
        require(self.chars <= 2 * 1024 * 1024, 'XML_TEXT_LIMIT')
        return super().data(data)

    def doctype(self, *args):
        raise Rejected('XML_DECLARATION_FORBIDDEN')

    def pi(self, *args):
        raise Rejected('XML_PROCESSING_INSTRUCTION_FORBIDDEN')

    def comment(self, *args):
        raise Rejected('XML_COMMENT_FORBIDDEN')


def xml(raw):
    require(type(raw) is bytes and len(raw) <= MAX_INPUT, 'INPUT_LIMIT')
    try:
        return ET.fromstring(raw, parser=ET.XMLParser(target=XMLBuilder()))
    except (ET.ParseError, UnicodeError, ValueError, RecursionError) as error:
        if isinstance(error, Rejected):
            raise
        raise Rejected('XML_INVALID') from None


def _path(value):
    raw = os.fspath(value)
    require(type(raw) is str and 0 < len(raw) <= 4096 and '\x00' not in raw,
            'PATH_INVALID')
    require('..' not in Path(raw).parts, 'PATH_INVALID')
    selected = Path(os.path.abspath(raw))
    require(len(selected.parts) <= 64, 'PATH_INVALID')
    return selected


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


@contextmanager
def _parent(path):
    require(hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY'), 'PLATFORM_UNSUPPORTED')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    handles = []
    try:
        fd = os.open(path.anchor, flags)
        handles.append((fd, None, None, os.fstat(fd)))
        for part in path.parent.parts[1:]:
            parent = fd
            expected = os.stat(part, dir_fd=parent, follow_symlinks=False)
            require(stat.S_ISDIR(expected.st_mode), 'PARENT_UNSAFE')
            fd = os.open(part, flags, dir_fd=parent)
            actual = os.fstat(fd)
            require((actual.st_dev, actual.st_ino) == (expected.st_dev, expected.st_ino),
                    'PARENT_CHANGED')
            handles.append((fd, parent, part, actual))
        def verify():
            for owned, parent, name, expected in handles:
                actual = os.fstat(owned)
                require((actual.st_dev, actual.st_ino) == (expected.st_dev, expected.st_ino),
                        'PARENT_CHANGED')
                if parent is not None:
                    actual = os.stat(name, dir_fd=parent, follow_symlinks=False)
                    require(stat.S_ISDIR(actual.st_mode) and
                            (actual.st_dev, actual.st_ino) == (expected.st_dev, expected.st_ino),
                            'PARENT_CHANGED')
        verify()
        yield fd, verify, handles
        verify()
    finally:
        for fd, *_ in reversed(handles):
            os.close(fd)


def read(value, maximum=MAX_INPUT):
    integer(maximum, MAX_INPUT, 1)
    if os.name == 'nt':
        import native_windows
        return native_windows.read_bounded(value, maximum, Rejected, single_link=True)
    path = _path(value)
    with _parent(path) as (parent, verify, _):
        expected = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        require(stat.S_ISREG(expected.st_mode) and expected.st_nlink == 1, 'INPUT_UNSAFE')
        require(expected.st_size <= maximum, 'INPUT_LIMIT')
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            before = os.fstat(fd)
            require(_identity(before) == _identity(expected), 'INPUT_CHANGED')
            chunks, count = [], 0
            while True:
                block = os.read(fd, min(65536, maximum + 1 - count))
                if not block:
                    break
                count += len(block)
                require(count <= maximum, 'INPUT_LIMIT')
                chunks.append(block)
            after = os.fstat(fd)
            named = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            require(count == before.st_size and _identity(before) == _identity(after) ==
                    _identity(named) and after.st_nlink == 1, 'INPUT_CHANGED')
            verify()
            return b''.join(chunks)
        finally:
            os.close(fd)


def source_root():
    here = Path(__file__).absolute().parent
    return next((p for p in [here, *here.parents] if (p / '.git').exists() or
                 ((p / 'tools').is_dir() and (p / 'systems').is_dir() and
                  (p / 'catalog/registry.json').is_file())), here)


def write_new(value, raw):
    require(type(raw) is bytes and len(raw) <= MAX_OUTPUT, 'OUTPUT_LIMIT')
    if os.name == 'nt':
        import native_windows
        with native_windows.output_scope(value, source_root(), Rejected) as path:
            native_windows.exclusive_write(path, raw, Rejected)
        return
    path, protected = _path(value), source_root()
    require(not path.is_relative_to(protected), 'OUTPUT_INSIDE_SOURCE')
    with _parent(path) as (parent, verify, handles):
        info = protected.lstat()
        require(all((v.st_dev, v.st_ino) != (info.st_dev, info.st_ino)
                    for *_, v in handles), 'OUTPUT_INSIDE_SOURCE')
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        try:
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'OUTPUT_UNSAFE')
            position = 0
            while position < len(raw):
                count = os.write(fd, raw[position:position + 65536])
                require(count > 0, 'OUTPUT_IO_ERROR')
                position += count
            os.fsync(fd)
            after = os.fstat(fd)
            named = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            require(_identity(after) == _identity(named) and after.st_size == len(raw) and
                    after.st_nlink == 1 and (before.st_dev, before.st_ino) ==
                    (after.st_dev, after.st_ino), 'OUTPUT_CHANGED')
            verify()
        finally:
            os.close(fd)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Rejected('ARGUMENTS_INVALID')


def bindings(pairs):
    require(len(pairs) <= 16, 'BINDING_LIMIT')
    selected = {}
    for key, path in pairs:
        identifier(key)
        require(key not in selected, 'DUPLICATE_BINDING')
        selected[key] = path
    return selected


def buffers(selected):
    result, total = {}, 0
    for key, path in selected.items():
        result[key] = read(path)
        total += len(result[key])
        require(total <= 16 * 1024 * 1024, 'TOTAL_INPUT_LIMIT')
    return result


def run(parser, operation, argv=None):
    try:
        args = parser.parse_args(argv)
        result = operation(args)
        raw = encode(result)
        if args.out is not None:
            write_new(args.out, raw)
            print(json.dumps({'status': result['status'], 'report_written': True}))
        else:
            sys.stdout.write(raw.decode('ascii'))
        return 0 if result['status'] in {'PASS', 'MATCH'} else 1
    except KeyboardInterrupt:
        print('{"status":"ERROR","code":"INTERRUPTED"}')
        return 130
    except Rejected as error:
        print(json.dumps({'status': 'ERROR', 'code': str(error)}))
        return 2
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        print('{"status":"ERROR","code":"INPUT_OR_OUTPUT_REFUSED"}')
        return 2
