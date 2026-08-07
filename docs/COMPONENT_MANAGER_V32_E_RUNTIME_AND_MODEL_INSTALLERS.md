# Component Manager v32-E Runtime And Model Installers

## Purpose

v32-E adds explicit, local-only installation boundaries for the transcription runtime and transcription models.

The installer boundary accepts either:

- a local source explicitly supplied by the user or test harness;
- a `VerifiedComponentArtifact` produced by v32-D.

It does not download anything and it does not activate components before verification.

## Core Contract

`artifact/source -> staging -> validation -> health check -> activation -> persistence -> ready`

The download manager remains separate:

- v32-D produces a verified artifact
- v32-E consumes that artifact or a local source
- readiness still depends on installation plus health verification

v32-F closes the readiness layer on top of these installers and makes the resolver the canonical authority for whether transcription can begin.

## Managed Install Types

- `managed`
- `externally_detected`
- `legacy_cache`
- `missing`
- `invalid`
- `repair_required`
- `incompatible`
- `ready`

Legacy cache is preserved as a first-class read-only state so older local models can continue to work without re-downloading or automatic migration.

## Runtime Installer

The runtime installer is a controlled bundle installer for transcription runtime files.

Current boundary behavior:

- accepts a local directory or verified artifact
- stages into a controlled temporary directory
- validates required runtime packages
- performs an import-based health check in isolation
- activates atomically by moving the staged tree into the managed runtime location
- persists installation metadata and events
- cleans staging on success or failure

It does not:

- run `pip`
- call package managers
- mutate `PATH`
- fetch runtime bits from the network

## Model Installer

The model installer handles faster-whisper / CTranslate2 model bundles.

Current boundary behavior:

- accepts a local source or verified artifact
- validates the bundle structure with the existing model manager
- checks for required model files
- verifies bundle metadata when present
- performs a CPU health check
- activates atomically into the managed model location
- preserves the previous active model until the new install succeeds
- records managed vs legacy cache metadata

The installer intentionally does not start a download or call `snapshot_download`.

## Managed Location Policy

Managed runtime and model installs live under application-controlled roots derived from the existing paths policy.

They are not installed into:

- the repository
- `site-packages`
- `Program Files`
- a random working directory
- global `PATH`

## Archive Security

The installer reuses the secure archive extraction helpers introduced for the FFmpeg boundary.

The extraction boundary blocks:

- `../` traversal
- absolute paths
- drive paths
- dangerous symlinks
- oversized archives
- excessive file counts
- duplicate conflicting entries

## Legacy Cache Adoption

Existing local model caches can be detected and reused as legacy cache.

Behavior:

- detect local cache without downloading
- validate structure
- expose it to the resolver
- do not move it automatically
- do not delete it automatically
- do not force migration during startup

## Health Checks

Runtime health check:

- verifies the bundle is importable in an isolated path context
- confirms the expected runtime package can be loaded

Model health check:

- verifies the model bundle structure
- confirms the model can be loaded by the local engine boundary
- uses a CPU check by default
- does not require GPU health to pass during installation

## Transcription Capability Integration

The capability resolver now considers:

- managed ready
- legacy cache ready
- missing model/runtime
- invalid or incompatible install
- repair required

The resolver does not install or repair anything automatically.
v32-F extends that contract so the resolver also owns device selection, profile fallback, and the final `can_transcribe_now` decision.

## CLI

The CLI exposes explicit local-only commands:

- `components runtime status`
- `components runtime verify`
- `components runtime install-local`
- `components runtime install-artifact`
- `components runtime repair-local`
- `components runtime remove`
- `components model status`
- `components model verify`
- `components model install-local`
- `components model install-artifact`
- `components model repair-local`
- `components model remove`

## Events

The installer emits dedicated runtime/model install, health, activation, repair, removal, rollback, and legacy-cache detection events.

## Limitations

- no product download sources are enabled
- no internet fetch path is enabled
- no automatic model installation
- no automatic runtime installation
- no migration_33
- no pip-based runtime setup
- no GPU driver installation
- no PATH mutation
- v32-G later adds a guided onboarding shell that consumes this installer-ready foundation
