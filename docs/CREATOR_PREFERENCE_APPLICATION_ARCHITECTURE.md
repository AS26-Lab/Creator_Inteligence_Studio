# Creator Preference Application Architecture

## Overview

Confirmed preferences are user-owned guidance that can be rendered into bounded context only after explicit confirmation.

Pipeline:

`Feedback Event -> Learning Signal -> Preference Candidate -> Human Confirmation -> Confirmed Preference -> Application Bundle`

## Application Service

`CreatorPreferenceApplicationService` is the canonical runtime boundary.

It accepts:

- `creator_id`
- optional `project_id`
- `workflow_type`
- current user instruction
- optional project instruction
- primary artifact metadata
- corpus context presence / size

It returns a `CreatorPreferenceApplicationBundle` containing:

- applied preferences;
- omitted preferences;
- conflicts;
- rendered context;
- request trace;
- application state;
- bundle fingerprint.

## Precedence

Deterministic priority:

1. system / safety
2. current user request
3. current project or artifact instruction
4. confirmed project / workflow-scoped preference
5. confirmed creator-global preference
6. historical corpus context

Current user and project instructions can override a stored preference.

## Supported Preference Shape

The initial supported type is structural rather than personality-based:

- `content_length_preference`

The renderer converts the structured value into bounded human-readable guidance.

## Scope Rules

Every preference retains explicit scope:

- creator-global
- project-specific
- workflow-specific

More specific preferences override broader preferences of the same type.

## Safety Rules

- no candidate preference may apply;
- no dismissed preference may apply;
- inactive confirmed preferences may not apply;
- free-text values are treated as untrusted user data;
- confirmed preferences cannot override system policy or safety behavior;
- the bundle is bounded by item and character limits.

## Workflow Integration

The application boundary is currently wired into:

- content brief
- production preparation

The same service remains provider-independent so OpenAI, Anthropic, or future providers consume the same rendered bundle.

## Diagnostics

Diagnostic output exposes:

- applied preference IDs;
- omitted preference IDs;
- scope;
- conflicts;
- counts;
- application state;
- bundle fingerprint.

This makes the application path auditable without exposing private source text by default.
