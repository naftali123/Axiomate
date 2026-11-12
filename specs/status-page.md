# Specification: Project Status Page

**Scope**: the file `status.html`. It is a project aid, not part of the product.
**Governed by**: constitution principle IX.
**Last updated**: 2026-11-12

## Purpose

Give one person a correct, high-level picture of the project in under two
minutes, and let them drill into any pipeline component without opening the specs.

## Reader

The project owner. Reads Hebrew, knows the project's goals, does not want to
read code or full specs to know where things stand.

## Requirements

### Form

- **SP-001**: There is exactly one status page, `status.html`, at the repository root.
- **SP-002**: The page is in Hebrew and laid out right to left.
- **SP-003**: The page is a single self-contained file: no external scripts,
  styles, fonts or images, so it opens from disk and from any host.
- **SP-004**: The page is readable on a phone and on a desktop, in light and
  dark colour schemes.
- **SP-005**: The page fits its summary sections in roughly two screens on a
  desktop. Detail belongs in the component panels and the specs.

### Content

- **SP-006**: The page shows, in this order: a one-sentence description of the
  product and the date of last update; the architecture diagram; current work;
  planned work; open issues; accuracy numbers; top risks; recent decisions; the
  table of feature specs.
- **SP-007**: The page describes the product only. Project tooling (hosting,
  branch protection, checks, this page itself) is not listed.
- **SP-008**: "Recent decisions" holds at most six entries, newest first, each
  with a one-line reason. Older decisions are dropped from the page; they
  remain in the specs and the constitution.
- **SP-009**: "Top risks" holds at most three entries.
- **SP-010**: Accuracy numbers come from the latest evaluation run on the
  held-out set, with the date of the run. Until a run exists the page says so.
- **SP-011**: Each row of the specs table names the spec, its phase (spec, plan,
  tasks, in progress, done) and a link to it.

### Architecture diagram

- **SP-012**: The diagram shows every pipeline stage in order, plus the context
  stores, and marks each as deterministic, language model or human review.
- **SP-013**: Each stage shows its status: not started, specified, built or tested.
- **SP-014**: Every component in the diagram can be activated by mouse, touch
  and keyboard, and opens a panel over the page with further detail.
- **SP-015**: A component panel contains, as far as currently known:
  - its role in one or two sentences;
  - what it receives and what it produces;
  - how it is intended to be built, or how it is built;
  - how it is verified, with the threshold if one is set;
  - its status and the spec that covers it, with a link.
- **SP-016**: A panel states plainly what is not yet decided, rather than
  leaving it out or guessing.
- **SP-017**: A panel closes with a close button, the Escape key, or a click
  outside it, and returns focus to the component that opened it.
- **SP-018**: Panel content reflects the current understanding. It is updated in
  the same change whenever a spec, plan or implementation changes that component.

### Upkeep

- **SP-019**: Any change to the project's state, architecture, plans, open
  issues, specs, evaluation numbers, decisions or risks updates the page in the
  same change, including the date.
- **SP-020**: A pull request that changes specs, code or the constitution
  without changing the page fails its check, unless labelled `status-not-affected`.

## Acceptance checks

1. Opening the file from disk with no network shows the complete page.
2. Every diagram component opens a panel with the five items in SP-015, by
   click and by keyboard.
3. Escape, the close button and a click outside each close the panel.
4. At phone width nothing overflows horizontally.
5. Nothing on the page contradicts the specs or the constitution at the same commit.

## Out of scope

- History of past states; the repository history serves that purpose.
- Editing project data from the page.
- Any language other than Hebrew.
