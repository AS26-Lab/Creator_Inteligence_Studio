# Component Manager v32-F Transcription Readiness

## Purpose

v32-F closes the local transcription readiness boundary.

`TranscriptionCapabilityResolver` is the canonical authority for readiness. It is deterministic, read-only, local-only, and side-effect free.

## Canonical Contract

The resolver answers:

- whether transcription can start now
- which profile is selected
- which profile is recommended
- which model path is resolved locally
- which runtime is selected
- which FFmpeg and FFprobe installs are selected
- whether the GPU is actually proven by benchmark evidence
- what is missing, corrupt, stale, or incompatible
- what fallback exists
- what user-facing actions should be offered

The hard gate is `can_transcribe_now`.

## Readiness States

Current readiness states:

- `ready`
- `ready_with_warnings`
- `degraded`
- `missing_components`
- `incompatible`
- `repair_required`
- `limited_mode`
- `unknown`

Examples:

- managed FFmpeg healthy, runtime healthy, model healthy, CPU ready -> `ready`
- GPU detected but not functionally proven -> `ready_with_warnings` when CPU is usable
- balanced model missing but fast available -> `degraded`
- model corrupt with no fallback -> `repair_required`
- runtime missing -> `missing_components`

## Evidence Precedence

The resolver prefers:

- managed healthy
- legacy or external validated
- detected but unverified
- missing

For GPU evidence:

- fresh successful benchmark
- stale successful benchmark
- reported but untested hardware
- benchmark failed
- no GPU

For model evidence:

- managed healthy
- legacy validated
- external validated
- partial
- corrupt
- missing

For FFmpeg:

- managed active healthy
- explicitly selected external healthy
- discovered external healthy
- unavailable

## Device Selection

`automatic` uses GPU only when there is fresh successful benchmark evidence.

- fresh successful GPU benchmark + supported profile -> GPU
- GPU reported but untested + CPU ready -> CPU with warning
- explicit GPU without proof -> no silent CPU fallback
- explicit CPU never upgrades silently to GPU

## Profile Fallback

Fallback is read-only:

- `balanced` missing + `fast` ready -> `fast`
- `maximum_quality` missing + `balanced` ready -> `balanced`
- `fast` missing -> no lower fallback
- `custom` -> no automatic fallback

The resolver recommends a fallback but does not mutate user preferences.

## Model Mapping

Profile mapping remains centralized in the transcription profile catalog.

Each profile resolves to:

- preferred model component
- allowed fallback models
- CPU compute policy
- GPU compute policy
- hardware requirements
- disk expectations
- evidence requirements

## Runtime Resolution

The resolver distinguishes:

- application-bundled runtime
- managed runtime
- external or legacy runtime when present

Resolution is local-only and does not mutate `sys.path` permanently.

## Model Path Resolution

The resolver returns an explicit local path or reference.

`TranscriptionService` and `FasterWhisperEngine` consume that path directly.

There is no implicit model discovery or hidden download during normal transcription.

## FFmpeg Resolution

FFmpeg and FFprobe are resolved through the central media-tool boundary.

The resolver records:

- source: managed or external
- health
- selected binary references

No PATH-global mutation is used to satisfy readiness.

## Disk Readiness

The resolver separates:

- disk required for current transcription
- disk required for future installation

Existing local transcription can remain ready even if there is not enough space to install a different model.

## Legacy Handling

Legacy cache models remain usable when validated.

Behavior:

- detect
- validate
- reuse
- read-only
- do not delete automatically
- do not move automatically

## Repair States

Managed components can be reported as repair required.

External and legacy components are not repaired automatically.

## Suggested Actions

Structured suggested actions include:

- run GPU benchmark
- install component
- repair component
- choose profile
- use CPU
- use GPU
- verify component
- relocate component
- free disk space
- continue limited
- retry health check

The resolver does not execute these actions.

## User-Friendly Presenter

Presentation is separate from resolution.

Examples:

- `Tu computadora esta lista para transcribir.`
- `Puedes transcribir ahora usando el procesador.`
- `El modelo Equilibrado no esta instalado, pero puedes comenzar con el perfil Rapido.`
- `Falta instalar un modelo de transcripcion.`

## TranscriptionService Hard Gate

`TranscriptionService` resolves capability first.

If `can_transcribe_now` is false:

- no FFmpeg startup
- no model load
- no hidden download
- no automatic benchmark

If `can_transcribe_now` is true:

- the resolved profile
- resolved model path
- resolved runtime
- resolved FFmpeg
- selected device
- selected compute type

must be used as the execution plan snapshot.

## Component-Changed Protection

If the resolved model or media tooling disappears before transcription starts, the service raises a component-changed error instead of silently resolving again.

## CLI

Read-only commands:

- `components capability`
- `components capability-matrix`
- `components transcription-plan`

These commands do not install or download anything.

## No Network / No Mutation

v32-F is read-only.

It does not:

- use network
- download components
- install components
- mutate preferences
- run automatic benchmarks

## Limitations

- GPU readiness still depends on benchmark evidence
- onboarding is not built yet
- no production download sources are enabled
- no migration_33 exists
- no automatic component installation is enabled

