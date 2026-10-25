"""Original ASCII observations in generated metadata fixtures; no binary execution."""
from pathlib import Path
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
import elf_inspector as e
from make_demo import make_elf,create

class RuntimeHints(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='outlands-elf-hints-')
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def file(self,name,tail=b''):
        target=self.root/name;target.write_bytes(make_elf()+b'\0'+tail);return target
    def raw(self,data):return e.scan_runtime_hints(io.BytesIO(data),len(data),e.Budget(e.Limits()))
    def tokens(self,scan):return [(x['kind'],x['text']) for x in scan['observations']]
    def test_default_has_no_hint_output_or_reads(self):
        path=self.file('demo.elf',b'liboptional.so\0/vendor/etc/demo.xml')
        with patch.object(e,'scan_runtime_hints',side_effect=AssertionError('disabled scan called')):
            result=e.analyze(files=[path]);self.assertNotIn('runtime_hints',result)
            self.assertNotIn('runtime_hint_scan',result['files'][0])
    def test_library_version_and_path_tokens(self):
        scan=self.raw(b'libaudio.so libcodec.so.1.2 /fictional/lib/libscene.so.7\0')
        self.assertEqual(self.tokens(scan),[('library_text','/fictional/lib/libscene.so.7'),('library_text','libaudio.so'),('library_text','libcodec.so.1.2')])
        self.assertEqual(scan['coverage'],'complete_ascii_scan')
    def test_false_suffix_and_embedded_substring_not_shortened(self):
        scan=self.raw(b'libbad.so_backup libbad.so.2beta libbad.so.2. libgood.so\0')
        self.assertEqual(self.tokens(scan),[('library_text','libgood.so')])
    def test_selected_config_and_firmware_prefixes_only(self):
        scan=self.raw(b'/vendor/etc/demo.xml /odm/etc/device.conf /system/etc/media.cfg /vendor/firmware/demo.bin /odm/firmware/other.bin /home/private/a.ini\0')
        self.assertEqual(len(scan['observations']),5)
        self.assertTrue(all(x['kind']=='config_or_firmware_path_text' for x in scan['observations']))
        self.assertNotIn('/home/private',json.dumps(scan))
    def test_token_across_chunk_boundary_retains_offset(self):
        with patch.object(e,'HINT_CHUNK',7):scan=self.raw(b'\0'*(7*3-2)+b'libboundary.so.3\0')
        self.assertEqual(scan['observations'][0]['text'],'libboundary.so.3')
        self.assertEqual(scan['observations'][0]['first_offset'],19)
    def test_non_ascii_and_control_bytes_are_separators(self):
        scan=self.raw(b'liba.so\0libb.so\xff\x1blibc.so\nlibd.so\x7f')
        self.assertEqual([x['text'] for x in scan['observations']],['liba.so','libb.so','libc.so','libd.so'])
        self.assertTrue(all(e.supported_text(x['text']) for x in scan['observations']))
    def test_repeated_tokens_count_without_spending_extra_slots(self):
        with patch.object(e,'MAX_HINTS_PER_FILE',1):scan=self.raw(b'librepeat.so\0librepeat.so librepeat.so')
        self.assertEqual(scan['observations'][0]['occurrences'],3)
        self.assertEqual(scan['reasons'],[])
    def test_overlong_ascii_run_is_omitted_not_prefix_claimed(self):
        with patch.object(e,'MAX_HINT_STRING',16),patch.object(e,'HINT_CHUNK',5):
            scan=self.raw(b'libshort.so'+b'x'*30+b'\0libreal.so\0')
        self.assertEqual([x['text'] for x in scan['observations']],['libreal.so'])
        self.assertEqual(scan['overlong_ascii_runs_omitted'],1)
        self.assertEqual(scan['reasons'],['STRING_LENGTH_LIMIT'])
    def test_per_file_byte_cut_omits_partial_final_token(self):
        with patch.object(e,'MAX_HINT_FILE_BYTES',12):scan=self.raw(b'libfirst.so\0libsecond.so\0')
        self.assertEqual([x['text'] for x in scan['observations']],['libfirst.so'])
        self.assertEqual(scan['bytes_scanned'],12)
        self.assertEqual(scan['reasons'],['PER_FILE_BYTE_LIMIT'])
    def test_cut_inside_token_never_reports_shortened_library(self):
        with patch.object(e,'MAX_HINT_FILE_BYTES',10):scan=self.raw(b'libname.so.2.3\0')
        self.assertEqual(scan['observations'],[])
    def test_exact_byte_limit_is_complete_when_file_ends(self):
        with patch.object(e,'MAX_HINT_FILE_BYTES',len(b'liba.so')):scan=self.raw(b'liba.so')
        self.assertEqual(scan['coverage'],'complete_ascii_scan')
        self.assertEqual(scan['observations'][0]['text'],'liba.so')
    def test_per_file_unique_observation_cap_visible(self):
        with patch.object(e,'MAX_HINTS_PER_FILE',1):scan=self.raw(b'libone.so\0libtwo.so\0')
        self.assertEqual(len(scan['observations']),1)
        self.assertEqual(scan['reasons'],['FILE_HINT_COUNT_LIMIT'])
    def test_total_bytes_cap_applies_across_files_and_marks_unscanned(self):
        budget=e.Budget(e.Limits());data=b'liba.so\0'
        with patch.object(e,'MAX_HINT_TOTAL_BYTES',len(data)):
            first=e.scan_runtime_hints(io.BytesIO(data),len(data),budget)
            second=e.scan_runtime_hints(io.BytesIO(data),len(data),budget)
        self.assertEqual(first['coverage'],'complete_ascii_scan')
        self.assertEqual(second['bytes_scanned'],0);self.assertEqual(second['reasons'],['GLOBAL_BYTE_LIMIT'])
        self.assertEqual(budget.hint_bytes,len(data))
    def test_total_observation_limit_is_global(self):
        budget=e.Budget(e.Limits())
        with patch.object(e,'MAX_HINTS_TOTAL',1):
            first=e.scan_runtime_hints(io.BytesIO(b'liba.so'),7,budget)
            second=e.scan_runtime_hints(io.BytesIO(b'libb.so'),7,budget)
        self.assertEqual(len(first['observations']),1);self.assertEqual(second['observations'],[])
        self.assertEqual(second['reasons'],['GLOBAL_HINT_COUNT_LIMIT'])
    def test_declared_graph_and_status_unaffected_by_observations(self):
        path=self.file('demo.elf',b'libmissing_optional.so\0/vendor/etc/nonexistent.xml\0')
        before=e.analyze(files=[path]);after=e.analyze(files=[path],runtime_hints=True)
        self.assertEqual(before['dependencies'],after['dependencies'])
        self.assertEqual(before['entry_files'],after['entry_files']);self.assertEqual(after['status'],'NO_SCOPE_FINDINGS')
        self.assertEqual(after['summary']['visited_in_graph'],1)
        self.assertEqual(after['runtime_hints']['observations'],2)
        self.assertEqual(after['runtime_hints']['files_with_partial_hint_coverage'],0)
    def test_hint_truncation_requires_review_without_creating_edges(self):
        path=self.file('demo.elf',b'liboptional.so\0')
        with patch.object(e,'MAX_HINT_FILE_BYTES',16):report=e.analyze(files=[path],runtime_hints=True)
        self.assertEqual(report['status'],'REVIEW_REQUIRED');self.assertEqual(report['dependencies'],[])
        self.assertIn('RUNTIME_HINT_PER_FILE_BYTE_LIMIT',[x['code'] for x in report['issues']])
    def test_matching_optional_library_is_not_followed_in_graph(self):
        entry=self.root/'app.elf';entry.write_bytes(make_elf(['libdeclared.so'])+b'\0liboptional.so\0')
        (self.root/'libdeclared.so').write_bytes(make_elf(soname='libdeclared.so'))
        (self.root/'liboptional.so').write_bytes(make_elf(['libnotreal.so'],soname='liboptional.so'))
        before=e.analyze([self.root],[entry]);after=e.analyze([self.root],[entry],runtime_hints=True)
        self.assertEqual(before['dependencies'],after['dependencies'])
        self.assertEqual(after['summary']['visited_in_graph'],2)
        self.assertEqual(len(after['dependencies']),1)
    def test_hint_read_uses_same_handle_and_preserves_source_and_hash(self):
        path=self.file('demo.elf',b'liboptional.so\0');before=path.read_bytes()
        result=e.inspect_file(path,e.Budget(e.Limits()),hash_files=True,runtime_hints=True)
        self.assertEqual(path.read_bytes(),before);self.assertEqual(result['sha256'],hashlib.sha256(before).hexdigest())
    def test_short_read_is_controlled(self):
        with self.assertRaisesRegex(e.InspectorError,'FILE_CHANGED_DURING_HINT_SCAN'):
            e.scan_runtime_hints(io.BytesIO(b'abc'),9,e.Budget(e.Limits()))
    def test_html_keeps_hints_separate_and_escapes_report_text(self):
        path=self.file('demo.elf',b'liboptional.so\0/vendor/etc/demo.xml\0')
        report=e.analyze(files=[path],runtime_hints=True);page=e.html_report(report).decode()
        self.assertIn('Optional runtime text hints',page)
        self.assertIn('do not prove dependencies',page);self.assertNotIn(str(self.root),page)
    def test_cli_flag_and_fresh_output(self):
        path=self.file('demo.elf',b'liboptional.so\0');output=self.root/'report'
        with contextlib.redirect_stdout(io.StringIO()):code=e.cli(['--file',str(path),'--runtime-hints','--output',str(output)])
        self.assertEqual(code,0);report=json.loads((output/'report.json').read_bytes())
        self.assertEqual(report['runtime_hints']['observations'],1)
        self.assertEqual(len(list(output.iterdir())),4)
    def test_non_elf_and_malformed_inputs_are_not_string_scanned(self):
        path=self.root/'plain';path.write_bytes(b'liba.so')
        with patch.object(e,'scan_runtime_hints',side_effect=AssertionError('not an ELF')):
            report=e.analyze(files=[path],runtime_hints=True)
        self.assertEqual(report['runtime_hints']['files_scanned'],0)
    def test_generated_hint_example_has_authored_observations(self):
        target=self.root/'example';create(target,clean=True,runtime_hints=True)
        report=e.analyze([target/'lib'],[target/'app/demo.elf'],runtime_hints=True)
        texts=[x['text'] for node in report['files'] for x in node['runtime_hint_scan']['observations']]
        self.assertIn('liboptional_effects.so.2',texts);self.assertIn('/vendor/etc/fictional-demo.xml',texts)

if __name__=='__main__':unittest.main()
