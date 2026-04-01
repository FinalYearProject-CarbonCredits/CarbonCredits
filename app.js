// Navigation
function showPage(pageId, event) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  const page = document.getElementById('page-' + pageId);
  if (!page) return;
  page.classList.add('active');
  if (event && event.currentTarget) {
    event.currentTarget.classList.add('active');
  } else if (pageId) {
    const tab = document.querySelector(`.nav-tab[data-page="${pageId}"]`);
    if (tab) tab.classList.add('active');
  }
  if (pageId === 'blockchain' && !chainsRendered) renderChain();
  if (pageId === 'satellite') renderSatGrid();
}

// Toast
function toast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = '// ' + msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

// charts
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

const days = Array.from({length:30}, (_,i) => `D${i+1}`);
const genData = (base, noise) => days.map(() => base + (Math.random()-0.4)*noise);

function initCharts() {
  makeLineChart('chart-issuance', days, [
    { data: genData(80000, 30000), borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.08)', fill: true, borderWidth: 1.5 },
    { data: genData(30000, 15000), borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,0.06)', fill: true, borderWidth: 1.5 }
  ]);
  makeLineChart('chart-price', days, [
    { data: genData(1180, 80), borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.08)', fill: true, borderWidth: 1.5 }
  ]);
}

// Live feed
const feedItems = [
  ['green', 'Sundarbans — 1,200 tCO₂ batch verified', '// NDVI scan complete'],
  ['blue', 'TKN#4831 retired by Infosys', '// 200 CCT offset'],
  ['amber', 'Odisha Mangroves — AI evaluation queued', '// Pending scan data'],
  ['green', 'New project PKT-007 registered — Kerala', '// Solar + reforestation'],
  ['red', 'Anomaly detected — PKT-008 baseline mismatch', '// Manual review'],
  ['blue', 'DEX pool rebalanced — 5,000 CCT added', '// Pool B liquidity'],
  ['green', 'PACT score updated — Gujarat Wind: 87.4', '// Annual review complete']
];
let feedIdx = 0;
setInterval(() => {
  const feed = document.getElementById('live-feed');
  if (!feed) return;
  const item = feedItems[feedIdx % feedItems.length];
  feedIdx++;
  const el = document.createElement('div');
  el.className = 'feed-item';
  el.style.animation = 'fadeIn 0.3s';
  el.innerHTML = `<div class="feed-dot ${item[0]}"></div><div class="feed-text">${item[1]} <span>${item[2]}</span></div><div class="feed-time">now</div>`;
  feed.insertBefore(el, feed.firstChild);
  if (feed.children.length > 8) feed.removeChild(feed.lastChild);
}, 5000);

// Satellite grid
function renderSatGrid() {
  const grid = document.getElementById('sat-grid');
  if (!grid || grid.children.length > 0) return;
  const sats = [
    { name: 'Sundarbans', ndvi: 0.82, color: '#22c55e' },
    { name: 'W. Ghats', ndvi: 0.79, color: '#22c55e' },
    { name: 'Bihar Wetlands', ndvi: 0.51, color: '#f59e0b' },
    { name: 'Gujarat Wind', ndvi: 0.12, color: '#38bdf8' },
    { name: 'Rajasthan', ndvi: 0.08, color: '#f87171' },
    { name: 'Odisha Coast', ndvi: 0.71, color: '#22c55e' }
  ];
  sats.forEach(s => {
    const g = Math.floor(s.ndvi * 80 + 20);
    const r = Math.floor((1 - s.ndvi) * 60);
    const div = document.createElement('div');
    div.className = 'sat-img';
    div.onclick = () => toast(`${s.name} — NDVI: ${s.ndvi} — Biomass scan complete`);
    div.innerHTML = `
      <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        ${Array.from({ length: 200 }, () => `<circle cx="${Math.random()*100}" cy="${Math.random()*100}" r="${Math.random()*2+0.5}" fill="rgb(${r},${g},${Math.floor(Math.random()*40)})" opacity="${Math.random()*0.8+0.2}"/>`).join('')}
        <rect x="0" y="0" width="100" height="100" fill="none" stroke="${s.color}" stroke-width="0.5" opacity="0.3"/>
      </svg>
      <div class="sat-label">${s.name}</div>
      <div class="sat-score"><span class="badge badge-green" style="font-size:9px;">NDVI ${s.ndvi}</span></div>`;
    grid.appendChild(div);
  });
}

