"""The Pitch Perfect joke study: the article, every number from docs/research/pitch-results.json.

Writes texts/pitch-perfect-jokes.html from tools/pitch_article/template.html and copies the results file to
assets/pitch-perfect-jokes/. The study code in tools/pitch is frozen at the tag pitch-code-cli-2 and is not imported.

    uv run --no-project python -I tools/pitch_article/article.py
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "site"))
from article_kit import NB, n, render

SLUG = "pitch-perfect-jokes"
RESULTS = ROOT / "docs" / "research" / "pitch-results.json"
PAGE = ROOT / "texts" / f"{SLUG}.html"
# tag objects are not in the results file, and CI checks out without tags
TAG_OBJECTS = {"pitch-design": "633276f5263ab66e7fe020ef93513f47a2dbb37b",
               "pitch-code-cli-2": "d451e25dfa59bd9fd304ecc2b9f8ff870f716cb3"}
CHECKS = [  # key in results["checks"], label in the table
    ("run_2", "run 2 in place of run 1"),
    ("unclear_as_group", "unclear butt counted as on the group"),
    ("unclear_as_speaker", "unclear butt counted as on the speaker"),
    ("scene_gap_5s", "scene gap 5 s"),
    ("scene_gap_12s", "scene gap 12 s"),
    ("full_runtime", "full runtime as Q3's denominator"),
    ("without_allusions", "without allusions"),
    ("protected_widened", "every group type counted as protected"),
]
COLUMNS = [("delta1", 100, "Q1"), ("D_pp1", 100, "Q2"), ("D_pp2", 100, "Q2"), ("delta3", 1, "Q3")]


def pp(v: float, dp: int = 1) -> str:
    return n(100 * v, dp, sign=True) + NB + "pp"


def pct(v: float, dp: int = 1) -> str:
    return n(100 * v, dp) + NB + "%"


def signed_ci(ci: list[float], scale: float = 100, dp: int = 1, unit: str = NB + "pp") -> str:
    return f"{n(scale * ci[0], dp, sign=True)} to {n(scale * ci[1], dp, sign=True)}{unit}"


def plain_ci(ci: list[float], scale: float = 100, dp: int = 1, unit: str = "") -> str:
    return f"{n(scale * ci[0], dp)} to {n(scale * ci[1], dp)}{unit}"


def reading(e: dict, question: str) -> str:
    """The registered rule of design §1: only an interval wholly on one side of zero gives a direction."""
    if e["indeterminate"]:
        return "indeterminate"
    lo, hi = e["ci95"]
    above = {"Q1": "supported", "Q2": "speaker", "Q3": "second film more"}[question]
    below = {"Q1": "not supported", "Q2": "group", "Q3": "first film more"}[question]
    return above if lo > 0 else below if hi < 0 else "inconclusive"


def checks_table(res: dict) -> str:
    rows = [("run 1, as registered", res["estimates"])] + [(lab, res["checks"][k]) for k, lab in CHECKS]
    out = []
    for lab, est in rows:
        cells = []
        for key, scale, q in COLUMNS:
            if key not in est:
                cells.append('<td class="v">–</td>')
                continue
            e, primary = est[key], res["estimates"][key]
            r = reading(e, q)
            mark = " <b>≠</b>" if r != reading(primary, q) else ""
            unit = NB + "pp" if scale == 100 else ""
            cells.append(f'<td class="v">{n(scale * e["estimate"], 1, sign=True)}<small>'
                         f'{signed_ci(e["ci95"], scale, 1, unit)}<br>{r}{mark}</small></td>')
        out.append(f'  <tr><td>{lab}</td>{"".join(cells)}</tr>')
    return "\n".join(out)


def differing(res: dict) -> list[tuple[str, str]]:
    return [(k, key) for k, _ in CHECKS for key, _, q in COLUMNS
            if key in res["checks"][k] and reading(res["checks"][k][key], q) != reading(res["estimates"][key], q)]


def agree_table(val: dict, sa: dict) -> str:
    det, codes, iv = val["detection"], val["codes"], val["codes"]["interval"]
    pd, pc = sa["pooled"]["detection"], sa["pooled"]["codes"]
    rows = [
        ("joke or not", f'κ {n(det["kappa"], 2)}<small>{val["coded"]} cues · {pct(det["percent_agreement"] / 100)} agree</small>',
         f'κ {n(pd["kappa"], 2)}<small>{n(pd["cues"])} cues · {pct(pd["percent_agreement"] / 100)} agree</small>'),
        ("target", (f'<b>κ {n(codes["kappa_target"], 2)}</b><small>{codes["cues"]} cues · 95 % CI '
                   f'{plain_ci(iv["kappa_target"], 1, 2)}</small>'),
         f'κ {n(pc["kappa_target"], 2)}<small>{n(pc["cues"])} cues</small>'),
        ("butt", (f'<b>κ {n(codes["kappa_butt"], 2)}</b><small>{codes["cues"]} cues · 95 % CI '
                 f'{plain_ci(iv["kappa_butt"], 1, 2)}</small>'),
         f'κ {n(pc["kappa_butt"], 2)}<small>{n(pc["cues"])} cues</small>'),
    ]
    return "\n".join(f'  <tr><td>{a}</td><td class="v">{b}</td><td class="v">{c}</td></tr>' for a, b, c in rows)


def num_refs(page: str, values: dict) -> str:
    """[[key]] markers become citations numbered by first appearance; every entry of refs.html must be cited."""
    refs = render((HERE / "refs.html").read_text(encoding="utf-8"), values)
    entries = dict(re.findall(r'<li data-key="([\w-]+)">(.*?)</li>', refs, re.DOTALL))
    order = list(dict.fromkeys(re.findall(r"\[\[([\w-]+)\]\]", page)))
    assert set(order) == set(entries), set(order) ^ set(entries)
    num = {k: i for i, k in enumerate(order, 1)}
    page = re.sub(r"\[\[([\w-]+)\]\]",
                  lambda m: f'<sup class="cite"><a href="#r{num[m.group(1)]}">{num[m.group(1)]}</a></sup>', page)
    return page.replace("{{refs}}", "\n".join(f'<li id="r{num[k]}">{entries[k]}</li>' for k in order))


def values(res: dict) -> dict:
    c1, c2 = res["counts"]["pp1"], res["counts"]["pp2"]
    r1, r2 = res["counts_run_2"]["pp1"], res["counts_run_2"]["pp2"]
    est, chk, rd = res["estimates"], res["checks"], res["readings"]
    val, sa, mdd = res["validation"], res["self_agreement"], res["minimum_detectable"]
    run2, aph = chk["run_2"], chk["q1_america_per_hour"]
    meta = res["meta"]

    # the text states these; fail loudly if a re-run changed them
    assert res["status"] == val["status"] == "Exploratory"
    gate = res["settings"]["kappa_gate"]
    assert val["codes"]["kappa_target"] < gate and val["codes"]["kappa_butt"] < gate
    assert val["codes"]["interval"]["kappa_target"][1] < gate < val["codes"]["interval"]["kappa_butt"][1]
    assert rd["Q1"]["label"] == rd["Q3"]["label"] == "inconclusive"
    assert rd["Q2"]["pp1"]["label"] == rd["Q2"]["pp2"]["label"] == "direction"
    assert rd["Q2"]["pp1"]["side"] == rd["Q2"]["pp2"]["side"] == "above"
    assert reading(est["delta1"], "Q1") == "inconclusive" and reading(est["delta3"], "Q3") == "inconclusive"
    assert reading(est["D_pp1"], "Q2") == reading(est["D_pp2"], "Q2") == "speaker"
    assert differing(res) == [("run_2", "D_pp1")]
    assert reading(chk["full_runtime"]["delta3"], "Q3") == "inconclusive"
    assert reading(aph["delta_rate_america"], "Q1") == "inconclusive"
    assert all(e["dropped"] == 0 and not e["indeterminate"]
               for group in [est, *chk.values()] for e in group.values())
    assert c1["failed_scenes"] == 0 and c2["failed_scenes"] == 1 and c1["failed_jokes"] == c2["failed_jokes"] == 0
    assert all(c["cleaning"]["lyric_fallback"] and c["cleaning"]["italic_runs"] == 0 for c in (c1, c2))
    assert all(c["cleaning"]["raw_cues"] - c["kept_cues"] == c["cleaning"]["cues_dropped_at_sound_and_tags"] for c in (c1, c2))
    assert c1["would_not_pass_today"] == c2["would_not_pass_today"]
    assert all(12 < 1 / est[f"share_america_{f}"]["estimate"] < 14 for f in ("pp1", "pp2"))  # "one in thirteen"
    assert all(15 <= c["protected"] <= 30 for c in (c1, c2, r1, r2))  # "about twenty"
    assert all(c["by_group_type"]["gender"] == max(c["by_group_type"].values()) for c in (c1, c2))
    assert val["cues"] == 100 and val["skipped"] == 53 and val["without_model_output"] == 0
    assert sa["pooled"]["detection"]["cues_without_model_output"] == c2["kept_cues_in_failed_scenes"]
    assert meta["tags"]["pitch-design"].startswith("81d5288") and meta["tags"]["pitch-code-cli-2"].startswith("21fa3ea")
    assert all(s["model"] == "claude-sonnet-5-5" and s["effort"] == "high" for s in meta["run_settings"])

    jokes_all = c1["jokes"] + c2["jokes"]
    v = {
        "deck": (f"A language model found {n(jokes_all)} jokes in the two films' subtitles and coded them "
                 "consistently across two runs, but it barely agreed with a human on whom they target, so every result is exploratory."),
        "jokes_all": n(jokes_all), "gate": n(gate, 1),
        "tag_design": meta["tags"]["pitch-design"], "tag_design_obj": TAG_OBJECTS["pitch-design"],
        "tag_code": meta["tags"]["pitch-code-cli-2"], "tag_code_obj": TAG_OBJECTS["pitch-code-cli-2"],
        "cli": re.search(r"\d+\.\d+\.\d+", meta["versions"]["anthropic"]).group(0),
        "v_python": meta["versions"]["python"], "v_numpy": meta["versions"]["numpy"],
        "reps": n(res["settings"]["bootstrap_replicates"]), "gap": n(res["settings"]["scene_gap_s"]),
        # data
        "raw1": n(c1["cleaning"]["raw_cues"]), "raw2": n(c2["cleaning"]["raw_cues"]),
        "cues1": n(c1["kept_cues"]), "cues2": n(c2["kept_cues"]),
        "sound1": c1["cleaning"]["cues_dropped_at_sound_and_tags"], "sound2": c2["cleaning"]["cues_dropped_at_sound_and_tags"],
        "scenes1": c1["scenes"], "scenes2": c2["scenes"], "scenes2_all": c2["scenes"] + c2["failed_scenes"],
        "failed_cues2": c2["kept_cues_in_failed_scenes"],
        "hours1": n(c1["dialogue_hours"], 2), "hours2": n(c2["dialogue_hours"], 2),
        "rt1": n(c1["runtime_hours"], 2), "rt2": n(c2["runtime_hours"], 2),
        "jokes1": c1["jokes"], "jokes2": c2["jokes"], "allus1": c1["by_kind"]["allusion"], "allus2": c2["by_kind"]["allusion"],
        "r2_jokes1": r1["jokes"], "r2_jokes2": r2["jokes"],
        "seg_diff1": abs(r1["jokes"] - c1["jokes"]), "seg_diff2": abs(r2["jokes"] - c2["jokes"]),
        "prot1": c1["protected"], "prot2": c2["protected"],
        # validation
        "val_cues": val["cues"], "skipped": val["skipped"], "coded": val["coded"],
        "det_pa": pct(val["detection"]["percent_agreement"] / 100), "det_k": n(val["detection"]["kappa"], 2),
        "a_jokes": val["detection"]["author_joke_cues"], "m_jokes": val["detection"]["model_joke_cues"],
        "found": pct(val["detection"]["share_of_author_jokes_found_by_model"], 0),
        "marked": pct(val["detection"]["share_of_model_jokes_marked_by_author"], 0),
        "code_cues": val["codes"]["cues"],
        "k_t": n(val["codes"]["kappa_target"], 2), "k_b": n(val["codes"]["kappa_butt"], 2),
        "k_t_ci": plain_ci(val["codes"]["interval"]["kappa_target"], 1, 2),
        "k_b_ci": plain_ci(val["codes"]["interval"]["kappa_butt"], 1, 2),
        "sa_t": n(sa["pooled"]["codes"]["kappa_target"], 2), "sa_b": n(sa["pooled"]["codes"]["kappa_butt"], 2),
        "sa_cues": n(sa["pooled"]["codes"]["cues"]),
        "sa_t1": n(sa["pp1"]["codes"]["kappa_target"], 2), "sa_b1": n(sa["pp1"]["codes"]["kappa_butt"], 2),
        "sa_t2": n(sa["pp2"]["codes"]["kappa_target"], 2), "sa_b2": n(sa["pp2"]["codes"]["kappa_butt"], 2),
        "sa_cues1": n(sa["pp1"]["codes"]["cues"]), "sa_cues2": n(sa["pp2"]["codes"]["cues"]),
        "agree_table": agree_table(val, sa),
        # Q1
        "am1_n": c1["america"], "am2_n": c2["america"],
        "am1": pct(est["share_america_pp1"]["estimate"]), "am1_ci": plain_ci(est["share_america_pp1"]["ci95"], unit=NB + "%"),
        "am2": pct(est["share_america_pp2"]["estimate"]), "am2_ci": plain_ci(est["share_america_pp2"]["ci95"], unit=NB + "%"),
        "d1": pp(est["delta1"]["estimate"]), "d1_ci": signed_ci(est["delta1"]["ci95"]),
        "mdd1": n(mdd["q1_pp"], 1) + NB + "pp",
        "r2_d1": pp(run2["delta1"]["estimate"]), "r2_d1_ci": signed_ci(run2["delta1"]["ci95"]),
        # Q2
        "gender1": c1["by_group_type"]["gender"], "gender2": c2["by_group_type"]["gender"],
        **{f"pb{i}_{b[0]}": c["protected_by_butt"].get(b, 0) for i, c in ((1, c1), (2, c2))
           for b in ("speaker", "group", "unclear")},
        "D1": pp(est["D_pp1"]["estimate"]), "D1_ci": signed_ci(est["D_pp1"]["ci95"]),
        "D2": pp(est["D_pp2"]["estimate"]), "D2_ci": signed_ci(est["D_pp2"]["ci95"]),
        "r2_prot1": r1["protected"], "r2_pb1_s": r1["protected_by_butt"]["speaker"], "r2_pb1_g": r1["protected_by_butt"]["group"],
        "r2_D1": pp(run2["D_pp1"]["estimate"]), "r2_D1_ci": signed_ci(run2["D_pp1"]["ci95"]),
        "r2_D2": pp(run2["D_pp2"]["estimate"]), "r2_D2_ci": signed_ci(run2["D_pp2"]["ci95"]),
        "Ddiff": pp(est["D_diff"]["estimate"]), "Ddiff_ci": signed_ci(est["D_diff"]["ci95"]),
        # Q3
        "wnpt1": c1["would_not_pass_today"], "wnpt2": c2["would_not_pass_today"],
        "rate1": n(est["rate_wnpt_pp1"]["estimate"], 1), "rate1_ci": plain_ci(est["rate_wnpt_pp1"]["ci95"], 1),
        "rate2": n(est["rate_wnpt_pp2"]["estimate"], 1), "rate2_ci": plain_ci(est["rate_wnpt_pp2"]["ci95"], 1),
        "d3": n(est["delta3"]["estimate"], 1, sign=True), "d3_ci": signed_ci(est["delta3"]["ci95"], 1, 1, ""),
        "mdd3": n(mdd["q3_per_hour"], 1),
        "r2_wnpt1": r1["would_not_pass_today"], "r2_wnpt2": r2["would_not_pass_today"],
        "r2_d3": n(run2["delta3"]["estimate"], 1, sign=True), "r2_d3_ci": signed_ci(run2["delta3"]["ci95"], 1, 1, ""),
        # checks
        "n_checks": len(chk), "checks_table": checks_table(res),
        "amr1": n(aph["rate_america_pp1"]["estimate"], 1), "amr2": n(aph["rate_america_pp2"]["estimate"], 1),
        "amr_d": n(aph["delta_rate_america"]["estimate"], 1, sign=True),
        "amr_d_ci": signed_ci(aph["delta_rate_america"]["ci95"], 1, 1, ""),
    }
    return v


def build(res: dict) -> str:
    v = values(res)
    return num_refs(render((HERE / "template.html").read_text(encoding="utf-8"), v | {"refs": "{{refs}}"}), v)


def main() -> None:
    res = json.loads(RESULTS.read_text(encoding="utf-8"))
    PAGE.write_text(build(res), encoding="utf-8")
    out = ROOT / "assets" / SLUG
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(RESULTS, out / "results.json")
    print(f"wrote {PAGE.relative_to(ROOT)} and assets/{SLUG}/results.json")


if __name__ == "__main__":
    main()
