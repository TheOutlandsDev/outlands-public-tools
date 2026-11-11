"""Qualify fresh Python Helpers source ZIPs and independent copied-library API consumers."""
if not __debug__:
    raise RuntimeError('OPTIMIZED_PYTHON_UNSUPPORTED')

import argparse
from contextlib import ExitStack
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import venv
import zipfile

ROOT=Path(__file__).resolve().parents[1]
RUNTIME_SHA256={'helpers.py': '4c45bce6364c221fd28040ec60055d50ae90684c5d2db2a7275843bfa60f7c8d', 'helpers_windows.py': 'a68f9aac8df6fc299fddd62c63d253ce3fbec6595c8aabb60ea9e54b3ff1df27'}
PROCESS_CASES=26
PROCESS_LINKS={
    'test_download.Download.test_native_symlink_leaf_inputs_are_refused',
    'test_download.Download.test_native_symlink_parent_is_refused',
}
PROCESS_WINDOWS_SKIPS={
    ('test_download.Download.test_native_posix_fifo_and_short_socket_are_refused','Native POSIX special file fixture'),
}
PROCESS_POSIX_SKIPS={
    ('test_download.Download.test_native_windows_junction_parent_is_refused','Native Windows junction fixture'),
    ('test_download.Download.test_native_windows_alternate_stream_is_refused','Native Windows alternate stream fixture'),
}

def pairs(rows):return {(row['test'],row['reason']) for row in rows}

def flatten(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):yield from flatten(item)
        else:yield item

def group(suite,expected,required,optional):
    selected=list(flatten(suite));ids=[test.id() for test in selected]
    assert len(ids)==len(set(ids))==expected,'MISSING_OR_DUPLICATE_TESTS'
    counts={}
    for name in ids:counts[name.split('.',1)[0]]=counts.get(name.split('.',1)[0],0)+1
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    skipped=[dict(test=test.id(),reason=reason) for test,reason in result.skipped]
    observed=pairs(skipped)
    unexpected=[row for row in skipped if (row['test'],row['reason']) not in required|optional]
    for module in counts:
        assert sum(row['test'].split('.',1)[0]==module for row in skipped)<counts[module],'WHOLLY_SKIPPED_MODULE'
    ok=result.wasSuccessful() and result.testsRun==expected and len(skipped)==len(observed) and required<=observed<=required|optional
    return dict(status='PASS' if ok else 'FAIL',tests=result.testsRun,
        passed=result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors),skipped=len(result.skipped),
        failures=len(result.failures),errors=len(result.errors),skips=skipped,unexpected_skips=unexpected,
        failed_tests=[test.id() for test,trace in result.failures+result.errors],module_counts=counts,test_ids=ids)

def run_tests(report):
    assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions()),'FRESH_DEPENDENCY_FREE_VENV_REQUIRED'
    sys.path.insert(0,str(ROOT))
    import helpers,helpers_windows
    for name in RUNTIME_SHA256:
        assert Path(sys.modules[Path(name).stem].__file__).resolve()==ROOT/name,'IMPORT_NOT_FROM_EXTRACTION'
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==RUNTIME_SHA256[name],'RUNTIME_SOURCE_CHANGED'
    strict=os.name!='nt' or os.environ.get('OUTLANDS_HELPERS_REQUIRE_LINKS')=='1'
    contract=json.loads((ROOT/'tests/SKIP-CONTRACT.json').read_text())
    loader=unittest.TestLoader()
    regressions=unittest.TestSuite(loader.discover(str(ROOT/'tests'),pattern=name+'.py') for name in contract['module_counts'])
    selected=list(flatten(regressions))
    pinned={name for names in contract['test_ids'].values() for name in names}
    assert {test.id() for test in selected}==pinned and len(selected)==contract['total_methods']==45,'REGRESSION_DISCOVERY_CHANGED'
    required=pairs(contract['windows_required_skips'] if os.name=='nt' else contract['posix_required_skips'])
    optional=pairs(contract['windows_short_name_absence_skips']) if os.name=='nt' else set()
    if os.name=='nt' and not strict:optional|=pairs(contract['windows_optional_1314_skips'])
    regression=group(regressions,45,required,optional)
    assert regression['module_counts']==contract['module_counts'],'REGRESSION_MODULE_DISCOVERY_CHANGED'
    copied=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_download.py')
    required=PROCESS_WINDOWS_SKIPS if os.name=='nt' else PROCESS_POSIX_SKIPS
    optional={(name,'Native symlink privilege unavailable') for name in PROCESS_LINKS} if os.name=='nt' and not strict else set()
    integration=group(copied,PROCESS_CASES,required,optional)
    integration.update(copied_runtime_only=True,copied_library_api=True,fresh_dependency_free_venv=True)
    unchanged=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in RUNTIME_SHA256.items())
    summary=dict(schema=1,status='PASS' if regression['status']==integration['status']=='PASS' and unchanged else 'FAIL',
        package='python-helpers',version='0.1.0',platform=sys.platform,python='.'.join(map(str,sys.version_info[:3])),
        tests=regression['tests']+integration['tests'],passed=regression['passed']+integration['passed'],
        skipped=regression['skipped']+integration['skipped'],failures=regression['failures']+integration['failures'],errors=regression['errors']+integration['errors'],
        unexpected_skips=regression['unexpected_skips']+integration['unexpected_skips'],regression=regression,integration=integration,
        fresh_venv=True,extracted_import=True,runtime_dependencies=0,native_links_required=strict,
        runtime_unchanged=unchanged,runtime_sha256=RUNTIME_SHA256,model_or_historical_data_used=False)
    report.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
    return 0 if summary['status']=='PASS' else 1

