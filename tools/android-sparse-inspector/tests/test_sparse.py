"""Synthetic sparse bytes and actual CLI tests; no firmware/device inputs."""
from pathlib import Path
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import binary_reader
import sparse_inspector as tool
from inspection_support import TextError


def header(blocks=1, chunks=1, block=4, **changes):
    values = dict(magic=0xED26FF3A, major=1, minor=0, header=28, chunk_header=12,
                  block=block, blocks=blocks, chunks=chunks, checksum=0)
    values.update(changes)
    return struct.pack('<IHHHHIIII', *(values[key] for key in
                       ('magic','major','minor','header','chunk_header','block','blocks','chunks','checksum')))


def chunk(kind=0xCAC1, blocks=1, body=b'demo', reserved=0, size=None, extension=b''):
    return struct.pack('<HHII', kind, reserved, blocks, 12+len(extension)+len(body) if size is None else size) + extension + body


class SparseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.input = self.base/'image.sparse'

    def inspect(self, data):
        self.input.write_bytes(data)
        with binary_reader.ImageReader(self.input) as reader:
            result = tool.inspect(reader)
        self.assertEqual(self.input.read_bytes(), data)
        return result

    def codes(self, report, coverage=False):
        return {row['code'] for row in report['coverage_issues' if coverage else 'findings']}

    def test_raw_valid_without_reading_payload(self):
        report = self.inspect(header()+chunk())
        self.assertEqual(report['status'], 'NO_SCOPE_FINDINGS')
        self.assertTrue(report['layout_walk_complete'])
        self.assertEqual(report['header']['declared_output_bytes'], '4')
        self.assertEqual(report['metadata_bytes_read'], 40)
        self.assertEqual(report['metadata_regions'][1]['sha256'], hashlib.sha256(chunk()[:12]).hexdigest())
        self.assertFalse(report['whole_image_hashed'])
        self.assertFalse(report['payload_crc_checked'])
        self.assertNotIn('demo', json.dumps(report))

    def test_fill_dontcare_and_raw_accounting(self):
        data = header(blocks=5, chunks=3) + chunk() + chunk(0xCAC2, 2, b'ABCD') + chunk(0xCAC3, 2, b'')
        report = self.inspect(data)
        self.assertEqual(report['status'], 'NO_SCOPE_FINDINGS')
        self.assertEqual([row['output_start_block'] for row in report['chunks']], [0,1,3])
        self.assertEqual(report['observed_output_blocks'], 5)

    def test_empty_image_layout_is_supported(self):
        report = self.inspect(header(blocks=0, chunks=0))
        self.assertEqual(report['status'], 'NO_SCOPE_FINDINGS')
        self.assertEqual(report['observed_output_blocks'], 0)

    def test_crc_declaration_is_not_verification(self):
        data = header(blocks=1,chunks=2) + chunk() + chunk(0xCAC4,0,b'abcd')
        report = self.inspect(data)
        self.assertEqual(report['status'], 'REVIEW_REQUIRED')
        self.assertEqual(report['findings'], [])
        self.assertIn('CRC32_UNVERIFIED', self.codes(report,True))
        self.assertEqual(report['observed_output_blocks'], 1)
        self.assertNotIn('abcd', json.dumps(report))

    def test_nonzero_image_checksum_unverified(self):
        report = self.inspect(header(checksum=123)+chunk())
        self.assertTrue(report['header']['image_checksum_declared'])
        self.assertIn('IMAGE_CHECKSUM_UNVERIFIED', self.codes(report,True))

    def test_crc_nonzero_blocks_flagged_not_counted(self):
        report = self.inspect(header(blocks=1,chunks=2)+chunk()+chunk(0xCAC4,3,b'abcd'))
        self.assertIn('CRC32_OUTPUT_BLOCKS_NONZERO', self.codes(report))
        self.assertEqual(report['observed_output_blocks'],1)

    def test_truncated_header_and_bad_signature(self):
        self.assertIn('SPARSE_HEADER_TRUNCATED', self.codes(self.inspect(b'not-an-image')))
        self.assertIn('SPARSE_SIGNATURE_MISMATCH', self.codes(self.inspect(header(magic=0)+chunk())))

    def test_unsupported_major_stops_without_interpreting_chunks(self):
        report = self.inspect(header(major=2)+chunk())
        self.assertIn('SPARSE_MAJOR_VERSION_UNSUPPORTED', self.codes(report,True))
        self.assertFalse(report['layout_walk_complete'])
        self.assertEqual(report['chunks'],[])

    def test_minor_and_extended_headers_mark_coverage(self):
        report = self.inspect(header(minor=1,header=32,chunk_header=16)+b'extr'+chunk(extension=b'ext2'))
        self.assertEqual(report['findings'],[])
        self.assertEqual(self.codes(report,True), {'SPARSE_MINOR_VERSION_UNINSPECTED','FILE_HEADER_EXTENSION_UNINSPECTED','CHUNK_HEADER_EXTENSION_UNINSPECTED'})
        self.assertTrue(report['layout_walk_complete'])
        self.assertEqual(report['metadata_bytes_read'],40)

    def test_header_sizes_below_minimum(self):
        for changes in ({'header':27},{'chunk_header':11}):
            with self.subTest(changes=changes):
                report = self.inspect(header(**changes)+chunk())
                self.assertIn('SPARSE_HEADER_SIZE_INVALID',self.codes(report))
                self.assertFalse(report['layout_walk_complete'])

    def test_header_extension_beyond_file(self):
        report = self.inspect(header(header=200)+chunk())
        self.assertIn('SPARSE_HEADER_TRUNCATED',self.codes(report))

    def test_invalid_block_sizes(self):
        for size in (0,1,3,6):
            with self.subTest(size=size):
                report = self.inspect(header(block=size)+chunk())
                self.assertIn('SPARSE_BLOCK_SIZE_INVALID',self.codes(report))

    def test_resource_limits_are_incomplete(self):
        for data,code in ((header(block=tool.MAX_BLOCK_BYTES+4)+chunk(),'BLOCK_SIZE_LIMIT'),
                          (header(block=tool.MAX_BLOCK_BYTES,blocks=0xffffffff)+chunk(),'DECLARED_OUTPUT_SIZE_LIMIT'),
                          (header(chunks=tool.MAX_CHUNKS+1)+chunk(),'CHUNK_COUNT_LIMIT')):
            with self.subTest(code=code):
                with self.assertRaisesRegex(TextError,'^'+code+'$'):
                    self.inspect(data)

    def test_chunk_header_and_data_truncation(self):
        self.assertIn('CHUNK_HEADER_TRUNCATED',self.codes(self.inspect(header()+b'\0'*11)))
        self.assertIn('CHUNK_DATA_TRUNCATED',self.codes(self.inspect(header()+chunk()[:-1])))

    def test_extended_chunk_header_truncation(self):
        report = self.inspect(header(chunk_header=24)+chunk())
        self.assertIn('CHUNK_HEADER_TRUNCATED',self.codes(report))

    def test_chunk_size_below_header_stops(self):
        report = self.inspect(header()+chunk(size=11))
        self.assertIn('CHUNK_SIZE_BELOW_HEADER',self.codes(report))
        self.assertFalse(report['layout_walk_complete'])

    def test_known_body_sizes(self):
        for kind,body in ((0xCAC1,b'abc'),(0xCAC2,b'abc'),(0xCAC3,b'x'),(0xCAC4,b'abc')):
            with self.subTest(kind=kind):
                report = self.inspect(header(blocks=0 if kind==0xCAC4 else 1)+chunk(kind,0 if kind==0xCAC4 else 1,body))
                self.assertIn('CHUNK_PAYLOAD_SIZE_MISMATCH',self.codes(report))

    def test_reserved_and_unknown_kind(self):
        report = self.inspect(header()+chunk(reserved=1))
        self.assertIn('CHUNK_RESERVED_NONZERO',self.codes(report))
        report = self.inspect(header()+chunk(kind=0xCAFF))
        self.assertIn('CHUNK_TYPE_UNSUPPORTED',self.codes(report,True))
        self.assertFalse(report['layout_walk_complete'])
        self.assertNotIn('OUTPUT_BLOCK_COUNT_MISMATCH',self.codes(report))

    def test_output_mismatch_and_exceeded(self):
        report = self.inspect(header(blocks=0)+chunk())
        self.assertIn('OUTPUT_BLOCK_COUNT_EXCEEDED',self.codes(report))
        self.assertIn('OUTPUT_BLOCK_COUNT_MISMATCH',self.codes(report))
        report = self.inspect(header(blocks=2)+chunk())
        self.assertIn('OUTPUT_BLOCK_COUNT_MISMATCH',self.codes(report))

    def test_trailing_bytes_and_extra_declared_chunk(self):
        report = self.inspect(header()+chunk()+b'trailer')
        self.assertIn('TRAILING_INPUT_BYTES',self.codes(report))
        report = self.inspect(header(chunks=2)+chunk())
        self.assertIn('CHUNK_HEADER_TRUNCATED',self.codes(report))

    def test_huge_payload_declaration_no_allocation(self):
        report = self.inspect(header(blocks=0xffffffff,block=4)+chunk(blocks=0xffffffff,body=b'',size=0xffffffff))
        self.assertIn('CHUNK_DATA_TRUNCATED',self.codes(report))
        self.assertEqual(report['metadata_bytes_read'],40)

    def test_large_declared_output_exact_decimal(self):
        blocks = 0xffffffff
        report = self.inspect(header(blocks=blocks)+chunk(0xCAC3,blocks,b''))
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')
        self.assertEqual(report['header']['declared_output_bytes'],str(blocks*4))
        self.assertEqual(report['metadata_bytes_read'],40)

    def test_reader_bounds_budget_and_mutation(self):
        self.input.write_bytes(header()+chunk())
        with binary_reader.ImageReader(self.input) as reader:
            for offset,length in ((-1,1),(0,0),(44,1),(False,1)):
                with self.assertRaisesRegex(TextError,'METADATA_RANGE_INVALID'):
                    reader.read_at(offset,length,'test')
            with patch.object(binary_reader,'MAX_METADATA_BYTES',1):
                with self.assertRaisesRegex(TextError,'METADATA_BYTE_LIMIT'):
                    reader.read_at(0,2,'test')
        with self.assertRaisesRegex(TextError,'INPUT_CHANGED'):
            with binary_reader.ImageReader(self.input):
                self.input.write_bytes(b'changed')

    def test_reader_empty_and_size_limit(self):
        self.input.write_bytes(b'')
        with self.assertRaisesRegex(TextError,'IMAGE_SIZE_LIMIT'):
            binary_reader.ImageReader(self.input)
        self.input.write_bytes(header()+chunk())
        with patch.object(binary_reader,'MAX_IMAGE_BYTES',1):
            with self.assertRaisesRegex(TextError,'IMAGE_SIZE_LIMIT'):
                binary_reader.ImageReader(self.input)

    def cli(self, data, folder='report',extra=()):
        self.input.write_bytes(data)
        return subprocess.run([sys.executable,'-B',str(ROOT/'sparse_inspector.py'),'--image',str(self.input),
                               '--output',str(self.base/folder),*extra],capture_output=True,text=True,check=False)

    def test_cli_success_report_and_fresh_output(self):
        data=header()+chunk()
        result=self.cli(data)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'NO_SCOPE_FINDINGS')
        self.assertNotIn(str(self.input),result.stdout+result.stderr)
        self.assertEqual(set(p.name for p in (self.base/'report').iterdir()),{'report.json','report.html','MANIFEST.json'})
        result=self.cli(data)
        self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['error'],'OUTPUT_EXISTS')
        self.assertEqual(self.input.read_bytes(),data)

    def test_cli_review_and_limit_and_arguments(self):
        result=self.cli(header()+chunk()[:-1])
        self.assertEqual(result.returncode,1)
        self.assertEqual(json.loads(result.stdout)['status'],'REVIEW_REQUIRED')
        result=self.cli(header(chunks=4001)+chunk(),folder='limit')
        self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['error'],'CHUNK_COUNT_LIMIT')
        self.assertFalse((self.base/'limit').exists())
        result=self.cli(header()+chunk(),folder='invalid',extra=('--unknown','private-value'))
        self.assertEqual(result.returncode,2)
        self.assertNotIn('private-value',result.stdout+result.stderr)

    def test_reader_regular_and_link_paths(self):
        with self.assertRaisesRegex(TextError,'REGULAR_FILE_REQUIRED'):
            binary_reader.ImageReader(self.base)
        self.input.write_bytes(header()+chunk())
        route=self.base/'linked.sparse'
        try:
            route.symlink_to(self.input)
        except OSError:
            self.skipTest('Symlink creation requires platform privileges')
        with self.assertRaisesRegex(TextError,'LINKED_PATH_REJECTED'):
            binary_reader.ImageReader(route)


if __name__ == '__main__':
    unittest.main()
