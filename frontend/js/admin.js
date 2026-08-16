const user = requireRole('admin');
if (!user) throw new Error('unauthorized');

document.getElementById('nav-user').textContent = `${user.full_name} · Admin`;

async function loadPendingLand() {
  const res = await apiFetch('/admin/land/pending');
  const data = await res.json();
  const el = document.getElementById('pending-land');
  if (!data.count) {
    el.innerHTML = '<span style="color:var(--text3);font-family:var(--mono);font-size:12px;">No pending land registrations</span>';
    return;
  }
  el.innerHTML = data.pending.map(p => `
    <div class="listing-card" id="land-${p.id}">
      <h3>Survey ${p.survey_number} / Plot ${p.plot_number}</h3>
      <div style="font-family:var(--mono);font-size:11px;color:var(--text3);">${p.owner_name} · ${p.owner_email}</div>
      <div style="font-size:13px;margin-top:8px;">${p.village}, ${p.taluka}, ${p.district}</div>
      <div style="margin-top:10px;font-size:13px;">
        <strong>Computed area:</strong> ${p.area_ha} ha<br>
        <strong>Document area:</strong> ${p.declared_area_document_ha} ha
        ${p.area_mismatch_flag ? '<span style="color:var(--amber);"> · MISMATCH >15% — review carefully</span>' : ''}
      </div>
      <div style="font-size:12px;margin-top:6px;">
        Centroid: ${p.centroid_lat}, ${p.centroid_lon}<br>
        Document: ${p.document_type?.replace(/_/g, ' ')} · ${p.document_filename}
      </div>
      <a href="${BACKEND}${p.document_url}" target="_blank" class="btn btn-outline" style="margin-top:10px;display:inline-block;">View Uploaded Document</a>
      <div style="display:flex;gap:8px;margin-top:12px;">
        <button class="btn btn-green" onclick="reviewLand(${p.id}, 'VERIFIED')">✓ Verify (matches document)</button>
        <button class="btn btn-outline" onclick="reviewLand(${p.id}, 'REJECTED')">Reject</button>
      </div>
    </div>
  `).join('');
}

window.reviewLand = async (parcelId, status) => {
  const notes = status === 'VERIFIED'
    ? 'Offline verification: land document matches drawn boundary and ownership confirmed.'
    : 'Document/boundary mismatch or ownership could not be verified offline.';
  try {
    const res = await apiFetch(`/admin/land/${parcelId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status, admin_notes: notes }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Review failed');
    toast(`Land ${status}`);
    document.getElementById(`land-${parcelId}`)?.remove();
  } catch (e) { toast(e.message); }
};

async function loadPendingKYC() {
  const res = await apiFetch('/admin/kyc/pending');
  const data = await res.json();
  const el = document.getElementById('pending-kyc');
  if (!data.count) {
    el.innerHTML = '<span style="color:var(--text3);font-family:var(--mono);font-size:12px;">No pending KYC</span>';
    return;
  }
  el.innerHTML = data.pending.map(k => `
    <div class="listing-card" id="kyc-${k.user_id}">
      <h3>${k.full_name || 'Unknown'}</h3>
      <div style="font-family:var(--mono);font-size:11px;color:var(--text3);">${k.user_email}</div>
      <div style="font-size:12px;margin-top:8px;">Phone: ${k.phone || '—'}<br>Address: ${k.address || '—'}<br>ID: ${k.id_document_ref || '—'}</div>
      <div style="display:flex;gap:8px;margin-top:12px;">
        <button class="btn btn-green" onclick="reviewKYC(${k.user_id}, 'VERIFIED')">✓ Verify KYC</button>
        <button class="btn btn-outline" onclick="reviewKYC(${k.user_id}, 'REJECTED')">Reject</button>
      </div>
    </div>
  `).join('');
}

window.reviewKYC = async (userId, status) => {
  const notes = status === 'VERIFIED' ? 'Offline KYC completed.' : 'KYC documents insufficient.';
  try {
    const res = await apiFetch(`/admin/kyc/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status, admin_notes: notes }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
    toast(`KYC ${status}`);
    document.getElementById(`kyc-${userId}`)?.remove();
  } catch (e) { toast(e.message); }
};

