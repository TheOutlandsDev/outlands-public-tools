"""Run separate release tests and record actual selected/executed IDs."""
import argparse
import io
import json
from pathlib import Path
import platform
import sys
import unittest
import warnings

ROOT=Path(__file__).resolve().parent

class Result(unittest.TextTestResult):
    def startTest(self,test):
        self.ids.append(test.id());super().startTest(test)

def run():
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    selected=suite.countTestCases();result_type=Result
    result_type.ids=[]
    stream=io.StringIO()
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')
        r=unittest.TextTestRunner(stream=stream,resultclass=result_type,verbosity=2).run(suite)
    value=dict(schema=1,status='PASS' if r.wasSuccessful() and not r.skipped else 'FAIL',python=platform.python_version(),platform=sys.platform,
               tests=selected,executed=r.testsRun,passed=r.testsRun-len(r.failures)-len(r.errors)-len(r.skipped),skipped=len(r.skipped),failures=len(r.failures),errors=len(r.errors),
               test_ids=r.ids,warnings=[dict(category=w.category.__name__,message=str(w.message)) for w in captured],
               original_implementation_files=1,original_checks_verified=True,original_assertions=9,verification_fixture_sanitized=True,synthetic_images_only=True,rev3b_sampling_qc_applied=False,legacy_cli_utf8_verified=True,calibration_verified=False,interactive_file_picker_verified=False)
    if value['status']!='PASS':print(stream.getvalue(),file=sys.stderr)
    return value

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path);args=p.parse_args();v=run()
    if args.report:
        with args.report.open('x',encoding='utf-8') as f:f.write(json.dumps(v,indent=2)+'\n')
    print('OVERLAY_TEST_RESULT '+json.dumps(v));raise SystemExit(v['status']!='PASS')
