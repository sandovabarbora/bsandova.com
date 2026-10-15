"""Worked examples for estimate.py on made-up data (no Czech value is read; one test reads only the item labels of
concern.parquet, and is skipped where the file is absent).

    uv run --no-project --with pandas --with pyarrow --with numpy --with scipy --with statsmodels --with pytest \
        python -m pytest -q tools/priorities/test_estimate.py
"""
from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

import estimate as E


# ---- made-up panels in the layout of estimate.wave_panel

def simulate_panel(rng, beta=0.3, rho=0.0, waves=40, topics=10, sigma=0.05, spells=None):
    """log A(k, t+) = α_k + γ_t + δ_(k, half) + ρ·log A(k, t−) + β·log C(k, t) + ε; A(k, t−) is the previous wave's
    A(k, t+), as the window before a wave is the window after the one before. ε has mean-one exp."""
    alpha = rng.normal(np.log(0.05), 0.5, topics)
    gamma = rng.normal(0, 0.1, waves)
    delta = rng.normal(0, 0.1, (topics, 2))
    mu_c = rng.uniform(np.log(0.02), np.log(0.4), topics)
    logc = np.zeros((topics, waves))
    e = np.zeros(topics)
    for t in range(waves):
        e = 0.7 * e + rng.normal(0, 0.3, topics)
        logc[:, t] = mu_c + e
    loga = np.zeros((topics, waves + 1))
    loga[:, 0] = alpha / (1 - rho)
    for t in range(waves):
        eps = rng.normal(-sigma ** 2 / 2, sigma, topics)
        loga[:, t + 1] = alpha + gamma[t] + delta[:, t % 2] + rho * loga[:, t] + beta * logc[:, t] + eps
    rows = []
    for k in range(topics):
        for t in range(waves):
            sp = f"T{k}#{0 if spells is None else spells(k, t)}"
            sp_next = f"T{k}#{0 if spells is None else spells(k, t + 1)}"
            rows.append({"topic": E.TOPICS[k], "code": k, "time": 100 + t, "spell": sp, "half": t % 2,
                         "topic_half": f"{k}|{t % 2}",
                         "first_of_spell": spells is not None and t > 0 and spells(k, t) != spells(k, t - 1),
                         "c": math.exp(logc[k, t]), "c_floor": 1e-4,
                         "a_post": math.exp(loga[k, t + 1]), "a_post_floor": 1e-6,
                         "a_pre": math.exp(loga[k, t]), "a_pre_floor": 1e-6,
                         "c_next": math.exp(logc[k, t + 1]) if t + 1 < waves else np.nan, "c_next_floor": 1e-4,
                         "spell_next": sp_next if t + 1 < waves else None})
    return pd.DataFrame(rows)


# ---- recovery of a known elasticity

def test_static_ppml_recovers_known_elasticity():
    rng = np.random.default_rng(1)
    est = E.q1_targets(simulate_panel(rng, beta=0.3), E.Variant())["static"].estimate()
    assert abs(est - 0.3) < 0.03


def test_dynamic_ppml_with_jackknife_recovers_known_elasticity():
    rng = np.random.default_rng(2)
    ests = [E.q1_targets(simulate_panel(rng, beta=0.3, rho=0.5), E.Variant())["dynamic"].estimate()
            for _ in range(5)]
    assert abs(np.mean(ests) - 0.3) < 0.03


def test_ppml_matches_statsmodels_poisson_glm():
    sm = pytest.importorskip("statsmodels.api")
    rng = np.random.default_rng(3)
    X = np.column_stack([rng.normal(size=200), np.ones(200), rng.integers(0, 2, 200)])
    y = rng.poisson(np.exp(X @ np.array([0.4, 0.5, -0.3])))
    b, _ = E.fit(y.astype(float), X, np.zeros(200), np.ones(200), "poisson")
    ref = sm.GLM(y, X, family=sm.families.Poisson()).fit().params
    assert np.allclose(b, ref, atol=1e-7)


