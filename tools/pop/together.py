"""Pop, measured, part 6: the two exploratory models across the five parts (docs/research/pop-measured-part6-design.md).

M1: log(days of the focal song in a national chart) on artist and country fixed effects and a same-language dummy.
M2: log(average ticket price) on log(GDP per capita) with tour fixed effects. Standard errors clustered by country.
Writes docs/research/pop-measured-part6-panel.csv, -tickets.csv and -results.json.

    uv run --with pandas --with numpy --with statsmodels python tools/pop/together.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs" / "research"
ARTISTS = ["harry-styles", "taylor-swift", "bts", "bad-bunny", "billie-eilish"]
SONG_LANG = {"harry-styles": "en", "taylor-swift": "en", "billie-eilish": "en", "bad-bunny": "es", "bts": "ko"}
COUNTRY_LANG = {**{c: "en" for c in "au ca gb hk ie in mt ng nz ph pk sg us za".split()},
                **{c: "es" for c in "ar bo cl co cr do ec es gt hn mx ni pa pe py sv uy ve".split()},
                "kr": "ko"}


def panel() -> pd.DataFrame:
    rows = []
    for a in ARTISTS:
        for r in pd.read_csv(R / f"{a}-countries.csv").to_dict("records"):
            rows.append({"artist": a, "country": r["country"], "days": r["focal_days"],
                         "still": bool(r["still_charting"]), "song_lang": SONG_LANG[a],
                         "country_lang": COUNTRY_LANG.get(r["country"], "other")})
    p = pd.DataFrame(rows)
    p = p[p.days > 0].copy()
    p["log_days"] = np.log(p.days)
    p["same"] = (p.song_lang == p.country_lang).astype(int)
    return p


def fit(formula: str, d: pd.DataFrame, term: str) -> dict:
    m = smf.ols(formula, data=d).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.country)[0]})
    b, lo, hi = m.params[term], *m.conf_int().loc[term]
    return {"coef": float(b), "lo": float(lo), "hi": float(hi), "pct": float(np.expm1(b)),
            "pct_lo": float(np.expm1(lo)), "pct_hi": float(np.expm1(hi)), "n": int(m.nobs),
            "clusters": int(d.country.nunique()), "r2": float(m.rsquared)}


def tickets() -> pd.DataFrame:
    rows = []
    for a in ARTISTS:
        t = pd.read_csv(R / f"{a}-tour.csv")
        if "hybrid" in t:
            t = t[t.hybrid != True]  # noqa: E712  (the CSV holds booleans)
        t = t[t.revenue_usd.notna() & t.gdppc_usd.notna() & (t.sold > 0)]
        for r in t.to_dict("records"):
            rows.append({"artist": a, "tour": r["tour"], "country": r["iso3"], "year": r["year"],
                         "price": r["revenue_usd"] / r["sold"], "gdppc": r["gdppc_usd"],
                         "per_night": r["available"] / r["nights"]})
    d = pd.DataFrame(rows)
    d["log_price"], d["log_gdppc"], d["log_size"] = np.log(d.price), np.log(d.gdppc), np.log(d.per_night)
    return d


def main() -> None:
    p = panel()
    p.to_csv(R / "pop-measured-part6-panel.csv", index=False)
    fe = "log_days ~ same + C(artist) + C(country)"
    out = {"m1": fit(fe, p, "same")}
    q = p.copy()
    q["same_es"], q["same_en"], q["same_ko"] = (q.same * (q.song_lang == g) for g in ("es", "en", "ko"))
    m = smf.ols("log_days ~ same_en + same_es + same_ko + C(artist) + C(country)", data=q).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(q.country)[0]})
    out["m1b"] = {g: {"coef": float(m.params[f"same_{g}"]), "lo": float(m.conf_int().loc[f"same_{g}"][0]),
                      "hi": float(m.conf_int().loc[f"same_{g}"][1]), "pairs": int(q[f"same_{g}"].sum())}
                  for g in ("en", "es", "ko")}
    checks = {}
    checks["without_still_charting"] = fit(fe, p[~p.still], "same")
    d2 = p.copy()
    d2.loc[d2.artist == "bts", "same"] = (d2.loc[d2.artist == "bts", "country_lang"] == "en").astype(int)
    checks["dynamite_as_english"] = fit(fe, d2, "same")
    d3 = p.copy()
    d3.loc[(d3.artist == "bad-bunny") & (d3.country == "us"), "same"] = 1
    checks["us_spanish_for_bad_bunny"] = fit(fe, d3, "same")
    checks["without_luxembourg"] = fit(fe, p[p.country != "lu"], "same")
    out["m1_checks"] = checks
    # Czechia on M1's residuals: how much longer or shorter than predicted the five songs lasted there
    m1 = smf.ols(fe, data=p).fit()
    res = p.assign(resid=m1.resid)
    out["czechia_residuals"] = {r.artist: float(np.expm1(r.resid)) for r in res[res.country == "cz"].itertuples()}
    out["m1_pairs"] = {"n": int(len(p)), "same": int(p.same.sum()), "still": int(p.still.sum())}

    t = tickets()
    t.to_csv(R / "pop-measured-part6-tickets.csv", index=False)
    out["m2"] = fit("log_price ~ log_gdppc + C(tour)", t, "log_gdppc")
    out["m2b"] = fit("log_price ~ log_gdppc + log_size + C(tour)", t, "log_gdppc")
    out["m2c"] = {}
    for a in ARTISTS:
        s = t[t.artist == a]
        if s.country.nunique() >= 5:
            out["m2c"][a] = fit("log_price ~ log_gdppc + C(tour)", s, "log_gdppc") | {"countries": int(s.country.nunique())}
    out["m2_drop_artist"] = {a: fit("log_price ~ log_gdppc + C(tour)", t[t.artist != a], "log_gdppc")["coef"] for a in ARTISTS}
    out["m2_entries"] = {"n": int(len(t)), "countries": int(t.country.nunique()), "tours": int(t.tour.nunique())}
    (R / "pop-measured-part6-results.json").write_text(json.dumps(out, indent=1))
    print("written pop-measured-part6-results.json")


if __name__ == "__main__":
    main()
