"""The meme study: figures and the article, every number from the result files.

Reads docs/research/memes-{results,describe,power}.json (describe.py writes the second, after the results), writes
assets/actor-memes/ (charts.json, the static fallbacks and copies of the JSON files) and texts/actor-memes.html from
tools/memes/template.html. Nothing of the frozen run is changed or rerun.

    uv run --no-project --with pandas==3.0.6 --with numpy==2.5.3 --with matplotlib==3.11.2 \
        python -I tools/memes/article.py
"""
from __future__ import annotations

import datetime as dt
import html as H
import json
import math
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "site"))
from article_kit import (
    GREY,
    HELD,
    LIGHT,
    NB,
    n,
    render,
    results_reader,
    use_article_style,
)

plt = use_article_style()
SLUG = "actor-memes"
R, A = ROOT / "docs" / "research", ROOT / "assets" / SLUG
CORAL, TEAL = "#c0503f", "#2a7f86"
KJ, ST = "Kevin James", "Stonestreet (Cam)"
NAME = {KJ: "Kevin James", ST: "Eric Stonestreet"}
COLOUR = {KJ: HELD, ST: CORAL}
MONTH = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
CHECKS = [  # variant, label; a variant that one event does not run shows as not run
    ("window_-3_14", "window of 18 days, −3 to +14"),
    ("window_-3_60", "window of 64 days, −3 to +60"),
    ("mean_index", "mean instead of median baseline"),
    ("same_season", "placebo dates within 45 days of the calendar date"),
    ("exclusion_90", "placebo dates at least 90 days away"),
    ("pre_event_only", "placebo dates before the meme only"),
    ("koq_controls", "the two King of Queens castmates as baseline"),
    ("window_-3_60_without_Matt_LeBlanc", "64 days, pool without Matt LeBlanc"),
    ("drop_Sofía_Vergara", "without Sofía Vergara in the baseline"),
    ("day0_2023-10-06", "day 0 on 6 October, for the half-life only"),
    ("external_index", "the reference pool as baseline"),
    ("external_index_window_-3_60", "the reference pool, 64 days"),
    ("external_index_window_-3_60_without_Matt_LeBlanc", "the reference pool, 64 days, without Matt LeBlanc"),
    ("tiktok_prewave", "the first TikTok, 13 June 2023, as day 0"),
]


def pct(v: float, dp: int = 0, sign: bool = True) -> str:
    return n(v, dp, sign=sign) + NB + "%"


def up(ar: float) -> float:
    return 100 * math.expm1(ar)


def pv(p: float) -> str:
    return f"{p:.3f}" if p < 0.1 else f"{p:.2f}"


def day(s: str, year: bool = False) -> str:
    d = dt.date.fromisoformat(s)
    return f"{d.day} {MONTH[d.month - 1]}" + (f" {d.year}" if year else "")


def thousands(v: float, step: int = 1000) -> str:
    return n(round(v / step) * step)


def num_refs(page: str, values: dict) -> str:
    """[[key]] markers become citations numbered by first appearance; every entry of refs.html must be cited."""
    entries = dict(re.findall(r'<li data-key="([\w-]+)">(.*?)</li>', render((HERE / "refs.html").read_text(encoding="utf-8"), values), re.DOTALL))
    order = list(dict.fromkeys(re.findall(r"\[\[([\w-]+)\]\]", page)))
    assert set(order) <= set(entries), set(order) - set(entries)
    assert set(entries) <= set(order), f"uncited: {set(entries) - set(order)}"
    num = {k: i for i, k in enumerate(order, 1)}
    page = re.sub(r"\[\[([\w-]+)\]\]", lambda m: f'<sup class="cite"><a href="#r{num[m.group(1)]}">{num[m.group(1)]}</a></sup>', page)
    return page.replace("{{refs}}", "\n".join(f'<li id="r{num[k]}">{entries[k]}</li>' for k in order))


# ---------------------------------------------------------------- fig. 1, the daily gap with the placebo band

def tip(e: str, r: dict) -> str:
    return (f"day {r['day']:+d} · {day(r['date'])} · {n(r['views'])} views, {n(round(r['expected']))} expected"
            .replace("+0", "0"))


