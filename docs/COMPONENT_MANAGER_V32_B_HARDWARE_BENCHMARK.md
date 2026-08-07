# Component Manager v32-B Hardware Benchmark Foundation

## Scope Implemented

v32-B adds a small, explicit, local benchmark foundation for transcription runtime readiness.

Implemented behavior:

- CPU benchmark using a safe local fixture
- opt-in GPU benchmark using the same local fixture
- runtime verification through the existing faster-whisper/CTranslate2 boundary
- model loading from already installed local models only
- short inference measurement
- resource release after each run
- persistence of benchmark results into the existing v32 tables
- resolver integration so the latest functional benchmark can influence capability decisions
- read-only CLI inspection and explicit benchmark execution

This subphase does not implement:

- downloads
- installers
- FFmpeg installation
- CUDA installation
- driver installation
- relocation
- repair
- onboarding
- automatic benchmark execution at startup
- hidden network access

## Contract

The benchmark distinguishes:

- hardware detected
- runtime importable
- GPU reported
- GPU functionally tested
- model locally installed
- inference completed

It uses a small local fixture and records:

- requested profile
- requested device
- actual device
- runtime status
- model status
- selected compute type
- load duration
- inference duration
- total duration
- approximate RAM / VRAM samples when available
- transcript presence
- language detection when available
- safe error category and message
- readiness
- evidence references

## Status Model

Execution states:

- `pending`
- `checking_runtime`
- `checking_model`
- `loading_model`
- `preparing_fixture`
- `running_inference`
- `validating_result`
- `releasing_resources`
- `completed`
- `completed_with_warnings`
- `cancelled`
- `timed_out`
- `failed`

Readiness states:

- `ready`
- `ready_with_warnings`
- `degraded`
- `incompatible`
- `unavailable`
- `unknown`

## User-Facing Messages

Examples supported by the presenter:

- `Tu computadora está lista para transcribir.`
- `Falta instalar el modelo Equilibrado.`
- `Se detectó una GPU NVIDIA, pero todavía no se ha comprobado que funcione con el motor de transcripción.`
- `La prueba excedió el tiempo permitido.`

Technical details remain available in the JSON payload and the advanced UI.

## Persistence

Benchmark results are stored through the existing component-manager SQLite tables:

- `component_installations`
- `hardware_profiles`
- `transcription_runtime_checks`
- `component_events`

The benchmark is tagged with a dedicated `check_kind` in runtime-check metadata so the resolver can find the latest benchmark without creating a new schema branch.

## CLI

Read-only benchmark commands are available through the existing component CLI:

- `components benchmark --json`
- `components benchmark status --json`

The benchmark is explicit and never runs from bootstrap, capability inspection, or startup diagnostics.

## Validation

Validated locally with:

- `tests.test_component_manager_benchmark`
- `tests.test_component_manager_cli`
- `tests.test_component_manager_migration`
- `tests.test_component_manager_contracts`
- `tests.test_transcription_no_hidden_download`
- `tests.test_transcription_service`
- `tests.test_paths`
- `tests.test_bootstrap`
- `tests.test_ai_runtime_providers`

Representative AI Runtime GUI/orchestrator tests were also re-run to confirm v31 remained intact, but the full long suites exceeded the execution budget in this environment.

## Limitations

- no download manager
- no installation workflow
- no repair workflow
- no model movement workflow
- no GPU-wide performance certification
- no automatic benchmark scheduling

## Next Subphase

v32-C is now implemented as a managed FFmpeg boundary that preserves the existing local transcription flow and keeps benchmark resolution read-only.

The benchmark layer continues to rely on the central media-tool resolver, so managed FFmpeg can win by policy while external FFmpeg remains a read-only fallback.
