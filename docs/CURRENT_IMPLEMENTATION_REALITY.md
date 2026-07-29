# Current Implementation Reality

## Purpose

This document records what is actually implemented in the repository at the v30 cut-off. It is not a wish list.

## Cut-Off State

- canonical starting commit: `64f380dd4adf0fa9462188401eabd5e228fec387`
- current migration ceiling: `v30`
- repository state at inspection time: clean
- no `v31` exists
- no AI runtime has started

## What Is Implemented

### Core Application

- package entry point
- bootstrap
- CLI
- GUI desktop shell
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
- the current codebase has no provider orchestrator;
- the current codebase has no AI role catalog;
- the current codebase has no semantic retrieval layer;
- the current codebase has no feedback-learning loop for AI outputs;
- the current codebase has no component manager for models and FFmpeg;
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

- AI Runtime and Provider Orchestration Foundation
- Component Manager and Local Transcription Foundation as a formal AI stage
- Creator Corpus Foundation
- Semantic Retrieval Foundation
- Feedback Learning Foundation
- Creator Voice Workbench
- Human-Guided Script Drafting Foundation
- automatic video editing

Status: `not_started`

## Known Discrepancies And Resolutions

| Contradiction | Documents Involved | Canonical Resolution | Impact | Future Action |
|---|---|---|---|---|
| Existing deterministic infrastructure can be mistaken for AI. | `README.md`, older phase docs, service names, this Project Bible | Infrastructure stays infrastructure until models, retrieval, and feedback learning are added. | Prevents false claims about intelligence. | Keep statuses explicit in future docs. |
| Older AI/ML doc is too generic. | `docs/AI_ML_ARCHITECTURE.md`, `docs/PROJECT_BIBLE.md` | Project Bible and catch-up decisions now govern the AI contract. | Old doc becomes subordinate. | Update future references to point to the new canon. |
| Human-Guided Script Drafting was listed as next in an older doc. | `docs/SCRIPT_OUTLINE_AND_PRODUCTION_PREPARATION_FOUNDATION.md`, `docs/ROADMAP.md`, this roadmap | The next approved AI block is AI Runtime and Provider Orchestration Foundation, but it is not started. | Old phase ordering is superseded for the AI catch-up path. | Use the new roadmap only for AI work. |

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
