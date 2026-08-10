# Component Manager v32-M Windows Packaging

## Purpose

v32-M adds the packaging foundation needed to eventually ship Creator Intelligence Studio as a self-contained Windows application.

This phase does **not** claim a proven distributable app bundle. It establishes:

- a deterministic Windows runtime manifest;
- a bundle-root-aware bootstrap path;
- app-data root resolution for packaged execution;
- a single packaging strategy: PyInstaller `onedir`;
- explicit documentation for what is proven versus what remains foundation only.

## Selected Packaging Strategy

The repo is suited to a Windows `onedir` bundle with PyInstaller because:

- the GUI is PySide6-based;
- the runtime includes native wheels and DLL discovery;
- `onedir` keeps native payloads visible and easier to debug than `onefile`;
- `CTranslate2` and CUDA helper libraries are large enough that extraction-based startup is a worse default.

`onefile` is not selected because this project needs:

- predictable DLL discovery;
- lower extraction ambiguity;
- easier forensic inspection of runtime payloads;
- less startup churn for a large native runtime.

## Runtime Manifest

The build foundation writes a deterministic `runtime_manifest.json` into the bundle layout.

The manifest records:

- application version;
- Python version;
- `faster-whisper` version;
- `CTranslate2` version;
- platform;
- architecture;
- CPU/GPU support flags;
- build revision;
- build timestamp;
- packaging tool identity when available;
- notices reference.

## Clean-Machine Contract

The intended packaged contract is:

- launch from a copied bundle directory;
- no system Python required;
- no `pip` required at runtime;
- no manual PATH setup;
- runtime classification is explicit;
- CPU runtime should remain the baseline.

That contract is still a target until a real bundle is built and exercised end to end.

## Bundle Layout

The expected onedir layout is:

```text
dist/
  CreatorIntelligenceStudio/
    CreatorIntelligenceStudio.exe
    runtime/
      runtime_manifest.json
    libraries/
    resources/
    config/
    docs/
```

The build script writes the manifest and reports the expected layout even when the packager is absent.

## Current Blocker

## v32-N Real Bundle Result

The repository now has a real PyInstaller `onedir` build and an isolated clean-machine validation path.

On the current test machine:

- the bundle builds successfully;
- the copied bundle starts outside the repo;
- `CreatorIntelligenceStudio.exe --diagnostic-json` returns packaged runtime evidence;
- the runtime manifest is present at `runtime/runtime_manifest.json`;
- `config/default.json` is promoted to the bundle root so frozen bootstrap can resolve settings;
- the frozen runtime is classified as `application_bundled` with manifest evidence;
- `backports.tarfile==1.2.0` is bundled because the frozen `pkg_resources` hook requires it.

Status: `proven on current test machine` for the Windows `onedir` bundle path.
