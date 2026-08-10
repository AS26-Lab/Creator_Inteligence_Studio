# FFmpeg Product Source Licensing

## Scope

This document covers the selected BtbN Windows FFmpeg bundle used for `v32-K`.

## License Layers

1. FFmpeg upstream is primarily LGPL 2.1 or later.
2. FFmpeg can become GPL if it is built with `--enable-gpl`.
3. The selected build variant is `lgpl`, so it is treated as the LGPL family, not GPL.
4. BtbN's repository and build scripts are MIT licensed.
5. Bundled third-party libraries keep their own upstream licenses and notices.

## What Was Verified

- the selected asset name contains `win64-lgpl`
- FFmpeg official legal documentation says GPL only applies if GPL parts are explicitly enabled
- BtbN README documents the `lgpl` and `gpl` variants separately
- the repository treats the product source as a catalog-approved external artifact, not as a product-owned binary
- the real validation run on `2026-08-10` installed the pinned artifact and reported `ffmpeg version n8.1.2-34-g9b6c8969e0-20260809`
- the installed bundle exposed `LICENSE.txt` at the package root and preserved bundled notices in the managed installation layout

## Compliance Implications

- preserve bundled license and notice files in managed installation
- do not relabel a GPL bundle as LGPL
- do not trust the filename alone if the build configuration changes
- if upstream switches the selected artifact to `--enable-gpl` or `--enable-nonfree`, the catalog entry must be requalified

## Distribution Notes

Creator Intelligence Studio may download, verify, and install the selected artifact through the managed component flow, but it must not invent a custom license claim. The product should present FFmpeg attribution, provider attribution, and the selected license variant plainly.

This is an engineering qualification note, not legal advice.
