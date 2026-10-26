"""Frozen settings of the meme event study: paths, windows, seed and the events with their sources
(docs/research/memes-design.md §1, §2). No event date is written anywhere else."""
from __future__ import annotations

from pathlib import Path

from model import EventSpec

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools/data/memes"
RAW = DATA / "raw/pageviews.csv"
OUT = DATA / "out"
RESULTS = ROOT / "docs/research/memes-results.json"
MANIFEST = ROOT / "docs/research/memes-files.sha256"
DESIGN = ROOT / "docs/research/memes-design.md"

USER_AGENT = "bsandova-meme-event-study/0.1 (https://bsandova.com)"
PROJECT = "en.wikipedia"
START, END = "2021-01-01", "2024-12-31"
EST_WINDOW = (-150, -31)
EVENT_WINDOW = (-3, 30)
SENSITIVITY_WINDOWS = ((-3, 14), (-3, 60))
EXCLUSION_DAYS = 30
N_PLACEBO = None  # every admissible pseudo date (design §4.5); an int draws that many, seeded
MIN_CANDIDATES = 100
SEED = 42
SEASON_DAYS = 45       # same-season placebo check (design §7)
STRICT_EXCLUSION_DAYS = 90
NULL_JSON = ROOT / "docs/research/memes-placebo-null.json"
NULL_SHA = ROOT / "docs/research/memes-null-files.sha256"
NULL_SVG = ROOT / "docs/research/memes-estimation-windows.svg"
NULL_GAP = ROOT / "docs/research/memes-estimation-gap-by-month.csv"
NULL_TAG = "memes-null"
CODE_TAG = "memes-code"  # freezes tools/memes and the design before stage 1
LEBLANC = "Matt_LeBlanc"  # Friends actor in the pool; Matthew Perry died 28 Oct 2023 (design §8)

MF_CAST = ("Ed_O'Neill", "Sofía_Vergara", "Julie_Bowen", "Ty_Burrell", "Jesse_Tyler_Ferguson", "Sarah_Hyland",
           "Ariel_Winter", "Nolan_Gould", "Rico_Rodriguez_(actor)")
# `Rico_Rodriguez` of the spec is a disambiguation page, the infobox of Modern Family links `Rico_Rodriguez_(actor)`
# (design §2, deviation N).
# The spec's third control, Gary_Valentine, is a redirect to another person (design §2, deviation E).
KOQ_CAST = ("Leah_Remini", "Victor_Williams")

# External reference pool of the falsification, of the baseline of Kevin James and of two sensitivity runs (design §1, §2).
# Built on 26 October 2026 by pool.py from the infoboxes of these shows (Wikipedia text and page existence only) and
# frozen here; the full candidate list is docs/research/memes-reference-pool.json.
REFERENCE_SHOWS = (
    "2_Broke_Girls",
    "9JKL",
    "Abby's",
    "Alex,_Inc.",
    "American_Housewife",
    "Bless_This_Mess_(TV_series)",
    "Broke_(2020_TV_series)",
    "Call_Your_Mother",
    "Carol's_Second_Act",
    "Champions_(American_TV_series)",
    "Connecting",
    "Downward_Dog_(TV_series)",
    "Dr._Ken",
    "Fam_(TV_series)",
    "Fresh_Off_the_Boat",
    "Ghosted_(TV_series)",
    "I_Feel_Bad",
    "Indebted",
    "LA_to_Vegas",
    "Last_Man_Standing_(American_TV_series)",
    "Life_in_Pieces",
    "Living_Biblically",
    "Man_with_a_Plan_(TV_series)",
    "Marlon_(TV_series)",
    "Me,_Myself_&_I_(TV_series)",
    "Mike_&_Molly",
    "Mixed-ish",
    "Mom_(TV_series)",
    "New_Girl",
    "Outmatched",
    "Perfect_Harmony_(TV_series)",
    "Powerless_(TV_series)",
    "Rel_(TV_series)",
    "Schooled_(TV_series)",
    "Single_Parents_(TV_series)",
    "Speechless_(TV_series)",
    "Splitting_Up_Together",
    "Sunnyside_(American_TV_series)",
    "Superior_Donuts_(TV_series)",
    "The_Big_Bang_Theory",
    "The_Carmichael_Show",
    "The_Cool_Kids_(TV_series)",
    "The_Good_Place",
    "The_Great_Indoors_(TV_series)",
    "The_Kids_Are_Alright_(TV_series)",
    "The_Last_Man_on_Earth_(TV_series)",
    "The_Mick_(TV_series)",
    "The_Middle_(TV_series)",
    "The_Real_O'Neals",
    "The_Unicorn_(TV_series)",
    "Trial_&_Error_(TV_series)",
    "Undateable",
    "United_We_Fall_(TV_series)",
)
REFERENCE_POOL = (
    "Kat_Dennings",
    "Natalie_Morales_(actress)",
    "Zach_Braff",
    "Katy_Mixon",
    "Dax_Shepard",
    "Jaime_Camil",
    "Kyra_Sedgwick",
    "Patricia_Heaton",
    "Anders_Holm",
    "Otmara_Marrero",
    "Allison_Tolman",
    "Nina_Dobrev",
    "Randall_Park",
    "Adam_Scott",
    "Adam_Pally",
    "Kim_Matula",
    "Tim_Allen",
    "Colin_Hanks",
    "Jay_R._Ferguson",
    "Matt_LeBlanc",
    "Bobby_Moynihan",
    "Billy_Gardell",
    "Tika_Sumpter",
    "Anna_Faris",
    "Zooey_Deschanel",
    "Jason_Biggs",
    "Bradley_Whitford",
    "Vanessa_Hudgens",
    "AJ_Michalka",
    "Taran_Killam",
    "Minnie_Driver",
    "Jenna_Fischer",
    "Judd_Hirsch",
    "Johnny_Galecki",
    "David_Alan_Grier",
    "Kristen_Bell",
    "Joel_McHale",
    "Mary_McCormack",
    "Kaitlin_Olson",
    "Martha_Plimpton",
    "Walton_Goggins",
    "Nicholas_D'Agosto",
    "Chris_D'Elia",
    "Will_Sasso",
)
# first-billed titles dropped by rule, never replaced (design §2)
REFERENCE_DROPPED = {
    "9JKL": "dropped: the first-billed actor has no article link",
    "Dr._Ken": "dropped: the first-billed actor has no article link",
    "I_Feel_Bad": "dropped: redirect",
    "Marlon_(TV_series)": "dropped: the first-billed actor has no article link",
    "Rel_(TV_series)": "dropped: the first-billed actor has no article link",
    "Sunnyside_(American_TV_series)": "dropped: the first-billed actor has no article link",
    "The_Carmichael_Show": "dropped: the first-billed actor has no article link",
    "The_Last_Man_on_Earth_(TV_series)": "dropped: the first-billed actor has no article link",
    "The_Middle_(TV_series)": "dropped: already taken from an earlier show",
}

