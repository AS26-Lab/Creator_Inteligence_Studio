# Operational Evaluation

This layer provides a reproducible end-to-end harness for the existing Creator Intelligence Studio pipeline.

## Purpose

Operational evaluation runs controlled demo scenarios across the real services, records timings, cache behavior, warnings, assertions, and artifacts, and produces auditable reports. It does not add new algorithms or models.

## Scenarios

- `smoke_pipeline`
- `controlled_creator_workflow`
- `failure_recovery`
- `cache_reuse`
- `cpu_fallback`

## Isolation

- Demo creator, project, and video records only.
- Demo assets are generated in workspace-managed locations.
- Evaluation artifacts stay inside managed paths such as `temp/evaluations/`.
- No private user media is required.

## Stage coverage

The orchestrator reuses existing services for media inspection, audio preparation, transcription, acoustic analysis, visual analysis, multimodal analysis, clip ranking, controlled feedback, dataset snapshots, readiness checks, baseline training, verification, activation, and personalized scoring.
When a scenario includes clip rendering, it treats rendering as a local output step after review and verification, not as a ranking or training signal.

The controlled creator workflow also validates:

- workflow status aggregation per video;
- recommended next action;
- persisted task state after interruption;
- selection persistence for creator, project and last page;
- onboarding reopen behavior.

When a scenario includes subtitle deliveries, it validates local sidecar or burn-in outputs, manifest persistence, and verification metadata. This is a technical integrity check, not a statement about subtitle style quality or audience performance.

## Observability

Each run captures:

- stage timings;
- cache hits and misses;
- approximate RAM/VRAM sampling;
- assertions by severity;
- warnings and errors;
- produced artifacts;
- final result.

## CLI

- `evaluation scenarios`
- `evaluation run --scenario <name>`
- `evaluation show --run-id <id>`
- `evaluation stages --run-id <id>`
- `evaluation metrics --run-id <id>`
- `evaluation assertions --run-id <id>`
- `evaluation artifacts --run-id <id>`
- `evaluation retry-stage --run-id <id> --stage <name>`
- `evaluation cancel --run-id <id>`
- `evaluation export --run-id <id> --format json|csv|txt`
- `evaluation clean --run-id <id> [--dry-run]`

## GUI

The operational evaluation view shows scenarios, history, stages, metrics, assertions, warnings, artifacts, cache reuse, and the final result. It also supports compare, retry, cancel, export, and safe cleanup.

## Limitations

- A technically successful run does not prove recommendation quality.
- No new analysis model is introduced.
- Demo scenarios are synthetic and isolated from user-private content.
- `excluded` dataset rows are audited separately and do not count as train/validation/test leakage.
- The controlled binary baseline scenario does not require neutral examples to pass readiness.
- A passing run validates technical integrity and persistence, not recommendation quality or commercial usefulness.
