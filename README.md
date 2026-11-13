# Axiomate

Axiomate turns text into structured, checkable claims and compares them against a
source's historical record to find contradictions, discrepancies and inaccuracies.

## How it works

1. **Ingestion** – store each document with source, date and content hash.
2. **Interpretation** – a language model proposes candidate claims in a fixed schema.
3. **Validation gate** – deterministic checks (span grounding, value re-parsing,
   known vocabulary, schema); failures become flags with reason codes.
4. **Context resolution** – flags are cleared from context stores; every resolution
   is recorded as a named assumption.
5. **Claim store** – immutable, versioned claims with a formalization status.
6. **Matching** – deterministic join on entity, predicate and overlapping time.
7. **Comparison engine** – deterministic rules and a solver produce verdicts with
   proof traces.
8. **Review and reporting** – human decisions feed back into the context stores.

## First domain

Corporate financial disclosures: earnings releases, annual reports and investor
statements of public companies.

## Development method

This project follows Spec-Driven Development:

- `.specify/memory/constitution.md` – the project's governing principles.
- `status.html` – a one-page Hebrew summary of the project state, kept current.
- `specs/status-page.md` – the specification of the status page.
- `specs/verification.md` – how each pipeline stage is shown to work, and on what data.
- `specs/NNN-feature-name/` – one folder per feature, holding `spec.md`
  (what and why), `plan.md` (how) and `tasks.md` (work breakdown).

Code is written only against an approved spec, plan and task list.

## Status

Spec `001-claim-foundation` is in progress: the store foundation, document
ingestion (stage 1) and claim submission are built; query and source tracing
are not yet written.
See `status.html`.

## Trying it

```bash
pip install -e ".[dev]"
```

```bash
pytest
```

```bash
axiomate ingest tests/fixtures/documents/everi_2024q1_10q.html --publisher-cik 0001318568 --type quarterly_report --published-on 2024-05-08 --fiscal-year 2024 --fiscal-period Q1 --format html
```

```bash
axiomate document show <document_id> --segment 3
```

## Licence

Proprietary, all rights reserved. See [LICENSE](LICENSE). No use, copying,
modification or distribution is permitted without written permission.
