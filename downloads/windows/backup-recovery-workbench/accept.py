"""Fresh Windows download qualification; only synthetic summaries/captures are public."""
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
        line=subprocess.list2cmdline([str(root/('Recovery Exercise.cmd' if exercise else 'Recovery Demo.cmd')),*map(str,args)])
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
    log=p.stderr.decode('utf-8');assert re.search(r'Ran 61 tests?',log) and 'skipped=1' in log
    checks.append('all_61_original_core_checks_on_bundled_python_six_native_fixtures_one_opposite_platform_skip')
    exercise_workspace=private/'new recovery exercise'
    outcome=json.loads(cli(['--workspace',exercise_workspace],True).decode('utf-8').splitlines()[0])
    assert outcome['status']=='PASS' and outcome['files']==3 and outcome['bytes']==39
    assert outcome['original_csv_count']==3 and outcome['changed_source_csv_count']==9 and outcome['restored_csv_count']==3
    assert outcome['damaged_copy_error']=='SNAPSHOT_CONTENT_MISMATCH' and not outcome['damaged_copy_restore_created']
    checks.append('cmd_exercise_restores_original_bytes_preserves_changed_source_and_refuses_damaged_copy')
    preserved=tree(exercise_workspace);cli(['--workspace',exercise_workspace],True,2)
    assert tree(exercise_workspace)==preserved;checks.append('existing_exercise_refused_without_state_changes')
    overview=json.loads(cli(['--workspace',exercise_workspace,'--cli','overview']))
    assert len(overview['snapshots'])==1 and sum(x['status']=='failed' for x in overview['jobs'])==1
    checks.append('original_cli_reopens_exercise_and_retains_failed_job')
    gui_workspace=private/'browser recovery practice'
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
                if p.poll() is None and value.get('token'):http('/api/shutdown',{})
                if p.poll() is None:assert p.wait(timeout=10)==0
            finally:
                if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=10)
                worker.join(timeout=5);p.stdout.close();log.close()
    captures={}
    if browser:
        from playwright.sync_api import sync_playwright,expect
        expect.set_options(timeout=15000)
        with sync_playwright() as pw,pw.chromium.launch(headless=True) as chromium:
            context=chromium.new_context(viewport={'width':1280,'height':1024});page=context.new_page();requests=[]
            page.on('request',lambda request:requests.append(request.url))
            def capture(name):
                page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(packages/name),type='jpeg',quality=88,full_page=True)
                captures[name]=dict(bytes=(packages/name).stat().st_size,sha256=sha((packages/name).read_bytes()),scope='Actual Windows Chromium; invented fixtures only; no address bar, local paths or tokens')
            with server() as s:
                page.goto(s['url']);expect(page.locator('#status')).to_contain_text('Private instance ready')
                page.locator('#quiescent').check();page.locator('#snapshot').click();expect(page.locator('#status')).to_contain_text('Full snapshot committed')
                state=json.loads(s['http']('/api/overview'));snap=state['snapshots'][0];identifier=snap['snapshot_id'];assert snap['result']['file_count']==3 and snap['result']['total_bytes']==39
                source=gui_workspace/'inbox/sample-files-v1/data/sample.csv';assert source.read_bytes()==b'item,count\nsample,3\n'
                snapshot=gui_workspace/'snapshots'/identifier;backup_before=tree(snapshot)
                page.locator('#manifest').click();expect(page.locator('#snapshot-details')).to_contain_text('"payload_reverified": false');capture('recovery-snapshot.jpg')
                source.write_bytes(b'item,count\nsample,9\n')
                page.locator('#restore').click();expect(page.locator('#status')).to_contain_text('Restore drill verified')
                state=json.loads(s['http']('/api/overview'));restore=gui_workspace/state['jobs'][-1]['result']['target']/'files'
                assert (restore/'data/sample.csv').read_bytes()==b'item,count\nsample,3\n' and tree(restore)==tree(snapshot/'files')
                assert source.read_bytes()==b'item,count\nsample,9\n' and tree(snapshot)==backup_before
                capture('recovery-restored.jpg');checks.append('browser_restores_original_count_3_to_fresh_tree_after_source_changes_to_9')
                damaged=gui_workspace/'inbox/damaged-snapshot';shutil.copytree(snapshot,damaged);(damaged/'files/empty.txt').write_bytes(b'fictional damage')
                previous=tree(gui_workspace/'restores');page.locator('#import-source').fill('inbox/damaged-snapshot');page.locator('#import-pin').fill(snap['result']['manifest_sha256']);page.locator('#restore-imported').click()
                expect(page.locator('#status')).to_have_text('SNAPSHOT_CONTENT_MISMATCH')
                assert tree(gui_workspace/'restores')==previous and tree(snapshot)==backup_before and source.read_bytes()==b'item,count\nsample,9\n'
                page.locator('#refresh').click();expect(page.locator('#failed-count')).to_have_text('1');expect(page.locator('#jobs')).to_contain_text('SNAPSHOT_CONTENT_MISMATCH');capture('recovery-refused.jpg')
                checks.append('browser_refuses_damaged_copy_without_new_restore_and_retains_failed_job')
                page.set_viewport_size(dict(width=390,height=844));page.locator('#source').focus();page.keyboard.press('ControlOrMeta+A');page.keyboard.insert_text('inbox/sample-files-v2')
                assert page.evaluate('document.documentElement.scrollWidth')<=390;checks.append('narrow_layout_and_keyboard_input')
                page.locator('#shutdown').click();expect(page.locator('#status')).to_contain_text('Local server stopping')
            with server() as s:
                state=json.loads(s['http']('/api/overview'));assert len(state['snapshots'])==1 and len(state['jobs'])==3
                assert source.read_bytes()==b'item,count\nsample,9\n';page.goto(s['url']);expect(page.locator('#snapshot-count')).to_have_text('1');expect(page.locator('#failed-count')).to_have_text('1')
                page.locator('#shutdown').click()
            context.close();assert all(url.startswith('http://127.0.0.1:') for url in requests)
        checks.append('saved_instance_reopened_without_reseed_and_owned_servers_stopped')
    assert tree(root)==before;checks.append('no_package_writes_or_shipped_private_state')
    result=dict(schema=1,status='PASS',browser=browser,package_sha256=receipt['sha256'],packaging_source=receipt['packaging_source'],app_source=receipt['app_source'],runtime='3.14.10',core_tests=61,core_skips=1,checks=checks,exercise=outcome,captures=captures,scope='Fictional primary-byte copy recovery; no production, power-loss, hardware or metadata restoration claim')
    if browser:(packages/'acceptance.json').write_bytes(encoded(result))
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
