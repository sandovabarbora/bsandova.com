"""Frozen settings of the Pitch Perfect joke-target study (docs/research/pitch-design.md). No threshold, seed or path
is written anywhere else."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PROMPTS = HERE / "prompts"
DATA = ROOT / "tools/data/pitch"              # gitignored since ddbcc6c
RAW = DATA / "raw"
VALIDATION = DATA / "validation"
OUT = DATA / "out"
DESIGN = ROOT / "docs/research/pitch-design.md"
MANIFEST = ROOT / "docs/research/pitch-files.sha256"
SONG_MARKS = ROOT / "docs/research/pitch-song-marks.json"
RESULTS = ROOT / "docs/research/pitch-results.json"
SAMPLE = VALIDATION / "sample.json"
FORM = VALIDATION / "form.html"
HUMAN = VALIDATION / "validation-human.json"
ITALIC_RUNS = VALIDATION / "italic-runs.json"
ENV_FILE = ROOT / ".env"

DESIGN_TAG = "pitch-design"
CODE_TAG = "pitch-code-cli"   # freezes tools/pitch, the prompts and the codebook (design §3.3); replaces the tag
                              # pitch-code, whose code is unchanged but for the client below (change log, 27 October 2026)

FILMS = ("pp1", "pp2")        # order matters: the bootstrap and the sample draw PP1 first (design §3.4, §4.5)
FILM_NAMES = {"pp1": "Pitch Perfect", "pp2": "Pitch Perfect 2"}

# §2.2
LYRIC_SYMBOLS = ("\u266a", "\u266b")   # ♪ ♫
LYRIC_HASH = "#"
ITALIC_RUN_MIN = 3
SCENE_GAP_S = 8.0
SENSITIVITY_GAPS_S = (5.0, 12.0)

# §2.3, §2.4
KINDS = ("joke", "allusion")
TARGETS = ("america", "group", "character", "genre")
GROUP_TYPES = ("gender", "race", "weight", "sexuality", "nationality", "religion", "disability", "other")
PROTECTED = ("gender", "race", "weight", "sexuality", "nationality", "religion", "disability")   # decision D
BUTTS = ("speaker", "group", "unclear")

# §3.4
SAMPLE_PER_FILM = 50
SAMPLE_SEED = 2012
SKIP = "skip"

# §3.6, §4
MODEL = "claude-sonnet-5-5"   # the full model ID, no alias
# Deviation of 27 October 2026 (design change log): temperature cannot be sent to Claude 5 models, so it is not sent;
# thinking and effort are fixed explicitly instead of left to the API's defaults.
THINKING = {"type": "adaptive"}
EFFORT = "high"
SDK_PIN = "anthropic==2.3.0"
# Deviation of 27 October 2026: the runs go through the Claude Code CLI in print mode (no API key), with the same
# model, effort, prompts and schemas; the SDK client stays for anyone re-running the study with an API key.
CLIENTS = ("claude-cli", "api")
CLI_TIMEOUT_S = 1800
LIMIT_WAIT_S = 6 * 3600   # waiting out a usage limit, in all, before the run stops
# thinking counts toward max_tokens, so both leave room for it; the calls stream, as the SDK requires above ~21 000
MAX_TOKENS = {"segment": 32000, "code": 16000}
RUNS = (1, 2)
PRIMARY_RUN = 1               # decision G
MAX_FAIL_SHARE = 0.02
RETRIES = 1                   # one retry after a failed attempt, then logged as failed

BOOT_REPS = 10_000
BOOT_SEED = 42
VALID_BOOT_SEED = 43
DEGENERATE_MAX_SHARE = 0.05   # decision I
KAPPA_GATE = 0.6

# §5
Z_POWER = 1.960 + 0.842
DESIGN_EFFECT = 1.2
