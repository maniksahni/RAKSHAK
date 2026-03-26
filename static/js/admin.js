/**
 * RAKSHAK Admin Dashboard JS
 * Chart.js analytics, Live SOS map, User table, Danger Zone approvals
 */

let adminMap = null;
let alertMarkers = {};
Chart.defaults.color = '#a0aec0';
Chart.defaults.font.family = 'Inter, sans-serif';

function initAdmin(recentAlerts, dangerZones) {
  initAdminMap(recentAlerts, dangerZones);
  loadAnalytics();
  loadUsers();
  loadPendingZones();
  animateAdminCounters();
  initAdminScrollReveal();
  setInterval(refreshAlertFeed, 30000); // auto-refresh feed every 30s
}

// ── Animated Counters ─────────────────────────────────────────────────────────
function animateAdminCounters() {
  document.querySelectorAll('.stat-number').forEach(el => {
    const text = el.textContent.trim();
    const val = parseInt(text);
    if (isNaN(val) || val === 0) return;
    el.textContent = '0';
    const duration = 1000;
    const start = performance.now();
    function tick(now) {
      const t = Math.min((now - start) / duration, 1);
      const ease = 1 - Math.pow(1 - t, 3);
      el.textContent = Math.round(val * ease);
      if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });
}

// ── Scroll Reveal ─────────────────────────────────────────────────────────────
function initAdminScrollReveal() {
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
    el.style.transition = `opacity .5s ${i * 0.05}s cubic-bezier(.22,1,.36,1), transform .5s ${i * 0.05}s cubic-bezier(.22,1,.36,1)`;
    observer.observe(el);
  });
}

// ── Admin Leaflet Map ─────────────────────────────────────────────────────────
function initAdminMap(alerts, zones) {
  adminMap = L.map('admin-map', { zoomControl: true, attributionControl: false });
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19
  }).addTo(adminMap);
  adminMap.setView([20.5937, 78.9629], 5);

  // SOS alert markers (red)
  if (alerts) {
    alerts.forEach(a => {
      if (!a.latitude || !a.longitude) return;
      const icon = L.divIcon({
        className: '',
        html: `<div style="width:18px;height:18px;border-radius:50%;background:#dc2626;border:2px solid rgba(255,255,255,0.4);box-shadow:0 0 12px #dc2626,0 0 24px #dc262644;${a.status==='active'?'animation:sos-pulse 1.5s infinite;':''}"></div>`,
        iconSize: [18, 18], iconAnchor: [9, 9],
      });
      const m = L.marker([a.latitude, a.longitude], { icon })
        .bindPopup(`
          <div style="font-family:Inter,sans-serif;min-width:180px;">
            <strong style="color:#dc2626;">🚨 ${a.full_name||'User'}</strong><br>
            <span style="font-size:0.8rem;color:#a0aec0;">${a.phone||''}</span><br>
            <span style="font-size:0.78rem;">${a.address||`${a.latitude},${a.longitude}`}</span><br>
            <span class="pill pill-${a.status}" style="font-size:0.7rem;">${a.status}</span>
          </div>`)
        .addTo(adminMap);
      alertMarkers[a.id] = m;
    });
  }

  // Danger zone markers (amber)
  if (zones) {
    zones.forEach(z => {
      if (!z.latitude || !z.longitude) return;
      const icon = L.divIcon({
        className: '',
        html: `<div style="width:14px;height:14px;border-radius:50%;background:#f6ad55;border:2px solid rgba(255,255,255,0.3);box-shadow:0 0 8px #f6ad55;"></div>`,
        iconSize: [14, 14], iconAnchor: [7, 7],
      });
      L.marker([z.latitude, z.longitude], { icon })
        .bindPopup(`<div style="font-family:Inter,sans-serif;"><strong style="color:#f6ad55;">⚠️ ${(z.zone_type||'zone').replace(/_/g,' ').toUpperCase()}</strong><br><span style="font-size:0.8rem;">${z.description||''}</span></div>`)
        .addTo(adminMap);
    });
  }
}

