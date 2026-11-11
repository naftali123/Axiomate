# Axiomate Constitution

Status: draft, version 0.1.0

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
which side is true unless an external ground-truth source is explicitly supplied.

### VIII. Measured, test-first changes
Rules and comparison logic are written test-first. Every change is run against a
hand-labeled evaluation set, and precision and coverage are reported.

## Governance

Specs, plans and tasks must comply with this constitution. Amending it requires a
documented rationale and a version bump.
