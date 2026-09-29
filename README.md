# bsandova.com

This repository is the source of [bsandova.com](https://bsandova.com), the site of Barbora Šandová. It holds
research articles, tools and notes that are built from open data. For each article, the text, the published data,
the code that produced the numbers and the research designs sit side by side here, so every figure can be traced
and rebuilt.

## What is here

| Path | Contents |
|---|---|
| `index.html`, `texts/`, `cv/` | The site: front page, articles and CV (static HTML, no framework) |
| `texts/prague-*.html` | *Prague, measured*: the hub and Parts 1–5 |
| `docs/research/` | Research designs (registered analysis plans), file hashes, alignment codings |
| `docs/style/` | Editorial standard v1, house style, and the audit it rests on |
| `assets/` | Published data behind every figure (JSON/CSV), chart and map specs, photos, PDFs (`assets/pdf/`) |
| `assets/charts.js`, `assets/map.js` | Dependency-free interactive charts and maps, with a table view and a data link |
| `tools/` | Analysis and build scripts: `tools/zhmp/` (Part 1), `tools/praha/` (Parts 2–4), `tools/parking6/` (Part 5), `tools/charts/` and `tools/maps/` (figure specs), `tools/pdf.sh` |
| `ask/`, `deploy/` | *Ask the site*, an assistant that answers only from this site's data, and its server |
| `surf/`, `weather/` | Forecast verification pages and their daily verifiers |
| `infra/` | Cloudflare DNS and rules as Terraform |

## Prague, measured

Five studies of one city from the data it publishes about itself. Each part fixes its hypotheses, tests and
reporting sentences in a design committed before the analysis. Commit times are self-reported, and each article
says exactly what was registered when.

1. [Votes against in Prague's City Assembly, 2010–2026](https://bsandova.com/texts/prague-council)
2. [Housing estates and the 2025 vote in Prague's precincts](https://bsandova.com/texts/prague-rings)
3. [City grants to Prague's 57 districts and party alignment](https://bsandova.com/texts/prague-districts)
4. [New housing in Prague: permits, completions and the metro](https://bsandova.com/texts/prague-housing)
5. [Longer cars and Prague's paid kerb](https://bsandova.com/texts/prague-parking)

Every article ends with a **Reproduction** section that gives the script order and the command that rebuilds its
data. The raw inputs are public sources, listed with access dates and SHA-256 hashes in `docs/research/*-files.sha256`.
Large raw files are not committed. The scripts download them into `tools/data/`, which is ignored.

## Build and deploy

The site is static and served as Cloudflare Workers static assets (`wrangler.jsonc`). Every push to `main` deploys
through `.github/workflows/deploy.yml`, which runs `build.sh` first. That script stamps asset versions and
regenerates the sitemap, the feed and the changelog.

Local preview:

```sh
python3 -m http.server 8000            # then open http://localhost:8000/
./tools/pdf.sh                         # rebuild the PDFs of the series (needs Google Chrome)
```

The analysis scripts are Python. Each one names its dependencies in its docstring, for example:

```sh
uv run --no-project --with pandas --with numpy --with scipy python tools/zhmp/council_extended.py
```

## Citing

Each article gives its own citation and version under "cite as". For the repository as a whole, see
[`CITATION.cff`](CITATION.cff). Releases are archived on Zenodo.

## Licence

Code is under the MIT License ([`LICENSE`](LICENSE)). Text, figures, PDFs and published data are under CC BY 4.0
([`LICENSE-content`](LICENSE-content)). Photographs keep their authors' licences, named in each caption.

## Conventions

The pages follow [`docs/style/editorial-standard.md`](docs/style/editorial-standard.md):

- one kind per page (research, tool, note, hub);
- a metadata block and a dated change log on every page;
- registered labels used verbatim;
- intervals on every estimate.

Commits are one line, `<type>(scope): description`. Changes reach `main` through squash-merged pull requests.
