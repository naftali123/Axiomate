# Tasks: Disclosure Ingestion and Claim Foundation

**Inputs**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md),
[contracts/cli.md](contracts/cli.md)

`[P]` marks tasks that can run in parallel. `[S1]`–`[S3]` tie a task to a user
story. Within each story, tests are written first and must fail before the
implementation is written (constitution principle VIII).

## Phase 1 – Setup

- [x] T001 Create `pyproject.toml`, the `src/axiomate` package and the pytest configuration.
- [x] T002 Choose five US-listed companies from the `kapilrao/SEC-EDGAR` dataset and list them with their identifiers and the ten filings to use in `tests/fixtures/documents/SOURCES.md`.
- [x] T003 Extract the ten filings (quarterly and annual reports; at least three plain text and at least five HTML with embedded figures) and store them unchanged, each with accession number, dataset file, retrieval date and SHA-256 hash.
- [x] T004 [P] Write `tools/read_embedded_figures.py` and use it to extract the embedded structured figures for the four metrics from the HTML filings into `tests/fixtures/facts/`.
- [ ] T005 [P] Hand-check sentence boundaries for at least 200 segments across the filings; save under `tests/fixtures/boundaries/`. Needs a person to confirm. *Proposed: 241 segments are in place and await confirmation. Four labels were corrected while building the segmenter (see the README there).*
- [x] T006 [P] Write at least 20 well-formed claims by hand from the filings under `tests/fixtures/claims/good/`, each checked against the structured figures where available. *Done: 21 claims; 7 checked against embedded figures, 14 by reading the text.*
- [x] T007 Write `tools/corrupt_claims.py`, a deterministic generator that produces at least five malformed claims per rejection code from the good claims, into `tests/fixtures/claims/bad/`.

**Checkpoint**: the verification data in the spec's Verification section exists and is recorded with its provenance.

## Phase 2 – Foundation (blocks all stories)

- [x] T008 Write tests that updates and deletes are refused on every table.
- [x] T009 Write `store/schema.sql` with the tables from the data model and the immutability triggers.
- [x] T010 Write `store/db.py`: connection, transactions and the canonical export.
- [x] T011 Write the error type carrying code, field and message, shared by library and command line.

**Checkpoint**: an empty store can be created and exported.

## Phase 3 – Story 1: Ingest a disclosure (P1)

- [x] T012 [P] [S1] Tests for text normalization and HTML visible-text extraction: golden files, and every structured figure present in the stored text.
- [x] T013 [P] [S1] Tests for segmentation: abbreviations, decimals, headings, table rows, non-overlap, and at least 98% agreement with the hand-checked boundaries.
- [x] T014 [P] [S1] Integration tests for the five acceptance scenarios of Story 1, plus provenance conflict.
- [x] T015 [S1] Implement `documents/html_text.py`.
- [x] T016 [S1] Implement `documents/segment.py`.
- [x] T017 [S1] Implement `documents/ingest.py`: provenance checks, hashing, deduplication, storage.
- [x] T018 [S1] Implement `axiomate ingest` and `axiomate document show`.

**Checkpoint**: Story 1 passes its independent test; quickstart steps 1–2 work. *Reached. Measured on the ten filings: round trip 10/10, no duplicates 10/10, tagged figures 100%, sentence boundaries 241/241 against labels that are still unconfirmed.*

## Phase 4 – Story 2: Record a grounded claim (P2)

- [ ] T019 [P] [S2] Unit tests for the claim, flag and assumption models, including decimal handling and FR-017.
- [ ] T020 [P] [S2] Unit tests for status derivation.
- [ ] T021 [P] [S2] Integration tests for the five acceptance scenarios of Story 2 and every rejection code.
- [ ] T022 [S2] Implement `claims/schema.py`.
- [ ] T023 [S2] Implement `claims/status.py`.
- [ ] T024 [S2] Implement `claims/submit.py`: schema check, span grounding, segment containment, versioning.
- [ ] T025 [S2] Implement `axiomate claim add`.
- [ ] T026 [S2] Measure the rejection rate on the malformed fixture set; it must be 100% (SC-004).

**Checkpoint**: Story 2 passes its independent test; quickstart step 3 works.

## Phase 5 – Story 3: Find and trace (P3)

- [ ] T027 [P] [S3] Integration tests for the three acceptance scenarios of Story 3, including stable ordering and version handling.
- [ ] T028 [S3] Implement `claims/query.py`.
- [ ] T029 [S3] Implement `axiomate claim list` and `axiomate claim source`.

**Checkpoint**: Story 3 passes its independent test; quickstart step 4 works.

## Phase 6 – Polish

- [ ] T030 Determinism test: two fresh runs over all fixtures produce identical exports (SC-005).
- [ ] T031 Edge-case tests from the spec: duplicated figure, range and bound values, restated figure, non-calendar fiscal year.
- [ ] T032 Run the quickstart end to end and correct any drift between it and the tool.
- [ ] T033 Update `status.html`: stages 1 and 5 marked built and tested, spec table, date.
- [ ] T034 Update `README.md` with installation and usage.

## Dependencies

- Phase 2 blocks phases 3–5.
- Phase 4 needs phase 3 (claims point into stored documents).
- Phase 5 needs phase 4.
- Within a phase, `[P]` tasks touch different files and can run together.

## Suggested delivery

Stop after each checkpoint for review: Story 1 alone is a usable document store,
Story 2 adds the guarded claim store, Story 3 makes it auditable.
