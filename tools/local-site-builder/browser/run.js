// Development-only runner. The application does not depend on Playwright.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const args = process.argv.slice(2);
if (args.some(x => x !== '--install-browser')) throw new Error('Use --install-browser or no options.');
const temporary = path.resolve(process.env.SITE_ACCEPTANCE_TEMP || path.join(os.tmpdir(), 'local-site-builder-acceptance'));
const relative = path.relative(root, temporary);
if (!relative || (!relative.startsWith('..' + path.sep) && relative !== '..' && !path.isAbsolute(relative))) throw new Error('Choose acceptance temporary storage outside the application source.');
fs.mkdirSync(temporary, {recursive: true});
const env = {...process.env, SITE_ACCEPTANCE_TEMP: temporary, TEMP: temporary, TMP: temporary, TMPDIR: temporary,
  PLAYWRIGHT_BROWSERS_PATH: process.env.PLAYWRIGHT_BROWSERS_PATH || path.join(temporary, 'browsers')};
const cli = path.join(path.dirname(require.resolve('playwright/package.json')), 'cli.js');
if (args.includes('--install-browser')) {
  const install = spawnSync(process.execPath, [cli, 'install', ...(process.platform === 'linux' && process.env.CI ? ['--with-deps'] : []), 'chromium'], {stdio: 'inherit', env});
  if (install.status !== 0) process.exit(install.status || 1);
}
const run = spawnSync(process.execPath, [cli, 'test', '--config', path.join(__dirname, 'playwright.config.js')], {cwd: root, stdio: 'inherit', env});
process.exit(run.status === null ? 1 : run.status);
