"""Original nineteen fictional audit fixtures, isolated from unrelated tools."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('audit_original_fixture',Path(__file__).resolve().parents[1]/'release_audit.py')
audit=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)

class Fixture(unittest.TestCase):
    def setUp(self):
        temp_parent=Path(os.environ.get('OUTLANDS_TEST_TEMP',tempfile.gettempdir())).resolve()
        self.temporary=tempfile.TemporaryDirectory(dir=temp_parent)
        def cleanup():
            target=Path(self.temporary.name).resolve()
            if target==temp_parent or not target.is_relative_to(temp_parent):raise RuntimeError('UNEXPECTED_CLEANUP_TARGET')
            self.temporary.cleanup()
        self.addCleanup(cleanup)
        self.parent=Path(self.temporary.name);self.root=self.parent/'export';self.root.mkdir()
    def write(self,name,text):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text,encoding='utf-8');return path
    def skipTest(self, reason):
        if reason == 'Native symlink creation unavailable':
            error = sys.exception()
            if (os.name == 'nt' and isinstance(error,OSError) and getattr(error,'winerror',None) == 1314
                    and os.environ.get('OUTLANDS_AUDIT_REQUIRE_LINKS') != '1'):
                return super().skipTest(reason)
            raise AssertionError('Native symlink fixture creation failed') from error
        return super().skipTest(reason)


class AuditTests(Fixture):
    def test_empty_tree_has_no_findings(self):
        self.assertEqual(audit.inspect(self.root)['status'],'NO_PATTERN_FINDINGS')
    def test_detects_generated_credential_without_disclosing_it(self):
        value='gh'+'p_'+'A'*36;self.write('example.txt',value)
        result=audit.inspect(self.root)
        self.assertIn('CREDENTIAL_SHAPE',[x['rule'] for x in result['findings']])
        self.assertNotIn(value,json.dumps(result))
    def test_detects_generated_key_header(self):
        self.write('example.txt','-----BEGIN '+'OPENSSH '+'PRIVATE KEY-----')
        self.assertEqual(audit.inspect(self.root)['findings'][0]['rule'],'PRIVATE_KEY')
    def test_real_addresses_flagged_documentation_addresses_allowed(self):
        self.assertTrue(audit.inspect_text('10.'+'20.30.40'))
        self.assertTrue(audit.inspect_text('8.'+'8.8.8'))
        self.assertFalse(audit.inspect_text('127.0.0.1 192.0.2.10 198.51.100.10 203.0.113.10'))
    def test_email_examples_allowed(self):
        self.assertFalse(audit.inspect_text('reviewer@example.com'))
        self.assertTrue(audit.inspect_text('person'+'@'+'private.invalid'))
    def test_internal_hosts_url_credentials_and_ipv6(self):
        self.assertTrue(audit.inspect_text('https://'+'service'+'.internal/'))
        self.assertTrue(audit.inspect_text('https://'+'name:fictional'+'@example.com/'))
        self.assertTrue(audit.inspect_text('https://'+'intranet'+'/'))
        self.assertTrue(audit.inspect_text('fd'+'12:3456::1'))
        self.assertFalse(audit.inspect_text('::1 2001:db8::10'))
    def test_private_literals_checked_in_content_and_filenames(self):
        self.write('restricted-project.md','restricted-project')
        rules={x['rule'] for x in audit.inspect(self.root,['restricted-project'])['findings']}
        self.assertIn('PRIVATE_LITERAL',rules);self.assertIn('PATH_PRIVATE_LITERAL',rules)
    def test_sensitive_files_not_read(self):
        self.write('.env','fictional')
        result=audit.inspect(self.root)
        self.assertEqual(result['inventory'],[])
        self.assertIn('SENSITIVE_FILENAME',[x['rule'] for x in result['findings']])
    def test_archives_and_non_utf8_require_review(self):
        (self.root/'sample.zip').write_bytes(b'PK')
        (self.root/'sample.txt').write_bytes(b'\xff')
        rules={x['rule'] for x in audit.inspect(self.root)['findings']}
        self.assertEqual(rules,{'BINARY_OR_UNKNOWN_FORMAT_REVIEW','NON_UTF8_REVIEW'})
    def test_existing_git_metadata_is_declared_excluded(self):
        self.write('.git/config','fictional')
        result=audit.inspect(self.root)
        self.assertEqual(result['excluded'],['.git']);self.assertFalse(result['findings'])
    def test_nested_git_and_runtime_are_flagged(self):
        self.write('nested/.git/config','fictional');self.write('runtime/data.txt','fictional')
        rules=[x['rule'] for x in audit.inspect(self.root)['findings']]
        self.assertEqual(rules.count('PRIVATE_OR_RUNTIME_DIRECTORY'),2)
    def test_size_limit_requires_review(self):
        self.write('large.txt','x'*(audit.MAX_FILE+1))
        self.assertEqual(audit.inspect(self.root)['findings'][0]['rule'],'SIZE_LIMIT')
    def test_null_bytes_require_review(self):
        self.write('sample.txt','hello\x00world')
        self.assertEqual(audit.inspect(self.root)['findings'][0]['rule'],'BINARY_CONTENT_REVIEW')
    def test_read_only_inventory_does_not_change_input(self):
        path=self.write('sample.md','hello');before=(path.stat().st_mtime_ns,path.read_bytes())
        audit.inspect(self.root)
        self.assertEqual((path.stat().st_mtime_ns,path.read_bytes()),before)
        self.assertEqual(len(list(self.root.iterdir())),1)
    def test_manifest_detects_added_and_changed_files(self):
        path=self.write('sample.md','hello')
        manifest=self.parent/'manifest.json'
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(audit.main(['--root',str(self.root),'--write-manifest',str(manifest)]),0)
            self.assertEqual(audit.main(['--root',str(self.root),'--manifest',str(manifest)]),0)
            self.write('extra.md','extra')
            self.assertEqual(audit.main(['--root',str(self.root),'--manifest',str(manifest)]),1)
            path.write_text('changed',encoding='utf-8')
            self.assertEqual(audit.main(['--root',str(self.root),'--manifest',str(manifest)]),1)
    def test_manifest_cannot_traverse_or_duplicate_case(self):
        for paths in [['../escape'],['a.md','A.md']]:
            data=dict(schema_version=1,inventory=[dict(path=p,size=0,sha256='0'*64) for p in paths])
            with self.assertRaises(audit.AuditError):audit.validate_manifest(data)
    def test_reports_outside_tree_and_no_overwrite(self):
        with self.assertRaises(audit.AuditError):audit.write_new(self.root/'report.json',{},self.root)
        output=self.parent/'report.json';audit.write_new(output,{},self.root)
        with self.assertRaises(FileExistsError):audit.write_new(output,{},self.root)
    def test_cli_errors_omit_selected_path(self):
        private_path=self.parent/'absent';output=io.StringIO()
        with contextlib.redirect_stdout(output):code=audit.main(['--root',str(private_path)])
        self.assertEqual(code,2);self.assertNotIn(str(private_path),output.getvalue())
    def test_link_is_not_followed(self):
        target=self.parent/'target.txt';target.write_text('private',encoding='utf-8')
        try:os.symlink(target,self.root/'link.txt')
        except OSError:self.skipTest('Native symlink creation unavailable')
        result=audit.inspect(self.root)
        self.assertEqual(result['inventory'],[])
        self.assertEqual(result['findings'][0]['rule'],'LINK_OR_REPARSE')

if __name__=='__main__':unittest.main()
