"""Failure injection checks the public/private boundary without running a workbench."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qualify_system_exercises as qualification
from qualification_diagnostics import CheckFailed, CommandFailed, Progress


class QualificationDiagnostics(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'))
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.workspace = self.parent / 'private-workspace'
        self.evidence = self.parent / 'successful-evidence'
        self.diagnostics = self.parent / 'failure-receipt'
        self.packages = self.parent / 'downloads'
        self.console = io.StringIO()

    def run_failure(self, body, exception=Exception):
        with contextlib.redirect_stderr(self.console), patch.object(qualification, '_qualify', side_effect=body):
            with self.assertRaises(exception):
                qualification.qualify(self.packages, self.workspace, self.evidence,
                                      diagnostics=self.diagnostics)
        self.assertEqual([p.name for p in self.diagnostics.iterdir()], ['failure.json'])
        return json.loads((self.diagnostics / 'failure.json').read_text())

    def test_real_nonzero_child_identifies_component_without_publishing_its_output(self):
        sentinel = 'FICTIONAL_PRIVATE_CHILD_OUTPUT'
        def failed(packages, workspace, evidence, browser, render, progress):
            workspace.mkdir()
            progress.begin('document-template-workbench', 'browser-workflows')
            qualification.command([sys.executable, '-c',
                f'import sys;print({sentinel!r});sys.stderr.write({sentinel!r});sys.exit(7)'], workspace / 'child.log')
        row = self.run_failure(failed, CommandFailed)
        self.assertEqual((row['component'], row['stage'], row['return_code']),
                         ('document-template-workbench', 'browser-workflows', 7))
        self.assertEqual(row['reason'], 'COMMAND_FAILED')
        self.assertIn(sentinel, (self.workspace / 'child.log').read_text())
        public = json.dumps(row) + self.console.getvalue()
        for private in (sentinel, str(self.parent), 'child.log', 'import sys'):
            self.assertNotIn(private, public)
        self.assertFalse(row['raw_logs_included'])
        self.assertFalse(row['qualification_passed'])
        self.assertFalse(self.evidence.exists())

    def test_timeout_retains_partial_output_only_in_private_log(self):
        def failed(packages, workspace, evidence, browser, render, progress):
            workspace.mkdir()
            progress.begin('release-update-workbench', 'browser-workflows')
            timeout = subprocess.TimeoutExpired(['PRIVATE_COMMAND'], 240,
                        output=b'FICTIONAL_PRIVATE_STDOUT', stderr=b'FICTIONAL_PRIVATE_STDERR')
            with patch.object(qualification.subprocess, 'run', side_effect=timeout):
                qualification.command(['unused'], workspace / 'timeout.log')
        row = self.run_failure(failed, CommandFailed)
        self.assertEqual(row['reason'], 'COMMAND_TIMEOUT')
        self.assertEqual(row['timeout_seconds'], 240)
        self.assertEqual((self.workspace / 'timeout.log').read_bytes(),
                         b'FICTIONAL_PRIVATE_STDOUTFICTIONAL_PRIVATE_STDERR')
        self.assertNotIn('FICTIONAL_PRIVATE', json.dumps(row) + self.console.getvalue())

    def test_process_start_error_does_not_expose_executable_or_os_message(self):
        def failed(packages, workspace, evidence, browser, render, progress):
            progress.begin('document-original', 'render-convert')
            with patch.object(qualification.subprocess, 'run', side_effect=OSError('FICTIONAL_PRIVATE_PATH')):
                qualification.command(['PRIVATE_EXECUTABLE'], workspace / 'launch.log', timeout=120)
        row = self.run_failure(failed, CommandFailed)
        self.assertEqual(row['reason'], 'COMMAND_START_FAILED')
        self.assertNotIn('return_code', row)
        self.assertNotIn('PRIVATE', json.dumps(row) + self.console.getvalue())

    def test_unknown_exception_text_and_untrusted_environment_are_excluded(self):
        def failed(*args):
            args[-1].begin('ingestion-evidence', 'cli-oracles')
            raise ValueError('FICTIONAL_PRIVATE_EXCEPTION')
        with patch.dict(os.environ, {'GITHUB_SHA': 'PRIVATE_VALUE', 'GITHUB_RUN_ID': 'PRIVATE_VALUE',
                                     'GITHUB_RUN_ATTEMPT': 'PRIVATE_VALUE'}):
            row = self.run_failure(failed)
        self.assertEqual(row['reason'], 'UNEXPECTED_ERROR')
        self.assertNotIn('PRIVATE', json.dumps(row) + self.console.getvalue())
        self.assertNotIn('workflow_commit', row)

    def test_oracle_failure_has_its_own_stage_and_keeps_the_same_failure(self):
        def failed(*args):
            args[-1].begin('import-migration-workbench', 'browser-oracles')
            qualification.require(False, 'ALL_20_BROWSER_WORKFLOWS_REQUIRED')
        row = self.run_failure(failed, CheckFailed)
        self.assertEqual(row['check'], 'ALL_20_BROWSER_WORKFLOWS_REQUIRED')
        self.assertEqual(row['stage'], 'browser-oracles')

    def test_real_cli_preflight_failure_is_nonzero_and_preserves_existing_workspace(self):
        self.workspace.mkdir()
        marker = self.workspace / 'keep.txt'
        marker.write_text('original')
        result = subprocess.run([sys.executable, '-B', qualification.__file__,
            '--packages', str(self.packages), '--workspace', str(self.workspace),
            '--evidence', str(self.evidence), '--diagnostics', str(self.diagnostics)], capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(marker.read_text(), 'original')
        row = json.loads((self.diagnostics / 'failure.json').read_text())
        self.assertEqual(row['stage'], 'preflight')
        self.assertEqual(row['check'], 'NEW_PRIVATE_WORKSPACE_REQUIRED')
        self.assertNotIn(str(self.parent).encode(), result.stderr)
        self.assertFalse(self.evidence.exists())

    def test_existing_and_overlapping_diagnostics_are_refused_unchanged(self):
        self.diagnostics.mkdir()
        marker = self.diagnostics / 'keep.txt'; marker.write_text('original')
        progress = Progress()
        with self.assertRaises(CheckFailed):
            progress.prepare(self.diagnostics, self.workspace)
        self.assertEqual(marker.read_text(), 'original')
        with self.assertRaises(CheckFailed):
            progress.prepare(self.parent / 'overlap', self.parent)
        self.assertFalse((self.parent / 'overlap').exists())

    def test_success_creates_no_failure_receipt_and_receipt_io_cannot_mask_failure(self):
        with patch.object(qualification, '_qualify', return_value='passed'):
            result = qualification.qualify(self.packages, self.workspace, self.evidence,
                                          diagnostics=self.diagnostics)
        self.assertEqual(result, 'passed')
        self.assertEqual(list(self.diagnostics.iterdir()), [])
        progress = Progress(); progress.directory = self.diagnostics
        (self.diagnostics / 'failure.json').write_text('retain earlier record')
        with contextlib.redirect_stderr(self.console):
            progress.failed(CommandFailed('COMMAND_FAILED', returncode=9))
        self.assertEqual((self.diagnostics / 'failure.json').read_text(), 'retain earlier record')
        self.assertIn('"failure_receipt_saved": false', self.console.getvalue())


if __name__ == '__main__':
    unittest.main()
