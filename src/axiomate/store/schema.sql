-- Axiomate store, schema version 1.
-- Every table is append-only: triggers at the end refuse updates and deletes.
-- Decimal values are stored as text so that no precision is lost.

CREATE TABLE document (
    id                TEXT PRIMARY KEY CHECK (length(id) = 64),
    publisher_cik     TEXT NOT NULL,
    document_type     TEXT NOT NULL CHECK (document_type IN ('earnings_release', 'annual_report', 'quarterly_report', 'investor_statement', 'other')),
    published_on      TEXT NOT NULL,
    fiscal_year       INTEGER,
    fiscal_period     TEXT CHECK (fiscal_period IS NULL OR fiscal_period IN ('Q1', 'Q2', 'Q3', 'Q4', 'H1', '9M', 'FY')),
    format            TEXT NOT NULL CHECK (format IN ('text', 'html')),
    language          TEXT NOT NULL CHECK (language = 'en'),
    original          BLOB NOT NULL,
    canonical_text    TEXT NOT NULL,
    extractor_version TEXT NOT NULL,
    segmenter_version TEXT NOT NULL
) STRICT;

CREATE TABLE segment (
    document_id TEXT NOT NULL REFERENCES document (id),
    idx         INTEGER NOT NULL CHECK (idx >= 0),
    start       INTEGER NOT NULL CHECK (start >= 0),
    end         INTEGER NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('sentence', 'table_row', 'heading')),
    PRIMARY KEY (document_id, idx),
    CHECK (end > start)
) STRICT;

-- Fields that a not-formalizable claim may leave empty are nullable here;
-- the submission code enforces that a flag names each empty field.
CREATE TABLE claim (
    id             TEXT NOT NULL CHECK (length(id) = 64),
    version        INTEGER NOT NULL CHECK (version >= 1),
    schema_version TEXT NOT NULL,
    company_cik    TEXT,
    metric         TEXT CHECK (metric IS NULL OR metric IN ('revenue', 'net_income', 'earnings_per_share', 'operating_cash_flow')),
    value_kind     TEXT CHECK (value_kind IS NULL OR value_kind IN ('exact', 'approximate', 'at_least', 'at_most', 'range')),
    value_low      TEXT,
    value_high     TEXT,
    stated_value   TEXT,
    stated_scale   TEXT CHECK (stated_scale IS NULL OR stated_scale IN ('units', 'thousands', 'millions', 'billions')),
    unit           TEXT CHECK (unit IS NULL OR unit IN ('currency', 'currency_per_share', 'percent')),
    currency       TEXT,
    period_kind    TEXT CHECK (period_kind IS NULL OR period_kind IN ('duration', 'instant')),
    fiscal_year    INTEGER,
    fiscal_period  TEXT CHECK (fiscal_period IS NULL OR fiscal_period IN ('Q1', 'Q2', 'Q3', 'Q4', 'H1', '9M', 'FY')),
    period_start   TEXT,
    period_end     TEXT,
    basis          TEXT CHECK (basis IS NULL OR basis IN ('reported', 'adjusted')),
    nature         TEXT CHECK (nature IS NULL OR nature IN ('actual', 'guidance', 'forecast')),
    comparison     TEXT CHECK (comparison IS NULL OR comparison IN ('absolute', 'change_vs_period')),
    baseline_start TEXT,
    baseline_end   TEXT,
    polarity       TEXT CHECK (polarity IS NULL OR polarity IN ('affirmed', 'denied')),
    document_id    TEXT NOT NULL,
    segment_index  INTEGER NOT NULL,
    span_start     INTEGER NOT NULL CHECK (span_start >= 0),
    span_end       INTEGER NOT NULL,
    quote          TEXT NOT NULL CHECK (length(quote) > 0),
    said_on        TEXT NOT NULL,
    status         TEXT NOT NULL CHECK (status IN ('formal', 'formal-with-assumptions', 'not-formalizable')),
    PRIMARY KEY (id, version),
    FOREIGN KEY (document_id, segment_index) REFERENCES segment (document_id, idx),
    CHECK (span_end > span_start)
) STRICT;

CREATE INDEX claim_lookup ON claim (company_cik, metric, fiscal_year, fiscal_period);

CREATE TABLE flag (
    claim_id      TEXT NOT NULL,
    claim_version INTEGER NOT NULL,
    seq           INTEGER NOT NULL CHECK (seq >= 0),
    reason        TEXT NOT NULL CHECK (reason IN ('unresolved_reference', 'underspecified_time', 'vague_quantity', 'implicit_scope', 'unmapped_metric', 'missing_background', 'hedged_or_conditional', 'reported_speech', 'figurative', 'opinion')),
    field         TEXT,
    resolved      INTEGER NOT NULL CHECK (resolved IN (0, 1)),
    note          TEXT,
    PRIMARY KEY (claim_id, claim_version, seq),
    FOREIGN KEY (claim_id, claim_version) REFERENCES claim (id, version)
) STRICT;

CREATE TABLE assumption (
    claim_id      TEXT NOT NULL,
    claim_version INTEGER NOT NULL,
    seq           INTEGER NOT NULL CHECK (seq >= 0),
    statement     TEXT NOT NULL CHECK (length(statement) > 0),
    field         TEXT,
    origin        TEXT NOT NULL CHECK (origin IN ('context_store', 'model', 'human')),
    PRIMARY KEY (claim_id, claim_version, seq),
    FOREIGN KEY (claim_id, claim_version) REFERENCES claim (id, version)
) STRICT;

CREATE TRIGGER document_no_update BEFORE UPDATE ON document
BEGIN SELECT RAISE(ABORT, 'immutable: document rows cannot be updated'); END;
CREATE TRIGGER document_no_delete BEFORE DELETE ON document
BEGIN SELECT RAISE(ABORT, 'immutable: document rows cannot be deleted'); END;

CREATE TRIGGER segment_no_update BEFORE UPDATE ON segment
BEGIN SELECT RAISE(ABORT, 'immutable: segment rows cannot be updated'); END;
CREATE TRIGGER segment_no_delete BEFORE DELETE ON segment
BEGIN SELECT RAISE(ABORT, 'immutable: segment rows cannot be deleted'); END;

CREATE TRIGGER claim_no_update BEFORE UPDATE ON claim
BEGIN SELECT RAISE(ABORT, 'immutable: claim rows cannot be updated'); END;
CREATE TRIGGER claim_no_delete BEFORE DELETE ON claim
BEGIN SELECT RAISE(ABORT, 'immutable: claim rows cannot be deleted'); END;

CREATE TRIGGER flag_no_update BEFORE UPDATE ON flag
BEGIN SELECT RAISE(ABORT, 'immutable: flag rows cannot be updated'); END;
CREATE TRIGGER flag_no_delete BEFORE DELETE ON flag
BEGIN SELECT RAISE(ABORT, 'immutable: flag rows cannot be deleted'); END;

CREATE TRIGGER assumption_no_update BEFORE UPDATE ON assumption
BEGIN SELECT RAISE(ABORT, 'immutable: assumption rows cannot be updated'); END;
CREATE TRIGGER assumption_no_delete BEFORE DELETE ON assumption
BEGIN SELECT RAISE(ABORT, 'immutable: assumption rows cannot be deleted'); END;
