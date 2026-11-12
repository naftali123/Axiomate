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
- `specs/NNN-feature-name/` – one folder per feature, holding `spec.md`
  (what and why), `plan.md` (how) and `tasks.md` (work breakdown).

Code is written only against an approved spec, plan and task list.

## Status

Pre-implementation. The constitution is ratified. Spec `001-claim-foundation` has its spec, plan and tasks written, awaiting approval. See `status.html`.
