# Creator Preferences And Confirmation Architecture

Observed feedback events
-> derived learning signals
-> deterministic preference candidates
-> explicit human confirmation
-> persisted confirmed preferences

## Rules

- one signal is not a preference
- one candidate is not a confirmed preference
- confirmed preferences require explicit human action
- project scope does not automatically become creator-global scope
- workflow scope remains distinct
- dismissed candidates are auditable and do not auto-apply
- confirmations may include a user-edited final value
- the system stores provenance, evidence links, and scope metadata separately from any free-text confirmation value

## Developer Surfaces

The frozen runtime exposes diagnostic/validation commands for:

- `feedback record-edit`
- `preferences synthesize`
- `preferences confirm`
- `preferences dismiss`
- `preferences snapshot`

These are validation boundaries, not normal-user product features.

## Safety Boundaries

- no prompt application in v33-I
- no retrieval mutation
- no creator voice mutation
- no LLM required
- no remote network required
- no sensitive personal trait inference

## v33-J Application Boundary

Confirmed preferences are now eligible for bounded application through `CreatorPreferenceApplicationService`.

Rules:

- only `active` + `confirmed` preferences may apply
- candidates remain non-authoritative
- dismissed preferences remain non-authoritative
- current user and project instructions outrank stored preferences
- project / workflow scope stays explicit
- the application bundle is bounded and auditable
- content brief and production preparation are the first wired workflows

The application step does not change how preferences are stored, confirmed, dismissed, deactivated, or reactivated.
