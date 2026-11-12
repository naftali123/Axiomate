# Research: Disclosure Ingestion and Claim Foundation

Each entry records a decision, the reason, and what was rejected.

## Storage: SQLite

- **Reason**: a single file, no server, transactional, ships with Python, and
  supports triggers for enforcing immutability inside the database.
- **Rejected**: PostgreSQL (operational overhead with no benefit at this size);
  flat JSON files (no transactions, no enforced immutability).

## Sentence segmentation: project-owned rules

- **Reason**: principle V needs output that never changes unless we change it.
  Owning the rules lets us version them and tune them for financial text
  ("Inc.", "U.S.", "$4.2 billion", "Q3.").
- **Rejected**: statistical segmenters (output changes with model versions);
  third-party rule-based libraries (behaviour outside our control, weak on
  financial abbreviations and tables).

## HTML text extraction: standard-library parser with our own rules

- **Reason**: no extra dependency; visible-text rules (skip script, style and
  hidden elements; block elements and table rows end a segment) are short and
  testable with golden files.
- **Rejected**: browser rendering (heavy, version-dependent); general
  "readability" extractors (heuristic, may drop tables that hold the figures).

## Document identity: SHA-256 of original bytes

- **Reason**: makes deduplication and reproducibility structural.
- **Rejected**: random or sequential identifiers (differ between runs, break SC-005).

## No wall-clock timestamps in the store

- **Reason**: an "ingested at" column would make two identical runs differ.
  Publication date comes from provenance, not from the clock.
- **Rejected**: storing timestamps and excluding them from comparison (easy to
  get wrong; nothing in this feature needs them).

## Company identifier: SEC Central Index Key

- **Reason**: stable across name and ticker changes, assigned to every US filer.
- **Rejected**: ticker symbols (reused and changed); names (ambiguous).

## Numbers: decimals with stated and normalized forms

- **Reason**: floating point cannot represent financial figures exactly, and
  the later comparison engine must compare exact values. Keeping the stated
  form preserves traceability to the text.

## Interface: library plus command-line tool

- **Reason**: the library is what later stages call; the command-line tool
  gives a human a way to test each story independently, as the spec requires.
- **Rejected**: a web service (nothing needs it yet).

## Test data source: an open dataset on Hugging Face

- **Decision**: take filings from `kapilrao/SEC-EDGAR` (Apache-2.0, no account)
  and read the expected figures from the structured tags embedded in each filing.
- **Reason**: one openly licensed source provides both the text and the correct
  figures, with no identification required and nothing personal sent.
- **Rejected**: the SEC's own site (requires automated requests to carry a
  contact address); other Hugging Face collections that are gated, licensed for
  non-commercial use only, or contain processed text rather than the original
  filing.

## Open points deferred to later features

- The registry of companies and its handling of mergers and renames.
- Resolving relative periods ("the prior-year quarter") – stage 4.
- PDF input.
