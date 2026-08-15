# Integrations v35-A Foundation

## Purpose

v35-A creates the provider-neutral integration foundation for future connectors without enabling any real external provider in production flows.

## Implemented Boundary

- canonical integration contracts live under `src/creator_intelligence_studio/domain/integrations`
- `IntegrationService` provides the application boundary
- `IntegrationRegistry` discovers connector implementations
- `FakeIntegrationConnector` validates offline behavior
- `LocalNoAuthIntegrationConnector` proves multi-connector support
- integration diagnostics are exposed through the frozen runtime and CLI

## Current Guarantees

- account ownership is creator-scoped
- read and write capabilities are separated
- credential references are opaque
- secrets are not stored in plaintext integration rows
- no automatic corpus ingestion occurs
- Creator Voice remains unchanged by integration execution
- feedback and learning signals are not auto-generated from integration events

## Not Yet Implemented

- real social/video/storage/provider connectors
- OAuth provider flows
- automatic publishing
- background sync orchestration
- corpus ingestion from external accounts

## Validation

- connector registration and duplicate-ID rejection
- fake read and controlled fake write behavior
- creator isolation
- provider-down, auth-expired, permission-denied, and rate-limit handling
- packaged CLI smoke for `integrations list`
