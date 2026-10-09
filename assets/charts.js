/* Interactive charts for the articles. A <figure data-chart="path/charts.json#id"> keeps its static SVG as the
   fallback; this script replaces it with a chart drawn from the same numbers, adds a value on hover and on the arrow
   keys, a table view and a link to the data. No dependencies.

   A chart spec: {alt, panels:[{title, h, w, x:axis, y:axis, marks:[...]}], legend:[{label, c, dash, shape: d|box|o|dot}],
   table:{cols, rows}, data:[paths]}. An axis: {kind:'linear'|'log'|'cat', domain, ticks, fmt, label}. A fmt:
   {dp, unit, pre, sign}. Marks: line, area, dots, hbar, vbar, range, vrange, arrow, cell, rule, span, text (see drawPanel).
   spec.layout: 'rows' stacks the panels vertically at every width. An axis with labels:false draws no category names.
   A line may carry o (opacity) and end (a label at its last point, in ink; give the panel padRight for it); a callout
   {x, y, s, dx, dy, anchor, narrow:{...}} ties a short note to one data point. Data marks wipe in from the left the
   first time a figure is half in view (not under prefers-reduced-motion), and a paragraph with
   data-focus="<chart id>:<series>[,<series>]" keeps those lines strong, the others receding, while it is read. */
