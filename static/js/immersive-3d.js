/**
 * RAKSHAK — Global pointer-driven 3D tilt (smooth lerp, layered depth).
 * .tilt-card + inner .glass-card/.stat-card/.glass-section; standalone .glass-card.
 */
(function () {
  'use strict';

  var PERSPECTIVE = 1580;
  var TILT_MAX_RX = 24;
  var TILT_MAX_RY = 28;
  var GLASS_MAX_RX = 14;
  var GLASS_MAX_RY = 16;
  var LERP = 0.19;

  var states = [];

  function motionReduced() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function findInnerFace(host) {
    return host.querySelector('.glass-card, .stat-card, .glass-section, .lp-card-inner');
  }

  function resetState(s) {
    s.el.style.transform = '';
    s.el.style.filter = '';
    if (s.inner) {
      s.inner.style.transform = '';
      s.inner.style.boxShadow = '';
      s.inner.style.filter = '';
    }
  }

  function bindPointer(s) {
    s.el.addEventListener('mousemove', function (e) {
      if (motionReduced()) return;
      var r = s.el.getBoundingClientRect();
      s.tx = (e.clientX - r.left) / r.width * 2 - 1;
      s.ty = (e.clientY - r.top) / r.height * 2 - 1;
    });
    s.el.addEventListener('mouseleave', function () {
      s.tx = 0;
      s.ty = 0;
    });
  }

  function registerTiltCards() {
    document.querySelectorAll('.tilt-card:not(.no-immersive-tilt)').forEach(function (el) {
      if (el.dataset.immersive3dBound) return;
      el.dataset.immersive3dBound = '1';
      var s = {
        el: el,
        inner: findInnerFace(el),
        tx: 0,
        ty: 0,
        cx: 0,
        cy: 0,
        maxRx: TILT_MAX_RX,
        maxRy: TILT_MAX_RY,
        scale3d: true
      };
      bindPointer(s);
      states.push(s);
    });
  }

  function registerGlassCards() {
    document.querySelectorAll('.glass-card:not(.sos-card):not(.no-immersive-tilt)').forEach(function (card) {
      if (card.closest('.tilt-card') || card.dataset.immersive3dBound) return;
      card.dataset.immersive3dBound = '1';
      var s = {
        el: card,
        inner: null,
        tx: 0,
        ty: 0,
        cx: 0,
        cy: 0,
        maxRx: GLASS_MAX_RX,
        maxRy: GLASS_MAX_RY,
        scale3d: false
      };
      bindPointer(s);
      states.push(s);
    });
  }

  function collect() {
    if (motionReduced()) return;
    registerTiltCards();
    registerGlassCards();
  }

  function tick() {
    if (motionReduced()) {
      states.forEach(resetState);
      return;
    }
    states.forEach(function (s) {
      // Optimizaton: skip DOM updates if settled
      if (Math.abs(s.tx - s.cx) < 0.001 && Math.abs(s.ty - s.cy) < 0.001) {
        s.cx = s.tx;
        s.cy = s.ty;
        if (s.tx === 0 && s.ty === 0) {
          if (s.settled) return;
          s.settled = true;
          resetState(s);
          return;
        }
      } else {
        s.settled = false;
      }

      s.cx += (s.tx - s.cx) * LERP;
      s.cy += (s.ty - s.cy) * LERP;
      var rx = s.cy * -s.maxRx;
      var ry = s.cx * s.maxRy;
      var rz = s.cx * s.cy * -5.5;
      if (rz > 5) rz = 5;
      if (rz < -5) rz = -5;
      var zLift = 10 + (Math.abs(s.cx) + Math.abs(s.cy)) * 13;
      var t =
        'perspective(' +
        PERSPECTIVE +
        'px) rotateX(' +
        rx +
        'deg) rotateY(' +
        ry +
        'deg) rotateZ(' +
        rz +
        'deg) translateZ(' +
        zLift +
        'px)';
      if (s.scale3d) t += ' scale3d(1.045,1.045,1.045)';
      s.el.style.transform = t;
      var dist = 20 + Math.abs(s.cx) * 16 + Math.abs(s.cy) * 12;
      s.el.style.filter =
        'drop-shadow(' +
        s.cx * -8 +
        'px ' +
        (s.cy * -7 + 6) +
        'px ' +
        dist +
        'px rgba(88,28,135,0.22)) drop-shadow(0 ' +
        (12 + s.cy * -4) +
        'px 28px rgba(0,0,0,0.35))';
      if (s.inner) {
        var z = 18 + Math.abs(s.cx) * 18;
        s.inner.style.transform = 'translateZ(' + z + 'px)';
        s.inner.style.boxShadow =
          s.cx * -32 +
          'px ' +
          s.cy * -28 +
          'px 64px rgba(124,58,237,0.26), 0 22px 52px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04)';
        s.inner.style.setProperty(
          'filter',
          'brightness(' +
            (1.02 + Math.abs(s.cx) * 0.04 + Math.abs(s.cy) * 0.03) +
            ') saturate(1.08)'
        );
      }
    });
  }

  var rafId = null;
  var lastFrame = 0;

  function loop(ts) {
    rafId = null;
    // Throttle to ~30fps
    if (ts - lastFrame < 32) { rafId = requestAnimationFrame(loop); return; }
    lastFrame = ts;
    tick();
    if (!document.hidden) rafId = requestAnimationFrame(loop);
  }

  function startLoop() {
    if (!rafId && !document.hidden) rafId = requestAnimationFrame(loop);
  }

  function boot() {
    collect();
    if (window.matchMedia) {
      window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', function () {
        if (!motionReduced()) collect();
      });
    }
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) { if (rafId) { cancelAnimationFrame(rafId); rafId = null; } }
      else startLoop();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { boot(); startLoop(); });
  } else {
    boot(); startLoop();
  }
})();
