# Audience Model Foundation

Audience Model Foundation adds a local, structured, traceable model of audience behavior based only on observed evidence already available in the product.

## Principles

- Model observed behavior, not invented personas.
- Keep data, measurements, groupings, patterns, inferences, hypotheses and unknowns separate.
- Do not infer age, gender, occupation, income, intent, personality or motivation without a valid source.
- Do not store PII or viewer-level identities.
- Do not treat traffic source as identity.
- Do not equate views with deep interest or returning viewers with community membership.
- Do not add new APIs, web research, scraping, LLMs or ML.

## Modes

The model tracks:

- acquisition;
- consumption;
- conversion;
- loyalty;
- engagement;
- content affinity;
- lifecycle;
- contradictions;
- temporal change;
- human review.

## Storage

Migration v22 adds local tables for:

- audience profiles and snapshots;
- normalized audience signals;
- segments and segment definitions;
- segment evidence;
- affinities;
- journeys and journey steps;
- human reviews;
- model runs with cache fingerprinting.

The schema is creator-isolated, idempotent, non-destructive and additive.

## Signal semantics

Supported signal families include acquisition, consumption, engagement, conversion, loyalty, affinity, geography, device, subscription status, traffic source, returning behavior, cross-content flow and data quality.

The model keeps platform semantics separate for:

- YouTube longform;
- YouTube Shorts;
- Instagram Reels;
- TikTok;
- manual_other.

Missing metrics stay missing. They are never treated as zero.

## Segments, affinities and journeys

Segments are observable groupings only. They may be system-defined, creator-defined or evidence-suggested, but evidence-suggested segments do not activate automatically.

Affinities are aggregated patterns over topic, format, duration, platform, title, thumbnail, hook, tone and series.

Journeys are aggregated and may be useful for analysis, but they remain explicitly unverifiable at the individual level.

## Review and history

- Profiles are versioned through snapshots.
- Reviews preserve previous value, new value, reason and timestamp.
- Contradictions are preserved instead of auto-resolved.
- Cache reuse is based on creator, source fingerprint, configuration and analyzer version.

## UI and CLI

Audience Model Foundation exposes:

- CLI commands for profiles, signals, segments, affinities, journeys, roles, reviews and export;
- a desktop Audience area with overview, signals, segments, affinities, journeys, platform roles, content roles, contradictions and history;
- Task Center support for build, retry, cancel and open profile.

## Data sources

Only local sources are used:

- YouTube Read-Only Integration;
- Analytics Data Foundation;
- Analytics Lab;
- manual publications;
- manual CSV/XLSX imports for Instagram Reels and TikTok;
- snapshots;
- imported Shorts, Reels and TikTok metrics;
- Experiments and Learning;
- Content Library;
- Creator Memory for creator context only.

## Validation

Synthetic coverage uses two creators:

- Creator A: entertainment, short-form discovery, longform loyalty, cross-format flow and a low-conversion high-reach topic.
- Creator B: education/music, search-led acquisition, strong retention, slow growth, strong subscriber conversion and an outlier period.

## Privacy

- aggregated data only;
- no PII;
- no viewer-level profiles;
- no names or emails;
- no hidden cross-creator leakage;
- no automatic export;
- local deletion remains controlled and auditable.

## Next phase

The next phase is Instagram Read-Only Integration.
## Instagram Read-Only Integration

Instagram Read-Only Integration now contributes additional local evidence for the same behavioral model. The audience layer remains aggregated and creator-scoped: it consumes Instagram account/media snapshots, captions, covers, insights and links as evidence only, not as personas or demographics.
