"""Concert effect: chart specs, static figures and the article, every number filled in from the results.

Reads docs/research/concert-effect-results.json, -panel.csv and -songs.csv; writes assets/concerts/ (charts.json,
01-event.svg, 02-loo.svg, the published CSVs) and texts/concert-effect.html from tools/concerts/template.html.

    uv run --with matplotlib python tools/concerts/article.py
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs" / "research"
A = ROOT / "assets" / "concerts"
HELD, INK, GREY, LIGHT = "#34507c", "#111111", "#666666", "#b5b5b0"
NB = " "
plt.rcParams.update({"font.family": "Helvetica", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": GREY, "xtick.color": GREY, "ytick.color": GREY, "svg.fonttype": "none"})


def n(v: float, dp: int = 0) -> str:
    s = f"{abs(v):,.{dp}f}".replace(",", NB)
    return ("−" if v < 0 and round(abs(v), dp) else "") + s


def pp(v: float, dp: int = 3) -> str:
    """A share of chart streams as percentage points."""
    return n(100 * v, dp)


def raw_path(res: dict) -> dict:
    """Descriptive: the visited countries' average share by week from their first show, without any model."""
    import pandas as pd
    p = pd.read_csv(R / "concert-effect-panel.csv")
    t = p[p.country.isin(res["treated"]) & (p.g > 0)].copy()
    t["e"] = t.week - t.g
    t = t[(t.e >= -12) & (t.e <= 12)]
    raw = t.groupby("e").y1_share.mean()
    w0 = t[t.e == 0]
    pre = t[(t.e >= -4) & (t.e <= -1)].groupby("country").y1_share.mean()
    jump = (t[t.e == 0].set_index("country").y1_share - pre).sort_values()
    return {"raw": {int(k): float(v) for k, v in raw.items()}, "cohorts": int(t.g.nunique()), "jump": jump.to_dict(),
            "w0_total_mean": float(w0.total_streams.mean())}


