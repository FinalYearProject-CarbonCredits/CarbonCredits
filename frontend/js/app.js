const API = 'http://localhost:8000/api';

//  NAVIGATION

function showPage(pageId, event) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  const page = document.getElementById('page-' + pageId);
  if (!page) return;
  page.classList.add('active');

  if (event && event.currentTarget) {
    event.currentTarget.classList.add('active');
  } else {
    const tab = document.querySelector(`.nav-tab[data-page="${pageId}"]`);
    if (tab) tab.classList.add('active');
  }

  // Load real data when switching tabs
  if (pageId === 'dashboard') {
    loadDashboard();
    startDashboardRefresh();  // Auto-refresh every 30s
  } else {
    stopDashboardRefresh();   // Stop refresh when leaving
  }
  
  if (pageId === 'projects')   loadProjects();
  if (pageId === 'satellite')  loadSatellitePage();
  if (pageId === 'trading')    loadTrades();
  if (pageId === 'blockchain' && !chainsRendered) renderChain();
}

//  TOAST

function toast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = '// ' + msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

//  CHARTS

Chart.defaults.color = '#4a6152';
Chart.defaults.borderColor = 'rgba(34,197,94,0.08)';

function makeLineChart(id, labels, datasets) {
  const ctx = document.getElementById(id);
  if (!ctx) return;
  new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(34,197,94,0.05)' }, ticks: { font: { family: 'DM Mono', size: 9 }, color: '#4a6152' } },
        y: { grid: { color: 'rgba(34,197,94,0.05)' }, ticks: { font: { family: 'DM Mono', size: 9 }, color: '#4a6152' } }
      },
      elements: { point: { radius: 0, hoverRadius: 4 }, line: { tension: 0.4 } }
    }
  });
}

const days    = Array.from({ length: 30 }, (_, i) => `D${i + 1}`);
const genData = (base, noise) => days.map(() => base + (Math.random() - 0.4) * noise);

function initCharts() {
  makeLineChart('chart-issuance', days, [
    { data: genData(80000, 30000), borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.08)', fill: true, borderWidth: 1.5 },
    { data: genData(30000, 15000), borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,0.06)', fill: true, borderWidth: 1.5 }
  ]);
  makeLineChart('chart-price', days, [
    { data: genData(1180, 80), borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.08)', fill: true, borderWidth: 1.5 }
  ]);
}


//  LIVE FEED (dashboard)

const feedItems = [
  ['green', 'Sanjay Gandhi NP — 1,200 tCO₂ batch verified',     '// NDVI scan complete'],
  ['blue',  'Thane Mangroves CCT retired by Tata Chemicals',      '// 200 CCT offset'],
  ['amber', 'Aarey Colony — AI evaluation queued',                '// Pending scan data'],
  ['green', 'New project registered — Ulhas River Wetland',       '// Mumbai/Thane region'],
  ['red',   'Anomaly detected — Powai baseline mismatch',         '// Manual review'],
  ['blue',  'DEX pool rebalanced — 5,000 CCT added',              '// Pool B liquidity'],
  ['green', 'PACT score updated — Thane Creek Mangroves: 84.1',  '// Annual review complete']
];
let feedIdx = 0;

setInterval(() => {
  const feed = document.getElementById('live-feed');
  if (!feed) return;
  const item = feedItems[feedIdx % feedItems.length];
  feedIdx++;
  const el = document.createElement('div');
  el.className = 'feed-item';
  el.innerHTML = `<div class="feed-dot ${item[0]}"></div><div class="feed-text">${item[1]} <span>${item[2]}</span></div><div class="feed-time">now</div>`;
  feed.insertBefore(el, feed.firstChild);
  if (feed.children.length > 8) feed.removeChild(feed.lastChild);
}, 5000);

//  DASHBOARD — real data from backend (DYNAMIC)

let dashboardRefreshInterval = null;

// Fallback static data if backend is offline
const DASHBOARD_FALLBACK = {
  total_credits_cct: 185200,
  total_volume_inr: 229648000,
  total_projects: 6,
  avg_ndvi_region: 0.62,
  cct_price_inr: 1240,
  credits_pending: 12500,
  status_msg: 'Using cached data'
};

