# Implementation Plan: Disclosure Ingestion and Claim Foundation

**Feature**: `001-claim-foundation` | **Date**: 2026-11-12 | **Spec**: [spec.md](spec.md)
**Status**: Draft – awaiting approval

## Summary

Build the two foundations every later stage relies on: an immutable,
content-addressed document store with addressable sentences, and a claim store
that accepts only schema-conforming claims whose quoted span matches the stored
text. Everything in this feature is deterministic; no language model is involved.

## Technical context

| Item | Choice |
|---|---|
| Language | Python 3.12 |
| Schema and validation | Pydantic 2 |
| Storage | SQLite, through the standard library |
| HTML text extraction | Standard-library HTML parser with project-owned rules |
| Sentence segmentation | Project-owned rule-based segmenter |
| Numbers | Decimal, never floating point |
| Interface | Python library plus a command-line tool with JSON input and output |
| Testing | pytest, written test-first |
| Packaging | `pyproject.toml`, `src/` layout |
| Runtime dependencies | Pydantic only |

Reasons for each choice are in [research.md](research.md).

## Constitution check

| Principle | How this plan complies |
|---|---|
| I. Model proposes, code decides | No model in this feature. The claim-submission interface is the single entry point a later model stage will use, so nothing can bypass validation. |
| II. Traceability | A claim stores document id, character offsets and the quoted text; storage refuses it unless the stored text at those offsets equals the quote. |
| III. No silent assumptions | Assumptions are separate records with a mandatory origin. Status is derived from them, not chosen by the submitter. |
| IV. Flag rather than guess | Flags carry a reason code from a fixed list. A claim with an unresolved flag is `not-formalizable`. |
| V. Reproducibility | Identity is a content hash. No wall-clock time or random identifier is stored. Extractor and segmenter versions are recorded on each document. |
| VI. Time-indexed claims | `said_on` and the fiscal period are both mandatory and stored separately. |
| VII. Inconsistency is not falsehood | Not applicable; no verdicts in this feature. |
| VIII. Verified, test-first | Tests precede code in every task group. The spec's Verification section fixes the method, data and threshold for stages 1 and 5 before any code is written; the data is collected in the setup phase. |
| IX. Status page | Each task group that changes project state updates `status.html`. |

No violations; no complexity exceptions are needed.

## Project structure

```
src/axiomate/
  documents/
    ingest.py        # provenance checks, hashing, deduplication
    html_text.py     # deterministic visible-text extraction
    segment.py       # deterministic sentence segmentation
  claims/
    schema.py        # claim, flag, assumption models
    status.py        # derives the formalization status
    submit.py        # schema and span-grounding checks, versioning
    query.py         # lookup and source tracing
  store/
    schema.sql       # tables and immutability triggers
    db.py            # connection, transactions, canonical export
  cli.py
tests/
  unit/
  integration/
  fixtures/
    documents/       # real filings, unchanged, with SOURCES.md and hashes
    boundaries/      # hand-checked sentence boundaries
    claims/          # hand-written good claims; generated bad claims
tools/
  corrupt_claims.py  # deterministic generator of malformed claims
specs/001-claim-foundation/
  spec.md  plan.md  research.md  data-model.md  quickstart.md  tasks.md
  contracts/cli.md
```

## Design decisions

1. **Document identity is the SHA-256 of the original bytes.** Ingesting the
   same bytes again returns the existing record. Ingesting the same bytes with
   different provenance is rejected as a conflict rather than silently merged.
2. **Canonical text.** Plain text is normalized (Unicode NFC, `\n` line endings).
   HTML is reduced to visible text by fixed rules. The canonical text is stored
   and is what all offsets refer to; the original bytes are kept alongside it.
3. **Segments.** Canonical text is split into sentences by rule. Block elements
   end a segment, and each table row is one segment, so a figure in a table is
   addressable separately from the same figure in a headline.
4. **Addresses.** A sentence is addressed by document id and index. A span is a
   document id plus start and end character offsets in the canonical text.
5. **Span grounding.** A claim is stored only if the canonical text between its
   offsets equals its quoted text exactly, and the span lies inside one segment.
6. **Immutability in the database.** Triggers reject every update and delete on
   documents, segments, claims, flags and assumptions.
7. **Claim versioning.** A claim has a stable id and a version number. A
   correction inserts the next version; earlier versions stay readable.
8. **Derived status.** Any unresolved flag gives `not-formalizable`; otherwise
   any assumption gives `formal-with-assumptions`; otherwise `formal`. A
   submitted status that disagrees is rejected.
9. **Companies** are identified by their SEC Central Index Key.
10. **Periods** are stored as fiscal year, fiscal quarter (or full year) and
    explicit start and end dates, so non-calendar fiscal years are unambiguous.
11. **Values** keep both the figure as stated (with its scale) and the
    normalized figure in base units, both as decimals.
12. **Stable ordering.** Query results are ordered by period end, publication
    date, document id, segment index, claim id, version.
13. **Determinism test.** The store has a canonical export; two independent runs
    over the same inputs must produce identical exports.

## Spec amendment made during planning

The spec required every schema field on every claim. A claim that cannot be
formalized (for example "revenue grew significantly") has no value to record.
Added **FR-017**: on a `not-formalizable` claim, a field may be empty if a flag
on the claim names that field as the reason.

## Risks

| Risk | Mitigation |
|---|---|
| Segmenter mis-splits financial text (abbreviations, decimals) | Abbreviation list and fixture tests from real disclosures; segmenter version stored so documents can be re-segmented explicitly later |
| HTML parser behaviour changes between Python versions | Extractor version recorded per document; pinned Python version; golden-file tests |
| Schema too narrow for later stages | Schema is versioned; claims record the schema version they conform to |

## Phases

1. Setup: packaging, test runner, and collection of the verification data.
2. Foundation: database schema with immutability triggers, canonical export.
3. Story 1: ingestion.
4. Story 2: claim submission.
5. Story 3: query and tracing.
6. Polish: determinism run, quickstart validation, status page.

Detailed tasks are in [tasks.md](tasks.md).
