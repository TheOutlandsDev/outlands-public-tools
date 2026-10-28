// Original MIT first-run checks. No installation, credentials or runtime writes.
const fs = require('node:fs');
const path = require('node:path');
const ROOT = path.resolve(__dirname, '..');
function check(root = ROOT, version = process.versions.node, env = process.env) {
  const problems = [];
  if (version.split('.')[0] !== '24') return ['Install Node.js 24 LTS with npm from https://nodejs.org/ and reopen this terminal.'];
  for (const name of Object.keys(require(path.join(root, 'package.json')).dependencies)) {
    try { require.resolve(name, {paths: [root]}); }
    catch { problems.push('Dependencies missing: run npm ci here (npm.cmd ci on PowerShell).'); break; }
  }
  if (problems.length) return problems;
  try {
    const Database = require(require.resolve('better-sqlite3', {paths: [root]}));
    const db = new Database(':memory:'); db.prepare('SELECT 1').get(); db.close();
  } catch { return ['SQLite native binding unavailable. Use Node.js 24 and run npm ci again. A compiler/SDK may be needed; see START-HERE.md.']; }
  try {
    const settings = path.join(root, '.env');
    const {plainAncestors} = require('./../lib/safety'); plainAncestors(root);
    if (!fs.existsSync(settings)) problems.push('Credentials not set: run npm run setup here. Choose a new local password when prompted.');
    else {
      if (fs.lstatSync(settings).isSymbolicLink()) throw new Error('linked');
      const values = {...require('dotenv').parse(fs.readFileSync(settings)), ...env};
      if (!/^\$2[aby]\$/.test(values.ADMIN_PASSWORD_HASH || '') || (values.SESSION_SECRET || '').length < 32)
        problems.push('Private settings incomplete. Keep .env private; see START-HERE.md before changing it.');
      const data = values.SITE_DATA_DIR;
      if (!data || !path.isAbsolute(data)) problems.push('Choose an absolute private SITE_DATA_DIR outside the extracted app. See START-HERE.md.');
      else {
        let boundary = root;
        for (let parent = root; path.dirname(parent) !== parent; parent = path.dirname(parent)) {
          if (fs.existsSync(path.join(parent, '.git'))) {boundary = parent; break;}
        }
        const full = plainAncestors(data), rel = path.relative(boundary, full);
        if (!rel || (!rel.startsWith('..' + path.sep) && rel !== '..' && !path.isAbsolute(rel)))
          problems.push('SITE_DATA_DIR must be outside the extracted app. Keep the original folder for restart/recovery.');
      }
      if (values.HOST && values.HOST !== '127.0.0.1') problems.push('HOST must be 127.0.0.1; this editor is loopback only.');
      if (values.PORT !== undefined && (!/^\d+$/.test(values.PORT) || Number(values.PORT) > 65535)) problems.push('PORT must be a number from 0 to 65535. Choose a free local port.');
    }
  } catch { problems.push('Private settings or data path could not be checked. Use ordinary trusted local files; see START-HERE.md.'); }
  return problems;
}
function main(args = process.argv.slice(2)) {
  if (args.length !== 1 || !['--check', '--start'].includes(args[0])) {
    console.error('Use node scripts/doctor.js --check or --start.'); return 2;
  }
  const problems = check();
  if (problems.length) { console.error(problems.join('\n')); return 2; }
  console.log('Ready: Node 24, application dependencies, SQLite, local credentials and external data path.');
  if (args[0] === '--start') { require('dotenv').config({path: path.join(ROOT, '.env'), quiet: true}); require('../server'); }
  return 0;
}
if (require.main === module) process.exitCode = main();
module.exports = {check, main};
