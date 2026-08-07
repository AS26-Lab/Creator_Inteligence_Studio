# Current Implementation Reality

## Purpose

This document records what is actually implemented in the repository through the current v32-F slice. It is not a wish list.

## Cut-Off State

- canonical starting commit: `64f380dd4adf0fa9462188401eabd5e228fec387`
- current migration ceiling: `v32`
- repository state at inspection time: clean
- `v31` exists and introduces the first AI runtime foundation
- AI runtime orchestration has started as a controlled provider layer
- Component Manager and Local Transcription Foundation now spans v32-A through v32-F: catalog, installation inventory, hardware inventory, transcription profiles, deterministic capability resolver, managed FFmpeg, resumable downloads, explicit runtime/model installers, and resolver-owned transcription readiness. The existing transcription stack is still the runtime path for execution and is wrapped by the component-manager boundary rather than replaced.

## What Is Implemented

### Core Application

- package entry point
- bootstrap
- CLI
- GUI desktop shell
- interactive launcher cleans inherited test-only GUI variables before opening the visible window
- the desktop shell defers startup recovery and heavy AI Runtime refresh work until after `show()`
- logging
- environment diagnostics
- local paths
- SQLite persistence

Status: `implemented`

## Audited Capability Classes

| Capability | Classification | Evidence | Notes |
|---|---|---|---|
| Transcripcion local | `implemented` | `TranscriptionService.transcribe_video` drives `FasterWhisperEngine`, model download/verify commands, persistence, export, and stale detection. | Real local transcription exists and is model-backed. |
| Analisis acustico | `deterministic` | `AcousticAnalysisService.analyze_acoustics` computes frame metrics, pauses, events, and global metrics from local WAV data. | It is technical signal processing, not semantic audio understanding. |
| Analisis visual | `deterministic` | `VisualAnalysisService.analyze_visuals` samples frames with FFmpeg, computes frame metrics, detects cuts/scenes, and extracts keyframes. | It is local visual signal analysis, not model-based narrative comprehension. |
| Analisis multimodal | `deterministic` | `MultimodalAnalysisService.analyze_multimodal` aligns transcription, acoustic, and visual outputs, then applies deterministic candidate scoring and fusion. | It combines existing signals; it does not understand content semantically. |
| Ranking de clips | `deterministic` | `ClipRankingService.rank_clip_candidates` scores candidates from multimodal windows, resolves overlaps, applies diversity, and preserves human review state. | It is heuristic ranking, not creative judgment. |
| Render local de clips | `implemented` | `ClipRenderService.render_candidate`, `create_sidecar_delivery`, and `create_burn_in_render` call FFmpeg, verify output, and persist artifacts. | Existing reusable utility; not automatic editing intelligence. |
| Subtitulos | `implemented` | `SubtitleService.generate_video_subtitles`, `generate_clip_subtitles`, `import_subtitles`, `export_subtitles`, and edit history flows are present. | Editorial subtitle workflows exist and are traceable. |

### Creator, Project, Video Core

- creator CRUD and archive flows
- project CRUD and archive flows
- local video registration
- video availability verification
- local inspection artifacts

Status: `implemented`

### Media Preparation

- `ffprobe` based technical inspection
- `ffmpeg` based thumbnail derivation
- `ffmpeg` based normalized audio preparation

Status: `implemented`

### Transcription

- local transcription commands
- model status and model download commands
- export and deletion flows
- CUDA-capable `faster-whisper` / `CTranslate2` path

Status: `implemented`

### Acoustic, Visual, And Multimodal Analysis

- acoustic analysis services and artifacts
- visual analysis services and artifacts
- multimodal aggregation with candidate timelines

Status: `deterministic`

### Clip Ranking And Clip Rendering

- human-reviewed clip ranking
- history and notes
- local FFmpeg clip rendering
- render verification and manifest history

Status: ranking `deterministic`; rendering `implemented`

### AI Runtime And Provider Orchestration

