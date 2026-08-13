const user = requireRole('landowner');
if (!user) throw new Error('unauthorized');

document.getElementById('nav-user').textContent = `${user.full_name} · Landowner`;

let map, drawControl, drawnLayer, parcelLayer = null;

function initMap() {
  if (map) return;
  map = L.map('owner-map').setView([19.15, 72.92], 11);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18 }).addTo(map);
  L.circle([19.15, 72.92], { radius: 35000, color: '#22c55e', fillOpacity: 0.03, weight: 1, dashArray: '4 4' }).addTo(map);

  drawnLayer = new L.FeatureGroup().addTo(map);
  drawControl = new L.Control.Draw({
    draw: {
      polygon: {
        allowIntersection: false,
        shapeOptions: { color: '#22c55e', fillColor: '#22c55e', fillOpacity: 0.2, weight: 2 },
      },
      polyline: false, rectangle: false, circle: false, circlemarker: false, marker: false,
    },
    edit: { featureGroup: drawnLayer, remove: true },
  });
  map.addControl(drawControl);

  map.on(L.Draw.Event.CREATED, e => {
    drawnLayer.clearLayers();
    parcelLayer = e.layer;
    drawnLayer.addLayer(parcelLayer);
    updateBoundaryPreview(parcelLayer);
    document.getElementById('btn-register-land').disabled = false;
    toast('Boundary captured — complete document details and submit');
  });

  map.on(L.Draw.Event.DELETED, clearBoundary);
}

function clearBoundary() {
  if (drawnLayer) drawnLayer.clearLayers();
  parcelLayer = null;
  document.getElementById('stat-boundary').textContent = 'Not drawn';
  document.getElementById('stat-area').textContent = '—';
  document.getElementById('stat-lat').textContent = '—';
  document.getElementById('stat-lon').textContent = '—';
  document.getElementById('btn-register-land').disabled = true;
}

/** Client-side preview only — server values are authoritative */
function updateBoundaryPreview(layer) {
  const geo = layer.toGeoJSON().geometry;
  const coords = geo.coordinates[0];
  let area = 0;
  for (let i = 0; i < coords.length - 1; i++) {
    const [lon1, lat1] = coords[i];
    const [lon2, lat2] = coords[i + 1];
    area += (lon2 - lon1) * (lat2 + lat1);
  }
  area = Math.abs(area) * 6378137 * 6378137 / 2;
  const areaHa = (area / 10000).toFixed(4);
  let cLat = 0, cLon = 0;
  coords.slice(0, -1).forEach(c => { cLon += c[0]; cLat += c[1]; });
  cLat /= (coords.length - 1);
  cLon /= (coords.length - 1);

  document.getElementById('stat-boundary').textContent = 'Captured ✓';
  document.getElementById('stat-area').textContent = `${areaHa} ha (preview)`;
  document.getElementById('stat-lat').textContent = cLat.toFixed(6);
  document.getElementById('stat-lon').textContent = cLon.toFixed(6);
}

document.getElementById('btn-draw-boundary').addEventListener('click', () => {
  initMap();
  setTimeout(() => map.invalidateSize(), 200);
  new L.Draw.Polygon(map, drawControl.options.draw.polygon).enable();
  toast('Trace your exact land boundary — double-click to finish');
});

document.getElementById('btn-clear-boundary').addEventListener('click', () => {
  if (drawnLayer) drawnLayer.clearLayers();
  clearBoundary();
});

document.getElementById('btn-register-land').addEventListener('click', async () => {
  if (!parcelLayer) return toast('Draw your land boundary on the map first');

  const docInput = document.getElementById('land-document');
  if (!docInput.files?.length) return toast('Upload your land document');

  const form = new FormData();
  form.append('geometry', JSON.stringify(parcelLayer.toGeoJSON().geometry));
  form.append('survey_number', document.getElementById('survey-number').value.trim());
  form.append('plot_number', document.getElementById('plot-number').value.trim());
  form.append('village', document.getElementById('village').value.trim());
  form.append('taluka', document.getElementById('taluka').value.trim());
  form.append('district', document.getElementById('district').value.trim());
  form.append('document_type', document.getElementById('document-type').value);
  form.append('declared_area_document_ha', document.getElementById('declared-area').value);
  form.append('document', docInput.files[0]);

  const btn = document.getElementById('btn-register-land');
  btn.disabled = true;
  btn.textContent = 'Submitting...';

  try {
    const res = await fetch(`${API}/landowner/land/register`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body: form,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));

    toast(`Land registered — ${data.area_ha} ha computed from boundary`);
    document.getElementById('stat-area').textContent = `${data.area_ha} ha (confirmed)`;
    document.getElementById('stat-lat').textContent = data.centroid_lat;
    document.getElementById('stat-lon').textContent = data.centroid_lon;
    clearBoundary();
    loadMyLand();
  } catch (e) {
    toast(e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Submit Land for Admin Verification';
  }
});

