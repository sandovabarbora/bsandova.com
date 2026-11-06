# Film incentive payout study

Code for `docs/research/rebates-design.md`, frozen at the signed tag `rebates-design`; the snapshot is hashed in
`docs/research/rebates-files.sha256`. The data-step code was tagged `rebates-data-step` before any outcome
column was read; the estimation (`analysis.py`) came after that tag and is frozen by `rebates-code`. The design is
the registration: read it first, change log included. Every test and the dry run use invented lists with the header
geometry of the real ones. The real lists were looked at through evidence numbers, the non-outcome columns, counts and
digit-masked shapes of the outcome cells; no outcome value was used to choose a rule.

- `config.py`: paths, tags, the two lists (file, state date, stated years, the counts of §0), S2026, the headline rates
  pinned in the change log, the 180-day margin, the §3 thresholds, the one pinned unreadable cell, the label bands of
  §5, the Q2 horizons and at-risk minimum, and the three official planned-cost figures for Q5 (`OFFICIAL_Q5`).
- `parse.py`: the lists into rows of the 17 printed columns. Words and boxes come from `pdftotext -tsv`; the columns
  are found from the header block of each page; a cell goes to the nearest column of its kind (date or amount) by
  position. Amounts are exact (int, or Fraction when haléře are printed), dates are `datetime.date`.
- `structure.py`: §3 checks 1 (through the parser), 2, 3, 6 and 7, and a coverage block of the non-outcome columns.
- `files.py`: hashes, the manifest, the gate, the stamp.
- `analysis.py`: the estimation, written after `rebates-data-step`: the status rules of §2.4–2.5, Q1 with its bounds,
  label and decomposition, Q2 (Aalen–Johansen, exact Fractions), Q3, Q4, Q5, §3 checks 4 and 5, and §6 checks 1–8.
- `synth.py`: invented lists in the `pdftotext -tsv` format for the tests and `--synthetic`.
- `cli.py`: the stages.

## Running

No package is needed to run; the PDFs are read with poppler's `pdftotext` (a system tool, e.g. `brew install poppler`;
written against `pdftotext version 26.01.0`, which the structure report records). The tests need `pytest==9.1.1` only
and never call `pdftotext`.

    uv run --no-project --python 3.12 python -I tools/rebates/cli.py --verify-files    # every file under tools/data/rebates against the manifest
    uv run --no-project --python 3.12 python -I tools/rebates/cli.py --structure       # the data step; or python -m tools.rebates.cli --structure
    uv run --no-project --python 3.12 python -I tools/rebates/cli.py --synthetic       # the data step on invented lists
    uv run --no-project --python 3.12 --with pytest==9.1.1 python -I -m pytest -q -rs tools/rebates
    # after the author signs the tag rebates-code:
    nice -n 20 uv run --no-project --python 3.12 python -I tools/rebates/cli.py --run --unblind

`--structure` refuses unless every file under `tools/data/rebates/` is in the manifest with its hash (the annual
reports included, which this step does not open). It parses both lists, runs the checks and writes
`docs/research/rebates-structure.json`: counts, booleans, the day differences of the deadline column and evidence
numbers, no outcome value. It exits 1 on a stop of §3.

`--run` needs `--unblind` and refuses unless: `rebates-design`, `rebates-data-step` and `rebates-code` exist as
annotated tags (a branch of the same name does not count) and lie on one chain ending at HEAD; `tools/rebates` at HEAD
equals `rebates-code`; the manifest equals `rebates-data-step`; the design text above `## Change log` equals
`rebates-design`; the working tree is clean; and the snapshot matches the manifest. The results carry a stamp: the
manifest hash, every file hash, the three tag commits, HEAD and the tree of `tools/rebates`. The run also stops if a
data-step check of §3 stops. It writes `docs/research/rebates-results.json`. The code makes no tag.

## Design to code

