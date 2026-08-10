# Local Components And Transcription

## Purpose

This document defines the local component strategy, installation assumptions, and transcription baseline.

## Component Manager

The user does not install Python manually, use `pip`, or download models by hand.

The application should manage components when it is legally and technically possible.

Required behavior:

- versioned components;
- hashes;
- licenses;
- resumable downloads;
- rollback;
- repair;
- folder relocation;
- CPU support;
- NVIDIA acceleration when compatible;
- built-in FFmpeg distribution with reviewed version and license;
- large models downloaded from inside the application.

v32-D and v32-E split that idea into explicit boundaries:

- v32-D downloads verified artifacts only;
- v32-E installs runtime and model bundles only from local sources or verified artifacts;
- neither phase installs automatically as a side effect of detection.

## Onboarding

The base app must not pretend to be fully configured.

First run should include:

- setup assistant;
- install recommended button;
- clearly marked limited mode;
- per-component explanations for what it enables and blocks;
- size, location, available space, estimated time, and status;
- visible dashboard warnings;
- blocked functions that offer to install the missing component;
- `Settings -> Local Components`.

## Transcription Stack

Approved candidate stack:

- `faster-whisper`;
- `large-v3-turbo` for balanced mode;
- `large-v3` for maximum quality and doubtful segments;
- CPU INT8;
- GPU FP16 or INT8-FP16 depending on hardware;
- OpenAI as an authorized remote fallback;
- optional diarization.

## Modes

- fast;
- balanced, default;
- maximum quality.

Target behavior for a 10 minute video:

- fast: about 2 to 5 minutes;
- balanced: about 5 to 10 minutes;
- maximum quality: about 10 to 20 minutes;
- several hours is not commercially acceptable.

Use selective reprocessing instead of retranscribing everything.

## Benchmark Requirements

Benchmark with:

- Mexican Spanish;
- idioms;
- profanity;
- gaming speech;
- proper names;
- music;
- multiple voices;
- personal glossary;
- doubtful segments;
- hallucination detection;
- per-segment confidence.

The benchmark must use real CUDA performance, not only `nvidia-smi`.

## Existing Implementation Reality

The repository already includes transcription commands, model status, download, verification, export, and delete flows. The component manager now adds explicit runtime and model installers, managed-versus-legacy cache detection, and artifact handoff without hidden downloads. That is an operational foundation, but not yet the AI catch-up layer.

## v32-J Integration Validation

The local components foundation is now integration-validated as a coherent system.

Validated behavior includes:

- resolver-driven readiness presentation
- guided onboarding and limited mode
- explicit local component actions
- interruption and recovery handling
- Task Center consistency
- migration ceiling `v32`

Productive remote component sources remain disabled.

## v32-K Productive FFmpeg Source

The local components screen may now offer `Descargar componente multimedia` for the approved FFmpeg source only when the catalog, platform, and architecture checks pass.

The normal flow remains:

- download first
- verify the artifact
- explicit install second

Runtime and model productive sources stay disabled in this phase.

## v32-L Runtime Distribution Reality

The transcription runtime is now documented as one of three explicit distribution states:

- `application_bundled` for a future real app bundle with an embedded interpreter
- `managed` for app-controlled local runtime installs
- `legacy_external` for runtime packages importable from the active Python environment

Current repository reality is still not a true bundled app runtime. The clean-machine promise therefore remains a packaging target, not a proven repo artifact.

The UI should keep the runtime explanation plain:

- listo
- necesita reparacion
- no compatible
- no instalado

It should not imply that a runtime product download source is available unless one is explicitly qualified later.
