"""Inspect selected Android sparse-image metadata; never reconstruct an image. MIT."""
from __future__ import annotations
import json
import struct
from binary_reader import ImageReader, MAX_IMAGE_BYTES
from inspection_support import Parser, TextError, bounded_append, cli_error, finish, require, write_report

MAGIC = 0xED26FF3A
MAX_CHUNKS = 4000
MAX_BLOCK_BYTES = 1024 * 1024
KINDS = {0xCAC1: 'RAW', 0xCAC2: 'FILL', 0xCAC3: 'DONT_CARE', 0xCAC4: 'CRC32'}


def inspect(reader):
    report = {'schema_version': 1, 'tool': 'Android Sparse Image Inspector',
              'scope': 'One selected sparse file; structural metadata only, not a merged sparsechunk set.',
              'image_bytes': reader.size, 'whole_image_hashed': False, 'payload_crc_checked': False,
              'layout_walk_complete': False, 'header': None, 'chunks': [], 'findings': [], 'coverage_issues': []}

    def flag(code, chunk=None, coverage=False):
        bounded_append(report['coverage_issues' if coverage else 'findings'], {'code': code, 'chunk_index': chunk})

    def done():
        report['metadata_bytes_read'] = reader.bytes_read
        report['metadata_regions'] = reader.regions
        return finish(report)

    if reader.size < 28:
        flag('SPARSE_HEADER_TRUNCATED')
        return done()
    fields = struct.unpack('<IHHHHIIII', reader.read_at(0, 28, 'file-header'))
    magic, major, minor, header_bytes, chunk_header_bytes, block_bytes, total_blocks, total_chunks, checksum = fields
    if magic != MAGIC:
        flag('SPARSE_SIGNATURE_MISMATCH')
        return done()
    report['header'] = {'major_version': major, 'minor_version': minor,
                        'header_bytes': header_bytes, 'chunk_header_bytes': chunk_header_bytes,
                        'block_bytes': block_bytes, 'declared_output_blocks': total_blocks,
                        'declared_chunk_count': total_chunks,
                        'declared_output_bytes': str(total_blocks * block_bytes),
                        'image_checksum_declared': checksum != 0}
    if major != 1:
        flag('SPARSE_MAJOR_VERSION_UNSUPPORTED', coverage=True)
        return done()
    if header_bytes < 28 or chunk_header_bytes < 12:
        flag('SPARSE_HEADER_SIZE_INVALID')
        return done()
    if header_bytes > reader.size:
        flag('SPARSE_HEADER_TRUNCATED')
        return done()
    if block_bytes == 0 or block_bytes % 4:
        flag('SPARSE_BLOCK_SIZE_INVALID')
        return done()
    require(block_bytes <= MAX_BLOCK_BYTES, 'BLOCK_SIZE_LIMIT')
    require(total_blocks * block_bytes <= MAX_IMAGE_BYTES, 'DECLARED_OUTPUT_SIZE_LIMIT')
    require(total_chunks <= MAX_CHUNKS, 'CHUNK_COUNT_LIMIT')
    if minor != 0:
        flag('SPARSE_MINOR_VERSION_UNINSPECTED', coverage=True)
    if header_bytes > 28:
        flag('FILE_HEADER_EXTENSION_UNINSPECTED', coverage=True)
    if chunk_header_bytes > 12:
        flag('CHUNK_HEADER_EXTENSION_UNINSPECTED', coverage=True)
    if checksum:
        flag('IMAGE_CHECKSUM_UNVERIFIED', coverage=True)
    offset = header_bytes
    output_blocks = 0
    for index in range(1, total_chunks + 1):
        if offset + chunk_header_bytes > reader.size:
            flag('CHUNK_HEADER_TRUNCATED', index)
            return done()
        kind, reserved, blocks, total_size = struct.unpack('<HHII', reader.read_at(offset, 12, 'chunk-'+str(index)))
        row = {'index': index, 'kind': KINDS.get(kind, 'UNKNOWN'), 'type_hex': f'0x{kind:04x}',
               'input_offset': offset, 'input_bytes': total_size,
               'declared_output_blocks': blocks, 'output_start_block': output_blocks}
        bounded_append(report['chunks'], row)
        if reserved:
            flag('CHUNK_RESERVED_NONZERO', index)
        if total_size < chunk_header_bytes:
            flag('CHUNK_SIZE_BELOW_HEADER', index)
            return done()
        if offset + total_size > reader.size:
            flag('CHUNK_DATA_TRUNCATED', index)
            return done()
        body_size = total_size - chunk_header_bytes
        if kind not in KINDS:
            flag('CHUNK_TYPE_UNSUPPORTED', index, coverage=True)
            return done()
        expected = blocks * block_bytes if kind == 0xCAC1 else 4 if kind in (0xCAC2, 0xCAC4) else 0
        if body_size != expected:
            flag('CHUNK_PAYLOAD_SIZE_MISMATCH', index)
        if kind == 0xCAC4:
            flag('CRC32_UNVERIFIED', index, coverage=True)
            if blocks:
                flag('CRC32_OUTPUT_BLOCKS_NONZERO', index)
        else:
            output_blocks += blocks
        if output_blocks > total_blocks:
            flag('OUTPUT_BLOCK_COUNT_EXCEEDED', index)
        offset += total_size
    report['layout_walk_complete'] = True
    report['observed_output_blocks'] = output_blocks
    report['accounted_input_bytes'] = offset
    if output_blocks != total_blocks:
        flag('OUTPUT_BLOCK_COUNT_MISMATCH')
    if offset != reader.size:
        flag('TRAILING_INPUT_BYTES')
    return done()


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', required=True)
    try:
        args = parser.parse_args(argv)
        with ImageReader(args.image) as reader:
            report = inspect(reader)
        write_report(report, args.output, [args.image])
        print(json.dumps({'status': report['status'], 'metadata_bytes_read': report['metadata_bytes_read'],
                          'findings': len(report['findings']), 'coverage_issues': len(report['coverage_issues'])}, sort_keys=True))
        return int(report['status'] != 'NO_SCOPE_FINDINGS')
    except (TextError, OSError, ValueError, RecursionError) as error:
        return cli_error(error)


if __name__ == '__main__':
    raise SystemExit(main())
