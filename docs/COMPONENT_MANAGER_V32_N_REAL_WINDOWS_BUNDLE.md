# Component Manager v32-N Real Windows Bundle

## Status

`v32-N` is implemented and real-call validated on the current test machine.

## Build Result

- build command: `python scripts/build_windows_app.py`
- packaging tool: `PyInstaller 6.14.2`
- bundle strategy: `onedir`
- frozen entrypoint: `CreatorIntelligenceStudio.exe`
- bundle root: `dist/CreatorIntelligenceStudio`

## Validation Result

The frozen application was copied to an isolated temporary directory and executed with a sanitized environment.

Environment controls used in the validation harness:

- `PYTHONPATH` removed;
- `PYTHONHOME` removed;
- `VIRTUAL_ENV` removed;
- `CONDA_PREFIX` removed;
- `HF_HOME` redirected to an empty temp directory;
- `TRANSFORMERS_CACHE` redirected to an empty temp directory;
- `LOCALAPPDATA` redirected to a writable temp root for the harness.

The packaged diagnostic returned:

- `packaged_application = true`;
- bundle root resolved from the copied executable;
- runtime manifest loaded from the bundle;
- `application_bundled` evidence present;
- no hidden model download;
- no system Python requirement for startup.

## Bundle Layout Fixes

The real PyInstaller bundle initially placed some data under `_internal`, so the build script now promotes the required runtime files to the bundle root:

- `config/default.json`
- `docs/TRANSCRIPTION_RUNTIME_LICENSING.md`
- `runtime/runtime_manifest.json`

## Runtime Notes

- `faster-whisper==1.2.1` is frozen into the bundle;
- `ctranslate2==4.8.1` is frozen into the bundle;
- `backports.tarfile==1.2.0` is included because the frozen `pkg_resources` runtime hook requires it;
- CPU runtime is available on the packaged app;
- GPU remains optional and driver-owned;
- Whisper models remain separate;
- FFmpeg remains a separate managed component.

## Bundle Size

Current onedir footprint on the test machine:

- files: 4447
- size: about 955.64 MiB

Largest contributors:

- PySide6 / Qt
- `av.libs`
- `ctranslate2`
- `scipy`
- `onnxruntime`
- `numpy.libs`

## Remaining Limitation

This validates the bundle on the current test machine only. It does not prove every Windows machine or every GPU/driver combination.
