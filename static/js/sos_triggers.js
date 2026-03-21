/**
 * RAKSHAK — Shake-to-SOS & Volume Button Trigger
 * Hooks into existing POST /sos/trigger endpoint.
 * Requires: CSRF_TOKEN global (set in base.html), navigator.geolocation
 */
(function () {
  'use strict';

  // ── Settings (localStorage) ─────────────────────────────────────────────────
  const DEFAULTS = {
    shake_sos_enabled: true,
    volume_sos_enabled: true,
    countdown_seconds: 5
  };

  function getSetting(key) {
    const raw = localStorage.getItem('rakshak_' + key);
    if (raw === null) return DEFAULTS[key];
    if (raw === 'true') return true;
    if (raw === 'false') return false;
    const num = Number(raw);
    return isNaN(num) ? raw : num;
  }

  function setSetting(key, val) {
    localStorage.setItem('rakshak_' + key, String(val));
  }

  // ── Countdown & SOS trigger ─────────────────────────────────────────────────
  let countdownTimer = null;
  let countdownValue = 0;

  const overlay = document.getElementById('sos-countdown-overlay');
  const countdownNum = document.getElementById('sos-countdown-number');
  const cancelBtn = document.getElementById('sos-countdown-cancel');

  function showCountdown() {
    if (!overlay) return;
    countdownValue = getSetting('countdown_seconds');
    overlay.style.display = 'flex';
    countdownNum.textContent = countdownValue;

    // Pulse animation restart
    overlay.classList.remove('sos-pulse');
    void overlay.offsetWidth; // reflow
    overlay.classList.add('sos-pulse');

    countdownTimer = setInterval(function () {
      countdownValue--;
      if (countdownValue <= 0) {
        clearInterval(countdownTimer);
        countdownTimer = null;
        overlay.style.display = 'none';
        fireSOS();
      } else {
        countdownNum.textContent = countdownValue;
      }
    }, 1000);
  }

  function cancelCountdown() {
    if (countdownTimer) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
    if (overlay) overlay.style.display = 'none';
    if (typeof showToast === 'function') {
      showToast('SOS cancelled', 'info');
    }
  }

  if (cancelBtn) {
    cancelBtn.addEventListener('click', cancelCountdown);
  }

  function fireSOS() {
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        var headers = { 'Content-Type': 'application/json' };
        if (typeof CSRF_TOKEN !== 'undefined') {
          headers['X-CSRFToken'] = CSRF_TOKEN;
        }
        fetch('/sos/trigger', {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            trigger_type: 'auto_shake',
            accuracy: pos.coords.accuracy,
            message: 'Auto-triggered via shake/volume detection'
          })
        })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (d.success) {
              if (typeof showToast === 'function') showToast('SOS ALERT SENT', 'sos', 6000);
            } else {
              if (typeof showToast === 'function') showToast(d.error || 'SOS failed', 'error');
            }
          })
          .catch(function () {
            if (typeof showToast === 'function') showToast('Network error sending SOS', 'error');
          });
      },
      function () {
        // Fallback: send without coords — server will reject but at least we tried
        if (typeof showToast === 'function') {
          showToast('GPS unavailable — SOS could not be sent', 'error');
        }
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  }

  // ── Shake Detection (DeviceMotionEvent) ─────────────────────────────────────
  var SHAKE_THRESHOLD = 25; // m/s^2
  var SHAKE_COUNT_REQUIRED = 3;
  var SHAKE_WINDOW_MS = 2000;
  var shakeTimestamps = [];
  var shakeCooldown = false;

  function handleMotion(event) {
    if (!getSetting('shake_sos_enabled')) return;
    if (shakeCooldown || countdownTimer) return;

    var acc = event.accelerationIncludingGravity || event.acceleration;
    if (!acc) return;

    var x = Math.abs(acc.x || 0);
    var y = Math.abs(acc.y || 0);
    var z = Math.abs(acc.z || 0);

    if (x > SHAKE_THRESHOLD || y > SHAKE_THRESHOLD || z > SHAKE_THRESHOLD) {
      var now = Date.now();
      shakeTimestamps.push(now);

      // Remove timestamps outside the window
      shakeTimestamps = shakeTimestamps.filter(function (t) {
        return now - t < SHAKE_WINDOW_MS;
      });

      if (shakeTimestamps.length >= SHAKE_COUNT_REQUIRED) {
        shakeTimestamps = [];
        shakeCooldown = true;
        showCountdown();
        // Prevent re-trigger for 10 seconds
        setTimeout(function () { shakeCooldown = false; }, 10000);
      }
    }
  }

  // Request permission on iOS 13+
  function initShakeDetection() {
    if (typeof DeviceMotionEvent === 'undefined') return;

    if (typeof DeviceMotionEvent.requestPermission === 'function') {
      // iOS 13+ requires user gesture to request permission
      document.addEventListener('click', function requestMotion() {
        DeviceMotionEvent.requestPermission()
          .then(function (state) {
            if (state === 'granted') {
              window.addEventListener('devicemotion', handleMotion);
            }
          })
          .catch(function () { /* silently fail */ });
        document.removeEventListener('click', requestMotion);
      }, { once: true });
    } else {
      window.addEventListener('devicemotion', handleMotion);
    }
  }

  initShakeDetection();

  // ── Volume Button Trigger ───────────────────────────────────────────────────
  // Volume buttons on mobile fire "volumechange" on the <audio>/<video> element,
  // but there is no universal web API for hardware volume buttons.
  // Strategy: listen for rapid keypresses of VolumeUp/VolumeDown on Android Chrome,
  // and also monitor volumechange events on a silent media element.
  var VOLUME_PRESSES_REQUIRED = 5;
  var VOLUME_WINDOW_MS = 3000;
  var volumeTimestamps = [];
  var volumeCooldown = false;

  function recordVolumePress() {
    if (!getSetting('volume_sos_enabled')) return;
    if (volumeCooldown || countdownTimer) return;

    var now = Date.now();
    volumeTimestamps.push(now);
    volumeTimestamps = volumeTimestamps.filter(function (t) {
      return now - t < VOLUME_WINDOW_MS;
    });

    if (volumeTimestamps.length >= VOLUME_PRESSES_REQUIRED) {
      volumeTimestamps = [];
      volumeCooldown = true;
      showCountdown();
      setTimeout(function () { volumeCooldown = false; }, 10000);
    }
  }

  // Keyboard-based detection (works on Android Chrome, desktop testing)
  document.addEventListener('keydown', function (e) {
    if (e.key === 'AudioVolumeUp' || e.key === 'AudioVolumeDown' ||
        e.key === 'VolumeUp' || e.key === 'VolumeDown') {
      recordVolumePress();
    }
  });

  // Silent audio element to detect volumechange events (mobile fallback)
  try {
    var silentAudio = document.createElement('audio');
    silentAudio.setAttribute('src', 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=');
    silentAudio.setAttribute('preload', 'auto');
    silentAudio.volume = 0.5;
    silentAudio.muted = false;
    silentAudio.addEventListener('volumechange', function () {
      recordVolumePress();
    });
    // Keep it alive so the browser keeps the reference
    silentAudio.loop = true;
    // We don't actually play it — just having it listen is enough on some browsers
  } catch (e) {
    // silently fail if audio element creation fails
  }

  // ── Settings Panel (callable from dashboard) ────────────────────────────────
  window.openSOSTriggerSettings = function () {
    var existing = document.getElementById('sos-trigger-settings-modal');
    if (existing) existing.remove();

    var shakeEnabled = getSetting('shake_sos_enabled');
    var volumeEnabled = getSetting('volume_sos_enabled');
    var countdown = getSetting('countdown_seconds');

    var modal = document.createElement('div');
    modal.id = 'sos-trigger-settings-modal';
    modal.style.cssText = 'position:fixed;inset:0;z-index:100000;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.7);backdrop-filter:blur(8px);';
    modal.innerHTML =
      '<div style="background:linear-gradient(135deg,#0f0f17,#1a1a2e);border:1px solid rgba(220,38,38,0.2);border-radius:16px;padding:32px;max-width:400px;width:90%;color:#e2e2e2;box-shadow:0 20px 60px rgba(0,0,0,0.5);">' +
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;">' +
          '<h3 style="margin:0;font-size:1.1rem;color:#dc2626;font-weight:700;letter-spacing:0.05em;">SOS TRIGGER SETTINGS</h3>' +
          '<button id="sos-settings-close" style="background:none;border:none;color:#888;font-size:1.4rem;cursor:pointer;padding:0;line-height:1;">&times;</button>' +
        '</div>' +

        '<div style="margin-bottom:20px;">' +
          '<label style="display:flex;align-items:center;gap:12px;cursor:pointer;padding:12px;border-radius:8px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);">' +
            '<input type="checkbox" id="sos-set-shake" ' + (shakeEnabled ? 'checked' : '') + ' style="width:18px;height:18px;accent-color:#dc2626;">' +
            '<div><div style="font-weight:600;font-size:0.9rem;">Shake to SOS</div><div style="font-size:0.75rem;color:#888;">Shake your phone aggressively to trigger SOS</div></div>' +
          '</label>' +
        '</div>' +

        '<div style="margin-bottom:20px;">' +
          '<label style="display:flex;align-items:center;gap:12px;cursor:pointer;padding:12px;border-radius:8px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);">' +
            '<input type="checkbox" id="sos-set-volume" ' + (volumeEnabled ? 'checked' : '') + ' style="width:18px;height:18px;accent-color:#dc2626;">' +
            '<div><div style="font-weight:600;font-size:0.9rem;">Volume Button SOS</div><div style="font-size:0.75rem;color:#888;">Press volume buttons 5 times rapidly</div></div>' +
          '</label>' +
        '</div>' +

        '<div style="margin-bottom:24px;padding:12px;border-radius:8px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);">' +
          '<label style="font-weight:600;font-size:0.9rem;display:block;margin-bottom:8px;">Countdown (seconds)</label>' +
          '<input type="range" id="sos-set-countdown" min="3" max="10" value="' + countdown + '" style="width:100%;accent-color:#dc2626;">' +
          '<div style="display:flex;justify-content:space-between;font-size:0.75rem;color:#888;"><span>3s</span><span id="sos-countdown-val">' + countdown + 's</span><span>10s</span></div>' +
        '</div>' +

        '<button id="sos-settings-save" style="width:100%;padding:12px;background:linear-gradient(135deg,#dc2626,#b91c1c);color:#fff;border:none;border-radius:8px;font-weight:700;font-size:0.9rem;cursor:pointer;letter-spacing:0.05em;">SAVE SETTINGS</button>' +
      '</div>';

    document.body.appendChild(modal);

    // Event listeners
    document.getElementById('sos-settings-close').onclick = function () { modal.remove(); };
    modal.addEventListener('click', function (e) { if (e.target === modal) modal.remove(); });

    var slider = document.getElementById('sos-set-countdown');
    var valDisplay = document.getElementById('sos-countdown-val');
    slider.addEventListener('input', function () { valDisplay.textContent = slider.value + 's'; });

    document.getElementById('sos-settings-save').onclick = function () {
      setSetting('shake_sos_enabled', document.getElementById('sos-set-shake').checked);
      setSetting('volume_sos_enabled', document.getElementById('sos-set-volume').checked);
      setSetting('countdown_seconds', parseInt(slider.value, 10));
      if (typeof showToast === 'function') showToast('SOS trigger settings saved', 'success');
      modal.remove();
    };
  };

})();
