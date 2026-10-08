# House style for the long articles (Prague, measured)

Every article in the series exists in one form: the long one, at the part's original URL. This file is the style
the text must meet. The author's request: flowing text, no AI-isms, no slop, no short punchy theses opening
paragraphs.

## Prose

- **Paragraphs carry the argument.** Each opens by picking up where the last one left off: the object, the
  measurement, the step in the reasoning. It never opens with a slogan-like one-liner ("Both readings are true.",
  "The guess fails.", "It is the role, not the party.", "Nothing here is causal."). A finding is stated inside the
  sentence that explains it.
- **Bullets are for genuine lists only.** These include the hypothesis table, the list of scripts, the dated list of
  changes after registration, and references. Everything else is prose. Three findings in a row become a paragraph
  with transitions, not three bullets. Bold lead-ins in running text are not used.
- **Headings name content** ("Votes against across four terms"), not slogans ("The same people, voting
  differently").
- **Sentences** vary in length. No run of short declaratives for effect. Plain words are preferred to
  nominalisations.
- **Tone.** Numbers, caveats and registered status carry the weight, not adjectives. No intensifiers ("striking",
  "remarkable", "crucially", "notably", "importantly"). No hedging filler ("it is worth noting", "it should be said").
  No meta-announcements ("This section looks at…", "Let us turn to…").

## AI-isms and slop to remove on sight

- "Not X, but Y" / "It's not X — it's Y" as a rhetorical device. Keep it only where it is a real contrast of two
  measured things, at most once per article.
- Triads for rhythm ("fast, cheap and wrong"), and paired hedges.
- Rhetorical questions as transitions.
- "Here's the thing", "The answer is…", "In short", "Put simply", "What this means is", "The bottom line".
- Em-dash chains. Use commas, colons or a new sentence.
- Colon-reveal sentences ("The reason is simple: …").
- Closing morals or zingers at the end of paragraphs and sections.
- "Tells a story", "paints a picture", "the data speak", "under the hood", "at the end of the day".
- Personifying data ("the data say", "the files refuse").

## What must not change

- **Every number, interval, p-value, count, date and unit.** A script diffs all numbers between the old and new text;
  any change must be a deliberate, listed correction.
- **Registered wording of results:** "supported", "not supported", "inconclusive", "indeterminate", "uninformative",
  "underpowered", and the pre-written reporting sentences.
- **Citations and references.** Every figure, its alt text and caption; the hypothesis tables; "What changed after
  registration"; limitations.
- **Interactive elements** from the former short version: the councillor table (Part 1), the precinct map (Part 2),
  the district table (Part 3), the yearly table (Part 4).
- **Structure and CSS** of the page family (`text.css`, `a24.css`, the `.ht` table), the held colour of each part, the
  photo and its credit, the og tags (updated to the canonical URL).

## Structure of a merged article

1. **Header.** Kicker, h1, deck, facts. The deck is two or three sentences of prose.
2. **Opening section.** What the part set out to measure and why, as prose. Material from the short version comes
   first where it is the natural entry (e.g. Part 1's reading of the current term), then the long version's questions.
3. **"How this was done"** (registered design, referees, data).
4. **The tests,** with the table.
5. **Sections per question,** each integrating the short version's descriptive material where it belongs.
6. **Robustness.**
7. **"What changed after registration"**: since 8 October 2026 in the change log, linked from the metadata, not in the article.
8. **"What this does not show".**
9. **References**, merged and renumbered, with no duplicates.
10. **Footer.**

Length follows from content. Nothing substantive from either version is dropped. Duplicates are merged.
