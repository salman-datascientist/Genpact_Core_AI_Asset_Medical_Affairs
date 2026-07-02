/* ── app.js — Medical Affairs AI POC Frontend Logic ─────── */

const API = `${window.location.origin}/api`;
let pollInterval = null;
let startTime    = null;
let allPapers    = [];
let paperOffset  = 0;
let resultData   = null;
let pubmedConfig = {
  has_api_key: false,
  max_without_key: 3,
  max_with_key: 10,
  default_tier: 'no_api_key',
  default_requests_per_second: 3,
  disclosure: '',
};
let pubmedThrottleTimer = null;
let pubmedMonitorActive = false;
let lastPubMedMetrics = null;

/* ── Navigation ─────────────────────────────────────────── */
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  const navMap = {
    'screen-request':'nav-request','screen-progress':'nav-progress',
    'screen-evidence':'nav-evidence','screen-gaps':'nav-gaps',
    'screen-kols':'nav-kols','screen-papers':'nav-papers'
  };
  const navEl = document.getElementById(navMap[id]);
  if(navEl) navEl.classList.add('active');
  if(id === 'screen-papers') loadPapers();
  if(id === 'screen-evidence' || id === 'screen-gaps' || id === 'screen-kols') loadResults();
}

/* ── Request type selection ─────────────────────────────── */
function selectReqType(el, val) {
  document.querySelectorAll('.req-card').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
  document.getElementById('req-type').value = val;
}

/* ── Geography tag toggle ───────────────────────────────── */
function toggleGeo(el) {
  el.classList.toggle('selected');
}

/* ── Health check ───────────────────────────────────────── */
async function checkHealth() {
  try {
    const r = await fetch(`${API}/health`, {signal: AbortSignal.timeout(3000)});
    const el = document.getElementById('api-status');
    if(r.ok) {
      el.textContent = '● API Connected';
      el.className = 'api-status ok';
    } else { throw new Error(); }
  } catch {
    const el = document.getElementById('api-status');
    el.textContent = '● API Offline — run: python backend/api_server.py';
    el.className = 'api-status err';
  }
}

/* ── PubMed rate limit UI ───────────────────────────────── */
function getPubMedTierCap() {
  const tier = document.getElementById('f-pubmed-tier').value;
  return tier === 'with_api_key'
    ? pubmedConfig.max_with_key
    : pubmedConfig.max_without_key;
}

function buildPubMedMetrics(tier, rawRps) {
  return PubMedMetrics.buildPubMedMetrics(tier, rawRps, pubmedConfig);
}

function computePubMedMetrics(rpsOverride) {
  const tier = document.getElementById('f-pubmed-tier').value;
  const rawRps = rpsOverride ?? parseFloat(document.getElementById('f-pubmed-rps').value);
  return buildPubMedMetrics(tier, rawRps);
}

function setMetricValue(id, text, statusClass) {
  const el = document.getElementById(id);
  if (!el) return;
  if (el.textContent !== text) {
    el.textContent = text;
    el.classList.remove('safe', 'warn', 'danger');
    if (statusClass) el.classList.add(statusClass);
    const metric = el.closest('.pubmed-metric');
    if (metric) {
      metric.classList.remove('bump');
      void metric.offsetWidth;
      metric.classList.add('bump');
    }
  }
}

function applyPubMedStatusClasses(prefix, status) {
  const targets = [
    document.getElementById(`${prefix}-status-message`) || document.getElementById('pubmed-status-message'),
    document.getElementById('pubmed-disclosure-banner'),
    document.getElementById('pubmed-live-badge'),
    document.getElementById('pubmed-monitor-badge'),
    document.getElementById('pubmed-monitor-message'),
  ].filter(Boolean);

  targets.forEach(el => {
    el.classList.remove('neutral', 'safe', 'warn', 'danger', 'active', 'loaded');
    if (status) el.classList.add(status);
  });
}

