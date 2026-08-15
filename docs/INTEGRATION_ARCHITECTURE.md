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

## Future Expansion

Future real connectors can be added one by one without changing the contract version or the core product architecture.
