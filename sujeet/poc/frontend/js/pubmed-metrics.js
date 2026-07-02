/**
 * PubMed rate-limit metrics (pure functions — unit-testable without DOM).
 */
(function (root) {
  const DEFAULT_CONFIG = {
    has_api_key: false,
    max_without_key: 3,
    max_with_key: 10,
  };

  function tierCap(tier, config) {
    return tier === 'with_api_key' ? config.max_with_key : config.max_without_key;
  }

  function buildPubMedMetrics(tier, rawRps, config) {
    const cfg = { ...DEFAULT_CONFIG, ...config };
    const cap = tierCap(tier, cfg);
    const rps = Math.min(Math.max(rawRps || 0, 0), cap);
    const delaySec = rps > 0 ? 1 / rps + 0.02 : 0;
    const utilization = cap > 0 ? Math.min((rps / cap) * 100, 100) : 0;
    const estCalls = 5;

    let status = 'safe';
    let statusText = `Within NCBI limits — ${rps} req/s uses ${utilization.toFixed(0)}% of your ${cap} req/s allowance.`;
    let badgeText = cfg.has_api_key ? 'API Key Active' : 'No API Key';

    if (!Number.isFinite(rawRps) || rawRps <= 0) {
      status = 'danger';
      statusText = 'Enter a valid requests-per-second value greater than 0.';
      badgeText = 'Invalid Rate';
    } else if (rawRps > cap) {
      status = 'danger';
      statusText = `Rate exceeds NCBI limit — max ${cap} req/s for ${tier === 'with_api_key' ? 'API key' : 'no-key'} tier. Lower the value to avoid HTTP 429 errors.`;
      badgeText = 'Over Limit';
    } else if (utilization >= 85) {
      status = 'warn';
      statusText = `Approaching NCBI cap — ${utilization.toFixed(0)}% of ${cap} req/s used. Consider lowering to reduce 429 risk.`;
      badgeText = 'Near Limit';
    } else if (tier === 'with_api_key' && cfg.has_api_key) {
      statusText = `Optimized for NCBI API key tier — ${rps} req/s with ~${delaySec.toFixed(2)}s spacing between calls.`;
    } else {
      statusText = `Conservative NCBI no-key tier — ${rps} req/s keeps you under the 3 req/s public limit.`;
    }

    return {
      tier,
      cap,
      rps: Number.isFinite(rawRps) ? rawRps : 0,
      delaySec,
      utilization,
      estCalls,
      estDurationSec: estCalls * delaySec,
      status,
      statusText,
      badgeText,
    };
  }

  function validatePubMedRate(tier, rawRps, config) {
    const cfg = { ...DEFAULT_CONFIG, ...config };
    const cap = tierCap(tier, cfg);

    if (!Number.isFinite(rawRps) || rawRps <= 0) {
      return { valid: false, reason: 'requests_per_second must be greater than 0' };
    }
    if (rawRps > cap) {
      return { valid: false, reason: `cannot exceed ${cap} for tier ${tier}` };
    }
    if (tier === 'with_api_key' && !cfg.has_api_key) {
      return { valid: false, reason: 'with_api_key tier requires PUBMED_API_KEY' };
    }
    return { valid: true };
  }

  const api = { buildPubMedMetrics, validatePubMedRate, tierCap, DEFAULT_CONFIG };
  root.PubMedMetrics = api;

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})(typeof window !== 'undefined' ? window : globalThis);