(() => {
  const NS = 'http://www.w3.org/2000/svg';
  const COL = {held: '#34507c', ink: '#111111', grey: '#666666', light: '#b5b5b0', grid: '#e6e6e3'};
  const DASH = {dash: '5 3', dot: '1.5 2.5', long: '8 4'};
  const col = c => COL[c] || c || COL.held;
  const nbsp = ' ';
  const still = matchMedia('(prefers-reduced-motion: reduce)');
  let uid = 0;

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
  // how category names fit a slot of the given width: {parts per name, lines, every k-th shown}
  function catLayout(names, slot) {
    const w = n => 6.6 * n + 6;
    if (slot >= w(Math.max(...names.map(n => n.length)))) return {parts: names.map(n => [n]), lines: 1, every: 1};
    const split = names.map(splitMid);
    if (slot >= w(Math.max(...split.flat().map(n => n.length)))) return {parts: split, lines: 2, every: 1};
    const every = Math.ceil(w(Math.max(...names.map(n => n.length))) / slot);
    return {parts: names.map(n => [n]), lines: 1, every};
  }

  function splitMid(s) {
    const mid = s.length / 2;
    let k = -1;
    for (let i = s.indexOf(' '); i >= 0; i = s.indexOf(' ', i + 1)) if (k < 0 || Math.abs(i - mid) < Math.abs(k - mid)) k = i;
    return k < 0 ? [s] : [s.slice(0, k), s.slice(k + 1)];
  }

  function drawPanel(svg, P, box, narrow) {
    const targets = [];
    const g = el('g', {}, svg);
    const catY = P.y.kind === 'cat';
    // ticks without a format get as many decimals as their step needs
    const autoDp = ax => ax.kind === 'cat' ? 0 : Math.max(0, ...niceTicks(ax).map(t => (String(t).split('.')[1] || '').length));
    const tickFmtX = P.x.tickfmt || (P.x.fmt && {...P.x.fmt, dp: Math.max(P.x.fmt.dp ?? 0, autoDp(P.x))}) || {dp: autoDp(P.x), nogroup: P.x.year};
    const tickFmtY = P.y.tickfmt || (P.y.fmt && {...P.y.fmt, dp: Math.max(P.y.fmt.dp ?? 0, autoDp(P.y))}) || {dp: autoDp(P.y)};
    const yLabels = niceTicks(P.y).map(t => catY ? String(t) : fmt(t, {...tickFmtY, unit: ''}));
    const stackCats = catY && narrow;              // phone: category names sit above their row, not beside it
    const left = box.x + (catY ? (stackCats ? 4 : Math.min(box.w * 0.46, 12 + 7.2 * maxLen(yLabels))) : 10 + 6.6 * maxLen(yLabels));
    const top = box.y + (P.title ? 24 : 8) + (P.y.label && !catY ? 16 : 0);
    // an x-axis title wider than the panel breaks at the space nearest its middle, and the panel keeps room for both lines
    const xLab = P.x.label ? (6.6 * P.x.label.length > box.w - 8 ? splitMid(P.x.label) : [P.x.label]) : [];
    const right = box.x + box.w - (P.padRight ?? 12);
    // category names under the x axis: one line if they fit, else two lines at a space, else every k-th name
    const xCats = P.x.kind === 'cat' && P.x.labels !== false ? catLayout(P.x.domain.map(String), (right - left) / P.x.domain.length) : null;
    const catExtra = xCats && xCats.lines > 1 ? 12 : 0;
    const bottom = box.y + box.h - (xLab.length ? 28 + 12 * xLab.length : 24) - catExtra;
    const X = scale(P.x, left, right), Y = catY ? scale(P.y, top, bottom) : scale(P.y, bottom, top);

    if (P.title) el('text', {x: box.x, y: box.y + 12, class: 'ch-title'}, g).textContent = P.title;
    // grid and ticks
    const gx = el('g', {class: 'ch-axis'}, g);
    if (xCats) {
      const Xc = scale(P.x, left, right);
      P.x.domain.forEach((c, i) => {
        if (i % xCats.every) return;
        const t = el('text', {x: Xc(c), y: bottom + 15, 'text-anchor': 'middle', class: 'ch-cat'}, gx);
        xCats.parts[i].forEach((line, j) => el('tspan', {x: Xc(c), dy: j ? 12 : 0}, t).textContent = line);
      });
    }
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
    xLab.forEach((t, i) => {
      const cx = xLab.length > 1 ? box.x + box.w / 2 : (left + right) / 2;
      el('text', {x: cx, y: bottom + 33 + catExtra + 13 * i, 'text-anchor': 'middle', class: 'ch-lab'}, gx).textContent = t;
    });
    if (P.y.label && !catY) el('text', {x: left, y: top - 8, class: 'ch-lab'}, gx).textContent = P.y.label;
    const barY = c => stackCats ? Y(c) + Y.step * 0.12 : Y(c);

    const clip = el('rect', {x: box.x - 4, y: box.y - 4, width: box.w + 8, height: box.h + 8}, el('clipPath', {id: `chc${++uid}`}, el('defs', {}, g)));
    const gm = el('g', {'clip-path': `url(#chc${uid})`}, g);
    const lines = [], placed = [], ends = [];
    // a direct label is drawn only where it does not collide with one already placed; the tooltip still names it
    const free = (x, y, w) => { const b = [x, y - 10, w, 12]; if (b[0] + w > box.x + box.w || placed.some(q => b[0] < q[0] + q[2] && q[0] < b[0] + b[2] && b[1] < q[1] + q[3] && q[1] < b[1] + b[3])) return false; placed.push(b); return true; };
    for (const m of P.marks) {
      const c = col(m.c);
      if (m.type === 'span') {
        const a = X(m.v0), b = X(m.v1);
        el('rect', {x: Math.min(a, b), y: top, width: Math.abs(b - a), height: bottom - top, fill: c, 'fill-opacity': m.o ?? 0.1}, gm);
        if (m.label) el('text', {x: Math.min(a, b) + 4, y: top + 12, class: 'ch-note', fill: c}, gm).textContent = m.label;
      } else if (m.type === 'area') {
        const up = m.pts.map(p => `${X(p[0])},${Y(p[2])}`), dn = m.pts.slice().reverse().map(p => `${X(p[0])},${Y(p[1])}`);
        el('polygon', {points: up.concat(dn).join(' '), fill: c, 'fill-opacity': m.o ?? 0.14}, gm);
        lines.push({m, band: true});
      } else if (m.type === 'line') {
        el('polyline', {points: m.pts.map(p => `${X(p[0])},${Y(p[1])}`).join(' '), fill: 'none', stroke: c, 'stroke-width': m.w ?? 2,
          'stroke-dasharray': DASH[m.dash], 'stroke-linejoin': 'round', 'stroke-linecap': 'round', 'stroke-opacity': m.o,
          class: 'ch-line', 'data-key': m.name}, gm);
        if (m.end) ends.push({m, c, p: m.pts[m.pts.length - 1]});
        if (m.dots) for (const p of m.pts) el('circle', {cx: X(p[0]), cy: Y(p[1]), r: 3, fill: c}, gm);
        lines.push({m});
      } else if (m.type === 'rule') {
        const d = {stroke: c, 'stroke-width': m.w ?? 1, 'stroke-dasharray': DASH[m.dash]};
        if (m.axis === 'x') {
          const x = X(m.v); el('line', {...d, x1: x, x2: x, y1: top, y2: bottom}, gm);
          if (m.label) el('text', {x: x + (m.anchor === 'end' ? -4 : 4), y: top + (m.dy ?? 10), 'text-anchor': m.anchor || 'start', class: 'ch-note', fill: c}, gm).textContent = m.label;
          if (m.tip) targets.push({px: x, py: top + 10, tip: m.tip});
        } else {
          const y = Y(m.v); el('line', {...d, x1: left, x2: right, y1: y, y2: y}, gm);
          if (m.label) el('text', {x: m.anchor === 'end' ? right - 4 : left + 4, y: y - 5, 'text-anchor': m.anchor || 'start', class: 'ch-note', fill: c}, gm).textContent = m.label;
        }
      } else if (m.type === 'hbar') {
        for (const r of m.rows) {
          const y = barY(r.y), bh = Math.min(22, Y.step * (stackCats ? 0.38 : 0.5)), c2 = col(r.c || m.c);
          const a = X(r.x0 ?? (P.x.kind === 'log' ? P.x.domain[0] : 0)), b = X(r.x1);
          el('rect', {x: Math.min(a, b), y: y - bh / 2, width: Math.max(1, Math.abs(b - a)), height: bh, fill: c2, 'fill-opacity': m.o ?? 0.85, rx: 1}, gm);
          if (r.lo != null) {
            el('line', {x1: X(r.lo), x2: X(r.hi), y1: y, y2: y, stroke: COL.ink, 'stroke-width': 1.2}, gm);
            for (const v of [r.lo, r.hi]) el('line', {x1: X(v), x2: X(v), y1: y - 5, y2: y + 5, stroke: COL.ink, 'stroke-width': 1.2}, gm);
          }
          if (r.label) { const lx = Math.max(a, b, r.hi != null ? X(r.hi) : 0) + 6, over = lx + 6.6 * r.label.length > box.x + box.w;
            el('text', over ? {x: Math.min(a, b), y: y - bh / 2 - 5, class: 'ch-val'} : {x: lx, y: y + 4, class: 'ch-val'}, gm).textContent = r.label; }
          targets.push({px: b, py: y, tip: r.tip, box: [Math.min(a, b), y - bh / 2, Math.abs(b - a), bh]});
        }
      } else if (m.type === 'range') {
        for (const r of m.rows) {
          const y = catY ? barY(r.y) : Y(r.y), c2 = col(r.c || m.c);
          if (r.lo != null) el('line', {x1: X(r.lo), x2: X(r.hi), y1: y, y2: y, stroke: c2, 'stroke-width': m.w ?? 3, 'stroke-linecap': 'round'}, gm);
          const x = X(r.mid);
          if (r.shape === 'd') el('rect', {x: x - 4.5, y: y - 4.5, width: 9, height: 9, transform: `rotate(45 ${x} ${y})`, fill: col(r.fill || 'light'), stroke: COL.grey}, gm);
          else el('circle', {cx: x, cy: y, r: 5, fill: c2, stroke: '#fff', 'stroke-width': 2}, gm);
          if (r.label) { const lx = X(r.hi ?? r.mid) + 9, over = lx + 6.6 * r.label.length > box.x + box.w;
            el('text', over ? {x: X(r.lo ?? r.mid), y: y - 9, class: 'ch-val'} : {x: lx, y: y + 4, class: 'ch-val'}, gm).textContent = r.label; }
          targets.push({px: x, py: y, tip: r.tip, box: r.lo != null ? [X(r.lo), y - 8, X(r.hi) - X(r.lo), 16] : null});
        }
      } else if (m.type === 'dots') {
        for (const p of m.pts) {
          const x = X(p.x), y = Y(p.y), c2 = col(p.c || m.c);
          if ((p.shape || m.shape) === 'd') el('rect', {x: x - 4.5, y: y - 4.5, width: 9, height: 9, transform: `rotate(45 ${x} ${y})`, fill: c2}, gm);
          else el('circle', {cx: x, cy: y, r: p.r || m.r || 4.5, fill: c2, 'fill-opacity': p.o ?? m.o ?? 1, stroke: '#fff', 'stroke-width': 1.5}, gm);
          if (p.ring) el('circle', {cx: x, cy: y, r: (p.r || m.r || 4.5) + 3, fill: 'none', stroke: COL.ink, 'stroke-width': 1.2}, gm);
          if (p.label && !narrow) { const w = 6.4 * p.label.length;
            const spot = [[x + 7, y + (p.dy ?? 4)], [x + 7, y - 9], [x + 7, y + 15], [x - 7 - w, y + 4]].find(([lx, ly]) => free(lx, ly, w));
            if (spot) el('text', {x: spot[0], y: spot[1], class: 'ch-note', fill: c2}, gm).textContent = p.label; }
          targets.push({px: x, py: y, tip: p.tip});
        }
      } else if (m.type === 'vbar') {
        // vertical bars on a category x; stacked segments share an x and give y0/y1
        for (const r of m.rows) {
          const x = X(r.x), bw = Math.max(2, Math.min(40, X.step * 0.7)), c2 = col(r.c || m.c);
          const a = Y(r.y0 ?? (P.y.kind === 'log' ? P.y.domain[0] : 0)), b = Y(r.y1);
          el('rect', {x: x - bw / 2, y: Math.min(a, b), width: bw, height: Math.max(1, Math.abs(b - a)), fill: c2, 'fill-opacity': r.o ?? m.o ?? 0.85, rx: 1}, gm);
          if (r.lo != null) el('line', {x1: x, x2: x, y1: Y(r.lo), y2: Y(r.hi), stroke: COL.ink, 'stroke-width': 1.2}, gm);
          if (r.label && bw >= 14) el('text', {x, y: Math.min(a, b) - 5, 'text-anchor': 'middle', class: 'ch-val'}, gm).textContent = r.label;
          targets.push({px: x, py: Math.min(a, b), tip: r.tip, box: [x - bw / 2, Math.min(a, b), bw, Math.abs(b - a)]});
        }
      } else if (m.type === 'vrange') {
        // vertical intervals: rows {x, lo, hi, mid}
        for (const r of m.rows) {
          const x = X(r.x), c2 = col(r.c || m.c);
          if (r.lo != null) el('line', {x1: x, x2: x, y1: Y(r.lo), y2: Y(r.hi), stroke: c2, 'stroke-width': m.w ?? 2, 'stroke-linecap': 'round', 'stroke-opacity': r.o ?? 1}, gm);
          const y = Y(r.mid);
          el('circle', {cx: x, cy: y, r: m.r ?? 4, fill: c2, stroke: '#fff', 'stroke-width': 1.5}, gm);
          targets.push({px: x, py: y, tip: r.tip, box: r.lo != null ? [x - 6, Math.min(Y(r.lo), Y(r.hi)), 12, Math.abs(Y(r.hi) - Y(r.lo))] : null});
        }
      } else if (m.type === 'arrow') {
        // rows {y, from, to}: a change drawn as an arrow along x
        for (const r of m.rows) {
          const y = catY ? barY(r.y) : Y(r.y), a = X(r.from), b = X(r.to), c2 = col(r.c || m.c), d = b >= a ? 1 : -1;
          el('line', {x1: a, x2: b - d * 6, y1: y, y2: y, stroke: c2, 'stroke-width': 2}, gm);
          el('path', {d: `M${b},${y} l${-d * 8},-4.5 l0,9 z`, fill: c2}, gm);
          el('circle', {cx: a, cy: y, r: 4, fill: col(r.fromC || 'light'), stroke: COL.grey}, gm);
          if (r.label) el('text', {x: Math.max(a, b) + 8, y: y + 4, class: 'ch-val'}, gm).textContent = r.label;
          targets.push({px: b, py: y, tip: r.tip, box: [Math.min(a, b), y - 7, Math.abs(b - a), 14]});
        }
      } else if (m.type === 'cell') {
        // a matrix on two category axes: rows {x, y, v, s (text), tip}; shade is one hue, light to dark over m.domain
        const [v0, v1] = m.domain;
        for (const r of m.rows) {
          const cx = X(r.x), cy = Y(r.y), w = X.step - 4, h = Y.step - 4, t = Math.max(0, Math.min(1, (r.v - v0) / (v1 - v0)));
          el('rect', {x: cx - w / 2, y: cy - h / 2, width: w, height: h, fill: col(m.c), 'fill-opacity': 0.08 + 0.72 * t, rx: 2}, gm);
          el('text', {x: cx, y: cy + 4, 'text-anchor': 'middle', class: 'ch-val', style: t > 0.55 ? 'fill:#fff;stroke:none' : null}, gm).textContent = r.s;
          targets.push({px: cx, py: cy, tip: r.tip, box: [cx - w / 2, cy - h / 2, w, h]});
        }
      } else if (m.type === 'callout') {
        // a note tied to one data point by a short leader; narrow screens may give their own offsets or text
        const k = {...m, ...(narrow && m.narrow || {})}, x = X(k.x), y = Y(k.y), tx = x + (k.dx ?? 0), ty = y + (k.dy ?? -30);
        const rows = String(k.s).split('\n');
        el('line', {x1: x, y1: y, x2: tx, y2: ty < y ? ty + 4 + 13 * (rows.length - 1) : ty - 12, stroke: COL.ink, 'stroke-width': 0.8}, gm);
        el('circle', {cx: x, cy: y, r: 3, fill: '#fff', stroke: COL.ink, 'stroke-width': 1.2}, gm);
        const t = el('text', {x: tx, y: ty, 'text-anchor': k.anchor || 'middle', class: 'ch-callout'}, gm);
        rows.forEach((row, i) => { el('tspan', {x: tx, dy: i ? 13 : 0}, t).textContent = row; });
      } else if (m.type === 'text') {
        // a plain note; narrow screens may give their own x, offsets, anchor or text
        const k = {...m, ...(narrow && m.narrow || {})};
        el('text', {x: X(k.x) + (k.dx ?? 0), y: Y(k.y) + (k.dy ?? 0), 'text-anchor': k.anchor || 'start', class: 'ch-note',
                    fill: col(k.c)}, gm).textContent = k.s;
      }
    }
    // direct labels at line ends, in ink beside a dot of the series colour, pushed apart so they never overlap
    // all in one column right of the last x, so a series that ends early never lands on another's last point
    ends.sort((a, b) => Y(a.p[1]) - Y(b.p[1]));
    const ex = Math.max(...ends.map(e => X(e.p[0])), 0) + 8;
    let lastY = -1e9;
    for (const {m, c, p} of ends) {
      const y = Math.max(Y(p[1]) + 4, lastY + 14);
      lastY = y;
      el('circle', {cx: X(p[0]), cy: Y(p[1]), r: 3.5, fill: c, stroke: '#fff', 'stroke-width': 1.5, 'data-key': m.name}, gm);
      el('line', {x1: ex, x2: ex + 8, y1: y - 4, y2: y - 4, stroke: c, 'stroke-width': 3, 'stroke-linecap': 'round', 'data-key': m.name}, gm);
      el('text', {x: ex + 12, y, class: 'ch-end', 'data-key': m.name}, gm).textContent = m.end === true ? m.name : m.end;
    }
    // white halo as its own layer under each label: Safari ignores paint-order on some text and paints the stroke over the glyphs
    for (const t of g.querySelectorAll('text.ch-callout,text.ch-end,text.ch-note,text.ch-cat,text.ch-val')) {
      if ((t.getAttribute('style') || '').includes('stroke:none')) continue;
      const h = t.cloneNode(true);
      h.classList.add('ch-halo'); h.setAttribute('aria-hidden', 'true');
      t.parentNode.insertBefore(h, t);
      t.classList.add('ch-ink');
    }
    targets.clip = {rect: clip, x0: left - box.x + 4, w: box.w + 8};
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
    const stack = (narrow || spec.layout === 'rows') && spec.panels.length > 1;
    const totalW = spec.panels.reduce((s, p) => s + (p.w || 1), 0);
    const heights = spec.panels.map(p => (p.h || 260) + (p.title ? 16 : 0) + (narrow && p.y.kind === 'cat' ? p.y.domain.length * 12 : 0));
    const H = stack ? heights.reduce((a, b) => a + b + 18, 0) : Math.max(...heights);
    const svg = el('svg', {viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: 'img', 'aria-label': spec.alt || '', tabindex: 0, class: 'ch-svg'});
    holder.prepend(svg);
    let targets = [], x = 0, y = 0;
    const clips = [];
    spec.panels.forEach((P, i) => {
      const w = stack ? W : W * (P.w || 1) / totalW - (i < spec.panels.length - 1 ? 16 : 0);
      const t = drawPanel(svg, P, {x, y, w, h: stack ? heights[i] : H}, narrow);
      clips.push(t.clip);
      targets = targets.concat(t);
      if (stack) y += heights[i] + 18; else x += w + 16;
    });
    reveal(fig, clips);
    focus(fig);
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
      else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { show(cur < 0 ? targets.length - 1 : (cur - 1 + targets.length) % targets.length); e.preventDefault(); }
      else if (e.key === 'Escape') show(-1);
    });
    svg.addEventListener('blur', () => show(-1));
  }

  // data marks wipe in from the left the first time the figure is half in view; after that, on every re-render and
  // under reduced motion, they are simply there
  function reveal(fig, clips) {
    const set = k => clips.forEach(c => c.rect.setAttribute('width', c.x0 + (c.w - c.x0) * k));
    if (fig.dataset.shown || still.matches || !('IntersectionObserver' in window)) { set(1); fig.dataset.shown = '1'; return; }
    set(0);
    fig._clips = clips;
    if (fig._io) return;
    fig._io = new IntersectionObserver(es => {
      if (!es.some(e => e.isIntersecting)) return;
      fig._io.disconnect(); fig.dataset.shown = '1';
      const t0 = performance.now();
      const step = now => {
        const k = Math.min(1, (now - t0) / 1400);
        fig._clips.forEach(c => c.rect.setAttribute('width', c.x0 + (c.w - c.x0) * (1 - (1 - k) ** 3)));
        if (k < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    }, {threshold: 0.5});
    fig._io.observe(fig);
  }

  // the series named by the paragraph being read stay strong; the others recede
  function focus(fig) {
    const keys = (fig.dataset.focus || '').split(',').filter(Boolean);
    fig.classList.toggle('ch-has-focus', keys.length > 0);
    fig.querySelectorAll('.ch-svg [data-key]').forEach(n => n.classList.toggle('ch-on', keys.includes(n.dataset.key)));
  }

  function watchFocus(fig, id) {
    const ps = [...document.querySelectorAll(`[data-focus^="${id}:"]`)];
    if (!ps.length || !('IntersectionObserver' in window)) return;
    const live = new Set();
    const io = new IntersectionObserver(es => {
      for (const e of es) e.isIntersecting ? live.add(e.target) : live.delete(e.target);
      const p = ps.filter(q => live.has(q)).pop();
      fig.dataset.focus = p ? p.dataset.focus.slice(id.length + 1) : '';
      focus(fig);
    }, {rootMargin: '-35% 0px -35% 0px'});
    ps.forEach(q => io.observe(q));
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
        const li = document.createElement('li'), shape = l.shape === 'dot' ? 'o' : l.shape;
        if (shape === 'd' || shape === 'box' || shape === 'o') {
          const i = li.appendChild(document.createElement('i'));
          i.className = shape; i.style.background = col(l.c); if (shape === 'box') i.style.opacity = l.o ?? 0.3;
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
      // '../…' is written from the page; a bare name is next to the spec it came from
      const a = Object.assign(document.createElement('a'), {href: d.startsWith('../') ? d : new URL(d, new URL(dataUrl, location.href)).href, textContent: 'data · ' + d.split('/').pop()});
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
      .then(all => { if (all[id]) { mount(fig, all[id], url); watchFocus(fig, id); } })
      .catch(() => {});  // the static figure stays
  });
})();
