# Integration Security And Credentials

## Credential Boundary

Integration accounts store only opaque credential references in normal application state.

Allowed:

- `credential_ref`
- granted scopes / capabilities
- safe metadata summaries

For YouTube OAuth specifically:

- access tokens and refresh tokens stay behind the approved secure credential store
- account rows only retain opaque references and safe summaries
- desktop authorization uses the official loopback-style installed-app flow, not manual token paste
- the public OAuth application identity is materialized in the distributed bundle configuration at build time
- `H:\ALEJANDRO_2\ClientGoogle.json` and similar developer bootstrap files are build-only inputs, not runtime dependencies
- if the desktop OAuth bootstrap contains a `client_secret`, it is only used as a development/distributor bootstrap detail and is not stored in normal app state
- client configuration is developer/distributor responsibility, not end-user database state

Not allowed:

- raw access tokens
- refresh tokens
- client secrets
- plaintext secrets in SQLite account rows
- secrets in logs or diagnostic JSON

## Authentication States

- `not_linked`
- `linking`
- `connected`
- `expired`
- `revoked`
- `permission_missing`
- `error`

## Safety Rules

- creator A can never inspect or use creator B accounts
- read authentication does not imply write authorization
- destructive operations stay gated and explicit
- diagnostics expose safe summaries only
- all secrets remain behind the approved secure storage boundary

## Runtime Expectations

- offline tests must pass without real accounts
- provider errors should normalize to safe categories
- connector failures must degrade gracefully
- revocation or expiry should mark the account for relink rather than deleting creator-owned history
