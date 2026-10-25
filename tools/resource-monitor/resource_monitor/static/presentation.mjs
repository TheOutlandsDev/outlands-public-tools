// Original MIT pure presentation helpers. No DOM, network, storage or telemetry.
export function metric(value, digits = 1) {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value.toFixed(digits) : '—';
}

export function bytes(value, rate = false) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) return 'Unavailable';
  const labels = ['B', 'KiB', 'MiB', 'GiB', 'TiB'];
  let unit = 0;
  while (value >= 1024 && unit < labels.length - 1) { value /= 1024; unit += 1; }
  return `${value.toFixed(unit === 0 ? 0 : 1)} ${labels[unit]}${rate ? '/s' : ''}`;
}

export function timeLabel(value) {
  if (typeof value !== 'string' || !value.trim()) return 'Unavailable';
  const date = new Date(value);
  return Number.isFinite(date.getTime()) ? date.toISOString().slice(11, 19) : 'Unavailable';
}

export function chartPath(values, maximum = 100, width = 600, height = 170) {
  if (!Array.isArray(values) || !Number.isFinite(maximum) || maximum <= 0 || values.length > 600 || !Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) return '';
  let pen = false;
  return values.map((value, index) => {
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) { pen = false; return ''; }
    const x = values.length > 1 ? index * width / (values.length - 1) : 0;
    const y = 175 - Math.min(value, maximum) * height / maximum;
    const segment = `${pen ? 'L' : 'M'}${x.toFixed(2)},${y.toFixed(2)}`;
    pen = true;
    return segment;
  }).join(' ');
}

export function historyValues(samples, path) {
  return samples.map(sample => path.reduce((value, key) => value?.[key], sample) ?? null);
}

export function validHistory(value) {
  return Boolean(value && value.schema === 1 && ['demo', 'live'].includes(value.mode) &&
    Number.isInteger(value.capacity) && value.capacity >= 1 && value.capacity <= 600 &&
    typeof value.interval_seconds === 'number' && Number.isFinite(value.interval_seconds) &&
    Array.isArray(value.samples) && value.samples.length <= value.capacity);
}
