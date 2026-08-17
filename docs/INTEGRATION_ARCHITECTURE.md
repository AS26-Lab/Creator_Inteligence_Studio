# Integration Architecture

## Overview

The integration architecture is provider-neutral and optional.

```
external platform
-> connector implementation
-> IntegrationRegistry
-> IntegrationService
-> product workflows / diagnostics
```

The core product continues to work when no accounts are linked or when connectors are unavailable.

## Contracts

- `IntegrationConnectorDefinition`
- `IntegrationAccount`
- `IntegrationHealth`
- `IntegrationReadRequest` / `IntegrationReadResult`
- `IntegrationWriteRequest` / `IntegrationWriteResult`
- `ExternalContentResource`
- `IntegrationAnalyticsMetric`

The current registry includes three connector implementations:

- `fake.connector` for offline validation
- `local.connector` for local no-auth flows
- `youtube.connector` for the first real read-first provider adapter

## Key Rules

- creator ownership is mandatory
- read and write are different capabilities
- destructive capabilities remain separate and explicit
- connector health and user-visible quota/auth states are derived separately; quota exhaustion is surfaced as a user-facing state without inventing retry/reset times
- provider-specific raw metadata stays behind the connector boundary
- opaque `credential_ref` values are used instead of tokens in normal records
- network I/O lives only inside connector implementations

## Fake Connector Role

`FakeIntegrationConnector` is the canonical offline validation connector.

It is used to prove:

- connector registration
- capability filtering
- account linking abstraction
- read and write dispatch
- auth expiry
- permission denial
- rate limiting
- provider unavailability
- idempotent write behavior

## YouTube Read-First Role

`YouTubeIntegrationConnector` is the first real connector built behind this foundation.

It is intentionally read-only in v35-B and is limited to:

- account profile reads
- content inventory reads
- content metadata reads
- analytics reads

It does not expose write, publish, upload, schedule, update, delete, comment, or auto-ingest behavior.
Its OAuth application identity is resolved from the bundled application configuration at runtime; developer JSON bootstrap files are used only at build time to seed that bundle configuration.

## Instagram OAuth Role

`InstagramIntegrationConnector` should follow the same provider-neutral connector boundary, but its OAuth boundary is different from the Google desktop model.

- use Instagram API with Instagram Login for the provider path;
- keep the Meta App Secret server-side in the AS26 OAuth broker;
- start authorization, callback completion, and one-time redemption are broker responsibilities, not desktop responsibilities;
- the desktop only receives opaque transaction identifiers, safe status, and securely redeemed credential material;
- the v35-C2 profile-read slice resolves authenticated professional account metadata on top of that same credential boundary without exposing raw tokens to SQLite or UI code;
- the v35-C3 owned-media slice uses the same credential boundary to page own-media reads, preserve captions and carousel children, and keep cursor pagination bounded without invoking Insights;
- return only opaque credential references and safe metadata to the desktop app;
- keep raw access tokens and refresh tokens out of normal SQLite rows;
- preserve the local-first product boundary while delegating only the confidential OAuth exchange step to AS26.

## Future Expansion

Future real connectors can be added one by one without changing the contract version or the core product architecture.
