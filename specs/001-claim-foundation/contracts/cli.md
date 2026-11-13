# Contract: Command-Line Interface

Every command reads and writes JSON, exits 0 on success and non-zero on
rejection, and on rejection prints `{"error": <code>, "field": <name or null>,
"message": <text>}`. The library exposes the same operations as functions.

The global option `--db <path>` (before the command) names the store file;
the default is `axiomate.db` in the current directory.

## `axiomate ingest <file>`

Options: `--publisher-cik`, `--type`, `--published-on`, `--fiscal-year`,
`--fiscal-period`, `--format text|html`, `--language` (default `en`).

- Success: `{"document_id", "segments": <count>, "created": true|false}`.
  `created` is false when the identical document already existed.
- Errors: `missing_provenance` (publisher, publication date or type absent),
  `invalid_provenance` (a provenance value is malformed; the field is named),
  `unsupported_format` (also when the bytes are not UTF-8 text),
  `unsupported_language`, `provenance_conflict`, `empty_document`,
  `unreadable_file`.
- A publisher key shorter than ten digits is stored zero-padded to ten.

## `axiomate document show <document_id> [--segment N]`

- Success: provenance, canonical text and segment count; or, with `--segment`,
  `{"document_id", "index", "start", "end", "kind", "text"}`.
- Errors: `not_found`.

## `axiomate claim add <claim.json>`

Input: one claim as a flat JSON object with the fields of the data model, plus
optional `flags` and `assumptions` arrays. `status` and `segment_index` may be
left out: the status is derived, and the segment is found from the span. If
given, each must agree with what the store works out. Numbers may be written
as JSON numbers or as text; they are read exactly. To correct a claim, pass
`--supersedes <claim_id>`.

- Success: `{"claim_id", "version", "status", "created"}`. `created` is false
  when the identical claim was already stored.
- Errors: `schema_invalid` (with the field; also when the file is not JSON),
  `unknown_metric`, `document_not_found`, `span_mismatch`,
  `span_outside_segment`, `said_on_mismatch`, `status_mismatch`,
  `empty_field_without_flag`, `claim_exists` (a different claim is stored for
  the same span and metric and `--supersedes` was not given), `not_found` (the
  claim named by `--supersedes` does not exist), `unreadable_file`.

## `axiomate claim list --company-cik --metric --fiscal-year [--fiscal-period]`

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
