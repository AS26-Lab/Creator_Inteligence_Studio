# Integration Security And Credentials

## Credential Boundary

Integration accounts store only opaque credential references in normal application state.

Allowed:

- `credential_ref`
- granted scopes / capabilities
- safe metadata summaries

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
