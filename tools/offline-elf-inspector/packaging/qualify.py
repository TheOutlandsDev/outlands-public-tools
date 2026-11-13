"""Qualify a committed standalone ELF source archive in a fresh empty environment."""
if not __debug__:
    raise RuntimeError('OPTIMIZED_PYTHON_UNSUPPORTED')
import argparse
import hashlib
import importlib.metadata
import importlib.util
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
PACKAGE='offline-elf-inspector'
VERSION='1.1.0'
RUNTIME_SHA256={'elf_inspector.py':'ab2336c991490122b315aa71c3aba7d407cd23a822ec2c7a1b54788308c84501','examples/make_demo.py':'beda180104f4f71456edda889a82b9280ffcc82e47de0cad110aca7a1f7635bc'}
PROCESS_LINKS={'test_download.Download.test_native_symlink_input_root_and_output_parents'}
PROCESS_WINDOWS_SKIPS={('test_download.Download.test_native_posix_special_files_are_not_opened','Native POSIX FIFO and socket fixture'),('test_download.Download.test_linux_compiler_metadata_matches_pinned_readelf_oracle','Linux GCC and readelf oracle fixture')}
PROCESS_POSIX_SKIPS={('test_download.Download.test_native_windows_junctions_are_not_followed','Native Windows junction fixture')}

def sha(raw):return hashlib.sha256(raw).hexdigest()

def preparation():
    spec=importlib.util.spec_from_file_location('elf_source_oracle_preparation',ROOT/'packaging/prepare_oracle.py')
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
    import elf_inspector as inspector
    import original_support
    assert Path(inspector.__file__).resolve()==ROOT/'elf_inspector.py' and inspector.VERSION==VERSION
    strict=os.name!='nt' or os.environ.get('OUTLANDS_ELF_REQUIRE_LINKS')=='1'
    regression=original_support.run_originals(strict=strict,log_stream=sys.stderr)
    assert regression['tests']==73
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_download.py')
    selected=list(flatten(suite));ids=[t.id() for t in selected]
    assert len(ids)==len(set(ids))==30
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    skips=[dict(test=t.id(),reason=reason) for t,reason in result.skipped]
    required=PROCESS_WINDOWS_SKIPS if os.name=='nt' else PROCESS_POSIX_SKIPS
    optional={(name,'Native symlink privilege unavailable') for name in PROCESS_LINKS} if os.name=='nt' and not strict else set()
    observed=pairs(skips);unexpected=[r for r in skips if (r['test'],r['reason']) not in required|optional]
    ok=result.wasSuccessful() and result.testsRun==30 and len(observed)==len(skips) and required<=observed<=required|optional
    integration=dict(status='PASS' if ok else 'FAIL',tests=result.testsRun,
        passed=result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors),skipped=len(result.skipped),
        failures=len(result.failures),errors=len(result.errors),skips=skips,unexpected_skips=unexpected,
        failed_tests=[t.id() for t,trace in result.failures+result.errors],module_counts={'test_download':30},test_ids=ids,
        copied_runtime_only=True,copied_runtime_cli=True,fictional_inputs_only=True,reports_and_static_html_checked=True,
        fixture_binaries_executed=False,scanned_binaries_executed=False,hints_are_dependencies=False,
        loader_compatibility_verified=False)
    unchanged=all(sha((ROOT/name).read_bytes())==digest for name,digest in RUNTIME_SHA256.items())
    assert not list(importlib.metadata.distributions())
    value=dict(schema=1,package=PACKAGE,version=VERSION,status='PASS' if regression['status']==integration['status']=='PASS' and unchanged else 'FAIL',
        platform=sys.platform,python='.'.join(map(str,sys.version_info[:3])),tests=103,
        passed=regression['passed']+integration['passed'],skipped=regression['skipped']+integration['skipped'],
        failures=regression['failures']+integration['failures'],errors=regression['errors']+integration['errors'],
        unexpected_skips=regression['unexpected_skips']+integration['unexpected_skips'],regression=regression,integration=integration,
        fresh_venv=True,extracted_import=True,native_links_required=strict,runtime_unchanged=unchanged,runtime_sha256=RUNTIME_SHA256,
        runtime_dependencies=0,runtime_distributions=0,pip_in_application=False,real_user_binaries_used=False,
        fixture_binaries_executed=False,scanned_binaries_executed=False,inspected_binaries_executed=False,
        python_pin=regression['python_pin'],oracle_evidence=regression['oracle_evidence'])
    report.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    return 0 if value['status']=='PASS' else 1

