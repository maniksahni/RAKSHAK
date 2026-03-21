/**
 * RAKSHAK — Danger Zone Heatmap JS
 * Leaflet.heat + marker layers + click-to-report + proximity warning
 */

let heatMap = null;
let heatLayer = null;
let markersLayer = null;
let globalMarkersLayer = null;
let globalHeatLayer = null;
let reportingMode = false;
let selectedLat = null, selectedLng = null;
let userLoc = null;
let globalViewActive = false;

// ── GLOBAL CRIME HOTSPOTS DATA ──────────────────────────────────────────────
// Real-world high-crime areas for women's safety awareness
const GLOBAL_HOTSPOTS = [
  // India
  {lat:28.6139,lng:77.2090,name:'Delhi NCR',severity:'high',type:'harassment',desc:'High-frequency zone for street harassment & assault',country:'India',risk:0.95},
  {lat:19.0760,lng:72.8777,name:'Mumbai - Dharavi',severity:'high',type:'theft',desc:'Pickpocketing & chain snatching reports',country:'India',risk:0.85},
  {lat:22.5726,lng:88.3639,name:'Kolkata - Park Street',severity:'medium',type:'harassment',desc:'Evening harassment reports',country:'India',risk:0.7},
  {lat:12.9716,lng:77.5946,name:'Bangalore - Majestic',severity:'high',type:'harassment',desc:'Bus stand area — harassment hotspot',country:'India',risk:0.88},
  {lat:17.3850,lng:78.4867,name:'Hyderabad - Old City',severity:'medium',type:'poorly_lit',desc:'Poorly lit narrow lanes after dark',country:'India',risk:0.72},
  {lat:26.9124,lng:75.7873,name:'Jaipur - Walled City',severity:'medium',type:'harassment',desc:'Tourist harassment zone',country:'India',risk:0.68},
  {lat:23.0225,lng:72.5714,name:'Ahmedabad - Riverfront',severity:'low',type:'poorly_lit',desc:'Dimly lit stretches at night',country:'India',risk:0.5},
  {lat:13.0827,lng:80.2707,name:'Chennai - T. Nagar',severity:'medium',type:'theft',desc:'Crowded market — theft risk',country:'India',risk:0.65},
  {lat:26.8467,lng:80.9462,name:'Lucknow - Charbagh',severity:'high',type:'harassment',desc:'Railway station area — high risk',country:'India',risk:0.82},
  {lat:21.1702,lng:72.8311,name:'Surat - Textile Market',severity:'medium',type:'harassment',desc:'Crowded areas — harassment',country:'India',risk:0.6},

  // South America
  {lat:-23.5505,lng:-46.6333,name:'São Paulo - Centro',severity:'high',type:'theft',desc:'Armed robbery & assault hotspot',country:'Brazil',risk:0.92},
  {lat:-22.9068,lng:-43.1729,name:'Rio de Janeiro - Copacabana',severity:'high',type:'theft',desc:'Tourist robbery & assault zone',country:'Brazil',risk:0.9},
  {lat:4.7110,lng:-74.0721,name:'Bogotá - La Candelaria',severity:'high',type:'theft',desc:'Scopolamine drugging & robbery',country:'Colombia',risk:0.88},
  {lat:-12.0464,lng:-77.0428,name:'Lima - Centro',severity:'high',type:'theft',desc:'Express kidnapping reports',country:'Peru',risk:0.85},
  {lat:-34.6037,lng:-58.3816,name:'Buenos Aires - La Boca',severity:'medium',type:'theft',desc:'Tourist-targeting theft zone',country:'Argentina',risk:0.72},
  {lat:10.4806,lng:-66.9036,name:'Caracas - Petare',severity:'high',type:'other',desc:'One of highest crime rate zones globally',country:'Venezuela',risk:0.97},

  // Central America & Mexico
  {lat:19.4326,lng:-99.1332,name:'Mexico City - Tepito',severity:'high',type:'theft',desc:'High crime neighbourhood',country:'Mexico',risk:0.9},
  {lat:14.6349,lng:-90.5069,name:'Guatemala City - Zone 18',severity:'high',type:'other',desc:'Gang violence & assault zone',country:'Guatemala',risk:0.93},
  {lat:15.5000,lng:-88.0333,name:'San Pedro Sula',severity:'high',type:'other',desc:'Historically highest homicide rate',country:'Honduras',risk:0.95},

  // Africa
  {lat:-26.2041,lng:28.0473,name:'Johannesburg - Hillbrow',severity:'high',type:'other',desc:'High assault & robbery rates',country:'South Africa',risk:0.93},
  {lat:-33.9249,lng:18.4241,name:'Cape Town - CBD',severity:'high',type:'theft',desc:'Mugging & gang activity zone',country:'South Africa',risk:0.88},
  {lat:6.5244,lng:3.3792,name:'Lagos - Oshodi',severity:'high',type:'theft',desc:'Market area — robbery & harassment',country:'Nigeria',risk:0.85},
  {lat:-1.2921,lng:36.8219,name:'Nairobi - Eastleigh',severity:'high',type:'theft',desc:'Pickpocketing & carjacking zone',country:'Kenya',risk:0.82},
  {lat:33.5731,lng:-7.5898,name:'Casablanca - Medina',severity:'medium',type:'harassment',desc:'Tourist harassment zone',country:'Morocco',risk:0.68},

  // Europe
  {lat:41.3851,lng:2.1734,name:'Barcelona - La Rambla',severity:'medium',type:'theft',desc:'Pickpocketing capital of Europe',country:'Spain',risk:0.7},
  {lat:48.8566,lng:2.3522,name:'Paris - Gare du Nord',severity:'medium',type:'theft',desc:'Pickpocket & scam hotspot',country:'France',risk:0.68},
  {lat:41.9028,lng:12.4964,name:'Rome - Termini Station',severity:'medium',type:'theft',desc:'Tourist theft zone',country:'Italy',risk:0.65},
  {lat:37.9838,lng:23.7275,name:'Athens - Omonia Square',severity:'medium',type:'theft',desc:'Night-time mugging reports',country:'Greece',risk:0.7},
  {lat:51.5074,lng:-0.1278,name:'London - Westminster',severity:'low',type:'theft',desc:'Pickpocketing in tourist areas',country:'UK',risk:0.5},

  // Middle East
  {lat:30.0444,lng:31.2357,name:'Cairo - Khan el-Khalili',severity:'medium',type:'harassment',desc:'Market harassment zone',country:'Egypt',risk:0.75},
  {lat:33.8938,lng:35.5018,name:'Beirut - Hamra',severity:'medium',type:'other',desc:'Unstable security zone',country:'Lebanon',risk:0.72},

  // Asia
  {lat:14.5995,lng:120.9842,name:'Manila - Tondo',severity:'high',type:'other',desc:'High crime density area',country:'Philippines',risk:0.88},
  {lat:13.7563,lng:100.5018,name:'Bangkok - Khao San',severity:'medium',type:'theft',desc:'Tourist scam & theft area',country:'Thailand',risk:0.65},
  {lat:-6.2088,lng:106.8456,name:'Jakarta - Tanah Abang',severity:'medium',type:'theft',desc:'Market pickpocketing zone',country:'Indonesia',risk:0.7},
  {lat:23.8103,lng:90.4125,name:'Dhaka - Sadarghat',severity:'high',type:'harassment',desc:'Crowded areas — harassment',country:'Bangladesh',risk:0.82},
  {lat:27.7172,lng:85.3240,name:'Kathmandu - Thamel',severity:'medium',type:'theft',desc:'Tourist theft zone',country:'Nepal',risk:0.6},

  // North America
  {lat:25.7617,lng:-80.1918,name:'Miami - Overtown',severity:'high',type:'other',desc:'High violent crime rate',country:'USA',risk:0.82},
  {lat:41.8781,lng:-87.6298,name:'Chicago - South Side',severity:'high',type:'other',desc:'Gun violence hotspot',country:'USA',risk:0.9},
  {lat:36.1699,lng:-115.1398,name:'Las Vegas - Strip',severity:'medium',type:'theft',desc:'Tourist-targeting crimes',country:'USA',risk:0.65},
  {lat:18.5204,lng:-72.3360,name:'Port-au-Prince',severity:'high',type:'other',desc:'Kidnapping & gang zone',country:'Haiti',risk:0.95},
];

