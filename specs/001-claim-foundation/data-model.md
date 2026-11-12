# Data Model: Disclosure Ingestion and Claim Foundation

All records are immutable once written. Identifiers are derived from content,
never random and never time-based.

## Document

| Field | Type | Notes |
|---|---|---|
| id | text | SHA-256 of the original bytes |
| publisher_cik | text | SEC Central Index Key of the publishing company |
| document_type | enum | `earnings_release`, `annual_report`, `quarterly_report`, `investor_statement`, `other` |
| published_on | date | Required |
| fiscal_year | integer | Optional; the period the document covers |
| fiscal_quarter | enum | `Q1`–`Q4`, `FY`; optional |
| format | enum | `text`, `html` |
| language | text | Must be `en` |
| original | bytes | Exactly as ingested |
| canonical_text | text | What all offsets refer to |
| extractor_version | text | Version of the text-extraction rules |
| segmenter_version | text | Version of the segmentation rules |

Rules: publisher and publication date are mandatory. Identical bytes with
identical provenance return the existing record; identical bytes with different
provenance are rejected.

## Segment

| Field | Type | Notes |
|---|---|---|
| document_id | text | |
| index | integer | Position in the document, from 0 |
| start, end | integer | Character offsets in the canonical text |
| kind | enum | `sentence`, `table_row`, `heading` |

Rules: segments do not overlap and are ordered by offset.

## Claim

| Field | Type | Notes |
|---|---|---|
| id | text | Hash of document id, span offsets and metric; stable across versions |
| version | integer | From 1; a correction adds the next version |
| schema_version | text | Version of the claim schema |
| company_cik | text | The company the claim is about |
| metric | enum | `revenue`, `net_income`, `earnings_per_share`, `operating_cash_flow` |
| value_kind | enum | `exact`, `approximate`, `at_least`, `at_most`, `range` |
| value_low, value_high | decimal | Normalized to base units; equal unless a range |
| stated_value, stated_scale | decimal, enum | As written: `units`, `thousands`, `millions`, `billions` |
| unit | enum | `currency`, `currency_per_share`, `percent` |
| currency | text | ISO 4217 code; required unless unit is `percent` |
| period_kind | enum | `duration`, `instant` |
| fiscal_year, fiscal_quarter | integer, enum | |
| period_start, period_end | date | Explicit dates |
| basis | enum | `reported`, `adjusted` |
| nature | enum | `actual`, `guidance`, `forecast` |
| comparison | enum | `absolute`, `change_vs_period` |
| baseline_start, baseline_end | date | Required when comparison is `change_vs_period` |
| polarity | enum | `affirmed`, `denied` |
| document_id | text | Source document |
| segment_index | integer | Source segment |
| span_start, span_end | integer | Offsets in the canonical text |
| quote | text | Must equal the canonical text between the offsets |
| said_on | date | Must equal the document's publication date |
| status | enum | `formal`, `formal-with-assumptions`, `not-formalizable`; derived |

Rules:

- The span must lie inside the named segment.
- `value_low` ≤ `value_high`; `period_start` ≤ `period_end`.
- Status is derived (see below) and a mismatching submitted status is rejected.
- On a `not-formalizable` claim a field may be empty only if a flag names it.

## Flag

| Field | Type | Notes |
|---|---|---|
| claim_id, claim_version | text, integer | |
| reason | enum | See list below |
| field | text | The claim field affected; optional |
| resolved | boolean | |
| note | text | Optional |

Reason codes: `unresolved_reference`, `underspecified_time`, `vague_quantity`,
`implicit_scope`, `unmapped_metric`, `missing_background`, `hedged_or_conditional`,
`reported_speech`, `figurative`, `opinion`.

## Assumption

| Field | Type | Notes |
|---|---|---|
| claim_id, claim_version | text, integer | |
| statement | text | What was assumed |
| field | text | The claim field it supports |
| origin | enum | `context_store`, `model`, `human` |

## Status derivation

1. Any unresolved flag → `not-formalizable`.
2. Otherwise, any assumption → `formal-with-assumptions`.
3. Otherwise → `formal`.

## Relationships

```
Document 1 ── * Segment
Document 1 ── * Claim (through its span)
Claim    1 ── * Flag
Claim    1 ── * Assumption
```
