"""Residential institutions in Prague (inpatient hospitals, residential social services, prisons) with RÚIAN
address points, for the institution flag of Part 2 extended. Writes tools/data/praha2x/institutions.csv.

Sources: ÚZIS NRPZS NR-01-06 (places of care), MPSV register of social-service providers (rpss.json), Prison
Service (vs.gov.cz) for Pankrác and Ruzyně; coordinates from RÚIAN address points. Retrieved 2026-09-28.
"""

import csv
import json
import re
import urllib.parse
import urllib.request
from collections import OrderedDict, defaultdict
from pathlib import Path

D = str(Path(__file__).resolve().parents[2] / "tools" / "data" / "praha2x") + "/"
TODAY = "2026-09-28"
AGS = "https://ags.cuzk.gov.cz/arcgis/rest/services/RUIAN/MapServer/1/query"


def ruian_lookup(codes):
    out = {}
    codes = sorted({int(c) for c in codes if c})
    for i in range(0, len(codes), 100):
        chunk = codes[i : i + 100]
        q = urllib.parse.urlencode(
            {
                "where": "kod IN (%s)" % ",".join(map(str, chunk)),
                "outFields": "kod,adresa",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "json",
            }
        )
        with urllib.request.urlopen(AGS + "?" + q, timeout=60) as r:
            d = json.load(r)
        for f in d.get("features", []):
            a = f["attributes"]
            out[a["kod"]] = (f["geometry"]["x"], f["geometry"]["y"], a["adresa"])
    return out


rows = []

