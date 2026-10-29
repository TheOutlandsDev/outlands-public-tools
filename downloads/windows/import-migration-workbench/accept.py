"""Fresh Windows download qualification; only synthetic summaries/captures are public."""
from contextlib import closing
from decimal import Decimal
import sqlite3
import argparse
from contextlib import contextmanager
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit
import zipfile
from build import FILENAME,PREFIX,sha,encoded,members


def tree(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}


def accept(packages,workspace,browser=False):
    if os.name!='nt' or not workspace.is_absolute() or workspace.exists() or not workspace.parent.is_dir():raise ValueError('NEW_WINDOWS_WORKSPACE_REQUIRED')
    if browser and os.environ.get('GITHUB_ACTIONS')!='true':raise ValueError('HOSTED_BROWSER_QUALIFICATION_ONLY')
    receipt=json.loads((packages/'release-receipt.json').read_bytes());raw=(packages/FILENAME).read_bytes()
    assert sha(raw)==receipt['sha256'];contents=members(raw)
    manifest=json.loads(contents[PREFIX+'PACKAGE-MANIFEST.json'])
    assert len(contents)==receipt['files'] and set(contents)=={PREFIX+r['path'] for r in manifest['files']}|{PREFIX+'PACKAGE-MANIFEST.json'}
    for row in manifest['files']:
        b=contents[PREFIX+row['path']];assert row==dict(path=row['path'],bytes=len(b),sha256=sha(b))
    workspace.mkdir()
    with zipfile.ZipFile(packages/FILENAME) as z:z.extractall(workspace/'fresh extracted folder')
    root=workspace/'fresh extracted folder'/PREFIX.rstrip('/');app=root/'application';private=workspace/'private';private.mkdir();temporary=private/'temp';temporary.mkdir()
    before=tree(root);pwsh=shutil.which('pwsh');assert pwsh
    env={**os.environ,'PATH':os.pathsep.join([str(Path(os.environ['SystemRoot'])/'System32'),str(Path(pwsh).parent)]),
         'TEMP':str(temporary),'TMP':str(temporary),'TMPDIR':str(temporary),'OUTLANDS_TEST_TEMP':str(temporary),
         'PYTHONDONTWRITEBYTECODE':'1','WORKBENCH_REQUIRE_LINKS':'1',
         'PYTHONHOME':str(private/'invalid python home'),'PYTHONPATH':str(private/'invalid python path')}
    python=str(root/'runtime/python.exe');checks=[]
    def command(args,exercise=False):
        line=subprocess.list2cmdline([str(root/('Import Exercise.cmd' if exercise else 'Import Demo.cmd')),*map(str,args)])
        return '"'+os.environ['COMSPEC']+'" /d /s /c "'+line+'"'
    def cli(args,exercise=False,expected=0):
        p=subprocess.run(command(args,exercise),cwd=private,env=env,capture_output=True,timeout=90)
        (private/'last-cli.log').write_bytes(p.stdout+p.stderr)
        assert p.returncode==expected,'CMD check failed; private log retained.'
        return p.stdout
    health=json.loads(cli(['--check']));assert health['runtime']=='3.14.10' and health['isolated'] and health['bundled_runtime']
    assert tree(root)==before;checks.append('cmd_uses_isolated_bundled_runtime_without_system_python_or_state')
    p=subprocess.run([python,'-I','-B',str(app/'release_source.py'),'check'],cwd=app,env=env,capture_output=True,timeout=30)
    assert p.returncode==0 and json.loads(p.stdout)['status']=='SOURCE_MATCH';checks.append('original_source_inventory_preserved')
    p=subprocess.run([python,'-I','-B','-W','error',str(app/'run_checks.py')],cwd=app,env=env,capture_output=True,timeout=240)
    (private/'core-tests.log').write_bytes(p.stdout+p.stderr)
    assert p.returncode==0,'Bundled core checks failed; private log retained.'
    log=p.stderr.decode('utf-8');assert re.search(r'Ran 70 tests?',log) and 'skipped=1' in log
    checks.append('all_70_original_core_checks_on_bundled_python_seven_native_fixtures_one_opposite_platform_skip')
    exercise_workspace=private/'new import exercise'
    outcome=json.loads(cli(['--workspace',exercise_workspace],True).decode('utf-8').splitlines()[0])
    assert outcome['status']=='PASS' and outcome['command_checks']==15
    assert [outcome[k] for k in ('input_rows','accepted_records','duplicate_rows','rejected_rows','provenance_rows')]==[7,3,2,2,5]
    assert outcome['repeat_refused'] and outcome['conflict_refused'] and outcome['existing_store_unchanged']
    checks.append('cmd_exercise_runs_15_original_cli_commands_and_independent_sqlite_oracles')
    preserved=tree(exercise_workspace);cli(['--workspace',exercise_workspace],True,2)
    assert tree(exercise_workspace)==preserved;checks.append('existing_exercise_refused_without_writes')
    overview=json.loads(cli(['--workspace',exercise_workspace,'--cli','overview']))
    assert len(overview['plans'])==2 and len(overview['imports'])==1 and overview['unfinished_jobs']==0
    checks.append('original_cli_reopens_registered_previews_and_import')
    gui_workspace=private/'browser import practice'
    @contextmanager
    def server():
        p=subprocess.Popen(command(['--workspace',gui_workspace,'--no-browser']),cwd=private,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        lines=queue.Queue();log=(private/'last-server.log').open('w',encoding='utf-8')
        def read():
            for line in p.stdout:log.write(line);log.flush();lines.put(line)
            lines.put(None)
        worker=threading.Thread(target=read,daemon=True);worker.start();value={}
        def http(path,body=None):
            parts=urlsplit(value['url']);conn=HTTPConnection(parts.hostname,parts.port,timeout=10)
            try:
                conn.request('GET' if body is None else 'POST',path,body=None if body is None else json.dumps(body),headers={'X-Outlands-Token':value.get('token',''),'Content-Type':'application/json'});res=conn.getresponse();raw=res.read();assert res.status==200;return raw
            finally:conn.close()
        value['http']=http
        try:
            while True:
                line=lines.get(timeout=30)
                if line is None:raise AssertionError('Server stopped before ready; private log retained.')
                if line.startswith('Open http://127.0.0.1:'):value['url']=line.strip().removeprefix('Open ');break
            html=http('/').decode('utf-8');value['token']=re.search(r"const token='([^']+)'",html).group(1)
            yield value
        finally:
            try:
                if p.poll() is None and value.get('token') and not value.get('shutdown_requested'):http('/api/shutdown',{})
                if p.poll() is None:assert p.wait(timeout=10)==0
            finally:
                if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=10)
                worker.join(timeout=5);p.stdout.close();log.close()
    captures={};browser_import={}
    if browser:
        from playwright.sync_api import sync_playwright,expect
        expect.set_options(timeout=15000)
        with sync_playwright() as pw,pw.chromium.launch(headless=True) as chromium:
            context=chromium.new_context(viewport={'width':1280,'height':1024});page=context.new_page();requests=[]
            page.on('request',lambda request:requests.append(request.url))
            def capture(name):
                page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(packages/name),type='jpeg',quality=88,full_page=True)
                captures[name]=dict(bytes=(packages/name).stat().st_size,sha256=sha((packages/name).read_bytes()),scope='Actual Windows Chromium, bundled Python runtime, invented rows and contracts; no address bar, absolute paths or session tokens')
            def state(s):return json.loads(s['http']('/api/overview'))
            def approve(rejections=True):
                for name in ('quality','privacy','rights','context'):page.locator('#'+name).check()
                if rejections:page.locator('#accept-rejections').check()
            def reload():
                page.locator('#refresh').click();expect(page.locator('#status')).to_contain_text('Journal reloaded')
            def inspect():
                page.locator('#inspect-plan').click();expect(page.locator('#status')).to_contain_text('Saved preview and byte pin verified')
            def database_oracle(path):
                with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as con:
                    con.execute('PRAGMA query_only=ON')
                    assert con.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
                    assert con.execute('PRAGMA foreign_key_check').fetchall()==[]
                    assert [con.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ('records','provenance','rejected')]==[3,5,2]
                    rows=[json.loads(row[0]) for row in con.execute('SELECT data_json FROM records ORDER BY record_id')]
                assert len(rows)==3
                expected=[('sample-a',3,'12.50',True,'alpha'),('sample-b',7,'2.00',False,'=SUM(1)'),('sample-c',0,'0',True,None)]
                for row,(key,quantity,amount,active,note) in zip(rows,expected):
                    assert row['id']==key and type(row['quantity']) is int and row['quantity']==quantity and Decimal(row['amount'])==Decimal(amount) and row['active'] is active and row['note']==note
                return rows
            with server() as s:
                page.goto(s['url']);expect(page.locator('#status')).to_contain_text('Private instance ready')
                selected=['orders.csv','supplement.jsonl','conflicts.jsonl','contract.json']
                inputs={n:sha((gui_workspace/'inbox'/n).read_bytes()) for n in selected}
                page.locator('#preview').click();expect(page.locator('#status')).to_contain_text('Pinned preview saved')
                expect(page.locator('#preview-summary')).to_have_text('7 input rows · 3 accepted · 2 duplicate extras · 2 rejected · 0 conflicting rows')
                preview=json.loads(page.locator('#plan-details').inner_text())['plan']
                assert len(preview['records'])==3 and sum(len(row['provenance']) for row in preview['records'])==5
                first_plan=state(s)['plans'][0];capture('import-preview.jpg')
                checks.append('actual_browser_preview_matches_seven_rows_three_records_and_five_provenance_entries')
                approve(False);page.locator('#import').click();expect(page.locator('#status')).to_have_text('REJECTED_ROWS_REVIEW_REQUIRED')
                assert state(s)['imports']==[] and not list((gui_workspace/'stores').iterdir())
                capture('import-rejection-refused.jpg');checks.append('actual_browser_missing_rejection_acceptance_refused_before_store_creation')
                reload();inspect();approve();page.locator('#import').click();expect(page.locator('#status')).to_contain_text('Fresh SQLite store committed')
                imported=state(s)['imports'][0];store=gui_workspace/imported['target'];db=store/'data.sqlite3'
                rows=database_oracle(db);preserved_store=tree(store)
                assert sha(db.read_bytes())==imported['database_sha256']
                page.locator('#inspect-import').click();expect(page.locator('#status')).to_contain_text('Registered store schema, bytes, normalized values and provenance verified')
                verified=json.loads(page.locator('#records').inner_text());assert verified['records']==rows
                capture('import-verified.jpg');checks.append('actual_browser_reviewed_fresh_store_and_independent_sqlite_readback_match')
                inspect();approve();page.locator('#import').click();expect(page.locator('#status')).to_have_text('EXACT_PLAN_ALREADY_IMPORTED')
                assert len(state(s)['imports'])==1 and tree(store)==preserved_store
                checks.append('actual_browser_exact_repeat_refused_without_changing_existing_store')
                reload();sources=json.loads(page.locator('#sources').input_value());sources[1]['path']='inbox/conflicts.jsonl'
                page.locator('#sources').fill(json.dumps(sources));page.locator('#preview').click();expect(page.locator('#status')).to_contain_text('Pinned preview saved')
                expect(page.locator('#preview-summary')).to_contain_text('3 conflicting rows');approve();page.locator('#import').click()
                expect(page.locator('#status')).to_have_text('CONFLICTING_KEYS_REQUIRE_NEW_PLAN')
                assert len(state(s)['imports'])==1 and tree(store)==preserved_store
                capture('import-conflict-refused.jpg');checks.append('actual_browser_three_row_key_conflict_refused_preserving_source_and_store')
                reload();page.locator('#plans').select_option(first_plan['plan_id']);inspect();approve();page.locator('#export').click()
                expect(page.locator('#status')).to_contain_text('Reviewed private handoff created')
                report=json.loads(page.locator('#handoff').inner_text());assert report['manifest']['public_release_authorized'] is False and len(report['manifest']['files'])==7
                assert all(sha((gui_workspace/'inbox'/n).read_bytes())==pin for n,pin in inputs.items()) and tree(store)==preserved_store
                checks.append('actual_browser_reviewed_handoff_stays_private_and_input_bytes_unchanged')
                page.set_viewport_size(dict(width=390,height=844));page.locator('#actor').focus();page.keyboard.press('Tab');expect(page.locator('#reason')).to_be_focused()
                assert page.evaluate('document.documentElement.scrollWidth')<=390;checks.append('narrow_layout_and_keyboard_navigation')
                browser_import=dict(input_rows=7,records=3,provenance_rows=5,rejected_rows=2,quantities=[3,7,0],
                    database_sha256=imported['database_sha256'],missing_rejection_acceptance_refused=True,repeat_refused=True,conflict_refused=True,input_bytes_unchanged=True,existing_store_unchanged=True)
                page.locator('#shutdown').click();s['shutdown_requested']=True;expect(page.locator('#status')).to_contain_text('Local server stopping')
            with server() as s:
                reopened=state(s);assert len(reopened['plans'])==2 and len(reopened['imports'])==1
                page.goto(s['url']);expect(page.locator('#plan-count')).to_have_text('2');expect(page.locator('#import-count')).to_have_text('1')
                page.locator('#imports').select_option(imported['import_id']);page.locator('#inspect-import').click()
                expect(page.locator('#status')).to_contain_text('Registered store schema, bytes, normalized values and provenance verified')
                assert json.loads(page.locator('#records').inner_text())['records']==rows and tree(store)==preserved_store
                page.locator('#shutdown').click();s['shutdown_requested']=True
            context.close();assert all(url.startswith('http://127.0.0.1:') for url in requests)
        checks.append('saved_instance_reopened_without_reseed_and_owned_servers_stopped')
    assert tree(root)==before;checks.append('no_package_writes_or_shipped_private_state')
    result=dict(schema=1,status='PASS',browser=browser,package_sha256=receipt['sha256'],packaging_source=receipt['packaging_source'],app_source=receipt['app_source'],runtime='3.14.10',core_tests=70,core_skips=1,checks=checks,exercise=outcome,browser_import=browser_import,captures=captures,scope='Fictional Windows CMD/browser/fresh SQLite qualification; not manual separate-PC or production acceptance')
    if browser:(packages/'acceptance.json').write_bytes(encoded(result))
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
