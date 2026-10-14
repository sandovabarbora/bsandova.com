/* The animated restart map of the blackout article. A <figure data-restart="path/restart.json"> keeps its static image
   (img.anim-static) as the fallback; this script, with d3 from cdnjs, draws Prague's tram segments coloured by their
   passes per ten minutes against ordinary Fridays, 11:00–17:00, with a play button, a time slider and the network's
   curve below. It plays once when the figure comes into view, unless the reader prefers reduced motion. */
(() => {
  const STOP = '#c0503f', MID = '#e7b3a6', OK = '#bdbdb6', INK = '#111111', GREY = '#666666', HELD = '#34507c';
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const colour = d3.scaleLinear().domain([0, 0.5, 0.9]).range([STOP, MID, OK]).clamp(true);

  async function draw(fig) {
    const url = new URL(fig.dataset.restart, location.href);
    const S = await (await fetch(url)).json();
    const B = await (await fetch(new URL(S.base, location.href))).json();
    const nb = S.bins.length;
    fig.querySelector('.anim-static')?.remove();

    const bar = d3.select(fig).insert('div', 'figcaption').attr('class', 'anim-bar');
    const play = bar.append('button').attr('type', 'button').attr('class', 'anim-play').attr('aria-label', 'Play');
    const clock = bar.append('span').attr('class', 'anim-clock');
    const slider = bar.append('input').attr('type', 'range').attr('min', 0).attr('max', nb - 1).attr('step', 1)
      .attr('class', 'anim-range').attr('aria-label', 'Time of day');
    const note = bar.append('span').attr('class', 'anim-note');

    const W = 720, H = 520;
    const svg = d3.select(fig).insert('svg', 'figcaption').attr('viewBox', `0 0 ${W} ${H}`).attr('class', 'anim-map')
      .attr('role', 'img').attr('aria-label', 'Prague tram segments coloured by the share of their usual trams, by time of day');
    const lines = S.features.map(f => ({type: 'LineString', coordinates: f.l}));
    const proj = d3.geoMercator().fitExtent([[10, 10], [W - 10, H - 10]], {type: 'GeometryCollection', geometries: lines});
    const path = d3.geoPath(proj);
    const ring = r => ({type: 'Polygon', coordinates: [r]});
    svg.append('g').selectAll('path').data(B.districts).join('path').attr('d', r => path(ring(r)))
      .attr('fill', '#f3f2ee').attr('stroke', '#fff').attr('stroke-width', 0.8);
    svg.append('g').selectAll('path').data(B.water).join('path')
      .attr('d', l => path({type: 'LineString', coordinates: l})).attr('fill', 'none').attr('stroke', '#a9c4dc').attr('stroke-width', 3);
    const segs = svg.append('g').selectAll('path').data(S.features).join('path')
      .attr('d', f => path({type: 'LineString', coordinates: f.l})).attr('fill', 'none').attr('stroke-width', 2.4)
      .attr('stroke-linecap', 'round');
    segs.append('title');

    // the network's curve, with a cursor at the shown time
    const cw = W, ch = 90, m = {l: 34, r: 10, t: 10, b: 20};
    const spark = d3.select(fig).insert('svg', 'figcaption').attr('viewBox', `0 0 ${cw} ${ch}`).attr('class', 'anim-spark')
      .attr('aria-hidden', 'true');
    const x = d3.scaleLinear().domain([0, nb - 1]).range([m.l, cw - m.r]);
    const y = d3.scaleLinear().domain([0, 1.2]).range([ch - m.b, m.t]);
    spark.append('line').attr('x1', m.l).attr('x2', cw - m.r).attr('y1', y(1)).attr('y2', y(1)).attr('stroke', '#ddd');
    for (const e of S.events) {
      const i = S.bins.indexOf(e.at);
      if (i >= 0) spark.append('line').attr('x1', x(i)).attr('x2', x(i)).attr('y1', m.t).attr('y2', ch - m.b)
        .attr('stroke', GREY).attr('stroke-dasharray', '1.5 2.5');
    }
    spark.append('path').attr('d', d3.line().x((_, i) => x(i)).y(v => y(v))(S.network)).attr('fill', 'none')
      .attr('stroke', HELD).attr('stroke-width', 2);
    spark.selectAll('text.t').data([0, 6, 12, 18, 24, 30]).join('text').attr('class', 't').attr('x', i => x(i))
      .attr('y', ch - 5).attr('text-anchor', 'middle').text(i => S.bins[i]);
    spark.append('text').attr('x', 2).attr('y', y(1) + 3).text('1.0');
    const cursor = spark.append('circle').attr('r', 4.5).attr('fill', INK);

    let k = 0, timer = null;
    function show(i) {
      k = i;
      segs.attr('stroke', f => f.r[i] == null ? '#e2e2de' : colour(f.r[i]))
        .select('title').text(f => `${f.id}: ${f.r[i] == null ? 'no trams on ordinary Fridays' : Math.round(100 * f.r[i]) + ' % of usual trams'}`);
      const stopped = S.features.filter(f => f.r[i] === 0).length;
      clock.text(S.bins[i]);
      note.text(`${stopped} of ${S.features.length} segments without a tram · network ${Math.round(100 * S.network[i])} % of usual`);
      slider.property('value', i).attr('aria-valuetext', `${S.bins[i]}, ${stopped} segments without a tram`);
      cursor.attr('cx', x(i)).attr('cy', y(S.network[i]));
    }
    function stop() { if (timer) { timer.stop(); timer = null; } play.text('▶').attr('aria-label', 'Play'); }
    function start() {
      if (k >= nb - 1) show(0);
      play.text('❚❚').attr('aria-label', 'Pause');
      timer = d3.interval(() => { if (k >= nb - 1) return stop(); show(k + 1); }, 450);
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

  const go = () => document.querySelectorAll('figure[data-restart]').forEach(f => draw(f).catch(() => {}));
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
})();
