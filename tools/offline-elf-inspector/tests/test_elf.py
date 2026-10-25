"""Synthetic metadata fixtures only. Inspected ELF files are never executed."""
from pathlib import Path
import contextlib
import hashlib
import io
import json
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
import elf_inspector as e
from make_demo import make_elf,create

class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='outlands-elf-');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.libs=self.root/'libs';self.libs.mkdir()
    def file(self,name,data):
        path=self.libs/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return path
    def inspect(self,data,hashing=False):
        path=self.file('sample.elf',data);return e.inspect_file(path,e.Budget(e.Limits()),hashing)
    def scan(self,**kw):return e.analyze([self.libs],**kw)

class Parser(Fixture):
    def test_elf32_little(self):
        info=self.inspect(make_elf(['liba.so'],'libself.so',bits=32));self.assertEqual((info['class'],info['endian'],info['machine']),(32,'little',40));self.assertEqual(info['needed'],['liba.so'])
    def test_elf32_big(self):
        info=self.inspect(make_elf(['liba.so'],bits=32,endian='big'));self.assertEqual((info['class'],info['endian']),(32,'big'))
    def test_elf64_little(self):
        info=self.inspect(make_elf(['liba.so'],soname='libself.so'));self.assertEqual(info['soname'],'libself.so');self.assertEqual(info['class'],64)
    def test_elf64_big(self):
        info=self.inspect(make_elf(['liba.so'],endian='big'));self.assertEqual(info['needed'],['liba.so']);self.assertEqual(info['endian'],'big')
    def test_nonelf_ignored(self):self.assertIsNone(self.inspect(b'ordinary text'))
    def test_truncated_ident_and_headers(self):
        data=make_elf(['liba.so'])
        for end in [4,15,16,40,63,80,120,160]:
            with self.subTest(end=end),self.assertRaises(e.ParseError):self.inspect(data[:end])
    def test_class_endian_and_version_rejected(self):
        for offset,value in [(4,0),(4,3),(5,0),(5,3),(6,0)]:
            data=bytearray(make_elf());data[offset]=value
            with self.assertRaises(e.ParseError):self.inspect(data)
    def test_relocatable_core_and_extended_ph_count_rejected(self):
        for offset,value in [(16,1),(16,4),(56,0),(56,65535),(56,257),(54,55),(52,65)]:
            data=bytearray(make_elf());struct.pack_into('<H',data,offset,value)
            with self.subTest(offset=offset,value=value),self.assertRaises(e.ParseError):self.inspect(data)
    def test_virtual_string_address_is_mapped_not_file_offset(self):
        info=self.inspect(make_elf(['libmapped.so']));self.assertEqual(info['needed'],['libmapped.so'])
    def test_string_pointer_into_bss_is_not_file_backed(self):
        data=bytearray(make_elf(['liba.so']));struct.pack_into('<Q',data,512+16+8,65536+len(data)+2)
        with self.assertRaises(e.ParseError):self.inspect(data)
    def test_string_size_limit(self):
        data=bytearray(make_elf());struct.pack_into('<Q',data,512+16+8,e.MAX_STRTAB+1)
        with self.assertRaises(e.ParseError):self.inspect(data)
    def test_string_offsets_and_terminators(self):
        data=bytearray(make_elf(['liba.so']));struct.pack_into('<Q',data,520,999999)
        with self.assertRaises(e.ParseError):self.inspect(data)
        data=bytearray(make_elf(['liba.so']));data[data.index(b'liba.so')+7]=65
        with self.assertRaises(e.ParseError):self.inspect(data)
    def test_duplicate_singleton_dynamic_tag(self):
        with self.assertRaises(e.ParseError):self.inspect(make_elf(extra_tags=[(5,65536)]))
    def test_overlapping_virtual_mappings_are_ambiguous(self):
        data=bytearray(make_elf(['liba.so']));struct.pack_into('<H',data,56,3)
        # A second PT_LOAD maps the same virtual span to a different file offset.
        struct.pack_into('<IIQQQQQQ',data,64+112,1,4,1,65536,0,len(data)-1,len(data),1)
        with self.assertRaises(e.ParseError):self.inspect(data)
    def test_string_table_and_dynamic_segment_ranges(self):
        for at,value,fmt in [(512,99,'<q'),(64+56+32,15,'<Q'),(64+56+8,2**63,'<Q')]:
            data=bytearray(make_elf(['liba.so']));struct.pack_into(fmt,data,at,value)
            # Changing DT_NEEDED to an unknown tag is valid; change DT_STRTAB instead.
            if at==512:struct.pack_into('<q',data,512+16,99)
            with self.assertRaises(e.ParseError):self.inspect(data)
    def test_dynamic_null_required(self):
        data=bytearray(make_elf());struct.pack_into('<q',data,512+32,99)
        with self.assertRaises(e.ParseError):self.inspect(data)
    def test_needed_count_and_metadata_text_limits(self):
        with self.assertRaises(e.ParseError):self.inspect(make_elf(['lib.so']*257))
        for name in ['bad\nname.so','x'*1025]:
            with self.assertRaises(e.ParseError):self.inspect(make_elf([name]))
    def test_invalid_utf8_dependency(self):
        data=bytearray(make_elf(['liba.so']));data[data.index(b'liba.so')]=255
        with self.assertRaises(e.ParseError):self.inspect(data)
    def test_interpreter_and_search_paths_are_observed(self):
        info=self.inspect(make_elf(runpath='$ORIGIN/lib',rpath='/fictional/lib',interpreter='/fictional/ld.so'))
        self.assertEqual(info['interpreter'],'/fictional/ld.so');self.assertEqual(info['rpath'],'/fictional/lib');self.assertEqual(info['runpath'],'$ORIGIN/lib')
    def test_no_dynamic_segment(self):self.assertEqual(self.inspect(make_elf(dynamic=False))['metadata'],'no_dynamic_segment')
    def test_file_boundaries_and_load_alignment(self):
        for offset,value in [(64+8,99999999),(64+32,99999999),(64+40,0),(64+48,3)]:
            data=bytearray(make_elf());struct.pack_into('<Q',data,offset,value)
            with self.subTest(offset=offset),self.assertRaises(e.ParseError):self.inspect(data)
    def test_optional_sha256_independently_matches(self):
        data=make_elf(['liba.so']);self.assertEqual(self.inspect(data,True)['sha256'],hashlib.sha256(data).hexdigest())
    def test_changed_file_discards_metadata(self):
        path=self.file('change.elf',make_elf());real=e.parse_stream
        def change(stream,size,budget):
            result=real(stream,size,budget);path.write_bytes(b'changed input');return result
        with patch.object(e,'parse_stream',side_effect=change),self.assertRaises(e.InspectorError):e.inspect_file(path,e.Budget(e.Limits()))
    def test_mutated_metadata_never_unbounded_or_uncaught(self):
        original=make_elf(['liba.so'],'libself.so');rng=random.Random(611)
        for _ in range(150):
            data=bytearray(original);offset=rng.randrange(len(data));data[offset]^=rng.randrange(1,256)
            try:self.inspect(data)
            except e.InspectorError:pass

