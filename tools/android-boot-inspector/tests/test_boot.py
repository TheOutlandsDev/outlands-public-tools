"""Synthetic image metadata, actual CLI and read-budget regressions. MIT."""
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
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'examples'))
import binary_reader
import boot_inspector as boot
from generate import boot_fixture, vendor_fixture, generate
from inspection_support import TextError


class BootTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve(); self.image = self.base/'fictional.img'

    def inspect(self, data):
        self.image.write_bytes(data)
        with binary_reader.ImageReader(self.image) as reader: result = boot.inspect(reader)
        self.assertEqual(self.image.read_bytes(), data)
        return result

    def codes(self, report, key='findings'): return {x['code'] for x in report[key]}

    def mutate(self, data, offset, value):
        out = bytearray(data); struct.pack_into('<I', out, offset, value); return bytes(out)

    def cli(self, data, output='result', more=()):
        self.image.write_bytes(data)
        return subprocess.run([sys.executable, '-B', str(ROOT/'boot_inspector.py'), '--image', str(self.image),
                               '--output', str(self.base/output), *more], capture_output=True, text=True, check=False)

    def test_boot_v3_exact_layout(self):
        report = self.inspect(boot_fixture(3))
        self.assertEqual(report['status'], 'NO_SCOPE_FINDINGS')
        self.assertEqual([(x['role'], x['offset_bytes'], x['declared_bytes'], x['padded_end_bytes']) for x in report['sections']],
                         [('header', 0, 1580, 4096), ('kernel', 4096, 11, 8192), ('ramdisk', 8192, 7, 12288)])
        self.assertEqual(report['metadata_bytes_read'], 8+44+1580)

    def test_boot_v4_signature_layout(self):
        report = self.inspect(boot_fixture())
        self.assertEqual(report['status'], 'NO_SCOPE_FINDINGS')
        self.assertEqual(report['sections'][-1], {'role':'boot_signature', 'offset_bytes':12288,
                         'declared_bytes':9, 'padded_end_bytes':16384, 'within_file':True})

    def test_vendor_v3_layout(self):
        report = self.inspect(vendor_fixture(3))
        self.assertEqual(report['status'], 'NO_SCOPE_FINDINGS')
        self.assertEqual([x['role'] for x in report['sections']], ['header','vendor_ramdisk','dtb'])
        self.assertEqual(report['declared_padded_layout_bytes'], 12288)

    def test_vendor_v4_table(self):
        report = self.inspect(vendor_fixture())
        self.assertEqual(report['status'], 'NO_SCOPE_FINDINGS')
        self.assertTrue(report['ramdisk_table_inspected'])
        self.assertEqual([(r['offset_bytes'],r['declared_bytes'],r['type']) for r in report['ramdisk_fragments']], [(0,5,1),(5,7,3)])
        self.assertEqual(report['metadata_bytes_read'], 8+12+2128+216)

    def test_zero_components_are_declarations_not_bootability_claims(self):
        data = self.mutate(self.mutate(self.mutate(boot_fixture(), 8, 0), 12, 0), 1580, 0)[:4096]
        report = self.inspect(data)
        self.assertEqual(report['status'], 'NO_SCOPE_FINDINGS')
        self.assertEqual([r['offset_bytes'] for r in report['sections']], [0,4096,4096,4096])

    def test_payload_not_read_or_hashed(self):
        data = bytearray(vendor_fixture()); data[4096:4108] = b'PRIVATE_DATA'
        report = self.inspect(bytes(data)); encoded = json.dumps(report)
        self.assertNotIn('PRIVATE', encoded)
        self.assertFalse(report['payloads_inspected']); self.assertFalse(report['whole_image_hashed'])
        for region in report['metadata_regions']:
            self.assertTrue(region['offset_bytes'] < 2128 or 12288 <= region['offset_bytes'] < 12504)

    def test_sensitive_header_text_and_board_ids_omitted(self):
        data = bytearray(vendor_fixture()); data[28:40] = b'PRIVATE_TEXT'; data[2080:2092] = b'PRIVATE_NAME'
        data[12332:12344] = b'PRIVATEBOARD'
        report = self.inspect(bytes(data)); encoded = json.dumps(report)
        self.assertNotIn('PRIVATE', encoded); self.assertNotIn('board_id', encoded)
        self.assertFalse(report['strings_and_hardware_identifiers_included'])

    def test_unknown_magic(self):
        report = self.inspect(b'unknown!')
        self.assertEqual(self.codes(report), {'IMAGE_MAGIC_UNRECOGNIZED'})
        self.assertEqual(report['metadata_bytes_read'], 8)

    def test_short_headers(self):
        for data in (b'A', b'ANDROID!', boot_fixture()[:100], b'VNDRBOOT', vendor_fixture()[:100]):
            with self.subTest(length=len(data),magic=data[:8]):
                report = self.inspect(data); self.assertIn('HEADER_TRUNCATED', self.codes(report))

    def test_unsupported_versions_stop_before_layout(self):
        for data, offset in ((boot_fixture(),40),(vendor_fixture(),8)):
            for version in (0,1,2,5,0xffffffff):
                report = self.inspect(self.mutate(data,offset,version))
                self.assertIn('HEADER_VERSION_UNSUPPORTED',self.codes(report,'coverage_issues'))
                self.assertEqual(report['sections'], [])

    def test_small_and_extended_header_size(self):
        for data, offset, expected in ((boot_fixture(),20,1584),(vendor_fixture(),2096,2128)):
            report = self.inspect(self.mutate(data,offset,expected-1))
            self.assertIn('HEADER_SIZE_INVALID', self.codes(report)); self.assertEqual(report['sections'],[])
            report = self.inspect(self.mutate(data,offset,expected+4))
            self.assertIn('HEADER_SIZE_UNSUPPORTED', self.codes(report,'coverage_issues'))

    def test_reserved_boot_header(self):
        report = self.inspect(self.mutate(boot_fixture(),24,1))
        self.assertIn('RESERVED_HEADER_NONZERO',self.codes(report))

    def test_page_size_invalid_and_unsupported(self):
        report = self.inspect(self.mutate(vendor_fixture(),12,0))
        self.assertIn('PAGE_SIZE_INVALID', self.codes(report))
        for page in (1,768,131072,0xffffffff):
            report = self.inspect(self.mutate(vendor_fixture(),12,page))
            self.assertIn('PAGE_SIZE_UNSUPPORTED', self.codes(report,'coverage_issues'))
            self.assertEqual(report['sections'],[])

    def test_header_spans_multiple_vendor_pages(self):
        data = bytearray(4096); data[:2112] = vendor_fixture(3)[:2112]
        struct.pack_into('<III', data,12,512,0,0); struct.pack_into('<I',data,24,0)
        struct.pack_into('<I',data,2100,0)
        report = self.inspect(bytes(data[:2560]))
        self.assertEqual(report['status'], 'NO_SCOPE_FINDINGS')
        self.assertEqual(report['sections'][1]['offset_bytes'],2560)

    def test_declared_component_and_padding_truncation(self):
        report = self.inspect(boot_fixture()[:8195])
        self.assertIn('SECTION_OUTSIDE_FILE',self.codes(report))
        report = self.inspect(boot_fixture()[:12297])
        self.assertIn('SECTION_PADDING_TRUNCATED', self.codes(report))

    def test_trailing_bytes_explicit_coverage(self):
        report = self.inspect(boot_fixture()+b'AVBfooter-or-other-uninspected-tail')
        self.assertEqual(report['trailing_bytes'],35)
        self.assertIn('TRAILING_BYTES_UNINSPECTED',self.codes(report,'coverage_issues'))

    def test_large_declared_sizes_do_not_allocate(self):
        report = self.inspect(self.mutate(boot_fixture(),8,0xffffffff))
        self.assertIn('SECTION_OUTSIDE_FILE',self.codes(report))
        self.assertLess(report['metadata_bytes_read'],2000)

    def test_table_length_mismatch(self):
        report = self.inspect(self.mutate(vendor_fixture(),2112,217))
        self.assertIn('TABLE_LENGTH_MISMATCH',self.codes(report))
        self.assertFalse(report['ramdisk_table_inspected'])

    def test_extended_table_entry_unsupported(self):
        data = self.mutate(self.mutate(vendor_fixture(),2120,112),2112,224)
        report = self.inspect(data)
        self.assertIn('TABLE_ENTRY_SIZE_UNSUPPORTED',self.codes(report,'coverage_issues'))
        self.assertFalse(report['ramdisk_table_inspected'])

    def test_table_count_limit(self):
        data = self.mutate(vendor_fixture(),2116,2049)
        with self.assertRaisesRegex(TextError,'^TABLE_ENTRY_LIMIT$'): self.inspect(data)

    def test_table_not_read_if_outside_image(self):
        report = self.inspect(vendor_fixture()[:12400])
        self.assertIn('SECTION_OUTSIDE_FILE', self.codes(report))
        self.assertFalse(report['ramdisk_table_inspected'])

    def test_fragment_outside_section(self):
        report = self.inspect(self.mutate(vendor_fixture(),12396,8))
        self.assertIn('FRAGMENT_OUTSIDE_RAMDISK_SECTION',self.codes(report))

    def test_fragment_overlap(self):
        report = self.inspect(self.mutate(vendor_fixture(),12400,4))
        self.assertIn('FRAGMENT_OVERLAP_OBSERVED',self.codes(report))

    def test_fragment_gap(self):
        data = self.mutate(self.mutate(vendor_fixture(),12400,6),12396,6)
        report = self.inspect(data)
        self.assertIn('FRAGMENT_GAP_OBSERVED',self.codes(report))

    def test_fragment_unknown_type(self):
        report = self.inspect(self.mutate(vendor_fixture(),12296,99))
        self.assertIn('FRAGMENT_TYPE_UNSUPPORTED',self.codes(report,'coverage_issues'))
        self.assertEqual(report['ramdisk_fragments'][0]['type'],99)

    def test_empty_table_and_ramdisk(self):
        data = vendor_fixture()
        for offset in (24,2100,2112,2116,2124): data = self.mutate(data,offset,0)
        report = self.inspect(data[:4096])
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')
        self.assertFalse(report['ramdisk_table_inspected'])

    def test_empty_table_nonempty_ramdisk(self):
        data = self.mutate(self.mutate(vendor_fixture(),2112,0),2116,0)
        report = self.inspect(data)
        self.assertIn('FRAGMENT_COVERAGE_MISMATCH',self.codes(report))

    def test_metadata_reader_ranges_and_budget(self):
        self.image.write_bytes(boot_fixture())
        with binary_reader.ImageReader(self.image) as reader:
            for offset,length in ((-1,1),(0,0),(reader.size,1),(False,1)):
                with self.assertRaisesRegex(TextError,'^METADATA_RANGE_INVALID$'): reader.read_at(offset,length,'test')
            with patch.object(binary_reader,'MAX_METADATA_BYTES',7):
                with self.assertRaisesRegex(TextError,'^METADATA_BYTE_LIMIT$'): reader.read_at(0,8,'test')

    def test_reader_detects_changed_file(self):
        self.image.write_bytes(boot_fixture())
        with self.assertRaisesRegex(TextError,'^INPUT_CHANGED$'):
            with binary_reader.ImageReader(self.image) as reader:
                reader.read_at(0,8,'magic'); self.image.write_bytes(b'changed')

    def test_reader_limit_and_non_regular(self):
        self.image.write_bytes(b'')
        with self.assertRaisesRegex(TextError,'^IMAGE_SIZE_LIMIT$'): binary_reader.ImageReader(self.image)
        with self.assertRaisesRegex(TextError,'^REGULAR_FILE_REQUIRED$'): binary_reader.ImageReader(self.base)
        self.image.write_bytes(b'x'*10)
        with patch.object(binary_reader,'MAX_IMAGE_BYTES',9):
            with self.assertRaisesRegex(TextError,'^IMAGE_SIZE_LIMIT$'): binary_reader.ImageReader(self.image)

    def test_reader_absolute_path_and_stream_guards(self):
        for path in ('relative.img','//server/share/image.img',self.base/'..'/'outside.img'):
            with self.assertRaisesRegex(TextError,'^LOCAL_ABSOLUTE_PATH_REQUIRED$'): binary_reader.ImageReader(path)
        if os.name=='nt':
            with self.assertRaisesRegex(TextError,'^DEVICE_OR_STREAM_PATH_REJECTED$'):
                binary_reader.ImageReader(str(self.image)+':stream')

    def test_cli_success_and_report_hashes(self):
        result = self.cli(vendor_fixture())
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'NO_SCOPE_FINDINGS')
        self.assertNotIn(str(self.base),result.stdout)
        folder = self.base/'result'
        self.assertEqual({p.name for p in folder.iterdir()},{'report.json','report.html','MANIFEST.json'})
        for row in json.loads((folder/'MANIFEST.json').read_text())['files']:
            data=(folder/row['path']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(),row['sha256'])

    def test_cli_review_and_incomplete_exits(self):
        result = self.cli(b'unknown!','review')
        self.assertEqual(result.returncode,1); self.assertEqual(json.loads(result.stdout)['findings'],1)
        result = self.cli(b'','empty')
        self.assertEqual(result.returncode,2); self.assertEqual(json.loads(result.stdout)['status'],'INCOMPLETE')
        self.assertFalse((self.base/'empty').exists())
        result = self.cli(boot_fixture(),'args',('--private-path-unknown=secret',))
        self.assertEqual(result.returncode,2); self.assertNotIn('secret',result.stdout)
        result = self.cli(self.mutate(vendor_fixture(),2116,2049),'budget')
        self.assertEqual(result.returncode,2); self.assertEqual(json.loads(result.stdout)['error'],'TABLE_ENTRY_LIMIT')
        self.assertFalse((self.base/'budget').exists())

    def test_cli_existing_output_preserves_input_and_report(self):
        data = boot_fixture(); first = self.cli(data)
        self.assertEqual(first.returncode,0)
        expected = (self.base/'result'/'report.json').read_bytes()
        second = self.cli(data)
        self.assertEqual(second.returncode,2)
        self.assertEqual(self.image.read_bytes(),data)
        self.assertEqual((self.base/'result'/'report.json').read_bytes(),expected)

    def test_generated_examples_and_no_overwrite(self):
        folder=self.base/'examples'; self.assertEqual(generate(folder),6)
        expected={'boot-v3.img':0,'boot-v4.img':0,'vendor-v3.img':0,'vendor-v4.img':0,
                  'truncated-vendor.img':1,'unsupported-legacy.img':1}
        for name,exit_code in expected.items():
            report=self.inspect((folder/name).read_bytes())
            self.assertEqual(int(report['status']!='NO_SCOPE_FINDINGS'),exit_code,name)
        with self.assertRaisesRegex(TextError,'^OUTPUT_EXISTS$'): generate(folder)


if __name__=='__main__': unittest.main()

