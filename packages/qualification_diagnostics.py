"""Allowlisted public failure metadata; child output and paths stay private."""
import json
import os
from pathlib import Path
import re
import sys


COMPONENTS = frozenset(('qualification', 'complete-package', 'system-exercises',
    'lifecycle-exercises', 'ingestion-evidence', 'manufacturing-review',
    'material-quality-review', 'import-migration-workbench',
    'document-template-workbench', 'environment-setup-workbench',
    'release-update-workbench', 'document-rendering', 'document-original',
    'document-revised'))
STAGES = frozenset(('preflight', 'archive-validation', 'cli-workflows',
    'cli-oracles', 'browser-prerequisites', 'browser-workflows',
    'browser-oracles', 'capture-inventory', 'render-prerequisites',
    'render-source', 'render-convert', 'render-text', 'render-oracles',
    'render-info', 'render-images', 'evidence-inventory'))
CHECKS = frozenset(('NEW_PRIVATE_WORKSPACE_REQUIRED', 'NEW_EVIDENCE_DIRECTORY_REQUIRED',
    'EXPECTED_REVIEWED_COMPLETE_ARCHIVE', 'BOTH_EXERCISES_REQUIRED',
    'BOTH_LIFECYCLE_EXERCISES_REQUIRED', 'INGESTION_EVIDENCE_REQUIRED',
    'MANUFACTURING_REVIEW_REQUIRED', 'MANUFACTURING_ORACLES_REQUIRED',
    'MATERIAL_QUALITY_REVIEW_REQUIRED', 'MATERIAL_QUALITY_ORACLES_REQUIRED',
    'HOSTED_BROWSER_QUALIFICATION_ONLY', 'ALL_20_BROWSER_WORKFLOWS_REQUIRED',
    'BROWSER_CAPTURES_REQUIRED', 'UBUNTU_RENDER_TOOLS_REQUIRED',
    'BOTH_DOCUMENTS_REQUIRED', 'RENDER_SOURCE_PIN_MISMATCH', 'RENDER_PDF_REQUIRED',
    'RENDER_CONTENT_ORACLE_FAILED', 'RENDER_SECTION_ORACLE_FAILED',
    'ONE_PAGE_FICTIONAL_DOCUMENT_EXPECTED', 'UNREVIEWED_PUBLIC_EVIDENCE_FILE',
    'NEW_DIAGNOSTICS_DIRECTORY_REQUIRED', 'SEPARATE_DIAGNOSTICS_DIRECTORY_REQUIRED'))


class CheckFailed(ValueError):
    def __init__(self, code):
        self.code = code if code in CHECKS else 'CHECK_FAILED'
        super().__init__(self.code)


class CommandFailed(ValueError):
    def __init__(self, reason, returncode=None, timeout=None):
        self.reason = reason if reason in ('COMMAND_FAILED', 'COMMAND_TIMEOUT',
                                          'COMMAND_START_FAILED') else 'COMMAND_FAILED'
        self.returncode = returncode
        self.timeout = timeout
        super().__init__(self.reason)


class Progress:
    def __init__(self):
        self.component = 'qualification'
        self.stage = 'preflight'
        self.directory = None

    def prepare(self, directory, *private_roots):
        if directory is None:
            return
        directory = Path(directory)
        if not (directory.is_absolute() and not directory.exists()
                and directory.parent.is_dir()):
            raise CheckFailed('NEW_DIAGNOSTICS_DIRECTORY_REQUIRED')
        resolved = directory.resolve()
        for root in private_roots:
            other = Path(root).resolve()
            if resolved.is_relative_to(other) or other.is_relative_to(resolved):
                raise CheckFailed('SEPARATE_DIAGNOSTICS_DIRECTORY_REQUIRED')
        directory.mkdir()
        self.directory = directory

    def begin(self, component, stage):
        if component not in COMPONENTS or stage not in STAGES:
            raise CheckFailed('CHECK_FAILED')
        self.component, self.stage = component, stage
        print(json.dumps(dict(status='RUNNING', component=component, stage=stage)),
              file=sys.stderr, flush=True)

    def failed(self, error):
        # Never serialize str(error), exception arguments, command lines, paths,
        # environment contents, stdout, stderr or tracebacks into public evidence.
        row = dict(schema=1, status='FAIL', component=self.component,
                   stage=self.stage, reason='UNEXPECTED_ERROR',
                   raw_logs_included=False, qualification_passed=False)
        if isinstance(error, CheckFailed):
            row.update(reason='CHECK_FAILED', check=error.code)
        elif isinstance(error, CommandFailed):
            row['reason'] = error.reason
            if type(error.returncode) is int:
                row['return_code'] = error.returncode
            if type(error.timeout) in (int, float) and 0 < error.timeout <= 240:
                row['timeout_seconds'] = error.timeout
        for key, name, pattern in (
                ('GITHUB_SHA', 'workflow_commit', r'[0-9a-f]{40}'),
                ('GITHUB_RUN_ID', 'workflow_run', r'[0-9]{1,20}'),
                ('GITHUB_RUN_ATTEMPT', 'workflow_attempt', r'[0-9]{1,10}')):
            value = os.environ.get(key, '')
            if re.fullmatch(pattern, value):
                row[name] = value
        saved = False
        if self.directory is not None:
            try:
                with (self.directory / 'failure.json').open('x', encoding='utf-8', newline='\n') as stream:
                    stream.write(json.dumps(row, indent=2) + '\n')
                saved = True
            except OSError:
                pass  # Receipt I/O must not replace or conceal the original failure.
        print(json.dumps(dict(row, failure_receipt_saved=saved)), file=sys.stderr, flush=True)
        return row
