# Personalization Models

## Goal

This layer builds a first local baseline model per creator from the already isolated personalization datasets.

It is:

- local only;
- deterministic;
- explainable;
- separate from clip ranking;
- separate from multimodal scoring;
- safe to activate or retire explicitly.

It is not:

- a virality predictor;
- a deep model;
- a cross-creator model;
- an online learning system;
- a replacement for human review.

## Baseline model

The first implementation uses:

- `scikit-learn` logistic regression;
- `SimpleImputer`;
- `StandardScaler`;
- fixed random seed;
- validation-only threshold selection;
- local joblib artifacts stored under the application-managed model cache.

## Input policy

Training is allowed only when:

- the snapshot is completed or completed_with_warnings;
- the snapshot belongs to the requested creator;
- the feature schema is compatible;
- at least one positive and one negative example exist;
- the split is valid;
- the snapshot is not blocked by quality, conflicts, or leakage.

## Features

The model uses an allowlist of named features derived from the personalization dataset.

Excluded from training:

- labels;
- review status;
- human rating used to derive the label;
- tags used to derive the label;
- split names;
- creator IDs;
- video IDs;
- candidate IDs;
- any direct leakage field.

## Metrics

The training run stores:

- accuracy;
- balanced accuracy;
- precision;
- recall;
- specificity;
- F1;
- ROC-AUC when valid;
- PR-AUC when valid;
- log loss when valid;
- baseline comparisons.

## Artefacts

Artefacts are stored locally at:

`models/personalization/<creator-id>/<training-run-id>/`

Each run stores:

- `model.joblib`
- `manifest.json`
- `metrics.json`
- `feature_schema.json`

The loader verifies the artifact fingerprint before loading.

## Activation

Activation is explicit.
Only one active model should exist per creator and scope at a time.

The registry preserves:

- candidate runs;
- active / inactive / retired status;
- artifact state;
- auditability.

## Personalized scoring

Personalized scoring is separate from clip ranking.

It reads the active model for the creator and produces:

- `positive_score`;
- predicted label;
- explanation based on coefficients;
- threshold used.

The personalized score does not overwrite `rank_score`.

## Privacy and safety

- Training stays local.
- No models are uploaded.
- No raw audio, transcriptions, or notes are exported by default.
- joblib artifacts are loaded only from application-managed locations.
- artefacts with invalid fingerprints are rejected.

## Limitations

- This is a baseline, not a production recommender.
- There is no creator-level deep learning yet.
- There is no platform analytics feedback loop yet.
- There is no automatic tuning of the main ranker yet.

## Operational evaluation

The operational evaluation layer can validate training, activation and personalized scoring using synthetic demo data. That verifies the workflow, but it does not imply real-world model usefulness.