async function loadDashboard() {
  const loader = document.getElementById('dashboard-loader');
  if (loader) loader.style.display = 'flex';
  
  try {
    const res  = await fetch(`${API}/dashboard`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // Update with real data
    updateDashboardUI(data);
    if (loader) loader.style.display = 'none';
    toast('Dashboard data refreshed');
  } catch (e) {
    console.warn('Backend offline — using cached data', e);
    // Use fallback data
    updateDashboardUI(DASHBOARD_FALLBACK);
    if (loader) loader.style.display = 'none';
    toast('Backend offline — showing cached dashboard data');
  }
}

function updateDashboardUI(data) {
  // Hero stats - with fade animation
  const statVals = document.querySelectorAll('.hero-stat-val');
  const updates = [
    (data.total_credits_cct / 1000).toFixed(1) + 'K',
    '₹' + Math.round(data.total_volume_inr / 1e7) + 'Cr',
    data.total_projects.toString(),
    (data.avg_ndvi_region || 0.62).toFixed(2)
  ];
  
  statVals.forEach((el, i) => {
    if (el && updates[i]) {
      el.style.opacity = '0.5';
      el.textContent = updates[i];
      setTimeout(() => {
        el.style.transition = 'opacity 0.3s ease';
        el.style.opacity = '1';
      }, 50);
    }
  });

  // Metric cards
  const metricVals = document.querySelectorAll('.metric-val');
  if (metricVals[0]) metricVals[0].textContent = data.total_credits_cct.toLocaleString('en-IN') + ' CCT';
  if (metricVals[1]) metricVals[1].textContent = '₹' + data.cct_price_inr.toLocaleString('en-IN');
  
  // Additional metrics if available
  if (data.credits_pending) {
    const pendingEl = document.getElementById('credits-pending');
    if (pendingEl) pendingEl.textContent = data.credits_pending.toLocaleString('en-IN') + ' CCT';
  }
  if (data.status_msg) {
    const statusEl = document.getElementById('dashboard-status');
    if (statusEl) statusEl.textContent = data.status_msg;
  }
}

// Auto-refresh dashboard every 30 seconds when on dashboard tab
function startDashboardRefresh() {
  if (dashboardRefreshInterval) clearInterval(dashboardRefreshInterval);
  dashboardRefreshInterval = setInterval(() => loadDashboard(), 30000);
}

function stopDashboardRefresh() {
  if (dashboardRefreshInterval) {
    clearInterval(dashboardRefreshInterval);
    dashboardRefreshInterval = null;
  }
}

//  WEATHER — live from Open-Meteo via backend

async function loadWeather() {
  try {
    const res  = await fetch(`${API}/weather/mumbai`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const c    = data.current;
    const msg = `Mumbai Live: ${c.temperature_c}°C · Rain: ${c.precipitation_mm}mm · Wind: ${c.windspeed_kmh} km/h`;
    toast(msg);
    
    // Update weather widget if it exists
    const weatherEl = document.getElementById('dashboard-weather');
    if (weatherEl) {
      weatherEl.innerHTML = `<span style="font-family:var(--mono);font-size:11px;">🌡️ ${c.temperature_c}°C</span>`;
    }
  } catch (e) {
    console.warn('Weather API unavailable', e);
    // Use fallback weather
    const fallbackWeather = { temperature_c: 28, precipitation_mm: 2, windspeed_kmh: 12 };
    const msg = `Mumbai (cached): ${fallbackWeather.temperature_c}°C · Rain: ${fallbackWeather.precipitation_mm}mm · Wind: ${fallbackWeather.windspeed_kmh} km/h`;
    toast(msg);
  }
}


//  SATELLITE PAGE — real NDVI from backend

/*async function loadSatellitePage() {
  await loadNdviData();
}*/

async function runSatelliteScan() {
  toast('Fetching real NDVI from NASA MODIS — this can take 10-20s...');
  try {
    const res = await fetch(`${API}/ndvi/refresh`, { method: 'POST' });
    const data = await res.json();
    toast(data.message);
  } catch (e) {
    toast('MODIS refresh failed — network or NASA endpoint issue');
  }
  loadNdviData();
}

async function loadNdviData() {
  const grid = document.getElementById('sat-grid');
  if (!grid) return;
  grid.innerHTML = ''; // clear old content so we always refresh

  try {
    const res  = await fetch(`${API}/ndvi/mumbai`);
    const data = await res.json();

    data.zones.forEach(z => {
      const colorMap = { EXCELLENT: '#22c55e', GOOD: '#22c55e', MODERATE: '#f59e0b', POOR: '#f87171' };
      const color    = colorMap[z.health] || '#38bdf8';
      const g        = Math.floor(z.ndvi * 80 + 20);
      const r        = Math.floor((1 - z.ndvi) * 60);

      const div      = document.createElement('div');
      div.className  = 'sat-img';
      div.onclick    = () => toast(`${z.name} — NDVI: ${z.ndvi} — ${z.health}`);
      div.innerHTML  = `
        <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
          ${Array.from({ length: 200 }, () =>
            `<circle cx="${Math.random()*100}" cy="${Math.random()*100}"
             r="${Math.random()*2+0.5}"
             fill="rgb(${r},${g},${Math.floor(Math.random()*40)})"
             opacity="${Math.random()*0.8+0.2}"/>`
          ).join('')}
          <rect x="0" y="0" width="100" height="100" fill="none"
            stroke="${color}" stroke-width="0.5" opacity="0.3"/>
        </svg>
        <div class="sat-label">${z.name.split(' ').slice(0, 3).join(' ')}</div>
        <div class="sat-score">
          <span class="badge badge-green" style="font-size:9px;">NDVI ${z.ndvi}</span>
        </div>`;
      grid.appendChild(div);
    });

    toast(`Loaded ${data.zones.length} real NDVI zones — NASA MODIS data`);
  } catch (e) {
    console.warn('NDVI API unavailable, using static data');
    renderSatGridStatic(); // fallback
  }
}

// Fallback static satellite grid (original code)
function renderSatGridStatic() {
  const grid = document.getElementById('sat-grid');
  if (!grid) return;
  const sats = [
    { name: 'SGNP Borivali',  ndvi: 0.71, color: '#22c55e' },
    { name: 'Aarey Colony',   ndvi: 0.58, color: '#22c55e' },
    { name: 'Thane Mangroves',ndvi: 0.64, color: '#22c55e' },
    { name: 'Powai Lake',     ndvi: 0.39, color: '#f59e0b' },
    { name: 'Yeoor Hills',    ndvi: 0.67, color: '#22c55e' },
    { name: 'Ulhas Wetlands', ndvi: 0.44, color: '#f59e0b' }
  ];
  sats.forEach(s => {
    const g   = Math.floor(s.ndvi * 80 + 20);
    const r   = Math.floor((1 - s.ndvi) * 60);
    const div = document.createElement('div');
    div.className = 'sat-img';
    div.onclick   = () => toast(`${s.name} — NDVI: ${s.ndvi} — Biomass scan complete`);
    div.innerHTML = `
      <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        ${Array.from({ length: 200 }, () =>
          `<circle cx="${Math.random()*100}" cy="${Math.random()*100}"
           r="${Math.random()*2+0.5}" fill="rgb(${r},${g},${Math.floor(Math.random()*40)})"
           opacity="${Math.random()*0.8+0.2}"/>`
        ).join('')}
        <rect x="0" y="0" width="100" height="100" fill="none" stroke="${s.color}" stroke-width="0.5" opacity="0.3"/>
      </svg>
      <div class="sat-label">${s.name}</div>
      <div class="sat-score"><span class="badge badge-green" style="font-size:9px;">NDVI ${s.ndvi}</span></div>`;
    grid.appendChild(div);
  });
}

function runSatelliteScan() {
  toast('New satellite scan queued — Sentinel-2 tasked for Mumbai/Thane project areas');
  setTimeout(() => loadNdviData(), 1500);
}

//  PROJECTS — real data from backend DB

async function loadProjects() {
  try {
    const res      = await fetch(`${API}/projects`);
    const projects = await res.json();
    const table    = document.getElementById('projects-table');
    if (!table) return;

    table.innerHTML = '';
    projects.forEach(p => {
      const badgeMap = { ACTIVE:'green', PENDING:'blue', REVIEW:'amber', REJECTED:'red', EVALUATING:'amber' };
      const color    = badgeMap[p.status] || 'blue';
      const row      = document.createElement('tr');
      row.innerHTML  = `
        <td>${p.name}
          <div class="mono">${p.location}${p.osm_id ? ' · OSM#' + p.osm_id : ''}</div>
        </td>
        <td>${p.type}</td>
        <td>${p.location}</td>
        <td>${p.area_ha ? Number(p.area_ha).toLocaleString() + ' ha' : '—'}</td>
        <td>${p.claimed_co2 ? parseInt(p.claimed_co2).toLocaleString() : '—'}</td>
        <td style="color:var(--green);font-family:var(--mono);">${p.pact_score ?? '—'}</td>
        <td style="font-family:var(--mono);">${p.tokens_issued ? p.tokens_issued.toLocaleString() : '0'}</td>
        <td><span class="badge badge-${color}">${p.status}</span></td>`;
      row.onclick = () => toast(`${p.name} · ${p.area_ha} ha · Status: ${p.status}`);
      table.appendChild(row);
    });

    toast(`Loaded ${projects.length} real Mumbai/Thane projects from database`);
  } catch (e) {
    console.warn('Projects API unavailable');
    toast('Backend offline — showing cached data');
  }
}

function showAddProject() {
  const f = document.getElementById('add-project-form');
  if (!f) return;
  f.style.display = f.style.display === 'none' ? 'block' : 'none';
}

async function registerProject() {
  const name = document.getElementById('new-proj-name')?.value;
  const type = document.getElementById('new-proj-type')?.value;
  const loc  = document.getElementById('new-proj-loc')?.value;
  const area = document.getElementById('new-proj-area')?.value;
  const co2  = document.getElementById('new-proj-co2')?.value;

  if (!name || !loc || !area || !co2) { toast('Please fill all required fields'); return; }

  try {
    const res  = await fetch(`${API}/projects`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        type,
        location:    loc,
        area_ha:     parseFloat(area),
        claimed_co2: parseFloat(co2),
      }),
    });
    const data = await res.json();
    toast(`"${data.project.name}" saved to database!`);
    document.getElementById('add-project-form').style.display = 'none';
    // Clear fields
    ['new-proj-name','new-proj-loc','new-proj-area','new-proj-co2','new-proj-org']
      .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    loadProjects(); // refresh table with new real entry
  } catch (e) {
    toast('Backend offline — could not save project');
  }
}

