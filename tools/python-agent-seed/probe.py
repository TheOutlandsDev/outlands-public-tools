"""Internal trusted-fixture runner; audit hooks are not OS containment."""
import argparse
import ast
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import warnings

ROOT = Path(__file__).resolve().parent
TASKS = ['eval_001_pathlib_json_loader', 'eval_002_secure_subprocess', 'eval_003_typed_validation', 'eval_004_mutable_default', 'eval_005_csv_summary', 'expanded_002_secure_subprocess']

class Result(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.started = []; self.passed_ids = []; self.error_types = []
    def startTest(self, test):
        self.started.append(test.id()); super().startTest(test)
    def addSuccess(self, test):
        self.passed_ids.append(test.id()); super().addSuccess(test)
    def addError(self, test, error):
        self.error_types.append(dict(test=test.id(), exception=error[0].__name__)); super().addError(test, error)

def observe(mode, task):
    attempts = []
    def audit(event, args):
        if event == 'exec' and (ROOT/'original/04_examples/bad') in Path(args[0].co_filename).parents:
            attempts.append('excluded_bad_example_exec')
            raise RuntimeError('UNREVIEWED_PROCESS_OR_NETWORK_REFUSED')
        if event in ('socket.connect', 'socket.getaddrinfo', 'subprocess.Popen', 'os.system'):
            wanted = [sys.executable, '-c', "print('ok')"]
            if event == 'subprocess.Popen' and os.name == 'nt' and isinstance(args[1], str):
                # Windows audits the final command-line string; applicationName
                # may be None because the absolute executable is in that string.
                same = args[1] == subprocess.list2cmdline(wanted) and (args[0] is None or os.path.normcase(str(args[0])) == os.path.normcase(sys.executable))
            else:
                same = event == 'subprocess.Popen' and list(args[1]) == wanted and os.path.normcase(str(args[0])) == os.path.normcase(sys.executable)
            allowed = event == 'subprocess.Popen' and mode == 'examples' and same
            if not allowed:
                attempts.append(event)
                raise RuntimeError('UNREVIEWED_PROCESS_OR_NETWORK_REFUSED')
    sys.addaudithook(audit)
    for event in ('subprocess.Popen', 'socket.connect', 'excluded_bad_example_exec'):
        try:
            if event == 'subprocess.Popen':
                subprocess.Popen([sys.executable, '-c', 'pass'])
            elif event == 'socket.connect':
                sys.audit('socket.connect', None, ('127.0.0.1', 9))
            else:
                exec(compile('pass', str(ROOT/'original/04_examples/bad/unsafe_eval.py'), 'exec'), {})
        except RuntimeError as error:
            assert str(error) == 'UNREVIEWED_PROCESS_OR_NETWORK_REFUSED'
        else:
            raise RuntimeError('AUDIT_CANARY_NOT_REFUSED')
    assert attempts == ['subprocess.Popen', 'socket.connect', 'excluded_bad_example_exec']
    attempts.clear()
    if mode == 'examples':
        tests = ROOT/'original/04_examples/good/tests'
        sys.path.insert(0, str(ROOT/'original/04_examples/good/src'))
    else:
        assert task in TASKS
        base = ROOT/'original-expanded/test_002_secure_subprocess' if task == TASKS[-1] else ROOT/'original/05_evals'/task
        tests = base/'tests'
        sys.path.insert(0, str(base if mode == 'starter' else ROOT/'references'/task))
    declared = sum(sum(isinstance(n, ast.FunctionDef) and n.name.startswith('test_') for n in ast.walk(ast.parse(p.read_bytes()))) for p in tests.glob('test_*.py'))
    loader = unittest.TestLoader()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        suite = loader.discover(str(tests))
        discovered = suite.countTestCases()
        result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=2, resultclass=Result).run(suite)
    imports = [v for v in result.error_types if v['test'].startswith('unittest.loader._FailedTest.')]
    return dict(mode=mode, task=task, declared_methods=declared, framework_entries=discovered, framework_started=result.testsRun,
                actual_methods_started=len([v for v in result.started if not v.startswith('unittest.loader._FailedTest.')]),
                passed=len(result.passed_ids), failures=len(result.failures), errors=len(result.errors), import_failures=len(imports), skipped=len(result.skipped),
                started_ids=result.started, passed_ids=result.passed_ids, failure_ids=[test.id() for test, _ in result.failures], error_types=result.error_types,
                warnings=[dict(category=w.category.__name__, message=str(w.message)) for w in caught],
                audit_canaries_refused=3, unreviewed_runtime_attempts=attempts, success=result.wasSuccessful(), raw_tracebacks_included=False)

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--mode', required=True, choices=['examples', 'starter', 'reference']); p.add_argument('--task', choices=TASKS)
    a = p.parse_args(); print(json.dumps(observe(a.mode, a.task)))
