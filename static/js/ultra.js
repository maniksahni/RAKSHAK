/* ═══════════════════════════════════════════════════════════════════════
   ULTRA.JS — Visual Enhancement Layer for RAKSHAK
   Adds WebGL shader, holographic cards, section glow, word reveal,
   morphing counters, stagger entrance, loader effects.
   NO competing RAF loops — only the WebGL shader has its own RAF
   (GPU-bound, independent of main engine loop).
   ═══════════════════════════════════════════════════════════════════════ */
(function(){
'use strict';

const IS_MOBILE = matchMedia('(max-width:768px)').matches;
const REDUCED = matchMedia('(prefers-reduced-motion:reduce)').matches;
let tabVisible = true;
document.addEventListener('visibilitychange', () => { tabVisible = !document.hidden; });

/* ═══════════════════════════════════════════════════
   1. WEBGL FLUID GRADIENT — REPLACED WITH STATIC CSS GRADIENT
   The fractal-noise shader was running fbm() × 4 octaves per pixel at 30fps
   on the full viewport — far and away the largest remaining GPU cost.
   Three CSS gradient blobs already cover the hero area with the same look.
   ═══════════════════════════════════════════════════ */
(function replaceWebGLWithCSSGradient() {
  const canvas = document.getElementById('meshCanvas');
  if (!canvas) return;
  // Paint a static multi-stop radial gradient in its place — GPU composites
  // a single paint once, then the browser never touches it again.
  canvas.style.display = 'none';
  canvas.style.opacity = '0';
})();

/* ═══════════════════════════════════════════════════
   2. HOLOGRAPHIC CARD EFFECT
   Event-driven, no RAF — prismatic rainbow sheen
   ═══════════════════════════════════════════════════ */
(function initHolographic() {
  if (IS_MOBILE) return;

  document.querySelectorAll('.bc, .stc, .hwc, .tkc').forEach(card => {
    const holo = document.createElement('div');
    holo.className = 'ultra-holo';
    card.appendChild(holo);
    card.style.position = 'relative';

    // rAF-throttled mousemove so we update style at most once per frame
    let pending = false, lx = 0, ly = 0;
    card.addEventListener('mousemove', e => {
      const r = card.getBoundingClientRect();
      lx = ((e.clientX - r.left) / r.width) * 100;
      ly = ((e.clientY - r.top) / r.height) * 100;
      if (!pending) {
        pending = true;
        requestAnimationFrame(() => {
          holo.style.setProperty('--hx', lx + '%');
          holo.style.setProperty('--hy', ly + '%');
          holo.style.opacity = '1';
          pending = false;
        });
      }
    });
    card.addEventListener('mouseleave', () => { holo.style.opacity = '0'; });
  });
})();

/* ═══════════════════════════════════════════════════
   3. SECTION GLOW TRACKING
   Event-driven, no RAF — radial glow follows cursor
   ═══════════════════════════════════════════════════ */
(function initSectionGlow() {
  if (IS_MOBILE) return;

  document.querySelectorAll('.stats, .term-sec, .show, .how, #features, .tech, .dash, .testi, .cta').forEach(sec => {
    const glow = document.createElement('div');
    glow.className = 'ultra-section-glow';
    sec.style.position = 'relative';
    sec.insertBefore(glow, sec.firstChild);

    // rAF-throttle: one DOM write per frame max.
    // Use transform:translate3d only — left/top trigger layout on every move.
    // Glow is 420×420; translate by (lx-210, ly-210) centres it on the cursor.
    let pending = false, lx = 0, ly = 0;
    sec.addEventListener('mousemove', e => {
      const r = sec.getBoundingClientRect();
      lx = e.clientX - r.left;
      ly = e.clientY - r.top;
      if (!pending) {
        pending = true;
        requestAnimationFrame(() => {
          glow.style.transform = 'translate3d(' + (lx - 210) + 'px,' + (ly - 210) + 'px,0)';
          glow.style.opacity = '1';
          pending = false;
        });
      }
    });
    sec.addEventListener('mouseleave', () => { glow.style.opacity = '0'; });
  });
})();

/* ═══════════════════════════════════════════════════
   4. TEXT WORD-BY-WORD REVEAL
   IO-based, no RAF
   ═══════════════════════════════════════════════════ */
(function initWordReveal() {
  if (REDUCED) return;

  document.querySelectorAll('.ssub').forEach(el => {
    const words = el.textContent.split(' ');
    el.innerHTML = words.map((w, i) =>
      `<span class="ultra-word" style="transition-delay:${i * 0.04}s">${w}</span>`
    ).join(' ');
    el.classList.add('ultra-word-container');
  });

  const wio = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('ultra-words-visible');
        wio.unobserve(e.target);
      }
    });
  }, { threshold: 0.3 });

  document.querySelectorAll('.ultra-word-container').forEach(el => wio.observe(el));
})();

