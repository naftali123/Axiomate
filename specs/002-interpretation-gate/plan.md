# Implementation Plan: Claim Interpretation and Validation Gate

**Feature**: `002-interpretation-gate` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)
**Status**: Approved 2026-11-13

## Summary

Build the gate first, entirely without a model, and verify it on corrupted
claims. Collect the held-out filings. Then add interpretation: select the
segments worth reading, send each with its context to the model, store the
reply, turn it into candidates, pass them through the gate and into the claim
store. Last, the evaluation run that compares stored claims with the figures
tagged in the filings.

## Technical context

| Item | Choice |
|---|---|
| Language, storage, testing | As in spec 001: Python 3.12, SQLite, pytest, test-first |
| Model | Claude Opus 5.5 (`claude-opus-5-5`) through the Anthropic Python SDK |
| Model output | Structured output validated against a Pydantic model |
| Stored replies | One JSON file per reply, named by its key, in a directory |
| New runtime dependency | `anthropic`, as an optional extra; nothing else needs it |
| Number, date and term reading | Project-owned rules, standard library only |

Reasons are in [research.md](research.md).

## Constitution check

| Principle | How this plan complies |
|---|---|
| I. Model proposes, code decides | The model's reply is parsed into candidates and nothing more. Only `gate.check` followed by the claim store of spec 001 can store a claim. |
| II. Traceability | The model returns quotes, not offsets. Code finds the quote inside the segment that was sent; a quote not found verbatim is rejected. |
| III. No silent assumptions | The gate demands, for scale, period and metric, either evidence in the quote or an assumption on the claim. |
| IV. Flag rather than guess | Missing evidence gives a flag and the status `not-formalizable`. The gate never fills a field. |
| V. Reproducibility | Replies are stored under input hash, model id and instruction version. A run reads the store first. Tests run only from stored replies. |
| VI. Time-indexed claims | The period check reads dates and period words from the quote. |
| VIII. Verified, test-first | Each phase starts with its tests. The held-out filings are collected in phase 2 and not opened during development. |
| IX. Status page | Updated at each checkpoint. |

No violations.

## Project structure

```
src/axiomate/
  gate/
    numbers.py      # reads figures, scale words and signs from a quote
    periods.py      # reads dates and period words from a quote
    lexicon.py      # terms per metric; hedging and forward-looking words
    check.py        # the checks, in a fixed order; one outcome per candidate
  interpret/
    select.py       # which segments are sent, and with what context
    prompt.py       # the instructions and their version
    reply.py        # the model's output model; candidates from a reply
    replies.py      # the reply store: key, read, write
    client.py       # the one place that calls the model
    run.py          # one pass over a document, with its counts
  evaluate/
    tagged.py       # compare stored claims with tagged figures
    report.py       # precision, coverage, pass rate; thresholds
  store/schema.sql  # two new tables (schema version 2)
eval/
  filings/          # held-out filings, unchanged, with manifest
  facts/            # their tagged figures
  replies/          # stored model replies for all evaluation filings
  splits.json       # development and held-out
  reports/          # evaluation reports
tools/
  corrupt_for_gate.py   # deterministic generator of gate test cases
  claims_from_facts.py  # correct claims built mechanically from tags
```

## Design decisions

1. **Order of the gate's checks is fixed**: value, sign, scale, period,
   metric, hedging. The first contradiction decides a rejection; all missing
   evidence is collected into flags.
2. **Contradiction rejects, missing evidence flags.** If the quote says
   something different from the claim (another number, another sign, another
   scale word, another date), the candidate is rejected. If the quote is
   silent and no assumption covers the field, the candidate is flagged and
   stored as `not-formalizable`.
3. **Reading a figure.** The rules read forms such as `189,346`, `$1.8
   million`, `(4,554)`, `$ .71`, `6%`. A quote with several figures passes the
   value check if the claim's stated value is one of them.
4. **Sign.** Parentheses, "loss", "decrease", "decline" and "negative" call
   for a negative value; their absence calls for a non-negative one. A change
   claim takes its sign from the direction word.
5. **Scale evidence.** A scale word in the quote, or an assumption on
   `stated_scale`. A figure with no scale word and no assumption is taken as
   units only if it is a per-share amount or a percentage.
6. **Period evidence.** Dates and phrases such as "three months ended March
   31, 2024" are read by rule and compared with the claim's period. Relative
   phrases ("the same period in the prior year") are never resolved by the
   gate; they need an assumption.
7. **Metric evidence.** A fixed list of terms per metric. A term for a
   different one of the four metrics next to the figure, with none for the
   claimed metric, is a contradiction. A component term ("rental revenue")
   requires the `unmapped_metric` flag.
