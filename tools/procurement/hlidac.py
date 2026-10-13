"""Optional contract-type classification from Hlídač státu (design §4.11). Not run before registration.

    nice -n 20 uv run --with pandas==3.0.6 --with pyarrow==26.0.0 python tools/procurement/hlidac.py [--sample 20000]

Reads the token from the environment variable HLIDAC_STATU_TOKEN, or from the gitignored .env at the repository root.
The token is never printed, logged or written. Without a token the classification is skipped and the script says so.
For a random sample of primary contracts in the analysis range (drawn by id, not by value), it requests each
contract's record, one request a second, User-Agent "bsandova.com research", no e-mail address, and writes
tools/data/procurement/hlidac_types.parquet (id, works: True / False / missing). It prints counts of classified and
unclassified contracts only.

The endpoint and the field names of the classification are taken from the public API description and are checked on
the first response at the data step (field names only, no value); until then they are assumptions.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools" / "data" / "procurement"
API = "https://api.hlidacstatu.cz/api/v2/smlouvy/{id}"
UA = "bsandova.com research"  # no e-mail address in any request
TOKEN_VAR = "HLIDAC_STATU_TOKEN"
PAUSE_S = 1.0
SEED = 20250701


def load_token(env_file: Path = ROOT / ".env") -> str | None:
    token = os.environ.get(TOKEN_VAR)
    if token:
        return token.strip()
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == TOKEN_VAR:
                return value.strip().strip('"').strip("'") or None
    return None


def request(contract_id: str, token: str) -> urllib.request.Request:
    return urllib.request.Request(API.format(id=contract_id),
                                  headers={"Authorization": f"Token {token}", "User-Agent": UA})


def fetch_json(req: urllib.request.Request) -> dict:
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def works_from(record: dict) -> bool | None:
    """True if any classification type names construction works, False if classified otherwise, None if
    unclassified."""
    cls = record.get("Classification") or record.get("classification") or {}
    types = cls.get("Types") or cls.get("types") or []
    names = [str(t.get(k, "")) for t in types for k in ("TypeValue", "ClassifType", "Name", "name") if isinstance(t, dict)]
    names = [n.lower() for n in names if n]
    if not names:
        return None
    return any(n.startswith("stav") or "stavebn" in n for n in names)


def classify(ids: list[str], token: str, fetch=fetch_json, sleep=time.sleep) -> tuple[dict, dict]:
    """Returns ({id: works or None}, {outcome: count}). Errors are counted by HTTP status only, so no message that
    could carry a header reaches the output."""
    out, tally = {}, {"classified": 0, "unclassified": 0, "failed": 0}
    for i, cid in enumerate(ids):
        if i:
            sleep(PAUSE_S)
        try:
            w = works_from(fetch(request(cid, token)))
        except urllib.error.HTTPError as e:
            tally[f"HTTP {e.code}"] = tally.get(f"HTTP {e.code}", 0) + 1
            tally["failed"] += 1
            out[cid] = None
            continue
        except (urllib.error.URLError, TimeoutError, ValueError):
            tally["failed"] += 1
            out[cid] = None
            continue
        out[cid] = w
        tally["classified" if w is not None else "unclassified"] += 1
    return out, tally


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=20_000)
    a = ap.parse_args(argv)
    token = load_token()
    if not token:
        print(f"Hlídač státu classification skipped: {TOKEN_VAR} not set; the Hlídač type rows are recorded as skipped")
        return
    import pandas as pd
    df = pd.read_parquet(DATA / "contracts.parquet")
    pool = df[df["period"].isin(["pre", "post"]) & ~df["content_duplicate"] & df["value"].gt(500_000)
              & df["value"].le(13_500_000)]["id"]
    ids = pool.sample(min(a.sample, len(pool)), random_state=SEED).tolist()
    types, tally = classify(ids, token)
    pd.DataFrame({"id": list(types), "works": pd.array(list(types.values()), dtype="boolean")}).to_parquet(
        DATA / "hlidac_types.parquet", index=False)
    print(json.dumps(tally))


if __name__ == "__main__":
    sys.exit(main())
