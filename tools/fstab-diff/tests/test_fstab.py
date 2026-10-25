from pathlib import Path
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from fstab_diff import inspect, main
from text_support import TextError


def run(before,after,mode='linux',details=False): return inspect(before.encode(),after.encode(),mode,details)


class FstabTests(unittest.TestCase):
    def test_linux_defaults_and_numeric_equivalence(self):
        report=run('UUID=fiction / ext4 defaults','UUID=fiction / ext4 defaults 00 000')
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS'); self.assertFalse(report['changes'])

    def test_comments_escapes_and_embedded_hash(self):
        text='sshfs#fiction /mnt/my\\040disk fuse defaults 0 0 # generated'
        report=run(text,'# comment\n'+text,details=True)
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')
        self.assertEqual(report['records'][0]['fields']['target'],'/mnt/my disk')
        self.assertEqual(report['records'][0]['fields']['source'],'sshfs#fiction')

    def test_changed_source_type_flags_and_pass(self):
        report=run('a /x ext4 rw 0 0','b /x xfs ro 0 1')
        self.assertEqual(report['changes'][0]['fields_changed'],['source','fstype','options','pass_number'])
        self.assertNotIn('/x',json.dumps(report)); self.assertEqual(report['status'],'REVIEW_REQUIRED')

    def test_added_removed_and_target_rename(self):
        report=run('a /old ext4 rw','a /new ext4 rw')
        self.assertEqual([r['kind'] for r in report['changes']],['removed','added'])
        self.assertFalse(report['relative_order_changed'])

    def test_addition_not_reorder(self):
        report=run('a /a ext4 rw\nb /b ext4 rw','x /x ext4 rw\na /a ext4 rw\nb /b ext4 rw')
        self.assertFalse(report['relative_order_changed']); self.assertEqual(len(report['changes']),1)

    def test_relative_common_order(self):
        report=run('a /a ext4 rw\nb /b ext4 rw','b /b ext4 rw\na /a ext4 rw')
        self.assertTrue(report['relative_order_changed']); self.assertFalse(report['changes'])

    def test_duplicates_never_arbitrarily_paired(self):
        report=run('a /same ext4 rw\nb /same ext4 rw','a /same ext4 ro\nc /else ext4 rw')
        self.assertEqual(len(report['ambiguous_targets']),1)
        self.assertEqual([r['kind'] for r in report['changes']],['added'])
        self.assertFalse(report['relative_order_changed'])

    def test_duplicate_target_on_after_only(self):
        report=run('a /same ext4 rw','a /same ext4 rw\nb /same ext4 rw')
        self.assertFalse(report['changes']); self.assertEqual(len(report['ambiguous_targets']),1)

    def test_android_fs_mgr_flags_are_distinct(self):
        report=run('/fiction /data ext4 rw wait,check','/fiction /data ext4 rw wait,check,quota','android',True)
        self.assertEqual(report['changes'][0]['fields_changed'],['fs_mgr_flags'])
        self.assertEqual(report['records'][0]['fields']['fs_mgr_flags'],'wait,check')

    def test_option_order_and_duplicates_preserved(self):
        self.assertEqual(run('a /a ext4 rw,noatime','a /a ext4 noatime,rw')['changes'][0]['fields_changed'],['options'])
        self.assertTrue(run('a /a ext4 rw,rw','a /a ext4 rw,rw')['findings'])
        self.assertTrue(run('a /a ext4 rw,','a /a ext4 rw,')['findings'])

    def test_malformed_rows_coverage_even_if_both_same(self):
        for text in ('not enough fields','a /a ext4 rw 0 0 extra','a /a ext4 rw -1 0','a /a ext4 rw 999999 0','a /a ext4 rw nope','a /my\\041disk ext4 rw','a /bad\\x ext4 rw'):
            report=run(text,text)
            self.assertEqual(report['status'],'REVIEW_REQUIRED',text); self.assertTrue(report['coverage_issues'])

    def test_android_exact_field_count(self):
        for text in ('a /a ext4 rw','a /a ext4 rw wait extra'):
            self.assertTrue(run(text,text,'android')['coverage_issues'])

    def test_nonbreaking_space_does_not_split_a_target(self):
        report=run('a /my\u00a0disk ext4 rw','a /my\u00a0disk ext4 rw',details=True)
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')
        self.assertEqual(report['records'][0]['fields']['target'],'/my\u00a0disk')

    def test_explicit_format_and_empty(self):
        with self.assertRaises(TextError): run('','','guess')
        self.assertEqual(run('','# generated')['status'],'NO_SCOPE_FINDINGS')

    def test_cli_errors_and_privacy(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder).resolve(); before=base/'before'; after=base/'after'
            before.write_text('secret /private ext4 rw',encoding='utf-8'); after.write_text('secret /private ext4 ro',encoding='utf-8')
            capture=io.StringIO()
            with contextlib.redirect_stdout(capture): result=main(['--before',str(before),'--after',str(after),'--format','linux','--output',str(base/'out')])
            self.assertEqual(result,1); self.assertNotIn(str(base),capture.getvalue())
            self.assertNotIn('secret',(base/'out/report.json').read_text())
            capture=io.StringIO()
            with contextlib.redirect_stdout(capture): result=main(['--before',str(before),'--after',str(after),'--output',str(base/'fail')])
            self.assertEqual(result,2); self.assertFalse((base/'fail').exists())

    def test_real_cli_generated_examples(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder).resolve()
            subprocess.run([sys.executable,'-B',str(ROOT/'examples/generate.py'),'--output',str(base/'fixtures')],check=True,capture_output=True)
            for mode in ('linux','android'):
                for version,expected in [('same',0),('changed',1)]:
                    result=subprocess.run([sys.executable,'-B',str(ROOT/'fstab_diff.py'),'--before',str(base/f'fixtures/{mode}-before.fstab'),'--after',str(base/f'fixtures/{mode}-{version}.fstab'),'--format',mode,'--output',str(base/f'{mode}-{version}')],capture_output=True,text=True)
                    self.assertEqual(result.returncode,expected,result.stdout+result.stderr)


if __name__ == '__main__': unittest.main()
