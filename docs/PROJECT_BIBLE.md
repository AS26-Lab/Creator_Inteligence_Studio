# Project Bible

## Purpose

This document is the top-level authority for Creator Intelligence Studio. It defines the product identity, non-goals, architectural direction, decision rules, and the relationship between the canonical documents in this repository.

## Authority Hierarchy

If there is a contradiction, apply this order:

1. `docs/PROJECT_BIBLE.md`
2. The original vision documents and the approved IA/ML catch-up PDF stored under `docs/reference/`
3. `docs/AI_ML_ARCHITECTURE.md`
4. Specialized docs for memory, components, privacy, and roadmap
5. The real state of the code and migrations
6. Documentation from earlier phases
7. Comments, old prompts, and unapproved ideas

The latest approved canonical decision wins when two sources conflict. The conflict must be recorded, not silently corrected.

The approved catch-up PDF at `docs/reference/Creator_Intelligence_Studio_Catch_Up_IA_ML_2026-07-29.pdf` is a canonical source for the AI catch-up architecture. It remains subordinate to this Project Bible whenever a later approved decision narrows or replaces it.

## Product Vision

Creator Intelligence Studio is a strategic and creative copilot for creators.

It is not an automatic video editor and it must not be positioned as one.

The product must progressively understand:

- voice;
- tone;
- vocabulary;
- humor;
- rhythm;
- narrative structure;
- hooks;
- closers;
- limits;
- platform-specific differences.

Authentic scripts are a core capability and a top priority.

The product must support strategic intelligence based on:

- analytics;
- audience;
- market;
- trends;
- experiments;
- history;
- real outcomes.

The product must never promise virality.

The product must separate:

- fact;
- inference;
- hypothesis.

The creator always keeps the final decision.

Privacy, traceability, cost, and human control are structural requirements.

## UX Principle

Creator Intelligence Studio is primarily for creators and other non-technical users.

Default flows must be guided, safe, and understandable in plain language. Technical controls belong behind an explicit advanced mode. A capability is not complete until it is discoverable, understandable, and usable in the real product.

## Canonical Pillars

1. Strategic and creative copilot for creators.
2. Strong script capability, but not automatic video editing.
3. Progressive creator understanding.
4. Strategic intelligence grounded in evidence.
5. Human decision authority.
6. Privacy and creator isolation.
7. Traceability and reproducibility.
8. Replaceable AI roles instead of fixed vendor names.
9. Local-first processing where reasonable.
10. Quality and speed over ideological purity.
11. Authentic creator evidence must stay separate from AI-derived content and from structured confirmed preferences.
12. Creator Voice profiles must remain descriptive and diagnostic until a later approved phase allows any workflow application.

## Approved Scope

Included in product scope:

- ideation;
- opportunity analysis;
- planning;
- strategy;
- briefs;
- scripts;
- creator corpus identity, provenance, ingestion, versioning, and lifecycle;
- creator voice evidence selection and diagnostics;
- creator voice profile synthesis for diagnostics;
- creator voice guidance preview for diagnostics only;
- outlines;
- hooks;
- titles;
- thumbnail concepts;
- copy;
- descriptions;
- captions;
- hashtags;
- teasers;
- analysis of already edited long videos;
- analysis of already edited short videos;
- timestamps;
- candidate clips;
- explanations for why a fragment may work;
- manual cutting or adaptation recommendations;
- per-platform packages;
- scheduling;
- audience-based timing recommendations;
- publication preparation;
- assisted or automatic publication with approval;
- post-publication analytics;
- post mortem;
- continuous learning.

## Out Of Scope For The Current Priority

The following remain paused until a later approved phase:

- physical video file editing;
- automatic clip cutting;
- scene assembly;
- transitions;
- color correction;
- audio mixing;
- effects;
- rendering the final file;
- automatic Premiere, Resolve, or Final Cut project creation;
- camera or hardware control;
- training a foundation model from scratch.

These may remain as future ideas, but they are not part of the current priority and must stay explicitly paused.

## Canonical Product Principles

1. Avoid generic voice.
2. Avoid artificial tone.
3. Avoid AI-sounding phrases.
4. Avoid universal templates.
5. Avoid imitation of other creators.
6. Avoid exaggerated claims not aligned with creator identity.
7. Use analytics and outcomes as evidence, not as decoration.
8. Treat every meaningful output as creator-specific.
9. Keep privacy and creator isolation explicit.
10. Record provenance and decision history.

## Current Approved Architecture Direction

The initial AI stage is hybrid:

- local core;
- selective APIs;
- only two external providers at the start: OpenAI and Anthropic;
- no third normal provider in the first stage;
- future local models remain possible;
- local processing stays preferred when reasonable;
- quality and speed take precedence over dogma.

The provider strategy is role-based, not model-name-based.

## Decision Rules

Before accepting a new feature, verify:

- it fits the approved scope;
- it does not imply automatic video editing;
- it does not require a new provider by default;
- it does not collapse deterministic infrastructure into claimed AI;
- it does not mix creators;
- it does not create permanent MP4 retention by default;
- it does not bypass human decision authority;
- it has a clear privacy and cost model;
- it has a documented rollback path when relevant;
- it can be traced back to an approved source.

If a feature is ambiguous, classify it as paused until the next approved contract exists.

## Relationship To Subordinate Documents

- `docs/AI_ML_ARCHITECTURE.md` defines the AI/ML operating model.
- `docs/reference/README.md` indexes the approved catch-up PDF reference.
- `docs/CREATOR_MEMORY_AND_LEARNING.md` defines memory, corpus, retrieval, and learning.
- `docs/LOCAL_COMPONENTS_AND_TRANSCRIPTION.md` defines local installation, FFmpeg, transcription, and onboarding.
- `docs/COLLECTIVE_INTELLIGENCE_AND_PRIVACY.md` defines collective sharing and privacy.
- `docs/AI_IMPLEMENTATION_ROADMAP.md` defines the order and exit gates for AI work.
- `docs/CURRENT_IMPLEMENTATION_REALITY.md` describes the real state of the repository through the current inspected slice.
- `docs/ORIGINAL_VISION_TRACEABILITY.md` maps the original vision to the current codebase.
- `docs/DECISION_REGISTER.md` keeps the canonical decisions and replacements.

## Known Discrepancies And Resolutions

- The repository already contains deterministic, structural, and workflow infrastructure for many future AI features. Those modules are not equivalent to creative intelligence.
- The older `docs/AI_ML_ARCHITECTURE.md` was conceptual. It is now subordinate to this Project Bible and to the catch-up decisions.
- `Human-Guided Script Drafting Foundation` is still not started. The next approved block is `AI Runtime and Provider Orchestration Foundation`, but it is not implemented yet.
- The approved IA/ML catch-up PDF is a canonical reference, but the workspace may not always contain a local copy. If it is missing, the repository must keep the expected path documented and the file must be copied in without regeneration.
