/* bsandova.com — data stills: full-bleed, slowly moving "film frames" drawn from a project's own data.
   Reads a plate from assets/a24/ (a figure with only its data marks, see tools/a24_plates.py), splits it into
   lines, fills and points, and draws them on a canvas: a light band sweeps across the lines, points flicker,
   the frame drifts like a slow camera move. Only canvases on screen are animated.

   <canvas class="datastill" data-src="assets/a24/delayed.svg" data-view="0,0,1,1" data-fit="cover"></canvas>
   data-view: the part of the plate to frame, as fractions x,y,w,h of its viewBox. data-fit: cover | contain. */
(() => {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const cache = new Map();

  const nums = d => (d.match(/-?\d*\.?\d+(?:e-?\d+)?/gi) || []).map(Number);
  const subpaths = d => d.split(/(?=[Mm])/).map(s => s.trim()).filter(Boolean);

  function parse(text) {
    const doc = new DOMParser().parseFromString(text, 'image/svg+xml');
    const svg = doc.documentElement;
    const vb = (svg.getAttribute('viewBox') || '0 0 100 100').split(/\s+/).map(Number);
    const lines = [], fills = [], points = [];
    const isNone = (el, prop) => /none/.test((el.getAttribute('style') || '') + (el.getAttribute(prop) || '')) &&
      new RegExp(prop + ':\\s*none').test(el.getAttribute('style') || '');
    doc.querySelectorAll('defs path, clipPath path').forEach(p => p.setAttribute('data-skip', '1'));
    doc.querySelectorAll('path').forEach(p => {
      if (p.getAttribute('data-skip')) return;
      const style = p.getAttribute('style') || '';
      const filled = !/fill:\s*none/.test(style);
      const dashed = /stroke-dasharray/.test(style);
      for (const sp of subpaths(p.getAttribute('d') || '')) {
        const n = nums(sp); const pts = [];
        for (let i = 0; i + 1 < n.length; i += 2) pts.push([n[i], n[i + 1]]);
        if (!pts.length) continue;
        const xs = pts.map(q => q[0]), ys = pts.map(q => q[1]);
        const w = Math.max(...xs) - Math.min(...xs), h = Math.max(...ys) - Math.min(...ys);
        if (w < 3 && h < 3) points.push([(Math.max(...xs) + Math.min(...xs)) / 2, (Math.max(...ys) + Math.min(...ys)) / 2, 1]);
        else if (filled && /z\s*$/i.test(sp)) fills.push(pts);
        else if (pts.length > 1) lines.push({pts, dashed});
      }
    });
    doc.querySelectorAll('use').forEach(u => {
      const x = parseFloat(u.getAttribute('x')), y = parseFloat(u.getAttribute('y'));
      if (!isNaN(x) && !isNaN(y)) points.push([x, y, 1.6]);
    });
    const images = [];
    doc.querySelectorAll('image').forEach(im => {
      const href = im.getAttribute('xlink:href') || im.getAttribute('href');
      if (!href) return;
      const tr = im.getAttribute('transform') || '';
      const sc = (tr.match(/scale\(([^)]*)\)/) || [, '1 1'])[1].split(/[\s,]+/).map(Number);
      const tl = (tr.match(/translate\(([^)]*)\)/) || [, '0 0'])[1].split(/[\s,]+/).map(Number);
      const img = new Image(); img.src = href;
      images.push({img, x: +im.getAttribute('x') || 0, y: +im.getAttribute('y') || 0, w: +im.getAttribute('width'), h: +im.getAttribute('height'),
                   sx: sc[0], sy: sc.length > 1 ? sc[1] : sc[0], tx: tl[0] || 0, ty: tl[1] || 0});
    });
    return {vb, lines, fills, points, images};
  }

  function load(src) {
    if (!cache.has(src)) cache.set(src, fetch(src).then(r => r.text()).then(parse));
    return cache.get(src);
  }

  function mount(cv) {
    const view = (cv.dataset.view || '0,0,1,1').split(',').map(Number);
    const fit = cv.dataset.fit || 'cover';
    const ctx = cv.getContext('2d');
    let data = null, visible = false, t0 = performance.now(), raf = 0;
    const seed = [...(cv.dataset.src || '')].reduce((a, c) => a + c.charCodeAt(0), 0);

    load(cv.dataset.src).then(d => { data = d; kick(); });

    function frame(now) {
      raf = 0;
      if (!data || !visible) return;
      const still = cv.closest('.still');
      if (still && !still.classList.contains('on')) { raf = requestAnimationFrame(frame); return; }  // hidden hero frame: wait, don't draw
      const dpr = Math.min(devicePixelRatio || 1, 1.5);
      const W = cv.width = Math.round(cv.clientWidth * dpr), H = cv.height = Math.round(cv.clientHeight * dpr);
      const t = reduce ? 4 : (now - t0) / 1000;
      const [vx, vy, vw, vh] = [data.vb[0] + view[0] * data.vb[2], data.vb[1] + view[1] * data.vb[3], view[2] * data.vb[2], view[3] * data.vb[3]];
      const base = fit === 'cover' ? Math.max(W / vw, H / vh) : Math.min(W / vw, H / vh) * 0.86;
      const zoom = 1.02 + 0.035 * Math.sin(t / 9 + seed);
      const s = base * zoom;
      const ox = (W - vw * s) / 2 - vx * s + Math.sin(t / 11 + seed) * W * 0.012;
      const oy = (H - vh * s) / 2 - vy * s + Math.cos(t / 13 + seed) * H * 0.012;
      const X = x => ox + x * s, Y = y => oy + y * s;
      ctx.clearRect(0, 0, W, H);

      // raster layers (e.g. a density cloud): grey, breathing slowly
      for (const im of data.images) {
        if (!im.img.complete) continue;
        ctx.save(); ctx.translate(ox, oy); ctx.scale(s, s); ctx.scale(im.sx, im.sy); ctx.translate(im.tx, im.ty);
        ctx.filter = 'grayscale(1) brightness(1.6)'; ctx.globalAlpha = 0.55 + 0.2 * Math.sin(t / 3 + seed);
        ctx.drawImage(im.img, im.x, im.y, im.w, im.h); ctx.restore();
      }

      // fills: faint, brighter inside the moving light band
      const scan = ((t / 9) % 1.4 - 0.2) * W, band = W * 0.18;
      const drawFills = alpha => {
        ctx.fillStyle = `rgba(255,255,255,${alpha})`;
        for (const f of data.fills) { ctx.beginPath(); f.forEach(([x, y], i) => i ? ctx.lineTo(X(x), Y(y)) : ctx.moveTo(X(x), Y(y))); ctx.closePath(); ctx.fill(); }
      };
      const drawLines = (alpha, width) => {
        ctx.strokeStyle = `rgba(255,255,255,${alpha})`; ctx.lineWidth = width * dpr; ctx.lineJoin = 'round';
        for (const l of data.lines) {
          ctx.setLineDash(l.dashed ? [2 * dpr, 4 * dpr] : []);
          ctx.beginPath(); l.pts.forEach(([x, y], i) => i ? ctx.lineTo(X(x), Y(y)) : ctx.moveTo(X(x), Y(y))); ctx.stroke();
        }
        ctx.setLineDash([]);
      };
      drawFills(0.07); drawLines(0.42, 1.1);
      ctx.save(); ctx.beginPath(); ctx.rect(scan - band, 0, band * 2, H); ctx.clip();
      ctx.shadowColor = 'rgba(255,255,255,.8)'; ctx.shadowBlur = 10 * dpr;
      drawFills(0.16); drawLines(0.95, 1.5);
      ctx.restore();

      // points: flicker like stars
      for (let i = 0; i < data.points.length; i++) {
        const [x, y, r] = data.points[i];
        const a = 0.35 + 0.65 * Math.abs(Math.sin(t * (0.6 + (i % 7) * 0.13) + i));
        ctx.fillStyle = `rgba(255,255,255,${a * (r > 1 ? 1 : 0.6)})`;
        ctx.beginPath(); ctx.arc(X(x), Y(y), r * dpr * (r > 1 ? 1.4 : 1), 0, 7); ctx.fill();
      }
      if (!reduce) kick();
    }
    function kick() { if (!raf && visible && data) raf = requestAnimationFrame(frame); }
    new IntersectionObserver(es => { visible = es[0].isIntersecting; kick(); }, {rootMargin: '100px'}).observe(cv);
  }

  const start = () => document.querySelectorAll('canvas.datastill').forEach(mount);
  document.readyState === 'loading' ? addEventListener('DOMContentLoaded', start) : start();
  window.DataStill = {mount};
})();
