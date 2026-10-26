from pathlib import Path
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from permission_diff import inspect,main
from inspection_support import TextError


def run(before,after,details=False):return inspect([('b',before.encode())],[('a',after.encode())],details)


class PermissionTests(unittest.TestCase):
    def test_numeric_normalization_and_option_order(self):
        report=run('system/bin/demo 0 2000 0755 selabel=u:object_r:demo_exec:s0 capabilities=0x0',
                   'system/bin/demo 00 02000 755 capabilities=0x0000 selabel=u:object_r:demo_exec:s0')
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS');self.assertEqual(report['comparison_counts']['unchanged'],1)

    def test_owner_group_mode_label_capability_changes(self):
        report=run('system/bin/demo 0 2000 755 selabel=u:object_r:demo_exec:s0 capabilities=0x0',
                   'system/bin/demo 1000 1001 4755 selabel=u:object_r:other_exec:s0 capabilities=0x1')
        self.assertEqual(report['changes'][0]['fields_changed'],['uid','gid','mode_octal','selabel','capabilities'])

    def test_added_removed_and_rename(self):
        report=run('system/a 0 0 644','system/b 0 0 644')
        self.assertEqual([r['kind'] for r in report['changes']],['removed','added'])

    def test_duplicates_on_either_side_never_arbitrarily_paired(self):
        for before,after in [('a 0 0 644\na 0 0 600','a 0 0 644'),('a 0 0 644','a 0 0 644\na 0 0 644')]:
            report=run(before,after);self.assertFalse(report['changes']);self.assertEqual(len(report['held_identities']),1)

    def test_unknown_fields_hold_known_path_instead_of_false_removal(self):
        report=run('system/a 0 0 644','system/a 0 0 644 unknown=fictional')
        self.assertFalse(report['changes']);self.assertEqual(report['held_identities'][0]['reason'],'unsupported_declaration')
        self.assertEqual(report['status'],'REVIEW_REQUIRED')

    def test_unknown_path_cannot_create_false_unmatched_removal(self):
        report=run('system/demo 0 0 644','system/./demo 0 0 644')
        self.assertFalse(report['changes']);self.assertEqual(report['held_identities'][0]['reason'],'uninspected_identity_on_opposite_side')

    def test_malformed_numeric_fields_keep_known_identity(self):
        for value in ('system/a root 0 644','system/a 0 -1 644','system/a 0 0 rwx','system/a 0 0 100644','system/a 0','system/a 4294967296 0 644'):
            report=run('system/a 0 0 644',value)
            self.assertTrue(report['coverage_issues']);self.assertFalse(report['changes']);self.assertEqual(len(report['held_identities']),1)

    def test_optional_omission_is_not_assumed_zero_or_a_default_label(self):
        report=run('a 0 0 644','a 0 0 644 capabilities=0x0')
        self.assertEqual(report['changes'][0]['fields_changed'],['capabilities'])
        self.assertEqual(run('a 0 0 644','a 0 0 644')['status'],'NO_SCOPE_FINDINGS')

    def test_duplicate_and_malformed_optional_fields_held(self):
        for suffix in ('capabilities=0x0 capabilities=0x1','capabilities=-1','capabilities=1','capabilities=0x10000000000000000','selabel=not-context','selabel=u:object_r:a:s0 selabel=u:object_r:b:s0'):
            report=run('a 0 0 644','a 0 0 644 '+suffix)
            self.assertTrue(report['coverage_issues']);self.assertFalse(report['changes'])

    def test_selinux_categories_are_literal(self):
        report=run('a 0 0 644 selabel=u:object_r:demo:s0:c1,c2','a 0 0 644 selabel=u:object_r:demo:s0:c2,c1')
        self.assertEqual(report['changes'][0]['fields_changed'],['selabel'])

    def test_uint64_capability_values_preserved_as_hex_strings(self):
        report=run('a 0 0 644 capabilities=0xFFFFFFFFFFFFFFFF','a 0 0 644 capabilities=0xffffffffffffffff',True)
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')
        self.assertEqual(report['records'][0]['fields']['capabilities'],'0xffffffffffffffff')

    def test_paths_are_relative_literal_case_sensitive(self):
        for path in ('../a','/a','a//b','a/./b','a\\b','a:stream','a/../b'):
            report=run('',path+' 0 0 644');self.assertTrue(report['coverage_issues']);self.assertFalse(report['records'])
        self.assertEqual(len(run('a/File 0 0 644','a/file 0 0 644')['changes']),2)

    def test_reordering_comments_and_whitespace_are_not_value_changes(self):
        report=run('a 0 0 644\nb 0 0 755','# generated\n b\t0 0 0755\na 0 0 0644')
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')

    def test_inline_comments_and_escaped_paths_are_unsupported(self):
        self.assertTrue(run('a 0 0 644','a 0 0 644 # comment')['coverage_issues'])
        self.assertTrue(run('',r'my\040file 0 0 644')['coverage_issues'])

    def test_duplicate_across_selected_inputs(self):
        report=inspect([('b',b'a 0 0 644')],[('a',b'a 0 0 644'),('a2',b'a 0 0 600')])
        self.assertEqual(len(report['held_identities']),1);self.assertEqual(len(report['inputs']),3)

    def test_private_identity_fields_opt_in(self):
        value='system/private_demo 1000 2000 755 selabel=u:object_r:fictional_exec:s0'
        self.assertNotIn('private_demo',json.dumps(run(value,value)))
        report=run(value,value,True);self.assertEqual(report['records'][0]['fields']['uid'],1000)
        self.assertIn('fictional_exec',json.dumps(report))

    def test_no_filesystem_lookup_or_permission_application(self):
        report=run('fictional/not-existing 0 0 7777','fictional/not-existing 0 0 7777')
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS');self.assertIn('no filesystem or policy evaluation',report['scope'])

    def test_bounds_and_encoding_fail_closed(self):
        for data in (b'\0',b'\xff',b'a'*8193):
            with self.assertRaises(TextError):inspect([('b',b'')],[('a',data)])

    def test_empty_snapshots_and_unsupported_only_snapshot(self):
        self.assertEqual(run('','# generated')['status'],'NO_SCOPE_FINDINGS')
        self.assertEqual(run('','unsupported row')['status'],'REVIEW_REQUIRED')

    def test_real_cli_examples_and_source_immutability(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder).resolve()
            subprocess.run([sys.executable,'-B',str(ROOT/'examples/generate.py'),'--output',str(base/'fixtures')],check=True,capture_output=True)
            before=base/'fixtures/before.txt';original=before.read_bytes()
            for name,expected in [('same',0),('changed',1),('review',1)]:
                result=subprocess.run([sys.executable,'-B',str(ROOT/'permission_diff.py'),'--before',str(before),'--after',str(base/f'fixtures/{name}.txt'),'--output',str(base/name)],capture_output=True,text=True)
                self.assertEqual(result.returncode,expected,result.stdout+result.stderr);self.assertNotIn(str(base),result.stdout)
            self.assertEqual(before.read_bytes(),original)

    def test_private_fixed_errors_and_fresh_output(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder).resolve();before=base/'before';after=base/'after'
            before.write_text('a 0 0 644',encoding='utf-8');after.write_text('a 0 0 600',encoding='utf-8')
            capture=io.StringIO();args=['--before',str(before),'--after',str(after),'--output',str(base/'out')]
            with contextlib.redirect_stdout(capture):self.assertEqual(main(args),1)
            with contextlib.redirect_stdout(capture):self.assertEqual(main(args),2)
            self.assertNotIn(str(base),capture.getvalue());self.assertTrue((base/'out/report.html').is_file())


if __name__=='__main__':unittest.main()
