# Market and Trend Intelligence Foundation

Date consulted: 2026-07-27

Market and Trend Intelligence Foundation adds a local, creator-scoped layer for market definitions, topics, sources, external observations, trend signals, patterns, fit evaluations, opportunity candidates, reviews, snapshots and reports.

## Official public YouTube discovery

The only automated public discovery source in this phase is the official YouTube Data API, used through documented endpoints:

- `search.list`
- `videos.list`
- `channels.list`
- `playlists.list`
- `playlistItems.list`
- `videoCategories.list`

The implementation uses official quota-aware requests and keeps public discovery separate from private creator connections.

## What this phase does

- registers markets, topics and external sources;
- records evidence and provenance;
- imports public YouTube discovery results when explicitly allowed;
- stores trend signals, patterns and opportunity candidates for human review;
- preserves creator isolation and historical snapshots;
- keeps manual imports as a separate evidence path;
- prepares the next phase: `Opportunity and Recommendation Engine`.

## What this phase does not do

- no scraping;
- no browser automation;
- no private APIs;
- no Research API for this commercial creator product;
- no LLM;
- no ML;
- no automatic recommendations;
- no editorial calendar generation;
- no publication or write operations;
- no copying of third-party identities or full formats.

## Source and evidence discipline

Every signal and candidate remains traceable back to a source, research run or import, and observed content or snapshot. Missing data stays missing. Platform metrics remain platform-specific and are not merged into a universal ranking.

## Relationship to other layers

- Analytics Data Foundation receives normalized snapshots and observations.
- Analytics Lab keeps cumulative and period metrics separate.
- Audience Model Foundation consumes only aggregate, creator-scoped evidence.
- Thumbnail Lab can link reference assets and cover metadata without treating them as automatic thumbnails.
- Multi-Platform Integration Consolidation remains the shared registry and lifecycle layer above native connectors.
Strategic Planning can read market snapshots as immutable input for objectives, freshness and scenario analysis, but it does not scrape or auto-schedule content from them.

Those market and trend inputs can later feed [`docs/CONTENT_BRIEF_AND_PRE_PRODUCTION_FOUNDATION.md`](docs/CONTENT_BRIEF_AND_PRE_PRODUCTION_FOUNDATION.md) without turning evidence into automatic production.
