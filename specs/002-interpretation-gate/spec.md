# Feature Specification: Claim Interpretation and Validation Gate

**Feature**: `002-interpretation-gate`
**Created**: 2026-11-13
**Status**: Approved 2026-11-13
**Domain**: Corporate financial disclosures
**Builds on**: [001-claim-foundation](../001-claim-foundation/spec.md)

## Purpose

Spec 001 stores documents and accepts claims that someone else has written.
This feature makes the system produce claims itself. It covers pipeline stages
2 (interpretation) and 3 (validation gate):

- **Interpretation**: a language model reads a stored document and proposes
  candidate claims in the claim schema.
- **Validation gate**: deterministic checks decide what happens to each
  candidate. The model never has the last word (constitution principle I).

The two stages are specified together because neither can be judged alone: the
gate is measured on what the model actually proposes, and the model's output is
only usable after the gate.

## User Scenarios

### Story 1 – Check a candidate claim against its own quote (Priority: P1)

A candidate claim arrives with its quoted span. Before it is stored, the system
re-reads the quote by fixed rules and compares what the rules find with what
the claim says. A claim whose number, scale, period or metric is not supported
by its quote is not stored as a formal claim.

**Why this priority**: this is the safeguard that makes a model usable at all.
It is deterministic, so it can be built and verified completely before any
model is called.

**Independent test**: submit correct claims and copies with one element changed
(a digit, the scale, the period, the metric, the sign) and confirm that every
changed copy is caught and every correct claim passes.

**Acceptance scenarios**:

1. **Given** a claim whose value agrees with the number written in its quote,
   **when** it is checked, **then** it passes.
2. **Given** a claim whose value differs from the number in its quote (a
   changed digit, a wrong scale, a wrong sign), **when** it is checked,
   **then** it is rejected with a reason code naming the field.
3. **Given** a claim whose period or metric is not stated in its quote and has
   no assumption recording where it came from, **when** it is checked,
   **then** it does not pass as a formal claim.
4. **Given** a claim whose quote contains a hedge ("approximately", "expects",
   "may") that the claim does not reflect, **when** it is checked, **then**
   it is flagged.
5. **Given** any outcome, **when** the check finishes, **then** the outcome and
   its reason are recorded, so that the share of candidates that pass can be
   reported.

### Story 2 – Propose claims from a stored document (Priority: P2)

An analyst asks the system to read a stored document. The system proposes
claims about the four metrics, sends each through the gate, and stores those
that pass. Running the same request again gives the same result without calling
the model.

**Why this priority**: this is the first point at which Axiomate turns text
into claims without a person writing them.

**Independent test**: run interpretation on one stored filing twice and confirm
that claims are stored, each traceable to its sentence, and that the second run
makes no model call and changes nothing.

**Acceptance scenarios**:

1. **Given** a stored document, **when** interpretation runs, **then**
   candidate claims are proposed, each with the exact quoted span it rests on.
2. **Given** a figure in a table row whose period and scale are stated only in
   the table heading, **when** it is interpreted, **then** the claim records
   the period and the scale as named assumptions with their origin.
3. **Given** a statement the model cannot express in the schema (no amount, a
   metric outside the four, an opinion), **when** it is interpreted, **then**
   it is proposed with a flag and a reason code, not dropped and not guessed.
4. **Given** a document already interpreted with the same model and the same
   instructions, **when** interpretation runs again, **then** the stored
   output is reused, no model call is made and the store does not change.
5. **Given** a model reply that is malformed or cannot be read, **when** it is
   received, **then** nothing from it is stored and the failure is reported.

### Story 3 – Report how well it works (Priority: P3)

A maintainer runs an evaluation and gets precision, coverage and the pass rate
at the gate, on development filings and separately on filings never used
during development.

**Why this priority**: constitution principles IV and VIII require the numbers
before the output is trusted, and the status page must show them.

**Independent test**: run the evaluation on the held-out filings and confirm
that the report states each number, the data it was measured on, and whether
each threshold was met.

**Acceptance scenarios**:

1. **Given** filings with embedded figures, **when** the evaluation runs,
   **then** each extracted claim about a tagged figure is compared with that
   figure, and precision and coverage are reported.
2. **Given** the held-out filings, **when** the evaluation runs, **then**
   their results are reported separately from the development results.
3. **Given** an evaluation report, **when** the status page is updated,
   **then** it shows the held-out numbers and says what they do not cover.

### Edge cases

