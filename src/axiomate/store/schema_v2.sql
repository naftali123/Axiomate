-- Axiomate store, additions of schema version 2 (spec 002).
-- Records of interpretation runs and of what happened to every candidate.
-- Append-only, like every other table.

CREATE TABLE interpretation_run (
    id                  TEXT PRIMARY KEY CHECK (length(id) = 64),
    document_id         TEXT NOT NULL REFERENCES document (id),
    instruction_version TEXT NOT NULL,
    model               TEXT NOT NULL,
    segments_selected   INTEGER NOT NULL CHECK (segments_selected >= 0),
    calls_made          INTEGER NOT NULL CHECK (calls_made >= 0),
    replies_reused      INTEGER NOT NULL CHECK (replies_reused >= 0),
    replies_failed      INTEGER NOT NULL CHECK (replies_failed >= 0)
) STRICT;

CREATE TABLE candidate_outcome (
    run_id        TEXT NOT NULL REFERENCES interpretation_run (id),
    segment_index INTEGER NOT NULL,
    seq           INTEGER NOT NULL CHECK (seq >= 0),
    reply_key     TEXT NOT NULL CHECK (length(reply_key) = 64),
    outcome       TEXT NOT NULL CHECK (outcome IN ('passed', 'flagged', 'rejected')),
    "check"       TEXT CHECK ("check" IS NULL OR "check" IN ('quote', 'schema', 'value', 'sign', 'scale', 'period', 'metric', 'hedge', 'duplicate')),
    field         TEXT,
    claim_id      TEXT,
    PRIMARY KEY (run_id, segment_index, seq),
    CHECK ((outcome = 'rejected') = (claim_id IS NULL))
) STRICT;

CREATE TRIGGER interpretation_run_no_update BEFORE UPDATE ON interpretation_run
BEGIN SELECT RAISE(ABORT, 'immutable: interpretation_run rows cannot be updated'); END;
CREATE TRIGGER interpretation_run_no_delete BEFORE DELETE ON interpretation_run
BEGIN SELECT RAISE(ABORT, 'immutable: interpretation_run rows cannot be deleted'); END;

CREATE TRIGGER candidate_outcome_no_update BEFORE UPDATE ON candidate_outcome
BEGIN SELECT RAISE(ABORT, 'immutable: candidate_outcome rows cannot be updated'); END;
CREATE TRIGGER candidate_outcome_no_delete BEFORE DELETE ON candidate_outcome
BEGIN SELECT RAISE(ABORT, 'immutable: candidate_outcome rows cannot be deleted'); END;
