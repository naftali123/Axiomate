# Ideation: Web UI for Axiomate

**Feature**: `003-web-ui` (working name)
**Phase**: ideation – not a spec. Nothing here is approved or built.
**Created**: 2026-11-13

This note collects ideas and open questions so that a spec can be written from
it. It follows the order the project already uses: ideation → spec → plan →
tasks → code. Everything marked *proposal* is for the repository owner to accept,
change or drop; the questions at the end block the spec.

## 1. What the UI is for

Axiomate's engine is a command-line pipeline over a SQLite store. Its output is
exact but unreadable to anyone who did not build it: claims as JSON, flags with
reason codes, a gate that rejects or passes. The UI exists to answer three
questions for a person, in this order:

1. **What did the system do with this text?** (the process)
2. **What did it find, and why should I believe it?** (the results)
3. **How far can I trust the system as a whole?** (the quality)

It is a *window onto the store*, not a second engine. It never decides anything
the engine has not already decided, and it never shows a number that cannot be
traced to a stored claim and a source span (constitution II).

## 2. Who uses it (proposal)

| User | Job | What they need to see |
|---|---|---|
| **Analyst** (primary) | Read a company's filings and learn where the text disagrees with the record | Findings first, each with both quotes, one click from the source |
| **Reviewer** | Resolve what the system flagged and could not decide | A queue of open flags, each with the context needed to answer in seconds |
| **Owner / maintainer** | Know whether the system is accurate and what it does not cover | Precision and coverage per stage, thresholds met or missed, known limits |

A fourth, occasional user is the **newcomer** who needs the vocabulary
(claim, flag, assumption, conditional). The UI teaches it in place rather than
in a manual (section 5).

## 3. Look and feel

**Character: a careful reading room, not a dashboard.** The product's promise is
precision over coverage, so the interface should feel calm, legible and
deliberate. No gauges, no confetti, no "AI magic" styling.

Principles, each derived from the constitution:

1. **Evidence first.** The source sentence is always on screen or one click away;
   structured claims are shown *beside* the text they came from, never instead
   of it (II).
2. **Honest uncertainty is a first-class state.** "Not evaluable" and
   "conditional" get the same visual weight as "disagreement". They are never
   greyed out or hidden to make the page look more complete (III, IV).
3. **Never say "false".** The system reports disagreement between a text and a
   record, not which side is true (VII). Wording and colour must not imply a
   verdict of truth or fraud. Red is reserved for *errors in the system's own
   work* (a rejected candidate), not for the company.
4. **Show the assumption.** A result that rests on an assumption carries a
   visible chip with the assumption and its origin (context store, model,
   human), so "conditional" is never a mystery (III).
5. **Same answer, same page.** Stages after interpretation are deterministic
   (V), so a result page is stable and linkable. A URL points at one claim, one
   finding or one source span.
6. **The model is labelled, not hidden.** Anything a language model proposed is
   marked "proposed by model, checked by gate" with the instruction version, so
   nobody mistakes a proposal for a fact (I).

Visual language (proposal):

- Light and dark themes, large readable type for filing text, tabular figures
  for numbers (right-aligned, with the scale always shown: *$4.2 billion*, not
  *4200000000*).
- A small semantic palette used consistently: **neutral** (source text),
  **blue** (a claim, a fact), **amber** (flag / conditional / assumption),
  **teal** (consistent / passed), **violet** (disagreement), **red** (system
  error or rejected candidate). Colour is never the only signal; every state
  also has a word and an icon (accessibility).
- Quotes are always set in a quoted block with the exact characters from the
  document, in their original language and direction, even when the surrounding
  interface is in another language.
- Generous whitespace, one primary action per screen, no modal stacks.

## 4. Understanding the process

The status page already draws the eight-stage pipeline. The UI reuses that
picture, but per document and with real numbers, so "the process" is something
you can *look at* rather than read about.

### 4.1 The run strip

At the top of every document: eight stages in a row, each showing its state for
*this* document (not run / running / done / needs attention) and one count.

```
 ① Ingest ─ ② Interpret ─ ③ Gate ─ ④ Context ─ ⑤ Store ─ ⑥ Match ─ ⑦ Compare ─ ⑧ Review
   ✓ 412      ✓ 38          ✓ 31      ·           ✓ 27     ·          ·           ⚑ 4 open
 sentences   candidates    passed    (not built)  claims
```