/* ═══════════════════════════════════════════════════
   5. MORPHING COUNTER DIGITS
   IO-based, one-shot RAF for animation (not a loop)
   ═══════════════════════════════════════════════════ */
(function initMorphCounters() {
  document.querySelectorAll('.hs-v[data-count]').forEach(el => {
    const target = +el.dataset.count;
    el.innerHTML = '';
    el.classList.add('ultra-counter');

    const digits = String(target).length;
    const slots = [];
    for (let i = 0; i < digits; i++) {
      const slot = document.createElement('span');
      slot.className = 'ultra-digit';
      slot.textContent = '0';
      el.appendChild(slot);
      slots.push(slot);
    }
    const suffix = document.createElement('span');
    suffix.className = 'ultra-suffix';
    suffix.textContent = '+';
    el.appendChild(suffix);

    const io = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          animateDigits(slots, target);
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.5 });
    io.observe(el);
  });

  function animateDigits(slots, target) {
    const targetStr = String(target);
    const dur = 2000;
    const t0 = performance.now();

    function tick(now) {
      const p = Math.min((now - t0) / dur, 1);
      const eased = 1 - Math.pow(1 - p, 4);
      const current = String(Math.round(eased * target)).padStart(targetStr.length, '0');

      for (let i = 0; i < slots.length; i++) {
        const newDigit = current[i] || '0';
        if (slots[i].textContent !== newDigit) {
          slots[i].textContent = newDigit;
          slots[i].classList.add('ultra-digit-flip');
          setTimeout(() => slots[i].classList.remove('ultra-digit-flip'), 150);
        }
      }
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }
})();

/* ═══════════════════════════════════════════════════
   6. STAGGER ENTRANCE UPGRADE
   CSS-only, no RAF — cards fly in from alternating sides
   ═══════════════════════════════════════════════════ */
(function initStaggerEntrance() {
  if (REDUCED) return;

  document.querySelectorAll('.bc').forEach((card, i) => {
    card.style.transitionDelay = (0.08 * i) + 's';
    const dir = i % 2 === 0 ? -1 : 1;
    if (!card.classList.contains('vis')) {
      card.style.transform = `translateY(80px) rotate(${dir * 3}deg) scale(0.92)`;
    }
  });

  document.querySelectorAll('.tc').forEach((card) => {
    card.style.transition = 'all 0.6s cubic-bezier(.22,1,.36,1)';
  });
})();

/* ═══════════════════════════════════════════════════
   7. LOADING SCREEN ENHANCEMENT
   MutationObserver, no RAF — scanline + flash on exit
   ═══════════════════════════════════════════════════ */
(function enhanceLoader() {
  const loader = document.getElementById('loader');
  if (!loader) return;

  const scanline = document.createElement('div');
  scanline.className = 'ultra-scanline';
  loader.appendChild(scanline);

  if (!loader.classList.contains('done')) {
    const observer = new MutationObserver(mutations => {
      mutations.forEach(m => {
        if (m.target.classList.contains('done')) {
          const flash = document.createElement('div');
          flash.className = 'ultra-flash';
          document.body.appendChild(flash);
          setTimeout(() => flash.remove(), 800);
          observer.disconnect();
        }
      });
    });
    observer.observe(loader, { attributes: true, attributeFilter: ['class'] });
  }
})();

})();
