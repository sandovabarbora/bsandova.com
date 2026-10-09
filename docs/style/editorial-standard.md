# Editorial standard, bsandova.com (v1, 29 September 2026)

Every page listed in All work meets this standard. The prose rules of `long-articles.md` apply site-wide. Where
the two differ, this file wins: length now has caps, and superseded material leaves the current article.

## 1. Kinds

Every page is exactly one kind and says so in its kicker.

- **Research** states a question and a design and reports inference.
- **Tool** is a public artefact with code, tests and a worked example.
- **Note** is a dated descriptive or creative piece that makes no inferential claim.
- **Hub** is an index of other pages.

A page that cannot meet the standard for its kind moves down a kind or is retired. It is never published half-way.

## 2. Length caps (body text, without tables, captions, references and the folded metadata)

| Kind | Words |
|---|---|
| Research | at most 3 500 |
| Tool | at most 1 500 |
| Note | at most 900 |
| Hub | at most 1 000 |

There is no minimum length (dropped 9 October 2026): a page says what its evidence supports and stops; a short
null result is not padded.

## 3. Header, in the same order on every page

1. **Kicker**: kind · series and part · object and period. At most 12 words. It carries no status word such as
   "pre-registered" unless §6 allows it.
2. **H1**: names the object and, for research, the finding or the question. It is not a slogan and does not use the
   "not X but Y" device.
3. **Deck**: one sentence of at most 35 words that gives the question and the main result with its registered
   label.
4. **Facts strip**: at most four cards. Each card has a number, its unit, and its interval or the words
   "administrative count".
5. **The short version** (`details.tldr`, "Overwhelmed? Here's the short version"): 3–5 bullets. It is the one
   place for the gist. It repeats no sentence of the deck and no card of the facts strip. It covers what was
   found, how far to trust it and what it does not show.

## 4. Metadata block, directly under the short version, in mono, one line each

- **Published** date · **Updated** date · **Version** n, linked to the article's change log on the changelog page
  (`changelog/#<slug>`).
- **Status**:
  - research: registered study / exploratory;
  - tools: tool vX.Y;
  - notes: note.
- **Registration**: see §6.
- **Review**: only when there was an external review, named with affiliation. Otherwise the block has no review row, and the page makes no claim about referees or review anywhere.
- **Data**: sources with access or snapshot dates, the licence, and the hash list if there is one.
- **Code**: repository path, the commit of the published version, and the command that rebuilds the page's data.
- **Cite as**: Šandová, B. (2026). *Title*. bsandova.com/texts/slug, version n.
- **Licence**: code MIT; text, figures and data CC BY 4.0.

## 5. Body

Research sections come in this order:

1. The question and contribution: one paragraph, placed against at least three external references.
2. Data.
3. How this was done: design, estimand, inference unit and effective n.
4. The tests, with the table.
5. Results, one section per question.
6. Robustness, as a table.
7. What changed after registration: a dated list, each change told once. Since 8 October 2026 it is kept in the
   article's change log (`docs/changelogs/<slug>.html`, under `<slug>-changes`) and linked from the registration row of
   the metadata, not printed in the article.
8. What this means: one short section (at most 200 words) that says what the results support and what they do not,
   for someone who has to decide something about the object studied. It separates what is measured from what is
   inferred, gives no advice that the design cannot carry, and names the decision-relevant quantity with its
   uncertainty.
9. What this does not show.
10. Reproduction.
11. References.
Change log and corrections are dated and kept outside the article, in `docs/changelogs/<slug>.html`, shown on the
changelog page under the article's anchor; the article links to them from its version number and never carries
them in its text (changed 8 October 2026: the logs made the articles longer and broke the reading).

**Tools** follow this order:

1. What it does and prior art, with at least two comparable tools named.
2. Method.
3. Worked example with real output.
4. Tests and measured error.
5. Limits.
6. Install and reproduce.
7. References.

**Notes** have at most three sections and a dated kicker. They make no statistical claims beyond descriptive counts
with their source.

## 6. Registration claims

- "Pre-registered" requires a tamper-evident anchor dated before any outcome data were joined: an OSF
  registration, a Zenodo DOI, or a signed tag pushed to the public remote. The page cites it by its id.
- A design committed on the author's own branch before the results commit is described as follows: "registered
  analysis plan: design committed at `<hash>` on `<date>`, before the results commit `<hash>`; commit times are
  self-reported, and the branch was pushed after the analysis." Where GitHub's activity log shows the design on the
  public branch before the results, the last clause is replaced by the push times it records, with the note that a
  push is not a tamper-evident anchor (amended 9 October 2026). This applies to Parts 1, 3, 4 and 5 (parking).
- Where the design first appears in the same commit as the results (Part 2), the only permitted wording is "design
  written and reviewed before modelling; not independently timestamped."
- Everything the author had already seen when registering is disclosed in the article, not only in the design
  file.
- A registered study commits its design before any outcome is joined, and the article cites that commit and its date with the wording above. An OSF registration is optional (author's decision, 1 October 2026).

## 7. Numbers and units

- **Formatting**: thousands separated by a space (10 565); a space before % (1.6 %); percentage points written as
  pp; a real minus sign (−).
- **Consistency**: one unit per quantity site-wide. The same dataset has one name and one count everywhere.
- **Intervals**: every estimate has one, labelled by type: 95 % CI, 90 % CI (one-sided test at α), range under the
  registered inputs, or bootstrap by `<cluster>`. The level matches the decision rule.
- **Counts and samples**: population counts are marked as such. The effective sample (clusters) stands next to a
  headline estimate.
- **Registered labels**: supported, not supported, inconclusive, indeterminate, uninformative and underpowered are
  used verbatim. They read the same in deck, facts, table, body, hub and CV.
- **Tallies**: there are no tallies across families of tests.
- **Dates and seasons**: seasons are written 2014/15 and dates 29 September 2026.
- **Checking**: every number in the prose is generated from the published data or diff-checked against it.

## 8. Figures

- Figures are numbered in order of appearance.
- The caption gives what is plotted, its unit, n, the band and the source with its date.
- No superseded figures appear in a current article.
- Research has at most six figures plus one map. Tools and notes have at most three.
- Every figure is interactive where its data are public (`assets/charts.js`, `assets/map.js`) and has alt text.
- Colours named in a caption match the rendered palette.

## 9. References

- References are numbered by first citation. Every entry is cited, and every citation resolves to an entry.
- Each entry has one work, in the form: author (year). Title. Outlet. URL. Accessed date.
  - Data sources add the table code and the snapshot date.
  - Software adds the version.
- Primary sources are preferred.
- Private material is marked "(private; not verifiable)", and so are the claims that rest on it.

## 10. Prose

- The rules of `long-articles.md` apply.
- No promotional adjectives. No policy advice drawn from non-causal evidence.
- Causal language only for identified effects. Anything else is called "descriptive".

## 11. Series

- Parts are numbered by publication order, with no gaps. Prague, measured has Parts 1–5; parking is Part 5.
- Unpublished work does not appear on the hub or anywhere on the site.
- Every part links to the hub and to its neighbours.

## 12. Gate

- A page enters All work only after a pass against §3–§10.
- The pass is recorded in its change log (`docs/changelogs/<slug>.html`) as "Checked against editorial standard v1
  on `<date>`".
