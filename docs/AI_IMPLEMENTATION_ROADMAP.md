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

Component Manager and Local Transcription Foundation has now been implemented through v32-E as a foundation stack: v32-A, v32-B, v32-C, v32-D, and v32-E are already implemented.

- Objective: make local model/component installation and transcription onboarding explicit, guided, and reproducible.
- Dependencies: stable AI Runtime foundation, clear local component inventory, local-only install sources, and platform-specific policy.
- Current transcription state: local transcription already exists and remains implemented; it is now wrapped by a managed component foundation, a resumable artifact download boundary, and explicit runtime/model installers.
- Risks: drift into automatic media management, permanent media retention, hidden provider coupling, or implicit downloads.
- Decisions pending: model relocation policy depth, onboarding polish, and the exact user-facing installer copy.
- First contract to design: a guided runtime/model installer boundary that keeps non-technical users out of raw dependency details.

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
