# Tasks: Claim Interpretation and Validation Gate

**Inputs**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md),
[contracts/cli.md](contracts/cli.md)

`[P]` marks tasks that can run in parallel. Tests are written first and must
fail before the implementation is written (constitution principle VIII).

## Phase 1 – Validation gate (Story 1, no model)

- [ ] T001 [P] Tests for reading figures, scale words and signs from quotes taken from the development filings.
- [ ] T002 [P] Tests for reading dates and period phrases.
- [ ] T003 [P] Tests for the term lists: metric terms, component terms, hedging and forward-looking words.
- [ ] T004 Implement `gate/numbers.py`, `gate/periods.py`, `gate/lexicon.py`.
- [ ] T005 Write `tools/claims_from_facts.py`: correct claims built mechanically from the tagged figures of the development filings.
- [ ] T006 Write `tools/corrupt_for_gate.py`: at least 10 corrupted claims per kind (digit, scale, sign, period, metric, hedge removed, assumption removed), each with its expected outcome and check.
- [ ] T007 Tests for the five acceptance scenarios of Story 1 and for both generated sets.
- [ ] T008 Implement `gate/check.py`.
- [ ] T009 Implement `axiomate claim check`.
- [ ] T010 Measure: corrupted caught 100% (SC-003), correct pass ≥ 98% (SC-004). Update `status.html`.

**Checkpoint**: the gate is verified without any model call.

## Phase 2 – Held-out data

- [ ] T011 Choose at least eight HTML filings with tagged figures from at least four companies not in the development set, including one annual report; record them in `eval/filings/` with manifest and hashes.
- [ ] T012 Extract their tagged figures into `eval/facts/` without reading the filings' text.
- [ ] T013 Write `eval/splits.json` and a test that no filing is on both sides and that held-out files are not referenced by any test of phases 1, 3 or 4.

**Checkpoint**: the held-out set exists and is sealed.

## Phase 3 – Interpretation from stored replies (Story 2, no model)

- [ ] T014 [P] Tests for segment selection and context, on development filings.
- [ ] T015 [P] Tests for the reply model and for turning a reply into candidates: quote found, quote not found, duplicate, null fields, another company.
- [ ] T016 [P] Tests for the reply store: key, write once, read, missing.
- [ ] T017 Schema version 2: tables for runs and candidate outcomes, with immutability triggers and tests; stores of version 1 are upgraded in place.
- [ ] T018 Implement `interpret/select.py`, `interpret/reply.py`, `interpret/replies.py`.
- [ ] T019 Tests for a run from hand-written replies: acceptance scenarios 1–5 of Story 2, counts add up, second run changes nothing.
- [ ] T020 Implement `interpret/run.py` and `axiomate interpret` without calls.

**Checkpoint**: the whole path works from stored replies; still no model call.

## Phase 4 – Live calls (needs the API key)

- [ ] T021 Write the instructions (`interpret/prompt.py`), version 1.
- [ ] T022 Implement `interpret/client.py` and `--allow-calls`, with the call limit and the token counts.
- [ ] T023 Run one development filing; compare the measured cost with the estimate; stop if more than twice.
- [ ] T024 Run the other development filings; tune instructions and context on development filings only, raising the instruction version on every change.
- [ ] T025 Commit the stored replies of the development filings; test that the development run reproduces from them with no call.

**Checkpoint**: development numbers exist; instructions are frozen.

## Phase 5 – Evaluation (Story 3)

- [ ] T026 [P] Tests for the tagged comparison on hand-built cases: citing, agreeing, wrong value, wrong period, uncited tag.
- [ ] T027 Implement `evaluate/tagged.py`, `evaluate/report.py` and `axiomate evaluate`.
- [ ] T028 Development report.
- [ ] T029 Held-out run, once, with frozen instructions; commit its replies and its report.
- [ ] T030 Draw the prose sample by the fixed rule; present it to the repository owner as yes/no questions; record the answers.
- [ ] T031 Compare every result with its threshold; update `status.html` with the held-out numbers and what they do not cover.

**Checkpoint**: SC-001, SC-002 and SC-006 are measured.

## Phase 6 – Polish

- [ ] T032 Reproducibility: a second full run makes no call and leaves the export identical (SC-005).
- [ ] T033 Quickstart for this feature; run it end to end.
- [ ] T034 Update `README.md`, `specs/verification.md` and `status.html`.

## Dependencies

- Phase 3 needs phase 1. Phase 4 needs phase 3 and the API key.
- Phase 5 needs phases 2 and 4. Held-out replies (T029) are produced after T024 is closed.
- If a threshold is missed, the result is reported as it is. Instructions may then be changed only with a new version, and the held-out set counts as used: a new held-out set is needed for the next claim of success.