class Graph(Fixture):
    def test_unique_soname_candidate_and_closure_cycle(self):
        app=self.file('app.elf',make_elf(['liba.so']));self.file('renamed.so',make_elf(['libb.so'],'liba.so'));self.file('libb.so',make_elf(['liba.so'],'libb.so'))
        report=e.analyze([self.libs],[app]);self.assertEqual(report['status'],'NO_SCOPE_FINDINGS');self.assertEqual(report['summary']['visited_in_graph'],3);self.assertEqual(len(report['dependencies']),3)
    def test_ambiguous_candidates_not_arbitrarily_selected(self):
        self.file('app.elf',make_elf(['liba.so']));self.file('a.so',make_elf(soname='liba.so'));self.file('b.so',make_elf(soname='liba.so'))
        edge=self.scan()['dependencies'][0];self.assertEqual(edge['status'],'ambiguous_candidates');self.assertIsNone(edge['candidate']);self.assertEqual(edge['candidate_count'],2)
    def test_missing_means_unresolved_in_supplied_inputs(self):
        self.file('app.elf',make_elf(['libabsent.so']));self.assertEqual(self.scan()['dependencies'][0]['status'],'unresolved_in_supplied_inputs')
    def test_matching_name_with_wrong_architecture(self):
        self.file('app.elf',make_elf(['liba.so']));self.file('liba.so',make_elf(bits=32));self.assertEqual(self.scan()['dependencies'][0]['status'],'architecture_mismatch')
    def test_machine_and_endian_both_matter(self):
        self.file('app.elf',make_elf(['liba.so']));self.file('liba.so',make_elf(machine=62,endian='big'))
        self.assertEqual(self.scan()['dependencies'][0]['status'],'architecture_mismatch')
    def test_exec_is_not_a_shared_library_candidate(self):
        self.file('app.elf',make_elf(['liba.so']));data=bytearray(make_elf());struct.pack_into('<H',data,16,2);self.file('liba.so',data)
        self.assertEqual(self.scan()['dependencies'][0]['status'],'object_type_mismatch')
    def test_basename_soname_same_node_not_double_counted(self):
        self.file('app.elf',make_elf(['liba.so']));self.file('liba.so',make_elf(soname='liba.so'))
        self.assertEqual(self.scan()['dependencies'][0]['candidate_count'],1)
    def test_dependency_with_slash_not_path_traversal(self):
        self.file('app.elf',make_elf(['../../outside.so']));edge=self.scan()['dependencies'][0]
        self.assertEqual(edge['status'],'path_dependency_not_resolved');self.assertIsNone(edge['candidate'])
    def test_case_sensitive_names(self):
        self.file('app.elf',make_elf(['LIBA.so']));self.file('liba.so',make_elf());self.assertEqual(self.scan()['dependencies'][0]['status'],'unresolved_in_supplied_inputs')
    def test_nonelf_and_damaged_elf_coverage(self):
        self.file('readme.txt',b'not elf');self.file('broken.so',b'\x7fELF')
        report=self.scan();self.assertEqual(report['summary']['non_elf_ignored'],1);self.assertEqual(report['status'],'REVIEW_REQUIRED');self.assertTrue(report['issues'])
    def test_root_overlap_refused(self):
        sub=self.libs/'sub';sub.mkdir()
        with self.assertRaises(e.InspectorError):e.analyze([self.libs,sub])
    def test_entry_file_only_does_not_scan_siblings(self):
        app=self.file('app.elf',make_elf(['liba.so']));self.file('liba.so',make_elf())
        report=e.analyze(files=[app]);self.assertEqual(report['summary']['files_examined'],1);self.assertEqual(report['dependencies'][0]['status'],'unresolved_in_supplied_inputs')
    def test_budget_limits_preserve_partial_finding(self):
        self.file('a.elf',make_elf());self.file('b.elf',make_elf())
        report=self.scan(limits=e.Limits(max_files=1));self.assertEqual(report['status'],'REVIEW_REQUIRED');self.assertIn('FILE_COUNT_LIMIT',[i['code'] for i in report['issues']])
    def test_depth_limit_records_uninspected_directory(self):
        self.file('one/two/file.elf',make_elf());report=self.scan(limits=e.Limits(max_depth=1));self.assertIn('DEPTH_LIMIT',[i['code'] for i in report['issues']])
    def test_invalid_and_time_limits(self):
        for limit in [e.Limits(max_files=0),e.Limits(seconds=True),e.Limits(max_depth=65)]:
            with self.assertRaises(e.InspectorError):self.scan(limits=limit)
        self.file('app.elf',make_elf())
        with patch.object(e.time,'monotonic',side_effect=[0,100,100]):report=self.scan(limits=e.Limits(seconds=1))
        self.assertIn('TIME_BUDGET_REACHED',[i['code'] for i in report['issues']])
    def test_metadata_and_hash_budgets(self):
        self.file('app.elf',make_elf())
        with patch.object(e,'MAX_METADATA',1):report=self.scan()
        self.assertIn('METADATA_BYTE_BUDGET_REACHED',[i['code'] for i in report['issues']])
        with patch.object(e,'MAX_HASH',1):report=self.scan(hash_files=True)
        self.assertIn('HASH_BYTE_BUDGET_REACHED',[i['code'] for i in report['issues']])
    def test_candidate_display_is_bounded(self):
        self.file('app.elf',make_elf(['liba.so']))
        for i in range(20):self.file(str(i)+'.so',make_elf(soname='liba.so'))
        edge=self.scan()['dependencies'][0];self.assertEqual(edge['candidate_count'],20);self.assertEqual(len(edge['candidates']),16);self.assertEqual(edge['candidates_omitted'],4)
    def test_symlinks_are_not_followed_when_available(self):
        target=self.file('real.elf',make_elf());link=self.libs/'alias.so'
        try:link.symlink_to(target)
        except OSError:self.skipTest('Native symlink privilege unavailable')
        report=self.scan();self.assertIn('LINK_OR_REPARSE_SKIPPED',[i['code'] for i in report['issues']]);self.assertEqual(len(report['files']),1)
        with self.assertRaises(e.InspectorError):e.analyze(files=[link])

