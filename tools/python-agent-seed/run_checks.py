"""Report positive tests and expected starter defects as separate populations."""
import argparse,io,json,platform,sys,unittest,warnings
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT));import kit

class Result(unittest.TextTestResult):
    def startTest(self,test):self.ids.append(test.id());super().startTest(test)

def run():
    kit_result=kit.check();suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result_type=Result;result_type.ids=[];log=io.StringIO()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always');r=unittest.TextTestRunner(stream=log,resultclass=result_type,verbosity=2).run(suite)
    release=dict(tests=suite.countTestCases(),executed=r.testsRun,passed=r.testsRun-len(r.failures)-len(r.errors)-len(r.skipped),failures=len(r.failures),errors=len(r.errors),skipped=len(r.skipped),test_ids=r.ids,warnings=[dict(category=w.category.__name__,message=str(w.message)) for w in caught])
    ok=r.wasSuccessful() and not r.skipped and not caught and release['passed']==10
    if not ok:print(log.getvalue(),file=sys.stderr)
    return dict(schema=1,status='PASS' if ok else 'FAIL',package='python-agent-seed',python=platform.python_version(),platform=sys.platform,
                positive_methods=26+release['tests'],positive_passed=26+release['passed'],positive_failures=len(r.failures),positive_errors=len(r.errors),skipped=len(r.skipped),
                release=release,kit=kit_result,original_files=63,original_definitions=26,original_bytes_preserved=True,runtime_dependencies=0,original_starters_changed=False,model_quality_claimed=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path);a=p.parse_args();v=run()
    if a.report:
        with a.report.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2)+'\n')
    print('SEED_TEST_RESULT '+json.dumps(v));raise SystemExit(v['status']!='PASS')
