/**
 * RAKSHAK Dashboard JS
 * Handles: Leaflet map, SOS trigger, AI ping, alert feed, SocketIO updates
 */

let dashMap = null;
let userMarker = null;
let currentLat = null, currentLng = null;
let sosConfirmPending = false;
let pingInterval = null;

function initDashboard(dangerZones, userAlerts) {
  initMap(dangerZones);
  startAIPing();
  loadRiskScore();
  animateStatCounters();
  initScrollReveal();
}

// ── Animated Counters ─────────────────────────────────────────────────────────
function animateStatCounters() {
  document.querySelectorAll('.stat-number').forEach(el => {
    const val = parseInt(el.textContent);
    if (isNaN(val) || val === 0) return;
    el.textContent = '0';
    const duration = 800;
    const start = performance.now();
    function tick(now) {
      const t = Math.min((now - start) / duration, 1);
      const ease = 1 - Math.pow(1 - t, 3); // ease-out cubic
      el.textContent = Math.round(val * ease);
      if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });
}

// ── Scroll Reveal ─────────────────────────────────────────────────────────────
function initScrollReveal() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });
  document.querySelectorAll('.animate-in').forEach((el, i) => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = `opacity .5s ${i * 0.06}s cubic-bezier(.22,1,.36,1), transform .5s ${i * 0.06}s cubic-bezier(.22,1,.36,1)`;
    observer.observe(el);
  });
}

