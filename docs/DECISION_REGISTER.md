# Decision Register

## Purpose

This register keeps the canonical decisions, their status, and what they replace.

## Canonical Decisions

| Date | Decision | Status | Reason | Documents Affected | Replaces Or Limits |
|---|---|---|---|---|---|
| 2026-07-22 | Windows + NVIDIA CUDA is the initial platform focus | approved | best fit for current hardware and performance goals | `docs/PROJECT_BIBLE.md`, `README.md` | broad multi-platform first approach |
| 2026-07-22 | Python 3.11 is the initial runtime | approved | matches current environment and package compatibility | `README.md`, `pyproject.toml` | later runtime drift |
| 2026-07-22 | Local processing is preferred whenever viable | approved | privacy, latency, and control | `docs/PROJECT_BIBLE.md`, `docs/AI_ML_ARCHITECTURE.md` | cloud-first default |
| 2026-07-22 | External AI providers are optional and replaceable | approved | avoid lock-in | `docs/AI_ML_ARCHITECTURE.md` | single-provider coupling |
| 2026-07-22 | Script and voice work is optional until explicitly approved | approved | keep analysis and creative generation separable | `docs/PROJECT_BIBLE.md`, `docs/ROADMAP.md` | mandatory script generation |
| 2026-07-22 | Creator data must remain strictly separated | approved | privacy and contamination control | `docs/PROJECT_BIBLE.md`, `docs/CREATOR_MEMORY_AND_LEARNING.md` | global merged profiles |
| 2026-07-22 | SQLite is the initial structured store | approved | portable local development | `README.md`, migration layer | early external DB complexity |
| 2026-07-22 | Initial video registration keeps normalized absolute paths and does not copy media | approved | lightweight registration | `README.md`, `docs/CURRENT_IMPLEMENTATION_REALITY.md` | premature media duplication |
| 2026-07-22 | `ffprobe` inspects video; `ffmpeg` prepares thumbnail and audio | approved | technical inspection without AI | `README.md`, `docs/LOCAL_COMPONENTS_AND_TRANSCRIPTION.md` | AI-dependent inspection |
| 2026-07-22 | `faster-whisper` + `CTranslate2` is the local transcription backend | approved | CUDA-capable local transcription with CPU fallback | `README.md`, `docs/LOCAL_COMPONENTS_AND_TRANSCRIPTION.md` | remote-only transcription |
| 2026-07-22 | Visual, acoustic, and multimodal analysis start as technical and local | approved | avoid semantic overclaiming | `docs/CURRENT_IMPLEMENTATION_REALITY.md` | narrative interpretation before AI |
| 2026-07-23 | Rendered clips must be local, reproducible, and verified | approved | keep media output controlled | `docs/PROJECT_BIBLE.md` and production docs | unverified render flows |
| 2026-07-24 | Creator Memory is structured, versioned, and reviewable | approved | preserve evidence and contradictions | `docs/CREATOR_MEMORY_AND_LEARNING.md` | hidden automatic memory mutation |
| 2026-07-25 | Creator Language analysis is local, deterministic, and reviewable | approved | candidate generation only | `docs/CREATOR_MEMORY_AND_LEARNING.md`, `docs/CURRENT_IMPLEMENTATION_REALITY.md` | direct script generation claims |
| 2026-07-25 | Thumbnail Lab and Titles are local, deterministic, and traceable | approved | packaging analysis without automatic generation | `docs/ORIGINAL_VISION_TRACEABILITY.md` | auto-image generation as a default |
| 2026-07-27 | YouTube integration is read-only | approved | preserve account safety | `docs/COLLECTIVE_INTELLIGENCE_AND_PRIVACY.md`, platform docs | write scopes and automation |
| 2026-07-27 | TikTok integration is read-only | approved | preserve account safety | platform docs | write scopes and automation |
| 2026-07-29 | Creator Intelligence Studio is a strategic and creative copilot, not an automatic video editor | approved | prevent product drift | `docs/PROJECT_BIBLE.md` | editor-first positioning |
| 2026-07-29 | Approved AI providers in stage one are OpenAI and Anthropic only | approved | keep initial surface controlled | `docs/AI_ML_ARCHITECTURE.md` | third-provider normalization |
| 2026-07-29 | Provider choice must depend on roles, benchmarks, and replaceable catalogs | approved | avoid fixed-model coupling | `docs/AI_ML_ARCHITECTURE.md` | hard-coded model names |
| 2026-07-29 | Default MP4 retention is not allowed | approved | storage and privacy discipline | `docs/CREATOR_MEMORY_AND_LEARNING.md`, `docs/COLLECTIVE_INTELLIGENCE_AND_PRIVACY.md` | permanent duplicate media storage |
| 2026-07-29 | The next approved AI block is AI Runtime and Provider Orchestration Foundation | approved | roadmap order | `docs/AI_IMPLEMENTATION_ROADMAP.md`, `README.md` | skipping directly to later AI layers |

## Replaced Or Limited Decisions

| Decision Replaced | Replacement |
|---|---|
| Generic conceptual AI/ML architecture as top-level guidance | `docs/PROJECT_BIBLE.md` plus the catch-up decisions |
| Human-Guided Script Drafting as the immediate next AI step | AI Runtime and Provider Orchestration Foundation is now the next approved block |
| Any implicit assumption that infrastructure modules equal AI capability | current implementation reality and Project Bible classify them explicitly |

## Pending Decisions

- exact AI runtime contract and provider orchestration interface;
- secure credential storage implementation detail for provider APIs;
- benchmark protocol and scoring schema for provider competition;
- model registry schema and lifecycle;
- embedding model winner and vector-store backend selection;
- component manager packaging and download policy details;
- future collective intelligence server rules once enough data exists.

