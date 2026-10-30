"""Fresh bundled CMD, saved-run preservation and actual offline report browser acceptance."""
import argparse,json,os,re,shutil,subprocess,time,zipfile
from pathlib import Path
from build import FILENAME,PREFIX,SOURCE,sha,verify

def tree(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
def accept(packages,workspace,browser=False):
 assert os.name=='nt' and workspace.is_absolute() and not workspace.exists() and workspace.parent.is_dir()
 receipt=json.loads((packages/'release-receipt.json').read_bytes());raw=(packages/FILENAME).read_bytes();assert sha(raw)==receipt['sha256'];verify(raw)
 workspace.mkdir()
 with zipfile.ZipFile(packages/FILENAME) as z:z.extractall(workspace/'fresh extracted folder')
 root=workspace/'fresh extracted folder'/PREFIX.rstrip('/');original=tree(root);private=workspace/'private';private.mkdir();local=private/'app data';local.mkdir()
 env={**os.environ,'PATH':str(Path(os.environ['SystemRoot'])/'System32'),'LOCALAPPDATA':str(local),'PYTHONHOME':str(private/'wrong home'),'PYTHONPATH':str(private/'wrong path'),'PYTHONUSERBASE':str(private/'wrong user base'),'PYTHONINSPECT':'1'}
 launcher=root/'Manufacturing Review Demo.cmd'
 def cli(args,expected=0):
  line=subprocess.list2cmdline([str(launcher),*map(str,args)]);cmd='"'+os.environ['COMSPEC']+'" /d /s /c "'+line+'"'
  p=subprocess.run(cmd,cwd=private,env=env,capture_output=True,timeout=240);(private/'last-command.log').write_bytes(p.stdout+p.stderr)
  assert p.returncode==expected,'CMD failed; private log retained';assert not p.stderr
  return json.loads(p.stdout)
 health=cli(['--check','--no-browser']);assert health['runtime']=='3.14.10' and health['isolated'] and health['user_site_disabled'] and not health['external_import_paths']
 run=private/'fresh manual run';outcome=cli(['--workspace',run,'--no-browser']);assert outcome['command_checks']==36 and outcome['expected_review_outcomes']==17
 observed=json.loads((run/'result.json').read_bytes());assert observed['source_revision']==SOURCE and observed['exercises']['capacity']['command_checks']==12 and observed['exercises']['material-quality']['command_checks']==24
 for folder,value in observed['exercises'].items():
  for row in value['receipts']:
   for kind in ('input','report'):assert sha((run/folder/(row['case']+'-'+kind+'.json')).read_bytes())==row[kind+'_sha256']
 before=tree(run);assert cli(['--workspace',run,'--no-browser'],2)==dict(error='NEW_PRIVATE_RUN_REQUIRED') and tree(run)==before
 cli(['--open',run,'--no-browser']);assert tree(run)==before
 tampered=private/'changed saved run';shutil.copytree(run,tampered);(tampered/'report.html').write_bytes((tampered/'report.html').read_bytes()+b' ');changed=tree(tampered)
 assert cli(['--open',tampered,'--no-browser'],2)==dict(error='SAVED_RUN_CHANGED') and tree(tampered)==changed and tree(run)==before
 default=cli(['--no-browser']);assert default['status']=='PASS';default_report=Path(default['report']);assert default_report.is_relative_to(local/'Outlands/ManufacturingReviewDemo/runs')
 assert tree(root)==original
 captures={};video={};checks=['bundled_cmd_isolated_no_system_python_or_user_site','36_original_cli_checks_17_expected_reviews','independent_receipt_hashes','existing_run_refused_unchanged','saved_run_reopen_without_writes','tampered_run_refused_without_writes','fresh_default_appdata_run','package_tree_unchanged'];browser_checks=0
 if browser:
  assert os.environ.get('GITHUB_ACTIONS')=='true'
  from playwright.sync_api import sync_playwright,expect
  expect.set_options(timeout=15000)
  captions=[('overview','Thirty-six original CLI checks reproduce both fictional workflows. Seventeen expected review outcomes remain retained.'),
            ('capacity','Individual eligibility can pass while combined capacity fails. Compare peak three with the revised peak two.'),
            ('materials','Two labels claim five motors from one four-piece lot. Corrected declarations preserve the earlier overreservation.'),
            ('inspection','Three of four records leaves a gap. Complete records can still contain failed readings.'),
            ('outcomes','Four specimens reconcile to two first-pass good, one reworked good and one scrap. Eventual good is three quarters.'),
            ('evidence','Inspect original inputs, reports and hashes. Expected failures remain visible. Operator review is still required.')]
  with sync_playwright() as pw:
   engine=pw.chromium.launch(headless=True);context=engine.new_context(viewport=dict(width=1280,height=960),record_video_dir=str(private/'recording'),record_video_size=dict(width=1280,height=960));page=context.new_page();requests=[];page.on('request',lambda r:requests.append(r.url));video_handle=page.video
   page.goto((run/'report.html').as_uri());expect(page.get_by_text('Run complete \u2014 all expected checks reproduced.',exact=True)).to_be_visible();browser_checks+=1
   start=time.monotonic();segments=[]
   for index,(anchor,caption) in enumerate(captions):
    page.get_by_role('navigation').get_by_role('link',name=anchor.capitalize(),exact=True).click()
    if anchor=='evidence':page.locator('#evidence summary').click();expect(page.locator('#evidence table')).to_be_visible()
    page.locator('#'+anchor).screenshot(path=str(packages/('manufacturing-'+anchor+'.jpg')),type='jpeg',quality=88)
    browser_checks+=1;segments.append((index*10,(index+1)*10,caption));remaining=start+(index+1)*10-time.monotonic()
    if remaining>0:page.wait_for_timeout(remaining*1000)
   assert not any(r.startswith(('http:','https:')) for r in requests);checks.append('actual_file_report_has_no_remote_requests');browser_checks+=1
   page.set_viewport_size(dict(width=390,height=844));page.get_by_role('navigation').get_by_role('link',name='Inspection',exact=True).click();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');browser_checks+=1
   page.screenshot(path=str(packages/'manufacturing-narrow.jpg'),type='jpeg',quality=88)
   context.close();recording=Path(video_handle.path());engine.close()
  import imageio_ffmpeg
  target=packages/'manufacturing-review-walkthrough.mp4'
  result=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-hide_banner','-loglevel','error','-i',str(recording),'-an','-vf','tpad=stop_mode=clone:stop_duration=60','-t','60','-c:v','libx264','-crf','24','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],capture_output=True,timeout=180);assert result.returncode==0
  def stamp(s):return '00:'+str(s//60).zfill(2)+':'+str(s%60).zfill(2)+'.000'
  (packages/'manufacturing-review-walkthrough.vtt').write_text('WEBVTT\n\n'+''.join(stamp(a)+' --> '+stamp(b)+'\n'+text+'\n\n' for a,b,text in segments),encoding='utf-8',newline='\n')
  for p in packages.glob('manufacturing-*.jpg'):captures[p.name]=dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes()),synthetic_only=True)
  video=dict(filename=target.name,bytes=target.stat().st_size,sha256=sha(target.read_bytes()),captions='manufacturing-review-walkthrough.vtt',captions_sha256=sha((packages/'manufacturing-review-walkthrough.vtt').read_bytes()),seconds=60,actual_windows_bundle_report=True,physical_operations=False)
  checks+=['actual_windows_report_navigation_and_retained_receipts','narrow_390_no_horizontal_overflow','captioned_60_second_actual_browser_recording']
 value=dict(schema=1,status='PASS',package_sha256=receipt['sha256'],source_revision=SOURCE,packaging_revision=receipt['packaging_revision'],runtime='3.14.10',browser=browser,browser_checks=browser_checks,checks=checks,
            cli_checks=36,expected_review_outcomes=17,captures=captures,video=video,source_files_changed=False,system_python_required=False,physical_operations_performed=False,clean_windows_verification_separate=True)
 (packages/'acceptance.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');print(json.dumps(value))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
