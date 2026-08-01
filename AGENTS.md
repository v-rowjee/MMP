# Project guidance for Codex

## Project context

This repository contains the backend for an AI data analytics platform. Users upload CSV data, ask questions in natural language, and generate analytics dashboards.

`DESIGN.md` is the main source of project context. Read the relevant sections before making a non-trivial change. The design is still evolving, so do not treat implementation details, libraries, schemas, or directory examples as permanently fixed unless the current code depends on them.

## Confirmed delivery structure

The system has three confirmed pipelines, implemented in this order:

1. Upload
2. Chat
3. Dashboard

Build the final intended version one pipeline at a time. Do not introduce a separate throwaway MVP, temporary architecture, or duplicate flow unless explicitly requested. Later pipelines should reuse completed shared components.

## Working rules

- Inspect the existing code and `DESIGN.md` before proposing or making changes.
- Work only on the requested pipeline and avoid unrelated refactors.
- Keep endpoint handlers thin; business logic belongs in services or domain modules.
- Prefer simple, typed, testable code over unnecessary abstractions.
- Keep configuration outside business logic and never hard-code secrets.
- Validate external input and structured model output at system boundaries.
- Preserve authentication, ownership checks, and data isolation.
- Keep numerical analytics deterministic; language models must not invent or calculate user-facing figures.
- Return explicit failures or unavailable states instead of fabricated results.
- Add or update focused tests for changed behaviour.
- Do not silently change a confirmed contract. Explain conflicts and ask before making a significant design decision.

## Keeping documentation current

Implementation details may change. When code and `DESIGN.md` disagree, identify the mismatch and update the documentation alongside the code when the change is intentional. Keep this file short and stable; detailed architecture belongs in `DESIGN.md`.

## Verification

Before finishing a change:

- Run the narrowest relevant tests and checks available.
- Report what changed, what was verified, and any unresolved assumptions.
- Do not claim a command or test passed unless it was actually run.
