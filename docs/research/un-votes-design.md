# Did Czechia's UN votes change in the periods of its governments? — research design

**Status: pre-specified analysis, design committed 15 October 2026, before any Czech vote in the data was read.** The
headline question (Q1) is tested on General Assembly votes cast after that date: the votes of the 81st session from
16 October to 31 December 2026, most of them in November and December. The steps follow in dated commits: design →
screening → code → results (stage A) → results (stage B). Commit times are self-reported; the signed tag
`un-votes-design` fixes this text. Deviations are listed, dated, in the change log.

## 0. What has already been seen

- **The author** has never worked with UN voting data; her master's work on voting (Franco-German voting after the
  Aachen treaty) was on the EU Council only (stated 13 October 2026). What she knows of Czech UN votes from the news,
  stated on 15 October 2026: she has heard very little about it ("minimálně jsem o tom slyšela").
- **Votes already cast.** Q1's after period starts on 16 October 2026. The votes of 15 December 2025 – 15 October 2026 have been
  cast and are public (those of 15–30 December 2025 are in the data file); no Czech position on them has been read
  for this study. They are not part of Q1 (§1).
- **Feasibility check (13 October 2026).** A separate agent read Voeten's General Assembly files (Harvard Dataverse,
  doi:10.7910/DVN/LEJUQZ, v39) and UNGA-DM (Fjelstul, Hug and Kilby, 2025), with every Czech row dropped at load, and
  reported for the other EU members, sessions 65–77, the number of recorded votes per session and how often the other
  EU members split. Two numbers about Czechia reached it unsought in web-search snippets: "Poland is Czechia's closest
  UN voting partner, 97.5 % of 2,391 shared votes since 1946" and, for Visegrad and Western Balkan states as a group in
  2013–2023, "over 80 % pairwise coincidence". Neither is per government or relative to the EU. Poland is a comparison
  member here.
- **The data file.** The UN Digital Library's *General Assembly Voting Data*, version 5 (6 February 2026;
  https://digitallibrary.un.org/record/4060887), downloaded by the author on 15 October 2026; sha256
  `9b8ddbee7490d9e31aa1b2f852c0b074ff58afd9e4bb67e629bcddbdde7852f1`. Its description says it ends at resolution
  80/246 of 30 December 2025. Before registration, only its description, its column names and the rows of the other
  members were read (§5); Czechia is dropped in the query that reads the file.
- **Review.** A draft was read by an independent methods reviewer, who ran checks on the other members only and
  reported no Czech exposure. The version below takes in the review: the after periods start a month after each
  change (the December plenary re-adopts texts voted in committee under the old government), Q1 counts only votes cast
  after registration, the margins follow the placebo spread, the intervals resample agenda items, and the comparison
  set is the EU-27 throughout.
- **Prior expectation.** Stated by the author on 15 October 2026, before any Czech vote was read: "I expect a greater lean towards 'Trumpist' policy, and perhaps a greater lean towards Hungary, Russia and
  Slovakia, though with the Russian invasion of Ukraine in mind" (in Czech: "očekávám větší náklon k 'trumpistické'
  politice a možná větší náklon Maďarsko, Rusko, Slovensko, ale s ohledem na ruskou invazi na Ukrajinu"). Read against
  the questions: higher agreement with the United States, Hungary and Slovakia, perhaps with Russia, in the third Babiš
  period (Q3). She stated no expectation for the EU majority (Q1) or for the earlier changes (Q2).

## 1. Questions

Each question compares Czechia's change with the change of the other EU-27 members over the same votes (a difference
in differences on votes), so that a change in what the Assembly votes on, or in the United States or Russia
themselves, is not read as a Czech change. These are associations: a change of government comes with a new foreign
minister, new officials and a changing world agenda, and none of it is separated here. "In the period of a
government" never means "because of it".

Cabinet dates are the appointment of the cabinet with its foreign minister, who instructs the UN mission: 13 December
2017 (Babiš, first cabinet; pooled with the second, §8), 17 December 2021 (Fiala), 15 December 2025 (Babiš, third
cabinet). Each after period of Q2 starts **30 days after** the cabinet date; votes in those 30 days are in neither
period. Q1's after period starts the day after registration (16 October 2026), later than that. Dates are plenary vote dates, as
in the file: a plenary vote after registration counts even if the text was voted in committee before it. The Sobotka
period starts at the start of the data (29 January 2014), without a buffer.

- **Q1, the third Babiš government (headline, stage B).** β₁: Czechia's change in agreement with the EU majority from
  the Fiala period (votes 16 January 2022 – 14 December 2025) to the votes cast from 16 October to 31 December 2026, net
  of the other members' change. Nothing else is the headline.
