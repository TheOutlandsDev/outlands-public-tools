"""Original MIT read-only bounded image reader derived from this collection's GPT tool."""
from __future__ import annotations
import hashlib
import os
import stat
from inspection_support import identity, linked, local_path, no_links, require

MAX_IMAGE_BYTES = 16 * 1024**4
MAX_METADATA_BYTES = 512 * 1024


class ImageReader:
    """Stable ordinary-file descriptor; no devices, traversal or payload streaming."""
    def __init__(self, value):
        self.path = local_path(value); no_links(self.path); before = self.path.lstat()
        require(stat.S_ISREG(before.st_mode), 'REGULAR_FILE_REQUIRED')
        require(0 < before.st_size <= MAX_IMAGE_BYTES, 'IMAGE_SIZE_LIMIT')
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0)
        self.fd = os.open(self.path, flags)
        try:
            self.opened = os.fstat(self.fd)
            require(stat.S_ISREG(self.opened.st_mode) and not linked(self.opened), 'REGULAR_FILE_REQUIRED')
            require(identity(before) == identity(self.opened), 'INPUT_CHANGED')
        except BaseException:
            os.close(self.fd); raise
        self.size = self.opened.st_size; self.bytes_read = 0; self.regions = []

    def read_at(self, offset, length, label):
        require(type(offset) is int and type(length) is int and offset >= 0 and length > 0
                and offset + length <= self.size, 'METADATA_RANGE_INVALID')
        require(self.bytes_read + length <= MAX_METADATA_BYTES, 'METADATA_BYTE_LIMIT')
        os.lseek(self.fd, offset, os.SEEK_SET); data = bytearray()
        while len(data) < length:
            chunk = os.read(self.fd, min(65536, length-len(data)))
            require(bool(chunk), 'INPUT_CHANGED'); data.extend(chunk)
        self.bytes_read += length
        self.regions.append({'id': label, 'offset_bytes': offset, 'bytes': length,
                             'sha256': hashlib.sha256(data).hexdigest()})
        return bytes(data)

    def __enter__(self): return self

    def __exit__(self, kind, value, traceback):
        try:
            after = os.fstat(self.fd); no_links(self.path)
            require(identity(self.opened) == identity(after) == identity(self.path.lstat())
                    and self.opened.st_ctime_ns == after.st_ctime_ns, 'INPUT_CHANGED')
        finally: os.close(self.fd)
