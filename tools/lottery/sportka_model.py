"""Can the next Sportka draw be predicted from the past ones? A leakage-free model against the 6/49 baseline.

    uv run --with numpy --with pandas --with scikit-learn python tools/lottery/sportka_model.py

Reads assets/lottery/sportka.csv (first draw of each day, oldest first) and writes the "model" key of
assets/lottery/results.json.

One row per (drawing day, number), 3 715 days after a 60-day warm-up times 49 numbers. Features use only earlier
draws: draws since the number last appeared ("due"), its share in the last 10 and 50 draws and over all earlier draws
("hot"), the day of the week, the week of the year and the number itself. Train on the first 80 % of days, test on
the last 20 %. Logistic regression (standardised features) and histogram gradient boosting against a constant 6/49.
Intervals: 95 % bootstrap by drawing day (1 000 resamples of the 743 test days), for AUC and for the difference in
log loss from the baseline.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
from common import MAIN_T1, N_NUMBERS, PER_DRAW, load_sportka, write_results  # noqa: E402

SEED = 42
WARMUP = 60
N_BOOT = 1000


def features():
    df = load_sportka()
    n = len(df)
    app = np.zeros((n, N_NUMBERS), dtype=np.int8)
    for col in MAIN_T1:
        app[np.arange(n), df[col].to_numpy() - 1] = 1
    cs = np.vstack([np.zeros((1, N_NUMBERS)), np.cumsum(app, axis=0)])  # cs[t] = counts in draws < t
    t = np.arange(n)[:, None]
    base = PER_DRAW / N_NUMBERS

    def roll(w):
        lo = np.maximum(t - w, 0)
        width = t - lo
        return np.where(width > 0, (cs[t[:, 0]] - cs[lo[:, 0]]) / np.maximum(width, 1), base)

    freq_cum = np.where(t > 0, cs[:-1] / np.maximum(t, 1), base)
    gap = np.zeros((n, N_NUMBERS))
    last = np.full(N_NUMBERS, -1)
    for i in range(n):
        gap[i] = np.where(last >= 0, i - last, i + 1)
        last[app[i] == 1] = i
    dow = df["date"].map(lambda d: d.isoweekday()).to_numpy()[:, None] * np.ones((1, N_NUMBERS))
    week = df["tyden"].to_numpy()[:, None] * np.ones((1, N_NUMBERS))
    num = np.ones((n, 1)) * np.arange(1, N_NUMBERS + 1)[None, :]
    X = np.stack([gap, roll(10), roll(50), freq_cum, dow, week, num], axis=-1)[WARMUP:]
    y = app[WARMUP:]
    return X, y, df["date"].iloc[WARMUP:].to_numpy()


def logloss_rows(y, p):
    p = np.clip(p, 1e-15, 1 - 1e-15)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def main() -> None:
    X, y, dates = features()
    days = len(y)
    split = int(days * 0.8)
    Xtr, Xte = X[:split].reshape(-1, X.shape[-1]), X[split:].reshape(-1, X.shape[-1])
    ytr, yte = y[:split].ravel(), y[split:].ravel()
    base = ytr.mean()
    sc = StandardScaler().fit(Xtr)
    models = {"logistic": (LogisticRegression(max_iter=2000), True),
              "boosting": (HistGradientBoostingClassifier(random_state=SEED), False)}
    rng = np.random.default_rng(SEED)
    n_test_days = days - split
    boots = rng.integers(0, n_test_days, size=(N_BOOT, n_test_days))
    ll_base = logloss_rows(yte, np.full(len(yte), base)).reshape(n_test_days, N_NUMBERS).sum(1)
    out = {"days": days, "warmup": WARMUP, "train_days": split, "test_days": n_test_days,
           "train_from": dates[0], "test_from": dates[split], "test_to": dates[-1],
           "rows_train": len(ytr), "rows_test": len(yte), "baseline_p": base,
           "baseline_logloss": float(ll_base.sum() / len(yte)), "models": {}}
    for name, (m, scale) in models.items():
        a, b = (sc.transform(Xtr), sc.transform(Xte)) if scale else (Xtr, Xte)
        m.fit(a, ytr)
        ptr, pte = m.predict_proba(a)[:, 1], m.predict_proba(b)[:, 1]
        ll = logloss_rows(yte, pte).reshape(n_test_days, N_NUMBERS).sum(1)
        yd, pd_ = yte.reshape(n_test_days, N_NUMBERS), pte.reshape(n_test_days, N_NUMBERS)
        aucs, dll = [], []
        for idx in boots:
            aucs.append(roc_auc_score(yd[idx].ravel(), pd_[idx].ravel()))
            dll.append((ll[idx].sum() - ll_base[idx].sum()) / (len(idx) * N_NUMBERS))
        out["models"][name] = {
            "auc_train": float(roc_auc_score(ytr, ptr)), "auc_test": float(roc_auc_score(yte, pte)),
            "auc_lo": float(np.quantile(aucs, 0.025)), "auc_hi": float(np.quantile(aucs, 0.975)),
            "logloss_train": float(logloss_rows(ytr, ptr).mean()), "logloss_test": float(ll.sum() / len(yte)),
            "dlogloss": float((ll.sum() - ll_base.sum()) / len(yte)),
            "dlogloss_lo": float(np.quantile(dll, 0.025)), "dlogloss_hi": float(np.quantile(dll, 0.975))}
        print(name, out["models"][name])
    write_results("model", out)


if __name__ == "__main__":
    main()