def daily_chart(desc: dict, out: list[int]) -> dict:
    panels = []
    for e, dom, ticks in ((KJ, [-50, 500], [0, 100, 200, 300, 400, 500]), (ST, [-50, 100], [-50, 0, 50, 100])):
        days = desc["events"][e]["days"]
        panels.append({
            "title": NAME[e], "h": 220 if e == KJ else 160,
            "x": {"kind": "linear", "domain": [-3.5, 30.5], "ticks": [-3, 0, 5, 10, 15, 20, 25, 30], "fmt": {"dp": 0, "sign": True},
                  "label": f"days from the first post on X ({day(desc['events'][e]['event_date'])})",
                  "tipLabels": {str(r["day"]): tip(e, r) for r in days}},
            "y": {"kind": "linear", "domain": dom, "ticks": ticks, "fmt": {"dp": 0, "sign": True, "unit": " %"},
                  "label": "views above expected, %"},
            "marks": [{"type": "area", "name": "nine placebo dates in ten", "c": "grey", "o": 0.16,
                       "fmt": {"dp": 0, "sign": True, "unit": " %"},
                       "pts": [[r["day"], round(up(r["band"][0]), 1), round(up(r["band"][1]), 1)] for r in days]},
                      {"type": "rule", "axis": "y", "v": 0, "c": "grey"},
                      {"type": "rule", "axis": "x", "v": 0, "c": "light", "dash": "dot"},
                      {"type": "line", "name": NAME[e], "c": COLOUR[e], "w": 1.8, "fmt": {"dp": 0, "sign": True, "unit": " %"},
                       "pts": [[r["day"], round(up(r["ar"]), 1)] for r in days]}]})
    rows = [[NAME[e], r["day"], r["date"], r["views"], round(r["expected"]), round(up(r["ar"]), 1),
             f"{up(r['band'][0]):+.0f} to {up(r['band'][1]):+.0f}"] for e in (KJ, ST) for r in desc["events"][e]["days"]]
    return {"alt": "Views above the model's expectation, in per cent, day by day from three days before the first meme "
                   f"post to thirty days after, with the band that holds nine placebo dates in ten. Kevin James's article "
                   f"is above the band on every day from day {out[0]} to day {max(d for d in out if d < 20)} and again on "
                   f"day {out[-1]}, near +450 % on days 5 and 14. Eric Stonestreet's never rises above it.",
            "layout": "rows", "panels": panels,
            "legend": [{"label": "Kevin James", "c": HELD}, {"label": "Eric Stonestreet", "c": CORAL},
                       {"label": "nine placebo dates in ten (5th to 95th percentile)", "c": "grey", "shape": "box"}],
            "table": {"cols": ["actor", "day", "date", "views", "expected", "above expected, %", "placebo band, %"],
                      "rows": rows},
            "data": ["describe.json"]}


def static_daily(desc: dict, path: Path) -> None:
    f, axes = plt.subplots(2, 1, figsize=(7.2, 4.6), gridspec_kw={"height_ratios": [1.35, 1]})
    for ax, e, top in ((axes[0], KJ, 500), (axes[1], ST, 100)):
        days = desc["events"][e]["days"]
        x = [r["day"] for r in days]
        ax.fill_between(x, [up(r["band"][0]) for r in days], [up(r["band"][1]) for r in days], color=GREY, alpha=0.16, lw=0)
        ax.axhline(0, color=GREY, lw=0.8)
        ax.axvline(0, color=LIGHT, lw=0.8, ls=":")
        ax.plot(x, [up(r["ar"]) for r in days], color=COLOUR[e], lw=1.6)
        ax.set_ylim(-50, top)
        ax.set_title(NAME[e], fontsize=9, loc="left")
        ax.set_ylabel("above expected, %")
    axes[1].set_xlabel("days from the first post on X")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


# ---------------------------------------------------------------- fig. 2, the average gap so far (the test)

def running(r: dict, key: str, i: int | None = None) -> float:
    v = r[key] if i is None else r[key][i]
    return up(v / (r["day"] + 4))