# TikTok pre-wave of the Stonestreet meme, 13 June 2023: -7..+30 days (design §4, deviation C)
TIKTOK_BLOCK = ("2023-06-06", "2023-07-13")
# the September wave of the same meme, kept out of the TikTok run's placebo pool: -3..+30 around 27 September
SEPTEMBER_BLOCK = ("2023-09-24", "2023-10-27")

# Later waves of the memes, kept out of the placebo pools (design §4.5). Know Your Meme (the parts read) dates one for
# Kevin James: his Tonight Show appearance on 23 January 2024. The page was read only to that paragraph, so the block
# runs from 1 January to 29 February 2024 instead of a window around that one date. The Cam page lists nothing dated
# after 6 October 2023, which lies in its own event window.
KEVIN_LATER_WAVES = ("2024-01-01", "2024-02-29")

STONESTREET = EventSpec(
    name="Stonestreet (Cam)", target="Eric_Stonestreet", controls=MF_CAST, event_date="2023-09-27",
    source_note="Know Your Meme, Cameron Tucker Smiling: earliest X post it lists, 27 Sep 2023",
    confirmatory=True, falsification=True, cast=MF_CAST, reference=REFERENCE_POOL, blocked=(TIKTOK_BLOCK,))
# the baseline of Kevin James is the external pool: Remini reacted to the meme herself and the median of two is a mean
KEVIN_JAMES = EventSpec(
    name="Kevin James", target="Kevin_James", controls=REFERENCE_POOL, event_date="2023-09-21",
    source_note="Know Your Meme, Kevin James Smirking Getty Image: earliest X post it lists, 21 Sep 2023",
    confirmatory=True, falsification=True, cast=KOQ_CAST, reference=REFERENCE_POOL,
    placebo_blocked=(KEVIN_LATER_WAVES,), second_regressor="Victor_Williams",
    detect_window=("2023-09-01", "2023-10-15"))
TIKTOK = EventSpec(
    name="Stonestreet TikTok pre-wave", target="Eric_Stonestreet", controls=MF_CAST, event_date="2023-06-13",
    source_note="Know Your Meme, Cameron Tucker Smiling: first notable TikTok post, 13 Jun 2023 (sensitivity)",
    cast=MF_CAST, blocked=(SEPTEMBER_BLOCK,))

# day 0 of the sensitivity check for H2: the most-liked listed post of the Cam meme (design §1)
SENSITIVITY_DAY0 = {"Stonestreet (Cam)": "2023-10-06"}

EVENTS = (STONESTREET, KEVIN_JAMES)
SENSITIVITY_EVENTS = (TIKTOK,)
ARTICLES = tuple(dict.fromkeys(a for e in (*EVENTS, *SENSITIVITY_EVENTS) for a in (e.target, *e.controls, *e.cast, *e.reference)))
