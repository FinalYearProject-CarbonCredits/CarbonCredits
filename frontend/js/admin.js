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
      ${i.landowner_response ? `<div style="font-size:12px;color:var(--green);margin-top:6px;">Response: ${i.landowner_response}</div>` : ''}
    </div>`).join('');
}
