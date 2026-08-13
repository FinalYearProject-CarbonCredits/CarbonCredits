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
          Net creditable est. ${item.carbon_potential.estimated_annual_credits_tco2 || '—'} tCO₂e/yr
          · Total ~${item.carbon_potential.estimated_total_credits_tco2 || '—'} tCO₂e
        </div>
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
      ${i.landowner_response ? `<div style="font-size:12px;color:var(--green);margin-top:8px;">Response: ${i.landowner_response}</div>` : ''}
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
