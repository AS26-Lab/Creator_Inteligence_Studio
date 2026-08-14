# Creator Voice Profile Architecture

## Overview

The profile architecture sits between evidence selection and any future voice application layer.

Pipeline:

1. `CreatorVoiceEvidenceService` builds a deterministic evidence snapshot.
2. `CreatorVoiceProfileService` turns that snapshot into bounded profile features.
3. Future phases may consume the profile, but v34-B does not yet apply it to prompts or retrieval.

## Inputs

The profile service consumes:

- evidence snapshot identity and contents;
- text references for eligible evidence items;
- evidence type and authorship class;
- evidence weights and quality levels;
- scope, language, and project/workflow metadata;
- confirmed-preference evidence items.

The profile service does not call providers and does not use embeddings.

## Feature Extraction

The implementation uses deterministic, offline statistics:

- word counts;
- paragraph counts;
- sentence lengths;
- short sentence ratio;
- first-person and second-person usage;
- question and exclamation ratios;
- paragraph density;
- list usage and line-break frequency;
- lexical diversity;
- repeated phrases with privacy filtering;
- spoken sentence tendencies and filler rate when reviewed speech is present.

The implementation deliberately avoids topic modeling, personality inference, or sensitive attribute detection.

## Written vs Spoken

Written and spoken evidence remain distinct.

- written features are derived from creator-written and creator-edited text;
- spoken features are derived from transcribed speech;
- spoken version records are skipped when segment-level speech evidence exists;
- confirmed preferences are not counted as spoken or written style samples.

## Controlled Taxonomy

The initial taxonomy is small and bounded.

Allowed feature families:

- `length`;
- `sentence_structure`;
- `formatting`;
- `voice_usage`;
- `punctuation`;
- `lexical`;
- `spoken`.

No generic personality fields are introduced.

## Confidence And Readiness

Feature confidence is coarse and explainable.

Profile readiness uses a deterministic threshold based on authentic word volume and source diversity.

The profile status is one of:

- `insufficient_evidence`;
- `partial`;
- `ready`.

## Structured Preferences

Confirmed preferences are carried in a separate section.

They preserve:

- preference key;
- preference type;
- scope;
- project/workflow scoping;
- rendered structured text;
- conflict flag;
- conflict warning;
- evidence basis.

They are not converted into textual style features.

## Fingerprints And Rebuild

The profile fingerprint depends on:

- the evidence snapshot fingerprint;
- the profile version;
- the feature algorithm version;
- the derived feature payload;
- the structured preference payload;
- profile warnings and limitations.

Rebuilding from the same snapshot must produce the same semantic profile fingerprint.

## Diagnostics

The CLI surface supports:

- `voice profile-build`;
- `voice profile-show`;
- `voice profile-compare`.

The CLI prints safe summary output by default and JSON when requested.

## v34-C Consumption Boundary

`CreatorVoiceGuidanceService` consumes the profile as derived data.

It may:

- inspect readiness and confidence;
- consume only allowlisted features;
- preserve scope, language, and spoken/written distinctions;
- preserve confirmed preferences as separate structured guidance;
- record overrides and omissions explicitly.

It may not:

- apply guidance to workflow prompts;
- mutate preferences;
- mutate retrieval;
- generate a final style prompt.

## v34-D Workflow Application Boundary

`CreatorVoiceWorkflowApplicationService` consumes the guidance bundle and decides whether the guidance may be applied to a workflow.

It may:

- preserve shadow mode for comparison;
- gate application by workflow allowlist and explicit opt-in;
- emit observability about applied, omitted, and overridden guidance;
- leave the normal final request unchanged when application is disabled.

It may not:

- read raw corpus text;
- bypass confirmed preferences or explicit instructions;
- generalize application to all workflows;
- mutate the underlying profile.

## Non-Goals

v34-B does not:

- generate a final style prompt;
- apply the profile to AI workflows;
- mutate retrieval;
- create embeddings;
- fine-tune a model;
- infer personality or sensitive traits;
- persist profile state by default.
