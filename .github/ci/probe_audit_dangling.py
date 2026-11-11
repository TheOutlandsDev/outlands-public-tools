"""Compare two unchanged native Windows regressions with the sealed baseline.

These four diagnostic executions are separate from the eight qualification
lanes. Upload only the sanitized report. The owned workspace retains private
unittest traces. Native links are mandatory; no policy changes are attempted.
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
BASELINE = '3f7f1af3ac561a22d8b430d33db91b8d87b636cc'
DETECTOR_BASELINE = '2b0e55dfe2f1ba5340a0faeff40c777c9b3d6598'
SOURCE_PATH = 'tools/public-release-audit/'
TEST_PATH = SOURCE_PATH + 'tests/test_download.py'
TEST_IDS = (
    'test_download.Download.test_native_dangling_report_output_preserves_targets',
    'test_download.Download.test_native_dangling_write_manifest_output_preserves_targets',
)
TEST_SHA256 = '377193662d018db18d539135901676aaec59cca38273e6bb8f900de4df1e1416'
RUNTIME = ('release_audit.py', 'audit_windows.py')
BASELINE_RUNTIME_SHA256 = {
    'release_audit.py': 'f36a65dee30f9bd50b12bd30b5a2d6323956a6977e92b483f6ce5eb4dd527b52',
    'audit_windows.py': '2d9f22f82cfff85fe0323934c16d08d6d72973ea0435a6e3e030391082406192',
}
ANCHOR = ('        parent.verify()\n'
          '        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_BINARY | os.O_NOINHERIT, 0o600)\n')
GUARD = '''        # The Windows CRT can create a dangling symlink's target with O_EXCL.
        # Refuse every observed existing leaf before the creation attempt.
        try:
            path.lstat()
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError(errno.EEXIST, "OUTPUT_EXISTS")
'''


class ProbeError(Exception):
    """A fixed code without a selected path, upstream exception, or trace."""


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
    require(path.is_absolute() and not raw.startswith(('\\\\', '//'))
            and not any(part in ('.', '..') for part in path.parts)
            and not any(':' in part for part in path.parts[1:]),
            'ABSOLUTE_LOCAL_EXTERNAL_PATH_REQUIRED')
    require(not path.is_relative_to(ROOT), 'OUTPUT_MUST_BE_OUTSIDE_CHECKOUT')
    require(not path.exists() and not path.is_symlink() and not path.is_junction(), 'OUTPUT_MUST_BE_NEW')
    for parent in reversed(path.parents):
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
                and not getattr(info, 'st_file_attributes', 0) & 0x400,
                'ORDINARY_EXISTING_OUTPUT_PARENTS_REQUIRED')


# Import only the copied tests. Each case receives its own TestResult, so the
# exact baseline failure is checked independently and no trace is printed.
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
test_ids = __TEST_IDS__

def flatten(selected):
    for item in selected:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item

cases, private = [], []
for test_id in test_ids:
    suite = unittest.defaultTestLoader.loadTestsFromName(test_id)
    assert [case.id() for case in flatten(suite)] == [test_id]
    result = unittest.TestResult()
    suite.run(result)
    matches = (len(result.failures) == 1 and result.failures[0][0].id() == test_id
               and 'self.assertFalse(absent.exists())' in result.failures[0][1]
               and result.failures[0][1].rstrip().endswith('AssertionError: True is not false'))
    for kind, failures in (('FAILURE', result.failures), ('ERROR', result.errors)):
        for case, trace in failures:
            private.extend([kind + ' ' + case.id(), trace])
    cases.append(dict(test_id=test_id, tests=result.testsRun, failures=len(result.failures),
                      errors=len(result.errors), skipped=len(result.skipped),
                      passed=result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
                      expected_dangling_assertion=matches))
with raw_path.open('x', encoding='utf-8', newline='\n') as handle:
    handle.write('\n'.join(private))
summary = {key: sum(case[key] for case in cases) for key in ('tests', 'passed', 'failures', 'errors', 'skipped')}
summary.update(cases=cases, fresh_venv=True, runtime_dependencies=0, native_links_required=True,
               python='.'.join(map(str, sys.version_info[:3])))
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
    runner.write_text(RUNNER.replace('__TEST_IDS__', repr(TEST_IDS)), encoding='utf-8', newline='\n')
    temporary = selected / 'temp'
    temporary.mkdir()
    environment = selected / 'fresh-venv'
    venv.EnvBuilder(with_pip=False).create(environment)
    python = environment / 'Scripts/python.exe'
    result_path = selected / 'private-result.json'
    raw_path = selected / 'private-unittest.log'
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', PYTHON_COLORS='0', NO_COLOR='1',
               OUTLANDS_AUDIT_REQUIRE_LINKS='1', TEMP=str(temporary), TMP=str(temporary),
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


def expected_case(test_id, baseline):
    return dict(test_id=test_id, tests=1, failures=int(baseline), errors=0, skipped=0,
                passed=int(not baseline), expected_dangling_assertion=baseline)


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
    baseline = {name: blob(BASELINE, SOURCE_PATH + name) for name in RUNTIME}
    current = {name: (ROOT / SOURCE_PATH / name).read_bytes() for name in RUNTIME}
    require({name: sha(data) for name, data in baseline.items()} == BASELINE_RUNTIME_SHA256
            and all(data == blob(DETECTOR_BASELINE, SOURCE_PATH + name) for name, data in baseline.items()),
            'BASELINE_RUNTIME_PINS_CHANGED')
    require(all(data == blob(revision, SOURCE_PATH + name) for name, data in current.items()),
            'REVIEWED_RUNTIME_MUST_MATCH_CURRENT_GIT_BLOBS')
    require(baseline['release_audit.py'] == current['release_audit.py'], 'CLI_DETECTOR_AND_POSIX_MUST_BE_UNCHANGED')
    backend = baseline['audit_windows.py']
    require(backend.count(b'import ctypes\n') == 1 and backend.count(ANCHOR.encode()) == 1,
            'EXACT_BASELINE_PATCH_ANCHORS_REQUIRED')
    reviewed = backend.replace(b'import ctypes\n', b'import ctypes\nimport errno\n', 1).replace(
        ANCHOR.encode(), ANCHOR.replace('        fd =', GUARD + '        fd =').encode(), 1)
    require(current['audit_windows.py'] == reviewed and reviewed != backend, 'EXACT_REVIEWED_LEAF_GUARD_REQUIRED')
    report.update(source_revision=revision, test_source_sha256=TEST_SHA256, test_ids=list(TEST_IDS),
                  test_unchanged=True, exact_guard_only=True,
                  baseline_runtime_sha256=BASELINE_RUNTIME_SHA256,
                  reviewed_runtime_sha256={name: sha(data) for name, data in current.items()})
    args.workspace.mkdir()
    before = run_lane(args.workspace, 'baseline', baseline, current_test)
    report.update(baseline_tests=before['tests'], baseline_passed_count=before['passed'],
                  baseline_failures=before['failures'], baseline_errors=before['errors'],
                  baseline_skipped=before['skipped'], baseline_cases=before['cases'])
    require((before['tests'], before['failures'], before['errors'], before['skipped'], before['passed']) == (2, 2, 0, 0, 0)
            and before['cases'] == [expected_case(test_id, True) for test_id in TEST_IDS],
            'BASELINE_MUST_REPRODUCE_BOTH_EXACT_DANGLING_TARGET_ASSERTIONS')
    report['baseline_expected_dangling_target_creation'] = True
    after = run_lane(args.workspace, 'reviewed', current, current_test)
    report.update(reviewed_tests=after['tests'], reviewed_passed=after['passed'] == 2,
                  reviewed_passed_count=after['passed'], reviewed_failures=after['failures'],
                  reviewed_errors=after['errors'], reviewed_skipped=after['skipped'], reviewed_cases=after['cases'])
    require((after['tests'], after['passed'], after['failures'], after['errors'], after['skipped']) == (2, 2, 0, 0, 0)
            and after['cases'] == [expected_case(test_id, False) for test_id in TEST_IDS],
            'REVIEWED_RUNTIME_MUST_PASS_BOTH_UNCHANGED_TESTS')
    report.update(status='PASS', compatibility_executions=4,
                  qualification_matrix_executions_unchanged=680, outside_qualification_matrix=True,
                  fresh_dependency_free_venvs=True, runtime_dependencies=0, native_links_required=True,
                  copied_source_unchanged=True, bytecode_in_copied_source=False,
                  fixtures_generated_by_unchanged_public_test=True, real_inputs_used=False,
                  model_or_historical_data_used=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    report = dict(schema=1, status='FAIL', package='public-release-audit',
                  probe='dangling-output-baseline-comparison', baseline_revision=BASELINE,
                  detector_baseline_revision=DETECTOR_BASELINE)
    try:
        verify(args, report)
    except ProbeError as error:
        report['code'] = str(error)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        report['code'] = 'PROBE_IO_OR_EXECUTION_ERROR'
    # Only fixed codes, public revisions and hashes, booleans, IDs and counts
    # enter this report. Captured output, paths and traces remain private.
    try:
        fresh_external(args.report)
        with args.report.open('x', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(report, indent=2, sort_keys=True) + '\n')
    except (ProbeError, OSError, ValueError):
        print(json.dumps(dict(schema=1, status='FAIL', package='public-release-audit', code='SANITIZED_REPORT_WRITE_FAILED')))
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
