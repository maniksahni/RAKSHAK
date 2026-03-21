/**
 * RAKSHAK — Danger Zone Heatmap JS
 * Leaflet.heat + marker layers + click-to-report + proximity warning
 */

let heatMap = null;
let heatLayer = null;
let markersLayer = null;
let reportingMode = false;
let selectedLat = null, selectedLng = null;
let userLoc = null;

document.addEventListener('DOMContentLoaded', initHeatmap);

async function initHeatmap() {
  // Initialize dark Leaflet map
  heatMap = L.map('map', { zoomControl: true, attributionControl: false });
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19
  }).addTo(heatMap);
  heatMap.setView([20.5937, 78.9629], 6);

  markersLayer = L.layerGroup().addTo(heatMap);

  // Map click handler
  heatMap.on('click', function(e) {
    if (reportingMode) {
      selectedLat = e.latlng.lat;
      selectedLng = e.latlng.lng;
      document.getElementById('report-lat').value = selectedLat;
      document.getElementById('report-lng').value = selectedLng;
      document.getElementById('loc-display').textContent =
        `${selectedLat.toFixed(5)}, ${selectedLng.toFixed(5)}`;

      // Temp marker
      if (window._tempMarker) heatMap.removeLayer(window._tempMarker);
      window._tempMarker = L.circleMarker([selectedLat, selectedLng], {
        radius: 10, color: '#dc2626', fillColor: '#dc2626', fillOpacity: 0.5, weight: 2
      }).addTo(heatMap);

      document.getElementById('report-modal').style.display = 'flex';
    }
  });

  // Load data in parallel
  await Promise.all([loadHeatmap(), loadMarkers()]);

  // Geolocate user
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(pos => {
      userLoc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
      heatMap.setView([userLoc.lat, userLoc.lng], 14);

      const userIcon = L.divIcon({
        className: '',
        html: `<div style="width:16px;height:16px;border-radius:50%;background:#4299e1;border:3px solid rgba(255,255,255,0.8);box-shadow:0 0 12px #4299e1;"></div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      });
      L.marker([userLoc.lat, userLoc.lng], { icon: userIcon })
        .bindPopup('<strong>📍 You are here</strong>')
        .addTo(heatMap);

      // Check proximity
      checkUserProximity(userLoc.lat, userLoc.lng);
    }, () => {});
  }

  // Listen for new approved zones via SocketIO
  if (typeof socket !== 'undefined') {
    socket.on('new_danger_zone', (data) => {
      addZoneMarker(data.zone);
      showToast('⚠️ New danger zone added nearby!', 'warning');
    });
  }
}

// ── Load Heatmap Points ───────────────────────────────────────────────────────
async function loadHeatmap() {
  try {
    const resp = await fetch('/danger-zones/heatmap').then(r => r.json());
    if (!resp.success) return;

    heatLayer = L.heatLayer(resp.points, {
      radius: 35,
      blur: 25,
      maxZoom: 17,
      max: 1.0,
      gradient: { 0.0: '#4299e1', 0.3: '#f6ad55', 0.6: '#dc2626', 1.0: '#fff' },
    });
    heatLayer.addTo(heatMap);
  } catch (e) {
    console.warn('[RAKSHAK] Heatmap load failed:', e.message);
  }
}

// ── Load GeoJSON Markers ─────────────────────────────────────────────────────
async function loadMarkers() {
  try {
    const resp = await fetch('/danger-zones/list').then(r => r.json());
    if (!resp.success) return;

    resp.geojson.features.forEach(f => addZoneMarker(f.properties, f.geometry.coordinates));
  } catch (e) {
    console.warn('[RAKSHAK] Markers load failed:', e.message);
  }
}

function addZoneMarker(zone, coords) {
  const lat = zone.latitude || (coords && coords[1]);
  const lng = zone.longitude || (coords && coords[0]);
  if (!lat || !lng) return;

  const colors = { high: '#dc2626', medium: '#f6ad55', low: '#48bb78' };
  const color = colors[zone.severity] || '#dc2626';

  const icon = L.divIcon({
    className: '',
    html: `<div style="
      width:22px;height:22px;border-radius:50%;
      background:${color};
      border:2px solid rgba(255,255,255,0.4);
      box-shadow:0 0 14px ${color},0 0 28px ${color}66;
      cursor:pointer;
    "></div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });

  const zoneTypes = { harassment: '🚫', theft: '💀', poorly_lit: '🌑', other: '⚠️' };
  const emoji = zoneTypes[zone.zone_type] || '⚠️';

  const marker = L.marker([lat, lng], { icon }).bindPopup(`
    <div style="font-family:Inter,sans-serif;min-width:180px;">
      <div style="font-size:1.2rem;margin-bottom:4px;">${emoji}</div>
      <strong style="color:#dc2626;">${(zone.zone_type||'danger').replace(/_/g,' ').toUpperCase()}</strong>
      <div style="color:#a0aec0;font-size:0.82rem;margin:6px 0;">${zone.description || ''}</div>
      <div style="display:flex;gap:6px;align-items:center;">
        <span class="pill pill-${zone.severity}" style="font-size:0.7rem;">${zone.severity}</span>
        <span style="font-size:0.72rem;color:#718096;">👍 ${zone.upvotes||0} upvotes</span>
      </div>
    </div>
  `);
  markersLayer.addLayer(marker);
}

// ── Toggle Heatmap ────────────────────────────────────────────────────────────
function toggleHeatmap() {
  if (!heatLayer) return;
  if (heatMap.hasLayer(heatLayer)) {
    heatMap.removeLayer(heatLayer);
    showToast('Heatmap hidden', 'info');
  } else {
    heatMap.addLayer(heatLayer);
    showToast('Heatmap visible', 'info');
  }
}

// ── Report Mode ───────────────────────────────────────────────────────────────
function reportZoneMode() {
  reportingMode = !reportingMode;
  if (reportingMode) {
    showToast('Click on the map to select a danger location', 'info', 3000);
    heatMap.getContainer().style.cursor = 'crosshair';
    // Pulse the map border to indicate active mode
    heatMap.getContainer().style.boxShadow = '0 0 0 2px var(--red-primary), 0 0 20px rgba(220,38,38,0.2)';
  } else {
    heatMap.getContainer().style.cursor = '';
    heatMap.getContainer().style.boxShadow = '';
  }
}

function closeReportModal() {
  const modal = document.getElementById('report-modal');
  const card = modal?.querySelector('.report-modal-card');
  if (card) {
    card.style.transition = 'all .25s cubic-bezier(.22,1,.36,1)';
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px) scale(.95)';
  }
  setTimeout(() => {
    if (modal) modal.style.display = 'none';
    if (card) { card.style.opacity = ''; card.style.transform = ''; card.style.transition = ''; }
  }, 250);
  reportingMode = false;
  heatMap.getContainer().style.cursor = '';
  heatMap.getContainer().style.boxShadow = '';
  if (window._tempMarker) { heatMap.removeLayer(window._tempMarker); window._tempMarker = null; }
  selectedLat = selectedLng = null;
  document.getElementById('loc-display').textContent = 'Click on the map to select location';
}

async function submitReport(e) {
  e.preventDefault();
  if (!selectedLat || !selectedLng) {
    return showToast('Please click on the map to select a location first.', 'error');
  }
  const btn = document.getElementById('report-btn');
  btn.disabled = true; btn.textContent = 'Submitting...';
  showLoading('Submitting danger zone report...');

  const form = document.getElementById('report-form');
  const fd = new FormData(form);
  const data = Object.fromEntries(fd.entries());

  const resp = await postJSON('/danger-zones/report', data);
  hideLoading();
  if (resp.success) {
    showToast(resp.message, 'success');
    closeReportModal();
  } else showToast(resp.error || 'Submission failed', 'error');
  btn.disabled = false; btn.textContent = 'Submit Report';
}

// ── Locate Me ─────────────────────────────────────────────────────────────────
function locateMe() {
  if (userLoc) {
    heatMap.setView([userLoc.lat, userLoc.lng], 15);
  } else if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(pos => {
      heatMap.setView([pos.coords.latitude, pos.coords.longitude], 15);
    });
  }
}

// ── Proximity Warning ─────────────────────────────────────────────────────────
async function checkUserProximity(lat, lng) {
  try {
    const resp = await postJSON('/danger-zones/proximity', { lat, lng });
    if (resp.success && resp.count > 0) {
      const nearest = resp.nearby[0];
      const modal = document.getElementById('proximity-modal');
      const text   = document.getElementById('proximity-text');
      if (modal && text) {
        text.textContent = `${nearest.zone_type.replace(/_/g,' ')} zone ${Math.round(nearest.distance_m)}m away`;
        modal.style.display = 'flex';
        setTimeout(() => { modal.style.display = 'none'; }, 10000);
      }
    }
  } catch(e) {}
}
