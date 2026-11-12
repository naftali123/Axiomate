# Verification Strategy

**Scope**: the whole pipeline, across all features.
**Governed by**: constitution principle VIII.
**Last updated**: 2026-11-12

This document says, for each pipeline stage, what "working" means, how it is
measured and on what data. Each feature spec has a Verification section that
covers its own stages and refers back here.

## Two kinds of verification

- **Correctness tests** for deterministic stages (1, 3, 4, 5, 6, 7). The
  expected output is known exactly, so the result is pass or fail.
- **Quality measurement** for the interpretation stage (2) and for the pipeline
  end to end. The result is precision and coverage against labelled data,
  compared with a threshold.

## Per-stage verification

| Stage | "Working" means | Method | Data | Threshold |
|---|---|---|---|---|
| 1. Ingestion | Text is returned unchanged; segments are split correctly; figures visible in the filing are present in the stored text | Round-trip test; comparison with hand-checked boundaries; figure-presence check | Real filings; boundary labels; structured figures | Round trip 100%; boundaries ≥ 98%; figure presence 100% |
| 2. Interpretation | Extracted claims match the true figures | Compare extracted claims with structured figures and hand labels | Filings with known figures; hand labels | Set in the stage's spec |
| 3. Validation gate | Corrupted claims are caught; correct claims pass | Submit correct claims and corrupted copies | Correct claims; corruption generator | Set in the stage's spec |
| 4. Context resolution | Flags resolve to the right answer, each as a recorded assumption | Compare with known resolutions | Flagged cases with labelled resolutions | Set in the stage's spec |
| 5. Claim store | Bad claims are rejected; nothing can be altered; runs are identical | Submit well-formed and malformed claims; attempt changes; compare exports of two runs | Claim fixtures; corruption generator | Rejection 100%; acceptance 100%; exports identical |
| 6. Matching | The pairs that should be compared are found, and no others | Compare with labelled pairings | Claims with known pairings | Set in the stage's spec |
| 7. Comparison | The verdict is right for a known relation | Run on pairs with a known answer | Synthetic and real pairs | Set in the stage's spec |
| 8. Review | A human decision is applied automatically next time | Repeat a case after a decision | Repeated cases | Set in the stage's spec |
| End to end | Known discrepancies are found, without false alarms on clean text | Run the pipeline on documents with known discrepancies and on unchanged controls | Known real discrepancies; corrupted copies; controls | Set before the first end-to-end run |

A threshold marked "set in the stage's spec" must be fixed before that stage is
built (principle VIII).

## Data sources

1. **Real filings** from the SEC's public filings database (EDGAR): earnings
   releases and quarterly and annual reports of US-listed companies.
2. **Structured figures** that companies file alongside the text (XBRL). They
   give the correct values of the four first-version metrics per company and
   period, so extracted claims can be checked without hand labelling. They do
   not cover adjusted figures or hedged statements. *The exact data service and
   its coverage are still to be confirmed.*
3. **Known real discrepancies**: restated results and missed guidance, which are
   publicly documented.
4. **Deliberate corruption**: a real document or claim with one element changed
   (a number, a period, a direction), produced by a deterministic generator so
   the correct answer is known exactly. Unchanged copies are the controls.
5. **Hand labels**: a small set (about 100–200 sentences) for what the sources
   above cannot provide: sentence boundaries, hedges, what should be flagged.

## Rules for the data

- **Provenance**: every file records where it came from, when it was retrieved
  and its SHA-256 hash, in a manifest next to it. Files are stored unchanged.
- **Human-confirmed labels**: a label suggested by a model or a script counts
  only after a person has confirmed it.
- **Development and held-out sets**: the evaluation data is split in two. Rules
  are written and tuned against the development set only; the held-out set is
  used to report numbers and is never used to tune.
- **Growth**: every false alarm or miss found in review is added to the
  development set as a new case.
- **Reporting**: the latest precision and coverage are shown on `status.html`.

## Layout

```
tests/fixtures/      # small, per-feature test inputs with exact expected output
eval/
  filings/           # real filings, unchanged, with manifest
  facts/             # structured figures per company and period
  gold/              # hand labels and the labelling guidelines
  discrepancies/     # known real cases and corrupted copies, with answers
  splits.json        # which items are development and which are held out
```

## Known constraints

- The development environment currently cannot reach the SEC's servers. Sample
  filings must be downloaded by a person, or the hosts must be allowed in the
  environment's network settings.
- Hand labelling needs a person's time; the first batch is sized to stay small.
