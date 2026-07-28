# Thumbnail Lab and Titles Foundation

Thumbnail Lab and Titles Foundation adds a local, deterministic layer for evaluating titles, thumbnails, title+thumbnail pairs, brand fit, references, concepts, prompts, and review loops.

## What it does

- Registers title and thumbnail versions per packaging asset.
- Analyzes titles with explainable heuristics.
- Analyzes thumbnails with local image metadata and composition heuristics.
- Evaluates the title and thumbnail together against content, brand, platform, and history.
- Builds brand profiles from Creator Memory, Creator Language, Analytics, and historical packaging decisions.
- Manually registers reference assets and reference packages.
- Builds creative concepts, prompts, and designer briefs without calling image-generation APIs.
- Supports an optional review loop when a thumbnail is returned for critique.

## What it is not

- It is not image generation.
- It is not an image editor.
- It is not an automatic composition engine.
- It is not YouTube OAuth or market scraping.
- It is not a replacement for human review.

## Design principles

- Keep every title and thumbnail version immutable.
- Separate visually effective from brand-fit and content-fit judgments.
- Preserve evidence, contradictions, and confidence.
- Avoid copying external creators; extract principles only.
- Allow the user to export prompts and briefs without returning to the app.

## Main entities

- `packaging_assets`
- `title_versions`
- `thumbnail_versions`
- `packaging_reference_assets`
- `packaging_brand_profiles`
- `title_analysis_runs`
- `thumbnail_analysis_runs`
- `packaging_pair_evaluations`
- `thumbnail_frame_candidates`
- `creative_concepts`
- `creative_prompts`
- `thumbnail_reviews`
- `packaging_decisions`
- `packaging_experiment_links`

## Next step

The next phase is read-only YouTube integration, which will use packaging history and performance data but will not add publishing or editing automation.
See [`docs/YOUTUBE_READ_ONLY_INTEGRATION.md`](YOUTUBE_READ_ONLY_INTEGRATION.md) for the read-only channel, video, title, thumbnail and analytics sync layer.

Audience Model Foundation later consumes the same publication history and packaging performance as aggregate evidence for platform roles, content roles and affinities, without generating images or packaging suggestions automatically.
## TikTok Read-Only Integration

TikTok Read-Only Integration can attach cover metadata and packaging links for remote videos. The cover reference is stored as observed evidence only; it is not treated as a YouTube thumbnail, it is not downloaded by default, and changing the cover URL does not automatically confirm a visual change.
## Instagram Read-Only Integration

Instagram Read-Only Integration may attach cover and thumbnail metadata as observed evidence for Reels, posts and carousels without automatically downloading remote media. Instagram covers are stored as local evidence, not as a replacement for YouTube thumbnail assets.

## Market and Trend Intelligence Foundation

Market and Trend Intelligence Foundation may register external content, cover metadata and reference assets for comparison, but it does not download media automatically or equate external covers with approved thumbnails.
Strategic Planning may use packaging evidence as input, but it does not generate final thumbnails or titles.
