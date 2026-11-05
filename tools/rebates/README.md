# Film incentive payout study

Code for `docs/research/rebates-design.md`, frozen at the signed tag `rebates-design`; the snapshot is hashed in
`docs/research/rebates-files.sha256`. This is the data-step code: it is tagged `rebates-data-step` before any outcome
column is read, and the estimation (`analysis.py`) comes after that tag and is frozen by `rebates-code`. The design is
the registration: read it first, change log included. Every test and the dry run use invented lists with the header
geometry of the real ones. The real lists were looked at through evidence numbers, the non-outcome columns, counts and
digit-masked shapes of the outcome cells; no outcome value was used to choose a rule.

- `config.py`: paths, tags, the two lists (file, state date, stated years, the counts of §0), S2026, the headline rates
  pinned in the change log, the 180-day margin, the §3 thresholds, the one pinned unreadable cell.
- `parse.py`: the lists into rows of the 17 printed columns. Words and boxes come from `pdftotext -tsv`; the columns
  are found from the header block of each page; a cell goes to the nearest column of its kind (date or amount) by
  position. Amounts are exact (int, or Fraction when haléře are printed), dates are `datetime.date`.
- `structure.py`: §3 checks 1 (through the parser), 2, 3, 6 and 7, and a coverage block of the non-outcome columns.
- `files.py`: hashes, the manifest, the gate, the stamp.
- `analysis.py`: placeholder; the estimation is written after `rebates-data-step`.
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
manifest hash, every file hash, the three tag commits, HEAD and the tree of `tools/rebates`. For now the run stops in
`analysis.run` with `NotImplementedError`. The code makes no tag.

## Design to code

| Design | Code |
|---|---|
| §2.1 lists, dates, stated years | `config.LISTS` |
| §2.2 columns, merging, amounts, dates, odd numbers | `parse.raw_rows`, `parse.convert`, `parse.parse_amount`, `parse.parse_date(s)`, `parse.EVIDENCE` |
| §2.8 S2026, §2.9 rates, §2.5 margin | `config.S2026`, `config.headline_rate`, `config.highest_rate`, `config.MARGIN_DAYS` |
| §3 check 1 | `parse.convert` (ParseError with the evidence number), `structure.failed_parse` |
| §3 checks 2, 3, 6, 7 | `structure.check_2`, `check_3`, `check_6`, `check_7` |
| §3 checks 4, 5; §1 Q1 to Q5; §6 | `analysis.py`, after `rebates-data-step` |
| Running and verification | `files.gate`, `files.stamp` |

## Verified facts about the lists (5 November 2026, no outcome value shown)

- Both lists are Excel prints, 6 A3 pages each, with the same header block repeated on every page at the same
  position and no page title or footer. Nothing wraps: long titles are cut with "…"; in list B some applicants sit
  about 1 pt above their row, and are merged into it.
- The printed columns are: evidence number, title, applicant, tax ID, registration request, registration certificate,
  evidence certificate, **Alokace** (one column), §48(1) deadline, cancellation of the evidence certificate, change of
  the evidence certificate, **Nová alokace** (one column), incentive decision 1st and 2nd/only (dates), **Filmová
  pobídka 1. splátka** and **2. nebo jediná** (amounts), and **VYPLACENO (aktuálně celkem)**. This is 17 columns, but
  not the 17 of design §2.2, which names allocation and new allocation by instalment (see Open items).
- Evidence numbers: list A 509 rows, 507 of the form `#P/####` to `###P/####` and two printed without the slash
  (`11P2019`, `10P2021`); list B 462, with `199/P/2025` and `64/2023`. The year is the four-digit suffix.
- A few cells print several dates separated by "/" or ",": evidence certificate in A for 33P/2017 and 65P/2019 (kept
  as a tuple), and some change dates (kept as a tuple). One change date in A (24P/2019) has a masked shape that is not a
  date (`##.##.####/####.####`); it is pinned in `config.UNREADABLE_CELLS`, counts as listed and has no value.
- Some new allocations, and a few incentive and paid amounts in B, print haléře; they are read as exact Fractions.

## Open items and notes

- **Column names against design §2.2.** P0 and P1 (§2.3) are written on "allocation 1st + 2nd/only" and "new
  allocation 1st + 2nd/only"; the lists have one allocation and one new allocation, and the instalment split is in the
  incentive amounts. How P0, P1 and the instalment amounts map must be decided and logged before `rebates-code`.
- Two evidence-certificate dates in one cell (33P/2017, 65P/2019): which one starts Q2 (§2.10) must be logged before
  `rebates-code`.
- Tests cannot read `tools/data/rebates`: a guard in `conftest.py` fails any `open` or subprocess argument under it,
  and a test proves it fires.
