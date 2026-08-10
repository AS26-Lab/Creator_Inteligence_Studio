# Transcription Runtime Licensing

## Scope

This document records the runtime licensing situation for local transcription dependencies.

It is not legal advice.

## Runtime Dependencies

Current runtime packages relevant to transcription include:

- `faster-whisper`
- `ctranslate2`
- `PySide6`
- `scikit-learn`
- Windows CUDA helper wheels when present in the runtime environment

If the application is later packaged as a true self-contained bundle, the third-party notices should be reviewed again for the exact shipped set.

## Current Distribution Shape

The repository currently models the transcription runtime as application-managed or environment-detected Python packages, not as a separate model artifact.

That means:

- no model files belong in the runtime package
- no model source is implied by the runtime license review
- runtime source qualification and model source qualification remain separate decisions

## Notice Strategy

If the runtime is bundled with the application in a future packaging pipeline, third-party notices should at minimum cover:

- the bundled Python interpreter
- runtime wheels shipped inside the bundle
- transitive native libraries shipped with those wheels
- any additional files required for the local runtime to start

If the runtime remains environment-detected, the installed environment is still responsible for its own package notices.

## No Redistribution Claim

This document does not claim that the project is redistributing every dependency today.

It only records what should be reviewed if the runtime packaging boundary changes later.

## Packaged Windows Foundation

If the runtime is later bundled inside the Windows app:

- the manifest should record the shipped runtime versions;
- notices should cover the shipped runtime wheels and native DLLs;
- the preferred layout remains `onedir` unless a later decision replaces it.
