// Original generated-fixture tests. MIT. No live website or private data.
const {test,before,after}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {spawn}=require('node:child_process');
const crypto=require('node:crypto');
const bcrypt=require('bcryptjs');
const {once}=require('node:events');
const {backup,verify,restore}=require('../lib/backup');
const {validatePage,imageType,lock}=require('../lib/safety');
const {safeUrl,renderPageDocument}=require('../views/render');
const {templatePageData}=require('../content/starter-pages');
const {setup}=require('../scripts/setup');
const ROOT=path.resolve(__dirname,'..');
let base,folder,child,url,cookie='';const password='fictional-test-password-only';
async function start(data){
  child=spawn(process.execPath,[path.join(ROOT,'server.js')],{cwd:ROOT,stdio:['ignore','pipe','pipe','ipc'],env:{...process.env,HOST:'127.0.0.1',PORT:'0',SITE_DATA_DIR:data,ADMIN_PASSWORD_HASH:bcrypt.hashSync(password,4),SESSION_SECRET:crypto.randomBytes(32).toString('hex'),EMAIL_SERVICE_ENABLED:'false'}});
  let output='',errors='';child.stderr.on('data',d=>errors+=d);
  return await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>{child.kill();reject(new Error('Fixture server startup timed out: '+errors));},15000);
    child.stdout.on('data',d=>{output+=d;const match=output.match(/http:\/\/127\.0\.0\.1:\d+/);if(match){clearTimeout(timer);resolve(match[0]);}});
    child.once('exit',code=>{clearTimeout(timer);reject(new Error('Fixture server exited '+code+': '+errors));});
  });
}
async function stop(){if(child&&child.exitCode===null){const p=once(child,'exit');child.send('shutdown');await p;}child=null;}
async function request(route,options={}){
  let token='';
  if(options.method&&!['GET','HEAD'].includes(options.method)){
    const response=await fetch(url+'/api/csrf',{headers:cookie?{Cookie:cookie}:{}});
    const newCookie=response.headers.get('set-cookie');if(newCookie)cookie=newCookie.split(';')[0];
    token=(await response.json()).csrf;
  }
  const headers={'X-CSRF-Token':token,Origin:url,...(cookie?{Cookie:cookie}:{}),...options.headers};
  let body=options.body;
  if(body&&!(body instanceof FormData)&&typeof body!=='string'){headers['Content-Type']='application/json';body=JSON.stringify(body);}
  const response=await fetch(url+route,{redirect:'manual',...options,headers,body});
  const setCookie=response.headers.get('set-cookie');if(setCookie)cookie=setCookie.split(';')[0];
  const text=await response.text();let json;try{json=JSON.parse(text);}catch{}
  return {status:response.status,text,json,headers:response.headers};
}
before(async()=>{base=fs.mkdtempSync(path.join(os.tmpdir(),'outlands-site-test-'));folder=path.join(base,'data');url=await start(folder);});
after(async()=>{await stop();if(base&&path.dirname(base)===fs.realpathSync(os.tmpdir())&&path.basename(base).startsWith('outlands-site-test-'))fs.rmSync(base,{recursive:true,force:true});});
test('fictional starter public pages render without private family branding',async()=>{const r=await request('/');assert.equal(r.status,200);assert.match(r.text,/Cedar Workshop/);assert.doesNotMatch(r.text,/Pure Mama|puremamathyme|pregnancy|postpartum/i);});
test('private APIs and builder require login',async()=>{assert.equal((await request('/api/pages')).status,401);assert.equal((await request('/admin')).status,302);});
test('security headers and no-store apply to the editor',async()=>{const r=await request('/admin/login');assert.equal(r.headers.get('x-frame-options'),'DENY');assert.equal(r.headers.get('x-content-type-options'),'nosniff');assert.equal(r.headers.get('cache-control'),'no-store');});
test('forged host is rejected before serving site data',async()=>{const status=await new Promise((resolve,reject)=>{const req=require('node:http').get(url,{headers:{Host:'attacker.invalid'}},res=>{res.resume();resolve(res.statusCode);});req.on('error',reject);});assert.equal(status,403);});
test('cross-origin and token-free changes are rejected',async()=>{assert.equal((await request('/admin/login',{method:'POST',headers:{Origin:'https://attacker.invalid'},body:{}})).status,403);const r=await fetch(url+'/admin/login',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});assert.equal(r.status,403);});
test('invalid credentials fail and valid login regenerates a strict session',async()=>{assert.equal((await request('/admin/login',{method:'POST',body:{username:'admin',password:'wrong'}})).status,401);const r=await request('/admin/login',{method:'POST',body:{username:'admin',password}});assert.equal(r.status,302);assert.match(r.headers.get('set-cookie'),/HttpOnly/i);assert.match(r.headers.get('set-cookie'),/SameSite=Strict/i);assert.equal((await request('/api/session')).status,200);});
test('all fictional templates return valid bounded page structures',()=>{for(const id of ['guide','checklist','product','about','community','blank'])validatePage(templatePageData(id,'Example','example'));});
test('reserved and colliding slugs are rejected',async()=>{assert.equal((await request('/api/pages',{method:'POST',body:{title:'API',slug:'api'}})).status,400);assert.equal((await request('/api/pages',{method:'POST',body:{title:'Home',slug:'home'}})).status,409);});
test('new page is a draft and remains invisible publicly',async()=>{const r=await request('/api/pages',{method:'POST',body:{title:'Synthetic project',slug:'test-project',template:'guide'}});assert.equal(r.status,201);assert.equal((await request('/test-project')).status,404);});
test('saving draft does not publish and keeps its title',async()=>{const page=templatePageData('guide','Edited project','test-project');const r=await request('/api/pages/test-project/save-draft',{method:'POST',body:{title:'Edited project',draft_json:page}});assert.equal(r.status,200);assert.equal((await request('/test-project')).status,404);assert.equal((await request('/api/pages/test-project')).json.page.title,'Edited project');});
test('malformed blocks and oversized structures cannot be saved or published',async()=>{for(const draft of [{blocks:[null]},{blocks:Array(101).fill({})},{blocks:[{id:'x',type:'text',settings:{cards:[null]}}]},JSON.parse('{"blocks":[],"__proto__":{}}')]){assert.equal((await request('/api/pages/test-project/save-draft',{method:'POST',body:{draft_json:draft}})).status,400);assert.equal((await request('/api/pages/test-project/publish',{method:'POST',body:{page_json:draft}})).status,400);}});
test('publish produces escaped live content and an HTML output file',async()=>{const page=templatePageData('guide','Published <project>','test-project');page.blocks[0].settings.body='<script>alert(1)</script>';const r=await request('/api/pages/test-project/publish',{method:'POST',body:{title:'Published project',page_json:page}});assert.equal(r.status,200);const shown=await request('/test-project');assert.equal(shown.status,200);assert.match(shown.text,/&lt;script&gt;alert/);assert.doesNotMatch(shown.text,/<script>alert/);assert.ok(fs.existsSync(path.join(folder,'site/pages/test-project.html')));});
test('navigation labels and order update published HTML',async()=>{const r=await request('/api/navigation',{method:'POST',body:{items:[{slug:'test-project',label:'My project',visible:true},{slug:'home',label:'Start',visible:true}]}});assert.equal(r.status,200);const shown=await request('/');assert.match(shown.text,/My project/);assert.ok(shown.text.indexOf('My project')<shown.text.indexOf('>Start<'));});
test('published draft body, title and description remain private through a navigation refresh',async()=>{const page=templatePageData('guide','Draft-only heading','test-project');await request('/api/pages/test-project/save-draft',{method:'POST',body:{title:'Private draft title',description:'Private draft description',draft_json:page}});await request('/api/navigation',{method:'POST',body:{items:[{slug:'home',visible:true},{slug:'test-project',visible:true}]}});assert.doesNotMatch((await request('/test-project')).text,/Draft-only heading|Private draft title|Private draft description/);});
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jZuoAAAAASUVORK5CYII=','base64');
function imageForm(data=png,type='image/png',name='fictional.png'){const form=new FormData();form.set('image',new Blob([data],{type}),name);return form;}
test('raster upload checks bytes, uses a generated name and serves exact data',async()=>{const r=await request('/api/assets/upload',{method:'POST',body:imageForm()});assert.equal(r.status,201);assert.match(r.json.asset.filename,/^[a-f0-9]{32}\.png$/);const file=await fetch(url+r.json.asset.url);assert.deepEqual(Buffer.from(await file.arrayBuffer()),png);});
test('SVG, fake MIME and extra multipart fields are rejected',async()=>{assert.equal((await request('/api/assets/upload',{method:'POST',body:imageForm(Buffer.from('<svg/>'),'image/svg+xml','x.svg')})).status,400);assert.equal((await request('/api/assets/upload',{method:'POST',body:imageForm(Buffer.from('<script/>'))})).status,400);const form=imageForm();form.set('extra','no');assert.equal((await request('/api/assets/upload',{method:'POST',body:form})).status,400);});
test('missing upload and oversized image are rejected',async()=>{assert.equal((await request('/api/assets/upload',{method:'POST',body:new FormData()})).status,400);assert.equal((await request('/api/assets/upload',{method:'POST',body:imageForm(Buffer.alloc(5*1024*1024+1))})).status,400);});
test('contact message stays local with SMTP disabled and is escaped in inbox',async()=>{const r=await request('/api/contact',{method:'POST',body:{name:'<Example>',email:'demo@example.invalid',message:'Fictional message'}});assert.equal(r.status,201);assert.equal(r.json.delivered,false);assert.match((await request('/admin/inbox')).text,/&lt;Example&gt;/);assert.equal((await request('/api/email/test',{method:'POST',body:{}})).status,400);});
test('request JSON size limit is enforced',async()=>{assert.equal((await request('/api/pages',{method:'POST',body:{title:'x'.repeat(2100000)}})).status,413);});
test('unsafe URLs are rejected and text stays escaped',()=>{for(const url of ['javascript:alert(1)','data:text/html,bad','//attacker.invalid','/\\attacker.invalid','java\nscript:bad'])assert.equal(safeUrl(url),'#');assert.equal(safeUrl('/projects'),'/projects');const html=renderPageDocument({title:'<img>',slug:'x'},templatePageData('guide','<img>','x'),[]);assert.match(html,/&lt;img&gt;/);});
test('delete affects only the chosen generated draft, home is protected',async()=>{assert.equal((await request('/api/pages',{method:'POST',body:{title:'Delete fixture',slug:'delete-fixture'}})).status,201);assert.equal((await request('/api/pages/delete-fixture',{method:'DELETE'})).status,200);assert.equal((await request('/api/pages/home',{method:'DELETE'})).status,400);});
test('offline backup is blocked while the editor owns its data lock',async()=>{await assert.rejects(backup(folder,path.join(base,'blocked-backup')),/EEXIST/);});
test('logout destroys the session',async()=>{assert.equal((await request('/admin/logout',{method:'POST'})).status,302);assert.equal((await request('/api/pages')).status,401);cookie='';});
test('wrong login attempts are rate-limited',async()=>{for(let i=0;i<10;i++)assert.equal((await request('/admin/login',{method:'POST',body:{username:'admin',password:'wrong'}})).status,401);assert.equal((await request('/admin/login',{method:'POST',body:{username:'admin',password:'wrong'}})).status,429);});
test('verified backup restores pages, draft, inbox and upload into a new data root',async()=>{
  await stop();const saved=path.join(base,'backup'),restored=path.join(base,'restored');const r=await backup(folder,saved);assert.equal(r.status,'verified');verify(saved);restore(saved,restored);
  assert.throws(()=>restore(saved,restored),/already exists/);assert.equal(fs.existsSync(path.join(saved,'.env')),false);url=await start(restored);cookie='';await request('/admin/login',{method:'POST',body:{username:'admin',password}});
  assert.match((await request('/test-project')).text,/Published/);assert.match((await request('/api/pages/test-project')).text,/Draft-only heading/);assert.equal((await request('/api/messages')).json.messages.length,1);const assets=(await request('/api/assets')).json.assets;assert.equal(assets.length,1);assert.deepEqual(Buffer.from(await (await fetch(url+assets[0].url)).arrayBuffer()),png);
});
test('backup verification rejects tampering, unlisted files and unsafe manifest paths',async()=>{
  const saved=path.join(base,'backup'),manifestPath=path.join(saved,'manifest.json');const raw=fs.readFileSync(manifestPath);const manifest=JSON.parse(raw);const member=path.join(saved,...manifest.files[0].path.split('/'));const contents=fs.readFileSync(member);fs.writeFileSync(member,Buffer.from('tampered'));assert.throws(()=>verify(saved));fs.writeFileSync(member,contents);
  fs.writeFileSync(path.join(saved,'logs','extra.log'),'unexpected');assert.throws(()=>verify(saved));fs.unlinkSync(path.join(saved,'logs','extra.log'));
  manifest.files[0].path='../outside';fs.writeFileSync(manifestPath,JSON.stringify(manifest));assert.throws(()=>verify(saved));fs.writeFileSync(manifestPath,raw);verify(saved);
});
test('credential setup creates a new file without logging or replacing secrets',async()=>{const p=path.join(base,'setup');fs.mkdirSync(p);await setup('fictional-setup-password',p);const text=fs.readFileSync(path.join(p,'.env'),'utf8');assert.doesNotMatch(text,/fictional-setup-password/);const hash=text.match(/ADMIN_PASSWORD_HASH=(.+)/)[1];assert.ok(await bcrypt.compare('fictional-setup-password',hash));await assert.rejects(setup('another-fictional-password',p),/EEXIST/);await assert.rejects(setup('short',p));});
test('exclusive data lock cannot be acquired twice',()=>{const dir=path.join(base,'locks');const release=lock(dir);assert.throws(()=>lock(dir),/EEXIST/);release();const next=lock(dir);next();});
test('image signature detection rejects unsupported and undersized input',()=>{assert.equal(imageType(Buffer.from('PNG')),null);assert.deepEqual(imageType(png),['image/png','.png']);});
test('session tokens permit an opaque local webview but never token-free changes',async()=>{const r=await request('/api/pages',{method:'POST',headers:{Origin:'null'},body:{title:'Opaque fixture',slug:'opaque-fixture'}});assert.equal(r.status,201);const response=await fetch(url+'/api/pages',{method:'POST',headers:{Origin:'null',Cookie:cookie,'Content-Type':'application/json'},body:'{}'});assert.equal(response.status,403);});
test('duplicate IDs and missing per-type lists are rejected',()=>{for(const value of [{blocks:[{id:'x',type:'checklist',settings:{}}]},{blocks:[{id:'x',type:'faq',settings:{}}]},{blocks:[{id:'x',type:'three_cards',settings:{}}]},{blocks:[{id:'x',type:'text',settings:{}},{id:'x',type:'text',settings:{}}]}])assert.throws(()=>validatePage(value));});
test('static export contains only published content and replaces server contact forms',async()=>{
  const page=templatePageData('community','Contact fixture','static-contact');await request('/api/pages',{method:'POST',body:{title:'Contact fixture',slug:'static-contact',template:'community'}});await request('/api/pages/static-contact/publish',{method:'POST',body:{page_json:page}});
  await stop();const {exportSite}=require('../scripts/export');const target=path.join(base,'static-site');const r=exportSite(path.join(base,'restored'),target);assert.equal(r.status,'exported');assert.ok(fs.existsSync(path.join(target,'test-project/index.html')));assert.doesNotMatch(fs.readFileSync(path.join(target,'test-project/index.html'),'utf8'),/Private draft title|Draft-only heading/);const html=fs.readFileSync(path.join(target,'static-contact/index.html'),'utf8');assert.doesNotMatch(html,/<form/);assert.match(html,/Contact forms need the local editor server/);assert.ok(!fs.existsSync(path.join(target,'db')));assert.ok(!fs.existsSync(path.join(target,'admin')));assert.throws(()=>exportSite(path.join(base,'restored'),target));
});
