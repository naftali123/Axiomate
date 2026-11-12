# Axiomate – instructions for AI sessions

## Governing documents

- Read `.specify/memory/constitution.md` before making changes. Every spec, plan,
  task and code change must comply with it.
- Read `specs/verification.md` before specifying or building a pipeline stage.
  No stage is built until its verification method, data source and threshold
  are written down.
- This project follows Spec-Driven Development: write code only against an
  approved `spec.md`, `plan.md` and `tasks.md` under `specs/NNN-feature-name/`.

## Status page (blocking rule, constitution principle IX)

`status.html` at the repository root is the single Hebrew status page. Keeping it
up to date is mandatory.

- Update `status.html` in the same change whenever the project's state,
  architecture, plans, open issues, specs, evaluation numbers, key decisions or
  risks change.
- Always update the "עודכן לאחרונה" date when you edit it.
- Keep it in Hebrew, right-to-left, short, and self-contained (no external assets).
- Never add a second HTML status file.
- The page describes the product only. Do not list project tooling on it, such
  as GitHub Pages, branch protection, CI checks or the status page itself.
- The page follows `specs/status-page.md`. When the design or implementation of
  a pipeline component changes, update that component's detail panel too.
- Before finishing any task, check whether the page is still accurate and say so
  in your final message.
