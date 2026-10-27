"""Agreement, the scene bootstrap, the estimands, the readings and the power formulas (design §1, §4, §5), on
invented jokes only."""
from __future__ import annotations

import math

import config as C
import numpy as np
import pytest
import stats as T


def joke(first, target="character", butt="speaker", gtype="", kind="joke", last=None):
    return {"first_cue": first, "last_cue": first if last is None else last, "kind": kind, "target": target,
            "group_type": gtype, "group_other": "dentists" if gtype == "other" else "", "butt": butt}


# ---------------------------------------------------------------- kappa and the per-cue mapping

def test_kappa_perfect_agreement_is_one_and_textbook_table_is_point_four():
    assert T.kappa(["a", "b", "a", "c"], ["a", "b", "a", "c"]) == pytest.approx(1.0)
    a = ["y"] * 25 + ["n"] * 25
    b = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15        # po 0.7, pe 0.5
    assert T.kappa(a, b) == pytest.approx(0.4)


def test_kappa_at_chance_is_zero_and_below_chance_is_negative():
    a = ["y", "y", "n", "n"]
    assert T.kappa(a, ["y", "n", "y", "n"]) == pytest.approx(0.0)
    assert T.kappa(a, ["n", "n", "y", "y"]) == pytest.approx(-1.0)


def test_kappa_is_undefined_without_cues_or_without_variation_and_needs_pairs():
    assert T.kappa([], []) is None
    assert T.kappa(["a", "a"], ["a", "a"]) is None
    assert T.kappa([True, False], [False, False]) == pytest.approx(0.0)
    with pytest.raises(ValueError, match="paired"):
        T.kappa(["a"], [])


def test_a_cue_takes_the_codes_of_the_joke_starting_first_then_the_shortest():
    jokes = [joke(3, "genre", last=6), joke(3, "america", last=4), joke(2, "group", "group", "race", last=5)]
    codes = T.cue_codes(jokes, [1, 2, 3, 4, 6, 7])
    assert codes[1] == {"joke": False} and codes[7] == {"joke": False}
    assert codes[2]["target"] == codes[3]["target"] == codes[4]["target"] == "group"
    assert codes[6]["target"] == "genre"
    assert T.cue_codes([joke(3, "genre", last=6), joke(3, "america", last=4)], [4])[4]["target"] == "america"


def test_agreement_reports_detection_on_all_cues_and_codes_on_shared_jokes():
    x = {1: {"joke": True, "target": "genre", "butt": "group"}, 2: {"joke": False}, 3: {"joke": True, "target":
         "america", "butt": "speaker"}, 4: {"joke": False}}
    y = {1: {"joke": True, "target": "genre", "butt": "group"}, 2: {"joke": True, "target": "genre", "butt": "group"},
         3: {"joke": True, "target": "america", "butt": "speaker"}, 4: {"joke": False}}
    a = T.agreement(x, y, [1, 2, 3, 4])
    assert a["detection"]["percent_agreement"] == 75 and a["codes"]["cues"] == 2
    assert a["codes"]["kappa_target"] == pytest.approx(1.0) and a["codes"]["kappa_butt"] == pytest.approx(1.0)


def human(film, cue, j, target=None, butt=None):
    h = {"film": film, "cue": cue, "joke": j}
    if j is True:
        h.update(target=target, group_type="", group_other="", butt=butt)
    return h


def test_validation_separates_detection_from_codes_and_leaves_skips_out():
    model = {("pp1", 1): {"joke": True, "target": "genre", "butt": "group"},
             ("pp1", 2): {"joke": True, "target": "america", "butt": "speaker"},
             ("pp1", 3): {"joke": False}, ("pp2", 1): {"joke": True, "target": "character", "butt": "group"},
             ("pp2", 2): {"joke": False}, ("pp2", 3): {"joke": True, "target": "genre", "butt": "speaker"}}
    hum = [human("pp1", 1, True, "genre", "group"), human("pp1", 2, True, "america", "speaker"),
           human("pp1", 3, False), human("pp2", 1, True, "character", "group"), human("pp2", 2, True, "genre", "group"),
           human("pp2", 3, C.SKIP)]
    v = T.validation(model, hum, reps=200)
    assert v["skipped"] == 1 and v["coded"] == 5 and v["cues"] == 6
    d = v["detection"]
    assert d["percent_agreement"] == 80 and d["author_joke_cues"] == 4 and d["model_joke_cues"] == 3
    assert d["share_of_author_jokes_found_by_model"] == 0.75 and d["share_of_model_jokes_marked_by_author"] == 1.0
    assert v["codes"]["cues"] == 3 and v["codes"]["kappa_target"] == pytest.approx(1.0)
    assert v["status"] == "Registered study"


