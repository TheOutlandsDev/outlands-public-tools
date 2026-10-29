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
        line=subprocess.list2cmdline([str(root/('Document Exercise.cmd' if exercise else 'Document Demo.cmd')),*map(str,args)])
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
    log=p.stderr.decode('utf-8');assert re.search(r'Ran 71 tests?',log) and 'skipped=1' in log
    checks.append('all_71_original_core_checks_on_bundled_python_seven_native_fixtures_one_opposite_platform_skip')
    exercise_workspace=private/'new document exercise'
    outcome=json.loads(cli(['--workspace',exercise_workspace],True).decode('utf-8').splitlines()[0])
    assert outcome['status']=='PASS' and outcome['command_checks']==18
    assert [outcome[k] for k in ('templates','previews','documents','total_quantity','docx_parts')]==[2,2,2,7,8]
    assert outcome['unreviewed_build_refused'] and outcome['original_document_unchanged']
    checks.append('cmd_exercise_runs_18_original_cli_checks_and_independent_docx_oracles')
    preserved=tree(exercise_workspace);cli(['--workspace',exercise_workspace],True,2)
    assert tree(exercise_workspace)==preserved;checks.append('existing_exercise_refused_without_writes')
    overview=json.loads(cli(['--workspace',exercise_workspace,'--cli','overview']))
    assert [len(overview[k]) for k in ('templates','previews','builds')]==[2,2,2] and overview['unfinished_jobs']==0
    checks.append('original_cli_reopens_both_template_preview_and_document_revisions')
    gui_workspace=private/'browser document practice'
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
    captures={}
    browser_documents={}
    if browser:
        from playwright.sync_api import sync_playwright,expect
        from document_demo import inspect_doc
        expect.set_options(timeout=15000)
        with sync_playwright() as pw,pw.chromium.launch(headless=True) as chromium:
            context=chromium.new_context(viewport={'width':1280,'height':1024},accept_downloads=True);page=context.new_page();requests=[]
            page.on('request',lambda request:requests.append(request.url))
            def capture(name):
                page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(packages/name),type='jpeg',quality=88,full_page=True)
                captures[name]=dict(bytes=(packages/name).stat().st_size,sha256=sha((packages/name).read_bytes()),scope='Actual Windows Chromium, bundled Python runtime, invented templates and values; no address bar, local absolute paths or session tokens')
            def state(s):return json.loads(s['http']('/api/overview'))
            def approve():
                for name in ('quality','privacy','rights','context'):page.locator('#'+name).check()
            def download(pin,label):
                with page.expect_download() as received:page.locator('#download').click()
                selected=received.value;assert selected.suggested_filename=='generated-document.docx'
                data=Path(selected.path()).read_bytes();assert sha(data)==pin
                (private/(label+'.docx')).write_bytes(data)
                return data
            with server() as s:
                page.goto(s['url']);expect(page.locator('#status')).to_contain_text('Private instance ready')
                page.locator('#save-template').click();expect(page.locator('#status')).to_have_text('New template revision saved. Earlier revisions remain unchanged.')
                page.get_by_label('Review notes',exact=True).uncheck();page.locator('#preview').click()
                expect(page.locator('#preview-summary')).to_contain_text('2 sections');expect(page.locator('#semantic')).to_contain_text('Total quantity 7')
                page.locator('#build').click();expect(page.locator('#status')).to_have_text('REVIEW_REQUIRED')
                assert state(s)['builds']==[];capture('document-review-refused.jpg')
                checks.append('actual_browser_unreviewed_build_refused_before_document_creation')
                page.locator('#refresh').click();expect(page.locator('#status')).to_contain_text('Journal reloaded')
                page.locator('#inspect-preview').click();expect(page.locator('#status')).to_contain_text('Saved preview and source revision pins verified')
                approve();page.locator('#build').click();expect(page.locator('#status')).to_contain_text('Fresh DOCX built')
                first=state(s)['builds'][0];original=gui_workspace/first['target']/'document.docx';pin=inspect_doc(original,False,'Requested items')
                page.locator('#inspect-build').click();expect(page.locator('#status')).to_contain_text('Registered DOCX bytes')
                original_download=download(pin,'downloaded-original');assert sha(original_download)==outcome['original_docx_sha256']
                capture('document-first.jpg');checks.append('actual_browser_reviewed_first_docx_download_matches_registered_bytes_and_xml_oracle')
                template=json.loads(page.locator('#template').input_value());template['sections'][1]['title']='Requested quantities'
                page.locator('#template').fill(json.dumps(template,indent=2));page.locator('#save-template').click();expect(page.locator('#status')).to_contain_text('New template revision saved')
                page.get_by_label('Review notes',exact=True).check();page.locator('#preview').click();expect(page.locator('#preview-summary')).to_contain_text('3 sections')
                expect(page.locator('#semantic')).to_contain_text('Requested quantities');expect(page.locator('#semantic')).to_contain_text('Review notes')
                approve();page.locator('#build').click();expect(page.locator('#status')).to_contain_text('Fresh DOCX built')
                second=state(s)['builds'][-1];revised=gui_workspace/second['target']/'document.docx';second_pin=inspect_doc(revised,True,'Requested quantities')
                revised_download=download(second_pin,'downloaded-revised');assert sha(revised_download)==outcome['revised_docx_sha256']
                assert sha(original.read_bytes())==pin and first['build_id']!=second['build_id']
                capture('document-revised.jpg');checks.append('actual_browser_revision_adds_notes_without_replacing_original_docx')
                page.locator('#builds').select_option(first['build_id']);page.locator('#inspect-build').click();expect(page.locator('#status')).to_contain_text('Registered DOCX bytes')
                assert download(pin,'downloaded-historical')==original_download
                checks.append('historical_browser_download_still_matches_original_registered_docx')
                page.set_viewport_size(dict(width=390,height=844));page.locator('#actor').focus();page.keyboard.press('Tab');expect(page.locator('#reason')).to_be_focused()
                assert page.evaluate('document.documentElement.scrollWidth')<=390;checks.append('narrow_layout_and_keyboard_navigation')
                browser_documents=dict(original_docx_sha256=pin,revised_docx_sha256=second_pin,total_quantity=7,documents=2,original_preserved=True)
                page.locator('#shutdown').click();s['shutdown_requested']=True;expect(page.locator('#status')).to_contain_text('Local server stopping')
            with server() as s:
                reopened=state(s);assert [len(reopened[k]) for k in ('templates','previews','builds')]==[2,2,2]
                page.goto(s['url']);expect(page.locator('#template-count')).to_have_text('2');expect(page.locator('#preview-count')).to_have_text('2');expect(page.locator('#build-count')).to_have_text('2')
                page.locator('#builds').select_option(first['build_id']);assert download(pin,'downloaded-after-restart')==original_download
                page.locator('#shutdown').click();s['shutdown_requested']=True
            context.close();assert all(url.startswith('http://127.0.0.1:') or url.startswith('blob:http://127.0.0.1:') for url in requests)
        checks.append('saved_instance_reopened_without_reseed_and_owned_servers_stopped')
    assert tree(root)==before;checks.append('no_package_writes_or_shipped_private_state')
    result=dict(schema=1,status='PASS',browser=browser,package_sha256=receipt['sha256'],packaging_source=receipt['packaging_source'],app_source=receipt['app_source'],runtime='3.14.10',core_tests=71,core_skips=1,checks=checks,exercise=outcome,browser_documents=browser_documents,captures=captures,scope='Fictional Windows CMD/browser/document content qualification; not Microsoft Word visual, manual separate-PC or production acceptance')
    if browser:(packages/'acceptance.json').write_bytes(encoded(result))
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
