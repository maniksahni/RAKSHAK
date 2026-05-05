/**
 * RAKSHAK - automatic SOS trigger guard.
 *
 * Automatic/background SOS triggers are permanently disabled. SOS countdowns
 * should only start from explicit UI controls that call window.triggerGlobalSOS.
 */
(function () {
  'use strict';

  var AUTO_TRIGGER_KEYS = [
    'shake_sos_enabled',
    'volume_sos_enabled',
    'triple_tap_sos_enabled',
    'movement_sos_enabled'
  ];
  var RESET_VERSION = '2026-05-06-auto-sos-permanently-disabled';

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
      showToast('Automatic SOS triggers are disabled. Use the SOS button manually.', 'info', 7000);
    }
  };
})();