def test_the_gate_needs_both_kappas_at_least_point_six():
    def run(butts_model):
        targets = ["genre", "america", "character", "genre", "america", "character"]
        butts = ["group", "speaker", "unclear", "group", "speaker", "unclear"]
        model = {("pp1", k): {"joke": True, "target": t, "butt": b} for k, (t, b) in enumerate(zip(targets, butts_model,
                                                                                                    strict=True))}
        hum = [human("pp1", k, True, t, b) for k, (t, b) in enumerate(zip(targets, butts, strict=True))]
        return T.validation(model, hum, reps=50)
    assert run(["group", "speaker", "unclear", "group", "speaker", "unclear"])["status"] == "Registered study"
    low = run(["speaker", "group", "unclear", "group", "speaker", "unclear"])
    assert low["codes"]["kappa_butt"] < 0.6 and low["status"] == "Exploratory"
    assert T.validation({("pp1", 0): {"joke": False}}, [human("pp1", 0, False)], reps=10)["status"] == "Exploratory"


def test_kappa_interval_is_seeded_and_counts_undefined_draws():
    pairs = [("genre", "genre", "group", "group"), ("america", "america", "speaker", "group"),
             ("genre", "america", "speaker", "speaker"), ("character", "character", "unclear", "unclear")] * 3
    a, b = T.kappa_interval(pairs, reps=300), T.kappa_interval(pairs, reps=300)
    assert a == b and a["kappa_target"][0] <= a["kappa_target"][1] <= 1
    same = T.kappa_interval([("genre", "genre", "group", "group")] * 4, reps=20)
    assert same["kappa_target"] is None and same["dropped_target"] == 20
    assert T.kappa_interval([], reps=5)["dropped_butt"] == 5


# ---------------------------------------------------------------- scene tables

SCENE_OF = {1: 1, 2: 1, 3: 2, 4: 3, 5: 3}


def test_scene_table_counts_by_scene_of_the_first_cue():
    jokes = [joke(1, "america"), joke(2, "group", "group", "weight", last=3), joke(3, "group", "speaker", "race"),
             joke(4, "group", "unclear", "gender", kind="allusion"), joke(5, "group", "group", "other")]
    t = T.scene_table(jokes, [0.1, 0.2, 0.3], SCENE_OF)
    col = dict(zip(T.COLS, t.sum(axis=0), strict=True))
    assert t[:, T.COLS.index("jokes")].tolist() == [2, 1, 2]
    assert col == {"jokes": 5, "america": 1, "protected": 3, "speaker": 1, "group": 1, "unclear": 1, "wnpt": 1,
                   "hours": pytest.approx(0.6)}


def test_the_variants_of_the_checks():
    jokes = [joke(1, "group", "unclear", "race"), joke(3, "group", "group", "other"),
             joke(4, "genre", kind="allusion"), joke(5, "group", "group", "religion", kind="allusion")]
    as_group = T.scene_table(jokes, [1, 1, 1], SCENE_OF, T.Variant(unclear_as="group")).sum(0)
    assert as_group[T.COLS.index("wnpt")] == 2 and as_group[T.COLS.index("unclear")] == 0
    as_speaker = T.scene_table(jokes, [1, 1, 1], SCENE_OF, T.Variant(unclear_as="speaker")).sum(0)
    assert as_speaker[T.COLS.index("speaker")] == 1 and as_speaker[T.COLS.index("wnpt")] == 1
    wide = T.scene_table(jokes, [1, 1, 1], SCENE_OF, T.Variant(protected=C.GROUP_TYPES)).sum(0)
    assert wide[T.COLS.index("protected")] == 3
    no_allusions = T.scene_table(jokes, [1, 1, 1], SCENE_OF, T.Variant(kinds=("joke",))).sum(0)
    assert no_allusions[T.COLS.index("jokes")] == 2
    runtime = T.scene_table(jokes, [0.1, 0.1, 0.1], SCENE_OF, T.Variant(hours="runtime"), runtime_hours=1.5)
    assert runtime[:, T.COLS.index("hours")].sum() == pytest.approx(1.5)


# ---------------------------------------------------------------- the bootstrap