//  BLOCKCHAIN

let chainsRendered = false;
let blockHeight    = 28492;
const blocks       = [
  { num: 28488, hash: 'a4f9...c21e', data: 'MINT 24,800 CCT\nSGNP · 89.2 PACT' },
  { num: 28489, hash: 'b7d2...8f31', data: 'TRANSFER 2,000 CCT\nDEX Pool B' },
  { num: 28490, hash: 'c1a8...5d9a', data: 'MINT 4,100 CCT\nThane Mangroves · 84.1 PACT' },
  { num: 28491, hash: 'd3f4...2b7c', data: 'RETIRE 500 CCT\nTata Chemicals offset' },
  { num: 28492, hash: 'e9c6...4f12', data: 'MINT 2,700 CCT\nAarey Colony · 78.5 PACT' }
];

function renderChain() {
  chainsRendered = true;
  const chain    = document.getElementById('chain-display');
  if (!chain) return;
  chain.innerHTML = '';
  blocks.forEach((b, i) => {
    if (i > 0) {
      const arrow       = document.createElement('div');
      arrow.className   = 'block-arrow';
      arrow.textContent = '←';
      chain.appendChild(arrow);
    }
    const block = document.createElement('div');
    block.className = 'block';
    if (i === blocks.length - 1) block.style.borderColor = 'var(--green)';
    block.innerHTML = `<div class="block-num">#${b.num}</div><div class="block-hash">${b.hash}</div><div class="block-data">${b.data.replace('\n','<br>')}</div>`;
    block.onclick   = () => toast(`Block #${b.num} — Hash: ${b.hash}`);
    chain.appendChild(block);
  });
}

function addBlock() {
  blockHeight++;
  const el = document.getElementById('chain-height');
  if (el) el.textContent = blockHeight.toLocaleString();
  const types = ['MINT', 'TRANSFER', 'RETIRE'];
  const type  = types[Math.floor(Math.random() * 3)];
  const amt   = Math.floor(Math.random() * 3000 + 200);
  const hash  = Math.random().toString(36).substr(2, 4) + '...' + Math.random().toString(36).substr(2, 4);
  blocks.push({ num: blockHeight, hash, data: `${type} ${amt} CCT\nMumbai/Thane Region` });
  if (blocks.length > 6) blocks.shift();
  if (chainsRendered) renderChain();
  const chain = document.getElementById('chain-display');
  if (chain) chain.scrollLeft = chain.scrollWidth;
  toast(`Block #${blockHeight} added — ${type} ${amt} CCT`);
}

async function mintToken() {
  const proj  = document.getElementById('mint-project')?.value;
  const amt   = document.getElementById('mint-amount')?.value;
  const pact  = document.getElementById('mint-pact')?.value;
  if (!proj || !amt) { toast('Please fill all fields'); return; }

  try {
    // Find the matching project from DB
    const projRes  = await fetch(`${API}/projects`);
    const projects = await projRes.json();
    const match    = projects.find(p => proj.toLowerCase().includes(p.name.split(' ')[0].toLowerCase()));
    const pid      = match ? match.id : 1;

    const res  = await fetch(`${API}/credits/mint`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: pid, amount_cct: parseInt(amt), pact_score: parseFloat(pact) }),
    });
    const data = await res.json();
    blockHeight++;
    const el = document.getElementById('chain-height');
    if (el) el.textContent = blockHeight.toLocaleString();
    toast(`${data.message}`);
    addBlock();
    loadProjects(); // refresh project token count
  } catch (e) {
    // Fallback if backend offline
    blockHeight++;
    const el = document.getElementById('chain-height');
    if (el) el.textContent = blockHeight.toLocaleString();
    toast(`Minted ${amt} CCT for ${proj} — PACT: ${pact} — Block #${blockHeight}`);
    addBlock();
  }
}

//  TRADING

let tradeType = 'BUY';
let tradeData = { amount: 0, price: 0, total: 0 };