def test_q3_difference_of_two_jackknifed_equations():
    rng = np.random.default_rng(4)
    n_topics, years = 8, 30
    rows = []
    for k in range(n_topics):
        la, ls, lc = np.log(0.05), np.log(0.1), rng.normal(np.log(0.1), 0.3)
        for y in range(years):
            lc = np.log(0.1) + 0.7 * (lc - np.log(0.1)) + rng.normal(0, 0.3)
            la1 = 0.3 * np.log(0.05) + 0.6 * la + 0.5 * lc + rng.normal(-0.0005, 0.03)
            ls1 = 0.3 * np.log(0.1) + 0.6 * ls + 0.2 * lc + rng.normal(-0.0005, 0.03)
            rows.append({"topic": E.TOPICS[k], "code": k, "time": 2000 + y, "spell": f"T{k}",
                         "cbar": math.exp(lc), "cbar_floor": np.nan, "a": math.exp(la), "a_floor": 1e-6,
                         "a_next": math.exp(la1), "a_next_floor": 1e-6, "s": math.exp(ls), "s_floor": np.nan,
                         "s_next": math.exp(ls1), "s_next_floor": np.nan})
            la, ls = la1, ls1
    target = E.q3_target(pd.DataFrame(rows), E.Variant(topics=E.TOPICS))["dynamic"]
    assert abs(target.estimate() - 0.3) < 0.05
    assert E.boot_pvalue(target, 0.3, E.webb_weights(999)) > 0.05


# ---- the split-panel jackknife and a Nickell-type bias

def test_jackknife_reduces_nickell_bias_of_lagged_outcome():
    """Fixed effects with a lagged outcome over eight periods bias ρ̂ downwards by about (1 + ρ)/(T − 1); the
    split-panel jackknife removes the first-order term."""
    rng = np.random.default_rng(5)
    units, T, rho = 60, 8, 0.5
    full, jk = [], []
    for _ in range(25):
        alpha = rng.normal(0, 0.5, units)
        ly = alpha / (1 - rho) + rng.normal(0, 0.3, units)
        lag, y, unit, time = [], [], [], []
        for t in range(T):
            new = alpha + rho * ly + rng.normal(-0.045, 0.3, units)
            lag.append(ly)
            y.append(np.exp(new))
            unit.append(np.arange(units))
            time.append(np.full(units, t))
            ly = new
        lag, y, unit, time = map(np.concatenate, (lag, y, unit, time))
        spec = E.Spec(y, lag, np.zeros((len(y), 0)), (unit.astype(str), time.astype(str)), unit % E.NT, time)
        full.append(E.Equation(spec, False).estimate())
        jk.append(E.Equation(spec, True).estimate())
    bias_full, bias_jk = np.mean(full) - rho, np.mean(jk) - rho
    assert bias_full < -0.08
    assert abs(bias_jk) < 0.5 * abs(bias_full)


def test_halves_even_and_odd():
    even = E.halves(np.repeat(np.arange(6), 2), True)
    assert [c for c, _ in even] == [2.0, -0.5, -0.5]
    assert even[1][1].sum() == 6 and even[2][1].sum() == 6
    odd = E.halves(np.arange(5), True)
    assert [c for c, _ in odd] == [2.0, -0.25, -0.25, -0.25, -0.25]
    assert [m.sum() for _, m in odd[1:]] == [2, 3, 3, 2]
    assert sum(c for c, _ in odd) == pytest.approx(1.0)


# ---- spells (§2.4)

