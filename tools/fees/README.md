# Licence-fee funding study

Code for `docs/research/fees-design.md`, frozen at the signed tags `fees-design` and `fees-data-step`; the code itself is
frozen by `fees-code`, because `fees-data-step` sits on the snapshot commit (change log, 3 November 2026). The design is the
registration: read it first, change log included. Every test and the dry run use invented files with the layout of the real
ones. The real files were looked at through labels, positions and counts (`--structure`); a few masked prints showed digit-group
shapes (magnitudes) of some lines, which the change log records under "exposures during code and review". No real value
was used to choose a rule.

- `config.py`: paths, tags, every legal amount and threshold with its source, the living-minimum amounts, the §6(3)
  notice override (empty: none found as of 3 Nov 2026), the tie threshold and the label band.
- `legal.py` (pure): Q-A. The §6(2) rule with half-year July steps and the restart at the year of the increase, the
  §10a(3) clause in readings R1 (sum) and R2 (compounded) with the restart at the year of the crossing, the three
  paths, baselines A and B, the inflation path and deflator, the 12-member range and its label. Integers, Fractions and
  Decimal only; every ceiling is an integer ceiling.
- `alloc.py` (pure): largest-remainder allocation to whole crowns.
- `model.py` (pure): Q-B. Decile incomes from SILC Tab. 3a, exemption bounds E0 and E1, payer shares and their cap,
  VAT and excise incidence through the maps and the quintile-to-decile split, PIT bases, CIT to firms, the scenarios,
  check 2 of §3 on every allocation, the labels of §6, the monotonicity note, the firm range and remainder, the seniors' cut.
- `analysis.py` (pure): puts Q-A, Q-B, readings B and C, firms, seniors and the checks into one results dictionary.
- `readings.py` (pure): the pre-written readings filled from the numbers.
- `parse.py`: the parsers. Every source has a `locate_*` step (rows, columns, raw tokens) and a `parse_*` step that converts.
- `xlsx.py`: a stdlib `.xlsx` reader; `values=False` turns every number into a sentinel.
- `inputs.py`: reads the sources named in a `Sources` (the real snapshot, or the invented one).
- `structure.py`: the layout stage; prints labels, positions and counts only.
- `files.py`: hashes, the manifest, the frozen-code gate, the file stamp.
- `synth.py`: invented snapshot files (a minimal `.xlsx` writer, text and CSV fixtures) for the tests and the dry run.
- `cli.py`: the stages.
- `vat_map.csv`, `excise_map.csv`: the committed, hashed maps. Not edited.

## Running

No package is needed to run; the PDFs are read with poppler's `pdftotext` (a system tool, required: install poppler,
e.g. `brew install poppler`; written against `pdftotext version 26.01.0`; the run records its version in the results and the author should note it at tagging) and the spreadsheets with the standard library. The tests need `pytest==9.1.1` only.

    uv run --no-project --python 3.12 python -I tools/fees/cli.py --synthetic            # invented files, no gate
    uv run --no-project --python 3.12 python -I tools/fees/cli.py --verify-files         # every file under tools/data/fees against the manifest
    nice -n 20 uv run --no-project --python 3.12 python -I tools/fees/cli.py --structure # labels, positions, counts of the real files
    uv run --no-project --python 3.12 --with pytest==9.1.1 python -I -m pytest -q -rs tools/fees
    # after the author signs the tag fees-code:
    nice -n 20 uv run --no-project --python 3.12 python -I tools/fees/cli.py --run --unblind    # writes docs/research/fees-results.json

`--run` needs `--unblind` and refuses unless: the three tags `fees-design`, `fees-data-step` and `fees-code` exist as
annotated tags (a branch of the same name does not count) and lie on one chain ending at HEAD; `tools/fees` at HEAD equals
`fees-code`; the manifest and both maps equal `fees-data-step`; the design text above its change log equals `fees-design`;
`tools/fees`, the design text and the manifest have no uncommitted changes; and every file under `tools/data/fees/` is in
`docs/research/fees-files.sha256` with the listed hash (the two maps through their `../../fees/` path); a file that is missing,
changed or not listed refuses. The code makes no tag.
`results.json` carries a stamp: the manifest hash, every file hash, the map hashes, the commits of `fees-design`,
`fees-data-step` and `fees-code`, HEAD and the tree hash of `tools/fees`. Standard library only, one thread; run under `nice -n 20`.

## Design to code

