"""Qualify a committed literal module-metadata source archive using a fresh environment without packages."""
if not __debug__:
    raise RuntimeError('OPTIMIZED_PYTHON_UNSUPPORTED')
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import venv
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PACKAGE='kernel-module-inspector'
VERSION='0.1.0'
RUNTIME_SHA256={'module_inspector.py': 'a7473c76391146269fb892e7f1a0ee0f098a26e84ecd1850fc7db185588d7ecf', 'inspection_support.py': '45c9a4fce67ab695ea11d56adcb473ad7034fadf580860eb2db35307a709ee01', 'examples/generate.py': 'd84499b9319b83deb8a3776db6a9b19cca9e1afb9bfc9cb565ebc315ce1e2158'}

def sha(raw):return hashlib.sha256(raw).hexdigest()

def preparation():
    spec=importlib.util.spec_from_file_location('module_python_preparation',ROOT/'packaging/prepare_python.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def flatten(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):yield from flatten(item)
        else:yield item

def pairs(rows):return {(r['test'],r['reason']) for r in rows}

def run_tests(report):
    assert report.is_absolute() and report.parent.is_dir() and not os.path.lexists(report)
    assert not report.resolve().is_relative_to(ROOT.resolve())
    assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions()),'FRESH_EMPTY_VENV_REQUIRED'
    sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
    import module_inspector as inspector
    import inspection_support
    import original_support
    assert Path(inspector.__file__).resolve()==ROOT/'module_inspector.py'
    assert Path(inspection_support.__file__).resolve()==ROOT/'inspection_support.py'
    strict=os.name!='nt' or os.environ.get('OUTLANDS_MODULE_REQUIRE_LINKS')=='1'
    regression=original_support.run_originals(strict=strict,log_stream=sys.stderr)
    assert regression['tests']==38
    import test_download as copied
    suite=unittest.defaultTestLoader.loadTestsFromModule(copied)
    ids=[t.id() for t in flatten(suite)]
    assert len(ids)==len(set(ids))==30 and all(name.startswith('test_download.Download.test_') for name in ids)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    skips=[dict(test=t.id(),reason=reason) for t,reason in result.skipped]
    required=copied.REQUIRED_WINDOWS_SKIPS if os.name=='nt' else copied.REQUIRED_POSIX_SKIPS
    optional=copied.OPTIONAL_WINDOWS_LINK_SKIPS if os.name=='nt' and not strict else set()
    policies=copied.REQUIRED_WINDOWS_SKIPS|copied.REQUIRED_POSIX_SKIPS|copied.OPTIONAL_WINDOWS_LINK_SKIPS
    assert all(test in set(ids) for test,reason in policies),'COPIED_SKIP_POLICY_HAS_UNSELECTED_TEST'
    observed=pairs(skips)
    unexpected=[r for r in skips if (r['test'],r['reason']) not in required|optional]
    ok=result.wasSuccessful() and result.testsRun==30 and len(observed)==len(skips) and required<=observed<=required|optional
    failed_ids=sorted({getattr(test,'test_case',test).id() for test,trace in result.failures+result.errors})
    integration=dict(status='PASS' if ok else 'FAIL',tests=result.testsRun,
        passed=result.testsRun-len(result.skipped)-len(failed_ids),skipped=len(result.skipped),
        failures=len(result.failures),errors=len(result.errors),skips=skips,unexpected_skips=unexpected,
        failed_tests=failed_ids,failed_methods=len(failed_ids),module_counts={'test_download':30},test_ids=ids,
        copied_runtime_only=True,copied_runtime_cli=True,fictional_inputs_only=True,
        module_binaries_opened=False,modules_loaded=False,modules_decompressed=False,kmod_invoked=False,devices_accessed=False,real_system_inventory_used=False,kernel_abi_compatibility_verified=False,runtime_load_verified=False,reports_and_static_html_checked=True)
    unchanged=all(sha((ROOT/name).read_bytes())==digest for name,digest in RUNTIME_SHA256.items())
    assert not list(importlib.metadata.distributions())
    value=dict(schema=1,package=PACKAGE,version=VERSION,
        status='PASS' if regression['status']==integration['status']=='PASS' and unchanged else 'FAIL',
        platform=sys.platform,python='.'.join(map(str,sys.version_info[:3])),tests=68,
        passed=regression['passed']+integration['passed'],skipped=regression['skipped']+integration['skipped'],
        failures=regression['failures']+integration['failures'],errors=regression['errors']+integration['errors'],
        unexpected_skips=regression['unexpected_skips']+integration['unexpected_skips'],
        regression=regression,integration=integration,
        fresh_venv=True,extracted_import=True,native_links_required=strict,
        runtime_unchanged=unchanged,runtime_sha256=RUNTIME_SHA256,
        runtime_dependencies=0,runtime_distributions=0,pip_in_application=False,
        module_binaries_opened=False,modules_loaded=False,modules_decompressed=False,kmod_invoked=False,devices_accessed=False,real_system_inventory_used=False,kernel_abi_compatibility_verified=False,runtime_load_verified=False,
        python_pin=regression['python_pin'])
    report.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    return 0 if value['status']=='PASS' else 1

