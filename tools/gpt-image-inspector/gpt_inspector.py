"""Inspect bounded GPT metadata in one regular raw image; never open a device. MIT."""
from __future__ import annotations
import hashlib
import json
import os
import stat
import struct
import unicodedata
import uuid
import zlib
from inspection_support import (Parser, TextError, bounded_append, cli_error, finish,
                                identity, linked, local_path, no_links,
                                require, write_report)

MAX_IMAGE_BYTES = 16 * 1024**4
MAX_METADATA_BYTES = 2 * 1024**2
MAX_TABLE_ENTRIES = 4096


def issue(rows, code, region, index):
    row = {'code': code, 'region': region, 'entry_index': index or None}
    if row not in rows: bounded_append(rows, row)


class ImageReader:
    """Read-only stable descriptor with strict range and total-read budgets."""
    def __init__(self, value):
        self.path = local_path(value); no_links(self.path); self.before = self.path.lstat()
        require(stat.S_ISREG(self.before.st_mode), 'REGULAR_FILE_REQUIRED')
        require(0 < self.before.st_size <= MAX_IMAGE_BYTES, 'IMAGE_SIZE_LIMIT')
        self.fd = os.open(self.path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NONBLOCK', 0))
        try:
            self.opened = os.fstat(self.fd)
            require(stat.S_ISREG(self.opened.st_mode) and not linked(self.opened), 'REGULAR_FILE_REQUIRED')
            require(identity(self.opened) == identity(self.before), 'INPUT_CHANGED')
        except BaseException:
            os.close(self.fd); raise
        self.size = self.opened.st_size; self.bytes_read = 0; self.regions = []

    def read_at(self, offset, length, label):
        require(type(offset) is int and type(length) is int and offset >= 0 and length > 0 and offset + length <= self.size, 'METADATA_RANGE_INVALID')
        require(self.bytes_read + length <= MAX_METADATA_BYTES, 'METADATA_BYTE_LIMIT')
        os.lseek(self.fd, offset, os.SEEK_SET); data = bytearray()
        while len(data) < length:
            chunk = os.read(self.fd, min(65536, length-len(data)))
            require(bool(chunk), 'INPUT_CHANGED'); data.extend(chunk)
        self.bytes_read += len(data)
        self.regions.append({'id': label, 'offset': offset, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        return bytes(data)

    def __enter__(self): return self

    def __exit__(self, kind, value, traceback):
        try:
            after = os.fstat(self.fd); no_links(self.path)
            require(identity(self.opened) == identity(after) == identity(self.path.lstat())
                    and self.opened.st_ctime_ns == after.st_ctime_ns, 'INPUT_CHANGED')
        finally: os.close(self.fd)


def protective_mbr(data, last_lba, report):
    if data[510:512] != b'\x55\xaa': issue(report['findings'], 'MBR_SIGNATURE_MISMATCH', 'mbr', 0)
    entries = [data[446+i*16:462+i*16] for i in range(4)]
    protective = [entry for entry in entries if entry[4] == 0xee]
    if len(protective) != 1: issue(report['findings'], 'PROTECTIVE_MBR_ENTRY_COUNT', 'mbr', 0)
    if any(entry[4] not in {0, 0xee} for entry in entries): issue(report['findings'], 'HYBRID_MBR_DECLARED', 'mbr', 0)
    for entry in protective:
        start, count = struct.unpack_from('<II', entry, 8)
        if start != 1 or count != min(last_lba, 0xffffffff): issue(report['findings'], 'PROTECTIVE_MBR_RANGE_MISMATCH', 'mbr', 0)


def read_header(reader, role, lba, sector, report, details):
    data = reader.read_at(lba*sector, sector, role+'-header')
    result = {'role': role, 'header_lba': lba, 'table_inspected': False, 'partitions': []}
    report['headers'].append(result)
    def flag(code): issue(report['findings'], code, role, 0)
    if data[:8] != b'EFI PART': flag('GPT_SIGNATURE_MISMATCH'); return None
    revision, size, crc, reserved = struct.unpack_from('<IIII', data, 8)
    if revision != 0x00010000:
        issue(report['coverage_issues'], 'GPT_REVISION_UNSUPPORTED', role, 0); return None
    if not 92 <= size <= sector: flag('GPT_HEADER_SIZE_INVALID'); return None
    if reserved: flag('GPT_RESERVED_FIELD_NONZERO')
    crc_data = bytearray(data[:size]); crc_data[16:20] = b'\0'*4
    result['header_crc_matches'] = zlib.crc32(crc_data) == crc
    if not result['header_crc_matches']: flag('GPT_HEADER_CRC_MISMATCH')
    current, backup, first, last = struct.unpack_from('<QQQQ', data, 24)
    disk_guid = data[56:72]
    table_lba, count, entry_size, table_crc = struct.unpack_from('<QIII', data, 72)
    image_last = reader.size//sector-1
    result.update(first_usable_lba=first, last_usable_lba=last, declared_entry_count=count, declared_entry_size=entry_size)
    if details: result['disk_guid'] = str(uuid.UUID(bytes_le=disk_guid))
    if disk_guid == b'\0'*16: flag('ZERO_DISK_GUID')
    if current != lba or backup != (image_last if role=='primary' else 1): flag('GPT_HEADER_LOCATION_MISMATCH')
    if not 2 <= first <= last < image_last: flag('GPT_USABLE_RANGE_INVALID'); return None
    if entry_size != 128:
        issue(report['coverage_issues'], 'GPT_ENTRY_SIZE_UNSUPPORTED', role, 0); return None
    require(1 <= count <= MAX_TABLE_ENTRIES, 'GPT_ENTRY_COUNT_LIMIT')
    length = count*entry_size; table_sectors = (length+sector-1)//sector
    table_end = table_lba + table_sectors - 1
    safe = (2 <= table_lba <= table_end < first) if role=='primary' else (last < table_lba <= table_end < image_last)
    if not safe: flag('GPT_TABLE_RANGE_INVALID'); return None
    if (first-2)*sector < 16384 or (image_last-last-1)*sector < 16384:
        flag('GPT_TABLE_RESERVATION_TOO_SMALL')
    if any(data[92:size]): issue(report['coverage_issues'], 'GPT_HEADER_EXTENSION_UNINSPECTED', role, 0)
    if any(data[size:]): flag('GPT_HEADER_PADDING_NONZERO')
    table = reader.read_at(table_lba*sector, length, role+'-entries')
    result['table_inspected'] = True; result['table_crc_matches'] = zlib.crc32(table)==table_crc
    if not result['table_crc_matches']: flag('GPT_TABLE_CRC_MISMATCH')
    intervals = []; guids = {}
    for index in range(count):
        entry = table[index*128:(index+1)*128]
        if entry[:16] == b'\0'*16:
            if any(entry[16:]): issue(report['findings'], 'NONZERO_UNUSED_ENTRY_DATA', role, index+1)
            continue
        start, end, attributes = struct.unpack_from('<QQQ', entry, 32)
        row = {'index': index+1, 'first_lba': start, 'last_lba': end,
               'sectors': end-start+1 if end>=start else None, 'attributes_hex': f'0x{attributes:016x}'}
        name = None
        try:
            decoded = entry[56:128].decode('utf-16-le', errors='strict'); name, _, padding = decoded.partition('\0')
            if any(c != '\0' for c in padding): issue(report['findings'], 'PARTITION_NAME_PADDING_NONZERO', role, index+1)
            if any(unicodedata.category(c).startswith('C') for c in name):
                issue(report['findings'], 'PARTITION_NAME_CONTROL', role, index+1); name = None
        except UnicodeError: issue(report['findings'], 'PARTITION_NAME_ENCODING_INVALID', role, index+1)
        guid = entry[16:32]
        if guid == b'\0'*16: issue(report['findings'], 'ZERO_PARTITION_GUID', role, index+1)
        elif guid in guids: issue(report['findings'], 'DUPLICATE_PARTITION_GUID', role, index+1)
        guids[guid] = index+1
        if details: row.update(name=name, unique_guid=str(uuid.UUID(bytes_le=guid)), type_guid=str(uuid.UUID(bytes_le=entry[:16])))
        if start > end or start < first or end > last:
            issue(report['findings'], 'PARTITION_RANGE_INVALID', role, index+1)
        else: intervals.append((start, end, index+1))
        bounded_append(result['partitions'], row)
    furthest = None
    for item in sorted(intervals):
        if furthest and item[0] <= furthest[1]:
            issue(report['findings'], 'PARTITION_OVERLAP_OBSERVED', role, item[2])
        if furthest is None or item[1] > furthest[1]: furthest = item
    return {'disk_guid': disk_guid, 'first': first, 'last': last, 'count': count,
            'entry_size': entry_size, 'table': table}


def inspect(reader, sector, details=False):
    require(type(sector) is int and sector in {512,4096}, 'SECTOR_SIZE_UNSUPPORTED')
    require(reader.size >= 4*sector and reader.size%sector == 0, 'IMAGE_ALIGNMENT_INVALID')
    report = {'schema_version': 1, 'tool': 'Offline GPT Disk Image Inspector',
              'scope': 'Full regular raw image, explicit sector size; GPT metadata observations only.',
              'details_included': details, 'image_bytes': reader.size, 'sector_size': sector,
              'whole_image_hashed': False, 'headers': [], 'findings': [], 'coverage_issues': []}
    protective_mbr(reader.read_at(0, 512, 'mbr'), reader.size//sector-1, report)
    primary = read_header(reader, 'primary', 1, sector, report, details)
    backup = read_header(reader, 'backup', reader.size//sector-1, sector, report, details)
    report['primary_backup_metadata_compared'] = primary is not None and backup is not None
    if primary is not None and backup is not None:
        for key in ('disk_guid','first','last','count','entry_size','table'):
            if primary[key] != backup[key]: issue(report['findings'], 'PRIMARY_BACKUP_METADATA_MISMATCH', 'comparison', 0)
    report['metadata_bytes_read'] = reader.bytes_read; report['metadata_regions'] = reader.regions
    return finish(report)


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--image', required=True)
    parser.add_argument('--sector-size', type=int, choices=(512,4096), required=True)
    parser.add_argument('--output', required=True); parser.add_argument('--include-details', action='store_true')
    try:
        args = parser.parse_args(argv)
        with ImageReader(args.image) as reader: report = inspect(reader, args.sector_size, args.include_details)
        write_report(report, args.output, [args.image])
        print(json.dumps({'status': report['status'], 'metadata_bytes_read': report['metadata_bytes_read'],
                          'findings': len(report['findings']), 'coverage_issues': len(report['coverage_issues'])}, sort_keys=True))
        return int(report['status']!='NO_SCOPE_FINDINGS')
    except (TextError, OSError, ValueError, RecursionError) as error: return cli_error(error)


if __name__=='__main__': raise SystemExit(main())
