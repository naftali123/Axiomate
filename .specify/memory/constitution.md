# Axiomate Constitution

Status: ratified 2026-11-11, version 1.3.0

## Core principles

### I. The language model proposes, deterministic code decides
A language model may only turn text into candidate claims or suggest resolutions.
It never produces a verdict. Every claim it proposes must pass the deterministic
validation gate before it is used.

### II. Every result traces to the text
Each claim carries the exact source span it came from, and that span must exist
verbatim in the stored document. Each verdict carries a proof trace that names the
claims, rules and assumptions it rests on.

### III. No silent assumptions
Anything not literally stated in the text is recorded as a named assumption with
its origin (context store, model or human). A verdict that depends on any
assumption is graded `conditional`, never `proven`.

### IV. Flag rather than guess
Text that cannot be formalized reliably is flagged with a reason code and reported
as `not evaluable`. Precision takes priority over coverage: a missed contradiction
is preferred to a wrong accusation.

### V. Reproducibility
The same inputs, rule set and context stores always produce the same verdicts.
Model outputs are cached under input hash, model version and prompt version.
Stages after interpretation can be re-run without calling the model.

### VI. Claims are time-indexed
Every claim records both when it was said and the period it is about. A change
over time is not a contradiction.

### VII. Inconsistency is not falsehood
Axiomate reports disagreement between a text and a record. It does not assert
which side is true.

Every comparison is made against a declared reference. A reference is itself a
claim with an origin, never a ground truth: no source, however reliable, makes a
finding true. A finding states the relation ("consistent with R", "disagrees
with R"), names R, and records reliance on R as an assumption (principle III).
This principle governs the product's findings; the labels used to evaluate the
system itself are set by principle VIII.

### VIII. Verified, test-first changes
Rules and comparison logic are written test-first. Every change is run against a
hand-labeled evaluation set, and precision and coverage are reported.

No pipeline stage may be built until three things are written down: how the
stage will be verified, where the data for that verification comes from, and the
threshold it must meet. The project-wide strategy lives in
`specs/verification.md`; each feature spec has a Verification section for the
stages it covers. Evaluation data is split into a development set, used to write
and tune rules, and a held-out set, used only to report results.

### IX. Living status page (blocking rule)
The repository must contain exactly one Hebrew HTML status page, `status.html`, at
the repository root. It gives a highly summarized, high-level picture of the
project and must contain at least:

- a simple diagram of the architecture, with the status of each pipeline stage
  (not started, specified, built or tested);
- a brief of the current work;
- the planned work;
- the open issues;
- the accuracy numbers (precision and coverage) from the latest evaluation run,
  or a statement that none exist yet;
- the most recent key decisions, each with a one-line reason;
- a table of feature specs with their phase (spec, plan, tasks, done) and a link;
- the top risks;
- the date of its last update.

Keeping the page up to date is the most important part of this rule. Any change
that alters the project's state, architecture, plans or open issues must update
`status.html` in the same change. A change that leaves the page stale must not be
merged. The page stays short: it summarizes and links to specs, it does not
duplicate them. Its detailed requirements, including the detail panel behind
each diagram component, are in `specs/status-page.md`.

Enforcement: `CLAUDE.md` instructs every AI session to follow this rule, and the
`status-page` check on pull requests fails when specs, code or this constitution
change without `status.html` changing. The label `status-not-affected` skips the
check for changes that truly do not alter the project's state.

### X. Sources have declared standing
Every source can be questioned, but sources are not all equal: an audited filing
and an anonymous post do not carry the same weight. The standing of each kind of
source, and the order in which references are preferred, is written down as part
of the rule set, applied the same way to every case, and replaceable. A change of
standing is a change of rule set (principle V). No standing is implied or
assigned silently.

### XI. Specific findings, never an overall score
Axiomate reports specific results, each with its label (consistent,
disagreement, conditional, not evaluable) and the reference it rests on. It
does not combine them into a credibility or trust score for a company, a person
or a document. Any summary of results is a set of counts that always states how
much could be checked: how many claims were found, how many were evaluable, and
against which references.

## Governance

Specs, plans and tasks must comply with this constitution. Amending it requires a
documented rationale and a version bump.

## Amendments

- **1.1.0 (2026-11-12)**: principle VIII extended to require a verification
  method, data source and threshold before any stage is built. Rationale: the
  first feature's plan had tests but did not say where test data came from or
  how each stage would be shown to work.
- **1.2.0 (2026-11-12)**: principle IX now refers to `specs/status-page.md`
  for the status page's detailed requirements. Rationale: the page gained
  per-component detail panels and needed its own focused specification.
- **1.3.0 (2026-11-14)**: principle VII no longer allows any source to be
  treated as ground truth: every comparison names a declared reference, which is
  itself a claim, and reliance on it is an assumption. Principle X added: sources
  differ in standing, and the standing is declared, uniform and replaceable.
  Principle XI added: no overall credibility score, only labelled findings with
  the amount of data checked. Rationale: refusing all references would give an
  anonymous post the same weight as an audited filing, which is itself a hidden
  choice; objectivity comes from declaring the references and letting them be
  replaced, not from having none. A single score would hide what could not be
  checked and would read as an accusation, which principle VII forbids.
