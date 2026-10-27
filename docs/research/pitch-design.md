# Would Pitch Perfect pass today? Joke targets in two films — research design

**Status: pre-specified analysis, design committed 27 October 2026, before any subtitle file of either film was
supplied, read or hashed, and before any model coded any line of either film.** A content analysis of the jokes in
the English subtitles of *Pitch Perfect* (2012) and *Pitch Perfect 2* (2015), coded by a language model and validated
against a blind sample coded by the author. The steps follow in dated commits and tags: design (tag `pitch-design`),
code and tests on invented text only, independent review, code freeze (tag `pitch-code`), the blind human sample
(hashed and committed), the model run, results, page. Commit times are self-reported; the signed tag `pitch-design`
will fix this text. Deviations are listed, dated, in the change log.

## 0. What has already been seen

- **The brief** was written by the author and approved by her on 27 October 2026 (the date of every statement of the
  author below). It fixes the question, the unit, the codebook's categories, the three questions, the bootstrap, the
  data handling, the model, the validation gate and the workflow. This text turns it into a registered design; every
  choice the brief does not make was drafted by the drafting assistant and settled by the author before the tag
  (§1, "Settled decisions").
- **The films.** The author supplies the subtitle files from her own copies of both films. **She has seen both films
  several times** (the exact count is not known to her). She knows their jokes as a viewer; she has not counted or
  coded them, and no subtitle file has been read.
- **Prior expectation**, stated by the author on 27 October 2026, before any data: **Q1 yes**, *Pitch Perfect 2* aims a
  larger share of its jokes at America than *Pitch Perfect*; **Q2 mostly satire**, butt = speaker more often than
  butt = group among protected-trait jokes; **Q3 yes**, more "would not pass today" jokes per hour in *Pitch Perfect
  2*. These priors are recorded so that readers can judge the risk of confirmation: **the author is also the blind
  annotator of the validation sample** (§3.4), so her expectations can shape her own codes, though not the model's.
- **The subtitles.** No subtitle file of either film has been supplied, opened, parsed, counted or hashed. No cue
  count, runtime of dialogue, scene count or joke count of either film is known to this design. The numbers of §5 are
  assumptions, labelled as such.
- **The drafting assistant** is an AI model with general training knowledge. Both films are widely discussed, and it
  has very likely seen quotes from them, reviews and commentary on their humour (including whether it has aged
  well). It cannot audit its own training data. **This is a limit on blinding**: the codebook was written by something
  that may carry an impression of which jokes are in the films and of how they were received. To limit what that can
  do, every example in the codebook (§2.4) is invented and none paraphrases a scene of either film, and the codebook
  is fixed here, before any line of the films is read by code or model.
- **The coding model** (§4) has the same kind of knowledge and may recognise lines. This is a limit stated in §8, not
  something this design can remove.
- **Reviews.** None yet. The code is reviewed independently before the freeze tag `pitch-code` (§3.5).

## 1. Questions and readings

The unit is a **joke** (§2.3). All three questions describe the jokes as written in the subtitles; none is a claim
about intent, about the audience, or about the films' effect on anyone (§8). **"Would not pass today"** is this
study's operational name for a joke whose target is a protected trait (§2.4) and whose butt is the group (§2.4). It is
a classification of joke structure, not a judgement of current taste or of the films, and the page says so where the
phrase first appears.

**Common definitions.** *Share* is a count of jokes in a film divided by the count of jokes in the stated denominator
in the same film. *Rate per hour* is a count of jokes divided by the film's **dialogue hours**, the sum of the
durations of its scenes (§2.2). Every interval is a **95 % percentile interval from the scene bootstrap** (§4): scenes
are resampled with replacement within each film, 10 000 replicates, fixed seed. "Excludes 0" means both ends of the
interval lie on the same side of 0; an end exactly at 0 does not exclude it.

