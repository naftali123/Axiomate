# Contract: Command-Line Interface

Every command reads and writes JSON, exits 0 on success and non-zero on
rejection, and on rejection prints `{"error": <code>, "field": <name or null>,
"message": <text>}`. The library exposes the same operations as functions.

## `axiomate ingest <file>`

Options: `--publisher-cik`, `--type`, `--published-on`, `--fiscal-year`,
`--fiscal-quarter`, `--format text|html`, `--language` (default `en`).

- Success: `{"document_id", "segments": <count>, "created": true|false}`.
  `created` is false when the identical document already existed.
- Errors: `missing_provenance`, `unsupported_format`, `unsupported_language`,
  `provenance_conflict`.

## `axiomate document show <document_id> [--segment N]`

- Success: provenance and canonical text, or one segment with its offsets.
- Errors: `not_found`.

## `axiomate claim add <claim.json>`

Input: one claim as defined in the data model, with optional `flags` and
`assumptions`. To correct a claim, pass `--supersedes <claim_id>`.

- Success: `{"claim_id", "version", "status"}`.
- Errors: `schema_invalid` (with the field), `unknown_metric`,
  `document_not_found`, `span_mismatch`, `span_outside_segment`,
  `said_on_mismatch`, `status_mismatch`, `empty_field_without_flag`.

## `axiomate claim list --company-cik --metric --fiscal-year [--fiscal-quarter]`

Options: `--all-versions` (default returns only the latest version of each claim).

- Success: an array of claims with flags and assumptions, in the stable order
  defined in the plan.

## `axiomate claim source <claim_id> [--version N]`

- Success: `{"document_id", "published_on", "segment_index", "segment_text",
  "span_start", "span_end", "quote"}`.
- Errors: `not_found`.

## `axiomate export`

- Success: a canonical, deterministic dump of the whole store, used to compare
  two runs.