// Blockchain
let chainsRendered = false;
let blockHeight = 28492;
const blocks = [
  { num: 28488, hash: 'a4f9...c21e', data: 'MINT 3,400 CCT\nPKT-001 · 91.2 PACT' },
  { num: 28489, hash: 'b7d2...8f31', data: 'TRANSFER 2,000 CCT\nDEX Pool B' },
  { num: 28490, hash: 'c1a8...5d9a', data: 'MINT 1,800 CCT\nPKT-002 · 87.4 PACT' },
  { num: 28491, hash: 'd3f4...2b7c', data: 'RETIRE 500 CCT\nTata Steel offset' },
  { num: 28492, hash: 'e9c6...4f12', data: 'MINT 1,200 CCT\nPKT-001 · 91.2 PACT' }
];

function renderChain() {
  chainsRendered = true;
  const chain = document.getElementById('chain-display');
  if (!chain) return;
  chain.innerHTML = '';
  blocks.forEach((b, i) => {
    if (i > 0) {
      const arrow = document.createElement('div');
      arrow.className = 'block-arrow';
      arrow.textContent = '←';
      chain.appendChild(arrow);
    }
    const block = document.createElement('div');
    block.className = 'block';
    if (i === blocks.length - 1) block.style.borderColor = 'var(--green)';
    block.innerHTML = `<div class="block-num">#${b.num}</div><div class="block-hash">${b.hash}</div><div class="block-data">${b.data.replace('\n','<br>')}</div>`;
    block.onclick = () => toast(`Block #${b.num} — Hash: ${b.hash}`);
    chain.appendChild(block);
  });
}

function addBlock() {
  blockHeight++;
  document.getElementById('chain-height').textContent = blockHeight.toLocaleString();
  const types = ['MINT', 'TRANSFER', 'RETIRE'];
  const type = types[Math.floor(Math.random()*3)];
  const amt = Math.floor(Math.random()*3000 + 200);
  const hash = Math.random().toString(36).substr(2,4) + '...' + Math.random().toString(36).substr(2,4);
  blocks.push({ num: blockHeight, hash, data: `${type} ${amt} CCT\nPKT-00${Math.ceil(Math.random()*6)}` });
  if (blocks.length > 6) blocks.shift();
  if (chainsRendered) renderChain();
  const chain = document.getElementById('chain-display');
  if (chain) chain.scrollLeft = chain.scrollWidth;
  toast(`Block #${blockHeight} added — ${type} ${amt} CCT`);
}

function mintToken() {
  const proj = document.getElementById('mint-project').value;
  const amt = document.getElementById('mint-amount').value;
  const pact = document.getElementById('mint-pact').value;
  if (!proj || !amt) { toast('Please fill all fields'); return; }
  blockHeight++;
  document.getElementById('chain-height').textContent = blockHeight.toLocaleString();
  toast(`Minted ${amt} CCT for ${proj} — PACT: ${pact} — Block #${blockHeight}`);
  addBlock();
}

// AI EVALUATION
async function runEvaluation() {
  const btnText = document.getElementById('eval-btn-text');
  const output = document.getElementById('eval-output');
  const placeholder = document.getElementById('eval-placeholder');
  const name = document.getElementById('proj-name').value;
  const type = document.getElementById('proj-type').value;
  const area = document.getElementById('proj-area').value;
  const co2 = document.getElementById('proj-co2').value;
  const baseline = document.getElementById('proj-baseline').value;

  btnText.innerHTML = '<span class="loading-spinner"></span> EVALUATING...';
  placeholder.style.display = 'none';
  output.style.display = 'block';
  output.innerHTML = '<div style="color:var(--text3); font-family:var(--mono); font-size:12px; padding:20px 0; text-align:center;"><span class="loading-spinner"></span><br><br>AI evaluation running...<br>Satellite data · NDVI analysis · Baseline comparison</div>';

  const prompt = `You are a carbon credit PACT evaluator. Evaluate this project and give a structured assessment:\n\nProject: ${name}\nType: ${type}\nArea: ${area} hectares\nClaimed CO₂: ${co2} tCO₂/yr\nBaseline: ${baseline}\n\nProvide a JSON response ONLY with this structure:\n{\n  \"pact_score\": <0-100 number>,\n  \"additionality\": <0-100>,\n  \"leakage_risk\": <0-100, higher = more risk>,\n  \"permanence\": <0-100>,\n  \"verified_co2\": <adjusted tCO₂ estimate as number>,\n  \"recommendation\": \"APPROVE\" or \"REVIEW\" or \"REJECT\",\n  \"key_findings\": [\"finding1\",\"finding2\",\"finding3\"],\n  \"risk_flags\": [\"flag1\"] or []\n}`;

  try {
    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 800,
        messages: [{ role: 'user', content: prompt }]
      })
    });
    const data = await res.json();
    const text = data.content.map(c => c.text || '').join('');
    const clean = text.replace(/```json|```/g, '').trim();
    const result = JSON.parse(clean);
    renderEvalResult(result, name);
  } catch(e) {
    const score = Math.floor(Math.random() * 35 + 55);
    renderEvalResult({
      pact_score: score,
      additionality: Math.floor(Math.random()*30+60),
      leakage_risk: Math.floor(Math.random()*30+10),
      permanence: Math.floor(Math.random()*30+60),
      verified_co2: Math.floor(parseInt(co2) * (0.65 + Math.random()*0.3)),
      recommendation: score > 75 ? 'APPROVE' : score > 55 ? 'REVIEW' : 'REJECT',
      key_findings: ['Baseline scenario is plausible and well-documented','Additionality case supported by regional land-use data','Permanence requires monitoring agreement verification'],
      risk_flags: score < 70 ? ['Leakage buffer adjustment recommended'] : []
    }, name);
  }
  btnText.innerHTML = '▶ RUN AI EVALUATION';
}

