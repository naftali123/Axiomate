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
- A reply that fails on its own (the model declines, or the reply does not
  parse) is counted in `replies_failed` and the run goes on. A failure of the
  service (`model_unavailable`: no key, no network, refused request) stops the
  run and records nothing; replies already received stay in the directory.
- Errors: `not_found`, `reply_missing`, `model_unavailable`,
  `call_limit_reached`.

## `axiomate evaluate --split development|held_out [--splits <file>]`

Compares the passed claims of the split's filings with their tagged figures.
The split file (default `eval/splits.json`) names each filing and the
directory of its tag file.

- Success: the evaluation report as JSON: `precision` and `coverage`, each
  with `numerator`, `denominator`, `value`, `threshold` and `met`; `pass_rate`;
  the counts per filing; every disagreement with its claim and its tag;
  `"thresholds_met": true|false`.
- Tagged figures that are not in the visible text are counted separately
  (`tagged_not_visible`) and are not part of the coverage denominator.
- Errors: `not_found` (a filing of the split is not in the store, or has no
  interpretation run under the current instructions and model).
