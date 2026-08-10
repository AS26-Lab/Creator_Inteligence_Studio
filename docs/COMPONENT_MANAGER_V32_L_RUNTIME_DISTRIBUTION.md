# Component Manager v32-L Runtime Distribution

## Purpose

v32-L closes the runtime distribution boundary for local transcription and hardens HTTP/TLS resource ownership in the downloader.

This phase does **not** enable product runtime sources and does **not** enable model product sources.

## Current Distribution Reality

The repository currently ships the transcription runtime as Python packages in the application dependency set:

- `faster-whisper`
- `ctranslate2`
- Windows CUDA helper wheels when present

There is no checked-in Windows application bundle or installer pipeline in this repository that embeds a separate Python interpreter and packages the runtime as a truly self-contained app bundle.

That means the current operational reality is:

- `application_bundled` is a future packaging option, not the present implementation
- `managed` covers locally installed, app-controlled runtime bundles
- `legacy_external` covers runtime packages importable from the active Python environment
- `missing`, `incompatible`, and `repair_required` remain explicit failure states

## Clean-Machine Contract

The intended user contract is:

- install Creator Intelligence Studio
- launch it
- no manual Python setup
- no `pip` at runtime
- no terminal setup
- no PATH editing
- runtime readiness is shown explicitly

Current repo state does not prove that a fresh Windows machine without Python installed satisfies that contract end-to-end, because the repository does not yet include a committed app-bundle pipeline that ships its own interpreter.

## CPU Baseline

The runtime boundary must remain usable on CPU-only machines.

Required behavior:

- CPU-only remains a valid path
- GPU remains optional acceleration
- missing GPU support must not block basic local transcription if CPU runtime is available

## GPU Boundary

Current GPU support relies on:

- `ctranslate2`
- `faster-whisper`
- Windows NVIDIA runtime wheels for CUDA helper libraries when packaged into the environment
- a compatible NVIDIA driver already present on the machine

This phase does not install drivers.

## No Runtime Pip

User-facing runtime setup must not depend on:

- `pip install`
- `python -m pip`
- `ensurepip`
- ad hoc subprocess pip calls

Build-time packaging may still use those tools if the packaging pipeline does so explicitly.

## Transport Hardening

The downloader now treats the HTTP response and its underlying connection as a single owned resource.

Required cleanup behavior:

- close on success
- close on HTTP failure
- close on retry
- close on pause
- close on cancel
- close on redirect
- close on exception

This removes the SSL socket leak observed during the real FFmpeg product download validation.

## UI Contract

The local components view should describe runtime state plainly:

- ready
- needs repair
- incompatible
- missing

It should not imply that a runtime download source is active unless one is actually qualified.

## Future Packaging Decision

If the clean-machine contract must be satisfied without relying on the active Python environment, a later phase should evaluate a true application bundle with an embedded interpreter and pinned runtime wheels.

That decision should be made with:

- license review
- redistribution review
- integrity/signing design
- size and bandwidth analysis
- rollback strategy

v32-L does not implement that bundle.

## v32-M Note

v32-M adds the packaging foundation and bundle manifest contract, but it does not change the v32-L conclusion that a real bundled runtime must be demonstrated with an actual build before `application_bundled` can be claimed.
