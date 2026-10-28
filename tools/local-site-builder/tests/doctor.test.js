const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {check} = require('../scripts/doctor');
test('unsupported Node fails before dependency or settings access', () => {
  assert.match(check('/nonexistent', '22.0.0', {}).join(' '), /Node.js 24/);
});
test('missing packages give an explicit install step without writing', () => {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'site-doctor-'));
  try {
    fs.writeFileSync(path.join(folder, 'package.json'), '{"dependencies":{"fictional-uninstalled-package":"1"}}');
    assert.match(check(folder, '24.0.0', {}).join(' '), /npm ci/);
    assert.deepEqual(fs.readdirSync(folder), ['package.json']);
  } finally { fs.unlinkSync(path.join(folder, 'package.json')); fs.rmdirSync(folder); }
});
test('checking a fresh installed source asks for credentials without creating them', () => {
  const root = path.resolve(__dirname, '..');
  assert.equal(fs.existsSync(path.join(root, '.env')), false);
  const before = fs.readdirSync(root);
  assert.match(check(root, '24.0.0', {}).join(' '), /run npm run setup/);
  assert.deepEqual(fs.readdirSync(root), before);
});
