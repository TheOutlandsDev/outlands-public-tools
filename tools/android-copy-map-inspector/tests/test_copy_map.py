from pathlib import Path
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from copy_map_inspector import inspect, main, relative, roots_from_bytes
from text_support import TextError


def run(text, roots=None, details=False): return inspect([('input-0001',text.encode())],roots,details)


class CopyMapTests(unittest.TestCase):
    def test_literal_continuation_and_comment(self):
        report=run('PRODUCT_COPY_FILES += \\\n  fictional/a:vendor/a \\\n  fictional/b:vendor/b:owner # comment\n')
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS'); self.assertEqual(len(report['entries']),2)
        self.assertNotIn('fictional',json.dumps(report)); self.assertTrue(report['entries'][1]['owner_present'])

    def test_dangling_and_interrupted_continuation(self):
        for text in ('PRODUCT_COPY_FILES += \\', 'PRODUCT_COPY_FILES += \\\n# interrupted\na:b'):
            report=run(text); self.assertEqual(report['status'],'REVIEW_REQUIRED'); self.assertFalse(report['entries'])

    def test_explicit_roots_only(self):
        text='PRODUCT_COPY_FILES += $(LOCAL_PATH)/a:$(TARGET_COPY_OUT_VENDOR)/a'
        self.assertTrue(run(text)['coverage_issues'])
        report=run(text,{'LOCAL_PATH':'fictional','TARGET_COPY_OUT_VENDOR':'vendor'},True)
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')
        self.assertEqual(report['entries'][0]['resolved_destination'],'vendor/a')

    def test_roots_strict_schema(self):
        good=b'{"schema_version":1,"roots":{"LOCAL_PATH":"fictional"}}'
        self.assertEqual(roots_from_bytes(good),{'LOCAL_PATH':'fictional'})
        for bad in (b'{}',b'{"schema_version":true,"roots":{}}',b'{"schema_version":1,"roots":{"LOCAL_PATH":"../bad"}}',b'{"schema_version":1,"roots":{},"extra":0}',b'{"schema_version":1,"roots":{"bad":"a"}}'):
            with self.assertRaises(TextError): roots_from_bytes(bad)

    def test_traversal_absolute_and_reserved(self):
        for value in ('../a','/a','C:/a','a//b','a/./b','a\\b','a/NUL.txt','a/trailing.','a/ trailing','a/*','a:stream'):
            self.assertFalse(relative(value),value)
        self.assertTrue(relative('fictional/naive-file.bin'))
        for word in ('a:../escape','../source:dest','/source:dest','a:CON','a:a//b'):
            self.assertTrue(run('PRODUCT_COPY_FILES += '+word)['coverage_issues'])

    def test_conflict_classification(self):
        report=run('PRODUCT_COPY_FILES += a:vendor/a a:vendor/a b:vendor/a c:Vendor/A d:vendor/a/child')
        codes={r['code'] for r in report['conflicts']}
        self.assertEqual(codes,{'DUPLICATE_DECLARED_COPY','DECLARED_DESTINATION_CONFLICT','PORTABILITY_DESTINATION_COLLISION','FILE_PARENT_DESTINATION_CONFLICT'})

    def test_normalization_and_owner_conflict(self):
        report=run('PRODUCT_COPY_FILES += a:vendor/caf\u00e9 b:vendor/cafe\u0301 a:vendor/x:one a:vendor/x:two')
        self.assertEqual({r['code'] for r in report['conflicts']},{'PORTABILITY_DESTINATION_COLLISION','DECLARED_DESTINATION_CONFLICT'})

    def test_no_function_or_condition_evaluation(self):
        report=run('ifeq ($(MODE),yes)\nPRODUCT_COPY_FILES += $(shell touch /fictional/marker):vendor/a\nendif\ninclude private.mk\nPRODUCT_COPY_FILES := a:b')
        self.assertTrue(report['coverage_issues']); self.assertTrue(all(r['resolution']=='unresolved' for r in report['entries']))

    def test_assignment_does_not_hide_other_declarations(self):
        report=run('PRODUCT_COPY_FILES += a:b\nPRODUCT_COPY_FILES := c:d\nPRODUCT_COPY_FILES += e:b')
        self.assertEqual(len(report['entries']),2); self.assertEqual(len(report['conflicts']),1)
        self.assertTrue(report['coverage_issues'])

    def test_invalid_words_quotes_and_nested_expansions(self):
        for value in ('no-colon','a:b:owner:extra','a:b:bad!owner','"a:b"','a\\ b:c','$(nested$(NAME))/a:b','a/$(NAME):b'):
            self.assertTrue(run('PRODUCT_COPY_FILES += '+value)['coverage_issues'],value)

    def test_comments_and_empty_append(self):
        self.assertEqual(run('# generated\nPRODUCT_COPY_FILES += # empty')['status'],'NO_SCOPE_FINDINGS')

    def test_details_are_explicit(self):
        text='PRODUCT_COPY_FILES += fictional/source:vendor/private-path:owner'
        self.assertNotIn('private-path',json.dumps(run(text)))
        self.assertIn('private-path',json.dumps(run(text,details=True)))

    def test_function_fragments_never_become_literal_entries(self):
        report=run('PRODUCT_COPY_FILES += $(shell echo fictional:vendor/fake)')
        self.assertFalse(report['entries']); self.assertTrue(report['coverage_issues'])

    def test_nonbreaking_space_is_path_data(self):
        report=run('PRODUCT_COPY_FILES += fictional/caf\u00a0e:vendor/caf\u00a0e',details=True)
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')
        self.assertEqual(report['entries'][0]['resolved_destination'],'vendor/caf\u00a0e')

    def test_escaped_comment_cannot_become_a_continuation(self):
        report=run('PRODUCT_COPY_FILES += fictional/a:vendor/a\\#literal\n fictional/b:vendor/b')
        self.assertFalse(report['entries']); self.assertEqual(report['status'],'REVIEW_REQUIRED')
        self.assertIn('QUOTING_OR_ESCAPING_UNSUPPORTED',{r['code'] for r in report['coverage_issues']})

    def test_empty_fold_retains_start_and_interruption(self):
        report=run('\\\nPRODUCT_COPY_FILES += a:b')
        self.assertEqual(report['entries'][0]['line'],1)
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')
        self.assertTrue(run('\\\n# interrupted')['coverage_issues'])

    def test_cli_roots_and_private_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder).resolve(); source=base/'input.mk'; source.write_text('PRODUCT_COPY_FILES += a:b',encoding='utf-8')
            roots=base/'roots.json'; roots.write_text('{"schema_version":1,"roots":{}}',encoding='utf-8')
            capture=io.StringIO()
            with contextlib.redirect_stdout(capture): result=main(['--file',str(source),'--roots',str(roots),'--output',str(base/'out')])
            self.assertEqual(result,0); self.assertNotIn(str(base),capture.getvalue())
            report=json.loads((base/'out/report.json').read_text()); self.assertIn('roots_input',report)
            roots.write_text('{bad',encoding='utf-8'); capture=io.StringIO()
            with contextlib.redirect_stdout(capture): result=main(['--file',str(source),'--roots',str(roots),'--output',str(base/'fail')])
            self.assertEqual(result,2); self.assertFalse((base/'fail').exists()); self.assertNotIn(str(base),capture.getvalue())

    def test_real_cli_generated_examples(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder).resolve()
            subprocess.run([sys.executable,'-B',str(ROOT/'examples/generate.py'),'--output',str(base/'fixtures')],check=True,capture_output=True)
            for name,expected in [('clean.mk',0),('review.mk',1)]:
                result=subprocess.run([sys.executable,'-B',str(ROOT/'copy_map_inspector.py'),'--file',str(base/'fixtures'/name),'--output',str(base/name)],capture_output=True,text=True)
                self.assertEqual(result.returncode,expected,result.stdout+result.stderr)


if __name__ == '__main__': unittest.main()