document.addEventListener('DOMContentLoaded', initHeatmap);

async function initHeatmap() {
  // Initialize dark Leaflet map
  heatMap = L.map('map', { zoomControl: true, attributionControl: false });
  darkLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19
  }).addTo(heatMap);
  heatMap.setView([20.5937, 78.9629], 4);

  markersLayer = L.layerGroup().addTo(heatMap);
  globalMarkersLayer = L.layerGroup().addTo(heatMap);

  // Map drag/move HUD Telemetry loop
  heatMap.on('move', function() {
    triggerHUDTelemetry();
  });
  heatMap.on('zoomend', function() {
    triggerHUDTelemetry();
  });
  
  // Map click handler (report mode)
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

  // Load data in parallel — community zones + global hotspots
  await Promise.all([loadHeatmap(), loadMarkers()]);
  loadGlobalHotspots();

  // Geolocate user
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(pos => {
      userLoc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
      heatMap.setView([userLoc.lat, userLoc.lng], 14);

      const userIcon = L.divIcon({
        className: '',
        html: `<div style="width:18px;height:18px;border-radius:50%;background:#4299e1;border:3px solid rgba(255,255,255,0.9);box-shadow:0 0 16px #4299e1,0 0 32px rgba(66,153,225,0.4);"></div>
               <div style="position:absolute;top:-4px;left:-4px;width:26px;height:26px;border-radius:50%;border:2px solid rgba(66,153,225,0.4);animation:userPing 2s ease-out infinite;"></div>`,
        iconSize: [18, 18],
        iconAnchor: [9, 9],
      });
      L.marker([userLoc.lat, userLoc.lng], { icon: userIcon })
        .bindPopup('<strong style="color:#4299e1;">📍 You are here</strong><br><span style="color:#a0aec0;font-size:0.8rem;">GPS location locked</span>')
        .addTo(heatMap);

      // Check proximity
      checkUserProximity(userLoc.lat, userLoc.lng);
    }, () => {});
  }

  // Inject pulsing marker CSS
  injectGlobalMarkerStyles();

  // Listen for new approved zones via SocketIO
  if (typeof socket !== 'undefined') {
    socket.on('new_danger_zone', (data) => {
      addZoneMarker(data.zone);
      showToast('⚠️ New danger zone added nearby!', 'warning');
    });
  }

  // Update global zone count badge
  updateGlobalStats();
}

