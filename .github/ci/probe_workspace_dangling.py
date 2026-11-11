"""Compare one unchanged native Windows regression against baseline and reviewed code.

The two compatibility executions are separate from the eight qualification lanes.
Only the sanitized report is an uploadable artifact. Keep the owned workspace,
including its raw unittest diagnostics, private. Native links must be available;
this probe neither changes system policy nor requests administrator privileges.
"""
if not __debug__:
    raise RuntimeError('OPTIMIZED_PYTHON_UNSUPPORTED')

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import venv


ROOT = Path(__file__).resolve().parents[2]
BASELINE = '2c298e50e4983ef1703afa6232cefe1095b37b1e'
TEST_PATH = 'tools/project-workspace/tests/test_download.py'
TEST_ID = 'test_download.Download.test_native_symlink_output_leaf_preserves_targets'
TEST_SHA256 = '8013a6fccb0f6cac820f1a912bd08cbcf26d91511a7f88e3765b7936697013d2'
RUNTIME = ('workspace.py', 'workspace_windows.py')
BASELINE_RUNTIME_SHA256 = {
    'workspace.py': '4d861bf9a43ef1b4fd74c4136d45f4e10c9046a85b037e5e27a419d1e60f24b5',
    'workspace_windows.py': '20eb542209acfc70278844026d24fd74db4ad06e0b343227f579c01204be3471',
}


class ProbeError(Exception):
    """A fixed diagnostic code, never a path, upstream exception, or test trace."""


def require(condition, code):
    if not condition:
        raise ProbeError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*arguments):
    completed = subprocess.run(['git', *arguments], cwd=ROOT, capture_output=True, timeout=30)
    require(completed.returncode == 0, 'REQUIRED_LOCAL_GIT_OBJECT_UNAVAILABLE')
    return completed.stdout


def blob(revision, path):
    return git('show', revision + ':' + path)


def fresh_external(path):
    raw = str(path)
    require(path.is_absolute() and not raw.startswith(('\\\\', '//')),
            'ABSOLUTE_LOCAL_EXTERNAL_PATH_REQUIRED')
    require(not path.is_relative_to(ROOT), 'OUTPUT_MUST_BE_OUTSIDE_CHECKOUT')
    require(not path.exists() and not path.is_symlink() and not path.is_junction(), 'OUTPUT_MUST_BE_NEW')
    for parent in reversed(path.parents):
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
                and not getattr(info, 'st_file_attributes', 0) & 0x400,
                'ORDINARY_EXISTING_OUTPUT_PARENTS_REQUIRED')


# This authored private runner imports only the copied public test module. Its
# TestResult stores tracebacks without a TextTestRunner printing private paths.
RUNNER = r'''if not __debug__:
    raise RuntimeError('OPTIMIZED_PYTHON_UNSUPPORTED')
import importlib.metadata
import json
from pathlib import Path
import sys
import unittest

source, result_path, raw_path = map(Path, sys.argv[1:])
assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions())
sys.path.insert(0, str(source / 'tests'))
import test_download
assert Path(test_download.__file__).resolve() == source / 'tests/test_download.py'
test_id = 'test_download.Download.test_native_symlink_output_leaf_preserves_targets'
suite = unittest.defaultTestLoader.loadTestsFromName(test_id)
def flatten(selected):
    for item in selected:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item
assert [case.id() for case in flatten(suite)] == [test_id]
result = unittest.TestResult()
suite.run(result)
traces = [trace for case, trace in result.failures]
matches = (len(traces) == 1
           and 'self.assertFalse(absent.exists())' in traces[0]
           and traces[0].rstrip().endswith('AssertionError: True is not false'))
private = []
for kind, cases in (('FAILURE', result.failures), ('ERROR', result.errors)):
    for case, trace in cases:
        private.extend([kind + ' ' + case.id(), trace])
with raw_path.open('x', encoding='utf-8', newline='\n') as handle:
    handle.write('\n'.join(private))
summary = dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
               skipped=len(result.skipped),
               passed=result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
               expected_dangling_assertion=matches, fresh_venv=True, runtime_dependencies=0,
               native_links_required=True, python='.'.join(map(str, sys.version_info[:3])))
with result_path.open('x', encoding='utf-8', newline='\n') as handle:
    handle.write(json.dumps(summary, sort_keys=True) + '\n')
'''


def run_lane(workspace, label, runtime, test):
    selected = workspace / label
    selected.mkdir()
    source = selected / 'source'
    (source / 'tests').mkdir(parents=True)
    for name, data in runtime.items():
        (source / name).write_bytes(data)
    (source / 'tests/test_download.py').write_bytes(test)
    runner = selected / 'private-runner.py'
    runner.write_text(RUNNER, encoding='utf-8', newline='\n')
    temporary = selected / 'temp'
    temporary.mkdir()
    environment = selected / 'fresh-venv'
    venv.EnvBuilder(with_pip=False).create(environment)
    python = environment / 'Scripts/python.exe'
    result_path = selected / 'private-result.json'
    raw_path = selected / 'private-unittest.log'
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', PYTHON_COLORS='0', NO_COLOR='1',
               OUTLANDS_WORKSPACE_REQUIRE_LINKS='1', TEMP=str(temporary), TMP=str(temporary),
               OUTLANDS_TEST_TEMP=str(temporary), OUTLANDS_TEST_TEMP_ROOT=str(temporary))
    for key in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP', 'PYTHONSAFEPATH'):
        env.pop(key, None)
    try:
        completed = subprocess.run([str(python), '-I', '-B', '-W', 'error', str(runner),
                                    str(source), str(result_path), str(raw_path)],
                                   cwd=selected, env=env, stdin=subprocess.DEVNULL,
                                   capture_output=True, timeout=180)
    except subprocess.TimeoutExpired as error:
        (selected / 'private-process.log').write_bytes((error.stdout or b'') + (error.stderr or b''))
        raise ProbeError('COMPATIBILITY_CHILD_TIMEOUT') from None
    (selected / 'private-process.log').write_bytes(completed.stdout + completed.stderr)
    require(completed.returncode == 0 and result_path.is_file(), 'COMPATIBILITY_CHILD_DID_NOT_REPORT')
    require(completed.stdout == b'' and completed.stderr == b'', 'UNEXPECTED_CHILD_CONSOLE_OUTPUT')
    result = json.loads(result_path.read_text(encoding='utf-8'))
    require(result['fresh_venv'] is True and result['runtime_dependencies'] == 0
            and result['native_links_required'] is True and result['python'] == '3.15.2',
            'CHILD_RUNTIME_CONTRACT_CHANGED')
    require((source / 'tests/test_download.py').read_bytes() == test
            and all((source / name).read_bytes() == data for name, data in runtime.items()),
            'COPIED_SOURCE_CHANGED')
    require(not list(source.rglob('*.pyc')), 'BYTECODE_APPEARED_IN_COPIED_SOURCE')
    return result


