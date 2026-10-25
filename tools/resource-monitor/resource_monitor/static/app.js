// Original MIT dashboard. All requests remain on this page's loopback origin.
import { metric, bytes, timeLabel, chartPath, historyValues, validHistory } from '/presentation.mjs';

const $ = id => document.getElementById(id);
const tokenPattern = /^[A-Za-z0-9_-]{32,128}$/;
let token = new URLSearchParams(location.hash.slice(1)).get('token') || '';
if (!tokenPattern.test(token)) token = '';
history.replaceState(null, '', location.pathname);
let paused = false;
let timer;
let busy = false;
let connected = false;
let active = true;

function status(message, success = false) {
  $('connection-state').textContent = message;
  $('status-dot').classList.toggle('connected', success);
}

function notice(message, demo = false) {
  $('notice').textContent = message;
  $('notice').classList.toggle('demo', demo);
}

function setEnabled(value) {
  for (const id of ['pause', 'export-json', 'export-csv']) $(id).disabled = !value;
}

async function request(path) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const response = await fetch(path, { headers: { 'X-Outlands-Token': token }, cache: 'no-store', credentials: 'omit', redirect: 'error', signal: controller.signal });
    if (response.status === 403) throw new Error('auth');
    if (!response.ok) throw new Error('request');
    return response;
  } finally { clearTimeout(timeout); }
}

function draw(data) {
  if (!validHistory(data)) throw new Error('shape');
  const samples = data.samples.slice(-60);
  const current = samples.at(-1);
  $('mode-badge').textContent = data.mode === 'demo' ? 'FICTIONAL DEMO' : 'LIVE METRICS';
  $('auth-panel').hidden = true;
  setEnabled(true);
  if (!current) { notice(data.sampling_error ? 'The sampler could not complete a reading. No measurement has been substituted.' : 'Waiting for the first sample. No history is saved automatically.'); return; }
  const memory = current.memory || {};
  const network = current.network || {};
  $('cpu').textContent = metric(current.cpu_percent);
  $('memory').textContent = metric(memory.percent);
  for (const [id, value] of [['cpu-bar', current.cpu_percent], ['memory-bar', memory.percent]]) {
    if (typeof value === 'number' && Number.isFinite(value)) { $(id).value = value; $(id).setAttribute('aria-valuetext', `${metric(value)} percent`); }
    else { $(id).value = 0; $(id).setAttribute('aria-valuetext', 'Unavailable'); }
  }
  $('cpu-note').textContent = current.cpu_percent == null ? 'Warm-up or unavailable' : 'Current system utilization';
  $('memory-detail').textContent = `${bytes(memory.used_bytes)} of ${bytes(memory.total_bytes)}`;
  $('received-rate').textContent = bytes(network.received_bps, true);
  $('sent-rate').textContent = bytes(network.sent_bps, true);
  $('network-note').textContent = network.counter_reset ? 'Counter reset; awaiting baseline' : network.received_bps == null ? 'Rates need two valid samples' : 'Rates use monotonic sample time';
  $('network-totals').textContent = `↓ ${bytes(network.received_bytes)} · ↑ ${bytes(network.sent_bytes)}`;
  $('history-caption').textContent = `${data.samples.length} of ${data.capacity} retained · every ${metric(data.interval_seconds, 1)} s`;
  $('cpu-path').setAttribute('d', chartPath(historyValues(samples, ['cpu_percent'])));
  $('memory-path').setAttribute('d', chartPath(historyValues(samples, ['memory', 'percent'])));
  const received = historyValues(samples, ['network', 'received_bps']);
  const sent = historyValues(samples, ['network', 'sent_bps']);
  const maximum = Math.max(1024, ...received.filter(Number.isFinite), ...sent.filter(Number.isFinite));
  $('received-path').setAttribute('d', chartPath(received, maximum));
  $('sent-path').setAttribute('d', chartPath(sent, maximum));
  $('network-scale').textContent = `SCALE ${bytes(maximum, true)}`;
  const rows = document.createDocumentFragment();
  for (const sample of [...samples].reverse().slice(0, 10)) {
    const row = document.createElement('tr');
    const issues = Array.isArray(sample.issues) ? sample.issues : [];
    const cells = [`#${sample.sequence}`, timeLabel(sample.timestamp), `${metric(sample.cpu_percent)}%`, `${metric(sample.memory?.percent)}%`, bytes(sample.network?.received_bps, true), bytes(sample.network?.sent_bps, true), issues.length ? 'Partial / warm-up' : 'Available'];
    cells.forEach((text, index) => { const cell = document.createElement('td'); cell.textContent = text; if (index === 6) cell.className = issues.length ? 'state-note' : 'state-ok'; row.append(cell); });
    rows.append(row);
  }
  $('readings').replaceChildren(rows);
  $('last-update').textContent = `Last sample ${timeLabel(current.timestamp)} UTC`;
  const issues = Array.isArray(current.issues) ? current.issues : [];
  if (data.sampling_error) notice('The sampler could not complete its latest reading. Displayed history may be stale; no measurement was substituted.');
  else if (data.mode === 'demo') notice('Fictional demo data. This view is not reading CPU, memory or network activity from your computer.', true);
  else if (issues.length) notice('Some readings are warming up or unavailable. Missing values are not reported as zero.');
  else notice('Live aggregate metrics. History stays in server memory until you explicitly export it.');
}

async function poll() {
  clearTimeout(timer);
  if (!active || paused || busy || !token) return;
  busy = true;
  try {
    const response = await request('/api/history');
    const data = await response.json();
    if (paused || !active) return;
    draw(data);
    connected = true;
    status('Connected locally', true);
  } catch (error) {
    if (paused || !active) return;
    connected = false;
    setEnabled(false);
    if (error.message === 'auth') {
      token = '';
      $('auth-panel').hidden = false;
      setEnabled(false);
      status('Reconnect required');
      notice('The local session token is missing or expired. Open the current capability URL printed by your server.');
    } else {
      status('Connection unavailable');
      notice('Could not refresh the local API. Previous readings remain visible and may be stale.');
    }
  } finally {
    busy = false;
    if (active && !paused && token) timer = setTimeout(poll, 1000);
  }
}

async function download(format) {
  if (!connected) return;
  try {
    const response = await request(`/api/export.${format}`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `outlands-resource-history.${format}`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch {
    notice('Export could not be downloaded. Check the connection and current session token.');
  }
}

$('pause').addEventListener('click', () => {
  paused = !paused;
  $('pause').textContent = paused ? 'Resume view' : 'Pause view';
  clearTimeout(timer);
  if (paused) { status('View paused'); notice('Only this tab is paused. The server continues sampling within its bounded in-memory history.'); }
  else poll();
});
$('connect-form').addEventListener('submit', event => {
  event.preventDefault();
  const value = $('token').value.trim();
  $('token').value = '';
  if (!tokenPattern.test(value)) { notice('Enter the token from your current local server URL.'); return; }
  token = value;
  paused = false;
  $('pause').textContent = 'Pause view';
  poll();
});
$('export-json').addEventListener('click', () => download('json'));
$('export-csv').addEventListener('click', () => download('csv'));
window.addEventListener('pagehide', () => { active = false; clearTimeout(timer); });
if (!token) { $('auth-panel').hidden = false; status('Reconnect required'); notice('Use the complete local capability URL printed by the server to connect.'); }
else poll();