def toy_concern_table():
    """Six waves; Health's item changes at EB65; Economy's label only changes wording at EB64 (no new spell)."""
    dates = {62: ("2004-10", "2004-11"), 63: ("2005-05", "2005-06"), 64: ("2006-04-01", "2006-04-20"),
             65: ("2006-10-01", "2006-10-20"), 66: ("2007-04-01", "2007-04-20"), 67: ("2007-10-01", "2007-10-20")}
    rows = []
    for w, (s, e) in dates.items():
        labels = {"Health": "Healthcare system" if w < 65 else "Health and social security",
                  "Economy": "Economic situation" if w < 64 else "The economic situation",
                  "Pensions": "Pensions", "DK": "DK"}
        for i, lab in enumerate(labels.values()):
            rows.append({"wave": w, "sheet": "S", "arm": "all", "item": lab, "share": 0.1 * (i + 1),
                         "share_dash": False, "count_weighted": 0.0, "czech_n": 1000.0, "fieldwork_start": s,
                         "fieldwork_end": e, "net_row": False})
    return pd.DataFrame(rows)


def test_spells_from_item_lists():
    con = E.concern_from_table(toy_concern_table())
    assert con.starts["Health"] == {65}
    assert con.starts["Economy"] == set()
    assert con.spell["Health", 64] != con.spell["Health", 65]
    assert con.share["Pensions", 62] == pytest.approx(0.3)
    assert con.floor[62] == pytest.approx(0.0005)
    assert con.dates[62] == (date(2004, 10, 1), date(2004, 11, 30))


def test_no_lag_across_a_spell_change():
    con = E.concern_from_table(toy_concern_table())
    days = pd.date_range("2004-01-01", "2008-12-31", freq="D")
    rng = np.random.default_rng(6)
    speeches = pd.DataFrame({"date": np.repeat(days, 3), "value": 100.0,
                             "topic": rng.integers(-1, E.NT, 3 * len(days))})
    corp = E.Corpus.from_speeches(speeches, (date(2004, 1, 1), date(2008, 12, 31)))
    wins = E.windows(con.dates)
    panel = E.wave_panel(con, corp, wins, E.covered_waves(wins, corp.span))
    v = E.Variant()
    q1 = E.q1_targets(panel, v)
    pairs = lambda t: set(zip(t.eqs[0][1].spec.cluster, t.eqs[0][1].spec.time))
    health = E.TOPICS.index("Health")
    assert (health, 65) in pairs(q1["static"])
    assert (health, 65) not in pairs(q1["dynamic"])      # its lag would be the window paired with EB64
    assert (health, 66) in pairs(q1["dynamic"])
    q1r = E.q1r_targets(panel, v)
    assert (health, 64) in pairs(q1r["static"])
    assert (health, 64) not in pairs(q1r["dynamic"])     # C(EB64) as the lag of C(EB65)
    economy = E.TOPICS.index("Economy")
    assert (economy, 64) in pairs(q1["dynamic"])


def test_yearly_mean_stays_within_one_spell():
    con = E.concern_from_table(toy_concern_table())
    val, sp = E.cbar(con, "Health", 2006)                # EB64 (old list) and EB65 (new list)
    assert sp == con.spell["Health", 65]
    assert val == pytest.approx(con.share["Health", 65])
    val, _ = E.cbar(con, "Pensions", 2006)
    assert val == pytest.approx(0.3)


def test_registered_spells_hold_on_real_item_labels():
    path = E.D / "concern.parquet"
    if not path.exists():
        pytest.skip("concern.parquet not present")
    labels = pd.read_parquet(path, columns=["wave", "arm", "item", "net_row"])
    E.registered_spells_hold(E.item_lists(labels, "A"))   # labels only; no share is read
    items_b = E.item_lists(labels, "B")
    assert ("Housing", 75) not in items_b                 # arm B of EB74–76 had no housing item


def test_unknown_item_label_stops():
    df = toy_concern_table()
    df.loc[0, "item"] = "Something new"
    with pytest.raises(ValueError):
        E.concern_from_table(df)


# ---- windows (§4)