- **Q1 (directional).** Is the share of jokes whose target is America (§2.4) higher in *Pitch Perfect 2* than in
  *Pitch Perfect*? Estimand: Δ1 = share_America(PP2) − share_America(PP1), all jokes of the film as denominator.
  Pre-written readings:
  - interval wholly above 0: **supported**. Page sentence: "A larger share of the second film's jokes aim at America
    than of the first film's: X pp more (95 % CI a to b, bootstrap by scene)."
  - interval wholly below 0: **not supported**. Page sentence: "The opposite: a smaller share of the second film's
    jokes aim at America, X pp fewer (95 % CI a to b, bootstrap by scene)."
  - interval includes 0: **inconclusive**. Page sentence: "The two films aim a similar share of jokes at America, or
    differ by less than this sample can tell: X pp (95 % CI a to b, bootstrap by scene). A difference of about M pp
    would have been detected four times in five" (M the minimum detectable difference, recomputed from the real
    counts by the formula of §5).
  The per-film shares are reported with their intervals.
- **Q2 (per film, no direction).** Among jokes that target a protected trait, how many are satire (butt = speaker)
  and how many punch down (butt = group)? Estimand per film: D = share_speaker − share_group, the denominator being
  all protected-trait jokes of the film, `unclear` included (so the two shares need not sum to 1). The shares of
  speaker, group and unclear are reported with their intervals. Pre-written readings, per film:
  - interval of D wholly above 0: "In [film], jokes on protected traits more often laugh at the speaker than at the
    group: D = X pp (95 % CI a to b)."
  - interval wholly below 0: "In [film], jokes on protected traits more often laugh at the group than at the speaker:
    D = X pp (95 % CI a to b)."
  - interval includes 0: **inconclusive**. "In [film], satire and punching down cannot be told apart in this sample:
    D = X pp (95 % CI a to b)."
  The difference of D between the films, D(PP2) − D(PP1), is reported with its interval and **no reading**: it is
  descriptive and carries no label (§5 shows it has almost no power).
- **Q3 (no direction).** "Would not pass today" jokes per dialogue hour, *Pitch Perfect* against *Pitch Perfect 2*.
  Estimand: Δ3 = rate(PP2) − rate(PP1). Pre-written readings:
  - interval wholly above 0: "The second film has more jokes that would not pass today per hour of dialogue: X more
    per hour (95 % CI a to b)."
  - interval wholly below 0: "The first film has more jokes that would not pass today per hour of dialogue: X more
    per hour (95 % CI a to b)."
  - interval includes 0: **inconclusive**. "The two films have a similar rate of jokes that would not pass today, or
    differ by less than this sample can tell: X per hour (95 % CI a to b)."
  The per-film rates and counts are reported with their intervals.

**Degenerate bootstrap.** A replicate in which a share has no denominator (for Q2, a resampled film with no
protected-trait joke) is dropped from that statistic, and the number dropped is reported. If more than 5 % of the
10 000 replicates are dropped for a statistic, its question is labelled **indeterminate** for that film and no reading
is given. If a film has no protected-trait joke at all, Q2 for that film is reported as "no protected-trait joke
found", with no interval.

**No family correction.** The three questions are separate questions with separate readings, reported side by side.
There is no tally across them (editorial standard §7) and no headline that combines them.

### Settled decisions

The brief does not settle these. The drafting assistant drafted them; **the author confirmed A to C and E to I, and
the two-sided readings of Q2 and Q3, and changed D, on 27 October 2026**, before the tag. After the tag a change is a
dated deviation (§6.3).

- **A. Butt is coded for every joke**, not only for protected-trait jokes, so that the validation sample (§3.4) gives
  a Butt agreement on more than a handful of cues. For a target that is not a group of people, `group` means "the
  target" (the institution, the character, the genre). The code name `group` is kept from the brief. Q2 and Q3 use
  Butt only for protected-trait jokes.
- **B. One target per joke, with a priority rule** when a joke has several (§2.4): group of people, then America,
  then genre, then character or situation. The rule is ordered so that a protected-trait target is not hidden under a
  broader one.
- **C. America versus nationality.** A joke at Americans or the United States as a nation is America (national
  identity). A joke at any other nationality or national origin is group: nationality. A joke at a racial or ethnic
  group within the United States is group: race.
- **D. "Protected trait" is seven group types**: gender, race, weight, sexuality, nationality, religion and
  disability (the brief's five, with religion and disability added by the author). Weight is in the list though it is
  not a protected characteristic in most law; the term is this study's, not a legal one. Jokes at other groups (age,
  class, occupation and any other) are coded group: other with the group written down, counted and reported, and are
  **not** protected traits in Q2 and Q3.
