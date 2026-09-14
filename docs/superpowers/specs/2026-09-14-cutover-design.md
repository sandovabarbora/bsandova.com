# cutover — prove that nothing changed

Date: 2026-09-14 · Status: approved in chat · Owner: Barbora Šandová

## Purpose

A small, public Python package that proves two tables are the same before a
migration's consumers are repointed. It produces the two numbers that end a
cutover argument: *0/0 mismatches across N columns* and *K/K partitions with an
identical fingerprint*. It is the reusable form of the method used on the dbt
salary-recompute cutover and the GA4 backfill described in
`texts/engineering.html`.

Package name: `cutover` (free on PyPI; `parity` is taken). Licence Apache-2.0.
Repository: `~/Documents/Coding/cutover`, GitHub `sandovabarbora/cutover`.

## Non-goals (v1)

- Computing the diff inside a remote warehouse (Ibis-style pushdown).
- Schema-evolution rules ("this rename is allowed").
- Any GUI or server. One CLI, one Python function, one HTML file out.

## Inputs

Everything becomes a `pyarrow.Table`. Built-in readers, chosen by URI/extension:

| form | reader |
|---|---|
| `x.parquet`, `x.csv` | DuckDB `read_parquet` / `read_csv_auto` |
| `duckdb:///path.db?table=t` or `?sql=...` | DuckDB |
| `sqlite:///path.db?table=t` | DuckDB sqlite extension |
| `postgres://...?table=t` or `?sql=...` | DuckDB postgres extension |
| `pyarrow.Table`, `pandas.DataFrame`, `polars.DataFrame` (Python API only) | as is |

Extra `cutover[bigquery]`: `cutover.sources.from_bigquery(sql, project=None)` →
`QueryJob.to_arrow()`. No other clients in v1.

## Comparison

`compare(old, new, *, key, partition=None, tolerance=None, ignore=(), sample=20)`

Computed in an in-process DuckDB connection over the two Arrow tables, in this
order; every step contributes to the report, and later steps run on whatever
survives the earlier ones.

1. **Schema.** Columns only in old, only in new, and type differences on shared
   columns. Comparison proceeds on the shared columns with compatible types;
   the rest is reported, and any of the three lists non-empty fails the run
   unless `--allow-schema-drift`.
2. **Key.** Null keys and duplicate keys on each side, with counts and samples.
   A non-unique key on either side is a FAIL with reason `key_not_unique`,
   because a column diff on a non-unique key is meaningless. The run still
   reports schema and row-set results.
3. **Row set.** Keys only in old, only in new: counts and up to `sample` rows.
4. **Columns.** On keys present on both sides, per column: number of mismatches,
   with `NULL = NULL`, exact equality for non-floats, and for floats
   `abs(a-b) <= abs_tol + rel_tol*abs(b)` with per-column `tolerance={"amount":
   0.01}` (absolute) or `{"amount": ("rel", 1e-6)}`. Up to `sample` mismatching
   rows per column, showing key, old, new.
5. **Fingerprint by partition.** If `partition` is given: for each partition
   value, a hash of the rows ordered by key on each side (DuckDB `md5` over a
   canonical string of the row, aggregated with `string_agg` ordered by key,
   respecting tolerance-free exact values). Reports `identical / total`
   partitions and the list of differing ones. Without a partition, one
   fingerprint per side.
6. **Verdict.** PASS iff schema drift is empty (or allowed), keys are unique,
   both row-set differences are 0, every column has 0 mismatches, and every
   partition fingerprint matches. FAIL otherwise, with `reasons: [...]`.

Ignored columns (`ignore`) are dropped from steps 1, 4 and 5 and listed in the
report.

## Output

- `Report` object: `.passed`, `.reasons`, `.schema`, `.keys`, `.rows`,
  `.columns`, `.partitions`, `.to_dict()`, `.to_json()`, `.to_html()`,
  `.to_text()`.
- CLI `cutover OLD NEW --key k [--key k2] [--partition p] [--tol col=0.01]
  [--tol col=rel:1e-6] [--ignore col] [--sample 20] [--allow-schema-drift]
  [--json out.json] [--html out.html] [--quiet]`. Prints the text report.
  Exit code 0 PASS, 1 FAIL, 2 error (unreadable source, bad arguments).
- HTML: one self-contained file, no external resources, dark neutral palette,
  readable on a phone; sections in the order above, samples as tables.

## Scale and failure

- DuckDB does the joins and hashes; memory limit configurable
  (`--memory 4GB`), spill to a temp directory. Samples are `LIMIT`ed, never
  materialised in full.
- Timezone-aware timestamps are compared as UTC instants; naive timestamps as
  given. Decimal vs float is a type difference (reported), not a coercion.
- Reader errors are exit 2 with the underlying message; comparison problems
  (non-unique key, drift) are exit 1 with reasons.

## Tests

`pytest`, synthetic tables built in the tests (no fixtures on disk):

- identical tables → PASS, 0/0, K/K
- dropped rows → `rows.only_in_old` = n, FAIL
- extra rows → `rows.only_in_new` = n, FAIL
- float drift inside tolerance → PASS; outside → FAIL with the column named
- NULL flip → mismatch counted once, NULL=NULL not counted
- type change on a shared column → schema drift, FAIL; with allow flag the
  column is skipped and the rest compared
- duplicate key on one side → FAIL `key_not_unique`, row set still reported
- one broken partition → `partitions.identical = K-1`, that partition listed
- ignore column → its drift does not fail
- CLI: exit codes 0/1/2, JSON and HTML written, HTML has no `http` reference

## Repository

`uv` project, `ruff`, `pytest`, GitHub Actions: test matrix Python 3.10–3.13,
publish to PyPI on tag via trusted publishing (configured by the owner once).
README with the two commands above and a 30-second example. CHANGELOG.

## On the site

`texts/cutover.html`, "How to prove a cutover": the method, the six steps, and a
demo on NYC TLC yellow-taxi parquet: a "legacy" daily aggregate written in
pandas against a "new" one in SQL, run through `cutover`, with the report
embedded and whatever it finds reported as found. Row in section E of
`index.html` with chips read / code / pypi.
