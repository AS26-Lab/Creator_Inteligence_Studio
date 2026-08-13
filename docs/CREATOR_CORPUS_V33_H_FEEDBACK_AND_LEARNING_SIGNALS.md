# Creator Corpus v33-H Feedback And Learning Signals

## Purpose

v33-H adds a local, creator-scoped foundation for recording feedback about generated or edited content and deriving conservative learning signals from that evidence.

This phase captures evidence. It does not automatically apply learned preferences to prompts, retrieval ranking, or creator voice.

## Core Rule

One signal is not a learned preference.

AI-generated content is not creator-original content merely because it was accepted.

## What Is Recorded

Canonical feedback events record:

- creator identity;
- optional project scope;
- workflow scope;
- artifact scope;
- version lineage;
- event type;
- event source;
- creation time;
- safe metadata.

Supported event types are intentionally small:

- accepted
- rejected
- regenerated
- adopted
- superseded
- edited

## What Is Derived

Learning signals are derived from feedback events and remain auditable.

The foundation keeps:

- explicit evidence links;
- conservative status progression;
- idempotent event handling;
- creator isolation;
- project and workflow scope;
- deterministic revision diffs for edit transitions.

## Validation Surfaces

The packaged runtime exposes diagnostic/developer-only validation surfaces that call the canonical services:

- planning context snapshot creation;
- edit-feedback recording.

These surfaces exist so frozen packaged validation can reach the real application boundary. They are not normal-user product features.

## Explicit Non-Goals

v33-H does not:

- apply preferences automatically;
- rerank retrieval from feedback;
- mutate prompts from learning signals;
- change creator voice;
- train models;
- infer sensitive traits;
- turn a single edit into a permanent rule.

## Relationship To Earlier Phases

- v33-A through v33-G establish corpus, retrieval, context, workflow grounding, and optional semantic retrieval.
- v33-H adds evidence capture and conservative derived signals.
- later phases may decide whether any candidate signals are safe to apply.