- **E. The validation sample is 50 cues from each film**, not 100 from the pooled cues, so neither film dominates it.
- **F. Scenes are built on the kept cues**, after lyrics and sound cues are removed (§2.2). A song therefore usually
  breaks a scene. Dialogue hours are the sum of scene durations, so long songs and silences do not count as hours of
  dialogue.
- **G. Run 1 of the model is primary**; run 2 measures self-agreement only (§4).
- **H. The lyric fallback** (§2.2) is an author review of fully italic runs, recorded before the model run, not a model
  judgement.
- **I. The degenerate-bootstrap rule** (above), with the label **indeterminate**.

## 2. Data and definitions

### 2.1 Files

- **Source.** English `.srt` subtitle files of *Pitch Perfect* (2012, dir. Jason Moore) and *Pitch Perfect 2* (2015,
  dir. Elizabeth Banks), supplied by the author from her own copies. One file per film. If a file is SDH (subtitles
  for the deaf and hard of hearing), it is used as described below; the type of each file is recorded.
- **Storage.** `tools/data/pitch/raw/pp1.srt` and `tools/data/pitch/raw/pp2.srt`, **gitignored** (`tools/data/pitch/`,
  ignored since commit `ddbcc6c`, before any file was supplied). They are never edited by hand. Their SHA-256 hashes, sizes and the date
  supplied go to `docs/research/pitch-files.sha256`, committed before any model run. Every run checks both hashes and
  stops on a mismatch. A file is read as UTF-8, else as cp1252, and the encoding used is recorded.
- **Copyright.** The subtitles are the films' scripts and are not published. The repository and the page carry only
  counts, cue numbers, codes, intervals and **short single-line quotes** (one subtitle line at most, quoted to
  illustrate a category or a result, at most ten on the page). Model inputs and outputs that contain subtitle text stay
  in `tools/data/pitch/` (gitignored). The committed results file holds cue numbers and codes, not text.

### 2.2 Cleaning, lyrics and scenes

Applied by code, in this order, to each file:

1. **Parse.** Cues by their index, start and end time and text lines. A malformed cue (no valid time line) stops the
   run with its position; nothing is skipped silently.
2. **Song lyrics are excluded, line by line.** A line is a lyric line if it contains ♪ or ♫, or if it begins or ends
   with `#` (a common substitute for ♪ in subtitle files). Lyric lines are removed; the other lines of the same cue are
   kept. **Spoken lines during a performance are kept**, including the commentators' and any spoken aside within a
   number.
   **Fallback.** If a file contains no ♪, ♫ or `#` marker at all, lyrics are taken to be marked by italics, which
   files also use for voices off screen (the commentators may be off screen). The code then lists every run of three
   or more consecutive cues whose text is wholly in italics (`<i>…</i>`), with cue numbers and times. The author
   reviews the list against her copy and marks each run "song" or "not song"; her marks are committed, with the
   blind sample's hash (§3.4) and before any model run. Runs marked "song" are removed whole. Italic cues outside
   such runs are kept. The fallback, the number of runs and how each was marked are reported.
3. **Sound cues are stripped.** Text in square brackets or parentheses (`[laughs]`, `(cheering)`) is removed. Speaker
   labels (a word in capitals followed by a colon) are kept as text, since they say who speaks. Formatting tags
   (`<i>`, `<b>`, `<font>`) are removed after step 2. A cue left with no text is dropped.
4. **Kept cues.** What remains, numbered by their original cue index. Counts of cues and lines dropped at each step
   are reported per film.
5. **Scenes.** A scene is a maximal run of kept cues in which no gap between the end of one cue and the start of the
   next exceeds **8 seconds**. A scene's duration is the end of its last cue minus the start of its first. A film's
   **dialogue hours** are the sum of its scene durations. The full runtime (last cue end of the raw file) is also
   reported.

### 2.3 Jokes (pass 1)

