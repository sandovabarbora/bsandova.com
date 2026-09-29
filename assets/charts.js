/* Interactive charts for the articles. A <figure data-chart="path/charts.json#id"> keeps its static SVG as the
   fallback; this script replaces it with a chart drawn from the same numbers, adds a value on hover and on the arrow
   keys, a table view and a link to the data. No dependencies.

   A chart spec: {alt, panels:[{title, h, w, x:axis, y:axis, marks:[...]}], legend:[{label, c, dash, shape}],
   table:{cols, rows}, data:[paths]}. An axis: {kind:'linear'|'log'|'cat', domain, ticks, fmt, label}. A fmt:
   {dp, unit, pre, sign}. Marks: line, area, dots, hbar, range, rule, span, text (see draw() below). */
(() => {
  const NS = 'http://www.w3.org/2000/svg';
  const COL = {held: '#34507c', ink: '#111111', grey: '#666666', light: '#b5b5b0', grid: '#e6e6e3'};
  const DASH = {dash: '5 3', dot: '1.5 2.5', long: '8 4'};
  const col = c => COL[c] || c || COL.held;
  const nbsp = ' ';

  const fmt = (v, f = {}) => {
    if (v == null || Number.isNaN(v)) return '–';
    const dp = f.dp ?? 1;
    let s = Math.abs(v).toFixed(dp);
    if (!f.nogroup) { const [i, d] = s.split('.'); s = (i.length > 3 ? i.replace(/\B(?=(\d{3})+(?!\d))/g, nbsp) : i) + (d ? '.' + d : ''); }
    const sign = v < 0 ? '−' : (f.sign && v > 0 ? '+' : '');
    return (f.pre || '') + sign + s + (f.unit || '');
  };

  const maxLen = a => a.length ? Math.max(...a.map(s => s.length)) : 1;
  const el = (tag, attrs = {}, parent) => {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) if (v != null) e.setAttribute(k, v);
    if (parent) parent.appendChild(e);
    return e;
  };

  const scale = (ax, r0, r1) => {
    if (ax.kind === 'cat') {
      const n = ax.domain.length, step = (r1 - r0) / n;
      const f = v => r0 + step * (ax.domain.indexOf(v) + 0.5);
      f.step = step; f.cat = true; return f;
    }
    const [d0, d1] = ax.domain;
    if (ax.kind === 'log') {
      const l0 = Math.log10(d0), l1 = Math.log10(d1);
      return v => r0 + (Math.log10(v) - l0) / (l1 - l0) * (r1 - r0);
    }
    return v => r0 + (v - d0) / (d1 - d0) * (r1 - r0);
  };

  const niceTicks = ax => {
    if (ax.ticks) return ax.ticks;
    if (ax.kind === 'cat') return ax.domain;
    const [a, b] = ax.domain, span = b - a, raw = span / 5, p = 10 ** Math.floor(Math.log10(raw));
    const step = [1, 2, 5, 10].map(m => m * p).find(s => span / s <= 6);
    const out = [];
    for (let t = Math.ceil(a / step - 1e-9) * step; t <= b + 1e-9; t += step) out.push(+t.toFixed(10));
    return out;
  };

  // one panel into an <svg>; returns hover targets in svg coordinates
  function drawPanel(svg, P, box, narrow) {
    const targets = [];
    const g = el('g', {}, svg);
    const catY = P.y.kind === 'cat';
    const tickFmtX = P.x.tickfmt || P.x.fmt || {dp: 0, nogroup: P.x.year};
    const tickFmtY = P.y.tickfmt || P.y.fmt || {dp: 0};
    const yLabels = niceTicks(P.y).map(t => catY ? String(t) : fmt(t, {...tickFmtY, unit: ''}));
    const stackCats = catY && narrow;              // phone: category names sit above their row, not beside it
    const left = box.x + (catY ? (stackCats ? 4 : Math.min(box.w * 0.46, 12 + 6.4 * maxLen(yLabels))) : 10 + 6.6 * maxLen(yLabels));
    const top = box.y + (P.title ? 24 : 8) + (P.y.label && !catY ? 16 : 0);
    const bottom = box.y + box.h - (P.x.label ? 40 : 24);
    const right = box.x + box.w - (P.padRight ?? 12);
    const X = scale(P.x, left, right), Y = catY ? scale(P.y, top, bottom) : scale(P.y, bottom, top);

    if (P.title) el('text', {x: box.x, y: box.y + 12, class: 'ch-title'}, g).textContent = P.title;
    // grid and ticks
    const gx = el('g', {class: 'ch-axis'}, g);
    if (P.x.kind !== 'cat') for (const t of niceTicks(P.x)) {
      const x = X(t);
      if (!P.x.nogrid) el('line', {x1: x, x2: x, y1: top, y2: bottom, stroke: COL.grid}, gx);
      el('text', {x, y: bottom + 15, 'text-anchor': 'middle'}, gx).textContent = P.x.tickLabels?.[t] ?? fmt(t, {...tickFmtX, unit: ''});
    }
    if (!catY) for (const t of niceTicks(P.y)) {
      const y = Y(t);
      if (!P.y.nogrid) el('line', {x1: left, x2: right, y1: y, y2: y, stroke: COL.grid}, gx);
      el('text', {x: left - 6, y: y + 3.5, 'text-anchor': 'end'}, gx).textContent = P.y.tickLabels?.[t] ?? fmt(t, {...tickFmtY, unit: ''});
    } else for (const c of P.y.domain) {
      const y = Y(c);
      if (stackCats) el('text', {x: left, y: y - Y.step * 0.18, class: 'ch-cat'}, gx).textContent = c;
      else el('text', {x: left - 8, y: y + 4, 'text-anchor': 'end', class: 'ch-cat'}, gx).textContent = c;
    }
    el('line', {x1: left, x2: right, y1: bottom, y2: bottom, stroke: COL.grey, 'stroke-width': 1}, gx);
    if (P.x.label) el('text', {x: (left + right) / 2, y: bottom + 33, 'text-anchor': 'middle', class: 'ch-lab'}, gx).textContent = P.x.label;
    if (P.y.label && !catY) el('text', {x: left, y: top - 8, class: 'ch-lab'}, gx).textContent = P.y.label;
    const barY = c => stackCats ? Y(c) + Y.step * 0.12 : Y(c);

    const lines = [], placed = [];
    // a direct label is drawn only where it does not collide with one already placed; the tooltip still names it
    const free = (x, y, w) => { const b = [x, y - 10, w, 12]; if (b[0] + w > box.x + box.w || placed.some(q => b[0] < q[0] + q[2] && q[0] < b[0] + b[2] && b[1] < q[1] + q[3] && q[1] < b[1] + b[3])) return false; placed.push(b); return true; };
    for (const m of P.marks) {
      const c = col(m.c);
      if (m.type === 'span') {
        const a = X(m.v0), b = X(m.v1);
        el('rect', {x: Math.min(a, b), y: top, width: Math.abs(b - a), height: bottom - top, fill: c, 'fill-opacity': m.o ?? 0.1}, g);
        if (m.label) el('text', {x: Math.min(a, b) + 4, y: top + 12, class: 'ch-note', fill: c}, g).textContent = m.label;
      } else if (m.type === 'area') {
        const up = m.pts.map(p => `${X(p[0])},${Y(p[2])}`), dn = m.pts.slice().reverse().map(p => `${X(p[0])},${Y(p[1])}`);
        el('polygon', {points: up.concat(dn).join(' '), fill: c, 'fill-opacity': m.o ?? 0.14}, g);
        lines.push({m, band: true});
      } else if (m.type === 'line') {
        el('polyline', {points: m.pts.map(p => `${X(p[0])},${Y(p[1])}`).join(' '), fill: 'none', stroke: c, 'stroke-width': m.w ?? 2,
          'stroke-dasharray': DASH[m.dash], 'stroke-linejoin': 'round', 'stroke-linecap': 'round'}, g);
        if (m.dots) for (const p of m.pts) el('circle', {cx: X(p[0]), cy: Y(p[1]), r: 3, fill: c}, g);
        lines.push({m});
      } else if (m.type === 'rule') {
        const d = {stroke: c, 'stroke-width': m.w ?? 1, 'stroke-dasharray': DASH[m.dash]};
        if (m.axis === 'x') {
          const x = X(m.v); el('line', {...d, x1: x, x2: x, y1: top, y2: bottom}, g);
          if (m.label) el('text', {x: x + (m.anchor === 'end' ? -4 : 4), y: top + (m.dy ?? 10), 'text-anchor': m.anchor || 'start', class: 'ch-note', fill: c}, g).textContent = m.label;
          if (m.tip) targets.push({px: x, py: top + 10, tip: m.tip});
        } else {
          const y = Y(m.v); el('line', {...d, x1: left, x2: right, y1: y, y2: y}, g);
          if (m.label) el('text', {x: m.anchor === 'end' ? right - 4 : left + 4, y: y - 5, 'text-anchor': m.anchor || 'start', class: 'ch-note', fill: c}, g).textContent = m.label;
        }
      } else if (m.type === 'hbar') {
        for (const r of m.rows) {
          const y = barY(r.y), bh = Math.min(22, Y.step * (stackCats ? 0.38 : 0.5)), c2 = col(r.c || m.c);
          const a = X(r.x0 ?? (P.x.kind === 'log' ? P.x.domain[0] : 0)), b = X(r.x1);
          el('rect', {x: Math.min(a, b), y: y - bh / 2, width: Math.max(1, Math.abs(b - a)), height: bh, fill: c2, 'fill-opacity': m.o ?? 0.85, rx: 1}, g);
          if (r.lo != null) {
            el('line', {x1: X(r.lo), x2: X(r.hi), y1: y, y2: y, stroke: COL.ink, 'stroke-width': 1.2}, g);
            for (const v of [r.lo, r.hi]) el('line', {x1: X(v), x2: X(v), y1: y - 5, y2: y + 5, stroke: COL.ink, 'stroke-width': 1.2}, g);
          }
          if (r.label) { const lx = Math.max(a, b, r.hi != null ? X(r.hi) : 0) + 6, over = lx + 6.6 * r.label.length > box.x + box.w;
            el('text', over ? {x: Math.min(a, b), y: y - bh / 2 - 5, class: 'ch-val'} : {x: lx, y: y + 4, class: 'ch-val'}, g).textContent = r.label; }
          targets.push({px: b, py: y, tip: r.tip, box: [Math.min(a, b), y - bh / 2, Math.abs(b - a), bh]});
        }
      } else if (m.type === 'range') {
        for (const r of m.rows) {
          const y = catY ? barY(r.y) : Y(r.y), c2 = col(r.c || m.c);
          if (r.lo != null) el('line', {x1: X(r.lo), x2: X(r.hi), y1: y, y2: y, stroke: c2, 'stroke-width': m.w ?? 3, 'stroke-linecap': 'round'}, g);
          const x = X(r.mid);
          if (r.shape === 'd') el('rect', {x: x - 4.5, y: y - 4.5, width: 9, height: 9, transform: `rotate(45 ${x} ${y})`, fill: col(r.fill || 'light'), stroke: COL.grey}, g);
          else el('circle', {cx: x, cy: y, r: 5, fill: c2, stroke: '#fff', 'stroke-width': 2}, g);
          if (r.label) { const lx = X(r.hi ?? r.mid) + 9, over = lx + 6.6 * r.label.length > box.x + box.w;
            el('text', over ? {x: X(r.lo ?? r.mid), y: y - 9, class: 'ch-val'} : {x: lx, y: y + 4, class: 'ch-val'}, g).textContent = r.label; }
          targets.push({px: x, py: y, tip: r.tip, box: r.lo != null ? [X(r.lo), y - 8, X(r.hi) - X(r.lo), 16] : null});
        }
      } else if (m.type === 'dots') {
        for (const p of m.pts) {
          const x = X(p.x), y = Y(p.y), c2 = col(p.c || m.c);
          if ((p.shape || m.shape) === 'd') el('rect', {x: x - 4.5, y: y - 4.5, width: 9, height: 9, transform: `rotate(45 ${x} ${y})`, fill: c2}, g);
          else el('circle', {cx: x, cy: y, r: p.r || m.r || 4.5, fill: c2, stroke: '#fff', 'stroke-width': 1.5}, g);
          if (p.label && !narrow) { const w = 6.4 * p.label.length;
            const spot = [[x + 7, y + (p.dy ?? 4)], [x + 7, y - 9], [x + 7, y + 15], [x - 7 - w, y + 4]].find(([lx, ly]) => free(lx, ly, w));
            if (spot) el('text', {x: spot[0], y: spot[1], class: 'ch-note', fill: c2}, g).textContent = p.label; }
          targets.push({px: x, py: y, tip: p.tip});
        }
      } else if (m.type === 'text') {
        el('text', {x: X(m.x), y: Y(m.y), 'text-anchor': m.anchor || 'start', class: 'ch-note', fill: col(m.c)}, g).textContent = m.s;
      }
    }
    // lines and bands: one crosshair target per x of the first line, listing every series at that x
    if (lines.length) {
      const xs = [...new Set(lines.flatMap(l => l.m.pts.map(p => p[0])))].sort((a, b) => a - b);
      for (const xv of xs) {
        const rows = [];
        for (const {m, band} of lines) {
          const p = m.pts.find(q => q[0] === xv);
          if (!p || m.notip) continue;
          rows.push(`${m.name}: ${band ? fmt(p[1], m.fmt) + '–' + fmt(p[2], m.fmt) : fmt(p[1], m.fmt)}`);
        }
        if (!rows.length) continue;
        const ys = lines.filter(l => !l.band).map(l => l.m.pts.find(q => q[0] === xv)).filter(Boolean).map(p => ({y: Y(p[1])}));
        targets.push({px: X(xv), py: ys.length ? Math.min(...ys.map(q => q.y)) : top, xonly: true, cross: [top, bottom],
          marks: lines.filter(l => !l.band).map(l => ({p: l.m.pts.find(q => q[0] === xv), c: col(l.m.c)})).filter(q => q.p).map(q => ({x: X(q.p[0]), y: Y(q.p[1]), c: q.c})),
          tip: [fmt(xv, P.x.fmt || {dp: 0, nogroup: true}), ...rows].join('\n')});
      }
    }
    return targets;
  }

  function render(fig, spec) {
    const holder = fig.querySelector('.ch');
    const W = holder.clientWidth;
    if (!W) return;
    const narrow = W < 560;
    holder.querySelector('svg')?.remove();
    const stack = narrow && spec.panels.length > 1;
    const totalW = spec.panels.reduce((s, p) => s + (p.w || 1), 0);
    const heights = spec.panels.map(p => (p.h || 260) + (p.title ? 16 : 0) + (narrow && p.y.kind === 'cat' ? p.y.domain.length * 12 : 0));
    const H = stack ? heights.reduce((a, b) => a + b + 18, 0) : Math.max(...heights);
    const svg = el('svg', {viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: 'img', 'aria-label': spec.alt || '', tabindex: 0, class: 'ch-svg'});
    holder.prepend(svg);
    let targets = [], x = 0, y = 0;
    spec.panels.forEach((P, i) => {
      const w = stack ? W : W * (P.w || 1) / totalW - (i < spec.panels.length - 1 ? 16 : 0);
      targets = targets.concat(drawPanel(svg, P, {x, y, w, h: stack ? heights[i] : H}, narrow));
      if (stack) y += heights[i] + 18; else x += w + 16;
    });
    const hover = el('g', {class: 'ch-hover'}, svg);
    const tip = holder.querySelector('.ch-tip');
    let cur = -1;
    const show = i => {
      cur = i; hover.innerHTML = '';
      if (i < 0) { tip.hidden = true; return; }
      const t = targets[i];
      if (t.cross) {
        el('line', {x1: t.px, x2: t.px, y1: t.cross[0], y2: t.cross[1], stroke: COL.ink, 'stroke-width': 1, 'stroke-dasharray': '2 3'}, hover);
        for (const q of t.marks) el('circle', {cx: q.x, cy: q.y, r: 4.5, fill: q.c, stroke: '#fff', 'stroke-width': 2}, hover);
      } else el('circle', {cx: t.px, cy: t.py, r: 9, fill: 'none', stroke: COL.ink, 'stroke-width': 1}, hover);
      tip.textContent = t.tip; tip.hidden = false;
      const tw = tip.offsetWidth, th = tip.offsetHeight;
      let lx = t.px + 14, ly = t.py - th - 10;
      if (lx + tw > W) lx = t.px - tw - 14;
      if (ly < 0) ly = t.py + 14;
      tip.style.transform = `translate(${Math.max(0, lx)}px, ${ly}px)`;
    };
    const pick = (mx, my) => {
      let best = -1, bd = 1e9;
      targets.forEach((t, i) => {
        if (t.xonly) return;
        const inBox = t.box && mx >= t.box[0] - 4 && mx <= t.box[0] + t.box[2] + 4 && my >= t.box[1] - 4 && my <= t.box[1] + t.box[3] + 4;
        const d = inBox ? 0 : Math.hypot(mx - t.px, my - t.py);
        if (d < bd) { bd = d; best = i; }
      });
      if (bd <= 22) return best;
      targets.forEach((t, i) => {
        if (!t.xonly || my < t.cross[0] - 10 || my > t.cross[1] + 10) return;
        const d = Math.abs(mx - t.px) + 30;
        if (d < bd) { bd = d; best = i; }
      });
      return bd < 80 ? best : -1;
    };
    svg.addEventListener('pointermove', e => {
      const r = svg.getBoundingClientRect();
      const i = pick(e.clientX - r.left, e.clientY - r.top);
      if (i !== cur) show(i);
    });
    svg.addEventListener('pointerleave', () => show(-1));
    svg.addEventListener('keydown', e => {
      if (!targets.length) return;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { show((cur + 1) % targets.length); e.preventDefault(); }
      else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { show((cur - 1 + targets.length) % targets.length); e.preventDefault(); }
      else if (e.key === 'Escape') show(-1);
    });
    svg.addEventListener('blur', () => show(-1));
  }

  function mount(fig, spec, dataUrl) {
    const img = fig.querySelector('img');
    const holder = document.createElement('div');
    holder.className = 'ch';
    const tipEl = holder.appendChild(document.createElement('div'));
    tipEl.className = 'ch-tip'; tipEl.setAttribute('role', 'status'); tipEl.hidden = true;
    if (spec.legend?.length) {
      const lg = document.createElement('ul');
      lg.className = 'ch-legend';
      for (const l of spec.legend) {
        const li = document.createElement('li');
        if (l.shape === 'd' || l.shape === 'box' || l.shape === 'o') {
          const i = li.appendChild(document.createElement('i'));
          i.className = l.shape; i.style.background = col(l.c); if (l.shape === 'box') i.style.opacity = l.o ?? 0.3;
        } else {
          const s = el('svg', {width: 22, height: 8, 'aria-hidden': 'true'});
          el('line', {x1: 1, x2: 21, y1: 4, y2: 4, stroke: col(l.c), 'stroke-width': 2, 'stroke-dasharray': DASH[l.dash]}, s);
          li.appendChild(s);
        }
        li.append(l.label);
        lg.appendChild(li);
      }
      fig.insertBefore(lg, img);
    }
    fig.insertBefore(holder, img);
    const table = document.createElement('div');
    table.className = 'ch-table'; table.hidden = true;
    if (spec.table) {
      const t = document.createElement('table'), hd = t.createTHead().insertRow(), bd = t.createTBody();
      for (const c of spec.table.cols) hd.appendChild(document.createElement('th')).textContent = c;
      for (const r of spec.table.rows) { const tr = bd.insertRow(); for (const v of r) tr.insertCell().textContent = v; }
      table.appendChild(t);
    }
    fig.insertBefore(table, img);
    const ctl = document.createElement('p');
    ctl.className = 'ch-ctl';
    const b1 = Object.assign(document.createElement('button'), {type: 'button', textContent: 'chart'});
    const b2 = Object.assign(document.createElement('button'), {type: 'button', textContent: 'table'});
    b1.setAttribute('aria-pressed', 'true'); b2.setAttribute('aria-pressed', 'false');
    const setView = tbl => { holder.hidden = tbl; table.hidden = !tbl; b1.setAttribute('aria-pressed', String(!tbl)); b2.setAttribute('aria-pressed', String(tbl)); };
    b1.onclick = () => setView(false); b2.onclick = () => setView(true);
    ctl.append(b1, b2);
    if (!spec.table) b2.remove();
    for (const d of spec.data || [dataUrl]) {
      const a = Object.assign(document.createElement('a'), {href: d, textContent: 'data · ' + d.split('/').pop()});
      ctl.append(a);
    }
    const hint = ctl.appendChild(document.createElement('span'));
    hint.className = 'ch-hint'; hint.textContent = 'hover or use the arrow keys for values';
    fig.insertBefore(ctl, img);
    img.hidden = true;
    fig.classList.add('ch-live');
    render(fig, spec);
    let raf = 0;
    new ResizeObserver(() => { cancelAnimationFrame(raf); raf = requestAnimationFrame(() => render(fig, spec)); }).observe(holder);
  }

  const cache = {};
  document.querySelectorAll('figure[data-chart]').forEach(fig => {
    const [url, id] = fig.dataset.chart.split('#');
    (cache[url] ||= fetch(url).then(r => r.ok ? r.json() : Promise.reject(r.status)))
      .then(all => { if (all[id]) mount(fig, all[id], url); })
      .catch(() => {});  // the static figure stays
  });
})();
