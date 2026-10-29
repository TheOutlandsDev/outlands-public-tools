"""Actual fictional standalone CLIs, public writer interoperability and reconciliation."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {'docx-table-extractor': 'docx_tables.py', 'document-intake-checker': 'document_intake.py',
         'tabular-reconciliation-checker': 'reconcile.py', 'document-content-diff': 'document_diff.py'}


class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fictional-document-tools-')
        self.addCleanup(self.temp.cleanup)
        self.private = Path(self.temp.name)

    def call(self, directory, script, args, code=0):
        value = subprocess.run([sys.executable, '-B', str(directory / script), *args],
                               cwd=self.private, capture_output=True, timeout=30)
        self.assertEqual(value.returncode, code, value.stdout.decode('utf-8', errors='replace'))
        self.assertEqual(value.stderr, b'')
        return json.loads(value.stdout)

    def doc(self, variant='before'):
        path = self.private / (variant + '.docx')
        if not path.exists():
            self.call(ROOT / 'tools/docx-table-extractor', 'fictional_docx.py',
                      ['--out', str(path), '--variant', variant])
        return path

    def args(self, name, path):
        if name == 'docx-table-extractor':
            return ['--input', str(self.doc()), '--table', 'table-1'], 0
        if name == 'document-intake-checker':
            return ['--input', str(self.doc()), '--table', 'table-1', '--mapping', str(path / 'examples/mapping.json')], 0
        if name == 'document-content-diff':
            return ['--before', str(self.doc()), '--after', str(self.doc('after'))], 1
        return ['--before', str(path / 'examples/before.json'), '--after', str(path / 'examples/after.json'),
                '--contract', str(path / 'examples/contract.json')], 1

    def test_all_fictional_cli_examples(self):
        for name, script in TOOLS.items():
            path = ROOT / 'tools' / name; args, code = self.args(name, path)
            with self.subTest(tool=name):
                self.assertEqual(self.call(path, script, args, code)['status'], 'PASS' if code == 0 else 'DIFFERENCES')

    def test_each_tool_runs_from_its_own_copied_source(self):
        for name, script in TOOLS.items():
            path = self.private / name
            shutil.copytree(ROOT / 'tools' / name, path, ignore=shutil.ignore_patterns('__pycache__'))
            args, code = self.args(name, path)
            with self.subTest(tool=name):
                self.call(path, script, args, code)
                self.assertEqual(self.call(path, 'source_check.py', [])['status'], 'SOURCE_MATCH')

    def test_new_reports_and_overwrite_refusal(self):
        for name, script in TOOLS.items():
            path = ROOT / 'tools' / name; args, code = self.args(name, path)
            output = self.private / (name + '.json')
            args += ['--out', str(output)]
            self.assertTrue(self.call(path, script, args, code)['report_written'])
            raw = output.read_bytes()
            self.assertEqual(self.call(path, script, args, 2)['status'], 'ERROR')
            self.assertEqual(output.read_bytes(), raw)

    def test_cli_argument_errors_omit_supplied_values(self):
        for name, script in TOOLS.items():
            result = self.call(ROOT / 'tools' / name, script, ['--unknown', 'SYNTHETIC_SENTINEL'], 2)
            self.assertEqual(result, {'status': 'ERROR', 'code': 'ARGUMENTS_INVALID'})

    def test_metadata_and_formatting_change_only_is_content_match(self):
        path = ROOT / 'tools/document-content-diff'
        result = self.call(path, 'document_diff.py', ['--before', str(self.doc()), '--after', str(self.doc('formatting'))])
        self.assertEqual(result['status'], 'MATCH')
        self.assertTrue(result['raw_bytes_changed'])

    def test_document_intake_record_sets_reconcile_with_equal_totals_and_real_differences(self):
        path = ROOT / 'tools/document-intake-checker'
        inputs = []
        for variant in ('before', 'after'):
            result = self.call(path, 'document_intake.py', ['--input', str(self.doc(variant)), '--table', 'table-1',
                               '--mapping', str(path / 'examples/mapping.json')])
            self.assertTrue(result['ready_for_explicit_review'])
            self.assertFalse(result['imported'])
            record_set = dict(format='outlands-record-set-v1', records=[v['record'] for v in result['accepted']])
            selected = self.private / (variant + '.json')
            selected.write_text(json.dumps(record_set), encoding='utf-8')
            inputs.append(selected)
        selected = ROOT / 'tools/tabular-reconciliation-checker'
        report = self.call(selected, 'reconcile.py', ['--before', str(inputs[0]), '--after', str(inputs[1]),
                           '--contract', str(selected / 'examples/contract.json')], 1)
        self.assertEqual(report['totals']['units'], dict(before='19', after='19', delta='0'))
        self.assertEqual(len(report['changes']), 3)
        self.assertFalse(report['external_system_writes'])

    def test_bad_intake_is_not_ready_for_downstream_review(self):
        path = ROOT / 'tools/document-intake-checker'
        result = self.call(path, 'document_intake.py', ['--input', str(self.doc('needs-review')), '--table', 'table-1',
                           '--mapping', str(path / 'examples/mapping.json')], 1)
        self.assertFalse(result['ready_for_explicit_review'])
        self.assertEqual(result['accepted'], [])
        self.assertEqual(result['counts']['conflict_rows'], 2)

    def test_public_source_copies_match_canonical_blobs(self):
        for relative in ('toolkit.py', 'native_windows.py', 'source_check.py', 'tests/test_boundaries.py'):
            raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', 'HEAD:tools/workbook-intake-checker/' + relative])
            for name in TOOLS:
                self.assertEqual((ROOT / 'tools' / name / relative).read_bytes(), raw)
        original = subprocess.check_output(['git', '-C', str(ROOT), 'show', 'HEAD:tools/workbook-intake-checker/intake.py'])
        self.assertEqual((ROOT / 'tools/document-intake-checker/intake.py').read_bytes(), original)
        for name in ('document-intake-checker', 'document-content-diff'):
            for relative in ('docx_core.py', 'fictional_docx.py', 'tests/test_docx_core.py'):
                self.assertEqual((ROOT / 'tools' / name / relative).read_bytes(),
                                 (ROOT / 'tools/docx-table-extractor' / relative).read_bytes())

    def test_independent_existing_public_docx_writer_interoperability(self):
        code = '''import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from documents import ooxml
model=dict(title='Fictional independent writer',sections=[dict(title='Sample',blocks=[dict(kind='table',columns=[dict(label='Record',width=60,kind='text'),dict(label='Units',width=40,kind='quantity')],rows=[['sample-public',7]],totals=[])])])
Path(sys.argv[2]).write_bytes(ooxml.build(model))
'''
        generated = self.private / 'independent.docx'
        result = subprocess.run([sys.executable, '-B', '-c', code,
            str(ROOT / 'systems/document-template-workbench'), str(generated)], capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
        report = self.call(ROOT / 'tools/docx-table-extractor', 'docx_tables.py',
                           ['--input', str(generated), '--table', 'table-1'])
        self.assertEqual(report['selected_tables'][0]['rows'], [['Record', 'Units'], ['sample-public', '7']])
        self.assertEqual(report['source_sha256'], hashlib.sha256(generated.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