def test_windows_on_a_toy_calendar():
    dates = {1: (date(2020, 1, 10), date(2020, 1, 20)), 2: (date(2020, 3, 1), date(2020, 3, 10)),
             3: (date(2020, 12, 1), date(2020, 12, 5))}
    w = E.windows(dates)
    assert w[1]["after"] == (date(2020, 1, 21), date(2020, 2, 29))       # cut at the day before wave 2
    assert w[1]["before"] == (date(2019, 12, 1), date(2020, 1, 9))       # same 40 days
    assert w[2]["after"] == (date(2020, 3, 11), date(2020, 9, 8))        # 182 days
    assert (w[2]["after"][1] - w[2]["after"][0]).days + 1 == 182
    assert w[3]["after"] == (date(2020, 12, 6), date(2021, 6, 5))        # no next wave
    assert E.covered_waves(w, (date(2019, 6, 1), date(2020, 12, 31))) == [1, 2]       # wave 3's after: 26 of 182
    assert E.covered_waves(w, (date(2019, 12, 5), date(2021, 12, 31))) == [1, 3]      # 36 of 40 days is 90 %
    year = E.windows(dates, 365, cap=False)
    assert year[1]["after"] == (date(2020, 1, 21), date(2021, 1, 19))
    assert E.parse_day("2004-12", True) == date(2004, 12, 31)
    assert E.parse_day("2004-02", True) == date(2004, 2, 29)


def test_window_shares_and_floor():
    days = pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"])
    sp = pd.DataFrame({"date": days, "value": [100.0, 300.0, 600.0], "topic": [0, 1, -1]})
    corp = E.Corpus.from_speeches(sp, (date(2020, 1, 1), date(2020, 1, 31)))
    s, f = corp.shares(date(2020, 1, 1), date(2020, 1, 2))
    assert s[0] == pytest.approx(0.25) and s[1] == pytest.approx(0.75) and f == pytest.approx(0.5 / 400)
    s, _ = corp.shares(date(2020, 1, 1), date(2020, 1, 31))
    assert s[0] == pytest.approx(0.1) and s[2] == 0


def test_government_of_a_wave():
    assert E.wave_government((date(2017, 11, 15), date(2018, 3, 12))) == "Babiš"
    assert E.wave_government((date(2015, 6, 1), date(2015, 11, 1))) == "Sobotka"
    assert E.wave_government((date(2010, 6, 1), date(2010, 11, 1))) is None


# ---- labels (§5)

@pytest.mark.parametrize("ci90, ci95, expected", [
    ((-0.20, 0.05), (-0.30, 0.10), "underpowered"),
    ((0.11, 0.35), (0.10, 0.40), "underpowered"),                # above 0.10, but checked first
    ((-math.inf, 0.05), (-math.inf, 0.10), "underpowered"),      # unbounded
    ((-0.05, 0.08), (-0.07, 0.10), "not supported"),
    ((-0.10, 0.10), (-0.12, 0.12), "not supported"),             # within ±0.10, bounds included
    ((0.15, 0.30), (0.12, 0.33), "supported"),
    ((0.05, 0.20), (0.02, 0.22), "positive, possibly small"),
    ((0.12, 0.25), (0.10, 0.27), "positive, possibly small"),    # 95 % not wholly above 0.10
    ((-0.05, 0.12), (-0.07, 0.14), "inconclusive"),
    ((0.0, 0.15), (-0.01, 0.17), "inconclusive"),
])
def test_label_rules(ci90, ci95, expected):
    assert E.label(ci90, ci95) == expected


def test_static_and_dynamic_must_agree_and_wider_interval_is_used():
    assert E.combined("supported", "supported") == "supported"
    assert E.combined("supported", "inconclusive") == "model-dependent"
    assert E.wider((0.1, 0.2), (0.0, 0.3)) == (0.0, 0.3)
    assert E.wider((0.1, math.inf), (0.0, 0.3)) == (0.1, math.inf)


# ---- inference

def null_panel(rng, beta, waves=12):
    return simulate_panel(rng, beta=beta, waves=waves, sigma=0.3)


