# Creator Voice Guidance Architecture

## Overview

The guidance architecture is the consumption layer between `CreatorVoiceProfile` and any future workflow integration.

Pipeline:

1. `CreatorVoiceEvidenceService` builds a deterministic evidence snapshot.
2. `CreatorVoiceProfileService` derives a structured Creator Voice profile.
3. `CreatorVoiceGuidanceService` consumes that profile and emits a bounded preview bundle.

The current phase stops at preview.

## Domain Contracts

Canonical contracts introduced in v34-C:

- `CreatorVoiceGuidanceRequest`
- `CreatorVoiceGuidanceItem`
- `CreatorVoiceGuidanceOmission`
- `CreatorVoiceGuidanceConflict`
- `CreatorVoiceGuidanceBundle`

These contracts are deterministic, serializable, and rebuildable.

## Service Boundary

`CreatorVoiceGuidanceService` is the only intended entry point for consuming Creator Voice profiles.

It:

- accepts the profile as derived data;
- applies scope, language, confidence, and readiness checks;
- maps a small allowlist of features to controlled guidance templates;
- records override and omission reasons;
- emits a fingerprinted bundle for diagnostics.

It does not interpret corpus text, does not score style with an LLM, and does not mutate the final AI request.

## Feature Mapping

The preview uses controlled mappings, not free-form prompt generation.

Examples:

- `typical_word_count` -> introductory length guidance;
- `median_sentence_length` -> sentence-length guidance;
- `paragraph_density` -> formatting guidance;
- `question_ratio` -> question-usage guidance;
- `spoken_median_sentence_length` -> spoken-mode guidance.

The mapping is intentionally small and conservative.

## Precedence Handling

When a voice tendency conflicts with a higher-precedence signal, the voice item is omitted and the bundle records the reason.

Handled overrides:

- confirmed preference override;
- current user override;
- project instruction override;
- profile scope mismatch;
- language mismatch;
- unsupported workflow mode;
- insufficient confidence.

## Budgets And Ordering

The bundle is bounded by explicit budgets:

- maximum item count;
- maximum rendered characters.

Ordering is deterministic and based on feature priority, scope, and safety filters.

## Preview Renderer

The rendered preview is template-driven and bounded.

It does not include raw corpus text or private repeated tokens.

The renderer exists only to make diagnostics human-readable.

## Fingerprint

The bundle fingerprint depends on:

- guidance policy version;
- profile fingerprint;
- creator, project, workflow, and language scope;
- enabled/disabled state;
- budgets;
- selected and omitted guidance identities.

Unchanged inputs must produce the same bundle fingerprint.

## CLI Surface

`voice guidance-preview` is the canonical diagnostic entry point.

It can be run in:

- enabled mode;
- disabled mode.

The command is preview-only and does not alter workflow behavior.

## Non-Goals

v34-C does not:

- wire guidance into request assembly;
- wire guidance into prompt rendering;
- add a final style prompt;
- change retrieval ranking;
- change preference application;
- synthesize personality fields;
- infer sensitive traits.