class Reports(Fixture):
    def test_source_unchanged_and_no_absolute_input_roots(self):
        path=self.file('app.elf',make_elf());before=path.read_bytes();report=self.scan(hash_files=True)
        self.assertEqual(before,path.read_bytes());self.assertNotIn(str(self.libs),json.dumps(report))
    def test_html_text_escaped_and_no_active_script(self):
        self.file('app.elf',make_elf(['<script>alert(1)</script>']))
        page=e.html_report(self.scan()).decode();self.assertNotIn('<script>',page);self.assertIn('&lt;script&gt;',page);self.assertNotIn('src="http',page)
    def test_report_inventory_and_independent_hash_readback(self):
        self.file('app.elf',make_elf());report=self.scan();out=self.root/'report';e.write_report(report,out,[self.libs])
        self.assertEqual({p.name for p in out.iterdir()},{'index.html','report.json','MANIFEST.json','README.txt'})
        for row in json.loads((out/'MANIFEST.json').read_text())['files']:
            raw=(out/row['path']).read_bytes();self.assertEqual(len(raw),row['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256'])
        self.assertEqual(json.loads((out/'report.json').read_text()),report)
    def test_existing_and_inside_input_outputs_refused(self):
        report=self.scan()
        with self.assertRaises(e.InspectorError):e.write_report(report,self.libs,[self.libs])
        with self.assertRaises(e.InspectorError):e.write_report(report,self.libs/'report',[self.libs])
    def test_generated_example_mixed_and_clean(self):
        for clean in (False,True):
            path=self.root/('clean' if clean else 'mixed');create(path,clean);report=e.analyze([path/'lib'],[path/'app/demo.elf'])
            self.assertEqual(report['status'],'NO_SCOPE_FINDINGS' if clean else 'REVIEW_REQUIRED')
            with self.assertRaises(e.InspectorError):create(path)
    def test_cli_exit_codes_and_new_only_reports(self):
        demo=self.root/'demo';create(demo)
        command=[sys.executable,'-B',e.__file__,'--root',str(demo/'lib'),'--file',str(demo/'app/demo.elf'),'--output',str(self.root/'cli-report')]
        first=subprocess.run(command,capture_output=True,text=True,timeout=15);self.assertEqual(first.returncode,2,first.stderr);self.assertEqual(json.loads(first.stdout)['report_files'],4)
        second=subprocess.run(command,capture_output=True,text=True,timeout=15);self.assertEqual(second.returncode,1);self.assertEqual(json.loads(second.stderr)['code'],'OUTPUT_MUST_BE_NEW_DIRECTORY')
    def test_cli_errors_omit_paths(self):
        result=subprocess.run([sys.executable,'-B',e.__file__,'--file',str(self.root/'missing')],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,1);self.assertNotIn(str(self.root),result.stderr);self.assertNotIn('Traceback',result.stderr)

