"""Fresh hash-locked installs and real authored-PDF tests from a verified source ZIP."""
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
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]

def run_tests(report, runtime_only=False):
    sys.path.insert(0, str(ROOT))
    import pdf_bounds
    assert Path(pdf_bounds.__file__).resolve() == ROOT / 'pdf_bounds.py'
    assert sys.prefix != sys.base_prefix
    pins = pdf_bounds.dependency_versions()
    if runtime_only:
        try: importlib.metadata.version('pypdf')
        except importlib.metadata.PackageNotFoundError: pass
        else: raise AssertionError('TEST_DEPENDENCY_PRESENT_IN_RUNTIME_ONLY_STAGE')
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='test_download_cli.py' if runtime_only else 'test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    unexpected = [(test,reason) for test,reason in result.skipped if not (
        os.name == 'nt' and reason == 'POSIX FIFO fixture') and not (
        os.name == 'nt' and os.environ.get('OUTLANDS_PDF_REQUIRE_NATIVE_LINKS') != '1' and reason == 'Native symlink privilege unavailable')]
    expected = 5 if runtime_only else 62
    summary = dict(status='PASS' if result.wasSuccessful() and not unexpected and result.testsRun == expected else 'FAIL',
                   python='.'.join(map(str,sys.version_info[:3])), platform=sys.platform,
                   tests=result.testsRun, passed=result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors),
                   skipped=len(result.skipped), failures=len(result.failures), errors=len(result.errors),
                   skips=[dict(test=test.id(),reason=reason) for test,reason in result.skipped],
                   unexpected_skips=[dict(test=test.id(),reason=reason) for test,reason in unexpected],
                   failed_tests=[test.id() for test,trace in result.failures+result.errors],
                   dependencies=pins, test_dependency=None if runtime_only else importlib.metadata.version('pypdf'),
                   fresh_venv=True, extracted_import=True, runtime_only=runtime_only,
                   native_links_required=os.environ.get('OUTLANDS_PDF_REQUIRE_NATIVE_LINKS') == '1')
    report.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return 0 if summary['status']=='PASS' else 1

def qualify(packages, workspace, report):
    assert workspace.is_absolute() and not workspace.exists() and not workspace.is_relative_to(ROOT) and not report.exists()
    receipt=json.loads((packages/'build-manifest.json').read_text())
    assert receipt['package']=='pdf-text-bounds' and receipt['version']=='0.2.0'
    archive=packages/receipt['filename']
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['sha256']
    workspace.mkdir()
    prefix='pdf-text-bounds-0.2.0/'
    with zipfile.ZipFile(archive) as source:
        names=source.namelist()
        manifest=json.loads(source.read(prefix+'SOURCE-MANIFEST.json'))
        expected={prefix+row['path'] for row in manifest['files']} | {prefix+'SOURCE-MANIFEST.json'}
        assert len(names)==len(set(names))==receipt['files'] and set(names)==expected
        for name in names:
            assert name.startswith(prefix) and '..' not in name.split('/') and '\\' not in name and ':' not in name
            assert not (source.getinfo(name).external_attr >> 16) & 0o170000 == 0o120000
        for row in manifest['files']:
            data=source.read(prefix+row['path'])
            assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
            assert data==(ROOT/row['path']).read_bytes(), 'ARCHIVE_SOURCE_DIFFERS'
        source.extractall(workspace)
    app=workspace/prefix
    environment=workspace/'fresh-venv'
    venv.EnvBuilder(with_pip=True).create(environment)
    python=environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',TEMP=str(workspace),TMP=str(workspace))
    env.pop('PYTHONPATH',None)
    def command(args, log):
        with (workspace/log).open('w',encoding='utf-8') as output:
            result=subprocess.run([str(python),'-I','-B']+args,cwd=app,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=300)
        if result.returncode:
            raise RuntimeError('QUALIFICATION_STEP_FAILED: '+log)
    pip=['-m','pip','--disable-pip-version-check']
    command(pip+['install','--require-hashes','--only-binary=:all:','-r','requirements.lock.txt','--report',str(workspace/'runtime-install.json')], 'runtime-install.log')
    command(pip+['check'], 'runtime-pip-check.log')
    runtime=workspace/'runtime.json'
    command(['-W','error',str(app/'packaging/qualify.py'),'--tests','--runtime-only','--report',str(runtime)],'runtime-cli.log')
    assert json.loads(runtime.read_text())['status']=='PASS'
    # Deliberately wrong wheel digest, dry run in a separate path: must fail and never modify the venv.
    bad=workspace/'bad-hash.txt'
    bad.write_text('pypdf==7.0.1 --hash=sha256:'+'0'*64+'\n',encoding='ascii')
    result=subprocess.run([str(python),'-I','-B']+pip+['install','--dry-run','--ignore-installed','--no-deps','--no-cache-dir',
        '--require-hashes','--only-binary=:all:','-r',str(bad)],cwd=app,env=env,capture_output=True,timeout=120)
    (workspace/'bad-hash.log').write_bytes(result.stdout+result.stderr)
    assert result.returncode != 0 and b'Expected sha256' in result.stderr and b'Got' in result.stderr, 'HASH_REFUSAL_MISSING'
    command(pip+['install','--require-hashes','--only-binary=:all:','-r','requirements-dev.lock.txt','--report',str(workspace/'dev-install.json')], 'dev-install.log')
    command(pip+['check'], 'dev-pip-check.log')
    command([str(app/'source_check.py')], 'source-check.log')
    command([str(app/'check_advisories.py')], 'advisories.log')
    command(['-W','error',str(app/'packaging/qualify.py'),'--tests','--report',str(report)],'full-tests.log')
    summary=json.loads(report.read_text())
    installed_wheels=[]
    provenance=json.loads((app/'docs/WHEELS.json').read_text())['packages']
    approved={entry['filename']:entry['sha256'] for package in provenance for entry in package['files']}
    for row in json.loads((workspace/'runtime-install.json').read_text())['install'] + json.loads((workspace/'dev-install.json').read_text())['install']:
        assert row['download_info']['url'].split('?')[0].endswith('.whl')
        filename=unquote(urlparse(row['download_info']['url']).path.rsplit('/',1)[-1])
        digest=row['download_info']['archive_info']['hashes']['sha256']
        assert approved[filename]==digest, 'INSTALLED_WHEEL_NOT_REVIEWED'
        installed_wheels.append(dict(name=row['metadata']['name'],version=row['metadata']['version'],filename=filename,sha256=digest))
    assert len(installed_wheels)==9
    summary.update(source_revision=receipt['source_revision'],zip_sha256=receipt['sha256'],version='0.2.0',
                   hash_refusal=True, binary_only=True, runtime_cli=json.loads(runtime.read_text()),
                   source_gate=True, advisory_check=True,installed_wheels=installed_wheels)
    report.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary))
    return 0 if summary['status']=='PASS' else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packages',type=Path); parser.add_argument('--workspace',type=Path)
    parser.add_argument('--report',required=True,type=Path)
    parser.add_argument('--tests',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--runtime-only',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.tests: raise SystemExit(run_tests(args.report,args.runtime_only))
    if args.packages is None or args.workspace is None: parser.error('--packages and --workspace required')
    raise SystemExit(qualify(args.packages,args.workspace,args.report))
