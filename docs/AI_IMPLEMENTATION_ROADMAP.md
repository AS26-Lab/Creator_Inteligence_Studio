# AI Implementation Roadmap

## Purpose

This roadmap fixes the mandatory order for AI work. It prevents the project from drifting into infrastructure-heavy work without real intelligence.

## Mandatory Order

1. AI Runtime and Provider Orchestration Foundation
2. Component Manager and Local Transcription Foundation
3. Creator Corpus Foundation
4. Explicit Local Retrieval Foundation
5. Feedback Learning Foundation
6. Creator Voice Workbench
7. IA in existing modules
8. Scripts and full creative loop
9. Multimodal analysis and assisted publication

The collective server and predictive ML come later, once there are enough users and enough data.

## v35 Integrations

The next approved major block after the Creator Voice workbench is Integrations, and the approved connector order is locked by the decision register.

- v35-A establishes provider-neutral connector contracts, creator-owned accounts, secure credential references, and offline fake-connector validation
- it does not enable real social/video/storage provider publishing flows
- it does not change Creator Voice application behavior
- it does not alter the AI runtime or retrieval architecture

- v35-B adds the first real connector, YouTube, as a read-first provider adapter for account identity, video inventory, metadata, and analytics
- it keeps write/publish/update/delete/comment operations disabled
- it uses official OAuth and least-privilege read scopes only
- the distributed Windows bundle materializes the public OAuth client identity into bundled configuration at build time; developer JSON is bootstrap-only and not a runtime dependency
- it does not auto-ingest YouTube content into Creator Corpus or Creator Voice

- v35-C adds Instagram Read-Only as the current approved connector, keeps the phase read-only, and uses the AS26 OAuth broker for the sensitive Instagram token exchange boundary
- v35-D adds TikTok Read-Only as the next approved connector and keeps the phase read-only
- v35-E consolidates YouTube, Instagram, TikTok, and manual sources behind the shared integration layer without changing native connector semantics
- v36 introduces Market / Trend Intelligence Foundation after the connector block is complete

Approved v35-C slices:

- v35-C1 Instagram OAuth Broker Foundation
- v35-C2 Instagram Account/Profile Read
- v35-C3 Owned Media Listing + Metadata
- v35-C4 Account + Media Insights
- v35-C5 Real-Account Certification + Packaging/Recovery Closure

The integration pillar now has a provider-neutral foundation and one approved real read-only connector.

Future connector phases must still follow this approved roadmap and product-value ordering unless the user explicitly approves a revision.

## Future Creator Voice / Script Intelligence Differentiator

Advanced per-creator linguistic modeling is an approved future capability for the Creator Voice and Script Intelligence areas. It is deferred until a later phase and must not be implemented during v35-A.

- The model must remain creator-specific, never universal.
- There is no universal blacklist of "AI words" or generic bad-word lists for the feature.
- The system may use positive and conservative negative linguistic evidence only after enough authentic creator evidence exists.
- Future analysis may compare authentic creator language against AI-generated language to find explainable mismatches, but it is not a universal AI detector.
- Creator Voice Training or Linguistic Calibration may later accept creator-authored exercises as durable evidence, independent of a single LLM conversation.
- Future ingestion must include approved document and short-form text sources such as PDF, DOCX, TXT, Markdown, scripts, titles, hooks, captions, CTAs, posts, and emoji-containing text.
- Language authenticity and performance remain separate signals.
- All linguistic state, samples, and calibration responses remain creator-scoped.
- Sensitive inference and personality profiling remain out of scope.

## Next Handoff

Component Manager and Local Transcription Foundation now has v32-A through v32-H implemented as a coherent stack: catalog, benchmark, managed FFmpeg, resumable downloads, explicit runtime/model installers, canonical readiness, guided local-components UI, and explicit local actions with task lifecycle wiring.

- Objective: keep local model/component installation and transcription readiness explicit, guided, and reproducible.
- Dependencies: stable AI Runtime foundation, clear local component inventory, local-only install sources, and platform-specific policy.
- Current transcription state: local transcription already exists and remains implemented; it is now wrapped by managed component installers, a canonical readiness resolver, and explicit UI actions.
- Risks: drift into automatic media management, permanent media retention, hidden provider coupling, or implicit downloads.
- Decisions pending: onboarding polish and exact copy refinements for action confirmations and task-center phrasing.
- First contract for the next phase: recovery and repair polish for interrupted local tasks without changing the canonical resolver. v32-I now covers the operation recovery hardening slice for local component actions.

v32-L hardens the runtime distribution boundary and downloader resource cleanup.

- runtime distribution is now recorded explicitly as application-bundled, managed, or legacy-external rather than implied by import success alone
- the current repository still does not prove a self-contained bundled Windows app runtime with an embedded interpreter
- HTTP/TLS response ownership is now deterministic so SSL sockets close on success, failure, pause, cancel, redirect, and retry
- runtime and model productive sources remain disabled

v33-A opens the Creator Corpus foundation as a local-only storage and ingestion layer.

- creator-scoped corpus identity, provenance, deduplication, versioning, and lifecycle are now implemented
- transcription-derived documents can be ingested into the corpus without introducing retrieval or embeddings
- semantic retrieval remains paused for later phases; feedback learning is now implemented as a local creator-scoped foundation

v33-B turns the corpus foundation into a deterministic ingestion and normalization pipeline.

- raw and normalized content are stored separately
- authorship class and eligibility signals are explicit
- repeated ingestion is idempotent
- creator isolation is enforced on corpus mutation
- retrieval remains paused; v33-B does not implement embeddings or ranking

