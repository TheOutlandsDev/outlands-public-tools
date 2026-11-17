"""Machine-readable test observation inside the separate test image."""
import hashlib,importlib.metadata,json,sys
from pathlib import Path
import pytest

root=Path('/workspace');baseline=json.loads((root/'BASELINE.json').read_bytes())
class Recorder:
    def __init__(self):self.selected=[];self.started=[];self.passed=[];self.failed=[];self.skipped=[];self.warnings=[]
    def pytest_collection_finish(self,session):self.selected=[i.nodeid for i in session.items]
    def pytest_runtest_logstart(self,nodeid,location):self.started.append(nodeid)
    def pytest_runtest_logreport(self,report):
        if report.failed:self.failed.append(report.nodeid)
        if report.skipped:self.skipped.append(report.nodeid)
        if report.when=='call' and report.passed:self.passed.append(report.nodeid)
    def pytest_warning_recorded(self,warning_message,when,nodeid,location):self.warnings.append(dict(category=warning_message.category.__name__,message=str(warning_message.message)))
plugin=Recorder()
code=pytest.main(['-q','-p','no:cacheprovider','--basetemp','/tmp/control-tests',str(root/'tests')],plugins=[plugin])
assert code==0 and len(plugin.selected)==len(plugin.started)==len(plugin.passed)==16 and not plugin.failed and not plugin.skipped
assert set(plugin.selected)==set(plugin.started)==set(plugin.passed)
assert len(plugin.warnings)==1 and plugin.warnings[0]['category']=='StarletteDeprecationWarning'
assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==pin for name,pin in baseline['source_sha256'].items())
value=dict(status='PASS',profile='Linux-container-tests',python=sys.version.split()[0],tests=16,passed=16,skipped=0,failures=0,errors=0,original_tests=2,added_tests=14,selected_test_ids=sorted(plugin.selected),started_test_ids=sorted(plugin.started),successful_test_ids=sorted(plugin.passed),warnings=plugin.warnings,original_source_sha256=baseline['source_sha256'],dependencies={d.metadata['Name']:d.version for d in importlib.metadata.distributions()},actual_database_operations_verified=False,external_dependency_readiness_verified=False)
print(json.dumps(dict(container_test_receipt=value)))
