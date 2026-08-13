# Creator Feedback And Learning Architecture

## Overview

The feedback and learning layer is a local, creator-scoped evidence system built on top of the existing corpus and workflow foundations.

It is designed to answer:

- what happened;
- on which artifact it happened;
- which version was AI-generated;
- which version the creator ended up using;
- what changed;
- what evidence exists;
- how often the same evidence repeats;
- whether the evidence is creator-global, project-specific, or workflow-specific.

## Architecture Layers

1. Canonical feedback events.
2. Deterministic revision diff generation for edit transitions.
3. Conservative learning-signal derivation.
4. Auditable evidence links.
5. Diagnostic read/query surfaces.

## Canonical Event Boundary

`CreatorFeedbackEvent` is the source of truth.

It records:

- `creator_id`
- optional `project_id`
- `workflow_type`
- `artifact_type`
- `artifact_id`
- optional `source_version_id`
- optional `result_version_id`
- optional `ai_execution_id`
- `event_type`
- `event_source`
- `created_at`
- metadata

The repository and service layer enforce creator ownership and dedupe keys so repeated replay does not inflate counts.

## Revision Diff Boundary

`CreatorRevisionDiffService` computes deterministic text diff summaries for explicit version transitions.

The persisted diff is compact and versioned. It records summary facts such as lengths, additions, removals, and change ratio instead of storing another full copy of the artifact text.

## Learning Signal Boundary

`CreatorLearningSignal` is derived state.

Signals remain:

- creator-scoped;
- optionally project-scoped;
- optionally workflow-scoped;
- evidence-backed;
- rebuildable;
- dismissible.

Signal status is conservative:

- observed
- candidate
- dismissed

Confirmed preferences are intentionally not automatic in v33-H.

## Explicit Separation Rules

The system keeps these boundaries separate:

- feedback event != learning signal;
- learning signal != candidate preference;
- candidate preference != confirmed preference;
- AI-generated content != creator-original content;
- provider approval != content acceptance.

## Packaged Validation Role

The packaged Windows runtime exposes developer/diagnostic surfaces so frozen validation can invoke the canonical services without adding user-facing controls.

Those surfaces are only for:

- packaged runtime validation;
- developer diagnostics;
- evidence capture in frozen smoke tests.

## Privacy And Safety

The architecture does not require:

- network calls;
- OpenAI or Anthropic execution;
- embedding updates;
- vector database writes;
- prompt mutation;
- sensitive-trait inference.

Safe logging is limited to IDs, scope, counts, and statuses unless explicit debug output is requested.
