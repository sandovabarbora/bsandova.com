"""Chart specs for the silent-detector article (texts/silent-detector.html), read by assets/charts.js.

Reads assets/detector/detector.json (written by quaesitor/method/src/detector.py) for the filter tips and
assets/detector/auc.json (tools/detector/auc.py: the same AUCs refitted from assets/detector/answers.csv, with
question-level bootstrap 95 % intervals) and writes assets/detector/charts.json. tools/figures/detector_figures.py draws the
static SVG fallbacks from the same two files.

    python3 tools/charts/silent_detector.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets/detector"
D = json.loads((A / "detector.json").read_text())
C = json.loads((A / "auc.json").read_text())
DATA = ["../assets/detector/answers.csv", "../assets/detector/auc.json", "../assets/detector/detector.json"]
NB = " "


def n(v: float, dp: int = 0, unit: str = "") -> str:
    """Numbers as the article writes them: a space between thousands, a real minus sign."""
    s = f"{abs(v):,.{dp}f}".replace(",", NB)
    return ("−" if v < 0 else "") + s + unit


def pct(v: float, dp: int = 0) -> str:
    return n(100 * v, dp, " %")


def ci(r: dict) -> str:
    return f"95 % CI {r['lo']:.2f} to {r['hi']:.2f}"


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
        b = C["models"][f"{nm}/{key}"]
        t5 = next(t for t in m["trust"] if t["threshold"] == 0.5)
        lab = f"{LABEL[nm]} · {short}"
        cats.append(lab)
        prec = "–" if t5["precision_correct"] is None else pct(t5["precision_correct"])
        rows.append({"y": lab, "x0": 0.3, "x1": m["auc"], "lo": b["lo"], "hi": b["hi"], "c": c, "label": f"{m['auc']:.2f}",
                     "tip": f"{LABEL[nm]}\n{full}\nAUC {m['auc']:.2f}, {ci(b)}\n{b['reading']}\nat a 50 % threshold: forwards {pct(t5['forwarded_share'], 1 if t5['forwarded_share'] < 0.01 else 0)}, {prec} of them correct"})
    lg, gb = C["models"][nm + "/logistic"], C["models"][nm + "/gbm"]
    trows.append([LABEL[nm], f"{lg['auc']:.2f}", f"{lg['lo']:.2f} to {lg['hi']:.2f}", f"{gb['auc']:.2f}", f"{gb['lo']:.2f} to {gb['hi']:.2f}"])
R = C["rule"]
trows.append(["rule: forward only when all repeats agree", f"{R['auc']:.2f}", f"{R['lo']:.2f} to {R['hi']:.2f}", "–", "–"])
title = f"silently wrong or correct? {n(C['answers'])} answers, {C['questions']} questions"
charts["auc"] = {
    "alt": "Horizontal bars of held-out AUC for four feature sets and two model families, each with a question-level bootstrap 95 % interval; AUCs between 0.43 and 0.64, and only the best, 0.64 (0.51 to 0.77), has an interval that excludes 0.5.",
    "legend": [{"label": "logistic regression", "c": "grey", "shape": "box", "o": 0.85},
               {"label": "gradient boosting", "c": "held", "shape": "box", "o": 0.85},
               {"label": "95 % CI, bootstrap by question", "c": "ink"},
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
                           "tip": f"rule: forward only when all repeats agree\nAUC {base['auc']:.2f}, {ci(R)}\nforwards {pct(base['forwarded_share'])}, {pct(base['precision_correct'])} of them correct"}]}],
    "table": {"cols": ["feature set", "logistic regression AUC", "95 % CI", "gradient boosting AUC", "95 % CI"], "rows": trows},
    "data": DATA,
}

# fig. 2 · SQL-shape gradient boosting, trained on one pack and scored on another, with bootstrap intervals
tr = C["transfer_sql_gbm"]
PACK = {"ecommerce": "e-commerce", "saas": "SaaS", "taxi": "taxi"}
packs = list(tr)
cats, rows, trows = [], [], []
for a in packs:
    for b in packs:
        r = tr[a][b]
        lab = f"{PACK[a]}, within pack" if a == b else f"{PACK[a]} → {PACK[b]}"
        what = f"held-out questions within {PACK[a]} ({r['groups']} questions)" if a == b else \
            f"trained on {PACK[a]}, scored on {PACK[b]} ({r['groups']} questions)"
        cats.append(lab)
        rows.append({"y": lab, "mid": r["auc"], "lo": r["lo"], "hi": r["hi"], "c": "grey" if a == b else "held",
                     "label": f"{r['auc']:.2f}",
                     "tip": f"{what}\nAUC {r['auc']:.2f}, {ci(r)}\n{r['reading']}"})
        trows.append([PACK[a], PACK[b], str(r["groups"]), f"{r['auc']:.2f}", f"{r['lo']:.2f} to {r['hi']:.2f}", r["reading"]])
charts["transfer"] = {
    "alt": "Nine AUCs with question-level bootstrap 95 % intervals for the SQL-shape model, trained on one pack and scored on another or on held-out questions of the same pack; "
           f"all lie between {min(r['mid'] for r in rows):.2f} and {max(r['mid'] for r in rows):.2f}, and every interval includes 0.5 except taxi within pack, "
           f"{tr['taxi']['taxi']['auc']:.2f} ({tr['taxi']['taxi']['lo']:.2f} to {tr['taxi']['taxi']['hi']:.2f}).",
    "legend": [{"label": "trained on one pack, scored on another", "c": "held"},
               {"label": "within the pack, held-out questions", "c": "grey"},
               {"label": "0.5 = coin flip", "c": "ink", "dash": "dash"}],
    "panels": [{"h": 340, "title": "SQL-shape AUC with 95 % CI, bootstrap by question",
                "x": {"kind": "linear", "domain": [0.0, 1.15], "ticks": [0.0, 0.25, 0.5, 0.75, 1.0],
                      "tickfmt": {"dp": 2}, "label": "AUC on the scored pack"},
                "y": {"kind": "cat", "domain": cats},
                "marks": [{"type": "rule", "axis": "x", "v": 0.5, "c": "ink", "dash": "dash", "tip": "0.5 = coin flip"},
                          {"type": "range", "w": 2, "rows": rows}]}],
    "table": {"cols": ["trained on", "scored on", "questions scored", "AUC", "95 % CI", "reading"], "rows": trows},
    "data": DATA,
}

(A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False, indent=1) + "\n")
print("wrote", A / "charts.json", list(charts))
