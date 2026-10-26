"""Outputs of the meme event study (design §4, §6): summary.json, the abnormal-attention SVG, the pre-event raw-series
SVG for the confounder check, and the page skeleton with the numbers filled in. The prose is a skeleton for the author
to rewrite, so it only states what a label allows.
"""
from __future__ import annotations

import io
import json
import re
from collections.abc import Mapping
from pathlib import Path

import pandas as pd

MAX_SVG_BYTES = 40_000
BLURB = {
    "positive": "a jump, and the castmates did not move with it",
    "no detectable jump": "no jump I can tell from chance",
    "inconclusive": "inconclusive",
}


def write_summary(path: Path, payload: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False, default=str) + "\n")


def _svg(fig) -> str:
    buf = io.StringIO()
    fig.savefig(buf, format="svg")
    return buf.getvalue()


def _plt():
    import matplotlib
    matplotlib.use("svg")
    import matplotlib.pyplot as plt
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["svg.hashsalt"] = "memes"
    return plt


def _tidy(ax) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def ar_svg(ars: Mapping[str, pd.Series], events: Mapping[str, str]) -> str:
    """Abnormal attention (log points) by day from each event, a zero line and a dotted line at day 0."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    for label, ar in ars.items():
        days = (ar.index - pd.Timestamp(events[label])).days
        ax.plot(days, ar.to_numpy(), lw=1.4, label=label)
    ax.axhline(0, color="grey", lw=0.8)
    ax.axvline(0, color="grey", lw=0.8, ls=":")
    ax.set_xlabel("days from the first post")
    ax.set_ylabel("abnormal attention (log)")
    ax.legend(frameon=False)
    _tidy(ax)
    fig.tight_layout()
    out = _svg(fig)
    if len(out.encode()) > MAX_SVG_BYTES:
        plt.rcParams["path.simplify_threshold"] = 0.5
        out = _svg(fig)
    plt.close(fig)
    return out


def estimation_svg(panel: pd.DataFrame, cutoffs: Mapping[str, str], start: str) -> str:
    """Raw log1p series up to three days before each event only, for the confounder check of design §3. The event
    windows are not drawn, so the check cannot be steered by the result."""
    plt = _plt()
    names = list(cutoffs)
    fig, axes = plt.subplots(len(names), 1, figsize=(7, 2.2 * len(names)), squeeze=False)
    import numpy as np
    for ax, name in zip(axes[:, 0], names, strict=True):
        part = panel.loc[start:cutoffs[name]]
        for col in part.columns:
            ax.plot(part.index, np.log1p(part[col]).to_numpy(), lw=0.6)
        ax.set_title(f"{name}: raw log1p views up to {cutoffs[name]}", fontsize=8)
        _tidy(ax)
    fig.tight_layout()
    out = _svg(fig)
    plt.close(fig)
    return out


# ---------------------------------------------------------------- page

CSS = ("body{font:17px/1.55 system-ui,sans-serif;max-width:38rem;margin:2rem auto;padding:0 1rem;background:#fff;"
       "color:#1a1a1a}h1,h2,th,summary{font-weight:400}h1{font-size:1.5rem}h2{font-size:1.15rem;margin-top:1.6rem}"
       "table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ccc;padding:.3rem .4rem;"
       "text-align:left}svg{max-width:100%;height:auto}"
       "@media(prefers-color-scheme:dark){body{background:#161616;color:#e8e8e8}td,th{border-color:#444}"
       "svg text{fill:#e8e8e8}}")


def _num(x: float | None, nd: int = 1) -> str:
    return "none" if x is None else f"{x:.{nd}f}"


def _p(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def _cast_sentence(e: Mapping) -> str:
    if not e.get("gates_label") or e.get("falsification_p") is None:
        return ""
    if e["falsification_p"] >= 0.05:
        return " The castmates' own pages did not rise by more than chance."
    return " The castmates' pages rose too, so this may be news about the show."


def _event_sentence(e: Mapping) -> str:
    name = e["name"]
    label = e["label"] or "inconclusive"
    if label == "positive":
        hl = ("Half of the peak was gone after " + _num(e["half_life_days"], 0) + " days."
              if e["half_life_days"] is not None else "The peak did not halve within the window.")
        text = f"{name}: a jump, on average {e['car_pct_uplift']:.0f} % above the baseline over the window. {hl}"
    elif label == "no detectable jump":
        text = (f"{name}: no jump I can tell from chance. That is not proof of none, only that a small one would "
                "hide in the noise.")
    else:
        text = f"{name}: inconclusive. The tests do not agree, or only the uncorrected test passes."
    return text + _cast_sentence(e)


def render_html(summary: Mapping, svg: str) -> str:
    events = summary["events"]
    rows = "".join(
        f"<tr><td>{e['name']}</td><td>{e['event_date']}</td><td>{e['car_pct_uplift']:.0f} %</td>"
        f"<td>{_p(e['placebo_p'])}</td><td>{_p(e['holm_p'])}</td><td>{_num(e['half_life_days'], 0)}</td>"
        f"<td>{e['label'] or 'n/a'}</td></tr>" for e in events)
    results = " ".join(_event_sentence(e) for e in events)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Two memes, two Wikipedia pages</title><style>{CSS}</style></head><body>
<h1>Two memes, two Wikipedia pages</h1>
<h2>Question</h2>
<p>Did two memes from autumn 2023 send people to Wikipedia? Not memes in general, but two: Eric Stonestreet as Cameron Tucker, and Kevin James in a King of Queens photo.</p>
<h2>What I measured</h2>
<p>Daily views of each actor's English article, set against the articles of their castmates. The castmates show what a normal day looks like, not what the meme did.</p>
<p>I add up the gap from 3 days before the first post to 30 days after. A set of 300 other dates shows how large such a gap is by chance.</p>
<h2>Result</h2>
<p>{results}</p>
<table><tr><th>Event</th><th>First post</th><th>Mean uplift</th><th>p</th><th>Holm p</th><th>Half-life, days</th><th>Label</th></tr>{rows}</table>
{svg}
<h2>What would refute the thesis</h2>
<p>If the castmates rose as much as the actor, it was news about the show, not the meme.</p>
<h2>Limits</h2>
<p>Views measure looking something up, not seeing a meme. Castmates have their own news. The first post is not the peak of the meme.</p>
<details><summary>Method</summary>
<p>Market model on log(1 + views), fitted on days -150 to -31 before the first post, minus the days around an earlier TikTok wave. Abnormal attention is the gap to the model. The p-value is the share of 300 random dates with a gap at least as large. Two tests share a Holm correction.</p></details>
<h2>Sources</h2>
<p><a href="https://knowyourmeme.com/memes/cameron-tucker-smiling">Know Your Meme, Cameron Tucker Smiling</a>. <a href="https://knowyourmeme.com/memes/kevin-james-smirking-getty-image">Know Your Meme, Kevin James Smirking Getty Image</a>. <a href="https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/">Wikimedia Analytics API</a>. MacKinlay (1997), Journal of Economic Literature 35(1).</p>
</body></html>
"""


def visible_text(html: str) -> str:
    """The prose a reader sees: no style, script or svg, no tags."""
    body = re.sub(r"<(style|script|svg)\b.*?</\1>", " ", html, flags=re.DOTALL)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).strip()
