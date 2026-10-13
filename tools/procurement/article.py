"""Small-scale contract limits: figures and the article, every number from the results, screen, power and manifest files.

Reads docs/research/procurement-bunching-{results,screen,power,manifest}.json and tools/data/procurement/contracts.parquet
(aggregated here into price bins; no contract-level field leaves this script), writes assets/procurement/
(charts.json, 01-around-3m.svg, 03-a-b.svg, 02-monthly.svg, bins.csv, results.json) and
texts/procurement-thresholds.html from tools/procurement/template.html.

    uv run --with numpy==2.5.3 --with scipy==1.18.1 --with pandas==3.0.6 --with pyarrow==26.0.0 --with matplotlib \
        python tools/procurement/article.py
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "site"))
import bunching as bu  # noqa: E402
from article_kit import GREY, HELD, INK, LIGHT, n, render, use_article_style  # noqa: E402

R = ROOT / "docs" / "research"
A = ROOT / "assets" / "procurement"
DATA = ROOT / "tools" / "data" / "procurement"
MONTHS = {"pre": 60, "post": 12}  # 1 Jan 2020 – 31 Dec 2024; 1 Jul 2025 – 30 Jun 2026 (design §4.1)
LOC = {"old_supplies_services": "2 M, old limit", "new_supplies_services": "3 M, new limit",
       "old_works": "6 M, old limit", "new_works": "9 M, new limit"}
MIN_CELL = 30  # publication policy: every published price bin holds at least 30 contracts, or the build stops
plt = use_article_style()


def read(name: str) -> dict:
    return json.loads((R / f"procurement-bunching-{name}.json").read_text(encoding="utf-8"))


def primary(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["value"].gt(0) & df["period"].isin(["pre", "post"]) & ~df["content_duplicate"]]


def counterfactual(df: pd.DataFrame) -> dict:
    """Open-bin counts, exact-million counts and the registered counterfactual (design §5.4) per period."""
    spec = bu.Spec()
    X = bu.design_matrix(spec.degree)
    keep = ~spec.excluded()
    out = {}
    for p in ("pre", "post"):
        v = df.loc[df["period"] == p, "value"].to_numpy(float)
        ex = bu.exact_million(v)
        j = bu.bin_index(v[~ex])
        c = np.bincount(j[j >= 0], minlength=bu.N_BINS).astype(float)
        fitted = np.exp(X @ bu.poisson_fit(c[keep], X[keep]))
        exact = {int(round(m / 1e6)): int((np.abs(v - m) < 0.5).sum()) for m in bu.MILLIONS}
        out[p] = {"open": c, "fitted": fitted, "exact": exact}
    return out


def window_series(cf: dict, lo: float, hi: float) -> pd.DataFrame:
    e = bu.edges()
    js = np.arange(bu.N_BINS)[(e[:-1] >= lo) & (e[1:] <= hi)]
    rows = []
    for p in ("pre", "post"):
        for j in js:
            rows.append({"period": p, "upper_kc": int(e[j + 1]), "contracts": int(cf[p]["open"][j]),
                         "per_month": cf[p]["open"][j] / MONTHS[p], "counterfactual_per_month": cf[p]["fitted"][j] / MONTHS[p]})
    return pd.DataFrame(rows)


def figures(res: dict, cf: dict) -> dict:
    A.mkdir(parents=True, exist_ok=True)
    shutil.copy(R / "procurement-bunching-results.json", A / "results.json")
    w = window_series(cf, 2_400_000, 3_600_000)
    assert w["contracts"].min() >= MIN_CELL, f"a published bin holds fewer than {MIN_CELL} contracts"
    w.to_csv(A / "bins.csv", index=False)
    ex = {p: cf[p]["exact"][3] / MONTHS[p] for p in ("pre", "post")}
    ymax = float(max(w["per_month"].max(), max(ex.values()))) * 1.3  # headroom keeps the dot clear of the band label

    def panel(p, title):
        s = w[w.period == p]
        pts = [[float(r.upper_kc) / 1e6 - 0.005, float(r.per_month)] for r in s.itertuples()]
        cfp = [[float(r.upper_kc) / 1e6 - 0.005, float(r.counterfactual_per_month)] for r in s.itertuples()]
        return {"title": title, "h": 230,
                "x": {"kind": "linear", "domain": [2.4, 3.6], "ticks": [2.4, 2.6, 2.8, 3.0, 3.2, 3.4, 3.6],
                      "fmt": {"dp": 3, "unit": " M Kč"}, "tickfmt": {"dp": 1},
                      "label": "price without VAT, million Kč, bins of 10 000 Kč"},
                "y": {"kind": "linear", "domain": [0, ymax], "fmt": {"dp": 0}, "label": "contracts a month"},
                "marks": [{"type": "span", "v0": 2.85, "v1": 3.0, "c": "light", "label": "band below 3 M"},
                          {"type": "line", "pts": cfp, "c": "grey", "dash": "dash", "name": "counterfactual",
                           "fmt": {"dp": 1}},
                          {"type": "line", "pts": pts, "c": "held" if p == "post" else "ink", "name": "contracts a month",
                           "fmt": {"dp": 1}},
                          {"type": "vrange", "c": "held", "rows": [{"x": 3.0, "mid": ex[p],
                           "tip": f"priced at exactly 3 000 000 Kč: {ex[p]:.0f} a month"}]}]}
    charts = {"around3m": {
        "alt": "Contracts a month by price between 2.4 and 3.6 million Kč without VAT, before and after the limit "
               "rose to 3 million: after the change, more contracts sit just under 3 million than the dashed curve, "
               "and a marked dot shows a high count exactly at 3 million.",
        "panels": [panel("pre", "2020–2024, limit 2 million"), panel("post", "July 2025 – June 2026, limit 3 million")],
        "legend": [{"label": "contracts, 2020–2024", "c": "ink"}, {"label": "contracts, July 2025 – June 2026", "c": "held"},
                   {"label": "counterfactual", "c": "grey", "dash": "dash"},
                   {"label": "at exactly 3 000 000 Kč", "c": "held", "shape": "dot"}],
        "table": {"cols": ["period", "bin up to, Kč", "contracts", "a month", "counterfactual a month"],
                  "rows": [[r.period, int(r.upper_kc), int(r.contracts), round(float(r.per_month), 1),
                            round(float(r.counterfactual_per_month), 1)] for r in w.itertuples()]},
        "data": ["bins.csv"]}}
    L = res["locations"]
    labels = [LOC[k] for k in LOC]
    rows_a = [{"y": LOC[k], "from": L[f"a_{k}_pre"], "to": L[f"a_{k}_post"],
               "tip": f"{LOC[k]}, a: {L[f'a_{k}_pre']:.2f} before, {L[f'a_{k}_post']:.2f} after"} for k in LOC]
    rows_b = [{"y": LOC[k], "from": L[f"b_{k}_pre"], "to": L[f"b_{k}_post"],
               "tip": f"{LOC[k]}, b: {L[f'b_{k}_pre']:.2f} before, {L[f'b_{k}_post']:.2f} after"} for k in LOC]
    top = max(max(r["from"], r["to"]) for r in rows_a + rows_b) * 1.1
    ticks_ab = [round(0.2 * i, 1) for i in range(int(top // 0.2) + 1)]  # the domain starts below 0 so the 0 tick is not clipped
    charts["ab"] = {
        "alt": "Contracts at exactly each limit (a) and just below it (b), per counterfactual contract in the band, "
               "before and after the change: a rises at 3 million and falls at 2 million; b falls at both old limits "
               "and rises at both new ones.",
        "panels": [{"title": f"a · priced at exactly the limit", "h": 170,
                    "x": {"kind": "linear", "domain": [-0.04, top], "ticks": ticks_ab, "fmt": {"dp": 2},
                          "label": "per expected contract in the band"},
                    "y": {"kind": "cat", "domain": labels}, "marks": [{"type": "arrow", "c": "held", "rows": rows_a}]},
                   {"title": "b · strictly below the limit, within 5 %", "h": 170,
                    "x": {"kind": "linear", "domain": [-0.04, top], "ticks": ticks_ab, "fmt": {"dp": 2},
                          "label": "per expected contract in the band"},
                    "y": {"kind": "cat", "domain": labels}, "marks": [{"type": "arrow", "c": "grey", "rows": rows_b}]}],
        "legend": [{"label": "from 2020–2024 (circle) to July 2025 – June 2026 (arrow head)", "c": "held"}],
        "table": {"cols": ["location", "a before", "a after", "b before", "b after"],
                  "rows": [[LOC[k], round(L[f"a_{k}_pre"], 3), round(L[f"a_{k}_post"], 3), round(L[f"b_{k}_pre"], 3),
                            round(L[f"b_{k}_post"], 3)] for k in LOC]},
        "data": ["results.json"]}
    ms = res["monthly_exact_share"]
    months = sorted(ms["3M"])
    idx = {m: i for i, m in enumerate(pd.period_range("2020-01", "2026-06", freq="M").astype(str))}
    change = idx["2025-04"] - 0.5

    def series(key):
        return [[idx[m], 1000 * ms[key][m]] for m in months]

    def segments(key):
        """The series split wherever a month is missing, so no line is drawn across the gap."""
        out, cur = [], []
        for x, y in series(key):
            if cur and x != cur[-1][0] + 1:
                out.append(cur)
                cur = []
            cur.append([x, y])
        return out + [cur]
    ticks = [idx[f"{y}-01"] for y in range(2020, 2027)]
    month_names = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    tip_labels = {str(i): f"{month_names[int(m[5:]) - 1]} {m[:4]}" for m, i in idx.items()}

    def lines(key, name, c):
        segs = segments(key)
        return [{"type": "line", "pts": seg, "c": c, "name": name, **({"end": key[0] + " M"} if i == len(segs) - 1 else {})}
                for i, seg in enumerate(segs)]
    charts["monthly"] = {
        "alt": "Share of contracts in the range priced at exactly 2 million and at exactly 3 million Kč, by month of "
               "conclusion, January 2020 to June 2026: the 3 million share rises after April 2025, the 2 million share "
               "falls.",
        "panels": [{"h": 240, "x": {"kind": "linear", "domain": [-1, len(idx)], "ticks": ticks, "fmt": {"dp": 0},
                                    "tickLabels": {str(t): str(2020 + k) for k, t in enumerate(ticks)},
                                    "tipLabels": tip_labels, "label": "month of conclusion"},
                    "y": {"kind": "linear", "domain": [0, max(max(v for _, v in series(k)) for k in ("2M", "3M")) * 1.1],
                          "fmt": {"dp": 1}, "label": "per 1 000 contracts in the range"},
                    "marks": [{"type": "rule", "axis": "x", "v": change, "c": "grey", "dash": "dot", "label": "3 Apr 2025"},
                              *lines("2M", "at exactly 2 M", "grey"), *lines("3M", "at exactly 3 M", "held")],
                    "padRight": 44}],
        "table": {"cols": ["month", "at 2 M, per 1 000", "at 3 M, per 1 000"],
                  "rows": [[m, round(1000 * ms["2M"][m], 2), round(1000 * ms["3M"][m], 2)] for m in months]},
        "data": ["results.json"]}
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False))

    f, axs = plt.subplots(1, 2, figsize=(7.2, 2.7), sharey=True)
    for ax, p, title in ((axs[0], "pre", "2020–2024, limit 2 million"), (axs[1], "post", "Jul 2025 – Jun 2026, limit 3 million")):
        s = w[w.period == p]
        x = s.upper_kc / 1e6 - 0.005
        ax.axvspan(2.85, 3.0, color=LIGHT, alpha=0.35, lw=0)
        ax.plot(x, s.counterfactual_per_month, color=GREY, ls="--", lw=1)
        ax.plot(x, s.per_month, color=HELD if p == "post" else INK, lw=1)
        ax.plot([3.0], [ex[p]], "o", color=HELD, ms=5, mec="white")
        ax.set_title(title, fontsize=9, color=GREY); ax.set_xlabel("price without VAT, million Kč")
    axs[0].set_ylabel("contracts a month"); f.tight_layout(); f.savefig(A / "01-around-3m.svg"); plt.close(f)

    f, axs = plt.subplots(1, 2, figsize=(7.2, 2.4), sharey=True)
    for ax, rows, title, c in ((axs[0], rows_a, "a · at exactly the limit", HELD), (axs[1], rows_b, "b · just below it", GREY)):
        for i, r in enumerate(reversed(rows)):
            ax.annotate("", xy=(r["to"], i), xytext=(r["from"], i), arrowprops={"arrowstyle": "->", "color": c, "lw": 1.6})
            ax.plot(r["from"], i, "o", color=LIGHT, mec=GREY, ms=5)
        ax.set_xlim(0, top); ax.set_yticks(range(len(rows))); ax.set_yticklabels([r["y"] for r in reversed(rows)])
        ax.set_title(title, fontsize=9, color=GREY); ax.set_xlabel("per expected contract in the band")
    f.tight_layout(); f.savefig(A / "03-a-b.svg"); plt.close(f)

    f, ax = plt.subplots(figsize=(7.2, 2.6))
    for key, c in (("2M", GREY), ("3M", HELD)):
        for i, seg in enumerate(segments(key)):
            ax.plot([q[0] for q in seg], [q[1] for q in seg], color=c, lw=1.2,
                    label=f"at exactly {key[0]} million" if i == 0 else None)
    ax.axvline(change, color=GREY, ls=":", lw=0.8)
    ax.set_xticks(ticks); ax.set_xticklabels([str(y) for y in range(2020, 2027)])
    ax.set_ylabel("per 1 000 contracts"); ax.legend(frameon=False)
    f.tight_layout(); f.savefig(A / "02-monthly.svg"); plt.close(f)
    return {"window": w, "exact3": ex}


def n2(v: float) -> str:
    """Two decimals, keeping the sign of a negative value that rounds to zero (−0.00), so an interval's side shows."""
    s = n(v, 2)
    return "−" + s if v < 0 and not s.startswith("−") else s