A **joke** is a stretch of one or more consecutive kept cues, within one scene, that is written to amuse: a punchline
with its set-up, a comic insult, a comic understatement or exaggeration, a pun, a comic non sequitur. An **allusion**
is a reference to something outside the film (a person, a brand, another film, a song, an event) used for comic
effect; it is a joke unit with `kind = allusion`. A reference that is not comic is not a joke. A joke's span is the
cues from its set-up to its punchline; set-up that lies more than one scene back is not part of the span. A joke
belongs to the scene of its first cue. Overlapping jokes are allowed (a cue may belong to two jokes); a running gag is
a new joke at each reprise.

Pass 1 gives the model one scene at a time, with the text of the preceding scene as context only, and asks for every
joke as a list of `{first_cue, last_cue, kind}`. Cue numbers outside the scene are rejected and the call is retried
once, then logged as failed (§3).

### 2.4 Codebook (pass 2)

Pass 2 gives the model one joke at a time, with the full text of its scene and the joke's cues marked, and asks for
the three fields below. The definitions and examples are part of the prompt and are frozen at the tag `pitch-code`.
**Every example is invented for this design; none is taken or adapted from either film.**

**Target**: whom or what the joke is about. Exactly one value. When a joke has several targets, the first that applies
in the order group of people, America, genre, character or situation (decision B).

- `america`: the United States as a nation or its national identity, its institutions (government, courts, the
  military, schools and universities as institutions, the media, corporations), its competition culture (winning,
  rankings, trophies, sport and contest culture treated as national habit) and US college life as an institution
  (fraternities, sororities, campus rituals, college sport).
  - "We're Americans. If it isn't a competition, we'll make it one and then sue the judges."
  - "Freshman orientation: three hours on fire safety, five minutes on where the library is."
- `group`: a group of people defined by a shared trait, where the trait is what the joke is about. The **group type**
  is recorded: `gender`, `race`, `weight`, `sexuality`, `nationality`, `religion`, `disability`, or `other` with the
  group written down (age, class, occupation and any other; decision D). Americans as a nation are `america`, not `group`
  (decision C).
  - gender: "Of course she can't read the map, she's been holding it like a handbag."
  - weight: "He sat on the bench and the bench filed a complaint."
  - nationality: "The Swiss team arrived exactly on time, which is how you know they're not from here."
  - religion: "Ask the vicar's daughter to judge the talent show, she only knows hymns and guilt."
  - disability: "He uses a wheelchair, so obviously he's the one we leave to guard the stairs."
- `character`: an individual character or a situation in the story, where no group trait and no national institution
  is what the joke is about: a character's habits, a mishap, an absurd turn of events, wordplay with no target.
  - "I've rehearsed this apology so much it now has a bridge and a key change."
  - "The van broke down, so naturally we're now lost on foot instead."
- `genre`: musicals, films, pop music or showbusiness and their conventions, including allusions to other works and
  performers when the joke is about them as entertainment.
  - "This is the part of the movie where we all learn something and the music swells."
  - "Nobody spontaneously bursts into harmony at a bus stop. Except, apparently, us."

**Butt**: on whom the laugh falls. Coded for every joke (decision A). Exactly one value.

- `speaker`: the laugh is on the person who speaks, or on the view they voice: their ignorance, prejudice, vanity or
  self-deprecation is what is funny. For a joke at a group, this is **satire**: the stereotype is shown as the
  speaker's failing.
  - "As a man, I am naturally excellent at directions," said while walking into a lake.
  - "I'm not racist, I have a playlist."
- `group`: the laugh is on the target (for a joke at a group, the group itself, through the stereotype). For a joke at
  a group, this is **punching down** in this study's sense: the stereotype is offered as the truth that makes the joke
  work.
  - "Don't let the vegan cook, the soup will just be a lecture." (group: other, vegans, with the laugh on them)
  - The weight example above, where the laugh is on the man on the bench.
- `unclear`: both readings are open from the text, or the delivery (tone, face, a cut) would decide and the
  subtitles do not show it. Used when the coder cannot choose, not as a middle value.

**Protected trait** (decision D): target `group` with group type `gender`, `race`, `weight`, `sexuality`,
`nationality`, `religion` or `disability`. **Would not pass today**: a protected-trait joke with butt `group`.

The model returns JSON, `{target, group_type, group_other, butt}`; `group_type` is empty unless the target is
`group`. A reply that does not parse or uses a value outside the codebook is retried once, then logged as failed and
counted (§3).

