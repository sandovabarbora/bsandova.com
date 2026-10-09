"""Publish a weekly Ask evaluation only when the run actually reached the agent.

    python ask/eval_guard.py <run_dir> <ask_dir>

`sitewitness eval --out <run_dir>` writes eval.json and eval-history.json there. A row whose request failed
(HTTP 502, timeout, refused connection) carries an "error" field and no answer: it says nothing about the agent.
On 5 October 2026 every one of the 30 requests failed with HTTP 502 and the run was saved over the last good
evaluation as a score of 0 / 30. From now on:

- when at most a quarter of the rows are transport errors, eval.json and eval-history.json are copied to <ask_dir>;
- otherwise <ask_dir>/eval.json is left as it is (the last good run), the summary is appended to
  <ask_dir>/eval-history.json marked "failed": true with its error count (the page shows it as a failed run, not as
  a score), and the exit status is 1 so the workflow run is red.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

MAX_ERROR_SHARE = 0.25


def transport_errors(rows: list[dict]) -> int:
    return sum(1 for r in rows if r.get("error"))


def is_failed_run(rows: list[dict], max_share: float = MAX_ERROR_SHARE) -> bool:
    if not rows:
        return True
    return transport_errors(rows) / len(rows) > max_share


def failed_record(summary: dict, rows: list[dict]) -> dict:
    errors = sorted({str(r["error"])[:80] for r in rows if r.get("error")})
    return {**summary, "failed": True, "transport_errors": transport_errors(rows), "errors": errors}


def publish(run_dir: Path, ask_dir: Path) -> int:
    run = json.loads((run_dir / "eval.json").read_text())
    summary, rows = run["summary"], run["rows"]
    if not is_failed_run(rows):
        shutil.copyfile(run_dir / "eval.json", ask_dir / "eval.json")
        shutil.copyfile(run_dir / "eval-history.json", ask_dir / "eval-history.json")
        print(f"published: {summary['correct']} / {summary['n']} on {summary['date']}")
        return 0
    hp = ask_dir / "eval-history.json"
    hist = json.loads(hp.read_text()) if hp.exists() else []
    hist = [h for h in hist if h.get("date") != summary["date"]] + [failed_record(summary, rows)]
    hp.write_text(json.dumps(hist, indent=1, ensure_ascii=False) + "\n")
    print(f"failed run on {summary['date']}: {transport_errors(rows)} of {len(rows)} requests did not reach the agent; "
          "eval.json kept, failure recorded in eval-history.json")
    return 1


if __name__ == "__main__":
    sys.exit(publish(Path(sys.argv[1]), Path(sys.argv[2])))
