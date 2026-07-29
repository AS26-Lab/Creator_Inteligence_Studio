# AI / ML Architecture

## Status

This document defines the approved AI/ML operating model for Creator Intelligence Studio. It is subordinate to `docs/PROJECT_BIBLE.md`.

The first approved implementation block is now present as `docs/AI_RUNTIME_AND_PROVIDER_ORCHESTRATION_FOUNDATION.md` and is limited to controlled provider diagnostics, role catalogs, budgets, privacy policy, execution persistence, and safe CLI/GUI exposure.

## Architecture Model

The product uses a hybrid architecture:

- local core for deterministic work and storage;
- selective external APIs only where they materially improve quality or speed;
- local processing whenever it is reasonable;
- replaceable AI roles instead of fixed provider coupling;
- observable, reproducible outputs;
- human approval for sensitive decisions.

The first stage uses only:

1. OpenAI
2. Anthropic

No third normal provider is approved for the initial stage.

## Provider Orientation

### OpenAI

Initial preferred role:

- structured tasks;
- classification;
- extraction;
- general reasoning;
- analytics support;
- multimodal support;
- transcription fallback;
- alternative generation.

### Anthropic

Initial preferred role:

- scripts;
- voice-preserving rewrite;
- narrative work;
- copywriting;
- creative critique;
- authenticity evaluation.

No provider is permanently crowned. Benchmarks decide task-by-task.

## Replaceable Roles

The product must depend on conceptual roles, not model names.

- `cheap_structured_model`
- `general_reasoning_model`
- `creative_writing_model`
- `multimodal_model`
- `transcription_fallback_model`
- `evaluation_model`

Each role needs:

- capabilities;
- state;
- version;
- snapshot;
- cost;
- benchmark results;
- deprecated models;
- controlled replacement;
- provider-internal fallback;
- cross-provider fallback only with permission;
- no silent change for important tasks.

## Catalog Requirements

The central catalog must record:

- role;
- provider;
- model name;
- version;
- capability notes;
- supported formats;
- supported modalities;
- known limits;
- cost profile;
- latency profile;
- benchmark history;
- status;
- replacement history;
- retirement status.

## Orchestration Requirements

The orchestrator must:

- select a role;
- honor task sensitivity;
- enforce provider policy;
- record the selected model and provider;
- preserve prompt and output provenance;
- route fallbacks explicitly;
- preserve human override points;
- avoid silent upgrades on important tasks.

The first concrete execution path is provider diagnostics:

`AIExecutionRequest -> AIOrchestrator -> privacy -> budget -> role resolution -> provider -> validation -> persistence -> AIExecutionResult`

## Privacy And Control

The AI stack must:

- keep creator data isolated by `creator_id`;
- avoid training on private creator data without explicit approval;
- keep secrets out of logs, SQLite, and backups;
- prefer local processing where practical;
- document every provider exchange that matters.

## Caching And Observability

Cache and observability must cover:

- prompt templates;
- provider responses;
- retries;
- costs;
- token usage;
- latency;
- fallback reason;
- benchmark version;
- task role;
- creator scope.

## Benchmarks

Benchmarks are required before provider choice becomes canonical.

They must compare:

- authenticity;
- rewriting quality;
- strategic quality;
- multimodal extraction;
- structured extraction;
- latency;
- cost;
- stability;
- creator fit.

## Discrepancy Note

The older conceptual doc focused on rules, embeddings, classifiers, and rankers. That is still useful, but it no longer defines the top-level contract. The current authority is the Project Bible plus the catch-up decisions.
