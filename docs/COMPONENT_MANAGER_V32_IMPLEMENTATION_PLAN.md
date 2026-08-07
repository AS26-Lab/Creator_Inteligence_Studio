# Component Manager v32 Implementation Plan

## Purpose

This plan breaks v32 into small, verifiable subphases. It is intentionally conservative so the repository can gain a managed component layer without destabilizing the already working transcription flow.

## Current Status

v32-A is implemented as a read-only foundation, v32-B is implemented as the local hardware/runtime benchmark foundation, v32-C is implemented as the managed FFmpeg boundary, and v32-D is implemented as the resumable download-manager foundation. The remaining subphases below stay valid and pending: runtime/model installer, relocation expansion, onboarding, and deeper GUI work.

## Phase Order

### v32-A - Schema and Catalog Foundation

Objective:

- define component catalog and install state contracts
- add versioned catalog and review metadata
- keep the current transcription tables untouched

Files:

- new component domain objects
- new catalog repository
- migration v32

Tests:

- catalog entry validation
- versioning and review status
- state machine transitions

Gate:

- catalog can be loaded and validated without downloading anything

Non-scope:

- actual component installation
- transcription behavior changes

Status:

- implemented in this branch as a foundation-only slice

### v32-B - Hardware Capability Inventory

Objective:

- distinguish detection from functional readiness
- inventory CPU/RAM/GPU/VRAM/runtime state

Files:

- hardware capability service
- benchmark data model
- runtime check repository

Tests:

- fake GPU
- CPU fallback
- runtime benchmark failure

Gate:

- hardware state can be explained in plain language and serialized safely

Non-scope:

- auto-install
- CUDA toolkit installation

Status:

- implemented in this branch as a small local benchmark foundation that certifies already-installed components without downloads

### v32-C - FFmpeg Managed Component

Objective:

- wrap FFmpeg and ffprobe as a managed local component
- preserve the current extraction workflow

Files:

- FFmpeg component adapter
- catalog entry for FFmpeg
- verification/health check logic

Tests:

- configured path
- PATH fallback
- missing binary
- version probe failure

Gate:

- the app can explain whether FFmpeg is ready and where it came from

Non-scope:

- audio algorithm changes

Status:

- implemented as a managed local package boundary with staging, health check, activation, repair, removal, and external fallback policy

### v32-D - Download Manager

Objective:

- make downloads resumable, pausable, and cancellable
- isolate partial state from final activation

Files:

- download manager
- partial download metadata
- downloader test server harness

Tests:

- Range resume
- checksum mismatch
- ETag change
- disk full
- cancel mid-download

Gate:

- partial downloads can be resumed or cleaned safely

Non-scope:

- model selection policy

Status:

- implemented as a resumable download-manager foundation with local/test sources only and no automatic installation

### v32-E - Runtime and Model Installation

Objective:

- manage transcription runtime and model components as explicit installs
- keep activation behind verification and a functional test

Files:

- runtime installer
- model installer
- verifier
- component location tracking

Tests:

- install
- verify
- repair
- relocate
- rollback

Gate:

- a component becomes active only after hash + verification + functional test

Non-scope:

- advanced diarization

### v32-F - Transcription Capability Resolver

Objective:

- centralize the decision of whether local transcription can run
- select profile/device deterministically

Files:

- resolver
- profile definition registry
- UI summary adapter

Tests:

- ready
- degraded
- incompatible
- limited mode

Gate:

- resolver never downloads anything and never mutates state

Non-scope:

- inference algorithm changes

### v32-G - GUI and Onboarding

Objective:

- add guided onboarding
- add the local components screen
- present technical details only in advanced mode

Files:

- onboarding view
- local components view
- view model additions
- navigation entry

Tests:

- onboarding copy
- recommended install path
- manual path
- limited mode path

Gate:

- a non-technical user can reach a safe local transcription path without reading internal jargon

Non-scope:

- full UI overhaul

### v32-H - Integration With Existing Transcription

Objective:

- plug the resolver into the current transcription entry points
- keep current service behavior where it is already stable

Files:

- transcription entry points
- workspace integration
- task center messages

Tests:

- current transcribe flow still works
- no hidden download after resolver says blocked
- cancellation still works

Gate:

- existing transcription flow continues to function with the new resolver boundary

Non-scope:

- AI Runtime changes

### v32-I - Recovery, Repair, Relocation

Objective:

- support restarting interrupted component installs
- support repair and relocation safely

Files:

- recovery hooks
- repair actions
- relocation logic
- cleanup routines

Tests:

- interrupted download recovery
- model moved to another drive
- stale partial cleanup

Gate:

- no stale lock or orphaned partial file remains after recovery

Non-scope:

- provider changes

### v32-J - Validation and Closure

Objective:

- verify all contracts in a small local suite
- document the new reality

Files:

- audit updates
- roadmap update if needed
- decision register entries if needed

Tests:

- component catalog
- download manager
- hardware check
- resolver
- transcription integration
- GUI onboarding

Gate:

- no hidden download, no silent fallback, no cross-creator mixing, no permanent MP4 retention

## Initial Test Matrix

| Suite | Purpose |
|---|---|
| component catalog tests | validate catalog parsing and review state |
| download state machine | validate pause/resume/cancel transitions |
| resumable download fake server | validate range handling |
| hash mismatch | validate safe rejection |
| disk full | validate preflight blocking |
| path permissions | validate move/install safety |
| install activation | validate hash + test + activation sequence |
| repair | validate repair workflow |
| relocation | validate component move workflow |
| hardware detection | validate inventory serialization |
| fake GPU | validate degraded/incompatible fallback |
| CPU fallback | validate minimum mode path |
| runtime benchmark | validate readiness gate |
| capability resolver | validate deterministic outputs |
| missing component UX | validate user-facing messages |
| onboarding GUI | validate guided flow |
| restart recovery | validate interrupted work recovery |
| transcription integration | validate current flow stays intact |
| temporary cleanup | validate partial file cleanup |
| no hidden download | validate resolver blocks before network |
| no network during capability check | validate offline-safe decisions |
| no data deletion | validate safe cleanup boundaries |
| AI Runtime regression | validate v31 remains untouched |

## Open Decisions Before Coding

- source of FFmpeg
- source of transcription models
- whether the installer is bundled or network-driven
- whether partial downloads expire automatically
- how much disk space to reserve for each profile
- which benchmarks count as ready vs degraded
- whether relocation is allowed across all supported drives

## First Implementation Prompt Recommendation

The first coding prompt should ask for:

1. component catalog domain and repository
2. hardware capability service
3. resolver interface
4. a fake-only test suite for catalog and resolver

That is the smallest safe slice that creates the v32 contract without changing transcription behavior yet.
