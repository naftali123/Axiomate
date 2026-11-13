# Research: Claim Interpretation and Validation Gate

## Model: Claude Opus 5.5

- **Decision**: `claude-opus-5-5` through the official Anthropic Python SDK.
- **Why**: extraction from financial tables with context is the kind of task
  where a wrong reading is costly (constitution principle IV), and the amount
  of text is small because replies are stored. The cost difference to a
  smaller model is a few dollars over the whole evaluation.
- **Rejected for now**: a smaller model. It can be measured later against the
  same stored evaluation; the reply key includes the model id, so both can be
  held side by side.

## Structured output instead of free text

- **Decision**: the SDK's parsed structured output with a Pydantic model.
- **Why**: the reply is then a list of candidates in a known shape or an
  error, never prose to be scraped.
- **Note**: the reply model is deliberately looser than the claim schema
  (fields may be null). The claim schema and the gate decide, not the output
  format.

## Quotes, not offsets

- **Decision**: the model returns the quoted text; code finds it.
- **Why**: models miscount characters. A quote either occurs verbatim in the
  segment or the candidate is rejected, which is exactly principle II.

## Replies as files

- **Decision**: one JSON file per reply key.
- **Why**: they must be committed for the evaluation filings, reviewed in
  diffs and read without the database. A database table would hide them.

## One segment per call

- **Decision**: no grouping in the first version.
- **Why**: simple mapping from reply to segment, simple failure handling, and
  stable keys: editing one segment's context does not invalidate others.
- **Trade-off**: more calls. The instructions are a cached prefix, which
  removes most of the repeated input cost.

## Rules for numbers, dates and terms: project-owned

- **Decision**: small rule sets in the standard library.
- **Why**: the gate must be deterministic and explainable; each rejection
  names the rule. General-purpose parsers accept far more than filings use
  and change between versions.

## Evaluation against tags, not against a second model

- **Decision**: tagged figures are the only automatic ground truth.
- **Why**: they come from the company, in the same file. A second model as
  judge would measure agreement between models, not correctness.
