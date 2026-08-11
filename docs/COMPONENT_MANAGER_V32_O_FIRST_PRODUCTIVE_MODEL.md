# Component Manager v32-O First Productive Transcription Model

## Status

Implemented in source, unit-validated, and real-download validated on the current Windows test machine.

## Decision

The first productive transcription model source is:

- component id: `transcription-model.small`
- friendly name: `Modelo de transcripcion - Equilibrado`
- upstream repository: `Systran/faster-whisper-small`
- pinned revision: `536b0662742c02347bc0e980a01041f333bce120`
- license: `MIT`

## Why This Model

This model is the best first product-source fit for the current `Balanced` profile because it is:

- the smallest supported productive transcription model
- the default balanced profile target in the existing transcription profile registry
- a lower-risk first source than `medium` for disk, download, and CPU baseline behavior
- still compatible with GPU acceleration when the hardware supports it

## Source Qualification

The product source is explicit and pinned to immutable file identities under the upstream snapshot layout.

Required source files:

- `config.json`
- `tokenizer.json`
- `vocabulary.txt`
- `model.bin`

The repository now records:

- provider
- upstream project
- revision
- source page
- per-file expected bytes
- per-file expected SHA-256
- aggregate expected bytes
- catalog revision

The per-file SHA-256 values are qualification hashes derived from the exact pinned revision after one trusted download from that revision. They are not claimed as upstream-published checksums.

## Source Layout

The source manifest is multi-file. It is not treated as one opaque hidden snapshot download.

Download flow:

1. Download each required file through the Download Manager.
2. Verify each file against its expected SHA-256 and expected byte count.
3. Stage the files under the managed model snapshot layout.
4. Persist a verified artifact record.
5. Install explicitly from the verified artifact.

## Boundaries

This phase does not enable:

- multiple model product sources
- `snapshot_download()`
- remote transcription
- automatic model installation on detection
- migration `33`
- user runtime `pip`
- PATH mutation
- drivers

## Validation State

What is validated in this workspace:

- catalog qualification
- manifest identity
- unit-level persistence of the verified model artifact record
- rehydration of the verified artifact from the persisted download repository
- real packaged Windows transcription from the isolated bundle
- restart/offline readiness after installation

## Remaining Risk

The upstream model source is explicit and pinned, but it is still a third-party release asset. Availability depends on upstream retention policy and repository stability.
