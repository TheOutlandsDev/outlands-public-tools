const path = require('node:path');
const {defineConfig} = require('@playwright/test');
module.exports = defineConfig({
  testDir: __dirname,
  testMatch: 'workflow.spec.js',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90000,
  globalTimeout: 180000,
  expect: {timeout: 10000},
  outputDir: path.resolve(__dirname, '../test-results/runner'),
  reporter: [['line']],
  use: {headless: true, viewport: {width: 1440, height: 960}, reducedMotion: 'reduce', trace: 'off', screenshot: 'off', video: 'off'}
});