Clicking a stage opens a plain-language panel: *what this stage does, what went
in, what came out, and why items were dropped.* Stages that are not built yet
are shown as not built, with a link to their spec, never as empty success.

### 4.2 The funnel

The single most useful picture for understanding a result is where the text
went. A funnel from "sentences in the filing" to "claims in the store":

```
 412 sentences ─▶ 52 contain a number ─▶ 38 candidates ─▶ 27 claims ─┬▶ 4 flagged
                                                                     └▶ 7 rejected
```

Every bar is clickable and lists its members. This directly answers "why isn't
my sentence in the results?": it was in none of the bars, or it fell out at a
named step with a named reason. It also makes the precision-over-coverage
choice visible and defensible instead of looking like a bug.

### 4.3 Reasons in plain words

Every rejection, flag and "not evaluable" carries the engine's reason code *and*
a one-line explanation, for example *"The quote says millions, the claim says
billions – scale mismatch"*. The code stays visible for people who need it.

### 4.4 Re-running

The UI does not run the model by default. Anything that would call the model
shows what will be sent (public filing text only), the estimated cost and the
cached result if one exists, and waits for an explicit action (V, and the
standing rule that only public text leaves the system).

## 5. Understanding the results

### 5.1 Three layers of detail (progressive disclosure)

Every result can be read at three depths. The user picks the depth; the default
is the first.

1. **Plain statement.** One sentence a non-specialist can read:
   *"In Q3 2025 the company said revenue was $4.2 billion. Its record for the
   same quarter says $4.0 billion."*
2. **Structured claim.** Metric, value and scale, period, basis, polarity, with
   each field linked to the words in the quote that support it, or to the
   assumption that fills it.
3. **Proof trace.** The claims, rules and assumptions the finding rests on, and
   the raw JSON for export and audit.

### 5.2 Anatomy of a finding card

```
┌──────────────────────────────────────────────────────────────┐
│ ◆ DISAGREEMENT · conditional            Revenue · Q3 2025    │
│                                                              │
│  Said    "Revenue was $4.2 billion"       10-Q · 28 Oct 2025 │
│  Record  "Net revenues of $4.0 billion"   10-Q · 28 Jul 2025 │
│          ─────────────────────────────────                   │
│  Difference  +$0.2 billion  (+5.0%)                          │
│                                                              │
│  Depends on  ⚑ "Revenue means total revenue"  (context store)│
│                                                              │
│  [ Open both in source ]  [ Proof trace ]  [ Resolve ⚑ ]     │
└──────────────────────────────────────────────────────────────┘
```

- **Grade word:** *proven* only when nothing in the proof is an assumption;
  otherwise *conditional* with the assumptions listed (III).
- **Both quotes** always side by side, each with document, date and link.
- **Time is explicit:** the period a claim is about and the date it was said are
  separate labelled fields, and a change over time is shown as *a change*, not
  a disagreement (VI).

### 5.3 The source reader

The most important screen. A split view:

```
┌─ Filing text ───────────────────────┬─ Claims in this view ─────────┐
│ …Total revenues were [$4.2 billion] │ ◆ Revenue · Q3 2025 · $4.2B   │
│ for the quarter, compared with      │   gate: passed                │
│ [$4.0 billion] in the same quarter  │ ◇ Revenue · Q3 2024 · $4.0B   │
│ last year…                          │   ⚑ assumes "same quarter     │
│                                     │     last year = Q3 2024"      │
│ Net income decreased due to weak    │ · "Net income decreased…"     │
│ demand.                             │   not evaluable: no figure    │
└─────────────────────────────────────┴───────────────────────────────┘
```

- Highlighted spans in the text link to claims and back; hover one, the other
  lights up.
- Sentences that produced nothing are visible too (quiet marker), with the
  reason, so absence is explained.
- Filters: by metric, by status (passed / flagged / rejected / not evaluable),
  by "rests on an assumption".

### 5.4 The review queue (stage 8, later)