async function loadMyLand() {
  const res = await apiFetch('/landowner/land');
  const parcels = await res.json();
  const el = document.getElementById('my-land');
  const select = document.getElementById('listing-parcel-id');

  if (!parcels.length) {
    el.innerHTML = '<span style="color:var(--text3);font-family:var(--mono);font-size:12px;">No land registered yet</span>';
    select.innerHTML = '<option value="">— Register land first —</option>';
    return;
  }

  el.innerHTML = parcels.map(p => `
    <div class="listing-card">
      <span class="land-status ${p.verification_status}">${p.verification_status}</span>
      <h3>Survey ${p.survey_number} / Plot ${p.plot_number}</h3>
      <div style="font-family:var(--mono);font-size:11px;color:var(--text3);">${p.village}, ${p.taluka}, ${p.district}</div>
      <div style="margin-top:10px;font-size:13px;">
        <strong style="color:var(--green);">${p.area_ha} ha</strong> computed
        · Centroid ${p.centroid_lat}, ${p.centroid_lon}
      </div>
      <div style="font-size:12px;color:var(--text2);margin-top:6px;">
        Document: ${p.document_type?.replace(/_/g, ' ')} · Declared ${p.declared_area_document_ha} ha
        ${p.area_mismatch_flag ? '<span style="color:var(--amber);"> · Area mismatch flagged for admin</span>' : ''}
      </div>
      ${p.admin_notes ? `<div style="font-size:11px;color:var(--amber);margin-top:6px;">Admin: ${p.admin_notes}</div>` : ''}
      <button class="btn btn-green" style="margin-top:12px;" onclick="analyzeLand(${p.id})">Analyze Carbon Potential</button>
      <div id="analysis-${p.id}" class="result-box" style="display:none;margin-top:10px;"></div>
    </div>
  `).join('');

  const verified = parcels.filter(p => p.verification_status === 'VERIFIED');
  select.innerHTML = verified.length
    ? verified.map(p => `<option value="${p.id}">Survey ${p.survey_number} — ${p.area_ha} ha (${p.village})</option>`).join('')
    : '<option value="">— Awaiting land verification —</option>';
}

