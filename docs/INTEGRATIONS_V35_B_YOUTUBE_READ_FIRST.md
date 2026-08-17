# Integrations v35-B YouTube Read-First

## Purpose

v35-B adds the first real integration connector behind the v35-A foundation.

The approved connector is:

- `youtube.connector`

The connector is read-first and creator-owned. It is not a publishing connector.

## Approved Capabilities

- `account_profile_read`
- `content_list_read`
- `content_metadata_read`
- `analytics_read`

## Explicit Non-Goals

- no uploads
- no publishing
- no scheduling
- no updates
- no deletes
- no comments mutation
- no automatic ingestion into Creator Corpus
- no Creator Voice mutation
- no preference mutation

## Official References Reviewed

The implementation was aligned to official Google documentation only:

- YouTube Data API v3 `channels.list`
- YouTube Data API v3 `playlistItems.list`
- YouTube Data API v3 `videos.list`
- YouTube Analytics API `reports.query`
- Google OAuth 2.0 for installed desktop applications using a loopback redirect flow

## Google Testing Behavior

The bundled OAuth client is still running under `External` + `Testing` in Google OAuth. For YouTube scopes, Google can issue refresh tokens that expire after a short testing window, including the commonly observed 7-day behavior. That expiry is a Google policy outcome, not a CIS credential-store defect.

## Closure State

- offline validation: implemented
- frozen packaging validation: implemented
- real-account certification: completed
- canonical credential lifecycle: implemented
- recovery-first profile reconciliation: implemented
- orphan credential cleanup: completed
- restart/recovery smoke: completed

The live certification validated a single real Google account connection end to end:

- `channels.list` minimum profile read returned `200`
- account profile read returned `200`
- small video listing succeeded
- metadata enrichment for a bounded sample succeeded
- non-monetary analytics query succeeded
- restart/recovery reused the stored credential without opening a browser
- the packaged runtime did not require `ClientGoogle.json`

## Quota And Rate-Limit UX

- quota and rate-limit failures are normalized into a user-visible `quota_exhausted` state
- `auth_expired`, `needs_attention`, and `provider_unavailable` remain separate user states for auth and provider failures
- last-updated and retry/reset information is shown only when the connector or provider can supply it
- no quota reset time is invented when the provider does not provide a reliable retry or reset value
- stale successful data remains visible when refresh is blocked by quota

## Creator Bootstrap Note

The live certification run used the normal creator-owned integration model. The isolated local certification database needed a single `creator-a` seed row before the first YouTube persistence write could succeed, which is a test-environment artifact of starting from an empty local database rather than a Google/OAuth defect. The normal product flow resolves creators through the catalog/bootstrap layer before integration persistence.

## Product Meaning

YouTube is the first approved real connector because it unlocks creator account identity, video inventory, content metadata, and creator analytics without requiring write access.
