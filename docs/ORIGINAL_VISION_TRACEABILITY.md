# Original Vision Traceability

## Purpose

This document maps original product intent to the current repository state. It is a traceability record, not a rewrite of the vision.

## Traceability Table

| Original Requirement | Current Module / Doc | State | Gap | Current Decision | Roadmap |
|---|---|---|---|---|---|
| Creator strategic and creative copilot | `docs/PROJECT_BIBLE.md` | partial | no AI runtime yet | keep as north star | AI Runtime and Provider Orchestration Foundation |
| Strong script capability | `docs/SCRIPT_OUTLINE_AND_PRODUCTION_PREPARATION_FOUNDATION.md` | implemented as preparation | no human-guided drafting yet | outlines and prep are the current script-adjacent base | Creator Voice Workbench, then scripting loop |
| Voice, tone, rhythm, humor, narrative understanding | `docs/CREATOR_MEMORY.md`, `docs/CREATOR_LANGUAGE_ANALYSIS.md` | infrastructure_only | semantic understanding missing | preserve local creator profiles and rules | Creator Corpus, Semantic Retrieval, Feedback Learning |
| No automatic video editor | `docs/PROJECT_BIBLE.md` | implemented as a non-goal | none | keep paused | remains out of scope |
| Strategic intelligence with analytics and experiments | `docs/ANALYTICS_LAB.md`, `docs/EXPERIMENTS_AND_LEARNING.md` | implemented structurally | no AI layer on top | retain evidence-led foundations | IA in existing modules |
| No viral promise | `docs/PROJECT_BIBLE.md` | implemented as policy | none | hard rule | all future AI stages |
| Fact / inference / hypothesis separation | `docs/PROJECT_BIBLE.md` | implemented as policy | enforcement layer still thin | keep explicit labels | provider orchestration and evaluation |
| Creator decision authority | UI, workflow docs, approval flows | implemented structurally | AI decisions not yet present | human approvals remain final | all future AI stages |
| Privacy, traceability, cost, human control | `docs/ACCOUNT_SAFETY.md`, `docs/COST_POLICY.md`, this Project Bible | partial | AI-specific policy still needed | document provider and corpus rules | AI architecture + privacy docs |
| Local-first, but quality over dogma | `README.md`, `docs/AI_ML_ARCHITECTURE.md` | implemented as direction | needs AI-specific contract | hybrid architecture is approved | AI Runtime and Provider Orchestration Foundation |
| Safe provider execution through a central AI runtime | `docs/AI_RUNTIME_AND_PROVIDER_ORCHESTRATION_FOUNDATION.md` | implemented | only provider diagnostics are enabled in v31 | keep modules off direct provider calls | Component Manager and Local Transcription Foundation |

## Requirement Groups

### Already covered by v30 infrastructure

- local creator/project/video management
- inspection and preparation
- transcription base
- analysis base
- packaging base
- planning base
- briefs and production preparation

### Audited capability classes

| Capability | Current classification | Evidence anchor | Resolution |
|---|---|---|---|
| Transcripcion local | `implemented` | `TranscriptionService.transcribe_video` and `FasterWhisperEngine` | Keep as a real local capability and reuse it for future AI fallback paths. |
| Analisis acustico | `deterministic` | `AcousticAnalysisService.analyze_acoustics` | Document as technical signal processing, not semantic understanding. |
| Analisis visual | `deterministic` | `VisualAnalysisService.analyze_visuals` | Document as technical signal processing with keyframes and scene heuristics. |
| Analisis multimodal | `deterministic` | `MultimodalAnalysisService.analyze_multimodal` | Document as signal fusion and candidate generation only. |
| Ranking de clips | `deterministic` | `ClipRankingService.rank_clip_candidates` | Document as heuristic scoring and human-review workflow. |
| Render local de clips | `implemented` | `ClipRenderService.render_candidate` | Keep as reusable rendering utility, not as automatic editing intelligence. |
| Subtitulos | `implemented` | `SubtitleService.generate_video_subtitles` and related flows | Keep as editorial subtitle workflow built on transcription. |

### Explicitly paused

- automatic video editing
- automatic clipping
- project auto-creation in NLEs
- foundation model training

### Requires the next AI blocks

- provider orchestration
- semantic retrieval
- corpus learning
- creator voice workbench
- AI-enabled module upgrades

## Discrepancy Note

Older phase documentation treated some deterministic foundations as if they were near intelligence. The current resolution is to keep those foundations, but classify them correctly and prevent scope drift.
