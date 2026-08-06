# Component Manager v32-A Foundation

## Scope Implemented

This branch implements the read-only foundation for the approved v32 Component Manager work:

- versioned component catalog
- local installation inventory
- lightweight hardware inventory
- versioned transcription profiles
- deterministic transcription capability resolver
- no hidden download during capability checks
- read-only CLI inspection

This subphase does not implement:

- download manager
- pause/resume/cancel download flow
- installation or repair
- relocation
- onboarding UI
- GPU benchmark gate
- FFmpeg installation
- CUDA installation
- driver management

## Implemented Contracts

### Migration 32

- `component_catalog`
- `component_installations`
- `hardware_profiles`
- `transcription_profiles`
- `transcription_runtime_checks`
- `component_events`

The migration is idempotent and seeds the current approved catalog and transcription profiles.

### Component Catalog

Seeded entries include:

- `ffmpeg`
- `ffprobe`
- `transcription-runtime.faster-whisper`
- `transcription-runtime.ctranslate2`
- `transcription-model.base`
- `transcription-model.small`
- `transcription-model.medium`
- `transcription-model.large-v3-turbo`
- `transcription-model.large-v3`

### Transcription Profiles

Seeded profiles include:

- `fast`
- `balanced`
- `maximum_quality`
- `custom`

`balanced` remains the default visible profile.

### Hardware Inventory

The hardware service records:

- OS and architecture
- CPU logical count
- RAM totals when safely readable
- GPU detection status
- reported CUDA state
- CTranslate2 CUDA state
- free space for data, models, and temp volumes

It does not mark GPU readiness without a real transcription benchmark.

### Transcription Capability Resolver

The resolver is deterministic and read-only. It reports:

- readiness
- recommended profile
- selected profile
- model and runtime status
- missing components
- warnings
- blocking reasons
- suggested actions

It never downloads and never mutates state.

### Hidden Download Protection

`TranscriptionService` now uses explicit model inspection for missing models and returns a friendly blocked result instead of starting a hidden download.

## CLI

Read-only inspection is available through:

- `components status --json`
- `components capability --json`

These commands expose catalog, hardware, capability, and presentation summaries without installation or network access.

## Evidence

Validated locally with:

- `tests.test_component_manager_migration`
- `tests.test_component_manager_contracts`
- `tests.test_component_manager_cli`
- `tests.test_transcription_no_hidden_download`
- `tests.test_transcription_service`
- `tests.test_paths`
- `tests.test_bootstrap`

The longer AI Runtime suites were attempted separately; the combined discovery run exceeded the execution timeout, but no code in v32-A changes AI Runtime v31 behavior.

## Limitations

- no installer
- no downloader
- no relocation
- no benchmark gate
- no onboarding screen
- no GPU certification

## Next Subphase

v32-B should add the hardware benchmark and download/install boundaries, using this foundation as the contract layer.
