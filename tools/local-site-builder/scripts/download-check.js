// Original MIT acceptance from an extracted source ZIP. Synthetic private data only.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawn, spawnSync} = require('node:child_process');
const {once} = require('node:events');
const ROOT = path.resolve(__dirname, '..');
const {plainAncestors} = require('../lib/safety');
const {backup, verify, restore} = require('../lib/backup');
const {templatePageData} = require('../content/starter-pages');
async function run(workspace) {
  assert.ok(path.isAbsolute(workspace), 'Choose an absolute NEW private workspace.');
  const base = plainAncestors(workspace), rel = path.relative(ROOT, base);
  assert.ok(rel.startsWith('..' + path.sep) || path.isAbsolute(rel));
  fs.mkdirSync(base); // Exclusive: never reuses someone else's work.
  assert.ok(!fs.existsSync(path.join(ROOT, '.env')), 'Use a fresh extracted app without credentials.');
  const password = crypto.randomBytes(24).toString('hex');
  const initial = path.join(base, 'site'), saved = path.join(base, 'backup'), recovered = path.join(base, 'restored');
  const env = {...process.env, HOST: '127.0.0.1', PORT: '0', SITE_DATA_DIR: initial, EMAIL_SERVICE_ENABLED: 'false'};
  for (const key of ['ADMIN_PASSWORD_HASH', 'SESSION_SECRET', 'ADMIN_USERNAME']) delete env[key];
  const setup = spawnSync(process.execPath, ['scripts/setup.js', '--stdin'], {cwd: ROOT, env, input: password + '\n', encoding: 'utf8'});
  assert.equal(setup.status, 0, 'Private setup failed.');
  const check = spawnSync(process.platform === 'win32' ? 'cmd.exe' : 'sh', process.platform === 'win32' ? ['/d', '/c', 'start.cmd --check'] : ['start.sh', '--check'], {cwd: ROOT, env, encoding: 'utf8'});
  assert.equal(check.status, 0, 'Launcher readiness check failed.');
  let child, url, cookie = '';
  async function start(data) {
    cookie = ''; env.SITE_DATA_DIR = data;
    child = spawn(process.execPath, ['scripts/doctor.js', '--start'], {cwd: ROOT, env, stdio: ['ignore', 'pipe', 'pipe', 'ipc']});
    await new Promise((resolve, reject) => {
      let text = ''; const timer = setTimeout(() => reject(new Error('Startup timeout.')), 15000);
      child.stdout.on('data', bytes => { text += bytes; const m = text.match(/http:\/\/127\.0\.0\.1:\d+/); if (m) {url = m[0]; clearTimeout(timer); resolve();} });
      child.stderr.resume(); child.once('exit', () => {clearTimeout(timer); reject(new Error('Startup failed.'));});
    });
  }
  async function stop() {
    if (child && child.exitCode === null) { const exited = once(child, 'exit'); child.send('shutdown'); await exited; }
    child = null;
  }
  async function request(route, body) {
    const headers = cookie ? {Cookie: cookie} : {};
    if (body) {
      const r = await fetch(url + '/api/csrf', {headers});
      const next = r.headers.get('set-cookie'); if (next) cookie = next.split(';')[0];
      headers.Cookie = cookie; headers['X-CSRF-Token'] = (await r.json()).csrf;
      headers.Origin = url; headers['Content-Type'] = 'application/json';
    }
    const r = await fetch(url + route, {method: body ? 'POST' : 'GET', headers, body: body ? JSON.stringify(body) : undefined, redirect: 'manual'});
    const next = r.headers.get('set-cookie'); if (next) cookie = next.split(';')[0];
    return {status: r.status, text: await r.text()};
  }
  const results = [];
  try {
    await start(initial);
    assert.equal((await request('/api/pages')).status, 401);
    assert.equal((await request('/admin/login', {username: 'admin', password})).status, 302);
    assert.equal((await request('/api/pages', {title: 'Download workshop', slug: 'download-workshop', template: 'guide'})).status, 201);
    let page = templatePageData('guide', 'Published download example', 'download-workshop');
    assert.equal((await request('/api/pages/download-workshop/save-draft', {draft_json: page})).status, 200);
    assert.equal((await request('/download-workshop')).status, 404); results.push('saved_draft_stays_private');
    assert.equal((await request('/api/pages/download-workshop/publish', {page_json: page})).status, 200);
    assert.match((await request('/download-workshop')).text, /Published download example/); results.push('explicit_publish_visible');
    page = templatePageData('guide', 'Newer private download draft', 'download-workshop');
    assert.equal((await request('/api/pages/download-workshop/save-draft', {draft_json: page})).status, 200);
    await assert.rejects(backup(initial, path.join(base, 'blocked-while-running'))); results.push('running_backup_refused');
    await stop();
    await start(initial);
    assert.equal((await request('/api/pages')).status, 401); results.push('restart_expires_session');
    assert.match((await request('/download-workshop')).text, /Published download example/);
    await stop();
    await backup(initial, saved); verify(saved);
    const member = path.join(saved, ...verify(saved).files[0].path.split('/'));
    const original = fs.readFileSync(member); fs.writeFileSync(member, 'fictional corruption');
    assert.throws(() => verify(saved)); fs.writeFileSync(member, original); verify(saved); results.push('tampered_backup_refused');
    restore(saved, recovered);
    const db = path.join(recovered, 'db/site.sqlite'), hash = () => crypto.createHash('sha256').update(fs.readFileSync(db)).digest('hex');
    const before = hash(); assert.throws(() => restore(saved, recovered)); assert.equal(hash(), before); results.push('existing_restore_preserved');
    await start(recovered);
    assert.match((await request('/download-workshop')).text, /Published download example/);
    assert.doesNotMatch((await request('/download-workshop')).text, /Newer private download draft/);
    assert.equal((await request('/admin/login', {username: 'admin', password})).status, 302);
    assert.match((await request('/api/pages/download-workshop')).text, /Newer private download draft/); results.push('restored_published_and_private_versions');
    await stop();
    const receipt = {schema: 1, app: 'local-site-builder', version: require('../package.json').version, mode: 'synthetic HTTP and CLI; no browser', checks: results, status: 'PASS'};
    fs.writeFileSync(path.join(base, 'observed-results.json'), JSON.stringify(receipt, null, 2) + '\n', {flag: 'wx'});
    console.log(JSON.stringify(receipt));
  } finally { await stop(); }
}
if (require.main === module) {
  if (process.argv.length !== 4 || process.argv[2] !== '--workspace') {console.error('Use node scripts/download-check.js --workspace ABSOLUTE_NEW_PRIVATE_DIRECTORY'); process.exitCode = 2;}
  else run(process.argv[3]).catch(() => {console.error('Download check failed. Private new files retained; no settings, URLs or raw output printed.'); process.exitCode = 1;});
}