def table(rows):
    return np.array(rows, dtype=float)


def films(n1=6, n2=8):
    rng = np.random.default_rng(0)
    out = {}
    for f, n in (("pp1", n1), ("pp2", n2)):
        jokes = rng.integers(1, 6, n)
        am = np.minimum(jokes, rng.integers(0, 3, n))
        prot = np.minimum(jokes - am, rng.integers(0, 2, n))
        sp = rng.integers(0, 2, n) * prot
        gr = prot - sp
        out[f] = np.column_stack([jokes, am, prot, sp, gr, np.zeros(n), gr, rng.uniform(0.01, 0.05, n)])
    return out


def test_the_bootstrap_resamples_scenes_with_one_generator_pp1_then_pp2_per_replicate():
    tabs = films()
    got = T.bootstrap_totals(tabs, reps=50, seed=42)
    rng = np.random.default_rng(42)
    for b in range(50):
        for f in C.FILMS:
            idx = rng.integers(0, len(tabs[f]), len(tabs[f]))
            assert np.allclose(got[f][b], tabs[f][idx].sum(0))


def test_a_scene_drawn_twice_counts_twice_and_jokeless_scenes_add_hours():
    tabs = {"pp1": table([[0, 0, 0, 0, 0, 0, 0, 1.0], [2, 1, 0, 0, 0, 0, 0, 1.0]]), "pp2": table([[1, 1, 0, 0, 0, 0, 0, 1]])}
    tot = T.bootstrap_totals(tabs, reps=200, seed=1)["pp1"]
    assert set(tot[:, 0]) <= {0, 2, 4} and np.all(tot[:, -1] == 2.0)


def test_statistics_point_values_and_nan_without_a_denominator():
    tot = {"pp1": np.array([10, 2, 4, 3, 1, 0, 1, 2.0]), "pp2": np.array([20, 8, 0, 0, 0, 0, 0, 4.0])}
    s = T.statistics(tot)
    assert s["share_america_pp1"] == 0.2 and s["share_america_pp2"] == 0.4 and s["delta1"] == pytest.approx(0.2)
    assert s["D_pp1"] == 0.5 and s["share_speaker_pp1"] == 0.75 and math.isnan(s["D_pp2"])
    assert math.isnan(s["D_diff"]) and s["rate_wnpt_pp1"] == 0.5 and s["delta3"] == -0.5
    assert s["rate_america_pp2"] == 2.0


def test_denominator_free_draws_are_dropped_counted_and_make_a_question_indeterminate():
    # one protected joke in one of 20 scenes of PP1: about (19/20)^20 = 36 % of replicates have none
    rows = [[1, 0, 0, 0, 0, 0, 0, 0.01]] * 19 + [[1, 0, 1, 1, 0, 0, 0, 0.01]]
    tabs = {"pp1": table(rows), "pp2": films()["pp2"]}
    est = T.estimate(tabs, reps=2000, seed=42)
    d = est["D_pp1"]
    assert 0.30 < d["dropped"] / 2000 < 0.42 and d["indeterminate"]
    assert d["estimate"] == 1.0 and d["ci95"] == [1.0, 1.0]
    assert est["D_diff"]["dropped"] >= d["dropped"] and not est["delta1"]["indeterminate"]
    assert T.read_q2(d, "pp1", 1)["label"] == "indeterminate"


def test_exactly_five_percent_dropped_is_still_determinate():
    s = T.summarise({"x": np.array(0.5)}, {"x": np.array([np.nan] * 5 + [0.5] * 95)})["x"]
    assert s["dropped"] == 5 and not s["indeterminate"]
    s = T.summarise({"x": np.array(0.5)}, {"x": np.array([np.nan] * 6 + [0.5] * 94)})["x"]
    assert s["indeterminate"]


def test_the_interval_is_numpys_default_quantile_of_the_kept_replicates():
    tabs = films()
    est = T.estimate(tabs, reps=400, seed=42)
    boot = T.statistics(T.bootstrap_totals(tabs, reps=400, seed=42))["delta1"]
    assert est["delta1"]["ci95"] == pytest.approx(list(np.quantile(boot, [0.025, 0.975])))
    assert est["delta1"]["estimate"] == pytest.approx(
        tabs["pp2"][:, 1].sum() / tabs["pp2"][:, 0].sum() - tabs["pp1"][:, 1].sum() / tabs["pp1"][:, 0].sum())