function setTradeType(type) {
  tradeType = type;
  document.querySelectorAll('.trade-type-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelector(`[data-trade-type="${type}"]`).classList.add('active');
}

function updateTradeCalc() {
  const amount = parseFloat(document.getElementById('trade-amount')?.value) || 0;
  const price  = parseFloat(document.getElementById('trade-price')?.value) || 1240;
  const total  = amount * price;
  tradeData = { amount, price, total };
  
  const totalEl = document.getElementById('trade-total');
  if (totalEl) totalEl.textContent = '₹' + total.toLocaleString('en-IN');
}

function executeTrade() {
  const { amount, price, total } = tradeData;
  if (!amount) { toast('Enter amount to trade'); return; }
  toast(`${tradeType} order: ${amount.toLocaleString()} CCT @ ₹${price.toLocaleString('en-IN')}/token = ₹${total.toLocaleString('en-IN')} — Order placed on DEX`);
}

async function loadTrades() {
  const table = document.getElementById('trades-table');
  if (!table) return;
  toast('Trade history loaded — DEX liquidity: 180,000 CCT');
}


//  PROJECT EVALUATION DISPLAY

function renderEvaluation(r, name, scoreColor, recColor) {
  const result = document.getElementById('evaluation-result');
  if (!result) return;
  
  result.innerHTML = `
    <div style="background:var(--bg3);padding:16px;border-radius:6px;margin-bottom:16px;">
      <div style="font-family:var(--mono);font-size:9px;color:var(--text3);">PACT SCORE</div>
      <div style="font-family:var(--display);font-size:56px;color:${scoreColor};line-height:1;">${r.pact_score}</div>
    </div>
    <span class="badge badge-${recColor}" style="font-size:14px;padding:8px 16px;">${r.recommendation}</span>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:16px;">
    <div style="background:var(--bg3);padding:12px;border-radius:4px;">
      <div style="font-family:var(--mono);font-size:10px;color:var(--text3);">ADDITIONALITY</div>
      <div style="font-family:var(--display);font-size:28px;color:var(--green);">${r.additionality}</div>
      <div class="progress-bar"><div class="progress-fill green" style="width:${r.additionality}%"></div></div>
    </div>
    <div style="background:var(--bg3);padding:12px;border-radius:4px;">
      <div style="font-family:var(--mono);font-size:10px;color:var(--text3);">LEAKAGE RISK</div>
      <div style="font-family:var(--display);font-size:28px;color:${r.leakage_risk > 40 ? 'var(--red)' : 'var(--amber)'};">${r.leakage_risk}</div>
      <div class="progress-bar"><div class="progress-fill amber" style="width:${r.leakage_risk}%"></div></div>
    </div>
    <div style="background:var(--bg3);padding:12px;border-radius:4px;">
      <div style="font-family:var(--mono);font-size:10px;color:var(--text3);">PERMANENCE</div>
      <div style="font-family:var(--display);font-size:28px;color:var(--blue);">${r.permanence}</div>
      <div class="progress-bar"><div class="progress-fill blue" style="width:${r.permanence}%"></div></div>
    </div>
  </div>
  <div style="background:var(--bg3);padding:14px;border-radius:4px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
    <div style="font-family:var(--mono);font-size:11px;color:var(--text3);">VERIFIED CO₂ (AI-ADJUSTED)</div>
    <div style="font-family:var(--display);font-size:28px;color:var(--green);">${r.verified_co2.toLocaleString()} tCO₂</div>
  </div>
  <div style="margin-bottom:12px;">
    <div style="font-family:var(--mono);font-size:10px;color:var(--text3);margin-bottom:8px;">KEY FINDINGS</div>
    ${r.key_findings.map(f => `<div style="font-size:12px;color:var(--text2);padding:6px 0;border-bottom:1px solid var(--border);display:flex;gap:8px;"><span style="color:var(--green);">✓</span>${f}</div>`).join('')}
  </div>
  ${r.risk_flags && r.risk_flags.length > 0 ? `<div>
    <div style="font-family:var(--mono);font-size:10px;color:var(--red);margin-bottom:8px;">RISK FLAGS</div>
    ${r.risk_flags.map(f => `<div style="font-size:12px;color:var(--text2);padding:6px 0;display:flex;gap:8px;"><span style="color:var(--red);">⚠</span>${f}</div>`).join('')}
  </div>` : ''}
  <button class="btn btn-green btn-full" style="margin-top:16px;" onclick="toast('${name} submitted for blockchain registration')">
    ${r.recommendation === 'APPROVE' ? '⬡ APPROVE & MINT TOKENS' : '📋 SUBMIT FOR MANUAL REVIEW'}
  </button>`;
}


//  INIT — wire up all buttons

function initUI() {
  // Nav tabs
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', e => showPage(tab.dataset.page, e));
  });

  // Satellite
  const btnRunSat = document.getElementById('btn-run-satellite');
  if (btnRunSat) btnRunSat.addEventListener('click', runSatelliteScan);


  // Blockchain
  const btnAddBlock = document.getElementById('btn-add-block');
  if (btnAddBlock) btnAddBlock.addEventListener('click', addBlock);
  const btnMint = document.getElementById('btn-mint-token');
  if (btnMint) btnMint.addEventListener('click', mintToken);

  // Trading
  const btnTradeBuy  = document.getElementById('trade-buy');
  const btnTradeSell = document.getElementById('trade-sell');
  if (btnTradeBuy)  btnTradeBuy.addEventListener('click',  () => setTradeType('BUY'));
  if (btnTradeSell) btnTradeSell.addEventListener('click', () => setTradeType('SELL'));
  const tradeAmount = document.getElementById('trade-amount');
  const tradePrice  = document.getElementById('trade-price');
  if (tradeAmount) tradeAmount.addEventListener('input', updateTradeCalc);
  if (tradePrice)  tradePrice.addEventListener('input',  updateTradeCalc);
  const btnTradeExecute = document.getElementById('btn-trade-execute');
  if (btnTradeExecute) btnTradeExecute.addEventListener('click', executeTrade);

  // Projects
  const btnShowAddProject = document.getElementById('btn-show-add-project');
  if (btnShowAddProject) btnShowAddProject.addEventListener('click', showAddProject);
  const btnRegisterProject = document.getElementById('btn-register-project');
  if (btnRegisterProject) btnRegisterProject.addEventListener('click', registerProject);
  const btnCancelAddProject = document.getElementById('btn-cancel-add-project');
  if (btnCancelAddProject) btnCancelAddProject.addEventListener('click', () => {
    const f = document.getElementById('add-project-form');
    if (f) f.style.display = 'none';
  });

  // Additionality slider
  const addRange = document.getElementById('proj-additionality');
  if (addRange) addRange.addEventListener('input', e => {
    const addVal = document.getElementById('add-val');
    if (addVal) addVal.textContent = e.target.value;
  });

  // Init static UI
  updateTradeCalc();
  initCharts();

  // Load real data on startup
  loadDashboard();
  startDashboardRefresh();   // auto-refresh dashboard every 30s
  loadWeather();             // also load live weather
}

window.addEventListener('DOMContentLoaded', initUI);

//  FOREST MAP 

let carbonMap       = null;   // Leaflet map instance
let mapMarkers      = [];     // all markers currently on map
let allMapProjects  = [];     // raw project data from backend
let activeFilter    = 'all';  // current filter selection

//Status colors for project markers and badges
const STATUS_COLOR = {
  ACTIVE:     '#22c55e',
  PENDING:    '#38bdf8',
  REVIEW:     '#f59e0b',
  REJECTED:   '#f87171',
  EVALUATING: '#a855f7',
};

function markerColor(project) {
  return STATUS_COLOR[project.status] || '#4a6152';
}

