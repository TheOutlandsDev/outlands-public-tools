from pathlib import Path
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from property_diff import inspect,main
from inspection_support import TextError


def run(before,after,details=False):return inspect([('b',before.encode())],[('a',after.encode())],details)


class PropertyTests(unittest.TestCase):
    def test_comments_whitespace_and_reordering_do_not_change_unique_values(self):
        report=run('# generated\nro.demo.a = first\npersist.demo.b=second\n','persist.demo.b = second\nro.demo.a=first')
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS');self.assertEqual(report['comparison_counts']['unchanged'],2)

    def test_added_removed_changed_and_renamed_keys(self):
        report=run('demo.removed=old\ndemo.changed=one\ndemo.before=same','demo.added=new\ndemo.changed=two\ndemo.after=same')
        self.assertEqual([r['kind'] for r in report['changes']],['removed','changed','removed','added','added'])
        self.assertEqual(report['changes'][1]['fields_changed'],['value'])

    def test_duplicate_key_is_held_even_when_values_identical(self):
        for after in ('demo.a=one\ndemo.a=one','demo.a=one\ndemo.a=two'):
            report=run('demo.a=one',after)
            self.assertEqual(len(report['held_identities']),1);self.assertFalse(report['changes'])
            self.assertEqual(report['status'],'REVIEW_REQUIRED')

    def test_duplicates_on_before_do_not_invent_add_or_remove(self):
        report=run('demo.a=one\ndemo.a=two','')
        self.assertFalse(report['changes']);self.assertEqual(len(report['held_identities']),1)

    def test_duplicate_across_selected_files(self):
        report=inspect([('b',b'demo.a=one')],[('a',b'demo.a=one'),('other',b'demo.a=two')])
        self.assertEqual(len(report['held_identities']),1)
        self.assertEqual(len(report['inputs']),3)

    def test_import_is_coverage_never_loaded(self):
        report=run('demo.a=one','import /fictional/not-opened.prop\ndemo.a=one')
        self.assertFalse(report['changes']);self.assertEqual(report['coverage_issues'][0]['code'],'PROPERTY_IMPORT_NOT_FOLLOWED')

    def test_unidentified_opposite_side_holds_unmatched_add_remove(self):
        for before,after in [('demo.a=one','import /fictional/not-followed.prop'),('unsupported row','demo.a=one')]:
            report=run(before,after);self.assertFalse(report['changes'])
            self.assertEqual(report['held_identities'][0]['reason'],'uninspected_identity_on_opposite_side')

    def test_matched_supported_change_remains_visible_with_unrelated_coverage(self):
        report=run('demo.a=one\ndemo.b=one','demo.a=two\nunsupported row')
        self.assertEqual(len(report['changes']),1);self.assertEqual(len(report['held_identities']),1)

    def test_unsupported_lines_and_keys_are_visible(self):
        for text in ('[section]','demo a=one','=one','demo/a=one','a'*129+'=one'):
            report=run('',text);self.assertTrue(report['coverage_issues'],text);self.assertEqual(report['status'],'REVIEW_REQUIRED')

    def test_first_equal_and_hash_are_literal_value_data(self):
        report=run('demo.a=one=two#literal','demo.a=one=two#literal',True)
        self.assertEqual(report['records'][0]['fields']['value'],'one=two#literal')
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')

    def test_quotes_backslashes_and_dollar_signs_are_not_evaluated(self):
        for value in ('"fictional value"','${fictional}','trailing\\',"'quoted'"):
            report=run('demo.a='+value,'demo.a='+value,True)
            self.assertEqual(report['records'][0]['fields']['value'],value);self.assertFalse(report['changes'])

    def test_empty_values_are_supported_and_distinct_from_absence(self):
        self.assertEqual(run('demo.a=','demo.a=')['status'],'NO_SCOPE_FINDINGS')
        self.assertEqual(run('','demo.a=')['changes'][0]['kind'],'added')

    def test_keys_are_literal_case_sensitive_and_values_trim_only_ascii(self):
        self.assertEqual(len(run('demo.A=one','demo.a=one')['changes']),2)
        report=run('demo.a=one','demo.a=one\u00a0',True)
        self.assertEqual(report['changes'][0]['fields_changed'],['value'])

    def test_no_runtime_property_semantics_inferred(self):
        report=run('ro.demo.value=one\nctl.demo=one','ro.demo.value=one\nctl.demo=one')
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')
        self.assertIn('no import/override/order/permission/runtime evaluation',report['scope'])

    def test_private_keys_and_values_only_in_opt_in_report(self):
        left='persist.fictional.identifier=fictional-value'
        self.assertNotIn('fictional',json.dumps(run(left,left)))
        self.assertIn('fictional-value',json.dumps(run(left,left,True)))

    def test_utf8_bom_crlf_and_final_line(self):
        report=inspect([('b',b'\xef\xbb\xbfdemo.a=one\r\n')],[('a',b'demo.a=one')])
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')

    def test_controls_and_bounds_fail_instead_of_truncating(self):
        for value in (b'demo.a=\0',b'\xff',b'demo.a='+b'x'*8193):
            with self.assertRaises(TextError):inspect([('b',b'')],[('a',value)])

    def test_empty_selected_snapshots(self):
        self.assertEqual(run('','# generated')['status'],'NO_SCOPE_FINDINGS')

    def test_real_cli_examples_preserve_inputs_and_exit_codes(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder).resolve()
            subprocess.run([sys.executable,'-B',str(ROOT/'examples/generate.py'),'--output',str(base/'fixtures')],check=True,capture_output=True)
            before=base/'fixtures/before.prop';original=before.read_bytes()
            for name,expected in [('same',0),('changed',1),('review',1)]:
                result=subprocess.run([sys.executable,'-B',str(ROOT/'property_diff.py'),'--before',str(before),'--after',str(base/f'fixtures/{name}.prop'),'--output',str(base/name)],capture_output=True,text=True)
                self.assertEqual(result.returncode,expected,result.stdout+result.stderr);self.assertNotIn(str(base),result.stdout)
            self.assertEqual(before.read_bytes(),original)

    def test_private_error_codes_and_escaped_detail_report(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder).resolve();before=base/'before';after=base/'after'
            before.write_text('demo.a=old',encoding='utf-8');after.write_text('demo.a=</pre><script>fictional</script>',encoding='utf-8')
            capture=io.StringIO();args=['--before',str(before),'--after',str(after),'--output',str(base/'out'),'--include-details']
            with contextlib.redirect_stdout(capture):self.assertEqual(main(args),1)
            self.assertNotIn('<script>',(base/'out/report.html').read_text());self.assertIn('&lt;script&gt;',(base/'out/report.html').read_text())
            with contextlib.redirect_stdout(capture):self.assertEqual(main(args),2)
            self.assertNotIn(str(base),capture.getvalue())


if __name__=='__main__':unittest.main()
