# Opportunity and Recommendation Engine Foundation

Date consulted: 2026-07-28

This phase turns creator-scoped evidence into reviewable recommendation candidates without adding LLM, ML, publication, remote writing, or automatic execution.

## Purpose

- assemble a reproducible recommendation context from Creator Memory, Creator Language, Audience Model, Analytics Lab, Market Intelligence, Platform Integrations, Experiments, Thumbnail Lab and Content Library;
- generate deterministic, rule-based recommendation candidates;
- expose evidence, contradictions, risks, constraints, alternatives, metrics and invalidation criteria;
- keep every recommendation human-reviewable and expirable.

## What this phase does

- creates recommendation requests, runs, candidates, evidence, risks, constraints, alternatives, metrics, invalidation criteria, reviews, feedback, snapshots and reports;
- preserves fact / inference / hypothesis labeling;
- separates objective alignment, fit, priority, freshness and copying risk;
- links approved recommendations to the existing Experiments system without duplicating it;
- keeps execution and publication outside this phase.

## What this phase does not do

- no editorial calendar generation;
- no automatic planning of weeks or months;
- no final script generation;
- no automatic image or thumbnail generation;
- no publication or remote writing;
- no scraping or browser automation;
- no TikTok Research API;
- no private APIs;
- no LLM;
- no ML;
- no automatic approval;
- no irreversible execution.

## Recommendation discipline

- recommendations must have evidence, objective, creator, freshness, confidence and limitations;
- popularity does not imply fit;
- momentum does not imply priority;
- copying risk can block approval;
- contradictory evidence remains visible;
- stale recommendations do not appear urgent;
- history and snapshots remain immutable.

## Context snapshots

Recommendation generation starts from an immutable context snapshot so that a historical recommendation can be explained with the exact inputs that produced it.

Typical inputs:

- Creator Memory snapshot;
- Creator Language snapshot;
- Audience Model snapshot;
- Analytics Lab snapshot;
- Market Intelligence snapshot;
- Platform Integrations snapshot;
- Experiments snapshot;
- Thumbnail Lab snapshot;
- Content Library snapshot;
- creator preferences and constraints;
- engine configuration.

## Evidence and classification

Every recommendation candidate stores evidence with explicit classification:

- `fact`;
- `inference`;
- `hypothesis`.

Evidence also keeps:

- source domain;
- source identifiers;
- snapshot references;
- quality;
- strength;
- confidence;
- limitations;
- contradictions.

## Rules and ranking

The engine uses explicit, deterministic rules to:

- validate the request and context;
- aggregate evidence;
- evaluate constraints and contradictions;
- calculate fit, risk, freshness and learning value;
- assign a priority level;
- generate alternatives, metrics and invalidation criteria.

Rules are versioned and auditable. No hidden model inference is introduced here.

## Experimental bridge

Approved recommendations can be converted into experiment drafts by linking them to the existing Experiments module. This phase does not create a second source of truth for experiments.

## Privacy

- local processing only;
- no publication;
- no remote writes;
- no scraping;
- no passwords or tokens;
- no viewer PII;
- no cross-creator leakage;
- audit trail preserved;
- local deletion does not affect remote platforms.

## Next phase

Strategic Planning and Content Roadmap Foundation.
