# Contract: Command-Line Interface (additions)

The rules of spec 001's contract apply: JSON in and out, exit 0 on success.

## `axiomate claim check <claim.json>`

Runs the gate on one claim without storing it.

- Success: `{"outcome": "passed"|"flagged"|"rejected", "check", "field",
  "message", "flags": [...]}`. A rejection is a successful check: exit 0.
- Errors: `schema_invalid`, `document_not_found`, `unreadable_file`.

## `axiomate interpret <document_id> --replies <dir> [--allow-calls]`

Proposes claims for a stored document, passes them through the gate and stores
those that pass or are flagged.

- Without `--allow-calls` only stored replies are used; a segment with no
  stored reply is an error (`reply_missing`), and nothing is stored.
- With `--allow-calls` missing replies are requested from the model and
  written to the directory. The API key is read from the environment.
- Options: `--max-calls N` stops before exceeding N calls.
- Success: `{"run_id", "segments_selected", "calls_made", "replies_reused",
  "replies_failed", "candidates", "passed", "flagged", "rejected"}`.
- Errors: `not_found`, `reply_missing`, `model_unavailable`,
  `call_limit_reached`.

## `axiomate evaluate --split development|held_out --facts <dir>`

Compares stored claims with tagged figures.

- Success: the evaluation report as JSON; `"thresholds_met": true|false`.
- Errors: `not_found` (a filing of the split is not in the store).
