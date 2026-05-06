/* ── app.js — Medical Affairs AI POC Frontend Logic ─────── */

const API = 'http://localhost:8000/api';
let pollInterval = null;
let startTime    = null;
let allPapers    = [];
let paperOffset  = 0;
let resultData   = null;

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

/* ── Run Agent ──────────────────────────────────────────── */
async function runAgent() {
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
  };

  try {
    const r = await fetch(`${API}/run-agent`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    if(!r.ok) { const e = await r.json(); throw new Error(e.error || r.statusText); }

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
    alert('Error starting agent: ' + err.message + '\n\nMake sure the API server is running:\n  cd poc/backend\n  python api_server.py');
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
    if(s.done) {
      clearInterval(pollInterval);
      document.getElementById('btn-run').disabled = false;
      document.getElementById('btn-run').innerHTML = '&#9889; Generate Evidence Package &#8594;';
      document.getElementById('prog-badge').textContent = s.error ? 'ERROR' : 'COMPLETE';
      if(s.error) {
        const firstLine = (s.error||'').split('\n')[0];
        addLog('error', 'AGENT FAILED: ' + firstLine);
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
  document.getElementById('prog-pct-label').textContent =
    `${pct}% complete — Step ${s.steps.length} of 9 ${s.running?'running':''}`;

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
      html += `<div class="step-row done">
        <div class="step-icon">${icon}</div>
        <div class="step-body">
          <div class="step-name">Step ${i+1} — ${name}</div>
          <div class="step-detail">${obs}</div>
          <span class="step-status ss-done">✔ Complete</span>
        </div></div>`;
      addLog('success', `Step ${i+1} complete: ${obs.substring(0,80)}`);
    } else if(i === steps.length) {
      html += `<div class="step-row running">
        <div class="step-icon">${icon}</div>
        <div class="step-body">
          <div class="step-name"><span class="spinner"></span>Step ${i+1} — ${name}</div>
          <div class="step-detail">Processing...</div>
          <span class="step-status ss-running">⚡ Running</span>
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
    <td style="font-size:11px;color:#64748B">${(r.journal||'').substring(0,35)}</td>
    <td style="text-align:center">${r.n_patients||'—'}</td>
    <td><b>${r.drug||'—'}</b></td>
    <td>${r.comparator||'—'}</td>
    <td style="text-align:center;font-weight:600;color:${r.pfs_months?'#16A34A':'#94A3B8'}">${r.pfs_months!=null?r.pfs_months+'mo':'—'}</td>
    <td style="text-align:center;font-weight:600;color:${r.os_months?'#2563EB':'#94A3B8'}">${r.os_months!=null?r.os_months+'mo':'—'}</td>
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
      <td style="font-weight:600;color:#1E3A5F">${k.name||'—'}</td>
      <td style="text-align:center">${k.papers_found||0}</td>
      <td>${(k.active_years||[]).join(', ')||'—'}</td>
      <td style="font-size:11px;color:#64748B">${(k.journals||[]).join(', ').substring(0,60)||'—'}</td>
      <td style="text-align:center;font-weight:800;color:#1E3A5F">${k.kol_score||0}</td>
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
    <td><a href="https://pubmed.ncbi.nlm.nih.gov/${p.pmid}" target="_blank" style="color:#2563EB;text-decoration:none;font-weight:600">${p.pmid}</a></td>
    <td style="text-align:center;font-weight:600">${p.pub_year||'—'}</td>
    <td style="max-width:300px;font-size:12px">${(p.title||'').substring(0,100)}${(p.title||'').length>100?'...':''}</td>
    <td style="font-size:11px;color:#64748B;white-space:nowrap">${(p.authors||[]).slice(0,2).join(', ')}${(p.authors||[]).length>2?' et al.':''}</td>
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
  setInterval(checkHealth, 30000);
  // Auto-load results if available
  loadResults();
});
