"""Actual standalone CLI walkthroughs and a fictional four-tool handoff."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {'workbook-intake-checker': 'intake.py', 'snapshot-contract-checker': 'snapshot.py',
         'xml-workflow-checker': 'workflow.py', 'planner-handoff-checker': 'handoff.py'}


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode() + b'\n'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def arguments(name, directory):
    example = directory / 'examples'
    if name == 'workbook-intake-checker':
        return ['--input', str(example / 'records.csv'), '--mapping', str(example / 'mapping.json'), '--format', 'csv']
    if name == 'snapshot-contract-checker':
        return ['--manifest', str(example / 'manifest.json'), '--policy', str(example / 'policy.json'),
                '--item', 'records', str(example / 'records.txt')]
    if name == 'xml-workflow-checker':
        return ['--input', str(example / 'before.xml')]
    return ['--project', str(example / 'project.json'), '--handoff', str(example / 'handoff.json'),
            '--attachment', 'provenance', str(example / 'provenance.txt')]


class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fictional-modular-tools-')
        self.addCleanup(self.temp.cleanup)
        self.private = Path(self.temp.name)

    def call(self, directory, script, args, code=0):
        result = subprocess.run([sys.executable, '-B', str(directory / script), *args],
                                cwd=self.private, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, code, result.stdout.decode('utf-8', errors='replace'))
        self.assertEqual(result.stderr, b'')
        return json.loads(result.stdout)

    def test_all_documented_fictional_cli_examples(self):
        for name, script in TOOLS.items():
            path = ROOT / 'tools' / name
            with self.subTest(tool=name):
                result = self.call(path, script, arguments(name, path))
                self.assertEqual(result['status'], 'PASS')

    def test_documented_review_and_diff_exit_codes(self):
        path = ROOT / 'tools/workbook-intake-checker'
        self.assertEqual(self.call(path, 'intake.py', ['--input', str(path / 'examples/needs-review.csv'),
            '--mapping', str(path / 'examples/mapping.json'), '--format', 'csv'], 1)['status'], 'REVIEW_REQUIRED')
        path = ROOT / 'tools/xml-workflow-checker'
        self.assertEqual(self.call(path, 'workflow.py', ['--input', str(path / 'examples/after.xml'),
            '--before', str(path / 'examples/before.xml')], 1)['status'], 'DIFFERENCES')

    def test_each_tool_runs_from_its_own_copied_directory(self):
        for name, script in TOOLS.items():
            original = ROOT / 'tools' / name
            selected = self.private / name
            shutil.copytree(original, selected, ignore=shutil.ignore_patterns('__pycache__'))
            with self.subTest(tool=name):
                self.assertEqual(self.call(selected, script, arguments(name, selected))['status'], 'PASS')
                source = self.call(selected, 'source_check.py', [])
                self.assertEqual(source['status'], 'SOURCE_MATCH')

    def test_each_tool_creates_only_new_reports_and_refuses_overwrite(self):
        for name, script in TOOLS.items():
            path = ROOT / 'tools' / name
            output = self.private / (name + '.json')
            args = arguments(name, path) + ['--out', str(output)]
            with self.subTest(tool=name):
                self.assertEqual(self.call(path, script, args), {'status': 'PASS', 'report_written': True})
                original = output.read_bytes()
                self.assertEqual(json.loads(original)['status'], 'PASS')
                self.assertEqual(self.call(path, script, args, 2)['status'], 'ERROR')
                self.assertEqual(output.read_bytes(), original)

    def test_each_cli_error_omits_supplied_argument(self):
        for name, script in TOOLS.items():
            result = self.call(ROOT / 'tools' / name, script, ['--unknown', 'SYNTHETIC_SENTINEL'], 2)
            self.assertEqual(result, {'status': 'ERROR', 'code': 'ARGUMENTS_INVALID'})

    def test_generated_xlsx_has_same_normalized_records_as_csv(self):
        path = ROOT / 'tools/workbook-intake-checker'
        output = self.private / 'fictional.xlsx'
        generated = self.call(path, 'fictional_workbook.py', ['--out', str(output)])
        self.assertEqual(generated['sha256'], sha(output.read_bytes()))
        workbook = self.call(path, 'intake.py', ['--input', str(output), '--mapping',
                  str(path / 'examples/mapping.json'), '--format', 'xlsx', '--sheet', 'Records'])
        csv = self.call(path, 'intake.py', arguments('workbook-intake-checker', path))
        self.assertEqual(workbook['accepted'], csv['accepted'])
        self.assertEqual(workbook['counts'], csv['counts'])

    def test_native_backend_and_common_copies_match_public_pins(self):
        native = (ROOT / 'tools/environment-contract-checker/environment_windows.py').read_bytes()
        common = (ROOT / 'tools/workbook-intake-checker/toolkit.py').read_bytes()
        for name in TOOLS:
            path = ROOT / 'tools' / name
            self.assertEqual((path / 'native_windows.py').read_bytes(), native)
            self.assertEqual((path / 'toolkit.py').read_bytes(), common)
        for rel in ('project.py', 'engines/allocation.py', 'engines/demand.py',
                    'engines/identity.py', 'engines/readiness.py', 'engines/__init__.py'):
            self.assertEqual((ROOT / 'tools/planner-handoff-checker/planner_contract' / rel).read_bytes(),
                             (ROOT / 'systems/production-planning-workbench/planning' / rel).read_bytes())

    def test_fictional_intake_snapshot_workflow_and_explicit_handoff(self):
        intake = ROOT / 'tools/workbook-intake-checker'
        preview = self.call(intake, 'intake.py', arguments('workbook-intake-checker', intake))
        preview_raw = encode(preview)
        (self.private / 'preview.json').write_bytes(preview_raw)
        manifest = dict(format='outlands-snapshot-v1', snapshot_id='sample-intake', version='v1',
            captured_at='2030-01-01T00:00:00Z', items=[dict(id='preview', sha256=sha(preview_raw),
            bytes=len(preview_raw), records=2)], reconciliation=dict(input_records=3,
            accepted_records=2, duplicate_records=1, rejected_records=0))
        manifest_raw = encode(manifest); (self.private / 'manifest.json').write_bytes(manifest_raw)
        policy = dict(format='outlands-snapshot-policy-v1', manifest_sha256=sha(manifest_raw),
            expected_version='v1', as_of='2030-01-01T00:00:00Z', max_age_seconds=0,
            expected_items=[dict(id='preview', records=2)])
        (self.private / 'policy.json').write_bytes(encode(policy))
        snapshot = self.call(ROOT / 'tools/snapshot-contract-checker', 'snapshot.py', ['--manifest',
            str(self.private / 'manifest.json'), '--policy', str(self.private / 'policy.json'),
            '--item', 'preview', str(self.private / 'preview.json')])
        flow_path = ROOT / 'tools/xml-workflow-checker'
        flow = self.call(flow_path, 'workflow.py', arguments('xml-workflow-checker', flow_path))
        attached = {'intake': preview_raw, 'snapshot': encode(snapshot), 'workflow': encode(flow)}
        for key, raw in attached.items():
            (self.private / (key + '.json')).write_bytes(raw)
        handoff_path = ROOT / 'tools/planner-handoff-checker'
        project = handoff_path / 'examples/project.json'
        project_hash = sha(project.read_bytes())
        # No inferred conversion into planner fields. Explicitly select the
        # existing public fictional project and review each supplied evidence pin.
        pins = [{'id': key, 'sha256': sha(attached[key])} for key in sorted(attached)]
        review = dict(project_sha256=project_hash, attachments_sha256=sha(encode(pins)),
                      inputs_reviewed=False, mappings_reviewed=False, policies_reviewed=False, plan_only=True)
        envelope = dict(format='outlands-planner-handoff-v1', project_sha256=project_hash,
                        attachments=pins, review=review)
        review_file = self.private / 'review.json'
        review_file.write_bytes(encode(envelope))
        args = ['--project', str(project), '--handoff', str(review_file)]
        for key in sorted(attached):
            args += ['--attachment', key, str(self.private / (key + '.json'))]
        pending = self.call(handoff_path, 'handoff.py', args, 1)
        self.assertFalse(pending['eligible_for_explicit_import'])
        for key in ('inputs_reviewed', 'mappings_reviewed', 'policies_reviewed'):
            review[key] = True
        review_file.write_bytes(encode(envelope))
        accepted = self.call(handoff_path, 'handoff.py', args)
        self.assertTrue(accepted['eligible_for_explicit_import'])
        self.assertFalse(accepted['project_imported'])
        (self.private / 'snapshot.json').write_bytes(b'Fictional changed evidence')
        stale = self.call(handoff_path, 'handoff.py', args, 1)
        self.assertFalse(stale['eligible_for_explicit_import'])
        self.assertIn('STALE_ATTACHMENT_REVIEW', stale['issues'])
        self.assertEqual(sha(project.read_bytes()), project_hash)
        self.assertFalse(list(self.private.rglob('*.sqlite*')))


if __name__ == '__main__':
    unittest.main()