| Design | Code |
|---|---|
| §2.1 arithmetic, largest remainder | `alloc.largest_remainder`, Fractions throughout, `legal.step_up` |
| §2.2 current law, window, restart, notice | `legal.current_law_steps`, `legal.monthly_amounts`, `config.NOTICE_OVERRIDE` |
| §2.3 bill, R1 and R2, restart | `legal.bill_path`, `legal.bill_exceeds` |
| §2.4 units, E0 and E1, payer share | `model.exempt_flags`, `model.payer_shares`, `model.fee_today`, `parse.parse_silc_deciles` |
| §2.4 after: pool, VAT, excise, PIT, CIT | `parse.pool_lines`, `model.spending_parts`, `model.tax_weights`, `model.after` |
| §2.5 sharing, gross lines | `config.SHARES`, `model.state_lines` (used only if gross lines exist) |
| §2.6 inflation, deflator, shock | `parse.cnb_annual`, `legal.inflation_series`, `legal.price_levels` |
| §2.7 paths, baselines, X | `legal.qa_member`, `legal.baseline_2026` |
| §3 checks 1 and 2 | `model.firms_today` (descriptive), `model.firm_range`, `model.CheckFailure` |
| §4 range, §6 labels | `legal.qa_members`, `legal.qa_label`, `model.label_*` |
| §7 checks 1 to 9d | `analysis.run`, key `checks_reported` |
| §1 readings A, B, C, firms | `readings.py` |
| Seniors | `model.seniors_cut`, `parse.parse_silc_seniors` |

## Verified facts about the sources (layout only, 3 November 2026, no value shown)

- SILC Tab. 3a (`silc/16002126_data/1600212603a.xlsx`, identical bytes to the individually linked copy): deciles in columns
  D to M by the headings "nejnižších ... nejvyšších"; rows by label: "Počet domácností" (absolute), "Členů", "vyživovaných dětí",
  "OECD modif." (consumption units per household), "A. Hrubé peněžní příjmy", "1." and "2." (employment, self-employment),
  "C. Daň z příjmů fyzických osob", "E. Čisté peněžní příjmy" (annual, per consumption unit). Income year read from the label "PŘEHLED PŘÍJMŮ za rok".
- SILC Tab. 10a: columns found by "a více let" (one person 65+) and "aspoň jeden ... let a více" (two adults); per-person
  income; a dash in the children row means none.
- Consumption: Tab. 3a (`1600662631.xlsx`, sheet "Charakteristiky") gives households and members by quintile; Tab. 3b
  (`1600662632.xlsx`, sheet "Vydaje") gives annual CZK per person by CZ-COICOP code, read down to the row "Struktura výdajů v %";
  a label that continues on the next row carries its numbers on that row. All 108 codes of both maps and their parents are in the table.
- State budget (Part G, Tab. 2a, tis. Kč): the column "Skutečnost" under the year 2025, found per page from the header
  (the page layouts differ by a few characters); a label that wraps puts its numbers on the next line; some items have an
  empty cell under 2025 (listed in the results, read as 0). Part C has national (gross) lines for VAT, CIT and mineral-oil
  excise, none for PIT, so check 7 is not computable.
- ČNB key indicators, sheet "Česká verze": row "Spotřebitelské ceny (%, meziročně, průměr)", quarters in groups under "čtvrtletí roku".
- ČT: budget line "příjem z televizních poplatků" (tis. Kč, column of 2026); 2025 report: sentence "K 31. 12. 2025 měla Česká televize
  v evidenci celkem N domácností" and the table row with the column "Skutečnost".
- ČRo: chart item "Výnosy z rozhlasových poplatků" (thousand CZK); 2025 report: stock table row "FYZICKÉ OSOBY" in the column "k 31. 12. 2025"
  and the sentence of realised revenue.
- RES: `res_data.csv`, entities with an empty DDATZAN by KATPO; all 20 codes of the list 579 occur; no band straddles the schedule classes.

## Open items and notes

- Firms today are reported descriptively (remainder, schedule-implied amount, ratio; no pass or fail), as the design change log of 3 Nov 2026 (before the code tag) says.
- Checks 6 and 7 of §7 are reported as not computable (no household-level ratios in the tables; no national PIT line).
- Items with an empty cell under Skutečnost 2025 in Tab. 2a are read as 0 and listed in the results, except that a pool item
  with an empty cell, or any pool item absent other than 1226 and 1227 (`config.POOL_ABSENT`), stops the run.
- Tests cannot read `tools/data/fees`: a guard in `conftest.py` fails any `open` or subprocess argument under it, and a test proves it fires.
