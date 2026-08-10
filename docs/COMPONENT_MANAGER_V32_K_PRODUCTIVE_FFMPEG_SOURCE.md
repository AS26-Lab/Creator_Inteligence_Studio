# Component Manager v32-K Productive FFmpeg Source

## Status

`v32-K` qualifies a single productive source for the multimedia component only:

- `provider`: `btbn`
- `upstream_project`: `ffmpeg`
- `platform`: `windows`
- `architecture`: `x86_64`
- `license_variant`: `lgpl`
- `release_tag`: `autobuild-2026-08-09-13-03`
- `asset_name`: `ffmpeg-n8.1.2-34-g9b6c8969e0-win64-lgpl-8.1.zip`
- `source_url`: `https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-08-09-13-03/ffmpeg-n8.1.2-34-g9b6c8969e0-win64-lgpl-8.1.zip`
- `expected_sha256`: `6b4edff47f121d2ed218b1b19d17f67aed08f9f1c9cbcee576fd0548a748c412`
- `expected_download_bytes`: `145937826`
- `source_page_reference`: `https://github.com/BtbN/FFmpeg-Builds/releases/tag/autobuild-2026-08-09-13-03`

The selected source is pinned in the component catalog as `approved_product_source`. It is not a floating `latest` URL.

## Why This Source

- FFmpeg official documentation says FFmpeg only provides source code and points Windows users to BtbN builds.
- BtbN publishes Windows x86_64 `lgpl` and `gpl` variants.
- The selected asset name and release metadata match the pinned Windows x86_64 `lgpl` artifact.

## Download / Install Boundary

- download uses the existing resumable Download Manager
- install uses the existing FFmpeg managed installer
- download completion does not imply READY
- explicit install is still required after verification

## Safety Rules

- HTTPS only
- no user-entered source URL
- no fallback provider
- no auto-download on startup
- no auto-install on download completion
- SHA-256 is mandatory before install
- allowlist is limited to `github.com` and `release-assets.githubusercontent.com`

## Retention Risk

This artifact is a daily BtbN autobuild. BtbN documents that only the last 14 daily builds are retained, while the last build of each month is retained for two years. That means this pin is stable and exact, but it is not durable forever unless the release remains in the retained window.

## Validation Status

- offline regression tests pass
- pre-v32-K database compatibility is covered by test
- real internet download validation is opt-in through `CIS_RUN_PRODUCT_FFMPEG_DOWNLOAD=1`
- real internet download, verification, install, health check, and resolver validation passed on `2026-08-10`
- observed versions during validation: `ffmpeg version n8.1.2-34-g9b6c8969e0-20260809` and `ffprobe version n8.1.2-34-g9b6c8969e0-20260809`
