from pathlib import Path
import contextlib
import hashlib
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'examples'))
import generate as fixtures
import gpt_inspector as tool
from inspection_support import TextError


class GPTTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.image=self.base/'fictional.img'

    def inspect(self,data=None,sector=512,details=False):
        self.image.write_bytes(fixtures.build_image(sector) if data is None else data)
        before=self.image.read_bytes()
        with tool.ImageReader(self.image) as reader:report=tool.inspect(reader,sector,details)
        self.assertEqual(self.image.read_bytes(),before)
        return report

    def codes(self,report):return {r['code'] for r in report['findings']}

    def edit_tables(self,data,offset,value):
        for lba in (1,len(data)//512-1):
            table_lba=struct.unpack_from('<Q',data,lba*512+72)[0]
            data[table_lba*512+offset:table_lba*512+offset+len(value)]=value
        fixtures.refresh_checksums(data,512)

    def test_clean_both_sector_sizes(self):
        for sector in (512,4096):
            report=self.inspect(sector=sector)
            self.assertEqual(report['status'],'NO_SCOPE_FINDINGS');self.assertTrue(report['primary_backup_metadata_compared'])
            self.assertTrue(all(h['header_crc_matches'] and h['table_crc_matches'] for h in report['headers']))
            self.assertEqual(len(report['headers'][0]['partitions']),2)

    def test_metadata_budget_and_no_whole_image_hash(self):
        report=self.inspect();self.assertFalse(report['whole_image_hashed'])
        self.assertEqual(report['metadata_bytes_read'],512+1024+32768)
        self.assertEqual(len(report['metadata_regions']),5)

    def test_private_names_and_identifiers_are_opt_in(self):
        report=self.inspect();value=json.dumps(report)
        self.assertNotIn('demo_alpha',value);self.assertNotIn(str(self.base),value)
        self.assertNotIn('11111111-2222',value)
        self.assertIn('demo_alpha',json.dumps(self.inspect(details=True)))

    def test_bad_header_crc(self):
        data=fixtures.build_image();data[512+16]^=1
        self.assertIn('GPT_HEADER_CRC_MISMATCH',self.codes(self.inspect(data)))

    def test_bad_table_crc_and_split_brain(self):
        data=fixtures.build_image();data[1024+56]^=1
        codes=self.codes(self.inspect(data))
        self.assertIn('GPT_TABLE_CRC_MISMATCH',codes);self.assertIn('PRIMARY_BACKUP_METADATA_MISMATCH',codes)

    def test_split_brain_even_when_both_crcs_match(self):
        data=fixtures.build_image();data[1024+56]^=1;fixtures.refresh_checksums(data,512)
        report=self.inspect(data)
        self.assertIn('PRIMARY_BACKUP_METADATA_MISMATCH',self.codes(report))
        self.assertTrue(all(h['table_crc_matches'] for h in report['headers']))

    def test_overlap_and_nested_interval(self):
        data=fixtures.build_image(partitions=[(36,90,'outer'),(40,45,'inner'),(80,100,'overlap')])
        self.assertIn('PARTITION_OVERLAP_OBSERVED',self.codes(self.inspect(data)))

    def test_adjacent_partitions_are_not_overlaps(self):
        data=fixtures.build_image(partitions=[(36,50,'left'),(51,60,'right')])
        self.assertEqual(self.inspect(data)['status'],'NO_SCOPE_FINDINGS')

    def test_partition_ranges(self):
        for start,end in ((50,40),(2,40),(36,250)):
            self.assertIn('PARTITION_RANGE_INVALID',self.codes(self.inspect(fixtures.build_image(partitions=[(start,end,'range')]))))

    def test_duplicate_and_zero_guids(self):
        data=fixtures.build_image();self.edit_tables(data,128+16,data[1024+16:1024+32])
        self.assertIn('DUPLICATE_PARTITION_GUID',self.codes(self.inspect(data)))
        data=fixtures.build_image();self.edit_tables(data,16,b'\0'*16)
        self.assertIn('ZERO_PARTITION_GUID',self.codes(self.inspect(data)))

    def test_invalid_utf16_and_unused_entry_data(self):
        data=fixtures.build_image();self.edit_tables(data,56,b'\0\xd8')
        self.assertIn('PARTITION_NAME_ENCODING_INVALID',self.codes(self.inspect(data)))
        data=fixtures.build_image();self.edit_tables(data,256+32,b'\1')
        self.assertIn('NONZERO_UNUSED_ENTRY_DATA',self.codes(self.inspect(data)))

    def test_name_padding_and_controls(self):
        data=fixtures.build_image();self.edit_tables(data,56,b'a\0\0\0b\0')
        self.assertIn('PARTITION_NAME_PADDING_NONZERO',self.codes(self.inspect(data)))
        data=fixtures.build_image();self.edit_tables(data,56,b'\x01\0')
        self.assertIn('PARTITION_NAME_CONTROL',self.codes(self.inspect(data)))

    def test_missing_headers_still_explicit_review(self):
        report=self.inspect(bytearray(4096))
        self.assertEqual(report['status'],'REVIEW_REQUIRED');self.assertFalse(report['primary_backup_metadata_compared'])
        self.assertIn('GPT_SIGNATURE_MISMATCH',self.codes(report))

    def test_revision_and_entry_size_unsupported(self):
        for offset,value,code in [(8,0x20000,'GPT_REVISION_UNSUPPORTED'),(84,256,'GPT_ENTRY_SIZE_UNSUPPORTED')]:
            data=fixtures.build_image();struct.pack_into('<I',data,512+offset,value)
            report=self.inspect(data)
            self.assertIn(code,{r['code'] for r in report['coverage_issues']});self.assertFalse(report['headers'][0]['table_inspected'])

    def test_header_size_and_usable_range(self):
        data=fixtures.build_image();struct.pack_into('<I',data,512+12,91)
        self.assertIn('GPT_HEADER_SIZE_INVALID',self.codes(self.inspect(data)))
        data=fixtures.build_image();struct.pack_into('<QQ',data,512+40,200,100)
        self.assertIn('GPT_USABLE_RANGE_INVALID',self.codes(self.inspect(data)))

    def test_untrusted_table_pointer_never_read(self):
        data=fixtures.build_image();struct.pack_into('<Q',data,512+72,2**64-1)
        report=self.inspect(data)
        self.assertIn('GPT_TABLE_RANGE_INVALID',self.codes(report))
        self.assertFalse(any(r['id']=='primary-entries' for r in report['metadata_regions']))

    def test_table_geometry_cannot_overlap_usable_area(self):
        data=fixtures.build_image();struct.pack_into('<Q',data,512+72,35)
        report=self.inspect(data);self.assertIn('GPT_TABLE_RANGE_INVALID',self.codes(report))
        self.assertFalse(report['headers'][0]['table_inspected'])

    def test_entry_count_bound_and_image_alignment(self):
        data=fixtures.build_image();struct.pack_into('<I',data,512+80,4097)
        with self.assertRaisesRegex(TextError,'GPT_ENTRY_COUNT_LIMIT'):self.inspect(data)
        with self.assertRaisesRegex(TextError,'IMAGE_ALIGNMENT_INVALID'):self.inspect(b'generated')

    def test_header_location_reserved_and_padding(self):
        data=fixtures.build_image();struct.pack_into('<Q',data,512+24,2);struct.pack_into('<I',data,512+20,1);data[512+100]=1
        fixtures.refresh_checksums(data,512)
        codes=self.codes(self.inspect(data))
        self.assertTrue({'GPT_HEADER_LOCATION_MISMATCH','GPT_RESERVED_FIELD_NONZERO','GPT_HEADER_PADDING_NONZERO'}<=codes)

    def test_nonzero_header_extension_is_coverage(self):
        data=fixtures.build_image();struct.pack_into('<I',data,512+12,96);data[512+92]=1;fixtures.refresh_checksums(data,512)
        report=self.inspect(data)
        self.assertIn('GPT_HEADER_EXTENSION_UNINSPECTED',{r['code'] for r in report['coverage_issues']})

    def test_protective_and_hybrid_mbr(self):
        for offset,value,code in [(510,0,'MBR_SIGNATURE_MISMATCH'),(450,0,'PROTECTIVE_MBR_ENTRY_COUNT'),(466,0x83,'HYBRID_MBR_DECLARED'),(454,2,'PROTECTIVE_MBR_RANGE_MISMATCH')]:
            data=fixtures.build_image();data[offset]=value
            self.assertIn(code,self.codes(self.inspect(data)))

    def test_empty_partition_table(self):
        report=self.inspect(fixtures.build_image(partitions=[]))
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS');self.assertFalse(report['headers'][0]['partitions'])

    def test_reader_detects_changed_input(self):
        self.image.write_bytes(fixtures.build_image())
        with self.assertRaisesRegex(TextError,'INPUT_CHANGED'):
            with tool.ImageReader(self.image) as reader:
                reader.read_at(0,512,'mbr');self.image.write_bytes(b'changed')

    def test_reader_size_range_and_read_budget(self):
        self.image.write_bytes(fixtures.build_image())
        with patch.object(tool,'MAX_IMAGE_BYTES',1024):
            with self.assertRaisesRegex(TextError,'IMAGE_SIZE_LIMIT'):tool.ImageReader(self.image)
        with tool.ImageReader(self.image) as reader:
            with self.assertRaisesRegex(TextError,'METADATA_RANGE_INVALID'):reader.read_at(-1,512,'bad')
            with patch.object(tool,'MAX_METADATA_BYTES',512):
                reader.read_at(0,512,'mbr')
                with self.assertRaisesRegex(TextError,'METADATA_BYTE_LIMIT'):reader.read_at(0,1,'extra')

    @unittest.skipUnless(os.name=='posix','POSIX sparse-file fixture avoids physical allocation')
    def test_large_sparse_regular_image_uses_small_reads(self):
        with self.image.open('wb') as stream:stream.truncate(3*1024**3)
        with tool.ImageReader(self.image) as reader:
            self.assertEqual(reader.read_at(reader.size-512,512,'last'),b'\0'*512);self.assertEqual(reader.bytes_read,512)

    def test_reader_refuses_linked_file(self):
        self.image.write_bytes(fixtures.build_image());link=self.base/'link.img'
        try:link.symlink_to(self.image)
        except OSError:self.skipTest('Symlink creation requires platform privileges')
        with self.assertRaisesRegex(TextError,'LINKED_PATH_REJECTED'):tool.ImageReader(link)

    @unittest.skipUnless(hasattr(os,'mkfifo'),'POSIX special-file fixture')
    def test_reader_refuses_fifo_without_opening(self):
        fifo=self.base/'fifo';os.mkfifo(fifo)
        with self.assertRaisesRegex(TextError,'REGULAR_FILE_REQUIRED'):tool.ImageReader(fifo)

    def test_actual_cli_examples_and_source_preservation(self):
        subprocess.run([sys.executable,'-B',str(ROOT/'examples/generate.py'),'--output',str(self.base/'fixtures')],check=True,capture_output=True)
        for name,sector,expected in [('clean-512',512,0),('clean-4096',4096,0),('review-crc',512,1),('review-overlap',512,1)]:
            image=self.base/f'fixtures/{name}.img';before=hashlib.sha256(image.read_bytes()).hexdigest()
            result=subprocess.run([sys.executable,'-B',str(ROOT/'gpt_inspector.py'),'--image',str(image),'--sector-size',str(sector),'--output',str(self.base/name)],capture_output=True,text=True)
            self.assertEqual(result.returncode,expected,result.stdout+result.stderr)
            self.assertNotIn(str(self.base),result.stdout);self.assertEqual(before,hashlib.sha256(image.read_bytes()).hexdigest())
            manifest=json.loads((self.base/name/'MANIFEST.json').read_text())
            for row in manifest['files']:self.assertEqual(hashlib.sha256((self.base/name/row['path']).read_bytes()).hexdigest(),row['sha256'])

    def test_private_errors_and_escaped_detail_report(self):
        self.image.write_bytes(fixtures.build_image(partitions=[(36,40,'</pre><script>fiction</script>')]))
        out=self.base/'out';capture=io.StringIO()
        args=['--image',str(self.image),'--sector-size','512','--output',str(out),'--include-details']
        with contextlib.redirect_stdout(capture):self.assertEqual(tool.main(args),0)
        html=(out/'report.html').read_text();self.assertNotIn('<script>',html);self.assertIn('&lt;script&gt;',html)
        with contextlib.redirect_stdout(capture):self.assertEqual(tool.main(args),2)
        self.assertNotIn(str(self.base),capture.getvalue())


if __name__=='__main__':unittest.main()
