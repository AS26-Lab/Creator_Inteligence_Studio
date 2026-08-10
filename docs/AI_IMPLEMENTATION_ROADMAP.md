# AI Implementation Roadmap

## Purpose

This roadmap fixes the mandatory order for AI work. It prevents the project from drifting into infrastructure-heavy work without real intelligence.

## Mandatory Order

1. AI Runtime and Provider Orchestration Foundation
2. Component Manager and Local Transcription Foundation
3. Creator Corpus Foundation
4. Semantic Retrieval Foundation
5. Feedback Learning Foundation
6. Creator Voice Workbench
7. IA in existing modules
8. Scripts and full creative loop
9. Multimodal analysis and assisted publication

The collective server and predictive ML come later, once there are enough users and enough data.

## Next Handoff

Component Manager and Local Transcription Foundation now has v32-A through v32-H implemented as a coherent stack: catalog, benchmark, managed FFmpeg, resumable downloads, explicit runtime/model installers, canonical readiness, guided local-components UI, and explicit local actions with task lifecycle wiring.

- Objective: keep local model/component installation and transcription readiness explicit, guided, and reproducible.
- Dependencies: stable AI Runtime foundation, clear local component inventory, local-only install sources, and platform-specific policy.
- Current transcription state: local transcription already exists and remains implemented; it is now wrapped by managed component installers, a canonical readiness resolver, and explicit UI actions.
- Risks: drift into automatic media management, permanent media retention, hidden provider coupling, or implicit downloads.
- Decisions pending: onboarding polish and exact copy refinements for action confirmations and task-center phrasing.
- First contract for the next phase: recovery and repair polish for interrupted local tasks without changing the canonical resolver. v32-I now covers the operation recovery hardening slice for local component actions.

## Stage Gates

Every stage must define:

- entry conditions;
- exit criteria;
- quality gates;
- privacy checks;
- cost checks;
- rollback or fallback behavior;
- what remains paused.

## Explicitly Paused Areas

The following stay paused until approved by a later contract:

- automatic video editing;
- automatic clipping;
- scene assembly;
- transitions;
- color correction;
- audio mixing;
- effects rendering;
- final file production;
- automatic project creation for Premiere, Resolve, or Final Cut;
- camera or hardware control;
- foundation model training.

## Anti-Drift Rules

- Do not implement later stages before earlier contracts exist.
- Do not promote deterministic rules to creative intelligence.
- Do not replace human evaluation with a model opinion.
- Do not hide provider swaps.
- Do not allow silent behavior changes on important tasks.
- Do not mix creators.
- Do not create permanent MP4 retention by default.
- Do not postpone basic discoverability or usability until the final UI/UX overhaul; fix navigation traps and incomprehensible flows while the feature is being built.

## Roadmap Linkage

- `docs/PROJECT_BIBLE.md` defines the canon.
- `docs/AI_ML_ARCHITECTURE.md` defines the operating model.
- `docs/CREATOR_MEMORY_AND_LEARNING.md` defines memory and learning.
- `docs/LOCAL_COMPONENTS_AND_TRANSCRIPTION.md` defines local component onboarding.
- `docs/COLLECTIVE_INTELLIGENCE_AND_PRIVACY.md` defines data sharing and privacy.
- `docs/CURRENT_IMPLEMENTATION_REALITY.md` records the actual state before AI work starts.

## v32-G

Guided local components UI is the next visible layer after the canonical resolver closure.

It should expose:

- local readiness summary
- recommended profile
- component cards
- structured actions
- onboarding shell

It should not introduce:

- productive downloads
- automatic installs
- automatic benchmark startup
- duplicated readiness logic

## v32-H

Explicit local component actions now sit on top of the guided UI.

It should expose:

- explicit verify / install / repair / remove flows
- local file and folder picker confirmations
- task lifecycle feedback in Task Center
- safe backend revalidation before mutation

It should not introduce:

- productive internet sources
- automatic install on view open
- automatic benchmark startup
- duplicate component truth in widgets

## v32-I

Component operation lifecycle hardening adds startup reconciliation, cooperative cancellation, and bounded staging cleanup.

It should not introduce:

- automatic resume of interrupted mutations
- unbounded cleanup outside managed roots
- a new migration

## v32-J

Integration validation confirms that `v32-A` through `v32-I` work together as one local component foundation.

It should not introduce:

- productive internet component sources
- real FFmpeg downloads
- real model downloads
- `migration_33`

## v32-K

Qualified FFmpeg product source for Windows x86_64.

It should:

- pin one exact BtbN artifact in the component catalog
- keep download != install
- verify SHA-256 before install
- preserve existing v32 database compatibility

It should not:

- enable runtime or model productive sources
- allow user-entered source URLs
- use a floating `latest` URL as the catalog identity
- introduce `migration_33`