def verify(args, report):
    require(sys.platform == 'win32', 'WINDOWS_REQUIRED')
    require(sys.version_info[:3] == (3, 15, 2), 'PYTHON_3_15_2_REQUIRED')
    fresh_external(args.workspace)
    fresh_external(args.report)
    require(not args.report.is_relative_to(args.workspace), 'SANITIZED_REPORT_MUST_BE_OUTSIDE_PRIVATE_WORKSPACE')
    revision = git('rev-parse', 'HEAD').decode('ascii').strip()
    require(re.fullmatch('[0-9a-f]{40}', revision) is not None, 'CURRENT_REVISION_INVALID')
    baseline_test = blob(BASELINE, TEST_PATH)
    current_test = (ROOT / TEST_PATH).read_bytes()
    require(current_test == baseline_test == blob(revision, TEST_PATH)
            and sha(current_test) == TEST_SHA256, 'PUBLIC_TEST_MUST_BE_EXACTLY_UNCHANGED')
    baseline = {name: blob(BASELINE, 'tools/project-workspace/' + name) for name in RUNTIME}
    current = {name: (ROOT / 'tools/project-workspace' / name).read_bytes() for name in RUNTIME}
    require({name: sha(data) for name, data in baseline.items()} == BASELINE_RUNTIME_SHA256,
            'BASELINE_RUNTIME_PINS_CHANGED')
    require(all(data == blob(revision, 'tools/project-workspace/' + name) for name, data in current.items()),
            'REVIEWED_RUNTIME_MUST_MATCH_CURRENT_GIT_BLOBS')
    require(baseline['workspace.py'] == current['workspace.py'], 'CLI_MUST_BE_UNCHANGED')
    require(baseline['workspace_windows.py'] != current['workspace_windows.py'], 'REVIEWED_BACKEND_CHANGE_REQUIRED')
    report.update(source_revision=revision, test_source_sha256=TEST_SHA256, test_unchanged=True,
                  baseline_runtime_sha256=BASELINE_RUNTIME_SHA256,
                  reviewed_runtime_sha256={name: sha(data) for name, data in current.items()})
    args.workspace.mkdir()
    before = run_lane(args.workspace, 'baseline', baseline, current_test)
    report.update(baseline_tests=before['tests'], baseline_failures=before['failures'],
                  baseline_errors=before['errors'], baseline_skipped=before['skipped'])
    require((before['tests'], before['failures'], before['errors'], before['skipped'], before['passed']) == (1, 1, 0, 0, 0)
            and before['expected_dangling_assertion'] is True,
            'BASELINE_MUST_REPRODUCE_EXACT_DANGLING_TARGET_ASSERTION')
    report['baseline_expected_dangling_target_creation'] = True
    after = run_lane(args.workspace, 'reviewed', current, current_test)
    report.update(reviewed_tests=after['tests'], reviewed_passed=after['passed'] == 1,
                  reviewed_failures=after['failures'], reviewed_errors=after['errors'], reviewed_skipped=after['skipped'])
    require((after['tests'], after['passed'], after['failures'], after['errors'], after['skipped']) == (1, 1, 0, 0, 0),
            'REVIEWED_RUNTIME_MUST_PASS_UNCHANGED_TEST')
    require(not after['expected_dangling_assertion'], 'REVIEWED_DANGLING_TARGET_ASSERTION_REMAINED')
    report.update(status='PASS', reviewed_passed_count=1, compatibility_executions=2,
                  qualification_matrix_executions_unchanged=576, outside_qualification_matrix=True,
                  fresh_dependency_free_venvs=True, runtime_dependencies=0, native_links_required=True,
                  copied_source_unchanged=True, bytecode_in_copied_source=False,
                  fixtures_generated_by_unchanged_public_test=True, real_inputs_used=False,
                  model_or_historical_data_used=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    report = dict(schema=1, status='FAIL', package='project-workspace',
                  probe='dangling-output-baseline-comparison', baseline_revision=BASELINE)
    try:
        verify(args, report)
    except ProbeError as error:
        report['code'] = str(error)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        report['code'] = 'PROBE_IO_OR_EXECUTION_ERROR'
    # The report contains only fixed codes, public revisions/hashes, and counts.
    # It never embeds captured child output, traces, selected paths, or bodies.
    try:
        fresh_external(args.report)
        with args.report.open('x', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(report, indent=2, sort_keys=True) + '\n')
    except (ProbeError, OSError, ValueError):
        print(json.dumps(dict(schema=1, status='FAIL', package='project-workspace', code='SANITIZED_REPORT_WRITE_FAILED')))
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