## 3. Screening and blinding (before any joke is coded)

1. **Code on invented text only.** The parser, the cleaning steps, the scene rule, the sampler, the prompts, the
   bootstrap and the outputs are written and tested on invented subtitle files made for the tests: lyric markers,
   italics, SDH cues, malformed cues, encodings, gaps of exactly 8 s. Model calls in the tests are mocked. **No agent
   or person runs the model on real subtitle text before the tag `pitch-code` and the committed hash of the blind
   sample (§3.4).**
2. **Independent review** of the code and the prompts, before the freeze. Its points and their resolution are
   recorded in the change log.
3. **Code freeze.** The author tags the final code, prompts and codebook `pitch-code`. Every run on real subtitles
   refuses unless the tag exists, `tools/pitch` at HEAD equals it, and `tools/pitch` and this text have no uncommitted
   changes. The prompts, the codebook text and the model settings are hashed into the run log.
4. **The blind sample.** After `pitch-code`, the author supplies the two files and the code hashes them (§2.1),
   cleans them (§2.2) and draws **50 kept cues from each film** (decision E), uniformly without replacement, with
   `numpy.random.default_rng(2012)` on the kept cues sorted by film and cue number. A local form (an HTML file in
   `tools/data/pitch/validation/`, gitignored, opened offline) shows each sampled cue highlighted inside its scene, the
   same context the model sees, in a random order. The author codes each cue, **without any model output for any
   cue of either film existing yet**: is the highlighted cue part of a joke (yes or no); if yes, target, group type
   and butt by §2.4. Her codes are saved as `validation-human.json` (cue numbers and codes only, no text); its SHA-256
   is committed to `docs/research/pitch-files.sha256` **before any model run on real subtitles**. The file itself is
   committed after the model run, and every later step checks it against the hash.
   If the lyric fallback (§2.2) applies, the author's song marks are committed in the same commit.
5. **What the author does not see.** No model output on real subtitles before her codes are hashed. After the hash she
   may not change a code. A cue she cannot code is marked `skip` and reported; skipped cues are not replaced.
6. **Run log.** Each model call is logged (scene or joke, attempt, status, input and output token counts) in
   `tools/data/pitch/out/` (gitignored). Failed calls after one retry are counted per film and pass; if more than 2 %
   of scenes or jokes fail, the run stops and the failure is reported, and no estimate is computed.

## 4. Estimation

1. **Model.** `claude-sonnet-5-5`, temperature 0, the prompts and codebook as frozen at `pitch-code`, no examples from
   the films, no system or user text that names the films' reception. The model version string returned by the API is
   recorded.
2. **Two full runs.** Pass 1 and pass 2 are run over both films twice, independently, with identical settings.
   **Run 1 is primary** (decision G); run 2 measures self-agreement.
3. **Joke-level counts.** Per film: jokes, jokes by kind, by target, by group type, by butt, protected-trait jokes and
   "would not pass today" jokes; scenes, kept cues, dialogue hours.
4. **Estimands** Δ1, D (per film), D(PP2) − D(PP1), Δ3, and the per-film shares and rates, as in §1.
5. **Bootstrap.** For each film separately, its scenes are resampled with replacement to the film's number of scenes,
   carrying every joke of a resampled scene (a scene drawn twice counts twice, a scene with no joke counts in the
   dialogue hours). Each statistic is computed on each replicate; the two films are resampled independently within
   one replicate, so differences use matched replicates. **10 000 replicates, `numpy.random.default_rng(42)`**, one
   generator, films in the order PP1 then PP2. The interval is the 2.5th and 97.5th percentile (`numpy.quantile`,
   default method). Scenes, not jokes, are resampled because jokes in one scene share a set-up, characters and tone.
6. **Self-agreement (run 1 against run 2)**, on all kept cues of both films: joke detection per cue (a cue is "joke"
   if it lies in any joke span), as per cent agreement and Cohen's κ; and on cues that both runs call a joke, κ on
   Target (four values) and on Butt (three values). A cue in several jokes takes the codes of the joke whose span
   starts first, then the shortest. Reported per film and pooled.