// ── Analytics Charts ──────────────────────────────────────────────────────────
async function loadAnalytics() {
  try {
    const resp = await fetch('/admin/analytics').then(r=>r.json());
    if (!resp.success) return;

    const gridColor = 'rgba(255,255,255,0.05)';
    const tickColor = '#6b7280';

    // 1. Alerts per day — gradient bar chart
    const daysData = resp.alerts_per_day || [];
    const alertsCtx = document.getElementById('chart-alerts-day').getContext('2d');
    const alertGrad = alertsCtx.createLinearGradient(0, 0, 0, 200);
    alertGrad.addColorStop(0, 'rgba(220,38,38,0.8)');
    alertGrad.addColorStop(1, 'rgba(220,38,38,0.15)');
    new Chart(alertsCtx, {
      type: 'bar',
      data: {
        labels: daysData.map(d => d.date),
        datasets: [{
          label: 'Alerts', data: daysData.map(d => d.count),
          backgroundColor: alertGrad,
          borderColor: '#dc2626', borderWidth: 1, borderRadius: 6,
          hoverBackgroundColor: 'rgba(220,38,38,0.9)',
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        animation: { duration: 1200, easing: 'easeOutQuart' },
        plugins: { legend: { display: false },
          tooltip: { backgroundColor: 'rgba(15,15,26,0.95)', borderColor: '#dc2626', borderWidth: 1,
            titleFont: { family: 'Rajdhani', weight: '700' }, padding: 12, cornerRadius: 8 }
        },
        scales: {
          x: { grid: { color: gridColor, drawBorder: false }, ticks: { color: tickColor, maxRotation: 30 } },
          y: { grid: { color: gridColor, drawBorder: false }, ticks: { color: tickColor } }
        }
      }
    });

    // 2. Peak hours — area chart with gradient
    const hours = Array.from({length:24},(_,i)=>i);
    const hoursMap = Object.fromEntries((resp.peak_hours||[]).map(h=>[h.hour, h.count]));
    const peakCtx = document.getElementById('chart-peak-hours').getContext('2d');
    const peakGrad = peakCtx.createLinearGradient(0, 0, 0, 200);
    peakGrad.addColorStop(0, 'rgba(246,173,85,0.3)');
    peakGrad.addColorStop(1, 'rgba(246,173,85,0.02)');
    new Chart(peakCtx, {
      type: 'line',
      data: {
        labels: hours.map(h => `${h}:00`),
        datasets: [{
          label: 'Alerts', data: hours.map(h => hoursMap[h]||0),
          borderColor: '#f6ad55', backgroundColor: peakGrad,
          fill: true, tension: 0.4, pointRadius: 2, pointHoverRadius: 6,
          pointBackgroundColor: '#f6ad55', pointBorderColor: '#0a0a0f',
          pointBorderWidth: 2, borderWidth: 2.5,
          pointHoverBackgroundColor: '#fff', pointHoverBorderColor: '#f6ad55',
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        animation: { duration: 1500, easing: 'easeOutQuart' },
        plugins: { legend: { display: false },
          tooltip: { backgroundColor: 'rgba(15,15,26,0.95)', borderColor: '#f6ad55', borderWidth: 1,
            titleFont: { family: 'Rajdhani', weight: '700' }, padding: 12, cornerRadius: 8 }
        },
        scales: {
          x: { grid: { color: gridColor, drawBorder: false }, ticks: { color: tickColor, maxTicksLimit: 8 } },
          y: { grid: { color: gridColor, drawBorder: false }, ticks: { color: tickColor } }
        },
        interaction: { intersect: false, mode: 'index' },
      }
    });

    // 3. Risk distribution — enhanced doughnut with center text
    const riskData = resp.risk_dist || [];
    const riskMap = Object.fromEntries(riskData.map(r=>[r.risk_level, r.count]));
    const totalRisk = (riskMap.low||0) + (riskMap.medium||0) + (riskMap.high||0);
    const riskCanvas = document.getElementById('chart-risk-dist');
    new Chart(riskCanvas, {
      type: 'doughnut',
      data: {
        labels: ['Low Risk','Medium Risk','High Risk'],
        datasets: [{
          data: [riskMap.low||0, riskMap.medium||0, riskMap.high||0],
          backgroundColor: ['rgba(72,187,120,0.8)','rgba(246,173,85,0.8)','rgba(220,38,38,0.8)'],
          borderColor: ['#48bb78','#f6ad55','#dc2626'],
          borderWidth: 2, hoverOffset: 12,
          hoverBorderWidth: 3,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        animation: { animateRotate: true, duration: 1200 },
        plugins: {
          legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true, pointStyle: 'circle' } },
          tooltip: { backgroundColor: 'rgba(15,15,26,0.95)', borderWidth: 1, cornerRadius: 8, padding: 12 }
        },
        cutout: '70%',
      },
      plugins: [{
        id: 'centerText',
        beforeDraw: function(chart) {
          const ctx = chart.ctx;
          ctx.save();
          const cx = chart.chartArea.left + (chart.chartArea.right - chart.chartArea.left) / 2;
          const cy = chart.chartArea.top + (chart.chartArea.bottom - chart.chartArea.top) / 2;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.font = '800 1.6rem Rajdhani, sans-serif';
          ctx.fillStyle = '#f7fafc';
          ctx.fillText(totalRisk, cx, cy - 8);
          ctx.font = '500 0.65rem Inter, sans-serif';
          ctx.fillStyle = '#4a5568';
          ctx.fillText('USERS', cx, cy + 12);
          ctx.restore();
        }
      }]
    });

    // 4. Alert status — horizontal bar with gradient
    const statusData = resp.alert_status || [];
    const statusMap = Object.fromEntries(statusData.map(s=>[s.status, s.count]));
    const statusCtx = document.getElementById('chart-alert-status').getContext('2d');
    new Chart(statusCtx, {
      type: 'bar',
      data: {
        labels: ['Active','Resolved','False Alarm'],
        datasets: [{
          data: [statusMap.active||0, statusMap.resolved||0, statusMap.false_alarm||0],
          backgroundColor: ['rgba(220,38,38,0.8)','rgba(72,187,120,0.8)','rgba(160,174,192,0.5)'],
          borderColor: ['#dc2626','#48bb78','#a0aec0'],
          borderWidth: 1.5, borderRadius: 6,
          hoverBackgroundColor: ['rgba(220,38,38,1)','rgba(72,187,120,1)','rgba(160,174,192,0.7)'],
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true, maintainAspectRatio: false,
        animation: { duration: 1000, easing: 'easeOutQuart' },
        plugins: { legend: { display: false },
          tooltip: { backgroundColor: 'rgba(15,15,26,0.95)', borderWidth: 1, cornerRadius: 8, padding: 12 }
        },
        scales: {
          x: { grid: { color: gridColor, drawBorder: false }, ticks: { color: tickColor } },
          y: { grid: { display: false }, ticks: { color: '#f7fafc', font: { weight: '600', size: 12 } } }
        }
      }
    });

  } catch (e) {
    console.warn('[RAKSHAK] Analytics failed:', e);
  }
}


// ── User Management ───────────────────────────────────────────────────────────
window.currentDossierId = null;

async function loadUsers(q='') {
  try {
    const url = '/admin/users' + (q ? `?q=${encodeURIComponent(q)}` : '');
    const resp = await fetch(url).then(r=>r.json());
    const tbody = document.getElementById('users-tbody');
    if (!resp.success || !tbody) return;

    // Cache user data globally for the modal
    if (!window.globalUsersMap) window.globalUsersMap = {};
    
    if (!resp.users.length) {
      tbody.innerHTML = `<tr><td colspan="8">
        <div class="empty-state" style="padding:40px;text-align:center;">
          <div style="width:80px;height:80px;border-radius:50%;border:1px dashed rgba(244,63,94,.5);margin:0 auto 20px;display:flex;align-items:center;justify-content:center;animation:spinSlow 10s linear infinite;">
            <i class="bi bi-radar" style="font-size:2rem;color:#f43f5e;animation:none;"></i>
          </div>
          <p style="font-family:'Courier New',monospace;color:rgba(255,255,255,0.5);letter-spacing:0.1em;font-size:0.8rem;text-transform:uppercase;">No operatives found on this frequency.</p>
        </div>
      </td></tr>`;
      return;
    }

    tbody.innerHTML = resp.users.map((u,i) => {
      window.globalUsersMap[u.id] = u;
      
      const roleStr = u.role || 'user';
      const riskStr = u.risk_level || 'low';
      const roleColor = roleStr === 'admin' ? '#f43f5e' : (roleStr === 'trusted_contact' ? '#818cf8' : '#22c55e');
      const riskClass = riskStr === 'high' ? 'danger' : (riskStr === 'medium' ? 'amber' : 'green');
      const statusIcon = u.is_active ? '<i class="bi bi-check-circle-fill" style="color:#22c55e;"></i> ACTIVE' : '<i class="bi bi-slash-circle-fill" style="color:#f43f5e;"></i> LOCKED';
      const initial = (u.full_name && u.full_name.length > 0) ? u.full_name[0].toUpperCase() : '?';
      
      return `
      <tr style="cursor:pointer;" onclick="openDossier(${u.id})">
        <td style="font-family:'Courier New',monospace;font-size:0.7rem;color:var(--text-muted);vertical-align:middle;">#${u.id}</td>
        <td style="vertical-align:middle;">
          <div class="d-flex align-items-center gap-2">
            <div style="width:28px;height:28px;border-radius:50%;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.15);display:flex;align-items:center;justify-content:center;font-size:.7rem;font-weight:700;">${initial}</div>
            <div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:0.9rem;letter-spacing:-.01em;">${u.full_name || 'Unknown'}</div>
          </div>
        </td>
        <td style="font-size:0.8rem;color:var(--text-secondary);font-family:'Courier New',monospace;vertical-align:middle;">${u.email || ''}</td>
        <td style="font-size:0.8rem;font-family:'Courier New',monospace;vertical-align:middle;">${u.phone || ''}</td>
        <td style="vertical-align:middle;">
          <span style="font-size:0.65rem;border:1px solid ${roleColor}40;background:${roleColor}10;color:${roleColor};padding:4px 10px;border-radius:20px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;">${roleStr.replace('_',' ')}</span>
        </td>
        <td style="vertical-align:middle;">
          <span class="threat-op-val" style="font-size:0.75rem;color:var(--accent-${riskClass});"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--accent-${riskClass});margin-right:4px;box-shadow:0 0 5px var(--accent-${riskClass});"></span>${riskStr.toUpperCase()}</span>
        </td>
        <td style="vertical-align:middle;font-size:0.7rem;font-weight:700;letter-spacing:.05em;">${statusIcon}</td>
        <td style="vertical-align:middle;">
          <button class="btn-holographic" style="font-size:0.7rem;padding:4px 12px;border-radius:8px;" onclick="openDossier(${u.id})">
            ACCESS DOSSIER <i class="bi bi-box-arrow-in-up-right ms-1"></i>
          </button>
        </td>
      </tr>`;
    }).join('');
  } catch(e) {
    console.warn('[RAKSHAK] Load users failed:', e);
  }
}

window.openDossier = function(uid) {
  const u = window.globalUsersMap[uid];
  if(!u) return;
  window.currentDossierId = uid;
  
  const initial = (u.full_name && u.full_name.length > 0) ? u.full_name[0].toUpperCase() : '?';
  document.getElementById('dos-avatar').textContent = initial;
  document.getElementById('dos-name').textContent = u.full_name || 'Unknown';
  document.getElementById('dos-id').textContent = 'UID: ' + u.id;
  document.getElementById('dos-email').textContent = u.email || 'N/A';
  document.getElementById('dos-phone').textContent = u.phone || 'N/A';
  
  const riskStr = u.risk_level || 'low';
  const roleStr = u.role || 'user';
  
  const riskColor = riskStr === 'high' ? '#f43f5e' : (riskStr === 'medium' ? '#f59e0b' : '#22c55e');
  const roleColor = roleStr === 'admin' ? '#f43f5e' : (roleStr === 'trusted_contact' ? '#818cf8' : '#22c55e');
  
  const riskEl = document.getElementById('dos-risk');
  riskEl.textContent = riskStr.toUpperCase();
  riskEl.style.color = riskColor;
  
  const roleEl = document.getElementById('dos-role');
  roleEl.textContent = roleStr.replace('_',' ');
  roleEl.style.color = roleColor;
  
  const statusEl = document.getElementById('dos-status');
  statusEl.textContent = u.is_active ? 'ACTIVE' : 'LOCKED';
  statusEl.style.color = u.is_active ? '#22c55e' : '#f43f5e';
  
  const pingEl = document.getElementById('dos-ping');
  const d = u.last_ping ? new Date(u.last_ping) : null;
  pingEl.textContent = d ? d.toLocaleString() : 'NO SIGNAL';
  
  const toggleBtn = document.getElementById('dos-btn-toggle');
  if(u.is_active) {
    toggleBtn.innerHTML = '<i class="bi bi-sign-stop me-2"></i>Lock Access';
    toggleBtn.style.color = '#f43f5e';
    toggleBtn.style.borderColor = 'rgba(244,63,94,.4)';
  } else {
    toggleBtn.innerHTML = '<i class="bi bi-shield-check me-2"></i>Restore Access';
    toggleBtn.style.color = '#22c55e';
    toggleBtn.style.borderColor = 'rgba(34,197,94,.4)';
  }
  
  // Open the custom side-panel dossier
  const sidePanel = document.getElementById('customDossierPanel');
  const overlay   = document.getElementById('customDossierOverlay');
  if (sidePanel) sidePanel.classList.add('open');
  if (overlay) overlay.classList.add('show');
}

window.closeDossier = function() {
  const sidePanel = document.getElementById('customDossierPanel');
  const overlay   = document.getElementById('customDossierOverlay');
  if (sidePanel) sidePanel.classList.remove('open');
  if (overlay) overlay.classList.remove('show');
}

let searchTimeout;
function searchUsers(q) {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => loadUsers(q), 400);
}

window.toggleUser = async function(uid) {
  const resp = await fetch(`/admin/users/${uid}/toggle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  }).then(r=>r.json());
  if (resp.success) {
    showToast(resp.is_active ? 'System Access Restored.' : 'System Access Locked.', 'info');
    loadUsers();
    // Refresh modal if open
    setTimeout(()=>{ if(window.globalUsersMap[uid]) { window.globalUsersMap[uid].is_active = resp.is_active; openDossier(uid); } }, 500);
  } else showToast(resp.error||'Failed','error');
}

window.changeRole = async function(uid, role) {
  const resp = await fetch(`/admin/users/${uid}/change-role`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({role: role})
  }).then(r=>r.json());
  if (resp.success) {
    showToast(`Role upgraded to ${role}.`, 'info');
    loadUsers();
    setTimeout(()=>{ if(window.globalUsersMap[uid]) { window.globalUsersMap[uid].role = role; openDossier(uid); } }, 500);
  } else showToast(resp.error||'Failed','error');
}

// ── Pending Danger Zones ──────────────────────────────────────────────────────
async function loadPendingZones() {
  try {
    const resp = await fetch('/admin/danger-zones/pending').then(r=>r.json());
    const container = document.getElementById('pending-zones-list');
    if (!container) return;

    if (!resp.success || !resp.zones.length) {
      container.innerHTML = `<div class="col-12">
      <div class="empty-state" style="padding:30px;text-align:center;">
        <div style="width:40px;height:40px;margin:0 auto 10px;border-radius:50%;background:rgba(34,197,94,0.1);display:flex;align-items:center;justify-content:center;box-shadow:0 0 20px rgba(34,197,94,0.2);">
          <i class="bi bi-shield-check" style="font-size:1.5rem;color:#22c55e;"></i>
        </div>
        <p style="font-family:'Courier New',monospace;color:rgba(34,197,94,0.7);letter-spacing:0.1em;font-size:0.75rem;text-transform:uppercase;margin:0;">Grid Secure. No Active Hostile Zones.</p>
      </div>
    </div>`;
      return;
    }

    container.innerHTML = resp.zones.map(z => `
      <div class="col-md-4" id="zone-card-${z.id}">
        <div class="glass-card p-3">
          <div class="d-flex align-items-center gap-2 mb-2">
            <span class="pill pill-medium">${z.zone_type.replace(/_/g,' ')}</span>
            <span class="pill pill-${z.severity}">${z.severity}</span>
          </div>
          <p style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:8px;">${z.description}</p>
          <p style="font-size:0.75rem;color:var(--text-muted);margin-bottom:12px;">
            <i class="bi bi-person me-1"></i>${z.reporter_name} &bull; ${z.created_at||''}
          </p>
          <div class="d-flex gap-2">
            <button onclick="approveZone(${z.id})" class="btn-rakshak" style="padding:6px 16px;font-size:0.8rem;flex:1;">✔ Approve</button>
            <button onclick="rejectZone(${z.id})" class="btn-glass" style="padding:6px 12px;font-size:0.8rem;color:var(--red-primary);">✘</button>
          </div>
        </div>
      </div>`).join('');
  } catch(e) {
    console.warn('[RAKSHAK] Pending zones failed:', e);
  }
}

async function approveZone(id) {
  const resp = await postJSON(`/admin/danger-zones/${id}/approve`);
  if (resp.success) {
    showToast('Danger zone approved!', 'success');
    const card = document.getElementById('zone-card-'+id);
    if (card) {
      card.style.transition = 'all .4s cubic-bezier(.22,1,.36,1)';
      card.style.opacity = '0';
      card.style.transform = 'scale(0.9) translateY(-10px)';
      setTimeout(() => card.remove(), 400);
    }
  } else showToast(resp.error||'Failed','error');
}

async function rejectZone(id) {
  const resp = await postJSON(`/admin/danger-zones/${id}/reject`);
  if (resp.success) {
    showToast('Zone rejected.', 'info');
    const card = document.getElementById('zone-card-'+id);
    if (card) {
      card.style.transition = 'all .4s cubic-bezier(.22,1,.36,1)';
      card.style.opacity = '0';
      card.style.transform = 'translateX(30px)';
      setTimeout(() => card.remove(), 400);
    }
  } else showToast(resp.error||'Failed','error');
}

// ── Alert Feed Refresh ────────────────────────────────────────────────────────
async function refreshAlertFeed() {
  try {
    const resp = await fetch('/admin/alerts-feed').then(r=>r.json());
    if (!resp.success) return;
    const feed = document.getElementById('admin-alert-feed');
    if (!feed) return;

    feed.innerHTML = resp.alerts.length ? resp.alerts.slice(0,20).map(a => `
      <div class="alert-feed-item" id="admin-alert-${a.id}">
        <div class="d-flex align-items-center justify-content-between mb-1">
          <strong style="font-size:0.85rem;">${a.full_name||'User'}</strong>
          <span class="pill pill-${(a.trigger_type||'').replace(/_/g,'-')}" style="font-size:0.65rem;">${(a.trigger_type||'').replace(/_/g,' ')}</span>
        </div>
        <div style="font-size:0.78rem;color:var(--text-muted);">${a.address||`${a.latitude},${a.longitude}`}</div>
        <div class="d-flex align-items-center justify-content-between mt-1">
          <span class="pill pill-${a.status}" style="font-size:0.65rem;">${a.status}</span>
          ${a.status==='active' ? `<button onclick="adminResolve(${a.id})" style="background:none;border:1px solid var(--accent-green);color:var(--accent-green);border-radius:4px;padding:2px 8px;font-size:0.7rem;cursor:pointer;">Resolve</button>` : ''}
        </div>
      </div>`).join('')
      : `<div class="empty-state"><i class="bi bi-inbox"></i><p>No alerts.</p></div>`;
  } catch(e) {}
}

async function adminResolve(id) {
  const resp = await postJSON(`/admin/alerts/${id}/resolve`);
  if (resp.success) { showToast('Alert resolved.','success'); refreshAlertFeed(); }
  else showToast(resp.error||'Failed','error');
}

function refreshAll() {
  refreshAlertFeed();
  loadUsers();
  loadPendingZones();
  showToast('Dashboard refreshed!','info',2000);
}

// ── SocketIO Callbacks ────────────────────────────────────────────────────────
function onNewSos(data) {
  const a = data.alert;
  showToast(`🚨 SOS from User #${a.user_id}`, 'sos', 8000);
  refreshAlertFeed();

  // Add marker to map
  if (adminMap && a.latitude && a.longitude) {
    const icon = L.divIcon({
      className:'',
      html:`<div style="width:22px;height:22px;border-radius:50%;background:#dc2626;border:3px solid white;box-shadow:0 0 20px #dc2626;animation:sos-pulse 1s infinite;"></div>`,
      iconSize:[22,22],iconAnchor:[11,11],
    });
    L.marker([a.latitude,a.longitude],{icon})
      .bindPopup(`<strong style="color:#dc2626;">🚨 New SOS Alert!</strong><br>User #${a.user_id}`)
      .addTo(adminMap).openPopup();
    adminMap.setView([a.latitude,a.longitude],14);
  }
}

function onRiskUpdate(data) {
  showToast(`Risk level update: User #${data.user_id} → ${data.risk_level.toUpperCase()}`, 'warning', 4000);
}

function onNewDangerZone(data) {
  showToast('⚠️ New danger zone approved!','warning');
  loadPendingZones();
}
