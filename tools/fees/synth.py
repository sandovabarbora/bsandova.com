"""Invented snapshot files with the layout of the real ones (labels copied from the label-only print of the snapshot
step, every number made up), for the tests and the --synthetic dry run. No real value is used or derived here."""
from __future__ import annotations

import csv
import io
import zipfile
from decimal import Decimal as D
from pathlib import Path
from xml.sax.saxutils import escape

import config as C
import inputs as I
import parse as P

# ------------------------------------------------------------------ a minimal .xlsx writer


def _col(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def xlsx_bytes(sheets: dict[str, list[list]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        names = list(sheets)
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   + "".join(f'<sheet name="{escape(n)}" sheetId="{k + 1}" r:id="rId{k + 1}"/>' for k, n in enumerate(names))
                   + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + "".join(f'<Relationship Id="rId{k + 1}" Target="worksheets/sheet{k + 1}.xml"/>' for k in range(len(names)))
                   + "</Relationships>")
        for k, n in enumerate(names):
            rows = []
            for r, row in enumerate(sheets[n]):
                cells = []
                for c, v in enumerate(row):
                    ref = f"{_col(c)}{r + 1}"
                    if v is None or v == "":
                        continue
                    if isinstance(v, str):
                        cells.append(f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(v)}</t></is></c>')
                    else:
                        cells.append(f'<c r="{ref}"><v>{v}</v></c>')
                rows.append(f'<row r="{r + 1}">{"".join(cells)}</row>')
            z.writestr(f"xl/worksheets/sheet{k + 1}.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                       f'<sheetData>{"".join(rows)}</sheetData></worksheet>')
    return buf.getvalue()


# ------------------------------------------------------------------ invented numbers

HH = [D(480_000 + 7_000 * d) for d in range(10)]
MEMBERS = [D(x) for x in ("1.4", "1.6", "1.9", "2.2", "2.4", "2.5", "2.6", "2.7", "2.7", "2.8")]
CHILDREN = [D(x) for x in ("0.2", "0.3", "0.4", "0.5", "0.55", "0.6", "0.6", "0.6", "0.55", "0.5")]
CU = [D(x) for x in ("1.25", "1.35", "1.5", "1.65", "1.75", "1.8", "1.85", "1.9", "1.9", "1.95")]
NET_CU = [D(x) for x in (110_000, 150_000, 180_000, 205_000, 230_000, 255_000, 285_000, 325_000, 385_000, 600_000)]
TAX_CU = [D(x) for x in (1_000, 4_000, 8_000, 12_000, 17_000, 23_000, 30_000, 40_000, 55_000, 120_000)]
GROSS_CU = [n * D("1.35") for n in NET_CU]
EMP_CU = [n * D("1.1") for n in NET_CU]
SELF_CU = [n * D("0.15") for n in NET_CU]
Q_HH = [D(x) for x in (1_000_000, 1_020_000, 1_030_000, 1_035_000, 1_030_000)]
Q_MEMBERS = [D(x) for x in ("1.5", "2.0", "2.4", "2.6", "2.7")]

BUDGET_2025 = {1111: 120_000_000, 1112: 20_000_000, 1113: 10_000_000, 1121: 130_000_000, 1131: 2_000_000,
               1211: 300_000_000, 1221: 30_000_000, 1222: 40_000_000, 1223: 10_000_000, 1224: 3_000_000,
               1225: 1_000_000, 1231: 5_000_000, 1233: 4_000_000, 1234: 500_000, 1321: 3_000_000,
               1611: 350_000_000, 1621: 40_000_000}
FEE = {"ct_budget": 6_700_000, "cro_chart": 2_400_000, "ct_real": 6_400_000, "cro_real": 2_300_000,
       "ct_households": 3_700_000, "cro_stock": 3_050_000}
CNB_Q = {2023: ["10.7", "10.0", "7.0", "6.9"], 2024: ["2.3", "2.2", "2.7", "2.9"], 2025: ["2.8", "2.5", "2.9", "2.5"],
         2026: ["2.1", "2.4", "2.6", "2.4"], 2027: ["2.5", "2.4", "2.3", "2.2"], 2028: ["2.1", "2.0", "2.0", None]}
BAND_COUNTS = {"000": 5000, "110": 900_000, "120": 300_000, "130": 90_000, "210": 50_000, "220": 12_000, "230": 20_000,
               "240": 8_000, "310": 4_000, "320": 700, "330": 1_000, "340": 600, "410": 150, "420": 40, "430": 20,
               "440": 10, "450": 8, "460": 4, "470": 3, "510": 1}


def fmt_cz(v) -> str:
    return f"{D(v):,.2f}".replace(",", " ").replace(".", ",")


# ------------------------------------------------------------------ workbooks

DECILE_HEAD = [f"{w} 10 %" for w in P.DECILE_WORDS[:-1]] + ["nejvyšších 10 %"]


def _silc_common(title: str, header_cols: list[str], hh, members, children, net_label_vals, extra=None) -> list[list]:
    pad = ["", "", ""]
    rows = [[f"Tab. 3  {title}"], ["", "a/ Složení domácností a roční příjmy"], ["", "Households", "", "", "", "", "", "", "", "", "", "", "Rok  2025"],
            ["", "a/ Household composition", "", "", "", "", "", "", "", "", "", "", "Year 2025"], [""],
            pad + header_cols, [""],
            [" Počet domácností", "", "absol."] + hh, ["", "", "v %"] + [1] * len(hh),
            [" Počet členů domácností", "", "absol."] + [1] * len(hh), [""], [" Průměrný počet na domácnost:"],
            [" Členů", "", ""] + members, ["pracujících", "", ""] + [1] * len(hh),
            ["vyživovaných dětí", "", ""] + children]
    return rows


def silc_3a() -> bytes:
    rows = _silc_common("Domácnosti podle decilového rozdělení", DECILE_HEAD, HH, MEMBERS, CHILDREN, None)
    pad = ["", "", ""]
    rows += [["nezaměstnaných"] + pad[1:] + [0] * 10, ["", "", ""] + [0] * 10,
             [" Spotřebních jednotek   OECD", "", ""] + [1] * 10, ["", "                 OECD modif.", ""] + CU,
             [" PŘEHLED PŘÍJMŮ za rok 2024 (Kč)"],
             [" A. Hrubé peněžní příjmy (1 až 4)", "", ""] + GROSS_CU,
             [" 1. Příjmy ze závislé činnosti", "", ""] + EMP_CU, ["z toho z hlavního zaměstnání", "", ""] + EMP_CU,
             [" 2. Příjmy z podnikání", "", ""] + SELF_CU,
             [" C. Daň z příjmů fyzických osob", "", ""] + TAX_CU,
             [" E. Čisté peněžní příjmy (A-B-C+D)", "", ""] + NET_CU,
             [" Hrubé peněžní příjmy", "", ""] + [100] * 10,
             [" Čisté příjmy", "", ""] + [70] * 10]
    return xlsx_bytes({"příjmy": rows})


SENIOR_HEAD = ["méně než 65 let", "65 a více let", "oba méně než 65", "aspoň jeden 65 let a více", "Ostatní domác. bez záv. dětí",
               "1 dospělý se závislými dětmi", "1 závislé dítě", "2 závislé děti", "3 a více závislých dětí", "Ostatní se záv. dětmi"]


def silc_10a() -> bytes:
    rows = _silc_common("Domácnosti podle druhu domácnosti EU", SENIOR_HEAD,
                        [D(x) for x in (700_000, 640_000, 500_000, 380_000, 300_000, 150_000, 200_000, 220_000, 90_000, 100_000)],
                        [D(x) for x in ("1", "1", "2", "2", "2.8", "2.2", "3", "4", "5", "4.5")],
                        [D(0)] * 4 + [D("0.3")] * 6, None)
    rows += [["nezaměstnaných", "", ""] + [0] * 10, [" Spotřebních jednotek   OECD", "", ""] + [1] * 10,
             ["", "                 OECD modif.", ""] + [1] * 10, [" PŘEHLED PŘÍJMŮ za rok 2024 (Kč)"],
             [" E. Čisté peněžní příjmy (A-B-C+D)", "", ""]
             + [D(x) for x in (260_000, 190_000, 300_000, 200_000, 280_000, 190_000, 200_000, 180_000, 170_000, 210_000)]]
    return xlsx_bytes({"příjmy": rows})


QHEAD = ["nejnižších\nlowest\n20 %", "druhých\nsecond\n20 %", "třetích\nthird\n20 %", "čtvrtých\nfourth\n20 %",
         "nejvyšších\nhighest\n20 %"]


def hbs_characteristics() -> bytes:
    rows = [["Tab. 3        Domácnosti podle kvintilového rozdělení čistých peněžních příjmů na osobu"], ["a/ Složení domácností"], [], [],
            [], [], ["", "Households,\ntotal"] + QHEAD,
            [" Počet domácností (absol.)", sum(Q_HH)] + Q_HH, [" Počet domácností (v %)", 100] + [20] * 5,
            ["členů", D("2.3")] + Q_MEMBERS]
    return xlsx_bytes({"Charakteristiky": rows})


def spend_codes() -> dict[str, list[D]]:
    """Per person and year, by quintile, for every code of the maps: rows from a base, parents from their parts."""
    entries = P.read_map(C.VAT_MAP)
    spend: dict[str, list[D]] = {}
    base = D(1000)
    for k, e in enumerate(entries):
        q = [base * (1 + D(k % 7) / 5) * (1 + D(i) * D("0.4")) for i in range(5)]
        spend[e["coicop"]] = q
    rest = {e["coicop"]: spend[e["coicop"]] for e in entries if e["kind"] == "residual"}
    parents = {}
    for code in sorted(rest, key=lambda c: -c[:-5].count(".")):
        parent = code[:-5]
        under = [c for c in spend if c.startswith(parent + ".")]
        parents[parent] = [sum(spend[c][i] for c in under) + rest[code][i] for i in range(5)]
        spend[parent] = parents[parent]
    return {k: v for k, v in spend.items() if not k.endswith("~rest")}


def _key(code: str):
    return tuple(int(x) for x in code.split("."))


def hbs_expenditure() -> bytes:
    rows = [["Tab. 3        Domácnosti"], ["b/ Skupiny spotřebních výdajů - průměry na osobu v Kč za rok, struktura v %"], [], [], [], [],
            ["", "", "Households,\ntotal"] + QHEAD, ["", " SPOTŘEBNÍ VÝDAJE (CZ-COICOP)", D(1)] + [D(1)] * 5]
    spend = spend_codes()
    first = True
    for code in sorted(spend, key=_key):
        vals = [D(1)] + [D(x) for x in spend[code]]
        if first:                                    # a label that continues on the next row, which carries the numbers
            rows += [[f" {code}", "Label that continues"], ["", "on the next row"] + vals]
            first = False
        else:
            rows.append([f" {code} " if code.count(".") == 2 else f" {code}", f"Label {code}"] + vals)
    rows += [["Struktura výdajů v %:"], [" 01", "Potraviny"] + [D(20)] * 6]
    return xlsx_bytes({"Vydaje": rows})


def cnb_indicators() -> bytes:
    years = sorted(CNB_Q)
    head = [None] * 14
    for y in years:
        head += [f"čtvrtletí roku {y}", None, None, None]
    labels = ["", ""] + [D(2017 + k) for k in range(12)] + [lab for _ in years for lab in ("I.", "II.", "III.", "IV.")]
    cpi = ["", "Spotřebitelské ceny  (%, meziročně, průměr)"] + [D(1)] * 12
    for y in years:
        cpi += [D(v) + D("0.0000000000000004") if v is not None else None for v in CNB_Q[y]]
    other = ["", "Regulované ceny (%, meziročně, průměr)"] + [D(9)] * 36
    return xlsx_bytes({"Česká verze": [[], ["", "KLÍČOVÉ MAKROEKONOMICKÉ INDIKÁTORY"], ["", ""] + head[2:], labels,
                                         ["", "CENY"], cpi, other],
                       "English version": [["", "KEY MACROECONOMIC INDICATORS"]]})


# ------------------------------------------------------------------ text files

BUDGET_ENDS = (121, 141, 159, 177, 189, 212, 232)


def _num_line(prefix: str, values: list[str]) -> str:
    line = prefix.ljust(96)
    for end, v in zip(BUDGET_ENDS, values, strict=True):
        line = line.ljust(end - len(v)) + v
        line = line[:end - len(v)] + v if len(line) > end else line
    return line


def budget_g() -> str:
    head = ["Tabulka č. 2a: Příjmy státního rozpočtu v druhovém třídění rozpočtové skladby (tis. Kč)",
            " " * 114 + "2024" + " " * 36 + "2025",
            " " * 111 + "Skutečnost" + "        Schválený rozpočet" + " " * 25 + "Skutečnost        změnách (%)       změnách",
            "      Třída"]

    def vals(v: int):
        v24 = int(v * 0.9)
        return [fmt_cz(v24), fmt_cz(v * 0.8), fmt_cz(v * 0.95), fmt_cz(v), "104,50", fmt_cz(v * 0.05), fmt_cz(v * 0.1)]
    page1 = head + ["    1Daňové příjmy".ljust(96) + fmt_cz(1).rjust(25), "      Podseskupení",
                    "  111Příjem z daní z příjmů fyzických osob", "      Položka"]
    codes = sorted(BUDGET_2025)
    body = []
    for c in codes:
        if c == 1131:                                # wrapped label: code line, numbers line, continuation line
            body += [f" {c} Příjem z dorovnávacích daní podle zvláštního", _num_line("", vals(BUDGET_2025[c])),
                     "      zákona o dorovnávacích daních"]
        elif c == 1321:
            body.append(_num_line(f" {c} Příjem z daně s tečkou 12 a číslem 3", [fmt_cz(-5)] + vals(BUDGET_2025[c])[1:]))
        else:
            body.append(_num_line(f" {c} Příjem z položky {c}", vals(BUDGET_2025[c])))
    page2 = ["Tabulka č. 2a: Příjmy státního rozpočtu v druhovém třídění rozpočtové skladby (tis. Kč)"] + head[1:3] + body[len(body) // 2:]
    page1 += body[:len(body) // 2]
    tail = ["Tabulka č. 2b: Výdaje státního rozpočtu v druhovém třídění rozpočtové skladby (tis. Kč)",
            _num_line(" 5139 Nákup materiálu", vals(999))]
    return "\f".join(["\n".join(page1), "\n".join(page2), "\n".join(tail)])


def budget_c() -> str:
    return ("Tabulka č. 7: Příjmy státního rozpočtu z daní z příjmů fyzických osob (mld. Kč)\n"
            "Tabulka č. 12: Celostátní inkaso DPH dle údajů finančních a celních úřadů (mil. Kč)\n"
            "Tabulka č. 9: Celostátní inkaso daní z příjmů právnických osob bez daně z neočekávaných zisků (mld. Kč)\n"
            "     z minerálních olejů (celostátní výnos)               10\n")


def csu_cpi() -> str:
    return ("Průměrná roční míra inflace vyjádřená přírůstkem průměrného indexu spotřebitelských cen\n"
            "(CPI – Consumer Price Index) za 12 měsíců roku 2025 proti průměru 12 měsíců roku 2024 činila\n"
            "v České republice 2,5 %. Tato data za rok 2025 byla zveřejněna.\n")


def ct_budget() -> str:
    n = FEE["ct_budget"]
    return ("Televizní poplatky\n\n"
            + " " * 52 + "2025" + " " * 10 + "2026\n (v tis. Kč)\n"
            + " " * 51 + "rozpočet      rozpočet      rozdíl      %\n"
            + f" příjem z televizních poplatků     {fmt_cz(n - 900_000)[:-3]}   {fmt_cz(n)[:-3]}    900 000   15,5 %\n")


def ct_report() -> str:
    return ("Příjem z televizních poplatků\n\n\n (v tis. Kč)                                 Rozpočet           Skutečnost"
            "             Rozdíl             Plnění %\n"
            f"příjem z televizních poplatků                    {fmt_cz(6_000_000)[:-3]}      {fmt_cz(FEE['ct_real'])[:-3]}"
            "          400 000           106,7 %\n\n"
            f"K 31. 12. 2025 měla Česká televize v evidenci celkem {fmt_cz(FEE['ct_households'])[:-3]} domácností, z toho "
            "2 000 000 (54 %) představovali SIPO plátci a 1 700 000 (46 %) plátci hradící České televizi napřímo.\n")


def cro_chart() -> str:
    return ("            data: [\n                    ['Výnosy z rozhlasových poplatků', "
            f"{FEE['cro_chart']}],\n                    ['Tržby z reklamy a sponzoringu a ost. obch. aktivit', 80000]\n")


def cro_report() -> str:
    stock = fmt_cz(FEE["cro_stock"])[:-3]
    return ("Text of the left column of a two-column page                 Počet evid. rozhlasových                stav\n"
            " " * 110 + "změna\n"
            + " " * 73 + "přijímačů (v ks)               k 1. 1. 2025                     k 31. 12. 2025\n"
            + " " * 73 + "Fyzické osoby – SIPO             1 100 000          -100 000         1 000 000\n"
            + "left text                                                    FYZICKÉ OSOBY                    3 000 000         50 000      "
            + stock + "\n"
            "Výnosy z rozhlasových poplatků byly oproti původní plánované roční hodnotě 2 000 000 tis. Kč vykázá-\n"
            "ny v objemu o 300 000 tis. Kč vyšším, tj. v částce 2 300 000 tis. Kč. Do tohoto nárůstu se promítají dopady.\n")


def bill() -> str:
    return ("Příspěvek pro rok 2027 činí celkem 5 741 826 000 Kč.\n\nPříspěvek pro rok 2027 činí celkem 2 065 766 000 Kč.\n")


def band_codes_csv() -> str:
    labels = {"000": "Neuvedeno", "110": "Bez zaměstnanců", "120": "1 - 5 zaměstnanců", "130": "6 - 9 zaměstnanců",
              "210": "10 - 19 zaměstnanců", "220": "20 - 24 zaměstnanci", "230": "25 - 49 zaměstnanců",
              "240": "50 - 99 zaměstnanců", "310": "100 - 199 zaměstnanců", "320": "200 - 249 zaměstnanců",
              "330": "250 - 499 zaměstnanců", "340": "500 - 999 zaměstnanců", "410": "1000 - 1499 zaměstnanců",
              "420": "1500 - 1999 zaměstnanců", "430": "2000 - 2499 zaměstnanců", "440": "2500 - 2999 zaměstnanců",
              "450": "3000 - 3999 zaměstnanců", "460": "4000 - 4999 zaměstnanců", "470": "5000 - 9999 zaměstnanců",
              "510": "10 000 a více zaměstnanců"}
    out = io.StringIO()
    w = csv.writer(out, quoting=csv.QUOTE_ALL)
    w.writerow(["kodjaz", "akrcis", "kodcis", "chodnota", "zkrtext", "text", "admplod", "admnepo"])
    for c, t in labels.items():
        w.writerow(["CS", "KATPOECD", 579, c, t, t, "1973-01-01", "9999-09-09"])
    return out.getvalue()


def res_csv(counts: dict[str, int] | None = None, terminated: int = 7) -> str:
    counts = counts or BAND_COUNTS
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["ICO", "OKRESLAU", "DDATVZN", "DDATZAN", "ZPZAN", "DDATPAKT", "FORMA", "ROSFORMA", "KATPO", "NACE"])
    n = 0
    for code, k in counts.items():
        for _ in range(k):
            n += 1
            w.writerow([n, "CZ010", "2000-01-01", "", "", "2026-01-01", "101", "100", code, "47"])
    for i in range(terminated):                      # terminated entities are not counted
        w.writerow([n + i + 1, "CZ010", "2000-01-01", "2020-01-01", "1", "2026-01-01", "101", "100", "230", "47"])
    return out.getvalue()


def make_snapshot(root: Path, counts: dict[str, int] | None = None) -> I.Sources:
    root.mkdir(parents=True, exist_ok=True)
    files = {"silc_3a.xlsx": silc_3a(), "silc_10a.xlsx": silc_10a(), "hbs_chars.xlsx": hbs_characteristics(),
             "hbs_spend.xlsx": hbs_expenditure(), "cnb.xlsx": cnb_indicators()}
    texts = {"budget_g.txt": budget_g(), "budget_c.txt": budget_c(), "csu_cpi.txt": csu_cpi(), "ct_budget.txt": ct_budget(),
             "ct_report.txt": ct_report(), "cro_chart.js": cro_chart(), "cro_report.txt": cro_report(), "bill.txt": bill(),
             "res.csv": res_csv(counts), "bands.csv": band_codes_csv()}
    for k, v in files.items():
        (root / k).write_bytes(v)
    for k, v in texts.items():
        (root / k).write_text(v, encoding="utf-8")
    return I.Sources(silc_3a=root / "silc_3a.xlsx", silc_10a=root / "silc_10a.xlsx",
                     hbs_characteristics=root / "hbs_chars.xlsx", hbs_expenditure=root / "hbs_spend.xlsx",
                     budget_g=root / "budget_g.txt", budget_c=root / "budget_c.txt", cnb_indicators=root / "cnb.xlsx",
                     csu_cpi=root / "csu_cpi.txt", ct_budget=root / "ct_budget.txt", ct_report=root / "ct_report.txt",
                     cro_chart=root / "cro_chart.js", cro_report=root / "cro_report.txt", bill=root / "bill.txt",
                     res_csv=root / "res.csv", band_codes=root / "bands.csv")
