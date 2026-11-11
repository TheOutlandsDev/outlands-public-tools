"""Fresh .NET Public API Diff source/SDK builds and real native/copied-application fixtures."""
if not __debug__:
    raise RuntimeError('OPTIMIZED_PYTHON_UNSUPPORTED')

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
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
    link_tests={'test_native_symlink_leaf_input_is_refused','test_native_symlink_input_parent_is_refused','test_native_symlink_output_parent_is_refused','test_native_symlink_leaf_output_preserves_targets'}
    for test,reason in result.skipped:
        name=test.id().rsplit('.',1)[-1]
        allowed=(os.name!='nt' and name=='test_native_windows_junction_input_and_output_parent_are_refused' and reason=='Native Windows junction fixture') or (os.name=='nt' and os.environ.get('OUTLANDS_API_REQUIRE_NATIVE_LINKS')!='1' and name in link_tests and reason=='Native symlink privilege unavailable')
        if not allowed:unexpected.append(dict(test=test.id(),reason=reason))
    strict=os.name!='nt' or os.environ.get('OUTLANDS_API_REQUIRE_NATIVE_LINKS')=='1'
    counts_ok=(len(result.skipped)==(0 if os.name=='nt' else 1)) if strict else len(result.skipped)<=4
    summary=dict(status='PASS' if result.wasSuccessful() and result.testsRun==29 and result.testsRun>len(result.skipped) and counts_ok and not unexpected else 'FAIL',
        tests=result.testsRun,passed=result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors),skipped=len(result.skipped),
        failures=len(result.failures),errors=len(result.errors),unexpected_skips=unexpected,
        skips=[dict(test=test.id(),reason=reason) for test,reason in result.skipped],
        failed_tests=[test.id() for test,trace in result.failures+result.errors],copied_app_only=True,fresh_dependency_free_venv=True,
        native_links_required=os.name!='nt' or os.environ.get('OUTLANDS_API_REQUIRE_NATIVE_LINKS')=='1')
    report.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
    return 0 if summary['status']=='PASS' else 1

