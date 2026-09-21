"""Judge every job in status/jobs.json the way the status page does, from the same sources, and exit 1
with a report when any job is late, stale or failed. Run daily by .github/workflows/status.yml, which
mails the report. The page shows the state to whoever looks; this is for the days nobody does.

    python tools/status_check.py            # prints the report, exit 1 on any problem
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://bsandova.com"
GH = "https://api.github.com"


def get(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": "bsandova-status-check", "Accept": "application/vnd.github+json"})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok and url.startswith(GH):
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main() -> int:
    now = datetime.now(timezone.utc)
    jobs = json.loads((ROOT / "status" / "jobs.json").read_text())
    lines, problems = [], 0
    for j in jobs:
        state, detail = "ok", []
        try:
            age_h = None
            if j.get("data"):
                d = get(f"{SITE}/{j['data']['file'].replace('../', '')}")
                if isinstance(d, dict) and "summary" in d and "date" in d["summary"]:
                    gen = datetime.fromisoformat(d["summary"]["date"] + "T05:00:00+00:00")
                    age_h = (now - gen).total_seconds() / 3600
                    detail.append(f"last eval {d['summary']['date']} · {d['summary']['correct']}/{d['summary']['n']}")
                elif isinstance(d, dict) and "generated" in d:
                    gen = datetime.fromisoformat(d["generated"] + "T06:40:00+00:00")
                    age_h = (now - gen).total_seconds() / 3600
                    detail.append(f"data {d['generated']} ({age_h:.0f} h old)")
                    q = d.get("quality", {})
                    if q.get("missing_issue_dates"):
                        detail.append(f"missing issues {', '.join(q['missing_issue_dates'][-5:])}")
                elif isinstance(d, list) and d and "date" in d[0]:
                    last = max(r["date"] for r in d)
                    gen = datetime.fromisoformat(last + "T03:00:00+00:00")
                    age_h = (now - gen).total_seconds() / 3600
                    detail.append(f"last sweep {last} ({age_h/24:.0f} d old)")
            ok = None
            if "github_workflow" in j["runs"]:
                w = j["runs"]["github_workflow"]
                # a run still in progress has no conclusion yet; judge the last finished one
                done = [r for r in get(f"{GH}/repos/{w['repo']}/actions/workflows/{w['workflow']}/runs?per_page=5&status=completed")["workflow_runs"]]
                if done:
                    ok = done[0]["conclusion"] == "success"
                    detail.append(f"last run {done[0]['run_started_at'][:16]} {done[0]['conclusion']}")
            cad = j.get("cadence_hours")
            if ok is False:
                state = "failed"
            elif cad and age_h is not None:
                state = "ok" if age_h < cad else "late" if age_h < 2 * cad else "stale"
        except Exception as e:  # noqa: BLE001
            state, detail = "unknown", [f"could not read: {e}"]
        if state != "ok":
            problems += 1
        lines.append(f"{state.upper():8s} {j['name']:32s} {' · '.join(detail)}")
    report = "\n".join(lines)
    print(report)
    Path(os.environ.get("REPORT_PATH", "/dev/null")).write_text(report + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