// ── HUD Telemetry Formatter ───────────────────────────────────────────────────
function triggerHUDTelemetry() {
  if(!heatMap) return;
  const center = heatMap.getCenter();
  const zoom = heatMap.getZoom();
  
  const elLat = document.getElementById('hud-lat');
  const elLng = document.getElementById('hud-lng');
  const elZoom = document.getElementById('hud-zoom');
  const elBearing = document.getElementById('hud-bearing');
  
  if(elLat) elLat.textContent = center.lat.toFixed(5);
  if(elLng) elLng.textContent = center.lng.toFixed(5);
  if(elZoom) elZoom.textContent = zoom.toFixed(1) + 'x';
  if(elBearing) {
    // Generate an artificial sweep bearing based on milliseconds to simulate radar spin direction
    const artificialBearing = ((Date.now() / 20) % 360).toFixed(1);
    elBearing.textContent = artificialBearing + '°';
  }
}

// ── Inject CSS for animated markers ─────────────────────────────────────────
function injectGlobalMarkerStyles() {
  if (document.getElementById('global-marker-css')) return;
  const style = document.createElement('style');
  style.id = 'global-marker-css';
  style.textContent = `
    @keyframes userPing {
      0% { transform:scale(1); opacity:0.8; }
      100% { transform:scale(2.5); opacity:0; }
    }
    @keyframes hotspotPulse {
      0%,100% { box-shadow:0 0 8px currentColor, 0 0 16px currentColor; transform:scale(1); }
      50% { box-shadow:0 0 16px currentColor, 0 0 32px currentColor; transform:scale(1.15); }
    }
    @keyframes hotspotRing {
      0% { transform:scale(1); opacity:0.6; }
      100% { transform:scale(3); opacity:0; }
    }
    .global-hotspot-marker {
      border-radius:50%;cursor:pointer;
      animation:hotspotPulse 2s ease-in-out infinite;
      position:relative;
    }
    .hotspot-ring {
      position:absolute;border-radius:50%;
      border:1.5px solid currentColor;
      animation:hotspotRing 2.5s ease-out infinite;
      pointer-events:none;
    }
  `;
  document.head.appendChild(style);
}