def qualify(packages,sdk,framework,workspace,report):
    assert workspace.is_absolute() and not workspace.exists() and not workspace.is_relative_to(ROOT) and not report.exists()
    receipt=json.loads((packages/'build-manifest.json').read_text())
    assert receipt['package']=='dotnet-api-diff' and receipt['version']=='0.1.0' and receipt['files']==32
    archive=packages/receipt['filename'];assert hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['sha256']
    workspace.mkdir();prefix='dotnet-api-diff-0.1.0/'
    with zipfile.ZipFile(archive) as source:
        names=source.namelist();manifest=json.loads(source.read(prefix+'SOURCE-MANIFEST.json'))
        assert len(names)==len(set(names))==32 and len(manifest['files'])==31 and set(names)=={prefix+r['path'] for r in manifest['files']}|{prefix+'SOURCE-MANIFEST.json'}
        for name in names:
            assert name.startswith(prefix) and '..' not in name.split('/') and '\\' not in name and ':' not in name
            assert source.getinfo(name).external_attr>>16==0o100644
        for row in manifest['files']:
            data=source.read(prefix+row['path']);assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
            assert data==(ROOT/row['path']).read_bytes(),'ARCHIVE_SOURCE_DIFFERS'
        source.extractall(workspace)
    app=workspace/prefix
    selected=json.loads((sdk/'sdk-receipt.json').read_text());specs=json.loads((app/'docs/SDKS.json').read_text())['releases']
    entries=[a for r in specs if r['version']==selected['version'] and r['framework']==framework for a in r['assets'] if a['platform']==sys.platform]
    assert len(entries)==1 and selected['status']=='PASS' and selected['platform']==sys.platform and selected['framework']==framework
    entry=entries[0];sdk_archive=sdk/entry['filename']
    assert selected['sha512']==entry['sha512'] and sdk_archive.stat().st_size==selected['bytes']
    assert hashlib.sha512(sdk_archive.read_bytes()).hexdigest()==entry['sha512'],'SDK_ARCHIVE_CHANGED'
    host=sdk/'runtime'/('dotnet.exe' if os.name=='nt' else 'dotnet')
    home=workspace/'home';home.mkdir();temp=workspace/'temp';temp.mkdir()
    env=dict(os.environ,DOTNET_ROOT=str(sdk/'runtime'),DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_CLI_HOME=str(home),
        DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',DOTNET_NOLOGO='1',DOTNET_CLI_UI_LANGUAGE='en-US',
        DOTNET_ADD_GLOBAL_TOOLS_TO_PATH='false',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE='true',DOTNET_CLI_USE_MSBUILD_SERVER='0',MSBUILDDISABLENODEREUSE='1',
        NUGET_PACKAGES=str(workspace/'packages'),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',TEMP=str(temp),TMP=str(temp),OUTLANDS_TEST_TEMP_ROOT=str(temp))
    for key in ('PYTHONPATH','MSBuildSDKsPath','MSBUILD_EXE_PATH','DOTNET_STARTUP_HOOKS','DOTNET_ADDITIONAL_DEPS','DOTNET_ROLL_FORWARD','DOTNET_SHARED_STORE'):
        env.pop(key,None)
    if env.get('OUTLANDS_REQUIRE_SYMLINK_TEST')=='1':env['OUTLANDS_API_REQUIRE_NATIVE_LINKS']='1'
    (workspace/'global.json').write_text(json.dumps({'sdk':{'version':selected['version'],'rollForward':'disable','allowPrerelease':False}}),encoding='utf-8')
    actual=subprocess.check_output([str(host),'--version'],cwd=app,env=env,text=True,timeout=45).strip();assert actual==selected['version']
    runtimes=subprocess.check_output([str(host),'--list-runtimes'],cwd=app,env=env,text=True,timeout=45)
    runtimes=[line.split(' [',1)[0] for line in runtimes.splitlines()]
    def command(args,log,timeout=300):
        result=subprocess.run(args,cwd=app,env=env,capture_output=True,timeout=timeout)
        (workspace/log).write_bytes(result.stdout+result.stderr)
        assert result.returncode==0,'QUALIFICATION_STEP_FAILED: '+log
        return result
    command([sys.executable,'-I','-B',str(app/'source_check.py')],'source-check.log')
    build=workspace/'build'
    props=['-p:TargetFramework='+framework,'-p:UseAppHost=false','-p:UseSharedCompilation=false']
    command([str(host),'restore','tests/ApiDiff.Tests.csproj','--configfile','NuGet.Config','--artifacts-path',str(build),'--nologo']+props,'restore.log')
    compiled=command([str(host),'build','tests/ApiDiff.Tests.csproj','-c','Release','--artifacts-path',str(build),'--no-restore','--nologo','--disable-build-servers']+props,'build.log')
    assert b'0 Warning(s)' in compiled.stdout and b'0 Error(s)' in compiled.stdout,'BUILD_DIAGNOSTICS_NOT_CLEAN'
    assets=list(build.rglob('project.assets.json'));assert len(assets)==4
    for path in assets:
        asset=json.loads(path.read_text())
        assert all(r['type']!='package' for r in asset['libraries'].values()),'UNEXPECTED_PACKAGE_DEPENDENCY'
        assert set(asset['project']['frameworks'])=={framework},'FIXTURE_OR_PROJECT_TARGET_MISMATCH'
    apps=list((build/'bin'/'ApiDiff').rglob('ApiDiff.dll'));harnesses=list((build/'bin').rglob('ApiDiff.Tests.dll'))
    assert len(apps)==len(harnesses)==1
    executable=apps[0];harness=harnesses[0]
    before=list((build/'bin'/'Before').rglob('Example.Plugin.dll'));after=list((build/'bin'/'After').rglob('Example.Plugin.dll'))
    assert len(before)==len(after)==1
    config=json.loads(executable.with_suffix('.runtimeconfig.json').read_text())
    assert config['runtimeOptions']['tfm']==framework and config['runtimeOptions']['framework']['name']=='Microsoft.NETCore.App'
    native=command([str(host),str(harness),str(before[0]),str(after[0])],'native-tests.log',180)
    rows=[]
    for line in native.stdout.splitlines():
        try:value=json.loads(line)
        except (ValueError,UnicodeError):continue
        if isinstance(value,dict) and 'discovered' in value:rows.append(value)
    assert len(rows)==1;native=rows[0]
    assert native['discovered']==58 and native['failed']==0 and native['passed']>0
    strict=os.name!='nt' or env.get('OUTLANDS_API_REQUIRE_NATIVE_LINKS')=='1'
    assert native['nativeLinksRequired']==strict and native['passed']+native['failed']+native['skipped']==58
    required=set() if os.name=='nt' else {('Windows junction input and output parents refused','POSIX_HAS_NO_WINDOWS_JUNCTION')}
    optional={(name,'WINDOWS_NATIVE_LINK_PRIVILEGE_UNAVAILABLE_1314') for name in ('symlink input refused','symlink input parent refused','symlink output parent refused','existing symlink output preserves target','dangling symlink output creates no target')} if os.name=='nt' and not strict else set()
    observed={(r['name'],r['reason']) for r in native['skipReasons']}
    assert native['skipped']==len(native['skipReasons'])==len(observed) and required<=observed<=required|optional,'UNEXPECTED_NATIVE_SKIP'
    if strict:assert (native['passed'],native['skipped'])==((58,0) if os.name=='nt' else (57,1))
    environment=workspace/'fresh-venv';venv.EnvBuilder(with_pip=False).create(environment)
    python=environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    env.update(OUTLANDS_DOTNET=str(host),OUTLANDS_API_APP_DIR=str(executable.parent),OUTLANDS_API_BEFORE=str(before[0]),OUTLANDS_API_AFTER=str(after[0]))
    command([str(python),'-I','-B','-W','error',str(app/'packaging/qualify.py'),'--tests','--report',str(report)],'copied-cli.log',180)
    integration=json.loads(report.read_text());assert integration['status']=='PASS'
    result=dict(schema=1,status='PASS',package='dotnet-api-diff',version='0.1.0',source_revision=receipt['source_revision'],zip_sha256=receipt['sha256'],
        platform=sys.platform,python='.'.join(map(str,sys.version_info[:3])),framework=framework,sdk=actual,runtimes=runtimes,sdk_archive=selected,
        native=native,integration=integration,tests=native['discovered']+integration['tests'],passed=native['passed']+integration['passed'],
        skipped=native['skipped']+integration['skipped'],failures=native['failed']+integration['failures'],errors=integration['errors'],unexpected_skips=[],
        fresh_extraction=True,source_gate=True,sdk_hash_verified=True,package_dependencies=0,build_warnings=0,build_errors=0,all_project_targets_verified=True,
        fixtures=[dict(role=role,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for role,p in (('before',before[0]),('after',after[0]))],
        app_files=[dict(path=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (executable,executable.with_suffix('.deps.json'),executable.with_suffix('.runtimeconfig.json'))])
    report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(result));return 0

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packages',type=Path);p.add_argument('--sdk',type=Path)
    p.add_argument('--framework',choices=('net10.0','net11.0'));p.add_argument('--workspace',type=Path);p.add_argument('--report',type=Path,required=True)
    p.add_argument('--tests',action='store_true',help=argparse.SUPPRESS);a=p.parse_args()
    if a.tests:raise SystemExit(run_tests(a.report))
    if any(x is None for x in (a.packages,a.sdk,a.framework,a.workspace)):p.error('--packages --sdk --framework --workspace required')
    raise SystemExit(qualify(a.packages,a.sdk,a.framework,a.workspace,a.report))
