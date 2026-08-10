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

This is foundation, not proof of a distributable installer.
