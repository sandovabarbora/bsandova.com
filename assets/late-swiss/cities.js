/* The animated comparison of part 4, drawn with d3 and the shared controls of assets/animap.js. A
   <figure data-cities="path/cities.json"> keeps its static image as the fallback; for each city in turn the concentration
   curve and the curve chance alone would give move into place, the gap between them shaded, and the map beside them
   shows where that city's top tenth of segments lies. */
(() => {
  const CORAL = '#c0503f', INK = '#111111', GREY = '#666666', FAINT = '#d6d6d1';
  const pct = v => (100 * v).toFixed(1) + ' %';

  async function draw(fig) {
    const url = new URL(fig.dataset.cities, location.href);
    const S = await (await fetch(url)).json();
    const bases = await Promise.all(S.cities.map(c => fetch(new URL(c.base, location.href)).then(r => r.json()).catch(() => null)));
    fig.querySelector('.anim-static')?.remove();
    const W = 720, H = 380, m = {l: 44, r: 14, t: 14, b: 40}, cw = 340;
    const svg = d3.select(fig).insert('svg', 'figcaption').attr('viewBox', `0 0 ${W} ${H}`).attr('class', 'anim-map')
      .attr('role', 'img')
      .attr('aria-label', 'Concentration curves and the curves chance alone would give for Prague, Zurich, Basel and Bern, ' +
                          'with a map of where each city\'s top tenth of segments lies');

    // the curve panel
    const x = d3.scaleLinear().domain([0, 1]).range([m.l, cw]), y = d3.scaleLinear().domain([0, 1.05]).range([H - m.b, m.t]);
    const g = svg.append('g');
    g.append('g').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickValues([0, 0.1, 0.25, 0.5, 0.75, 1])
      .tickFormat(d3.format('.0%'))).attr('class', 'anim-axis');
    g.append('g').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).tickValues([0, 0.25, 0.5, 0.75, 1])
      .tickFormat(d3.format('.0%'))).attr('class', 'anim-axis');
    g.append('text').attr('class', 'anim-label').attr('x', (m.l + cw) / 2).attr('y', H - 6).attr('text-anchor', 'middle')
      .text('share of segments, largest producers first');
    g.append('text').attr('class', 'anim-label').attr('transform', `translate(11,${(H - m.b + m.t) / 2}) rotate(-90)`)
      .attr('text-anchor', 'middle').text('share of the delay made');
    g.append('line').attr('x1', x(0)).attr('y1', y(0)).attr('x2', x(1)).attr('y2', y(1)).attr('stroke', FAINT)
      .attr('stroke-dasharray', '3 3');
    g.append('line').attr('x1', x(S.top)).attr('x2', x(S.top)).attr('y1', y(0)).attr('y2', y(1.05)).attr('stroke', GREY)
      .attr('stroke-dasharray', '1.5 2.5');
    const line = d3.line().x(p => x(p[0])).y(p => y(p[1]));
    g.append('g').selectAll('path').data(S.cities).join('path').attr('d', c => line(c.curve)).attr('fill', 'none')
      .attr('stroke', FAINT).attr('stroke-width', 1.2);
    const gap = g.append('path').attr('fill', CORAL).attr('opacity', 0.14);
    const chance = g.append('path').attr('fill', 'none').attr('stroke', GREY).attr('stroke-width', 1.5)
      .attr('stroke-dasharray', '4 3');
    const main = g.append('path').attr('fill', 'none').attr('stroke', INK).attr('stroke-width', 2.4);
    const dotS = g.append('circle').attr('r', 4.5).attr('fill', INK).attr('cx', x(S.top));
    const dot0 = g.append('circle').attr('r', 4).attr('fill', '#fff').attr('stroke', GREY).attr('stroke-width', 1.5)
      .attr('cx', x(S.top));
    const labS = g.append('text').attr('class', 'anim-label').attr('x', x(S.top) + 8);
    const lab0 = g.append('text').attr('class', 'anim-label').attr('x', x(S.top) + 8).attr('fill', GREY);
    // shaded only where the city's curve runs above its chance curve
    const both = c => d3.area().x(p => x(p[0])).y0((_, k) => y(c.chance[k][1]))
      .y1((p, k) => y(Math.max(p[1], c.chance[k][1])))(c.curve);

    // the map panel: one group per city, faded in and out
    const mx0 = cw + 26, mw = W - mx0 - 4, mh = H - 8;
    const maps = S.cities.map((c, i) => {
      const gm = svg.append('g').attr('opacity', 0);
      const geo = l => ({type: 'LineString', coordinates: l});
      const proj = d3.geoMercator().fitExtent([[mx0, 4], [mx0 + mw, mh]],
                                              {type: 'GeometryCollection', geometries: [...c.top, ...c.rest].map(geo)});
      const path = d3.geoPath(proj);
      const B = bases[i];
      if (B) {
        gm.append('clipPath').attr('id', `cities-clip-${i}`).append('rect').attr('x', mx0).attr('y', 0).attr('width', mw)
          .attr('height', H);
        const gb = gm.append('g').attr('clip-path', `url(#cities-clip-${i})`);
        gb.append('path').attr('d', B.districts.map(r => path({type: 'Polygon', coordinates: [r]})).join(''))
          .attr('fill', '#f3f2ee').attr('stroke', '#fff').attr('stroke-width', 0.7);
        gb.append('path').attr('d', (B.lakes || []).map(r => path({type: 'Polygon', coordinates: [r]})).join(''))
          .attr('fill', '#dfe6ec');
        gb.append('path').attr('d', (B.water || []).map(l => path(geo(l))).join('')).attr('fill', 'none')
          .attr('stroke', '#c5d2de').attr('stroke-width', 3);
      }
      gm.append('path').attr('d', c.rest.map(l => path(geo(l))).join('')).attr('fill', 'none').attr('stroke', '#b9b9b3')
        .attr('stroke-width', 1.1);
      gm.append('path').attr('d', c.top.map(l => path(geo(l))).join('')).attr('fill', 'none').attr('stroke', CORAL)
        .attr('stroke-width', 2.6).attr('stroke-linecap', 'round');
      return gm;
    });
    svg.append('text').attr('class', 'anim-label').attr('x', W - 4).attr('y', H - 6).attr('text-anchor', 'end')
      .text('coral: the top tenth of segments');

    const dur = window.bsAnim.still ? 0 : 900;
    window.bsAnim.controls(fig, S.cities.map(c => c.name), S.notes, 3200, i => {
      const c = S.cities[i], t = d3.transition().duration(dur).ease(d3.easeCubicInOut);
      main.transition(t).attr('d', line(c.curve));
      chance.transition(t).attr('d', line(c.chance));
      gap.transition(t).attr('d', both(c));
      dotS.transition(t).attr('cy', y(c.S));
      dot0.transition(t).attr('cy', y(c.S0));
      labS.transition(t).attr('y', y(c.S) - 6).text(`S ${pct(c.S)}`);
      lab0.transition(t).attr('y', y(c.S0) + 14).text(`chance ${pct(c.S0)}`);
      maps.forEach((gm, k) => gm.transition(t).attr('opacity', k === i ? 1 : 0));
    }, 'City');
  }

  const go = () => document.querySelectorAll('figure[data-cities]').forEach(f => draw(f).catch(() => {}));
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
})();