window.analyzeLand = async (parcelId) => {
  const el = document.getElementById(`analysis-${parcelId}`);
  el.style.display = 'block';
  el.textContent = 'Running satellite analysis on registered boundary...';
  try {
    const res = await apiFetch(`/landowner/land/${parcelId}/analyze`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Analysis failed');
    const cp = data.credit_potential;
    const bl = data.baseline_assessment || cp.baseline_assessment || {};
    const sat = data.satellite_analysis || {};
    const ndviCh = sat.ndvi_change || {};
    el.textContent = [
      `Verification: ${data.verification_status}`,
      `Computed area: ${data.computed_area_ha} ha`,
      `NDVI: ${sat.ndvi_mean ?? 'N/A'} · AGBD source: ${sat.agbd_source ?? 'N/A'}`,
      sat.mean_agbd_mg_ha != null ? `Mean AGBD: ${sat.mean_agbd_mg_ha} Mg/ha` : '',
      ndviCh.available ? `NDVI trend (${ndviCh.lookback_months}mo): ${ndviCh.vegetation_trend} (Δ ${ndviCh.ndvi_delta})` : '',
      `Annual potential: ${cp.estimated_annual_removal_tco2e.min}–${cp.estimated_annual_removal_tco2e.max} tCO₂e/yr`,
      bl.net_creditable_annual_tco2e ? `Net creditable (after baseline/leakage/buffer): ${bl.net_creditable_annual_tco2e.min}–${bl.net_creditable_annual_tco2e.max} tCO₂e/yr` : '',
      `Additionality score: ${bl.additionality_score_pct ?? '—'}%`,
      '', cp.disclaimer,
    ].filter(Boolean).join('\n');
  } catch (e) { el.textContent = e.message; }
};

async function loadKYC() {
  const res = await apiFetch('/landowner/kyc');
  const k = await res.json();
  const badge = document.getElementById('kyc-badge');
  badge.textContent = `KYC: ${k.status.replace(/_/g, ' ')}`;
  badge.className = 'kyc-badge ' + (k.status === 'VERIFIED' ? 'verified' : k.status === 'SUBMITTED' ? 'pending' : 'not-started');
  if (k.full_name) document.getElementById('kyc-name').value = k.full_name;
  if (k.phone) document.getElementById('kyc-phone').value = k.phone;
  if (k.address) document.getElementById('kyc-address').value = k.address;
  if (k.id_document_ref) document.getElementById('kyc-id').value = k.id_document_ref;
}

async function loadListings() {
  const res = await apiFetch('/landowner/listings');
  const list = await res.json();
  const el = document.getElementById('my-listings');
  if (!list.length) {
    el.innerHTML = '<span style="color:var(--text3);font-family:var(--mono);font-size:12px;">No listings yet</span>';
    return;
  }
  el.innerHTML = list.map(l => `
    <div class="listing-card">
      <h3>${l.title}</h3>
      <div style="font-family:var(--mono);font-size:11px;color:var(--text3);">
        Survey ${l.survey_number || '—'} · ${l.area_ha} ha · Lease ${l.lease_duration_years} years
      </div>
    </div>`).join('');
}

document.getElementById('btn-kyc').addEventListener('click', async () => {
  try {
    const res = await apiFetch('/landowner/kyc/submit', {
      method: 'POST',
      body: JSON.stringify({
        full_name: document.getElementById('kyc-name').value,
        phone: document.getElementById('kyc-phone').value,
        address: document.getElementById('kyc-address').value,
        id_document_ref: document.getElementById('kyc-id').value,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'KYC failed');
    toast(data.message);
    loadKYC();
  } catch (e) { toast(e.message); }
});

document.getElementById('btn-listing').addEventListener('click', async () => {
  const parcelId = document.getElementById('listing-parcel-id').value;
  if (!parcelId) return toast('Select a verified land parcel');
  try {
    const res = await apiFetch('/landowner/listings', {
      method: 'POST',
      body: JSON.stringify({
        parcel_id: parseInt(parcelId),
        title: document.getElementById('list-title').value || undefined,
        lease_duration_years: parseInt(document.getElementById('list-lease').value),
        notes: document.getElementById('list-notes').value || undefined,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Listing failed');
    toast(data.message);
    loadListings();
  } catch (e) { toast(e.message); }
});

initMap();
loadKYC();
loadMyLand();
loadListings();
loadInquiries();

async function loadInquiries() {
  const el = document.getElementById('lease-inquiries');
  if (!el) return;
  const res = await apiFetch('/landowner/inquiries');
  const data = await res.json();
  if (!data.count) {
    el.innerHTML = '<span style="color:var(--text3);font-family:var(--mono);font-size:12px;">No lease inquiries yet</span>';
    return;
  }
  el.innerHTML = data.inquiries.map(i => `
    <div class="listing-card" id="inq-${i.id}">
      <h3>${i.listing_title || 'Listing'}</h3>
      <div style="font-family:var(--mono);font-size:10px;color:var(--amber);">${i.status}</div>
      <div style="font-size:13px;margin-top:8px;">
        <strong>${i.company_name}</strong>${i.company_organization ? ' · ' + i.company_organization : ''}
        ${i.company_phone ? '<br>Phone: ' + i.company_phone : ''}
      </div>
      <div style="font-size:12px;color:var(--text2);margin-top:8px;">${i.message}</div>
      ${i.proposed_lease_years ? `<div style="font-size:12px;margin-top:4px;">Proposed lease: ${i.proposed_lease_years} years</div>` : ''}
      ${i.status === 'SUBMITTED' ? `
        <div style="display:flex;gap:8px;margin-top:12px;">
          <button class="btn btn-green" onclick="respondInquiry(${i.id}, 'ACCEPTED')">Accept</button>
          <button class="btn btn-outline" onclick="respondInquiry(${i.id}, 'DECLINED')">Decline</button>
        </div>` : i.landowner_response ? `<div style="font-size:12px;color:var(--green);margin-top:8px;">Your response: ${i.landowner_response}</div>` : ''}
    </div>`).join('');
}

window.respondInquiry = async (id, status) => {
  const response = prompt('Your response to the company:', status === 'ACCEPTED' ? 'We accept your lease proposal. Please contact us offline to proceed.' : 'Thank you, we are not available at this time.');
  if (!response || response.length < 5) return toast('Response too short');
  try {
    const res = await apiFetch(`/landowner/inquiries/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status, landowner_response: response }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed');
    toast(data.message);
    loadInquiries();
  } catch (e) { toast(e.message); }
};
