# Creator Voice v34-A Evidence Foundation

## Purpose

v34-A establishes the canonical evidence boundary for future Creator Voice work. It decides what qualifies as creator voice evidence, why it qualifies, what is excluded, and how the selected evidence is exposed in a deterministic snapshot.

This phase does not synthesize a final voice profile, does not mutate prompts, and does not introduce embeddings or LLM inference.

## What v34-A Implements

- local Creator Voice evidence selection;
- deterministic evidence snapshots;
- creators, projects, workflows, and languages as explicit scope dimensions;
- explainable exclusion reasons;
- conservative handling of creator-edited AI content;
- separate structured treatment for confirmed preferences;
- offline operation with no provider calls.

## Reuse Map

| Existing concept | Voice role | Reuse / extend / ignore |
|---|---|---|
| `creator_corpus` documents, versions, and segments | canonical source of evidence | reuse |
| `authorship_class` | primary authenticity gate | reuse |
| `voice_learning_eligible` | eligibility gate for evidence selection | reuse |
| provenance / content hashes | deterministic identity and dedupe | reuse |
| review / confidence metadata | speech confidence policy and quality grading | reuse |
| `CreatorFeedbackService` | separate learning channel, not voice evidence | reuse only as adjacent input |
| confirmed preferences | structured guidance evidence, not style text | reuse separately |
| legacy creator voice / style rules | no direct synthesis in v34-A | ignore for profile generation |

## Canonical Evidence Types

Initial safe evidence types:

- `creator_written`
- `creator_edited`
- `creator_spoken`
- `confirmed_preference`

No vague style categories are introduced in v34-A.

## Qualification Rules

Eligible content is conservative by default.

- `creator_original` is eligible when active and `voice_learning_eligible` is true.
- `creator_edited` is eligible when active and `voice_learning_eligible` is true, but AI-origin lineage is treated conservatively.
- `transcribed_creator_speech` is eligible when active, `voice_learning_eligible` is true, and the segment confidence / review policy permits it.
- `ai_generated` is excluded.
- `ai_rewritten` is excluded by default.
- `imported_unknown` is excluded by default.
- `confirmed_preference` is eligible only as structured preference evidence, not as proof of writing style.

## Conservative AI-Edit Policy

v34-A uses a conservative rule for AI-origin edits.

- accepted AI output does not become creator-original by acceptance alone;
- AI-generated ancestor content remains marked as AI-origin contaminated;
- creator-edited AI content can be selected as evidence, but it is lower-confidence than creator-original evidence;
- no automatic span-level attribution is claimed yet;
- the service does not infer personality or style from the edit delta.

## Speech Policy

Transcribed creator speech is treated as valuable evidence, but only when it is trustworthy enough to be included.

- high-confidence reviewed segments may qualify;
- `needs_review` segments are excluded;
- low-confidence segments are excluded;
- `excluded_from_voice_learning` segments are excluded;
- the version-level snapshot is conservative when the segment set contains unsafe material.

## Scope

Every evidence item remains creator-scoped.

Supported scopes:

- creator-global;
- project-specific;
- workflow-specific;
- language-specific selection when requested.

Project scope never silently globalizes to other creators or other projects.

## Snapshot Contract

A snapshot is deterministic for a given corpus state and policy version.

It includes:

- `creator_id`;
- optional `project_id`;
- optional `workflow_type`;
- optional `language`;
- `policy_version`;
- `generated_at`;
- selected evidence items;
- counts by type and quality;
- excluded counts and reasons;
- language, project, and workflow distributions;
- estimated text size;
- a content fingerprint.

The snapshot is derived data only. The canonical source remains the corpus, provenance, review metadata, and confirmed preferences.

## Non-Goals

v34-A does not:

- synthesize a final Creator Voice profile;
- apply Creator Voice to prompts;
- change retrieval ranking;
- create style embeddings;
- infer personality or sensitive traits;
- add a UI editor for voice tuning;
- mutate confirmed preferences.

## Verification

The implementation is covered by focused tests for:

- creator-original eligibility;
- creator-edited policy;
- creator-spoken eligibility;
- low-confidence speech;
- needs-review speech;
- AI-generated exclusion;
- AI-rewritten exclusion;
- imported-unknown exclusion;
- confirmed preference separation;
- archive handling;
- project scope;
- workflow scope;
- language scope;
- creator isolation;
- duplicate deduplication;
- fingerprint stability;
- snapshot rebuild consistency;
- CLI diagnostics.
