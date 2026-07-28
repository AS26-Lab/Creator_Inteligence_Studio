# Creator Memory / Creator Profile Foundation

## Scope

Creator Memory stores a structured, editable, versioned profile for each creator.

It covers:

- identity and objectives;
- language, tone, formality and humor;
- vocabulary and recurring expressions;
- approved and rejected examples;
- style rules and limits;
- evidence, contradictions and human review;
- snapshot history and deterministic retrieval.

## What it does not do

- no LLM generation;
- no ML training;
- no automatic profiling;
- no audience model;
- no voice cloning;
- no fine-tuning;
- no publication automation.

## Core rule

Memory is not truth. Every trait, rule, example and limit must retain origin, date, evidence, contradictions, confidence and review history.

## Data model

The phase persists:

- `creator_profiles`
- `creator_traits`
- `creator_trait_evidence`
- `creator_examples`
- `creator_vocabulary`
- `creator_style_rules`
- `creator_style_rule_reviews`
- `creator_limits`
- `creator_profile_snapshots`
- `creator_memory_feedback`

## Retrieval

Retrieval is local and deterministic. Ranking prefers:

- matching scope;
- matching topic;
- platform and content type compatibility;
- confidence;
- recency;
- approval state;
- evidence weight.

## Privacy

- data stays local;
- exports are explicit;
- private text is not broadcast by default;
- creators remain isolated;
- evidence is kept minimal but traceable.

Thumbnail Lab and Titles Foundation consults this memory for brand fit, approved and rejected examples, style rules, limits, and objectives before proposing concepts or prompts.

## Next phase

Creator Language Analysis / Narrative Profile.

See [`docs/CREATOR_LANGUAGE_ANALYSIS.md`](CREATOR_LANGUAGE_ANALYSIS.md) for the local language analysis layer that consumes structured sources and can propose reviewable candidates without mutating Creator Memory automatically.
Strategic Planning reads Creator Memory snapshots as immutable planning context.
