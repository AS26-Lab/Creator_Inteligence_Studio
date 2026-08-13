# Creator Corpus v33-G Product Semantic Retrieval Lifecycle

## Status

`adopted as an optional local capability`, while lexical retrieval remains the baseline and fallback.

## Decision

v33-F established that the local multilingual candidate is useful, but the product had no semantic lifecycle.

v33-G adds the missing product boundary:

- explicit managed embedding model component
- local embedding service
- derived semantic index
- creator-scoped semantic search
- hybrid retrieval with lexical fallback
- rebuildable staging and activation lifecycle

## Product Shape

Supported product modes:

- `lexical`
- `hybrid_if_available`

Semantic-only is not the normal user mode.

If the semantic model is missing, broken, stale, or not installed, the corpus still works with lexical retrieval.

## Managed Embedding Component

The embedding model is represented as a real component catalog entry:

- component id: `creator-embedding-model.multilingual-e5-small`
- provider/source: `intfloat/multilingual-e5-small`
- revision: `614241f622f53c4eeff9890bdc4f31cfecc418b3`
- license: `MIT`
- selected universal artifact: `onnx/model.onnx`
- accelerator artifact: `onnx/model_qint8_avx512_vnni.onnx`

The AVX512/VNNI artifact is kept as an accelerator-specific variant, not as the universal default.

## Lifecycle

The product lifecycle is:

approved manifest -> explicit download -> file verification -> explicit install -> health -> semantic capability ready

The implementation does not auto-install and does not use a remote embedding API.

## Index Boundary

Semantic vectors are derived data.

The index stores:

- creator id
- document id
- version id
- chunk identity
- content hash
- model identity
- model revision
- chunking version
- vector blob
- timestamps

The canonical corpus remains the source of truth.

## Retrieval Boundary

`CreatorCorpusRetrievalService` now supports a semantic-aware path when the semantic capability is healthy.

If the semantic layer is unavailable, retrieval falls back to lexical and reports the fallback mode explicitly.

## Validation State

This phase proved:

- source requalification for the candidate repo
- CPU artifact selection over the AVX512-only artifact
- model component metadata
- local embedding health checks
- creator-scoped semantic index build and search
- lexical fallback when semantic capability is absent
- hybrid retrieval wiring into the canonical retrieval service
- real model download and install in a clean product environment
- packaged Windows runtime validation against the installed model
- a real corpus E2E on the fully installed product path

## Recommendation

Keep lexical as the first-class fallback.

Use hybrid only when the embedding model and derived index are healthy and explicitly installed.
The semantic layer is optional and locally managed; it does not replace lexical retrieval.