def average_chart(desc: dict, res: dict) -> dict:
    marks = []
    for e in (KJ, ST):
        days = desc["events"][e]["days"]
        marks.append({"type": "area", "name": f"{NAME[e]}, nine placebo dates in ten", "c": COLOUR[e], "o": 0.12,
                      "fmt": {"dp": 0, "sign": True, "unit": " %"},
                      "pts": [[r["day"], round(running(r, "car_band", 0), 1), round(running(r, "car_band", 1), 1)] for r in days]})
    marks += [{"type": "rule", "axis": "y", "v": 0, "c": "grey"},
              {"type": "rule", "axis": "x", "v": 0, "c": "light", "dash": "dot"}]
    for e in (KJ, ST):
        days = desc["events"][e]["days"]
        marks.append({"type": "line", "name": NAME[e], "c": COLOUR[e], "w": 2, "end": NAME[e],
                      "fmt": {"dp": 0, "sign": True, "unit": " %"},
                      "pts": [[r["day"], round(running(r, "car"), 1)] for r in days]})
    rows = [[NAME[e], r["day"], round(running(r, "car"), 1),
             f"{running(r, 'car_band', 0):+.0f} to {running(r, 'car_band', 1):+.0f}"]
            for e in (KJ, ST) for r in desc["events"][e]["days"]]
    return {"alt": f"The average gap to expected views since day −3, day by day, with the band that holds nine placebo "
                   f"dates in ten. Kevin James's average leaves its band on day 6 and ends at "
                   f"{pct(res[KJ]['car_pct_uplift'])}, above the band's top. Eric Stonestreet's stays inside its band and "
                   f"ends at {pct(res[ST]['car_pct_uplift'])}.",
            "panels": [{"h": 260, "padRight": 120,
                        "x": {"kind": "linear", "domain": [-3.5, 30.5], "ticks": [-3, 0, 5, 10, 15, 20, 25, 30],
                              "fmt": {"dp": 0, "sign": True}, "label": "days from the first post on X"},
                        "y": {"kind": "linear", "domain": [-40, 150], "ticks": [-25, 0, 25, 50, 75, 100, 125, 150],
                              "fmt": {"dp": 0, "sign": True, "unit": " %"}, "label": "average above expected since day −3, %"},
                        "marks": marks}],
            "legend": [{"label": "Kevin James", "c": HELD}, {"label": "Eric Stonestreet", "c": CORAL},
                       {"label": "nine placebo dates in ten, per actor", "c": "grey", "shape": "box"}],
            "table": {"cols": ["actor", "day", "average above expected since day −3, %", "placebo band, %"], "rows": rows},
            "data": ["describe.json"]}


def static_average(desc: dict, path: Path) -> None:
    f, ax = plt.subplots(figsize=(7.2, 3.3))
    for e in (KJ, ST):
        days = desc["events"][e]["days"]
        x = [r["day"] for r in days]
        ax.fill_between(x, [running(r, "car_band", 0) for r in days], [running(r, "car_band", 1) for r in days],
                        color=COLOUR[e], alpha=0.12, lw=0)
        ax.plot(x, [running(r, "car") for r in days], color=COLOUR[e], lw=1.8, label=NAME[e])
    ax.axhline(0, color=GREY, lw=0.8)
    ax.axvline(0, color=LIGHT, lw=0.8, ls=":")
    ax.set_ylim(-40, 150)
    ax.set_xlabel("days from the first post on X")
    ax.set_ylabel("average above expected, %")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


# ---------------------------------------------------------------- fig. 3, the screening series before the memes

def decimal(d: str) -> float:
    t = dt.date.fromisoformat(d)
    start = dt.date(t.year, 1, 1)
    return round(t.year + (t - start).days / (dt.date(t.year + 1, 1, 1) - start).days, 4)


SCREEN_PANELS = [
    ("Eric Stonestreet and his baseline", ST, [("Eric_Stonestreet", "Eric Stonestreet", CORAL),
                                               ("median of the Modern Family cast", "Modern Family cast, median", GREY)]),
    ("Kevin James and his baseline", KJ, [("Kevin_James", "Kevin James", HELD),
                                          ("median of the reference pool", "reference pool, median", GREY),
                                          ("Victor_Williams", "Victor Williams", TEAL)]),
]


def segments(pts: list) -> list[list]:
    out, cur = [], []
    for d, v in pts:
        if v is None:
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append([decimal(d), round(math.expm1(v))])
    return out + ([cur] if cur else [])


