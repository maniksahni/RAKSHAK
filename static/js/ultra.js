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
   1. WEBGL FLUID GRADIENT BACKGROUND
   Own RAF is fine — GPU shader work, independent of DOM
   ═══════════════════════════════════════════════════ */
(function initWebGL() {
  const canvas = document.getElementById('meshCanvas');
  if (!canvas) return;

  const gl = canvas.getContext('webgl', { alpha: true, premultipliedAlpha: false, antialias: false });
  if (!gl) return;

  canvas.style.opacity = '1';

  const vs = `
    attribute vec2 a_pos;
    void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }
  `;

  const fs = `
    precision mediump float;
    uniform float u_time;
    uniform vec2 u_resolution;
    uniform vec2 u_mouse;

    vec3 mod289(vec3 x) { return x - floor(x * (1.0/289.0)) * 289.0; }
    vec2 mod289(vec2 x) { return x - floor(x * (1.0/289.0)) * 289.0; }
    vec3 permute(vec3 x) { return mod289(((x*34.0)+1.0)*x); }

    float snoise(vec2 v) {
      const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                         -0.577350269189626, 0.024390243902439);
      vec2 i  = floor(v + dot(v, C.yy));
      vec2 x0 = v - i + dot(i, C.xx);
      vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
      vec4 x12 = x0.xyxy + C.xxzz;
      x12.xy -= i1;
      i = mod289(i);
      vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
      vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
      m = m*m; m = m*m;
      vec3 x = 2.0 * fract(p * C.www) - 1.0;
      vec3 h = abs(x) - 0.5;
      vec3 ox = floor(x + 0.5);
      vec3 a0 = x - ox;
      m *= 1.79284291400159 - 0.85373472095314 * (a0*a0 + h*h);
      vec3 g;
      g.x = a0.x * x0.x + h.x * x0.y;
      g.yz = a0.yz * x12.xz + h.yz * x12.yw;
      return 130.0 * dot(m, g);
    }

    float fbm(vec2 p) {
      float v = 0.0, a = 0.5;
      mat2 rot = mat2(cos(0.5), sin(0.5), -sin(0.5), cos(0.5));
      for (int i = 0; i < 4; i++) {
        v += a * snoise(p);
        p = rot * p * 2.0 + vec2(100.0);
        a *= 0.5;
      }
      return v;
    }

    void main() {
      vec2 uv = gl_FragCoord.xy / u_resolution;
      float t = u_time * 0.08;

      vec2 mouse = u_mouse / u_resolution;
      float mouseDist = length(uv - mouse);
      float mouseInfluence = smoothstep(0.5, 0.0, mouseDist) * 0.3;

      float n1 = fbm(uv * 2.5 + vec2(t, t * 0.7));
      float n2 = fbm(uv * 1.8 - vec2(t * 0.5, t * 0.3) + vec2(50.0));
      float n3 = fbm(uv * 3.2 + vec2(t * 0.3, -t * 0.6) + vec2(100.0));

      vec3 purple = vec3(0.545, 0.361, 0.965);
      vec3 red    = vec3(1.0, 0.231, 0.231);
      vec3 cyan   = vec3(0.133, 0.827, 0.933);
      vec3 emerald= vec3(0.204, 0.827, 0.6);
      vec3 pink   = vec3(0.957, 0.447, 0.722);

      vec3 col = mix(purple, red, smoothstep(-0.3, 0.5, n1));
      col = mix(col, cyan, smoothstep(-0.2, 0.6, n2) * 0.6);
      col = mix(col, emerald, smoothstep(0.0, 0.7, n3) * 0.35);
      col = mix(col, pink, mouseInfluence);

      float vig = 1.0 - smoothstep(0.4, 1.4, length(uv - 0.5) * 1.8);
      float alpha = (0.12 + mouseInfluence * 0.15) * vig;
      col *= 1.2;

      gl_FragColor = vec4(col, alpha);
    }
  `;

  function createShader(type, src) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      console.warn('Shader error:', gl.getShaderInfoLog(s));
      return null;
    }
    return s;
  }

  const vShader = createShader(gl.VERTEX_SHADER, vs);
  const fShader = createShader(gl.FRAGMENT_SHADER, fs);
  if (!vShader || !fShader) return;

  const program = gl.createProgram();
  gl.attachShader(program, vShader);
  gl.attachShader(program, fShader);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return;
  gl.useProgram(program);

  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), gl.STATIC_DRAW);
  const aPos = gl.getAttribLocation(program, 'a_pos');
  gl.enableVertexAttribArray(aPos);
  gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

  const uTime = gl.getUniformLocation(program, 'u_time');
  const uRes = gl.getUniformLocation(program, 'u_resolution');
  const uMouse = gl.getUniformLocation(program, 'u_mouse');

  /* Read from shared globals set by inline engine */
  function resize() {
    const dpr = Math.min(devicePixelRatio, 1.5);
    canvas.width = innerWidth * dpr;
    canvas.height = innerHeight * dpr;
    canvas.style.width = innerWidth + 'px';
    canvas.style.height = innerHeight + 'px';
    gl.viewport(0, 0, canvas.width, canvas.height);
  }
  resize();
  addEventListener('resize', resize);

  let lastFrame = 0, rafId = null;
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

  function render(ts) {
    rafId = null;
    if (!tabVisible) return;
    if (ts - lastFrame < 33) { rafId = requestAnimationFrame(render); return; }
    lastFrame = ts;

    const mx = window._MX || innerWidth / 2;
    const my = window._MY || innerHeight / 2;

    gl.uniform1f(uTime, ts * 0.001);
    gl.uniform2f(uRes, canvas.width, canvas.height);
    gl.uniform2f(uMouse, mx * (canvas.width / innerWidth), (innerHeight - my) * (canvas.height / innerHeight));
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    rafId = requestAnimationFrame(render);
  }

  function start() { if (!rafId && tabVisible) rafId = requestAnimationFrame(render); }
  document.addEventListener('visibilitychange', () => { if (tabVisible) start(); });
  setTimeout(start, 2000);
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

    // rAF-throttle: batch mousemove updates to one per frame (not per mouse event).
    // Keep left/top (centered via CSS transform:translate(-50%,-50%)) — don't override transform.
    let pending = false, lx = 0, ly = 0;
    sec.addEventListener('mousemove', e => {
      const r = sec.getBoundingClientRect();
      lx = e.clientX - r.left;
      ly = e.clientY - r.top;
      if (!pending) {
        pending = true;
        requestAnimationFrame(() => {
          glow.style.left = lx + 'px';
          glow.style.top = ly + 'px';
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
