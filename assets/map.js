/* Interactive choropleth maps for the articles, after the precinct map of Part 2. A
   <figure class="mp-fig" data-map="path/map.json"> keeps its static SVG (img.mp-static) as the fallback; this script
   draws the map from the JSON: a row of views to pick, the areas shaded by the picked value, a tooltip with every
   value of the area under the pointer (or the arrow keys), a legend, a table of all areas and a link to the data.

   Spec: {held, features:[{id, name, sub, r:[[[lon,lat],...]] for an area or l:[[[lon,lat],...]] for a line (a route),
                           v:{key:number|null}}],
          views:[{key, label, fmt:{dp, unit, pct, sign}, scale:'seq'|'div', domain:[lo,hi], note,
                  cats:[{v, label}] for a yes/no or categorical view, mark:{id, label} to draw one feature in ink}],
          overlay:{lines:[[[lon,lat],...]], points:[[lon,lat]], labels:[{at:[lon,lat], s}]},
          note, hint, fit:'features' (frame the features, not the basemap's outline), lat0 (projection latitude, default Prague's), base (a basemap JSON {outline, districts, water}
          drawn under the features, path as for data), data:[paths]} */
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

  function mount(fig, S, url, B) {
    const img = fig.querySelector('img');
    const held = S.held || '#34507c';
    // equirectangular at Prague's latitude, fitted to 900 units wide
    const lat0 = S.lat0 ?? 50.08, k = 1 / Math.cos(lat0 * Math.PI / 180), W = 900;
    let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
    [...S.features.map(f => f.r || f.l), ...(B && S.fit !== 'features' ? [B.outline] : [])].forEach(rs => rs.forEach(ring => ring.forEach(([x, y]) => { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); })));
    if (S.fit === 'features') { const px = (x1 - x0) * 0.03, py = (y1 - y0) * 0.03; x0 -= px; x1 += px; y0 -= py; y1 += py; }  // the basemap is clipped to the features' box
    const s = W / (x1 - x0), H = Math.round((y1 - y0) * k * s);
    const X = x => +((x - x0) * s).toFixed(1), Y = y => +((y1 - y) * k * s).toFixed(1);

    const bar = document.createElement('div'); bar.className = 'mp-bar'; bar.setAttribute('role', 'group'); bar.setAttribute('aria-label', 'What the map shows');
    const box = document.createElement('div'); box.className = 'mp';
    const tip = document.createElement('div'); tip.className = 'mp-tip'; tip.hidden = true; tip.setAttribute('role', 'status');
    const leg = document.createElement('div'); leg.className = 'mp-leg';
    const table = document.createElement('div'); table.className = 'mp-table'; table.hidden = true;
    const svg = el('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': img?.alt || '', tabindex: 0});
    const defs = el('defs', {}, svg), pat = el('pattern', {id: 'mp-nd-' + Math.random().toString(36).slice(2), width: 6, height: 6, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)'}, defs);
    el('rect', {width: 6, height: 6, fill: '#f4f4f1'}, pat); el('line', {x1: 0, y1: 0, x2: 0, y2: 6, stroke: '#c4c4bf', 'stroke-width': 1.6}, pat);
    const ND = `url(#${pat.id})`;
    if (B) {  // the basemap: districts, the city outline and the river, under everything and never hit-tested
      const gB = el('g', {'pointer-events': 'none', class: 'mp-base'}, svg);
      const line = (pts, closed) => 'M' + pts.map(([x, y]) => X(x) + ',' + Y(y)).join('L') + (closed ? 'Z' : '');
      el('path', {d: B.districts.map(r => line(r, true)).join(''), fill: '#f2f2ef', stroke: '#fff', 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke'}, gB);
      el('path', {d: B.outline.map(r => line(r, true)).join(''), fill: 'none', stroke: '#c9c9c4', 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke'}, gB);
      el('path', {d: (B.water || []).map(l => line(l, false)).join(''), fill: 'none', stroke: '#c5d2de', 'stroke-width': 4, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'vector-effect': 'non-scaling-stroke'}, gB);
    }
    const gA = el('g', {}, svg), gO = el('g', {'pointer-events': 'none'}, svg);
    // a line's colour goes in its style, since the stylesheet's white outline for areas would win over an attribute
    const paint = (p, c) => { if (p.classList.contains('ln')) p.style.stroke = c; else p.setAttribute('fill', c); };
    const paths = S.features.map((f, i) => {
      // an area is filled; a line (f.l) is stroked in the value's colour and drawn above the areas
      const d = f.l ? f.l.map(line => 'M' + line.map(([x, y]) => X(x) + ',' + Y(y)).join('L')).join('')
                    : f.r.map(ring => 'M' + ring.map(([x, y]) => X(x) + ',' + Y(y)).join('L') + 'Z').join('');
      const p = el('path', {d, class: f.l ? 'a ln' : 'a', 'data-i': i}, gA);
      // set inline so a cached stylesheet without the line rule cannot fill a route as an area
      if (f.l) Object.assign(p.style, {fill: 'none', strokeWidth: '2.4', strokeLinecap: 'round', strokeLinejoin: 'round'});
      return p;
    });
    const O = S.overlay || {};
    for (const l of O.lines || []) el('path', {d: 'M' + l.map(([x, y]) => X(x) + ',' + Y(y)).join('L'), fill: 'none', stroke: '#111', 'stroke-width': 1.6, 'vector-effect': 'non-scaling-stroke'}, gO);
    for (const [x, y] of O.points || []) el('circle', {cx: X(x), cy: Y(y), r: 2.6, fill: '#fff', stroke: '#111', 'stroke-width': 1}, gO);
    for (const lb of O.labels || []) { const t = el('text', {x: X(lb.at[0]), y: Y(lb.at[1]), class: 'mp-lab', 'text-anchor': 'middle'}, gO); t.textContent = lb.s; }
    box.append(svg, tip);
    fig.insertBefore(bar, img); fig.insertBefore(box, img); fig.insertBefore(leg, img); fig.insertBefore(table, img);

    const val = (V, x) => V.cats ? (V.cats.find(c => c.v === x)?.label ?? 'no data') : fmt(x, V.fmt);
    let cur = 0, sel = -1;
    const show = v => {
      cur = v;
      const V = S.views[v], vals = S.features.map(f => f.v[V.key]).filter(x => x != null).sort((a, b) => a - b);
      if (V.cats) {
        // categories: the last one takes the held colour, the others steps of grey
        const cc = V.cats.map((c, j) => j === V.cats.length - 1 ? held : ['#e2e2de', '#b9b9b4', '#8a8a86'][j] || '#8a8a86');
        paths.forEach((p, i) => { const x = S.features[i].v[V.key], j = V.cats.findIndex(c => c.v === x); paint(p, j < 0 ? ND : cc[j]); p.classList.toggle('nodata', j < 0); });
        leg.textContent = '';
        V.cats.forEach((c, j) => { const sw = document.createElement('span'); sw.className = 'mp-sw'; sw.style.setProperty('--c', cc[j]); sw.textContent = c.label; leg.append(sw); });
        const t = document.createElement('span'); t.textContent = '· ' + V.label + (V.note ? ' · ' + V.note : ''); leg.append(t);
        if (vals.length < S.features.length) { const n = document.createElement('span'); n.className = 'mp-nd'; n.textContent = 'no data'; leg.append(n); }
        if (S.note) { const n = document.createElement('span'); n.className = 'mp-note'; n.textContent = S.note; leg.append(n); }
        if (B?.credit) { const n = document.createElement('span'); n.className = 'mp-note'; n.textContent = B.credit; leg.append(n); }
        bar.querySelectorAll('button[data-v]').forEach(bt => bt.setAttribute('aria-pressed', String(+bt.dataset.v === v)));
        buildTable(); if (sel >= 0) detail(sel);
        return;
      }
      let [lo, hi] = V.domain || [vals[Math.floor(0.02 * (vals.length - 1))], vals[Math.ceil(0.98 * (vals.length - 1))]];
      if (V.scale === 'div' && !V.domain) { const m = Math.max(Math.abs(lo), Math.abs(hi)); lo = -m; hi = m; }
      const ramp = rampOf(held, V.scale, S.neg);
      paths.forEach((p, i) => { const x = S.features[i].v[V.key]; paint(p, x == null ? ND : ramp(hi > lo ? (x - lo) / (hi - lo) : 0.5)); p.classList.toggle('nodata', x == null); });
      const mk = V.mark && S.features.findIndex(f => f.id === V.mark.id);
      if (mk >= 0) { paint(paths[mk], '#222'); paths[mk].classList.remove('nodata'); }
      leg.textContent = '';
      const a = document.createElement('span'); a.textContent = (vals[0] < lo ? '≤ ' : '') + fmt(lo, V.fmt);
      const i = document.createElement('i'); i.style.background = `linear-gradient(90deg,${[0, 0.25, 0.5, 0.75, 1].map(ramp).join(',')})`;
      const b = document.createElement('span'); b.textContent = fmt(hi, V.fmt) + (vals[vals.length - 1] > hi ? '+' : '') + ' · ' + V.label + (V.note ? ' · ' + V.note : '');
      leg.append(a, i, b);
      if (mk >= 0) { const sw = document.createElement('span'); sw.className = 'mp-sw'; sw.style.setProperty('--c', '#222'); sw.textContent = V.mark.label; leg.append(sw); }
      if (S.note) { const n = document.createElement('span'); n.className = 'mp-note'; n.textContent = S.note; leg.append(n); }
      if (B?.credit) { const n = document.createElement('span'); n.className = 'mp-note'; n.textContent = B.credit; leg.append(n); }
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
      S.views.forEach((V, j) => { const r = t.insertRow(); if (j === cur) r.className = 'on'; r.insertCell().textContent = V.label; r.insertCell().textContent = val(V, f.v[V.key]); });
      tip.append(t); tip.hidden = false;
      const R = box.getBoundingClientRect();
      let tx, ty;
      if (ev) { tx = ev.clientX - R.left; ty = ev.clientY - R.top; }
      else { const bb = paths[i].getBBox(), sc = R.width / W; tx = (bb.x + bb.width / 2) * sc; ty = (bb.y + bb.height / 2) * sc; }
      tip.style.left = Math.max(0, Math.min(tx + 14, R.width - tip.offsetWidth - 4)) + 'px';
      tip.style.top = Math.max(0, ty - tip.offsetHeight - 12) + 'px';
      paths.forEach((p, j) => p.classList.toggle('sel', j === i));
      if (paths[i].classList.contains('ln') && gA.lastChild !== paths[i]) gA.appendChild(paths[i]);  // the picked line on top
    };
    const buildTable = () => {
      const V = S.views[cur];
      const rows = S.features.map((f, i) => [i, f.v[V.key]]).sort((a, b) => (b[1] ?? -1e18) - (a[1] ?? -1e18));
      const t = document.createElement('table'), hd = t.createTHead().insertRow(), bd = t.createTBody();
      ['', ...S.views.map(v => v.label)].forEach(c => { hd.appendChild(document.createElement('th')).textContent = c; });
      for (const [i] of rows) { const f = S.features[i], r = bd.insertRow(); r.insertCell().textContent = f.name + (f.sub ? ' · ' + f.sub : ''); S.views.forEach(v => { r.insertCell().textContent = val(v, f.v[v.key]); }); }
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
    // '../…' is written from the page; a bare name is next to the spec it came from
    for (const d of S.data || [url]) ctl.append(Object.assign(document.createElement('a'), {href: d.startsWith('../') ? d : new URL(d, new URL(url, location.href)).href, textContent: 'data · ' + d.split('/').pop()}));
    const hint = document.createElement('span'); hint.className = 'ch-hint'; hint.textContent = S.hint || 'hover, tap or use the arrow keys for an area';
    ctl.append(hint);
    fig.insertBefore(ctl, img);

    const hit = e => { const p = e.target.closest('path.a'); if (p) detail(+p.dataset.i, e); };
    box.addEventListener('pointermove', hit); box.addEventListener('pointerdown', hit);
    box.addEventListener('pointerleave', () => { tip.hidden = true; sel = -1; paths.forEach(p => p.classList.remove('sel')); });
    // arrow keys walk the areas west to east
    const order = S.features.map((f, i) => [i, (f.r || f.l)[0].reduce((a, [x]) => a + x, 0) / (f.r || f.l)[0].length]).sort((a, b) => a[1] - b[1]).map(a => a[0]);
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
    const rel = (d, from) => d.startsWith('../') ? d : new URL(d, new URL(from, location.href)).href;
    fetch(url).then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(S => S.base ? fetch(rel(S.base, url)).then(r => r.ok ? r.json() : null).catch(() => null).then(B => mount(fig, S, url, B))
                        : mount(fig, S, url))
      .catch(e => console.warn('map.js:', url, e));
  });
})();