def test_randomisation_interval_covers_on_a_null():
    """Topic series exchangeable and the sharp null true at β0: rejection at 10 % about 10 %, so the 90 %
    interval covers β0 about 90 % of the time."""
    rng = np.random.default_rng(7)
    perms, exact = E.permutations(10, 499, seed=8)
    rejections = []
    for i in range(150):
        beta = 0.0 if i % 2 else 0.2
        t = E.q1_targets(null_panel(rng, beta), E.Variant())["static"]
        ri = E.Randomisation(t, perms, exact)
        rejections.append(ri.pvalue(beta) <= 0.10)
    assert 0.04 <= np.mean(rejections) <= 0.17


def test_randomisation_interval_contains_truth_iff_not_rejected():
    rng = np.random.default_rng(9)
    perms, exact = E.permutations(10, 499, seed=10)
    t = E.q1_targets(null_panel(rng, 0.0, waves=16), E.Variant())["static"]
    ri = E.Randomisation(t, perms, exact)
    lo, hi = E.invert(ri.pvalue, t.estimate(), 0.10)
    assert lo < t.estimate() < hi
    assert (lo <= 0 <= hi) == (ri.pvalue(0.0) > 0.10)


def test_all_permutations_when_few_topics():
    perms, exact = E.permutations(8, 100_000)
    assert exact and len(perms) == math.factorial(8)
    perms, exact = E.permutations(10, 1000, seed=1)
    assert not exact and perms.shape == (1000, 10)
    assert (np.sort(perms, axis=1) == np.arange(10)).all()


def test_wild_bootstrap_size_on_a_null():
    rng = np.random.default_rng(11)
    W = E.webb_weights(999, seed=12)
    rej = []
    for _ in range(120):
        t = E.q1_targets(null_panel(rng, 0.1, waves=16), E.Variant())["static"]
        rej.append(E.boot_pvalue(t, 0.1, W) <= 0.10)
    assert 0.03 <= np.mean(rej) <= 0.20


def test_full_inference_record_on_made_up_data():
    rng = np.random.default_rng(13)
    t = E.q1_targets(simulate_panel(rng, beta=0.4, waves=18, sigma=0.05), E.Variant())["static"]
    out = E.intervals(t, E.webb_weights(499, seed=14), n_perms=999)
    for kind in ("wild", "randomisation", "used"):
        lo, hi = out[kind]["90"]
        assert lo < out["estimate"] < hi
        assert out[kind]["95"][0] <= lo and out[kind]["95"][1] >= hi
    for lvl in ("90", "95"):
        assert E.width(out["used"][lvl]) == max(E.width(out["wild"][lvl]), E.width(out["randomisation"][lvl]))
    assert out["label"] == E.label(out["used"]["90"], out["used"]["95"])


def test_webb_weights_six_points():
    W = E.webb_weights(5000, seed=1)
    assert set(np.round(np.unique(W), 6)) == set(np.round(E.WEBB, 6))
    assert abs(W.mean()) < 0.03 and abs((W ** 2).mean() - 1) < 0.03


# ---- the whole study on fake tables with the real schemas (no real file is read)

CAPS = ("Macroeconomics", "Labor", "Health", "Social Welfare", "Education", "Law and Crime", "Immigration", "Housing",
        "Environment", "Energy", "Defense", "International Affairs", "Agriculture", "Culture", "Transportation")
SCHEDULE = {  # item label: (first wave, last wave), as the Volume A item lists run
    "Economic situation": (62, 97), "The economic situation": (98, 104), "Rising prices/inflation": (62, 82),
    "Rising prices/ inflation/ cost of living": (83, 104), "Taxation": (62, 103), "Government debt": (77, 104),
    "Unemployment": (62, 104), "Healthcare system": (62, 76), "Health and social security": (77, 92),
    "Health": (93, 104), "Pensions": (62, 102), "The educational system": (62, 76),
    "The education system": (77, 104), "Crime": (62, 104), "Immigration": (62, 104), "Housing": (62, 104),
    "Protecting the environment": (62, 71), "Energy related issues": (66, 70), "Energy": (71, 76),
    "The environment": (72, 76), "The environment, climate and energy issues": (77, 92),
    "The environment and climate change": (93, 102), "Energy supply": (93, 102),
    "The environment and risks related to climate change": (103, 104), "Defence/Foreign affairs": (62, 76),
    "Terrorism": (62, 102), "The international situation": (97, 104), "Security and defence": (103, 104),
    "Russia’s invasion of Ukraine": (103, 104), "Threats to democracy": (103, 104),
    "The conflict in the Middle East": (104, 104), "DK": (62, 104), "Other (SPONTANEOUS)": (62, 104)}