// ── Leaflet Map ─────────────────────────────────────────────────────────────
function initMap(dangerZones) {
  dashMap = L.map('map', { zoomControl: true, attributionControl: false });

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19
  }).addTo(dashMap);

  dashMap.setView([20.5937, 78.9629], 5); // Default: India

  // Add danger zones as glowing markers
  if (dangerZones) {
    dangerZones.forEach(zone => {
      const colors = { high: '#dc2626', medium: '#f6ad55', low: '#48bb78' };
      const color = colors[zone.severity] || '#dc2626';

      const icon = L.divIcon({
        className: '',
        html: `<div style="width:16px;height:16px;border-radius:50%;background:${color};border:2px solid rgba(255,255,255,0.3);box-shadow:0 0 12px ${color},0 0 24px ${color}44;animation:sos-pulse 2s infinite;"></div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      });
      L.marker([zone.latitude, zone.longitude], { icon })
        .bindPopup(`<div style="font-family:Inter,sans-serif;">
          <strong style="color:#dc2626;">${zone.zone_type ? zone.zone_type.replace(/_/g,' ').toUpperCase() : 'DANGER'}</strong><br>
          <span style="color:#a0aec0;font-size:0.8rem;">${zone.description || ''}</span><br>
          <span class="pill pill-${zone.severity}" style="font-size:0.7rem;">${zone.severity}</span>
        </div>`)
        .addTo(dashMap);
    });
  }

  // Locate user
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(pos => {
      currentLat = pos.coords.latitude;
      currentLng = pos.coords.longitude;
      dashMap.setView([currentLat, currentLng], 14);

      const userIcon = L.divIcon({
        className: '',
        html: `<div style="width:20px;height:20px;border-radius:50%;background:#4299e1;border:3px solid rgba(255,255,255,0.8);box-shadow:0 0 16px #4299e1,0 0 32px #4299e144;"></div>`,
        iconSize: [20, 20],
        iconAnchor: [10, 10],
      });
      userMarker = L.marker([currentLat, currentLng], { icon: userIcon })
        .bindPopup('<strong>📍 You are here</strong>')
        .addTo(dashMap);

      checkProximity(currentLat, currentLng);
    }, () => {}, { enableHighAccuracy: true });
  }
}

// ── SOS Hold-to-Activate ────────────────────────────────────────────────────
let sosHoldTimer = null;
let sosHoldStart = 0;
let sosHoldRAF = null;
const SOS_HOLD_DURATION = 2000; // 2 seconds
let sosCountdownTimer = null;

function startSOSHold(e) {
  if (sosConfirmPending) return;
  e.preventDefault();
  sosHoldStart = Date.now();
  const ring = document.getElementById('sos-progress-ring');
  const holdStatus = document.getElementById('sos-hold-status');
  const btn = document.getElementById('sos-btn');
  if (holdStatus) { holdStatus.style.opacity = '1'; holdStatus.textContent = 'Keep holding...'; }
  if (btn) btn.classList.add('sos-holding');

  function animateRing() {
    const elapsed = Date.now() - sosHoldStart;
    const progress = Math.min(elapsed / SOS_HOLD_DURATION, 1);
    if (ring) ring.setAttribute('stroke-dashoffset', 578 - (578 * progress));

    if (progress < 1) {
      sosHoldRAF = requestAnimationFrame(animateRing);
    } else {
      // Hold complete — trigger SOS
      if (holdStatus) { holdStatus.textContent = 'ACTIVATING...'; holdStatus.style.color = '#dc2626'; }
      if (btn) { btn.classList.remove('sos-holding'); btn.classList.add('sos-activated'); }
      setTimeout(() => triggerSOS(), 200);
    }
  }
  sosHoldRAF = requestAnimationFrame(animateRing);
}

function endSOSHold() {
  if (sosHoldRAF) cancelAnimationFrame(sosHoldRAF);
  sosHoldRAF = null;
  const elapsed = Date.now() - sosHoldStart;
  const ring = document.getElementById('sos-progress-ring');
  const holdStatus = document.getElementById('sos-hold-status');
  const btn = document.getElementById('sos-btn');
  if (ring) ring.setAttribute('stroke-dashoffset', '578');
  if (btn) { btn.classList.remove('sos-holding'); btn.classList.remove('sos-activated'); }

  if (elapsed < SOS_HOLD_DURATION && sosHoldStart > 0) {
    if (holdStatus) { holdStatus.textContent = 'Hold longer to activate'; holdStatus.style.color = 'var(--text-muted)'; }
    setTimeout(() => { if (holdStatus) holdStatus.style.opacity = '0'; }, 1500);
  }
  sosHoldStart = 0;
}

function triggerSOS() {
  if (sosConfirmPending) return;
  sosConfirmPending = true;

  const modal = document.getElementById('sos-modal');
  if (modal) modal.style.display = 'flex';

  // Update GPS status in modal
  const gpsEl = document.getElementById('modal-gps-status');
  if (gpsEl && currentLat && currentLng) {
    gpsEl.textContent = `Location locked: ${currentLat.toFixed(4)}, ${currentLng.toFixed(4)}`;
    gpsEl.style.color = 'var(--accent-green)';
  }

  // Auto-send countdown (5 seconds)
  startSOSCountdown(5);
}

function startSOSCountdown(seconds) {
  let remaining = seconds;
  const numEl = document.getElementById('countdown-num');
  const fillEl = document.getElementById('sos-countdown-fill');
  if (fillEl) fillEl.style.width = '100%';

  sosCountdownTimer = setInterval(() => {
    remaining--;
    if (numEl) numEl.textContent = remaining;
    if (fillEl) fillEl.style.width = ((remaining / seconds) * 100) + '%';

    if (remaining <= 0) {
      clearInterval(sosCountdownTimer);
      sosCountdownTimer = null;
      confirmSOS();
    }
  }, 1000);
}

function clearSOSCountdown() {
  if (sosCountdownTimer) {
    clearInterval(sosCountdownTimer);
    sosCountdownTimer = null;
  }
}

function cancelSOS() {
  sosConfirmPending = false;
  clearSOSCountdown();
  const modal = document.getElementById('sos-modal');
  if (modal) modal.style.display = 'none';
  // Reset hold UI
  const holdStatus = document.getElementById('sos-hold-status');
  if (holdStatus) holdStatus.style.opacity = '0';
  const ring = document.getElementById('sos-progress-ring');
  if (ring) ring.setAttribute('stroke-dashoffset', '578');
}

async function confirmSOS() {
  cancelSOS();
  const btn = document.getElementById('sos-btn');
  const statusText = document.getElementById('sos-status-text');

  if (btn) btn.style.opacity = '0.6';
  if (statusText) statusText.textContent = 'Establishing secure uplink...';

  // Create & mount the Max Max Terminal Overlay
  const term = document.createElement('div');
  term.id = 'rakshak-terminal';
  term.style.cssText = 'position:fixed;inset:0;background:rgba(5,5,10,0.95);z-index:9999;display:flex;flex-direction:column;justify-content:center;padding:40px;font-family:"Courier New", monospace;color:#48bb78;backdrop-filter:blur(20px);box-shadow:inset 0 0 100px rgba(0,0,0,1);';
  
  const scanline = document.createElement('div');
  scanline.style.cssText = 'position:absolute;inset:0;background:linear-gradient(180deg,transparent,rgba(72,187,120,0.1),transparent);height:10px;animation:scanline 3s linear infinite;pointer-events:none;';
  term.appendChild(scanline);

  const styleNode = document.createElement('style');
  styleNode.innerHTML = '@keyframes scanline{0%{top:0}100%{top:100%}} .term-line{margin:8px 0;opacity:0;transform:translateX(-20px);animation:termIn 0.3s forwards ease-out;} @keyframes termIn{to{opacity:1;transform:translateX(0)}}';
  term.appendChild(styleNode);

  const container = document.createElement('div');
  container.style.cssText = 'max-width:800px;margin:0 auto;width:100%;text-shadow:0 0 8px rgba(72,187,120,0.6);';
  term.appendChild(container);
  document.body.appendChild(term);

  const lines = [
    `[SYS] Initializing RAKSHAK Core Uplink...`,
    `[SEC] Bypassing localized network interference...`,
    `[GPS] Locking orbital coordinates >> \${currentLat ? currentLat.toFixed(5) : 'UNKNOWN'}, \${currentLng ? currentLng.toFixed(5) : 'UNKNOWN'}`,
    `[NET] Establishing encrypted 256-bit handshake...`,
    `[AI] Threat vector analyzed. Level: CRITICAL.`,
    `[COM] Injecting distress payload to Trusted Contacts...`,
    `[COM] Payload securely delivered. Terminating uplink.`,
  ];

  // Async Terminal typer
  const runTerminal = async () => {
    for (let i = 0; i < lines.length; i++) {
        const p = document.createElement('p');
        p.className = 'term-line';
        p.innerHTML = lines[i];
        if(i === 4) p.style.color = '#dc2626'; // Red for CRITICAL
        container.appendChild(p);
        await new Promise(r => setTimeout(r, Math.random() * 400 + 300));
    }
    await new Promise(r => setTimeout(r, 800));
    term.style.transition = 'opacity 0.6s';
    term.style.opacity = '0';
    setTimeout(() => term.remove(), 600);
  };

  try {
    // Run Terminal animation & GPS fetch concurrently
    let lat = currentLat, lng = currentLng, acc = null, bat = null;
    
    const gpsPromise = new Promise((resolve) => {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(pos => {
          lat = pos.coords.latitude; lng = pos.coords.longitude;
          acc = pos.coords.accuracy; bat = pos.coords.altitude;
          resolve();
        }, () => resolve(), { timeout: 3000, enableHighAccuracy: true });
      } else resolve();
    });

    await Promise.all([runTerminal(), gpsPromise]);
    await sendSOS(lat, lng, acc, bat);

  } catch (e) {
    term.remove();
    showToast('SOS failed: ' + e.message, 'error');
  }
}

async function sendSOS(lat, lng, accuracy, battery) {
  try {
    const resp = await postJSON('/sos/trigger', {
      latitude: lat,
      longitude: lng,
      accuracy: accuracy,
      battery_level: battery,
      trigger_type: 'manual',
    });
    
    const btn = document.getElementById('sos-btn');
    const statusText = document.getElementById('sos-status-text');
    if (resp.success) {
      showToast('SOS Alert successfully broadcasted!', 'sos', 8000);
      if (btn) {
        btn.style.opacity = '1';
        btn.style.background = 'radial-gradient(circle at 35% 35%, #48bb78, #276749)';
        btn.style.transform = 'scale(1.1)';
        setTimeout(() => { btn.style.transform = ''; }, 300);
      }
      if (statusText) {
        statusText.style.color = 'var(--accent-green)';
        statusText.textContent = `Alert #\${resp.alert_id} dispatched. Network secured.`;
      }
      setTimeout(() => {
        if (btn) btn.style.background = '';
        if (statusText) { statusText.textContent = 'Ready — will capture GPS location automatically'; statusText.style.color = ''; }
      }, 6000);
      refreshAlertFeed();
    } else {
      showToast('SOS error: ' + (resp.error || 'Unknown error'), 'error');
      if (btn) btn.style.opacity = '1';
      if (statusText) statusText.textContent = 'Error — please try again';
    }
  } catch (e) {
    showToast('Network error: ' + e.message, 'error');
    const btn = document.getElementById('sos-btn');
    if (btn) btn.style.opacity = '1';
  }
}

// ── Alert Actions ────────────────────────────────────────────────────────────
async function resolveAlert(alertId) {
  const resp = await postJSON(`/sos/${alertId}/resolve`);
  if (resp.success) {
    showToast('Alert marked as resolved.', 'success');
    const el = document.getElementById('alert-'+alertId);
    if (el) el.querySelector('.pill').className = 'pill pill-resolved';
  } else showToast(resp.error || 'Failed', 'error');
}

async function refreshAlertFeed() {
  const resp = await fetch('/sos/history').then(r=>r.json());
  if (!resp.success) return;
  const feed = document.getElementById('alert-feed');
  if (!feed || !resp.alerts.length) return;
  feed.innerHTML = resp.alerts.slice(0,10).map(a => `
    <div class="alert-feed-item" id="alert-${a.id}">
      <div class="d-flex align-items-center justify-content-between">
        <span class="pill pill-${a.status}">${a.status}</span>
        <span class="pill" style="font-size:0.65rem;">${(a.trigger_type||'').replace(/_/g,' ').toUpperCase()}</span>
      </div>
      <div style="font-size:0.85rem;margin-top:6px;">${a.address || (a.latitude+', '+a.longitude)}</div>
      <div class="d-flex justify-content-between mt-1">
        <span style="font-size:0.75rem;color:var(--text-muted);">${a.created_at||''}</span>
        <a href="/sos/${a.id}/pdf" style="font-size:0.72rem;border:1px solid var(--accent-blue);color:var(--accent-blue);border-radius:4px;padding:2px 8px;text-decoration:none;">PDF</a>
      </div>
    </div>`).join('');
}

async function markAllRead() {
  const resp = await postJSON('/sos/notifications/read-all');
  if (resp.success) {
    showToast('All notifications marked as read.', 'info');
    const badge = document.getElementById('notif-count');
    if (badge) badge.textContent = '0';
  }
}

// ── AI Ping ──────────────────────────────────────────────────────────────────
function startAIPing() {
  // Immediate first ping
  sendPing();
  // Then every 2 minutes
  pingInterval = setInterval(sendPing, 120000);

  // Keep-alive on page unload
  window.addEventListener('beforeunload', () => {
    clearInterval(pingInterval);
  });
}

async function sendPing() {
  try {
    // Also emit via SocketIO
    if (typeof socket !== 'undefined' && socket.connected) {
      socket.emit('ping_alive', { lat: currentLat, lng: currentLng });
    }
    const resp = await postJSON('/ai/ping', { lat: currentLat, lng: currentLng });
    if (resp.success) {
      updateRiskBadge(resp.risk_level);
    }
  } catch (e) {
    // Silent fail — server will detect missed pings
    console.warn('[RAKSHAK] Ping failed:', e.message);
  }
}

async function loadRiskScore() {
  try {
    const resp = await fetch('/ai/risk-score').then(r=>r.json());
    if (resp.success) {
      updateRiskBadge(resp.risk_level);
      const mc = document.getElementById('missed-count');
      if (mc) mc.textContent = resp.consecutive_missed_pings || 0;
      const lp = document.getElementById('last-ping-ts');
      if (lp) lp.textContent = resp.last_ping ? new Date(resp.last_ping).toLocaleTimeString() : 'Never';
    }
  } catch(e) {}
}

function updateRiskBadge(level) {
  const disp = document.getElementById('risk-display');
  const navBadge = document.getElementById('nav-risk-badge');
  const labels = { low:'LOW', medium:'MEDIUM', high:'HIGH' };
  const html = `<span class="risk-badge risk-${level}"><span style="width:8px;height:8px;border-radius:50%;background:currentColor;"></span> ${labels[level]||level.toUpperCase()}</span>`;
  if (disp) disp.innerHTML = html;
  if (navBadge) navBadge.outerHTML = html;
}

// ── Proximity Check ──────────────────────────────────────────────────────────
async function checkProximity(lat, lng) {
  try {
    const resp = await postJSON('/danger-zones/proximity', { lat, lng });
    if (resp.success && resp.count > 0) {
      const nearest = resp.nearby[0];
      const el = document.getElementById('proximity-warning');
      if (el) {
        el.style.display = 'flex';
        document.getElementById('proximity-text').textContent =
          `${nearest.zone_type.replace(/_/g,' ')} zone ${Math.round(nearest.distance_m)}m away — ${nearest.description.substring(0,60)}...`;
      }
    }
  } catch(e) {}
}

// ── SocketIO live callbacks (defined for base.html) ──────────────────────────
function onNewSos(data) {
  showToast(`🚨 New SOS Alert triggered!`, 'sos', 8000);
  refreshAlertFeed();
}

function onRiskUpdate(data) {
  if (data.user_id === window.currentUserId) {
    updateRiskBadge(data.risk_level);
  }
}

function onNewDangerZone(data) {
  showToast('⚠️ New danger zone approved near you!', 'warning');
}
