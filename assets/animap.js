/* Animated segment maps for the articles, drawn with d3 (loaded from cdnjs with its integrity hash). A
   <figure class="anim-fig" data-animap="path/spec.json"> keeps its static image (img.anim-static) as the fallback; this
   script draws the segments coloured by their value in each time step, with a play button, a time slider, a summary
   line and a curve below with a cursor. It plays once when the figure comes half into view, unless the reader prefers
   reduced motion; the slider and the arrow keys work either way.

   Spec: {bins:[label], base: basemap JSON path (from the page) {districts, water},
          features:[{id, l:[[lon,lat],...], v:[number|null per bin]}],
          colour:{domain:[...], range:[...]}, empty: colour for null,
          tip:{mult, dp, unit, sign, empty}: the value in the segment's tooltip,
          notes:[text per bin], series:{values:[...], domain:[lo,hi], ref, label}, ticks:[bin index],
          events:[{at: bin label, label}], step: ms per bin, aria: description of the map} */
(() => {
  const INK = '#111111', GREY = '#666666', HELD = '#34507c';
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;

  const fmt = (v, t = {}) => {
    if (v == null) return t.empty || 'no data';
    const x = v * (t.mult ?? 1), s = Math.abs(x).toFixed(t.dp ?? 0);
    return (x < 0 ? '−' : t.sign && x > 0 ? '+' : '') + s + (t.unit || '');
  };

  async function draw(fig) {
    const S = await (await fetch(new URL(fig.dataset.animap, location.href))).json();
    const B = await (await fetch(new URL(S.base, location.href))).json();
    const nb = S.bins.length;
    const colour = d3.scaleLinear().domain(S.colour.domain).range(S.colour.range).clamp(true);
    fig.querySelector('.anim-static')?.remove();

    const bar = d3.select(fig).insert('div', 'figcaption').attr('class', 'anim-bar');
    const play = bar.append('button').attr('type', 'button').attr('class', 'anim-play');
    const clock = bar.append('span').attr('class', 'anim-clock');
    const slider = bar.append('input').attr('type', 'range').attr('min', 0).attr('max', nb - 1).attr('step', 1)
      .attr('class', 'anim-range').attr('aria-label', 'Time');
    const note = bar.append('span').attr('class', 'anim-note');

    const W = 720, H = 520;
    const svg = d3.select(fig).insert('svg', 'figcaption').attr('viewBox', `0 0 ${W} ${H}`).attr('class', 'anim-map')
      .attr('role', 'img').attr('aria-label', S.aria || 'Animated map');
    const geo = f => ({type: 'LineString', coordinates: f.l});
    const proj = d3.geoMercator().fitExtent([[10, 10], [W - 10, H - 10]],
                                            {type: 'GeometryCollection', geometries: S.features.map(geo)});
    const path = d3.geoPath(proj);
    svg.append('g').selectAll('path').data(B.districts || []).join('path')
      .attr('d', r => path({type: 'Polygon', coordinates: [r]})).attr('fill', '#f3f2ee').attr('stroke', '#fff')
      .attr('stroke-width', 0.8);
    svg.append('g').selectAll('path').data(B.water || []).join('path')
      .attr('d', l => path({type: 'LineString', coordinates: l})).attr('fill', 'none').attr('stroke', '#a9c4dc')
      .attr('stroke-width', 3);
    const segs = svg.append('g').selectAll('path').data(S.features).join('path').attr('d', f => path(geo(f)))
      .attr('fill', 'none').attr('stroke-width', 2.4).attr('stroke-linecap', 'round');
    segs.append('title');

    const cw = W, ch = 90, m = {l: 34, r: 14, t: 10, b: 20};
    const spark = d3.select(fig).insert('svg', 'figcaption').attr('viewBox', `0 0 ${cw} ${ch}`).attr('class', 'anim-spark')
      .attr('aria-hidden', 'true');
    const x = d3.scaleLinear().domain([0, nb - 1]).range([m.l, cw - m.r]);
    const y = d3.scaleLinear().domain(S.series.domain).range([ch - m.b, m.t]);
    if (S.series.ref != null) {
      spark.append('line').attr('x1', m.l).attr('x2', cw - m.r).attr('y1', y(S.series.ref)).attr('y2', y(S.series.ref))
        .attr('stroke', '#ddd');
      spark.append('text').attr('x', 2).attr('y', y(S.series.ref) + 3).text(S.series.refLabel ?? S.series.ref);
    }
    for (const e of S.events || []) {
      const i = S.bins.indexOf(e.at);
      if (i >= 0) spark.append('line').attr('x1', x(i)).attr('x2', x(i)).attr('y1', m.t).attr('y2', ch - m.b)
        .attr('stroke', GREY).attr('stroke-dasharray', '1.5 2.5');
    }
    spark.append('path').attr('d', d3.line().x((_, i) => x(i)).y(v => y(v))(S.series.values)).attr('fill', 'none')
      .attr('stroke', HELD).attr('stroke-width', 2);
    spark.selectAll('text.t').data(S.ticks || []).join('text').attr('class', 't').attr('x', i => x(i))
      .attr('y', ch - 5).attr('text-anchor', 'middle').text(i => S.bins[i]);
    const cursor = spark.append('circle').attr('r', 4.5).attr('fill', INK);

    let k = 0, timer = null;
    function show(i) {
      k = i;
      segs.attr('stroke', f => f.v[i] == null ? (S.empty || '#e2e2de') : colour(f.v[i]))
        .select('title').text(f => `${f.id}: ${fmt(f.v[i], S.tip)}`);
      clock.text(S.bins[i]);
      note.text(S.notes ? S.notes[i] : '');
      slider.property('value', i).attr('aria-valuetext', `${S.bins[i]}${S.notes ? ', ' + S.notes[i] : ''}`);
      cursor.attr('cx', x(i)).attr('cy', y(S.series.values[i]));
    }
    function stop() { if (timer) { timer.stop(); timer = null; } play.text('▶').attr('aria-label', 'Play'); }
    function start() {
      if (k >= nb - 1) show(0);
      play.text('❚❚').attr('aria-label', 'Pause');
      timer = d3.interval(() => { if (k >= nb - 1) return stop(); show(k + 1); }, S.step || 450);
    }
    play.on('click', () => timer ? stop() : start());
    slider.on('input', e => { stop(); show(+e.target.value); });
    show(0);
    stop();
    if (!still) {
      const io = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { io.disconnect(); start(); } },
                                          {threshold: 0.5});
      io.observe(fig);
    }
  }

  const go = () => document.querySelectorAll('figure[data-animap]').forEach(f => draw(f).catch(() => {}));
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
})();
