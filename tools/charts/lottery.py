"""Chart specs for the lottery study (texts/lottery.html), read by assets/charts.js.

Reads assets/lottery/results.json and the CSVs beside it (written by the scripts in tools/lottery/) and writes
assets/lottery/charts.json. tools/lottery/figures.py draws the static SVG fallbacks from the same files.

    python3 tools/charts/lottery.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "site"))
from article_kit import n  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets/lottery"
R = json.loads((A / "results.json").read_text())


def rows(name: str) -> list[dict]:
    with open(A / name) as fh:
        return [{k: float(v) for k, v in r.items()} for r in csv.DictReader(fh)]


charts = {}
F, M, E, I = R["fairness"], R["model"], R["eurojackpot"], R["importance"]

# fig. 1 · times each number was drawn
cnt = rows("sportka_counts.csv")
lo, hi = F["per_number"]["band"]
exp = F["expected"]
bars = []
for r in cnt:
    k = int(r["number"])
    out = r["count"] < lo or r["count"] > hi
    bars.append({"x": str(k), "y0": exp, "y1": r["count"], "c": "ink" if out else "held",
                 "tip": f"number {k}\ndrawn {n(r['count'])} times (expected {n(exp, 1)})\nz {r['z']:+.2f}".replace("+-", "−").replace("-", "−")
                        + f"\np {r['p_raw']:.3f}, after Benjamini–Hochberg {r['p_fdr']:.2f}"})
charts["counts"] = {
    "alt": f"Bars for the 49 Sportka numbers showing how often each was drawn in {n(F['n_draws'])} draws, 1994–2026, against the expected {n(exp, 1)}. "
           f"All lie between {min(int(r['count']) for r in cnt)} and {max(int(r['count']) for r in cnt)}; four fall outside the 95 % range for a single number, as about 2.5 of 49 would by chance.",
    "legend": [{"label": "inside the 95 % range for one number", "c": "held", "shape": "box", "o": 0.85},
               {"label": "outside it", "c": "ink", "shape": "box", "o": 0.85},
               {"label": f"expected, {n(exp, 1)}", "c": "ink"},
               {"label": f"95 % range, {lo:.0f}–{hi:.0f}", "c": "grey", "dash": "dash"}],
    "panels": [{"h": 280, "title": f"times drawn, {n(F['n_draws'])} draws of 6 of 49",
                "x": {"kind": "cat", "domain": [str(k) for k in range(1, 50)], "labels": False, "label": "numbers 1 to 49"},
                "y": {"kind": "linear", "domain": [820, 1010], "ticks": [850, 900, 950, 1000]},
                "marks": [{"type": "vbar", "rows": bars},
                          {"type": "rule", "axis": "y", "v": exp, "c": "ink"},
                          {"type": "rule", "axis": "y", "v": lo, "c": "grey", "dash": "dash"},
                          {"type": "rule", "axis": "y", "v": hi, "c": "grey", "dash": "dash"}]}],
    "table": {"cols": ["number", "times drawn", "z", "p", "p, Benjamini–Hochberg"],
              "rows": [[str(int(r["number"])), n(r["count"]), f"{r['z']:.2f}".replace("-", "−"), f"{r['p_raw']:.3f}", f"{r['p_fdr']:.2f}"] for r in cnt]},
    "data": ["../assets/lottery/sportka_counts.csv", "../assets/lottery/sportka.csv"],
}

# fig. 2 · the most frequent number
hot = [(f"Sportka {p['from']}–{p['to']}", p["hottest"], p["hottest_count"], p["expected"], "held") for p in F["periods"]]
hot.append(("Sportka 1994–2026", F["hottest_overall"]["number"], F["hottest_overall"]["count"], exp, "held"))
hot += [(f"fair simulation, seed {s['seed']}", s["hottest"], s["hottest_count"], exp, "grey") for s in F["seeds"]]
charts["hottest"] = {
    "alt": "Dot chart of the most frequent number: 20 in 1994–2003, 31 in 2004–2013, 47 in 2014–2026 and 44 over the whole history; "
           "in four fair simulated histories of the same size it is 23, 14, 2 and 17.",
    "legend": [{"label": "Sportka draws", "c": "held", "shape": "o"}, {"label": "simulated fair draws", "c": "grey", "shape": "o"}],
    "panels": [{"h": 300, "x": {"kind": "linear", "domain": [0, 50], "ticks": [1, 10, 20, 30, 40, 49], "label": "most frequent number"},
                "y": {"kind": "cat", "domain": [h[0] for h in hot]},
                "marks": [{"type": "dots", "pts": [{"x": h[1], "y": h[0], "c": h[4], "label": str(h[1]),
                                                     "tip": f"{h[0]}\nmost frequent: {h[1]}, drawn {n(h[2])} times (expected {n(h[3], 1)})"} for h in hot]}]}],
    "table": {"cols": ["history", "most frequent number", "times drawn", "expected"],
              "rows": [[h[0], str(h[1]), n(h[2]), n(h[3], 1)] for h in hot]},
    "data": ["../assets/lottery/results.json"],
}

# fig. 3 · the prediction model
lab = {"logistic": "logistic regression", "boosting": "gradient boosting"}
cats, rng_rows, dots, trows = [], [], [], []
for k, m in M["models"].items():
    t, tr = f"{lab[k]}, test", f"{lab[k]}, training"
    cats += [tr, t]
    rng_rows.append({"y": t, "mid": m["auc_test"], "lo": m["auc_lo"], "hi": m["auc_hi"], "c": "held", "label": f"{m['auc_test']:.3f}",
                     "tip": f"{lab[k]}, {n(M['test_days'])} test days\nAUC {m['auc_test']:.3f}, 95 % CI {m['auc_lo']:.3f} to {m['auc_hi']:.3f}\nlog loss vs 6/49: {m['dlogloss']:+.5f}"})
    dots.append({"x": m["auc_train"], "y": tr, "c": "grey", "shape": "d", "label": f"{m['auc_train']:.3f}",
                 "tip": f"{lab[k]}, {n(M['train_days'])} training days\nAUC {m['auc_train']:.3f} on the data it was fitted to"})
    trows.append([lab[k], f"{m['auc_train']:.3f}", f"{m['auc_test']:.3f}", f"{m['auc_lo']:.3f} to {m['auc_hi']:.3f}",
                  f"{m['dlogloss']:.5f} ({m['dlogloss_lo']:.5f} to {m['dlogloss_hi']:.5f})".replace("-", "−")])
charts["model"] = {
    "alt": f"AUC of two models predicting which numbers the next Sportka draw holds. On the {M['test_days']} most recent days both score about 0.49–0.50 with 95 % intervals that include 0.5; "
           f"gradient boosting scores {M['models']['boosting']['auc_train']:.3f} on its own training data.",
    "legend": [{"label": "test AUC, 95 % CI bootstrap by drawing day", "c": "held"},
               {"label": "training AUC", "c": "grey", "shape": "d"},
               {"label": "0.5 = chance", "c": "ink", "dash": "dash"}],
    "panels": [{"h": 220, "x": {"kind": "linear", "domain": [0.47, 0.6], "ticks": [0.48, 0.5, 0.52, 0.54, 0.56, 0.58, 0.6], "tickfmt": {"dp": 2}, "label": "AUC"},
                "y": {"kind": "cat", "domain": cats},
                "marks": [{"type": "rule", "axis": "x", "v": 0.5, "c": "ink", "dash": "dash", "tip": "0.5 = no better than chance"},
                          {"type": "range", "w": 2.5, "rows": rng_rows}, {"type": "dots", "pts": dots}]}],
    "table": {"cols": ["model", "training AUC", "test AUC", "95 % CI", "log loss minus baseline (95 % CI)"], "rows": trows},
    "data": ["../assets/lottery/results.json", "../assets/lottery/sportka.csv"],
}

# fig. 4 · posterior predictive check
P = E["ppc"]["bins"]
charts["ppc"] = {
    "alt": "For six jackpot ranges, the observed number of Eurojackpot jackpot wins against the model's posterior predictive mean and 95 % interval; every observed count lies inside its interval, "
           "and the top range, €110–120 million, has 4 wins in 8 draws against about 2 predicted.",
    "legend": [{"label": "observed wins", "c": "held", "shape": "o"}, {"label": "predicted, mean and 95 % interval", "c": "grey"}],
    "panels": [{"h": 260, "x": {"kind": "cat", "domain": [b["bin"] for b in P], "label": "jackpot at the draw, € million"},
                "y": {"kind": "linear", "domain": [0, 15], "ticks": [0, 5, 10, 15], "label": "jackpot wins"},
                "marks": [{"type": "vrange", "w": 6, "c": "light", "rows": [{"x": b["bin"], "lo": b["pred_lo"], "hi": b["pred_hi"], "mid": b["pred_mean"],
                                                                               "tip": f"€{b['bin']} M, {b['draws']} draws\npredicted {b['pred_mean']:.2f} wins, 95 % interval {b['pred_lo']:.0f}–{b['pred_hi']:.0f}"} for b in P]},
                          {"type": "dots", "pts": [{"x": b["bin"], "y": b["observed"], "c": "held", "r": 5.5, "label": f"{b['observed']} of {b['draws']}",
                                                    "tip": f"€{b['bin']} M\nobserved {b['observed']} wins in {b['draws']} draws\nposterior predictive p = {b['pp_p']:.2f}"} for b in P]}]}],
    "table": {"cols": ["jackpot, € million", "draws", "observed wins", "predicted mean", "95 % interval", "p (two-sided)"],
              "rows": [[b["bin"], str(b["draws"]), str(b["observed"]), f"{b['pred_mean']:.2f}", f"{b['pred_lo']:.0f}–{b['pred_hi']:.0f}", f"{b['pp_p']:.2f}"] for b in P]},
    "data": ["../assets/lottery/ej_draws_2025_2026.csv", "../assets/lottery/results.json"],
}

# fig. 5 · expected value per column
cv = rows("ej_curves.csv")
charts["ev"] = {
    "alt": "Expected payout of one €2 Eurojackpot column rises with the jackpot, from about €0.60 at €10 million to about €1.29 at the €120 million cap, and stays below the €2 price across the whole range; "
           "the lower tiers contribute about €0.54 to €0.55 throughout.",
    "legend": [{"label": "expected payout, posterior mean", "c": "held"}, {"label": "95 % credible band", "c": "held", "shape": "box", "o": 0.18},
               {"label": "lower tiers only", "c": "grey", "dash": "dash"}, {"label": "price, €2", "c": "ink"}],
    "panels": [{"h": 280, "x": {"kind": "linear", "domain": [10, 120], "ticks": [10, 30, 50, 70, 90, 120], "label": "jackpot, € million", "fmt": {"dp": 0, "pre": "€", "unit": " M"}},
                "y": {"kind": "linear", "domain": [0, 2.1], "ticks": [0, 0.5, 1, 1.5, 2], "tickfmt": {"dp": 1}, "label": "€ per column"},
                "marks": [{"type": "area", "name": "95 % band", "c": "held", "o": 0.18, "fmt": {"dp": 2, "pre": "€"},
                           "pts": [[r["jackpot_eur"] / 1e6, r["ev_lo"], r["ev_hi"]] for r in cv]},
                          {"type": "line", "name": "expected payout", "c": "held", "fmt": {"dp": 2, "pre": "€"}, "pts": [[r["jackpot_eur"] / 1e6, r["ev_mean"]] for r in cv]},
                          {"type": "line", "name": "lower tiers", "c": "grey", "dash": "dash", "w": 1.4, "fmt": {"dp": 2, "pre": "€"},
                           "pts": [[r["jackpot_eur"] / 1e6, r["ev_lower_mean"]] for r in cv]},
                          {"type": "rule", "axis": "y", "v": 2, "c": "ink", "label": "price of a column, €2", "anchor": "end"}]}],
    "table": {"cols": ["jackpot", "columns sold, million (95 % CrI)", "expected payout (95 % CrI)", "expected loss per column"],
              "rows": [[f"€{r['jackpot'] / 1e6:.0f} M", f"{r['N']['mean'] / 1e6:.1f} ({r['N']['lo'] / 1e6:.1f}–{r['N']['hi'] / 1e6:.1f})",
                        f"€{r['ev']['mean']:.2f} ({r['ev']['lo']:.2f}–{r['ev']['hi']:.2f})", f"€{r['loss']['mean']:.2f}"] for r in E["levels"]]},
    "data": ["../assets/lottery/ej_curves.csv", "../assets/lottery/results.json"],
}

# fig. 6 · importance sampling
d = I["delta"]
charts["importance"] = {
    "alt": f"Estimates, with 95 % intervals, of how much more an unpopular Eurojackpot combination returns per column at the €120 million cap than an average one; the exact value is €{d:.3f}. "
           "Plain Monte Carlo with a million columns sees no jackpot and estimates zero or an interval of ±€0.42; importance sampling recovers the value, with intervals narrowing as the jackpot is oversampled.",
    "legend": [{"label": "plain Monte Carlo", "c": "grey"}, {"label": "importance sampling", "c": "held"}, {"label": f"exact, €{d:.3f}", "c": "ink", "dash": "dash"}],
    "panels": [{"h": 280, "x": {"kind": "linear", "domain": [-0.45, 0.45], "ticks": [-0.4, -0.2, 0, 0.2, 0.4], "tickfmt": {"dp": 1}, "label": "€ per column, 10⁶ simulated columns each"},
                "y": {"kind": "cat", "domain": [f"{e['name']} · {n(e['jackpots'])} jackpots" for e in I["estimators"]]},
                "marks": [{"type": "rule", "axis": "x", "v": 0, "c": "grey"},
                          {"type": "rule", "axis": "x", "v": d, "c": "ink", "dash": "dash", "tip": f"exact gain €{d:.4f} per column"},
                          {"type": "range", "w": 2.5, "rows": [{"y": f"{e['name']} · {n(e['jackpots'])} jackpots", "mid": e["est"], "lo": e["lo"], "hi": e["hi"], "c": "grey" if e["name"].startswith("naive") else "held",
                                                               "tip": f"{e['name']}\nestimate €{e['est']:.4f}, 95 % CI {e['lo']:.4f} to {e['hi']:.4f}\njackpots in the sample: {n(e['jackpots'])}".replace("-", "−")} for e in I["estimators"]]}]}],
    "table": {"cols": ["estimator", "estimate, €", "95 % CI", "jackpots sampled"],
              "rows": [[e["name"], f"{e['est']:.4f}", f"{e['lo']:.4f} to {e['hi']:.4f}".replace("-", "−"), str(e["jackpots"])] for e in I["estimators"]]},
    "data": ["../assets/lottery/results.json"],
}

(A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False, indent=1) + "\n")
print("wrote", A / "charts.json", list(charts))
