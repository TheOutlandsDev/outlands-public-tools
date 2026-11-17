"""Run the unchanged expanded helper on a disposable, fixed exercise copy."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
import warnings

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import kit
from probe import Result


def run(mode):
    assert mode in ('starter', 'reference')
    task = kit.TASKS[-1]
    with tempfile.TemporaryDirectory(prefix='seed-expanded-copy-') as temp:
        copy = Path(temp)/'exercise'
        kit.prepare(task, copy)
        if mode == 'reference':
            for name in ('__init__.py', 'git_status.py'):
                shutil.copyfile(ROOT/'references'/task/'starter'/name, copy/'starter'/name)
        attempts = []
        def audit(event, args):
            if event in ('subprocess.Popen', 'os.system', 'socket.connect', 'socket.getaddrinfo'):
                attempts.append(event)
                raise RuntimeError('PROCESS_OR_NETWORK_REFUSED')
        sys.addaudithook(audit)
        for event in ('subprocess.Popen', 'socket.connect'):
            try:
                if event == 'subprocess.Popen':
                    subprocess.Popen([sys.executable, '-c', 'pass'])
                else:
                    sys.audit(event, None, ('127.0.0.1', 9))
            except RuntimeError as error:
                assert str(error) == 'PROCESS_OR_NETWORK_REFUSED'
            else:
                raise RuntimeError('AUDIT_CANARY_NOT_REFUSED')
        assert attempts == ['subprocess.Popen', 'socket.connect']
        attempts.clear()
        results = []
        runner = unittest.TextTestRunner
        class RecordingRunner(runner):
            def __init__(self, *args, **kwargs):
                kwargs.update(stream=io.StringIO(), resultclass=Result)
                super().__init__(*args, **kwargs)
            def run(self, suite):
                result = super().run(suite)
                results.append(result)
                return result
        # Capture results without editing the original helper or its test suite.
        unittest.TextTestRunner = RecordingRunner
        try:
            with warnings.catch_warnings(record=True) as caught, contextlib.redirect_stdout(io.StringIO()):
                warnings.simplefilter('always')
                try:
                    runpy.run_path(str(copy/'scripts/run_tests.py'), run_name='__main__')
                except SystemExit as error:
                    exit_code = error.code
                else:
                    raise RuntimeError('ORIGINAL_RUNNER_DID_NOT_EXIT')
        finally:
            unittest.TextTestRunner = runner
        assert len(results) == 1
        result = results[0]
        value = dict(mode=mode, task=task, declared_methods=5,
            framework_entries=result.testsRun, framework_started=result.testsRun,
            actual_methods_started=len(result.started), passed=len(result.passed_ids),
            failures=len(result.failures), errors=len(result.errors), import_failures=0,
            skipped=len(result.skipped), started_ids=result.started,
            passed_ids=result.passed_ids, failure_ids=[test.id() for test, _ in result.failures],
            error_types=result.error_types,
            warnings=[dict(category=w.category.__name__, message=str(w.message)) for w in caught],
            audit_canaries_refused=2, unreviewed_runtime_attempts=attempts,
            success=result.wasSuccessful(), runner_exit=exit_code,
            original_runner_executed=True, disposable_copy=True, original_files_changed=False,
            raw_tracebacks_included=False)
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=('starter', 'reference'))
    print(json.dumps(run(parser.parse_args().mode)))