- One sentence states several figures for several periods ("for the three and
  nine months ended June 30 was $5.4 million and $12.1 million, respectively").
- A figure is a change, not a level ("decreased by $11.1 million").
- A negative figure is written in parentheses, or as "loss".
- A table row gives no period or scale; they are in the heading above it.
- The same figure appears in a sentence and in a table.
- A figure belongs to a component of a metric ("rental revenue"), not to the
  metric itself.
- A statement concerns a different company (a subsidiary, a competitor).
- The quote the model returns differs from the stored text by one character.
- The model proposes two different claims for the same span and metric.
- The model service is unavailable or returns nothing.

## Requirements

### Functional requirements – validation gate

- **FR-001**: Every candidate claim MUST pass through the gate before it is
  stored; no path into the claim store bypasses it for model-proposed claims.
- **FR-002**: The gate MUST re-read the number in the quote by fixed rules and
  require that it equals the claim's stated value, and that the stated value
  multiplied by its scale equals the normalized value, with the sign that the
  wording gives (loss, decrease, parentheses).
- **FR-003**: The gate MUST require evidence for the scale: either the scale
  word is in the quote, or an assumption on the claim records where the scale
  comes from.
- **FR-004**: The gate MUST require evidence for the period in the same way:
  the dates or period words in the quote must agree with the claim's period,
  or an assumption records where the period comes from.
- **FR-005**: The gate MUST require that a term for the claim's metric, from a
  fixed list of terms per metric, appears in the quote or in its segment, or
  that an assumption records where the metric comes from.
- **FR-006**: The gate MUST check hedging words in the quote against the claim:
  an approximation word requires an approximate value kind; a forward-looking
  word requires guidance or forecast; a conditional or reported-speech
  construction requires a flag.
- **FR-007**: The gate MUST give each candidate exactly one outcome: `passed`,
  `flagged` (stored as not formalizable, with reason codes) or `rejected`
  (not stored), and MUST record the outcome, the check that decided it and the
  field concerned.
- **FR-008**: The gate MUST be deterministic and MUST NOT call a model.
- **FR-009**: When evidence is missing the gate MUST flag, never fill the gap
  itself (constitution principle IV).

### Functional requirements – interpretation

- **FR-010**: The system MUST propose claims for a stored document by calling
  a language model, limited to the four first-version metrics.
- **FR-011**: Each proposed claim MUST carry the quoted span it rests on; the
  system, not the model, locates the quote in the stored text and computes the
  offsets, and a quote that is not found verbatim is rejected.
- **FR-012**: The model MUST be given a segment together with the context
  needed to read it (for a table row, the heading rows of its table), and
  anything taken from that context rather than from the quote MUST be recorded
  as an assumption with origin `model`.
- **FR-013**: The model's reply MUST be stored unchanged under a key made of
  the input's hash, the model version and the instruction version. A later run
  with the same key MUST reuse the stored reply and make no call.
- **FR-014**: The stored replies for the evaluation filings MUST be kept in the
  repository, so that tests and evaluation runs are reproducible without
  access to the model.
- **FR-015**: Only document text may be sent to the model service. No
  information about the user or the project is sent.
- **FR-016**: A run MUST report how many segments were read, how many model
  calls were made, how many were served from stored replies, and how many
  candidates passed, were flagged and were rejected.
- **FR-017**: A failed or unreadable model reply MUST store nothing and MUST be
  reported; it MUST NOT stop the rest of the document from being processed.

### Functional requirements – evaluation

- **FR-018**: The system MUST compare extracted claims with the figures
  embedded in the filing and report precision and coverage as defined below.
- **FR-019**: Development and held-out filings MUST be listed in a split file;
  the held-out filings MUST NOT be used to write or tune rules or instructions.
- **FR-020**: The evaluation report MUST state, for each number, the data it
  was measured on and the threshold it is compared with.

### Key entities

- **Candidate claim**: a claim proposed by the model, before the gate.
- **Gate outcome**: `passed`, `flagged` or `rejected`, with the deciding check
  and field.
- **Model reply record**: the stored reply with its key (input hash, model
  version, instruction version).
- **Interpretation run**: one pass over a document, with its counts.
- **Evaluation report**: precision, coverage and pass rate per data set.

## Out of scope

- Resolving flags from context stores (stage 4).
- Matching and comparing claims (stages 6 and 7), and any verdict.
- Metrics beyond the four; documents other than quarterly and annual reports.
- Choosing between two models or tuning a model.
- Checking a claim against anything other than its own document.

## Success criteria

- **SC-001**: On the held-out filings, at least 98% of the passed claims that
  cite a tagged figure agree with it in metric, value and period.
- **SC-002**: On the held-out filings, at least 70% of the tagged figures for
  the four metrics are covered by a passed claim.
- **SC-003**: Every deliberately corrupted claim in the test set is caught by
  the gate, with the expected reason code.
- **SC-004**: At least 98% of the correct claims in the test set pass the gate.
- **SC-005**: A second run over the same documents makes no model call and
  leaves the store unchanged.
- **SC-006**: Of the sampled prose claims reviewed by a person, at least 90%
  are judged correct.

Precision is set far above coverage on purpose: a missed claim costs coverage,
a wrong claim can lead to a wrong accusation (constitution principle IV).

## Verification

This feature covers stages 2 and 3. The project-wide strategy is in
[../verification.md](../verification.md).

**Definitions**

- A claim *cites* a tagged figure when its quoted span contains the figure as
  displayed, in the segment where the tag is.
- *Precision*: of the passed claims that cite a tagged figure for one of the
  four metrics, the share whose metric, normalized value and period equal the
  tag's.
- *Coverage*: of the tagged figures for the four metrics, the share cited by a
  passed claim that agrees with the tag.
- *Pass rate*: of all candidates, the share with outcome `passed`.

| What is verified | Method | Data | Threshold |
|---|---|---|---|
| The gate catches wrong claims (SC-003) | Submit corrupted copies of correct claims | A deterministic generator, at least 10 corrupted claims per kind: digit changed, scale changed, sign flipped, period changed, metric changed, hedge removed, assumption removed | 100%, each with the expected code |
| The gate lets correct claims through (SC-004) | Submit correct claims | The 21 hand-written claims of spec 001, plus claims built mechanically from the tagged figures of the development filings | ≥ 98% pass |
| Extracted claims are right (SC-001) | Compare with tagged figures | Held-out HTML filings | Precision ≥ 98% |
| Enough is extracted (SC-002) | Compare with tagged figures | Held-out HTML filings | Coverage ≥ 70% |
| Prose claims are right (SC-006) | A person answers yes or no on a sample | About 30 passed claims from running prose, drawn from the held-out filings by a fixed rule | ≥ 90% judged correct |
| Runs are reproducible (SC-005) | Run twice; count calls; compare exports | Development filings with stored replies | No call on the second run; exports identical |
| Nothing is silently dropped | Count candidates by outcome | Any run | Passed + flagged + rejected = proposed |

**Data collection**

- **Development set**: the five HTML filings already in the repository, with
  their tagged figures. Instructions and rules are written and tuned on these.
- **Held-out set**: at least eight further HTML filings with tagged figures,
  from at least four companies not in the development set, taken from the same
  open dataset (`kapilrao/SEC-EDGAR`) with the same provenance record. They
  are collected before interpretation is built and are not read during
  development. At least one annual report is included.
- **Tagged figures** are the company's own machine-readable tags. They are an
  independent source, so no person needs to confirm them.
- **Prose sample**: claims in running prose have no tags. A fixed rule (every
  n-th passed prose claim, in store order) draws about 30 from the held-out
  filings, and the repository owner answers yes or no on each, once.

**What these numbers will not show**

- Tagged figures sit mostly in tables and notes. Precision and coverage
  therefore say most about tabular figures.
- The prose figure rests on about 30 claims, so it is a rough estimate: with 30
  cases, one error moves it by more than three points. It is reported as an
  estimate.
- Claims the model never proposed from prose are not counted at all: there is
  no measure of prose coverage in this feature.
- Plain-text filings carry no tags and are not measured here.

## Dependencies and assumptions

- **Model service**: Claude through Anthropic's API (decided 2026-11-13). The
  exact model version is fixed in the plan and recorded with every reply. An
  API key is supplied by the repository owner and is never stored in the
  repository.
- **Cost**: model calls are paid per use. The plan must estimate the cost of
  interpreting the evaluation filings before any call is made, and limit which
  segments are sent.
- Tests in continuous integration never call the model; they run from the
  stored replies.
- The claim store, schema and status rules of spec 001 are used unchanged. If
  this feature needs a schema change, it is made as an amendment to spec 001.

## Clarifications

Resolved on 2026-11-13:

- **Model service**: Claude through Anthropic's API.
- **How prose is evaluated**: automatically where tags exist, plus one small
  yes/no sample for prose, instead of a full hand-labelled set.

- **Thresholds**: approved as proposed with the specification (98% precision,
  70% coverage, 90% on the prose sample; 100% and 98% for the gate).

## Constitution check

- I (model proposes, code decides): FR-001, FR-008; the model's reply is only
  ever a candidate.
- II (traceability): FR-011.
- III (no silent assumptions): FR-003, FR-004, FR-005, FR-012.
- IV (flag rather than guess): FR-007, FR-009, Story 2 scenario 3; precision
  threshold above coverage.
- V (reproducibility): FR-013, FR-014, SC-005.
- VI (time-indexed claims): FR-004.
- VII (inconsistency is not falsehood): no verdicts in this feature.
- VIII (verified, test-first): the Verification section fixes method, data and
  thresholds; the held-out set is collected before the stage is built.
- IX (status page): Story 3 scenario 3.