def test_a_film_without_scenes_cannot_be_bootstrapped():
    with pytest.raises(ValueError, match="no scene"):
        T.bootstrap_totals({"pp1": np.zeros((0, len(T.COLS))), "pp2": films()["pp2"]}, reps=2)


# ---------------------------------------------------------------- readings

def summ(est, lo, hi, ind=False):
    return {"estimate": est, "ci95": [lo, hi], "dropped": 0, "replicates": 10000, "indeterminate": ind}


def test_an_end_exactly_at_zero_does_not_exclude_it():
    assert T.side([0.0, 0.3]) == "includes" and T.side([-0.2, 0.0]) == "includes"
    assert T.side([0.01, 0.3]) == "above" and T.side([-0.3, -0.01]) == "below" and T.side(None) == "includes"


def test_q1_readings_and_sentences():
    up = T.read_q1(summ(0.12, 0.03, 0.2), 8.9)
    assert up["label"] == "supported" and "12.0 pp more (95 % CI 3.0 to 20.0, bootstrap by scene)" in up["sentence"]
    down = T.read_q1(summ(-0.12, -0.2, -0.03), 8.9)
    assert down["label"] == "not supported" and "12.0 pp fewer" in down["sentence"]
    flat = T.read_q1(summ(0.02, 0.0, 0.1), 8.94)
    assert flat["label"] == "inconclusive" and "A difference of about 8.9 pp would have been detected" in flat["sentence"]
    assert T.read_q1(summ(0.02, -0.1, 0.1, ind=True), 8.9) == {"label": "indeterminate", "sentence": None}


def test_q2_readings_per_film():
    assert T.read_q2(summ(0.6, 0.2, 0.9), "pp1", 30)["sentence"].startswith(
        "In Pitch Perfect, jokes on protected traits more often laugh at the speaker")
    assert "laugh at the group than at the speaker: D = -60.0 pp (95 % CI -90.0 to -20.0)." in T.read_q2(
        summ(-0.6, -0.9, -0.2), "pp2", 30)["sentence"]
    assert T.read_q2(summ(0.1, -0.3, 0.5), "pp2", 30)["label"] == "inconclusive"
    assert T.read_q2(summ(None, None, None), "pp1", 0) == {"label": "no protected-trait joke found", "sentence": None}


def test_q3_readings():
    assert T.read_q3(summ(3.2, 1.0, 5.0))["sentence"] == ("The second film has more jokes that would not pass today "
                                                         "per hour of dialogue: 3.2 more per hour (95 % CI 1.0 to 5.0).")
    assert "The first film has more" in T.read_q3(summ(-3.2, -5, -1))["sentence"]
    assert T.read_q3(summ(1.0, -2, 4))["label"] == "inconclusive"
    assert T.read_q3(summ(1.0, -2, 4, ind=True))["label"] == "indeterminate"


# ---------------------------------------------------------------- power

@pytest.mark.parametrize("n,q1,q2,q3", [(200, 11.0, 0.69, 8.6), (300, 8.9, 0.56, 10.5), (400, 7.7, 0.49, 12.1)])
def test_the_power_formulas_reproduce_the_table_of_section_5(n, q1, q2, q3):
    film = {"jokes": n, "america": 0.15 * n, "protected": 0.10 * n, "wnpt": 0.05 * n, "hours": 1.6}
    m = T.mdd({"pp1": film, "pp2": film})
    assert round(m["q1_pp"], 1) == q1 and round(m["q2_D"]["pp1"], 2) == q2 and round(m["q3_per_hour"], 1) == q3


def test_power_without_counts_is_none_not_an_error():
    zero = {"jokes": 0, "america": 0, "protected": 0, "wnpt": 0, "hours": 0}
    m = T.mdd({"pp1": zero, "pp2": zero})
    assert "q1_pp" not in m and m["q2_D"] == {"pp1": None, "pp2": None} and "q3_per_hour" not in m


@pytest.mark.slow
def test_the_registered_ten_thousand_replicates_on_invented_films():
    tabs = films(90, 110)
    est = T.estimate(tabs)
    assert all(v["replicates"] == 10_000 for v in est.values())
    for k in ("delta1", "D_pp1", "delta3"):
        lo, hi = est[k]["ci95"]
        assert lo <= est[k]["estimate"] <= hi
    pairs = [("genre", "genre", "group", "group"), ("america", "genre", "speaker", "speaker")] * 20
    assert T.kappa_interval(pairs)["dropped_target"] < 10_000
