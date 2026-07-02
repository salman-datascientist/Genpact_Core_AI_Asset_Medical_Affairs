'use strict';

const test = require('node:test');
const assert = require('node:assert');
const path = require('path');

const metricsPath = path.join(__dirname, '..', 'js', 'pubmed-metrics.js');
const { buildPubMedMetrics, validatePubMedRate, tierCap, DEFAULT_CONFIG } = require(metricsPath);

const CONFIG = {
  ...DEFAULT_CONFIG,
  has_api_key: true,
};

test('tierCap returns correct NCBI limits', () => {
  assert.strictEqual(tierCap('no_api_key', CONFIG), 3);
  assert.strictEqual(tierCap('with_api_key', CONFIG), 10);
});

test('buildPubMedMetrics safe rate for API key tier', () => {
  const m = buildPubMedMetrics('with_api_key', 5, CONFIG);
  assert.strictEqual(m.status, 'safe');
  assert.strictEqual(m.cap, 10);
  assert.strictEqual(m.rps, 5);
  assert.ok(m.delaySec > 0.2);
  assert.strictEqual(m.utilization, 50);
});

test('buildPubMedMetrics warns near cap', () => {
  const m = buildPubMedMetrics('with_api_key', 9, CONFIG);
  assert.strictEqual(m.status, 'warn');
  assert.strictEqual(m.badgeText, 'Near Limit');
});

test('buildPubMedMetrics danger when over cap input', () => {
  const m = buildPubMedMetrics('no_api_key', 5, CONFIG);
  assert.strictEqual(m.status, 'danger');
  assert.match(m.statusText, /exceeds NCBI limit/i);
});

test('buildPubMedMetrics danger for invalid rps', () => {
  const m = buildPubMedMetrics('no_api_key', 0, CONFIG);
  assert.strictEqual(m.status, 'danger');
  assert.strictEqual(m.badgeText, 'Invalid Rate');
});

test('validatePubMedRate accepts valid settings', () => {
  const v = validatePubMedRate('with_api_key', 3, CONFIG);
  assert.strictEqual(v.valid, true);
});

test('validatePubMedRate rejects over cap', () => {
  const v = validatePubMedRate('no_api_key', 4, CONFIG);
  assert.strictEqual(v.valid, false);
  assert.match(v.reason, /cannot exceed 3/);
});

test('validatePubMedRate rejects with_key tier without env key', () => {
  const v = validatePubMedRate('with_api_key', 2, { ...CONFIG, has_api_key: false });
  assert.strictEqual(v.valid, false);
  assert.match(v.reason, /PUBMED_API_KEY/);
});