- provider credential storage through the OS credential backend or explicit development fallback
- provider diagnostics for OpenAI and Anthropic
- centralized provider request profiles for OpenAI and Anthropic diagnostic contracts
- gpt-5.6-luna diagnostics currently target OpenAI Responses API with max_output_tokens, reasoning.effort=none, and omit temperature in the minimal connectivity payload
- real-call validation for OpenAI Responses API completed on 2026-08-06 with execution `a1c404db-dc52-48de-9500-a231d8b8a4f5`, status `completed`, input tokens `13`, output tokens `5`, latency `1990 ms`, and visible message `Diagnostico completado.`
- OpenAI request validation runs before HTTP so unsupported parameters are blocked locally
- OpenAI response handling now preserves textual connectivity responses separately from structured-output validation, instead of coercing all non-JSON text into provider failure
- role-based model registry
- versioned prompt template registry
- budget policy checks
- privacy policy checks
- execution and usage persistence
- exact-match cache entries
- CLI exposure for providers, models, roles, budgets, diagnostics, and history

Status: `implemented` for the foundation layer; OpenAI has been real-call validated on Responses API; only `provider_diagnostic` task support is enabled in v31.

### Subtitles

- video subtitle generation
- clip subtitle generation
- edit, import, export, validate, and history flows
- sidecar and burn-in delivery models

Status: `implemented`

### Analytics, Experiments, And Learning

- analytics import foundation
- analytics lab
- experiment registration and learning artifacts
- operational evaluation

Status: `implemented`

### Creator Memory, Creator Language, And Packaging

- creator memory
- creator language analysis
- thumbnail lab
- title analysis
- creative packaging

Status: `implemented`

### Platform Read-Only Integrations

- YouTube read-only
- Instagram read-only
- TikTok read-only
- multi-platform consolidation

Status: `implemented`

### Strategic Foundations

- audience model foundation
- market and trend intelligence foundation
- opportunity and recommendation engine foundation
- strategic planning and content roadmap foundation
- content brief and pre-production foundation
- script outline and production preparation foundation

Status: `implemented`

## What Is Deterministic Or Infrastructure Only

- many phase modules are deterministic workflow scaffolding;
- many services are structural and database-backed;
- creator memory, creator language, packaging, planning, briefs, and production prep are not yet semantic AI;
- the current `AI_ML_ARCHITECTURE.md` in the repository was conceptual infrastructure, not a running AI stack;
- the current codebase has no semantic retrieval layer;
- the current codebase has no feedback-learning loop for AI outputs;
- the current codebase does not expose product download sources for transcription runtime or models;
- the current codebase has no collective intelligence sharing pipeline;
- the current codebase has no automatic video editing pipeline.
- acoustic, visual, multimodal, and clip ranking pipelines are deterministic signal-processing and scoring layers, not semantic AI.

Status: `infrastructure_only` or `deterministic`, depending on module

## What Requires AI

- strategic creative generation
- voice-aware script drafting
- provider orchestration
- multimodal interpretation beyond local technical analysis
- creative rewrite and critique
- semantic retrieval
- role-based model competition

Status: `requires_ai`

## What Requires ML

- creator-specific embeddings search
- semantic retrieval ranking
- feedback-driven learning
- benchmarked model selection
- future prediction layers

Status: `requires_ml`

## What Is Not Started

- Creator Corpus Foundation
- Semantic Retrieval Foundation
- Feedback Learning Foundation
- Creator Voice Workbench
- Human-Guided Script Drafting Foundation
- automatic video editing

Status: `not_started`

## Component Manager v32-D Resumable Download Manager Foundation

- resumable download manager exists as a filesystem-backed foundation
- downloads are persisted under the controlled downloads root, separate from installation state
- pause, resume, cancel, restart recovery, size checks, SHA-256 checks, and Range handling are implemented
- the manager does not install or activate components automatically
- local/test sources are allowed only with explicit test/developer approval; no product download sources are enabled yet
- the FFmpeg installer can consume a verified artifact contractually, but the pipeline is not connected automatically

Status: `implemented`

## Component Manager v32-E Managed Transcription Runtime And Model Installers

- explicit local-only runtime installation exists for transcription bundles
- explicit local-only model installation exists for faster-whisper / CTranslate2 model bundles
- verified artifacts from v32-D can be consumed contractually by the installers
- staging, validation, atomic activation, and persistence are implemented
- managed installs and legacy cache detection are separated
- the model manager no longer relies on implicit hidden downloads in the normal path
- the capability resolver and transcription engine now resolve explicit installed paths instead of assuming download-on-demand behavior
- no product download sources for runtime or models are enabled
- no pip-based runtime installation is used

Status: `implemented`

## Component Manager v32-F Transcription Readiness Closure