def figures(res: dict) -> None:
    A.mkdir(parents=True, exist_ok=True)
    for name in ("panel", "songs", "shows", "results"):
        src = R / f"concert-effect-{name}.{'json' if name == 'results' else 'csv'}"
        shutil.copy(src, A / src.name.replace("concert-effect-", ""))
    ev = res["y1_share"]["event"]
    base = res["pre_mean"]["y1_share"]
    pts = [{"x": r["e"], "lo": 100 * r["lo"], "hi": 100 * r["hi"], "mid": 100 * r["att"],
            "c": "held" if r["e"] >= 0 else "ink",
            "tip": f"week {r['e']:+d}: {pp(r['att'])} points (band {pp(r['lo'])} to {pp(r['hi'])})"} for r in ev]
    ymin, ymax = min(p["lo"] for p in pts), max(p["hi"] for p in pts)
    charts = {"event": {
        "alt": "Event study: the effect of a first concert on Harry Styles's share of a country's Spotify Top-200 streams, "
               "by week from 12 before to 12 after, with 95 % uniform bands; the concert week stands out.",
        "panels": [{"h": 280, "x": {"kind": "linear", "domain": [-12.5, 12.5], "ticks": list(range(-12, 13, 2)), "fmt": {"dp": 0},
                                    "label": "weeks from the first show in the country"},
                    "y": {"kind": "linear", "domain": [ymin * 1.1, ymax * 1.1], "fmt": {"dp": 2},
                          "label": "effect on his share of chart streams, percentage points"},
                    "marks": [{"type": "rule", "axis": "y", "v": 0, "c": "grey"},
                              {"type": "rule", "axis": "x", "v": -0.5, "c": "grey", "dash": "dash", "label": "first show", "dy": 12},
                              {"type": "vrange", "rows": pts, "w": 2}]}],
        "legend": [{"label": "before the show", "c": "ink"}, {"label": "from the show week", "c": "held"}],
        "table": {"cols": ["week", "effect, points", "95 % band"],
                  "rows": [[r["e"], round(100 * r["att"], 4), f"{100 * r['lo']:.4f} to {100 * r['hi']:.4f}"] for r in ev]},
        "data": ["results.json"]}}
    loo = sorted(res["leave_one_out"].items(), key=lambda kv: kv[1])
    charts["loo"] = {
        "alt": "The five-week summary effect re-estimated without each treated country in turn; every estimate is positive.",
        "panels": [{"h": 14 * len(loo), "x": {"kind": "linear", "domain": [0, max(v for _, v in loo) * 100 * 1.25], "fmt": {"dp": 3},
                                              "label": "five-week summary effect without the country, percentage points"},
                    "y": {"kind": "cat", "domain": [c for c, _ in loo]},
                    "marks": [{"type": "rule", "axis": "x", "v": 100 * res["y1_share"]["summary"]["att"], "c": "held", "dash": "dash",
                               "label": "all countries"},
                              {"type": "hbar", "rows": [{"y": c, "x1": 100 * v, "c": "light", "tip": f"without {c}: {pp(v)} points"} for c, v in loo]}]}],
        "table": {"cols": ["country left out", "summary effect, points"], "rows": [[c, round(100 * v, 4)] for c, v in loo]},
        "data": ["results.json"]}
    rp = raw_path(res)["raw"]
    charts["raw"] = {
        "alt": "Visited countries' average share of Spotify Top-200 streams for Harry Styles by week from the first show: "
               "falling before the show, a jump in the show week, then falling again.",
        "panels": [{"h": 220, "x": {"kind": "linear", "domain": [-12.5, 12.5], "ticks": list(range(-12, 13, 2)), "fmt": {"dp": 0},
                                    "label": "weeks from the first show in the country"},
                    "y": {"kind": "linear", "domain": [0, max(rp.values()) * 100 * 1.15], "fmt": {"dp": 2},
                          "label": "his share of Top-200 streams, %"},
                    "marks": [{"type": "rule", "axis": "x", "v": -0.5, "c": "grey", "dash": "dash", "label": "first show", "dy": 12},
                              {"type": "line", "pts": [[k, 100 * v] for k, v in sorted(rp.items())], "c": "held", "dots": True}]}],
        "table": {"cols": ["week", "average share, %"], "rows": [[k, round(100 * v, 4)] for k, v in sorted(rp.items())]},
        "data": ["panel.csv"]}
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False))
    f, ax = plt.subplots(figsize=(7.2, 2.6))
    ax.plot(sorted(rp), [100 * rp[k] for k in sorted(rp)], color=HELD, marker="o", ms=3)
    ax.axvline(-0.5, color=GREY, lw=0.8, ls="--"); ax.set_xlabel("weeks from the first show in the country")
    ax.set_ylabel("share of Top-200 streams, %")
    f.tight_layout(); f.savefig(A / "00-raw.svg"); plt.close(f)

    f, ax = plt.subplots(figsize=(7.2, 3))
    for r in ev:
        c = HELD if r["e"] >= 0 else INK
        ax.plot([r["e"], r["e"]], [100 * r["lo"], 100 * r["hi"]], color=c, lw=1.4)
        ax.scatter(r["e"], 100 * r["att"], color=c, s=14, zorder=3)
    ax.axhline(0, color=GREY, lw=0.8); ax.axvline(-0.5, color=GREY, lw=0.8, ls="--")
    ax.set_xlabel("weeks from the first show in the country"); ax.set_ylabel("effect, percentage points")
    f.tight_layout(); f.savefig(A / "01-event.svg"); plt.close(f)
    f, ax = plt.subplots(figsize=(6.4, 0.16 * len(loo) + 0.8))
    ax.barh(range(len(loo)), [100 * v for _, v in loo], color=LIGHT)
    ax.set_yticks(range(len(loo))); ax.set_yticklabels([c for c, _ in loo], fontsize=6.5)
    ax.axvline(100 * res["y1_share"]["summary"]["att"], color=HELD, ls="--", lw=1)
    ax.set_xlabel("five-week summary effect without the country, percentage points")
    f.tight_layout(); f.savefig(A / "02-loo.svg"); plt.close(f)


