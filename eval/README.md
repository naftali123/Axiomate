# Evaluation data

- `filings/` – the held-out filings of spec 002, unchanged, with `manifest.json`
  (provenance and hashes) and `selection.json` (how they were chosen).
- `facts/` – the figures tagged in those filings, extracted by
  `tools/read_embedded_figures.py`.
- `splits.json` – which filings are development and which are held out. A
  filing never changes sides.

**The held-out filings are sealed.** They were chosen from metadata and tag
counts only, on 2026-11-13, before interpretation was built. They are not to be
read, quoted in tests, or used to write or tune rules or instructions. They are
used once, with frozen instructions, to report results (spec 002, task T029).
If a threshold is missed and the instructions are then changed, this set counts
as used and a new one is needed. A test enforces that no other test or source
file refers to them.