- `TranscriptionCapabilityResolver` is the canonical readiness authority
- `can_transcribe_now` is the hard gate for local transcription
- profile fallback is deterministic and read-only
- GPU readiness depends on benchmark evidence and freshness
- `TranscriptionService` consumes a resolved execution plan and refuses to start when the capability is blocked
- the CLI exposes read-only capability and execution-plan commands

Status: `implemented`

## Component Manager v32-A Foundation

- migration `v32` is present and idempotent
- the component catalog is versioned and seeded
- installations, hardware profiles, runtime checks, and events have first-class tables
- transcription profiles are versioned and seeded with `fast`, `balanced`, `maximum_quality`, and `custom`
- the resolver is deterministic and read-only
- `TranscriptionService` no longer auto-downloads a missing model implicitly
- CLI read-only inspection is available through `components status` and `components capability`

## Component Manager v32-B Hardware Benchmark Foundation

- explicit local benchmark service exists for CPU and opt-in GPU checks
- benchmark execution uses only already installed local models and a safe local fixture
- runtime, model loading, inference, resource release, and readiness classification are recorded
- benchmark results persist into the existing component-manager SQLite tables
- the capability resolver can read the latest successful benchmark evidence without mutating state
- the benchmark path does not download, install, relocate, or update anything automatically
- CLI read-only benchmark inspection is available through `components benchmark` and `components benchmark status`

Status: `implemented`

## Component Manager v32-C Managed FFmpeg Boundary

- managed FFmpeg and FFprobe are now represented as a single local bundle with two executables
- external FFmpeg detection remains read-only and is never repaired, moved, or removed by the app
- the component manager can install from a local directory or local ZIP package through staging
- activation is performed only after health checking and validation
- the health checker verifies both binaries and uses a local fixture for ffprobe / ffmpeg execution checks
- repair is local-only and preserves the previous active installation until replacement succeeds
- removal is available for managed installs only and can fall back to external detection when present
- the central media-tool resolver now feeds audio preparation, media inspection, and transcription capability resolution
- CLI support is explicit through `components ffmpeg status`, `verify`, `install-local`, `repair-local`, and `remove`
- no HTTP downloader is implemented
- no PATH-global mutation is implemented

Status: `implemented`

## Known Discrepancies And Resolutions

| Contradiction | Documents Involved | Canonical Resolution | Impact | Future Action |
|---|---|---|---|---|
| Existing deterministic infrastructure can be mistaken for AI. | `README.md`, older phase docs, service names, this Project Bible | Infrastructure stays infrastructure until models, retrieval, and feedback learning are added. | Prevents false claims about intelligence. | Keep statuses explicit in future docs. |
| Older AI/ML doc is too generic. | `docs/AI_ML_ARCHITECTURE.md`, `docs/PROJECT_BIBLE.md` | Project Bible and catch-up decisions now govern the AI contract. | Old doc becomes subordinate. | Update future references to point to the new canon. |
| Human-Guided Script Drafting was listed as next in an older doc. | `docs/SCRIPT_OUTLINE_AND_PRODUCTION_PREPARATION_FOUNDATION.md`, `docs/ROADMAP.md`, this roadmap | The next approved AI block is AI Runtime and Provider Orchestration Foundation, but it is not started. | Old phase ordering is superseded for the AI catch-up path. | Use the new roadmap only for AI work. |
| AI Runtime was previously described as not started after the foundation existed. | This document, `docs/AI_RUNTIME_AND_PROVIDER_ORCHESTRATION_FOUNDATION.md` | The AI Runtime foundation is implemented at v31 and the open OpenAI compatibility work is a closeout correction, not a new phase. | Prevents contradictory status reporting. | Keep future docs aligned with the implemented foundation and current contract audit. |

## Reuse Opportunities

The existing repo already provides reusable infrastructure for future AI work:

- Analytics
- Experiments
- Creator Memory
- Creator Language
- Thumbnail Lab
- YouTube Read-Only
- Instagram Read-Only
- TikTok Read-Only
- Audience Model
- Market and Trend Intelligence
- Opportunity and Recommendation Engine
- Strategic Planning
- Content Roadmap
- Content Briefs
- Script Outlines
- Production Preparation
- claims
- rights
- reviews
- approvals
- snapshots
- provenance
- creator isolation

These are mostly structural, deterministic, and traceable foundations. They should not be documented as mature creative intelligence until they are connected to models, retrieval, and learning.
