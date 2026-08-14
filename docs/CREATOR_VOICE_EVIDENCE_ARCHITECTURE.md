# Creator Voice Evidence Architecture

## Overview

Creator Voice evidence is a local, deterministic selection layer that sits on top of the creator corpus and confirmed-preference store.

Its job is to answer three questions:

1. What evidence qualifies as creator voice evidence?
2. Why does it qualify or fail to qualify?
3. What bounded snapshot can future Creator Voice synthesis consume safely?

The architecture intentionally stops before synthesis. It is evidence selection, not style generation.

## Inputs

The service reads:

- creator corpus documents;
- corpus versions;
- transcript segments;
- authorship class;
- voice-learning eligibility;
- review and confidence metadata;
- provenance and hashes;
- confirmed preferences;
- project membership;
- workflow scope;
- language metadata.

The service does not call an LLM or external provider.

## Evidence Taxonomy

Controlled evidence types in v34-A:

- `creator_written` for creator-authored written evidence;
- `creator_edited` for creator-edited evidence;
- `creator_spoken` for transcribed creator speech;
- `confirmed_preference` for structured preference evidence.

The taxonomy deliberately avoids subjective style labels.

## Selection Pipeline

The canonical service follows this order:

1. Validate creator ownership.
2. Load documents, versions, segments, and confirmed preferences.
3. Apply active/archive and scope gates.
4. Apply language filters when requested.
5. Exclude unsafe authorship classes.
6. Apply conservative speech-confidence rules.
7. Apply conservative AI-origin edit handling.
8. Deduplicate by content hash and source identity.
9. Apply bounded caps.
10. Produce a deterministic snapshot and fingerprint.

## Authorship Rules

The core authorship policy is:

- creator-original evidence qualifies when active and eligible;
- creator-edited evidence qualifies when active and eligible, but AI-origin lineage remains visible;
- transcribed creator speech qualifies only when review policy allows it;
- AI-generated content is excluded;
- AI-rewritten content is excluded by default;
- imported-unknown content is excluded by default.

## AI Self-Contamination Gate

The system must not learn its own AI output as if it were creator-authentic evidence.

Accepted AI content remains AI-derived unless a later conservative human-edited lineage is supported by the corpus and policy.

The following do not promote AI output into authentic voice evidence:

- user viewing it;
- user accepting it;
- it becoming current;
- it being reused later;
- it being present in a project.

## Creator-Edited AI Content

v34-A treats creator-edited AI content conservatively.

Current rule:

- eligible as `creator_edited` when the current version is active and voice-learning eligible;
- lower evidence weight than creator-original evidence;
- no claim that the whole version is equivalent to pure creator-original text;
- no LLM-based span attribution;
- no personality inference.

This is intentionally conservative until explicit diff-span attribution exists.

## Speech Confidence Policy

Transcribed speech is eligible only when safe enough for voice evidence.

Policy in v34-A:

- reviewed, high-confidence speech is eligible;
- `needs_review` segments are excluded;
- low-confidence segments are excluded;
- `excluded_from_voice_learning` segments are excluded;
- version-level speech evidence is blocked when the underlying segment set is unsafe.

## Confirmed Preferences

Confirmed preferences are included as structured evidence only.

They can inform future synthesis, but they are not:

- text samples;
- style proof;
- authorship proof;
- language-translated voice samples.

## Scope Model

The evidence boundary respects:

- creator-global scope;
- project-specific scope;
- workflow-specific scope;
- language-specific filtering.

Project scope does not silently become global voice style.

## Dedupe and Diversity

Evidence selection uses deterministic dedupe and bounded caps.

The current architecture:

- deduplicates by content hash;
- caps per item count, per source, and per evidence type;
- prevents one duplicate chain from dominating the snapshot;
- preserves diversity across source identity and evidence type;
- avoids O(N^2) comparison patterns.

## Quality Model

Quality metadata uses explainable levels:

- `high`;
- `medium`;
- `low`.

The quality model is deterministic and should not be confused with a probability score.

Factors may include:

- authorship class;
- AI-origin contamination;
- review state;
- confidence;
- completeness;
- text length;
- duplication;
- scope match.

## Snapshot Contract

A snapshot is immutable for a given corpus state and policy version.

It includes:

- creator, project, workflow, and language filters;
- policy version;
- selected evidence items;
- counts by type and quality;
- excluded counts by reason;
- language, project, and workflow distributions;
- estimated word and character totals;
- a deterministic fingerprint.

The fingerprint is derived from request state, selected evidence identity, and exclusion reasons. It does not rely on wall-clock time.

## Diagnostics

The CLI surface is intentionally small.

`voice evidence-snapshot` reports:

- safe summary output by default;
- JSON output on request;
- evidence IDs and counts;
- quality and exclusion reasons;
- fingerprint;
- bounded debug snippets only when explicitly requested.

The diagnostic surface is not a voice editor.

## Non-Goals

v34-A does not:

- synthesize a final style prompt;
- mutate prompts;
- mutate retrieval ranking;
- create style embeddings;
- train or fine-tune a model;
- infer personality;
- infer sensitive attributes;
- do network calls;
- do provider calls.

## Rebuildability

Snapshots are derived data.

Canonical source remains:

- corpus documents;
- corpus versions;
- transcript segments;
- provenance;
- review metadata;
- confirmed preferences.

If the snapshot is lost, it can be rebuilt from canonical state and the same policy version.
