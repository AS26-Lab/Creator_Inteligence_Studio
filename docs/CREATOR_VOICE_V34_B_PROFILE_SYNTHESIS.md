# Creator Voice v34-B Profile Synthesis

## Purpose

v34-B turns the deterministic evidence snapshot from v34-A into a structured Creator Voice profile.

The profile is diagnostic. It describes observable pattern tendencies only. It does not synthesize a model-facing style prompt and it does not apply the profile to AI workflows.

## What v34-B Implements

- deterministic profile synthesis from `CreatorVoiceEvidenceSnapshot`;
- bounded text/statistical feature extraction;
- separate written and spoken pattern tracking;
- separate structured confirmed-preference records;
- explainable readiness and confidence levels;
- deterministic fingerprints for profile rebuilds and comparisons;
- local CLI diagnostics for build, show, and compare.

## Core Rule

Evidence
-> observable pattern
-> structured profile

Not:

evidence
-> personality guess

## Feature Taxonomy

Only a small, controlled feature set is exposed.

Typical feature families:

- length;
- sentence structure;
- formatting;
- voice usage;
- punctuation;
- lexical repetition and diversity;
- spoken-specific tendency markers.

The implementation intentionally favors robust, bounded signals over broad coverage.

## Reuse Map

| Existing concept | Profile role | Reuse / extend / ignore |
|---|---|---|
| CreatorVoiceEvidenceSnapshot | canonical input | reuse |
| creator_written / creator_edited / creator_spoken evidence | text feature source | reuse |
| confirmed_preference evidence | separate structured guidance | reuse separately |
| deterministic diff utilities | future refinement support | reuse only indirectly |
| text analyzers in `creator_language` | word, sentence, and phrase heuristics | reuse |
| legacy creator memory style rules | not a source of truth for the profile | ignore |

## Readiness

The profile tracks a deterministic readiness status:

- `insufficient_evidence`;
- `partial`;
- `ready`.

Readiness is based on authentic words and source diversity, not on subjective appeal.

## Confidence

Confidence is explainable and coarse:

- `low`;
- `medium`;
- `high`.

The confidence level reflects evidence amount, source diversity, and consistency.

## Confirmation Boundary

Confirmed preferences remain separate from text-derived voice features.

If a confirmed preference conflicts with an observed pattern, the profile must show both and mark the conflict rather than silently resolving it.

## Profile Comparison

Comparison is supported as a diagnostic tool.

It reports changed feature keys and changed sections, but it does not change any downstream behavior.

## Non-Goals

v34-B does not:

- create a final Creator Voice prompt;
- infer personality, ideology, or sensitive traits;
- apply profile output to prompts;
- change retrieval;
- create embeddings;
- fine-tune a model;
- train a local style model;
- replace confirmed preferences;
- add a UI editor for voice tuning.