| Design | Code |
|---|---|
| §2.1 lists, dates, stated years | `config.LISTS` |
| §2.2 columns, merging, amounts, dates, odd numbers | `parse.raw_rows`, `parse.convert`, `parse.parse_amount`, `parse.parse_date(s)`, `parse.EVIDENCE` |
| §2.8 S2026, §2.9 rates, §2.5 margin | `config.S2026`, `config.headline_rate`, `config.highest_rate`, `config.MARGIN_DAYS` |
| §3 check 1 | `parse.convert` (ParseError with the evidence number), `structure.failed_parse` |
| §3 checks 2, 3, 6, 7 | `structure.check_2`, `check_3`, `check_6`, `check_7` |
| §2.3 P0, P1; §2.4 D, D_eff; §2.5 mature, status | `analysis.Project` |
| §2.6 Q1 bounds, decomposition; §5 label | `analysis.bounds`, `analysis.decomposition`, `analysis.q1`, `analysis.label` |
| §2.10 Q2 | `analysis.observation`, `analysis.aalen_johansen`, `analysis.q2` |
| §2.7 Q3; §1 Q4; §2.9, §2.11 Q5 | `analysis.q3`, `analysis.q4`, `analysis.q5`, `config.OFFICIAL_Q5` |
| §3 checks 4, 5; §6 checks 1–8 | `analysis.check_4`, `analysis.check_5`, `analysis.section_6` |
| Running and verification | `files.gate`, `files.stamp` |

## Verified facts about the lists (5 November 2026, no outcome value shown)

- Both lists are Excel prints, 6 A3 pages each, with the same header block repeated on every page at the same
  position and no page title or footer. Nothing wraps: long titles are cut with "…"; in list B some applicants sit
  about 1 pt above their row, and are merged into it.
- The printed columns are: evidence number, title, applicant, tax ID, registration request, registration certificate,
  evidence certificate, **Alokace** (one column), §48(1) deadline, cancellation of the evidence certificate, change of
  the evidence certificate, **Nová alokace** (one column), incentive decision 1st and 2nd/only (dates), **Filmová
  pobídka 1. splátka** and **2. nebo jediná** (amounts), and **VYPLACENO (aktuálně celkem)**. This is 17 columns, but
  not the 17 of design §2.2, which names allocation and new allocation by instalment (see the change log).
- Evidence numbers: list A 509 rows, 507 of the form `#P/####` to `###P/####` and two printed without the slash
  (`11P2019`, `10P2021`); list B 462, with `199/P/2025` and `64/2023`. The year is the four-digit suffix.
- A few cells print several dates separated by "/" or ",": evidence certificate in A for 33P/2017 and 65P/2019 (kept
  as a tuple), and some change dates (kept as a tuple). One change date in A (24P/2019) has a masked shape that is not a
  date (`##.##.####/####.####`); it is pinned in `config.UNREADABLE_CELLS`, counts as listed and has no value.
- Some new allocations, and a few incentive and paid amounts in B, print haléře; they are read as exact Fractions.

## The snapshot

`tools/data/rebates/2026-11-05/` (gitignored, hashed in `docs/research/rebates-files.sha256`): the two lists, the
Fund's notice of 27 March 2026 (S2026), the applicant guide 2025, the law texts under `law/` (§2.9 rates), and under
`annual/` the Fund's annual reports 2018–2022 (`annual-reports-2018-2022.zip`) and 2025 (`annual-report-2025.pdf`).
The code reads only the two lists; the annual reports are the source of the three official Q5 figures (2020, p. 38;
2021, p. 35; 2025, annex p. 84), copied into `config.OFFICIAL_Q5` with their basis and logged in the design's change
log. They are shown beside Q5 and inform no label.

## Notes

- The column decisions (P0 = Alokace; P1 = Nová alokace where printed, else Alokace; the earlier of two
  evidence-certificate dates starts Q2) and the choices made at the estimation step are in the design's change log.
- Tests cannot read `tools/data/rebates`: a guard in `conftest.py` fails any `open` or subprocess argument under it,
  and a test proves it fires.