One open flag at a time: the sentence in context, what is missing, the two or
three plausible answers as buttons, and what the choice will change ("this
resolves 3 other flags that depend on the same alias"). A decision is saved as
data in a context store, and the queue shows the effect immediately, which
makes the "decisions improve the system" loop tangible (VIII).

### 5.5 The trust page

A single page that answers "can I rely on this?", fed by the evaluation reports
the project already produces:

- precision and coverage per stage, against the threshold, met or missed;
- on which data (development vs held-out) and how many items;
- **"What this does not cover"** as a standing section – not a footnote.

It is the in-product twin of the evaluation section of `status.html` and must
read from the same report files, so the two cannot disagree.

## 6. Screens (first cut)

| # | Screen | Answers | Depends on |
|---|---|---|---|
| 1 | **Sources** – list of documents with run strip per row | What has been ingested and how far has it got? | stages 1–3, 5 (built) |
| 2 | **Document** – run strip, funnel, reader | What happened to this text? | built |
| 3 | **Claim** – three-layer view, history of versions | What exactly is claimed and where from? | built |
| 4 | **Company & metric timeline** – claims over time for one metric | How has what they said changed? | store queries (built) |
| 5 | **Findings** – list and card | Where does text disagree with record? | stages 6–7 (not built) |
| 6 | **Review queue** | What needs a human? | stages 4, 8 (not built) |
| 7 | **Trust** – quality numbers and limits | How far can I rely on it? | evaluation reports |
| 8 | **Glossary** – inline popovers, one page | What does this word mean? | none |

Screens 1–4, 7 and 8 need only what is already built, so a first release can be
useful before matching and comparison exist.

## 7. How it fits the engine (constraints)

- **Read-mostly.** The service reads the store and the evaluation reports.
  Writes are limited to actions the engine already has (ingest a public filing,
  submit a human decision), each through the engine's own validation.
- **No new logic in the UI.** Wording, grading and reason texts come from the
  engine (a reason-text table next to the reason codes), so the CLI and the UI
  say the same thing.
- **Reproducible pages.** Pages are rendered from the store plus a version of
  the instructions; the same store gives the same page.
- **Privacy.** Only public filing text. No accounts are needed for a read-only
  first release; if the service is ever shared, authentication becomes a spec
  topic, not an afterthought.
- **Status page rule.** The UI is a pipeline-adjacent component; the spec will
  say how it appears on `status.html`.

## 8. Slicing (proposal)

1. **003 – Read-only explorer:** sources, document (run strip, funnel, reader),
   claim, trust page, glossary. Works on today's data.
2. **004 – Findings:** after matching and comparison are specified and built.
3. **005 – Review:** after context resolution and the review loop exist.

Verification for the UI (per constitution VIII) is not accuracy of claims – the
engine owns that – but *fidelity and comprehension*: every number on a page
equals the stored value (automatic, test-first), every highlighted span equals
the stored quote (automatic), and a short comprehension check with real users
(section 9, question 5).

## 9. Open questions for the owner

Each has a recommendation so you can answer "yes" to all of them.

1. **Interface language.** Hebrew RTL chrome with English quotes, English
   chrome, or switchable? *Recommend: switchable, built right-to-left-safe from
   the start, Hebrew first; quotes always in their original direction.*
2. **Audience.** Only you for now, a small team, or public? *Recommend: single
   owner, no accounts in 003; keep the design account-ready.*
3. **Hosting.** Local app run from the repository, or a hosted service?
   *Recommend: runs locally first (same SQLite file), hosting decided in its own
   spec.*
4. **Uploading documents.** Only the public corpus, or may users add their own
   filings? *Recommend: corpus only in 003; uploads change privacy and are a
   separate spec.*
5. **Proof of understanding.** Is a small comprehension check acceptable – three
   people (or you) reading five pages and answering yes/no questions about what
   the page says? *Recommend: yes; it replaces long manual review.*
6. **Visual direction.** Do you want a clickable static mock-up (HTML, no
   backend) of the document reader and finding card before the spec? *Recommend:
   yes – it is the cheapest way to test the look and feel, and lets you react to
   something concrete.*

## 10. Owner feedback (2026-11-13)

Answers: Q1–Q3 yes (Hebrew first and switchable; single owner; local first). Q4:
agreed (public corpus only). Q6 yes (mock-up built). **Q5: no manual
dependency**, so the comprehension check in section 8 is dropped; verification
of the UI is automated only (stored values equal displayed values, highlighted
spans equal stored quotes, a wording check that bans verdict-of-truth language,
browser tests of the main flows, accessibility checks).

Changes to the flow, reflected in `mockup/mockup.html.txt`:

1. **Entities first.** The home screen is a list of entities (companies now;
   later non-profits, other organizations, public figures), each with an
   overall rating. *(Replaced in section 14: counts, no rating.)*
2. **Entity page.** The latest statements or publications of that entity, each
   tagged by the system (metric, period, source type, result, "rests on an
   assumption"), filterable.
3. **Statement page.** A simpler version of the earlier finding card: the quote,
   a plain reading, the result, what it was compared with, four-step "how we got
   here", and details collapsed.

**Visual direction (second round).** Messaging-app shell (Telegram/WhatsApp
style: chat list on one side, conversation on the other, single pane on a
phone) with investment-app cues (tickers, tabular numbers, a consistency
sparkline and quarter-on-quarter delta). Each entity shows a profile image (a
company logo; the mock-up uses placeholder monograms) and its latest statement
beside it (the rating's final position is described in section 11). Statements
in the entity page are
message bubbles; the comparison record on the statement page is shown as a
"reply" quote.

**Rating** *(replaced in section 14 by counts; kept here as the record of the
earlier proposal)*. The rating is a *consistency rating*, not an honesty or credibility
score: consistent statements divided by statements that could be checked,
always shown with coverage (how many statements could be checked at all), and
"not enough data" below 10 checked statements. Not-evaluable statements count
neither for nor against. This keeps to principles IV (flag rather than guess)
and VII (inconsistency is not falsehood). Open for the spec: whether the rating
is shown as a number, a band or both, and the rule for the band thresholds.

**Entity types beyond companies** (public figures in particular) change the
risk: a rating attached to a named person needs its own review of wording,
sources and privacy before it is built. The first release supports companies
only; other types appear in the UI as "coming soon".

## 11. Third round of feedback and open questions

*The rating, ring, trend, ticker values and the two open questions on ratings
in this section are replaced by section 14.*

Changes in the mock-up: a more distinctive look (a market ticker tape, a hero
header in the entity's colour with a rating ring and trend, mono-spaced figures,
status edges and icons on message bubbles); the rating appears first in the row
of tags, which runs from the left edge; and the external rating is a number
from 1 to 10 where **1 is the highest**. The mock-up derives it from
consistency (91% and above = 1, each 10 points lower = one step), a placeholder
mapping. Entities with fewer than 10 checked statements show "no rating".

**Open question – ratings and percentages per metric (to discuss later).**
Percentages (and the rating) should probably be computed *per metric and per
evaluation parameter* – revenue, net income, earnings per share, operating cash
flow, and whatever parameters we add for judging each entity – rather than as
one overall figure. To decide: which parameters exist and who defines them; the
weights, or whether to avoid weights by showing a per-metric profile; how, or
whether, the per-metric figures roll up into the single 1–10 rating; the
minimum sample per metric before a figure is shown; and how a metric with no
checked statements appears. Until this is decided the mock-up shows one overall
figure and says so on the rating page.

**Open question – the 1 = best scale.** A scale where 1 is best reverses the
usual reading of "higher is better" and of the percentages shown next to it. The
UI must always label it (for example "2 of 10, 1 = highest"). To decide whether
that stays in the spec as is.

## 12. Fourth round: usability fixes

Two defects found in the mock-up, both turned into requirements for the spec:

1. **One rating, one place** *(now one counts line, one place; see section 14)*. A number beside the profile image (a "new
   statements" counter) was read as a second, contradictory rating. Rule: an
   entity's rating appears once per place it is shown (list row, entity header),
   and no other number competes with it next to the profile image. The counter
   was removed. In the entity header the number appears once, in the ring.
2. **Back goes back to where the user came from.** The explanation of the
   rating returned to the main list even when it was opened from an entity page.
   Rule: every drill-down page has a back control that returns to the page it
   was opened from (an entity page, a statement page or the list), works from a
   direct link or after a reload, and names its destination ("Back to Example
   Corp"). In the mock-up the origin is carried in the address
   (`#about-entity-<id>`), so it does not depend on browser history.

Both rules will be checked by the automated browser tests named in section 10.

## 13. Next step

On your answers: write `specs/003-web-ui/spec.md` (stories, requirements,
verification, thresholds), then plan and tasks, and update `status.html` at each
step.

## 14. Fifth round: counts, not a rating (constitution 1.3.0)

The owner decided that any single number attached to a named entity reads as a
verdict on that entity, whatever it is called, and that a 1–10 scale invites
ranking ("the least credible company"). Constitution principle XI now forbids
an overall score, and principle VII requires every finding to name the
reference it was checked against. This replaces the rating in sections 10–12.

Changes, reflected in `mockup/mockup.html.txt`:

1. **Counts, not a rating.** The entity header shows plain counts: statements
   found, checked, matching the record, differing from the record, not
   checkable. No percentage, ring, trend line, quarter-on-quarter delta or
   ticker values.
2. **The minimum sample stays.** Below 10 checked statements the header shows
   "not enough data to count"; the statements themselves are still listed.
3. **No ranking.** Entities are never sorted or filtered by differences. The
   list is ordered by latest activity or by name.
4. **Neutral wording.** "Matches the record", "differs from the record" and
   "not checkable", not "consistent" and "inconsistent". Violet, never red.
5. **A difference shows its harmless explanations.** Every differing
   statement says that a difference may come from a published restatement, a
   different definition of the metric, rounding or another period, and that the
   system does not decide which text is right.
6. **The list row carries no number**, only the latest statement and its
   label, so nothing beside the profile image reads as a judgement (section
   12.1).

Questions closed by this round: a number or a band, the 1 = best scale, and how
per-metric figures roll up into one rating. Whether counts are also shown per
metric is decided in section 15.

Still open for the spec, and sharper now: entity types beyond companies. Counts
of differences attached to a named person carry the same risk a rating did, and
need their own review of wording, sources and privacy before they are built.

## 15. Sixth round: counts per metric

*Layout simplified in section 16; the decisions on counts per metric stand.*

The owner decided to show the counts per metric as well. Reflected in
`mockup/mockup.html.txt`:

1. **A "by metric" table** on the entity page, under the overall counts: one
   row per metric (revenue, net income, earnings per share, operating cash
   flow, other) with the same five counts as the header.
2. **Fixed order.** Rows always appear in the same order. They are never sorted
   by differences, and no row is highlighted for having more of them.
3. **Never combined.** There is no total, average or weighting across metrics.
   The header counts are plain sums of the rows, not a separate figure.
4. **Minimum per metric.** A metric with fewer than 3 checked statements shows
   "too few to count" (or "not checked" when none were) instead of matching and
   differing counts; the number of statements and of not-checkable ones is
   still shown.
5. **The table is shown only when the entity meets the overall minimum** (10
   checked). Below it, the header's "not enough data" stands alone.
6. **A metric filters the feed.** Selecting a metric shows only its statements
   and can be combined with the result filter. A bar names the active metric
   and clears it. The table can be collapsed, so it does not crowd the feed on
   a phone.

Open for the spec: the list of metrics and who maintains it, what "other"
includes, whether earnings per share is shown apart from net income, and the
per-metric minimum (3 is a placeholder).

## 16. Seventh round: a very simple layout

The owner found the entity page too heavy. Rule: **one line on the surface,
everything else behind one expansion.** Reflected in `mockup/mockup.html.txt`:

1. **One line under the entity's name:** "checked 18 of 29 statements · 2
   differ from the record", or "too few to count" below the minimum. No row of
   numbers, no table on the surface.
2. **One "details" expansion, closed by default.** It holds the full counts
   (matching, differing, not checkable), the per-metric table and the note on
   what the counts do and do not mean. It stays open while the user filters.
3. **The per-metric table has three columns:** metric, "checked x of y" and
   "differ from the record". Matching counts follow from these and are not
   repeated. A metric under the minimum shows "too few".
4. **Two result filters instead of four:** "all" and "only differing". The
   label on each statement still shows its result.

General rule for the spec: a data set that is not needed to read the page is
behind an expansion, never on the surface.
