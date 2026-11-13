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
   overall rating.
2. **Entity page.** The latest statements or publications of that entity, each
   tagged by the system (metric, period, source type, result, "rests on an
   assumption"), filterable.
3. **Statement page.** A simpler version of the earlier finding card: the quote,
   a plain reading, the result, what it was compared with, four-step "how we got
   here", and details collapsed.

**Rating.** The rating is a *consistency rating*, not an honesty or credibility
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

## 11. Next step

On your answers: write `specs/003-web-ui/spec.md` (stories, requirements,
verification, thresholds), then plan and tasks, and update `status.html` at each
step.
