# Component Manager v32-K Productive FFmpeg Source

## Status

`v32-K` qualifies a single productive source for the multimedia component only:

- `provider`: `btbn`
- `upstream_project`: `ffmpeg`
- `platform`: `windows`
- `architecture`: `x86_64`
- `license_variant`: `lgpl`
- `release_tag`: `autobuild-2026-07-31-14-10`
- `asset_name`: `ffmpeg-n8.1.2-34-g9b6c8969e0-win64-lgpl-8.1.zip`
- `source_url`: `https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-07-31-14-10/ffmpeg-n8.1.2-34-g9b6c8969e0-win64-lgpl-8.1.zip`
- `expected_sha256`: `089e4169e93b2b3f3acbfced3c0704d24276a225641bdda04d796d28b07a2a38`
- `expected_download_bytes`: `145349121`
- `source_page_reference`: `https://github.com/BtbN/FFmpeg-Builds/releases/tag/autobuild-2026-07-31-14-10`

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

The previously validated daily pin `autobuild-2026-08-09-13-03` was real-call verified on `2026-08-10`, but BtbN documents that only the last 14 daily builds are retained. That makes the daily pin useful as evidence, not durable enough as the default product source.

The selected product pin is the month-end release `autobuild-2026-07-31-14-10`. BtbN documents that the last build of each month is kept for two years, so this is the durable retained-class choice for the product catalog.

Expected availability window: approximately until `2028-07-31`, subject to upstream policy changes or manual removal.

## Validation Status

- offline regression tests pass
- pre-v32-K database compatibility is covered by test
- real internet download validation is opt-in through `CIS_RUN_PRODUCT_FFMPEG_DOWNLOAD=1`
- real internet download, verification, install, health check, and resolver validation passed on `2026-08-10` for the month-end pin
- observed versions during validation stayed within the same `n8.1.2-34-g9b6c8969e0` release family and the release tag remained `autobuild-2026-07-31-14-10`
