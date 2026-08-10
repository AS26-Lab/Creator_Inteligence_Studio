# Windows Application Packaging

## Purpose

This document describes the Windows packaging boundary for Creator Intelligence Studio.

## Strategy

The current packaging direction is:

- PyInstaller `onedir`
- app-owned runtime manifest
- explicit bundle-root detection
- writable app-data root outside the bundle

## What The Bundle Owns

The bundle is expected to own:

- the Python interpreter used by the packaged app;
- `faster-whisper`;
- `CTranslate2`;
- PySide6 and its Qt plugins;
- any required native wheels and DLLs;
- runtime notices and metadata.

## What Remains Separate

Do not bundle:

- Whisper models;
- FFmpeg product source;
- NVIDIA drivers;
- user secrets;
- system Python.

## Runtime Classification

`application_bundled` is only valid when the bundle provides manifest evidence and the runtime imports match that manifest.

Without that evidence, the runtime must remain classified as:

- `managed`
- `legacy_external`
- `missing`
- `incompatible`
- `repair_required`

## Build Foundation

The repository now includes a build script that:

- generates a runtime manifest;
- records packaging-tool identity when available;
- points to a PyInstaller onedir flow;
- reports blockers when the packager is not installed.

## v32-N Validation Update

The Windows `onedir` bundle is now real-call validated on the current test machine.

The proven bundle characteristics are:

- packaged app launches from a copied directory outside the repo;
- no system Python is required for startup;
- `PYTHONPATH` and `PYTHONHOME` are not required;
- runtime manifest is loaded from the bundle;
- `config/default.json` is available at the bundle root;
- `application_bundled` is claimed only when the manifest evidence matches;
- `faster-whisper` and `CTranslate2` are frozen into the bundle;
- Whisper models remain separate;
- FFmpeg remains a separate managed component.

The bundle is proven only on the current test machine, not on all Windows machines.