class IndependentOracle(Fixture):
    def test_real_compiler_metadata_against_readelf(self):
        gcc=shutil.which('gcc');readelf=shutil.which('readelf')
        if sys.platform!='linux' or not gcc or not readelf:
            if os.environ.get('ELF_REQUIRE_ORACLE')=='1':self.fail('Linux gcc/readelf oracle required')
            self.skipTest('Independent gcc/readelf oracle requires Linux binutils and GCC')
        (self.root/'a.c').write_text('int original(void) { return 42; }\n')
        (self.root/'b.c').write_text('extern int original(void); int consumer(void) { return original(); }\n')
        for args in [[gcc,'-shared','-fPIC','-nostdlib','-Wl,-soname,liboriginal.so',str(self.root/'a.c'),'-o',str(self.libs/'renamed.so')],
                     [gcc,'-shared','-fPIC','-nostdlib',str(self.root/'b.c'),'-L'+str(self.libs),'-Wl,--no-as-needed','-l:renamed.so','-o',str(self.libs/'consumer.so')]]:
            subprocess.run(args,check=True,capture_output=True,timeout=30)
        # Both .so files are inspected only. They are never loaded, imported or run.
        native=subprocess.run([readelf,'-d',str(self.libs/'consumer.so')],check=True,capture_output=True,text=True,timeout=10).stdout
        self.assertIn('[liboriginal.so]',native)
        report=self.scan();consumer=next(f for f in report['files'] if f['name']=='consumer.so')
        self.assertEqual(consumer['needed'],['liboriginal.so']);self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')

if __name__=='__main__':unittest.main()