function renderEvalResult(r, name) {
  const output = document.getElementById('eval-output');
  const recColor = r.recommendation === 'APPROVE' ? 'green' : r.recommendation === 'REVIEW' ? 'amber' : 'red';
  const scoreColor = r.pact_score >= 75 ? 'var(--green)' : r.pact_score >= 55 ? 'var(--amber)' : 'var(--red)';

  output.innerHTML = `
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:20px; padding-bottom:16px; border-bottom:1px solid var(--border);">
      <div>
        <div style="font-family:var(--mono); font-size:11px; color:var(--text3);">PACT SCORE</div>
        <div style="font-family:var(--display); font-size:56px; color:${scoreColor}; line-height:1;">${r.pact_score}</div>
      </div>
      <span class="badge badge-${recColor}" style="font-size:14px; padding:8px 16px;">${r.recommendation}</span>
    </div>

    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; margin-bottom:16px;">
      <div style="background:var(--bg3); padding:12px; border-radius:4px;">
        <div style="font-family:var(--mono); font-size:10px; color:var(--text3);">ADDITIONALITY</div>
        <div style="font-family:var(--display); font-size:28px; color:var(--green);">${r.additionality}</div>
        <div class="progress-bar"><div class="progress-fill green" style="width:${r.additionality}%"></div></div>
      </div>
      <div style="background:var(--bg3); padding:12px; border-radius:4px;">
        <div style="font-family:var(--mono); font-size:10px; color:var(--text3);">LEAKAGE RISK</div>
        <div style="font-family:var(--display); font-size:28px; color:${r.leakage_risk > 40 ? 'var(--red)' : 'var(--amber)'};">${r.leakage_risk}</div>
        <div class="progress-bar"><div class="progress-fill amber" style="width:${r.leakage_risk}%"></div></div>
      </div>
      <div style="background:var(--bg3); padding:12px; border-radius:4px;">
        <div style="font-family:var(--mono); font-size:10px; color:var(--text3);">PERMANENCE</div>
        <div style="font-family:var(--display); font-size:28px; color:var(--blue);">${r.permanence}</div>
        <div class="progress-bar"><div class="progress-fill blue" style="width:${r.permanence}%"></div></div>
      </div>
    </div>

    <div style="background:var(--bg3); padding:14px; border-radius:4px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;">
      <div style="font-family:var(--mono); font-size:11px; color:var(--text3);">VERIFIED CO₂ (AI-ADJUSTED)</div>
      <div style="font-family:var(--display); font-size:28px; color:var(--green);">${r.verified_co2.toLocaleString()} tCO₂</div>
    </div>

    <div style="margin-bottom:12px;">
      <div style="font-family:var(--mono); font-size:10px; color:var(--text3); margin-bottom:8px;">KEY FINDINGS</div>
      ${r.key_findings.map(f => `<div style="font-size:12px; color:var(--text2); padding:6px 0; border-bottom:1px solid var(--border); display:flex; gap:8px;"><span style="color:var(--green);">✓</span>${f}</div>`).join('')}
    </div>

    ${r.risk_flags && r.risk_flags.length > 0 ? `<div>
      <div style="font-family:var(--mono); font-size:10px; color:var(--red); margin-bottom:8px;">RISK FLAGS</div>
      ${r.risk_flags.map(f => `<div style="font-size:12px; color:var(--text2); padding:6px 0; display:flex; gap:8px;"><span style="color:var(--red);">⚠</span>${f}</div>`).join('')}
    </div>` : ''}

    <button class="btn btn-green btn-full" style="margin-top:16px;" onclick="toast('${name} submitted for blockchain registration')">
      ${r.recommendation === 'APPROVE' ? '⬡ APPROVE & MINT TOKENS' : '📋 SUBMIT FOR MANUAL REVIEW'}
    </button>`;
}

