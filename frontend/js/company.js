const user = requireRole('company');
if (!user) throw new Error('unauthorized');

document.getElementById('nav-user').textContent = `${user.full_name} · Company`;

let map, markers = [];

async function loadListings() {
  const res = await apiFetch('/company/available-landowners');
  const data = await res.json();
  const el = document.getElementById('listings');

  if (!data.count) {
    el.innerHTML = '<span style="color:var(--text3);font-family:var(--mono);font-size:12px;">No KYC-verified landowners available yet.</span>';
    return;
  }

  el.innerHTML = data.landowners.map(item => `
    <div class="listing-card" id="listing-${item.listing_id}">
      <h3>${item.land.title}</h3>
      <div style="font-family:var(--mono);font-size:10px;color:var(--green);margin-bottom:8px;">
        KYC VERIFIED · ${item.owner.full_name}${item.owner.organization ? ' · ' + item.owner.organization : ''}
      </div>
      <div style="font-size:13px;color:var(--text2);">
        ${item.land.location_label || ''} · <strong>${item.land.area_ha} ha</strong> (verified boundary)<br>
        Survey ${item.land.survey_number || '—'} / Plot ${item.land.plot_number || '—'} · ${item.land.village || ''}
      </div>
      <div style="margin-top:12px;padding:12px;background:var(--bg3);border-radius:8px;">
        <div style="font-family:var(--mono);font-size:10px;color:var(--text3);">LEASE TERMS</div>
        <div style="font-size:14px;margin-top:4px;">
          Duration: <strong style="color:var(--amber)">${item.lease.duration_years} years</strong>
          · Type: ${item.lease.type.replace(/_/g, ' ')}
        </div>
        <div style="font-family:var(--mono);font-size:11px;color:var(--green);margin-top:8px;">
          ${item.carbon_potential.preliminary_only === false ? 'Verified' : 'Net creditable est.'}
          ${item.carbon_potential.estimated_annual_credits_tco2 || '—'} tCO₂e/yr
          · Total ~${item.carbon_potential.estimated_total_credits_tco2 || '—'} tCO₂e
        </div>
        ${item.issuance ? `<div style="margin-top:8px;"><span class="issuance-status ${item.issuance.status}">${item.issuance.status.replace(/_/g, ' ')}</span>
          ${item.issuance.registry_label ? ' · ' + item.issuance.registry_label : ''}
          ${item.issuance.methodology ? ' · ' + item.issuance.methodology : ''}
          ${item.issuance.registry_serial_number ? '<div style="font-family:var(--mono);font-size:10px;margin-top:4px;">Serial: ' + item.issuance.registry_serial_number + '</div>' : ''}
        </div>` : '<div style="margin-top:8px;"><span class="issuance-status NOT_SUBMITTED">PRELIMINARY ONLY</span></div>'}
      </div>
      ${item.notes ? `<div style="font-size:12px;color:var(--text3);margin-top:8px;">${item.notes}</div>` : ''}
      <button class="btn btn-green" style="margin-top:12px;" onclick="openInquiry(${item.listing_id}, ${item.lease.duration_years})">
        Express Lease Interest
      </button>
    </div>
  `).join('');

  initMap(data.landowners);
}

window.openInquiry = (listingId, defaultYears) => {
  const msg = prompt('Message to landowner (min 10 chars):', 'We are interested in leasing this land for a carbon project.');
  if (!msg || msg.length < 10) return toast('Message too short');
  const years = prompt('Proposed lease duration (years):', String(defaultYears));
  submitInquiry(listingId, msg, years ? parseInt(years) : null);
};

