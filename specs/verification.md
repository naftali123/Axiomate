# Verification Strategy

**Scope**: the whole pipeline, across all features.
**Governed by**: constitution principle VIII.
**Last updated**: 2026-11-13

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
| 1. Ingestion | Text is returned unchanged; segments are split correctly; figures visible in the filing are present in the stored text | Round-trip test; comparison with confirmed boundary labels; figure-presence check | Real filings; boundary labels; structured figures | Round trip 100%; boundaries ≥ 98%; figure presence 100% |
| 2. Interpretation | Extracted claims match the true figures | Compare extracted claims with structured figures; a person answers yes or no on a small sample of prose claims | Held-out filings with known figures; about 30 sampled prose claims | Proposed in spec 002 (draft): precision ≥ 98%, coverage ≥ 70%, prose sample ≥ 90% |
| 3. Validation gate | Corrupted claims are caught; correct claims pass | Submit correct claims and corrupted copies | Correct claims; corruption generator | Proposed in spec 002 (draft): corrupted caught 100%; correct pass ≥ 98% |
| 4. Context resolution | Flags resolve to the right answer, each as a recorded assumption | Compare with known resolutions | Flagged cases with labelled resolutions | Set in the stage's spec |
| 5. Claim store | Bad claims are rejected; nothing can be altered; runs are identical | Submit well-formed and malformed claims; attempt changes; compare exports of two runs | Claim fixtures; corruption generator | Rejection 100%; acceptance 100%; exports identical |
| 6. Matching | The pairs that should be compared are found, and no others | Compare with labelled pairings | Claims with known pairings | Set in the stage's spec |
| 7. Comparison | The verdict is right for a known relation | Run on pairs with a known answer | Synthetic and real pairs | Set in the stage's spec |
| 8. Review | A human decision is applied automatically next time | Repeat a case after a decision | Repeated cases | Set in the stage's spec |
| End to end | Known discrepancies are found, without false alarms on clean text | Run the pipeline on documents with known discrepancies and on unchanged controls | Known real discrepancies; corrupted copies; controls | Set before the first end-to-end run |

A threshold marked "set in the stage's spec" must be fixed before that stage is
built (principle VIII).

## Data sources

1. **Real filings** from the open dataset `kapilrao/SEC-EDGAR` on Hugging Face
   (Apache-2.0 licence, no account needed). It holds the original content of
   about 8 million filings with their accession number, filing date, period and
   filer. Quarterly (10-Q) and annual (10-K) reports are used. Older filings are
   plain text and recent ones are HTML, which covers both input formats.
2. **Structured figures embedded in the filings.** Recent HTML filings carry
   machine-readable tags around their financial figures (inline XBRL), naming
   the metric, period, unit and scale. They give the correct values of the four
   first-version metrics from the same file as the text, so extracted claims
   can be checked without hand labelling and without a second source. They do
   not cover adjusted figures or hedged statements.
3. **Known real discrepancies**: restated results, found by comparing a
   company's later filings with its earlier ones in the same dataset.
4. **Deliberate corruption**: a real document or claim with one element changed
   (a number, a period, a direction), produced by a deterministic generator so
   the correct answer is known exactly. Unchanged copies are the controls.
5. **Hand labels**: a small set (about 100–200 sentences) for what the sources
   above cannot provide: sentence boundaries, hedges, what should be flagged.

Checked on 2026-11-12 by downloading sample files: quarterly reports up to 2025
are present, the content is the original HTML, and filings from about 2020
onward carry embedded figures for the four metrics.

**Limits of this source**

- Earnings press releases are not included: each current-report (8-K) record
  holds only the cover document, not the attached release. The first version
  therefore works on quarterly and annual reports.
- Files are not organized by company, so companies are chosen from what a few
  files contain rather than picked by name.
- A single filing is 1–5 MB, so the sample is kept to ten filings.
- The SEC's own site is not used: it requires automated requests to identify
  their sender with a contact address.

## Rules for the data

- **Provenance**: every file records where it came from, when it was retrieved
  and its SHA-256 hash, in a manifest next to it. Files are stored unchanged.
- **Confirmed labels**: a label suggested by a model or a script counts only
  after it is confirmed. There are two ways:
  - *By a person.* Required for every label that takes judgment: what a claim
    says, whether a statement is hedged, what should be flagged.
  - *By independent cross-check* (amended 2026-11-12). Allowed only for
    mechanical labels for which an established tool written by others exists;
    at present this means sentence boundaries. The label counts when the tool
    agrees with it. Where the tool disagrees, a person decides, and the
    decision is recorded with its reason. The tool is used only for checking,
    never by the product. This is weaker than a person reading every label:
    two tools can share a blind spot, so numbers that rest on it say so.
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

- Hand labelling needs a person's time; the first batch is sized to stay small.
