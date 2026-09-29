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
| `surf/`, `weather/`, `status/`, `watch/`, `library/`, `atlantic/`, `changelog/` | Live pages; `surf/` and `weather/` also hold their daily collectors and verifiers |
| `assets/` | Published data behind every figure (JSON/CSV), chart and map specs, photos, PDFs; `charts.js` and `map.js` draw them |
| `style.css`, `text.css`, `a24.css`, `404.html`, `favicon.ico` | Shared styles and site furniture |
| `tools/site/` | Build and upkeep: editorial-standard check, changelog, sitemap, feed, top bar, OG cards, paper figures, PDFs, status check |
| `tools/figures/` | Static figure generators for single articles |
| `tools/zhmp/`, `tools/praha/`, `tools/parking6/` | Analyses of *Prague, measured* Parts 1, 2–4 and 5 |
| `tools/charts/`, `tools/maps/` | Interactive chart and map specs |
| `tools/lottery/`, `tools/detector/`, `tools/delay-atlas/`, `tools/quaesitor/`, `tools/demos/` | Other articles' analyses, the Quaesitor page generators, the cutover demo |
| `docs/research/`, `docs/style/`, `docs/superpowers/` | Research designs and file hashes; editorial standard and audits; design specs and plans |
| `ask/`, `deploy/`, `sitewitness.toml` | *Ask the site*, an assistant that answers only from this site's data: page, eval, Worker proxy, Fly server, config |
| `infra/` | Cloudflare DNS and rules as Terraform |
| `build.sh`, `wrangler.jsonc`, `_redirects`, `.assetsignore` | Build, deploy config, 301s, and what is kept off the site |

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

## Registration branches and releases

The branches `feature/PRAHA-1x_council-extended`, `feature/PRAHA-2x_rings-extended`,
`feature/PRAHA-3x_districts-extended`, `feature/PRAHA-4x_housing-extended`, `feature/PRAHA-6_parking-study` and
`docs/PARK-2_m1g-correction` are kept on purpose. They hold the design and results commits in their original order,
which the squash merges into `main` do not keep. Releases (`vX.Y.Z`) are archived on Zenodo.

Errors in an article can be reported with the issue form *Report an error in an article*. Confirmed corrections are
dated in the article's change log.

## Build and deploy

The site is static and served as Cloudflare Workers static assets (`wrangler.jsonc`). Every push to `main` deploys
through `.github/workflows/deploy.yml`, which runs `build.sh` first. That script stamps asset versions and
regenerates the sitemap, the feed and the changelog.

Local preview:

```sh
python3 -m http.server 8000     # then open http://localhost:8000/
./tools/site/pdf.sh             # rebuild the PDFs of the series (needs Google Chrome)
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
