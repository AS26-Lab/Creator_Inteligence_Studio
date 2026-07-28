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

Analytics foundation checks can be added as controlled scenarios to validate CSV/XLSX import, schema detection, mapping reuse, duplicate handling, interruption/retry and normalized export without external APIs.
Experiments and Learning scenarios can reuse the same harness with synthetic recommendations, decisions, evaluations, learning reviews and report exports, while keeping results verifiable and non-causal.
Creator Memory scenarios can validate profile roundtrips, traits, vocabulary, examples, limits, snapshot comparison, deterministic retrieval, CSV-safe export, and creator isolation without introducing LLMs or external APIs.
Creator Language scenarios can validate deterministic tokenization, sentence segmentation, filler analysis, narrative patterns, candidate generation, profile snapshots, cross-creator isolation, and CSV-safe export without mutating Creator Memory automatically.
Thumbnail Lab scenarios can validate title analysis, thumbnail analysis, pair evaluation, brand alignment, reference guidance, prompt generation, review loops, CSV-safe export, and creator isolation without generating images or editing layers automatically.
YouTube Read-Only scenarios can validate desktop OAuth, read-only scopes, channel import, video import, thumbnail metadata, analytics import, content linking, quota estimation, retry handling, interruption/recovery, and CSV-safe sync reports without any write operations on YouTube.
Audience Model scenarios can validate migration v22, signal normalization, segment creation, journeys, affinities, contradictions, profile snapshots, human review, cache reuse, invalidation, CSV-safe export, CLI and GUI visibility, while staying on synthetic data and avoiding invented demographics.
Instagram Read-Only Integration scenarios can validate OAuth flow, professional account validation, media sync, caption and cover history, insights import, rate limits, interruption and resume, content linking, exports and GUI/CLI visibility using only synthetic data and fakes.
TikTok Read-Only Integration scenarios can validate desktop OAuth, loopback callbacks, read-only scope validation, profile import, public video sync, cursor resume, cover history, public counters, manual analytics coexistence, rate-limit handling, interruption and resume, exports and GUI/CLI visibility using only synthetic data and fakes.

Market and Trend Intelligence Foundation scenarios should validate provenance, creator isolation, official public discovery boundaries, missing-data handling, reviewable opportunity candidates, and the absence of scraping or automatic recommendation claims.
Strategic Planning adds local review checkpoints, overload detection and snapshot history for operational inspection.
