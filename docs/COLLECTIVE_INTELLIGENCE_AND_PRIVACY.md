# Collective Intelligence And Privacy

## Purpose

This document defines the approved privacy and collective intelligence model.

## Three Layers

1. Universal knowledge
2. Anonymous collective intelligence
3. Private creator memory

Participation in the collective layer must be:

- optional;
- off by default;
- explicit;
- revocable;
- visible;
- auditable.

## Data Prohibited From Collective Sharing

Never share:

- MP4;
- audio;
- transcripts;
- scripts;
- voice;
- humor;
- filler words;
- exact titles;
- exact captions;
- thumbnails;
- URLs;
- names;
- API keys;
- private projects.

## Data That Can Be Shared With Consent

With consent, and only after anonymization:

- platform;
- broad niche;
- sufficiently wide subcategory;
- account size range;
- duration;
- hook type;
- structure;
- percentiles;
- variation against own cohort;
- applied recommendation;
- relative result;
- experiment;
- confidence.

Use ranges, percentiles, and cohort minima.

Never change a global rule based on a single sample.

## Supabase And AS26 API

Approved decision:

- Supabase as initial provider;
- PostgreSQL as the database backend;
- the app never connects directly to PostgreSQL;
- AS26 API sits between the app and the database;
- contribution identifier is random and separate from account or license;
- global knowledge packages are versioned and signed;
- offline operation is possible with the last downloaded version;
- architecture remains standard enough to migrate away from Supabase later.

Do not deploy production until the user base justifies it.

## Privacy Rules

- creator isolation is mandatory;
- consent is mandatory for collective sharing;
- revocation must be possible;
- auditing must be possible;
- secrets stay out of SQLite, JSON, logs, and backups;
- support never receives API keys or passwords.

## Discrepancy Note

The current repository already has read-only platform integrations and local analytics foundations. Those are evidence sources, not permission to expose private creator material to the collective layer.