def qualify(packages,reference,workspace,report,oracle_receipt):
    lock_raw=(ROOT/'ORACLE-LOCK.json').read_bytes();lock=json.loads(lock_raw)
    version='.'.join(map(str,sys.version_info[:3]));minor='.'.join(map(str,sys.version_info[:2]))
    assert version==lock['python_versions'][minor],'LOCKED_PYTHON_PATCH_REQUIRED'
    base=Path(sys._base_executable).resolve();base_sha=sha(base.read_bytes())
    assert oracle_receipt.is_absolute() and oracle_receipt.is_file() and not oracle_receipt.is_symlink()
    oracle=json.loads(oracle_receipt.read_bytes())
    assert oracle['schema']==1 and oracle['status']=='PASS' and oracle['platform']==sys.platform
    assert oracle['oracle_required'] is (sys.platform=='linux')
    assert oracle['oracle_lock_sha256']==sha(lock_raw) and oracle['preparation_helper_sha256']==sha((ROOT/'packaging/prepare_oracle.py').read_bytes())
    for key in ('application_uses_oracle','fixture_binaries_executed','binary_reproducibility_claimed','global_install_performed'):assert oracle[key] is False
    assert set(oracle['tools'])==({'gcc','readelf'} if sys.platform=='linux' else set())
    helper=preparation()
    for name,record in oracle['tools'].items():
        observed,path=helper.describe(name,os.environ['OUTLANDS_ELF_'+name.upper()],lock[name+'_version'])
        assert observed==record
    for path in (workspace,report):
        assert path.is_absolute() and path.parent.is_dir() and not os.path.lexists(path)
        assert not path.resolve().is_relative_to(ROOT.resolve())
    assert packages.is_absolute() and packages.is_dir()
    receipt=json.loads((packages/'build-manifest.json').read_bytes())
    assert receipt['schema']==1 and receipt['package']==PACKAGE and receipt['version']==VERSION
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
        assert len(names)==len(set(names))==receipt['files']==len(manifest['files'])+1==29
        assert len(manifest['files'])==28
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
        temp=Path(tempfile.mkdtemp(prefix='elf-',dir='/tmp'));assert temp.resolve()==temp and not temp.is_symlink()
    env=helper.compiler_environment()
    env.update(TEMP=str(temp),TMP=str(temp),TMPDIR=str(temp),OUTLANDS_TEST_TEMP=str(temp),OUTLANDS_TEST_TEMP_ROOT=str(temp),
        OUTLANDS_TEST_PYTHON_SHA256=base_sha,OUTLANDS_TEST_PYTHON_VERSION=version,
        OUTLANDS_ELF_ORACLE_REPORT=str(oracle_receipt),ELF_REQUIRE_ORACLE='1' if sys.platform=='linux' else '0')
    def command(args,log,timeout=300):
        result=subprocess.run(args,cwd=app,env=env,capture_output=True,timeout=timeout)
        (workspace/log).write_bytes(result.stdout+result.stderr)
        return result
    assert command([sys.executable,'-I','-B',str(app/'source_check.py')],'source-check-private.log').returncode==0
    for name in ('source_check.py','packaging/build.py','packaging/qualify.py','packaging/prepare_oracle.py','tests/original_support.py'):
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
        optimization_refusal=True,source_bytecode_files=0,inherited_pip_and_python_environment_removed=True,compiler_overrides_removed=True,
        fixture_temp_mode='workspace_owned_windows' if os.name=='nt' else 'short_owned_posix',oracle_preparation=oracle)
    report.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(value))
    return done.returncode

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packages',type=Path);parser.add_argument('--reference-build',type=Path)
    parser.add_argument('--oracle-receipt',type=Path);parser.add_argument('--workspace',type=Path)
    parser.add_argument('--report',required=True,type=Path);parser.add_argument('--tests',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.tests:raise SystemExit(run_tests(args.report))
    if any(value is None for value in (args.packages,args.oracle_receipt,args.workspace)):
        parser.error('--packages, --oracle-receipt and --workspace are required')
    raise SystemExit(qualify(args.packages,args.reference_build,args.workspace,args.report,args.oracle_receipt))
