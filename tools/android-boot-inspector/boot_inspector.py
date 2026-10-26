"""Inspect supported Android boot/vendor_boot v3/v4 metadata in one ordinary file. MIT."""
from __future__ import annotations
import json
import struct
from binary_reader import ImageReader
from inspection_support import Parser, TextError, bounded_append, cli_error, finish, require, write_report

MAX_TABLE_ENTRIES = 2048
TABLE_ENTRY_BYTES = 108


def flag(report, code, region, index=None, coverage=False):
    rows = report['coverage_issues'] if coverage else report['findings']
    row = {'code': code, 'region': region, 'entry_index': index}
    if row not in rows: bounded_append(rows, row)


def aligned(size, page): return ((size + page - 1) // page) * page


def header(reader, report, length):
    if reader.size < length:
        flag(report, 'HEADER_TRUNCATED', 'header'); return None
    return reader.read_at(0, length, 'header')


def sections(reader, report, page, sizes):
    cursor = 0
    for role, size in sizes:
        end = cursor + size; padded = cursor + aligned(size, page)
        within = end <= reader.size
        bounded_append(report['sections'], {'role': role, 'offset_bytes': cursor,
                       'declared_bytes': size, 'padded_end_bytes': padded, 'within_file': within})
        if not within: flag(report, 'SECTION_OUTSIDE_FILE', role)
        elif padded > reader.size: flag(report, 'SECTION_PADDING_TRUNCATED', role)
        cursor = padded
    report['declared_padded_layout_bytes'] = cursor
    report['trailing_bytes'] = max(0, reader.size-cursor)
    if reader.size > cursor:
        flag(report, 'TRAILING_BYTES_UNINSPECTED', 'tail', coverage=True)


def boot(reader, report):
    prefix = header(reader, report, 44)
    if prefix is None: return
    version = struct.unpack_from('<I', prefix, 40)[0]
    report.update(image_kind='boot', header_version=version)
    if version not in (3, 4):
        flag(report, 'HEADER_VERSION_UNSUPPORTED', 'header', coverage=True); return
    expected = 1580 if version == 3 else 1584
    data = header(reader, report, expected)
    if data is None: return
    kernel, ramdisk, _os, declared = struct.unpack_from('<IIII', data, 8)
    report.update(header_bytes=declared, page_size=4096)
    if declared != expected:
        flag(report, 'HEADER_SIZE_UNSUPPORTED' if declared > expected else 'HEADER_SIZE_INVALID',
             'header', coverage=declared > expected); return
    if any(data[24:40]): flag(report, 'RESERVED_HEADER_NONZERO', 'header')
    signature = struct.unpack_from('<I', data, 1580)[0] if version == 4 else 0
    sizes = [('header', declared), ('kernel', kernel), ('ramdisk', ramdisk)]
    if version == 4: sizes.append(('boot_signature', signature))
    sections(reader, report, 4096, sizes)


def vendor_table(reader, report, table_section, count, stride, ramdisk_bytes):
    require(count <= MAX_TABLE_ENTRIES, 'TABLE_ENTRY_LIMIT')
    size = table_section['declared_bytes']
    if count * stride != size:
        flag(report, 'TABLE_LENGTH_MISMATCH', 'ramdisk_table'); return
    if count == 0:
        if ramdisk_bytes: flag(report, 'FRAGMENT_COVERAGE_MISMATCH', 'ramdisk_table')
        return
    if stride != TABLE_ENTRY_BYTES:
        flag(report, 'TABLE_ENTRY_SIZE_UNSUPPORTED', 'ramdisk_table', coverage=True); return
    if not table_section['within_file']: return
    data = reader.read_at(table_section['offset_bytes'], size, 'ramdisk-table')
    report['ramdisk_table_inspected'] = True
    intervals = []
    for index in range(count):
        length, start, kind = struct.unpack_from('<III', data, index*stride)
        end = start + length
        within = end <= ramdisk_bytes
        bounded_append(report['ramdisk_fragments'], {'index': index+1, 'offset_bytes': start,
                       'declared_bytes': length, 'type': kind, 'within_ramdisk_section': within})
        if kind not in (0, 1, 2, 3):
            flag(report, 'FRAGMENT_TYPE_UNSUPPORTED', 'ramdisk_table', index+1, coverage=True)
        if not within: flag(report, 'FRAGMENT_OUTSIDE_RAMDISK_SECTION', 'ramdisk_table', index+1)
        elif length: intervals.append((start, end, index+1))
    cursor = 0
    for start, end, index in sorted(intervals):
        if start < cursor: flag(report, 'FRAGMENT_OVERLAP_OBSERVED', 'ramdisk_table', index)
        if start > cursor: flag(report, 'FRAGMENT_GAP_OBSERVED', 'ramdisk_table', index)
        cursor = max(cursor, end)
    if cursor != ramdisk_bytes:
        flag(report, 'FRAGMENT_COVERAGE_MISMATCH', 'ramdisk_table')


def vendor(reader, report):
    prefix = header(reader, report, 12)
    if prefix is None: return
    version = struct.unpack_from('<I', prefix, 8)[0]
    report.update(image_kind='vendor_boot', header_version=version)
    if version not in (3, 4):
        flag(report, 'HEADER_VERSION_UNSUPPORTED', 'header', coverage=True); return
    expected = 2112 if version == 3 else 2128
    data = header(reader, report, expected)
    if data is None: return
    page = struct.unpack_from('<I', data, 12)[0]
    ramdisk = struct.unpack_from('<I', data, 24)[0]
    declared, dtb = struct.unpack_from('<II', data, 2096)
    report.update(header_bytes=declared, page_size=page)
    if declared != expected:
        flag(report, 'HEADER_SIZE_UNSUPPORTED' if declared > expected else 'HEADER_SIZE_INVALID',
             'header', coverage=declared > expected); return
    if page == 0:
        flag(report, 'PAGE_SIZE_INVALID', 'header'); return
    if not 512 <= page <= 65536 or page & (page-1):
        flag(report, 'PAGE_SIZE_UNSUPPORTED', 'header', coverage=True); return
    sizes = [('header', declared), ('vendor_ramdisk', ramdisk), ('dtb', dtb)]
    if version == 4:
        table_bytes, count, stride, bootconfig = struct.unpack_from('<IIII', data, 2112)
        report.update(table_declared_entries=count, table_entry_bytes=stride)
        sizes += [('ramdisk_table', table_bytes), ('bootconfig', bootconfig)]
    sections(reader, report, page, sizes)
    if version == 4:
        vendor_table(reader, report, report['sections'][3], count, stride, ramdisk)


def inspect(reader):
    report = {'schema_version': 1, 'tool': 'Boot / Vendor Boot Header Inspector',
              'scope': 'Single regular boot or vendor_boot image; declared v3/v4 layout and table extents only.',
              'image_bytes': reader.size, 'image_kind': 'unknown', 'sections': [],
              'ramdisk_fragments': [], 'ramdisk_table_inspected': False,
              'whole_image_hashed': False, 'payloads_inspected': False,
              'strings_and_hardware_identifiers_included': False,
              'findings': [], 'coverage_issues': []}
    magic = header(reader, report, 8)
    if magic == b'ANDROID!': boot(reader, report)
    elif magic == b'VNDRBOOT': vendor(reader, report)
    elif magic is not None: flag(report, 'IMAGE_MAGIC_UNRECOGNIZED', 'header')
    report.update(metadata_bytes_read=reader.bytes_read, metadata_regions=reader.regions)
    return finish(report)


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--image', required=True); parser.add_argument('--output', required=True)
    try:
        args = parser.parse_args(argv)
        with ImageReader(args.image) as reader: report = inspect(reader)
        write_report(report, args.output, [args.image])
        print(json.dumps({'status': report['status'], 'metadata_bytes_read': report['metadata_bytes_read'],
                          'findings': len(report['findings']), 'coverage_issues': len(report['coverage_issues'])}, sort_keys=True))
        return int(report['status'] != 'NO_SCOPE_FINDINGS')
    except (TextError, OSError, ValueError, RecursionError) as error: return cli_error(error)


if __name__ == '__main__': raise SystemExit(main())
