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

## Future Expansion

Future real connectors can be added one by one without changing the contract version or the core product architecture.
