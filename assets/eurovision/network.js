/* The animated vote network of the Eurovision article, drawn with d3 and the shared controls of assets/animap.js.
   A <figure data-network="path/network.json"> keeps its static image as the fallback; the pairs of countries that gave
   each other far more of their final points than an even split, five contests at a time, are drawn as arcs between
   them, thicker the stronger, year by year. */
(() => {
  const CORAL = '#c0503f', INK = '#111111';

  async function draw(fig) {
    const S = await (await fetch(new URL(fig.dataset.network, location.href))).json();
    fig.querySelector('.anim-static')?.remove();
    const W = 720, H = 560;
    const svg = d3.select(fig).insert('svg', 'figcaption').attr('viewBox', `0 0 ${W} ${H}`).attr('class', 'anim-map')
      .attr('role', 'img').attr('aria-label', 'Map of Europe with arcs between countries that vote for each other, by year');
    const poly = r => ({type: 'Polygon', coordinates: [r]});
    const proj = d3.geoMercator().fitExtent([[6, 6], [W - 6, H - 6]],
                                            {type: 'GeometryCollection', geometries: S.base.map(poly)});
    const path = d3.geoPath(proj);
    svg.append('g').selectAll('path').data(S.base).join('path').attr('d', r => path(poly(r)))
      .attr('fill', '#f3f2ee').attr('stroke', '#fff').attr('stroke-width', 0.8);
    const xy = c => proj([S.nodes[c].x, S.nodes[c].y]);
    const width = d3.scaleLinear().domain([S.ratio, 6]).range([1.5, 6]).clamp(true);
    const arc = ([a, b]) => {
      const [x1, y1] = xy(a), [x2, y2] = xy(b), dx = x2 - x1, dy = y2 - y1;
      const mx = (x1 + x2) / 2 - dy * 0.18, my = (y1 + y2) / 2 + dx * 0.18;
      return `M${x1},${y1} Q${mx},${my} ${x2},${y2}`;
    };
    const gl = svg.append('g'), gn = svg.append('g');
    const codes = Object.keys(S.nodes);
    const dots = gn.selectAll('g').data(codes).join('g').attr('transform', c => `translate(${xy(c)})`);
    dots.append('circle').attr('r', 2.5).attr('fill', '#9a9a95');
    const labels = dots.append('text').attr('class', 'anim-label').attr('dy', -6).attr('text-anchor', 'middle')
      .text(c => S.nodes[c].name);
    const dur = window.bsAnim.still ? 0 : 350;

    window.bsAnim.controls(fig, S.years.map(String), S.notes, 900, i => {
      const on = new Set(S.active[i]);
      dots.select('circle').attr('fill', c => on.has(c) ? INK : '#c4c4bf').attr('r', c => on.has(c) ? 3.5 : 2.5);
      labels.attr('display', c => on.has(c) ? null : 'none');
      gl.selectAll('path').data(S.frames[i], l => l[0] + l[1]).join(
        enter => enter.append('path').attr('fill', 'none').attr('stroke', CORAL).attr('stroke-linecap', 'round')
          .attr('d', arc).attr('stroke-width', l => width(l[2])).attr('opacity', 0)
          .call(e => e.append('title'))
          .call(e => e.transition().duration(dur).attr('opacity', 0.75)),
        update => update.call(u => u.transition().duration(dur).attr('stroke-width', l => width(l[2]))),
        exit => exit.call(x => x.transition().duration(dur).attr('opacity', 0).remove()))
        .select('title').text(l => `${S.nodes[l[0]].name} and ${S.nodes[l[1]].name}: ${l[2].toFixed(1)}× an even share`);
    }, 'Year');
  }

  const go = () => document.querySelectorAll('figure[data-network]').forEach(f => draw(f).catch(() => {}));
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
})();
