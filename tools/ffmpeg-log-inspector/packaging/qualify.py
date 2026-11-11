"""Qualify fresh extracted source with hash-verified PowerShell and no Python dependencies."""
if not __debug__:
    raise RuntimeError('OPTIMIZED_PYTHON_UNSUPPORTED')

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest
import venv
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def run_tests(report):
    assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_download.py')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    unexpected=[]
    for test,reason in result.skipped:
        allowed=(os.name!='nt' and reason=='Native Windows junction fixture') or (
            os.name=='nt' and os.environ.get('OUTLANDS_REQUIRE_SYMLINK_TEST')!='1' and reason=='Native symlink privilege unavailable')
        if not allowed: unexpected.append(dict(test=test.id(),reason=reason))
    summary=dict(status='PASS' if result.wasSuccessful() and result.testsRun==22 and not unexpected else 'FAIL',
        tests=result.testsRun,passed=result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors),
        skipped=len(result.skipped),failures=len(result.failures),errors=len(result.errors),unexpected_skips=unexpected,
        skips=[dict(test=test.id(),reason=reason) for test,reason in result.skipped],
        failed_tests=[test.id() for test,trace in result.failures+result.errors],
        copied_runtime_only=True,fresh_dependency_free_venv=True,
        native_links_required=os.environ.get('OUTLANDS_REQUIRE_SYMLINK_TEST')=='1')
    report.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
    return 0 if summary['status']=='PASS' else 1

def qualify(packages,runtime,workspace,report):
    assert workspace.is_absolute() and not workspace.exists() and not workspace.is_relative_to(ROOT) and not report.exists()
    receipt=json.loads((packages/'build-manifest.json').read_text())
    assert receipt['package']=='ffmpeg-log-inspector' and receipt['version']=='0.1.0' and receipt['files']==23
    archive=packages/receipt['filename']
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['sha256']
    workspace.mkdir()
    prefix='ffmpeg-log-inspector-0.1.0/'
    with zipfile.ZipFile(archive) as source:
        names=source.namelist();manifest=json.loads(source.read(prefix+'SOURCE-MANIFEST.json'))
        expected={prefix+row['path'] for row in manifest['files']}|{prefix+'SOURCE-MANIFEST.json'}
        assert len(names)==len(set(names))==23 and set(names)==expected
        for name in names:
            assert name.startswith(prefix) and '..' not in name.split('/') and '\\' not in name and ':' not in name
            assert source.getinfo(name).external_attr>>16==0o100644
        for row in manifest['files']:
            data=source.read(prefix+row['path'])
            assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
            assert data==(ROOT/row['path']).read_bytes(),'ARCHIVE_SOURCE_DIFFERS'
        source.extractall(workspace)
    app=workspace/prefix
    selected=json.loads((runtime/'runtime-receipt.json').read_text())
    specs=json.loads((app/'docs/RUNTIMES.json').read_text())['releases']
    assets=[asset for row in specs if row['version']==selected['version'] for asset in row['assets'] if asset['platform']==sys.platform]
    assert len(assets)==1 and selected['status']=='PASS' and selected['platform']==sys.platform
    spec=assets[0];package=runtime/spec['filename']
    assert selected['sha256']==spec['sha256'] and package.stat().st_size==spec['bytes']
    assert hashlib.sha256(package.read_bytes()).hexdigest()==spec['sha256'],'RUNTIME_ARCHIVE_CHANGED'
    pwsh=runtime/'runtime'/('pwsh.exe' if os.name=='nt' else 'pwsh')
    info=json.loads(subprocess.check_output([str(pwsh),'-NoLogo','-NoProfile','-NonInteractive','-Command',
        '[ordered]@{powershell=$PSVersionTable.PSVersion.ToString();edition=$PSVersionTable.PSEdition;dotnet=[Runtime.InteropServices.RuntimeInformation]::FrameworkDescription;architecture=[Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture.ToString()}|ConvertTo-Json -Compress'],text=True,timeout=30))
    assert info['powershell']==selected['version'] and info['edition']=='Core' and info['architecture']=='X64'
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',OUTLANDS_PWSH=str(pwsh),OUTLANDS_TEST_TEMP_ROOT=str(workspace),TEMP=str(workspace),TMP=str(workspace))
    env.pop('PYTHONPATH',None)
    gate=subprocess.run([sys.executable,'-I','-B',str(app/'source_check.py')],cwd=app,env=env,capture_output=True,timeout=30)
    (workspace/'source-check.log').write_bytes(gate.stdout+gate.stderr)
    assert gate.returncode==0,'EXTRACTED_SOURCE_GATE_FAILED'
    result=subprocess.run([str(pwsh),'-NoLogo','-NoProfile','-NonInteractive','-File',str(app/'tests/Run-Tests.ps1'),
        '-WorkRoot',str(workspace/'regression fixtures')],cwd=app,env=env,capture_output=True,timeout=300)
    (workspace/'regression.log').write_bytes(result.stdout+result.stderr)
    counts=re.findall(rb'PASS total=(\d+); all inspected input hashes unchanged;',result.stdout)
    harness_skips=result.stdout.count(b'SKIP symbolic-link fixture: native Windows privilege unavailable.')
    strict=env.get('OUTLANDS_REQUIRE_SYMLINK_TEST')=='1'
    assert harness_skips in (0,1) and (not harness_skips or os.name=='nt') and (not strict or harness_skips==0)
    expected_cases=56-harness_skips
    assert result.returncode==0 and not result.stderr and counts==[str(expected_cases).encode()],'POWERSHELL_REGRESSION_FAILED'
    environment=workspace/'fresh-venv';venv.EnvBuilder(with_pip=False).create(environment)
    python=environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    result=subprocess.run([str(python),'-I','-B','-W','error',str(app/'packaging/qualify.py'),'--tests','--report',str(report)],
                          cwd=app,env=env,capture_output=True,timeout=180)
    (workspace/'copied-runtime.log').write_bytes(result.stdout+result.stderr)
    assert report.exists(),'COPIED_RUNTIME_SUITE_DID_NOT_REPORT'
    integration=json.loads(report.read_text())
    summary=dict(schema=1,status='PASS' if result.returncode==0 and integration['status']=='PASS' else 'FAIL',
        package='ffmpeg-log-inspector',version='0.1.0',source_revision=receipt['source_revision'],zip_sha256=receipt['sha256'],
        platform=sys.platform,python='.'.join(map(str,sys.version_info[:3])),runtime=info,runtime_archive=selected,
        regression_cases=expected_cases,regression_skipped=harness_skips,integration=integration,tests=56+integration['tests'],passed=expected_cases+integration['passed'],
        skipped=harness_skips+integration['skipped'],failures=integration['failures'],errors=integration['errors'],
        unexpected_skips=integration['unexpected_skips'],skips=([dict(test='powershell-harness.linked-input',reason='Native symlink privilege unavailable')] if harness_skips else [])+integration['skips'],
        fresh_extraction=True,source_gate=True,runtime_hash_verified=True,inspection_logic_unchanged=True)
    report.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(summary))
    return 0 if summary['status']=='PASS' else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packages',type=Path);parser.add_argument('--runtime',type=Path)
    parser.add_argument('--workspace',type=Path);parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--tests',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.tests: raise SystemExit(run_tests(args.report))
    if any(p is None for p in (args.packages,args.runtime,args.workspace)):parser.error('--packages, --runtime and --workspace required')
    raise SystemExit(qualify(args.packages,args.runtime,args.workspace,args.report))
