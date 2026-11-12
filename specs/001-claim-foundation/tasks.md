# Tasks: Disclosure Ingestion and Claim Foundation

**Inputs**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md),
[contracts/cli.md](contracts/cli.md)

`[P]` marks tasks that can run in parallel. `[S1]`–`[S3]` tie a task to a user
story. Within each story, tests are written first and must fail before the
implementation is written (constitution principle VIII).

## Phase 1 – Setup

- [ ] T001 Create `pyproject.toml`, the `src/axiomate` package and the pytest configuration.
- [ ] T002 [P] Add fixture disclosures (two text, two HTML, one with a table) under `tests/fixtures/documents/`.
- [ ] T003 [P] Add claim fixtures under `tests/fixtures/claims/`: well-formed claims and one malformed claim per rejection code in the contract.

## Phase 2 – Foundation (blocks all stories)

- [ ] T004 Write tests that updates and deletes are refused on every table.
- [ ] T005 Write `store/schema.sql` with the tables from the data model and the immutability triggers.
- [ ] T006 Write `store/db.py`: connection, transactions and the canonical export.
- [ ] T007 Write the error type carrying code, field and message, shared by library and command line.

**Checkpoint**: an empty store can be created and exported.

## Phase 3 – Story 1: Ingest a disclosure (P1)

- [ ] T008 [P] [S1] Tests for text normalization and HTML visible-text extraction, with golden files.
- [ ] T009 [P] [S1] Tests for segmentation: abbreviations, decimals, headings, table rows, non-overlap.
- [ ] T010 [P] [S1] Integration tests for the five acceptance scenarios of Story 1, plus provenance conflict.
- [ ] T011 [S1] Implement `documents/html_text.py`.
- [ ] T012 [S1] Implement `documents/segment.py`.
- [ ] T013 [S1] Implement `documents/ingest.py`: provenance checks, hashing, deduplication, storage.
- [ ] T014 [S1] Implement `axiomate ingest` and `axiomate document show`.

**Checkpoint**: Story 1 passes its independent test; quickstart steps 1–2 work.

## Phase 4 – Story 2: Record a grounded claim (P2)

- [ ] T015 [P] [S2] Unit tests for the claim, flag and assumption models, including decimal handling and FR-017.
- [ ] T016 [P] [S2] Unit tests for status derivation.
- [ ] T017 [P] [S2] Integration tests for the five acceptance scenarios of Story 2 and every rejection code.
- [ ] T018 [S2] Implement `claims/schema.py`.
- [ ] T019 [S2] Implement `claims/status.py`.
- [ ] T020 [S2] Implement `claims/submit.py`: schema check, span grounding, segment containment, versioning.
- [ ] T021 [S2] Implement `axiomate claim add`.
- [ ] T022 [S2] Measure the rejection rate on the malformed fixture set; it must be 100% (SC-004).

**Checkpoint**: Story 2 passes its independent test; quickstart step 3 works.

## Phase 5 – Story 3: Find and trace (P3)

- [ ] T023 [P] [S3] Integration tests for the three acceptance scenarios of Story 3, including stable ordering and version handling.
- [ ] T024 [S3] Implement `claims/query.py`.
- [ ] T025 [S3] Implement `axiomate claim list` and `axiomate claim source`.

**Checkpoint**: Story 3 passes its independent test; quickstart step 4 works.

## Phase 6 – Polish

- [ ] T026 Determinism test: two fresh runs over all fixtures produce identical exports (SC-005).
- [ ] T027 Edge-case tests from the spec: duplicated figure, range and bound values, restated figure, non-calendar fiscal year.
- [ ] T028 Run the quickstart end to end and correct any drift between it and the tool.
- [ ] T029 Update `status.html`: stages 1 and 5 marked built and tested, spec table, date.
- [ ] T030 Update `README.md` with installation and usage.

## Dependencies

- Phase 2 blocks phases 3–5.
- Phase 4 needs phase 3 (claims point into stored documents).
- Phase 5 needs phase 4.
- Within a phase, `[P]` tasks touch different files and can run together.

## Suggested delivery

Stop after each checkpoint for review: Story 1 alone is a usable document store,
Story 2 adds the guarded claim store, Story 3 makes it auditable.