function updatePubMedRateUI() {
  const tierEl = document.getElementById('f-pubmed-tier');
  const rpsEl = document.getElementById('f-pubmed-rps');
  const cap = getPubMedTierCap();
  const tier = tierEl.value;

  rpsEl.max = cap;
  if (parseFloat(rpsEl.value) > cap) {
    rpsEl.value = cap;
  }

  const withKeyOption = tierEl.querySelector('option[value="with_api_key"]');
  if (withKeyOption) {
    withKeyOption.disabled = !pubmedConfig.has_api_key;
  }

  if (tier === 'with_api_key' && !pubmedConfig.has_api_key) {
    tierEl.value = 'no_api_key';
  }

  const metrics = computePubMedMetrics();
  lastPubMedMetrics = metrics;

  document.getElementById('pubmed-tier-hint').textContent =
    metrics.tier === 'with_api_key'
      ? `Using PUBMED_API_KEY from backend/.env (NCBI max ${pubmedConfig.max_with_key} req/s).`
      : `No API key detected — NCBI max ${pubmedConfig.max_without_key} req/s.`;

  document.getElementById('pubmed-rps-hint').textContent =
    `Allowed range: 0.1 to ${metrics.cap} requests/second for the selected tier.`;

  setMetricValue('metric-cap', String(metrics.cap));
  setMetricValue('metric-rps', metrics.rps.toFixed(1), metrics.status);
  setMetricValue('metric-delay', `${metrics.delaySec.toFixed(2)}s`);
  setMetricValue('metric-util', `${metrics.utilization.toFixed(0)}%`, metrics.status);

  const meterFill = document.getElementById('pubmed-meter-fill');
  const meterMarker = document.getElementById('pubmed-meter-marker');
  meterFill.style.width = `${metrics.utilization}%`;
  meterFill.classList.remove('safe', 'warn', 'danger');
  meterFill.classList.add(metrics.status);
  meterMarker.style.left = `${Math.min(metrics.utilization, 100)}%`;

  document.getElementById('pubmed-meter-caption').textContent =
    `${metrics.utilization.toFixed(0)}% of ${metrics.cap} req/s NCBI allowance`;

  const statusMsg = document.getElementById('pubmed-status-message');
  statusMsg.textContent = metrics.statusText;
  statusMsg.classList.remove('neutral', 'safe', 'warn', 'danger');
  statusMsg.classList.add(metrics.status);

  const badge = document.getElementById('pubmed-live-badge');
  badge.classList.remove('active', 'warn', 'danger');
  badge.classList.add(metrics.status === 'safe' ? 'active' : metrics.status);
  document.getElementById('pubmed-status-label').textContent = metrics.badgeText;

  rpsEl.classList.toggle('input-error', !validatePubMedRate(false));
}

function startPubMedThrottleAnimation(metrics) {
  stopPubMedThrottleAnimation();
  if (!metrics || metrics.rps <= 0) return;

  pubmedMonitorActive = true;
  const card = document.getElementById('pubmed-monitor-card');
  card.style.display = 'block';

  setMetricValue('monitor-rps', `${metrics.rps.toFixed(1)} req/s`);
  setMetricValue('monitor-delay', `${metrics.delaySec.toFixed(2)}s`);
  setMetricValue('monitor-calls', String(metrics.estCalls));

  const badge = document.getElementById('pubmed-monitor-badge');
  const stateEl = document.getElementById('pubmed-monitor-state');
  const msgEl = document.getElementById('pubmed-monitor-message');
  badge.classList.add('active');
  stateEl.textContent = 'Throttling';
  msgEl.textContent = `PubMed calls spaced at ${metrics.delaySec.toFixed(2)}s — respecting NCBI ${metrics.cap} req/s cap.`;
  msgEl.classList.add('active');

  let remaining = metrics.delaySec;
  const fill = document.getElementById('pubmed-throttle-fill');
  const countdownEl = document.getElementById('monitor-countdown');

  pubmedThrottleTimer = setInterval(() => {
    remaining -= 0.1;
    if (remaining <= 0) remaining = metrics.delaySec;
    const pct = ((metrics.delaySec - remaining) / metrics.delaySec) * 100;
    fill.style.width = `${pct}%`;
    countdownEl.textContent = `${remaining.toFixed(1)}s`;
  }, 100);
}

function stopPubMedThrottleAnimation() {
  pubmedMonitorActive = false;
  if (pubmedThrottleTimer) {
    clearInterval(pubmedThrottleTimer);
    pubmedThrottleTimer = null;
  }
  const fill = document.getElementById('pubmed-throttle-fill');
  if (fill) fill.style.width = '0%';
}