GROUP = re.compile(r"(?<=\d) (?=\d{3}(?!\d))")


def nbsp_numbers(html: str) -> str:
    """A thousands separator that cannot break a line: U+00A0 between digit groups, in text and attribute values
    alike (the page has no URL or code with a digit group)."""
    return GROUP.sub("\u00a0", html)


def renumber_refs(html: str) -> str:
    """References numbered by first citation in the page (editorial standard §9): ids, links, labels and order."""
    order = []
    for k in re.findall(r'href="#r(\d+)"', html):
        if k not in order:
            order.append(k)
    new = {old: str(i + 1) for i, old in enumerate(order)}
    items = {num: whole for whole, num in re.findall(r'(<li id="r(\d+)">.*?</li>)', html, re.S)}
    assert set(items) == set(order), f"uncited or missing references: {set(items) ^ set(order)}"
    a, b = html.index("<ol>", html.index('id="refs"')), html.index("</ol>", html.index('id="refs"'))
    body = "\n".join(re.sub(r'id="r\d+"', f'id="r{new[k]}"', items[k]) for k in order)
    html = html[:a] + "<ol>\n" + body + "\n" + html[b:]
    html = re.sub(r'<a href="#r(\d+)">\1</a>', lambda m: f'<a href="#rX{new[m.group(1)]}">{new[m.group(1)]}</a>', html)
    return html.replace('href="#rX', 'href="#r')