async function submitInquiry(listingId, message, proposedYears) {
  try {
    const res = await apiFetch('/company/inquiries', {
      method: 'POST',
      body: JSON.stringify({
        listing_id: listingId,
        message,
        proposed_lease_years: proposedYears,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Inquiry failed');
    toast(data.message);
    loadMyInquiries();
  } catch (e) { toast(e.message); }
}

async function loadMyInquiries() {
  const res = await apiFetch('/company/inquiries');
  const data = await res.json();
  const el = document.getElementById('my-inquiries');
  if (!el) return;
  if (!data.count) {
    el.innerHTML = '<span style="color:var(--text3);font-family:var(--mono);font-size:12px;">No inquiries sent yet</span>';
    return;
  }
  el.innerHTML = data.inquiries.map(i => `
    <div class="listing-card">
      <h3>${i.listing_title || 'Listing #' + i.listing_id}</h3>
      <div style="font-family:var(--mono);font-size:10px;color:var(--amber);">${i.status}</div>
      <div style="font-size:12px;margin-top:6px;">${i.message}</div>
      ${i.landowner_response ? '<div style="font-size:12px;color:var(--green);margin-top:8px;">Response: ' + i.landowner_response + '</div>' : ''}
      ${i.status === 'ACCEPTED' ? `
        <div style="margin-top:12px;">
          <button class="btn btn-outline" onclick="toggleMessages(${i.id})">💬 Messages</button>
          <div id="msgs-${i.id}" style="display:none;margin-top:8px;">
            <div class="chat-thread"></div>
            <div class="chat-input-row">
              <input class="form-input" id="msg-input-${i.id}" placeholder="Type a message..." onkeydown="if(event.key==='Enter')sendMsgCompany(${i.id})">
              <button class="btn btn-green" onclick="sendMsgCompany(${i.id})">Send</button>
            </div>
          </div>
        </div>` : ''}
    </div>`).join('');
}

function initMap(landowners) {
  if (!map) {
    map = L.map('company-map').setView([19.15, 72.92], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18 }).addTo(map);
  }
  markers.forEach(m => map.removeLayer(m));
  markers = [];
  landowners.forEach(item => {
    const m = L.marker([item.land.lat, item.land.lon])
      .bindPopup(`<b>${item.land.title}</b><br>${item.owner.full_name}<br>Lease: ${item.lease.duration_years} yrs`)
      .addTo(map);
    markers.push(m);
  });
}

loadListings();
loadMyInquiries();

// ── Contracts ──
async function loadContracts() {
  const el = document.getElementById('my-contracts');
  if (!el) return;
  const res = await apiFetch('/company/contracts');
  const data = await res.json();
  if (!data.count) {
    el.innerHTML = '<span style="color:var(--text3);font-family:var(--mono);font-size:12px;">No contracts yet</span>';
    return;
  }
  el.innerHTML = data.contracts.map(c => `
    <div class="contract-card">
      <span class="contract-status ${c.status}">${c.status}</span>
      <h3>${c.listing_title || 'Contract #' + c.id}</h3>
      <div style="font-family:var(--mono);font-size:11px;color:var(--text3);">
        Landowner: ${c.landowner_name}${c.landowner_org ? ' · ' + c.landowner_org : ''}
      </div>
      <div style="font-size:13px;margin-top:10px;">
        <strong>${c.area_ha} ha</strong> · ${c.lease_years} years
        · ₹${(c.annual_lease_inr || 0).toLocaleString('en-IN')}/yr
        · Total ₹${(c.total_lease_inr || 0).toLocaleString('en-IN')}
      </div>
      <div style="margin-top:8px;font-size:12px;">
        Landowner signed: ${c.landowner_signed ? '✓ ' + c.landowner_signed_at : '✗ Pending'}
        · Company signed: ${c.company_signed ? '✓ ' + c.company_signed_at : '✗ Pending'}
      </div>
      <div style="margin-top:6px;">
        <span class="payment-badge ${c.payment_status}">${c.payment_status}</span>
        ${c.payment_reference ? ' · Ref: ' + c.payment_reference : ''}
      </div>
      <div style="display:flex;gap:8px;margin-top:12px;">
        ${!c.company_signed ? '<button class="btn btn-green" onclick="signContract(' + c.id + ')">✍ Sign Contract</button>' : ''}
        ${c.status === 'SIGNED' && c.payment_status === 'UNPAID' ? '<button class="btn btn-amber" onclick="recordPayment(' + c.id + ', ' + c.total_lease_inr + ')">💳 Record Payment</button>' : ''}
        ${c.has_pdf ? '<a href="' + BACKEND + '/api/company/contracts/' + c.id + '/pdf" target="_blank" class="btn btn-outline">📄 Download PDF</a>' : ''}
      </div>
    </div>
  `).join('');
}

window.signContract = async (contractId) => {
  const name = prompt('Type your full name to digitally sign this contract:', user.full_name);
  if (!name || name.length < 2) return toast('Name too short');
  try {
    const res = await apiFetch(`/company/contracts/${contractId}/sign`, {
      method: 'POST',
      body: JSON.stringify({ typed_name: name }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Sign failed');
    toast(data.message);
    loadContracts();
  } catch (e) { toast(e.message); }
};

window.recordPayment = async (contractId, totalAmount) => {
  const ref = prompt('Payment reference (UPI/NEFT/cheque number):', '');
  if (!ref || ref.length < 3) return toast('Payment reference too short');
  try {
    const res = await apiFetch(`/company/contracts/${contractId}/pay`, {
      method: 'POST',
      body: JSON.stringify({ amount_inr: totalAmount, reference: ref }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Payment failed');
    toast(data.message);
    loadContracts();
  } catch (e) { toast(e.message); }
};

loadContracts();

document.getElementById('btn-serial')?.addEventListener('click', async () => {
  const serial = document.getElementById('serial-lookup').value.trim();
  const el = document.getElementById('serial-result');
  if (!serial) return toast('Enter a serial');
  el.style.display = 'block';
  el.textContent = 'Looking up…';
  try {
    const res = await fetch(`${API}/registry/credits/${encodeURIComponent(serial)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Not found');
    el.textContent = [
      `Status: ${data.status}`,
      `Registry: ${data.registry}`,
      `Methodology: ${data.methodology || '—'}`,
      `Listing: ${data.listing_title || '—'}`,
      `Verified: ${data.verified_annual_tco2e ?? '—'} tCO₂e/yr`,
      `Issued total: ${data.issued_total_tco2e ?? '—'} tCO₂e`,
      `VVB: ${data.verifier_name || '—'}`,
      `Issued at: ${data.issued_at || '—'}`,
      '',
      data.disclaimer,
    ].join('\n');
  } catch (e) { el.textContent = e.message; }
});

// ── Messaging (with auto-refresh polling) ──
const _msgPollers = {};

window.toggleMessages = async (inquiryId) => {
  const el = document.getElementById(`msgs-${inquiryId}`);
  if (!el) return;
  if (el.style.display === 'block') {
    el.style.display = 'none';
    if (_msgPollers[inquiryId]) { clearInterval(_msgPollers[inquiryId]); delete _msgPollers[inquiryId]; }
    return;
  }
  el.style.display = 'block';
  await refreshMessages(inquiryId);
  // Poll every 10 seconds for new messages while panel is open
  if (!_msgPollers[inquiryId]) {
    _msgPollers[inquiryId] = setInterval(() => refreshMessages(inquiryId), 10000);
  }
};

async function refreshMessages(inquiryId) {
  const el = document.getElementById(`msgs-${inquiryId}`);
  if (!el) return;
  try {
    const res = await apiFetch(`/company/inquiries/${inquiryId}/messages`);
    const data = await res.json();
    const thread = el.querySelector('.chat-thread');
    if (thread) {
      thread.innerHTML = data.messages.length
        ? data.messages.map(m => `
          <div class="chat-msg ${m.sender_role}">
            <div class="chat-meta">${m.sender_role} · ${m.created_at ? new Date(m.created_at).toLocaleString() : ''}</div>
            ${m.body}
          </div>`).join('')
        : '<span style="color:var(--text3);font-family:var(--mono);font-size:11px;">No messages yet</span>';
      thread.scrollTop = thread.scrollHeight;
    }
  } catch (e) { console.error(e); }
}

window.sendMsgCompany = async (inquiryId) => {
  const input = document.getElementById(`msg-input-${inquiryId}`);
  if (!input || !input.value.trim()) return toast('Enter a message');
  try {
    const res = await apiFetch(`/company/inquiries/${inquiryId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ body: input.value.trim() }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
    input.value = '';
    await refreshMessages(inquiryId);
  } catch (e) { toast(e.message); }
};
