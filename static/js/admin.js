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
  setInterval(refreshAlertFeed, 30000); // auto-refresh feed every 30s
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

    // 1. Alerts per day
    const daysData = resp.alerts_per_day || [];
    new Chart(document.getElementById('chart-alerts-day'), {
      type: 'bar',
      data: {
        labels: daysData.map(d => d.date),
        datasets: [{
          label: 'Alerts', data: daysData.map(d => d.count),
          backgroundColor: 'rgba(220,38,38,0.6)',
          borderColor: '#dc2626', borderWidth: 1, borderRadius: 4,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: gridColor }, ticks: { color: tickColor, maxRotation: 30 } },
          y: { grid: { color: gridColor }, ticks: { color: tickColor } }
        }
      }
    });

    // 2. Peak hours
    const hours = Array.from({length:24},(_,i)=>i);
    const hoursMap = Object.fromEntries((resp.peak_hours||[]).map(h=>[h.hour, h.count]));
    new Chart(document.getElementById('chart-peak-hours'), {
      type: 'line',
      data: {
        labels: hours.map(h => `${h}:00`),
        datasets: [{
          label: 'Alerts', data: hours.map(h => hoursMap[h]||0),
          borderColor: '#f6ad55', backgroundColor: 'rgba(246,173,85,0.12)',
          fill: true, tension: 0.4, pointRadius: 3, pointHoverRadius: 5,
          pointBackgroundColor: '#f6ad55',
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: gridColor }, ticks: { color: tickColor, maxTicksLimit: 8 } },
          y: { grid: { color: gridColor }, ticks: { color: tickColor } }
        }
      }
    });

    // 3. Risk distribution (doughnut)
    const riskData = resp.risk_dist || [];
    const riskMap = Object.fromEntries(riskData.map(r=>[r.risk_level, r.count]));
    new Chart(document.getElementById('chart-risk-dist'), {
      type: 'doughnut',
      data: {
        labels: ['Low','Medium','High'],
        datasets: [{
          data: [riskMap.low||0, riskMap.medium||0, riskMap.high||0],
          backgroundColor: ['rgba(72,187,120,0.7)','rgba(246,173,85,0.7)','rgba(220,38,38,0.7)'],
          borderColor: ['#48bb78','#f6ad55','#dc2626'],
          borderWidth: 1.5, hoverOffset: 8,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { padding: 16 } } },
        cutout: '65%',
      }
    });

    // 4. Alert status breakdown
    const statusData = resp.alert_status || [];
    const statusMap = Object.fromEntries(statusData.map(s=>[s.status, s.count]));
    new Chart(document.getElementById('chart-alert-status'), {
      type: 'bar',
      data: {
        labels: ['Active','Resolved','False Alarm'],
        datasets: [{
          data: [statusMap.active||0, statusMap.resolved||0, statusMap.false_alarm||0],
          backgroundColor: ['rgba(220,38,38,0.7)','rgba(72,187,120,0.7)','rgba(160,174,192,0.4)'],
          borderColor: ['#dc2626','#48bb78','#a0aec0'],
          borderWidth: 1, borderRadius: 4,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: gridColor }, ticks: { color: tickColor } },
          y: { grid: { color: gridColor }, ticks: { color: tickColor } }
        }
      }
    });

  } catch (e) {
    console.warn('[RAKSHAK] Analytics failed:', e);
  }
}

// ── User Management ───────────────────────────────────────────────────────────
async function loadUsers(q='') {
  try {
    const url = '/admin/users' + (q ? `?q=${encodeURIComponent(q)}` : '');
    const resp = await fetch(url).then(r=>r.json());
    const tbody = document.getElementById('users-tbody');
    if (!resp.success || !tbody) return;

    if (!resp.users.length) {
      tbody.innerHTML = `<tr><td colspan="8"><div class="empty-state"><i class="bi bi-people"></i><p>No users found.</p></div></td></tr>`;
      return;
    }

    tbody.innerHTML = resp.users.map((u,i) => `
      <tr>
        <td style="color:var(--text-muted);font-size:0.8rem;">${i+1}</td>
        <td><div style="font-weight:600;font-size:0.9rem;">${u.full_name}</div></td>
        <td style="font-size:0.82rem;color:var(--text-secondary);">${u.email}</td>
        <td style="font-size:0.82rem;">${u.phone}</td>
        <td><span class="pill pill-${u.role==='admin'?'resolved':'pending'}" style="font-size:0.7rem;">${u.role}</span></td>
        <td><span class="pill pill-${u.risk_level}" style="font-size:0.7rem;">${u.risk_level}</span></td>
        <td><span class="pill pill-${u.is_active?'approved':'rejected'}" style="font-size:0.7rem;">${u.is_active?'Active':'Inactive'}</span></td>
        <td>
          <button onclick="toggleUser(${u.id},${u.is_active})" class="btn-glass" style="font-size:0.75rem;padding:4px 10px;">
            ${u.is_active ? 'Deactivate' : 'Activate'}
          </button>
        </td>
      </tr>`).join('');
  } catch(e) {
    console.warn('[RAKSHAK] Load users failed:', e);
  }
}

let searchTimeout;
function searchUsers(q) {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => loadUsers(q), 400);
}

async function toggleUser(uid, currentlyActive) {
  const resp = await postJSON(`/admin/users/${uid}/toggle`);
  if (resp.success) {
    showToast(resp.is_active ? 'User activated.' : 'User deactivated.', 'info');
    loadUsers();
  } else showToast(resp.error||'Failed','error');
}

// ── Pending Danger Zones ──────────────────────────────────────────────────────
async function loadPendingZones() {
  try {
    const resp = await fetch('/admin/danger-zones/pending').then(r=>r.json());
    const container = document.getElementById('pending-zones-list');
    if (!container) return;

    if (!resp.success || !resp.zones.length) {
      container.innerHTML = `<div class="col-12"><div class="empty-state"><i class="bi bi-check-circle"></i><p>No pending zones. All clear!</p></div></div>`;
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
    document.getElementById('zone-card-'+id)?.remove();
  } else showToast(resp.error||'Failed','error');
}

async function rejectZone(id) {
  const resp = await postJSON(`/admin/danger-zones/${id}/reject`);
  if (resp.success) {
    showToast('Zone rejected.', 'info');
    document.getElementById('zone-card-'+id)?.remove();
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