// Trading
let tradeType = 'BUY';
function setTradeType(t) {
  tradeType = t;
  const buy = document.getElementById('trade-buy');
  const sell = document.getElementById('trade-sell');
  if (!buy || !sell) return;
  if (t === 'BUY') {
    buy.style.background = 'var(--green-glow)'; buy.style.color = 'var(--green)';
    sell.style.background = 'transparent'; sell.style.color = 'var(--text3)';
  } else {
    sell.style.background = 'rgba(248,113,113,0.1)'; sell.style.color = 'var(--red)';
    buy.style.background = 'transparent'; buy.style.color = 'var(--text3)';
  }
}

function updateTradeCalc() {
  const amt = parseFloat(document.getElementById('trade-amount').value) || 0;
  const price = parseFloat(document.getElementById('trade-price').value) || 0;
  const sub = amt * price;
  const fee = sub * 0.003;
  const total = sub + fee;
  document.getElementById('trade-subtotal').textContent = '₹' + Math.round(sub).toLocaleString('en-IN');
  document.getElementById('trade-fee').textContent = '₹' + Math.round(fee).toLocaleString('en-IN');
  document.getElementById('trade-total').textContent = '₹' + Math.round(total).toLocaleString('en-IN');
}

function executeTrade() {
  const amt = document.getElementById('trade-amount').value;
  const price = document.getElementById('trade-price').value;
  toast(`${tradeType} order: ${amt} CCT @ ₹${price} — Submitted to DEX`);
}

// Projects
function showAddProject() {
  const f = document.getElementById('add-project-form');
  if (!f) return;
  f.style.display = f.style.display === 'none' ? 'block' : 'none';
}

function registerProject() {
  const name = document.getElementById('new-proj-name').value;
  const type = document.getElementById('new-proj-type').value;
  const loc = document.getElementById('new-proj-loc').value;
  const area = document.getElementById('new-proj-area').value;
  const co2 = document.getElementById('new-proj-co2').value;
  if (!name || !loc || !area || !co2) { toast('Please fill all required fields'); return; }
  const table = document.getElementById('projects-table');
  const id = 'PKT-00' + (table.children.length + 1);
  const row = document.createElement('tr');
  row.innerHTML = `<td>${name}<div class="mono">${id} | 2024-2044</div></td><td>${type}</td><td>${loc}</td><td>${area} ha</td><td>${parseInt(co2).toLocaleString()}</td><td style="color:var(--text3);font-family:var(--mono);">—</td><td style="color:var(--text3);font-family:var(--mono);">0</td><td><span class="badge badge-blue">PENDING</span></td>`;
  row.onclick = () => toast(`${name} — Awaiting satellite scan and AI evaluation`);
  table.appendChild(row);
  document.getElementById('add-project-form').style.display = 'none';
  toast(`Project "${name}" registered as ${id} — Queued for AI evaluation`);
  ['new-proj-name','new-proj-loc','new-proj-area','new-proj-co2','new-proj-org'].forEach(id => document.getElementById(id).value = '');
}

function runSatelliteScan() {
  toast('New satellite scan queued — Sentinel-2 tasked for 6 project areas');
}

// AI Advisor Chat
const conversationHistory = [];
const systemPrompt = `You are CarbonChain AI Advisor, an expert assistant for a digital carbon credit platform. You have deep knowledge of:
- PACT methodology (Permanence, Additionality, Leakage, Co-benefits, Transparency)
- Voluntary and compliance carbon markets
- Indian Carbon Market (ICM) framework under Energy Conservation Amendment Act 2022
- Blockchain-based carbon registries and tokenization
- Satellite-based verification (NDVI, biomass, land-cover change detection)
- Carbon credit quality standards (Verra VCS, Gold Standard, ART TREES)
- The University of Cambridge "Global, Robust and Comparable Digital Carbon Assets" research (2024)
- Corporate net-zero strategies and carbon offsetting

The CarbonChain platform uses: satellite data (Sentinel-2, Landsat-9, MODIS), AI evaluation (PACT scoring), blockchain registry (ERC-20 CCT tokens, PoS chain), DEX trading, and regulatory API integration.

Be concise, expert, and practical. Use data and examples from the platform context where relevant.`;

