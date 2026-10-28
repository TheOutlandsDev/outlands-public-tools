"""Verify each fresh ZIP, then exercise fictional CLI workflows and optional UI tests."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from packages import build as toolkit


def sha(raw):return hashlib.sha256(raw).hexdigest()


def execute(app, args, private, label, expected=0):
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',OUTLANDS_TEST_TEMP=str(private))
    result=subprocess.run([sys.executable,'-B','-W','error',*map(str,args)],cwd=app,env=env,capture_output=True,timeout=240)
    # Logs may contain disposable paths/IDs. They stay in this private new workspace.
    (private/(label+'.stdout')).write_bytes(result.stdout);(private/(label+'.stderr')).write_bytes(result.stderr)
    if result.returncode!=expected:raise ValueError('EXTRACTED_CHECK_FAILED_'+label)
    return result


def snapshot(directory):
    return {p.relative_to(directory).as_posix():sha(p.read_bytes()) for p in directory.rglob('*') if p.is_file()}


def accept(packages,workspace,browser=False):
    if not workspace.is_absolute() or workspace.exists() or workspace.is_relative_to(ROOT):raise ValueError('NEW_EXTERNAL_PRIVATE_WORKSPACE_REQUIRED')
    matrix=json.loads((packages/'release-matrix.json').read_bytes())
    if {a['app'] for a in matrix['applications']}!={'sql-report-workbench','developer-workspace'}:raise ValueError('EXACT_APPLICATION_SET_REQUIRED')
    workspace.mkdir();receipts=[]
    for item in matrix['applications']:
        data=(packages/item['filename']).read_bytes()
        if len(data)!=item['bytes'] or sha(data)!=item['sha256']:raise ValueError('PACKAGE_HASH_MISMATCH')
        manifest=toolkit.verify_archive(data)
        if manifest['source_revision']!=item['source_revision'] or manifest['packaging_revision']!=item['packaging_revision']:raise ValueError('REVISION_MISMATCH')
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if any((n.external_attr>>16)&0o170000!=0o100000 for n in archive.infolist()):raise ValueError('ORDINARY_MEMBERS_REQUIRED')
            archive.extractall(workspace)
        package=workspace/(item['app']+'-'+item['version']);app=package/'application'
        private=workspace/(item['app']+' private checks');private.mkdir()
        execute(app,['release_source.py','check'],private,'source')
        core=execute(app,['run_checks.py'],private,'core');log=core.stderr.decode('utf-8')
        total=int(re.search(r'Ran (\d+) tests?',log).group(1));skip=re.search(r'skipped=(\d+)',log)
        checks=['zip_and_every_source_member_verified','original_application_manifest_matches','core_suite_passed']
        instance=private/'fictional instance'
        result=json.loads(execute(app,['workbench.py','--workspace',instance,'demo'],private,'demo').stdout)
        if item['app']=='sql-report-workbench':
            assert result==dict(mode='FICTIONAL_SQL_REPORT_DEMO',groups=[['alpha',8],['beta',11]],filtered_groups=[['alpha',5],['beta',11]],query_versions=2,revision_groups=[['alpha',9],['beta',12]],report_valid=True,report_datasets=1,artifacts=4,comparison_rows_equal=False,private_export_files=7,backup_validated=True,external_connections_used=False,report_rendered=False)
            fixture=json.loads((app/'examples/sample-dataset.json').read_bytes());tables={t['name']:t for t in fixture['tables']}
            groups={r[0]:r[1] for r in tables['groups']['rows']};sums={}
            for row in tables['items']['rows']:sums[groups[row[1]]]=sums.get(groups[row[1]],0)+row[2]
            assert sorted(map(list,sums.items()))==result['groups']
            for export in (instance/'reports').iterdir():
                record=json.loads((export/'manifest.json').read_bytes());assert record['public_release_authorized'] is False
                for name,row in record['files'].items():raw=(export/name).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
                expected=json.loads((export/'result.json').read_bytes());actual=list(csv.reader(io.StringIO((export/'preview.csv').read_text(encoding='utf-8'))));assert actual[1:]==[[str(v) for v in r] for r in expected['rows']]
            reopened=json.loads(execute(app,['workbench.py','--workspace',instance,'datasets'],private,'reopen').stdout)
            assert len(reopened['datasets'])==1
            checks+=['independent_python_aggregates_match','report_validation_and_parameterized_revision_results_match','all_export_members_and_csv_json_agree']
        else:
            assert result==dict(mode='FICTIONAL_DEVELOPER_WORKSPACE_DEMO',projects=1,files=5,versions=2,checked=4,unchecked=1,changed_files=1,validation_artifacts=2,new_review_pending=True,private_export_members=9,export_version=1,backup_validated=True,project_code_executed=False,external_services_used=False)
            original=json.loads((app/'examples/sample-project.json').read_bytes())
            for export in (instance/'reports').iterdir():
                receipt=json.loads((export/'receipt.json').read_bytes());raw=(export/'project-source.zip').read_bytes();assert len(raw)==receipt['bytes'] and sha(raw)==receipt['sha256']
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    record=json.loads(archive.read('manifest.json'));assert record['project_version']==1 and record['code_executed'] is False and record['public_release_authorized'] is False
                    assert set(archive.namelist())==set(record['files'])|{'manifest.json'}
                    for name,row in record['files'].items():b=archive.read(name);assert len(b)==row['bytes'] and sha(b)==row['sha256']
                    for file in original['files']:assert archive.read('source/'+file['path'])==file['content'].encode()
            reopened=json.loads(execute(app,['workbench.py','--workspace',instance,'projects'],private,'reopen').stdout)
            assert len(reopened['projects'])==1
            checks+=['two_revisions_and_distinct_review_states_match','unchecked_file_remains_explicit','historical_export_preserves_all_original_source_bytes']
        checks.append('persistent_instance_reopened_in_new_cli_process')
        before=snapshot(instance)
        execute(app,['workbench.py','--workspace',instance,'demo'],private,'existing-refused',expected=2)
        assert snapshot(instance)==before;checks.append('existing_instance_refused_without_byte_changes')
        if browser:
            ui=execute(app,['run_browser_checks.py'],private,'browser');count=int(re.search(rb'Ran (\d+) tests?',ui.stderr).group(1))
            if b'skipped=' in ui.stderr:raise ValueError('BROWSER_SKIP_REFUSED')
            checks.append('fresh_zip_real_browser_suite_passed')
        else:count=None
        receipts.append(dict(app=item['app'],package_version=item['version'],application_version=item['application_version'],source_revision=item['source_revision'],zip_sha256=item['sha256'],synthetic_only=True,core_tests=total,core_skips=int(skip.group(1)) if skip else 0,browser_tests=count,browser_scope='executed' if browser else 'not run in this acceptance',demo=result,checks=checks))
    public=dict(schema=1,status='PASS',applications=receipts)
    (workspace/'acceptance.json').write_bytes(toolkit.encode(public));print(json.dumps(public))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args()
    try:accept(a.packages,a.workspace,a.browser)
    except Exception as error:
        print('Acceptance refused: '+str(error)+'; private new diagnostics retained.',file=sys.stderr);raise SystemExit(1)