// ── Load Global Hotspots ────────────────────────────────────────────────────
function loadGlobalHotspots() {
  const heatPoints = [];

  GLOBAL_HOTSPOTS.forEach((spot, i) => {
    const colors = { high:'#dc2626', medium:'#f6ad55', low:'#48bb78' };
    const color = colors[spot.severity] || '#dc2626';
    const size = spot.severity === 'high' ? 18 : spot.severity === 'medium' ? 14 : 11;
    const ringDelay = (i * 0.3 % 3).toFixed(1);

    const icon = L.divIcon({
      className: '',
      html: `<div class="global-hotspot-marker" style="
        width:${size}px;height:${size}px;
        background:${color};color:${color};
        border:2px solid rgba(255,255,255,0.3);
        animation-delay:${ringDelay}s;
      ">
        <div class="hotspot-ring" style="
          top:${-size*0.4}px;left:${-size*0.4}px;
          width:${size*1.8}px;height:${size*1.8}px;
          color:${color};animation-delay:${ringDelay}s;
        "></div>
      </div>`,
      iconSize: [size, size],
      iconAnchor: [size/2, size/2],
    });

    const typeEmoji = { harassment:'🚫', theft:'💰', poorly_lit:'🌑', other:'⚠️' };
    const emoji = typeEmoji[spot.type] || '⚠️';

    const riskPct = Math.round(spot.risk * 100);
    const riskBar = `<div style="width:100%;height:4px;background:rgba(255,255,255,0.1);border-radius:2px;margin-top:6px;overflow:hidden;">
      <div style="width:${riskPct}%;height:100%;background:${color};border-radius:2px;"></div>
    </div>`;

    const marker = L.marker([spot.lat, spot.lng], { icon }).bindPopup(`
      <div style="font-family:Inter,sans-serif;min-width:220px;padding:4px;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
          <span style="font-size:1.3rem;">${emoji}</span>
          <div>
            <strong style="color:${color};font-size:0.95rem;">${spot.name}</strong>
            <div style="font-size:0.7rem;color:#718096;">🌍 ${spot.country}</div>
          </div>
        </div>
        <div style="color:#a0aec0;font-size:0.82rem;margin-bottom:6px;">${spot.desc}</div>
        <div style="display:flex;gap:8px;align-items:center;">
          <span style="background:${color}22;color:${color};border:1px solid ${color}44;padding:2px 8px;border-radius:50px;font-size:0.7rem;font-weight:600;">
            ${spot.severity.toUpperCase()}
          </span>
          <span style="font-size:0.72rem;color:#718096;">Risk: ${riskPct}%</span>
        </div>
        ${riskBar}
      </div>
    `);
    globalMarkersLayer.addLayer(marker);

    // Add to heat data
    heatPoints.push([spot.lat, spot.lng, spot.risk]);
  });

  // Global heat overlay
  globalHeatLayer = L.heatLayer(heatPoints, {
    radius: 40,
    blur: 30,
    maxZoom: 10,
    max: 1.0,
    gradient: { 0.0:'#48bb78', 0.3:'#f6ad55', 0.6:'#dc2626', 0.85:'#ff4444', 1.0:'#fff' },
  });
  globalHeatLayer.addTo(heatMap);
}

// ── Toggle Global View ──────────────────────────────────────────────────────
function toggleGlobalView() {
  globalViewActive = !globalViewActive;
  const btn = document.getElementById('global-toggle-btn');

  if (globalViewActive) {
    heatMap.setView([20, 10], 2);
    if (btn) { btn.style.borderColor = '#dc2626'; btn.style.color = '#dc2626'; btn.innerHTML = '<i class="bi bi-globe2 me-1" style="color:#dc2626;"></i> Global ON'; }
    showToast('Global danger zones — showing worldwide hotspots', 'warning', 3000);
  } else {
    if (userLoc) heatMap.setView([userLoc.lat, userLoc.lng], 14);
    else heatMap.setView([20.5937, 78.9629], 6);
    if (btn) { btn.style.borderColor = ''; btn.style.color = ''; btn.innerHTML = '<i class="bi bi-globe2 me-1" style="color:var(--accent-blue);"></i> Global View'; }
  }
}

// ── Toggle Global Markers ───────────────────────────────────────────────────
function toggleGlobalMarkers() {
  if (!globalMarkersLayer) return;
  if (heatMap.hasLayer(globalMarkersLayer)) {
    heatMap.removeLayer(globalMarkersLayer);
    if (globalHeatLayer) heatMap.removeLayer(globalHeatLayer);
    showToast('Global markers hidden', 'info');
  } else {
    heatMap.addLayer(globalMarkersLayer);
    if (globalHeatLayer) heatMap.addLayer(globalHeatLayer);
    showToast('Global markers visible', 'info');
  }
}

// ── Update stats badge ──────────────────────────────────────────────────────
function updateGlobalStats() {
  const badge = document.getElementById('global-zone-count');
  if (badge) {
    const total = GLOBAL_HOTSPOTS.length;
    const high = GLOBAL_HOTSPOTS.filter(h => h.severity === 'high').length;
    badge.textContent = `${total} zones · ${high} high risk`;
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

// ── Satellite Toggle ─────────────────────────────────────────────────────────
let satelliteLayer = null;
let darkLayer = null;
let isSatellite = false;

function toggleSatellite() {
  if (!heatMap) return;
  const btn = document.getElementById('sat-toggle');
  if (!satelliteLayer) {
    satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      attribution:'Esri',maxZoom:19
    });
  }
  if (!darkLayer) {
    darkLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution:'CARTO',maxZoom:19
    });
  }
  if (isSatellite) {
    heatMap.removeLayer(satelliteLayer);
    darkLayer.addTo(heatMap);
    if (btn) btn.innerHTML = '<i class="bi bi-layers me-1" style="color:var(--accent-green);"></i> Satellite';
  } else {
    heatMap.removeLayer(darkLayer);
    satelliteLayer.addTo(heatMap);
    if (btn) btn.innerHTML = '<i class="bi bi-layers me-1" style="color:var(--accent-green);"></i> Dark Map';
  }
  isSatellite = !isSatellite;
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