async function sendMsg() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  appendMsg('user', msg);
  conversationHistory.push({ role: 'user', content: msg });
  appendTyping();

  try {
    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 1000,
        system: systemPrompt,
        messages: conversationHistory
      })
    });
    const data = await res.json();
    const reply = data.content.map(c => c.text || '').join('');
    removeTyping();
    appendMsg('ai', reply);
    conversationHistory.push({ role: 'assistant', content: reply });
  } catch(e) {
    removeTyping();
    appendMsg('ai', 'I apologize — there was a connection issue. Please check your network and try again. In the meantime, I can tell you that the PACT methodology evaluates carbon projects on four key dimensions: Permanence (will the carbon stay sequestered?), Additionality (would it have happened anyway?), Leakage (does it just move emissions elsewhere?), and Co-benefits (positive social/biodiversity impacts).');
  }
}

function quickAsk(msg) {
  const input = document.getElementById('chat-input');
  input.value = msg;
  sendMsg();
}

function appendMsg(role, text) {
  const msgs = document.getElementById('chat-msgs');
  const div = document.createElement('div');
  div.className = `chat-msg ${role}`;
  const formatted = text.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  div.innerHTML = `<div class="msg-bubble">${formatted}</div><div class="msg-meta">${role === 'user' ? 'You' : 'CarbonChain AI · Claude'} · just now</div>`;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function appendTyping() {
  const msgs = document.getElementById('chat-msgs');
  const div = document.createElement('div');
  div.className = 'chat-msg ai';
  div.id = 'typing-indicator';
  div.innerHTML = `<div class="msg-bubble"><div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div></div>`;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function removeTyping() {
  const t = document.getElementById('typing-indicator');
  if (t) t.remove();
}

function initUI() {
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', e => showPage(tab.dataset.page, e));
  });

  const btnRunSat = document.getElementById('btn-run-satellite');
  if (btnRunSat) btnRunSat.addEventListener('click', runSatelliteScan);

  const btnRunEvalHeader = document.getElementById('btn-run-eval-header');
  const btnRunEvalFooter = document.getElementById('btn-run-eval-footer');
  if (btnRunEvalHeader) btnRunEvalHeader.addEventListener('click', runEvaluation);
  if (btnRunEvalFooter) btnRunEvalFooter.addEventListener('click', runEvaluation);

  const btnAddBlock = document.getElementById('btn-add-block');
  if (btnAddBlock) btnAddBlock.addEventListener('click', addBlock);

  const btnMint = document.getElementById('btn-mint-token');
  if (btnMint) btnMint.addEventListener('click', mintToken);

  const btnTradeBuy = document.getElementById('trade-buy');
  const btnTradeSell = document.getElementById('trade-sell');
  if (btnTradeBuy) btnTradeBuy.addEventListener('click', () => setTradeType('BUY'));
  if (btnTradeSell) btnTradeSell.addEventListener('click', () => setTradeType('SELL'));

  const tradeAmount = document.getElementById('trade-amount');
  const tradePrice = document.getElementById('trade-price');
  if (tradeAmount) tradeAmount.addEventListener('input', updateTradeCalc);
  if (tradePrice) tradePrice.addEventListener('input', updateTradeCalc);

  const btnTradeExecute = document.getElementById('btn-trade-execute');
  if (btnTradeExecute) btnTradeExecute.addEventListener('click', executeTrade);

  const btnShowAddProject = document.getElementById('btn-show-add-project');
  if (btnShowAddProject) btnShowAddProject.addEventListener('click', showAddProject);

  const btnRegisterProject = document.getElementById('btn-register-project');
  if (btnRegisterProject) btnRegisterProject.addEventListener('click', registerProject);

  const btnCancelAddProject = document.getElementById('btn-cancel-add-project');
  if (btnCancelAddProject) btnCancelAddProject.addEventListener('click', () => {
    const f = document.getElementById('add-project-form');
    if (f) f.style.display = 'none';
  });

  const addRange = document.getElementById('proj-additionality');
  if (addRange) {
    addRange.addEventListener('input', e => {
      const addVal = document.getElementById('add-val');
      if (addVal) addVal.textContent = e.target.value;
    });
  }

  document.querySelectorAll('[data-quick]').forEach(btn => {
    btn.addEventListener('click', () => quickAsk(btn.dataset.quick));
  });

  const inputChat = document.getElementById('chat-input');
  if (inputChat) {
    inputChat.addEventListener('keydown', event => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMsg();
      }
    });
  }

  const btnChatSend = document.getElementById('btn-chat-send');
  if (btnChatSend) btnChatSend.addEventListener('click', sendMsg);

  updateTradeCalc();
  initCharts();
}

window.addEventListener('DOMContentLoaded', initUI);
