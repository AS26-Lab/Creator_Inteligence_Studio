# Personalization Data

## Scope

This layer prepares reproducible, versioned datasets per creator from existing human feedback.

It does not train models.
It does not change ranking rules.
It does not mix creators by default.
It does not upload data.

## Core ideas

- creator isolation is the default boundary;
- snapshots are immutable once completed;
- labels come only from explicit human feedback;
- features are derived from already computed local artifacts;
- conflicts are explicit and never silently resolved;
- train, validation and test splits are deterministic and leakage-aware;
- readiness is reported as a transparent status and score, not as a prediction.

## Snapshot lifecycle

Supported snapshot states:

- `building`
- `completed`
- `completed_with_warnings`
- `failed`
- `stale`
- `archived`

Each snapshot stores:

- creator and optional project scope;
- dataset, feature and label schema versions;
- source and configuration fingerprints;
- counts for examples, labels, splits and conflicts;
- readiness report and warnings;
- immutable example rows.

Regenerating a dataset creates a new snapshot version.
The previous snapshot remains intact and can be compared or archived.

## Labels

Labels are derived only from explicit human review signals.

Initial mapping:

- positive: approved, rating 4 or 5, or shortlisted with explicit positive rule;
- negative: rejected, rating 1 or 2;
- neutral_or_uncertain: unreviewed, needs_review, rating 3, weak shortlist context, or conflicting feedback;
- excluded: conflict, stale source, invalid bounds, duplicate, or leakage risk when configured to exclude.

Label source is recorded for every example:

- `review_status`
- `rating`
- `tag`
- `collection`
- `manual_bounds`
- `combined_human_rule`

No automatic score is treated as a training label.

## Features

Features are named, versioned and deterministic.

They can include:

- multimodal candidate metrics;
- acoustic metrics;
- visual metrics;
- ranking metrics;
- context features;
- coverage and presence flags;
- human-review metadata only as audit information, not as leakage-prone direct predictors.

Feature vectors use stable names and a feature schema version.
Missing values remain `null` unless an explicit missingness flag is useful.
Zero is not used as a stand-in for missing data.

## Missing values

Policy:

- keep the feature as `null` when it truly does not exist;
- add a missing indicator when it improves auditability;
- do not infer a zero or median automatically in storage;
- preserve the difference between "not available" and "available but zero".

## Conflicts

Conflicts are detected when signals disagree or provenance becomes uncertain.

Examples:

- approved and rejected on the same source without clear resolution;
- approved with a very low rating, or rejected with a high rating;
- duplicates with opposite labels;
- nearly identical candidates with conflicting decisions;
- stale or missing source artifacts;
- migrated feedback with warnings;
- manual bounds that no longer fit the current source.

Conflicts are recorded in `creator_dataset_conflicts`.
They can be excluded or marked uncertain based on configuration.

## Splits

Primary split strategy:

- split by `video_asset_id` first;
- keep duplicate or highly overlapping groups together via `group_key`;
- prefer deterministic assignment with a fixed seed;
- avoid leakage across train, validation and test.

When there are too few independent videos:

- the system reports that the split is not fully reliable;
- the snapshot may still complete with warnings;
- `evaluation_not_ready` style readiness is allowed.

Supported splits:

- `train`
- `validation`
- `test`
- `excluded`

## Quality report

Quality is measured with transparent technical metrics such as:

- duplicate ratio;
- overlap ratio;
- missing feature ratio;
- class balance;
- creator coverage;
- temporal coverage;
- source diversity;
- label consistency;
- leakage risk;
- readiness score.

Quality reports are stored per snapshot and are part of the audit trail.

## Readiness

Readiness states:

- `not_ready`
- `collecting_feedback`
- `limited`
- `ready_for_baseline`
- `ready_for_evaluation`
- `ready_for_personalized_training`
- `blocked_by_quality`
- `blocked_by_conflicts`

The readiness score is explanatory only.
It is not a probability of model success.

## Sample weights

Sample weights are used for future training preparation only.

They can reflect:

- clarity of human decision;
- explicit rating;
- conflicts;
- duplicates;
- stale sources;
- feedback migration warnings;
- quality of source evidence.

The automatic rank score is not used as a proxy for human confidence.

## Privacy

- datasets remain local;
- creator data is isolated;
- exports do not include full transcript text by default;
- private notes are excluded by default from ML exports;
- auditing exports are separate and explicit.

## Export formats

- JSON audit: snapshot, schema, examples, labels, conflicts, splits, quality and readiness.
- CSV features: technical IDs, split, label, weight, expanded features, no private notes by default.
- JSONL ML: one example per line with feature schema version, label schema version and stable feature names.

## CLI

- `personalization build`
- `personalization show`
- `personalization latest`
- `personalization list`
- `personalization examples`
- `personalization quality`
- `personalization readiness`
- `personalization compare`
- `personalization archive`
- `personalization export`

## GUI

The GUI exposes a Personalization Data view with:

- snapshot list;
- quality report;
- readiness summary;
- example list;
- conflict indicators;
- export and archive actions.

Text content and private notes are not shown by default.

## Limitations

- No model training yet.
- No cross-creator mixing by default.
- No automatic label inference from scores.
- No personalization weights adjusted by learning yet.
- No recommendation of clip performance.

## Handoff to personalization models

- the dataset snapshot is the input to local model training;
- only completed or completed_with_warnings snapshots are eligible;
- train, validation and test splits are reused as stored;
- labels remain human-derived and traceable;
- the model layer must not rewrite labels or feedback history;
- feature schema compatibility is required before training.

## Operational evaluation handoff

Operational evaluation scenarios may produce synthetic dataset snapshots to validate the full workflow. These demo snapshots remain isolated from real creator data and are not mixed into production personalization datasets.
