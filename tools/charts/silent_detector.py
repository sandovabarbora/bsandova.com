"""Chart specs for the silent-detector article (texts/silent-detector.html), read by assets/charts.js.

Reads assets/detector/detector.json (written by quaesitor/method/src/detector.py, the same file
tools/detector_figures.py draws the static SVGs from) and writes assets/detector/charts.json.

    python3 tools/charts/silent_detector.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets/detector"
D = json.loads((A / "detector.json").read_text())
DATA = ["../assets/detector/detector.json"]
NB = " "


def n(v: float, dp: int = 0, unit: str = "") -> str:
    """Numbers as the article writes them: a space between thousands, a real minus sign."""
    s = f"{abs(v):,.{dp}f}".replace(",", NB)
    return ("−" if v < 0 else "") + s + unit


def pct(v: float, dp: int = 0) -> str:
    return n(100 * v, dp, " %")


charts = {}

# fig. 1 · held-out AUC per feature set and model family (as detector_figures.fig1)
LABEL = {"agreement": "agreement across repeats", "sql": "shape of the SQL", "run": "model · pack · language", "all": "everything above"}
FAM = [("logistic", "logistic", "logistic regression", "grey"), ("gbm", "boosting", "gradient boosting", "held")]
names = ["agreement", "sql", "run", "all"]
base = D["baseline"]
rows, cats, trows = [], [], []
for nm in names:
    for key, short, full, c in FAM:
        m = D["models"][f"{nm}/{key}"]
        t5 = next(t for t in m["trust"] if t["threshold"] == 0.5)
        lab = f"{LABEL[nm]} · {short}"
        cats.append(lab)
        prec = "–" if t5["precision_correct"] is None else pct(t5["precision_correct"])
        rows.append({"y": lab, "x0": 0.3, "x1": m["auc"], "c": c, "label": f"{m['auc']:.2f}",
                     "tip": f"{LABEL[nm]}\n{full}\nAUC {m['auc']:.2f}\nat a 50 % threshold: forwards {pct(t5['forwarded_share'], 1 if t5['forwarded_share'] < 0.01 else 0)}, {prec} of them correct"})
    trows.append([LABEL[nm], f"{D['models'][nm + '/logistic']['auc']:.2f}", f"{D['models'][nm + '/gbm']['auc']:.2f}"])
trows.append(["rule: forward only when all repeats agree", f"{base['auc']:.2f}", "–"])
title = f"silently wrong or correct? {n(D['trained_on'])} answers, {D['questions']} questions"
charts["auc"] = {
    "alt": "Horizontal bars of held-out AUC for four feature sets and two model families; all between 0.43 and 0.64, with 0.5 marked as coin flip and the agreement rule at 0.55.",
    "legend": [{"label": "logistic regression", "c": "grey", "shape": "box", "o": 0.85},
               {"label": "gradient boosting", "c": "held", "shape": "box", "o": 0.85},
               {"label": "0.5 = coin flip", "c": "ink", "dash": "dash"},
               {"label": f"rule: repeats agree · {base['auc']:.2f}", "c": "ink", "dash": "dot"}],
    "panels": [{"h": 330, "title": title,
                "x": {"kind": "linear", "domain": [0.3, 1.0], "ticks": [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
                      "tickfmt": {"dp": 1}, "label": "AUC, held-out questions (GroupKFold by question)"},
                "y": {"kind": "cat", "domain": cats},
                "marks": [{"type": "hbar", "rows": rows},
                          {"type": "rule", "axis": "x", "v": 0.5, "c": "ink", "dash": "dash",
                           "tip": "0.5 = coin flip"},
                          {"type": "rule", "axis": "x", "v": base["auc"], "c": "ink", "dash": "dot",
                           "tip": f"rule: forward only when all repeats agree\nAUC {base['auc']:.2f}\nforwards {pct(base['forwarded_share'])}, {pct(base['precision_correct'])} of them correct"}]}],
    "table": {"cols": ["feature set", "logistic regression AUC", "gradient boosting AUC"], "rows": trows},
    "data": DATA,
}

# fig. 2 · SQL-shape gradient boosting, trained on one pack and scored on another (as detector_figures.fig2)
tr = D["transfer_sql_gbm_auc"]
packs = list(tr)
cells, trows = [], []
for a in packs:
    for b in packs:
        v = tr[a][b]
        what = "held-out questions within the pack" if a == b else "trained on the row, scored on the column"
        note = "\nbelow 0.5: the pattern points the wrong way" if v < 0.5 else ""
        cells.append({"x": b, "y": a, "v": v, "s": f"{v:.2f}",
                      "tip": f"trained on {a} · tested on {b}\nAUC {v:.2f}\n{what}{note}"})
    trows.append([a] + [f"{tr[a][b]:.2f}" for b in packs])
charts["transfer"] = {
    "alt": "A three by three matrix of AUC values for the SQL-shape model trained on one pack and tested on another; off-diagonal values between 0.41 and 0.62, and the ecommerce and taxi diagonals below 0.5.",
    "panels": [{"h": 300, "title": "SQL-shape AUC · rows trained on, columns tested on",
                "x": {"kind": "cat", "domain": packs, "nogrid": True, "label": "tested on"},
                "y": {"kind": "cat", "domain": packs},
                "marks": [{"type": "cell", "c": "held", "domain": [0.0, 1.25], "rows": cells}]}],
    "table": {"cols": ["trained on ↓ · tested on →"] + packs, "rows": trows},
    "data": DATA,
}

(A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False, indent=1) + "\n")
print("wrote", A / "charts.json", list(charts))