def qualify(packages,reference,workspace,report):
    assert packages.is_absolute() and workspace.is_absolute() and not workspace.exists() and workspace.parent.is_dir()
    assert not workspace.is_relative_to(ROOT) and not report.exists() and report.parent.is_dir()
    receipt=json.loads((packages/'build-manifest.json').read_text())
    assert receipt['package']=='python-helpers' and receipt['version']=='0.1.0' and receipt['files']==22
    assert receipt['filename']=='python-helpers-0.1.0.zip'
    archive=packages/receipt['filename']
    assert archive.stat().st_size==receipt['bytes'] and hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['sha256']
    identical=False
    if reference is not None:
        assert reference.is_absolute() and reference.resolve()!=packages.resolve()
        assert (reference/receipt['filename']).read_bytes()==archive.read_bytes(),'ARCHIVE_BYTES_DIFFER'
        assert (reference/'build-manifest.json').read_bytes()==(packages/'build-manifest.json').read_bytes(),'BUILD_MANIFEST_BYTES_DIFFER'
        identical=True
    workspace.mkdir();prefix='python-helpers-0.1.0/'
    with zipfile.ZipFile(archive) as source:
        names=source.namelist();manifest=json.loads(source.read(prefix+'SOURCE-MANIFEST.json'))
        assert len(names)==len(set(names))==22 and len(manifest['files'])==21
        assert set(names)=={prefix+row['path'] for row in manifest['files']}|{prefix+'SOURCE-MANIFEST.json'}
        for name in names:
            assert name.startswith(prefix) and '..' not in name.split('/') and '\\' not in name and ':' not in name
            info=source.getinfo(name)
            assert info.external_attr>>16==0o100644 and info.create_system==3 and info.compress_type==zipfile.ZIP_STORED and info.date_time==(1980,1,1,0,0,0)
        for row in manifest['files']:
            data=source.read(prefix+row['path'])
            assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
            assert data==(ROOT/row['path']).read_bytes(),'ARCHIVE_SOURCE_DIFFERS'
        source.extractall(workspace)
    app=workspace/prefix;temp=workspace/'temp';temp.mkdir()
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',TEMP=str(temp),TMP=str(temp),OUTLANDS_TEST_TEMP=str(temp),OUTLANDS_TEST_TEMP_ROOT=str(temp))
    env.pop('PYTHONPATH',None)
    def command(args,log,timeout=240):
        result=subprocess.run(args,cwd=app,env=env,capture_output=True,timeout=timeout)
        (workspace/log).write_bytes(result.stdout+result.stderr)
        return result
    gate=command([sys.executable,'-I','-B',str(app/'source_check.py')],'source-check.log')
    assert gate.returncode==0,'EXTRACTED_SOURCE_GATE_FAILED'
    for helper in ('build.py','qualify.py'):
        refused=command([sys.executable,'-O','-B',str(app/'packaging'/helper),'--help'],helper+'-optimized.log')
        assert refused.returncode!=0 and b'OPTIMIZED_PYTHON_UNSUPPORTED' in refused.stderr,'OPTIMIZATION_REFUSAL_FAILED'
    environment=workspace/'fresh-venv';venv.EnvBuilder(with_pip=False).create(environment)
    python=environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    with ExitStack() as owned:
        if os.name!='nt':
            # AF_UNIX filesystem socket names are short on some hosts. Keep the
            # generated fixtures in an owned short temporary parent rather than
            # skip their safeguards because the extraction path is long.
            short=Path(owned.enter_context(tempfile.TemporaryDirectory(prefix='oph-')))
            assert short.is_absolute() and short.parent==Path(tempfile.gettempdir()).resolve()
            env.update(TEMP=str(short),TMP=str(short),OUTLANDS_TEST_TEMP=str(short),OUTLANDS_TEST_TEMP_ROOT=str(short))
        done=command([str(python),'-I','-B','-W','error',str(app/'packaging/qualify.py'),'--tests','--report',str(report)],'qualification-private.log')
    assert report.exists(),'QUALIFICATION_DID_NOT_REPORT'
    result=json.loads(report.read_text())
    result.update(source_revision=receipt['source_revision'],zip_sha256=receipt['sha256'],archive_members=22,source_files=21,
        fresh_extraction=True,source_gate=True,source_manifest_verified=True,identical_zip=identical,
        identical_build_manifest=identical,optimization_refusal=True)
    report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result));return done.returncode

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packages',type=Path);parser.add_argument('--reference-build',type=Path)
    parser.add_argument('--workspace',type=Path);parser.add_argument('--report',required=True,type=Path)
    parser.add_argument('--tests',action='store_true',help=argparse.SUPPRESS);args=parser.parse_args()
    if args.tests:raise SystemExit(run_tests(args.report))
    if args.packages is None or args.workspace is None:parser.error('--packages and --workspace are required')
    raise SystemExit(qualify(args.packages,args.reference_build,args.workspace,args.report))
