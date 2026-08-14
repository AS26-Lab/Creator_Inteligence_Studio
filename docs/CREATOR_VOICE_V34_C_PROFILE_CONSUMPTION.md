# Creator Voice v34-C Profile Consumption

## Purpose

v34-C creates the canonical consumption boundary for Creator Voice profiles.

It answers a narrow question:

> Given a structured Creator Voice profile, what guidance is safe to preview without applying it to normal workflows?

The answer is a deterministic `CreatorVoiceGuidanceBundle`.

## Core Rule

Creator Voice is a tendency signal, not an instruction authority.

Precedence remains:

1. system and safety
2. current user request
3. current project or artifact instruction
4. confirmed preferences
5. Creator Voice guidance
6. historical corpus context

## What The Service Does

`CreatorVoiceGuidanceService`:

- validates creator and scope compatibility;
- checks profile readiness;
- selects only allowlisted profile features;
- filters low-confidence or unsafe features;
- applies explicit budgets;
- records conflicts and omissions;
- renders a bounded preview string from controlled templates;
- fingerprints the resulting bundle deterministically.

## What The Service Does Not Do

The consumption boundary does not:

- synthesize a final style prompt;
- apply voice guidance to AI workflows;
- mutate retrieval;
- mutate preferences;
- call an LLM;
- create embeddings;
- fine-tune a model;
- infer personality or sensitive traits.

## Supported Guidance Shape

The current preview surface is intentionally small and conservative.

Safe guidance categories include:

- length;
- sentence structure;
- formatting;
- interaction style;
- spoken style when the workflow is spoken-compatible.

Guidance is emitted only when the underlying profile feature is strong enough and not overridden by a higher-precedence signal.

## Exclusion And Override Reasons

The bundle reports omissions explicitly.

Common reasons include:

- `missing_profile`;
- `insufficient_profile`;
- `wrong_scope`;
- `wrong_language`;
- `low_confidence`;
- `too_little_signal`;
- `preference_override`;
- `user_override`;
- `project_override`;
- `unsupported_feature`;
- `disabled`.

## Diagnostic Surface

The CLI surface includes:

- `voice guidance-preview`

The preview can be disabled explicitly and returns an empty bundle without error.

## Non-Goals

v34-C does not:

- modify `ContentBriefService`;
- modify `ProductionPreparationService`;
- modify `StrategicPlanningService`;
- apply Creator Voice globally;
- replace confirmed preferences;
- replace explicit user instructions;
- replace project instructions.
