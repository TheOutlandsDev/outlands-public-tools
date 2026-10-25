"""Authored disposable repositories and porcelain cases; no real worktree scan."""
from pathlib import Path
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'examples'))
import git_worktree_report as r
from make_demo import create

GIT = os.environ.get('OUTLANDS_TEST_GIT') or shutil.which('git')
if not GIT:
    raise RuntimeError('Git is required; repository fixtures are not skipped.')
GIT = Path(GIT).absolute()
BASE = b'# branch.oid ' + b'a' * 40 + b'\0# branch.head main\0'
ONE = b'1 .M N... 100644 100644 100644 ' + b'a' * 40 + b' ' + b'a' * 40 + b' file.txt\0'


class Reporter(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='git-report-tests-')
        self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)

    def rejects(self, code, action):
        with self.assertRaises(r.ReportError) as caught: action()
        self.assertEqual(str(caught.exception), code)

    def fixture(self):
        return create(self.root / 'repo', GIT)

    def git(self, repo, *args):
        return subprocess.check_output([str(GIT), '-c', 'core.hooksPath=' + os.devnull,
                                        '-c', 'user.name=Fictional Example', '-c', 'user.email=example@example.invalid',
                                        '-C', str(repo), *args], env=r.isolated_environment(), stderr=subprocess.PIPE, timeout=15)

    def test_actual_demo_status_and_index_unchanged(self):
        repo = self.fixture(); before = r.metadata_receipt(repo / '.git', repo / '.git')
        report = r.inspect(repo, GIT)
        self.assertEqual(report['entry_count'], 3)
        self.assertEqual(report['counts'], {'untracked': 1, 'unmerged': 0, 'staged': 1, 'unstaged': 1})
        self.assertEqual(report['head_state'], 'branch'); self.assertEqual(report['branch'], 'main')
        self.assertEqual(before, r.metadata_receipt(repo / '.git', repo / '.git'))
        text = json.dumps(report); self.assertNotIn(str(repo), text); self.assertNotIn('Fictional staged update', text)

    def test_unborn_repository(self):
        repo = self.root / 'repo'; repo.mkdir(); self.git(repo, 'init', '--initial-branch=main')
        (repo / 'new.txt').write_text('Fictional')
        report = r.inspect(repo, GIT)
        self.assertEqual(report['head_state'], 'unborn'); self.assertIsNone(report['head_oid'])
        self.assertEqual(report['counts']['untracked'], 1)

    def test_detached_head(self):
        repo = self.fixture(); self.git(repo, 'checkout', '--detach', 'HEAD')
        report = r.inspect(repo, GIT); self.assertEqual(report['head_state'], 'detached'); self.assertIsNone(report['branch'])

    def test_local_upstream_counts_are_not_network_refresh(self):
        repo = self.fixture(); self.git(repo, 'branch', 'base'); self.git(repo, 'branch', '--set-upstream-to=base')
        self.git(repo, 'commit', '-m', 'Fictional next commit')
        report = r.inspect(repo, GIT)
        self.assertEqual(report['upstream']['ahead'], 1); self.assertEqual(report['upstream']['behind'], 0)
        self.assertEqual(report['upstream']['basis'], 'stored_local_refs_only_no_network_refresh')

    def test_linked_worktree(self):
        repo = self.fixture(); linked = self.root / 'linked'
        self.git(repo, 'worktree', 'add', '-b', 'fictional-linked', str(linked))
        report = r.inspect(linked, GIT)
        self.assertEqual(report['branch'], 'fictional-linked'); self.assertEqual(report['entry_count'], 0)

    def test_actual_staged_rename_with_spaces(self):
        repo = self.fixture()
        (repo / 'staged.txt').write_text('Fictional original\n', encoding='utf-8')
        self.git(repo, 'add', 'staged.txt'); self.git(repo, 'mv', 'staged.txt', 'renamed item.txt')
        report = r.inspect(repo, GIT); renamed = [row for row in report['entries'] if row['kind'] == 'renamed_or_copied']
        self.assertEqual(len(renamed), 1); self.assertEqual(renamed[0]['original_path'], 'staged.txt')
        self.assertEqual(renamed[0]['path'], 'renamed item.txt')

    def test_actual_partial_similarity_rename(self):
        repo = self.fixture(); original = ''.join(f'Fictional baseline line {i:02d}\n' for i in range(20))
        (repo / 'staged.txt').write_text(original, encoding='utf-8'); self.git(repo, 'add', 'staged.txt'); self.git(repo, 'commit', '-m', 'Authored rename baseline')
        self.git(repo, 'mv', 'staged.txt', 'renamed.txt')
        (repo / 'renamed.txt').write_text(original.replace('line 19', 'changed final line'), encoding='utf-8'); self.git(repo, 'add', 'renamed.txt')
        rows = [row for row in r.inspect(repo, GIT)['entries'] if row['kind'] == 'renamed_or_copied']
        self.assertEqual(len(rows), 1); self.assertGreater(int(rows[0]['similarity'][1:]), 0); self.assertLess(int(rows[0]['similarity'][1:]), 100)

    def test_filter_configuration_refused_without_execution(self):
        repo = self.fixture(); trap = self.root / 'executed.txt'
        self.git(repo, 'config', 'filter.poison.clean', f'echo poison > "{trap.as_posix()}"')
        (repo / '.gitattributes').write_text('*.txt filter=poison\n', encoding='utf-8')
        self.rejects('CONFIGURED_HELPER_OR_LAYOUT_UNSUPPORTED', lambda: r.inspect(repo, GIT)); self.assertFalse(trap.exists())

    def test_include_configuration_refused(self):
        repo = self.fixture(); self.git(repo, 'config', 'include.path', 'missing-fictional-config')
        self.rejects('CONFIGURED_HELPER_OR_LAYOUT_UNSUPPORTED', lambda: r.inspect(repo, GIT))

    def test_worktree_configuration_filter_is_also_refused(self):
        repo = self.fixture(); self.git(repo, 'config', 'extensions.worktreeConfig', 'true')
        self.git(repo, 'config', '--worktree', 'filter.worktree-poison.clean', 'ignored-fictional-helper')
        self.rejects('CONFIGURED_HELPER_OR_LAYOUT_UNSUPPORTED', lambda: r.inspect(repo, GIT))

    def test_partial_clone_config_refused(self):
        repo = self.fixture(); self.git(repo, 'config', 'remote.origin.promisor', 'true')
        self.rejects('CONFIGURED_HELPER_OR_LAYOUT_UNSUPPORTED', lambda: r.inspect(repo, GIT))

    def test_custom_diff_and_sparse_layout_config_refused(self):
        for key in ('diff.poison.textconv', 'diff.poison.command', 'core.sparseCheckout', 'core.worktree', 'core.alternateRefsCommand'):
            with self.subTest(key=key):
                self.rejects('CONFIGURED_HELPER_OR_LAYOUT_UNSUPPORTED', lambda key=key: r.check_config((key + '\0').encode()))

    def test_shallow_grafts_and_alternate_object_stores_refused(self):
        repo = self.fixture()
        for relative in ['shallow', 'info/grafts', 'objects/info/alternates', 'objects/info/http-alternates']:
            path = repo / '.git' / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('Fictional unsupported metadata\n')
            with self.subTest(relative=relative):
                self.rejects('SHALLOW_GRAFT_OR_ALTERNATE_UNSUPPORTED', lambda: r.inspect(repo, GIT))
            path.unlink()

    def test_metadata_change_refused(self):
        repo = self.fixture()
        with patch.object(r, 'metadata_receipt', side_effect=[[], [('changed', 'observation')]]):
            self.rejects('REPOSITORY_METADATA_CHANGED', lambda: r.inspect(repo, GIT))

    def test_old_git_version_refused(self):
        repo = self.fixture()
        with patch.object(r, 'run_bounded', return_value=b'git version 2.48.0\n'):
            self.rejects('GIT_2_49_OR_NEWER_REQUIRED', lambda: r.inspect(repo, GIT))

    def test_ignored_entries_are_explicitly_outside_scope(self):
        repo = self.fixture(); (repo / '.gitignore').write_text('ignored-*\n')
        (repo / 'ignored-private.txt').write_text('Fictional ignored content')
        report = r.inspect(repo, GIT)
        self.assertNotIn('ignored-private.txt', json.dumps(report))
        self.assertIn('excluding_ignored', report['coverage'])

    def test_fsmonitor_and_hook_configuration_not_executed(self):
        repo = self.fixture(); trap = self.root / 'executed.txt'
        self.git(repo, 'config', 'core.fsmonitor', f'echo poison > "{trap.as_posix()}"')
        hooks = repo / '.git/hooks'; hooks.mkdir(exist_ok=True)
        hook = hooks / 'post-index-change'; hook.write_text(f'#!/bin/sh\necho poison > "{trap.as_posix()}"\n')
        hook.chmod(0o700)
        r.inspect(repo, GIT); self.assertFalse(trap.exists())

    def test_global_and_inherited_git_environment_ignored(self):
        repo = self.fixture(); outside = self.root / 'global'; outside.write_text('[filter "poison"]\n clean = ignored\n')
        with patch.dict(os.environ, {'GIT_CONFIG_GLOBAL': str(outside), 'GIT_DIR': '/fictional/wrong', 'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'filter.x.clean', 'GIT_CONFIG_VALUE_0': 'ignored'}):
            report = r.inspect(repo, GIT)
        self.assertEqual(report['entry_count'], 3)

    def test_existing_report_refused(self):
        repo = self.fixture(); report = r.inspect(repo, GIT); output = self.root / 'report'
        r.write_report(report, output, repo); old = (output / 'report.json').read_bytes()
        self.rejects('FRESH_OUTPUT_REQUIRED', lambda: r.write_report(report, output, repo)); self.assertEqual(old, (output / 'report.json').read_bytes())

    def test_output_inside_worktree_refused(self):
        repo = self.fixture()
        self.rejects('OUTPUT_INSIDE_WORKTREE', lambda: r.write_report(r.inspect(repo, GIT), repo / 'report', repo))

    def test_output_inside_linked_common_metadata_refused(self):
        repo = self.fixture(); linked = self.root / 'linked'
        self.git(repo, 'worktree', 'add', '-b', 'fictional-linked', str(linked))
        self.rejects('OUTPUT_INSIDE_GIT_METADATA', lambda: r.write_report(r.inspect(linked, GIT), repo / '.git/report', linked))

    def test_report_manifest_independently_matches(self):
        repo = self.fixture(); output = self.root / 'report'; r.write_report(r.inspect(repo, GIT), output, repo)
        manifest = json.loads((output / 'MANIFEST.json').read_text())
        self.assertEqual(len(manifest['files']), 1)
        row = manifest['files'][0]; data = (output / row['path']).read_bytes()
        self.assertEqual(row['bytes'], len(data)); self.assertEqual(row['sha256'], hashlib.sha256(data).hexdigest())

    def test_cli_safe_errors_and_counts(self):
        repo = self.fixture(); output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = r.main(['--repo', str(repo), '--git-executable', str(GIT), '--output', str(self.root / 'report')])
        self.assertEqual(code, 0); self.assertNotIn(str(repo), output.getvalue())
        output = io.StringIO()
        with contextlib.redirect_stdout(output): code = r.main(['--repo', str(self.root / 'private-absent'), '--git-executable', str(GIT), '--output', str(self.root / 'report2')])
        self.assertEqual(code, 2); self.assertNotIn('private-absent', output.getvalue())

    def test_exact_root_required(self):
        repo = self.fixture(); folder = repo / 'sub'; folder.mkdir()
        # No repository discovery outside the exact supplied worktree root.
        with self.assertRaises((r.ReportError, OSError)): r.inspect(folder, GIT)

    def test_relative_and_unc_inputs_refused(self):
        for value in ['relative', '//fictional/server', '\\\\fictional\\server']:
            self.rejects('LOCAL_ABSOLUTE_PATH_REQUIRED', lambda value=value: r.local_path(value))

    def test_metadata_pointer_rejects_network_device_controls_before_io(self):
        for value in ['//fictional/share', '\\\\fictional\\share', '\\\\?\\Q:\\device', 'bad\npath', 'Q:relative']:
            with self.subTest(value=value), patch.object(r, 'no_links', side_effect=AssertionError('Pointer attempted filesystem IO')):
                self.rejects('GIT_METADATA_POINTER_UNSUPPORTED', lambda value=value: r.metadata_pointer(self.root, value))

    def test_relative_metadata_pointer_preserves_parent_components(self):
        base = self.root / 'base'; base.mkdir(); target = self.root / 'metadata'; target.mkdir()
        self.assertEqual(r.metadata_pointer(base, '../metadata'), target)

    def test_metadata_presence_never_uses_following_exists(self):
        with patch.object(Path, 'exists', side_effect=AssertionError('Following existence probe')):
            self.assertTrue(r.metadata_present(self.root))
            self.assertFalse(r.metadata_present(self.root / 'absent' / 'control'))
            with patch.object(r, 'linked', return_value=True):
                self.rejects('LINKED_PATH_REJECTED', lambda: r.metadata_present(self.root))

    def test_native_link_rejected_when_available(self):
        repo = self.fixture(); link = self.root / 'linked-root'
        try: link.symlink_to(repo, target_is_directory=True)
        except OSError:
            if os.name == 'posix': raise
            self.skipTest('Native Windows symlink privilege unavailable')
        self.rejects('LINKED_PATH_REJECTED', lambda: r.inspect(link, GIT))

    def test_stdout_bound_and_timeout_owned_process(self):
        self.rejects('GIT_OUTPUT_LIMIT', lambda: r.run_bounded([sys.executable, '-c', 'print("x"*10000)'], maximum=20))
        started = time.monotonic()
        self.rejects('GIT_TIMEOUT', lambda: r.run_bounded([sys.executable, '-c', 'import time;time.sleep(20)'], seconds=.1))
        self.assertLess(time.monotonic() - started, 5)

    def test_nonzero_child_error_not_exposed(self):
        self.rejects('GIT_COMMAND_FAILED', lambda: r.run_bounded([sys.executable, '-c', 'import sys;print("private-data",file=sys.stderr);sys.exit(7)']))

    def test_stderr_bound(self):
        self.rejects('GIT_OUTPUT_LIMIT', lambda: r.run_bounded([sys.executable, '-c', 'import sys;sys.stderr.write("x"*70000)']))

    def test_nonregular_git_executable_refused(self):
        repo = self.fixture()
        self.rejects('TRUSTED_GIT_EXECUTABLE_REQUIRED', lambda: r.inspect(repo, self.root))

    def test_pipe_read_failure_is_not_a_partial_success(self):
        class BadPipe(io.BytesIO):
            def read(self, _size): raise OSError('Fictional read failure')
        class Job:
            def assign(self, _process): pass
            def close(self): pass
        child = SimpleNamespace(stdout=BadPipe(), stderr=io.BytesIO(), poll=lambda: 0, returncode=0)
        with patch.object(r, 'WindowsJob', Job), patch.object(r.subprocess, 'Popen', return_value=child):
            self.rejects('GIT_PIPE_READ_FAILED', lambda: r.run_bounded(['fictional-owned-child']))


class Porcelain(unittest.TestCase):
    def rejects(self, code, data):
        with self.assertRaises(r.ReportError) as caught: r.parse_status(data)
        self.assertEqual(str(caught.exception), code)

    def test_clean_and_tracked(self):
        self.assertEqual(r.parse_status(BASE)['entry_count'], 0)
        self.assertEqual(r.parse_status(BASE + ONE)['counts']['unstaged'], 1)

    def test_utf8_spaces_newlines_and_tab_are_data(self):
        report = r.parse_status(BASE + '? café tab\tline\n.txt\0'.encode('utf-8'))
        self.assertEqual(report['entries'][0]['path'], 'café tab\tline\n.txt')

    def test_rename_and_copy_original_paths_use_next_nul_record(self):
        for kind in (b'R100', b'C75', b'C075'):
            data = BASE + b'2 R. N... 100644 100644 100644 ' + b'a' * 40 + b' ' + b'b' * 40 + b' ' + kind + b' new item\0old item\0'
            row = r.parse_status(data)['entries'][0]
            self.assertEqual(row['original_path'], 'old item'); self.assertEqual(row['similarity'], kind.decode())

    def test_unmerged_three_object_records(self):
        data = BASE + b'u UU N... 100644 100644 100644 100644 ' + b'a' * 40 + b' ' + b'b' * 40 + b' ' + b'c' * 40 + b' conflict.txt\0'
        counts = r.parse_status(data)['counts']
        self.assertEqual(counts['unmerged'], 1); self.assertEqual(counts['staged'], 0); self.assertEqual(counts['unstaged'], 0)

    def test_sha256_object_names(self):
        data = b'# branch.oid ' + b'a' * 64 + b'\0# branch.head main\0'
        self.assertEqual(len(r.parse_status(data)['head_oid']), 64)

    def test_unknown_headers_ignored_by_count_not_echoed(self):
        report = r.parse_status(BASE + b'# future private-extra\0')
        self.assertEqual(report['ignored_header_count'], 1); self.assertNotIn('private-extra', json.dumps(report))

    def test_missing_local_upstream_is_unknown_not_zero(self):
        report = r.parse_status(BASE + b'# branch.upstream origin/main\0')
        self.assertIsNone(report['upstream']['ahead']); self.assertEqual(report['upstream']['comparison'], 'unavailable')

    def test_duplicate_headers_and_paths_refused(self):
        self.rejects('STATUS_DUPLICATE_HEADER', BASE + b'# branch.head other\0')
        self.rejects('STATUS_DUPLICATE_PATH', BASE + b'? duplicate\0? duplicate\0')

    def test_unsupported_record_and_truncated_records_refused(self):
        self.rejects('STATUS_RECORD_UNSUPPORTED', BASE + b'! ignored\0')
        self.rejects('STATUS_FORMAT_UNSUPPORTED', BASE[:-1])
        self.rejects('STATUS_FORMAT_UNSUPPORTED', BASE + b'1 too-short\0')

    def test_invalid_utf8_and_unsafe_paths_refused(self):
        self.rejects('STATUS_UTF8_REQUIRED', BASE + b'? \xff\0')
        for name in ['/absolute', '../escape', 'x/../a', 'Q:/drive', 'a//b']:
            self.rejects('STATUS_PATH_UNSUPPORTED', BASE + b'? ' + name.encode() + b'\0')

    def test_missing_branch_headers_refused(self):
        self.rejects('STATUS_BRANCH_HEADERS_REQUIRED', b'? item\0')

    def test_entry_limit_and_path_length(self):
        with patch.object(r, 'MAX_ENTRIES', 1): self.rejects('STATUS_ENTRY_LIMIT', BASE + b'? a\0? b\0')
        self.rejects('STATUS_RECORD_LIMIT', BASE + b'? ' + b'a' * 5000 + b'\0')

    def test_invalid_metadata_and_counts(self):
        self.rejects('STATUS_FORMAT_UNSUPPORTED', BASE + ONE.replace(b'100644', b'badbad', 1))
        self.rejects('STATUS_FORMAT_UNSUPPORTED', BASE + b'# branch.ab +1 -2\0')

    def test_truncated_rename_and_invalid_score_refused(self):
        prefix = b'2 R. N... 100644 100644 100644 ' + b'a' * 40 + b' ' + b'b' * 40
        self.rejects('STATUS_FORMAT_UNSUPPORTED', BASE + prefix + b' R100 new\0')
        self.rejects('STATUS_FORMAT_UNSUPPORTED', BASE + prefix + b' R101 new\0old\0')

    def test_submodule_record_is_observed_without_recursion(self):
        report = r.parse_status(BASE + ONE.replace(b'N...', b'S.M.'))
        self.assertEqual(report['entries'][0]['submodule'], 'S.M.')

    def test_invalid_branch_and_config_encoding_refused(self):
        self.rejects('STATUS_BRANCH_UNSUPPORTED', BASE.replace(b'main', b'bad\nbranch'))
        with self.assertRaises(r.ReportError): r.check_config(b'bad\xff\0')

    def test_record_output_byte_limit(self):
        with patch.object(r, 'MAX_OUTPUT', 10): self.rejects('STATUS_FORMAT_UNSUPPORTED', BASE)


if __name__ == '__main__': unittest.main()
