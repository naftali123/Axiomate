# Data Model: Claim Interpretation and Validation Gate

The claim, flag and assumption records of spec 001 are unchanged. This feature
adds the records below. All are append-only.

## Model reply (file)

| Field | Type | Notes |
|---|---|---|
| key | text | SHA-256 of instruction version, model id and request text |
| instruction_version | text | Version of the instructions |
| model | text | Model id requested |
| served_model | text | Model id the service reported |
| request_text | text | Exactly what was sent: segment and marked context |
| reply | object | The structured reply, unchanged |
| input_tokens, output_tokens | integer | As reported |

A file never changes once written.

## Candidate (inside a reply)

The claim fields of spec 001 except `document_id`, `segment_index`,
`span_start`, `span_end`, `said_on`, `status`, plus `quote`, `flags` and
`assumptions`. Any claim field may be null. `company_cik` may be null, meaning
the document's publisher.

## Interpretation run (database)

| Field | Type | Notes |
|---|---|---|
| id | text | SHA-256 of document id, instruction version, model id |
| document_id | text | |
| instruction_version, model | text | |
| segments_selected | integer | |
| calls_made, replies_reused, replies_failed | integer | |

## Candidate outcome (database)

| Field | Type | Notes |
|---|---|---|
| run_id | text | |
| segment_index | integer | The segment that was sent |
| reply_key | text | |
| seq | integer | Position of the candidate in the reply |
| outcome | enum | `passed`, `flagged`, `rejected` |
| check | text | The check that decided: `quote`, `schema`, `value`, `sign`, `scale`, `period`, `metric`, `hedge`, `duplicate`, or empty for `passed` |
| field | text | The claim field concerned; optional |
| claim_id | text | Set when a claim was stored |

Rule: for every run, passed + flagged + rejected equals the number of
candidates in its replies.

## Gate result (in memory)

| Field | Type | Notes |
|---|---|---|
| outcome | enum | As above |
| check, field, message | text | For a rejection |
| flags | list | Flags the gate adds, with reason codes from spec 001 |

Gate flags use the existing reason codes: `missing_background` (scale without
evidence), `underspecified_time` (period without evidence), `unmapped_metric`
(metric without evidence, or a component of a metric),
`hedged_or_conditional`, `reported_speech`, `implicit_scope`.

## Evaluation report (file)

| Field | Notes |
|---|---|
| data set | `development` or `held_out`, with the list of filings |
| instruction_version, model | |
| tagged figures | Count for the four metrics |
| claims citing a tagged figure | Passed claims only |
| precision, coverage, pass rate | Each with numerator, denominator and threshold |
| disagreements | Each wrong claim with its tag, for review |

## Split file

`eval/splits.json`: for each evaluation filing, `development` or `held_out`.
A filing never changes sides.
