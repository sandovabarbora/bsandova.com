/* Transfer roulette: pick a hub, a pair of tram lines, a time of day and a planned slack, and read how often the
   connection was made in 2025. Reads the cells written by tools/transfer/describe.py (assets/transfers/roulette.json).
   Markup: <figure class="rl" data-roulette="../assets/transfers/roulette.json"> with a static fallback inside. */
(() => {
  const BANDS = { peak: "weekday peak", daytime: "weekday daytime", weekend: "weekend daytime", evening: "evening" };
  const pct = (v) => `${Math.round(100 * v)} %`;
  const min = (s) => (s < 0 ? `${Math.round(s)} s` : s < 90 ? `${Math.round(s)} s` : `${(s / 60).toFixed(1)} min`);
  const el = (tag, attrs = {}, kids = []) => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) k === "text" ? (e.textContent = v) : e.setAttribute(k, v);
    for (const c of kids) e.append(c);
    return e;
  };
  const select = (label, opts) => {
    const s = el("select", { "aria-label": label });
    for (const [v, t] of opts) s.append(el("option", { value: v, text: t }));
    return s;
  };

  async function mount(fig) {
    let cells;
    try {
      const d = await (await fetch(fig.dataset.roulette)).json();
      cells = d.rows.map((r) => ({
        hub: r[0], a: r[1], a_to: r[2], b: r[3], b_to: r[4], band: d.bands[r[5]], connections: r[6], dates: r[7],
        m_s: r[8], own_slack_median_min: r[9], made_at_own_slacks: r[10], costly_miss: r[11],
        median_extra_wait_s: r[12], curve: r[13].map(([s, p, lo, hi]) => ({ s, p, lo, hi })),
      }));
    } catch (e) {
      console.warn("roulette: data not loaded", e);
      return;
    }
    const hubs = [...new Set(cells.map((c) => c.hub))].sort((a, b) => a.localeCompare(b, "cs"));
    const ui = el("div", { class: "rl-ui" });
    const hubSel = select("hub", hubs.map((h) => [h, h]));
    const pairSel = select("lines", []);
    const bandSel = select("time of day", Object.entries(BANDS));
    const slack = el("input", { type: "range", min: "1", max: "10", step: "1", value: "3", "aria-label": "planned slack, minutes" });
    const slackOut = el("output", { text: "3 min" });
    const big = el("p", { class: "rl-big" });
    const sub = el("p", { class: "rl-sub" });
    const note = el("p", { class: "rl-note", text: "Each answer is one cell of many; the best and worst cells look extreme partly by chance, so read the interval, not just the number." });
    ui.append(
      el("label", {}, [el("span", { text: "hub" }), hubSel]),
      el("label", {}, [el("span", { text: "from line → to line" }), pairSel]),
      el("label", {}, [el("span", { text: "time of day" }), bandSel]),
      el("label", {}, [el("span", { text: "planned slack" }), slack, slackOut]),
    );
    const out = el("div", { class: "rl-out", "aria-live": "polite" }, [big, sub, note]);
    const fallback = fig.querySelector(".rl-static");
    if (fallback) fallback.style.display = "none";
    fig.prepend(ui, out);

    const pairs = () => {
      const seen = new Map();
      for (const c of cells.filter((c) => c.hub === hubSel.value)) {
        const k = `${c.a}|${c.a_to}|${c.b}|${c.b_to}`;
        if (!seen.has(k)) seen.set(k, `${c.a} (to ${c.a_to}) → ${c.b} (to ${c.b_to})`);
      }
      return [...seen].sort((x, y) => x[1].localeCompare(y[1], "cs", { numeric: true }));
    };
    const fillPairs = () => {
      pairSel.replaceChildren(...pairs().map(([v, t]) => el("option", { value: v, text: t })));
    };
    const render = () => {
      const [a, ato, b, bto] = pairSel.value.split("|");
      const s = Number(slack.value);
      slackOut.textContent = `${s} min`;
      const c = cells.find((x) => x.hub === hubSel.value && x.a === a && x.a_to === ato && x.b === b && x.b_to === bto && x.band === bandSel.value);
      if (!c) {
        big.textContent = "too few connections";
        sub.textContent = "Fewer than 500 connections on 30 days for this pair at this time of day, or the two lines do not meet here then.";
        return;
      }
      const k = c.curve.find((x) => x.s === s);
      big.textContent = pct(k.p);
      sub.textContent = `of connections made with ${s} min planned (95 % interval ${pct(k.lo)} to ${pct(k.hi)}), with a ${Math.round(c.m_s)} s walk allowed. ` +
        `As timetabled here (median ${c.own_slack_median_min} min), ${pct(c.made_at_own_slacks)} were made, ${pct(c.costly_miss)} of connections cost over 5 min more wait, median extra wait ${min(c.median_extra_wait_s)}; ${c.connections.toLocaleString("en").replace(/,/g, "\u00a0")} connections on ${c.dates} days.`;
    };
    const tightPair = () => {  // open on a pair the timetable really plans a few minutes apart
      const c = cells.find((x) => x.hub === hubSel.value && x.band === bandSel.value &&
        x.own_slack_median_min >= 2 && x.own_slack_median_min <= 4);
      if (c) pairSel.value = `${c.a}|${c.a_to}|${c.b}|${c.b_to}`;
    };
    hubSel.addEventListener("change", () => { fillPairs(); tightPair(); render(); });
    for (const x of [pairSel, bandSel]) x.addEventListener("change", render);
    slack.addEventListener("input", render);
    hubSel.value = hubs.includes("Anděl") ? "Anděl" : hubs[0];
    fillPairs();
    tightPair();
    render();
  }

  const style = el("style", { text: `
.text .rl-ui{display:grid;grid-template-columns:repeat(auto-fit,minmax(13rem,1fr));gap:.6rem 1.2rem;margin:0 0 1rem}
.text .rl-ui label{display:flex;flex-direction:column;gap:.25rem;font:400 11px/1.4 var(--mono,monospace);color:#666;text-transform:none}
.text .rl-ui select,.text .rl-ui input{font:400 14px/1.3 var(--sans,sans-serif);color:#000;background:#fff;border:1px solid #000;border-radius:0;padding:.35rem .4rem}
.text .rl-ui input[type=range]{border:0;padding:0;accent-color:#c0503f}
.text .rl-ui output{font:400 12px var(--mono,monospace);color:#000}
.text .rl-out{border-top:1px solid #000;padding-top:.8rem}
.text p.rl-big{font:500 clamp(40px,6vw,72px)/1 var(--sans,sans-serif);letter-spacing:-.04em;margin:0 0 .4rem;color:#c0503f}
.text p.rl-sub{max-width:64ch;margin:0 0 .5rem}
.text p.rl-note{font:400 12px/1.5 var(--mono,monospace);color:#666;max-width:64ch;margin:0}` });
  document.head.append(style);
  document.querySelectorAll("figure[data-roulette]").forEach(mount);
})();