7. **Validation (run 1 against the author)**, on the 100 sampled cues, by the same per-cue mapping: **joke detection
   reported separately from code agreement**. Detection: per cent agreement, Cohen's κ, and the share of the author's
   joke cues the model found and of the model's joke cues the author marked. Codes: on cues both call a joke, Cohen's κ
   on Target and on Butt, with the number of cues each rests on and a 95 % bootstrap interval over cues (10 000
   replicates, `default_rng(43)`). Skipped cues are left out and counted.
8. **The gate.** κ on Target ≥ 0.6 **and** κ on Butt ≥ 0.6 (point estimates, run 1 against the author): the study is a
   **Registered study**. Otherwise it is **Exploratory**, the page's status says so, and the readings of §1 are still
   given, under that status. The threshold is not loosened, the codebook and prompts are not changed to pass it, and
   no second sample is drawn in place of the first. A recoding after a failed gate is a new, exploratory analysis, on
   a new tag, reported as such.
9. Versions of Python, numpy and the API client, the model version string, the tag commits and the file hashes are
   written to `docs/research/pitch-results.json`.

## 5. Power (assumptions, not data)

**Every number in this section rests on assumptions stated here.** No subtitle of either film has been read. The
formulas are normal approximations at α = 0.05 two-sided and 80 % power, z = 1.960 + 0.842 = 2.802, with the scene
clustering entered as a design effect.

**Assumptions.**

- **Jokes per film: N = 300** ("a few hundred", from the brief), with 200 and 400 as brackets. Equal in both films.
- **Clustering**: 3 jokes per scene on average and an intra-scene correlation of 0.1, so a design effect of
  1 + (3 − 1) · 0.1 = **1.2**.
- **Q1**: a share of America jokes of **15 %** in both films under the null.
- **Q2**: protected-trait jokes are **10 %** of all jokes (30 per film at N = 300); speaker and group split evenly
  and no `unclear` (the variance is then largest). **The 10 % is kept after religion and disability were added to the
  protected set (decision D)**: it was a round guess, not an estimate, and jokes on these two traits are not expected
  to be common enough to move it; a higher share would only lower the detectable sizes of Q2 and Q3.
- **Q3**: half of protected-trait jokes would not pass today (15 per film at N = 300); **1.6 dialogue hours** per film
  (a runtime of about two hours less songs and silences, assumed, not measured).

**Formulas.** Q1: MDD = z · √(1.2 · 2p(1 − p)/N). Q2: with no `unclear`, D = 2·share_speaker − 1, so
MDD(D) = z · √(1.2 · 4 · 0.25/n), n the protected-trait jokes in one film, as a departure of D from 0 (an even split).
Q3: counts Poisson with the same design effect, MDD = z · √(1.2 · (c₁ + c₂))/T, c the "would not pass" jokes of a
film and T its dialogue hours.

| Jokes per film (assumed) | Q1, Δ1 | Q2, D per film (share punching down) | Q3, Δ3 per dialogue hour (in jokes) |
|---|---|---|---|
| 200 | 11.0 pp (15 % against 26 %) | 0.69 (n = 20; 50 % against 16 % or 84 %) | 8.6 per hour on a base of 6.2 (13.7 jokes on a base of 10) |
| **300** | **8.9 pp (15 % against 24 %)** | **0.56 (n = 30; 50 % against 22 % or 78 %)** | **10.5 per hour on a base of 9.4 (16.8 jokes on a base of 15)** |
| 400 | 7.7 pp (15 % against 23 %) | 0.49 (n = 40; 50 % against 26 % or 74 %) | 12.1 per hour on a base of 12.5 (19.4 jokes on a base of 20) |

**Reading.** At about 300 jokes per film, Q1 can see a difference in the America share of about 9 pp. Q2 can tell
satire from punching down only if one of them is about three quarters or more of a film's protected-trait jokes. Q3
can see a difference only if one film has roughly twice the rate of the other or more, and at counts of 10 to 20 the
normal approximation is rough. **The likely outcome for Q2 and Q3 is inconclusive** unless the films differ sharply;
that is a property of two films, not of the method, and the page says so. The difference D(PP2) − D(PP1) (§1) has a
detectable size of about 0.79 at N = 300 (√2 times the per-film figure) and carries no reading. After the run the
minimum detectable differences are recomputed by these formulas from the real counts, design effect 1.2 kept, and
quoted in the inconclusive sentences of §1.

