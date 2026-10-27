// Original synthetic acceptance. No real site, account, inbox or SMTP service.
const {test, expect} = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawn, spawnSync} = require('node:child_process');
const {once} = require('node:events');
const ROOT = path.resolve(__dirname, '..');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
function tree(root) {
  const files = {};
  function walk(folder) {
    for (const entry of fs.readdirSync(folder, {withFileTypes: true})) {
      const full = path.join(folder, entry.name);
      assert(!entry.isSymbolicLink(), 'Fixture paths must be ordinary directories/files');
      if (entry.isDirectory()) walk(full);
      else files[path.relative(root, full).split(path.sep).join('/')] = sha(fs.readFileSync(full));
    }
  }
  walk(root);
  return files;
}
test('private draft, explicit publish, stopped backup and verified fresh-directory recovery', async ({browser}) => {
  const temporary = fs.realpathSync(process.env.SITE_ACCEPTANCE_TEMP);
  const base = fs.mkdtempSync(path.join(temporary, 'fictional-site-'));
  assert.equal(path.dirname(base), temporary);
  const source = path.join(base, 'application');
  const data = path.join(base, 'site-data');
  const saved = path.join(base, 'verified-backup');
  const restored = path.join(base, 'restored-data');
  const evidenceDir = path.join(ROOT, 'test-results', 'acceptance');
  fs.mkdirSync(source);
  fs.mkdirSync(evidenceDir, {recursive: true});
  // Only the reviewed application files are copied; dependencies resolve from
  // this checkout, and credentials are created privately inside the fixture.
  const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, 'SOURCE-MANIFEST.json')));
  for (const row of manifest.files) {
    if (!/^(server\.js|package\.json|(?:admin|assets|content|lib|views|scripts)\/)/.test(row.path)) continue;
    const bytes = fs.readFileSync(path.join(ROOT, row.path));
    assert.equal(sha(bytes), row.sha256, 'Runtime differs from its reviewed manifest: ' + row.path);
    const dest = path.join(source, row.path);
    fs.mkdirSync(path.dirname(dest), {recursive: true});
    fs.writeFileSync(dest, bytes, {flag: 'wx'});
  }
  const environment = Object.fromEntries(['PATH', 'Path', 'SystemRoot', 'SYSTEMROOT', 'WINDIR', 'COMSPEC'].filter(key => process.env[key]).map(key => [key, process.env[key]]));
  Object.assign(environment, {NODE_PATH: path.join(ROOT, 'node_modules'), HOST: '127.0.0.1', PORT: '0', SITE_DATA_DIR: data,
    EMAIL_SERVICE_ENABLED: 'false', TEMP: temporary, TMP: temporary, TMPDIR: temporary});
  const password = 'fixture-' + crypto.randomBytes(18).toString('hex');
  let child, admin, publicPage, adminContext, publicContext;
  const summary = {synthetic_only: true, app_version: require('../package.json').version,
    node: process.version, platform: process.platform, chromium: browser.version(), status: 'running', phases: []};
  const Database = require('better-sqlite3');
  const db = new Database(':memory:');
  summary.sqlite = db.prepare('select sqlite_version() as version').get().version;
  db.close();
  const phase = name => {summary.phase = name; console.log('Acceptance: ' + name);};
  function command(script, args = [], input) {
    return spawnSync(process.execPath, [path.join(source, 'scripts', script), ...args],
      {cwd: source, env: environment, encoding: 'utf8', input, timeout: 20000});
  }
  function success(result) {assert.equal(result.status, 0, 'Fixture CLI failed: ' + result.stderr); return result;}
  async function start(folder) {
    environment.SITE_DATA_DIR = folder;
    child = spawn(process.execPath, [path.join(source, 'server.js')], {cwd: source, env: environment, stdio: ['ignore', 'pipe', 'pipe', 'ipc']});
    let output = '';
    child.stderr.resume();
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Fixture startup timed out')), 15000);
      child.once('exit', () => {clearTimeout(timer); reject(new Error('Fixture exited before startup'));});
      child.stdout.on('data', chunk => {
        output += chunk;
        const match = output.match(/http:\/\/127\.0\.0\.1:\d+/);
        if (match) {clearTimeout(timer); resolve(match[0]);}
      });
    });
  }
  async function stop() {
    if (child && child.exitCode === null) {
      const exiting = once(child, 'exit');
      child.send('shutdown');
      const [code] = await Promise.race([exiting, new Promise((_, reject) => {
        const timer = setTimeout(() => reject(new Error('Fixture shutdown timed out')), 10000); timer.unref();
      })]);
      assert.equal(code, 0, 'Graceful fixture shutdown failed');
    }
    child = null;
  }
  async function login(url) {
    await admin.goto(url + '/admin');
    await admin.getByLabel('Username', {exact: true}).fill('admin');
    await admin.getByLabel('Password', {exact: true}).fill(password);
    await admin.getByRole('button', {name: 'Login', exact: true}).click();
    await expect(admin.locator('#preview h1')).toBeVisible();
  }
  async function capture(page, name) {
    await page.screenshot({path: path.join(evidenceDir, name + '.jpg'), type: 'jpeg', quality: 88, fullPage: false});
  }
  try {
    phase('New-only setup using private stdin');
    success(command('setup.js', ['--stdin'], password + '\n'));
    const credentials = fs.readFileSync(path.join(source, '.env'));
    assert(!credentials.includes(Buffer.from(password)));
    const again = command('setup.js', ['--stdin'], password + '\n');
    assert.notEqual(again.status, 0);
    assert.deepEqual(fs.readFileSync(path.join(source, '.env')), credentials);
    summary.phases.push('setup-new-only');
    const url = await start(data);
    adminContext = await browser.newContext({viewport: {width: 1440, height: 960}, reducedMotion: 'reduce'});
    publicContext = await browser.newContext({viewport: {width: 1440, height: 960}, reducedMotion: 'reduce'});
    admin = await adminContext.newPage();
    publicPage = await publicContext.newPage();
    const errors = [];
    admin.on('pageerror', error => errors.push(error.name));
    publicPage.on('pageerror', error => errors.push(error.name));
    phase('Browser login and separate public page');
    await publicPage.goto(url + '/');
    await expect(publicPage.getByRole('heading', {level: 1})).toHaveText('Welcome');
    await capture(publicPage, '01-original-public');
    await login(url);
    phase('Saved draft remains private');
    await admin.locator('#preview h1').fill('Weekend repair guide');
    await admin.getByRole('button', {name: 'Save Draft', exact: true}).click();
    await expect(admin.locator('#statusbar')).toHaveText('Draft saved.');
    await admin.reload();
    await expect(admin.locator('#preview h1')).toHaveText('Weekend repair guide');
    await publicPage.reload();
    await expect(publicPage.getByRole('heading', {level: 1})).toHaveText('Welcome');
    await capture(admin, '02-private-draft');
    summary.phases.push('draft-reloaded-public-unchanged');
    phase('Explicit publish changes the public page');
    await admin.getByRole('button', {name: 'Publish', exact: true}).click();
    await expect(admin.locator('#statusbar')).toHaveText('Page published.');
    await publicPage.reload();
    await expect(publicPage.getByRole('heading', {level: 1})).toHaveText('Weekend repair guide');
    await capture(publicPage, '03-published-page');
    summary.phases.push('explicit-publish-observed');
    phase('Second private draft and running-backup refusal');
    await admin.locator('#preview h1').fill('Next workshop guide — draft only');
    await admin.getByRole('button', {name: 'Save Draft', exact: true}).click();
    await expect(admin.locator('#statusbar')).toHaveText('Draft saved.');
    const blocked = command('backup.js', [path.join(base, 'running-backup')]);
    assert.notEqual(blocked.status, 0);
    assert(!fs.existsSync(path.join(base, 'running-backup')));
    await adminContext.close(); adminContext = null;
    await publicContext.close(); publicContext = null;
    await stop();
    assert(!fs.existsSync(path.join(data, '.owner-lock')));
    phase('Stopped backup, checksum verification and source preservation');
    const original = tree(data);
    const backup = JSON.parse(success(command('backup.js', [saved])).stdout);
    assert.equal(backup.status, 'verified');
    success(command('backup.js', ['verify', saved]));
    assert.deepEqual(tree(data), original);
    assert(!fs.existsSync(path.join(saved, '.env')));
    const receipt = JSON.parse(fs.readFileSync(path.join(saved, 'manifest.json')));
    assert.equal(receipt.credentials_included, false);
    summary.backup_files = receipt.files.length;
    summary.phases.push('stopped-backup-verified-source-unchanged');
    phase('Tampered backup refused');
    const tampered = path.join(base, 'tampered-backup');
    fs.cpSync(saved, tampered, {recursive: true, errorOnExist: true, force: false});
    fs.appendFileSync(path.join(tampered, 'site/pages/home.html'), '\nsynthetic-tamper\n');
    assert.notEqual(command('backup.js', ['verify', tampered]).status, 0);
    summary.phases.push('tampered-backup-rejected');
    phase('Fresh-directory restore and existing-destination refusal');
    const cleanBackup = tree(saved);
    const restore = JSON.parse(success(command('backup.js', ['restore', saved, restored])).stdout);
    assert.equal(restore.status, 'restored');
    for (const row of receipt.files) assert.equal(sha(fs.readFileSync(path.join(restored, row.path))), row.sha256);
    const restoredBytes = tree(restored);
    const collision = command('backup.js', ['restore', saved, restored]);
    assert.notEqual(collision.status, 0);
    assert.match(collision.stderr, /already exists/);
    assert.deepEqual(tree(restored), restoredBytes);
    assert.deepEqual(tree(saved), cleanBackup);
    assert.deepEqual(tree(data), original);
    summary.phases.push('restored-hashes-match', 'existing-destination-unchanged');
    phase('Restored public page and separate private draft reopened');
    const reopened = await start(restored);
    adminContext = await browser.newContext({viewport: {width: 1440, height: 960}, reducedMotion: 'reduce'});
    publicContext = await browser.newContext({viewport: {width: 1440, height: 960}, reducedMotion: 'reduce'});
    admin = await adminContext.newPage();
    publicPage = await publicContext.newPage();
    admin.on('pageerror', error => errors.push(error.name));
    publicPage.on('pageerror', error => errors.push(error.name));
    await publicPage.goto(reopened + '/');
    await expect(publicPage.getByRole('heading', {level: 1})).toHaveText('Weekend repair guide');
    await login(reopened);
    await expect(admin.locator('#preview h1')).toHaveText('Next workshop guide — draft only');
    await capture(admin, '04-restored-private-draft');
    await capture(publicPage, '05-restored-public');
    assert.deepEqual(errors, []);
    summary.phases.push('restored-public-and-private-draft-observed');
    await adminContext.close(); adminContext = null;
    await publicContext.close(); publicContext = null;
    await stop();
    summary.status = 'passed';
    summary.finished_at = new Date().toISOString();
  } catch (error) {
    summary.status = 'failed';
    summary.error_type = error.name;
    // No trace, HAR, cookie jar, password, .env, backup or server log is uploaded.
    if (admin && !admin.isClosed() && !admin.url().includes('/login')) await capture(admin, 'failure').catch(() => {});
    throw error;
  } finally {
    fs.writeFileSync(path.join(evidenceDir, 'verification.json'), JSON.stringify(summary, null, 2) + '\n');
    if (adminContext) await adminContext.close().catch(() => {});
    if (publicContext) await publicContext.close().catch(() => {});
    try {await stop();} finally {
      if (child && child.exitCode === null) child.kill();
      // Remove only this test's own generated fixture after validating its root.
      assert.equal(path.dirname(base), temporary);
      assert(path.basename(base).startsWith('fictional-site-'));
      fs.rmSync(base, {recursive: true, force: true});
    }
  }
});
