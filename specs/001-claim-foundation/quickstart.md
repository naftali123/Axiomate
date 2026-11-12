# Quickstart: Disclosure Ingestion and Claim Foundation

This walk-through doubles as the manual acceptance test for the feature.

## 1. Ingest a disclosure (Story 1)

```bash
axiomate ingest tests/fixtures/documents/everi_2024q1_10q.html \
  --publisher-cik 0001318568 --type quarterly_report \
  --published-on 2024-05-08 --fiscal-year 2024 --fiscal-period Q1 --format html
```

Expect a document id and `"created": true`. Run it again and expect the same id
with `"created": false`.

## 2. Look at a sentence

```bash
axiomate document show <document_id> --segment 3
```

Expect the sentence text and its character offsets.

## 3. Record a claim (Story 2)

```bash
axiomate claim add tests/fixtures/claims/acme_q3_revenue.json
```

Expect a claim id, version 1 and status `formal`. Then submit
`tests/fixtures/claims/bad_span.json` and expect `span_mismatch`.

## 4. Find and trace (Story 3)

```bash
axiomate claim list --company-cik 0000000001 --metric revenue \
  --fiscal-year 2025 --fiscal-period Q3
```

```bash
axiomate claim source <claim_id>
```

Expect the claim, then the exact sentence and publication date it came from.

## 5. Check reproducibility

Repeat steps 1–3 in a fresh store, run `axiomate export` in both, and expect the
two outputs to be identical.
