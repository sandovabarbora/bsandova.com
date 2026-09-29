/* Interactive choropleth maps for the articles, after the precinct map of Part 2. A
   <figure class="mp-fig" data-map="path/map.json"> keeps its static SVG (img.mp-static) as the fallback; this script
   draws the map from the JSON: a row of views to pick, the areas shaded by the picked value, a tooltip with every
   value of the area under the pointer (or the arrow keys), a legend, a table of all areas and a link to the data.

   Spec: {held, features:[{id, name, sub, r:[[[lon,lat],...]], v:{key:number|null}}],
          views:[{key, label, fmt:{dp, unit, pct, sign}, scale:'seq'|'div', domain:[lo,hi]}],
          overlay:{lines:[[[lon,lat],...]], points:[[lon,lat]], labels:[{at:[lon,lat], s}]},
          note, data:[paths]} */
(() => {
  const NS = 'http://www.w3.org/2000/svg';
  const nb = ' ';
  const fmt = (v, f = {}) => {
    if (v == null || Number.isNaN(v)) return 'no data';
    const x = f.pct ? v * 100 : v, dp = f.dp ?? 0;
    let s = Math.abs(x).toFixed(dp);
    const [i, d] = s.split('.');
    s = (i.length > 3 && !f.nogroup ? i.replace(/\B(?=(\d{3})+(?!\d))/g, nb) : i) + (d ? '.' + d : '');
    return (x < 0 ? '−' : f.sign && x > 0 ? '+' : '') + s + (f.pct ? nb + '%' : f.unit || '');
  };
  const hex = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
  const mix = (a, b, t) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
  const rgb = c => `rgb(${c.join(',')})`;
  const rampOf = (held, scale, neg) => {
    const H = hex(held), W = [246, 244, 238], K = [17, 17, 17];
    if (scale === 'div') {
      const N = hex(neg || '#9a4a2b'), M = [226, 226, 222];
      return t => rgb(t < 0.5 ? mix(mix(N, K, 0.25), M, t * 2) : mix(M, mix(H, K, 0.25), (t - 0.5) * 2));
    }
    const stops = [W, mix(H, W, 0.55), H, mix(H, K, 0.45)];
    return t => { const u = Math.max(0, Math.min(1, t)) * 3, i = Math.min(2, Math.floor(u)); return rgb(mix(stops[i], stops[i + 1], u - i)); };
  };
  const el = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); if (parent) parent.appendChild(e); return e; };

  function mount(fig, S, url) {
    const img = fig.querySelector('img');
    const held = S.held || '#34507c';
    // equirectangular at Prague's latitude, fitted to 900 units wide
    const lat0 = 50.08, k = 1 / Math.cos(lat0 * Math.PI / 180), W = 900;
    let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
    S.features.forEach(f => f.r.forEach(ring => ring.forEach(([x, y]) => { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); })));
    const s = W / (x1 - x0), H = Math.round((y1 - y0) * k * s);
    const X = x => +((x - x0) * s).toFixed(1), Y = y => +((y1 - y) * k * s).toFixed(1);

    const bar = document.createElement('div'); bar.className = 'mp-bar'; bar.setAttribute('role', 'group'); bar.setAttribute('aria-label', 'What the map shows');
    const box = document.createElement('div'); box.className = 'mp';
    const tip = document.createElement('div'); tip.className = 'mp-tip'; tip.hidden = true; tip.setAttribute('role', 'status');
    const leg = document.createElement('div'); leg.className = 'mp-leg';
    const table = document.createElement('div'); table.className = 'mp-table'; table.hidden = true;
    const svg = el('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': img?.alt || '', tabindex: 0});
    const gA = el('g', {}, svg), gO = el('g', {'pointer-events': 'none'}, svg);
    const paths = S.features.map((f, i) => {
      const d = f.r.map(ring => 'M' + ring.map(([x, y]) => X(x) + ',' + Y(y)).join('L') + 'Z').join('');
      const p = el('path', {d, class: 'a', 'data-i': i}, gA);
      return p;
    });
    const O = S.overlay || {};
    for (const l of O.lines || []) el('path', {d: 'M' + l.map(([x, y]) => X(x) + ',' + Y(y)).join('L'), fill: 'none', stroke: '#111', 'stroke-width': 1.6}, gO);
    for (const [x, y] of O.points || []) el('circle', {cx: X(x), cy: Y(y), r: 2.6, fill: '#fff', stroke: '#111', 'stroke-width': 1}, gO);
    for (const lb of O.labels || []) { const t = el('text', {x: X(lb.at[0]), y: Y(lb.at[1]), class: 'mp-lab', 'text-anchor': 'middle'}, gO); t.textContent = lb.s; }
    box.append(svg, tip);
    fig.insertBefore(bar, img); fig.insertBefore(box, img); fig.insertBefore(leg, img); fig.insertBefore(table, img);

    let cur = 0, sel = -1;
    const show = v => {
      cur = v;
      const V = S.views[v], vals = S.features.map(f => f.v[V.key]).filter(x => x != null).sort((a, b) => a - b);
      let [lo, hi] = V.domain || [vals[Math.floor(0.02 * (vals.length - 1))], vals[Math.ceil(0.98 * (vals.length - 1))]];
      if (V.scale === 'div' && !V.domain) { const m = Math.max(Math.abs(lo), Math.abs(hi)); lo = -m; hi = m; }
      const ramp = rampOf(held, V.scale, S.neg);
      paths.forEach((p, i) => { const x = S.features[i].v[V.key]; p.setAttribute('fill', x == null ? '#e6e6e3' : ramp(hi > lo ? (x - lo) / (hi - lo) : 0.5)); p.classList.toggle('nodata', x == null); });
      leg.textContent = '';
      const a = document.createElement('span'); a.textContent = fmt(lo, V.fmt);
      const i = document.createElement('i'); i.style.background = `linear-gradient(90deg,${[0, 0.25, 0.5, 0.75, 1].map(ramp).join(',')})`;
      const b = document.createElement('span'); b.textContent = fmt(hi, V.fmt) + ' · ' + V.label + (V.note ? ' · ' + V.note : '');
      leg.append(a, i, b);
      if (vals.length < S.features.length) { const n = document.createElement('span'); n.className = 'mp-nd'; n.textContent = 'no data'; leg.append(n); }
      bar.querySelectorAll('button[data-v]').forEach(bt => bt.setAttribute('aria-pressed', String(+bt.dataset.v === v)));
      buildTable();
      if (sel >= 0) detail(sel);
    };
    const detail = (i, ev) => {
      sel = i;
      const f = S.features[i];
      tip.textContent = '';
      const h = document.createElement('b'); h.textContent = f.name + (f.sub ? ' · ' + f.sub : ''); tip.append(h);
      const t = document.createElement('table');
      S.views.forEach((V, j) => { const r = t.insertRow(); if (j === cur) r.className = 'on'; r.insertCell().textContent = V.label; r.insertCell().textContent = fmt(f.v[V.key], V.fmt); });
      tip.append(t); tip.hidden = false;
      const R = box.getBoundingClientRect();
      let tx, ty;
      if (ev) { tx = ev.clientX - R.left; ty = ev.clientY - R.top; }
      else { const bb = paths[i].getBBox(), sc = R.width / W; tx = (bb.x + bb.width / 2) * sc; ty = (bb.y + bb.height / 2) * sc; }
      tip.style.left = Math.max(0, Math.min(tx + 14, R.width - tip.offsetWidth - 4)) + 'px';
      tip.style.top = Math.max(0, ty - tip.offsetHeight - 12) + 'px';
      paths.forEach((p, j) => p.classList.toggle('sel', j === i));
    };
    const buildTable = () => {
      const V = S.views[cur];
      const rows = S.features.map((f, i) => [i, f.v[V.key]]).sort((a, b) => (b[1] ?? -1e18) - (a[1] ?? -1e18));
      const t = document.createElement('table'), hd = t.createTHead().insertRow(), bd = t.createTBody();
      ['', ...S.views.map(v => v.label)].forEach(c => { hd.appendChild(document.createElement('th')).textContent = c; });
      for (const [i] of rows) { const f = S.features[i], r = bd.insertRow(); r.insertCell().textContent = f.name + (f.sub ? ' · ' + f.sub : ''); S.views.forEach(v => { r.insertCell().textContent = fmt(f.v[v.key], v.fmt); }); }
      table.replaceChildren(t);
    };
    S.views.forEach((V, j) => { const bt = document.createElement('button'); bt.type = 'button'; bt.dataset.v = j; bt.textContent = V.label; bt.onclick = () => show(j); bar.append(bt); });
    // controls under the map: map or table, and the data behind it
    const ctl = document.createElement('p'); ctl.className = 'ch-ctl';
    const b1 = Object.assign(document.createElement('button'), {type: 'button', textContent: 'map'});
    const b2 = Object.assign(document.createElement('button'), {type: 'button', textContent: 'table'});
    const view = tbl => { box.hidden = tbl; leg.hidden = tbl; table.hidden = !tbl; b1.setAttribute('aria-pressed', String(!tbl)); b2.setAttribute('aria-pressed', String(tbl)); };
    b1.onclick = () => view(false); b2.onclick = () => view(true); view(false);
    ctl.append(b1, b2);
    for (const d of S.data || [url]) ctl.append(Object.assign(document.createElement('a'), {href: d, textContent: 'data · ' + d.split('/').pop()}));
    const hint = document.createElement('span'); hint.className = 'ch-hint'; hint.textContent = 'hover, tap or use the arrow keys for an area';
    ctl.append(hint);
    fig.insertBefore(ctl, img);

    const hit = e => { const p = e.target.closest('path.a'); if (p) detail(+p.dataset.i, e); };
    box.addEventListener('pointermove', hit); box.addEventListener('pointerdown', hit);
    box.addEventListener('pointerleave', () => { tip.hidden = true; sel = -1; paths.forEach(p => p.classList.remove('sel')); });
    // arrow keys walk the areas west to east
    const order = S.features.map((f, i) => [i, f.r[0].reduce((a, [x]) => a + x, 0) / f.r[0].length]).sort((a, b) => a[1] - b[1]).map(a => a[0]);
    svg.addEventListener('keydown', e => {
      const at = order.indexOf(sel);
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { detail(order[(at + 1) % order.length]); e.preventDefault(); }
      else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { detail(order[(at - 1 + order.length) % order.length]); e.preventDefault(); }
      else if (e.key === 'Escape') { tip.hidden = true; sel = -1; paths.forEach(p => p.classList.remove('sel')); }
    });
    img.hidden = true;
    fig.classList.add('mp-live');
    show(S.start || 0);
  }

  document.querySelectorAll('figure[data-map]').forEach(fig => {
    const url = fig.dataset.map;
    fetch(url).then(r => r.ok ? r.json() : Promise.reject(r.status)).then(S => mount(fig, S, url)).catch(() => {});
  });
})();