- **Q2, the two earlier changes (stage A).** β₂a: Sobotka period (29 January 2014 – 12 December 2017) to the Babiš
  period (12 January 2018 – 16 December 2021). β₂b: the Babiš period (12 January 2018 – 16 December 2021) to the Fiala
  period (16 January 2022 – 14 December 2025).
- **Q3, other partners (secondary, descriptive labels).** For each change, β with agreement with the **United
  States**, **Russia**, **Hungary** and **Slovakia** in place of the EU majority. The partner is neither focal nor a
  comparison member. Twelve labels are reported without a correction for multiplicity; none is read on its own.
- **Q4, which votes (descriptive).** The votes of each period on which Czechia's position differed from the EU
  majority, with title and agenda item; in stage B also the votes of 15 December 2025 – 15 October 2026, as a separate block.

## 2. Data and definitions

- **Source.** UN Digital Library, *General Assembly Voting Data*. Stage A (Q2, and Q1's before period) uses version 5
  as fixed by its sha256 above. Stage B uses the first version that covers resolutions adopted to 31 December 2026;
  the rows up to 30 December 2025 are compared with version 5 and the number of changed rows is reported; if any
  changed, Q2 is reported on both versions and Q1's before period on version 5. The file holds the recorded vote of
  each member on each **adopted** resolution; paragraph votes, amendments and failed drafts are not in it (§8).
- **Votes.** Every vote (`undl_id`) from 29 January 2014, regular and emergency special sessions, dated by `date`.
  Duplicate (vote, member) rows are counted and the first kept.
- **Positions.** `ms_vote` Y, N or A; X (not voting, absent) is missing for that member on that vote.
- **EU-27.** The 27 members since February 2020, in every period, for the majority and the comparison; the United
  Kingdom is not used at all, so the set never changes inside a window. Croatia joined before 2014.
- **Agreement** of member *c* with position *p*: 1 if equal; 0.5 if one of the two is A and the other Y or N; 0 if
  one is Y and the other N. Missing if either is missing.
- **EU majority.** For the focal member *f*: the most common position among the other EU-27 members that voted. For a
  comparison member *c*: the most common position among the EU-27 members other than *c* and *f*. A tie drops the vote
  for that member. Ties among the other EU members are rare (2 of 1,190 votes since 2014, without Czechia); Czechia's
own are counted in stage A.
- **Partners (Q3).** The vote of USA, RUS, HUN or SVK.

## 3. Screening (before any agreement is summarised)

Reported for the whole file; none of it reads a Czech position.

1. Rows and votes per session and per year; duplicate (vote, member) rows.
2. Member codes in the EU-27 and the partners present in every period.
3. The votes of each period and of each 30-day buffer; votes whose date falls outside its session's span (listed).
4. The share of votes on which the EU-27 members other than Czechia split, per period.
5. The share of X per member and period for the comparison members (the Czech share is reported with the results).

## 4. Estimation

For a focal member *f*, a before period *P* and an after period *Q*: on each vote on which *f* has a position, the
difference between *f*'s agreement and the mean agreement of the comparison members that voted, counting only
comparison members with a position on both sides of the change. **β_f** is the mean of that difference over *Q* minus
its mean over *P*.

In code (`tools/un/votes.py`): `windows(dates, before, after)` with both ends included; Q1 is
`before = (2022-01-16, 2025-12-14)`, `after = (2026-10-16, 2026-12-31)`; Q2a `(2014-01-29, 2017-12-12)` and
`(2018-01-12, 2021-12-16)`; Q2b `(2018-01-12, 2021-12-16)` and `(2022-01-16, 2025-12-14)`. The driver that runs every
β, placebo and label (`tools/un/estimate.py`) is written and frozen, with tests on made-up votes, before stage A.

**Intervals.** A bootstrap of agenda items (the field `agenda_title`, which groups the resolutions repeated year after
year; a vote without one is its own item), resampled within each period, 2 000 draws, a generator started from seed
20261015 for each β: the 90 % and 95 % percentile intervals and the standard error *se*.

**Placebo rank.** β and *se* are computed with each other EU-27 member as focal (with the same periods, and the same
partner in Q3; its comparison members are all other EU-27 members, Czechia among them, except the partner), keeping members with at least 20 votes in the after period. Czechia's **p** is the share of all these
members, Czechia included, whose |β|/*se* is at least Czechia's (ties count against Czechia). With about 27 members,
p ≤ 0.10 means Czechia is among the two or three members whose change stands out most. The number of members is
reported with each p.

## 5. Power (computed on the other EU members only)

`tools/un/power.py` → `docs/research/un-votes-power.json`, with the code of §4. Czechia is dropped in the query that
reads the file, so the placebos have one comparison member fewer than the real run. Each other member was taken as
focal for pseudo changes sized like the questions: an October–December after period following four years (16 October
to 31 December 2022 and 2023, the size of Q1: about 80 votes, a third of them splitting the EU; 2 000 draws, members
with at least 20 votes after) and the Q2a periods themselves.

| pseudo change | members | votes after (split) | median width of 90 % interval | widest | 90th pct of \|β\| | 90th pct of \|β\|/se |
|---|---|---|---|---|---|---|
| Oct–Dec 2022 after four years | 26 | 82 (25) | 0.050 | 0.110 | 0.016 | 1.12 |
| Oct–Dec 2023 after four years | 26 | 80 (27) | 0.048 | 0.121 | 0.022 | 0.99 |
| 2018–2021 after 2014–2017 | 26 | 377 (127) | 0.042 | 0.106 | 0.013 | 0.97 |

A member's ordinary movement relative to the rest of the EU is one to two points of agreement. For a typical member,
a Czech change of about three points would meet the rules of §6 and one of one point would not; for the members with
the most variable records (about one in ten) the interval is twice as wide. Agreement with the EU majority is near its
ceiling for most members, so a change shows mostly as votes on which a member leaves an otherwise united EU; if
Czechia's agreement in the before period is already near one, "higher agreement" can hardly occur (its level is
reported with every β).

## 6. Labels

For each β, in this order, the first that applies:

1. **lower** / **higher agreement after the change** — |β| ≥ 0.02, the 95 % interval excludes 0, and p ≤ 0.10.
2. **no change larger than 3 points** — the 90 % interval of β lies within −0.03 to +0.03 (a statement about the
   change relative to the other members, not about levels).
3. **underpowered** — the 90 % interval is wider than 0.06, twice the margin, so rule 2 could not have applied.
4. **inconclusive** — anything else.

The margin of three points is about one and a half times the largest ordinary movement of most members (§5), and
the minimum of two points keeps a change within that ordinary movement from being labelled as a shift. A label is
about the change relative to the other EU-27 members in the periods of the governments, not about Czechia's level and
not about what caused it. Q1 is the headline; Q2 is reported in full in stage A whatever its labels; Q3 is
descriptive; Q4 is a list.

## 7. Checks (reported; none relabels a primary result)

1. **Split votes only**: β on the votes on which the EU-27 members other than *f* split.
2. **No partial credit**: agreement 1 only for identical positions, else 0.
3. **No buffer**: after periods from the cabinet date itself.
4. **Comparison without Hungary and Slovakia**, whose own governments changed in the window (Slovakia, October 2023).
5. **Regular sessions only**, without emergency special sessions.
6. **Confidence dates**: after periods of Q2 starting 30 days after 12 July 2018 (the second Babiš cabinet's
   confidence; the first cabinet lost its vote on 16 January 2018) and 13 January 2022 (Fiala); for Q1 the date is
   unchanged, as registration (October 2026) is after the third cabinet's confidence vote of 13 January 2026.
7. **The United States split**: for Q3 with the US, the Fiala period cut at 20 January 2025, when the US government
   changed, using only the part before.
8. **Absent**: Czechia's share of X in each period (a government that avoids votes is invisible to β).
9. **Same season before**: Q1 with the before period restricted to the votes of 16 October to 31 December in
   2022–2025, so that the before and after periods cover the same part of the Assembly year.
10. **UNGA-DM cross-check**, run with the results: for sessions 68–77, the share of (member, adopted resolution) pairs
   whose position is the same in UNGA-DM and in the Digital Library file, all members.

## 8. Limits stated now

- Q1 rests on one session's votes after registration, about 80; only a change of about three points or more can be
  told from ordinary movement (§5).
- Only adopted resolutions: positions on failed drafts, amendments and paragraphs are not in the source.
- A UN vote is cast by the mission on instructions; this design cannot say who decided a vote, or whether a change
  came from the government, the ministry or the world agenda. Votes in the first weeks after a change largely repeat
  committee votes cast under the old government, which is why the after periods start 30 days later.
- The first Babiš cabinet (December 2017 – June 2018) lost its confidence vote; it is pooled with the second.
- The partners change too (the United States in January 2025; Slovakia in October 2023; Hungary held a parliamentary
  election in April 2026), so Q3 mixes Czech and partner changes.

## 9. Stages and what is published when

- **Stage A** (after screening and frozen code): Q2 to Q4 for the two earlier changes. An article may be published with
  Q1 marked as pending. Stage A reads Czech positions up to 14 December 2025 only; the votes from 15 December 2025 are
  first read in stage B.
- **Stage B** (after the data covering 2026 are released): Q1, Q3 and Q4 for the third Babiš government with the
  frozen code. If no version covering December 2026 is out by 30 April 2027, stage B waits and the change log says so.

## Change log

- 15 October 2026: design committed.
