"""Reads the snapshot files named in a `Sources` and turns them into the inputs of the model. The synthetic dry run and
the tests point `Sources` at invented files with the same layout; only `real_sources` points at tools/data/fees."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import config as C
import legal as L
import model as M
import parse as P
import xlsx as X


@dataclass(frozen=True)
class Sources:
    silc_3a: Path
    silc_10a: Path
    hbs_characteristics: Path
    hbs_expenditure: Path
    budget_g: Path
    budget_c: Path
    cnb_indicators: Path
    csu_cpi: Path
    ct_budget: Path
    ct_report: Path
    cro_chart: Path
    cro_report: Path
    bill: Path
    res_csv: Path
    band_codes: Path
    vat_map: Path = C.VAT_MAP
    excise_map: Path = C.EXCISE_MAP


def real_sources() -> Sources:
    s = C.SNAP
    return Sources(
        silc_3a=s / "silc/16002126_data/1600212603a.xlsx", silc_10a=s / "silc/16002126_data/1600212610a.xlsx",
        hbs_characteristics=s / "consumption/individual/1600662631.xlsx",
        hbs_expenditure=s / "consumption/individual/1600662632.xlsx",
        budget_g=s / "budget/2026-04-30_G-Tabulkova-cast.pdf",
        budget_c=s / "budget/2026-04-30_C-Zprava-o-vysledcich-hospodareni-statniho-rozpoctu_v01.pdf",
        cnb_indicators=s / "cnb/zomp_2026_leto_makroindikatory.xlsx", csu_cpi=s / "cpi/inflace_2025.pdf",
        ct_budget=s / "ct/Rozpocet_Ceske_televize_na_rok_2026.pdf",
        ct_report=s / "ct/CT_Vyrocni_zprava_o_cinnosti_a_hospodareni_CT_2025.pdf",
        cro_chart=s / "cro/projekty_cro-rozpocet-26a_chart.js",
        cro_report=s / "cro/CRo_VZ_cinnost_a_hospodareni_2025_8f3fbe9c.pdf",
        bill=s / "bill/t023100.pdf", res_csv=s / "employers/res_data.csv",
        band_codes=s / "employers/ciselnik_579_katpo.csv")


@dataclass(frozen=True)
class Loaded:
    qb: M.QbInputs
    qa: L.QaInputs
    gross_labels: dict[str, bool]
    cnb_quarterly: dict[int, list[Decimal | None]]
    budget_blank_items: list[int]
    pool_items_absent: list[int]


def sheet(path: Path, name: str):
    wb = X.read_workbook(path)
    if name not in wb:
        raise P.ParseError(f"sheet {name!r} not found in {path.name}")
    return wb[name]


def load(src: Sources) -> Loaded:
    P.verify_bill(P.read_text(src.bill, layout=False))
    silc = P.parse_silc_deciles(sheet(src.silc_3a, "příjmy"))
    seniors = P.parse_silc_seniors(sheet(src.silc_10a, "příjmy"))
    hh_q, members_q = P.parse_hbs_characteristics(sheet(src.hbs_characteristics, "Charakteristiky"))
    hbs = P.Hbs(hh_q, members_q, P.parse_hbs_expenditure(sheet(src.hbs_expenditure, "Vydaje")))
    total_hh = sum(silc.households)
    if not Decimal(3_000_000) <= total_hh <= Decimal(8_000_000):
        raise P.ParseError("SILC household count is outside the plausible range: check the unit of the table")
    budget_text = P.read_text(src.budget_g)
    items = P.parse_budget_items(budget_text)
    blank = P.blank_items(budget_text)
    pool = P.pool_lines(items, blank)
    gross_labels = P.gross_line_labels(P.read_text(src.budget_c))
    quarterly = P.parse_cnb_quarterly(X.read_workbook(src.cnb_indicators))
    csu = P.parse_csu_cpi(P.read_text(src.csu_cpi, layout=False))
    ct_line = P.parse_ct_budget(P.read_text(src.ct_budget))
    ct_n, ct_real = P.parse_ct_report(P.read_text(src.ct_report), P.read_text(src.ct_report, layout=False))
    cro_line = P.parse_cro_chart(src.cro_chart.read_text(encoding="utf-8"))
    cro_n, cro_real = P.parse_cro_report(P.read_text(src.cro_report), P.read_text(src.cro_report, layout=False))
    qa = L.QaInputs(csu_2025=csu, cnb_annual=P.cnb_annual(quarterly),
                    fee_line_2026={"CT": ct_line, "CRO": cro_line}, realised_2025={"CT": ct_real, "CRO": cro_real})
    infl = L.inflation_series(qa.csu_2025, qa.cnb_annual)
    revenue = sum((L.baseline_2026(qa, b, "A", L.year_sums(L.monthly_amounts(b, infl))) for b in C.BROADCASTERS),
                  Fraction(0))
    labels = P.read_band_codes(src.band_codes)
    for lab in labels.values():
        P.band_bounds(lab)
    qb = M.QbInputs(silc=silc, hbs=hbs, vat_map=P.read_map(src.vat_map), excise_map=P.read_map(src.excise_map),
                    pool=pool, payers_tv=ct_n, payers_r=cro_n, fee_revenue_2026=revenue, seniors=seniors,
                    employer_counts=P.count_employers(src.res_csv, labels), band_labels=labels, gross_lines=None)
    return Loaded(qb, qa, gross_labels, quarterly, blank, P.pool_absent(items))