v33-C adds explicit local retrieval without semantic embeddings.

- retrieval queries require `creator_id`
- default results exclude archived and non-eligible corpus content
- document, version, and segment hits are explainable and paginated
- the retrieval index is derived data and can be rebuilt from canonical corpus tables
- embeddings, vector search, and LLM retrieval remain paused

v33-D adds creator context assembly and prompt grounding.

- retrieval results are converted into structured context bundles
- corpus text remains untrusted data during prompt rendering
- context budgets, provenance, authorship, and categories are explicit
- the first safe integration point is the content brief snapshot workflow

v33-E validates grounded AI workflows and centralizes context policy.

- workflow-specific policies classify when grounding is required, preferred, optional, or forbidden
- content brief, production preparation, and strategic planning now use the shared context boundary
- provider diagnostics remain context free
- corpus context remains separate from conversation history and primary user artifacts
- empty corpus and context-off modes remain valid for the approved workflows

v33-F evaluates local semantic/hybrid retrieval without replacing lexical retrieval.

- the lexical retrieval baseline remains the production truth
- a local multilingual ONNX candidate can improve paraphrase-style retrieval in evaluation
- the semantic layer stays evaluation-only until a product adoption decision is approved
- no external embedding API or vector database is introduced

v33-G adds the optional product lifecycle for the semantic layer.

- the semantic embedding model is managed and versioned as a local component
- the universal CPU artifact is selected as the default product asset
- the AVX512/VNNI artifact remains an accelerator-specific variant
- the derived semantic index is rebuildable and creator-scoped
- lexical fallback remains first-class
- hybrid retrieval is only used when the semantic capability is ready
- no external vector database, Supabase integration, or remote embedding API is introduced

v33-H adds the local creator feedback and learning-signals foundation.

- feedback is recorded as canonical local events
- learning signals are derived conservatively from those events
- repeated evidence can promote observed signals to candidate signals
- confirmed preferences are not automatic
- packaged validation surfaces may invoke the canonical services for frozen checks, but they are diagnostic/developer boundaries rather than normal-user product flows
- prompt mutation, retrieval reranking, voice learning, and fine-tuning remain paused

v33-I adds deterministic preference synthesis and human confirmation.

- repeated learning signals can become reviewable preference candidates
- confirm, edit-and-confirm, dismiss, deactivate, and reactivate are explicit user decisions
- confirmed preferences stay separate from feedback events and derived signals
- no confirmed preference is automatically applied to prompts, retrieval, or creator voice

v33-J adds bounded confirmed-preference application.

- only active confirmed preferences may influence grounded workflows
- current user and project / artifact instructions outrank stored preferences
- preferences are rendered into a bounded application bundle, not injected as arbitrary prompt text
- content brief and production preparation are the first wired workflows
- retrieval, semantic indexing, and Creator Voice remain unchanged
- no candidate or dismissed preference can apply

v34-A begins Creator Voice as evidence foundation only.

- creator voice evidence is selected from authentic creator evidence, not inferred by an LLM
- AI-generated and AI-rewritten content remain excluded by default
- creator-edited AI content is handled conservatively as evidence, not as pure creator-original truth
- confirmed preferences remain separate structured guidance and are not textual style samples
- snapshots are deterministic, bounded, rebuildable, and creator-scoped
- no style prompt synthesis, no embeddings, no prompt application, and no retrieval mutation are introduced

v34-B adds Creator Voice profile synthesis on top of the evidence snapshot.

- structured profile features are derived deterministically from the snapshot
- no personality guessing, no sensitive inference, and no prompt application are introduced
- spoken and written patterns remain distinct
- confirmed preferences remain separate from text-derived features
- profiles are diagnostic and explainable, not model-facing style prompts

v34-C adds Creator Voice guidance consumption as a diagnostic preview boundary.

- guidance is derived from the profile only, not raw corpus text
- higher-precedence user, project, and confirmed-preference instructions outrank Creator Voice
- normal workflow prompts remain unchanged
- the preview surface is deterministic, bounded, and offline

v34-D adds a controlled Creator Voice workflow application boundary.

- workflow integration remains shadow-first for comparison and observability
- real application is gated to approved workflows and remains subordinate to explicit instructions and confirmed preferences
- the final request only changes when the application boundary is explicitly enabled
- no global prompt injection is introduced

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
- foundation model training;
- automatic application of learned preferences to prompts or retrieval.
- automatic application of confirmed preferences to prompts, retrieval, or creator voice.

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

## v32-M

Windows application packaging foundation.

It should:

- use PyInstaller `onedir` as the single packaging strategy
- generate a deterministic runtime manifest
- resolve a bundle root from the executable when frozen
- redirect writable runtime state to an app-data root

It should not:

- claim a proven distributable bundle without a real build
- bundle Whisper models
- bundle FFmpeg product sources
- add a second packaging stack

## v32-N

Windows application packaging is now real-call validated on the current test machine.

It should:

- keep the bundle boundary explicit
- keep models separate
- keep FFmpeg separate

## v32-O

The first productive transcription model source is now the next narrow follow-up inside the local components stack.

It should:

- qualify exactly one transcription model source
- pin exact upstream revision and file manifest
- keep download and install separate
- persist verified artifacts for offline rehydration

It should not:

- enable multiple model sources
- call `snapshot_download()`
- allow floating source identities
- enable remote transcription

It should not:

- claim proof for all Windows machines from one test host
