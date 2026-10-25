"""Disposable checks for the newly added tools; never imports private sources."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

def load(name,relative):
    spec=importlib.util.spec_from_file_location(name,ROOT/relative)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

audit=load('release_audit','tools/public-release-audit/release_audit.py')
workspace=load('workspace','tools/project-workspace/workspace.py')
docs=load('docs_check','tools/documentation-check/docs_check.py')
helpers=load('helpers','tools/python-helpers/helpers.py')
review_store=load('review_store','systems/dataset-review/review_store.py')

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

class WorkspaceTests(Fixture):
    def test_default_plan_has_no_writes(self):
        self.assertEqual(workspace.create(self.root,'demo')['status'],'PLAN_ONLY')
        self.assertEqual(list(self.root.iterdir()),[])
    def test_created_copies_are_byte_identical_and_neutrally_named(self):
        source=self.parent/'input.txt';data=b'fictional input\r\n';source.write_bytes(data)
        result=workspace.create(self.root,'demo',source,True)
        self.assertTrue(result['source_verified'])
        for folder in ('original','working'):self.assertEqual((self.root/'demo'/folder/'intake.bin').read_bytes(),data)
        metadata=json.loads((self.root/'demo/original/SOURCE.json').read_text())
        self.assertEqual(metadata['sha256'],hashlib.sha256(data).hexdigest())
        self.assertNotIn(str(source),(self.root/'demo/CONTROL.md').read_text())
        self.assertEqual(source.read_bytes(),data)
    def test_existing_workspace_not_overwritten(self):
        workspace.create(self.root,'demo',commit=True)
        with self.assertRaises(workspace.WorkspaceError):workspace.create(self.root,'demo',commit=True)
        self.assertTrue((self.root/'demo/CONTROL.md').exists())
    def test_invalid_and_reserved_names_rejected(self):
        for name in ('../escape','CON','con','a/b','hidden.name',''):
            with self.subTest(name=name),self.assertRaises(workspace.WorkspaceError):workspace.create(self.root,name,commit=True)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_invalid_source_does_not_create_partial_workspace(self):
        with self.assertRaises(OSError):workspace.create(self.root,'demo',self.parent/'missing',True)
        self.assertFalse((self.root/'demo').exists())
    def test_workspace_has_private_ignore_default(self):
        workspace.create(self.root,'demo',commit=True)
        self.assertEqual((self.root/'demo/.gitignore').read_text(),'*\n')

class DocumentationTests(Fixture):
    def test_local_links_and_valid_json(self):
        self.write('README.md','[usage](docs/usage.md)\n[site](https://example.org)')
        self.write('docs/usage.md','# Usage');self.write('sample.json','{"demo":true}')
        self.assertEqual(docs.check(self.root)['status'],'PASS')
    def test_missing_escaping_and_local_absolute_links_fail(self):
        self.write('README.md','[missing](absent.md)\n[escape](../outside.md)')
        self.assertEqual(len(docs.check(self.root)['findings']),2)
    def test_fenced_and_inline_code_not_treated_as_links(self):
        self.write('README.md','```text\n[x](missing)\n```\n`[x](missing)`')
        self.assertEqual(docs.check(self.root)['status'],'PASS')
    def test_json_nonstandard_constants_rejected(self):
        self.write('sample.json','{"demo":NaN}')
        self.assertEqual(docs.check(self.root)['findings'][0]['rule'],'INVALID_JSON')
    def test_reference_and_encoded_links(self):
        self.write('README.md','[ref]: <some%20file.md>\n[ref]')
        self.write('some file.md','# Demo')
        self.assertEqual(docs.check(self.root)['status'],'PASS')

class HelperTests(Fixture):
    def test_nested_redaction_preserves_original(self):
        value={'items':[{'API-Key':'x'*16}],'visible':'hello'}
        redacted=helpers.redact_structure(value)
        self.assertEqual(redacted['items'][0]['API-Key'],'<redacted>')
        self.assertEqual(value['items'][0]['API-Key'],'x'*16)
    def test_redaction_does_not_claim_free_text_anonymity(self):
        self.assertEqual(helpers.redact_structure({'note':'ordinary text'}),{'note':'ordinary text'})
    def test_depth_and_non_json_types_rejected(self):
        with self.assertRaises(helpers.HelperError):helpers.redact_structure({'items':[[[1]]]},max_depth=1)
        with self.assertRaises(helpers.HelperError):helpers.redact_structure({'object':object()})
    def test_bounded_json_object(self):
        path=self.write('data.json','{"ok":true}')
        self.assertEqual(helpers.load_json_object(path),{'ok':True})
        with self.assertRaises(helpers.HelperError):helpers.load_json_object(path,max_bytes=2)
    def test_invalid_json_errors_omit_source_values_and_paths(self):
        path=self.write('data.json','not valid json')
        with self.assertRaises(helpers.HelperError) as error:helpers.load_json_object(path)
        self.assertNotIn(str(path),str(error.exception));self.assertNotIn('not valid',str(error.exception))

class DatasetReviewTests(Fixture):
    def setUp(self):
        super().setUp();self.store=self.parent/'review.sqlite3';review_store.initialize(self.store)
    def import_rows(self,rows,name='input.jsonl'):
        path=self.parent/name
        path.write_text(''.join(json.dumps(row)+'\n' for row in rows),encoding='utf-8')
        return review_store.import_records(self.store,path)
    def approve(self,identifier):
        return review_store.review(self.store,identifier,'approved','Reviewer','Checked fictional fixture',{k:True for k in review_store.CHECKS})
    def test_imported_approval_is_ignored(self):
        self.import_rows([dict(text='fictional content',group='demo',status='approved')])
        self.assertEqual(review_store.records(self.store)[0]['status'],'pending')
    def test_empty_and_unapproved_exports(self):
        self.import_rows([dict(text='fictional content',group='demo')])
        output=self.parent/'export.jsonl';result=review_store.export_records(self.store,output)
        self.assertEqual(result['records'],0);self.assertEqual(output.read_bytes(),b'')
    def test_approved_record_exported_without_reviewer_metadata(self):
        self.import_rows([dict(text='fictional content',group='demo')])
        identifier=review_store.records(self.store)[0]['id'];self.approve(identifier)
        output=self.parent/'export.jsonl';review_store.export_records(self.store,output)
        row=json.loads(output.read_text())
        self.assertEqual(row['text'],'fictional content');self.assertNotIn('actor',row);self.assertNotIn('note',row)
    def test_all_four_checks_required(self):
        self.import_rows([dict(text='fictional content',group='demo')])
        identifier=review_store.records(self.store)[0]['id']
        with self.assertRaises(review_store.ReviewError):review_store.review(self.store,identifier,'approved','Reviewer','Note',{'quality':True})
    def test_key_pattern_blocks_approval(self):
        self.import_rows([dict(text='gh'+'p_'+'A'*36,group='demo')])
        identifier=review_store.records(self.store)[0]['id']
        with self.assertRaises(review_store.ReviewError):self.approve(identifier)
    def test_exact_dedup_and_strongest_holdout_wins(self):
        result=self.import_rows([dict(text='same',group='alpha'),dict(text='same',group='beta',split='test')])
        rows=review_store.records(self.store)
        self.assertEqual(result['added'],1);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['split'],'test')
    def test_duplicate_linked_groups_remain_merged_for_later_imports(self):
        self.import_rows([dict(text='first',group='beta'),dict(text='first',group='alpha',split='test'),dict(text='second',group='beta')])
        self.import_rows([dict(text='third',group='beta')],name='second.jsonl')
        rows=review_store.records(self.store)
        self.assertEqual({r['group_id'] for r in rows},{'alpha'})
        self.assertEqual({r['split'] for r in rows},{'test'})
    def test_reimport_does_not_change_review_status(self):
        rows=[dict(text='fictional content',group='demo')];self.import_rows(rows)
        identifier=review_store.records(self.store)[0]['id'];self.approve(identifier);self.import_rows(rows)
        self.assertEqual(review_store.records(self.store)[0]['status'],'approved')
    def test_store_and_export_not_overwritten(self):
        before=self.store.read_bytes()
        with self.assertRaises(FileExistsError):review_store.initialize(self.store)
        self.assertEqual(before,self.store.read_bytes())
        output=self.parent/'export.jsonl';output.write_text('preserved',encoding='utf-8')
        with self.assertRaises(FileExistsError):review_store.export_records(self.store,output)
        self.assertEqual(output.read_text(),'preserved')
    def test_state_cannot_be_created_inside_repository(self):
        with self.assertRaises(review_store.ReviewError):review_store.selected_path(ROOT/'private.sqlite3',private_output=True)
    def test_invalid_import_is_transactional(self):
        with self.assertRaises(review_store.ReviewError):self.import_rows([dict(text='valid',group='demo'),dict(text='invalid',group='../escape')])
        self.assertEqual(review_store.records(self.store),[])
    def test_rejection_removes_record_from_future_exports(self):
        self.import_rows([dict(text='fictional content',group='demo')]);identifier=review_store.records(self.store)[0]['id'];self.approve(identifier)
        review_store.review(self.store,identifier,'rejected','Reviewer','Recheck',{})
        self.assertEqual(review_store.export_records(self.store,self.parent/'export.jsonl')['records'],0)

if __name__=='__main__':unittest.main()
