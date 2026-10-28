// Synthetic portable acceptance. Only a sanitized receipt leaves the private fixture.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {spawn,spawnSync,fork}=require('node:child_process');
const {once}=require('node:events');
const ROOT=path.resolve(process.argv[2]),BASE=path.resolve(process.argv[3]),BROWSER=process.argv[4];
const APP=path.join(ROOT,'application'),LAUNCH=path.join(ROOT,'launch.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const checks=[];checks.push=function(name){Array.prototype.push.call(this,name);console.log('Checked: '+name);};const password='fixture-'+crypto.randomBytes(18).toString('hex');
const temporary=path.join(BASE,'temp'),local=path.join(BASE,'local app data');fs.mkdirSync(temporary);fs.mkdirSync(local);
const workspace=path.join(local,'Outlands/LocalSiteBuilder'),data=path.join(workspace,'data'),saved=path.join(BASE,'verified backup'),restored=path.join(BASE,'restored data');
const env=Object.fromEntries(Object.entries(process.env).filter(([k])=>['SYSTEMROOT','WINDIR','COMSPEC','PATHEXT'].includes(k.toUpperCase())));
Object.assign(env,{PATH:path.join(process.env.SystemRoot,'System32'),LOCALAPPDATA:local,TEMP:temporary,TMP:temporary,TMPDIR:temporary});
function tree(root){const result={};function visit(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){assert(!e.isSymbolicLink());const f=path.join(dir,e.name);if(e.isDirectory())visit(f);else result[path.relative(root,f).split(path.sep).join('/')]=sha(fs.readFileSync(f));}}visit(root);return result;}
const original=tree(ROOT);
function cli(args=[],input,expected=0){
  const r=spawnSync(process.execPath,[LAUNCH,...args],{env,cwd:BASE,encoding:'utf8',input,timeout:60000});
  fs.writeFileSync(path.join(BASE,'last-cli.log'),r.stdout+r.stderr);
  assert.equal(r.status,expected,'Portable CLI failed; private last-cli.log retained.');return r;
}
let child,url,cookie='';
async function start(target){
  cookie='';child=fork(LAUNCH,['--no-browser',...(target?['--data',target]:[])],{execPath:process.execPath,execArgv:[],cwd:BASE,env,stdio:['ignore','pipe','pipe','ipc']});
  const log=fs.createWriteStream(path.join(BASE,'last-server.log'));child.stderr.pipe(log,{end:false});
  const result=await new Promise((resolve,reject)=>{let text='';const timeout=setTimeout(()=>reject(Error('Startup timeout')),20000);child.once('exit',()=>{clearTimeout(timeout);reject(Error('Startup failed; private log retained'));});child.stdout.on('data',b=>{log.write(b);text+=b;const m=text.match(/Editor: (http:\/\/127\.0\.0\.1:\d+)\/admin/);if(m){clearTimeout(timeout);resolve(m[1]);}});});url=result;return url;
}
async function stop(){if(child&&child.exitCode===null){const exit=once(child,'exit');child.send('shutdown');const [code]=await Promise.race([exit,new Promise((_,reject)=>{const t=setTimeout(()=>reject(Error('Shutdown timeout')),12000);t.unref();})]);assert.equal(code,0);}child=null;assert(!fs.existsSync(path.join(data,'.owner-lock')));}
async function request(route,body){
  const headers=cookie?{Cookie:cookie,Connection:'close'}:{Connection:'close'};
  if(body){const c=await fetch(url+'/api/csrf',{headers});const next=c.headers.get('set-cookie');if(next)cookie=next.split(';')[0];headers.Cookie=cookie;headers['X-CSRF-Token']=(await c.json()).csrf;headers.Origin=url;headers['Content-Type']='application/json';}
  const r=await fetch(url+route,{method:body?'POST':'GET',headers,body:body?JSON.stringify(body):undefined,redirect:'manual'});const next=r.headers.get('set-cookie');if(next)cookie=next.split(';')[0];return {status:r.status,text:await r.text()};
}
async function login(){assert.equal((await request('/admin/login',{username:'admin',password})).status,302);}
async function main(){
  const checked=JSON.parse(cli(['--check']).stdout);assert.equal(checked.runtime,'24.22.2');assert.equal(checked.abi,'137');assert(!fs.existsSync(workspace));checks.push('bundled_node_and_real_sqlite_check_creates_no_private_state');
  // Exercise the literal CMD entry point with hostile inherited Node options and a different cwd.
  const command='"'+path.join(ROOT,'Local Site Builder.cmd')+'" --check';
  const cmd=spawnSync(process.env.ComSpec||process.env.COMSPEC,['/d','/s','/c','"'+command+'"'],{windowsVerbatimArguments:true,env:{...env,NODE_OPTIONS:'--require=Z:/not-installed.cjs',NODE_PATH:'Z:/not-installed'},cwd:BASE,encoding:'utf8',timeout:60000});
  fs.writeFileSync(path.join(BASE,'cmd-check.log'),cmd.stdout+cmd.stderr);assert.equal(cmd.status,0);assert.equal(JSON.parse(cmd.stdout).runtime,'24.22.2');checks.push('cmd_entrypoint_with_spaces_ignores_external_node_options_and_path');
  const core=spawnSync(process.execPath,['--test','--test-reporter=tap','--test-concurrency=1','tests/app.test.js','tests/doctor.test.js'],{cwd:APP,env,encoding:'utf8',timeout:240000});
  fs.writeFileSync(path.join(BASE,'core-tests.log'),core.stdout+core.stderr);assert.equal(core.status,0,'Bundled core tests failed; private log retained');assert.match(core.stdout,/# tests 35/);assert.match(core.stdout,/# skipped 0/);checks.push('all_35_original_application_and_readiness_tests_zero_skips_bundled_runtime');
  const source=spawnSync(process.execPath,['scripts/source-check.js'],{cwd:APP,env,encoding:'utf8',timeout:60000});assert.equal(source.status,0);checks.push('original_complete_source_manifest_unchanged');
  cli(['--setup-stdin'],password+'\n');const settings=fs.readFileSync(path.join(workspace,'.env'));assert(!settings.includes(Buffer.from(password)));cli(['--setup-stdin'],password+'\n',1);assert.deepEqual(fs.readFileSync(path.join(workspace,'.env')),settings);assert(!fs.existsSync(data));checks.push('new_private_credentials_only_no_plain_password_or_replacement');
  cli(['--workspace',path.join(ROOT,'private forbidden'),'--setup-stdin'],password+'\n',1);assert(!fs.existsSync(path.join(ROOT,'private forbidden')));checks.push('in_package_private_storage_refused');
  await start();assert.equal((await request('/api/pages')).status,401);await login();checks.push('fictional_first_site_authenticated_and_loopback_only');
  const collision=cli(['--no-browser'],undefined,1);assert.match(collision.stderr,/EEXIST|lock/);checks.push('running_site_second_owner_refused');
  const {templatePageData}=require(path.join(APP,'content/starter-pages'));
  assert.equal((await request('/api/pages',{title:'Portable workshop',slug:'portable-workshop',template:'guide'})).status,201);
  const published=templatePageData('guide','Published portable example','portable-workshop');
  assert.equal((await request('/api/pages/portable-workshop/save-draft',{draft_json:published})).status,200);assert.equal((await request('/portable-workshop')).status,404);
  assert.equal((await request('/api/pages/portable-workshop/publish',{page_json:published})).status,200);assert.match((await request('/portable-workshop')).text,/Published portable example/);
  const draft=templatePageData('guide','Newer private portable draft','portable-workshop');assert.equal((await request('/api/pages/portable-workshop/save-draft',{draft_json:draft})).status,200);checks.push('saved_draft_private_until_explicit_publish_and_newer_draft_separate');
  cli(['--backup',path.join(BASE,'running backup')],undefined,1);assert(!fs.existsSync(path.join(BASE,'running backup')));checks.push('running_site_backup_refused_without_output');
  const oldCookie=cookie;await stop();assert.deepEqual(fs.readFileSync(path.join(workspace,'.env')),settings);
  await start();cookie=oldCookie;assert.equal((await request('/api/pages')).status,401);await login();assert.match((await request('/portable-workshop')).text,/Published portable example/);assert.match((await request('/api/pages/portable-workshop')).text,/Newer private portable draft/);await stop();checks.push('actual_process_restart_preserves_draft_and_public_page_expires_session');
  const stopped=tree(data);cli(['--backup',saved]);cli(['--verify-backup',saved]);assert.deepEqual(tree(data),stopped);assert(!fs.existsSync(path.join(saved,'.env')));checks.push('stopped_verified_backup_source_unchanged_credentials_excluded');
  const tampered=path.join(BASE,'tampered backup');fs.cpSync(saved,tampered,{recursive:true});const m=JSON.parse(fs.readFileSync(path.join(tampered,'manifest.json')));fs.appendFileSync(path.join(tampered,...m.files[0].path.split('/')),'tampered');cli(['--verify-backup',tampered],undefined,1);checks.push('tampered_backup_refused');
  cli(['--data',restored,'--restore',saved]);const restoredBefore=tree(restored);for(const r of JSON.parse(fs.readFileSync(path.join(saved,'manifest.json'))).files)assert.equal(restoredBefore[r.path],r.sha256);
  cli(['--data',restored,'--restore',saved],undefined,1);assert.deepEqual(tree(restored),restoredBefore);assert.deepEqual(tree(data),stopped);
  await start(restored);await login();assert.match((await request('/portable-workshop')).text,/Published portable example/);assert.match((await request('/api/pages/portable-workshop')).text,/Newer private portable draft/);await stop();checks.push('restore_matches_all_hashes_existing_destination_preserved_and_reopens');
  if(BROWSER){
    const {chromium}=require(BROWSER);const browser=await chromium.launch({headless:true});
    async function uiLogin(page){await page.goto(url+'/admin');await page.getByLabel('Username',{exact:true}).fill('admin');await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Login',exact:true}).click();await page.locator('#preview h1').waitFor();}
    async function text(locator,expected){await locator.waitFor();const until=Date.now()+10000;while(Date.now()<until){if((await locator.textContent()).trim()===expected)return;await new Promise(r=>setTimeout(r,100));}assert.equal((await locator.textContent()).trim(),expected);}
    let a,pub,ac,pc;
    try{
      await start();ac=await browser.newContext({viewport:{width:1440,height:960}});pc=await browser.newContext();a=await ac.newPage();pub=await pc.newPage();
      await pub.goto(url+'/');await text(pub.locator('h1'),'Welcome');await uiLogin(a);await a.locator('#preview h1').fill('Portable website demonstration');await a.getByRole('button',{name:'Save Draft',exact:true}).click();await text(a.locator('#statusbar'),'Draft saved.');await a.reload();await text(a.locator('#preview h1'),'Portable website demonstration');await pub.reload();await text(pub.locator('h1'),'Welcome');
      await a.getByRole('button',{name:'Publish',exact:true}).click();await text(a.locator('#statusbar'),'Page published.');await pub.reload();await text(pub.locator('h1'),'Portable website demonstration');
      await a.locator('#preview h1').fill('Future workshop private draft');await a.getByRole('button',{name:'Save Draft',exact:true}).click();await text(a.locator('#statusbar'),'Draft saved.');await ac.close();await pc.close();await stop();
      await start();ac=await browser.newContext();pc=await browser.newContext();a=await ac.newPage();pub=await pc.newPage();await pub.goto(url+'/');await text(pub.locator('h1'),'Portable website demonstration');await uiLogin(a);await text(a.locator('#preview h1'),'Future workshop private draft');await ac.close();await pc.close();await stop();
      const uiSaved=path.join(BASE,'browser backup'),uiRestored=path.join(BASE,'browser restored');cli(['--backup',uiSaved]);cli(['--verify-backup',uiSaved]);cli(['--data',uiRestored,'--restore',uiSaved]);await start(uiRestored);ac=await browser.newContext();pc=await browser.newContext();a=await ac.newPage();pub=await pc.newPage();await pub.goto(url+'/');await text(pub.locator('h1'),'Portable website demonstration');await uiLogin(a);await text(a.locator('#preview h1'),'Future workshop private draft');
      checks.push('chromium_editor_draft_publish_restart_and_verified_restore_bundled_processes');
    }finally{if(ac)await ac.close().catch(()=>{});if(pc)await pc.close().catch(()=>{});await stop();await browser.close();}
  }
  assert.deepEqual(tree(ROOT),original);checks.push('complete_distribution_unchanged_no_credentials_data_or_runtime_logs');
  const receipt={status:'PASS',browser:!!BROWSER,core_tests:35,application_tests:32,readiness_tests:3,core_skips:0,node:process.versions.node,abi:process.versions.modules,checks};
  fs.writeFileSync(path.join(BASE,'observed.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));
}
main().catch(async error=>{fs.writeFileSync(path.join(BASE,'failure.log'),error.stack);try{await stop();}catch{}console.error('Portable acceptance failed after '+(checks.at(-1)||'startup')+'; code='+(error.code||error.cause?.code||error.name)+'; private failure.log retained.');process.exitCode=1;});
