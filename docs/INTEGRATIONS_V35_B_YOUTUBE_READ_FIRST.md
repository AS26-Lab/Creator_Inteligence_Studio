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

## Closure State

- offline validation: implemented
- frozen packaging validation: implemented
- real-account certification: pending because no valid developer OAuth configuration was available in this closure

## Quota And Rate-Limit UX

- quota and rate-limit failures are normalized into a user-visible `quota_exhausted` state
- `auth_expired`, `needs_attention`, and `provider_unavailable` remain separate user states for auth and provider failures
- last-updated and retry/reset information is shown only when the connector or provider can supply it
- no quota reset time is invented when the provider does not provide a reliable retry or reset value
- stale successful data remains visible when refresh is blocked by quota

## Product Meaning

YouTube is the first approved real connector because it unlocks creator account identity, video inventory, content metadata, and creator analytics without requiring write access.