function updatePubMedProgressMonitor(agentStatus) {
  const card = document.getElementById('pubmed-monitor-card');
  const steps = agentStatus.steps || [];
  const currentStep = steps.length;
  const isPubMedStep = currentStep >= 1 && currentStep <= 3 && agentStatus.running;
  const metrics = agentStatus.pubmed_rate
    ? buildPubMedMetrics(
        agentStatus.pubmed_rate.tier || 'no_api_key',
        agentStatus.pubmed_rate.requests_per_second
      )
    : lastPubMedMetrics;

  if (!metrics) return;

  if (isPubMedStep) {
    card.style.display = 'block';
    if (!pubmedMonitorActive) startPubMedThrottleAnimation(metrics);

    const msgEl = document.getElementById('pubmed-monitor-message');
    const stepNames = ['PubMed RWE search', 'PubMed competitor search', 'PubMed metadata fetch'];
    msgEl.textContent = `Active: ${stepNames[currentStep - 1] || 'PubMed call'} — throttled to ${metrics.rps} req/s (~${metrics.estDurationSec.toFixed(0)}s total PubMed phase).`;
  } else if (agentStatus.done) {
    stopPubMedThrottleAnimation();
    card.style.display = 'block';
    const hasRateError = steps.some(s => /rate limit|429|PubMed rate/i.test(s.observation || ''));
    const badge = document.getElementById('pubmed-monitor-badge');
    const stateEl = document.getElementById('pubmed-monitor-state');
    const msgEl = document.getElementById('pubmed-monitor-message');

    badge.classList.remove('active', 'warn', 'danger');
    msgEl.classList.remove('active', 'warn', 'danger');

    if (hasRateError) {
      badge.classList.add('danger');
      stateEl.textContent = 'Rate Limited';
      msgEl.textContent = 'PubMed returned rate-limit errors. Lower requests/second and retry.';
      msgEl.classList.add('danger');
      document.getElementById('monitor-countdown').textContent = '429';
    } else {
      badge.classList.add('active');
      stateEl.textContent = 'Complete';
      msgEl.textContent = `PubMed phase finished at ${metrics.rps} req/s — all calls within NCBI limits.`;
      msgEl.classList.add('active');
      document.getElementById('monitor-countdown').textContent = 'Done';
    }
  } else if (!agentStatus.running) {
    stopPubMedThrottleAnimation();
  }
}

function validatePubMedRate(showAlert = true) {
  const tier = document.getElementById('f-pubmed-tier').value;
  const rpsEl = document.getElementById('f-pubmed-rps');
  const rps = parseFloat(rpsEl.value);
  const result = PubMedMetrics.validatePubMedRate(tier, rps, pubmedConfig);

  if (!result.valid) {
    if (showAlert) {
      if (result.reason.includes('PUBMED_API_KEY')) {
        alert('The "With API key" tier requires PUBMED_API_KEY in backend/.env.');
      } else if (result.reason.includes('cannot exceed')) {
        alert(
          `Requests per second cannot exceed ${getPubMedTierCap()} for the selected NCBI tier.\n\n` +
          pubmedConfig.disclosure
        );
      } else {
        alert('Requests per second must be greater than 0.');
      }
    }
    rpsEl.classList.add('input-error');
    return false;
  }

  rpsEl.classList.remove('input-error');
  return true;
}

async function loadPubMedConfig() {
  try {
    const r = await fetch(`${API}/pubmed-config`, { signal: AbortSignal.timeout(3000) });
    if (!r.ok) return;
    pubmedConfig = await r.json();

    document.getElementById('pubmed-disclosure').textContent = pubmedConfig.disclosure;
    document.getElementById('pubmed-disclosure-banner').classList.add('loaded');

    const tierEl = document.getElementById('f-pubmed-tier');
    tierEl.value = pubmedConfig.default_tier;
    document.getElementById('f-pubmed-rps').value =
      pubmedConfig.default_requests_per_second;

    updatePubMedRateUI();
  } catch (e) {
    document.getElementById('pubmed-disclosure').textContent =
      'Could not load NCBI rate-limit settings from the API.';
    document.getElementById('pubmed-status-message').textContent =
      'Connect to the API server to load NCBI rate-limit guidance.';
    document.getElementById('pubmed-status-label').textContent = 'Offline';
  }
}