def values(res: dict) -> dict:
    y1, y2, y3 = res["y1_share"], res["y2_songs"], res["y3_share_top3"]
    base = res["pre_mean"]["y1_share"]
    ev = {r["e"]: r for r in y1["event"]}
    ev2 = {r["e"]: r for r in y2["event"]}
    pre = [r for r in y1["event"] if -12 <= r["e"] <= -2]
    bad_pre = [r for r in pre if not (r["lo"] <= 0 <= r["hi"])]
    loo = res["leave_one_out"]
    songs = list(csv.DictReader(open(R / "concert-effect-songs.csv", encoding="utf-8")))
    shows = list(csv.DictReader(open(R / "concert-effect-shows.csv", encoding="utf-8")))
    s = y1["summary"]
    v = {"n_countries": n(res["countries"]), "n_treated": n(len(res["treated"])), "n_never": n(len(res["never_treated"])),
         "n_dropped": n(len(res["dropped_unbalanced"])), "dropped": ", ".join(res["dropped_unbalanced"]),
         "n_shows": n(len(shows)), "n_songs": n(len(songs)),
         "top3": ", ".join(f"<i>{x['title']}</i>" for x in songs[:3]),
         "base_pp": pp(base), "w0": pp(ev[0]["att"]), "w0_lo": pp(ev[0]["lo"]), "w0_hi": pp(ev[0]["hi"]),
         "w0_rel": n(100 * ev[0]["att"] / base), "w1": pp(ev[1]["att"]), "w1_lo": pp(ev[1]["lo"]), "w1_hi": pp(ev[1]["hi"]),
         "w2": pp(ev[2]["att"]), "w3": pp(ev[3]["att"]), "wm1": pp(ev[-1]["att"]),
         "late": pp(sum(ev[k]["att"] for k in range(5, 13)) / 8),
         "sum": pp(s["att"]), "sum_lo": pp(s["lo"]), "sum_hi": pp(s["hi"]), "sum_rel": n(100 * s["att"] / base),
         "label": y1["label"], "why": y1["why"],
         "y2_w0": n(ev2[0]["att"], 2), "y2_w0_lo": n(ev2[0]["lo"], 2), "y2_w0_hi": n(ev2[0]["hi"], 2),
         "y2_base": n(res["pre_mean"]["y2_songs"], 2), "y2_label": y2["label"], "y3_label": y3["label"],
         "y3_sum": pp(y3["summary"]["att"]),
         "never": pp(res["never_treated_only"]["att"]), "never_lo": pp(res["never_treated_only"]["lo"]),
         "never_hi": pp(res["never_treated_only"]["hi"]),
         "placebo": pp(res["placebo_26w"]["att"]), "placebo_lo": pp(res["placebo_26w"]["lo"]), "placebo_hi": pp(res["placebo_26w"]["hi"]),
         "loo_min": pp(min(loo.values())), "loo_min_c": min(loo, key=loo.get), "loo_max": pp(max(loo.values())),
         "loo_max_c": max(loo, key=loo.get), "loo_us": pp(loo["United States"]), "loo_uk": pp(loo["United Kingdom"]),
         "n_bad_pre": n(len(bad_pre)), "bad_pre": ", ".join(f"week {r['e']}" for r in bad_pre) or "none",
         "bad_pre_band": "; ".join(f"{pp(r['lo'])} to {pp(r['hi'])}" for r in bad_pre),
         "csdid": res["csdid_version"]}
    rp = raw_path(res)
    v |= {"cohorts": n(rp["cohorts"]), "raw_m12": pp(rp["raw"][-12]), "raw_m2": pp(rp["raw"][-2]), "raw_0": pp(rp["raw"][0]),
          "raw_p4": pp(rp["raw"][4]), "raw_p12": pp(rp["raw"][12]),
          "w0_total": n(rp["w0_total_mean"] / 1e6), "extra": n(round(ev[0]["att"] * rp["w0_total_mean"], -3)),
          "jump_top": ", ".join(f"{c} (+{pp(v)})" for c, v in list(reversed(list(rp["jump"].items())))[:4]),
          "jump_neg": ", ".join(f"{c} ({pp(v)})" for c, v in rp["jump"].items() if v < 0),
          "jump_zero": ", ".join(c for c, v in rp["jump"].items() if v == 0), "n_zero": n(sum(v == 0 for v in rp["jump"].values())),
          "mde": n(100 * 1.96 * y1["summary"]["se"] / base), "extra_all": n(ev[0]["att"] * rp["w0_total_mean"] * len(res["treated"]) / 1e6, 1)}
    photo = next(p for p in json.loads((ROOT / "assets" / "photo" / "sources.json").read_text()) if p["slug"] == "concert-effect")
    v["photo"] = ('<section class="film film-page"><div class="shot" style="view-transition-name:ph-concert-effect;'
                  '--bg:url(../assets/photo/concert-effect.jpg);--bg-s:url(../assets/photo/concert-effect-1200.jpg)"></div>'
                  f'<p class="credit">Photo: <a href="{photo["page"]}">{photo["author"]}</a> · {photo["licence"]}, toned</p></section>')
    return v


def main() -> None:
    res = json.loads((R / "concert-effect-results.json").read_text())
    figures(res)
    t = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    v = values(res)
    missing = sorted(set(re.findall(r"\{\{(\w+)\}\}", t)) - set(v))
    if missing:
        sys.exit(f"keys not computed: {missing}")
    out = re.sub(r"\{\{(\w+)\}\}", lambda m: v[m.group(1)], t)
    (ROOT / "texts" / "concert-effect.html").write_text(out, encoding="utf-8")
    print("written texts/concert-effect.html")


if __name__ == "__main__":
    main()