def qualify(packages,reference,workspace,report,python_root=None,python_receipt=None):
    lock_raw=(ROOT/'PYTHON-LOCK.json').read_bytes();lock=json.loads(lock_raw)
    version='.'.join(map(str,sys.version_info[:3]));minor='.'.join(map(str,sys.version_info[:2]))
    assert sys.platform in {'win32','linux'} and version==lock['python_versions'][minor],'LOCKED_PYTHON_PATCH_REQUIRED'
    base=Path(sys._base_executable).resolve();base_sha=sha(base.read_bytes())
    for path in (workspace,report):
        assert path.is_absolute() and path.parent.is_dir() and not os.path.lexists(path)
        assert path.parent.resolve()==path.parent and not path.parent.is_symlink() and not getattr(path.parent,'is_junction',lambda:False)()
        assert not path.resolve().is_relative_to(ROOT.resolve())
    python_preparation=None
    if python_root is not None or python_receipt is not None:
        assert python_root is not None and python_receipt is not None
        assert python_root.is_absolute() and python_root.is_dir() and python_receipt.is_absolute() and python_receipt.is_file()
        python_preparation=json.loads(python_receipt.read_bytes());pin=python_preparation
        assert pin['schema']==1 and pin['status']=='PASS' and pin['platform']==sys.platform and pin['python_version']==version
        assert pin['build_release']==lock['python_build_release'] and pin['archive']==lock['python_archives'][sys.platform][minor]
        assert pin['preparation_helper_sha256']==sha((ROOT/'packaging/prepare_python.py').read_bytes()) and pin['python_lock_sha256']==sha(lock_raw)
        assert pin['archive_sha256_verified'] is pin['actual_interpreter_verified'] is True
        assert pin['global_install_performed'] is pin['binary_reproducibility_claimed'] is False
        selected=(python_root/pin['executable_relative']).resolve()
        assert selected.is_relative_to(python_root.resolve()) and selected==base and pin['executable_sha256']==base_sha and pin['executable_bytes']==base.stat().st_size
    assert packages.is_absolute() and packages.is_dir()
    receipt=json.loads((packages/'build-manifest.json').read_bytes())
    assert receipt['schema']==1 and receipt['package']==PACKAGE and receipt['version']==VERSION
    assert re.fullmatch('[a-f0-9]{40}',receipt['source_revision'])
    assert receipt['filename']==PACKAGE+'-'+VERSION+'.zip'
    archive=packages/receipt['filename'];assert archive.stat().st_size==receipt['bytes'] and sha(archive.read_bytes())==receipt['sha256']
    identical=False
    if reference is not None:
        assert reference.is_absolute() and reference.resolve()!=packages.resolve()
        assert (reference/receipt['filename']).read_bytes()==archive.read_bytes()
        assert (reference/'build-manifest.json').read_bytes()==(packages/'build-manifest.json').read_bytes()
        identical=True
    workspace.mkdir();prefix=PACKAGE+'-'+VERSION+'/'
    with zipfile.ZipFile(archive) as source:
        names=source.namelist();manifest=json.loads(source.read(prefix+'SOURCE-MANIFEST.json'))
        assert len(names)==len(set(names))==receipt['files']==len(manifest['files'])+1==30
        assert len(manifest['files'])==29
        assert set(names)=={prefix+row['path'] for row in manifest['files']}|{prefix+'SOURCE-MANIFEST.json'}
        for name in names:
            assert name.startswith(prefix) and '..' not in name.split('/') and '\\' not in name and ':' not in name
            info=source.getinfo(name)
            assert info.external_attr>>16==0o100644 and info.create_system==3
            assert info.compress_type==zipfile.ZIP_STORED and info.date_time==(1980,1,1,0,0,0)
        for row in manifest['files']:
            data=source.read(prefix+row['path'])
            assert len(data)==row['bytes'] and sha(data)==row['sha256'] and data==(ROOT/row['path']).read_bytes(),'ARCHIVE_SOURCE_DIFFERS'
        assert source.read(prefix+'SOURCE-MANIFEST.json')==(ROOT/'SOURCE-MANIFEST.json').read_bytes()
        source.extractall(workspace)
    app=workspace/prefix
    if os.name=='nt':
        temp=workspace/'temp';temp.mkdir()
    else:
        temp=Path(tempfile.mkdtemp(prefix='build-',dir='/tmp'));assert temp.resolve()==temp and not temp.is_symlink()
    env=preparation().clean_environment()
    env.update(TEMP=str(temp),TMP=str(temp),TMPDIR=str(temp),OUTLANDS_TEST_TEMP=str(temp),OUTLANDS_TEST_TEMP_ROOT=str(temp),
        OUTLANDS_TEST_PYTHON_SHA256=base_sha,OUTLANDS_TEST_PYTHON_VERSION=version)
    def command(args,log,timeout=300):
        result=subprocess.run(args,cwd=app,env=env,capture_output=True,timeout=timeout)
        (workspace/log).write_bytes(result.stdout+result.stderr)
        return result
    assert command([sys.executable,'-I','-B',str(app/'source_check.py')],'source-check-private.log').returncode==0
    for name in ('source_check.py','packaging/build.py','packaging/qualify.py','packaging/prepare_python.py','tests/original_support.py'):
        done=command([sys.executable,'-O','-B',str(app/name),'--help'],name.replace('/','-')+'-optimized-private.log')
        assert done.returncode!=0 and b'OPTIMIZED_PYTHON_UNSUPPORTED' in done.stderr
    environment=workspace/'fresh-venv';venv.EnvBuilder(with_pip=False).create(environment)
    python=environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    done=command([str(python),'-I','-B','-W','error',str(app/'packaging/qualify.py'),'--tests','--report',str(report)],'qualification-private.log',timeout=600)
    assert report.exists(),'QUALIFICATION_DID_NOT_REPORT'
    value=json.loads(report.read_bytes());assert not list(app.rglob('*.pyc')),'SOURCE_BYTECODE_UNEXPECTED'
    assert sha(base.read_bytes())==base_sha
    assert value['python_pin']['python']==version and value['python_pin']['executable_sha256']==base_sha
    value.update(source_revision=receipt['source_revision'],zip_sha256=receipt['sha256'],archive_members=len(names),source_files=len(manifest['files']),
        fresh_extraction=True,source_gate=True,source_manifest_verified=True,identical_zip=identical,identical_build_manifest=identical,
        optimization_refusal=True,source_bytecode_files=0,inherited_pip_and_python_environment_removed=True,
        fixture_temp_mode='workspace_owned_windows' if os.name=='nt' else 'short_owned_posix',python_preparation=python_preparation)
    report.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(value))
    return done.returncode

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packages',type=Path);parser.add_argument('--reference-build',type=Path)
    parser.add_argument('--workspace',type=Path);parser.add_argument('--python-root',type=Path);parser.add_argument('--python-receipt',type=Path)
    parser.add_argument('--report',required=True,type=Path);parser.add_argument('--tests',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.tests:raise SystemExit(run_tests(args.report))
    if any(value is None for value in (args.packages,args.workspace)):
        parser.error('--packages and --workspace are required')
    raise SystemExit(qualify(args.packages,args.reference_build,args.workspace,args.report,args.python_root,args.python_receipt))
