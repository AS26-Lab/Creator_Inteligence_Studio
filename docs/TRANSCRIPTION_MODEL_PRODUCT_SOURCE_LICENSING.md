# Transcription Model Product Source Licensing

## Scope

This document covers the first productive transcription model source for Creator Intelligence Studio.

## Selected Source

- component id: `transcription-model.small`
- upstream repository: `Systran/faster-whisper-small`
- pinned revision: `536b0662742c02347bc0e980a01041f333bce120`
- source page: `https://huggingface.co/Systran/faster-whisper-small/tree/536b0662742c02347bc0e980a01041f333bce120`
- license: `MIT`

## Trust Model

Hugging Face provides the immutable repository identity, the release page, the per-file names, and the file sizes shown on the source page. In this workspace, the SHA-256 values recorded for the required files are qualification hashes established by a one-time download from that exact pinned revision and a local SHA-256 calculation of the retrieved bytes.

That means:

- upstream provenance = immutable repository + exact revision + file identities + source page
- integrity pin provenance = locally established SHA-256 values for the exact bytes fetched from that immutable revision

The repository does not claim that Hugging Face published those SHA-256 values directly for this model snapshot.

## Covered Files

The product source is qualified as a multi-file snapshot with these required files:

- `config.json`
- `tokenizer.json`
- `vocabulary.txt`
- `model.bin`

## Distribution Notes

- Downloading the model from the source page is a network operation.
- Local transcription remains local once the model is installed.
- The model source is not the same as the application runtime.
- The model source is not bundled with the application.
- The model source is not the same as FFmpeg.

## Verification Notes

The repository records expected bytes and SHA-256 values for the exact pinned files. The SHA-256 values are qualification hashes derived from the pinned source revision, not a separate upstream checksum feed. Installation must fail closed if any file does not match.

## Remaining Uncertainty

This is not a legal opinion.

The practical licensing question that still matters operationally is whether future redistribution or mirroring would require additional review if upstream retention becomes insufficient. That question is intentionally deferred.