def values(res: dict, screen: dict, power: dict, manifest: dict, df: pd.DataFrame, fig: dict) -> dict:
    d, s, L, rob = res["decision"], res["secondary"], res["locations"], res["robustness"]
    h1, h2 = d["D_new_a"], d["D_old_a"]
    v = {"h1": n(h1["estimate"], 2), "h1_lo": n(h1["ci95"][0], 2), "h1_hi": n(h1["ci95"][1], 2),
         "h1_lo90": n(h1["ci90"][0], 2), "h1_hi90": n(h1["ci90"][1], 2), "h1_label": h1["label"], "h1_se": n(h1["se"], 3),
         "h2": n(h2["estimate"], 2), "h2_lo": n(h2["ci95"][0], 2), "h2_hi": n(h2["ci95"][1], 2), "h2_label": h2["label"],
         "mde_h1": n(power["data_step_mde"]["D_new_a"], 2), "mde_h2": n(power["data_step_mde"]["D_old_a"], 2),
         "h1_pct": n(100 * h1["estimate"]), "h1_lo_pct": n(100 * h1["ci95"][0]), "h1_hi_pct": n(100 * h1["ci95"][1]),
         "bias": n2(h1["placebo_bias"]), "kd_lo95": n2(s["k_low_minus_high"]["ci95"][0]),
         "kd_hi95": n2(s["k_low_minus_high"]["ci95"][1]), "gate": "passed" if not d["gate_failed"] else "failed",
         "k_low": n(s["k_low"]["estimate"], 2), "k_high": n(s["k_high"]["estimate"], 2),
         "kd": n(s["k_low_minus_high"]["estimate"], 2), "kd_lo90": n(s["k_low_minus_high"]["ci90"][0], 2),
         "kd_hi90": n(s["k_low_minus_high"]["ci90"][1], 2), "adjust": res["adjust"]}
    for key, tag in (("D_new_a_supplies_services", "n3"), ("D_new_a_works", "n9"), ("D_old_a_supplies_services", "o2"),
                     ("D_old_a_works", "o6"), ("D_new_b", "nb"), ("D_old_b", "ob"), ("D_new_b_supplies_services", "nb3"),
                     ("D_new_b_works", "nb9")):
        v[tag], v[tag + "_lo"], v[tag + "_hi"] = (n(s[key]["estimate"], 2), n(s[key]["ci95"][0], 2),
                                                   n(s[key]["ci95"][1], 2))
    for k, tag in (("old_supplies_services", "l2"), ("new_supplies_services", "l3"), ("old_works", "l6"),
                   ("new_works", "l9")):
        for m in ("a", "b"):
            for p in ("pre", "post"):
                v[f"{tag}{m}_{p}"] = n(L[f"{m}_{k}_{p}"], 2)
    pl = [(c, s[f"placebo_a_control_{c}"]["ci90"]) for c in ("4M", "5M", "7M", "8M", "10M", "12M", "13M")]
    out_of_zero = [c for c, (lo, hi) in pl if hi < 0 or lo > 0]
    assert out_of_zero == ["10M"], out_of_zero
    v["p10"] = n(s["placebo_a_control_10M"]["estimate"], 2)
    v["p10_lo"], v["p10_hi"] = n2(s["placebo_a_control_10M"]["ci90"][0]), n2(s["placebo_a_control_10M"]["ci90"][1])

    def row(name, tag):
        c = rob[name]["calibrated_D_new_a"]
        v[tag], v[tag + "_lo"], v[tag + "_hi"], v[tag + "_lab"] = n(c["estimate"], 2), n(c["ci95"][0], 2), n(c["ci95"][1], 2), c["label"]
    names = {"window 2.5 % below": "w25", "window 10 % below": "w10", "polynomial degree 5": "d5",
             "polynomial degree 9": "d9", "other adjustment of a": "adj", "neighbouring controls only": "nbr",
             "VAT images excluded from the fit": "vat", "R-VAT: VAT-only prices added, / 1.21": "rvat",
             "equal with- and without-VAT values dropped": "eq", "no content-key deduplication": "nod",
             "post from 3 April 2025": "apr", "post from 1 October 2025": "oct", "pre 2022–2024 only": "p22",
             "largest 1 % of authorities dropped": "big", "linked records dropped": "lnk",
             "call-offs (objednávka) dropped": "cof", "frameworks and periodic prices dropped": "frm",
             "authority flagged as payer only": "pay", "placebo date 1 January 2023 (pre only)": "pdt"}
    for name, tag in names.items():
        row(name, tag)
    calibrated = [rob[k]["calibrated_D_new_a"]["estimate"] for k in names if k not in
                  ("window 10 % below", "authority flagged as payer only", "placebo date 1 January 2023 (pre only)")]
    v["rob_min"], v["rob_max"] = n(min(calibrated), 2), n(max(calibrated), 2)
    sens = res["sensitivity"]
    assert set(sens["rows_that_flip"]) == {"window 10 % below", "authority flagged as payer only"} and not sens["sensitive"]
    v["n_flip"] = str(len(sens["rows_that_flip"]))
    pd_ = rob["placebo date 1 January 2023 (pre only)"]["D_new_a"]["ci90"]
    v["pdt_lo90"], v["pdt_hi90"] = n(pd_[0], 2), n(pd_[1], 2)
    xw = rob["type split: works by subject stems"]["D_new_a_supplies_services"]
    v["xw"], v["xw_lo"], v["xw_hi"] = n2(xw["estimate"]), n2(xw["ci90"][0]), n2(xw["ci90"][1])
    xs = rob["type split: supplies and services by subject stems"]["D_new_a_works"]
    v["xs_lo"], v["xs_hi"] = n2(xs["ci90"][0]), n2(xs["ci90"][1])
    assert res["type_cross_check"] == {"stems": "fails", "hlidac": "skipped"}
    # screening and data
    v["n_records"] = n(screen["records"]); v["n_czk"] = n(screen["CZK with a price"])
    v["n_notpurchase"] = n(screen["subject excluded as not a purchase (§4.5)"])
    v["n_noico"] = n(screen["no publishing IČO (dropped)"])
    dup = screen["content-key duplicates flagged (dropped in the primary)"]
    v["n_dup"] = n(dup["at an exact whole million"] + dup["other values"])
    pres = screen["presence by period (all values)"]
    v["pres_pre"], v["pres_post"] = n(100 * pres["pre"]["share with value without VAT"], 1), n(100 * pres["post"]["share with value without VAT"], 1)
    ms = res["monthly_exact_share"]
    for key, tag in (("2M", "m2"), ("3M", "m3")):
        pre = [x for mo, x in ms[key].items() if mo < "2025"]
        post = [x for mo, x in ms[key].items() if mo >= "2025-07"]
        v[f"{tag}_pre"], v[f"{tag}_post"] = n(1000 * float(np.mean(pre)), 1), n(1000 * float(np.mean(post)), 1)
        v[f"{tag}_pre_max"] = n(1000 * max(pre), 1)
    kept = screen["CZK with a price"] - screen["subject excluded as not a purchase (§4.5)"] - screen["no publishing IČO (dropped)"]
    v["pay_share"] = n(100 * screen["flag payer_flag (kept)"] / kept)
    v["min_cell"] = str(MIN_CELL)
    v["n_dumps"] = str(len(manifest)); v["gib"] = n(sum(m["bytes"] for m in manifest.values()) / 2 ** 30, 1)
    m = df["value"].gt(bu.LO) & df["value"].le(bu.HI)
    v["n_pre"], v["n_post"] = n(int((m & (df.period == "pre")).sum())), n(int((m & (df.period == "post")).sum()))
    v["n_auth"] = n(int(df.loc[m, "authority"].nunique()))
    v["ex3_pre"], v["ex3_post"] = n(fig["exact3"]["pre"], 0), n(fig["exact3"]["post"], 0)
    return v


def main() -> None:
    res, screen, power, manifest = read("results"), read("screen"), read("power"), read("manifest")
    df = primary(pd.read_parquet(DATA / "contracts.parquet", columns=["value", "period", "content_duplicate", "authority"]))
    fig = figures(res, counterfactual(df))
    v = values(res, screen, power, manifest, df, fig)
    out = nbsp_numbers(renumber_refs(render(HERE.joinpath("template.html").read_text(encoding="utf-8"), v)))
    (ROOT / "texts" / "procurement-thresholds.html").write_text(out, encoding="utf-8")
    print(f"written texts/procurement-thresholds.html, {len(v)} values")


if __name__ == "__main__":
    main()