## 6. Labels

### 6.1 Study status

**Registered study** if the gate of §4.8 passes, **Exploratory** otherwise. The status is in the page's metadata
block and its kicker, verbatim, and the page states κ on Target and on Butt with the number of cues each rests on.

### 6.2 Question labels

As pre-written in §1: Q1 **supported**, **not supported** or **inconclusive**; Q2 and Q3 a direction sentence or
**inconclusive**; any of them **indeterminate** under the degenerate-bootstrap rule. The words are used verbatim on the
page, in the facts strip, the table and the deck. A label is the same under either status; under Exploratory the page
says the coding did not reach the agreement registered for it.

### 6.3 Deviations

Any change after the tag `pitch-design` is a deviation: dated, listed in the change log below with its reason and the
stage at which it was made (before code, before `pitch-code`, before the blind sample, before the model run, after the
model run), and named on the page. A change made after any model output on real subtitles was seen makes the affected
question exploratory, whatever the gate. The registered readings, the gate and the codebook are never changed after
the model run.

## 7. Checks (reported; none relabels a primary result)

- **Run 2** in place of run 1: every estimand and its interval.
- **`unclear` as group**: Q2 and Q3 with every `unclear` butt on a protected-trait joke counted as `group` (the upper
  bound of punching down), and **as speaker** (the lower bound).
- **Scene gap** of 5 s and 12 s in place of 8 s, for the intervals (the point estimates of shares do not change; the
  rates of Q3 change through the dialogue hours).
- **Full runtime** as the denominator of Q3's rates, in place of dialogue hours.
- **Without allusions**: Q1 to Q3 on `kind = joke` only.
- **Protected set widened** to every `group` type (group: other included), for Q2 and Q3.
- **Q1 by joke count per hour** of America jokes, in addition to the share.

## 8. Limits stated now

- **Joke targets, not intent or effect.** The study counts what jokes are about and on whom the laugh falls in the
  text. It does not measure what the writers meant, how audiences took the jokes, or any effect of the films. It
  supports no verdict such as "the film is sexist" and the page draws none. A difference between the films is an
  association between the film and the share or rate; it is not caused by the year, the director or the audience, and
  the page uses no causal verb for it.
- **"Would not pass today"** is an operational definition (§1), not a measurement of today's standards. Standards
  vary by audience and country, and the study surveys nobody.
- **Irony is hard for a model.** Satire and punching down differ by whose view the joke mocks, and a model can misread
  irony, especially from text alone. The validation gate measures this on 100 cues, few of them protected-trait jokes,
  so the Butt agreement on the cases that matter most for Q2 rests on very few cues; the page gives that number.
- **Subtitles are not the delivery.** Tone, timing, a look, a cut, a visual gag and the music carry much of the
  humour and decide many butts. Visual jokes with no line are not in the data at all. Subtitle files differ in
  wording and line breaks from the spoken dialogue, and from each other.
- **Lyrics are excluded.** Jokes in the songs (parodies, changed lyrics) are not counted. The marker rule depends on
  how the file marks songs; the fallback depends on the author's review.
- **The author is also the annotator** of the validation sample, and she approved the codebook. Her coding is blind to
  the model's output, not to her own expectations (recorded in §0: she expects mostly satire in Q2, and yes in Q1 and
  Q3) or to her knowledge of the films, which she has seen several times.
- **The coding model and the drafting assistant know the films** from their training (§0). The model may recognise a
  line and code it by what it knows of the scene or its reception, not by the text it is given.
- **One model family codes**, validated by one human; no second human coder.
- **Small n.** Two films, a few hundred jokes each, a few dozen protected-trait jokes (§5). Q2 and Q3 are likely to be
  inconclusive. The scene bootstrap treats scenes as exchangeable within a film, which they are only roughly.
- **Joke segmentation** shapes every denominator. A model that splits jokes more finely in one film raises its counts;
  the self-agreement and the validation detection agreement show how stable it is, not that it is right.
