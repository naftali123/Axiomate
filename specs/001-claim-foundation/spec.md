# Feature Specification: Disclosure Ingestion and Claim Foundation

**Feature**: `001-claim-foundation`
**Created**: 2026-11-11
**Status**: Approved 2026-11-12
**Domain**: Corporate financial disclosures

## Purpose

Every later stage of Axiomate depends on two things being trustworthy: the stored
text of a disclosure, and the structured claims that point into it. This feature
delivers both foundations and nothing else. It covers pipeline stages 1
(ingestion) and 5 (claim store), plus the claim schema for financial disclosures.

## User Scenarios

### Story 1 – Ingest a disclosure with its provenance (Priority: P1)

An analyst adds a company disclosure (for example an earnings release) together
with who published it, what kind of document it is, when it was published and
which fiscal period it covers. The system stores it unchanged and makes every
sentence individually addressable.

**Why this priority**: nothing can be claimed, traced or compared without a
stable source text.

**Independent test**: ingest one document, then retrieve it and any of its
sentences by address and confirm the text is identical to the original.

**Acceptance scenarios**:

1. **Given** a disclosure with complete provenance, **when** it is ingested,
   **then** it is stored with a content hash and each sentence has a stable address.
2. **Given** a document that was already ingested, **when** the identical content
   is ingested again, **then** no second copy is created and the existing record
   is returned.
3. **Given** a disclosure with no publisher or no publication date, **when** it is
   ingested, **then** it is rejected with a message naming the missing field.
4. **Given** a stored document, **when** anyone attempts to alter its text,
   **then** the attempt is refused.
5. **Given** an HTML disclosure, **when** it is ingested, **then** its visible
   text is stored and addressable, and the original file is retrievable.

### Story 2 – Record a claim grounded in the text (Priority: P2)

