# Creator Corpus v33-F Semantic Retrieval Evaluation

## Status

`evaluated`, not adopted as the production retrieval path.

## Purpose

v33-F evaluates whether a local semantic or hybrid retrieval layer adds measurable value over the existing lexical baseline.

Lexical retrieval remains the production default, baseline, and fallback.

## What Was Evaluated

The local semantic foundation was exercised with:

- `intfloat/multilingual-e5-small`
- revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`
- ONNX Runtime CPU execution
- tokenizer-driven local inference
- creator-scoped synthetic corpus data only

The evaluated ONNX artifact was the quantized model:

- `onnx/model_qint8_avx512_vnni.onnx`

## Why This Candidate

The candidate was chosen because it is:

- multilingual
- MIT licensed
- local CPU runnable
- ONNX-compatible
- smaller than larger multilingual alternatives
- practical for Windows packaged deployment experiments

## Evaluation Result

The local evaluation showed:

- lexical retrieval remains strong for exact matches
- semantic scoring improves paraphrase-style queries
- hybrid fusion keeps exact lexical matches high
- creator isolation remained intact in the evaluation harness
- the semantic path is still an optional derived capability, not a product default

## Decision

The repository now has a local semantic retrieval foundation and a deterministic evaluation harness.

It does not yet adopt semantic retrieval as the production path.

Production retrieval remains lexical with the semantic layer available for evaluation and future controlled adoption.

## v33-G Handoff

v33-G turns the evaluation result into an optional product capability:

- the semantic model is managed and versioned
- the universal CPU artifact is preferred over the AVX512-only artifact
- lexical fallback stays mandatory
- hybrid retrieval is only used when semantic capability is healthy

The v33-F evaluation remains the benchmark reference for later regressions.
