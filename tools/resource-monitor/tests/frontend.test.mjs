// Original MIT pure frontend tests using Node's built-in test runner.
import test from 'node:test';
import assert from 'node:assert/strict';
import { metric, bytes, timeLabel, chartPath, historyValues, validHistory } from '../resource_monitor/static/presentation.mjs';

test('percent formatting keeps zero and decimals', () => { assert.equal(metric(0), '0.0'); assert.equal(metric(42.25), '42.3'); });
test('missing and invalid percentages stay unavailable', () => { for (const value of [null, undefined, NaN, Infinity, -1, '20']) assert.equal(metric(value), '—'); });
test('byte formatting uses binary units and rate labels', () => { assert.equal(bytes(1024), '1.0 KiB'); assert.equal(bytes(2048, true), '2.0 KiB/s'); assert.equal(bytes(0), '0 B'); });
test('invalid bytes never render false zero', () => { for (const value of [null, undefined, NaN, Infinity, -1]) assert.equal(bytes(value), 'Unavailable'); });
test('timestamps show UTC time', () => assert.equal(timeLabel('2026-01-01T12:34:56+00:00'), '12:34:56'));
test('invalid timestamp stays unavailable', () => { for (const value of [null, '', 'invalid']) assert.equal(timeLabel(value), 'Unavailable'); });
test('chart uses bounded numeric SVG path data', () => assert.equal(chartPath([0, 50, 100]), 'M0.00,175.00 L300.00,90.00 L600.00,5.00'));
test('missing chart values form gaps', () => assert.equal(chartPath([0, null, 100]), 'M0.00,175.00  M600.00,5.00'));
test('chart clamps values above selected scale', () => assert.equal(chartPath([200], 100), 'M0.00,5.00'));
test('chart refuses unsupported bounds', () => { for (const maximum of [0, -1, Infinity, NaN]) assert.equal(chartPath([1], maximum), ''); assert.equal(chartPath(Array(601).fill(1)), ''); });
test('history extraction preserves gaps', () => assert.deepEqual(historyValues([{network:{sent_bps:1}}, {}, {network:{sent_bps:0}}], ['network','sent_bps']), [1,null,0]));
test('history schema accepts the documented bounded shape', () => assert.equal(validHistory({schema:1,mode:'demo',capacity:2,interval_seconds:1,samples:[]}), true));
test('history schema rejects unknown, oversized or nonfinite states', () => { for (const value of [null, {}, {schema:1,mode:'remote',capacity:2,interval_seconds:1,samples:[]}, {schema:1,mode:'demo',capacity:601,interval_seconds:1,samples:[]}, {schema:1,mode:'demo',capacity:1,interval_seconds:NaN,samples:[]}]) assert.equal(validHistory(value), false); });