def fake_tables(root, rng):
    import json as _json
    import zipfile as _zip
    import prepare
    d = root / "tools/data/priorities"
    for sub in ("eurostat", "parlacap", "psp_topics", "validation"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    rows = []
    for w in range(62, 105):
        s, e = prepare.FIELDWORK[w]
        arms = ("A", "B") if w in (65, 92) else ("all",)
        for arm in arms:
            for lab, (a, b) in SCHEDULE.items():
                if a <= w <= b:
                    rows.append({"wave": w, "sheet": "S", "arm": arm, "item": lab,
                                 "share": round(float(rng.uniform(0, 0.4)), 2), "share_dash": False,
                                 "count_weighted": 0.0, "czech_n": 1000.0, "fieldwork_start": s,
                                 "fieldwork_end": e, "date_precision": "day", "mode_flag": False, "net_row": False})
    pd.DataFrame(rows).to_parquet(d / "concern.parquet", index=False)

    def speeches(n, lo, hi):
        days = pd.date_range(lo, hi, freq="D")
        return pd.DataFrame({"date": rng.choice(days, n), "word_count": rng.integers(20, 2000, n),
                             "CAP_category": rng.choice(CAPS + ("Mix", "Other"), n)})

    pc = speeches(40_000, "2013-11-25", "2023-07-26")
    pc["speaker_role"] = rng.choice(["Regular", "Chairperson", "Guest"], len(pc), p=[0.7, 0.2, 0.1])
    pc["party_status"] = np.where(pc.speaker_role == "Guest", "-", rng.choice(["Coalition", "Opposition"], len(pc)))
    pc["id"] = [f"pc{i}" for i in range(len(pc))]
    pc["date"] = pc.date.dt.strftime("%Y-%m-%d")
    with _zip.ZipFile(d / "parlacap/ParlaCAP-CZ_speeches.tsv.zip", "w") as z:
        z.writestr("x_ParlaCAP-CZ_speeches.tsv", pc.to_csv(sep="\t", index=False))
    kept = pc[(pc.speaker_role != "Chairperson") & ~pc.CAP_category.isin(["Mix", "Other"])]
    pd.DataFrame({"id": kept.id, "date": pd.to_datetime(kept.date), "term": "2013-2017",
                  "speaker_role": kept.speaker_role, "speaker_MP": "yes",
                  "party_status": kept.party_status.replace("-", np.nan), "CAP_category": kept.CAP_category,
                  "CAP_prob": 0.9, "word_count": kept.word_count}).to_parquet(d / "attention.parquet", index=False)

    ps = speeches(60_000, "2004-01-14", "2026-10-14")
    ps["id"] = [f"ps{i}" for i in range(len(ps))]
    ps["chair"] = rng.random(len(ps)) < 0.2
    pd.DataFrame({"id": ps.id, "term": "2002ps", "sitting": 1, "date": ps.date, "chair": ps.chair,
                  "word_count": ps.word_count}).to_parquet(d / "psp_speeches.parquet", index=False)
    top = np.where(ps.CAP_category == "Mix", rng.choice(CAPS, len(ps)), ps.CAP_category)
    for i, part in enumerate(np.array_split(np.arange(len(ps)), 3)):
        pd.DataFrame({"id": ps.id.to_numpy()[part], "CAP_category": ps.CAP_category.to_numpy()[part],
                      "CAP_top": top[part], "CAP_prob": np.float32(0.7)}).to_parquet(d / f"psp_topics/part-x-{i:03d}.parquet")

    codes = sorted({c for cs in E.COFOG.values() for c in cs})
    sp = [{"year": y, "cofog": c, "value": float(rng.uniform(1000, 5000)), "status": ""}
          for y in range(1995, 2025) for c in codes]
    sp += [{"year": y, "cofog": "TOTAL", "value": 100_000.0, "status": ""} for y in range(1995, 2025)]
    pd.DataFrame(sp).to_parquet(d / "spending.parquet", index=False)
    for name in ("une_rt_a_CZ", "demo_pjanind_CZ"):
        yrs = list(range(2000, 2026))
        (d / f"eurostat/{name}.json").write_text(_json.dumps({
            "id": ["freq", "time"], "size": [1, len(yrs)],
            "dimension": {"time": {"category": {"index": {str(y): i for i, y in enumerate(yrs)}}}},
            "value": {str(i): float(rng.uniform(3, 30)) for i in range(len(yrs))}}))

    keys = [f"S{i:03d}" for i in range(120)]
    sample = pd.DataFrame({"id": keys, "label": rng.choice(CAPS + ("Mix", "Other"), 120),
                           "word_count": rng.integers(50, 2000, 120), "stratum": "x",
                           "pi": rng.uniform(0.001, 0.5, 120), "source": ["parlacap"] * 100 + ["psp_2004_2013"] * 20,
                           "key": keys})
    sample.to_parquet(d / "validation/sample.parquet")
    for model in ("sonnet", "opus"):
        (d / f"validation/coding-{model}-01.json").write_text(_json.dumps(
            [{"key": k, "topic": str(rng.choice(CAPS + ("Other",))), "confidence": "high"} for k in keys]))
    (d / "validation/adjudication-assistant.json").write_text(_json.dumps({k: "Other" for k in keys}))
    (d / "validation/adjudication-author.json").write_text(_json.dumps({}))
    val = {f: {"by_topic": {t: {"f1": float(rng.uniform(0.3, 0.9))} for t in E.TOPICS}, "macro_f1": 0.7}
           for f in ("parlacap", "psp_2004_2013")}
    (root / "validation.json").write_text(_json.dumps(val))


def test_whole_study_runs_on_fake_tables(tmp_path, monkeypatch):
    fake_tables(tmp_path, np.random.default_rng(15))
    monkeypatch.setattr(E, "D", tmp_path / "tools/data/priorities")
    monkeypatch.setattr(E, "VALIDATION", tmp_path / "validation.json")
    monkeypatch.setattr(E, "BOOT", 99)
    monkeypatch.setattr(E, "PERMS", 99)
    res = E.clean(E.run())
    labels = set(E.label((0, 1), (0, 1)) for _ in [0]) | {"not supported", "supported", "positive, possibly small",
                                                         "inconclusive", "model-dependent"}
    for s in ("parlacap", "whole"):
        for q in ("Q1", "Q1r", "Q3"):
            assert res["primary"][s][q]["label"] in labels
    assert res["primary"]["spending"]["Q2"]["label"] in labels
    assert res["data"]["parlacap"]["waves"] == list(range(81, 99))     # both windows covered by ParlaCAP
    assert res["data"]["whole"]["waves"] == list(range(62, 104))
    ri = res["primary"]["spending"]["Q2"]["static"]["randomisation"]
    assert ri["permutations"] == 99 and not ri["all_permutations"]          # 8! > 99 here; 8! <= 100 000 in the study
    assert set(res["q4"]["government"]["parlacap"]) == {"Sobotka", "Babiš", "Fiala"}
    assert res["q4"]["government"]["whole"]["Fiala"]["periods"] == list(range(96, 104))
    assert "unemployment_and_old_age_dependency_controls" in res["checks"]["spending"]
    assert res["data"]["spell_starts"]["Environment and energy"] == [66, 71, 72, 77, 93, 103]

    def errors(o, path=""):
        if isinstance(o, dict):
            if "error" in o:
                yield path, o["error"]
            for k, v in o.items():
                yield from errors(v, f"{path}/{k}")
    assert list(errors(res)) == []