async function loadUsers() {
  const res = await apiFetch('/admin/users');
  const users = await res.json();
  document.getElementById('all-users').innerHTML = users.map(u => `
    <div style="padding:8px 0;border-bottom:1px solid var(--border);font-size:12px;">
      <strong>${u.full_name}</strong> · ${u.role} · ${u.email}
    </div>`).join('');
}

loadPendingLand();
loadPendingKYC();
loadUsers();
loadInquiries();

async function loadInquiries() {
  const el = document.getElementById('all-inquiries');
  if (!el) return;
  const res = await apiFetch('/admin/inquiries');
  const data = await res.json();
  if (!data.count) {
    el.innerHTML = '<span style="color:var(--text3);font-family:var(--mono);font-size:12px;">No lease inquiries yet</span>';
    return;
  }
  el.innerHTML = data.inquiries.map(i => `
    <div class="listing-card">
      <h3>${i.listing_title || 'Listing #' + i.listing_id}</h3>
      <div style="font-family:var(--mono);font-size:10px;color:var(--amber);">${i.status}</div>
      <div style="font-size:12px;margin-top:6px;">
        ${i.company}${i.company_organization ? ' · ' + i.company_organization : ''} → ${i.landowner}
      </div>
      <div style="font-size:12px;color:var(--text2);margin-top:6px;">${i.message}</div>
      ${i.landowner_response ? '<div style="font-size:12px;color:var(--green);margin-top:6px;">Response: ' + i.landowner_response + '</div>' : ''}
      ${i.status === 'ACCEPTED' ? '<button class="btn btn-outline" style="margin-top:8px;" onclick="viewMessages(' + i.id + ')">💬 View Messages</button><div id="admin-msgs-' + i.id + '" class="chat-thread" style="display:none;"></div>' : ''}
    </div>`).join('');
}

// ── Contracts ──
async function loadContracts() {
  const el = document.getElementById('all-contracts');
  if (!el) return;
  const res = await apiFetch('/admin/contracts');
  const data = await res.json();
  if (!data.count) {
    el.innerHTML = '<span style="color:var(--text3);font-family:var(--mono);font-size:12px;">No contracts yet</span>';
    return;
  }
  el.innerHTML = data.contracts.map(c => `
    <div class="contract-card">
      <span class="contract-status ${c.status}">${c.status}</span>
      <span class="payment-badge ${c.payment_status}" style="margin-left:8px;">${c.payment_status}</span>
      <h3>${c.listing_title || 'Contract #' + c.id}</h3>
      <div style="font-size:12px;margin-top:6px;">
        ${c.landowner_name} → ${c.company_name}${c.company_org ? ' · ' + c.company_org : ''}
      </div>
      <div style="font-size:13px;margin-top:8px;">
        ${c.area_ha} ha · ${c.lease_years} years · ₹${(c.total_lease_inr || 0).toLocaleString('en-IN')}
      </div>
      <div style="font-size:11px;color:var(--text3);margin-top:6px;">
        Landowner: ${c.landowner_signed ? '✓ signed' : '✗'}
        · Company: ${c.company_signed ? '✓ signed' : '✗'}
        ${c.payment_reference ? ' · Payment ref: ' + c.payment_reference : ''}
      </div>
    </div>`).join('');
}

loadContracts();

// ── Message viewing ──
window.viewMessages = async (inquiryId) => {
  const el = document.getElementById(`admin-msgs-${inquiryId}`);
  if (!el) return;
  if (el.style.display === 'block') { el.style.display = 'none'; return; }
  el.style.display = 'block';
  try {
    const res = await apiFetch(`/admin/inquiries/${inquiryId}/messages`);
    const data = await res.json();
    el.innerHTML = data.messages.length
      ? data.messages.map(m => `
        <div class="chat-msg ${m.sender_role}">
          <div class="chat-meta">${m.sender_role} · ${m.created_at ? new Date(m.created_at).toLocaleString() : ''}</div>
          ${m.body}
        </div>`).join('')
      : '<span style="color:var(--text3);font-family:var(--mono);font-size:11px;">No messages</span>';
  } catch (e) { el.textContent = e.message; }
};