def screen_chart(desc: dict) -> dict:
    sc = desc["screening"]
    ticks = [2021, 2022, 2023]
    tl = {str(t): str(t) for t in ticks}
    panels = []
    for title, e, series in SCREEN_PANELS:
        w = sc["estimation_windows"][e]
        marks = [{"type": "span", "v0": decimal(w[0]), "v1": decimal(w[1]), "c": "held", "o": 0.08},
                 {"type": "span", "v0": decimal(sc["blank"][0]), "v1": decimal(sc["blank"][1]), "c": "grey", "o": 0.18}]
        for key, label, c in series:
            for seg in segments(sc["series"][key]):
                marks.append({"type": "line", "name": label, "c": c, "w": 1, "pts": seg})
        panels.append({"title": title, "h": 220,
                       "x": {"kind": "linear", "domain": [2021, 2023.75], "ticks": ticks, "tickLabels": tl,
                             "fmt": {"dp": 2, "nogroup": True}, "label": f"day, 1 January 2021 to {day(sc['cutoff'], True)}"},
                       "y": {"kind": "log", "domain": [200, 70000], "ticks": [300, 1000, 3000, 10000, 30000],
                             "tickLabels": {str(t): n(t) for t in (300, 1000, 3000, 10000, 30000)},
                             "fmt": {"dp": 0}, "label": "daily views (log scale)"},
                       "marks": marks})
    return {"alt": "Daily views before the memes, January 2021 to 17 September 2023, on a log scale, with the estimation "
                   "windows shaded and the TikTok block blank. Eric Stonestreet's page has single-day spikes of five to "
                   "eighteen times its usual level, two of them near or inside his estimation window. Kevin James's page "
                   "has none in 2023. The medians of the baselines are smooth.",
            "layout": "rows", "panels": panels,
            "legend": [{"label": NAME[ST], "c": CORAL}, {"label": NAME[KJ], "c": HELD}, {"label": "Victor Williams", "c": TEAL},
                       {"label": "median of a baseline", "c": "grey"}],
            "table": {"cols": ["article", "date of the spike", "views", "61-day median", "times"],
                      "rows": [[a.replace("_", " "), s["date"], s["views"], s["median_61d"], s["ratio"]]
                               for a, sp in sc["spikes"].items() for s in sp]},
            "data": ["describe.json"]}


def static_screen(desc: dict, path: Path) -> None:
    sc = desc["screening"]
    f, axes = plt.subplots(2, 1, figsize=(7.2, 4.6), sharex=True)
    for ax, (title, e, series) in zip(axes, SCREEN_PANELS, strict=True):
        w = sc["estimation_windows"][e]
        ax.axvspan(decimal(w[0]), decimal(w[1]), color=HELD, alpha=0.08, lw=0)
        for key, label, c in series:
            for i, seg in enumerate(segments(sc["series"][key])):
                ax.plot([p[0] for p in seg], [p[1] for p in seg], color=c, lw=0.6, label=label if i == 0 else None)
        ax.set_yscale("log")
        ax.set_title(title, fontsize=9, loc="left")
        ax.legend(frameon=False, fontsize=7, loc="upper left", ncol=3)
    axes[1].set_xticks([2021, 2022, 2023], ["2021", "2022", "2023"])
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


# ---------------------------------------------------------------- tables

def primary_table(ev: dict) -> str:
    out = []
    for e in (KJ, ST):
        r = ev[e]
        out.append(f'  <tr><td>{NAME[e]} <small>day 0 {day(r["event_date"], True)}</small></td>'
                   f'<td class="v">{pct(r["car_pct_uplift"])}<small>CAR {n(r["car"], 2, sign=True)}</small></td>'
                   f'<td class="v">{n(r["excess_views"], 0, sign=True)}</td>'
                   f'<td class="v">{pv(r["placebo_p"])}<small>of {n(r["n_placebo"])} dates</small></td>'
                   f'<td class="v">{pv(r["holm_p"])}</td><td class="v">{pct(r["mdu80_q975_pct"], sign=False)}</td>'
                   f'<td class="v">{r["label"]}</td></tr>')
    return "\n".join(out)


def checks_table(sens: dict) -> str:
    out = []
    for key, label in CHECKS:
        cells = []
        for e in (ST, KJ):
            r = sens.get((e, key))
            cells.append('<td class="v"><small>not run</small></td>' if r is None else
                         f'<td class="v">{pct(r["car_pct_uplift"])}<small>p {pv(r["placebo_p"])} · {n(r["n_placebo"])} dates</small></td>')
        out.append(f'  <tr><td>{label}</td>{"".join(cells)}</tr>')
    return "\n".join(out)