- **Out of scope.** *Pitch Perfect 3* (2017) and present-day comparison films are a planned second part, with its own
  design. Nothing here says how these two films compare with other comedies of their years or of today.

## Running and verification

Commands, the frozen prompts and the code are in `tools/pitch/` and its README, written after this design. The
freeze tag is `pitch-code` (§3.3). Planned outputs: `docs/research/pitch-files.sha256` (subtitle files, the blind
sample, the author's song marks if any), `docs/research/pitch-results.json` (counts, estimates, intervals, agreement,
versions, hashes, no subtitle text), and the gitignored working files under `tools/data/pitch/` (`raw/`,
`validation/`, `out/`). The page is written from the results file after it is committed.

## References

- Cohen, J. (1960). A coefficient of agreement for nominal scales. *Educational and Psychological Measurement* 20(1),
  37–46.
- Davison, A. C., Hinkley, D. V. (1997). *Bootstrap Methods and Their Application*. Cambridge University Press.
  (Resampling of clusters.)
- Gilardi, F., Alizadeh, M., Kubli, M. (2023). ChatGPT outperforms crowd workers for text-annotation tasks.
  *Proceedings of the National Academy of Sciences* 120(30), e2305016120.
- Details are verified before publication, in a dated commit; the page's references (editorial standard §9) are
  chosen then.

## Change log

- 27 October 2026: design committed, before any subtitle file of either film was supplied, read or hashed, and before
  any model coded any line, with decisions A to I of §1 drafted by the drafting assistant.
- 27 October 2026, the author's decisions, before the tag `pitch-design` and before any subtitle file was supplied:
  decisions A to C and E to I and the two-sided readings of Q2 and Q3 confirmed; decision D changed, religion and
  disability added to the protected traits (age, class and occupation stay group: other), with invented codebook
  examples for both and the 10 % assumption of §5 kept; §0 completed with what the author has seen of the films and
  her prior expectation for each question; the local data folder `tools/data/pitch/` gitignored (commit `ddbcc6c`).
- 27 October 2026, after the `pitch-design` tag and before `pitch-code`, approved by the author, before any subtitle
  file was supplied: temperature 0 cannot be sent (removed for Claude 5 models, 400 error); replaced by explicit
  adaptive thinking at effort high, enum-constrained structured outputs and max_tokens stops counted as failures.
  Run-to-run self-agreement, already registered, now carries the burden of showing sampling noise. Sources:
  https://platform.claude.com/docs/en/models/sonnet-5-5/migration-guide,
  https://platform.claude.com/docs/en/api/migration-2026-10-21 and
  https://platform.claude.com/docs/en/build-with-claude/structured-outputs. In the code: every call sends
  `thinking={"type": "adaptive"}` and `output_config.effort = "high"` and no sampling parameter; the model is pinned as
  `claude-sonnet-5-5` and the SDK as `anthropic==2.3.0`; `max_tokens` is 32 000 for pass 1 and 16 000 for pass 2 (room
  for thinking, which counts toward it), and the calls stream; the pass 1 reply is an object `{"jokes": [...]}` (the
  list of §2.3 inside an object) whose schema limits cue numbers to the scene's own and `kind` to the codebook, and
  the pass 2 schema limits target, group type and butt to the codebook values; the strict validation of §2.3 and §2.4
  stays as a second guard. Implementation clarifications, settled at the same time: (1) the blind sample is drawn
  with one `default_rng(2012)` over PP1's kept cues, then PP2's, and the form's display order is a permutation drawn
  from the same generator afterwards; (2) the scene bootstrap draws, within each replicate, PP1's scenes and then
  PP2's from the one `default_rng(42)`; (3) jokes whose pass 2 failed after the retry (within the 2 % limit) are left
  out of every count, share and rate, and their number is reported per film and run; (4) the full-runtime check of §7
  holds the runtime fixed as the denominator and resamples only the counts; (5) the author's song marks, if the
  fallback applies, are committed as `docs/research/pitch-song-marks.json` (cue numbers, times and marks, no text)
  with their hash in `pitch-files.sha256`; (6) a reply that the model refuses, or that stops for any reason other than
  `end_turn`, is a failed attempt, retried once under the rule of §2.3 and §2.4, with no fallback to another model.
