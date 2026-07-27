# Instagram Read-Only Integration

Instagram Read-Only Integration adds an official, local-only connector for Instagram professional accounts. It is limited to observation and local persistence. It does not publish content, delete content, edit remote content, manage comments, manage messages or scrape remote pages.

## Documentation checked

Checked on `2026-07-27`.

- Meta / Instagram API with Instagram Login, Meta Postman collection: https://www.postman.com/meta/instagram/folder/6raa77c/instagram-api-with-instagram-login
- Meta / Instagram API with Facebook Login, Meta Postman collection: https://www.postman.com/meta/instagram/folder/9cgqucg/instagram-api-with-facebook-login
- Meta / Instagram API documentation and insights collection: https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api
- Facebook Help Center account linking: https://www.facebook.com/help/1148909221857370
- Graph API changelog: https://developers.facebook.com/docs/graph-api/changelog/

## API version and provider

- Configured Graph API version: `v25.0`
- Minimum supported version tracked in code: `v23.0`
- Provider abstraction:
  - `instagram_login` is the initial implementation;
  - `facebook_login` remains an isolated future adapter.

## Core guarantees

- read-only only;
- professional accounts only;
- no public posting;
- no comment or message management;
- no scraping;
- no unofficial APIs;
- no LLM or ML;
- no PII or viewer-level profiles;
- no tokens in the main SQLite database;
- no automatic export;
- creator isolation preserved;
- historical records preserved.

## Account scope

The connector is restricted to Instagram professional accounts:

- `business`
- `creator`

Personal accounts are rejected with a clear validation error. The connector keeps the failure local and does not create a partially valid import.

## OAuth and access model

- OAuth uses the official Instagram login path for professional accounts.
- The implementation keeps scopes on an allowlist and rejects any write scope.
- Access level and app access status are tracked explicitly so development, standard access, advanced access and review-related states stay visible.
- Disconnect and revoke are separate actions.
- Credential references are stored locally; secrets remain in a protected credential backend when available.

## Imported data

The integration imports only official read data that the API exposes for the connected professional account:

- basic account metadata;
- own media catalog;
- Reels, posts, carousels, Stories and Lives when the API exposes them;
- captions and media metadata;
- media URLs and thumbnail or cover metadata only as references, not as downloaded assets;
- official insights for account and media scopes;
- pagination cursors and incremental sync state;
- local snapshots and historical versions for captions and covers;
- local links to publications, video assets and packaging assets.

Missing data stays missing. It is not converted to zero and is not inferred.

## Semantics

- media type and product type are kept distinct;
- account metrics and media metrics are not collapsed into one bucket;
- empty datasets remain empty;
- limited retention windows are recorded as limitations;
- unavailable metrics are stored as unavailable, not fabricated;
- rate-limit headers are captured when available but are not treated as the official limit itself.

## Downstream consumers

- Analytics Data Foundation receives imported account and media snapshots.
- Analytics Lab consumes imported official insights as local evidence.
- Audience Model Foundation consumes only aggregated signals derived from imported Instagram evidence.
- Thumbnail Lab receives cover and thumbnail metadata for local linking.

## Security and privacy

- no access token, refresh token or authorization code is stored in the main SQLite database;
- no client secret or app secret is logged or exported;
- no viewer-level profile is generated;
- no cross-creator leakage is permitted;
- local deletion and revocation are explicit operations;
- CSV exports are protected against formula injection.

## Limitations

- official API coverage varies by media type and app access level;
- some metrics require permissions, access review or account eligibility;
- some Stories and Live data are time-limited or not available for every account;
- production desktop auth may require a backend or public redirect URI depending on the Meta flow in use;
- the connector does not implement Instagram publishing.

## Next phase

The next phase is TikTok Read-Only Integration.
