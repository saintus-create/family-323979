/**
 * Starfield — Van Gogh / Starry Night inspired WebGL particle field
 * Only active on the /welcome (Docs landing) page.
 * Uses Three.js r166 loaded dynamically from jsDelivr.
 */
(function () {
  'use strict';

  // ── Only run on the landing page ───────────────────────────────────────
  function isLandingPage() {
    const p = window.location.pathname;
    return p === '/' || p === '/welcome' || p === '' || p.endsWith('/welcome');
  }

  // ── Load Three.js then initialise ──────────────────────────────────────
  function loadScript(src, cb) {
    if (window.THREE) { cb(); return; }
    const s = document.createElement('script');
    s.src = src;
    s.onload = cb;
    s.onerror = function () { console.warn('[starfield] Three.js failed to load'); };
    document.head.appendChild(s);
  }

  function init() {
    if (!isLandingPage()) return;

    // Small delay so Fern's React shell finishes painting
    setTimeout(function () {
      loadScript(
        'https://cdn.jsdelivr.net/npm/three@0.166.1/build/three.min.js',
        buildStarfield
      );
    }, 300);
  }

  // ── Build the starfield canvas ──────────────────────────────────────────
  function buildStarfield() {
    const THREE = window.THREE;
    if (!THREE) return;

    // ── Canvas setup ──────────────────────────────────────────────────────
    const canvas = document.createElement('canvas');
    canvas.id = 'fern-starfield';
    Object.assign(canvas.style, {
      position: 'fixed',
      inset: '0',
      width: '100%',
      height: '100%',
      zIndex: '0',
      pointerEvents: 'none',
      opacity: '0',
      transition: 'opacity 1.2s ease',
    });
    document.body.prepend(canvas);

    // Make sure body / main scroll area sits above the canvas
    const main = document.querySelector('main, #fern-content, .fern-content');
    if (main) main.style.position = 'relative';
    if (main) main.style.zIndex = '1';

    // ── Renderer ─────────────────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setClearColor(0x000000, 0);

    // ── Scene / camera ────────────────────────────────────────────────────
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 2000);
    camera.position.z = 1;

    // ── Detect dark/light theme ───────────────────────────────────────────
    function isDark() {
      return document.documentElement.getAttribute('data-theme') === 'dark' ||
             window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    // ── Star colours ─────────────────────────────────────────────────────
    // Light mode: deep-navy-to-indigo sky; dark mode: near-black charcoal sky
    // Stars are warm whites + pale blues + faint golds (Van Gogh palette)
    const STAR_COLORS_LIGHT = [
      0xF5EFD8, // warm cream
      0xDDCFA8, // gold-wheat
      0xC3CDEE, // pale blue
      0xEEEEFF, // near-white
      0xAAB4D8, // slate blue
    ];
    const STAR_COLORS_DARK = [
      0xF0E8CC, // warm parchment
      0xE8D5A0, // antique gold
      0xBFC8E8, // powder blue
      0xF5F5FF, // bright white
      0x8898C8, // muted blue
    ];

    // ── Create particle geometry ──────────────────────────────────────────
    const STAR_COUNT = 1800;
    const positions = new Float32Array(STAR_COUNT * 3);
    const colors    = new Float32Array(STAR_COUNT * 3);
    const sizes     = new Float32Array(STAR_COUNT);

    const tmp = new THREE.Color();
    const palette = isDark() ? STAR_COLORS_DARK : STAR_COLORS_LIGHT;

    for (let i = 0; i < STAR_COUNT; i++) {
      // Spread across a wide plane slightly in front of camera
      positions[i * 3 + 0] = (Math.random() - 0.5) * 4;    // x
      positions[i * 3 + 1] = (Math.random() - 0.5) * 2.5;  // y
      positions[i * 3 + 2] = (Math.random() - 0.5) * 0.5 - 0.5; // z  (behind camera plane)

      tmp.set(palette[Math.floor(Math.random() * palette.length)]);
      colors[i * 3 + 0] = tmp.r;
      colors[i * 3 + 1] = tmp.g;
      colors[i * 3 + 2] = tmp.b;

      sizes[i] = Math.random() * 2.5 + 0.5;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color',    new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute('size',     new THREE.BufferAttribute(sizes, 1));

    // ── Sprite texture (soft glow) ────────────────────────────────────────
    function makeSprite() {
      const size = 64;
      const c = document.createElement('canvas');
      c.width = c.height = size;
      const ctx = c.getContext('2d');
      const g = ctx.createRadialGradient(size/2, size/2, 0, size/2, size/2, size/2);
      g.addColorStop(0,   'rgba(255,255,255,1)');
      g.addColorStop(0.3, 'rgba(255,255,255,0.6)');
      g.addColorStop(1,   'rgba(255,255,255,0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, size, size);
      return new THREE.CanvasTexture(c);
    }

    const material = new THREE.PointsMaterial({
      size: 0.012,
      sizeAttenuation: true,
      vertexColors: true,
      map: makeSprite(),
      transparent: true,
      opacity: isDark() ? 0.85 : 0.5,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });

    // ── Nebula swirls — a few large soft blobs (Van Gogh brushstrokes) ────
    function addNebula() {
      const nebulaColors = isDark()
        ? [0x1A1A6E, 0x0E3A6E, 0x2A1A5E]
        : [0x3B3B9B, 0x2563C0, 0x4B3D8F];
      for (let n = 0; n < 3; n++) {
        const nc = 120;
        const np = new Float32Array(nc * 3);
        const ncols = new Float32Array(nc * 3);
        const ns = new Float32Array(nc);
        tmp.set(nebulaColors[n]);
        for (let i = 0; i < nc; i++) {
          const angle = Math.random() * Math.PI * 2;
          const r = Math.random() * 0.6 + 0.1;
          np[i*3]   = Math.cos(angle) * r + (Math.random()-0.5)*2;
          np[i*3+1] = Math.sin(angle) * r * 0.5 + (Math.random()-0.5)*1.2;
          np[i*3+2] = -0.3 - Math.random()*0.2;
          ncols[i*3]   = tmp.r;
          ncols[i*3+1] = tmp.g;
          ncols[i*3+2] = tmp.b;
          ns[i] = Math.random() * 5 + 2;
        }
        const ng = new THREE.BufferGeometry();
        ng.setAttribute('position', new THREE.BufferAttribute(np, 3));
        ng.setAttribute('color',    new THREE.BufferAttribute(ncols, 3));
        ng.setAttribute('size',     new THREE.BufferAttribute(ns, 1));
        const nm = new THREE.PointsMaterial({
          size: 0.06,
          sizeAttenuation: true,
          vertexColors: true,
          map: makeSprite(),
          transparent: true,
          opacity: isDark() ? 0.18 : 0.08,
          depthWrite: false,
          blending: THREE.AdditiveBlending,
        });
        scene.add(new THREE.Points(ng, nm));
      }
    }

    const stars = new THREE.Points(geometry, material);
    scene.add(stars);
    addNebula();

    // ── Fade in ───────────────────────────────────────────────────────────
    requestAnimationFrame(function () {
      canvas.style.opacity = '1';
    });

    // ── Gentle drift + mouse parallax ─────────────────────────────────────
    let mouseX = 0, mouseY = 0;
    let targetX = 0, targetY = 0;
    document.addEventListener('mousemove', function (e) {
      mouseX = (e.clientX / window.innerWidth  - 0.5) * 0.04;
      mouseY = (e.clientY / window.innerHeight - 0.5) * 0.025;
    });

    let frame = 0;
    function animate() {
      requestAnimationFrame(animate);
      frame++;

      targetX += (mouseX - targetX) * 0.03;
      targetY += (mouseY - targetY) * 0.03;

      stars.rotation.y = targetX + frame * 0.00008;
      stars.rotation.x = -targetY;

      renderer.render(scene, camera);
    }
    animate();

    // ── Resize handler ────────────────────────────────────────────────────
    window.addEventListener('resize', function () {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });

    // ── Theme change — adjust opacity ──────────────────────────────────────
    const observer = new MutationObserver(function () {
      material.opacity = isDark() ? 0.85 : 0.5;
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  }

  // ── Route change detection (Fern is a SPA) ──────────────────────────────
  let lastPath = window.location.pathname;

  function checkRoute() {
    const cur = window.location.pathname;
    if (cur !== lastPath) {
      lastPath = cur;
      const existing = document.getElementById('fern-starfield');
      if (isLandingPage()) {
        if (!existing) init();
      } else {
        if (existing) {
          existing.style.opacity = '0';
          setTimeout(function () { existing.remove(); }, 1200);
        }
      }
    }
  }

  // Poll for route changes (Fern uses client-side routing)
  setInterval(checkRoute, 500);

  // ── Kick off ──────────────────────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
