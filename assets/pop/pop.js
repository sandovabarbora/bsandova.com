/* Pop, measured: the two charts that assets/charts.js does not draw. No dependencies.

   <figure data-pop="ones" data-src="…/widgets.json">  every global number one as a dot, stacked by days in the
       global Top 200, with a search: type a song and it is marked and counted. The article's own songs wear the artist's colour.
   <figure data-pop="tickets" data-src="…/widgets.json">  per country, the average ticket as squares, one square a
       day of income; a part square is the rest of a day.

   Each figure keeps its static <img> as the fallback and a table in the page; this script only adds to it. */
(() => {
  const NS = 'http://www.w3.org/2000/svg';
  const INK = '#111111', LIGHT = '#c9c9c4', GREY = '#666666';
  let HELD = '#34507c';   // the artist's colour from widgets.json (assets/palette.json), the same in every chart
  const el = (tag, attrs = {}, parent) => {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) if (v != null) e.setAttribute(k, v);
    if (parent) parent.appendChild(e);
    return e;
  };
  const h = (tag, attrs = {}, parent) => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) k === 'text' ? (e.textContent = v) : e.setAttribute(k, v);
    if (parent) parent.appendChild(e);
    return e;
  };
  const num = v => String(v).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  const fold = s => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');

  function ones(fig, data) {
    const songs = data.ones, n = songs.length;
    const img = fig.querySelector('img');
    const box = h('div', {class: 'pop-ones'});
    const form = h('label', {class: 'pop-find'}, box);
    const what = data.peak > 1 ? `song that peaked at ${data.peak}` : 'number one';
    const whats = data.peak > 1 ? `songs that peaked at ${data.peak}` : 'number ones';
    h('span', {text: `Find a ${what}`}, form);
    const input = h('input', {type: 'search', placeholder: data.peak > 1 ? 'type a title' : 'e.g. Flowers, Blinding Lights', autocomplete: 'off', list: 'pop-ones-list'}, form);
    const list = h('datalist', {id: 'pop-ones-list'}, box);
    for (const s of songs) h('option', {value: s.t}, list);
    const out = h('p', {class: 'pop-out', 'aria-live': 'polite'}, box);
    const wrap = h('div', {class: 'pop-wrap'}, box);
    const tip = h('div', {class: 'ch-tip', hidden: ''}, wrap);
    img.after(box);
    img.hidden = true;
    fig.classList.add('ch-live');

    let marked = null;
    const say = s => {
      const longer = songs.filter(o => o.d > s.d).length;
      out.textContent = `${s.t}: ${num(s.d)} days${s.c ? ', still in the chart' : ''}. ` +
        `${longer} of ${n} ${whats} since 2017 have more days.`;
    };
    function draw() {
      wrap.querySelectorAll('svg').forEach(s => s.remove());
      const W = wrap.clientWidth || 640, r = W < 520 ? 2.6 : 3.4, step = 2 * r + 1.2;
      const max = Math.max(...songs.map(s => s.d)), cols = Math.floor((W - 20) / step);
      const bin = Math.ceil(max / cols / 10) * 10, X = d => 10 + Math.floor(d / bin) * step + r;
      const stack = {};
      for (const s of songs) { const b = Math.floor(s.d / bin); stack[b] = (stack[b] || 0) + 1; s._b = b; s._k = stack[b]; }
      const H = Math.max(...Object.values(stack)) * step + 34;
      const svg = el('svg', {class: 'ch-svg', viewBox: `0 0 ${W} ${H}`, role: 'img',
        'aria-label': `${n} ${whats} since 2017 in the global chart, by days in the global Top 200; the median is ${data.median} days.`}, wrap);
      const base = H - 24;
      el('line', {x1: 10, x2: W - 10, y1: base + 2, y2: base + 2, stroke: GREY, 'stroke-width': 0.6}, svg);
      for (let t = 0; t <= max; t += 500) {
        el('line', {x1: X(t) - r, x2: X(t) - r, y1: base + 2, y2: base + 6, stroke: GREY, 'stroke-width': 0.6}, svg);
        el('text', {x: X(t) - r, y: base + 18, 'text-anchor': t ? 'middle' : 'start'}, svg).textContent = num(t);
      }
      el('text', {x: W - 10, y: base - 4, 'text-anchor': 'end', class: 'ch-note'}, svg).textContent = 'days in the global Top 200 →';
      if (data.median) {
        const mx = X(data.median) - r;
        el('line', {x1: mx, x2: mx, y1: 6, y2: base, stroke: GREY, 'stroke-dasharray': '3 3', 'stroke-width': 0.8}, svg);
        el('text', {x: mx + 4, y: 14, class: 'ch-note'}, svg).textContent = `median ${num(data.median)}`;
      }
      for (const s of songs) {
        const cx = X(s.d), cy = base - (s._k - 0.5) * step;
        const isM = marked === s, fill = s.o || isM ? (isM && !s.o ? INK : HELD) : LIGHT;
        const c = el('circle', {cx, cy, r: isM || s.o ? r + 1.6 : r, fill: s.c ? '#fff' : fill, stroke: fill, 'stroke-width': s.c ? 1.4 : 0}, svg);
        c.addEventListener('pointerenter', () => {
          tip.textContent = `${s.t}\n${num(s.d)} days${s.c ? ' (still charting)' : ''}`;
          tip.hidden = false;
          tip.style.transform = `translate(${Math.min(cx + 10, W - 200)}px, ${Math.max(cy - 50, 0)}px)`;
        });
        c.addEventListener('pointerleave', () => { tip.hidden = true; });
        c.addEventListener('click', () => { marked = s; say(s); draw(); });
        if (isM || s.f) el('text', {x: Math.min(cx + r + 4, W - 120), y: cy - r - 3, class: 'ch-note', fill: isM && !s.o ? INK : HELD,
          'font-weight': s.f ? 600 : null}, svg)
          .textContent = s.t.replace(/^.*? - /, '');
      }
    }
    input.addEventListener('input', () => {
      const q = fold(input.value.trim());
      if (q.length < 2) return;
      const hit = songs.find(s => fold(s.t).includes(q));
      if (!hit) { out.textContent = `Not among the ${whats} since 2017.`; return; }
      marked = hit; say(hit); draw();
    });
    draw();
    new ResizeObserver(() => draw()).observe(wrap);
  }

  function tickets(fig, data) {
    const t = data.tickets;
    if (!t || !t.length) return;
    const img = fig.querySelector('img');
    const box = h('div', {class: 'pop-tickets', role: 'img',
      'aria-label': 'Average ticket price by country, drawn as days of GDP per capita; the table below gives every value.'});
    for (const r of t) {
      const row = h('div', {class: 'pop-t' + (/^Czech/.test(r.n) ? ' cz' : '')}, box);
      h('span', {class: 'pop-n', text: r.n}, row);
      const sq = h('span', {class: 'pop-sq'}, row);
      const full = Math.floor(r.d), part = r.d - full;
      for (let i = 0; i < full; i++) h('i', {}, sq);
      if (part > 0.02) h('i', {style: `width:${(part * 12).toFixed(1)}px`}, sq);
      h('span', {class: 'pop-v', text: `${r.d.toFixed(1)} d · $${r.p}`}, row);
    }
    img.after(box);
    img.hidden = true;
    fig.classList.add('ch-live');
  }

  // <figure data-pop="map" data-src="…/map.svg">: the map is inlined so each country can show its values on hover
  async function map(fig) {
    const img = fig.querySelector('img');
    const svg = new DOMParser().parseFromString(await (await fetch(fig.dataset.src)).text(), 'image/svg+xml').documentElement;
    svg.classList.add('pop-map');
    const wrap = h('div', {class: 'pop-wrap'});
    const tip = h('div', {class: 'ch-tip', hidden: ''}, wrap);
    wrap.appendChild(svg);
    img.after(wrap);
    img.hidden = true;
    fig.classList.add('ch-live');
    svg.querySelectorAll('title').forEach(t => { t.parentNode.dataset.tip = t.textContent; t.remove(); });
    svg.addEventListener('pointermove', e => {
      const s = e.target.closest('[data-tip]');
      if (!s) { tip.hidden = true; return; }
      const r = wrap.getBoundingClientRect();
      tip.textContent = s.dataset.tip.replace(/ · /g, '\n');
      tip.hidden = false;
      tip.style.transform = `translate(${Math.min(e.clientX - r.left + 12, r.width - 240)}px, ${e.clientY - r.top + 12}px)`;
    });
    svg.addEventListener('pointerleave', () => { tip.hidden = true; });
  }

  const run = () => document.querySelectorAll('figure[data-pop]').forEach(async fig => {
    try {
      if (fig.dataset.pop === 'map') return await map(fig);
      const data = await (await fetch(fig.dataset.src)).json();
      if (data.c) { HELD = data.c; fig.style.setProperty('--pop-c', data.c); }
      ({ones, tickets})[fig.dataset.pop]?.(fig, data);
    } catch (e) { /* the static figure stays */ }
  });
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', run) : run();
})();