8. **What the gate cannot do.** A field that rests on an assumption is not
   checked against the text: the gate only confirms the assumption is there.
   Whether such assumptions are right is measured by the evaluation, on the
   tagged figures, not guaranteed by the gate.
9. **Which segments are sent.** Only segments that contain a digit and a
   metric term, or table rows whose label contains a metric term. The rule
   uses the same term list as the gate and never looks at tags.
10. **Context.** A table row is sent with the first rows of its table and the
    three segments before the table. A sentence is sent with the nearest
    heading and the two sentences before it. The context is marked as context;
    quotes must come from the segment itself.
11. **One call per segment**, with the instructions as a cached prefix.
    Grouping several segments into one call is left out for now, so that one
    reply maps to one segment and a failure costs one segment.
12. **Reply key**: SHA-256 of the instruction version, the model id, and the
    exact text sent (segment and context). The same text under the same
    instructions and model is never sent twice.
13. **Stored replies are files**, one per key, holding the request text, the
    raw reply, the model id reported by the service and the token counts. The
    directory for evaluation filings is committed.
14. **Runs and outcomes are stored in the database**: one row per candidate
    with its reply key, outcome, deciding check, field and, when stored, its
    claim id. These rows are append-only like every other table.
15. **A reply is a list of candidates** in the claim schema without offsets,
    ids or status. Code adds document, segment, offsets, publication date and
    the company (the document's publisher, unless the candidate names another,
    which is flagged `implicit_scope`).
16. **Two candidates for the same span and metric**: the first is stored; the
    second is rejected as a duplicate and counted.
17. **Evaluation is deterministic** and reads only the store and the tag
    files. It writes a report file with every number, its data set and its
    threshold.
18. **The model call is isolated** in `client.py`. Everything else, including
    all tests, works from stored replies. A missing reply without permission
    to call is an error, never a silent skip.
19. **No personal data.** The request holds the instructions and filing text
    only. The API key comes from the environment and is never written.

## Changes found while building the gate

- **The figure is read where it stands in its segment.** A quote may be only
  the figure (`8,180`), while its parentheses, scale word or "approximately"
  sit just outside it. Those count. The period must still be in the quote
  itself, and the metric in the quote or the segment.
- **A negative value needs something to show for it**: parentheses, a governing
  decrease or loss phrase, a row label that says loss, or an assumption.
  Otherwise the claim is flagged. A figure written as negative but claimed as
  positive is rejected.
- **Scale in tables.** A figure in a table row needs an assumption for its
  scale even when the scale is units, unless it is a per-share amount or a
  percentage: tables state their scale in the heading.
- **Probes.** Hedge and scale checks need prose with "approximately $X
  million". The generator builds such claims mechanically with a placeholder
  metric and period; they test the reading of the figure and are not counted
  as correct claims.
- **Three hand-written claims of spec 001 were corrected.** See the checkpoint
  in tasks.md.
- **What the correct-claim set does and does not exercise.** Claims built from
  tags carry assumptions for period and scale by construction, so on them the
  gate's period and scale checks only confirm the assumption exists. They do
  exercise the reading of displayed figures, signs and row labels.

## Cost

Estimated before any call, to be replaced by a measurement on the first filing:

- About 100–150 selected segments per filing, 13 filings: roughly 1,300–2,000
  calls.
- Per call about 1,500 input tokens (mostly the cached instructions) and 400
  output tokens.
- At the list price of Claude Opus 5.5 ($4 input and $20 output per million
  tokens), that is in the order of $15–30 for all evaluation filings, once.
  Stored replies make every later run free.

The run stops and reports if the first filing costs more than twice its
estimate.

## Risks

| Risk | Mitigation |
|---|---|
| A wrong assumption passes the gate (decision 8) | Precision on tagged figures is measured on held-out data; the threshold is 98% |
| Table context is not enough to find the period | Context rule is tuned on development filings only; flagged claims are counted, not hidden |
| The segment selection misses claims | Coverage against tagged figures counts every tagged figure, selected or not |
| Instructions are tuned until held-out numbers look good | Held-out replies are produced once, after instructions are frozen; any later change of instructions is recorded with its version |
| Cost overrun | Estimate first, measure on one filing, stop rule |
| The service changes the model behind the id | The reported model id is stored with each reply; stored replies are never regenerated silently |

## Phases

1. Gate reading rules and checks, with the corruption test set.
2. Held-out data: filings, tagged figures, split file.
3. Interpretation from stored replies: selection, reply model, run, counts.
4. Live calls: instructions, client, development filings. *Needs the API key.*
5. Evaluation: tagged comparison, report, held-out run, prose sample.
6. Polish: reproducibility run, quickstart, status page.

Detailed tasks are in [tasks.md](tasks.md).
