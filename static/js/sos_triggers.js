/**
 * RAKSHAK - automatic SOS trigger guard.
 *
 * Background and sensor-driven SOS triggers are permanently disabled.
 * Direct user actions such as the SOS button or Vision Shield gestures remain allowed.
 */
(function () {
  'use strict';

  var AUTO_TRIGGER_KEYS = [
    'shake_sos_enabled',
    'volume_sos_enabled',
    'triple_tap_sos_enabled',
    'movement_sos_enabled'
  ];
  var RESET_VERSION = '2026-05-06-manual-sos-only';

  function disableAutoTriggers() {
    try {
      AUTO_TRIGGER_KEYS.forEach(function (key) {
        localStorage.setItem('rakshak_' + key, 'false');
      });
      localStorage.setItem('rakshak_auto_trigger_reset_version', RESET_VERSION);
    } catch (_) {
      // Defaults are already disabled when storage is unavailable.
    }
  }

  function hideStaleCountdown() {
    var overlay = document.getElementById('sos-countdown-overlay');
    var number = document.getElementById('sos-countdown-number');
    if (overlay) overlay.style.display = 'none';
    if (number) number.textContent = '5';
  }

  function hardenPage() {
    disableAutoTriggers();
    hideStaleCountdown();
  }

  hardenPage();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', hardenPage, { once: true });
  }

  window.addEventListener('pageshow', function (event) {
    disableAutoTriggers();
    if (event.persisted) hideStaleCountdown();
  });

  window.disableRakshakAutoSosTriggers = disableAutoTriggers;
  window.openSOSTriggerSettings = function () {
    disableAutoTriggers();
    if (typeof showToast === 'function') {
      showToast('Automatic sensor-based SOS triggers are disabled. Use the SOS button or Vision Shield gesture.', 'info', 7000);
    }
  };
})();