//Build a custom SVG circle marker
function makeMarkerIcon(color, size = 14) {
  return L.divIcon({
    className: '',
    html: `<div style="
      width:${size}px; height:${size}px; border-radius:50%;
      background:${color};
      border:2px solid rgba(255,255,255,0.25);
      box-shadow:0 0 8px ${color}88;
    "></div>`,
    iconSize:   [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

//Build popup HTML for a project
function buildPopup(p) {
  const color  = markerColor(p);
  const badge  = `background:${color}22; border:1px solid ${color}55; color:${color};`;
  const ndvi   = getNdviForProject(p);
  const ndviHtml = ndvi
    ? `<div class="popup-row"><span class="popup-label">NDVI</span><span class="popup-val green">${ndvi}</span></div>`
    : '';

  return `
    <div class="popup-name">${p.name}</div>
    <div class="popup-row"><span class="popup-label">TYPE</span><span class="popup-val">${p.type}</span></div>
    <div class="popup-row"><span class="popup-label">LOCATION</span><span class="popup-val">${p.location}</span></div>
    <div class="popup-row"><span class="popup-label">AREA</span><span class="popup-val">${p.area_ha ? p.area_ha.toLocaleString() + ' ha' : '—'}</span></div>
    <div class="popup-row"><span class="popup-label">CLAIMED CO₂</span><span class="popup-val amber">${p.claimed_co2 ? parseInt(p.claimed_co2).toLocaleString() + ' tCO₂/yr' : '—'}</span></div>
    <div class="popup-row"><span class="popup-label">PACT SCORE</span><span class="popup-val green">${p.pact_score ?? 'Pending eval'}</span></div>
    <div class="popup-row"><span class="popup-label">TOKENS</span><span class="popup-val blue">${p.tokens_issued ? p.tokens_issued.toLocaleString() + ' CCT' : '0 CCT'}</span></div>
    ${ndviHtml}
    <span class="popup-badge" style="${badge}">${p.status}</span>
    <button class="popup-btn" onclick="highlightSidebarCard(${p.id})">View in panel →</button>
  `;
}

// Match NDVI data to a project by proximity
let ndviZones = [];
function getNdviForProject(p) {
  if (!p.lat || !ndviZones.length) return null;
  let best = null, bestDist = 999;
  ndviZones.forEach(z => {
    const d = Math.abs(z.lat - p.lat) + Math.abs(z.lon - p.lon);
    if (d < bestDist) { bestDist = d; best = z; }
  });
  return best && bestDist < 0.08 ? best.ndvi : null;
}

// Initialise Leaflet map
function initMap() {
  if (carbonMap) return; // already initialised

  // Clear any old map instance from the container
  const mapContainer = document.getElementById('carbonchain-map');
  if (mapContainer && mapContainer._leaflet_id) {
    delete mapContainer._leaflet_id;
  }

  carbonMap = L.map('carbonchain-map', {
    center:    [19.15, 72.92],   // Mumbai/Thane centre
    zoom:      11,
    zoomControl: true,
  });

  // OpenStreetMap tiles (free, no API key)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 18,
  }).addTo(carbonMap);

  // Region boundary circle (visual indicator)
  L.circle([19.15, 72.92], {
    radius:    35000,
    color:     '#22c55e',
    fillColor: '#22c55e',
    fillOpacity: 0.04,
    weight:    1,
    dashArray: '6 4',
  }).addTo(carbonMap);
}

// Place markers for a list of projects
function placeMarkers(projects) {
  // Clear existing
  mapMarkers.forEach(m => carbonMap.removeLayer(m));
  mapMarkers = [];

  projects.forEach(p => {
    if (!p.lat || !p.lon) return;

    const marker = L.marker([p.lat, p.lon], {
      icon: makeMarkerIcon(markerColor(p)),
    });

    marker.bindPopup(buildPopup(p), { maxWidth: 260, minWidth: 220 });

    marker.on('click', () => highlightSidebarCard(p.id));

    marker.addTo(carbonMap);
    mapMarkers.push(marker);
  });
}

// Render the sidebar project list
function renderSidebarList(projects) {
  const list = document.getElementById('map-project-list');
  if (!list) return;

  if (!projects.length) {
    list.innerHTML = `<div style="color:var(--text3);font-family:var(--mono);font-size:12px;padding:16px 0;text-align:center;">No projects match this filter</div>`;
    return;
  }

  list.innerHTML = projects.map(p => {
    const color = markerColor(p);
    const ndvi  = getNdviForProject(p);
    const ndviHtml = ndvi ? `
      <div class="map-proj-ndvi">
        <span style="color:var(--text3);">NDVI</span>
        <span style="color:var(--green); margin-left:6px;">${ndvi}</span>
        <div class="ndvi-bar"><div class="ndvi-fill" style="width:${ndvi * 100}%;"></div></div>
      </div>` : '';

    return `
      <div class="map-project-card" id="sidebar-card-${p.id}" onclick="flyToProject(${p.id})">
        <div class="map-proj-name">${p.name}</div>
        <div style="margin-bottom:4px;">
          <span class="badge" style="background:${color}22; border:1px solid ${color}55; color:${color}; font-size:9px;">${p.status}</span>
          <span style="font-family:var(--mono); font-size:10px; color:var(--text3); margin-left:6px;">${p.type}</span>
        </div>
        <div class="map-proj-meta">
          <span>${p.area_ha ? p.area_ha.toLocaleString() + ' ha' : '—'}</span>
          <span>${p.claimed_co2 ? parseInt(p.claimed_co2).toLocaleString() + ' tCO₂' : '—'}</span>
          ${p.pact_score ? `<span style="color:var(--green);">PACT ${p.pact_score}</span>` : ''}
        </div>
        ${ndviHtml}
      </div>`;
  }).join('');
}

// Fly to a project on the map
function flyToProject(projectId) {
  const p = allMapProjects.find(x => x.id === projectId);
  if (!p || !p.lat) return;
  carbonMap.flyTo([p.lat, p.lon], 14, { duration: 1.2 });

  // Open its popup
  const markerIdx = allMapProjects
    .filter(x => x.lat && x.lon)
    .findIndex(x => x.id === projectId);
  if (mapMarkers[markerIdx]) mapMarkers[markerIdx].openPopup();

  highlightSidebarCard(projectId);
}

function highlightSidebarCard(projectId) {
  document.querySelectorAll('.map-project-card').forEach(c => c.classList.remove('highlighted'));
  const card = document.getElementById(`sidebar-card-${projectId}`);
  if (card) {
    card.classList.add('highlighted');
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

// Apply filter
function applyMapFilter(filter) {
  activeFilter = filter;
  document.querySelectorAll('.map-filter-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.filter === filter);
  });

  const filtered = filter === 'all'
    ? allMapProjects
    : allMapProjects.filter(p => p.status === filter || p.type === filter);

  placeMarkers(filtered);
  renderSidebarList(filtered);

  const countEl = document.getElementById('map-project-count');
  if (countEl) countEl.textContent = `${filtered.length} projects`;
}

// Load weather into sidebar
async function loadMapWeather() {
  const el = document.getElementById('weather-content');
  if (!el) return;
  try {
    const res  = await fetch(`${API}/weather/mumbai`);
    const data = await res.json();
    const c    = data.current;
    el.innerHTML = `
      <div class="weather-grid">
        <div class="weather-item">
          <div class="weather-label">Temp</div>
          <div class="weather-value">${c.temperature_c}°C</div>
        </div>
        <div class="weather-item">
          <div class="weather-label">Rain</div>
          <div class="weather-value">${c.precipitation_mm}<span style="font-size:12px;font-family:var(--mono);"> mm</span></div>
        </div>
        <div class="weather-item">
          <div class="weather-label">Wind</div>
          <div class="weather-value">${c.windspeed_kmh}<span style="font-size:12px;font-family:var(--mono);"> km/h</span></div>
        </div>
        <div class="weather-item">
          <div class="weather-label">Humidity</div>
          <div class="weather-value">${c.humidity_pct ?? '—'}<span style="font-size:12px;font-family:var(--mono);">%</span></div>
        </div>
      </div>
      <div style="font-family:var(--mono); font-size:9px; color:var(--text3); margin-top:8px;">// Open-Meteo · Live</div>`;
  } catch (e) {
    el.innerHTML = `<span style="font-family:var(--mono); font-size:11px; color:var(--text3);">Backend offline</span>`;
  }
}

// Load NDVI summary into sidebar 
async function loadMapNdvi() {
  const el = document.getElementById('ndvi-summary');
  if (!el) return;
  try {
    const res  = await fetch(`${API}/ndvi/mumbai`);
    const data = await res.json();
    ndviZones  = data.zones;

    const avg = (data.zones.reduce((s, z) => s + z.ndvi, 0) / data.zones.length).toFixed(2);
    el.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
        <span style="font-family:var(--mono); font-size:10px; color:var(--text3);">AVG NDVI</span>
        <span style="font-family:var(--display); font-size:24px; color:var(--green);">${avg}</span>
      </div>
      ${data.zones.map(z => `
        <div style="margin-bottom:8px;">
          <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:2px;">
            <span style="color:var(--text2);">${z.name.split(' ').slice(0,3).join(' ')}</span>
            <span style="font-family:var(--mono); color:var(--green);">${z.ndvi}</span>
          </div>
          <div class="ndvi-bar"><div class="ndvi-fill" style="width:${z.ndvi * 100}%;"></div></div>
        </div>`).join('')}
      <div style="font-family:var(--mono); font-size:9px; color:var(--text3); margin-top:4px;">// NASA MODIS MOD13Q1</div>`;
  } catch (e) {
    el.innerHTML = `<span style="font-family:var(--mono); font-size:11px; color:var(--text3);">Backend offline</span>`;
  }
}

// Main loader — called when Map tab is clicked
async function loadMapPage() {
  // Step 1: init Leaflet (safe to call multiple times)
  initMap();

  // Step 2: fix Leaflet tile rendering bug when page was hidden
  setTimeout(() => carbonMap.invalidateSize(), 100);

  // Step 3: fetch NDVI first (used inside project cards)
  await loadMapNdvi();

  // Step 4: fetch real projects from backend
  try {
    const res      = await fetch(`${API}/projects`);
    allMapProjects = await res.json();

    const countEl = document.getElementById('map-project-count');
    if (countEl) countEl.textContent = `${allMapProjects.length} projects`;

    applyMapFilter(activeFilter);
    toast(`Map loaded — ${allMapProjects.length} real Mumbai/Thane project locations`);
  } catch (e) {
    // Fallback hardcoded locations if backend offline
    allMapProjects = [
      { id:1, name:'Sanjay Gandhi National Park', type:'Reforestation', location:'Borivali, Mumbai', area_ha:10350, claimed_co2:28000, pact_score:89.2, tokens_issued:24800, status:'ACTIVE',     lat:19.213, lon:72.910 },
      { id:2, name:'Thane Creek Mangroves',        type:'Mangrove',      location:'Thane',            area_ha:1690,  claimed_co2:4800,  pact_score:84.1, tokens_issued:4100,  status:'ACTIVE',     lat:19.074, lon:73.001 },
      { id:3, name:'Aarey Colony Forest',          type:'Reforestation', location:'Goregaon, Mumbai', area_ha:1287,  claimed_co2:3200,  pact_score:78.5, tokens_issued:2700,  status:'ACTIVE',     lat:19.163, lon:72.871 },
      { id:4, name:'Ulhas River Wetlands',         type:'Soil Carbon',   location:'Ambernath, Thane', area_ha:890,   claimed_co2:1900,  pact_score:61.3, tokens_issued:0,     status:'REVIEW',     lat:19.198, lon:73.192 },
      { id:5, name:'Mumbai Coastal Mangroves',     type:'Mangrove',      location:'Bandra-Versova',   area_ha:5142,  claimed_co2:14200, pact_score:null, tokens_issued:0,     status:'PENDING',    lat:19.081, lon:72.836 },
      { id:6, name:'Yeoor Hills Reserve',          type:'Reforestation', location:'Thane West',       area_ha:1820,  claimed_co2:5100,  pact_score:null, tokens_issued:0,     status:'EVALUATING', lat:19.233, lon:73.001 },
    ];
    applyMapFilter(activeFilter);
    toast('Backend offline — showing cached project locations');
  }

  // Step 5: load live weather
  loadMapWeather();
}

// Wire up map filter buttons 
function initMapUI() {
  document.querySelectorAll('.map-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => applyMapFilter(btn.dataset.filter));
  });

  const refreshBtn = document.getElementById('btn-refresh-map');
  if (refreshBtn) refreshBtn.addEventListener('click', () => {
    // Properly dispose of old map instance
    if (carbonMap) {
      carbonMap.remove();
    }
    
    // Reset state
    carbonMap = null;
    allMapProjects = [];
    ndviZones = [];
    document.getElementById('map-project-list').innerHTML = '<div style="color:var(--text3);font-family:var(--mono);font-size:12px;padding:20px 0;text-align:center;">Refreshing...</div>';
    loadMapPage();
  });
}

// Hook map into existing showPage
const _origShowPage = window.showPage;
window.showPage = function(pageId, event) {
  _origShowPage(pageId, event);
  if (pageId === 'map') loadMapPage();
  if (pageId === 'calculator') {
    initCalculator();
    recalcFootprint();
  }
};

// Init map UI buttons on DOM ready
window.addEventListener('DOMContentLoaded', initMapUI);

//  CARBON FOOTPRINT CALCULATOR

// Sector default emission presets
const SECTOR_PRESETS = {
  manufacturing: { scope1: 12400, scope2: 8200,  scope3: 31000 },
  it:            { scope1: 800,   scope2: 4200,  scope3: 9500  },
  finance:       { scope1: 400,   scope2: 2800,  scope3: 6200  },
  retail:        { scope1: 2100,  scope2: 3400,  scope3: 18000 },
  transport:     { scope1: 18000, scope2: 2100,  scope3: 12000 },
  construction:  { scope1: 9800,  scope2: 5600,  scope3: 22000 },
  hospitality:   { scope1: 3200,  scope2: 6100,  scope3: 8400  },
  healthcare:    { scope1: 2800,  scope2: 5200,  scope3: 11000 },
};

let calcDonutChart = null;

// Update sector presets when dropdown changes 
function updateCalcSector() {
  const sector  = document.getElementById('calc-sector')?.value;
  const preset  = SECTOR_PRESETS[sector];
  if (!preset) return;
  document.getElementById('calc-scope1').value = preset.scope1;
  document.getElementById('calc-scope2').value = preset.scope2;
  document.getElementById('calc-scope3').value = preset.scope3;
  recalcFootprint();
}

// Update reduction label
function updateReductionLabel() {
  const val = document.getElementById('calc-reduction')?.value;
  const el  = document.getElementById('calc-reduction-val');
  if (el) el.textContent = val + '%';
}

// Core calculation (runs live as user types)
function recalcFootprint() {
  const s1       = parseFloat(document.getElementById('calc-scope1')?.value) || 0;
  const s2       = parseFloat(document.getElementById('calc-scope2')?.value) || 0;
  const s3       = parseFloat(document.getElementById('calc-scope3')?.value) || 0;
  const redPct   = parseFloat(document.getElementById('calc-reduction')?.value) || 0;
  const total    = s1 + s2 + s3;
  const after    = Math.round(total * (1 - redPct / 100));
  const cct      = after;
  const cost     = cct * 1240;

  // Update summary cards
  const fmt = n => n.toLocaleString('en-IN');
  const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

  setEl('calc-total-display', fmt(total));
  setEl('calc-after-display', fmt(after));
  setEl('calc-cct-display',   fmt(cct));
  setEl('calc-cost-display',  '₹' + (cost >= 1e7 ? (cost/1e7).toFixed(1) + 'Cr' : (cost/1e5).toFixed(1) + 'L'));

  // Update donut chart
  updateCalcChart(s1, s2, s3);
}

// Donut chart
function updateCalcChart(s1, s2, s3) {
  const ctx = document.getElementById('calc-chart');
  if (!ctx) return;

  if (calcDonutChart) {
    calcDonutChart.data.datasets[0].data = [s1, s2, s3];
    calcDonutChart.update();
    return;
  }

  calcDonutChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels:   ['Scope 1 (Direct)', 'Scope 2 (Energy)', 'Scope 3 (Value Chain)'],
      datasets: [{
        data:            [s1, s2, s3],
        backgroundColor: ['#f87171', '#f59e0b', '#38bdf8'],
        borderColor:     ['#0e1610'],
        borderWidth:     3,
        hoverOffset:     6,
      }],
    },
    options: {
      responsive:          true,
      maintainAspectRatio: false,
      cutout:              '68%',
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.label}: ${ctx.parsed.toLocaleString('en-IN')} tCO₂`
          }
        }
      },
    },
  });
}

// AI recommendations (hits Anthropic API) 
async function runCalcAI() {
  const company  = document.getElementById('calc-company')?.value  || 'Company';
  const sector   = document.getElementById('calc-sector')?.value   || 'manufacturing';
  const s1       = parseFloat(document.getElementById('calc-scope1')?.value) || 0;
  const s2       = parseFloat(document.getElementById('calc-scope2')?.value) || 0;
  const s3       = parseFloat(document.getElementById('calc-scope3')?.value) || 0;
  const redPct   = parseFloat(document.getElementById('calc-reduction')?.value) || 0;
  const year     = document.getElementById('calc-year')?.value     || '2030';
  const projType = document.getElementById('calc-proj-type')?.value || 'any';
  const total    = s1 + s2 + s3;
  const after    = Math.round(total * (1 - redPct / 100));

  // Fetch real available projects from backend
  let projectsText = 'No project data available';
  try {
    const res      = await fetch(`${API}/projects`);
    const projects = await res.json();
    const active   = projects.filter(p => p.status === 'ACTIVE');
    projectsText   = active.map(p =>
      `- ${p.name} (${p.type}, PACT: ${p.pact_score}, ${p.tokens_issued?.toLocaleString()} CCT available, ${p.area_ha} ha)`
    ).join('\n');
  } catch (e) {
    projectsText = `- Sanjay Gandhi NP (Reforestation, PACT: 89.2, 24,800 CCT available)
- Thane Creek Mangroves (Mangrove, PACT: 84.1, 4,100 CCT available)
- Aarey Colony Forest (Reforestation, PACT: 78.5, 2,700 CCT available)`;
  }

  // Show loading state
  const btnText   = document.getElementById('calc-btn-text');
  const result    = document.getElementById('calc-ai-result');
  const placeholder = document.getElementById('calc-ai-placeholder');
  if (btnText)     btnText.innerHTML = '<span class="loading-spinner"></span> ANALYSING...';
  if (placeholder) placeholder.style.display = 'none';
  if (result)    { result.style.display = 'block'; result.innerHTML = '<div style="color:var(--text3);font-family:var(--mono);font-size:12px;padding:20px 0;text-align:center;"><span class="loading-spinner"></span><br><br>AI analysing emissions profile...<br>Matching Mumbai/Thane projects...</div>'; }

  const prompt = `You are a carbon offset advisor for the CarbonChain platform (Mumbai/Thane region).

Company: ${company}
Sector: ${sector}
Total emissions: ${total.toLocaleString()} tCO₂/yr
  - Scope 1 (Direct): ${s1.toLocaleString()} tCO₂
  - Scope 2 (Energy): ${s2.toLocaleString()} tCO₂  
  - Scope 3 (Value Chain): ${s3.toLocaleString()} tCO₂
Internal reduction target: ${redPct}% by ${year}
Residual emissions to offset: ${after.toLocaleString()} tCO₂
Preferred project type: ${projType}
CCT price: ₹1,240 per token

Available projects on CarbonChain (Mumbai/Thane):
${projectsText}

Respond ONLY with a JSON object:
{
  "summary": "2-sentence executive summary of their carbon situation",
  "urgency": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "recommended_projects": [
    {
      "name": "project name from the list",
      "cct_to_buy": <number>,
      "cost_inr": <number>,
      "reason": "one sentence why this project fits"
    }
  ],
  "reduction_tips": ["tip1", "tip2", "tip3"],
  "net_zero_year": <year as number>,
  "risk_note": "one sentence on biggest risk if they don't act"
}`;

  try {
    const res  = await fetch('https://api.anthropic.com/v1/messages', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model:      'claude-sonnet-4-20250514',
        max_tokens: 900,
        messages:   [{ role: 'user', content: prompt }],
      }),
    });
    const data  = await res.json();
    const text  = data.content.map(c => c.text || '').join('');
    const clean = text.replace(/```json|```/g, '').trim();
    renderCalcResult(JSON.parse(clean), after, total);
  } catch (e) {
    // Fallback result
    renderCalcResult({
      summary: `${company} has a total carbon footprint of ${total.toLocaleString()} tCO₂/yr. With a ${redPct}% internal reduction target, they need to offset ${after.toLocaleString()} tCO₂ through verified carbon credits.`,
      urgency: after > 20000 ? 'HIGH' : after > 5000 ? 'MEDIUM' : 'LOW',
      recommended_projects: [
        { name: 'Sanjay Gandhi National Park', cct_to_buy: Math.round(after * 0.5), cost_inr: Math.round(after * 0.5 * 1240), reason: 'Highest PACT score (89.2) ensures maximum credit quality and regulatory compliance.' },
        { name: 'Thane Creek Mangroves',       cct_to_buy: Math.round(after * 0.3), cost_inr: Math.round(after * 0.3 * 1240), reason: 'Mangrove credits offer strong co-benefits including biodiversity and coastal protection.' },
        { name: 'Aarey Colony Forest',         cct_to_buy: Math.round(after * 0.2), cost_inr: Math.round(after * 0.2 * 1240), reason: 'Local Mumbai project with strong community support and media visibility.' },
      ],
      reduction_tips: [
        'Switch to renewable energy procurement to eliminate Scope 2 emissions',
        'Implement supplier emissions reporting to quantify and reduce Scope 3',
        'Electrify company vehicle fleet to cut Scope 1 transport emissions',
      ],
      net_zero_year: parseInt(year),
      risk_note: 'Delayed action risks regulatory non-compliance under India\'s Carbon Credit Trading Scheme (CCTS) framework.',
    }, after, total);
  }

  if (btnText) btnText.innerHTML = '▶ CALCULATE & GET AI RECOMMENDATIONS';
}

// Render AI result
function renderCalcResult(r, after, total) {
  const result = document.getElementById('calc-ai-result');
  if (!result) return;

  const urgencyColor = { LOW: 'green', MEDIUM: 'amber', HIGH: 'red', CRITICAL: 'red' };
  const uColor = urgencyColor[r.urgency] || 'amber';

  const projectsHtml = r.recommended_projects.map(p => `
    <div class="calc-project-match" onclick="toast('${p.name} — ${p.cct_to_buy?.toLocaleString()} CCT selected')">
      <div class="calc-project-match-name">${p.name}</div>
      <div class="calc-project-match-row"><span>CCT to buy</span><span style="color:var(--green);">${p.cct_to_buy?.toLocaleString()}</span></div>
      <div class="calc-project-match-row"><span>Cost</span><span style="color:var(--amber);">₹${p.cost_inr?.toLocaleString('en-IN')}</span></div>
      <div style="font-size:11px; color:var(--text3); margin-top:6px; line-height:1.5;">${p.reason}</div>
    </div>`).join('');

  const tipsHtml = r.reduction_tips.map(t => `
    <div style="font-size:12px; color:var(--text2); padding:6px 0; border-bottom:1px solid var(--border); display:flex; gap:8px; line-height:1.5;">
      <span style="color:var(--green); flex-shrink:0;">→</span>${t}
    </div>`).join('');

  // Pathway breakdown
  const s1 = parseFloat(document.getElementById('calc-scope1')?.value) || 0;
  const s2 = parseFloat(document.getElementById('calc-scope2')?.value) || 0;
  const s3 = parseFloat(document.getElementById('calc-scope3')?.value) || 0;

  result.innerHTML = `
    <!-- Urgency + summary -->
    <div style="display:flex; align-items:flex-start; gap:12px; margin-bottom:16px; padding-bottom:16px; border-bottom:1px solid var(--border);">
      <span class="badge badge-${uColor}" style="flex-shrink:0; margin-top:2px;">${r.urgency} URGENCY</span>
      <div style="font-size:13px; color:var(--text2); line-height:1.6;">${r.summary}</div>
    </div>

    <!-- Emission pathway -->
    <div style="font-family:var(--mono); font-size:10px; color:var(--text3); letter-spacing:2px; margin-bottom:10px;">// EMISSION PATHWAY</div>
    <div class="calc-pathway">
      <div class="calc-pathway-row">
        <span class="calc-pathway-label">Scope 1</span>
        <div class="calc-pathway-bar-wrap"><div class="calc-pathway-fill" style="width:${(s1/total*100).toFixed(0)}%; background:#f87171;"></div></div>
        <span class="calc-pathway-val">${s1.toLocaleString()}</span>
      </div>
      <div class="calc-pathway-row">
        <span class="calc-pathway-label">Scope 2</span>
        <div class="calc-pathway-bar-wrap"><div class="calc-pathway-fill" style="width:${(s2/total*100).toFixed(0)}%; background:#f59e0b;"></div></div>
        <span class="calc-pathway-val">${s2.toLocaleString()}</span>
      </div>
      <div class="calc-pathway-row">
        <span class="calc-pathway-label">Scope 3</span>
        <div class="calc-pathway-bar-wrap"><div class="calc-pathway-fill" style="width:${(s3/total*100).toFixed(0)}%; background:#38bdf8;"></div></div>
        <span class="calc-pathway-val">${s3.toLocaleString()}</span>
      </div>
      <div class="calc-pathway-row" style="margin-top:4px; padding-top:8px; border-top:1px solid var(--border);">
        <span class="calc-pathway-label" style="color:var(--green);">To offset</span>
        <div class="calc-pathway-bar-wrap"><div class="calc-pathway-fill" style="width:${(after/total*100).toFixed(0)}%; background:#22c55e;"></div></div>
        <span class="calc-pathway-val" style="color:var(--green);">${after.toLocaleString()}</span>
      </div>
    </div>

    <!-- Recommended projects -->
    <div style="font-family:var(--mono); font-size:10px; color:var(--text3); letter-spacing:2px; margin:16px 0 10px;">// RECOMMENDED PROJECTS</div>
    ${projectsHtml}

    <!-- Reduction tips -->
    <div style="font-family:var(--mono); font-size:10px; color:var(--text3); letter-spacing:2px; margin:16px 0 10px;">// INTERNAL REDUCTION TIPS</div>
    ${tipsHtml}

    <!-- Risk note -->
    <div style="background:rgba(25, 17, 17, 0.08); border:1px solid rgba(248,113,113,0.2); border-radius:6px; padding:12px 14px; margin-top:16px;">
      <div style="font-family:var(--mono); font-size:10px; color:var(--red); margin-bottom:4px;">⚠ RISK</div>
      <div style="font-size:12px; color:var(--text2);">${r.risk_note}</div>
    </div>

    <!-- Net zero target -->
    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:16px; padding:14px; background:var(--bg3); border-radius:6px;">
      <span style="font-family:var(--mono); font-size:11px; color:var(--text3);">NET ZERO TARGET</span>
      <span style="font-family:var(--display); font-size:32px; color:var(--green);">${r.net_zero_year}</span>
    </div>

    <!-- Buy now button -->
    <button class="btn btn-green btn-full" style="margin-top:16px;"
      onclick="toast('Offset order placed — ${after?.toLocaleString()} CCT purchase initiated')">
      ⬡ PURCHASE OFFSET CREDITS ON DEX
    </button>`;
}

// Initialise calculator on page load
function initCalculator() {
  // Wire up sector dropdown
  const sectorEl = document.getElementById('calc-sector');
  if (sectorEl) sectorEl.addEventListener('change', updateCalcSector);

  // Wire up all inputs for live recalc
  ['calc-scope1','calc-scope2','calc-scope3','calc-reduction','calc-year'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', recalcFootprint);
  });

  // Initial calculation
  recalcFootprint();
}

// Also init if page loads directly on calculator tab
window.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('page-calculator')) initCalculator();
});
