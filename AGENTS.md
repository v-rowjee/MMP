# Project guidance for Codex

## Project context

This repository contains the backend for an AI data analytics platform. Users upload tabular files, receive a generated analytics dashboard, and then ask questions about their data and dashboard findings.

Before proposing or making changes, read the applicable `AGENTS.md`, inspect the relevant code, and read `LANGGRAPH_ARCHITECTURE.md`. Treat `LANGGRAPH_ARCHITECTURE.md` as the main source of architecture context.

## Confirmed architecture

The runtime order is:

1. Upload
2. Dashboard
3. Chat

- Implement upload as deterministic application and service code.
- Implement dashboard generation as a LangGraph workflow with `DashboardState`.
- Implement chat as a separate LangGraph workflow with `ChatState`.
- Persist datasets, dashboard results, evidence, statuses, and chat messages in the database.
- Enable chat only after the dashboard is ready.
- Let chat read persisted dashboard evidence and query the dataset when required.
- Keep LangGraph state scoped to one graph run. Do not use it as permanent storage.

## Working rules

- Work only on the requested feature and avoid unrelated refactors.
- Keep everything simple and use the fewest practical lines of clear code.
- Use classes for services and group related service functions in the same class.
- Do not create custom error classes; use standard exceptions.
- Add only basic error handling unless security or data integrity requires more.
- Do not add unnecessary abstractions, wrappers, dependencies, configuration, or comments.
- Keep endpoint handlers thin and place business logic in services or domain modules.
- Reuse existing code, models, dependencies, naming, and project structure.
- Keep configuration outside business logic and never hard-code secrets or environment-specific values.
- Keep new and modified code typed.
- Validate external input and structured model output at system boundaries.
- Preserve authentication, ownership checks, RLS, and user data isolation.
- Keep numerical calculations deterministic. LLMs may select or interpret analysis but must not invent figures.
- Return explicit failure or unavailable states instead of fabricated results.
- Do not add enhancements, retries, fallbacks, optimisations, or extra features unless requested.
- Do not leave placeholders, mock results, or hard-coded application data.
- Do not silently change an existing contract or architecture decision. Ask before making a significant design change.

## Database changes

- Reuse the current schema where possible.
- If a database setup or schema script changes, provide the drop-all-application-tables script first, followed by the complete updated setup or schema script.
- Do not drop or modify authentication-managed tables.
- Preserve ownership constraints and RLS policies.

## Documentation

- Keep detailed architecture in `LANGGRAPH_ARCHITECTURE.md` rather than duplicating it here.
- When the implementation and architecture document disagree, identify the mismatch.
- Update `LANGGRAPH_ARCHITECTURE.md` alongside the code only when the architecture change is intentional and approved.

## Verification

Before finishing a change:

- Add or update focused tests for the changed behaviour.
- Run the narrowest relevant tests and configured lint or formatting checks.
- Run the relevant type checker.
- Fix all type errors caused or exposed by the changes.
- Do not claim a check passed unless it was actually run.
- Report what changed, what was verified, and any unresolved assumption or blocker.
