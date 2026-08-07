# Component Manager v32-D Download Manager Foundation

## Purpose

v32-D adds a resumable, persistent download boundary for managed components. The boundary is intentionally separate from installation.

## Current Reality

- downloads are resumable, pausable, cancellable, and restart-recoverable
- partial state is persisted under the controlled `downloads` directory
- verified artifacts are produced before any installer is invoked
- the manager does not install, activate, or repair components automatically
- the current implementation allows local/test sources only; no product download sources are enabled yet
- the FFmpeg installer can consume a verified local artifact contractually
- the transcription runtime and model installers can also consume verified artifacts contractually

## Core Contract

`download != install`

Flow:

`catalog entry -> explicit download request -> queued -> downloading -> verifying -> completed_verified -> verified artifact`

After that, a later installer phase may consume the artifact and perform health checks and activation.
The installer is responsible for activation; the downloader only produces the verified artifact.

## State Machine

Tracked states:

- `queued`
- `preparing`
- `downloading`
- `pause_requested`
- `paused`
- `resume_requested`
- `verifying`
- `completed`
- `cancel_requested`
- `cancelled`
- `interrupted`
- `failed`

## Safety Rules

- HTTP/HTTPS only
- no automatic installation
- no automatic activation
- no PATH mutation
- no external internet sources enabled for product flows yet
- local/test localhost usage requires explicit test or developer approval

## Validation

- streaming chunks
- pause/resume
- cancel
- restart recovery
- size verification
- SHA-256 verification
- disk-space preflight
- Range handling
- ETag/Last-Modified tracking
