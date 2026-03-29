/**
 * RAKSHAK — Global pointer-driven 3D tilt (smooth lerp, layered depth).
 * .tilt-card + inner .glass-card/.stat-card/.glass-section; standalone .glass-card.
 */
(function () {
  'use strict';

  var PERSPECTIVE = 1420;
  var TILT_MAX_RX = 20;
  var TILT_MAX_RY = 24;
  var GLASS_MAX_RX = 11;
  var GLASS_MAX_RY = 12;
  var LERP = 0.17;

  var states = [];

  function motionReduced() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function findInnerFace(host) {
    return host.querySelector('.glass-card, .stat-card, .glass-section, .lp-card-inner');
  }

  function resetState(s) {
    s.el.style.transform = '';
    if (s.inner) {
      s.inner.style.transform = '';
      s.inner.style.boxShadow = '';
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
      s.cx += (s.tx - s.cx) * LERP;
      s.cy += (s.ty - s.cy) * LERP;
      var rx = s.cy * -s.maxRx;
      var ry = s.cx * s.maxRy;
      var zLift = 6 + (Math.abs(s.cx) + Math.abs(s.cy)) * 10;
      var t =
        'perspective(' +
        PERSPECTIVE +
        'px) rotateX(' +
        rx +
        'deg) rotateY(' +
        ry +
        'deg) translateZ(' +
        zLift +
        'px)';
      if (s.scale3d) t += ' scale3d(1.038,1.038,1.038)';
      s.el.style.transform = t;
      if (s.inner) {
        var z = 14 + Math.abs(s.cx) * 14;
        s.inner.style.transform = 'translateZ(' + z + 'px)';
        s.inner.style.boxShadow =
          s.cx * -28 +
          'px ' +
          s.cy * -24 +
          'px 56px rgba(124,58,237,0.2), 0 18px 44px rgba(0,0,0,0.45), 0 0 1px rgba(255,255,255,0.06)';
      }
    });
  }

  function loop() {
    tick();
    requestAnimationFrame(loop);
  }

  function boot() {
    collect();
    if (window.matchMedia) {
      window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', function () {
        if (!motionReduced()) collect();
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      boot();
      requestAnimationFrame(loop);
    });
  } else {
    boot();
    requestAnimationFrame(loop);
  }
})();
