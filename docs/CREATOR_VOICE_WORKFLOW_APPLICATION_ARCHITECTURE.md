# Creator Voice Workflow Application Architecture

## Overview

This architecture sits after `CreatorVoiceProfileService` and `CreatorVoiceGuidanceService`.

Pipeline:

1. `CreatorVoiceEvidenceService` builds a deterministic evidence snapshot.
2. `CreatorVoiceProfileService` derives a structured profile.
3. `CreatorVoiceGuidanceService` produces bounded guidance.
4. `CreatorVoiceWorkflowApplicationService` decides whether guidance may be applied to a workflow.

## Domain Contracts

Canonical contracts introduced in v34-D:

- `CreatorVoiceWorkflowApplicationRequest`
- `CreatorVoiceWorkflowApplicationBundle`
- `CreatorVoiceWorkflowApplicationState`
- `CreatorVoiceWorkflowApplicationVersion`

These contracts are deterministic, serializable, and rebuildable.

## Service Boundary

`CreatorVoiceWorkflowApplicationService` is the controlled consumer of the guidance bundle.

It:

- validates creator and scope;
- inspects profile readiness and guidance state;
- preserves shadow-first comparison;
- applies explicit allowlist and opt-in checks;
- records applied, omitted, and overridden guidance;
- emits a bounded bundle and fingerprint.

It does not:

- synthesize evidence;
- synthesize the profile;
- infer personality;
- mutate preferences;
- mutate retrieval;
- perform provider execution.

## Precedence Handling

The application boundary keeps the existing precedence order:

1. system and safety;
2. current user request;
3. current project or artifact instruction;
4. confirmed preferences;
5. Creator Voice guidance.

If higher-precedence signals conflict with voice guidance, the voice item is omitted or marked overridden.

## Shadow First

Shadow mode is the default diagnostic behavior outside approved application workflows.

That allows the product to:

- compare voice on/off outputs;
- validate request immutability;
- validate exclusion and override reporting.

## CLI Surface

`voice application-preview` is the canonical diagnostic entry point.

It supports:

- shadow preview;
- explicit `--apply` application preview;
- JSON and human-readable output.

## Non-Goals

v34-D does not:

- apply Creator Voice globally;
- change retrieval;
- mutate preferences;
- generate a final style prompt;
- use an LLM for interpretation;
- broaden application beyond the controlled workflow boundary.
