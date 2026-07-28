# YouTube Read-Only Integration

YouTube Read-Only Integration adds an official desktop OAuth connection to Google/YouTube that only uses read scopes and only imports data into local storage.

## Official documentation consulted

- OAuth for installed apps: https://developers.google.com/youtube/v3/guides/auth/installed-apps
- OAuth native app flow: https://developers.google.com/identity/protocols/oauth2/native-app
- OAuth scopes: https://developers.google.com/identity/protocols/oauth2/scopes
- YouTube Data API v3 docs: https://developers.google.com/youtube/v3/docs
- YouTube Data API channels: https://developers.google.com/youtube/v3/docs/channels
- YouTube Data API videos.list: https://developers.google.com/youtube/v3/docs/videos/list
- YouTube Analytics metrics: https://developers.google.com/youtube/analytics/metrics
- YouTube Analytics dimensions: https://developers.google.com/youtube/analytics/dimensions
- YouTube Analytics reference: https://developers.google.com/youtube/analytics/reference
- YouTube Analytics data model: https://developers.google.com/youtube/analytics/data_model
- YouTube Analytics content owner reports: https://developers.google.com/youtube/analytics/content_owner_reports
- OAuth revocation: https://oauth2.googleapis.com/revoke

## Read-only scopes

The integration is restricted to the following scopes:

- `https://www.googleapis.com/auth/youtube.readonly`
- `https://www.googleapis.com/auth/yt-analytics.readonly`

No write scope is requested or stored.

## What it imports

- connected channels;
- remote videos and Shorts classification when official evidence exists;
- titles, descriptions, thumbnails and remote metadata;
- official analytics metrics available to the authenticated account;
- incremental snapshots that preserve historical changes without overwriting prior records;
- local links to publications, video assets, title versions and thumbnail versions.

## What it does not do

- it does not upload, edit, delete or moderate YouTube content;
- it does not respond to comments;
- it does not manage playlists, monetization or account settings;
- it does not store tokens in plaintext in the main SQLite database;
- it does not download thumbnails unless explicitly configured;
- it does not use external LLMs or non-official APIs.

## Storage and privacy

- credential references are stored locally;
- access and refresh tokens remain in a protected credential backend when available;
- creator isolation is preserved;
- disconnect and revoke are local actions with no write operation against YouTube content.

## Downstream consumers

- Analytics Lab consumes imported metrics and snapshots.
- Thumbnail Lab consumes remote titles, thumbnail metadata and local links when available.

## Next phase

The next phase is Audience Model Foundation.

Audience Model Foundation consumes the read-only channels, videos, thumbnails and metrics from this integration as local evidence only. It does not add any YouTube write operation, does not scrape, and does not infer demographic profiles.
## Instagram bridge note

Instagram Read-Only Integration is documented separately in [`docs/INSTAGRAM_READ_ONLY_INTEGRATION.md`](INSTAGRAM_READ_ONLY_INTEGRATION.md). It uses the same local-evidence principle but a separate connector, separate storage, and no YouTube write operations.
TikTok Read-Only Integration is documented separately in [`docs/TIKTOK_READ_ONLY_INTEGRATION.md`](TIKTOK_READ_ONLY_INTEGRATION.md). It follows the same local-evidence principle with TikTok Login Kit and Display API only.

## Market intelligence note

Market and Trend Intelligence Foundation may reuse public YouTube discovery evidence, but only through the official public research adapter and without changing YouTube read-only semantics. It does not add broader crawling, scraping, or write operations.
