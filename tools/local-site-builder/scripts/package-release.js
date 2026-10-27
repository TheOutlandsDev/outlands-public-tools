// Package only the reviewed, committed application subtree. No runtime files.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const {execFileSync} = require('node:child_process');
const {inventory} = require('./source-check');
const ROOT = path.resolve(__dirname, '..');
function main() {
  const args = process.argv.slice(2);
  if (args.length > 1) throw new Error('Usage: node scripts/package-release.js [NEW_ABSOLUTE_ZIP]');
  const version = require('../package.json').version;
  const filename = 'local-site-builder-' + version + '.zip';
  const output = args[0] || path.join(process.env.RUNNER_TEMP || os.tmpdir(), filename);
  if (!path.isAbsolute(output) || fs.existsSync(output)) throw new Error('Choose a new absolute ZIP path.');
  const repo = execFileSync('git', ['rev-parse', '--show-toplevel'], {cwd: ROOT, encoding: 'utf8'}).trim();
  const target = path.resolve(output), rel = path.relative(repo, target);
  if (!rel || (!rel.startsWith('..' + path.sep) && rel !== '..' && !path.isAbsolute(rel))) throw new Error('Release output must be outside the source checkout.');
  if (!fs.statSync(path.dirname(target)).isDirectory()) throw new Error('Output parent must exist.');
  const prefix = path.relative(repo, ROOT).split(path.sep).join('/');
  const ref = prefix ? 'HEAD:' + prefix : 'HEAD';
  const names = inventory().map(row => row.path).concat('SOURCE-MANIFEST.json').sort();
  const tracked = execFileSync('git', ['ls-tree', '-r', '--name-only', ref], {cwd: repo, encoding: 'utf8'}).trim().split('\n').sort();
  if (JSON.stringify(names) !== JSON.stringify(tracked)) throw new Error('Committed subtree differs from the reviewed source allowlist.');
  for (const name of names) {
    const data = execFileSync('git', ['show', 'HEAD:' + (prefix ? prefix + '/' : '') + name], {cwd: repo, maxBuffer: 5 * 1024 * 1024});
    if (!data.equals(fs.readFileSync(path.join(ROOT, name)))) throw new Error('Commit all reviewed source bytes before packaging: ' + name);
  }
  const archive = execFileSync('git', ['archive', '--format=zip', '--prefix=local-site-builder-' + version + '/', ref], {cwd: repo, maxBuffer: 15 * 1024 * 1024});
  fs.writeFileSync(target, archive, {flag: 'wx'});
  console.log(JSON.stringify({status: 'packaged', filename, version, files: names.length,
    source_commit: execFileSync('git', ['rev-parse', 'HEAD'], {cwd: repo, encoding: 'utf8'}).trim(),
    bytes: archive.length, sha256: crypto.createHash('sha256').update(archive).digest('hex')}));
}
if (require.main === module) {
  try {main();} catch (error) {console.error(error.message); process.exitCode = 1;}
}