# ---------------------------------------------------------------- the page

def prose_rules(page: str) -> None:
    """Design deviation D: the spec's style rules hold in the article's visible prose."""
    art = page[page.index('<article class="text">'):page.index("</article>")]
    assert "<b>" not in art and "<strong>" not in art, "bold in the article"
    text = H.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", art, flags=re.DOTALL)))
    assert "—" not in text, "an em dash in the article"
    assert ";" not in text, f"a semicolon in the article: {text[max(0, text.index(';') - 80):text.index(';') + 20]!r}"


def main() -> None:
    j = results_reader("memes")
    res, desc, power = j("results"), j("describe"), j("power")
    ev = {e["name"]: e for e in res["events"]}
    sens = {(s["name"], s["variant"]): s for s in res["sensitivity"] if "dropped_event" not in s}
    sens[(ST, "tiktok_prewave")] = next(s for s in res["sensitivity"] if s["variant"] == "tiktok_prewave")
    k, s = ev[KJ], ev[ST]
    kd, sd = desc["events"][KJ], desc["events"][ST]
    null = res["meta"]["null"]

    # the text states these; fail loudly if a re-run changed them
    assert desc["panel_sha256"] == null["panel_sha256"]
    assert k["label"] == "positive" and s["label"] == "uninformative" and not res["dropped_events"]
    assert k["holm_p"] < 0.05 and k["placebo_p"] < 0.04  # the resolution sentence applies (design §4.5)
    assert s["placebo_p"] >= 0.05 and s["mdu80_q975_pct"] > null["uninformative_threshold_pct"]
    assert k["second_regressor"] == "Victor_Williams" and null["events"][KJ]["baseline"]["chosen"] == "pool+second"
    assert null["pool_dropped"] == ["Otmara_Marrero"] and null["pool_kept"] == 43
    assert k["half_life_status"] == s["half_life_status"] == "observed" and s["peak_ar"] < 0.05
    assert res["h2"]["difference_days_stonestreet_minus_kevin_james"] == s["half_life_days"] - k["half_life_days"]
    # §6: a check with p >= 0.05 where the primary is below it is named next to the label
    k_over = sorted(v for (e, v), r in sens.items() if e == KJ and r["placebo_p"] >= 0.05)
    assert k_over == ["window_-3_60", "window_-3_60_without_Matt_LeBlanc"], k_over
    assert all(r["placebo_p"] >= 0.05 for (e, _), r in sens.items() if e == ST)
    assert 0.05 < k["falsification_p"] < 0.1 and s["falsification_p"] > 0.5
    assert sens[(KJ, "window_-3_14")]["falsification_p"] < 0.05 and k["loo_p"] >= 0.05
    peak = max(kd["days"], key=lambda r: r["ar"])
    assert peak["date"] == k["peak_date_raw"] == "2023-09-26"
    second = max((r for r in kd["days"] if r["day"] > 10), key=lambda r: r["views"])
    assert second["date"] == "2023-10-05"
    s_peak_raw = max(sd["days"], key=lambda r: r["ar"])
    assert all(r["ar"] <= r["band"][1] for r in sd["days"]), "the text says Stonestreet never rises above the band"
    assert all(r["car_band"][0] <= r["car"] <= r["car_band"][1] for r in sd["days"])
    k_out = [r["day"] for r in kd["days"] if r["ar"] > r["band"][1]]
    assert k_out == [*range(4, 19), 23], k_out
    avg_out = [r["day"] for r in kd["days"] if r["car"] > r["car_band"][1]]
    assert avg_out == list(range(6, 31)), avg_out
    pre = [r["expected"] for r in kd["days"] if r["day"] <= 0]
    sp = desc["screening"]["spikes"]
    in_win = lambda a, e: [x for x in sp[a] if desc["screening"]["estimation_windows"][e][0] <= x["date"] <= desc["screening"]["estimation_windows"][e][1]]
    assert [x["date"] for x in in_win("Eric_Stonestreet", ST)] == ["2023-07-19"]
    assert [x["date"] for x in in_win("Victor_Williams", KJ)] == ["2023-07-19"]
    st_win = {(a, x["date"]) for a in ("Eric_Stonestreet", *[c for c in sp if c not in ("Kevin_James", "Leah_Remini", "Victor_Williams")])
              for x in in_win(a, ST)}
    assert st_win == {("Eric_Stonestreet", "2023-07-19"), ("Sofía_Vergara", "2023-07-18"), ("Ed_O'Neill", "2023-05-13")}, st_win
    assert [x["date"] for x in in_win("Leah_Remini", KJ)] == ["2023-06-01", "2023-08-03"] and sp["Leah_Remini"][-1]["date"] == "2023-09-08"
    assert [x["date"] for x in sp["Eric_Stonestreet"] if x["date"].startswith("2023-04")] == ["2023-04-28"]
    assert not [x for x in sp["Kevin_James"] if x["date"] >= "2023"]
    st_ratios = [x["ratio"] for x in sp["Eric_Stonestreet"]]
    assert 0.02 < k["placebo_p"] < 0.03 and s["placebo_p"] > 0.5  # "about one in forty", "most ordinary dates"
    top2 = sorted(kd["days"], key=lambda r: r["ar"], reverse=True)[:2]
    assert [r["day"] for r in top2] == [5, 14]
    assert kd["days"][4]["ar"] > 0 and all(r["ar"] < 0.1 for r in kd["days"] if r["day"] <= 0)  # "climb the day after"
    mdu_design = power[ST]["false_positive_rate"]["median_mdu80_q975_pct"]

    A.mkdir(parents=True, exist_ok=True)
    for src in ("results", "describe"):
        shutil.copy(R / f"memes-{src}.json", A / f"{src}.json")
    charts = {"daily": daily_chart(desc, k_out), "average": average_chart(desc, ev), "screen": screen_chart(desc)}
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    static_daily(desc, A / "01-daily.svg")
    static_average(desc, A / "02-average.svg")
    static_screen(desc, A / "03-screening.svg")

    def sv(e, key):
        return sens[(e, key)]

    v = {
        "k_up": pct(k["car_pct_uplift"]), "k_car": n(k["car"], 1), "k_excess": thousands(k["excess_views"]),
        "k_p": pv(k["placebo_p"]), "k_holm": pv(k["holm_p"]), "k_n": n(k["n_placebo"]),
        "k_beat": round(k["placebo_p"] * (k["n_placebo"] + 1)) - 1,
        "k_mdu": pct(k["mdu80_q975_pct"], sign=False),
        "k_day0": day(k["event_date"]), "k_peak_day": day(peak["date"]), "k_peak_views": n(peak["views"]),
        "k_peak_exp": n(round(peak["expected"])), "k_peak_up": pct(up(peak["ar"])),
        "k_second_day": day(second["date"]), "k_second_views": n(second["views"]),
        "k_exp_pre": thousands(sum(pre) / len(pre), 100), "k_last_up": pct(up(kd["days"][-1]["ar"])),
        "k_out_first": k_out[0], "k_out_run": max(d for d in k_out if d < 20), "k_out_late": k_out[-1],
        "k_hl": n(k["half_life_days"]), "k_hl_raw": n(k["half_life_raw_days"]), "k_hl_peak": day(k["peak_date"]),
        "k_f_car": n(k["falsification_car"], 1), "k_f_p": pv(k["falsification_p"]),
        "k_f_power": n(res["meta"]["falsification_power_pct"][KJ]) + NB + "%",
        "k_loo_p": pv(k["loo_p"]), "k_f14_p": pv(sv(KJ, "window_-3_14")["falsification_p"]),
        "k_st_p": pv(k["space_time_p"]), "k_st_n": k["n_space_time"],
        "k_w14_up": pct(sv(KJ, "window_-3_14")["car_pct_uplift"]), "k_w14_p": pv(sv(KJ, "window_-3_14")["placebo_p"]),
        "k_w60_up": pct(sv(KJ, "window_-3_60")["car_pct_uplift"]), "k_w60_p": pv(sv(KJ, "window_-3_60")["placebo_p"]),
        "k_w60_car": n(sv(KJ, "window_-3_60")["car"], 1),
        "k_w60lb_p": pv(sv(KJ, "window_-3_60_without_Matt_LeBlanc")["placebo_p"]),
        "k_koq_up": pct(sv(KJ, "koq_controls")["car_pct_uplift"]), "k_koq_p": pv(sv(KJ, "koq_controls")["placebo_p"]),
        "k_mean_p": pv(sv(KJ, "mean_index")["placebo_p"]), "k_season_p": pv(sv(KJ, "same_season")["placebo_p"]),
        "k_season_n": n(sv(KJ, "same_season")["n_placebo"]),
        "k_beta": n(kd["coef"]["beta_baseline"], 2), "k_beta_vw": n(kd["coef"]["beta_Victor_Williams"], 2),
        "k_sd_a": n(null["events"][KJ]["baseline"]["pool"], 2), "k_sd_b": n(null["events"][KJ]["baseline"]["pool+second"], 2),
        "s_up": pct(s["car_pct_uplift"]), "s_car": n(s["car"], 2), "s_excess": thousands(-s["excess_views"], 100),
        "s_p": pv(s["placebo_p"]), "s_n": n(s["n_placebo"]), "s_mdu": pct(s["mdu80_q975_pct"], sign=False),
        "s_mdu95": pct(s["mdu80_pct"], sign=False), "s_mdu_design": n(mdu_design, 1) + NB + "%",
        "s_beat": round(s["placebo_p"] * (s["n_placebo"] + 1)) - 1,
        "s_day0": day(s["event_date"]), "s_peak": pct(up(s["peak_ar"]), 1), "s_peak_day": day(s["peak_date"]),
        "s_peak_raw": pct(up(s_peak_raw["ar"])), "s_peak_raw_day": day(s_peak_raw["date"]),
        "s_hl": n(s["half_life_days"]), "h2_diff": n(abs(res["h2"]["difference_days_stonestreet_minus_kevin_james"])),
        "s_f_car": n(s["falsification_car"], 1), "s_f_p": pv(s["falsification_p"]),
        "s_f_power": n(res["meta"]["falsification_power_pct"][ST]) + NB + "%", "s_loo_p": pv(s["loo_p"]),
        "s_st_p": pv(s["space_time_p"]),
        "s_d6_up": pct(sv(ST, "day0_2023-10-06")["car_pct_uplift"]), "s_d6_p": pv(sv(ST, "day0_2023-10-06")["placebo_p"]),
        "s_vg_up": pct(sv(ST, "drop_Sofía_Vergara")["car_pct_uplift"]), "s_vg_p": pv(sv(ST, "drop_Sofía_Vergara")["placebo_p"]),
        "s_ext_up": pct(sv(ST, "external_index")["car_pct_uplift"]), "s_ext_p": pv(sv(ST, "external_index")["placebo_p"]),
        "s_tt_up": pct(sv(ST, "tiktok_prewave")["car_pct_uplift"]), "s_tt_p": pv(sv(ST, "tiktok_prewave")["placebo_p"]),
        "s_beta": n(sd["coef"]["beta_baseline"], 2),
        "s_spike_min": n(min(st_ratios)), "s_spike_max": n(max(st_ratios)),
        "st_spike_jul": day("2023-07-19"), "vg_ratio": n(sp["Sofía_Vergara"][0]["ratio"]),
        "vw_ratio": n(in_win("Victor_Williams", KJ)[0]["ratio"]),
        "lr_aug": n(in_win("Leah_Remini", KJ)[-1]["ratio"]), "lr_sep": n(sp["Leah_Remini"][-1]["ratio"]),
        "est_st": f"{day(desc['screening']['estimation_windows'][ST][0])} to {day(desc['screening']['estimation_windows'][ST][1])}",
        "est_kj": f"{day(desc['screening']['estimation_windows'][KJ][0])} to {day(desc['screening']['estimation_windows'][KJ][1])}",
        "pool_n": null["pool_kept"], "v_python": res["meta"]["versions"]["python"],
        "v_numpy": res["meta"]["versions"]["numpy"], "v_pandas": res["meta"]["versions"]["pandas"],
        "primary_table": primary_table(ev), "checks_table": checks_table(sens),
    }
    page = num_refs(render((HERE / "template.html").read_text(encoding="utf-8"), v | {"refs": "{{refs}}"}), v)
    prose_rules(page)
    (ROOT / "texts" / f"{SLUG}.html").write_text(page, encoding="utf-8")
    print(json.dumps({x: y for x, y in v.items() if not x.endswith("table")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
