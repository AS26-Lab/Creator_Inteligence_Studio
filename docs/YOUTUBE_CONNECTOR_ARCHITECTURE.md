# YouTube Connector Architecture

## Boundary

`YouTubeIntegrationConnector` lives behind the provider-neutral integration contract.

Application and domain layers talk to:

- `IntegrationRegistry`
- `IntegrationService`
- `IntegrationReadRequest` / `IntegrationReadResult`
- `IntegrationAccount`

Provider-specific Google/YouTube client behavior stays inside the connector implementation.

## Connector Identity

- connector id: `youtube.connector`
- provider: `youtube`
- contract version: `integration-contract-v1`
- authentication type: `oauth2`

## Supported Read Flow

The connector supports:

- authenticated channel profile reads
- uploaded video inventory reads
- video metadata reads
- non-monetary analytics reads

## Credential Handling

- OAuth tokens are stored only through the secure credential boundary
- general account rows store an opaque credential reference
- no raw token material is written to SQLite account metadata, logs, or diagnostic JSON

## Ownership

The connector is creator-scoped.

Creator A cannot use Creator B's linked YouTube account.

## Data Normalization

The connector normalizes:

- channel identity and public references
- uploaded video list entries
- video metadata with title, description, timestamps, status, and safe provider metadata
- analytics metrics with explicit availability and provenance

## Safety Rules

- read-only scopes only
- no write APIs
- no auto-ingest into Creator Corpus
- no Creator Voice mutation
- no preference mutation
- no background polling requirement

## Validation Strategy

The connector is validated with:

- offline fake clients
- frozen packaged runtime smoke
- creator-ownership checks
- rate-limit and expiry normalization

Real-account certification remains a separate gate.
