/**
 * RAKSHAK Dashboard JS
 * Handles: Leaflet map, SOS trigger, AI ping, alert feed, SocketIO updates
 */

let dashMap = null;
let userMarker = null;
let currentLat = null, currentLng = null;
let sosConfirmPending = false;
let pingInterval = null;
let previousRiskLevel = null;

function initDashboard(dangerZones, userAlerts) {
  initMap(dangerZones);
  startAIPing();
  loadRiskScore();
  animateStatCounters();
  initScrollReveal();
  initRealtimeClock();
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
  }, { threshold: 0.02, rootMargin: '0px 0px 50px 0px' });
  document.querySelectorAll('.animate-in').forEach((el, i) => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(12px)';
    el.style.transition = `opacity .25s ${i * 0.03}s ease-out, transform .25s ${i * 0.03}s ease-out`;
    observer.observe(el);
  });
}

// ── Ultra Premium Leaflet Map Engine ──────────────────────────────────────────
function initMap(dangerZones) {
  dashMap = L.map('map', { zoomControl: false, attributionControl: false });

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19
  }).addTo(dashMap);

  dashMap.setView([20.5937, 78.9629], 5); // Default: India

  // Dynamic HUD Coordinate Tracking
  dashMap.on('mousemove', (e) => {
    const elLat = document.getElementById('map-target-lat');
    const elLng = document.getElementById('map-target-lng');
    if(elLat) elLat.textContent = `LAT: ${e.latlng.lat.toFixed(5)}`;
    if(elLng) elLng.textContent = `LNG: ${e.latlng.lng.toFixed(5)}`;
  });
  dashMap.on('move', () => {
    const center = dashMap.getCenter();
    const elLat = document.getElementById('map-target-lat');
    const elLng = document.getElementById('map-target-lng');
    if(!document.querySelector(':hover')) { // Update to center if mouse is not over
      if(elLat) elLat.textContent = `LAT: ${center.lat.toFixed(5)}`;
      if(elLng) elLng.textContent = `LNG: ${center.lng.toFixed(5)}`;
    }
  });

  // Add danger zones as glowing tactical nodes
  if (dangerZones) {
    dangerZones.forEach(zone => {
      const icon = L.divIcon({
        className: '',
        html: `<div style="width:24px;height:24px;display:flex;align-items:center;justify-content:center;position:relative;">
                 <div style="position:absolute;width:100%;height:100%;border:1px solid #fff;border-radius:50%;animation:sos-pulse 1.5s infinite;"></div>
                 <div style="width:6px;height:6px;background:#fff;border-radius:50%;box-shadow:0 0 10px #fff;"></div>
               </div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });
      L.marker([zone.latitude, zone.longitude], { icon })
        .bindPopup(`<div style="font-family:'Space Grotesk',sans-serif;background:rgba(10,10,15,0.9);border:1px solid #7c3aed;padding:8px;border-radius:6px;color:#fff;">
          <strong style="color:#8b5cf6;letter-spacing:0.1em;border-bottom:1px solid rgba(124,58,237,0.3);padding-bottom:4px;display:block;margin-bottom:6px;">${zone.zone_type ? zone.zone_type.replace(/_/g,' ').toUpperCase() : 'THREAT DETECTED'}</strong>
          <span style="color:rgba(255,255,255,0.7);font-size:0.75rem;font-family:'Courier New',monospace;">${zone.description || 'Verified danger zone'}</span><br>
          <div style="margin-top:6px;background:rgba(124,58,237,0.2);color:#8b5cf6;font-size:0.65rem;padding:2px 6px;display:inline-block;border-radius:4px;font-weight:700;">${zone.severity.toUpperCase()} PRIORITY</div>
        </div>`, { closeButton: false, className: 'tactical-popup' })
        .addTo(dashMap);
    });
  }

  // Locate user with targeting reticle
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(pos => {
      currentLat = pos.coords.latitude;
      currentLng = pos.coords.longitude;
      dashMap.setView([currentLat, currentLng], 15);

      const userIcon = L.divIcon({
        className: '',
        html: `<div style="position:relative;width:40px;height:40px;display:flex;align-items:center;justify-content:center;">
                 <div style="position:absolute;width:100%;height:100%;border:2px dashed #8b5cf6;border-radius:50%;animation:radarSpin 8s linear infinite;"></div>
                 <div style="position:absolute;width:20px;height:20px;border:2px solid #8b5cf6;border-radius:50%;"></div>
                 <div style="position:absolute;width:2px;height:2px;background:#fff;box-shadow:0 0 10px #fff;"></div>
                 <div style="position:absolute;top:-5px;bottom:-5px;width:1px;background:rgba(139,92,246,0.6);"></div>
                 <div style="position:absolute;left:-5px;right:-5px;height:1px;background:rgba(139,92,246,0.6);"></div>
               </div>`,
        iconSize: [40, 40],
        iconAnchor: [20, 20],
      });
      userMarker = L.marker([currentLat, currentLng], { icon: userIcon })
        .bindPopup('<strong style="font-family:\'Space Grotesk\',sans-serif;color:#8b5cf6;letter-spacing:0.1em;">ASSET LOCATED</strong>', { closeButton: false, className: 'tactical-popup' })
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
      if (holdStatus) { holdStatus.textContent = 'ACTIVATING...'; holdStatus.style.color = '#7c3aed'; }
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

  // Activate panic mode
  document.body.classList.add('panic-mode');

  // Create & mount the Max Max Terminal Overlay
  const term = document.createElement('div');
  term.id = 'rakshak-terminal';
  term.style.cssText = 'position:fixed;inset:0;background:rgba(5,5,10,0.95);z-index:9999;display:flex;flex-direction:column;justify-content:center;padding:40px;font-family:"Courier New", monospace;color:#ef4444;backdrop-filter:blur(20px);box-shadow:inset 0 0 100px rgba(0,0,0,1);';

  // Matrix rain canvas background
  const matrixCanvas = document.createElement('canvas');
  matrixCanvas.className = 'matrix-rain-canvas';
  term.appendChild(matrixCanvas);
  startMatrixRain(matrixCanvas);

  const scanline = document.createElement('div');
  scanline.style.cssText = 'position:absolute;inset:0;background:linear-gradient(180deg,transparent,rgba(239,68,68,0.1),transparent);height:10px;animation:scanline 3s linear infinite;pointer-events:none;';
  term.appendChild(scanline);

  const styleNode = document.createElement('style');
  styleNode.innerHTML = '@keyframes scanline{0%{top:0}100%{top:100%}} .term-line{margin:8px 0;opacity:0;transform:translateX(-20px);animation:termIn 0.3s forwards ease-out;} @keyframes termIn{to{opacity:1;transform:translateX(0)}}';
  term.appendChild(styleNode);

  const container = document.createElement('div');
  container.style.cssText = 'max-width:800px;margin:0 auto;width:100%;text-shadow:0 0 8px rgba(139,92,246,0.6);position:relative;z-index:1;';
  term.appendChild(container);
  document.body.appendChild(term);

  const lines = [
    `[SYS] Initializing RAKSHAK Core Uplink...`,
    `[SEC] Bypassing localized network interference...`,
    `[GPS] Locking orbital coordinates >> \${currentLat ? currentLat.toFixed(5) : 'UNKNOWN'}, \${currentLng ? currentLng.toFixed(5) : 'UNKNOWN'}`,
    `[NET] Establishing encrypted 256-bit handshake...`,
    `[SYS] Threat vector analyzed. Level: CRITICAL.`,
    `[COM] Injecting distress payload to Trusted Contacts...`,
    `[COM] Payload securely delivered. Terminating uplink.`,
  ];

  // Async Terminal typer with blinking cursor
  const runTerminal = async () => {
    // Add initial cursor
    const cursorEl = document.createElement('span');
    cursorEl.className = 'term-cursor';
    container.appendChild(cursorEl);

    for (let i = 0; i < lines.length; i++) {
        // Remove cursor before adding line
        if (cursorEl.parentNode) cursorEl.remove();
        const p = document.createElement('p');
        p.className = 'term-line';
        p.innerHTML = lines[i];
        if(i === 4) p.style.color = '#7c3aed'; // Red for CRITICAL
        container.appendChild(p);
        // Add cursor after last line
        container.appendChild(cursorEl);
        await new Promise(r => setTimeout(r, Math.random() * 400 + 300));
    }
    await new Promise(r => setTimeout(r, 800));
    term.style.transition = 'opacity 0.6s';
    term.style.opacity = '0';
    setTimeout(() => {
      term.remove();
      // Remove panic mode after a delay
      setTimeout(() => document.body.classList.remove('panic-mode'), 6000);
    }, 600);
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
        btn.style.background = 'radial-gradient(circle at 35% 35%, #ef4444, #276749)';
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

  // Sound alert when risk transitions to HIGH
  if (level === 'high' && previousRiskLevel !== 'high') {
    playRiskAlertBeep();
  }
  previousRiskLevel = level;
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

// ── Web Audio API: Risk Alert Beep ────────────────────────────────────────────
function playRiskAlertBeep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    // Two-tone alert: high-low-high pattern
    const freqs = [880, 660, 880];
    const durations = [0.15, 0.15, 0.2];
    let offset = 0;
    freqs.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'square';
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.15, ctx.currentTime + offset);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + offset + durations[i]);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(ctx.currentTime + offset);
      osc.stop(ctx.currentTime + offset + durations[i]);
      offset += durations[i] + 0.05;
    });
    // Clean up context after sounds finish
    setTimeout(() => ctx.close(), 1500);
  } catch(e) {
    console.warn('[RAKSHAK] Audio alert failed:', e.message);
  }
}

// ── Matrix Rain Effect ────────────────────────────────────────────────────────
function startMatrixRain(canvas) {
  const ctx = canvas.getContext('2d');
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;

  const chars = 'RAKSHAKSOS01アイウエオカキ警報安全'.split('');
  const fontSize = 14;
  const columns = Math.floor(canvas.width / fontSize);
  const drops = new Array(columns).fill(1);

  let animId = null;
  function draw() {
    ctx.fillStyle = 'rgba(5, 5, 10, 0.05)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#ef4444';
    ctx.font = fontSize + 'px monospace';

    for (let i = 0; i < drops.length; i++) {
      const text = chars[Math.floor(Math.random() * chars.length)];
      ctx.fillStyle = Math.random() > 0.95 ? '#7c3aed' : 'rgba(239,68,68, 0.7)';
      ctx.fillText(text, i * fontSize, drops[i] * fontSize);

      if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
        drops[i] = 0;
      }
      drops[i]++;
    }
    animId = requestAnimationFrame(draw);
  }
  draw();

  // Stop when canvas is removed
  const observer = new MutationObserver(() => {
    if (!document.contains(canvas)) {
      cancelAnimationFrame(animId);
      observer.disconnect();
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
}

// ── Real-time Clock ───────────────────────────────────────────────────────────
function initRealtimeClock() {
  // Look for greeting bar
  const greetingBar = document.querySelector('.dash-greeting');
  if (!greetingBar) return;

  // Check if clock already exists
  if (document.getElementById('realtime-clock')) return;

  const clockEl = document.createElement('span');
  clockEl.id = 'realtime-clock';
  clockEl.className = 'realtime-clock';
  clockEl.style.marginLeft = '12px';
  greetingBar.appendChild(clockEl);

  function updateClock() {
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    const s = String(now.getSeconds()).padStart(2, '0');
    clockEl.textContent = `[ ${h}:${m}:${s} ]`;
  }
  updateClock();
  setInterval(updateClock, 1000);
}