A claim in the financial schema (for example "Acme, revenue, 4.2 billion USD,
fiscal Q3 2025, reported, actual") is submitted with a pointer to the exact span
of text it comes from. The system accepts it only if it is complete and the span
exists verbatim in the stored document.

**Why this priority**: constitution principle II requires every claim to trace
to the text; enforcing this at the point of storage protects everything downstream.

**Independent test**: submit one well-formed claim and several malformed ones and
confirm only the well-formed claim is stored.

**Acceptance scenarios**:

1. **Given** a complete claim whose span matches the document, **when** it is
   submitted, **then** it is stored with a formalization status.
2. **Given** a claim whose quoted span does not appear verbatim at the stated
   address, **when** it is submitted, **then** it is rejected.
3. **Given** a claim missing a required field (such as the fiscal period),
   **when** it is submitted, **then** it is rejected with the field named.
4. **Given** a stored claim, **when** a correction is submitted, **then** a new
   version is created and the earlier version remains retrievable.
5. **Given** a claim that relies on information not literally in the span,
   **when** it is submitted, **then** that information is stored as a named
   assumption with its origin, and the status is `formal-with-assumptions`.

### Story 3 – Find claims and trace them back (Priority: P3)

An analyst asks for all claims about a given company, metric and fiscal period,
and for any claim can see the exact sentence, document and publication date it
came from.

**Why this priority**: this is the lookup the matching stage will be built on,
and the first point at which a human can audit the store.

**Independent test**: store claims for two companies and two periods, query for
one combination and confirm exactly the expected claims return, each with its
source sentence.

**Acceptance scenarios**:

1. **Given** stored claims, **when** queried by company, metric and period,
   **then** only matching claims are returned, in a stable order.
2. **Given** any stored claim, **when** its source is requested, **then** the
   exact span, document and publication date are returned.
3. **Given** a claim with flags or assumptions, **when** it is retrieved,
   **then** they are returned with it.

### Edge cases

- The same figure appears twice in one document (headline and table).
- A period is stated relatively ("the prior-year quarter").
- A value is a range, a bound ("at least") or an approximation ("roughly").
- A figure is restated in a later document for an earlier period.
- A company's fiscal year does not match the calendar year.
- A company changes its name or is acquired.

## Requirements

### Functional requirements

- **FR-001**: The system MUST store each document with publisher, document type,
  publication date, covered fiscal period (when applicable) and a content hash.
- **FR-002**: The system MUST treat stored document text as immutable.
- **FR-003**: The system MUST NOT store duplicate copies of identical content.
- **FR-004**: The system MUST split each document into sentences by a
  deterministic method and give each a stable address.
- **FR-005**: The system MUST reject a document that lacks a publisher or a
  publication date.
- **FR-006**: The system MUST accept a claim only if it conforms to the claim
  schema below.
- **FR-014**: The system MUST accept documents as plain text or HTML. For HTML,
  the stored text is the visible text, extracted by a deterministic method, and
  the original file is kept alongside it.
- **FR-015**: The system MUST accept documents in English only and reject a
  document declared to be in another language.
- **FR-016**: The system MUST accept a claim only if its metric is one of:
  revenue, net income, earnings per share, operating cash flow.
- **FR-017**: On a `not-formalizable` claim, a schema field MAY be empty if a
  flag on the claim names that field as the reason. On any other claim every
  required field MUST be present.
- **FR-007**: The system MUST accept a claim only if its quoted span appears
  verbatim at the stated address in the stored document.
- **FR-008**: Every claim MUST record both the date it was said (the document's
  publication date) and the period it is about.
- **FR-009**: Every claim MUST carry one status: `formal`,
  `formal-with-assumptions` or `not-formalizable`.
- **FR-010**: The system MUST store flags (with reason codes) and assumptions
  (with origin: context store, model or human) attached to a claim.
- **FR-011**: Claims MUST be immutable; a correction creates a new version and
  preserves the old one.
- **FR-012**: The system MUST return claims by company, metric and fiscal period,
  in a stable order.
- **FR-013**: The same inputs MUST always produce the same stored result.

### Claim schema (financial disclosures)

| Field | Meaning | Required |
|---|---|---|
| Company | The entity the claim is about, by canonical identifier | Yes |
| Metric | One of: revenue, net income, earnings per share, operating cash flow | Yes |
| Value | A number, a range, or a bound | Yes |
| Unit and scale | Currency, percent, count; thousands, millions, billions | Yes |
| Precision | Exact, approximate, at least, at most, range | Yes |
| Period | The fiscal period or point in time the claim is about | Yes |
| Basis | Reported (standard accounting) or adjusted | Yes |
| Nature | Actual result, guidance, or forecast | Yes |
| Comparison | Absolute figure, or change against a named earlier period | Yes |
| Polarity | Affirmed or denied | Yes |
| Source span | Document, sentence address, exact quoted text | Yes |
| Said on | Publication date of the document | Yes |
| Status | Formalization status | Yes |
| Flags | Reason codes for anything hard to formalize | No |
| Assumptions | Named assumptions with origin | No |

### Key entities

- **Document**: an immutable disclosure with provenance and a content hash.
- **Sentence**: an addressable unit of a document.
- **Claim**: one atomic, schema-conforming statement grounded in a span.
- **Flag**: a reason a claim is hard to formalize.
- **Assumption**: something a claim relies on that the text does not state.

## Out of scope

- PDF input, non-English documents and companies not listed in the US.
- Metrics beyond the fixed list of four.
- Extracting claims from text automatically (stage 2).
- Checks beyond schema and span grounding (rest of stage 3).
- Context resolution, matching, comparison, review (stages 4, 6, 7, 8).
- Building the registry of companies and metrics; this feature only requires
  that claims reference them by identifier.

## Success criteria

- **SC-001**: A document retrieved after ingestion is byte-for-byte identical to
  what was ingested, in 100% of cases.
- **SC-002**: Ingesting the same content any number of times yields exactly one
  stored document.
- **SC-003**: 100% of stored claims have a span that matches the stored text
  verbatim.
- **SC-004**: 100% of malformed or ungrounded claims in the test set are rejected,
  each with a reason.
- **SC-005**: Running the same ingestion and claim submissions twice produces
  identical stores.
- **SC-006**: For any stored claim, the source sentence can be shown in one lookup.

## Verification

This feature covers stages 1 and 5. The project-wide strategy is in
[../verification.md](../verification.md).

| What is verified | Method | Data | Threshold |
|---|---|---|---|
| Stored text is unchanged (SC-001) | Ingest, retrieve, compare bytes | Ten real filings | 100% |
| Duplicates are not stored (SC-002) | Ingest each filing three times | Ten real filings | One record each |
| Sentences are split correctly | Compare with confirmed boundary labels | At least 200 labelled segments from the filings, confirmed by independent cross-check, with a person deciding the disputed ones | ≥ 98% of boundaries |
| Figures survive HTML extraction | Each figure tagged in the filing for the four metrics must appear in the stored text | HTML filings and the structured figures embedded in them | 100% |
| Good claims are accepted | Submit hand-written claims | At least 20 claims, each checked against the structured figures embedded in the filing where available | 100% |
| Bad claims are rejected (SC-004) | Submit corrupted copies of the good claims | At least 5 corrupted claims per rejection code, from a deterministic generator | 100%, each with the expected code |
| Nothing can be altered | Attempt updates and deletes on every table | Any stored data | 100% refused |
| Runs are reproducible (SC-005) | Two fresh runs, compare exports | All of the above | Identical |

**Data collection**

- Five US-listed companies are chosen and recorded with their identifiers.
- Ten of their real filings are taken from the open dataset `kapilrao/SEC-EDGAR`
  on Hugging Face: quarterly and annual reports, some older ones in plain text
  and recent ones in HTML with tables. Each is stored unchanged with its
  accession number, dataset file, retrieval date and hash.
- Earnings press releases are not in that dataset, so they are not part of this
  feature's test data. The document type remains in the schema for later.
- Sentence boundaries on the sample are confirmed by an independent splitter;
  a person decides the cases where it disagrees (amended 2026-11-12, see
  `../verification.md`).
- Good claims are written by hand; bad claims are generated from them.

All of this is development data. Held-out data is not needed until a stage
produces precision and coverage numbers.

## Clarifications

Resolved on 2026-11-12:

- **Unformalizable claims** (found during planning): see FR-017.
- **What "a flag names that field" means** (found while building claim
  submission, 2026-11-13): a flag on one field of the value, the period or the
  baseline covers the other fields of that same group. Details in the data model.
- **Input formats**: plain text and HTML. PDF is out of scope for this feature.
- **Language and market**: English-language filings of US-listed companies.
- **Metrics**: a fixed list for the first version – revenue, net income,
  earnings per share, operating cash flow. Other metrics are rejected.

## Constitution check

- II (traceability): FR-007, SC-003, SC-006.
- III (no silent assumptions): FR-010, Story 2 scenario 5.
- IV (flag rather than guess): FR-009, FR-010.
- V (reproducibility): FR-003, FR-004, FR-013, SC-005.
- VI (time-indexed claims): FR-008.
- VIII (verification): the Verification section above; method, data and
  thresholds are fixed before any code is written.
- IX (status page): `status.html` updated in the same change.