# 1. hospitals (NRPZS)
with open(D + "nrpzs_mista.csv", encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        if r["ZZ_kraj_kod"] != "CZ010":
            continue
        forma = r["ZZ_forma_pece"] or ""
        if "lůžk" not in forma and "DIOP" not in forma:
            continue
        lon = lat = ""
        m = re.match(r"POINT\(([\d.]+) ([\d.]+)\)", r["ZZ_GPS"] or "")
        if m:  # NRPZS stores POINT(lat lon)
            lat, lon = m.group(1), m.group(2)
        addr = "%s %s, %s %s" % (r["ZZ_ulice"], r["ZZ_cislo_domovni_orientacni"].strip(), r["ZZ_PSC"], r["ZZ_obec"])
        rows.append(
            dict(
                type="hospital_inpatient",
                name="%s [%s]" % (r["ZZ_nazev"], r["ZZ_druh_nazev"]),
                address=addr,
                lon=lon,
                lat=lat,
                adm_code=r["ZZ_RUIAN_kod"],
                source="MZCR NRPZS NR-01-06; ZZ_ID=%s" % r["ZZ_ID"],
            )
        )

# 2. residential social services (RPSS)
druhy = {x["id"]: x["nazev"]["cs"] for x in json.load(open(D + "rpss_druhy.json"))["polozky"]}
KEEP = {"DruhSocialniSluzby/%d" % k for k in (11, 12, 13, 14, 15)}
care = OrderedDict()
secret = defaultdict(int)
for s in json.load(open(D + "rpss.json"))["polozky"]:
    if s.get("datumPoskytovaniDo") and s["datumPoskytovaniDo"] < TODAY:
        continue
    dk = s["druhSocialniSluzby"]["id"]
    if dk not in KEEP:
        continue
    if not any(f["forma"]["id"] == "FormaSocialniSluzby/pob" for f in (s.get("formy") or [])):
        continue
    for z in s.get("zarizeni") or []:
        if z.get("poskytujeDo") and z["poskytujeDo"] < TODAY:
            continue
        a = z.get("adresa")
        if not a:
            if z.get("utajenaAdresa"):
                secret[druhy[dk]] += 1
            continue
        if (a.get("kraj") or {}).get("id") != "Kraj/19" and (a.get("obec") or {}).get("id") != "Obec/554782":
            continue
        kod = a["kodAdresnihoMista"]
        c = care.setdefault(kod, dict(names=[], druhy=[], ids=[], a=a))
        if z["nazev"].strip() not in c["names"]:
            c["names"].append(z["nazev"].strip())
        if druhy[dk] not in c["druhy"]:
            c["druhy"].append(druhy[dk])
        if s["identifikator"] not in c["ids"]:
            c["ids"].append(s["identifikator"])
for kod, c in care.items():
    a = c["a"]
    num = str(a.get("cisloDomovni") or "") + ("/" + a["cisloOrientacni"] if a.get("cisloOrientacni") else "")
    addr = "%s %s, %s Praha" % ((a.get("ulice") or {}).get("nazev", ""), num, a.get("psc") or "")
    rows.append(
        dict(
            type="care_home",
            name="%s [%s]" % ("; ".join(c["names"]), "; ".join(c["druhy"])),
            address=addr.strip(),
            lon="",
            lat="",
            adm_code=str(kod),
            source="MPSV RPSS; identifikator=%s" % ",".join(c["ids"]),
        )
    )

# 3. prisons (vs.gov.cz addresses, cross-checked with IPR Praha layer FSV_CUR_OV_VEZNICE_B)
rows.append(
    dict(
        type="prison",
        name="Vazební věznice a ústav pro výkon zabezpečovací detence Praha-Pankrác",
        address="Soudní 988/1, 140 57 Praha 4",
        lon="",
        lat="",
        adm_code="21948020",
        source="VS CR vs.gov.cz/organizacni-jednotky/vazebni-veznice-praha-pankrac; IPR Praha Veznice",
    )
)
rows.append(
    dict(
        type="prison",
        name="Vazební věznice Praha-Ruzyně",
        address="Staré náměstí 3/12, 161 02 Praha 6",
        lon="",
        lat="",
        adm_code="22232494",
        source="VS CR vs.gov.cz/organizacni-jednotky/vazebni-veznice-praha-ruzyne; IPR Praha Veznice",
    )
)

# Source codes absent from the current RÚIAN layer, re-matched by address text (2026-09-28).
RETIRED = {
    "22161759": "85647811",  # U vojenské nemocnice 1200/1 (ÚVN)
    "80024893": "81404255",  # Řešovská 852/10
    "80054885": "82804621",  # K Hrnčířům 1038
    "80137255": "87406772",  # U hostivařského nádraží 792
    "21730598": "26279894",
}  # U nemocnice 504/1 no longer exists; nearest same-street o.č. 1 = 2094/1
for r in rows:
    if r["adm_code"] in RETIRED:
        r["source"] += "; source adm_code %s not in current RUIAN, replaced" % r["adm_code"]
        r["adm_code"] = RETIRED[r["adm_code"]]

# RÚIAN lookup: canonical address text for all, coordinates where missing
look = ruian_lookup(r["adm_code"] for r in rows if r["adm_code"])
missing = []
for r in rows:
    k = int(r["adm_code"]) if r["adm_code"] else None
    if k in look:
        x, y, adr = look[k]
        r["address"] = adr
        if not r["lon"]:
            r["lon"], r["lat"] = "%.6f" % x, "%.6f" % y
            r["source"] += "; coords=RUIAN AdresniMisto def. point"
    if not r["lon"]:
        missing.append(r)
    else:
        r["lon"] = "%.6f" % float(r["lon"])
        r["lat"] = "%.6f" % float(r["lat"])

with open(D + "institutions.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["type", "name", "address", "lon", "lat", "adm_code", "source"])
    w.writeheader()
    w.writerows(rows)

from collections import Counter

print(Counter(r["type"] for r in rows))
print("secret-address residential facilities skipped:", dict(secret))
print(
    "not found in RUIAN layer:",
    [(r["name"][:50], r["adm_code"]) for r in rows if r["adm_code"] and int(r["adm_code"]) not in look],
)
print("missing coords:", [(r["name"][:60], r["adm_code"], r["address"]) for r in missing])