/* ── Run Agent ──────────────────────────────────────────── */
async function runAgent() {
  if (!validatePubMedRate(true)) return;

  const btn = document.getElementById('btn-run');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Starting Agent...';

  const payload = {
    drug:         document.getElementById('f-drug').value,
    indication:   document.getElementById('f-indication').value,
    stakeholder:  document.getElementById('f-stakeholder').value,
    comparator:   document.getElementById('f-comparator').value,
    year_from:    document.getElementById('f-year-from').value,
    year_to:      document.getElementById('f-year-to').value,
    request_type: document.getElementById('req-type').value,
    geography:    [...document.querySelectorAll('.geo-tag.selected')]
                    .map(t => t.textContent.trim()).join(', ') || 'United States',
    pubmed_tier: document.getElementById('f-pubmed-tier').value,
    pubmed_requests_per_second: parseFloat(document.getElementById('f-pubmed-rps').value),
  };

  try {
    const r = await fetch(`${API}/run-agent`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    if(!r.ok) {
      const e = await r.json().catch(() => ({}));
      throw new Error(e.error || r.statusText);
    }

    const pubmedRate = payload.pubmed_requests_per_second;
    lastPubMedMetrics = computePubMedMetrics(pubmedRate);
    addLog('info', `PubMed rate limit set to ${pubmedRate} req/s (${payload.pubmed_tier}) — ~${lastPubMedMetrics.delaySec.toFixed(2)}s between calls.`);

    document.getElementById('pubmed-monitor-card').style.display = 'block';
    startPubMedThrottleAnimation(lastPubMedMetrics);

    startTime = Date.now();
    document.getElementById('chip-drug').textContent   = payload.drug;
    document.getElementById('chip-ind').textContent    = payload.indication;
    document.getElementById('chip-stake').textContent  = payload.stakeholder;
    document.getElementById('prog-chips').style.display = 'grid';
    document.getElementById('prog-sub').textContent    =
      `${payload.drug} · ${payload.indication} · ${payload.geography}`;
    document.getElementById('prog-badge').textContent  = 'RUNNING';

    showScreen('screen-progress');
    startPolling();

  } catch(err) {
    const isRateLimit = /rate limit|429|requests\/second|pubmed tier/i.test(err.message || '');
    alert(
      (isRateLimit ? 'PubMed rate limit error:\n\n' : 'Error starting agent: ') +
      err.message +
      '\n\nMake sure the API server is running:\n  cd poc/backend\n  python api_server.py'
    );
    btn.disabled = false;
    btn.innerHTML = '⚡ Generate Evidence Package →';
  }
}

/* ── Load demo results (from pre-run) ──────────────────── */
async function loadDemo() {
  showScreen('screen-progress');
  document.getElementById('prog-badge').textContent = 'LOADING DEMO';
  document.getElementById('prog-sub').textContent = 'Zejula · Ovarian Cancer · United States (pre-run results)';
  document.getElementById('prog-chips').style.display = 'grid';
  document.getElementById('chip-drug').textContent  = 'Niraparib';
  document.getElementById('chip-ind').textContent   = 'Ovarian Cancer';
  document.getElementById('chip-stake').textContent = 'Payer (Aetna)';
  document.getElementById('chip-elapsed').textContent = '48s';
  await loadResults();
  document.getElementById('prog-badge').textContent = 'COMPLETE';
}

/* ── Polling ─────────────────────────────────────────────── */
function startPolling() {
  if(pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(pollStatus, 1500);
}

async function pollStatus() {
  try {
    const r = await fetch(`${API}/agent-status`);
    const s = await r.json();
    updateProgressUI(s);
    updatePubMedProgressMonitor(s);
    if(s.done) {
      clearInterval(pollInterval);
      stopPubMedThrottleAnimation();
      updatePubMedProgressMonitor(s);
      document.getElementById('btn-run').disabled = false;
      document.getElementById('btn-run').innerHTML = '&#9889; Generate Evidence Package &#8594;';
      document.getElementById('prog-badge').textContent = s.error ? 'ERROR' : 'COMPLETE';
      if(s.error) {
        const firstLine = (s.error||'').split('\n')[0];
        addLog('error', 'AGENT FAILED: ' + firstLine);
        if (/rate limit|429|PubMed/i.test(s.error)) {
          addLog('warn', 'Tip: Lower PubMed requests/second on the request form and retry.');
        }
        addLog('warn', 'Check the server terminal for full traceback.');
        document.getElementById('prog-pct-label').textContent = 'Agent failed — see log below';
      } else {
        addLog('success', 'Agent complete! Loading results...');
        await loadResults();
      }
    }
  } catch(e) {
    console.warn('Poll error', e);
  }
}

function updateProgressUI(s) {
  const pct = s.progress || 0;
  document.getElementById('prog-bar').style.width = pct + '%';
  const rateLabel = s.pubmed_rate
    ? ` · PubMed ${s.pubmed_rate.requests_per_second} req/s`
    : (lastPubMedMetrics ? ` · PubMed ${lastPubMedMetrics.rps} req/s` : '');
  document.getElementById('prog-pct-label').textContent =
    `${pct}% complete — Step ${s.steps.length} of 9 ${s.running?'running':''}${rateLabel}`;

  if(startTime) {
    const elapsed = Math.round((Date.now() - startTime)/1000);
    document.getElementById('chip-elapsed').textContent = elapsed + 's';
    const eta = pct > 0 ? Math.round((elapsed/pct)*(100-pct)) : '—';
    document.getElementById('prog-eta').textContent = typeof eta === 'number' ? `Est. ~${eta}s remaining` : '—';
  }

  renderSteps(s.steps);
}

const STEP_ICONS = ['🔍','🔍','📥','💾','🧠','📊','🔬','👨‍⚕️','📋'];
const STEP_NAMES = [
  'PubMed Search (RWE)','PubMed Search (Competitors)','Fetch Paper Metadata',
  'Save to Database','SLR Abstract Screening','Evidence Data Extraction',
  'Gap Analysis','KOL Scoring','Generate Report'
];

function renderSteps(steps) {
  const container = document.getElementById('steps-container');
  const total = 9;
  let html = '';
  for(let i=0; i<total; i++) {
    const step = steps[i];
    const icon = STEP_ICONS[i] || '⚙️';
    const name = STEP_NAMES[i] || `Step ${i+1}`;
    if(step) {
      const obs = (step.observation||'').substring(0,200);
      const isRateErr = /rate limit|429|PubMed rate/i.test(step.observation || '');
      html += `<div class="step-row done${isRateErr ? ' error' : ''}">
        <div class="step-icon">${icon}</div>
        <div class="step-body">
          <div class="step-name">Step ${i+1} — ${name}</div>
          <div class="step-detail">${obs}</div>
          <span class="step-status ${isRateErr ? 'ss-error' : 'ss-done'}">${isRateErr ? '⚠ Rate limit issue' : '✔ Complete'}</span>
        </div></div>`;
      addLog(isRateErr ? 'warn' : 'success', `Step ${i+1} complete: ${obs.substring(0,80)}`);
    } else if(i === steps.length) {
      const isPubMedStep = i <= 2;
      html += `<div class="step-row running">
        <div class="step-icon">${icon}</div>
        <div class="step-body">
          <div class="step-name"><span class="spinner"></span>Step ${i+1} — ${name}</div>
          <div class="step-detail">${isPubMedStep && lastPubMedMetrics
            ? `Throttling PubMed calls at ${lastPubMedMetrics.rps} req/s (~${lastPubMedMetrics.delaySec.toFixed(2)}s spacing)...`
            : 'Processing...'}</div>
          <span class="step-status ss-running">${isPubMedStep ? '⏱ Rate-limited' : '⚡ Running'}</span>
        </div></div>`;
    } else {
      html += `<div class="step-row pending">
        <div class="step-icon">${icon}</div>
        <div class="step-body">
          <div class="step-name">Step ${i+1} — ${name}</div>
          <div class="step-detail">Waiting...</div>
          <span class="step-status ss-pending">⏳ Pending</span>
        </div></div>`;
    }
  }
  container.innerHTML = html;
}

let loggedLines = new Set();
function addLog(type, msg) {
  if(loggedLines.has(msg)) return;
  loggedLines.add(msg);
  const panel = document.getElementById('log-panel');
  const now = new Date().toTimeString().substring(0,8);
  const cls = {success:'log-success',error:'log-error',warn:'log-warn',info:'log-info'}[type]||'log-info';
  const typeLabel = {success:'OK   ',error:'ERROR',warn:'WARN ',info:'INFO '}[type]||'INFO ';
  panel.innerHTML += `<div class="log-line"><span class="log-time">[${now}]</span> <span class="${cls}">${typeLabel}</span> ${msg}</div>`;
  panel.scrollTop = panel.scrollHeight;
}

/* ── Load Results ────────────────────────────────────────── */
async function loadResults() {
  try {
    const r = await fetch(`${API}/results/latest`);
    if(!r.ok) return;
    resultData = await r.json();
    if(resultData.error) return;

    const sum = resultData.summary || {};
    document.getElementById('t-papers').textContent   = sum.papers_found   || 0;
    document.getElementById('t-included').textContent = sum.papers_included || (resultData.evidence_table||[]).length;
    document.getElementById('t-evidence').textContent = (resultData.evidence_table||[]).length;
    document.getElementById('t-gaps').textContent     = (resultData.gaps||[]).filter(g=>g.status==='GAP').length;

    renderEvidence(resultData);
    renderGaps(resultData);
    renderKOLs(resultData);
  } catch(e) { console.warn('Results error', e); }
}

/* ── Evidence Table ─────────────────────────────────────── */
function renderEvidence(data) {
  const rows  = data.evidence_table || [];
  const sum   = data.summary || {};
  document.getElementById('ev-total').textContent    = sum.papers_found    || rows.length;
  document.getElementById('ev-included').textContent = sum.papers_included || rows.length;
  document.getElementById('ev-excluded').textContent = sum.papers_excluded || 0;
  document.getElementById('ev-uncertain').textContent= (sum.papers_found||0) - (sum.papers_included||0) - (sum.papers_excluded||0);

  const tbody = document.getElementById('evidence-tbody');
  if(!rows.length) {
    tbody.innerHTML = '<tr><td colspan="11" class="empty-msg">No evidence extracted yet.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => `<tr>
    <td>${r.year||'—'}</td>
    <td style="max-width:240px;font-weight:500">${(r.title||'').substring(0,80)}${r.title&&r.title.length>80?'...':''}</td>
    <td style="white-space:nowrap">${(r.authors||'').substring(0,30)}</td>
    <td style="font-size:11px;color:#5A7189">${(r.journal||'').substring(0,35)}</td>
    <td style="text-align:center">${r.n_patients||'—'}</td>
    <td><b>${r.drug||'—'}</b></td>
    <td>${r.comparator||'—'}</td>
    <td style="text-align:center;font-weight:600;color:${r.pfs_months?'#16A34A':'#94A3B8'}">${r.pfs_months!=null?r.pfs_months+'mo':'—'}</td>
    <td style="text-align:center;font-weight:600;color:${r.os_months?'#00AECF':'#94A3B8'}">${r.os_months!=null?r.os_months+'mo':'—'}</td>
    <td><span style="font-size:10px;background:#F1F5F9;padding:2px 6px;border-radius:6px">${r.study_design||'—'}</span></td>
    <td>${r.country||'—'}</td>
  </tr>`).join('');
}

/* ── Gap Analysis ────────────────────────────────────────── */
function renderGaps(data) {
  const gaps    = data.gaps || data.gap_analysis || [];
  const gapCount= gaps.filter(g=>g.status==='GAP').length;
  const covCount= gaps.filter(g=>g.status==='COVERED').length;
  document.getElementById('gap-critical').textContent = gapCount;
  document.getElementById('gap-covered').textContent  = covCount;
  document.getElementById('gap-total').textContent    = gaps.length;

  const tbody = document.getElementById('gap-tbody');
  if(!gaps.length) {
    tbody.innerHTML = '<tr><td colspan="3" class="empty-msg">No gap analysis available.</td></tr>';
    return;
  }
  tbody.innerHTML = gaps.map(g => `<tr>
    <td><b>${g.required_section||g.section||'—'}</b></td>
    <td>${g.status==='COVERED'
      ? '<span class="badge-covered">&#10004; COVERED</span>'
      : '<span class="badge-gap">&#10006; GAP</span>'}</td>
    <td style="font-size:12px;color:#374151">${g.recommendation||'—'}</td>
  </tr>`).join('');
}

/* ── KOL Ranking ─────────────────────────────────────────── */
function renderKOLs(data) {
  const kols = data.kols || data.top_kols || [];
  document.getElementById('kol-high').textContent  = kols.filter(k=>k.priority==='HIGH').length;
  document.getElementById('kol-med').textContent   = kols.filter(k=>k.priority==='MEDIUM').length;
  document.getElementById('kol-total').textContent = kols.length;

  const tbody = document.getElementById('kol-tbody');
  if(!kols.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty-msg">No KOL data available.</td></tr>';
    return;
  }
  tbody.innerHTML = kols.map(k => {
    const pillCls = k.priority==='HIGH'?'pill-high':k.priority==='MEDIUM'?'pill-med':'pill-low';
    return `<tr>
      <td style="text-align:center;font-weight:700">#${k.rank}</td>
      <td style="font-weight:600;color:#073161">${k.name||'—'}</td>
      <td style="text-align:center">${k.papers_found||0}</td>
      <td>${(k.active_years||[]).join(', ')||'—'}</td>
      <td style="font-size:11px;color:#5A7189">${(k.journals||[]).join(', ').substring(0,60)||'—'}</td>
      <td style="text-align:center;font-weight:800;color:#073161">${k.kol_score||0}</td>
      <td><span class="${pillCls}">${k.priority}</span></td>
    </tr>`;
  }).join('');
}

/* ── Literature DB ───────────────────────────────────────── */
async function loadPapers(append=false) {
  try {
    const r = await fetch(`${API}/papers?limit=50&offset=${paperOffset}`);
    const d = await r.json();
    if(!append) allPapers = d.papers||[];
    else allPapers = [...allPapers, ...(d.papers||[])];
    document.getElementById('papers-count-badge').textContent = `${d.total||0} papers`;
    renderPapersTable(allPapers);
  } catch(e) {
    document.getElementById('papers-tbody').innerHTML =
      '<tr><td colspan="6" class="empty-msg">Could not load papers — API offline</td></tr>';
  }
}

function renderPapersTable(papers) {
  const tbody = document.getElementById('papers-tbody');
  if(!papers.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-msg">No papers in database yet.</td></tr>';
    return;
  }
  tbody.innerHTML = papers.map(p => `<tr>
    <td><a href="https://pubmed.ncbi.nlm.nih.gov/${p.pmid}" target="_blank" style="color:#00AECF;text-decoration:none;font-weight:600">${p.pmid}</a></td>
    <td style="text-align:center;font-weight:600">${p.pub_year||'—'}</td>
    <td style="max-width:300px;font-size:12px">${(p.title||'').substring(0,100)}${(p.title||'').length>100?'...':''}</td>
    <td style="font-size:11px;color:#5A7189;white-space:nowrap">${(p.authors||[]).slice(0,2).join(', ')}${(p.authors||[]).length>2?' et al.':''}</td>
    <td style="font-size:11px">${(p.journal||'').substring(0,40)}</td>
    <td>${p.country||'—'}</td>
  </tr>`).join('');
}

function filterPapers() {
  const q = document.getElementById('paper-search').value.toLowerCase();
  const filtered = allPapers.filter(p =>
    (p.title||'').toLowerCase().includes(q) ||
    (p.authors||[]).join(' ').toLowerCase().includes(q) ||
    (p.journal||'').toLowerCase().includes(q)
  );
  renderPapersTable(filtered);
}

function loadMorePapers() {
  paperOffset += 50;
  loadPapers(true);
}

/* ── CSV Export ──────────────────────────────────────────── */
function exportCSV() {
  if(!resultData || !resultData.evidence_table) {
    alert('No evidence data to export. Run the agent first.');
    return;
  }
  const rows = resultData.evidence_table;
  const headers = ['Year','Title','Authors','Journal','N_Patients','Drug','Comparator','PFS_months','OS_months','Study_Design','Country'];
  const csv = [headers.join(','), ...rows.map(r =>
    [r.year,`"${(r.title||'').replace(/"/g,'""')}"`,`"${r.authors||''}"`,
     `"${r.journal||''}"`,r.n_patients||'',r.drug||'',r.comparator||'',
     r.pfs_months||'',r.os_months||'',r.study_design||'',r.country||''].join(',')
  )].join('\n');
  const a = Object.assign(document.createElement('a'),{
    href: URL.createObjectURL(new Blob([csv],{type:'text/csv'})),
    download: 'evidence_table.csv'
  });
  a.click();
}

/* ── Init ────────────────────────────────────────────────── */
window.addEventListener('DOMContentLoaded', () => {
  checkHealth();
  loadPubMedConfig();
  setInterval(checkHealth, 30000);
  document.getElementById('f-pubmed-rps').addEventListener('input', updatePubMedRateUI);
  // Auto-load results if available
  loadResults();
});
