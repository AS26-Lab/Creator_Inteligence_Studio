# Component Manager v32-H Explicit Local Component Actions

## Purpose

v32-H turns the guided local-components screen into an explicit action surface.

The UI still consumes the canonical `TranscriptionCapabilityResolver` output. It does not decide readiness, fallback, or install policy. Instead, it sends structured action requests to the backend and observes task lifecycle updates through the existing task center state.

## What v32-H Adds

- explicit `verify_component`
- explicit `run_gpu_benchmark`
- explicit local-source `install_component`
- explicit managed `repair_component`
- explicit managed `remove_component`
- revalidation before mutation
- confirmation before destructive actions
- task records for component actions
- human-friendly error mapping
- resolver refresh after terminal state

## What v32-H Does Not Add

- productive internet sources
- automatic download on open
- automatic install
- automatic benchmark
- direct widget-level readiness rules
- pip, conda, winget, or PATH mutation
- migration `v33`

## UX Policy

- normal mode uses plain-language labels
- technical details stay behind the advanced toggle
- local installs require an explicit local file or folder picker
- destructive actions require a confirmation dialog
- unavailable actions are explained, not silently hidden

## Task Lifecycle

Component actions are executed through a structured request, a background task record, and a terminal resolver refresh.

This keeps the GUI responsive while preserving the resolver as the source of truth.
