# TikTok Read-Only Integration

TikTok Read-Only Integration adds an official, local-only connector for TikTok using Login Kit and Display API. It is limited to observation, local persistence and local exports requested by the user. It does not publish content, upload media, edit or delete remote content, manage comments or messages, scrape pages, or use unofficial APIs.

## Official sources consulted

Consulted on 2026-07-27 from TikTok for Developers only:

- https://developers.tiktok.com/
- Login Kit Overview
- Login Kit for Desktop
- Manage User Access Tokens
- Scopes Overview
- Scopes Reference
- Display API Overview
- Display API Get Started
- Get User Info
- List Videos
- Query Videos
- Rate Limits
- TikTok API v2 migration documentation
- Error handling
- App review and product approval
- Token revocation documentation when available

## Verified product behavior

- Desktop OAuth uses the official loopback redirect flow with localhost or 127.0.0.1 when registered.
- OAuth v2 authorization, token exchange, refresh and revocation are supported through official endpoints.
- The connector enforces a strict read-only allowlist.
- `video.publish` and `video.upload` are rejected.
- Login Kit and Display API approval status is tracked separately from user consent.
- Rate limits, cursor pagination and token expiration are persisted as operational state.

## Read-only scope allowlist

Approved scopes:

- `user.info.basic`
- `user.info.profile`
- `user.info.stats`
- `video.list`

Rejected scopes:

- `video.publish`
- `video.upload`
- any future write scope that is not explicitly approved

## Data model

Migration v24 adds creator-scoped tables for:

- connections;
- profiles;
- remote videos;
- text history;
- cover history;
- sync runs;
- sync items;
- metric imports and metric values;
- content links;
- rate-limit usage;
- sync schedules.

The SQLite main database stores only references, scope metadata, status and timestamps. Tokens, client secrets and authorization codes remain outside the main database.

## Data available from official APIs

Supported from official TikTok APIs when the relevant product and scopes are approved:

- authorized profile data;
- profile bio and links when the scope allows it;
- public profile statistics when the scope allows it;
- list of public videos owned by the authorized account;
- public video metadata;
- public counters exposed by the API.

## Data not available from Display API

The following remain separate manual or snapshot-based analytics inputs and are never inferred from public counters:

- watch time;
- average watch time;
- completion rate;
- retention curve;
- saves;
- profile views;
- traffic source;
- follower conversion;
- new or returning viewers;
- demographics;
- detailed For You traffic.

When the API does not return a value, the field remains missing or unavailable from API. It is never converted to zero.

## Sync behavior

- incremental sync with persisted cursor;
- resume after interruption;
- repair sync and cover refresh;
- deduplication by remote fingerprint;
- historical preservation of title, description and cover references;
- no automatic deletion of missing remote videos;
- no automatic full resync at startup.

## Compatibility with existing analytics

TikTok official counters feed Analytics Data Foundation as cumulative public snapshots only when available. Manual CSV/XLSX imports remain the path for private analytics and period metrics not exposed by Display API.

Analytics Lab, Audience Model Foundation and Thumbnail Lab receive only the compatible evidence they already support. No write capability is added anywhere in the stack.

## Privacy and revocation

- credential storage is local and protected;
- tokens are not stored in the main SQLite database;
- local disconnect removes local credentials and references;
- revocation is supported when the official endpoint is available;
- local deletion does not delete remote TikTok content.

## Operational limits

- product approval is required for production use;
- scopes can be partially granted by the user;
- missing approval or missing scopes remain explicit states;
- rate-limit handling is documented per endpoint;
- cover URLs may expire and are tracked as temporary references.

## Next phase

The next phase after this connector is Multi-Platform Integration Consolidation.
